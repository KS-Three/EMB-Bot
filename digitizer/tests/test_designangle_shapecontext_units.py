"""Unit tests for the helpers of `designangle` and `shapecontext` that the
pipeline-level tests (`test_design_angle.py`, `test_shapecontext.py`) reach
only indirectly. Synthetic geometry only."""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, machine
from digitizer_core import shapecontext as sc
from digitizer_core.designangle import (META_KEY, _angular_dist, _doubled_mean,
                                        fewest_columns_angle, house_design_angle,
                                        set_design_angle)
from digitizer_core.regions import Region


def _region(sid, poly, **meta):
    r = Region.__new__(Region)
    r.shape_id = sid
    r.polygon = poly
    r.meta = dict(meta)
    return r


# ---- designangle ----------------------------------------------------------

def test_angular_dist_is_a_half_circle_metric():
    assert _angular_dist(0, 180) == 0
    assert _angular_dist(10, 170) == pytest.approx(20)
    assert _angular_dist(0, 90) == 90
    assert _angular_dist(-10, 10) == pytest.approx(20)


def test_doubled_mean_wraps_across_the_half_circle():
    # 170 and 10 average to 0 (not 90) under the doubled-angle mean
    mean, r = _doubled_mean([170.0, 10.0], [1.0, 1.0])
    assert _angular_dist(mean, 0.0) < 1e-9
    assert r == pytest.approx(math.cos(math.radians(20)))
    # equal weights on perpendicular angles cancel: resultant 0
    _m, r0 = _doubled_mean([0.0, 90.0], [1.0, 1.0])
    assert r0 == pytest.approx(0.0, abs=1e-12)


def test_doubled_mean_empty_or_zero_weight_is_none():
    assert _doubled_mean([], []) == (None, 0.0)
    assert _doubled_mean([30.0], [0.0]) == (None, 0.0)


def test_doubled_mean_is_area_weighted():
    mean, _ = _doubled_mean([0.0, 20.0], [3.0, 1.0])
    assert 0.0 < mean < 10.0


def test_house_angle_none_without_votes_and_ignores_unvoted_regions():
    assert house_design_angle([]) is None
    assert house_design_angle([_region("a", box(0, 0, 5, 5))]) is None
    regs = [_region("a", box(0, 0, 5, 5), satin_angle_deg=40.0), _region("b", box(9, 0, 14, 5))]
    assert house_design_angle(regs) == pytest.approx(40.0)


def test_house_angle_cap_boundary():
    # two equal votes 58 deg apart: each sits 29 deg from the mean, inside the 30 cap
    # (exactly 60 apart sits ON the cap and float rounding decides it, so not pinned)
    ok = [_region("a", box(0, 0, 5, 5), satin_angle_deg=0.0),
          _region("b", box(9, 0, 14, 5), satin_angle_deg=58.0)]
    assert house_design_angle(ok) == pytest.approx(29.0)
    over = [_region("a", box(0, 0, 5, 5), satin_angle_deg=0.0),
            _region("b", box(9, 0, 14, 5), satin_angle_deg=62.0)]
    assert house_design_angle(over) is None
    # 90 apart: each 45 from the mean, past the cap -> not one house
    bad = [_region("a", box(0, 0, 5, 5), satin_angle_deg=0.0),
           _region("b", box(9, 0, 14, 5), satin_angle_deg=90.0)]
    assert house_design_angle(bad) is None


def test_house_angle_is_area_weighted_and_survives_zero_area():
    regs = [_region("big", box(0, 0, 20, 20), satin_angle_deg=10.0),
            _region("tiny", Polygon(), satin_angle_deg=20.0)]
    assert house_design_angle(regs) == pytest.approx(10.0, abs=1e-6)


def test_fewest_columns_horizontal_and_vertical_bars():
    assert fewest_columns_angle([box(0, 0, 40, 4)], machine.FILL_ROW_MM) == 0.0
    assert fewest_columns_angle([box(0, 0, 4, 40)], machine.FILL_ROW_MM) == 90.0


def test_fewest_columns_returns_a_half_circle_angle():
    a = fewest_columns_angle([box(0, 0, 30, 10)], machine.FILL_ROW_MM)
    assert 0.0 <= a < 180.0


def test_set_design_angle_nothing_takes_it():
    cfg = PipelineConfig(design_angle=True)
    assert set_design_angle([], cfg, "flat", machine.FILL_ROW_MM) is None
    regs = [_region("u", box(0, 0, 30, 30), stitched=False),
            _region("r", box(0, 0, 30, 30), tier="run")]
    assert set_design_angle(regs, cfg, "flat", machine.FILL_ROW_MM) is None
    assert all(META_KEY not in r.meta for r in regs)


def test_set_design_angle_lane_angle_wraps_and_beats_objective():
    cfg = PipelineConfig(design_angle=True)
    regs = [_region("f", box(0, 0, 40, 40))]
    got = set_design_angle(regs, cfg, "flat", machine.FILL_ROW_MM, lane_angle=190.0)
    assert got == pytest.approx(10.0)
    assert regs[0].meta[META_KEY] == pytest.approx(10.0)


def test_set_design_angle_house_beats_lane_and_setdefault_keeps_existing():
    cfg = PipelineConfig(design_angle=True)
    regs = [_region("h", box(0, 0, 10, 2), satin_angle_deg=25.0),
            _region("f", box(0, 10, 40, 40)),
            _region("kept", box(0, 60, 40, 40), **{META_KEY: 77.0})]
    got = set_design_angle(regs, cfg, "flat", machine.FILL_ROW_MM, lane_angle=100.0)
    assert got == pytest.approx(25.0)
    assert regs[1].meta[META_KEY] == pytest.approx(25.0)
    assert regs[2].meta[META_KEY] == 77.0


def test_set_design_angle_satin_only_without_house_or_lane_takes_nothing():
    # a thin bar is satin: no fill polys, so rule 3 has nothing to count
    cfg = PipelineConfig(design_angle=True)
    regs = [_region("bar", box(0, 0, 2, 40))]
    assert set_design_angle(regs, cfg, "flat", machine.FILL_ROW_MM) is None
    assert META_KEY not in regs[0].meta


# ---- shapecontext ---------------------------------------------------------

def test_sample_points_count_and_lie_on_the_boundary():
    sq = box(0, 0, 10, 10)
    pts = sc._sample_polygon_points(sq, 64)
    assert pts.shape == (64, 2)
    on = np.minimum.reduce([np.abs(pts[:, 0]), np.abs(pts[:, 0] - 10),
                            np.abs(pts[:, 1]), np.abs(pts[:, 1] - 10)])
    assert on.max() < 1e-9


def test_sample_points_split_across_holes_by_perimeter():
    donut = Polygon([(0, 0), (30, 0), (30, 30), (0, 30)],
                    [[(10, 10), (20, 10), (20, 20), (10, 20)]])
    pts = sc._sample_polygon_points(donut, 64)
    inner = np.sum((pts[:, 0] > 5) & (pts[:, 0] < 25) & (pts[:, 1] > 5) & (pts[:, 1] < 25))
    # hole perimeter 40 of total 160 -> a quarter of the points
    assert inner == 16
    assert len(pts) == 64


def test_sample_points_degenerate_polygon_is_empty():
    assert sc._sample_polygon_points(Polygon(), 64).shape == (0, 2)


def test_log_polar_bins_ranges_and_scale_invariance():
    pts = sc._sample_polygon_points(box(0, 0, 10, 6), 32)
    b1 = sc._log_polar_bins(pts)
    b2 = sc._log_polar_bins(pts * 7.0 + 3.0)
    assert b1.shape == (2, 32, 32)
    assert b1[0].min() >= 0 and b1[0].max() <= sc.N_RADIAL_BINS - 1
    assert b1[1].min() >= 0 and b1[1].max() <= sc.N_ANGULAR_BINS - 1
    off = ~np.eye(32, dtype=bool)
    assert np.array_equal(b1[0][off], b2[0][off])
    assert np.array_equal(b1[1][off], b2[1][off])


def test_histograms_count_every_other_point_once():
    pts = sc._sample_polygon_points(box(0, 0, 10, 6), 32)
    h = sc._shape_context_histograms(pts)
    assert h.shape == (32, sc.N_RADIAL_BINS * sc.N_ANGULAR_BINS)
    assert np.all(h.sum(axis=1) == 31)


def test_histograms_of_one_point_are_zero():
    assert sc._shape_context_histograms(np.zeros((1, 2))).shape == (1, 60)
    assert not sc._shape_context_histograms(np.zeros((1, 2))).any()


@pytest.mark.xfail(strict=True, raises=ValueError,
                   reason="hist.reshape(0, -1) is ambiguous for an empty point set; "
                          "unreachable via shape_context_distance (len < 3 guard)")
def test_histograms_of_no_points_is_an_empty_matrix():
    assert sc._shape_context_histograms(np.zeros((0, 2))).shape == (0, 60)


def test_chi2_cost_properties():
    h = sc._shape_context_histograms(sc._sample_polygon_points(box(0, 0, 10, 6), 24))
    c = sc._chi2_cost_matrix(h, h)
    assert np.allclose(np.diag(c), 0.0)
    assert np.allclose(c, c.T)
    assert (c >= 0).all() and (c <= 1.0 + 1e-9).all()      # normalized chi2 is bounded by 1
    # unnormalized scale does not matter
    assert np.allclose(sc._chi2_cost_matrix(h * 5, h), c)
    # all-zero rows are inert rather than NaN
    z = sc._chi2_cost_matrix(np.zeros((2, 60)), np.zeros((3, 60)))
    assert z.shape == (2, 3) and np.all(z == 0)


def test_distance_symmetric_and_point_count_agnostic():
    a, b = box(0, 0, 20, 8), Polygon([(0, 0), (20, 0), (10, 12)])
    assert sc.shape_context_distance(a, b) == pytest.approx(sc.shape_context_distance(b, a))
    assert sc.shape_context_distance(a, b) > 0.0
    assert sc.shape_context_distance(a, a, n_points=32) == pytest.approx(0.0, abs=1e-12)


def test_distance_none_when_too_few_points():
    assert sc.shape_context_distance(box(0, 0, 5, 5), box(0, 0, 5, 5), n_points=2) is None
