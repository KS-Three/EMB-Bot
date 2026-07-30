"""Stages 5 and 7 — sew order, underlap, ties, trims — and DST export.

These are the properties that decide whether the file behaves on a machine,
so each test names the defect it exists to catch.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import (
    FABRICS,
    PipelineConfig,
    export_dst,
    fabric_for_garment,
    get_fabric,
    machine,
    plan_stitches,
)
from digitizer_core.export import read_dst_points
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.warnings_codes import HOLE_NEARLY_CLOSED

from .conftest import PLAN_CFG_KW, cfg, segments


# --- Fabric table ---------------------------------------------------------

def test_fabric_table_matches_the_browser_engine():
    """Both products must make the same physical choices; src/fabrics.js is the
    other copy. Values pinned so a one-sided edit is visible."""
    assert len(FABRICS) == 7
    cap = get_fabric("structured_cap")
    assert (cap.pull_comp_mm, cap.fill_underlay, cap.trim_at_mm) == (0.4, "edge_zigzag", 3.0)
    towel = get_fabric("terry_towel")
    assert (towel.pull_comp_mm, towel.density_adjust, towel.trim_at_mm) == (0.6, 1.1, 4.0)
    assert fabric_for_garment("hat_front").id == "structured_cap"
    assert get_fabric("no_such_fabric").id == "pique_knit", "an unknown id must not raise"


# --- Stage 5 --------------------------------------------------------------

def _region(poly: Polygon, layer: int, number: str) -> Region:
    return Region(shape_id=f"S{layer}", polygon=poly, thread_index=0,
                  thread_number=number, area_mm2=poly.area, meta={"layer": layer})


def test_the_color_that_sews_first_extends_under_the_one_that_follows():
    """The seam defect this prevents: two colors pull apart on fabric and show
    a line of garment between them. Growing BOTH would just move the seam, so
    the direction of the growth is the whole point."""
    left = _region(Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]), 0, "1000")
    right = _region(Polygon([(10, 0), (20, 0), (20, 10), (10, 10)]), 1, "2000")
    planned, _ = resolve_overlaps([left, right], get_fabric("canvas_tote"),
                                  PipelineConfig(overlap_mm=0.25))
    first = next(p for p in planned if p.sew_index == 0)
    second = next(p for p in planned if p.sew_index == 1)

    assert first.polygon.bounds[2] > 10.0, "the first color must reach under the second"
    # Area, not bounds: the second color's free edges are compensated too, so
    # its buffer bulges past x=10 above and below the shared edge. What must
    # not happen is it covering any of the first color's actual area.
    assert second.polygon.intersection(left.polygon).area < 1e-9, \
        "the second color must not grow back over the first"
    assert first.sew_index < second.sew_index


def test_pull_compensation_grows_the_free_edges():
    solo = _region(Polygon([(0, 0), (10, 0), (10, 10), (0, 10)]), 0, "1000")
    planned, _ = resolve_overlaps([solo], get_fabric("terry_towel"), PipelineConfig())
    x0, y0, x1, y1 = planned[0].polygon.bounds
    assert x0 == pytest.approx(-0.6, abs=0.05)
    assert x1 == pytest.approx(10.6, abs=0.05)


def test_a_counter_that_would_close_under_pull_compensation_is_held_open():
    """Losing a letter's counter to compensation is lost artwork, and silently
    losing artwork is what makes an auto-digitizer untrustworthy."""
    outer = Point(0, 0).buffer(10.0)
    # Big enough to be real artwork (area 4.5 mm2 against the 2.25 mm2 floor),
    # small enough that terry towel's 0.6 mm compensation would close it.
    tight = Point(0, 0).buffer(1.2)
    region = _region(Polygon(outer.exterior.coords, [tight.exterior.coords]), 0, "1000")
    planned, warnings = resolve_overlaps([region], get_fabric("terry_towel"), PipelineConfig())
    assert len(planned[0].polygon.interiors) == 1, "the counter must survive"
    assert HOLE_NEARLY_CLOSED in {w["code"] for w in warnings}


# --- Stage 7 --------------------------------------------------------------

def test_every_color_starts_and_ends_with_a_lock_stitch(plan):
    stitch_plan, _, _ = plan
    for block in stitch_plan.blocks:
        first, last = block.runs[0], block.runs[-1]
        head = min(math.dist(first.points[0], p) for p in first.points[1:4])
        tail = min(math.dist(last.points[-1], p) for p in last.points[-4:-1])
        assert head <= machine.TIE_STITCH_MM + 1e-6
        assert tail <= machine.TIE_STITCH_MM + 1e-6


def test_a_lock_stitch_is_applied_once_not_twice():
    """The first run of a color is both "the start" and "after a trim". Asking
    those questions separately tied it twice and piled eight stitches of thread
    into one spot."""
    from digitizer_core.stage7_sequence import _apply_ties
    from digitizer_core.stitches import StitchRun

    run = StitchRun(points=[(0.0, 0.0), (10.0, 0.0)], kind="fill", trim=True)
    _apply_ties([run])
    # One lock adds 4 points at each end of a 2-point run. Two locks at the
    # head, which is what the earlier version produced, gives 14.
    assert len(run.points) == 10, run.points
    assert sum(1 for p in run.points if p == (0.0, 0.0)) == 3


def test_lock_stitches_stay_inside_the_shape(plan):
    """Regression from the first smoke run: ties laid symmetrically about the
    endpoint put a whisker of thread 0.8 mm outside the artwork."""
    stitch_plan, planned, _ = plan
    covered = planned[0].polygon
    for p in planned[1:]:
        covered = covered.union(p.polygon)
    covered = covered.buffer(0.05)
    outside = [pt for _, run in stitch_plan.iter_runs() for pt in run.points
               if not covered.covers(Point(pt))]
    assert outside == [], f"{len(outside)} stitches land outside the sewing geometry"


def test_the_thread_is_cut_between_colors(plan):
    stitch_plan, _, _ = plan
    assert len(stitch_plan.blocks) > 1
    for block in stitch_plan.blocks:
        assert block.runs[0].trim, "a color change must cut the previous thread"


def test_no_needle_up_move_is_left_as_a_long_float(plan):
    stitch_plan, _, _ = plan
    trim_at = fabric_for_garment(PLAN_CFG_KW["garment_id"]).trim_at_mm
    prev = None
    for _, run in stitch_plan.iter_runs():
        if run.jump and prev is not None and not run.trim:
            assert math.dist(prev, run.points[0]) <= trim_at + 1e-6
        prev = run.points[-1]


def test_underlay_is_sewn_before_the_fill_it_supports(plan):
    stitch_plan, _, _ = plan
    for block in stitch_plan.blocks:
        by_shape: dict[str, list[str]] = {}
        for run in block.runs:
            by_shape.setdefault(run.shape_id, []).append(run.kind)
        for shape_id, kinds in by_shape.items():
            if "underlay" in kinds and "fill" in kinds:
                assert kinds.index("underlay") < kinds.index("fill"), shape_id


def test_a_shape_is_entered_at_its_nearest_point_not_at_its_own_top_left_corner():
    """Regression: a shape's stitches were generated before its turn came, so
    every fill began at the column that started highest and leftmost, whatever
    the last stitch of the shape before it happened to be.

    On a row of tall shapes the needle finished each one at the bottom and was
    sent straight back to the top of the next: 41.1 mm flown per gap, 287.6 mm
    over a row of eight, all of it thread showing across the design. The
    shapes here sit 3 mm apart and the underlay walks 1 mm inside the edge, so
    about 4 mm is the whole hop there is to make.
    """
    fabric = get_fabric("canvas_tote")
    conf = PipelineConfig()
    regions = [
        Region(shape_id=f"S{i}",
               polygon=Polygon([(x, 0), (x + 8, 0), (x + 8, 40), (x, 40)]),
               thread_index=0, thread_number="1000", area_mm2=320.0,
               meta={"layer": 0})
        for i, x in enumerate(range(0, 88, 11))
    ]
    planned, _ = resolve_overlaps(regions, fabric, conf)
    blocks, _ = sequence(planned, fabric, conf)

    hops = []
    prev = None
    for block in blocks:
        for run in block.runs:
            if run.jump and prev is not None:
                hops.append(math.dist(prev, run.points[0]))
            prev = run.points[-1]

    assert len(hops) == 7, "one hop between each pair of the eight shapes"
    assert max(hops) < 5.0, \
        f"the needle is being sent back across a shape: {[round(h, 1) for h in hops]}"
    assert sum(hops) < 40.0, f"{sum(hops):.0f} mm of needle-up travel"


# --- Export ---------------------------------------------------------------

def test_the_dst_holds_exactly_the_stitches_the_plan_promised(plan):
    """The count shown to the operator has to be the count the machine sews."""
    stitch_plan, _, _ = plan
    points = read_dst_points(export_dst(stitch_plan))
    assert len(points) == stitch_plan.stats.stitch_count


def test_the_dst_comes_back_the_same_size_and_the_right_way_up(plan):
    stitch_plan, _, _ = plan
    points = read_dst_points(export_dst(stitch_plan))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    w, h = stitch_plan.stats.size_mm
    assert max(xs) - min(xs) == pytest.approx(w, abs=0.1)
    assert max(ys) - min(ys) == pytest.approx(h, abs=0.1)

    # y-DOWN survives the round trip: the topmost stitch in the plan must still
    # be the topmost one after decoding. A silent flip here would mirror every
    # design, and mirrored lettering is not subtle.
    plan_top = min(p[1] for _, run in stitch_plan.iter_runs() for p in run.points)
    plan_bottom = max(p[1] for _, run in stitch_plan.iter_runs() for p in run.points)
    assert abs(min(ys) - plan_top) < 0.1
    assert abs(max(ys) - plan_bottom) < 0.1


def test_the_design_comes_out_the_size_that_was_asked_for(whitebg):
    stitch_plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    width = stitch_plan.stats.size_mm[0]
    pull = fabric_for_garment(PLAN_CFG_KW["garment_id"]).pull_comp_mm
    # Stitching is deliberately wider than the artwork by the compensation.
    assert width == pytest.approx(80.0 + 2 * pull, abs=0.5)


def test_planning_the_same_regions_twice_gives_the_same_file(whitebg):
    a = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    b = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    assert a == b


def test_every_stitch_fits_in_a_dst_record(plan):
    stitch_plan, _, _ = plan
    longest = max(math.dist(a, b) for _, _, a, b in segments(stitch_plan))
    assert longest <= machine.MAX_STITCH_MM
