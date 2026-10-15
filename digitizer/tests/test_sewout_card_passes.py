"""The pass-count swatch (`tools/sewout_card_passes.py`, 2026-10-14).

Fremont's THE and 1895 at 81 mm on a Hat, `small_text_true_size` ON, sewn
with one, two and three bean passes side by side: the cloth answers how wide
stacked thread lays (the renderer draws it as one thread). These tests pin the
arms, regenerate the card in a temp dir from the COMMITTED cuts, and check the
file pystitch reads back. The replay itself is not re-run (a digitize is
minutes: `--cut` makes the cuts). ROADMAP gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_passes as cp  # noqa: E402

COMMITTED = cp.DEFAULT_OUT


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardpasses")
    rb = cp.generate(out, COMMITTED / "cuts", quiet=True)
    return out, rb


def test_the_arms_differ_only_in_passes_and_are_valid_config():
    assert cp.ARM_ORDER == ("p1", "p2", "p3") and cp.BLOCKS == ("T", "N")
    base = {k: v for k, v in cp.ARMS["p1"].items() if k != "bean_letter_passes"}
    for n, arm in enumerate(cp.ARM_ORDER, start=1):
        assert cp.ARMS[arm] == {**base, "bean_letter_passes": n}
        cfg = PipelineConfig(**cp.ARMS[arm])
        assert cfg.bean_letter_passes == n and cfg.bean_letter_max_stroke_mm == 0.5
    assert base == {"small_text_true_size": True}


def test_the_card_reads_back_whole_and_fits_the_hoop(card):
    out, rb = card
    assert (out / f"{cp.NAME}.dst").exists()
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1
    assert rb["max_record_axis_mm"] <= cp.v2.MAX_RECORD_MM


def test_every_block_has_three_arms_and_more_passes_sew_more(card):
    _out, rb = card
    by = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    for blk in cp.BLOCKS:
        n = [by[(blk, a)]["stitches"] for a in cp.ARM_ORDER]
        assert n[0] < n[1] < n[2], (blk, n)
        # the same letters in every arm: the boxes agree to a stitch width
        w = [by[(blk, a)]["width_mm"] for a in cp.ARM_ORDER]
        assert max(w) - min(w) < 0.5, (blk, w)


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "colour_changes_file", "within_hoop", "blocks"):
        assert rb[key] == committed[key], key
    assert abs(rb["stitches_file"] - committed["stitches_file"]) <= 0.03 * committed["stitches_file"]
