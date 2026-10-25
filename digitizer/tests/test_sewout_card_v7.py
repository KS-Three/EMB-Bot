"""Sew-out card v7 (`tools/sewout_card_v7.py`, 2026-10-25): the two flags still
waiting on fabric, `pull_comp_by_stroke` and `pro_measured_values`, as a 2 x 2
of arms on Fremont at 92.5 mm Hat, a fill plate and Becker MARINE at 76.5 mm
Hat.
Regenerates the card from the COMMITTED cuts and checks the file pystitch
reads back. Gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_v7 as c7  # noqa: E402

COMMITTED = c7.DEFAULT_OUT
FIELDS = {f.name for f in dataclasses.fields(PipelineConfig)}


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("card7")
    return out, c7.generate(out, COMMITTED / "cuts", quiet=True)


def test_each_arm_pins_both_fabric_flags_explicitly():
    want = {"a": (False, False), "b": (True, False), "c": (False, True), "d": (True, True)}
    assert list(c7.ARMS) == list(want)
    for arm, (pull, pro) in want.items():
        ov = c7.overrides(arm)
        assert ov["pull_comp_by_stroke"] is pull and ov["pro_measured_values"] is pro, arm
        assert set(ov) == set(c7.BASE) | set(c7.FABRIC_FLAGS), arm
        assert set(ov) <= FIELDS, set(ov) - FIELDS
        PipelineConfig(**ov)
    assert [c7.TEETH[a] for a in c7.ARMS] == [1, 2, 3, 4]


def test_base_carries_the_ruled_flips_never_the_fabric_flags():
    """Every arm pins both fabric flags itself, so a later default flip of
    either changes nothing on the card."""
    assert not set(c7.BASE) & set(c7.FABRIC_FLAGS)
    assert c7.BASE["small_text_cap_mm"] == 4.0 and c7.BASE["fill_underlay_cross"] is True


def test_the_committed_cuts_carry_each_arms_flag_set():
    for job in c7.JOBS:
        cut = c7.load(COMMITTED / "cuts", job)
        assert cut["base"] == c7.BASE
        assert set(cut["arms"]) == set(c7.ARMS)
        for arm, a in cut["arms"].items():
            assert a["overrides"] == c7.overrides(arm), (job, arm)


def test_fremont_and_plate_b_and_d_are_a_and_c_so_they_sew_two_arms():
    """The pull fit returns the hat's own 0.4 on Fremont's ~0.85 mm strokes;
    the plate has no column."""
    for job in ("fremont", "plate"):
        assert c7.same_as(c7.load(COMMITTED / "cuts", job)) == {"b": "a", "d": "c"}, job
        assert c7.SEWN[job] == ("a", "c"), job


def test_every_becker_arm_differs_and_pull_narrows_the_columns(card):
    cut = c7.load(COMMITTED / "cuts", "becker")
    assert c7.same_as(cut) == {}
    _out, rb = card
    w = {p["arm"]: p["satin"]["width_mm"] for p in rb["pieces"] if p["block"] == "M"}
    assert w["b"] < w["a"] and w["d"] < w["c"], w


def test_pull_on_sews_marine_plain_like_the_pro_and_off_splits_it(card):
    _out, rb = card
    split = {p["arm"]: p["satin"]["split_pct"] for p in rb["pieces"] if p["block"] == "M"}
    pro = rb["pro_satin"]["M"]
    assert pro["split_pct"] < 20 and 3.8 < pro["width_mm"] < 4.2, pro
    assert split["a"] > 50 and split["c"] > 50, split
    assert split["b"] < 20 and split["d"] < 20, split


def test_pro_values_reach_the_satin_the_fill_and_the_cap(card):
    _out, rb = card
    got = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    assert got["F", "a"]["satin"]["rail_step_mm"] == 0.4 and got["F", "c"]["satin"]["rail_step_mm"] == 0.37
    assert got["P", "a"]["fill"]["fill_stitch_mm"] == 3.0 and got["P", "c"]["fill"]["fill_stitch_mm"] == 3.49
    assert got["P", "a"]["fill"]["cap_stitch_mm"] < got["P", "c"]["fill"]["cap_stitch_mm"]


def test_the_card_fits_one_hoop_one_cone_and_reads_back(card):
    out, rb = card
    assert (out / f"{c7.NAME}.dst").exists()
    assert (out / f"{c7.NAME}_worksheet.png").exists() and (out / f"{c7.NAME}_worksheet.pdf").exists()
    assert all((out / f"arm_{a}.jpg").exists() for a in c7.ARMS)
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1 and max(rb["extent_mm"]) <= 100.0


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "within_hoop", "stitches_file", "trims", "arm_md5", "same_as"):
        assert rb[key] == committed[key], key
