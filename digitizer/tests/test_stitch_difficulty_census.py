"""`tools/stitch_difficulty_census.py` -- the speed question's measuring tool.

Each rule is pinned on a hand-built stream whose answer is known, so a later
edit cannot quietly change what "long satin" or "near hole" counts. Two
end-to-end checks ride on files: the committed Becker pro DST (no speed
commands, the bins add up) and a U01 that pystitch writes WITH SLOW/FAST, so
the tool is shown to see a speed command when one exists -- a census that
reports zero must be able to report one.
"""
from __future__ import annotations

import io
from pathlib import Path

import pystitch
import pytest

from tools import stitch_difficulty_census as sdc

ROOT = Path(__file__).resolve().parents[1]
BECKER_DST = ROOT / "testdata" / "reference" / "becker_hat_polo_large_beckers_logo_hat.dst"


def _run(points, cmd="stitch"):
    return [(x, y, cmd) for x, y in points]


def test_length_bins_and_quantiles():
    # Four sewn stitches: 0.3, 0.8, 2.0, 5.0 mm, plus one of 8.0 mm.
    pts = [(0, 0), (0.3, 0), (1.1, 0), (3.1, 0), (8.1, 0), (16.1, 0)]
    c = sdc.census(_run(pts))
    assert c["sewn_stitches"] == 5
    assert c["bins"] == {"lt_0p5": 0.2, "0p5_1": 0.2, "1_4": 0.2, "4_7": 0.2, "ge_7": 0.2}
    assert c["max_mm"] == 8.0


def test_a_jump_breaks_the_run_so_travel_is_not_a_stitch():
    stream = _run([(0, 0), (2, 0)]) + [(50, 0, "jump")] + _run([(50, 0), (52, 0)])
    c = sdc.census(stream)
    assert c["sewn_stitches"] == 2          # 0->2 and 50->52, never 2->50
    assert c["max_mm"] == 2.0


def test_long_satin_is_a_wide_swing_not_a_long_straight():
    zig = [(0, 0), (8, 0.2), (0, 0.4), (8, 0.6), (0, 0.8)]       # 8 mm swings
    straight = [(0, 0), (8, 0), (16, 0), (24, 0)]                  # 8 mm, no reversal
    assert sdc.census(_run(zig))["long_satin"] == 0.75             # 3 of 4 have a predecessor
    assert sdc.census(_run(straight))["long_satin"] == 0.0


def test_sharp_turn_counts_corners_but_not_satin_swings():
    square = [(0, 0), (3, 0), (3, 3), (0, 3), (0, 0)]             # three 90-degree turns
    assert sdc.census(_run(square))["sharp_turn"] == 0.75
    zig = [(0, 0), (3, 0.2), (0, 0.4), (3, 0.6)]
    assert sdc.census(_run(zig))["sharp_turn"] == 0.0


def test_near_hole_skips_the_two_ordinary_neighbours():
    # i-1 and i-2 within 0.5 mm do NOT count; i-3 does.
    close_neighbours = [(0, 0), (0.4, 0), (0.0, 0.1), (5, 5)]
    assert sdc.census(_run(close_neighbours))["near_hole"] == 0.0
    revisit = [(0, 0), (3, 0), (6, 0), (0.2, 0.1)]                # 4th lands on the 1st
    assert sdc.census(_run(revisit))["near_hole"] == 0.25


def test_peak_density_is_per_mm2_over_a_2mm_window():
    pts = [(0.5, 0.5)] * 8 + [(10.5, 10.5)]
    c = sdc.census(_run(pts))
    assert c["peak_density_per_mm2"] == 2.0                        # 8 penetrations / 4 mm2


def test_becker_pro_dst_carries_no_speed_command_and_its_bins_sum_to_one():
    row = sdc.file_row(BECKER_DST)
    assert "slow" not in row["commands"] and "fast" not in row["commands"]
    assert row["sewn_stitches"] > 10_000
    assert sum(row["bins"].values()) == pytest.approx(1.0, abs=1e-3)


def _u01_with_speeds() -> bytes:
    p = pystitch.EmbPattern()
    p.add_stitch_absolute(pystitch.STITCH, 0, 0)
    p.add_command(pystitch.SLOW)
    for i in range(1, 6):
        p.add_stitch_absolute(pystitch.STITCH, i * 30, 0)
    p.add_command(pystitch.FAST)
    p.add_stitch_absolute(pystitch.STITCH, 200, 0)
    p.end()
    buf = io.BytesIO()
    pystitch.write_u01(p, buf)
    return buf.getvalue()


def test_the_census_sees_a_speed_command_when_a_file_has_one(tmp_path):
    """The negative result in the review is only worth something if a
    positive one is reachable: U01 is the one format pystitch writes speeds
    to, and both the raw tally and the reader-side tally must find them."""
    data = _u01_with_speeds()
    raw = sdc.barudan_controls(data, 0x100)
    assert raw["slow"] == 1 and raw["fast"] == 1
    path = tmp_path / "speeds.u01"
    path.write_bytes(data)
    row = sdc.file_row(path)
    assert row["commands"].get("slow") == 1 and row["commands"].get("fast") == 1
    assert row["raw_controls"]["slow"] == 1


def test_only_u01_among_the_services_formats_writes_speeds():
    """The format half of the review, pinned: of what `/export` offers, only
    pystitch's U01 writer declares WRITES_SPEEDS. If a pystitch upgrade adds
    one, this fails and the review's question 1 needs re-answering."""
    import importlib

    from digitizer_service import formats

    writes = sorted(fmt for fmt in formats._WRITERS
                    if getattr(importlib.import_module(f"pystitch.{fmt.capitalize()}Writer"),
                               "WRITES_SPEEDS", False))
    assert writes == ["u01"]


def test_the_tool_is_off_every_path():
    """Nothing the engine, service or Studio runs may import the census."""
    for pkg in ("digitizer_core", "digitizer_service"):
        for py in (ROOT / pkg).rglob("*.py"):
            assert "stitch_difficulty_census" not in py.read_text(encoding="utf-8"), py
