"""The run tier — small shapes sew as outlines instead of vanishing.

The defect this build step erases: the pipeline silently dropped artwork too
small to fill or satin. On the owner's benchmark logo at 90 mm the whole
"ENTERPRISES INC." subline — fourteen letters, 1.9 mm tall — disappeared,
with nothing but a DROPPED_SMALL_SHAPES count to show for it. The rescue
keeps such shapes and sews their outline as a bean run (the professional
light tier: 3 passes at 0.73 mm), while a true-noise floor — the thread's
own visual weight — still drops what no technique can render.

The fixture is synthetic: a filled wordmark bar with a row of sub-detail
"letters" below it, plus two calibrated pieces of noise. Deterministic, and
shaped exactly like the failure that was found in the wild.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stage4_vectorize import vectorize
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_border import run_outline
from digitizer_core.stage7_sequence import sequence
from digitizer_core.warnings_codes import (
    DROPPED_SMALL_SHAPES,
    SHAPE_NOT_STITCHED,
    SMALL_SHAPES_AS_RUN,
)


def _subline_image() -> np.ndarray:
    """A wordmark with a sub-detail subline: the benchmark's shape, distilled.

    At target 80 mm the artwork lands at 8.75 px/mm, so the six 8x16 px bars
    are 0.9 x 1.8 mm — the size of the benchmark's subline letters, below the
    1.5 mm sewable floor but well above the thread-weight noise floor. The
    9x9 px dot (1.0 mm) fails the rescue's loop floor and must still drop
    REPORTED; the 3 px speck (0.3 mm) is anti-alias-sized dust and must
    still drop silently.
    """
    img = np.full((300, 800, 3), 255, np.uint8)
    img[60:140, 50:750] = (40, 40, 40)              # the wordmark
    for i in range(6):                              # the subline
        x = 300 + i * 20
        img[170:186, x:x + 8] = (40, 40, 40)
    img[200:209, 100:109] = (40, 40, 40)            # 1.0 mm dot: floor, reported
    img[200:203, 500:503] = (40, 40, 40)            # 0.3 mm speck: dust, silent
    return img


@pytest.fixture(scope="module")
def rescued():
    return digitize(_subline_image(),
                    PipelineConfig(target_width_mm=80.0, garment_id="left_chest"))


def test_rescue_is_the_default():
    assert PipelineConfig().small_shape_rescue is True


def test_small_isolated_text_sews_instead_of_vanishing(rescued):
    """THE defect: sub-detail letters with no neighbour to absorb into were
    dropped outright, and a whole line of a customer's logo vanished."""
    result, plan = rescued
    small = [r for r in result.regions if r.area_mm2 < 2.25]
    assert len(small) == 6, "all six subline bars must survive to stage 4"

    sewn_as_run = {r.shape_id for _b, r in plan.iter_runs() if r.kind == "run"}
    assert {r.shape_id for r in small} <= sewn_as_run, \
        "every rescued shape must produce run stitches"

    warning = next(w for w in plan.warnings if w["code"] == SMALL_SHAPES_AS_RUN)
    assert warning["count"] == 6, "the report must count what was rescued"


def test_run_stitches_land_on_the_rescued_shapes(rescued):
    """The rescue must sew the letters where they are: every rescued shape
    gets run stitches inside its own bounds (the benchmark acceptance probe —
    runs in the subline's bbox region — in fixture form)."""
    result, plan = rescued
    small = {r.shape_id: r for r in result.regions if r.area_mm2 < 2.25}
    for shape_id, region in small.items():
        pts = [p for _b, r in plan.iter_runs()
               if r.kind == "run" and r.shape_id == shape_id for p in r.points]
        assert pts, f"{shape_id} sewed nothing"
        x0, y0, x1, y1 = region.polygon.bounds
        for x, y in pts:
            assert x0 - 0.1 <= x <= x1 + 0.1 and y0 - 0.1 <= y <= y1 + 0.1, \
                f"{shape_id} run stitch at ({x:.2f},{y:.2f}) escaped its shape"


def test_noise_below_thread_weight_still_drops_and_is_reported(rescued):
    """The rescue must not sew lint. The 1.0 mm dot fails the loop floor
    (2*max(w,h) < RUN_MIN_LOOP_MM) and is big enough to be REPORTED dropped;
    the 0.3 mm speck is anti-alias dust and is cleaned silently, exactly as
    before. Rescuing hundreds of specks would be the opposite defect."""
    result, plan = rescued
    # Neither piece of noise may reach stage 4 ...
    for r in result.regions:
        x0, y0, x1, y1 = r.polygon.bounds
        assert not (x1 - x0 < 1.2 and y1 - y0 < 1.2), \
            f"{r.shape_id} looks like rescued noise: {r.polygon.bounds}"
    # ... and the reportable one still fires the honest drop warning.
    dropped = next(w for w in plan.warnings if w["code"] == DROPPED_SMALL_SHAPES)
    assert dropped["count"] == 1, "the 1.0 mm dot is genuinely dropped artwork"


def test_rescue_off_restores_the_old_drop():
    """The escape hatch: small_shape_rescue=False must reproduce the old
    behaviour exactly — shapes dropped, warned, and no run stitches anywhere."""
    result, plan = digitize(
        _subline_image(),
        PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                       small_shape_rescue=False))
    assert len(result.regions) == 1, "only the wordmark survives without rescue"
    assert not [r for _b, r in plan.iter_runs() if r.kind == "run"]
    dropped = next(w for w in plan.warnings if w["code"] == DROPPED_SMALL_SHAPES)
    assert dropped["count"] == 7, "six bars and the dot, all reportable-sized"
    assert SMALL_SHAPES_AS_RUN not in {w["code"] for w in plan.warnings}


def test_sub_detail_glyphs_survive_simplification():
    """Stage 4's eps is sized for shapes with room to spare: 0.2 mm is 3 px at
    benchmark resolution, and on the 1.9 mm subline it deleted both "I"s and
    mangled the rest into "ENTERPR SES NC". A sub-detail mask must get the
    sub-pixel floor instead — this E keeps its arms (concave, vertex-rich)
    where the stage eps flattened it to an 8-vertex blob."""
    ppm = 15.0
    mask = np.zeros((80, 80), bool)
    ey, ex = 30, 30
    mask[ey:ey + 24, ex:ex + 4] = True          # spine
    mask[ey:ey + 4, ex:ex + 18] = True          # top arm
    mask[ey + 10:ey + 14, ex:ex + 15] = True    # middle arm
    mask[ey + 20:ey + 24, ex:ex + 18] = True    # bottom arm

    p = Prep(rgb=np.zeros((80, 80, 3), np.uint8),
             bg_mask=np.zeros((80, 80), bool),
             px_per_mm=ppm, art_bbox=(0, 0, 80, 80))
    cfg = PipelineConfig()  # simplify_tol_mm 0.2 -> eps 3 px at this scale
    regions, dropped = vectorize([RegionMask(mask=mask, layer=0)], [0], p, cfg)
    assert not dropped and len(regions) == 1, "the glyph must survive at all"
    poly = regions[0].polygon
    assert len(poly.exterior.coords) >= 12, \
        f"only {len(poly.exterior.coords)} vertices: the arms were simplified off"
    assert poly.area / poly.convex_hull.area <= 0.7, \
        "an E is concave; a convex result means the glyph was flattened"


def test_a_shape_no_tier_can_stitch_sews_its_outline():
    """The reactive rescue: a ribbon thinner than half a fill row produces no
    rows at all, and used to vanish as SHAPE_NOT_STITCHED even though it
    passed every size floor. Its outline still exists; sew that."""
    hair = Polygon([(0, 0), (20, 0), (20, 0.15), (0, 0.15)])
    reg = Region(shape_id="Shair", polygon=hair, thread_index=0,
                 thread_number="0134", area_mm2=hair.area, source="test",
                 meta={"layer": 0})
    planned = [PlannedRegion(region=reg, polygon=hair, sew_index=0)]
    fabric = fabric_for_garment("left_chest")

    blocks, warnings = sequence(
        planned, fabric, PipelineConfig(satin=False, underlay=False))
    assert {r.kind for b in blocks for r in b.runs} >= {"run"}
    assert SMALL_SHAPES_AS_RUN in {w["code"] for w in warnings}

    blocks_off, warnings_off = sequence(
        planned, fabric,
        PipelineConfig(satin=False, underlay=False, small_shape_rescue=False))
    assert not blocks_off, "without rescue this shape produced nothing"
    assert SHAPE_NOT_STITCHED in {w["code"] for w in warnings_off}


def test_run_outline_is_a_closed_bean_circuit():
    """The rendering itself: one closed circuit per ring, bean passes on the
    exact outline (kind "run", so 'border off changes nothing' stays
    checkable), and a ring below RUN_MIN_LOOP_MM is refused, not faked."""
    square = Polygon([(0, 0), (1.2, 0), (1.2, 1.2), (0, 1.2)])
    runs, report = run_outline(square, "S1", entry=None, trim_at_mm=3.0)
    assert report["loops"] == 1 and not report["empty"]
    assert [r.kind for r in runs] == ["run"]
    pts = runs[0].points
    assert math.dist(pts[0], pts[-1]) < 1e-6, "a bean circuit ends at its start"
    length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    perim = square.exterior.length
    assert 2.5 * perim <= length <= machine.BEAN_PASSES * perim + 1e-6, \
        f"{length:.2f} mm sewn on a {perim:.2f} mm ring is not a triple pass"

    dot = Polygon([(0, 0), (0.5, 0), (0.5, 0.5), (0, 0.5)])   # 2.0 mm ring
    d_runs, d_report = run_outline(dot, "S2", entry=None, trim_at_mm=3.0)
    assert d_report["empty"] and d_runs == [], \
        "below three bean stations there is nothing honest to sew"
