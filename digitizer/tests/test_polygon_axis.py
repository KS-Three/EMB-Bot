"""Tests for digitizer_core/polygon_axis.py — the geometry, and the flag.

`cfg.satin_polygon_axis` is only worth anything if the axis it swaps in is a
real medial axis, so these pin it on shapes whose axis is known exactly, plus
the grid mapping it is drawn on and the census's fold metric. Cheap: one
`_rasterize` call, no pipeline run.
"""
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import box
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import decomposition_census as dc  # noqa: E402
from digitizer_core import polygon_axis as pa  # noqa: E402


def _pts(segs):
    return np.asarray([p for s in segs for p in s])


def test_a_bar_is_one_spine_with_no_corner_hooks():
    """The H defect's construction: a square-capped bar. Its medial axis is
    the centre line ending one half-width short of each cap, and nothing
    runs into a corner. Leaf-length pruning left a diagonal hook into one
    corner at each end here (y reached 1.93); the arc-residual test must not."""
    p = _pts(pa.axis_segments(box(0, 0, 10, 2), 0.05))
    assert np.allclose(p[:, 1], 1.0, atol=1e-6)
    assert p[:, 0].min() >= 1.0 - 1e-6 and p[:, 0].max() <= 9.0 + 1e-6
    assert p[:, 0].max() - p[:, 0].min() > 7.9


def test_a_crossing_keeps_all_four_arms():
    plus = unary_union([box(-5, -1, 5, 1), box(-1, -5, 1, 5)])
    p = _pts(pa.axis_segments(plus, 0.05))
    assert p[:, 0].min() < -3.9 and p[:, 0].max() > 3.9
    assert p[:, 1].min() < -3.9 and p[:, 1].max() > 3.9
    # every axis point lies on one of the two centre lines
    on_line = np.minimum(np.abs(p[:, 0]), np.abs(p[:, 1]))
    assert on_line.max() < 1e-6


def test_a_ring_has_no_twigs_into_its_hole_corners():
    """Hole and exterior are never 'close along the boundary', so a ring's
    axis runs round it. At each inside corner the true axis ROUNDS the
    reflex vertex on a parabolic arc (2.34 mm off the outer edge at the
    diagonal on this ring), so the axis is not all on the 2.0 mm centre
    line; what must not exist is a twig toward an OUTER corner, which would
    come closer to the boundary than the half-width."""
    ring = box(0, 0, 40, 20).difference(box(4, 4, 36, 16))
    p = _pts(pa.axis_segments(ring, 0.05))
    d_out = np.minimum.reduce([p[:, 0], 40 - p[:, 0], p[:, 1], 20 - p[:, 1]])
    d_hole = np.maximum.reduce([4 - p[:, 0], p[:, 0] - 36, 4 - p[:, 1], p[:, 1] - 16])
    assert d_out.min() > 1.94
    assert d_out.max() < 2.4
    assert (d_hole > 0).all(), "the axis never enters the hole"


def test_fold_metric_reads_the_n_weld_angle():
    straight = [(0, 0), (5, 0), (10, 0)]
    assert dc.max_turn_deg(straight, 0.5) == 0.0
    # a stem welded to a diagonal through the 108 deg fold the N measured
    turn = math.radians(108)             # heading change, not interior angle
    weld = [(0, 0), (5, 0), (5 + 5 * math.cos(turn), 5 * math.sin(turn))]
    assert abs(dc.max_turn_deg(weld, 0.5) - 108.0) < 1.0


def test_the_flag_defaults_off_and_off_never_imports_the_module():
    """OFF is the pre-2026-09-16 engine. The import is the cheap proof that
    the shipped path does not run any of this: `extract_strokes` imports
    `polygon_axis` inside the ON branch."""
    import ast
    from digitizer_core.config import PipelineConfig

    assert PipelineConfig().satin_polygon_axis is False
    src = Path(__file__).resolve().parents[1] / "digitizer_core" / "stage6_satin.py"
    tree = ast.parse(src.read_text(encoding="utf-8"))
    top = [n for n in ast.walk(tree)
           if isinstance(n, ast.ImportFrom) and n.module == "polygon_axis"
           and isinstance(getattr(n, "col_offset", 0), int) and n.col_offset == 0]
    assert not top, "polygon_axis must be imported inside the flag's branch, not at module level"


def test_the_flag_removes_the_corner_hooks_a_thinned_raster_grows():
    """The construction's point, on the engine's own entry point: a bar's
    raster skeleton is pruned by twig LENGTH and its cap corners still bend
    the spine; the polygon axis is straight."""
    from digitizer_core import stage6_satin as s6

    bar = box(0, 0, 12, 2.4)
    off, half_off, _f = s6.extract_strokes(bar)
    on, half_on, _f2 = s6.extract_strokes(bar, polygon_axis=True)
    assert on and off
    assert len(on) == 1, [len(s.spine) for s in on]
    ys = np.asarray([p[1] for s in on for p in s.spine])
    assert np.abs(ys - 1.2).max() < 0.2, "the polygon axis is the bar's centre line"
    # The mean half-width MOVES, and that is a property worth pinning rather
    # than a defect: it is averaged over skeleton pixels, and the thinned
    # skeleton's corner twigs sit in narrow ground, dragging the mean below
    # the bar's true 1.2 mm (1.12 here). The polygon axis is spine only, so
    # it reads the stroke (1.33 at this raster pitch). Every length threshold
    # downstream is stated in this number, so a flip moves them with it.
    assert half_off < 1.2 < half_on


def test_stage7_passes_the_flag_to_both_readers():
    """`satin_shape` decomposes on a skeleton and `_stroke_rows` classifies on
    one. If the flag reached only one, a shape would be ROUTED on one skeleton
    and SEWN on another."""
    import inspect

    from digitizer_core import stage6_satin as s6
    from digitizer_core import stage7_sequence as s7

    src = inspect.getsource(s7)
    assert "polygon_axis=cfg.satin_polygon_axis" in src
    assert src.count("polygon_axis=cfg.satin_polygon_axis") == 2, "satin_shape AND classify_ribbon"
    for fn in (s6.satin_shape, s6.extract_strokes, s6.classify_ribbon,
               s6.classify_strokes, s6._stroke_rows, s6._stroke_rung_takes):
        assert "polygon_axis" in inspect.signature(fn).parameters, fn.__name__


def test_draw_axis_lands_on_the_rasterizer_grid():
    """The axis is drawn with `_rasterize`'s own mapping, so the walker reads
    it where the raster skeleton would have been."""
    from digitizer_core import stage6_satin as s6

    bar = box(0, 0, 10, 2)
    mask, scale, ox, oy = s6._rasterize(bar)
    skel = pa.draw(pa.axis_segments(bar, 0.5 / scale), mask, scale, ox, oy)
    ys, xs = np.nonzero(skel)
    assert len(xs) > 0
    mm_y = oy + (ys + 0.5) / scale
    assert np.abs(mm_y - 1.0).max() <= 1.0 / scale
    assert (mask[ys, xs] > 0).all()


def test_the_axis_source_modes_pick_the_right_polygon():
    """`satin_polygon_axis` is a MODE, because no rule separates the two cases
    it has to serve: stage 5's round-join growth is what over-stitched drone's
    M (149 vertices against the artwork's 15), and the same smoothing is what
    keeps becker's blocky 1.8 px/mm artwork off bare cloth (12.2 mm2 from the
    grown polygon, 34.5 from its own artwork)."""
    from digitizer_core.stage6_satin import _AXIS_SIMPLIFY_MM, _axis_polygon

    grown = box(0, 0, 12, 3).buffer(0.3, join_style=1)      # round join, many vertices
    art = box(0, 0, 12, 3)
    assert _axis_polygon(grown, art, False) is grown
    assert _axis_polygon(grown, art, True) is grown          # True == "grown"
    assert _axis_polygon(grown, art, "grown") is grown
    assert _axis_polygon(grown, art, "artwork") is art
    assert _axis_polygon(grown, None, "artwork") is grown    # no artwork, no swap
    simplified = _axis_polygon(grown, art, "simplified")
    assert len(simplified.exterior.coords) < len(grown.exterior.coords)
    assert simplified.equals(grown.simplify(_AXIS_SIMPLIFY_MM))


def test_an_unknown_axis_mode_falls_back_to_the_grown_polygon():
    """A typo must not silently change which polygon is read."""
    from digitizer_core.stage6_satin import _axis_polygon

    grown, art = box(0, 0, 10, 2), box(0, 0, 10, 2).buffer(-0.1)
    assert _axis_polygon(grown, art, "artwrok") is grown
