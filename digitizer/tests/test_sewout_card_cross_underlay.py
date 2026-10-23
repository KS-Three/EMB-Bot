"""Sew-out card for `cfg.fill_underlay_cross` (`tools/sewout_card_cross_underlay.py`,
2026-10-21): a tatami plate on a hat and on a polo, the preset's own underlay
beside the pro's crossing pass. Regenerates the card from the COMMITTED cut
and checks the file pystitch reads back. Gate 1: the cloth is Kent's.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, fabrics  # noqa: E402
from tools import sewout_card_cross_underlay as cu  # noqa: E402

COMMITTED = cu.DEFAULT_OUT


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("card_cu")
    return out, cu.generate(out, COMMITTED / "cuts", quiet=True)


def test_the_arms_are_the_flag_off_and_on():
    assert PipelineConfig().fill_underlay_cross is False
    assert [ov for _l, ov in cu.ARMS] == [{"fill_underlay_cross": False}, {"fill_underlay_cross": True}]
    # each card's garment is one the flag moves
    for g in cu.GARMENTS.values():
        assert fabrics.GARMENT_FABRIC[g] in fabrics.CROSS_UNDERLAY_FABRICS


def test_each_card_fits_one_hoop_one_cone_and_reads_back(card):
    out, result = card
    for name, rb in result["cards"].items():
        assert (out / f"card_cross_underlay_{name}_40wt.dst").exists()
        assert rb["stitches_file"] == rb["stitches_plan"]
        assert rb["within_hoop"] and rb["colours"] == 1 and max(rb["extent_mm"]) <= 95.0
    assert (out / "scoring-sheet.md").exists() and (out / "README.md").exists()


def test_the_cross_arm_lays_more_underlay_than_the_preset(card):
    _out, result = card
    for rb in result["cards"].values():
        by = {p["arm"]: p for p in rb["pieces"]}
        assert by["cross"]["underlay_mm"] > by["preset"]["underlay_mm"]
        assert by["cross"]["underlay_share_pct"] > 10.0     # the pro's 8-20%
        assert rb["arm_md5"]["U:cross"] != rb["arm_md5"]["U:preset"]


def test_the_committed_readback_matches(card):
    _out, result = card
    committed = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    for name, rb in result["cards"].items():
        for key in ("colours", "within_hoop", "stitches_file", "arm_md5"):
            assert rb[key] == committed["cards"][name][key], (name, key)
