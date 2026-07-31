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

    Crosses are still identified by LENGTH rather than position: an earlier
    version keyed off a fixed parity, scored a clean curved ribbon at 30%, and
    graded nothing. Anything built on that had to be re-measured.
    """
    out: list[float] = []
    for run in runs:
        pts = run.points
        segs = [(math.dist(pts[i], pts[i + 1]), pts[i], pts[i + 1])
                for i in range(len(pts) - 1)]
        segs = [s for s in segs if s[0] > 1e-9]
        if len(segs) < 4:
            continue
        longest = sorted(s[0] for s in segs)[int(len(segs) * 0.9)]
        angs = [math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
                for L, a, b in segs if L >= longest * 0.5]
        # Drop the first and last cross: a column deliberately finishes with a
        # square-end terminal stitch onto the cap CORNERS, which is diagonal to
        # the column by design. Counting it as spray measures the feature, not
        # the defect — it is why a straight bar scored 23.9 deg.
        angs = angs[1:-1]
        for x, y in zip(angs, angs[2:]):
            d = abs(x - y) % 180.0
            out.append(min(d, 180.0 - d))
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

    A straight column's crosses are parallel by definition, and the mean
    rotation is 0.41 deg. Exactly ONE cross breaks that: the column enters from
    the cap face at the bar's mid-height and reaches the near rail diagonally
    ((0.00, 1.08) -> (0.41, 0.17) on this fixture, 23.9 deg). That is a
    cap-entry artifact, not the spray this module was rebuilt to fix, and it is
    pinned here so it cannot quietly become two.
    """
    satin, _, _ = _satin_runs(BAR)
    rot = _cross_rotations(satin)
    assert rot, "no crosses measured"
    assert sum(r > 15.0 for r in rot) <= 1, f"more than one bad cross: {rot}"
    assert sum(rot) / len(rot) <= 1.0, f"bar wobbles on average {sum(rot) / len(rot):.2f} deg"


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

    The interior count is pinned separately and is not a fan. Two neighbouring
    outer-rail intervals near the middle of the bend run 0.98 and 1.00 mm
    against the 0.40 target — one station's worth of coverage missing at a
    single spot. It predates the emitter's rail ordering (measured identical
    on both) and it is pinned here so it cannot spread; the earlier version of
    this test stepped through the points by two, saw only half the same-rail
    intervals, and never reported it.
    """
    from digitizer_core import PipelineConfig, digitize

    _result, plan = digitize(TESTDATA / "ribbon_curve.png",
                             PipelineConfig(target_width_mm=80.0,
                                            garment_id="left_chest"))
    runs = [r for _b, r in plan.iter_runs() if r.kind == "satin"]
    assert len(runs) == 1, f"the ribbon should sew as one column, got {len(runs)}"
    pts = runs[0].points
    assert len(pts) > 200, "the curved ribbon should sew as one long column"

    # Points come out A, B, A, B ... so p[i] and p[i+2] are consecutive
    # penetrations on the same rail, and stepping i by ONE covers both rails
    # and every interval on them. Cross number is i // 2.
    ncross = len(pts) // 2
    wide = [i for i in range(len(pts) - 2)
            if math.dist(pts[i], pts[i + 2]) > 2 * machine.SATIN_SPACING_MM]
    head = [i for i in wide if i // 2 < 5]
    tail = [i for i in wide if i // 2 >= ncross - 5]
    interior = [i for i in wide if i not in head and i not in tail]

    assert len(head) <= 2, f"the start cap is fanning: {head}"
    assert len(tail) <= 2, f"the end cap is fanning: {tail}"
    assert len(interior) <= 2, \
        f"{len(interior)} over-wide rail gaps away from the caps: {interior}"


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
