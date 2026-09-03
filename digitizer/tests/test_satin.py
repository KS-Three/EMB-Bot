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
# The module itself, not just its names: the degenerate-raster test has to
# monkeypatch `_dt_stats`, which needs the attribute lookup to go through the
# module object rather than a name bound at import time.
from digitizer_core import stage6_satin
from digitizer_core.stage6_satin import (
    classify_ribbon,
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
    the second, DT-based opinion (`classify_ribbon`'s regularity and p90 gates)
    overrides the perimeter-only verdict above and correctly calls this a blob.

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


# --- Gate attribution ------------------------------------------------------
#
# `classify_ribbon` is `is_satin_candidate`'s implementation, exposing WHICH
# gate rejected a shape. It exists because the routing defect (MASTER_SCOPE
# live defect 5 — 35% of the pro's satin ground sewn as fill) cannot be
# attributed without knowing which of the three rejection gates fired.
# Nothing in the pipeline reads it yet; these tests pin the equivalence that
# makes it a refactor rather than a behaviour change.

# A disc small enough to pass the width cap, so the ASPECT gate is what
# rejects it: r=2 gives ribbon width 2.0 mm (under the 5.0 cap) but a length
# estimate of 4.3 mm against the 6.0 mm the 3:1 test demands.
SMALL_DISC = Point(0, 0).buffer(2.0)
# Wider than the cap on the distance transform, narrower than it on
# 2*area/perimeter (which reads the end caps into the perimeter and comes out
# low): a 5.5 mm bar reads 4.47 mm on the ribbon statistic. So it clears the
# first two gates and is caught by the DT's own p90 cap.
WIDE_BAR = Polygon([(0, 0), (40, 0), (40, 5.5), (0, 5.5)])
# A long spike, kept as a MEASUREMENT rather than a rejection case: its
# medial-axis radii run from ~0 at the tip to the full half-width at the base,
# and it still passes the regularity term at dt_cv 0.479 against the 0.5 the
# term allows. A taper that steep clearing the gate by 4% is worth knowing
# before slice 2 touches that threshold.
SPIKE = Polygon([(0, 0), (60, 1.6), (0, 3.2)])


@pytest.mark.parametrize("name,poly", [
    ("BAR", BAR), ("O_RING", O_RING), ("C_STROKE", C_STROKE),
    ("T_SHAPE", T_SHAPE), ("BLOB", BLOB), ("SMALL_DISC", SMALL_DISC),
    ("WIDE_BAR", WIDE_BAR), ("SPIKE", SPIKE),
])
def test_classify_ribbon_agrees_with_the_bool_it_replaces(name, poly):
    """The refactor's whole safety claim: same verdict, every shape.

    If these two ever disagree, a stitch coordinate has moved somewhere and
    the attribution work has become a behaviour change without saying so."""
    for design_class in ("flat", "gradient"):
        v = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM,
                            design_class=design_class)
        assert v.satin is is_satin_candidate(poly, machine.SATIN_MAX_WIDTH_MM,
                                             design_class=design_class), name


@pytest.mark.parametrize("name,poly,reason", [
    ("BAR", BAR, "satin"),
    ("O_RING", O_RING, "satin"),
    ("BLOB", BLOB, "width_cap"),
    ("SMALL_DISC", SMALL_DISC, "aspect"),
    ("WIDE_BAR", WIDE_BAR, "dt_p90_cap"),
    ("SERRATED_DISC", _serrated_disc(10.0, 0.6), "dt_irregular"),
    ("SPIKE", SPIKE, "satin"),
])
def test_every_gate_is_reachable_and_names_itself(name, poly, reason):
    """Each rejection gate must be attributable to a shape that provokes it,
    or the probe's summary would have categories nothing can land in.

    The reason is the FIRST gate that fired, matching the short-circuit order
    of the function it replaces."""
    v = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM)
    assert v.reason == reason, f"{name}: expected {reason}, got {v.reason}"


def test_the_verdict_carries_the_margin_the_gate_missed_by():
    """A fix is only cheap if the misses cluster just past the line, so the
    metrics have to say by how much — not merely that a gate fired."""
    v = classify_ribbon(BAR, machine.SATIN_MAX_WIDTH_MM)
    for key in ("ribbon_w", "length_est", "aspect", "dt_mean", "dt_std",
                "dt_cv", "dt_p90_mm", "area_mm2"):
        assert key in v.metrics, f"missing metric: {key}"
    assert v.metrics["ribbon_w"] == pytest.approx(1.846, abs=0.01)
    assert v.metrics["aspect"] > 3.0, "a 24x2 bar is a ribbon by aspect"
    assert v.metrics["dt_p90_mm"] > 0.0, "the DT ran and reported a width"


def test_a_degenerate_raster_defers_under_its_own_name(monkeypatch):
    """`classify_ribbon` returns True on a degenerate raster — deferring
    rather than failing closed. That is a deliberate call, but it is NOT the
    same event as a shape passing the DT check on its merits, and the probe's
    per-gate table must not count the two together.

    Forced via `_dt_stats`, because no polygon can reach this branch (see
    `test_no_real_polygon_can_reach_the_degenerate_branch` below). An earlier
    version of this test fed a thin sliver and asserted
    `reason in ("satin", "dt_degenerate")` inside an `if v.satin:` — which
    could not fail: the sliver returns `satin`, so the test was passing while
    demonstrating the exact conflation it names.
    """
    monkeypatch.setattr(stage6_satin, "_dt_stats", lambda poly: None)
    v = classify_ribbon(BAR, machine.SATIN_MAX_WIDTH_MM)
    assert v.satin, "a degenerate raster defers to the verdict already reached"
    assert v.reason == "dt_degenerate", (
        "the deferral must name itself, not borrow `satin` — the probe reads "
        "`satin` as 'the DT approved this shape'")


def test_no_real_polygon_can_reach_the_degenerate_branch():
    """Why the test above has to force it, pinned so the day that stops being
    true is a red test rather than a silent gap.

    Two guards make the branch unreachable from any polygon. `w <= 0` sends a
    zero-area shape to `width_cap` before the DT runs at all, and
    `rasterize_polygon` picks its scale FROM the shape, so an arbitrarily thin
    ribbon still rasterizes to a full mask rather than an empty one — a
    0.02 x 0.001 mm bar comes back at scale 8400 px/mm.

    If a future rasterizer pins its scale instead, this test fails and the
    `dt_degenerate` branch becomes genuinely reachable — at which point it
    wants a real fixture, not a monkeypatch.
    """
    assert classify_ribbon(
        Polygon([(0, 0), (10, 0), (10, 0), (0, 0)]),
        machine.SATIN_MAX_WIDTH_MM).reason == "width_cap", \
        "a zero-area polygon must be caught by the width cap, not the DT"
    for w, h in ((12, 0.02), (0.5, 0.01), (0.02, 0.001)):
        poly = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
        assert stage6_satin._dt_stats(poly) is not None, \
            f"{w}x{h} mm unexpectedly degenerate — see this test's docstring"


# --- Promotion back to satin -----------------------------------------------
#
# Measured on 15 real customer designs against their professional
# digitizations (`docs/superpowers/specs/2026-08-16-satin-routing-gate-
# attribution-design.md`): of the pro's satin ground the classifier declines to
# satin, 63.6% is rejected by the REGULARITY term and the median miss is 0.05
# past a 0.5 limit. Simply loosening that limit does not work — a sweep
# recovers 625 pro-satin cells and leaks 439 pro-fill ones. What separates the
# two is not how tight the radius spread is but whether the shape IS its spine
# swept by its width, which is what `explained` measures.

# A 60mm stroke tapering to a point: the radii run from ~0 at the tip to the
# full half-width at the base, so the regularity term rejects it at dt_cv
# 0.507 — and it is a ribbon, at explained 0.903.
TAPERED_STROKE = Polygon([(0, 0), (60, 2.4), (0, 4.8)])


def test_a_tapered_stroke_the_regularity_term_rejects_comes_back_as_satin():
    """The promotion path, on the shape class that provoked it: script and
    dimensional lettering, whose strokes are thick-and-thin by design."""
    v = classify_ribbon(TAPERED_STROKE, machine.SATIN_MAX_WIDTH_MM)
    assert v.metrics["dt_cv"] > 0.5, \
        "fixture drift: this must still fail the regularity term"
    assert v.satin, "a tapered stroke is a ribbon; the pro satins it"
    assert v.reason == "promoted_ribbon"


@pytest.mark.parametrize("name,poly", [("WIDE_BAR", WIDE_BAR), ("BLOB", BLOB)])
def test_promotion_cannot_reopen_the_width_cap(name, poly):
    """It reopens the REGULARITY term only. A column wider than the machine
    holds does not become sewable because it is shaped like a ribbon — that
    is a physical limit, not a proxy the promotion is allowed to overrule."""
    v = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM)
    assert not v.satin, name
    assert v.reason in ("dt_p90_cap", "width_cap"), name


@pytest.mark.parametrize("tooth", [0.3, 0.6, 1.2])
def test_promotion_does_not_wave_the_serrated_disc_through(tooth):
    """The blob the DT check exists to catch must not come back through the
    door the promotion opens. A disc's area is ~8x what its collapsed medial
    axis can sweep, so `explained` reads 0.11-0.13 against the 0.80 the
    promotion demands — the noise that fools `2*area/perimeter` moves this
    statistic the WRONG way, which is what makes it safe here."""
    disc = _serrated_disc(10.0, tooth)
    v = classify_ribbon(disc, machine.SATIN_MAX_WIDTH_MM)
    assert not v.satin, f"tooth={tooth}: promoted a compact disc"


def test_the_four_letterform_archetypes_are_untouched_by_promotion():
    """Promotion must not change a shape that already had a verdict. All four
    keep satin, and keep reaching it through the ordinary path rather than
    through the new one."""
    for poly in (BAR, O_RING, C_STROKE, T_SHAPE):
        v = classify_ribbon(poly, machine.SATIN_MAX_WIDTH_MM)
        assert v.satin and v.reason == "satin"


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


# --- Multi-junction stroke corner coverage -----------------------------------
# A block "E": one vertical stem crossing THREE T-junctions along its own
# length (a top bar, a middle bar, a bottom bar), with the top and bottom
# bars flush against the stem's own left edge — proportions taken directly
# from `testdata/photo/enthusiast_logo.png`'s own vectorized "E" (translated
# to the origin), the real fixture PR #77 root-caused and deliberately left
# open: the stem's own bottom-left corner sewed as bare fabric. `_merge_
# through_junctions` welds the stem's up/down arms through all three nodes
# into ONE both-ends-free stroke (proven below), so BOTH of its caps —
# `_extend_to_cap` lands each within 0.15mm of the glyph's real corner — sit
# right where the stem is flush with a bar, not at an isolated square cap.
E_LETTERFORM = Polygon([
    (0.0, 0.0), (0.0, 7.324), (6.796, 7.324), (6.796, 5.675),
    (2.112, 5.609), (2.178, 4.421), (6.137, 4.355), (6.071, 2.837),
    (2.178, 2.837), (2.112, 1.716), (6.796, 1.650), (6.796, 0.0),
])


def test_a_stem_crossing_three_junctions_welds_into_one_stroke():
    """Confirms the fixture actually exercises the multi-junction case
    before trusting the coverage assertion below: the through-weld at each
    of the three T-junctions must chain into a single stroke with both ends
    free (its own two caps), not stay fragmented into per-segment pieces.

    The stem is picked by the one thing that is TRUE OF THE STEM — it is the
    stroke that runs the glyph's height — and not, as it once was, by being
    the longest spine. That worked only while the stem's spine swallowed the
    two corner forks at its flush corners, which is the geometry
    `_corner_forks` now declines to build a column on: the stem's own spine
    runs node to node at 5.25 mm and the bottom bar's, cap included, at 5.32.
    Every assertion below is the one this test always made.
    """
    strokes, _, _ = extract_strokes(E_LETTERFORM)
    stem = max(strokes, key=lambda s: max(p[1] for p in s.spine)
               - min(p[1] for p in s.spine))
    assert stem.free_start and stem.free_end, \
        "the stem should weld through all three junctions into one open stroke"
    # Three bars, each yielding to the stem with one free end of its own.
    bars = [s for s in strokes if s is not stem]
    assert len(bars) == 3
    assert all(b.free_start != b.free_end for b in bars), \
        "each bar should tuck into the stem at one end and stay free at the other"


def test_stem_free_end_reaches_its_own_flush_corner():
    """Regression, root-caused by PR #77 and fixed here: a stroke crossing
    MULTIPLE T-junctions along its own length still needs each of its own
    caps to reach the real corner it is flush with, not just get close.

    Root cause was not the junction machinery (`_merge_through_junctions`,
    `_extend_to_cap`, `_retract_cap_corner` all already land the spine
    within 0.15mm of the true corner) — it was `_short_stitch_guard`'s
    pull-toward-middle: the cross one station in from the cap starts out a
    real, keepable stitch (just over `SATIN_MIN_CROSS_MM`), but the guard's
    stock 35%-capped-at-0.6mm pull (sized for a wide curve, where a cross is
    several mm) took it under the floor, and the degenerate-cross filter a
    few lines later dropped a stitch that was never actually degenerate.
    Not letterform-specific: any cap zone or curve whose next-station cross
    starts only a little above the floor can hit the same interaction.
    """
    satin, _, _ = _satin_runs(E_LETTERFORM)
    pts = [p for r in satin for p in r.points]
    corner = (0.0, 0.0)  # the stem's own flush corner with the bottom bar
    d = min(math.dist(p, corner) for p in pts)
    assert d < 0.45, f"the flush corner is still {d:.2f}mm from the nearest stitch"


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


# --- Spur pruning: what counts as a twig -----------------------------------

def _tab_skeleton() -> np.ndarray:
    """A body with a tab hanging off it, the tab forking into two twigs.

    This is `enthusiast_logo`'s emblem bracket in miniature. The body runs
    down x=0; the tab's stem leaves it at (0,10) and ends in a fork at (5,10)
    whose two twigs are far shorter than the stem.

        (0,0)  |                    (7,8) A
               |          .        /
        (0,10) +-----------(5,10)
               |          `        \
        (0,20) |                    (7,12) B
    """
    m = np.zeros((21, 9), np.uint8)
    m[0:21, 0] = 1                                  # body: free at both ends
    for x in range(1, 6):
        m[10, x] = 1                                # stem, 5 px
    m[9, 6] = m[8, 7] = 1                           # twig A, 2*sqrt(2) px
    m[11, 6] = m[12, 7] = 1                         # twig B, same
    return m


def test_a_stem_dead_ended_by_its_own_pruned_twigs_is_not_itself_a_spur():
    """The `enthusiast_logo` extremity drop, isolated to the graph rule.

    `_prune_spurs` repeats so a twig behind a twig still goes. But erasing a
    spur leaves its branch node standing, and a node left holding one arm
    turns that arm into a dead end — through no thinning of its own. Measured
    again against the same bar, a real limb dies on the second pass.

    On the real fixture that is a 3.3 mm tab, and the margin is one raster
    pixel: the left bracket's stem is 19.000 px against a 19.4770 px bar, its
    mirror twin's 20.000 px against 19.1152 px. Same artwork, 0.06% apart in
    area, opposite outcomes. Retuning the bar cannot fix that — it only moves
    which shape sits on the knife edge — so the stem is exempted instead.
    """
    bar = 6.0                       # both twigs (2.83 px) under it, stem (5 px) under it too
    m = _tab_skeleton()
    stage6_satin._prune_spurs(m, bar)

    assert m[9, 6] == 0 and m[8, 7] == 0, "twig A is genuine noise and must still go"
    assert m[11, 6] == 0 and m[12, 7] == 0, "twig B is genuine noise and must still go"
    assert [int(m[10, x]) for x in range(1, 6)] == [1, 1, 1, 1, 1], \
        "the stem lost its branches to pass 1 and was then eaten as a spur itself"
    assert m[0:21, 0].all(), "the body is free at both ends and was never a spur"


def test_a_short_dead_end_hanging_off_a_body_is_still_pruned():
    """The control for the exemption above: a twig that was ALWAYS a dead end
    is ordinary noise and must still go, or the guard has simply disabled
    pruning."""
    m = np.zeros((21, 9), np.uint8)
    m[0:21, 0] = 1
    for x in range(1, 6):
        m[10, x] = 1                # identical stem, but nothing forks off it
    stage6_satin._prune_spurs(m, 6.0)

    assert [int(m[10, x]) for x in range(1, 6)] == [0, 0, 0, 0, 0], \
        "a stem that was a dead end from the start is a spur like any other"
    assert m[0:21, 0].all()


# --- the house cross angle for lettering (2026-08-26) -----------------------
# Kent, on a sewn Becker Marine logo: *"When doing lettering, fill angle should
# be the same (for almost every block style font like this). Why is the 'N'
# running Vertically?"* Every cross used to come from that stroke's OWN spine
# tangent, so each letter -- and each stroke inside a letter -- chose in
# isolation. Measured on that artwork, EMB-Bot's letter angles were
# statistically indistinguishable from random; the pro's were not.


def _axis_offsets(pts, house_deg):
    """How far each cross sits from the stroke axis it has to span, in deg."""
    import numpy as np
    a = np.asarray(pts, dtype=float)
    v = np.diff(a, axis=0)
    L = np.hypot(v[:, 0], v[:, 1])
    keep = L > 0.2
    return np.degrees(np.arctan2(v[keep, 1], v[keep, 0])) % 180.0


def test_no_house_angle_is_byte_identical_to_not_passing_one():
    """The default has to be invisible. Every golden in the suite is pinned to
    the per-stroke tangent, so `satin_angle_deg=None` must not merely look the
    same -- it must be the same points."""
    from shapely.geometry import Polygon as _P
    from digitizer_core.stage6_satin import satin_shape

    poly = _P([(0, 0), (3, 0), (3, 40), (0, 40)])
    a, _ = satin_shape(poly, "s1", underlay_style="none", trim_at_mm=99.0)
    b, _ = satin_shape(poly, "s1", underlay_style="none", trim_at_mm=99.0,
                       angle_deg=None)
    assert [list(r.points) for r in a] == [list(r.points) for r in b]


def test_the_house_angle_actually_moves_the_crosses():
    """A vertical bar's crosses are horizontal either way, so prove the knob
    works on a bar the house angle genuinely disagrees with: a 60 deg bar,
    whose own tangent would give 150 deg crosses, asked for 0."""
    import numpy as np
    from shapely import affinity
    from shapely.geometry import Polygon as _P
    from digitizer_core.stage6_satin import satin_shape

    bar = affinity.rotate(_P([(0, 0), (3, 0), (3, 40), (0, 40)]), 60 - 90,
                          origin="centroid")
    stock, _ = satin_shape(bar, "s", underlay_style="none", trim_at_mm=99.0)
    housed, _ = satin_shape(bar, "s", underlay_style="none", trim_at_mm=99.0,
                            angle_deg=0.0)
    sm = np.median(_axis_offsets([p for r in stock for p in r.points], 0.0))
    hm = np.median(_axis_offsets([p for r in housed for p in r.points], 0.0))
    # Stock follows the bar (crosses ~150 deg); housed is pulled toward 0/180.
    assert abs((sm - 150 + 90) % 180 - 90) < 25, f"stock crosses at {sm:.0f}"
    assert abs((hm - 0 + 90) % 180 - 90) < 25, f"housed crosses at {hm:.0f}"


def test_the_clamp_never_lets_a_cross_run_along_its_own_stroke():
    """THE load-bearing guard. A satin cross has to SPAN its column; forced
    parallel to the stroke it would lie along it and the column collapses.
    `_clamp_to_span` holds the house angle where the stroke allows and leans
    toward it, capped, where it does not -- so no orientation, anywhere in
    180 deg, may come out under the floor."""
    import math

    from digitizer_core.stage6_satin import (SATIN_HOUSE_MIN_SPAN_DEG,
                                             _clamp_to_span)

    worst = 90.0
    for axis in range(0, 180):
        out = math.degrees(_clamp_to_span(0.0, math.radians(axis))) % 180.0
        worst = min(worst, abs((out - axis + 90) % 180 - 90))
    assert worst >= SATIN_HOUSE_MIN_SPAN_DEG - 1e-6, (
        f"a cross came out {worst:.1f} deg off its own axis")


def test_a_stroke_that_can_span_the_house_angle_gets_it_exactly():
    """"Held loosely" is not "approximately". Where the stroke can span it
    within the lean cap, the house angle is passed through untouched -- the
    lean only ever engages on the strokes that would degenerate. A cross is
    the same cross 180 deg round, so compare mod 180."""
    import math

    from digitizer_core.stage6_satin import _clamp_to_span

    for axis in (90, 75, 61):          # all >= the 60 deg floor from 0
        out = math.degrees(_clamp_to_span(0.0, math.radians(axis))) % 180.0
        assert min(out, 180.0 - out) < 1e-9, (
            f"house angle was moved on a {axis} deg stroke that could span it")


def test_a_bar_along_the_house_axis_takes_its_own_perpendicular_with_no_side():
    """The stitch-angle rule (2026-09-03). A bar running ALONG the house's
    axis -- an E's arm under a horizontal house -- cannot lean toward the
    house on either side without that side being chosen by tangent noise:
    the old clamp gave 89.9 deg and 90.1 deg bars +45 and -45, and the
    smoothing swept the arm through the flip. Every font sews such a bar
    perpendicular (86 fonts: 3.0 deg off), and perpendicular has no side."""
    import math

    from digitizer_core.stage6_satin import _clamp_to_span

    def off_perp(axis_deg: float) -> float:
        out = math.degrees(_clamp_to_span(0.0, math.radians(axis_deg)))
        return abs((out - (axis_deg + 90.0) + 90.0) % 180.0 - 90.0)

    assert off_perp(90.0) < 1e-9
    assert off_perp(89.9) < 0.1 and off_perp(90.1) < 0.1, (
        off_perp(89.9), off_perp(90.1))
    assert off_perp(0.0) < 1e-9, "a stem square to the house is the house"


def test_the_lean_fades_continuously_from_the_cap_to_the_perpendicular():
    """No orientation may see a JUMP in its cross angle: a stroke that bends
    from 50 to 70 deg under a 0 deg house must sweep its cross, not snap it.
    Sweep every axis in twentieth-degree steps and bound the step in the
    output at 0.2 deg (the fade's own slope is 1.5 deg per deg, so 0.075) --
    and pin the shape of the fade: full cap at the cap, 22.5 on a true
    45 deg diagonal (inside the pro's p75 26 and the fonts' 29.5), zero
    along the house axis."""
    import math

    from digitizer_core.stage6_satin import (SATIN_HOUSE_MIN_SPAN_DEG,
                                             _clamp_to_span)

    cap = 90.0 - SATIN_HOUSE_MIN_SPAN_DEG
    prev = None
    for tenth in range(0, 3600):
        axis = tenth / 20.0
        out = math.degrees(_clamp_to_span(0.0, math.radians(axis))) % 180.0
        if prev is not None:
            step = abs((out - prev + 90.0) % 180.0 - 90.0)
            assert step < 0.2, f"cross jumped {step:.2f} deg at axis {axis}"
        prev = out

    def lean(axis_deg: float) -> float:
        out = math.degrees(_clamp_to_span(0.0, math.radians(axis_deg)))
        return abs((out - (axis_deg + 90.0) + 90.0) % 180.0 - 90.0)

    assert abs(lean(90.0 - cap) - cap) < 1e-6      # the cap's edge: full cap
    assert abs(lean(45.0) - cap * 0.75) < 1e-6     # a 45 deg diagonal: 22.5
    assert lean(90.0) < 1e-9                        # along the axis: none


def test_a_leaned_column_keeps_its_perpendicular_pitch():
    """Density compensation for lean (2026-09-03, Pulse's rule). An upright
    bar under a house 25 deg off its perpendicular holds the house exactly,
    so every cross leans 25 deg. Stationed at the bare spacing along the
    spine those threads would sit cos(25) = 10% too close across the column
    -- and at the 48 deg the retired bisector put on an N, 33% too close:
    the "pile" measured on enthusiast_logo (thread pitch 0.152 mm against
    the 0.200 an unleaned column lays; Fremont's bars the same).

    Measure the pitch ACROSS the threads: it must be what the stock
    (unhoused) column gets -- HALF the station spacing, because a zigzag
    lays two threads per station, out and back -- and the housed column
    must carry FEWER crosses by about cos(lean), not the same count. The
    count is held to 10%, not 1%: a leaned cross meets the boundary on a
    different float path from the ray that measured it, and `place`'s
    containment fallback then dents a few rails 15% and the outer-rail
    refinement re-inserts a station there (a pre-existing dent -- a ROTATED
    stock bar shows it on one whole rail -- recorded as its own defect)."""
    import math

    import numpy as np
    from shapely.geometry import Polygon as _P
    from digitizer_core import machine
    from digitizer_core.stage6_satin import satin_shape

    lean = 25.0
    bar = _P([(0, 0), (3, 0), (3, 40), (0, 40)])

    def perpendicular_pitch(runs) -> float:
        pts = np.asarray([p for r in runs for p in r.points], dtype=float)
        # Every full-length segment is a thread across the column (out and
        # back); the gap between consecutive threads, measured square to
        # the thread, is the pitch the fabric sees.
        mids = (pts[:-1] + pts[1:]) / 2.0
        vec = pts[1:] - pts[:-1]
        full = np.hypot(vec[:, 0], vec[:, 1]) > 2.0
        mids, vec = mids[full], vec[full]
        vec /= np.hypot(vec[:, 0], vec[:, 1])[:, None]
        nrm = np.stack([-vec[:, 1], vec[:, 0]], axis=1)
        gaps = np.abs(np.einsum("ij,ij->i", mids[1:] - mids[:-1], nrm[:-1]))
        gaps = gaps[(gaps > 0.1) & (gaps < 1.0)]
        return float(np.median(gaps))

    stock, _ = satin_shape(bar, "s", underlay_style="none", trim_at_mm=99.0)
    housed, _ = satin_shape(bar, "s", underlay_style="none", trim_at_mm=99.0,
                            angle_deg=90.0 - lean)
    thread_pitch = machine.SATIN_SPACING_MM / 2.0
    p_stock = perpendicular_pitch(stock)
    p_house = perpendicular_pitch(housed)
    assert abs(p_stock - thread_pitch) < 0.02, p_stock
    assert abs(p_house - thread_pitch) < 0.02, (
        f"leaned column packs thread at {p_house:.3f} mm, not {thread_pitch}")
    n_stock = sum(len(r.points) for r in stock)
    n_house = sum(len(r.points) for r in housed)
    expect = n_stock * math.cos(math.radians(lean))
    assert n_house < n_stock, "the leaned column did not shed any crosses"
    assert abs(n_house - expect) < 0.10 * n_stock, (n_stock, n_house, expect)


def test_resample_by_pitch_keeps_both_ends_and_spreads_by_cos_lean():
    """`_resample_by_pitch` on its own: ends kept (open and closed), the
    along-spine step is spacing / cos(lean) inside the cap, a zero-lean
    spine gets `_resample`'s station count, and degenerate inputs come back
    unchanged."""
    import math

    from digitizer_core.stage6_satin import _resample, _resample_by_pitch

    spacing = 0.4
    line = [(0.0, 0.0), (20.0, 0.0)]
    n = max(2, int(math.ceil(20.0 / spacing)))            # satin_stroke's own count
    zero = _resample_by_pitch(_resample(line, n), [0.0] * n, spacing)
    assert len(zero) == n and zero[0] == (0.0, 0.0) and zero[-1] == (20.0, 0.0)

    lean = math.radians(30.0)
    leaned = _resample_by_pitch(_resample(line, n), [lean] * n, spacing)
    steps = [math.dist(a, b) for a, b in zip(leaned, leaned[1:])]
    assert leaned[0] == (0.0, 0.0) and leaned[-1] == (20.0, 0.0)
    assert abs(max(steps) - spacing / math.cos(lean)) < 0.02, max(steps)
    assert abs(min(steps) - spacing / math.cos(lean)) < 0.02, min(steps)

    ring = [(5.0 * math.cos(t), 5.0 * math.sin(t))
            for t in [2 * math.pi * i / 80 for i in range(81)]]   # closed: last == first
    out = _resample_by_pitch(ring, [lean] * 81, spacing)
    assert out[0] == ring[0] and out[-1] == ring[-1]
    assert len(out) < 81, "a leaned ring should shed stations"

    assert _resample_by_pitch([(1.0, 1.0)], [0.0], spacing) == [(1.0, 1.0)]
    assert _resample_by_pitch([(1.0, 1.0), (1.0, 1.0)], [0.0, 0.0], spacing) == \
        [(1.0, 1.0), (1.0, 1.0)]


# --- the Goldman corner join (2026-09-03, stitch-angle rule pass 2) --------


def _L_shape(stem_w=1.2, foot_w=1.2, height=10.0, width=6.0):
    from shapely.geometry import Polygon as _P
    stem = _P([(0, 0), (stem_w, 0), (stem_w, height), (0, height)])
    foot = _P([(0, 0), (width, 0), (width, foot_w), (0, foot_w)])
    return stem.union(foot)


def test_an_L_corner_is_one_stroke_with_one_goldman_corner():
    """Two straight members meeting at 90 deg with a sharp inside corner: the
    skeleton walks stem and foot as one chain that turns ~90 deg at the apex.
    Before the join that turn was under `_SPLIT_TURN_DEG` and sewed as a
    fan; now it is a `Stroke.corners` entry -- the chain stays ONE stroke
    (sequencing, underlay and the travel web see what they always saw) with
    the longer member (the stem) owning the corner."""
    from digitizer_core.stage6_satin import extract_strokes

    strokes, half, _field = extract_strokes(_L_shape())
    joined = [st for st in strokes if st.corners]
    assert len(joined) == 1, [(len(s.spine), s.corners) for s in strokes]
    st = joined[0]
    assert len(st.corners) == 1
    apex_i, before_owns = st.corners[0]
    # the longer member owns: whichever side of the apex is the 10 mm stem
    import math
    left = sum(math.dist(a, b) for a, b in zip(st.spine[:apex_i + 1], st.spine[1:apex_i + 1]))
    right = sum(math.dist(a, b) for a, b in zip(st.spine[apex_i:], st.spine[apex_i + 1:]))
    assert before_owns == (left >= right)


def test_a_bend_of_the_same_angle_is_not_a_corner():
    """The 1,436 : 18 corpus rule: a column turning round a BEND keeps sewing
    through. Same 90 deg of turn as the L, spread round an arc with no
    reflex vertex on the boundary -- no corner, no cut, one plain stroke."""
    import math

    from shapely.geometry import LineString
    from digitizer_core.stage6_satin import extract_strokes

    arc = [(8.0 * math.cos(t), 8.0 * math.sin(t))
           for t in [math.pi / 2 * i / 30 for i in range(31)]]
    bend = LineString(arc).buffer(0.6, cap_style=2, join_style=1)
    strokes, _half, _field = extract_strokes(bend)
    assert len(strokes) == 1 and not strokes[0].corners, \
        [(len(s.spine), s.corners) for s in strokes]


def test_the_joined_corner_has_no_fan_and_no_bare_corner_square():
    """What the join is for. Rendered as thread, the corner square of the L
    (the stem_w x foot_w square at the apex) is covered by the owner's
    column, and every cross within a column width of the apex sits within
    20 deg of ITS OWN member's perpendicular -- the fan that swept the old
    corner through 90 deg over ~±1.5 mm is gone. The stock (pre-join)
    behaviour is reproduced for the comparison by clearing the corner."""
    import math

    import numpy as np
    from shapely.geometry import LineString, Polygon as _P
    from shapely.ops import unary_union
    from digitizer_core.stage6_satin import extract_strokes, satin_stroke, strip_splits

    poly = _L_shape()
    strokes, half, field = extract_strokes(poly)
    st = next(s for s in strokes if s.corners)

    def crosses(points):
        # Rails alternate A, B, A, B: even segments are the square crosses,
        # odd ones the return legs that lean one spacing forward (~20 deg on
        # a 1.2 mm column) -- only the crosses say where the column points.
        pts = np.asarray(strip_splits(list(points)), dtype=float)
        vec = pts[1:] - pts[:-1]
        length = np.hypot(vec[:, 0], vec[:, 1])
        keep = (length > 0.6) & (np.arange(len(vec)) % 2 == 0)
        mids = (pts[:-1] + pts[1:])[keep] / 2.0
        ang = np.degrees(np.arctan2(vec[keep, 1], vec[keep, 0])) % 180.0
        return mids, ang

    def fan_count(points):
        mids, ang = crosses(points)
        apex = np.array([half, half])
        near = np.hypot(mids[:, 0] - apex[0], mids[:, 1] - apex[1]) < 2.0 * half + 0.5
        # a stem cross is horizontal (0), a foot cross vertical (90)
        off = np.minimum(np.abs((ang[near] + 90) % 180 - 90),
                         np.abs((ang[near] - 90 + 90) % 180 - 90))
        return int((off > 20.0).sum()), int(near.sum())

    joined = satin_stroke(poly, st, half, field)
    from dataclasses import replace
    fanned = satin_stroke(poly, replace(st, corners=[]), half, field)
    fan_j, n_j = fan_count(joined)
    fan_f, n_f = fan_count(fanned)
    assert fan_f >= 3, f"the un-joined corner should fan ({fan_f} of {n_f})"
    assert fan_j == 0, f"joined corner still fans: {fan_j} of {n_j} crosses off-axis"

    square = _P([(0, 0), (1.2, 0), (1.2, 1.2), (0, 1.2)])
    thread = unary_union([LineString(joined).buffer(0.2, cap_style=1, join_style=1)])
    bare = square.difference(thread).area / square.area
    assert bare < 0.10, f"corner square {100 * bare:.0f}% bare"


def test_a_tapered_tip_is_not_a_corner():
    """ribbon_curve's golden: a taper curls in its last millimetre and its
    point is a convex vertex. The join's reflex-corner test must not fire,
    or the golden moves (it did, 1001 -> 987, in the first draft)."""
    from shapely.geometry import Polygon as _P
    from digitizer_core.stage6_satin import extract_strokes

    taper = _P([(0, -1.0), (12.0, -1.0), (16.0, 0.3), (12.0, 1.0), (0, 1.0)])
    strokes, _half, _field = extract_strokes(taper)
    assert not any(s.corners for s in strokes)
