"""`tools/pro_satin_underlay.py` reads a stitch file's satin columns and what
is sewn under each, with no run kinds to lean on. Pinned here on columns our
own emitter sewed to a known underlay and wrote through the service's DST
writer, so the pro's table (`docs/settings-vs-pro-2026-10-21.md` rows 5a-5b,
re-measured 2026-10-22) rests on a reader that is checked against ground
truth, not on its own say-so.

The case that broke the first cut: a 2 mm column with a 1 mm run under it.
A stitch with an end outside the column's footprint was dropped whole, and
under a short column most of a run stitch is outside, so every column under
2.5 mm read bare. Stitches are clipped to the footprint now.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import stitches
from digitizer_core.export import write_dst
from digitizer_core.stage6_satin import satin_shape
from digitizer_core.stitches import StitchBlock, StitchPlan
from tools import pro_satin_underlay as psu


def _plan(runs) -> StitchPlan:
    return StitchPlan(
        blocks=[StitchBlock(thread_index=0, thread_number="1234", rgb=(10, 20, 30), runs=list(runs))],
        palette=[{"number": "1234", "name": "Test Thread", "rgb": [10, 20, 30]}],
        design_size_mm=(12.0, 8.0))


def _columns(tmp_path: Path, name: str, runs) -> list[dict]:
    path = write_dst(_plan(runs), tmp_path / f"{name}.dst")
    return psu.read_columns(psu.blocks_from_file(path), min_crosses=6)


@pytest.mark.parametrize("length", [2.0, 4.0, 12.0])
def test_a_column_with_a_centre_run_under_it_reads_centre_and_without_reads_bare(tmp_path, length):
    col = Polygon([(0, 0), (length, 0), (length, 1), (0, 1)])
    bare, _ = satin_shape(col, "S", underlay_style="none", trim_at_mm=3.0)
    under, _ = satin_shape(col, "S", underlay_style="center_run", trim_at_mm=3.0,
                           short_column_underlay=True)
    assert stitches.UNDERLAY in {r.kind for r in under}
    rb = _columns(tmp_path, f"bare{length}", bare)
    ru = _columns(tmp_path, f"under{length}", under)
    assert len(rb) == 1 and len(ru) == 1, "one column each"
    assert rb[0]["bare"] is True
    assert ru[0]["bare"] is False
    assert "centre" in ru[0]["kinds"]
    assert "zigzag" not in ru[0]["kinds"]
    assert abs(ru[0]["width"] - 1.0) < 0.3


def test_our_wide_column_zigzag_reads_as_rungs_and_rail_steps(tmp_path):
    col = Polygon([(0, 0), (12, 0), (12, 4), (0, 4)])
    under, _ = satin_shape(col, "S", underlay_style="zigzag", trim_at_mm=3.0)
    kinds = [r.kind for r in under]
    assert kinds.count(stitches.UNDERLAY) == 2, "centre run + zigzag"
    rows = _columns(tmp_path, "zz", under)
    assert len(rows) == 1
    r = rows[0]
    assert r["bare"] is False
    # Ours is a LADDER, not the pro's zigzag: `_stroke_underlay` lays a rung
    # across at each station (no advance along the column) and then a step
    # along one rail to the next (`machine.SATIN_ZIGZAG_PITCH_MM`), so the
    # reader sees rungs (zigzag, advance ~0) and rail steps (edge). The
    # pro's legs cross AND advance 1.1-1.3 mm each. Found 2026-10-22 by
    # this test; the centre run's five stitches sit under KIND_SHARE here.
    assert "zigzag" in r["kinds"] and "edge" in r["kinds"], r["kinds"]
    assert r["zz_pitch"] < 0.3, "a rung does not advance along the column"


def test_a_fan_corner_s_own_crosses_are_not_underlay(tmp_path):
    """Rail-to-rail thread advancing under a millimetre is satin, whoever
    sewed it; the column mask does not reach the long outer steps of a
    corner fan, and without the advance gate they read as zigzag."""
    # an L sewn as one shape: the corner fan's crosses are its own
    ell = Polygon([(0, 0), (8, 0), (8, 1.5), (1.5, 1.5), (1.5, 8), (0, 8)])
    runs, _ = satin_shape(ell, "S", underlay_style="none", trim_at_mm=3.0)
    rows = _columns(tmp_path, "ell", runs)
    assert rows, "the L reads as columns"
    assert all(r["bare"] for r in rows), [r["kinds"] for r in rows]
