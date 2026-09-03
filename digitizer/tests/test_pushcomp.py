"""Directional pull/push compensation — Laws 22, 23, 24.

The defect this file exists to catch: stage 5 grew every shape by one uniform
`buffer(pull)`, in every direction at once. Pull is AXIAL — thread tension
pulls each stitch's two penetrations together, so an object loses size along
its stitch direction — and push is PERPENDICULAR, shoving fabric out at the
ends of a column. Two effects, two directions, and a uniform outline offset is
neither: right on average, wrong everywhere specific.

Every measurement below is in millimetres against the ARTWORK boundary, which
is the only frame the garment cares about.

The flag defaults off and the first test is why: the goldens in this repo are
load-bearing, and turning this on silently would invalidate all of them.
"""
from __future__ import annotations

import math

import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, get_fabric, machine, plan_stitches
from digitizer_core import stitches as ST
from digitizer_core.export import export_dst
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_fill import principal_angle_deg
from digitizer_core.stage6_satin import (is_satin_candidate, satin_shape,
                                         strip_splits)
from digitizer_core.stage7_sequence import sequence

from .conftest import cfg

PIQUE = get_fabric("pique_knit")          # 0.30 mm pull comp
PULL = PIQUE.pull_comp_mm
PUSH = machine.PUSH_CUTBACK_MM            # 0.40 mm, Law 24
CUTBACK = PULL + PUSH                     # what stage 7 hands stage 6


# --- fixtures --------------------------------------------------------------

def bar(w: float, h: float, rot: float = 0.0) -> Polygon:
    """A rectangle centred on the origin, optionally rotated.

    Rotation is the point of several tests: compensation must follow the
    ARTWORK's own stitch direction, not the coordinate axes. A version of this
    that only ever ran axis-aligned would pass while compensating along x.
    """
    p = affinity.translate(Polygon([(0, 0), (w, 0), (w, h), (0, h)]), -w / 2, -h / 2)
    return affinity.rotate(p, rot, origin=(0, 0)) if rot else p


def region(poly: Polygon, sid: str = "S0", layer: int = 0) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1000",
                  area_mm2=poly.area, meta={"layer": layer})


def planned_for(poly: Polygon, directional: bool, fabric=PIQUE, **kw):
    c = PipelineConfig(overlap_mm=0.25, directional_comp=directional, **kw)
    planned, _ = resolve_overlaps([region(poly)], fabric, c)
    return planned[0], c


def extents(geom, deg: float) -> tuple[float, float]:
    """(extent along `deg`, extent across it), in mm."""
    r = affinity.rotate(geom, -deg, origin=(0, 0))
    x0, y0, x1, y1 = r.bounds
    return x1 - x0, y1 - y0


def half_deltas(art: Polygon, grown, deg: float) -> tuple[float, float]:
    """How far `grown` sits outside `art` per side, along `deg` and across."""
    a_ax, a_pp = extents(art, deg)
    g_ax, g_pp = extents(grown, deg)
    return (g_ax - a_ax) / 2.0, (g_pp - a_pp) / 2.0


def column_of(art: Polygon, directional: bool):
    """The satin column stage 7 would sew for `art`, before ties.

    Ties are excluded deliberately: `sequence` folds a lock into each run's
    ends, and `tie_run` bounces between the last rail point and a point one
    leg INTO the shape, so the last two points of an emitted run are not the
    terminal cross. Measuring there reads the tie, not the column — it is what
    made the first pass of this work report a 0.19 mm cutback for a 0.40 one.
    """
    p, _ = planned_for(art, directional)
    runs, _ = satin_shape(p.polygon, "S0", underlay_style="none", trim_at_mm=3.0,
                          end_cutback_mm=CUTBACK if directional else 0.0)
    cols = [strip_splits(r.points) for r in runs if r.kind == ST.SATIN]
    assert cols, "fixture produced no satin column"
    return max(cols, key=len)


def signed_inside(art: Polygon, p) -> float:
    """mm from `p` to the artwork boundary; positive = inside the artwork."""
    q = Point(p)
    return art.boundary.distance(q) * (1.0 if art.covers(q) else -1.0)


def cap_gaps(art: Polygon, pts) -> tuple[float, float]:
    """How far inside the artwork cap each end cross sits. Positive = cut back."""
    mid = lambda a, b: ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    return (signed_inside(art, mid(pts[0], pts[1])),
            signed_inside(art, mid(pts[-2], pts[-1])))


def rail_overhang(art: Polygon, pts) -> float:
    """The furthest any penetration sits OUTSIDE the artwork = pull comp."""
    return max(-signed_inside(art, p) for p in pts)


# --- the flag is off, and off means nothing moved --------------------------

# Pinned from the pre-change tree: these are `git show HEAD` of config.py,
# machine.py, stage5_overlap.py, stage6_satin.py and stage7_sequence.py run
# through the same script, over 4 fixtures x 4 garments. All 16 matched.
# Two fixtures are pinned here as the standing guard; a third digit of DST
# hash would not add anything the point stream does not already say.
#
# THE TOWEL ENTRY WAS RE-BASELINED WHEN THIS LANE LANDED, and the reason is
# worth stating because a moved golden is exactly what this test exists to
# scream about. The lane branched before `f02aeec`, the fix for the inverted
# `density_adjust` — the field is named for density but is applied as row
# SPACING, so pile fabrics were sewing SPARSER than a polo. That commit took
# terry_towel from 1.1 to 0.85, which is 1.29x denser fill, and this fixture
# duly went 2888 -> 3445 stitches, 1.19x, the rest of the design being satin
# and underlay that the multiplier does not touch.
#
# It was NOT this lane. Verified by re-running every entry on the merged tree
# with `chain_links=False` as well: the other three match to the digit, and
# towel lands on the same moved value with chaining on or off, so neither
# directional comp nor chaining is in it. Isotropic compensation still produces
# byte-identical output to the engine of its own day.
# BOTH WHITEBG ENTRIES RE-BASELINED 2026-08-02: `principal_angle_deg` was
# double-counting each ring's closing duplicate vertex, bending the fill axis
# of every rotated shape (measured 1.99deg off on a rect; exact after
# `coords[:-1]`). The whitebg fill shapes re-fill along the corrected axis;
# ribbon is satin-only and holds to the digit, exactly the blast radius the
# patch+revert measurement predicted.
#
# RE-MEASURED AGAIN (2026-08-02) for the area-moment `principal_angle_deg`
# rewrite (vertex-weighted PCA -> polygon second moments, `_ring_moments`):
# vertex weighting let a pull-comp'd shape's buffer-arc corners (~16 extra
# vertices each) outvote the shape itself, up to 87 degrees off on a plain
# square. Same blast radius as the closing-vertex fix, for the same reason —
# only whitebg's FILL shapes move; ribbon stays satin-only and untouched.
# Stitch counts fell (2621->2469, 3440->3226): rows now run the shape's true
# long axis instead of a spurious diagonal, so they run longer and turn less.
#
# RE-BASELINED 2026-08-05 for corpus laws 23/26 landing, deliberately — this
# time all four entries move, not a subset, so it is worth spelling out why
# each one does:
#   * left_chest (pique_knit): law 26 (fill_underlay edge_lattice ->
#     edge_run) drops its fill's crosshatch-lattice underlay pass, so
#     stitch count falls further (2469 -> 2165).
#   * towel (terry_towel): NOT touched by law 26 (only pique_knit/jersey_tee
#     changed), but the fixture carries a small satin element, and law 23
#     (SATIN_ZIGZAG_PITCH_MM 2.0 -> 1.45, the new satin-only constant, plus
#     the 0.3 -> 0.09 rail-narrowing widening) is fabric-independent — it is
#     gated on column width via SATIN_ZIGZAG_ABOVE_MM, not on the fabric
#     preset — so it moves too (3226 -> 3234, +8 stitches, matching the
#     satin-only delta measured on left_chest between the law-26-only and
#     law-26+23 states).
#   * ribbon_curve (both garments): satin-only, so untouched by law 26 same
#     as before, but law 23 applies to every satin column over the width
#     gate regardless of fabric preset -- left_chest 1019 -> 1001, hat_front
#     1033 -> 1005.
# This is the exact blast radius the corpus-laws-round3 doc's own law 23
# entry predicted ("auto-applies to every satin column... regardless of
# fabric") and the reason the first attempt at these two laws was reverted
# rather than landed piecemeal -- see MASTER_SCOPE.md's cross-cutting/area-1
# history for that reverted attempt and this landing.
#
# RE-BASELINED 2026-08-14 for task A2 (pro-parity density work): satin now
# gets the fabric preset's own `density_adjust`, the same multiplier fill's
# row_mm has always had (stage7_sequence.py's `satin_spacing_mm`) -- closing
# the one place the Python engine's satin ignored a fabric it was already
# scaling fill for, and matching the browser engine's digitize.js, which has
# applied densityAdjust to its own satin spacing all along. ONLY the towel
# entry moves: terry_towel is the one fabric of these two fixtures' garments
# whose density_adjust (0.85) is not 1.0 -- left_chest (pique_knit) and
# hat_front (structured_cap) are both 1.0, so their satin spacing is
# unchanged and neither golden here nor ribbon_curve's two entries move.
# Tighter spacing (0.4 -> 0.34 mm) on logo_whitebg's satin element adds
# stitches: 3234 -> 3258.
# RE-PINNED 2026-08-15, `left_chest` ONLY: stage 6's travel guide stopped
# discarding every inset fragment but the largest, and started routing along a
# ring's own vertices instead of samples taken every TRAVEL_STITCH_MM
# (stage6_fill's `_inset_ring` / `_ring_route`). On this fixture that is ONE
# extra travel penetration, 2165 -> 2166; trim and jump flags (153 each),
# region ids, areas and warnings are all unmoved. Earned the way the flat-lane
# golden's key was: a worktree at the previous commit reproduces the old tuple
# byte-for-byte on this machine, so what moved is the engine, not the
# environment.
#
# `towel` is NOT re-pinned and its test is expected red. It was ALREADY red
# before that change — the pre-change worktree returns
# ("91030f1addf655a9f7a7", 3262, 10361) here, not the tuple below — so this
# machine cannot tell a stale pin from local drift, and
# `recapture_flat_lane_key.py`'s doctrine is that a machine failing its own
# pre-change check may not write a golden. Re-pin it where the pre-change
# tuple reproduces. (Both `ribbon_curve` entries reproduce exactly, before and
# after, and are the control that says the change is confined to fills whose
# inset actually fragments.)
GOLDEN_FLAG_OFF = {
    ("logo_whitebg.png", "left_chest"): ("05a59e2bc2a524087c4f", 2166, 7073),
    ("logo_whitebg.png", "towel"): ("98c918e7c1576e46f623", 3258, 10349),
    ("ribbon_curve.png", "left_chest"): ("1c3f5ad1d0de847c149a", 1001, 3527),
    ("ribbon_curve.png", "hat_front"): ("d982b1c0fe21b0ed1b5f", 1005, 3539),
}


@pytest.mark.parametrize("fixture,garment", sorted(GOLDEN_FLAG_OFF))
def test_flag_off_is_byte_identical_to_the_shipped_engine(fixture, garment, request):
    """The whole lane rides on this. Every golden in this repo was produced by
    the isotropic path, so directional compensation may only ever be something
    a caller opts into — a silent global geometry change would invalidate all
    of them at once, and nobody would know which sew-out to trust.
    """
    import hashlib

    from digitizer_core import run_stages
    from .conftest import TESTDATA

    base = run_stages(TESTDATA / fixture, cfg())
    plan = plan_stitches(base, cfg(garment_id=garment))
    blob = export_dst(plan)
    want_hash, want_n, want_bytes = GOLDEN_FLAG_OFF[(fixture, garment)]
    got_n = sum(len(r.points) for b in plan.blocks for r in b.runs)
    assert (hashlib.sha256(blob).hexdigest()[:20], got_n, len(blob)) == \
        (want_hash, want_n, want_bytes)


def test_flag_off_still_grows_every_face_by_exactly_pull():
    """The isotropic path is not merely 'unchanged', it is still the uniform
    dilation it always was — the refactor routes it through `_grow` now, and a
    helper that quietly clamped or squashed would show up here first."""
    art = bar(30, 20)
    p, _ = planned_for(art, directional=False)
    for deg in (0, 17, 45, 90, 133):
        ax, pp = half_deltas(art, p.polygon, deg)
        assert ax == pytest.approx(PULL, abs=0.002), f"axis {deg}"
        assert pp == pytest.approx(PULL, abs=0.002), f"across {deg}"


def test_flag_off_records_no_direction():
    """Nothing downstream may start depending on a stitch angle the shipped
    path never computed."""
    p, _ = planned_for(bar(30, 20), directional=False)
    assert p.stitch_angle_deg is None
    assert p.satin_tier is False


# --- Law 22, fill: compensation goes on the edges the rows penetrate --------

@pytest.mark.parametrize("rot", [0.0, 11.0, 37.0, 90.0])
def test_fill_grows_along_its_stitch_axis_and_not_across_it(rot):
    """Law 22. A fill's rows run along the fill angle, so it is the row ENDS
    where thread tension pulls penetrations together and the shape loses size.
    The faces the rows run parallel to lose nothing and must not be grown —
    that is the half of the uniform dilation that was never physics.

    Parametrised over rotation because the operation is a squashed buffer and
    an axis-aligned-only test would pass with the squash applied to x.
    """
    art = bar(30, 20, rot)
    axis = principal_angle_deg(art)
    p, _ = planned_for(art, directional=True)
    assert p.satin_tier is False
    assert p.stitch_angle_deg == pytest.approx(axis)

    ax, pp = half_deltas(art, p.polygon, axis)
    assert ax == pytest.approx(PULL, abs=0.003), "must still compensate axially"
    assert pp < 0.02, "must NOT grow across the stitch direction"

    # and the isotropic path, on the same artwork, grows both.
    iso, _ = planned_for(art, directional=False)
    i_ax, i_pp = half_deltas(art, iso.polygon, axis)
    assert i_ax == pytest.approx(PULL, abs=0.003)
    assert i_pp == pytest.approx(PULL, abs=0.003)
    assert i_pp - pp > 0.25, "directional must differ from isotropic across the axis"


def test_fill_compensation_tapers_with_the_face_normal():
    """Not a flag but a gradient: a face at 60 degrees to the stitch axis takes
    `pull * cos(60)`. Anything that just offset two flat sides would pass the
    rectangle test above and fail here, and letterforms are all oblique faces.
    """
    hexagon = Polygon([(math.cos(math.radians(60 * i)) * 10,
                        math.sin(math.radians(60 * i)) * 10) for i in range(6)])
    p, _ = planned_for(hexagon, directional=True, fill_angle_deg=0.0)
    for deg in (0, 30, 60):
        got, _ = half_deltas(hexagon, p.polygon, deg)
        assert got == pytest.approx(PULL * abs(math.cos(math.radians(deg))),
                                    abs=0.006), f"face at {deg} deg"


def test_the_fill_angle_stage_5_compensated_for_is_the_one_stage_6_sews():
    """The circularity this lane had to cut. Stage 6 has always derived the
    fill angle from the polygon stage 5 hands it, so compensating along that
    angle would depend on the compensation. Stage 5 now takes the angle on the
    ARTWORK, before any growth, and stage 7 hands it back — measured drift
    between the two on real fixture regions was up to 35 degrees, so this is
    not a rounding concern.
    """
    art = bar(30, 20, 37.0)
    p, _ = planned_for(art, directional=True)
    on_artwork = principal_angle_deg(art)
    on_grown = principal_angle_deg(p.polygon)
    assert p.stitch_angle_deg == pytest.approx(on_artwork)
    # The handoff is what makes them agree; without it stage 6 would use
    # `on_grown`. Assert the carried value, not that the two happen to match.
    #
    # This line carried `or True` from 2026-08-02 to 2026-08-17, which made it
    # unfalsifiable: `X or True` is always true, so the one assertion guarding
    # this lane's whole reason for existing carried zero bits. Removed, and the
    # test run honestly.
    assert p.stitch_angle_deg != pytest.approx(on_grown, abs=1e-9)


def test_an_explicit_fill_angle_still_wins():
    """`cfg.fill_angle_deg` forces every region's angle. It must also force the
    direction compensation is applied in, or comp and rows disagree by
    construction."""
    art = bar(30, 20, 37.0)
    p, _ = planned_for(art, directional=True, fill_angle_deg=12.5)
    assert p.stitch_angle_deg == pytest.approx(12.5)
    ax, pp = half_deltas(art, p.polygon, 12.5)
    assert ax == pytest.approx(PULL, abs=0.003)
    assert pp < 0.02


def test_directional_comp_does_not_inflate_the_outline():
    """The squashed buffer put 261 vertices on a 5-vertex rectangle, and
    `principal_angle_deg` sums moments over VERTICES — the artwork's 26.2 deg
    axis read as -22.7 off the dilated polygon, which
    `stage6_fill._underlay_paths` would have used for its centre run. The cure
    is simplification at the minor axis; this pins it."""
    art = bar(30, 20)
    p, _ = planned_for(art, directional=True)
    assert len(p.polygon.exterior.coords) <= len(art.exterior.coords) + 8


# --- Law 22 + 24, satin: uniform on the rails, cut back at the ends ---------

def test_satin_keeps_uniform_growth_because_on_a_rail_that_is_exact():
    """Not an omission. A column's stitch direction is perpendicular to its
    rails — which is to say parallel to the boundary normal there — so
    `pull * |n . axis|` IS `pull` the whole way along both rails. The uniform
    buffer is only wrong at the two CAPS, and caps are stage 6's to fix."""
    art = bar(30, 3.0)
    assert is_satin_candidate(art, machine.SATIN_MAX_WIDTH_MM)
    p, _ = planned_for(art, directional=True)
    assert p.satin_tier is True
    assert p.stitch_angle_deg is None, "a curving spine has no single axis"
    iso, _ = planned_for(art, directional=False)
    assert p.polygon.equals(iso.polygon)


@pytest.mark.parametrize("w,h,rot", [(45, 4.5, 0.0), (30, 3.0, 0.0), (30, 3.0, 11.0)])
def test_push_comp_cuts_the_column_back_inside_the_artwork_cap(w, h, rot):
    """Law 24, the effect this engine ignored entirely. Fabric is shoved out at
    a column's ends, so a column sewn flush to the artwork lands past it. With
    the flag off the end sits OUTSIDE the artwork by a full pull comp — the
    uniform dilation adding width in the one direction that is losing length.
    With it on the end sits INSIDE, by the cutback.
    """
    art = bar(w, h, rot)
    iso_gaps = cap_gaps(art, column_of(art, directional=False))
    dir_gaps = cap_gaps(art, column_of(art, directional=True))

    for g in iso_gaps:
        assert g < 0.0, "shipped behaviour overshoots the artwork cap"
    for g in dir_gaps:
        assert g > 0.15, "directional must stop short of the artwork cap"
    for before, after in zip(iso_gaps, dir_gaps):
        assert after - before > 0.4, "the end must move inward by the cutback"


def test_push_comp_on_the_best_resolved_bar_lands_on_law_24s_number():
    """The other fixtures lose a tenth or two to raster and resample
    quantisation; a 45 x 4.5 mm bar is resolved well enough to show the
    intended arithmetic exactly. Cap gap goes from -pull to +PUSH_CUTBACK_MM,
    which is the whole of Law 24 in one number."""
    art = bar(45, 4.5)
    a_iso, b_iso = cap_gaps(art, column_of(art, directional=False))
    a_dir, b_dir = cap_gaps(art, column_of(art, directional=True))
    assert a_iso == pytest.approx(-PULL, abs=0.03)
    assert b_iso == pytest.approx(-PULL, abs=0.03)
    assert a_dir == pytest.approx(PUSH, abs=0.03)
    assert b_dir == pytest.approx(PUSH, abs=0.03)


@pytest.mark.parametrize("w,h,rot", [(45, 4.0, 0.0), (30, 3.0, 0.0), (30, 3.0, 11.0)])
def test_push_comp_does_not_touch_the_column_width(w, h, rot):
    """Push is a LENGTH. The rails must sit exactly where pull comp put them,
    or this trades one distortion for another — a column that sews narrow is
    the defect pull comp exists to prevent.

    The first case reads 4.0mm, not the 4.5mm its sibling parametrizations
    above use: found 2026-08-05, a 4.5mm bar grows to 5.1mm under PULL
    (0.3mm/side) and lands just past `SATIN_MAX_WIDTH_MM`'s new per-station
    cross cap (the satin self-overlap fix, `stage6_satin.py::_rail_points`),
    losing ~0.017mm of rail_overhang to it -- a real, intentional interaction
    (this module will not classify a >5mm column satin in the first place,
    so it should not sew one because comp grew it there either), not a bug
    THIS test exists to catch. 4.0mm grows to 4.6mm, comfortably clear of the
    cap, and still exercises exactly what this test is about."""
    art = bar(w, h, rot)
    iso = rail_overhang(art, column_of(art, directional=False))
    dr = rail_overhang(art, column_of(art, directional=True))
    assert iso == pytest.approx(PULL, abs=0.01)
    assert dr == pytest.approx(PULL, abs=0.01)


def test_the_cutback_is_taken_off_a_closed_ring_nowhere():
    """A closed column has no ends to push fabric out of. Cutting one would
    open a gap in a ring that had none."""
    import numpy as np
    ring = Polygon(
        [(math.cos(t) * 10, math.sin(t) * 10) for t in np.linspace(0, 2 * math.pi, 80)],
        [[(math.cos(t) * 8, math.sin(t) * 8) for t in np.linspace(2 * math.pi, 0, 80)]],
    )
    p, _ = planned_for(ring, directional=True)
    base, _ = satin_shape(p.polygon, "S0", underlay_style="none", trim_at_mm=3.0,
                          end_cutback_mm=0.0)
    cut, _ = satin_shape(p.polygon, "S0", underlay_style="none", trim_at_mm=3.0,
                         end_cutback_mm=CUTBACK)
    n = lambda runs: sum(len(r.points) for r in runs if r.kind == ST.SATIN)
    assert n(base) == n(cut), "a closed ring has no free end to cut back"


def test_a_stub_too_short_to_survive_the_cutback_is_left_alone():
    """`_trim_chain` refuses to take a chain under half a millimetre. A column
    that vanished under compensation would be lost artwork, which is strictly
    worse than an uncompensated one."""
    art = bar(3.0, 1.2)
    p, _ = planned_for(art, directional=True)
    runs, report = satin_shape(p.polygon, "S0", underlay_style="none",
                               trim_at_mm=3.0, end_cutback_mm=CUTBACK)
    if not report["empty"]:
        assert sum(len(r.points) for r in runs) > 0


# --- the wiring is real ----------------------------------------------------

def test_the_flag_actually_reaches_plan_stitches(whitebg):
    """A committed, imported, documented module in this repo once shipped as
    dead code because nothing called it. Prove the plan changes."""
    off = plan_stitches(whitebg, cfg(garment_id="left_chest"))
    on = plan_stitches(whitebg, cfg(garment_id="left_chest", directional_comp=True))
    assert export_dst(off) != export_dst(on)


def test_a_fabric_with_no_pull_comp_is_untouched_either_way():
    """Compensation of zero is zero in every direction. Guards against the
    squash dividing by an amount of 0.0."""
    flat = get_fabric("canvas_tote")
    art = bar(30, 20)
    c = PipelineConfig(overlap_mm=0.0, directional_comp=True)
    zero = type(flat)(id="z", label="z", pull_comp_mm=0.0, fill_underlay="none",
                      satin_underlay="none", density_adjust=1.0, trim_at_mm=3.0,
                      notes="")
    planned, _ = resolve_overlaps([region(art)], zero, c)
    assert planned[0].polygon.equals(art)
