"""`tools/edge_truth_ladder.py` — stage 4's polygons against the vector truth.

Three contracts. The regenerated 800 rung IS the committed fixture (so the
ladder's other rungs are the same drawing at other sizes, not a new
fixture); the truth measures zero against itself (so any deviation the
ladder reports is the pipeline's); and on the pipeline the deviation is
sub-pixel at 800 px and falls with resolution, flag OFF — the baseline the
plan's acceptance criterion is stated against.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon, box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

import edge_truth_ladder as el  # noqa: E402

TESTDATA = HERE.parent / "testdata"


@pytest.mark.parametrize("fixture,committed", [("whitebg", "logo_whitebg.png"),
                                               ("ribbon", "ribbon_curve.png")])
def test_the_800_rung_is_the_committed_fixture_pixel_for_pixel(fixture, committed):
    regenerated = el.render(fixture, 800)
    on_disk = cv2.imread(str(TESTDATA / committed), cv2.IMREAD_COLOR)
    assert regenerated.shape == on_disk.shape
    assert np.array_equal(regenerated, on_disk), "the ladder draws something other than the fixture"


def test_rungs_must_be_whole_supersamples_of_the_frame():
    assert [el.scale_for(w) for w in el.RUNGS] == [1, 2, 4, 8, 16]
    assert el.scale_for(1000) == 5          # any whole multiple of 200 is a rung
    with pytest.raises(ValueError):
        el.scale_for(300)                   # 1.5x is not a whole supersample


def test_the_truth_measures_zero_against_itself():
    for fixture in el.FIXTURES:
        for name, t in el.truth(fixture, 4).items():
            geom = el._largest_polygon(t["geom"])
            d = el.deviation(geom, t["geom"], exclude=t["exclude"])
            assert d.size > 0, (fixture, name)
            assert np.abs(d).max() < 1e-9, (fixture, name, np.abs(d).max())


def test_deviation_sign_is_material_excess_on_the_shell_and_on_the_hole():
    truth = box(0, 0, 100, 100).difference(box(40, 40, 60, 60))     # a square with a square hole
    grown = box(-1, -1, 101, 101).difference(box(41, 41, 59, 59))    # more material everywhere
    shrunk = box(1, 1, 99, 99).difference(box(39, 39, 61, 61))       # less material everywhere
    # Every sample is one unit from the truth boundary except the few that
    # sit past a corner, where the nearest truth point is the corner itself.
    assert el.deviation(grown, truth).mean() == pytest.approx(1.0, abs=0.1)
    assert el.deviation(shrunk, truth).mean() == pytest.approx(-1.0, abs=0.1)
    assert (el.deviation(grown, truth) > 0.99).all()
    assert (el.deviation(shrunk, truth) < -0.99).all()


def test_a_polygon_is_mapped_back_from_plan_millimetres_to_pixel_edges():
    # Stage 4: mm = (px_index - centre) / px_per_mm. A vertex at pixel index
    # 10 with centre 100 at 8 px/mm is -11.25 mm; back again it must be the
    # pixel's CENTRE in edge coordinates, 10.5.
    sq = Polygon([(-11.25, -11.25), (-10.0, -11.25), (-10.0, -10.0), (-11.25, -10.0)])
    back = el.region_to_px(sq, 100.0, 100.0, 8.0)
    assert back.bounds == pytest.approx((10.5, 10.5, 20.5, 20.5))


def test_parse_flag_reads_values_and_refuses_unknown_fields():
    assert el.parse_flag("curve_turn_deg=15") == ("curve_turn_deg", 15)
    assert el.parse_flag("forced_class=flat") == ("forced_class", "flat")
    assert el.parse_flag("satin_per_stroke") == ("satin_per_stroke", True)
    with pytest.raises(ValueError):
        el.parse_flag("subpixel_edges")     # PR 2's flag does not exist yet


@pytest.fixture(scope="module")
def rungs(tmp_path_factory):
    work = tmp_path_factory.mktemp("ladder")
    return {w: el.measure_rung("whitebg", w, "flat", work) for w in (400, 1600)}


def test_every_truth_shape_is_produced_and_matched_from_400_px_up(rungs):
    """The 1 mm dot included: stage 3's run-tier rescue keeps it as a region
    from 400 px up (at the 200 px rung, under the resolution floor, it is
    not produced — the baseline in scope-history 09-08 has that row)."""
    for w, r in rungs.items():
        by = {row["shape"]: row for row in r["rows"]}
        for name in ("circle", "ring", "bar", "purple", "orange"):
            assert by[name]["produced"], (w, name)
            assert by[name]["iou"] > 0.9, (w, name, by[name]["iou"])
        assert by["dot"]["produced"] and by["dot"]["iou"] > 0.7, (w, by["dot"])


def test_the_trace_sits_inside_the_edge_by_under_a_pixel_and_the_curves_sharpen_with_resolution(rungs):
    """The pixel-centre trace of a filled shape sits half a pixel inside its
    edge, so the offset is negative and under one pixel. The spread has two
    floors: the pixel (the staircase) where the raster is coarse, and the
    0.2 mm Douglas-Peucker tolerance (the chord sag) where it is fine — at
    1600 px the ring's spread is 0.063 mm against a 0.060 mm pixel, so the
    bound is the larger of the pixel and half the tolerance. The circle and
    ring still sharpen from 400 to 1600 px."""
    tol = el.PipelineConfig().simplify_tol_mm
    for w, r in rungs.items():
        px_mm = 1.0 / r["px_per_mm"]
        for row in r["rows"]:
            if not row["produced"]:
                continue
            assert -1.0 * px_mm < row["offset_mm"] < 0.25 * px_mm, (w, row["shape"], row["offset_mm"], px_mm)
            assert row["spread_mm"] < max(px_mm, tol / 2), (w, row["shape"], row["spread_mm"], px_mm, tol)
    lo = {row["shape"]: row for row in rungs[400]["rows"]}
    hi = {row["shape"]: row for row in rungs[1600]["rows"]}
    for name in ("circle", "ring"):
        assert hi[name]["spread_mm"] < lo[name]["spread_mm"], (name, lo[name]["spread_mm"], hi[name]["spread_mm"])


def test_the_ribbon_polygon_is_the_same_polygon_at_400_and_1600_px(tmp_path):
    """Douglas-Peucker at a fixed 0.2 mm makes the same polygon whatever the
    raster under it: the ribbon keeps its vertex count and its spread from
    400 px to 1600 px, flag OFF (37 vertices and 0.06 mm on 2026-09-08).
    That floor is the simplification's, not the pixel's — the reading the
    plan's acceptance criterion had to be corrected by."""
    lo = el.measure_rung("ribbon", 400, "flat", tmp_path)["rows"][0]
    hi = el.measure_rung("ribbon", 1600, "flat", tmp_path)["rows"][0]
    assert lo["produced"] and hi["produced"]
    assert abs(lo["vertices"] - hi["vertices"]) <= 3, (lo["vertices"], hi["vertices"])
    assert abs(lo["spread_mm"] - hi["spread_mm"]) < 0.02, (lo["spread_mm"], hi["spread_mm"])
    assert lo["spread_mm"] > 0.03, "a sub-pixel change that moved this below the DP floor would be news"
