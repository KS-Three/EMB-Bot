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
    regions, dropped = vectorize([RegionMask.from_full(mask, layer=0)], [0], p, cfg)
    assert not dropped and len(regions) == 1, "the glyph must survive at all"
    poly = regions[0].polygon
    assert len(poly.exterior.coords) >= 12, \
        f"only {len(poly.exterior.coords)} vertices: the arms were simplified off"
    assert poly.area / poly.convex_hull.area <= 0.7, \
        "an E is concave; a convex result means the glyph was flattened"


def test_sub_detail_glyph_is_tagged_rescued_in_meta():
    """The `sub_detail` decision (sub-pixel eps + run-tier floor) must be
    visible on the resulting Region so a downstream pass (text-cluster
    detection) can find rescued shapes without re-deriving stage 4's own
    area math from scratch."""
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
    cfg = PipelineConfig()
    regions, dropped = vectorize([RegionMask.from_full(mask, layer=0)], [0], p, cfg)
    assert not dropped and len(regions) == 1
    assert regions[0].meta["rescued_small_shape"] is True


def test_ordinary_shape_has_no_rescued_flag():
    """An everyday, above-min-detail shape must not carry the key at all —
    only `True` is ever written, the same convention as
    `enclosed_background` (absent means false, never an explicit False)."""
    ppm = 15.0
    mask = np.zeros((80, 80), bool)
    mask[10:70, 10:70] = True  # a big filled square, nowhere near sub-detail
    p = Prep(rgb=np.zeros((80, 80, 3), np.uint8),
             bg_mask=np.zeros((80, 80), bool),
             px_per_mm=ppm, art_bbox=(0, 0, 80, 80))
    cfg = PipelineConfig()
    regions, dropped = vectorize([RegionMask.from_full(mask, layer=0)], [0], p, cfg)
    assert not dropped and len(regions) == 1
    assert "rescued_small_shape" not in regions[0].meta


# --- simplify_tol_mm: measured, not assumed, to already be scale-invariant -


def test_simplify_tol_mm_realized_deviation_is_px_per_mm_invariant():
    """Ember Design's equivalent scales its simplify tolerance with design
    size (`config.py`'s `simplify_tol_mm` docstring has the full writeup on
    why that isn't a like-for-like fix here). Direct measurement, not just
    the algebra: hold ONE synthetic contour's pixel geometry fixed and sweep
    `px_per_mm` across 3.0-40.0 — the range this app's real 40-180 mm
    `target_width_mm` bound produces (measured 4.0-34.1 px/mm running the
    full pipeline on every testdata fixture at 40-180 mm; 3.0 sits just
    below the resolution floor `stage1_prep` normally guarantees, included
    as a below-floor edge case). At every value the REALIZED deviation
    between the simplified and unsimplified contour — Hausdorff distance in
    mm, not the eps_px formula's own algebra — stays 0.185-0.200 mm, i.e.
    `simplify_tol_mm` itself (0.2), regardless of how big or small the
    design is. Vertex count is NOT expected to be invariant (a coarser
    design genuinely has less raw pixel detail available to preserve, not
    more error) — asserted here only as evidence the contour is real and
    responding to scale, not a degenerate no-op.
    """
    # A wavy blob with real curvature at two frequencies, so approxPolyDP has
    # genuine work to do rather than trivially collapsing a near-circle.
    size = 600
    yy, xx = np.mgrid[0:size, 0:size]
    cx, cy = size / 2, size / 2
    theta = np.arctan2(yy - cy, xx - cx)
    r = np.hypot(xx - cx, yy - cy)
    radius = 220 + 18 * np.sin(theta * 7) + 6 * np.sin(theta * 23)
    mask = r <= radius

    prior_vtx = None
    for ppm in [3.0, 4.0, 5.0, 8.0, 12.5, 16.75, 22.35, 40.0]:
        p = Prep(rgb=np.zeros((size, size, 3), np.uint8),
                 bg_mask=np.zeros((size, size), bool),
                 px_per_mm=ppm, art_bbox=(0, 0, size, size))
        # min_detail_mm dropped near-zero so nothing here takes the
        # sub-detail rescue path (that path's own fixed 0.5 px floor is a
        # different mechanism — see the config.py docstring — and would
        # confound this measurement of simplify_tol_mm in isolation).
        cfg_tol = PipelineConfig(target_width_mm=999, min_detail_mm=0.01)
        cfg_raw = PipelineConfig(target_width_mm=999, min_detail_mm=0.01,
                                  simplify_tol_mm=1e-6)
        regions_tol, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p, cfg_tol)
        regions_raw, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p, cfg_raw)
        poly_tol = regions_tol[0].polygon
        poly_raw = regions_raw[0].polygon
        hd = poly_tol.exterior.hausdorff_distance(poly_raw.exterior)
        eps_px = max(0.5, cfg_tol.simplify_tol_mm * ppm)
        if eps_px > 0.5:  # not floored — the 0.2 mm tolerance is exact here
            assert 0.15 <= hd <= 0.22, f"px_per_mm={ppm}: hausdorff={hd:.4f}mm"
        else:  # floored (below the ~2.5 px_per_mm this app's own resolution
            # floor keeps designs clear of in practice): the realized
            # tolerance widens, but must still be small and bounded, never
            # a silent runaway.
            assert hd <= 0.5, f"px_per_mm={ppm}: hausdorff={hd:.4f}mm (floored)"

        vtx = len(poly_tol.exterior.coords) - 1
        if prior_vtx is not None:
            # Vertex count must respond to scale (more px_per_mm -> more raw
            # detail survives) — a flat count across the whole sweep would
            # mean the mask/eps wiring above is a no-op, not real evidence.
            assert vtx != prior_vtx
        prior_vtx = vtx


def test_a_shape_no_tier_can_stitch_sews_its_outline():
    """The reactive rescue: a ribbon thinner than half a fill row at the
    angle it's asked to sew at produces no rows at all, and used to vanish
    as SHAPE_NOT_STITCHED even though it passed every size floor. Its
    outline still exists; sew that.

    Angle pinned explicitly (`meta["fill_angle_deg"]`) rather than left to
    auto-selection: `stage6_fill.best_fill_angle_deg` now sweeps 16
    candidate row directions plus the plain PCA angle specifically to find
    a working angle when one exists, so a ribbon this size auto-selected
    would just find one (measured: this same 20x0.15mm ribbon finds 49 rows
    at the sweep's chosen 78.75deg) — which would make this test exercise
    the sweep, not the rescue. Pinning the angle keeps this test's actual
    subject (sequence()'s handling of a genuinely empty fill report)
    independent of how good angle auto-selection happens to be.
    """
    hair = Polygon([(0, 0), (20, 0), (20, 0.15), (0, 0.15)])
    reg = Region(shape_id="Shair", polygon=hair, thread_index=0,
                 thread_number="0134", area_mm2=hair.area, source="test",
                 meta={"layer": 0, "fill_angle_deg": 0.0})
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


# --- curves sewn as curves: `curve_turn_deg` (2026-09-03, defect 22) --------


def _disc_mask(radius_px: float, size: int) -> np.ndarray:
    yy, xx = np.mgrid[0:size, 0:size]
    return np.hypot(xx - size / 2.0, yy - size / 2.0) <= radius_px


def _vertex_turns_deg(poly) -> np.ndarray:
    pts = np.asarray(poly.exterior.coords[:-1], dtype=float)
    v = np.roll(pts, -1, axis=0) - pts
    ang = np.degrees(np.arctan2(v[:, 1], v[:, 0]))
    return np.abs((np.diff(np.append(ang, ang[0])) + 180.0) % 360.0 - 180.0)


def test_curve_turn_deg_none_is_byte_identical_to_douglas_peucker():
    """The default has to be invisible: every golden is pinned to plain
    Douglas-Peucker at `simplify_tol_mm`, so None must give the same
    polygon, vertex for vertex."""
    size = 400
    mask = _disc_mask(75.0, size)          # a 2.4 mm-radius counter at 31 px/mm
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=31.25, art_bbox=(0, 0, size, size))
    a, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                     PipelineConfig(target_width_mm=999, min_detail_mm=0.01))
    b, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                     PipelineConfig(target_width_mm=999, min_detail_mm=0.01, curve_turn_deg=None))
    assert list(a[0].polygon.exterior.coords) == list(b[0].polygon.exterior.coords)


def test_curve_turn_deg_turns_a_9_gon_counter_into_a_curve():
    """Kent: "this O is not round." At 0.2 mm tolerance a 2.4 mm-radius arc
    is a polygon of ~45 deg corners (Hotel Fremont's counter: 9 vertices,
    47 deg). With `curve_turn_deg=15` the same raster contour comes back
    with no vertex turning more than ~2x the target and at least three
    times the vertices, every one within a pixel and a half of the true
    circle -- the raster's own limit, not the polygon's."""
    size = 400
    radius_px = 75.0                                     # 2.4 mm at 31.25 px/mm
    mask = _disc_mask(radius_px, size)
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=31.25, art_bbox=(0, 0, size, size))
    plain, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                         PipelineConfig(target_width_mm=999, min_detail_mm=0.01))
    curved, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                          PipelineConfig(target_width_mm=999, min_detail_mm=0.01, curve_turn_deg=15.0))
    n_plain = len(plain[0].polygon.exterior.coords) - 1
    n_curve = len(curved[0].polygon.exterior.coords) - 1
    assert n_plain <= 16, n_plain
    assert n_curve >= 3 * n_plain, (n_plain, n_curve)
    turns = _vertex_turns_deg(curved[0].polygon)
    assert turns.max() <= 30.0, turns.max()
    pts = np.asarray(curved[0].polygon.exterior.coords[:-1])
    cx = cy = 0.0                                          # `_to_mm` centres on the art bbox
    radial = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - radius_px / 31.25
    assert np.abs(radial).max() <= 1.5 / 31.25, np.abs(radial).max()


def test_curve_turn_deg_leaves_straight_edges_alone():
    """Only arcs gain vertices. A rotated rectangle's edges are staircases
    under the one-pixel floor, so it stays a quadrilateral with the flag on
    -- the polygon is not smoothed, it is re-read where it curved. (At
    12 px/mm the bound in force on these edges is `simplify_tol_mm`'s 2.4 px,
    which the staircase is also under.)"""
    import cv2

    size = 400
    img = np.zeros((size, size), np.uint8)
    box = cv2.boxPoints(((size / 2, size / 2), (250.0, 80.0), 25.0)).astype(np.int32)
    cv2.fillPoly(img, [box], 1)
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=12.0, art_bbox=(0, 0, size, size))
    plain, _ = vectorize([RegionMask.from_full(img > 0, layer=0)], [0], p,
                         PipelineConfig(target_width_mm=999, min_detail_mm=0.01))
    curved, _ = vectorize([RegionMask.from_full(img > 0, layer=0)], [0], p,
                          PipelineConfig(target_width_mm=999, min_detail_mm=0.01, curve_turn_deg=15.0))
    assert len(plain[0].polygon.exterior.coords) == len(curved[0].polygon.exterior.coords)


def test_curve_turn_deg_value_governs_once_the_arc_is_above_the_pixel_floor():
    """At a 2.4 mm radius every chord under ~30 px is bounded by the one-pixel
    floor, so 5, 10 and 15 deg read the same polygon there. The angle term
    takes over on larger arcs: a 300 px-radius disc reads more vertices at
    15 deg than at 30, and the vertex turns follow the setting."""
    size = 700
    radius_px = 300.0
    mask = _disc_mask(radius_px, size)
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=31.25, art_bbox=(0, 0, size, size))

    def poly_at(turn):
        regions, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                               PipelineConfig(target_width_mm=999, min_detail_mm=0.01,
                                              curve_turn_deg=turn))
        return regions[0].polygon

    fine, coarse = poly_at(15.0), poly_at(30.0)
    n_fine = len(fine.exterior.coords) - 1
    n_coarse = len(coarse.exterior.coords) - 1
    assert n_fine > n_coarse, (n_fine, n_coarse)
    assert _vertex_turns_deg(fine).max() <= 20.0
    assert _vertex_turns_deg(coarse).max() <= 40.0
    assert _vertex_turns_deg(coarse).max() > _vertex_turns_deg(fine).max()


def test_curve_refinement_maps_vertices_in_ring_order_across_a_hairline_neck():
    """A contour traced with CHAIN_APPROX_NONE visits a one-pixel-wide neck
    twice with identical coordinates. The vertex-to-raw mapping walks both
    rings in lockstep so the return leg is not sent to its outbound twin
    (review, 2026-09-03): the refined ring keeps the simplified ring's
    vertices in order, and the polygon stays valid."""
    size = 300
    img = np.zeros((size, size), np.uint8)
    yy, xx = np.mgrid[0:size, 0:size]
    img[np.hypot(xx - 90, yy - 150) <= 60] = 1
    img[np.hypot(xx - 210, yy - 150) <= 60] = 1
    img[150, 90:210] = 1                                 # a one-pixel neck
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=20.0, art_bbox=(0, 0, size, size))
    plain, _ = vectorize([RegionMask.from_full(img > 0, layer=0)], [0], p,
                         PipelineConfig(target_width_mm=999, min_detail_mm=0.01))
    curved, _ = vectorize([RegionMask.from_full(img > 0, layer=0)], [0], p,
                          PipelineConfig(target_width_mm=999, min_detail_mm=0.01, curve_turn_deg=15.0))
    assert len(curved) == len(plain)
    for a, b in zip(plain, curved):
        assert b.polygon.is_valid
        # the refined ring is truer, and truer means bigger on a disc (DP
        # chords cut inside the arc): a few percent, never a re-route
        assert abs(b.polygon.area - a.polygon.area) < 0.05 * a.polygon.area
        # every simplified vertex survives, in ring order
        ring_a = [tuple(np.round(c, 6)) for c in a.polygon.exterior.coords[:-1]]
        ring_b = [tuple(np.round(c, 6)) for c in b.polygon.exterior.coords[:-1]]
        pos = [ring_b.index(v) for v in ring_a if v in ring_b]
        assert len(pos) >= len(ring_a) - 2, (len(pos), len(ring_a))
        rolled = pos[pos.index(min(pos)):] + pos[:pos.index(min(pos))]
        assert rolled == sorted(rolled), rolled


def test_near_floor_holes_keep_their_polygon_while_the_shell_is_refined():
    """Kent's ruling (2026-09-03): near-floor lettering is not refined. The
    letters of a small line are also HOLES of the background they sit in,
    and stage 5 reshapes a letter against its background's hole -- so the
    guard has to judge every ring on its own. Review of PR #328 measured the
    shell-only guard leaving Fremont's `S54b55cf1` (0.47 mm strokes) with 0
    satin crosses under the flag because its hole in the background was
    refined; per-ring gating keeps all 24. Here: a disc background with a
    0.45 mm bar hole and a 1.3 mm disc hole -- the shell and the wide hole
    gain vertices, the bar hole is byte-identical to the flag-off polygon."""
    size = 400
    px_per_mm = 31.25
    yy, xx = np.mgrid[:size, :size]
    mask = (xx - 200) ** 2 + (yy - 200) ** 2 <= 150.0 ** 2          # 4.8 mm disc
    bar = (np.abs(xx - 200) <= 47) & (np.abs(yy - 120) <= 7)         # 3.0 x 0.45 mm bar
    disc = (xx - 200) ** 2 + (yy - 270) ** 2 <= 40.0 ** 2            # 1.3 mm radius hole
    mask = mask & ~bar & ~disc
    p = Prep(rgb=np.zeros((size, size, 3), np.uint8), bg_mask=np.zeros((size, size), bool),
             px_per_mm=px_per_mm, art_bbox=(0, 0, size, size))
    off, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                       PipelineConfig(target_width_mm=999, min_detail_mm=0.01))
    on, _ = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                      PipelineConfig(target_width_mm=999, min_detail_mm=0.01, curve_turn_deg=15.0))
    assert len(off) == 1 and len(on) == 1
    assert len(on[0].polygon.exterior.coords) > len(off[0].polygon.exterior.coords), "shell not refined"

    def rings(poly):
        out = {}
        for ring in poly.interiors:
            c = Polygon(ring).centroid
            out["bar" if c.y < 0 else "disc"] = list(ring.coords)
        return out

    r_off, r_on = rings(off[0].polygon), rings(on[0].polygon)
    assert set(r_off) == {"bar", "disc"} == set(r_on)
    assert r_on["bar"] == r_off["bar"], "the near-floor bar hole was refined"
    assert len(r_on["disc"]) > len(r_off["disc"]), "the wide disc hole was not refined"
