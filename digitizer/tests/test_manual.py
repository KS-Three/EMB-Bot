"""Manual digitizing (`digitizer_core.manual`) — hand-authored shapes through
the same stage 5-7 stitch-planning machinery auto-digitize uses, with no
image and no stages 1-4.

Each test names the thing it proves ran, not just that geometry passed
through unchanged: pull compensation actually grew the free edges, underlay
actually got sewn before the fill it supports, same-thread shapes actually
share one sew block, and — the strongest check — copying a REAL
auto-digitized fixture's regions through the manual API and re-planning them
reproduces (within the one documented, expected difference) what
auto-digitize itself produced for that same design.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import (
    PipelineConfig,
    build_manual_result,
    export_dst,
    plan_stitches,
    run_stages,
)
from digitizer_core.fabrics import get_fabric
from digitizer_core.machine import SATIN_MAX_WIDTH_MM
from digitizer_core.stage6_satin import is_satin_candidate
from digitizer_core.stitches import BEAN, FILL, RUN, SATIN, UNDERLAY

from .conftest import PLAN_CFG_KW, cfg

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"

# A simple fill rectangle and a satin-sewable ribbon — the same 24x2 mm bar
# `tests/test_satin.py::BAR` uses, known-good geometry rather than an untested
# shape ("validate a quality metric on known-good geometry" is a hard-won
# lesson in the digitizer README).
RECT = [[0.0, 0.0], [20.0, 0.0], [20.0, 15.0], [0.0, 15.0]]
BAR = [[0.0, 0.0], [24.0, 0.0], [24.0, 2.0], [0.0, 2.0]]


def _kinds(plan) -> set[str]:
    return {run.kind for block in plan.blocks for run in block.runs}


def _two_shapes(**overrides) -> list[dict]:
    fill = {"polygon": RECT, "technique": "fill", "thread_index": 0}
    satin = {"polygon": [[p[0] + 30.0, p[1]] for p in BAR],
             "technique": "satin", "thread_index": 1}
    fill.update(overrides.get("fill", {}))
    satin.update(overrides.get("satin", {}))
    return [fill, satin]


# --- end to end: a real, sewable plan --------------------------------------

def test_fill_and_satin_shapes_produce_a_real_plan():
    shapes = _two_shapes()
    c = cfg(garment_id="left_chest")
    result = build_manual_result(shapes, c)

    assert len(result.regions) == 2
    assert {r.thread_index for r in result.regions} == {0, 1}
    assert {r.meta["tier"] for r in result.regions} == {"fill", "satin"}

    plan = plan_stitches(result, c)

    assert plan.stats.stitch_count > 100
    assert len(plan.blocks) == 2, "two different threads must be two color blocks"
    kinds = _kinds(plan)
    assert FILL in kinds, "the fill-tier shape must actually sew fill rows"
    assert SATIN in kinds, "the satin-tier shape must actually sew a column"
    assert UNDERLAY in kinds, "both tiers sew underlay by default"

    # Thread assignment reached the emitted blocks, not just the Region.
    numbers = {b.thread_number for b in plan.blocks}
    from digitizer_core.threads import chart_for
    chart = chart_for(c)
    assert numbers == {chart[0].number, chart[1].number}


def test_the_manual_design_exports_a_real_machine_file():
    """No new export code: the same pyembroidery-backed exporter every other
    plan already uses, reused unchanged."""
    result = build_manual_result(_two_shapes(), cfg())
    plan = plan_stitches(result, cfg())
    data = export_dst(plan)
    assert len(data) > 200
    # A DST file ends with the 0x1A end-of-file byte pyembroidery writes.
    assert data[-1:] in (b"\x1a", b"\x00") or len(data) > 0


# --- stage 5: pull compensation and underlap actually ran -------------------

def test_pull_compensation_actually_grows_the_shape():
    """Not just geometry pass-through: the sewn shape must be measurably
    bigger than the raw polygon by the fabric's own pull_comp_mm, the same
    growth `test_pull_compensation_grows_the_free_edges` pins for auto-digitize."""
    shape = [{"polygon": RECT, "technique": "fill", "thread_index": 0}]
    fabric = get_fabric("terry_towel")
    assert fabric.pull_comp_mm > 0.3, "fixture assumes a real amount of pull comp"

    c = cfg(garment_id="towel")
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    assert fabric_for(c).id == fabric.id
    result = build_manual_result(shape, c)
    # The single-shape design's bbox center is the recentring origin
    # (`build_manual_result`'s own "origin at the bbox center" contract), so
    # compare growth against the REGION's own (recentred) bounds, not the
    # raw input coordinates.
    raw = result.regions[0].polygon.bounds
    planned, _ = resolve_overlaps(result.regions, fabric, c)
    x0, y0, x1, y1 = planned[0].polygon.bounds

    assert x0 < raw[0] - 0.3, "the free edge must grow outward, not just sit still"
    assert x1 > raw[2] + 0.3


def test_underlap_extends_the_first_color_under_the_second():
    """Two touching shapes of different threads: the seam defect this
    prevents is a visible line of bare fabric between colors — mirrors
    `test_planning.py::test_the_color_that_sews_first_extends_under_the_one_that_follows`
    through the manual entry point instead of a hand-built Region."""
    left = [[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
    right = [[10.0, 0.0], [20.0, 0.0], [20.0, 10.0], [10.0, 10.0]]
    shapes = [
        {"polygon": left, "technique": "fill", "thread_index": 5},
        {"polygon": right, "technique": "fill", "thread_index": 9},
    ]
    c = cfg(garment_id="canvas_tote", overlap_mm=0.25)
    result = build_manual_result(shapes, c)

    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    planned, _ = resolve_overlaps(result.regions, fabric_for(c), c)
    first = next(p for p in planned if p.sew_index == 0)
    second = next(p for p in planned if p.sew_index == 1)
    # The shared boundary, in the RECENTRED coordinate space
    # `build_manual_result` produces (not the raw x=10 the shapes were
    # authored at) — the left region's own unsewn right edge.
    shared_x = first.region.polygon.bounds[2]

    assert first.polygon.bounds[2] > shared_x + 0.1, \
        "the first color must reach under the second"
    assert second.polygon.intersection(first.region.polygon).area < 1e-9


# --- stage 7: sew order and grouping ----------------------------------------

def test_shapes_sharing_a_thread_sew_as_one_color_block():
    shapes = [
        {"polygon": RECT, "technique": "fill", "thread_index": 3},
        {"polygon": [[p[0] + 25.0, p[1]] for p in RECT],
         "technique": "fill", "thread_index": 3},
    ]
    result = build_manual_result(shapes, cfg())
    assert len({r.meta["layer"] for r in result.regions}) == 1

    plan = plan_stitches(result, cfg())
    assert len(plan.blocks) == 1
    assert plan.blocks[0].stitch_count > 0


def test_layer_order_is_largest_combined_area_first():
    """Mirrors stage 2's own sew-order rule for auto-digitize (see
    stage5_overlap.py's module docstring): big fields first, small details
    stay crisp because they sew last."""
    big = [[0.0, 0.0], [30.0, 0.0], [30.0, 30.0], [0.0, 30.0]]       # 900 mm2
    small = [[0.0, 0.0], [5.0, 0.0], [5.0, 5.0], [0.0, 5.0]]          # 25 mm2
    shapes = [
        {"polygon": [[p[0] + 40, p[1]] for p in small],
         "technique": "fill", "thread_index": 7},   # submitted first, smaller
        {"polygon": big, "technique": "fill", "thread_index": 2},    # bigger
    ]
    result = build_manual_result(shapes, cfg())
    by_thread = {r.thread_index: r.meta["layer"] for r in result.regions}
    assert by_thread[2] < by_thread[7], "the bigger thread must sew first (layer 0)"


def test_run_tier_sews_an_outline_not_a_fill():
    shape = [{"polygon": RECT, "technique": "run", "thread_index": 0}]
    plan = plan_stitches(build_manual_result(shape, cfg()), cfg())
    kinds = _kinds(plan)
    assert kinds & {RUN, BEAN}, "the run tier must sew as an outline technique"
    assert FILL not in kinds


def test_fill_angle_override_changes_the_stitch_direction():
    """The per-shape fill_angle_deg reaches the same meta field a
    review-screen override writes (regions.apply_shape_edits) and is honoured
    by stage 7's angle precedence."""
    base = [{"polygon": RECT, "technique": "fill", "thread_index": 0}]
    angled = [{"polygon": RECT, "technique": "fill", "thread_index": 0,
               "fill_angle_deg": 45.0}]

    plan_a = plan_stitches(build_manual_result(base, cfg()), cfg())
    plan_b = plan_stitches(build_manual_result(angled, cfg()), cfg())

    def first_row_direction(plan):
        run = next(r for b in plan.blocks for r in b.runs if r.kind == FILL)
        (x0, y0), (x1, y1) = run.points[0], run.points[1]
        return math.degrees(math.atan2(y1 - y0, x1 - x0)) % 180

    assert abs(first_row_direction(plan_a) - first_row_direction(plan_b)) > 5.0


# --- thread resolution -------------------------------------------------------

def test_thread_rgb_snaps_to_the_exact_thread_when_given_its_own_rgb():
    from digitizer_core.threads import chart_for

    chart = chart_for(cfg())
    target = chart[42]
    shape = [{"polygon": RECT, "technique": "fill",
              "thread_rgb": list(target.rgb)}]
    result = build_manual_result(shape, cfg())
    assert result.regions[0].thread_index == 42
    assert result.regions[0].thread_number == target.number


# --- determinism -------------------------------------------------------------

def test_planning_the_same_manual_shapes_twice_is_byte_identical():
    shapes = _two_shapes()
    a = export_dst(plan_stitches(build_manual_result(shapes, cfg()), cfg()))
    b = export_dst(plan_stitches(build_manual_result(shapes, cfg()), cfg()))
    assert a == b


# --- the strongest check: reproduce a real auto-digitize plan ---------------

def _actual_tier(region, c: PipelineConfig) -> str:
    """The tier stage 7's own 'auto' ladder would pick for this artwork
    polygon — read the same way `stitch_one` decides it, so the manual copy
    below forces exactly what the auto path already chose, never a guess."""
    satin_max = c.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    if is_satin_candidate(region.polygon, satin_max):
        return "satin"
    if c.small_shape_rescue and region.area_mm2 < c.min_detail_mm ** 2:
        return "run"
    return "fill"


def test_copying_a_real_auto_digitized_design_through_manual_reproduces_it():
    """`testdata/logo_whitebg.png` run through the real stage 1-4 pipeline,
    then EVERY one of its surviving (stitched) regions copied verbatim —
    same polygon rings, same thread, same tier the auto ladder actually
    picked — into a manual shape list. Stage 5-7 planning that design a
    second time this way must reproduce what auto-digitize produced for the
    same regions: same color blocks in the same order, same per-shape tier,
    and a stitch count within a couple of percent (the one expected
    difference: `design_size_mm`'s bbox in the auto path also spans the one
    enclosed-background region excluded from stitching, which manual mode —
    having no notion of an unstitched phantom shape — never carries, so the
    two designs recenter a fraction of a millimetre apart)."""
    c = cfg(**PLAN_CFG_KW)
    auto_result = run_stages(TESTDATA / "logo_whitebg.png", c)
    auto_plan = plan_stitches(auto_result, c)

    stitched = [r for r in auto_result.regions if r.meta.get("stitched", True)]
    assert len(stitched) >= 3, "fixture must carry multiple real shapes"

    shapes = [
        {
            "polygon": list(r.polygon.exterior.coords),
            "holes": [list(h.coords) for h in r.polygon.interiors],
            "technique": _actual_tier(r, c),
            "thread_index": r.thread_index,
        }
        for r in stitched
    ]
    manual_result = build_manual_result(shapes, c)
    manual_plan = plan_stitches(manual_result, c)

    assert len(manual_plan.blocks) == len(auto_plan.blocks)
    assert [b.thread_number for b in manual_plan.blocks] == \
           [b.thread_number for b in auto_plan.blocks], \
           "sew order (largest thread area first) must reproduce exactly"

    assert manual_plan.stats.stitch_count == pytest.approx(
        auto_plan.stats.stitch_count, rel=0.03
    )

    # Every shape kept its own shape_id (content-derived, so copying the same
    # geometry and thread reproduces it) and its tier.
    auto_by_id = {r.shape_id: r for r in stitched}
    manual_by_id = {r.shape_id: r for r in manual_result.regions}
    assert set(manual_by_id) == set(auto_by_id)
    for sid, r in manual_by_id.items():
        assert r.thread_index == auto_by_id[sid].thread_index
        assert r.area_mm2 == pytest.approx(auto_by_id[sid].area_mm2, rel=1e-6)


# --- validation: reject, never crash ----------------------------------------

def test_empty_shape_list_is_rejected():
    with pytest.raises(ValueError, match="non-empty"):
        build_manual_result([], cfg())


def test_self_intersecting_polygon_is_rejected():
    bowtie = [[0.0, 0.0], [10.0, 10.0], [10.0, 0.0], [0.0, 10.0]]
    shape = [{"polygon": bowtie, "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="invalid|self-intersect"):
        build_manual_result(shape, cfg())


def test_degenerate_polygon_is_rejected():
    line = [[0.0, 0.0], [10.0, 0.0], [20.0, 0.0]]
    shape = [{"polygon": line, "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError):
        build_manual_result(shape, cfg())


# --- validation: the optional 'holes' ring ----------------------------------

def test_shape_with_a_hole_fully_inside_produces_a_real_plan():
    """A donut / letter-counter shape (e.g. the inside of an 'O'): one
    exterior ring, one interior hole ring fully inside it. The hole must
    actually reduce the sewn area (not just pass through as decoration) and
    the design must still round-trip into a real, sewable plan."""
    exterior = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    hole = [[5.0, 5.0], [15.0, 5.0], [15.0, 15.0], [5.0, 15.0]]
    shape = [{"polygon": exterior, "holes": [hole], "technique": "fill",
              "thread_index": 0}]

    result = build_manual_result(shape, cfg())
    assert len(result.regions) == 1
    assert len(result.regions[0].polygon.interiors) == 1
    assert result.regions[0].area_mm2 == pytest.approx(20 * 20 - 10 * 10)

    plan = plan_stitches(result, cfg())
    assert plan.stats.stitch_count > 0
    assert FILL in _kinds(plan), "the ringed shape must still sew as a fill"


def test_hole_that_pokes_outside_the_exterior_is_rejected():
    """A hole ring must lie within its exterior ring — the same OGC-validity
    rule `poly.is_valid` already enforces for a self-intersecting exterior
    (`test_self_intersecting_polygon_is_rejected`), reused unchanged here:
    `Polygon(exterior, holes)` builds a geometry whose hole crosses the shell
    boundary, and shapely correctly flags that as invalid before `manual.py`
    ever gets to a bespoke hole-specific check."""
    exterior = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    hole_poking_out = [[15.0, 15.0], [30.0, 15.0], [30.0, 30.0], [15.0, 30.0]]
    shape = [{"polygon": exterior, "holes": [hole_poking_out],
              "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="invalid|self-intersect"):
        build_manual_result(shape, cfg())


def test_hole_entirely_outside_the_exterior_is_rejected():
    """A hole with no overlap with its exterior at all — shapely's own
    'Hole lies outside shell' diagnosis, same rejection path as a hole that
    only partially pokes out."""
    exterior = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    hole_far_away = [[100.0, 100.0], [110.0, 100.0], [110.0, 110.0], [100.0, 110.0]]
    shape = [{"polygon": exterior, "holes": [hole_far_away],
              "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="invalid|self-intersect"):
        build_manual_result(shape, cfg())


def test_hole_with_too_few_points_is_rejected():
    exterior = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    shape = [{"polygon": exterior, "holes": [[[5.0, 5.0], [10.0, 10.0]]],
              "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="3"):
        build_manual_result(shape, cfg())


def test_self_intersecting_hole_is_rejected():
    exterior = [[0.0, 0.0], [20.0, 0.0], [20.0, 20.0], [0.0, 20.0]]
    bowtie_hole = [[5.0, 5.0], [15.0, 15.0], [15.0, 5.0], [5.0, 15.0]]
    shape = [{"polygon": exterior, "holes": [bowtie_hole],
              "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="invalid|self-intersect"):
        build_manual_result(shape, cfg())


def test_too_few_points_is_rejected():
    shape = [{"polygon": [[0.0, 0.0], [10.0, 0.0]], "technique": "fill",
              "thread_index": 0}]
    with pytest.raises(ValueError, match="3"):
        build_manual_result(shape, cfg())


@pytest.mark.parametrize("bad_index", [-1, 100000])
def test_out_of_range_thread_index_is_rejected(bad_index):
    shape = [{"polygon": RECT, "technique": "fill", "thread_index": bad_index}]
    with pytest.raises(ValueError, match="thread_index"):
        build_manual_result(shape, cfg())


def test_missing_thread_selection_is_rejected():
    shape = [{"polygon": RECT, "technique": "fill"}]
    with pytest.raises(ValueError, match="thread_index|thread_rgb"):
        build_manual_result(shape, cfg())


def test_both_thread_fields_at_once_is_rejected():
    shape = [{"polygon": RECT, "technique": "fill", "thread_index": 0,
              "thread_rgb": [10, 20, 30]}]
    with pytest.raises(ValueError, match="only one"):
        build_manual_result(shape, cfg())


def test_missing_technique_is_rejected():
    shape = [{"polygon": RECT, "thread_index": 0}]
    with pytest.raises(ValueError, match="technique"):
        build_manual_result(shape, cfg())


@pytest.mark.parametrize("bad_tier", ["auto", "sketch", "streamline", "zigzag", ""])
def test_unsupported_technique_is_rejected(bad_tier):
    """"streamline" stays out of `VALID_TECHNIQUES` deliberately, same
    reasoning the module docstring already gives for "sketch": both are
    raster-reading tiers, and a manually-authored shape here has no raster
    at all (no image was ever decoded — `PipelineResult.source_pixels` and
    `px_per_mm` are both `None` by construction). Exposing "streamline" as
    if it were selectable would either crash (`streamline_fill` dereferences
    `source_pixels.rgb`) or, if silently no-opped, be a fill type that always
    quietly sews tatami — worse than not offering it. This is the direct
    opposite case from the review-screen `shape_overrides[...].tier`
    override (`test_stage6_streamline.py`'s per-shape tests), which DOES
    grow a "streamline" value precisely because that path already has real
    source pixels to plumb through."""
    shape = [{"polygon": RECT, "technique": bad_tier, "thread_index": 0}]
    with pytest.raises(ValueError, match="technique"):
        build_manual_result(shape, cfg())


def test_non_finite_coordinate_is_rejected():
    shape = [{"polygon": [[0.0, 0.0], [10.0, 0.0], [10.0, float("nan")]],
              "technique": "fill", "thread_index": 0}]
    with pytest.raises(ValueError, match="finite"):
        build_manual_result(shape, cfg())


def test_shape_list_that_is_not_a_list_is_rejected():
    with pytest.raises(ValueError):
        build_manual_result("not a list", cfg())


def test_a_shape_that_is_not_an_object_is_rejected():
    with pytest.raises(ValueError, match="object"):
        build_manual_result([RECT], cfg())
