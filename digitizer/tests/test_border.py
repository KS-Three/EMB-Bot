"""Stage 6 border — an outline sewn as one closed circuit.

The module's whole thesis is that a border is the region between two offsets
of a ring, expressed with `buffer` so containment is a boolean rather than a
sign convention. These tests hold it to the four numbers the corpus measured
(width, density, one circuit per ring, corners sewn through) and to the one
promise the default makes: with `border="off"` nothing changes at all.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, Region, digitize, fabric_for_garment, machine
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_border import border_runs
from digitizer_core.stage7_sequence import sequence
from digitizer_core.warnings_codes import BORDER_SEAM_SHARED
from tests.conftest import TESTDATA, cfg

SQUARE = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
DONUT = Polygon(
    [(math.cos(t) * 12, math.sin(t) * 12) for t in np.linspace(0, 2 * math.pi, 96)],
    [[(math.cos(t) * 6, math.sin(t) * 6) for t in np.linspace(2 * math.pi, 0, 96)]],
)
THIN_BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])
HAIRLINE = Polygon([(0, 0), (24, 0), (24, 0.5), (0, 0.5)])


def _runs(poly, style="auto", **kw):
    runs, report = border_runs(poly, "S1", entry=None, trim_at_mm=3.0,
                               style=style, **kw)
    return runs, report


# --- The default promises nothing changes ----------------------------------

def test_no_border_is_the_default_and_changes_nothing():
    """The measured case for no border: our fill already ends both row ends on
    the shape's edge, so there is no ragged edge for a border to cover, and an
    unearned outline is a few hundred stitches of machine time for nothing.

    The default moved from the string "off" to None on 2026-08-25 so that "the
    caller chose off" and "the caller chose nothing" stop being the same value
    — see config.py's border block for why that distinction is load-bearing.
    None still resolves to "off" for every class but the photo ones, which is
    what keeps this fixture's assertion (a flat logo) true unchanged.
    """
    assert PipelineConfig().border is None

    plain = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front"))[1]
    off = digitize(TESTDATA / "logo_whitebg.png",
                   cfg(garment_id="hat_front", border="off"))[1]
    assert plain.stats.stitch_count == off.stats.stitch_count
    assert not [r for _b, r in off.iter_runs() if r.kind in ("border", "bean")]


# --- The "significant" mode: Kent's rule, 2026-08-25 -----------------------

def test_border_worthy_wants_significant_and_smooth():
    """Both gates, independently: a shape earns a border by being a real share
    of the design AND by having an outline a border can trace cleanly.

    The populations these numbers came off (owl_kent.jpg on its own default
    route, 35 regions, per-ring raggedness): the four shapes that earn a
    border sit at 2.09 / 2.51 / 2.72 / 3.39, and the ten significant ones
    refused as abrupt start at 3.91 and run to 12.22. The 3.5 cutoff falls in
    that empty band — it separates two real populations rather than slicing
    through one. It is not CENTRED in the band, though: 3.65 would be. Left at
    3.5 because a rounder number is easier to reason about and the margin
    either side is real; revisit when portraits exist to measure.
    """
    from digitizer_core.stage7_sequence import _border_worthy, _raggedness

    disc = Point(0, 0).buffer(10.0)            # compact: raggedness ~1.0
    assert _raggedness(disc) == pytest.approx(1.0, abs=0.02)
    assert _raggedness(HAIRLINE) > machine.BORDER_ABRUPT_RAGGEDNESS

    total = disc.area * 100.0
    # Significant and smooth -> bordered.
    assert _border_worthy(disc, total, 0.0025, machine.BORDER_ABRUPT_RAGGEDNESS)
    # Smooth but too small a share -> not significant, no border.
    assert not _border_worthy(disc, disc.area * 10_000.0, 0.0025,
                              machine.BORDER_ABRUPT_RAGGEDNESS)
    # Big enough but abrupt -> the border would trace the raggedness.
    assert not _border_worthy(HAIRLINE, HAIRLINE.area * 2.0, 0.0025,
                              machine.BORDER_ABRUPT_RAGGEDNESS)


def test_a_smooth_ring_is_not_abrupt_however_thin():
    """REGRESSION (2026-08-25, same day the gate shipped). Raggedness is
    measured PER RING, so a clean annulus reads 1.0 no matter how thin it is.

    Measuring the whole shape at once summed every ring's perimeter over the
    hole-subtracted area, which made thinness look like raggedness: an outer
    10 / inner 8 ring scored 9.0 and an inner 9.4 scored 32.3, so both were
    refused a border — when a ring is the IDEAL border candidate (a letter O,
    a badge outline). That was the gate accidentally measuring WIDTH, which
    `border_runs` already handles downstream and better (a too-thin shape
    lightens to a bean run, a hairline is refused outright).
    """
    from digitizer_core.stage7_sequence import _border_worthy, _raggedness

    T = machine.BORDER_ABRUPT_RAGGEDNESS
    for inner in (2.0, 5.0, 8.0, 9.4):
        annulus = Point(0, 0).buffer(10.0).difference(Point(0, 0).buffer(inner))
        assert _raggedness(annulus) == pytest.approx(1.0, abs=0.05), \
            f"ring 10/{inner} should read as smooth as the circle it is"
        assert _border_worthy(annulus, annulus.area * 50.0, 0.0025, T), \
            f"ring 10/{inner} is smooth and significant — it earns a border"

    # ...and the fix does NOT let a genuinely ragged shape through: a ring
    # whose inner edge is a star still fails on that ring alone.
    spikes = Polygon([(math.cos(t) * (3.0 + 2.5 * (i % 2)),
                       math.sin(t) * (3.0 + 2.5 * (i % 2)))
                      for i, t in enumerate(np.linspace(0, 2 * math.pi, 41))])
    ragged_ring = Point(0, 0).buffer(10.0).difference(spikes)
    assert _raggedness(ragged_ring) > T
    assert not _border_worthy(ragged_ring, ragged_ring.area * 50.0, 0.0025, T)


def test_border_worthy_survives_degenerate_geometry():
    """A zero-area fragment is neither significant nor borderable, and stage 7
    must not die on one — it used to, see the seam test below."""
    from digitizer_core.stage7_sequence import _border_worthy

    assert not _border_worthy(Polygon(), 100.0, 0.0025, 3.5)
    assert not _border_worthy(SQUARE, 0.0, 0.0025, 3.5)


def test_geometry_collection_visible_geom_does_not_crash():
    """REGRESSION (2026-08-25). Shapely 2.1.2 returns None for
    `GeometryCollection.boundary`, and `_seam_band` called `.boundary.buffer()`
    on it unguarded — an AttributeError that took the whole `plan_stitches`
    call down, not a warning. Stage 5's overlap resolution can leave a visible
    geometry as exactly such a collection (a polygon plus a degenerate sliver).

    Never fired in production because `border` was "off" for everything;
    `testdata/photo/photo_dof_meadow.png` hits it the moment borders are on,
    which the photo route now turns them on for.
    """
    from shapely.geometry import GeometryCollection, LineString as _LS

    from digitizer_core.stage7_sequence import _polygonal_boundary, _seam_band

    coll = GeometryCollection([SQUARE, _LS([(30, 30), (34, 34)])])
    assert coll.boundary is None, "shapely changed; this guard may be moot"
    assert _polygonal_boundary(coll) is not None

    # The abutting neighbour shares SQUARE's right edge, so this is the real
    # seam case, not just a no-crash smoke test.
    band, length = _seam_band(coll, Polygon([(20, 0), (40, 0), (40, 20), (20, 20)]))
    assert band is not None and length == pytest.approx(20.0, abs=0.5)

    # And a collection with no polygonal part at all reports "no seam".
    assert _seam_band(GeometryCollection([_LS([(0, 0), (1, 1)])]), SQUARE) == (None, 0.0)


def test_style_none_and_missing_geometry_are_no_ops():
    assert _runs(SQUARE, style="none")[0] == []
    assert border_runs(None, "S1", entry=None, trim_at_mm=3.0)[0] == []


# --- One closed circuit per ring (law 13, 18/18) ---------------------------

def test_a_square_sews_as_one_circuit():
    runs, report = _runs(SQUARE)
    border = [r for r in runs if r.kind == "border"]
    assert len(border) == 1, "an outline is one circuit, not an assembly of arcs"
    assert report["loops"] == 1

    pts = border[0].points
    # A closed circuit ends where it began, within the deliberate overlap that
    # closes the seam — plus the whole-station phase the closure carries so its
    # penetrations land between the opening ones, and up to a column width
    # because start and end may sit on opposite rails.
    slack = machine.BORDER_CLOSURE_OVERLAP_MM + machine.BORDER_DENSITY_MM / 2 \
        + machine.BORDER_WIDTH_MM / 2
    assert math.dist(pts[0], pts[-1]) <= slack + 0.1


def test_a_counter_gets_its_own_circuit():
    """A shape with a hole has two visible edges, so it has two borders. This
    is why the geometry is built with buffer: one call returns every ring."""
    _runs_, report = _runs(DONUT)
    assert report["loops"] == 2, f"expected exterior + counter, got {report['loops']}"


# --- The corpus numbers ----------------------------------------------------

def test_constants_carry_the_law_41_adjudication():
    """docs/corpus-laws-round3-2026-08-01.md law 41 (unapplied-rulings table,
    :670-671), adjudicated desk-safe 2026-08-01 and never applied until now:
    an edge-covering border is WIDER than the closed-loop-letter population
    law 11 measured (1.66 mm med, 2.39 on the >=20 mm subset; ruling 1.70),
    and it sews at 0.40 mm density (p10 0.36, p90 0.42) — identical to
    lettering, refuting round 2's "looser than lettering" 0.45."""
    assert machine.BORDER_WIDTH_MM == 1.70
    assert machine.BORDER_DENSITY_MM == 0.40


def test_the_column_is_border_width_not_lettering_width():
    """Round 3 law 41: edge-covering borders run 1.66 mm median (2.39 on the
    >=20 mm subset), still well under 2.21 mm for satin generally. Sewing
    borders at full lettering width is most of why a machine outline reads
    heavy."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    crosses = sorted(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    med = crosses[len(crosses) // 2]
    assert med == pytest.approx(machine.BORDER_WIDTH_MM, abs=0.15), \
        f"border column median {med:.2f} mm"


def test_density_is_the_lettering_figure_no_relaxation():
    """Round 3 law 41 refuted round 2's "looser than lettering" 0.45: real
    covering borders sew at 0.40 mm, identical to lettering columns. Rails
    alternate A, B, A, B ... so two apart is the same rail."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    adv = sorted(math.dist(pts[i], pts[i + 2]) for i in range(len(pts) - 2))
    n = len(adv)
    assert adv[n // 2] == pytest.approx(machine.BORDER_DENSITY_MM, abs=0.08), \
        f"median same-rail advance {adv[n // 2]:.2f} mm"
    assert adv[int(n * 0.95)] <= 2 * machine.BORDER_DENSITY_MM


def test_no_stitch_exceeds_the_dst_ceiling():
    for poly in (SQUARE, DONUT, THIN_BAR):
        runs, _ = _runs(poly)
        for r in runs:
            for a, b in zip(r.points, r.points[1:]):
                assert math.dist(a, b) <= machine.MAX_STITCH_MM + 1e-6


# --- Containment is the point ----------------------------------------------

def test_the_whole_column_lies_inside_the_shape():
    """With BORDER_SEAM_OFFSET_MM at 0.0 the outer rail sits ON the visible
    edge and nothing crosses it. This is the assertion that would catch the
    winding-sign bug the module was built with `buffer` to make unexpressable:
    if offsets ever flipped outward, every border would fail here at once.
    """
    for poly in (SQUARE, DONUT):
        runs, _ = _runs(poly)
        room = poly.buffer(0.15)
        outside = [p for r in runs if r.kind == "border"
                   for p in r.points if not room.covers(Point(p))]
        assert outside == [], f"{len(outside)} border points outside the shape"


# --- The light tier and the refusal ----------------------------------------

def test_a_shape_too_thin_for_a_column_lightens_to_a_bean_run():
    runs, report = _runs(THIN_BAR)
    assert report["bean_loops"] >= 1
    assert report["loops"] == 0, "a 2 mm bar cannot host a 1.7 mm column"
    assert all(r.kind != "border" for r in runs)


def test_bean_style_lightens_even_where_a_column_would_fit():
    runs, report = _runs(SQUARE, style="bean")
    assert report["bean_loops"] >= 1 and report["loops"] == 0
    assert any(r.kind == "bean" for r in runs)


def test_a_shape_with_no_room_at_all_is_refused_not_faked():
    _runs_, report = _runs(HAIRLINE)
    assert report["too_narrow"] >= 1
    assert report["empty"], "nothing may be drawn where a centreline cannot live"


# --- Wiring ----------------------------------------------------------------

def test_auto_borders_the_fills_and_warns_when_it_lightens():
    auto = digitize(TESTDATA / "logo_whitebg.png",
                    cfg(garment_id="hat_front", border="auto"))[1]
    kinds = {r.kind for _b, r in auto.iter_runs()}
    assert "border" in kinds

    bean = digitize(TESTDATA / "logo_whitebg.png",
                    cfg(garment_id="hat_front", border="bean"))[1]
    assert "bean" in {r.kind for _b, r in bean.iter_runs()}
    assert "BORDER_LIGHTENED" in {w["code"] for w in bean.warnings}


# --- The review wave: closure phase, meta carry, corner bite ----------------

def test_closing_penetrations_avoid_their_own_rails_holes():
    """Regression, from adversarial review: the closing overlap was phased by
    HALF a station, but stations alternate rails, so same-rail holes sit two
    stations apart and the half shift put every closing penetration a
    quarter-pitch (0.11 mm — inside the same-hole radius) from an existing
    hole on its own rail. The whole-station phase lands each closing cross at
    an opposite-rail opening's position instead: 0.225 mm, dead midway, from
    the nearest own-rail hole."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    extra = int(machine.BORDER_CLOSURE_OVERLAP_MM / (machine.BORDER_DENSITY_MM / 2))
    assert extra >= 4, "fixture too small to exercise the closure"
    opening, closing = pts[:len(pts) - extra], pts[len(pts) - extra:]
    for gi in range(len(pts) - extra, len(pts)):
        c = pts[gi]
        same_rail = [p for j, p in enumerate(opening) if j % 2 == gi % 2]
        dmin = min(math.dist(c, p) for p in same_rail)
        assert dmin >= 0.2, \
            f"closing penetration {gi} lands {dmin:.3f} mm from an own-rail hole"


def test_border_intent_survives_a_redigitize():
    """Regression, from adversarial review: config.py promises the per-shape
    override 'rides the existing match_shape_ids carry-forward', but the match
    copied only the id and stage 4 rebuilds meta each generation — so a
    review-screen border decision silently reverted on every re-digitize."""
    from digitizer_core.regions import Region, match_shape_ids

    def region(sid, dx=0.0, **meta):
        poly = Polygon([(dx, 0), (10 + dx, 0), (10 + dx, 4), (dx, 4)])
        return Region(shape_id=sid, polygon=poly, thread_index=0,
                      thread_number="1", area_mm2=poly.area,
                      meta={"layer": 0, **meta})

    prev = [region("S_kept", border=False)]
    cur = [region("S_new", dx=0.3)]          # same art, nudged a hair
    match_shape_ids(prev, cur)
    assert cur[0].shape_id == "S_kept"
    assert cur[0].meta.get("border") is False, \
        "the operator's border decision must ride the id carry-forward"
    assert cur[0].meta["layer"] == 0, "pipeline facts stay the new generation's"


def test_corner_rounding_never_bites_deeper_than_half_a_column():
    """Regression, from adversarial review: the uncapped relaxation's fixed
    point on a spike-sharp star tip sat 1.85 mm inside it (its docstring
    claimed 0.66) — the outline visibly cut every corner off while the fill
    reached the true apex. Capped, a tip retreats at most about half a border
    width plus one sampling step, which stays inside the column's own thread."""
    from digitizer_core.stage6_border import round_inward

    for size in (24.0, 12.0):
        half = size / 2
        tips = []
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            rad = half if i % 2 == 0 else size / 5
            pts.append((rad * math.cos(ang), rad * math.sin(ang)))
            if i % 2 == 0:
                tips.append(pts[-1])
        star = Polygon(pts)
        rounded = round_inward(star, machine.BORDER_CORNER_RADIUS_MM,
                               machine.BORDER_DENSITY_MM / 2)
        for t in tips:
            bite = Point(t).distance(rounded)
            assert bite <= machine.BORDER_WIDTH_MM / 2 + 0.15, \
                f"{size} mm star tip bitten {bite:.2f} mm"


# --- The seam-sharing fix (was detect-and-warn only, PR #67; now the real ----
# --- fix — stage7_sequence._yield_frontage, sew-order tie-break)          ---

_SEAM_FABRIC = fabric_for_garment("left_chest")  # pique knit, 0.3 mm pull comp
_SEAM_TOL_MM = 0.05  # well inside a hair-width of the true seam line


def _seam_bar(x0: float, x1: float, layer: int, thread: int, name: str,
             border) -> Region:
    # Forced to "fill", same reasoning as test_chaining's fixtures: "auto"
    # would let the classifier decide satin vs fill per rectangle aspect
    # ratio, which has nothing to do with what this test measures.
    poly = Polygon([(x0, 0), (x1, 0), (x1, 10), (x0, 10)])
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=f"{1000 + thread}", area_mm2=poly.area,
                  meta={"layer": layer, "tier": "fill", "border": border})


def _seam_plan(regions):
    conf = PipelineConfig()
    planned, _ = resolve_overlaps(regions, _SEAM_FABRIC, conf)
    return sequence(planned, _SEAM_FABRIC, conf)


def _border_points(blocks, shape_id, kinds=("border",)):
    return [p for block in blocks for r in block.runs
            if r.kind in kinds and r.shape_id == shape_id for p in r.points]


def test_seam_sharing_is_resolved_automatically_not_just_warned():
    """Two different-colour rectangles sharing the edge x=10, both bordered —
    the exact coincidence `stage6_border`'s KNOWN LIMITATION describes, and
    the fixture PR #67's detect-only warning shipped with. This is the real
    fix: measured on the actual stitch penetrations, not on whether a warning
    stopped firing.

    Sew order is layer 0 (Sleft) then layer 1 (Sright), so Sleft's border
    commits to the seam first and `_yield_frontage` makes Sright retreat off
    it before tracing its own circuit.
    """
    regions = [_seam_bar(0, 10, 0, 0, "Sleft", True),
              _seam_bar(10, 20, 1, 1, "Sright", True)]

    # BEFORE: what `border_runs` used to receive with no seam awareness at
    # all — both shapes' own, un-suppressed visible geometry. Measured: 13
    # penetrations apiece sit on the x=10 line (the outer rail's stations
    # over the 10 mm shared run) — the double-thick bar, present on both
    # sides, is real on this fixture before anything downstream touches it.
    conf = PipelineConfig()
    planned, _ = resolve_overlaps(regions, _SEAM_FABRIC, conf)
    raw_by_id = {p.shape_id: p.visible_geom for p in planned}
    raw_left, _ = border_runs(raw_by_id["Sleft"], "Sleft", entry=None, trim_at_mm=3.0)
    raw_right, _ = border_runs(raw_by_id["Sright"], "Sright", entry=None, trim_at_mm=3.0)
    raw_left_seam = [pt for r in raw_left if r.kind == "border"
                     for pt in r.points if abs(pt[0] - 10.0) < _SEAM_TOL_MM]
    raw_right_seam = [pt for r in raw_right if r.kind == "border"
                      for pt in r.points if abs(pt[0] - 10.0) < _SEAM_TOL_MM]
    assert len(raw_left_seam) >= 10 and len(raw_right_seam) >= 10, \
        "fixture sanity: both raw circuits really do ride the seam"

    # AFTER: run the real pipeline. The warning is gone — the pair resolved,
    # it was not just silenced — and Sright's actual points have moved off
    # the line while Sleft's have not.
    blocks, warnings = sequence(planned, _SEAM_FABRIC, conf)
    assert not [w for w in warnings if w["code"] == BORDER_SEAM_SHARED], \
        "a resolvable pair must not still be reported as a manual-fix case"

    left_pts = _border_points(blocks, "Sleft")
    right_pts = _border_points(blocks, "Sright")
    assert left_pts and right_pts, "both shapes must still get a real border"

    left_seam = [p for p in left_pts if abs(p[0] - 10.0) < _SEAM_TOL_MM]
    right_seam = [p for p in right_pts if abs(p[0] - 10.0) < _SEAM_TOL_MM]
    assert len(left_seam) >= len(raw_left_seam), \
        "Sleft sewed first and must keep full density on the seam it owns"
    assert len(right_seam) == 0, \
        (f"Sright (sewed second) still has {len(right_seam)} penetrations "
         "on the shared seam — the double bar was not actually removed")

    # And Sright's circuit is still a REAL border a few mm off the line, not
    # a shape that quietly lost its outline to get here.
    assert min(p[0] for p in right_pts) > 10.0 + machine.BORDER_WIDTH_MM


def test_border_seam_shared_does_not_fire_without_abutment_or_border():
    """Negative case, two ways: a real gap between the shapes, and the seam
    intact but border turned off. Neither is the defect the fix (or its
    warning) exists for, so neither may fire it or change anything."""
    gap = [_seam_bar(0, 10, 0, 0, "Sleft", True),
          _seam_bar(16, 26, 1, 1, "Sright", True)]   # 6 mm gap, not abutting
    _blocks, gap_warnings = _seam_plan(gap)
    assert not [w for w in gap_warnings if w["code"] == BORDER_SEAM_SHARED]

    off = [_seam_bar(0, 10, 0, 0, "Sleft", False),
          _seam_bar(10, 20, 1, 1, "Sright", False)]  # abutting, border off
    _blocks, off_warnings = _seam_plan(off)
    assert not [w for w in off_warnings if w["code"] == BORDER_SEAM_SHARED]


def test_border_seam_shared_still_fires_when_a_shape_is_hemmed_in_on_every_side():
    """The residual case the automatic fix cannot resolve: a shape whose
    ENTIRE frontage is seam, with nowhere to retreat to.

    A 2 x 15 mm slot cut clean through a much bigger already-bordered shape,
    later-sewn, so `_yield_frontage` has to pull its border in from all four
    sides at once — and a slot only 2 mm wide cannot survive retreating
    ~1.6 mm from both long edges simultaneously. It falls back to its own
    unsuppressed geometry (a real border beats none) and the pair is named
    here instead, exactly like PR #67's original warning did for every case.
    """
    W, L = 2.0, 15.0
    cx, cy = 20.0, 20.0
    hole = [(cx - W / 2, cy - L / 2), (cx + W / 2, cy - L / 2),
            (cx + W / 2, cy + L / 2), (cx - W / 2, cy + L / 2)]
    big_poly = Polygon([(0, 0), (40, 0), (40, 40), (0, 40)], [hole])
    slot_poly = Polygon(hole)

    # Sanity: the slot really does hold a real border on its own, unsuppressed.
    _runs, raw_report = border_runs(slot_poly, "Slot", entry=None, trim_at_mm=3.0)
    assert not raw_report["empty"], "fixture sanity: the slot must sew something raw"

    big = Region(shape_id="Big", polygon=big_poly, thread_index=0, thread_number="1000",
                area_mm2=big_poly.area, meta={"layer": 0, "tier": "fill", "border": True})
    slot = Region(shape_id="Slot", polygon=slot_poly, thread_index=1, thread_number="1001",
                 area_mm2=slot_poly.area, meta={"layer": 1, "tier": "fill", "border": True})

    _blocks, warnings = _seam_plan([big, slot])
    hits = [w for w in warnings if w["code"] == BORDER_SEAM_SHARED]
    assert len(hits) == 1, f"expected one BORDER_SEAM_SHARED finding, got {warnings}"
    pair = {tuple(sorted(p)) for p in hits[0]["pairs"]}
    assert pair == {("Big", "Slot")}

    # And the slot still sewed something (the fallback, not a dropped shape).
    slot_pts = _border_points(_blocks, "Slot", kinds=("border", "bean"))
    assert slot_pts, "the fallback must still sew a real outline, not nothing"


# --- _yield_frontage and _border_seam_warning, in isolation --------------

def test_yield_frontage_insets_the_later_shapes_circuit_off_the_seam():
    from digitizer_core.stage7_sequence import _yield_frontage

    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    b = Polygon([(10, 0), (20, 0), (20, 10), (10, 10)])
    width = machine.BORDER_WIDTH_MM
    out, unresolved = _yield_frontage(b, {"A": a}, width, 2.0 * width)

    assert unresolved == []
    # Retreated well clear of the shared edge...
    assert out.bounds[0] > 10.0 + width
    # ...but the far edge, which shares no seam with anything, is untouched.
    assert out.bounds[2] == pytest.approx(20.0)


def test_yield_frontage_ignores_shapes_with_no_shared_edge():
    from digitizer_core.stage7_sequence import _yield_frontage

    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    b = Polygon([(16, 0), (26, 0), (26, 10), (16, 10)])  # 6 mm gap
    width = machine.BORDER_WIDTH_MM
    out, unresolved = _yield_frontage(b, {"A": a}, width, 2.0 * width)
    assert unresolved == []
    assert out.equals(b)


def test_yield_frontage_falls_back_when_nothing_survives_the_retreat():
    from digitizer_core.stage7_sequence import _yield_frontage

    a = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    # A sliver whose entire width is inside the retreat distance.
    b = Polygon([(10, 0), (10.3, 0), (10.3, 10), (10, 10)])
    width = machine.BORDER_WIDTH_MM
    out, unresolved = _yield_frontage(b, {"A": a}, width, 2.0 * width)

    assert out.equals(b), "must fall back to the untouched geometry, not vanish"
    assert unresolved == [("A", pytest.approx(10.0, abs=0.1))]


def test_border_seam_warning_names_only_unresolved_pairs():
    from digitizer_core.stage7_sequence import _border_seam_warning

    assert _border_seam_warning([]) is None

    w = _border_seam_warning([("Sa", "Sb", 10.0), ("Sc", "Sd", 5.0)])
    assert w["code"] == BORDER_SEAM_SHARED
    assert w["count"] == 2
    assert {tuple(p) for p in w["pairs"]} == {("Sa", "Sb"), ("Sc", "Sd")}
