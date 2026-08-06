"""Stage 6 satin — columns, classification, junctions, and caps.

Shapes here are the letterform archetypes: a bar (straight column), a C
(curve), an O (closed loop), a T (branch junction). Each test names the
defect it exists to catch, matching the step-3 convention.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import machine
from digitizer_core.stage6_satin import (
    extract_strokes,
    is_satin_candidate,
    ribbon_width_mm,
    satin_shape,
)
from tests.conftest import TESTDATA

BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])
O_RING = Polygon(
    [(math.cos(t) * 10, math.sin(t) * 10) for t in np.linspace(0, 2 * math.pi, 80)],
    [[(math.cos(t) * 7.5, math.sin(t) * 7.5) for t in np.linspace(2 * math.pi, 0, 80)]],
)
C_STROKE = Polygon(
    [(math.cos(t) * 15, math.sin(t) * 15) for t in np.linspace(0.6, 2 * math.pi - 0.6, 50)]
    + [(math.cos(t) * 12, math.sin(t) * 12) for t in np.linspace(2 * math.pi - 0.6, 0.6, 50)]
)
T_SHAPE = Polygon([(0, 0), (20, 0), (20, 3), (11.5, 3), (11.5, 20), (8.5, 20), (8.5, 3), (0, 3)])
BLOB = Point(0, 0).buffer(8.0)


def _satin_runs(poly, style="none"):
    runs, report = satin_shape(poly, "S1", underlay_style=style, trim_at_mm=3.0)
    return [r for r in runs if r.kind == "satin"], runs, report


def _cross_angles(run) -> list[float]:
    """The direction of each long segment of a run, in [0, 180) degrees.

    Crosses are identified by LENGTH rather than position: an earlier version
    keyed off a fixed parity, scored a clean curved ribbon at 30%, and graded
    nothing. Anything built on that had to be re-measured.
    """
    pts = run.points
    segs = [(math.dist(pts[i], pts[i + 1]), pts[i], pts[i + 1])
            for i in range(len(pts) - 1)]
    segs = [s for s in segs if s[0] > 1e-9]
    if len(segs) < 4:
        return []
    longest = sorted(s[0] for s in segs)[int(len(segs) * 0.9)]
    return [math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
            for L, a, b in segs if L >= longest * 0.5]


def _rotations(angs: list[float], step: int = 2) -> list[float]:
    d = [abs(x - y) % 180.0 for x, y in zip(angs, angs[step:])]
    return [min(r, 180.0 - r) for r in d]


def _cross_rotations(runs) -> list[float]:
    """How far each satin cross turns from the one BEFORE LAST, in degrees.

    Every segment of the emitted run is a cross now — the rails strictly
    alternate, so there are no short steps along a rail to skip past. What
    replaces them is a built-in lean: the outbound leg A(i)->B(i) goes square
    across and the return leg B(i)->A(i+1) leans one spacing forward, so
    NEIGHBOURING crosses differ by about 2*atan(spacing/width) no matter how
    clean the column is (9 deg on a 5 mm bar). Comparing neighbours measures
    that zigzag, not spray. Comparing each cross to the one two back holds the
    lean constant and leaves only the drift this metric exists to catch.

    The first and last cross are dropped: a column deliberately finishes with
    a square-end terminal stitch onto the cap CORNERS, diagonal to the column
    by design. NOTE what that trim costs: the cap-ENTRY stitch is also the
    first element, so this aggregate is blind to it — the straight-bar test
    pins the entry separately on the untrimmed list. (Adversarial review
    caught that pin silently dying when this trim first met the new emitter.)
    """
    out: list[float] = []
    for run in runs:
        angs = _cross_angles(run)[1:-1]
        out.extend(_rotations(angs, step=2))
    return out


def test_crosses_stay_parallel_along_a_curve():
    """Regression: the column sprayed because each rail point was an
    independent ray-cast to the nearest boundary feature, so neighbouring
    crosses could land on different edges and each side got clamped on its own,
    walking the column's centre off its own spine. Rails are parallel offsets
    of a smoothed width profile now, and a curve is where that shows: on the C
    the worst neighbour-to-neighbour rotation was measured at 5.7 deg.
    """
    satin, _, _ = _satin_runs(C_STROKE)
    rot = _cross_rotations(satin)
    assert rot, "no crosses measured"
    assert max(rot) <= 5.0, f"column sprays: worst rotation {max(rot):.1f} deg"


@pytest.mark.parametrize("name,poly,worst", [("C", C_STROKE, 5.0),
                                             ("O", O_RING, 5.0),
                                             ("T", T_SHAPE, 5.0)])
def test_every_archetype_keeps_its_crosses_parallel(name, poly, worst):
    """C 2.3 deg, O 3.1 deg, T 1.3 deg as measured. A branch junction is the
    interesting one: the stem yields to the through-bar there, and the yield
    used to tilt the last crosses of the stem.
    """
    satin, _, _ = _satin_runs(poly)
    rot = _cross_rotations(satin)
    assert rot, f"{name}: no crosses measured"
    assert max(rot) <= worst, f"{name} sprays: worst {max(rot):.1f} deg"


def test_outer_rail_holds_density_on_a_curve():
    """Regression: crosses were STATIONED along the spine, but thread lands on
    the rails, and on a bend the outer rail runs further than the spine —
    measured 47% under density on a tight ring (0.59 mm between outer
    penetrations against the 0.40 target). Over-wide intervals now get
    interpolated stations.

    Rails come straight off the emitted zigzag: the order is A, B, A, B, ...
    without exception, so the even points are one rail and the odd points are
    the other. An earlier emitter flipped alternate crosses to (B, A), which
    made a fixed-parity slice hop rails and read garbage — that produced two
    false conclusions in one day. Reading rails by parity is only safe BECAUSE
    the emitter no longer alternates; if that ever changes, this breaks loudly
    rather than quietly, since the slices would then measure column width.
    """
    satin, _, _ = _satin_runs(C_STROKE)
    adv: list[float] = []
    for r in satin:
        pts = r.points
        for rail in (pts[0::2], pts[1::2]):
            adv += [math.dist(x, y) for x, y in zip(rail, rail[1:])]
    adv = sorted(a for a in adv if a > 0.03)
    assert adv, "no rail advances measured"
    n = len(adv)
    assert adv[n // 2] <= 0.45, f"median rail advance {adv[n // 2]:.2f}"
    assert adv[int(n * 0.95)] <= 0.60, f"p95 rail advance {adv[int(n * 0.95)]:.2f}"


def test_a_straight_bar_is_parallel_but_for_the_cap_entry():
    """The floor case, and it documents the one blemish left on it.

    A straight column's crosses are parallel by definition. Exactly ONE
    stitch breaks that: the column enters from the cap face at the bar's
    mid-height and reaches the near rail diagonally — 23.9 deg against its
    neighbour on this fixture. That is a cap-entry artifact, not the spray
    this module was rebuilt to fix, and it is pinned here so it can neither
    quietly become two nor quietly worsen.

    The pin reads the UNTRIMMED, ADJACENT rotation list on purpose.
    `_cross_rotations` trims the ends (the terminal cross is diagonal by
    design) and compares two apart (the zigzag lean cancels) — both correct
    for measuring spray, and both blind to the entry: adversarial review
    found the original pin reading zero once the emitter made every segment
    a cross, at which point a worsening entry — 23.9 to any angle — was
    invisible. Measured now: adjacent untrimmed shows exactly one reading
    over 15 (23.9 at index 0); two-apart trimmed spray tops out at 11.4.
    """
    satin, _, _ = _satin_runs(BAR)
    assert len(satin) == 1
    rot = _cross_rotations(satin)
    assert rot, "no crosses measured"
    assert max(rot) <= 12.5, f"bar sprays: worst two-apart rotation {max(rot):.1f}"

    entry = _rotations(_cross_angles(satin[0]), step=1)
    big = [(i, r) for i, r in enumerate(entry) if r > 15.0]
    assert len(big) <= 1, f"more than one bad stitch: {big}"
    for i, r in big:
        assert i == 0, f"a >15 deg turn away from the entry, at {i}: {r:.1f}"
        assert r <= 30.0, f"the cap entry worsened: {r:.1f} deg (was 23.9)"


# --- Classification --------------------------------------------------------

def test_ribbons_go_satin_and_blobs_stay_fill():
    """The whole point of the classifier: lettering satins, emblems fill."""
    assert is_satin_candidate(BAR, machine.SATIN_MAX_WIDTH_MM)
    assert is_satin_candidate(O_RING, machine.SATIN_MAX_WIDTH_MM)
    assert is_satin_candidate(C_STROKE, machine.SATIN_MAX_WIDTH_MM)
    assert not is_satin_candidate(BLOB, machine.SATIN_MAX_WIDTH_MM), \
        "a compact blob is not a ribbon, whatever its width number says"


def test_ribbon_width_on_a_rectangle():
    # 2*area/perimeter counts the end caps in the perimeter, so a 24x2 bar
    # reads 2*48/52 = 1.846 — a hair under the true width, by design. The
    # classifier threshold absorbs the bias; what matters is it never reads
    # WIDER than truth (that could sneak a wide shape past the satin cap).
    assert ribbon_width_mm(BAR) == pytest.approx(1.846, abs=0.01)
    assert ribbon_width_mm(BAR) < 2.0


def _serrated_disc(r: float, tooth: float, n: int = 120) -> Polygon:
    """A disc whose boundary alternates +/-tooth around the mean radius r —
    `docs/dt-classifier-spike-2026-08-02.md`'s stress fixture, and the shape
    MASTER_SCOPE.md's satin/fill classifier bullet cites directly ("a
    serrated 20mm disc computes as '5.03mm' and gets satin-stitched instead
    of filled")."""
    pts = []
    for i in range(n * 2):
        a = math.pi * i / n
        rr = r + (tooth if i % 2 else -tooth)
        pts.append((rr * math.cos(a), rr * math.sin(a)))
    return Polygon(pts)


def test_a_noisy_compact_disc_reads_narrow_on_ribbon_width_alone():
    """Documents the blind spot the DT check exists to close, not a live bug
    in `is_satin_candidate` — that bug is fixed now, for every design class
    including `"flat"` (see the tests below); this pins the raw statistic's
    own failure so the fix always has something concrete to fix.

    A 20mm disc serrated by 0.6mm is still, unambiguously, a disc — but
    boundary noise roughly doubles its perimeter, and `2*area/perimeter`
    (plus the aspect gate built on the SAME perimeter) reads that as a
    narrow, long ribbon instead. `ribbon_width_mm` alone has no way to tell
    the difference; that is exactly why `is_satin_candidate` never stops
    there."""
    disc = _serrated_disc(10.0, 0.6)
    assert ribbon_width_mm(disc) < machine.SATIN_MAX_WIDTH_MM, \
        "the raw perimeter-only statistic is expected to read this narrow"


def test_the_dt_check_catches_the_serrated_disc_a_noisy_design_class_gets():
    """The regression pin for the fix: for a non-"flat" `design_class` (the
    photo/gradient tiers, where segmentation noise like this actually shows
    up — see `testdata/photo/region_blobs.png`'s `Sd12bfc9e`/`S94f29987` and
    `testdata/photo/summit_badge.png`'s `Sed818ef7`/`S00d736bf`/`S6096e7a9`,
    all real, near-square, organic regions this exact rule used to satin),
    the second, DT-based opinion (`_dt_regular_and_within_cap`) overrides the
    perimeter-only verdict above and correctly calls this a blob.

    Swept across a few tooth depths because the fix must not be a fluke of
    one specific noise amplitude."""
    for tooth in (0.3, 0.6, 1.2):
        disc = _serrated_disc(10.0, tooth)
        assert not is_satin_candidate(disc, machine.SATIN_MAX_WIDTH_MM,
                                      design_class="gradient"), \
            f"tooth={tooth}: still satins a compact disc under a noisy class"


def test_flat_design_class_now_gets_the_dt_check_too():
    """2026-08-06: supersedes the old `test_flat_design_class_keeps_the_old_
    verdict_on_purpose`, whose own premise this fix disproves. That test
    pinned `design_class="flat"` skipping the DT check on purpose, reasoning
    that flat art's clean, vector-like boundaries don't carry the
    segmentation-derived noise the check exists to catch. A fresh audit
    against this repo's own real-art benchmark found that premise false —
    see `test_flat_lane_starburst_shapes_correctly_flip_to_fill` below for
    the real-fixture evidence — so the exemption is gone: `design_class`
    no longer changes `is_satin_candidate`'s verdict at all, and the
    synthetic serrated disc (a design-class-agnostic noise source) now
    correctly reads False under `"flat"` too, matching every other class."""
    disc = _serrated_disc(10.0, 0.6)
    assert not is_satin_candidate(disc, machine.SATIN_MAX_WIDTH_MM,
                                  design_class="flat"), \
        "the flat lane should get the same DT tightening as the other 3 classes now"
    # design_class is now a no-op on the verdict — every class agrees.
    for dc in ("flat", "gradient", "photo_subject", "photo_scene"):
        assert is_satin_candidate(disc, machine.SATIN_MAX_WIDTH_MM, design_class=dc) == \
               is_satin_candidate(disc, machine.SATIN_MAX_WIDTH_MM, design_class="flat")


def test_flat_lane_starburst_shapes_correctly_flip_to_fill():
    """The real-pipeline evidence behind the 2026-08-06 widening: run
    `testdata/photo/enthusiast_logo.png` (this repo's real-art benchmark,
    picked because it "reproduces almost nothing [Kent] complains about" —
    see COOKBOOK.md's "Hard-won lessons") through the actual pipeline at
    `target_width_mm=90` and a shape the old flat-exempted rule satin-
    stitched — `Sff37b029` (the emblem's 4-point star) — reads as compact/
    irregular under the DT check, not a ribbon. Rendering its actual pre-fix
    stitch coordinates showed why this matters: it sewed as a literal
    starburst (crosses fanning from a single point), not the clean parallel
    rows `stage6_fill.stitch_shape` now produces for it — exactly the defect
    COOKBOOK.md's "Hard-won lessons" section names by name ("Green tests are
    not evidence of quality... the engine produced starbursts").

    `Scd89ad66` (the "A" of the ENTHUSIAST wordmark) is deliberately no
    longer part of this test's claim, updated same-day alongside a SEPARATE
    fix (`resolve_small_regions`'s enclosed-hole-absorption bug,
    `tests/test_stages.py::
    test_small_enclosed_hole_is_not_absorbed_into_its_enclosing_letter`):
    the "A" only read as a compact/irregular blob here because its real
    triangular counter was, at the time this test was written, being
    silently absorbed into its own ink — a solid letterform with no hole is
    exactly the kind of organic blob the DT check exists to catch. Now that
    the hole survives as a real interior ring, the "A" measures as the
    legitimate ribbon it actually is and correctly reads satin again — this
    is the two fixes' shapes interacting correctly, not a regression: a
    letterform's medial axis with its counter intact does not fan from a
    single point (confirmed by rendering `Scd89ad66`'s post-fix stitches,
    see this PR's own investigation), so satin is the right call for it, not
    a starburst risk to defend against with a fill fallback.
    """
    from digitizer_core import PipelineConfig, digitize

    result, _plan = digitize(TESTDATA / "photo/enthusiast_logo.png",
                             PipelineConfig(target_width_mm=90.0))
    assert result.design_class == "flat"
    by_id = {r.shape_id: r for r in result.regions}
    assert "Sff37b029" in by_id, \
        f"benchmark fixture regions moved: expected Sff37b029 in {sorted(by_id)}"
    assert not is_satin_candidate(by_id["Sff37b029"].polygon, machine.SATIN_MAX_WIDTH_MM,
                                  design_class="flat"), \
        "the emblem's star should read as fill (DT-irregular), not satin"

    # The "A" is the mirror case: it now HAS a real interior ring (the
    # enclosed-hole fix) and correctly reads as satin, not fill.
    a_region = by_id.get("Scd89ad66")
    assert a_region is not None, f"benchmark fixture regions moved: Scd89ad66 not in {sorted(by_id)}"
    assert len(a_region.polygon.interiors) == 1
    assert is_satin_candidate(a_region.polygon, machine.SATIN_MAX_WIDTH_MM,
                              design_class="flat"), \
        "the 'A', with its counter restored, is a regular ribbon and should read satin"


@pytest.mark.parametrize("name,poly", [("BAR", BAR), ("O_RING", O_RING),
                                       ("C_STROKE", C_STROKE), ("T_SHAPE", T_SHAPE)])
def test_the_dt_check_does_not_cost_real_ribbons_their_satin_call(name, poly):
    """Pure tightening only works if it stays quiet on shapes that ARE
    ribbons. All four letterform archetypes keep satin under the DT check
    too — the failure mode this fix targets is boundary noise on a COMPACT
    shape, not stroke geometry in general."""
    assert is_satin_candidate(poly, machine.SATIN_MAX_WIDTH_MM, design_class="gradient")


@pytest.mark.parametrize("name,poly", [("BAR", BAR), ("O_RING", O_RING),
                                       ("C_STROKE", C_STROKE), ("T_SHAPE", T_SHAPE)])
def test_the_dt_check_does_not_cost_real_ribbons_their_satin_call_when_flat(name, poly):
    """The 2026-08-06 widening's own safety invariant, checked directly:
    this must be a PURE tightening on the flat lane too, same as it was
    already proven for the other 3 classes above. Ordinary letterform
    archetypes — the population most flat-classified art actually is —
    must not lose their satin call just because `design_class="flat"` no
    longer buys a shape a free pass around the DT check."""
    assert is_satin_candidate(poly, machine.SATIN_MAX_WIDTH_MM, design_class="flat")


# --- Column geometry -------------------------------------------------------

def test_crosses_run_perpendicular_to_the_bar():
    satin, _, _ = _satin_runs(BAR)
    assert len(satin) == 1
    pts = satin[0].points
    # Odd steps are crosses (A->B); they must be near-vertical for a
    # horizontal bar. Check the middle half, away from cap corners.
    crosses = [(a, b) for a, b in zip(pts[::2], pts[1::2]) if 6 < a[0] < 18]
    assert crosses, "no interior crosses found"
    for a, b in crosses:
        dx, dy = abs(b[0] - a[0]), abs(b[1] - a[1])
        assert dy > 3 * dx, f"cross {a}->{b} is not perpendicular to the stroke"


def test_the_column_reaches_both_caps():
    """Regression: the medial axis stops half a width inside each cap, and a
    column built on the raw spine left 1.8 mm of bare fabric per end."""
    satin, _, _ = _satin_runs(BAR)
    xs = [p[0] for r in satin for p in r.points]
    assert min(xs) <= 0.35, f"left cap bare from {min(xs):.2f}"
    assert max(xs) >= 23.65, f"right cap bare from {max(xs):.2f}"


def test_cross_spacing_matches_satin_density():
    satin, _, _ = _satin_runs(BAR)
    pts = satin[0].points
    # A-rail penetrations (every 4th point) advance ~2 spacings each.
    a_rail = pts[0::4]
    gaps = [math.dist(a, b) for a, b in zip(a_rail, a_rail[1:]) if math.dist(a, b) > 0.01]
    med = sorted(gaps)[len(gaps) // 2]
    assert med == pytest.approx(2 * machine.SATIN_SPACING_MM, abs=0.15)


def test_no_cross_escapes_the_shape():
    for poly in (BAR, C_STROKE, O_RING, T_SHAPE):
        satin, _, _ = _satin_runs(poly)
        room = poly.buffer(0.15)
        outside = [p for r in satin for p in r.points if not room.covers(Point(p))]
        assert outside == [], f"{len(outside)} satin points outside the shape"


def test_no_stitch_exceeds_the_dst_ceiling():
    for poly in (BAR, C_STROKE, O_RING, T_SHAPE):
        _, runs, _ = _satin_runs(poly, style="center_run")
        for r in runs:
            for a, b in zip(r.points, r.points[1:]):
                assert math.dist(a, b) <= machine.MAX_STITCH_MM + 1e-6


# --- Stroke decomposition --------------------------------------------------

def test_an_o_is_one_closed_loop_not_confetti():
    """Regression: the closed-loop walk once returned the same cycle 300
    times, once per pixel, because the candidate list was snapshotted."""
    strokes, _, _ = extract_strokes(O_RING)
    assert len(strokes) == 1
    assert strokes[0].closed


def test_a_t_is_a_through_bar_plus_a_yielding_stem():
    """Regression: without junction welding the bar sewed as two trimmed
    halves with a gap of bare fabric in the middle."""
    satin, _, _ = _satin_runs(T_SHAPE)
    assert len(satin) == 2, f"expected bar+stem, got {len(satin)} strokes"
    # The longer stroke is the bar and it must span the full width.
    bar = max(satin, key=lambda r: len(r.points))
    xs = [p[0] for p in bar.points]
    assert max(xs) - min(xs) >= 19.0, "the bar must sew straight through the junction"


def test_the_stem_tucks_under_the_bar_not_across_it():
    satin, _, _ = _satin_runs(T_SHAPE)
    stem = min(satin, key=lambda r: len(r.points))
    ys = [p[1] for p in stem.points]
    # The stem may tuck into the bar's zone (y<3) but never near its far edge.
    assert min(ys) > 1.0, "stem crosses reach across the bar - junction X defect"


# --- Entry/exit point selection (Laws 27-29) --------------------------------
# A short-stemmed T so the detour from the junction end to the free cap (the
# stem's top) is a few mm — comfortably inside STRUCTURAL_ENTRY_BUDGET_MM —
# unlike T_SHAPE's 17 mm stem, which stays useful for pinning the FALLBACK.
T_SHORT_STEM = Polygon(
    [(0, 0), (20, 0), (20, 3), (11.5, 3), (11.5, 9), (8.5, 9), (8.5, 3), (0, 3)])


def test_choose_stroke_entry_prefers_the_structural_cap_within_budget():
    """Law 27: pros enter at the free end 85% of the time, not the nearer
    one. Law 29: they pay up to STRUCTURAL_ENTRY_BUDGET_MM of extra travel to
    reach it — here the cap is 4 mm farther than the junction end, which is
    inside the 10 mm budget, so the cap wins despite being farther."""
    from digitizer_core.stage6_satin import _choose_stroke_entry

    junction, cap = (1.0, 0.0), (5.0, 0.0)
    assert _choose_stroke_entry((0.0, 0.0), junction, False, cap, True) is True
    # Symmetric: same geometry, ends swapped, same verdict either way.
    assert _choose_stroke_entry((0.0, 0.0), cap, True, junction, False) is False


def test_choose_stroke_entry_is_exactly_at_the_budget_boundary():
    """10 mm extra is still paid ('up to ~10 mm'); past it, not."""
    from digitizer_core.stage6_satin import _choose_stroke_entry

    junction, cap = (0.0, 0.0), (10.0, 0.0)
    assert _choose_stroke_entry((0.0, 0.0), junction, False, cap, True) is True
    cap_too_far = (10.01, 0.0)
    assert _choose_stroke_entry((0.0, 0.0), junction, False, cap_too_far, True) is False


def test_choose_stroke_entry_falls_back_to_proximity_past_the_budget():
    """Law 29's own limit: past ~10-20 mm of detour, pros mostly stop paying
    for the structural entry, so the near end wins like it always did."""
    from digitizer_core.stage6_satin import _choose_stroke_entry

    junction, cap = (1.0, 0.0), (15.0, 0.0)
    assert _choose_stroke_entry((0.0, 0.0), junction, False, cap, True) is False


def test_choose_stroke_entry_uses_proximity_when_neither_end_is_structural():
    """Both ends free (an isolated stroke) or both welded into a junction:
    no structural signal to prefer, proximity is the whole rule, exactly as
    before this law existed."""
    from digitizer_core.stage6_satin import _choose_stroke_entry

    near, far = (2.0, 0.0), (9.0, 0.0)
    assert _choose_stroke_entry((0.0, 0.0), far, True, near, True) is True   # both free
    assert _choose_stroke_entry((0.0, 0.0), far, False, near, False) is True  # both junction


def test_a_short_stem_enters_at_its_free_cap_not_the_near_junction():
    """End-to-end: needle starts right at the stem's junction, but the stem's
    satin column still enters from its free cap at the top — the same
    structural preference the unit tests pin, wired through satin_shape."""
    runs, report = satin_shape(T_SHORT_STEM, "S1", underlay_style="none",
                               trim_at_mm=3.0, start_near=(10.0, 3.2))
    satin = [r for r in runs if r.kind == "satin"]
    stem = min(satin, key=lambda r: len(r.points))
    assert stem.points[0][1] > stem.points[-1][1] + 2.0, \
        "the stem should enter near its free cap (higher y), not the junction"


def test_a_long_stem_still_enters_near_when_the_cap_is_too_far():
    """T_SHAPE's stem is ~17 mm — past STRUCTURAL_ENTRY_BUDGET_MM, so this
    pins the fallback: nearest-end entry is unchanged when the structural
    cap would cost too much extra travel."""
    runs, report = satin_shape(T_SHAPE, "S1", underlay_style="none",
                               trim_at_mm=3.0, start_near=(10.0, 3.2))
    satin = [r for r in runs if r.kind == "satin"]
    stem = min(satin, key=lambda r: len(r.points))
    assert stem.points[0][1] < stem.points[-1][1], \
        "far past budget, the stem should still enter near the junction (lower y)"


def test_curve_inside_rail_does_not_chew_one_hole():
    """The short-stitch guard: on the inside of a curve penetrations bunch;
    alternate crosses must be pulled off the rail."""
    satin, _, _ = _satin_runs(C_STROKE)
    pts = [p for r in satin for p in r.points]
    inner = [p for p in pts if abs(math.hypot(*p) - 12.0) < 0.4]  # near inner rail
    # Count coincident penetrations (closer than 0.15 mm).
    crowded = 0
    for i, p in enumerate(inner):
        for q in inner[i + 1:]:
            if math.dist(p, q) < 0.15:
                crowded += 1
    assert crowded <= len(inner) // 10, \
        f"{crowded} near-coincident penetrations on the inside rail"


def test_a_satin_free_end_does_not_fan_into_a_starburst():
    """Regression, measured on testdata/ribbon_curve.png: spur pruning left the
    last millimetre of the spine running diagonally into a cap corner instead
    of down the middle of the stroke. Every cross built there pivoted on the
    same needle hole and swung out across the cap — a starburst, thread laid
    outside the ribbon, and the cap itself left bare.

    A column may finish each free end with one wide terminal cross reaching the
    cap corners; a fan is several of them in a row. Counted on the rail
    penetrations, the fan showed as four over-wide gaps STACKED AT ONE END —
    which is why this is measured per end zone and not as one total.

    The interior count is pinned at ZERO, and how it got there matters: two
    neighbouring same-rail intervals mid-bend used to read 0.98 and 1.00 mm
    against the 0.40 target. That was never missing thread — it was the
    short-stitch guard's pull scaling with column width. Rail refinement
    inserted a station where the outer rail ran 0.5203 mm, a hair over its
    1.3x gate; the inserted station's inner penetration landed 0.174 mm from
    its neighbour, and the guard retracted it 0.35 x the 2.78 mm cross =
    0.97 mm off the rail. The two ~1.0 mm "gaps" were this metric stepping
    through that one displaced point. With the pull capped at an absolute
    0.6 mm (SATIN_SHORT_STITCH_PULL_MAX_MM) the same intervals measure 0.61
    and 0.64 mm. History: it predates the emitter's rail ordering (measured
    identical on both), and the earlier version of this test stepped through
    the points by two, saw only half the same-rail intervals, and never
    reported it.
    """
    from digitizer_core import PipelineConfig, digitize
    from digitizer_core.stitches import strip_ties

    _result, plan = digitize(TESTDATA / "ribbon_curve.png",
                             PipelineConfig(target_width_mm=80.0,
                                            garment_id="left_chest"))
    runs = [r for _b, r in plan.iter_runs() if r.kind == "satin"]
    assert len(runs) == 1, f"the ribbon should sew as one column, got {len(runs)}"
    # Stage 7 folds lock stitches into the run; scanned raw they pair the last
    # real penetration with a tie midpoint and read as a phantom gap of
    # final_cross - 0.8 mm. Adversarial review found this test's tail
    # allowance calibrated against that artifact — the ribbon's tail is
    # actually CLEAN, provable once the ties are stripped.
    pts = strip_ties(runs[0].points)
    assert len(pts) > 200, "the curved ribbon should sew as one long column"

    # Points come out A, B, A, B ... so p[i] and p[i+2] are consecutive
    # penetrations on the same rail, and stepping i by ONE covers both rails
    # and every interval on them. Cross number is i // 2.
    ncross = len(pts) // 2
    wide = [(i, math.dist(pts[i], pts[i + 2])) for i in range(len(pts) - 2)
            if math.dist(pts[i], pts[i + 2]) > 2 * machine.SATIN_SPACING_MM]
    head = [w for w in wide if w[0] // 2 < 5]
    tail = [w for w in wide if w[0] // 2 >= ncross - 5]
    interior = [w for w in wide if w not in head and w not in tail]

    assert interior == [], f"over-wide rail gaps away from the caps: {interior}"
    assert tail == [], f"the end cap is fanning: {tail}"
    # The head zone is CLEAN too, and stays pinned that way. Its two readings
    # (0.96/0.83 mm at crosses 0 and 3) were taper coverage holes: the
    # smoothed width profile could not follow the tip's pinch to zero, so the
    # containment fallback jumped between discrete shrink factors instead of
    # ramping. `_rail_points` now caps taper-zone widths to the per-station
    # ray measurement and lets the zone refine — the same intervals measure
    # 0.30-0.56 mm. A tapered tip has no terminal fan to excuse, so the head
    # gets no allowance at all.
    assert head == [], f"the start cap is fanning: {head}"


def test_satin_crosses_do_not_self_overlap_across_a_wide_junction():
    """Regression, found and fixed 2026-08-05: `logo_alpha.png`'s `Sf5200f3f`
    is a multi-stroke glyph carrying a genuine wide apex (both ends of the
    affected stroke are FREE -- no junction node on this stroke at all,
    confirmed by direct inspection of `field.half_at()` along its spine: a
    smooth, single-peaked taper, 0.17mm at each tip ramping continuously up
    to 4.67mm at the apex and back down, no isolated spike -- this is the
    shape's real medial-axis width, not a measurement artifact). At
    `SATIN_MAX_WIDTH_MM=5.0`, that peak (locally ~9.3mm across) is well past
    where the corpus ever validated a satin cross at all
    (docs/corpus-laws-round3-2026-08-01.md flags its own >7.0mm bucket as
    82% non-ribbon junk) -- ungated, the crosses near the peak fanned out
    7-9mm and physically overlapped each other. Measured directly before the
    fix: 2580 non-adjacent rail-to-rail segment pairs crossed each other, and
    the shape's own isolated coverage peak read 9.57 layers of the design's
    overall 13.11 (see test_preflight.py::
    test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_glue,
    which pins the aggregate number this test complements with the actual
    geometry).

    Fix (`stage6_satin.py::_rail_points`): cap every station's width to
    `SATIN_MAX_WIDTH_MM / 2` too, alongside the existing local-corridor cap
    -- the same ceiling the satin/fill classifier already gates on ("ribbons
    wider than this sew better as fill", machine.py) and `_stroke_underlay`'s
    oversize check already reuses, not a new number: no classifier-eligible
    column should ever need a wider cross in the first place.

    2026-08-06 update: `Sf5200f3f` itself no longer reaches this code path
    in the real, sequenced pipeline at all -- the flat-lane DT-tightening
    widening (`test_flat_lane_starburst_shapes_correctly_flip_to_fill` et
    al., and `test_sf5200f3f_no_longer_reaches_satin_in_the_real_pipeline`
    directly below) correctly reclassifies it as fill now: a fuller fix than
    the cap here, which only stopped the crosses from overlapping, not from
    being the wrong technique for this shape in the first place.
    `_rail_points`'s cap is still live, general code, though -- it protects
    any satin column that DOES reach it, from a design class the DT check
    has not tightened, a forced "satin" override, or any other caller. So
    this test now calls `satin_shape` DIRECTLY on `Sf5200f3f`'s real,
    unmodified geometry (bypassing `is_satin_candidate` on purpose), keeping
    the exact rail-geometry regression coverage the 2026-08-05 fix earned,
    decoupled from whatever the classifier decides for this shape.
    """
    from digitizer_core import PipelineConfig, run_stages
    from digitizer_core.stage6_satin import satin_shape, strip_splits
    from digitizer_core.stitches import strip_ties

    c = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(TESTDATA / "logo_alpha.png", c)
    region = next(r for r in result.regions if r.shape_id == "Sf5200f3f")

    runs, report = satin_shape(region.polygon, region.shape_id,
                               underlay_style="center_run", trim_at_mm=3.0)
    assert not report["empty"], "fixture regressed: the shape no longer skeletonizes"

    segs = []
    for run in runs:
        if run.kind != "satin":
            continue
        pts = strip_splits(strip_ties(run.points))
        segs.extend(LineString((a, b)) for a, b in zip(pts, pts[1:]))

    assert segs, ("fixture regressed: Sf5200f3f no longer sews as satin even "
                  "when forced through satin_shape directly")

    # Adjacent segments legitimately share an endpoint (the zigzag's own
    # rail-to-rail step); only NON-adjacent crossings are the defect.
    crossings = 0
    for i, si in enumerate(segs):
        if si.length < 1e-6:
            continue
        for sj in segs[i + 2:]:
            if sj.length < 1e-6:
                continue
            if si.intersects(sj):
                crossings += 1

    assert crossings == 0, f"{crossings} non-adjacent satin crosses overlap each other"


def test_sf5200f3f_no_longer_reaches_satin_in_the_real_pipeline():
    """Companion to the direct-geometry test above: confirms the CLASSIFIER
    side of the 2026-08-06 fix for this exact shape, in the real sequenced
    pipeline (not `is_satin_candidate` called in isolation on an extracted
    polygon) -- `Sf5200f3f` now sews as fill, not satin, at the same config
    the 2026-08-05 self-overlap fix was originally measured against."""
    from digitizer_core import PipelineConfig, plan_stitches, run_stages

    c = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(TESTDATA / "logo_alpha.png", c)
    plan = plan_stitches(result, c)

    kinds = {run.kind for _b, run in plan.iter_runs() if run.shape_id == "Sf5200f3f"}
    assert kinds, "fixture regressed: Sf5200f3f produced no runs at all"
    assert "satin" not in kinds, \
        f"Sf5200f3f should sew as fill now, not satin -- got kinds {kinds}"


# --- Underlay --------------------------------------------------------------

def test_underlay_stays_inside_the_column():
    _, runs, _ = _satin_runs(BAR, style="center_run")
    satin_pts = [p for r in runs if r.kind == "satin" for p in r.points]
    under_pts = [p for r in runs if r.kind == "underlay" for p in r.points]
    assert under_pts, "center_run underlay expected"
    sx = [p[0] for p in satin_pts]
    ux = [p[0] for p in under_pts]
    assert min(ux) >= min(sx) - 1e-6 and max(ux) <= max(sx) + 1e-6


# --- Contract with stage 7 -------------------------------------------------

def test_report_contract_matches_the_fill_path():
    _, _, report = _satin_runs(BAR)
    assert set(report) == {"too_thin", "jumps", "empty"}


def test_a_degenerate_sliver_reports_empty_never_raises():
    sliver = Polygon([(0, 0), (10, 0), (10, 0.05), (0, 0.05)])
    runs, report = satin_shape(sliver, "S1", underlay_style="none", trim_at_mm=3.0)
    assert report["empty"] or runs  # either is honest; an exception is not


def test_same_shape_twice_gives_identical_stitches():
    """Regression: medial_axis breaks skeleton ties in RANDOM order unless
    seeded, and unseeded it digitized the same artwork differently run to run.
    The T is in the list deliberately — junction walks exercise the ordering
    paths a plain bar never touches."""
    for poly in (BAR, C_STROKE, O_RING, T_SHAPE):
        a, _, _ = _satin_runs(poly)
        b, _, _ = _satin_runs(poly)
        assert [r.points for r in a] == [r.points for r in b]


def test_a_shape_whose_skeleton_prunes_away_still_sews_as_fill():
    """A tiny plus sign is all spurs: every arm is short with one free end.
    If pruning empties the skeleton, the shape must fall back to fill in
    stage 7 — silently dropping artwork is the one unforgivable failure."""
    tiny_plus = Polygon([(0, 1.4), (1.2, 1.4), (1.2, 0), (2.2, 0), (2.2, 1.4),
                         (3.4, 1.4), (3.4, 2.4), (2.2, 2.4), (2.2, 3.8),
                         (1.2, 3.8), (1.2, 2.4), (0, 2.4)])
    runs, report = satin_shape(tiny_plus, "S1", underlay_style="none", trim_at_mm=3.0)
    if report["empty"]:
        assert runs == [], "an empty report with runs attached would double-sew"
    else:
        assert any(r.kind == "satin" for r in runs)


# --- Split satin ------------------------------------------------------------

WIDE_BAR = Polygon([(0, 0), (24, 0), (24, 7), (0, 7)])   # 7 mm crosses: splits


def test_no_split_below_threshold_is_byte_identical():
    """The contract that lets every parity instrument stay honest: a column
    with no over-threshold cross emits EXACTLY what it emitted before split
    satin existed. BAR's crosses are ~2 mm against the 5.0 threshold."""
    from digitizer_core.stage6_satin import satin_stroke, extract_strokes, _WidthField

    plain, _, _ = _satin_runs(BAR)
    raw, report = satin_shape(BAR, "S1", underlay_style="none", trim_at_mm=3.0,
                              split_above_mm=math.inf)
    raw = [r for r in raw if r.kind == "satin"]
    assert [r.points for r in plain] == [r.points for r in raw], \
        "an unsplittable column must not notice the feature exists"


def test_wide_crosses_split_and_stay_under_the_threshold():
    """Corpus law: 53% of 5 mm crosses split, ~100% from 7.5. On a 7 mm bar
    no stitch may exceed the threshold itself — full-width crosses split into
    pieces (longest 1.23 x segment = 3.7 mm), while cap-zone crosses that
    measure under 5.0 sew raw, exactly as the corpus majority does."""
    from digitizer_core.stage6_satin import strip_splits

    satin, _, _ = _satin_runs(WIDE_BAR)
    main = max(satin, key=lambda r: len(r.points))
    steps = [math.dist(a, b) for a, b in zip(main.points, main.points[1:])]
    assert max(steps) <= machine.SPLIT_SATIN_ABOVE_MM + 1e-6, \
        f"unsplit stitch survived: {max(steps):.2f} mm"
    # And the splits really are extra penetrations, not moved rails:
    rails = strip_splits(main.points)
    assert len(rails) < len(main.points), "no split points were inserted"


def test_strip_splits_recovers_the_exact_rails():
    """strip_splits is the reading contract: rails recovered from a split
    column must equal the rails of the same column emitted unsplit."""
    from digitizer_core.stage6_satin import strip_splits

    split_runs, _, _ = _satin_runs(WIDE_BAR)
    raw_runs, _ = satin_shape(WIDE_BAR, "S1", underlay_style="none",
                              trim_at_mm=3.0, split_above_mm=math.inf)
    raw_runs = [r for r in raw_runs if r.kind == "satin"]
    assert len(split_runs) == len(raw_runs)
    for s, r in zip(split_runs, raw_runs):
        stripped = strip_splits(s.points)
        assert len(stripped) == len(r.points), \
            f"rail count drifted: {len(stripped)} vs {len(r.points)}"
        worst = max(math.dist(a, b) for a, b in zip(stripped, r.points))
        assert worst <= 1e-6, f"a recovered rail moved {worst:.4f} mm"


def test_split_points_stagger_between_stations():
    """Aligned split holes trench a visible line down the column (corpus:
    aligned is the minority, 131 of 1,922 split columns). Consecutive
    same-rail stations must not put their first split point at the same
    fraction of the cross."""
    from digitizer_core.stage6_satin import strip_splits

    satin, _, _ = _satin_runs(WIDE_BAR)
    pts = satin[0].points
    rails = strip_splits(pts)
    # Walk crosses: rails alternate A,B; find each cross's split fractions.
    fracs = []
    ri = 0
    i = 0
    while i < len(pts) - 1 and ri < len(rails) - 1:
        assert pts[i] == rails[ri]
        j = i + 1
        mids = []
        while j < len(pts) and pts[j] != rails[ri + 1]:
            mids.append(pts[j])
            j += 1
        if mids:
            a, b = rails[ri], rails[ri + 1]
            span = math.dist(a, b)
            fracs.append(round(math.dist(a, mids[0]) / span, 3))
        i, ri = j, ri + 1
    assert len(fracs) >= 6, "expected many split crosses on a 7 mm bar"
    assert len(set(fracs)) >= 2, f"split holes trench a line: all at {fracs[0]}"


def test_split_satin_off_is_a_config_choice():
    from digitizer_core import PipelineConfig
    assert PipelineConfig().split_satin is True
    raw, _ = satin_shape(WIDE_BAR, "S1", underlay_style="none",
                         trim_at_mm=3.0, split_above_mm=math.inf)
    steps = [math.dist(a, b)
             for r in raw if r.kind == "satin"
             for a, b in zip(r.points, r.points[1:])]
    assert max(steps) > machine.SPLIT_SATIN_ABOVE_MM, \
        "inf threshold must sew raw crosses (the jolly-af house style)"


def test_same_rail_spacing_sits_on_the_thread_width_not_below_the_guard():
    """Law 17 field note, pinned: the short-stitch guard's 0.3 mm threshold is
    BELOW the design spacing on purpose, and must stay there.

    40 wt thread is 0.4 mm wide (physics law 16) and the professional corpus
    sews same-rail penetrations at 0.40-0.51 mm, so essentially every interval
    we emit lands in the 0.30-0.50 mm band: measured 97.4% on ribbon_curve,
    98.3% on logo_whitebg. That is the target, not a violation of the ~0.5 mm
    same-hole radius — which describes re-entering a hole that already holds
    anchored thread, not laying neighbouring stitches edge to edge.

    The guard exists for penetrations that bunch BELOW the spacing on the
    inside of a curve. Raising its threshold toward 0.5 would fire it on
    correctly-spaced satin, and since it retracts stations off the rail, that
    manufactures the coverage holes commits 493a548 and c6046ff removed. This
    test fails if anyone tries.
    """
    assert machine.SATIN_SHORT_STITCH_AT_MM < machine.SATIN_SPACING_MM, \
        "the guard must trip below the design spacing, never at or above it"

    satin, _, _ = _satin_runs(C_STROKE)
    adv = [math.dist(a, b)
           for r in satin
           for rail in (r.points[0::2], r.points[1::2])
           for a, b in zip(rail, rail[1:])]
    adv = [d for d in adv if d > 1e-9]
    assert adv, "no rail advances measured"
    in_band = sum(1 for d in adv if 0.30 <= d < 0.50)
    assert in_band / len(adv) >= 0.85, \
        f"only {100 * in_band / len(adv):.0f}% of intervals sit on the thread width"
    below_guard = sum(1 for d in adv if d < machine.SATIN_SHORT_STITCH_AT_MM)
    assert below_guard / len(adv) <= 0.05, \
        f"{below_guard} intervals bunched under the guard threshold — the guard is not doing its job"
