"""Stage 6 contour fill — rings that follow the silhouette.

Contour fill is the only one of the four techniques beyond tatami that
generates geometry the existing engine cannot, and everything it adds is a new
way to break an invariant tatami got for free. Its rows are curved, so a stitch
can leave the shape with both endpoints inside it (law 42). Its rows sit one
spacing apart in every direction, so stepping between them is a 0.40 mm stitch
against a 1.0 mm floor (law 44). Its rings shrink to nothing, so a shape can
silently end up with a bare patch in the middle.

These tests hold it to those three and to the promise the flag makes: with
`fill_technique="tatami"` — the default — the output is byte-for-byte what it
was before the module existed.

Every number asserted here was measured on the fixtures below before it was
written down; the comments say which draft failed it and by how much.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, machine, plan_stitches
from digitizer_core.export import export_dst
from digitizer_core.stage6_contour import (_entry_arc, _ring_points, _step_count,
                                           contour_fill)
from digitizer_core.warnings_codes import CONTOUR_RING_UNREACHABLE
from tests.conftest import PLAN_CFG_KW, cfg


def _circle(r, cx=0.0, cy=0.0, n=192):
    return Polygon([(cx + r * math.cos(t), cy + r * math.sin(t))
                    for t in np.linspace(0, 2 * math.pi, n, endpoint=False)])


ANNULUS = _circle(15.0).difference(_circle(6.0))
CRESCENT = _circle(14.0).difference(_circle(12.0, cx=7.0))
BLOB = Polygon([((12.0 + 3.0 * math.sin(3 * t) + 1.2 * math.cos(5 * t)) * math.cos(t),
                 (12.0 + 3.0 * math.sin(3 * t) + 1.2 * math.cos(5 * t)) * math.sin(t))
                for t in np.linspace(0, 2 * math.pi, 200, endpoint=False)])
STAR = Polygon([((15.0 if i % 2 == 0 else 6.0) * math.cos(math.pi / 2 + i * math.pi / 5),
                 (15.0 if i % 2 == 0 else 6.0) * math.sin(math.pi / 2 + i * math.pi / 5))
                for i in range(10)])
# A letter "e" in spirit: a hole that runs out to the outline through a mouth,
# so the nesting genuinely changes between generations.
LETTER_E = (_circle(14.0)
            .difference(_circle(7.0, cy=3.0))
            .difference(Polygon([(0, -1), (20, -1), (20, 4), (0, 4)])))
DUMBBELL = (_circle(7.0, cx=-10.0).union(_circle(7.0, cx=10.0))
            .union(Polygon([(-10, -0.3), (10, -0.3), (10, 0.3), (-10, 0.3)])))

SHAPES = {"annulus": ANNULUS, "crescent": CRESCENT, "blob": BLOB, "star": STAR,
          "letter_e": LETTER_E, "dumbbell": DUMBBELL}


def _fill(poly, **kw):
    kw.setdefault("spacing_mm", machine.FILL_ROW_MM)
    kw.setdefault("stitch_mm", machine.FILL_STITCH_MM)
    kw.setdefault("underlay_style", "edge_lattice")
    kw.setdefault("trim_at_mm", machine.TRIM_AT_MM)
    return contour_fill(poly, "S1", **kw)


def _stitches(runs, kinds=("fill", "underlay")):
    """Every needle-down step of the named kinds, as (kind, a, b)."""
    for r in runs:
        if r.kind not in kinds:
            continue
        for a, b in zip(r.points, r.points[1:]):
            yield r.kind, a, b


# --- Law 44: the ring-to-ring step is a stitch, and it clears the floor ------

@pytest.mark.parametrize("name", sorted(SHAPES))
def test_ring_to_ring_step_clears_the_needle_floor(name):
    """Law 44, the trap no CAM paper covers.

    Rings sit one spacing apart — 0.40 mm — and milling and FDM have no minimum
    segment length, so every reference implementation of contour-offset
    toolpathing hands you a 0.40 mm hop between rings. Against `MIN_STITCH_MM`
    that is the needle landing in the hole it just made.

    `_entry_arc` solves for the diagonal instead of taking the nearest point, so
    this passes by construction and the assert is here to catch a regression.
    Measured across these six shapes: every crossing lands at exactly
    `CONTOUR_TRANSITION_MIN_MM` (1.200 mm), 1.2x the floor.
    """
    runs, report = _fill(SHAPES[name])
    assert report["transitions"] > 0, "a contour fill with no ring-to-ring step"
    assert report["min_transition_mm"] >= machine.MIN_STITCH_MM


def test_the_naive_ring_step_is_the_one_this_avoids():
    """The failure mode itself, so the fix is not just asserted but demonstrated.

    Two rings 0.40 mm apart: entering the second at its NEAREST point — what
    every reference implementation does — emits a 0.40 mm stitch. `_entry_arc`
    walks along the ring while it crosses and turns that into a diagonal.
    """
    inner, outer = LineString(_circle(10.0).exterior.coords), None
    outer = LineString(_circle(10.4).exterior.coords)
    anchor = (10.0, 0.0)                      # a point on the inner ring

    naive = outer.interpolate(outer.project(Point(anchor)))
    assert math.dist(anchor, (naive.x, naive.y)) < machine.MIN_STITCH_MM

    _arc, chord = _entry_arc(outer, anchor, machine.CONTOUR_TRANSITION_MIN_MM)
    assert chord >= machine.CONTOUR_TRANSITION_MIN_MM


def test_a_rings_own_chords_clear_the_floor():
    """`_step_count`: the needle floor outranks the curvature cap.

    The first draft used `ceil(total / cap)`, which always overshoots the count
    and therefore undershoots the chord — and the cap bottoms out at exactly
    `MIN_STITCH_MM`, so every tight ring came out under the floor. Measured on
    that draft: a 3.0 mm ring resampled to 0.675 mm chords, a 6.0 mm ring to
    0.829, a 10.5 mm ring to 1.033.
    """
    for total in (3.0, 3.5, 4.2, 6.0, 10.5, 20.0, 40.0, 94.0):
        n = _step_count(total, machine.MIN_STITCH_MM)
        assert n >= 1
        assert total / n >= machine.MIN_STITCH_MM - 1e-9, f"ring of {total} mm"


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_no_zero_length_stitches_anywhere(name):
    """The needle never lands twice in one hole.

    The first draft closed each ring by re-interpolating at `entry + n*step mod
    total`, which lands within a float ulp of the start but not on it, and then
    tested closure with `==`. The duplicate survived and rotated into the middle
    of the path: 17 stitches of 0.000 mm on the annulus alone.
    """
    runs, _report = _fill(SHAPES[name])
    steps = [math.dist(a, b) for _k, a, b in _stitches(runs)]
    assert steps
    assert min(steps) > machine.TINY_STITCH_MM


@pytest.mark.parametrize("name", sorted(SHAPES))
def test_sub_floor_stitches_are_counted_not_hidden(name):
    """Where laws 18 and 42 genuinely conflict, the count is honest.

    A penetration the containment clip put on a sharp notch can sit under the
    floor with nowhere legal to move: dropping it puts the chord back outside
    the shape. `_floor_pass` tries both neighbours and counts whatever survives.
    Measured: one such stitch on the star (0.575 mm), zero on the other five.
    """
    runs, report = _fill(SHAPES[name])
    under = sum(1 for _k, a, b in _stitches(runs)
                if math.dist(a, b) < machine.MIN_STITCH_MM - 1e-9)
    assert under == report["short_stitches"]
    total = sum(1 for _ in _stitches(runs))
    assert under <= 0.01 * total, "sub-floor stitches are an exception, not a tier"


# --- Law 42: a chord lies on the concave side -------------------------------

@pytest.mark.parametrize("name", sorted(SHAPES))
def test_every_stitch_stays_inside_the_shape(name):
    """Law 42, tested on the SEGMENT and not on its endpoints.

    Sagitta is about L^2/8R, so a chord bows to the concave side with both ends
    testing inside. Tatami's rows are straight and never had this; a containment
    check that looks at penetrations cannot see it at all. Measured on the first
    draft, which clipped points rather than chords: 0.476 mm outside the star,
    0.179 outside the blob, 0.181 outside a 2 mm S-bar.
    """
    poly = SHAPES[name]
    runs, _report = _fill(poly)
    outside = [(a, b) for _k, a, b in _stitches(runs)
               if not poly.covers(LineString([a, b]))]
    assert not outside, f"{len(outside)} stitches leave the shape"


def test_the_transition_chord_is_containment_tested_too():
    """Defect 3 of the 2026-08-02 pass, closed 2026-08-04. `_entry_arc`
    solves the ring-to-ring crossing for LENGTH only (law 44), so around a
    small hole its chord could leave the shape with both endpoints inside —
    the shipped containment test failed verbatim on a 15 mm disc with a
    0.3 mm hole (measured on the pre-fix engine: one underlay transition
    0.255 mm outside the shape). `_link` now containment-tests the crossing
    chord and BANKS the path when it escapes — a travel costs a needle-up,
    a stitch across a hole costs the artwork.

    The cited 0.45 mm neck fixture could not be reconstructed from its
    description (four neck geometries tried, none escapes even on the
    pre-fix engine); the hole fixture reproduces the defect exactly and is
    the regression pin.
    """
    poly = _circle(15.0).difference(_circle(0.3))
    runs, _report = _fill(poly)
    outside = [(a, b) for _k, a, b in _stitches(runs)
               if not poly.covers(LineString([a, b]))]
    assert not outside, f"{len(outside)} transition stitches leave the shape"


def test_containment_survives_a_reflex_notch():
    """The star's inner vertices are the case a per-ring curvature cap misses.

    One sharp notch does not move a ring's average radius, so the sagitta bound
    computed from the ring's perimeter says the chord is fine. It is not. The
    clip measures instead of predicting, and the report counts the repairs.
    """
    runs, report = _fill(STAR)
    assert report["clipped"] > 0, "the star's notches need clipping; nothing did"
    assert all(STAR.covers(LineString([a, b])) for _k, a, b in _stitches(runs))


# --- Holes ------------------------------------------------------------------

def test_a_hole_takes_no_penetrations():
    """Wilcom's Spiral Fill ignores holes entirely. Our floor is zero, asserted."""
    hole = _circle(6.0)
    runs, _report = _fill(ANNULUS)
    inside = [a for _k, a, _b in _stitches(runs, ("fill", "underlay", "travel"))
              if hole.buffer(-1e-9).covers(Point(a))]
    assert not inside, f"{len(inside)} penetrations landed in the hole"


def test_a_hole_wall_gets_its_own_rings():
    """An annulus is two ring families — the outline shrinking in and the hole
    wall growing out — and both have to be sewn. 22 rings across 11 generations
    at 0.40 mm through a 9 mm band."""
    runs, report = _fill(ANNULUS, underlay_style="none")
    assert report["rings"] == 22
    assert report["skipped_rings"] == 0


def test_the_annulus_sews_as_two_continuous_paths():
    """The regression that motivated the linker rewrite.

    The first draft walked the ring generations in index order, which reads as
    inner-to-outer and is not: each generation holds an outer ring and a hole
    wall on OPPOSITE sides of the band, so consecutive rings were 1-4 mm apart
    and every one of the 22 banked its own path — 22 paths and 17 travel bridges
    on the one shape contour fill exists to sew well. Nearest-unvisited walks
    each family in turn.
    """
    _runs, report = _fill(ANNULUS, underlay_style="none")
    assert report["paths"] == 2
    assert report["jumps"] == 0


def test_a_hole_that_reaches_the_outline_still_terminates():
    """The letter-"e" case: nesting changes mid-sequence, so the parent/child map
    cannot be cached across generations."""
    runs, report = _fill(LETTER_E)
    assert report["rings"] > 0
    assert runs


# --- Rings stay where rings belong ------------------------------------------

@pytest.mark.parametrize("name", sorted(SHAPES))
def test_rings_reach_the_middle_or_account_for_what_they_leave(name):
    """Contour fill's whole claim is even coverage, so the rings have to reach
    the middle — and where they stop short, the shortfall has to have been
    COUNTED rather than silently swallowed.

    Depth is measured to the BOUNDARY, not to the exterior ring, and the target
    comes from the maximum inscribed circle rather than from a vertex. Both
    corrections matter on the annulus: the point furthest from the outline sits
    in the middle of the hole, where no thread belongs, so an exterior-only
    measure credits the shape with 8.80 mm of reachable depth when its deepest
    sewable point is 4.20.

    Measured shortfalls at the shipped spacing: crescent 0.300, blob 0.384,
    letter_e 0.399, star 0.453, annulus 0.299 — all inside one ring pair. The
    dumbbell stops 1.199 mm short, because its waist and both lobe centres
    converge to slivers too small to sew, and that is the branch below.
    """
    poly = SHAPES[name]
    runs, report = _fill(poly, underlay_style="none")
    pts = [a for _k, a, _b in _stitches(runs, ("fill",))]
    inradius = shapely.maximum_inscribed_circle(poly, 0.001).length
    deepest = max(poly.boundary.distance(Point(p)) for p in pts)
    shortfall = inradius - deepest

    assert shortfall >= -1e-6, "no stitch may sit deeper than the deepest point"
    if shortfall <= 2 * machine.FILL_ROW_MM:
        return

    # Stopping further short than a ring pair is law 44's drop, and that is
    # allowed — but only out loud. Silence here is a bare core in the middle of
    # the shape that nobody was told about.
    assert report["skipped_rings"] > 0, (
        f"{name} stops {shortfall:.3f} mm short of its own centre and reports "
        f"no dropped ring")
    # And the drop has to be big enough to explain the gap. Rings stop one pair
    # short for free, so what is left uncovered is at least a disc of the
    # remainder; anything the report claims must cover it.
    owed = math.pi * (shortfall - 2 * machine.FILL_ROW_MM) ** 2
    assert report["skipped_area_mm2"] >= owed, (
        f"{name} leaves a {shortfall:.3f} mm core but only counts "
        f"{report['skipped_area_mm2']:.3f} mm2 against {owed:.3f} owed")


def test_stitches_never_exceed_the_format_ceiling():
    for name, poly in SHAPES.items():
        runs, _report = _fill(poly)
        longest = max(math.dist(a, b) for _k, a, b in _stitches(runs))
        assert longest <= machine.MAX_STITCH_MM + 1e-9, name


# --- Bare fabric is counted, and only reported when it is visible ------------

def test_a_dropped_ring_is_counted():
    """A ring under three minimum stitches cannot be sewn. The reference
    implementations drop it silently; we count the ring and the area."""
    runs, report = _fill(DUMBBELL)
    assert report["skipped_rings"] > 0
    assert report["skipped_area_mm2"] > 0.0
    assert runs


def test_the_converging_centre_sliver_does_not_cry_wolf():
    """EVERY shape drops its innermost ring — the sliver where the offsets meet
    themselves — so a warning on the raw count would fire on every shape and
    train the operator to ignore warnings. Since 2026-08-04 the gate is the
    measured widest bare spot: a disc's centre dot reads 0.863 mm — the
    structural residue machine.CONTOUR_BARE_CORE_MM pins — and the line sits
    half a ring spacing above it (barecircle.starved_threshold_mm), so a
    healthy shape clears it with margin."""
    _runs, report = _fill(_circle(15.0))
    assert report["skipped_rings"] >= 1
    assert report["bare_radius_mm"] < machine.CONTOUR_BARE_CORE_MM + 0.01
    assert report["starved"] == 0


def test_the_dumbbells_area_sum_no_longer_cries_wolf():
    """This test used to assert the OPPOSITE — `starved == 1` — and was
    itself the miscalibration the 2026-08-02 pass called out. The dumbbell
    converges to slivers in three places at once, and their KNOWN drops sum
    to 5.01 mm2 on a 311 mm2 shape — 1.6 %, past the old 1 % area line. But
    an area SUM is not a visible defect: measured with the instrument, no
    single one of those three spots is wider than the 0.863 mm centre dot a
    plain healthy disc leaves (barecircle.py; the dumbbell reads exactly
    0.863). Three invisible dots do not add up to one visible patch, so the
    recalibrated gate — the widest bare SPOT against
    `starved_threshold_mm` — stays silent, and the ledger keeps counting
    honestly without deciding anything.
    """
    poly = SHAPES["dumbbell"]
    _runs, report = _fill(poly, underlay_style="none")
    assert report["skipped_rings"] > 0
    assert report["skipped_area_mm2"] > 0.01 * poly.area, \
        "the old gate fired here; if this stops holding the fixture drifted"
    assert report["bare_radius_mm"] == pytest.approx(0.863, abs=0.03)
    assert report["starved"] == 0


def test_a_shape_starved_of_rings_says_so():
    """The direction the old gate was blind in. A sharp 10-point star's
    notched interior is ANNIHILATED by the mitred offset at under half its
    inradius — the bare core was never a ring, so the area ledger charges
    0.2 % and the old gate stayed silent on a 1.33 mm bare radius (the config
    block's cited 1.47 mm class; full reproduction in test_barecircle.py).
    The gate is the measurement now, so the operator is told.
    """
    import shapely as _shapely
    s0 = Polygon([((20.0 if i % 2 == 0 else 6.0) * math.cos(math.pi / 2 + i * math.pi / 10),
                   (20.0 if i % 2 == 0 else 6.0) * math.sin(math.pi / 2 + i * math.pi / 10))
                  for i in range(20)])
    sc = 10.0 / _shapely.maximum_inscribed_circle(s0, 1e-4).length
    star = _shapely.affinity.scale(s0, xfact=sc, yfact=sc, origin=(0, 0))
    _runs, report = _fill(star, underlay_style="none")
    assert report["skipped_area_mm2"] < 0.01 * star.area, \
        "the old area gate was silent here — that blindness is the point"
    assert report["bare_radius_mm"] > 1.2
    assert report["starved"] == 1


# --- Determinism ------------------------------------------------------------

@pytest.mark.parametrize("name", sorted(SHAPES))
def test_the_same_shape_gives_the_same_stitches(name):
    a, ra = _fill(SHAPES[name])
    b, rb = _fill(SHAPES[name])
    assert [(r.kind, r.points) for r in a] == [(r.kind, r.points) for r in b]
    assert ra == rb


def test_the_plan_is_byte_identical_across_two_runs(whitebg):
    """Determinism at the file level, which is what the operator actually gets."""
    c = cfg(fill_technique="contour", **PLAN_CFG_KW)
    assert export_dst(plan_stitches(whitebg, c)) == export_dst(plan_stitches(whitebg, c))


# --- The flag ---------------------------------------------------------------

def test_tatami_is_the_default():
    assert PipelineConfig().fill_technique == "tatami"


def test_the_flag_is_reachable_from_plan_stitches(whitebg):
    """The dead-code check. `stage6_border.py` shipped once fully written,
    imported and never called, so all three of its modes were byte-identical —
    which is why this test compares FILES and not call counts.

    Measured on the fixture logo at 80 mm: 2,596 stitches of tatami against
    2,263 of contour, 8,366 DST bytes against 7,364.
    """
    off = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    on = export_dst(plan_stitches(whitebg, cfg(fill_technique="contour",
                                               **PLAN_CFG_KW)))
    assert off != on, "the contour flag changed nothing — the module is dead code"


def test_the_flag_off_changes_nothing(whitebg):
    """The golden the whole suite rests on: naming the default explicitly and
    leaving it alone produce the same file, byte for byte."""
    plain = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    named = export_dst(plan_stitches(whitebg, cfg(fill_technique="tatami",
                                                  **PLAN_CFG_KW)))
    assert plain == named


def test_contour_fills_the_plan_without_crying_wolf(whitebg):
    """This test used to assert the warning FIRED on the fixture logo. Both
    shapes that tripped it (Sb253ebba, Sf5200f3f) were false alarms of the
    old area-fraction gate: their widest bare spots measure 0.644 and
    0.499 mm — both under the 0.863 mm centre dot a plain healthy disc
    leaves — while their many small terminal slivers summed past 1 % of two
    small shapes. The recalibrated gate (widest bare spot, barecircle.py) is
    rightly silent on this artwork; the fire direction is proven on the
    annihilated star in test_barecircle.py and above."""
    plan = plan_stitches(whitebg, cfg(fill_technique="contour", **PLAN_CFG_KW))
    fills = [r for _b, r in plan.iter_runs() if r.kind == "fill"]
    assert fills, "contour produced no fill runs at all"
    codes = {w["code"] for w in plan.warnings}
    assert CONTOUR_RING_UNREACHABLE not in codes


def test_every_stitch_of_a_contour_plan_stays_inside_its_shape(whitebg):
    """The end-to-end form of law 42, on real artwork rather than a fixture.

    Measured: tatami leaves 714 of 47,869 sampled points outside their shape by
    up to 0.172 mm (its own row-end rounding, out of this lane); contour leaves
    0 of 49,721.
    """
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps

    c = cfg(fill_technique="contour", **PLAN_CFG_KW)
    planned, _w = resolve_overlaps(whitebg.regions, fabric_for(c), c)
    geom = {p.shape_id: p.polygon for p in planned}
    plan = plan_stitches(whitebg, c)

    outside = 0
    for _b, run in plan.iter_runs():
        if run.kind not in ("fill", "underlay"):
            continue
        poly = geom.get(run.shape_id)
        if poly is None:
            continue
        for a, b in zip(run.points, run.points[1:]):
            # Stage 7 folds lock stitches into the run it protects; those are
            # 0.8 mm bounces on the run's own first penetration and belong to
            # `_apply_ties`, not here.
            if not poly.buffer(1e-9).covers(LineString([a, b])):
                outside += 1
    assert outside == 0


def test_a_shape_too_small_to_ring_falls_back_to_tatami():
    """Turning the flag on can never drop artwork: a shape contour cannot ring
    reports empty, and stage 7 sews it with rows instead."""
    sliver = Polygon([(0, 0), (6, 0), (6, 0.25), (0, 0.25)])
    runs, report = _fill(sliver)
    assert report["empty"]
    assert runs == []
