"""Sew-out card v5 (`tools/sewout_card_v5.py`, 2026-10-20): Fremont's small words
at 92.5 mm Hat, one row per arm -- today's bean and `bean_letter_satin_mm` 0.5 /
0.65 / 0.85. Regenerates the card from the COMMITTED cuts and checks the file
pystitch reads back. Gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig  # noqa: E402
from tools import sewout_card_v5 as c5  # noqa: E402

COMMITTED = c5.DEFAULT_OUT


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("card5")
    return out, c5.generate(out, COMMITTED / "cuts", quiet=True)


def test_arms_are_today_plus_one_satin_width():
    assert c5.CUTS["today"] == {} and c5.WIDTH_MM == 92.5
    assert PipelineConfig().bean_letter_satin_mm is None
    widths = [ov["bean_letter_satin_mm"] for k, ov in c5.CUTS.items() if k != "today"]
    assert widths == [0.5, 0.65, 0.85]
    for ov in c5.CUTS.values():
        PipelineConfig(**ov)


def test_the_card_fits_one_hoop_one_cone_and_reads_back(card):
    out, rb = card
    assert (out / f"{c5.NAME}.dst").exists() and (out / "scoring-sheet.md").exists()
    assert rb["stitches_file"] == rb["stitches_plan"]
    assert rb["within_hoop"] and rb["colours"] == 1 and max(rb["extent_mm"]) <= 100.0


def test_every_satin_row_differs_from_today_on_every_word(card):
    _out, rb = card
    md5 = rb["arm_md5"]
    for word in c5.ROW_WORDS:
        rows = [md5[f"R:{word}-{arm}"] for arm in c5.CUTS]
        assert len(set(rows)) == len(rows), word


def test_the_committed_readback_matches(card):
    _out, rb = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for key in ("colours", "within_hoop", "stitches_file", "arm_md5"):
        assert rb[key] == committed[key], key
