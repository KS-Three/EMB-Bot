"""The lettering-arms card (`tools/sewout_card_lettering_arms.py`, 2026-10-14).

Fremont's EST / 1895 / THE / tagline on a Hat, in arms for two flags that were
built OFF and have never met cloth: `bean_letter_counter_hold_mm` (#952, block
A) and `small_letter_ties` (#956, blocks B1 at 81 mm and B2 at 92.5 mm), with
`small_text_true_size` ON in every arm by override. These tests pin the arms
(the overrides, the arm count, an md5 of each block's stitch output), regenerate
the card in a temp dir from the COMMITTED cuts, and check the file pystitch
reads back. The replay itself is not re-run (a digitize is minutes: `--cut`
makes the cuts). ROADMAP gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_lettering_arms as ca  # noqa: E402

COMMITTED = ca.DEFAULT_OUT

#: md5 of each block's stitch output, points rounded to 0.001 mm
BLOCK_MD5 = {
    "A": "@A@",
    "B1": "@B1@",
    "B2": "@B2@",
}
ARM_COUNT = 20


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardarms")
    rb = ca.generate(out, COMMITTED / "cuts", quiet=True)
    return out, rb


def test_the_cuts_differ_only_in_the_flag_under_test_and_are_valid_config():
    base = {"small_text_true_size": True}
    # the switch is ON in every cut, by override: the default is untouched
    for name, (_w, ov) in ca.CUTS.items():
        assert ov["small_text_true_size"] is True, name
        PipelineConfig(**ov)
    assert PipelineConfig().small_text_true_size is False
    assert PipelineConfig().bean_letter_counter_hold_mm is None
    assert PipelineConfig().small_letter_ties is False
    assert ca.CUTS["s81"] == (81.0, base) and ca.CUTS["s925"] == (92.5, base)
    assert ca.CUTS["s81_hold"][1] == {**base, "bean_letter_counter_hold_mm": 0.25}
    assert ca.CUTS["s81_ties"][1] == {**base, "small_letter_ties": True}
    assert ca.CUTS["s925_ties"][1] == {**base, "small_letter_ties": True}
    # every block: two arms, the first is the shared OFF cut at the block's own size
    assert set(ca.BLOCKS) == {"A", "B1", "B2"}
    for key, (_letter, size, arms, _words) in ca.BLOCKS.items():
        assert len(arms) == 2 and arms[0][0] == "off"
        assert ca.CUTS[arms[0][1]][0] == float(size) == ca.CUTS[arms[1][1]][0]
    assert ca.BLOCKS["A"][2][1] == ("hold", "s81_hold")
    assert ca.BLOCKS["B1"][2][1] == ("ties", "s81_ties") and ca.BLOCKS["B2"][2][1] == ("ties", "s925_ties")


def test_the_card_reads_back_whole_and_fits_the_4x4_hoop(card):
    out, rb = card
    assert (out / f"{ca.NAME}.dst").exists() and (out / "README.md").exists()
    assert (out / "scoring-sheet.md").exists() and (out / f"{ca.NAME}.png").exists()
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1
    assert max(rb["extent_mm"]) <= 100.0
    assert rb["max_record_axis_mm"] <= ca.v2.MAX_RECORD_MM


def test_the_arms_are_all_there_and_the_blocks_are_pinned(card):
    _out, rb = card
    assert len(rb["arm_md5"]) == ARM_COUNT, sorted(rb["arm_md5"])
    assert rb["block_md5"] == BLOCK_MD5
    # every word has both arms in every block it is in
    for key, (_l, _s, arms, words) in ca.BLOCKS.items():
        for word in words:
            for lbl, _cut in arms:
                assert f"{key}:{word}-{lbl}" in rb["arm_md5"]


def test_each_flag_changes_its_own_arms_only(card):
    _out, rb = card
    md5, n = rb["arm_md5"], rb["stitches_by_piece"]
    # A: the hold moves the needle points of both words
    for word in ("EST", "1895"):
        assert md5[f"A:{word}-off"] != md5[f"A:{word}-hold"], word
    # B: the ties add lock stitches, so ON sews at least as many; at least one word differs at each size
    for key in ("B1", "B2"):
        words = ca.BLOCKS[key][3]
        assert any(md5[f"{key}:{w}-off"] != md5[f"{key}:{w}-ties"] for w in words), key
    # the OFF arm of A and of B1 is the same cut: the same stitches
    for word in ("EST", "1895"):
        assert md5[f"A:{word}-off"] == md5[f"B1:{word}-off"]
        assert n[f"A:{word}-off"] == n[f"B1:{word}-off"]


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "colour_changes_file", "within_hoop", "blocks", "stitches_file", "block_md5", "arm_md5"):
        assert rb[key] == committed[key], key
