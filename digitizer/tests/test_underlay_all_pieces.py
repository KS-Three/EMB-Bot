"""`underlay_all_pieces` (built OFF 2026-10-08): the fill underlay's inset
splits a shape at any neck under twice `UNDERLAY_INSET_MM`, and only the
largest piece used to get underlay. On, every piece does."""
from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon, box

from digitizer_core import machine, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.stage6_fill import _underlay_paths, stitch_shape

# Two 10 x 10 mm squares joined by a 1 mm neck: the 1.0 mm inset parts them.
DUMBBELL = box(0, 0, 10, 10).union(box(10, 4.5, 20, 5.5)).union(box(20, 0, 30, 10))
LEFT, RIGHT = box(0, 0, 10, 10), box(20, 0, 30, 10)


def _pieces_hit(paths):
    pts = [Point(p) for path in paths for p in path]
    return {name for name, sq in (("L", LEFT), ("R", RIGHT))
            if any(sq.contains(pt) for pt in pts)}


def test_the_flag_is_off_by_default():
    assert PipelineConfig().underlay_all_pieces is False


def test_the_inset_really_splits_the_fixture():
    assert DUMBBELL.buffer(-machine.UNDERLAY_INSET_MM).geom_type == "MultiPolygon"


@pytest.mark.parametrize("style", ["edge_run", "edge_lattice", "zigzag",
                                   "double_lattice", "center_run", "cross_tatami"])
def test_off_underlays_one_piece_on_underlays_both(style):
    off = _underlay_paths(DUMBBELL, style, 0.0, (0.0, 0.0))
    on = _underlay_paths(DUMBBELL, style, 0.0, (0.0, 0.0), all_pieces=True)
    assert len(_pieces_hit(off)) == 1
    assert _pieces_hit(on) == {"L", "R"}
    inner = DUMBBELL.buffer(-machine.UNDERLAY_INSET_MM + 1e-6)
    assert all(inner.contains(Point(p)) for path in on for p in path)


def test_on_starts_at_the_piece_nearest_the_needle():
    on = _underlay_paths(DUMBBELL, "edge_run", 0.0, (30.0, 5.0), all_pieces=True)
    assert RIGHT.contains(Point(on[0][0]))
    assert LEFT.contains(Point(on[-1][-1]))


def test_an_unsplit_shape_is_byte_identical_either_way():
    sq = Polygon([(0, 0), (20, 0), (20, 12), (0, 12)])
    for style in ("edge_run", "edge_lattice", "cross_tatami"):
        assert (_underlay_paths(sq, style, 30.0, (1.0, 1.0))
                == _underlay_paths(sq, style, 30.0, (1.0, 1.0), all_pieces=True))


def test_stitch_shape_carries_the_flag():
    def under(flag):
        runs, _ = stitch_shape(DUMBBELL, "S1", angle_deg=0.0, row_mm=machine.FILL_ROW_MM,
                               stitch_mm=machine.FILL_STITCH_MM, underlay_style="edge_run",
                               trim_at_mm=machine.TRIM_AT_MM, start_near=(0.0, 0.0),
                               underlay_all_pieces=flag)
        return [r.points for r in runs if r.kind == stitches.UNDERLAY]
    assert len(_pieces_hit(under(False))) == 1
    assert _pieces_hit(under(True)) == {"L", "R"}


def test_a_sliver_piece_stays_bare():
    # A 1.2 mm stub off the neck insets to a piece far under one stitch square.
    shape = DUMBBELL.union(box(14, 5.5, 16.6, 8.1))
    parts = shape.buffer(-machine.UNDERLAY_INSET_MM)
    small = [g for g in parts.geoms if g.area < machine.UNDERLAY_STITCH_MM ** 2]
    assert small
    on = _underlay_paths(shape, "edge_run", 0.0, (0.0, 0.0), all_pieces=True)
    pts = [Point(p) for path in on for p in path]
    assert not any(g.buffer(1e-6).contains(pt) for g in small for pt in pts)
    assert _pieces_hit(on) == {"L", "R"}
