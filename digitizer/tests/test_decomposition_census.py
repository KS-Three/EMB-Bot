"""Tests for tools/decomposition_census.py — the geometry, not the census.

The census swaps the skeleton source for one digitize at a time; what it
concludes is only worth anything if the polygon-native axis it swaps IN is a
real medial axis. These pin that on shapes whose axis is known exactly, plus
the fold metric the N-weld count rests on. No pipeline run.
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


def _pts(segs):
    return np.asarray([p for s in segs for p in s])


def test_a_bar_is_one_spine_with_no_corner_hooks():
    """The H defect's construction: a square-capped bar. Its medial axis is
    the centre line ending one half-width short of each cap, and nothing
    runs into a corner. Leaf-length pruning left a diagonal hook into one
    corner at each end here (y reached 1.93); the arc-residual test must not."""
    p = _pts(dc.polygon_axis_segments(box(0, 0, 10, 2), 0.05))
    assert np.allclose(p[:, 1], 1.0, atol=1e-6)
    assert p[:, 0].min() >= 1.0 - 1e-6 and p[:, 0].max() <= 9.0 + 1e-6
    assert p[:, 0].max() - p[:, 0].min() > 7.9


def test_a_crossing_keeps_all_four_arms():
    plus = unary_union([box(-5, -1, 5, 1), box(-1, -5, 1, 5)])
    p = _pts(dc.polygon_axis_segments(plus, 0.05))
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
    p = _pts(dc.polygon_axis_segments(ring, 0.05))
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


def test_draw_axis_lands_on_the_rasterizer_grid():
    """The axis is drawn with `_rasterize`'s own mapping, so the walker reads
    it where the raster skeleton would have been."""
    from digitizer_core import stage6_satin as s6

    bar = box(0, 0, 10, 2)
    mask, scale, ox, oy = s6._rasterize(bar)
    skel = dc.draw_axis(dc.polygon_axis_segments(bar, 0.5 / scale), mask, scale, ox, oy)
    ys, xs = np.nonzero(skel)
    assert len(xs) > 0
    mm_y = oy + (ys + 0.5) / scale
    assert np.abs(mm_y - 1.0).max() <= 1.0 / scale
    assert (mask[ys, xs] > 0).all()
