"""Sew-out card v4 (`tools/sewout_card_v4.py`, 2026-10-20).

One hoop, one cone, Fremont 81 mm Hat on TODAY'S defaults: every cut is the
default config plus at most the one flag its block names, so the 1-tooth arm of
every block is what ships. These tests pin the cuts' overrides, regenerate the
card in a temp dir from the COMMITTED cuts and check the file pystitch reads
back. The replay itself is not re-run (a digitize is minutes: `--cut` makes the
cuts). ROADMAP gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_v4 as c4  # noqa: E402

COMMITTED = c4.DEFAULT_OUT


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("card4")
    rb = c4.generate(out, COMMITTED / "cuts", quiet=True)
    return out, rb


def test_every_cut_is_todays_defaults_plus_one_flag():
    assert c4.CUTS["today"] == {}
    for name, ov in c4.CUTS.items():
        PipelineConfig(**ov)
        assert len(ov) <= 2, name          # holds_off names both holds: one question
    # the 1-tooth arm of every block is the baseline cut, sewn as shipped
    for key, (_l, arms, _w) in c4.BLOCKS.items():
        assert arms[0][1] == "today", key
    # the defaults the arms are read against, as of the cut (2026-10-20)
    d = PipelineConfig()
    assert d.bean_letter_straight_mm == 0.7
    assert d.bean_letter_counter_hold_mm == 0.25 and d.bean_letter_bay_hold == 0.2
    assert d.small_letter_ties is False and d.bean_letter_passes is None   # None = 3


def test_the_card_reads_back_whole_and_fits_one_4x4_hoop_one_cone(card):
    out, rb = card
    for f in (f"{c4.NAME}.dst", f"{c4.NAME}.png", "README.md", "scoring-sheet.md"):
        assert (out / f).exists(), f
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1
    assert max(rb["extent_mm"]) <= 100.0
    assert rb["max_record_axis_mm"] <= c4.v2.MAX_RECORD_MM


def test_every_arm_is_there(card):
    _out, rb = card
    want = {f"{k}:{w}-{lbl}" for k, (_l, arms, _w) in c4.BLOCKS.items() for w in c4.words_of(k) for lbl, _c in arms}
    assert want <= set(rb["arm_md5"]), sorted(want - set(rb["arm_md5"]))


def test_the_baseline_arm_is_the_same_stitches_wherever_it_sits(card):
    _out, rb = card
    md5 = rb["arm_md5"]
    assert md5["B:1895-0.7"] == md5["H:1895-on"]
    assert md5["H:THE-on"] == md5["K:THE-off"]
    assert md5["H:1895-on"] == md5["P:1895-3"]


def test_every_arm_differs_where_the_question_is_asked(card):
    # a block whose arms sew the same stitches asks the cloth nothing (the skeleton
    # and fold-cut blocks were dropped for exactly this); EST in K is the control
    _out, rb = card
    assert rb["same_arms"] == ["K EST: arms off, ties identical"], rb["same_arms"]


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "within_hoop", "blocks", "stitches_file", "block_md5", "arm_md5"):
        assert rb[key] == committed[key], key
