"""Stage 6 — the fill itself, tested on geometry with known answers.

A plain rectangle is used deliberately: every property below has an arithmetic
expected value on a rectangle, so a failure points at the fill rather than at
an argument about what the right answer was.
"""
from __future__ import annotations

import math

import pytest
from shapely import affinity
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from digitizer_core import machine
from digitizer_core.stage6_fill import (
    _TRIM_STITCH_EQUIVALENT,
    _brick_row_points,
    _inset_ring,
    _order_cost,
    _reorder_for_fewer_cuts,
    _score,
    _chevron_row_points,
    _columns,
    _crosshatch_fill_paths,
    _fill_paths,
    _row_points,
    _row_points_at_phase,
    _row_spans,
    _stagger_phase,
    _stagger_slots,
    _wave_row_points,
    best_fill_angle_deg,
    principal_angle_deg,
    stitch_shape,
    travel_path,
)

RECT = Polygon([(0, 0), (40, 0), (40, 20), (0, 20)])
RING = Polygon(
    [(math.cos(t / 60 * 2 * math.pi) * 15, math.sin(t / 60 * 2 * math.pi) * 15) for t in range(60)],
    [[(math.cos(-t / 60 * 2 * math.pi) * 7, math.sin(-t / 60 * 2 * math.pi) * 7) for t in range(60)]],
)


def _rows_of(points):
    rows: dict[float, list[float]] = {}
    for x, y in points:
        rows.setdefault(round(y, 3), []).append(round(x, 3))
    return rows


def test_row_count_and_spacing_match_the_requested_density():
    paths = _fill_paths(RECT, 0.0, 0.4, 4.0, 4)
    rows = _rows_of(paths[0])
    ys = sorted(rows)
    # 20 mm of height at 0.4 mm spacing, allowing for the half-row inset.
    assert len(ys) == pytest.approx(20 / 0.4, abs=1)
    gaps = {round(b - a, 3) for a, b in zip(ys, ys[1:])}
    assert gaps == {0.4}


def test_penetrations_are_staggered_and_realign_every_fourth_row():
    paths = _fill_paths(RECT, 0.0, 0.4, 4.0, 4)
    rows = _rows_of(paths[0])
    ys = sorted(rows)
    # Interior penetrations only: both row ends land on the edge by design.
    interior = [sorted(x for x in rows[y] if 0.001 < x < 39.999) for y in ys[:5]]
    phases = [round(xs[0] % 4.0, 3) for xs in interior]
    assert len(set(phases[:4])) == 4, f"rows should not share a phase: {phases}"
    assert phases[4] == phases[0], "the pattern must repeat every 4 rows"


def test_no_stitch_is_longer_than_the_fill_stitch_length():
    runs, _ = stitch_shape(RECT, "S1", angle_deg=0.0, row_mm=0.4, stitch_mm=4.0,
                           underlay_style="none", trim_at_mm=3.0)
    longest = max(math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:]))
    assert longest <= 4.0 + 1e-6


def test_no_penetration_lands_beside_the_hole_the_needle_just_made():
    """The interior grid is anchored globally, so the first grid point inside a
    row sits an arbitrary fraction of a stitch past the edge. Keeping it put two
    penetrations tenths of a millimetre apart — thread shredding, a hot needle,
    and a lumpy edge where the fill should be crisp."""
    for x0 in (0.0, 0.13, 0.37, 0.61, 0.94, 2.5):
        for row in range(8):
            xs = [p[0] for p in _row_points(x0, x0 + 17.0, 0.0, row, 4.0, 4,
                                            reverse=False)]
            gaps = [b - a for a, b in zip(xs, xs[1:])]
            assert min(gaps) >= machine.MIN_STITCH_MM - 1e-9, \
                f"row {row} from {x0}: {[round(g, 3) for g in gaps]}"

    # And on real shapes. Rows run horizontally at angle 0, so a step that
    # holds y is along a row and must clear the minimum; a step that changes y
    # is the turn between two rows, which is one row spacing by design. The
    # ring is here for its curved edge, where spans are every length at once.
    for name, poly in (("rect", RECT), ("ring", RING)):
        for path in _fill_paths(poly, 0.0, 0.4, 4.0, 4):
            for a, b in zip(path, path[1:]):
                if abs(b[1] - a[1]) > 1e-9:
                    continue                # a row turn, not a stitch
                d = abs(b[0] - a[0])
                if d < machine.TINY_STITCH_MM:
                    continue                # a whole row this short IS the tip
                assert d >= machine.MIN_STITCH_MM - 1e-9, \
                    f"{d:.3f} mm stitch along a row of the {name}"


def test_stagger_offsets_do_not_walk_the_holes_into_a_diagonal():
    """A stagger that advances one notch per row shifts every penetration the
    same distance sideways as the rows step down: the channel is not removed,
    only tilted, and light still runs along it. Consecutive rows must jump
    around the cycle, never march through it."""
    assert _stagger_slots(4) == (0, 2, 1, 3)
    assert sorted(_stagger_slots(8)) == list(range(8)), "still a permutation"

    paths = _fill_paths(RECT, 0.0, 0.4, 4.0, 4)
    rows = _rows_of(paths[0])
    ys = sorted(rows)
    firsts = [min(x for x in rows[y] if 0.001 < x < 39.999) for y in ys[:16]]
    steps = [round(b - a, 6) for a, b in zip(firsts, firsts[1:])]
    longest = run = 1
    for a, b in zip(steps, steps[1:]):
        run = run + 1 if b == a else 1
        longest = max(longest, run)
    assert longest < 3, f"holes march in a straight diagonal: {steps}"


def test_row_ends_land_on_the_shape_edge():
    """What makes an edge crisp. Regression: the tiny-stitch filter used to
    delete these, because a row turn is shorter than the filter's floor."""
    paths = _fill_paths(RECT, 0.0, 0.4, 4.0, 4)
    rows = _rows_of(paths[0])
    for y, xs in rows.items():
        assert min(xs) == pytest.approx(0.0, abs=1e-6)
        assert max(xs) == pytest.approx(40.0, abs=1e-6)


def test_nothing_is_sewn_across_a_hole():
    runs, report = stitch_shape(RING, "S1", angle_deg=0.0, row_mm=0.4, stitch_mm=4.0,
                                underlay_style="none", trim_at_mm=3.0)
    hole = Polygon(RING.interiors[0])
    # A chord between two points on a curved edge dips a hair inside it; a
    # stitch crossing the counter does not. 0.25 mm separates the two cases.
    deep = hole.buffer(-0.25)
    crossing = [
        (a, b) for r in runs for a, b in zip(r.points, r.points[1:])
        if LineString([a, b]).intersects(deep)
    ]
    assert crossing == [], f"{len(crossing)} stitches cross the counter"
    # A ring needs the needle up once: routing the last quarter of the way
    # round would mean running travel stitches back over fill that is already
    # down, and travel showing on top of finished stitching is worse than a
    # trim. What the design promises is that the lift is CUT, never left as a
    # float across the counter.
    lifted = [r for r in runs if r.jump]
    assert all(r.trim for r in lifted), "a needle lift this long must be trimmed"


def test_travel_prefers_a_straight_run_and_falls_back_to_the_edge():
    straight = travel_path(RECT, LineString(RECT.exterior.coords), (5, 5), (30, 15))
    assert straight is not None
    assert len(straight) >= 2
    assert all(RECT.buffer(0.01).covers(Point(p)) for p in straight)

    ring_path = LineString(RING.buffer(-0.6).exterior.coords)
    around = travel_path(RING, ring_path, (-11, 0), (11, 0))
    assert around is not None, "travel around a hole should follow the edge"
    hole = Polygon(RING.interiors[0]).buffer(-0.25)
    assert not LineString(around).intersects(hole)


# A shape that pinches in two under the travel inset: a solid lobe, a 1.0 mm
# neck (narrower than 2 * TRAVEL_INSET_MM, so it closes), and a U-shaped lobe
# whose two tips cannot see each other in a straight line. Real artwork does
# this constantly — becker_hat_small's wordmark is one region whose inset
# shatters into 59 pieces.
_DUMBBELL = unary_union([
    Polygon([(0, 0), (20, 0), (20, 20), (0, 20)]),            # solid lobe
    Polygon([(20, 9.5), (24, 9.5), (24, 10.5), (20, 10.5)]),  # 1.0 mm neck
    Polygon([(24, 0), (40, 0), (40, 20), (36, 20), (36, 10),
             (28, 10), (28, 20), (24, 20)]),                  # U lobe
])


def test_inset_ring_keeps_every_fragment_not_just_the_biggest():
    """`_inset_ring` took `max(inner.geoms, key=area)` and threw the rest away,
    so a shape that pinches apart under the inset got a travel guide covering
    only its largest piece. On becker_hat_small that was 28% of the shape, and
    every fill path in the other 72% had nothing to travel along — 17 of that
    design's 32 thread cuts.
    """
    inner = _DUMBBELL.buffer(-machine.TRAVEL_INSET_MM)
    assert inner.geom_type == "MultiPolygon" and len(inner.geoms) == 2, \
        "fixture must actually pinch apart under the inset"
    rings = _inset_ring(_DUMBBELL, machine.TRAVEL_INSET_MM)
    assert len(rings) == 2, "one guide per fragment, not just the largest"


def test_travel_follows_the_fragment_it_is_actually_in():
    """The two tips of the U are 12 mm apart with the notch between them, so
    the route has to go down one wall and up the other. It used to be handed
    the SOLID lobe's ring — a guide on the far side of a closed neck — and
    gave up, which the caller turns into a jump and, past trim_at_mm, a cut."""
    a, b = (26.0, 18.0), (38.0, 18.0)
    assert not _DUMBBELL.buffer(0.01).covers(LineString([a, b])), \
        "fixture must need the ring — a straight route would not exercise it"
    route = travel_path(_DUMBBELL, _inset_ring(_DUMBBELL, machine.TRAVEL_INSET_MM), a, b)
    assert route is not None, "travel must follow the fragment holding both ends"
    assert all(_DUMBBELL.buffer(0.05).covers(Point(p)) for p in route), \
        "a travel route may never leave the shape"


def test_travel_still_refuses_when_the_ends_are_in_different_fragments():
    """The counterpart guard. Keeping every fragment must not let travel walk
    across the closed neck — there is no thread-down path there, and inventing
    one would drag the needle over bare cloth."""
    route = travel_path(_DUMBBELL, _inset_ring(_DUMBBELL, machine.TRAVEL_INSET_MM),
                        (2.0, 18.0), (38.0, 18.0))
    assert route is None


def test_principal_angle_follows_the_long_axis():
    tall = Polygon([(0, 0), (5, 0), (5, 60), (0, 60)])
    assert abs(principal_angle_deg(tall)) == pytest.approx(90.0, abs=1.0)
    wide = Polygon([(0, 0), (60, 0), (60, 5), (0, 5)])
    assert abs(principal_angle_deg(wide)) == pytest.approx(0.0, abs=1.0)


def _cols_at(poly: Polygon, angle_deg: float, row_mm: float = 0.4) -> int:
    rotated = affinity.rotate(poly, -angle_deg, origin=(0, 0), use_radians=False)
    return len(_columns(_row_spans(rotated, row_mm)))


def _diagonal_staircase() -> Polygon:
    """Six overlapping squares stepping diagonally — a shape whose long axis
    BY AREA is genuinely diagonal (so `principal_angle_deg` measuring 45deg
    there is correct, not a bug), but whose STAIR STRUCTURE means sewing
    rows along that diagonal forks/merges constantly (13 columns measured),
    while rows nearly perpendicular to the stairs cross the whole shape in
    one unbroken sweep (1 column measured). Exactly the gap
    `best_fill_angle_deg` closes: a real long axis that is nonetheless a bad
    row direction for THIS shape's structure.
    """
    step, size = 4.0, 5.0
    squares = [Polygon([(i * step, i * step), (i * step + size, i * step),
                        (i * step + size, i * step + size), (i * step, i * step + size)])
              for i in range(6)]
    return unary_union(squares)


def test_best_fill_angle_deg_finds_a_row_direction_pca_misses():
    stairs = _diagonal_staircase()
    pca = principal_angle_deg(stairs)
    assert pca == pytest.approx(45.0, abs=0.5), "sanity: the long axis by area really is diagonal"
    pca_cols = _cols_at(stairs, pca)
    assert pca_cols > 10, "sanity: sewing straight along the diagonal really does fork/merge a lot"

    chosen = best_fill_angle_deg(stairs, 0.4)
    chosen_cols = _cols_at(stairs, chosen)
    assert chosen != pytest.approx(pca, abs=0.1), "the sweep must pick something other than plain PCA here"
    assert chosen_cols == 1, "a near-perpendicular row direction crosses this stair shape in one column"
    assert chosen_cols < pca_cols


def test_best_fill_angle_deg_never_does_worse_than_plain_pca():
    """Including PCA's own angle as one of the swept candidates means the
    result can only tie or beat it, never lose to it — checked on every
    fixture shape already in this file, not just the diagonal staircase
    built to demonstrate an improvement."""
    for poly in (RECT, RING, _diagonal_staircase()):
        pca_cols = _cols_at(poly, principal_angle_deg(poly))
        chosen_cols = _cols_at(poly, best_fill_angle_deg(poly, 0.4))
        assert chosen_cols <= pca_cols


def test_best_fill_angle_deg_matches_pca_exactly_when_pca_is_already_optimal():
    """RECT's PCA angle (0deg, the long axis of a plain rectangle) already
    gives the minimum possible column count (1) — the sweep must return
    that EXACT angle, not a same-column-count-but-different candidate, so a
    shape that was already fine keeps generating byte-identical output."""
    assert best_fill_angle_deg(RECT, 0.4) == pytest.approx(principal_angle_deg(RECT), abs=1e-9)


def test_stitch_shape_uses_the_swept_angle_when_none_is_given():
    """End-to-end: an explicit angle still wins (unchanged precedence), but
    angle_deg=None now resolves through best_fill_angle_deg instead of
    plain principal_angle_deg — checked by comparing the actual row
    direction each produces on the diagonal staircase, where the two
    genuinely disagree."""
    stairs = _diagonal_staircase()
    pca = principal_angle_deg(stairs)
    swept = best_fill_angle_deg(stairs, machine.FILL_ROW_MM)
    assert swept != pytest.approx(pca, abs=0.1)

    explicit_runs, _ = stitch_shape(stairs, "S1", angle_deg=pca, row_mm=machine.FILL_ROW_MM,
                                    stitch_mm=4.0, underlay_style="none", trim_at_mm=3.0)
    assert explicit_runs, "an explicit angle must still be honoured, not overridden by the sweep"

    auto_runs, auto_report = stitch_shape(stairs, "S1", angle_deg=None, row_mm=machine.FILL_ROW_MM,
                                          stitch_mm=4.0, underlay_style="none", trim_at_mm=3.0)
    assert auto_runs and not auto_report["empty"]
    # Fewer forced jumps at the swept angle: 13 columns' worth of forced
    # travel decisions collapses to 1 column's worth.
    explicit_jumps = sum(1 for r in explicit_runs if r.jump)
    auto_jumps = sum(1 for r in auto_runs if r.jump)
    assert auto_jumps <= explicit_jumps


def test_a_shape_too_narrow_to_fill_is_reported_not_silently_sewn():
    sliver = Polygon([(0, 0), (60, 0), (60, machine.MIN_FILL_WIDTH_MM * 0.6), (0, machine.MIN_FILL_WIDTH_MM * 0.6)])
    runs, report = stitch_shape(sliver, "S1", angle_deg=0.0, row_mm=0.4, stitch_mm=4.0,
                                underlay_style="none", trim_at_mm=3.0)
    assert report["too_thin"] is True
    assert runs, "flagged is not the same as skipped — it still has to be sewn"


# --- Cross-hatch fill (two angled tatami passes) ---------------------------

def _dominant_row_angle_deg(paths) -> float:
    """Length-weighted majority direction (mod 180) of every stitch segment
    across a list of paths — the row direction a pass actually swept,
    MEASURED from the emitted geometry rather than trusted from whatever
    angle argument was passed in. Row spans dwarf the short row-to-row turns
    in total length, so the bucket with the most length wins even though
    every row also contributes one turn segment near-perpendicular to it."""
    lengths: dict[int, float] = {}
    for path in paths:
        for a, b in zip(path, path[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            bucket = round(math.degrees(math.atan2(dy, dx)) % 180.0)
            lengths[bucket] = lengths.get(bucket, 0.0) + length
    return float(max(lengths, key=lengths.get))


def test_crosshatch_fill_paths_are_two_angularly_distinct_passes():
    """The core claim: cross-hatch is two REAL passes at 90 degrees apart,
    not the same rows emitted twice. A plain rectangle sews as exactly one
    column per pass, so the two elements of the returned list are pass 1 and
    pass 2 outright — no need to guess where one ends and the other begins."""
    paths = _crosshatch_fill_paths(RECT, 0.0, machine.FILL_ROW_MM, 4.0, 4)
    assert len(paths) == 2, "a plain rectangle sews one column per pass"
    angle0 = _dominant_row_angle_deg([paths[0]])
    angle1 = _dominant_row_angle_deg([paths[1]])
    assert angle0 == pytest.approx(0.0, abs=1.0), \
        f"pass 1 should sew rows along the 0deg fill angle, measured {angle0}"
    assert angle1 == pytest.approx(90.0, abs=1.0), \
        f"pass 2 should sew rows along angle+90, measured {angle1}"


def test_crosshatch_row_spacing_uses_the_widened_spacing_per_pass():
    """Each pass must individually run at row_mm * CROSSHATCH_ROW_SCALE_
    FACTOR, not the raw row_mm a plain single-pass tatami fill would use —
    measured the same way test_row_count_and_spacing_match_the_requested_
    density measures plain tatami's spacing, on each pass separately."""
    row_mm = 0.4
    expected = round(row_mm * machine.CROSSHATCH_ROW_SCALE_FACTOR, 3)
    assert expected != row_mm, "sanity: the scale factor must actually widen the spacing"

    paths = _crosshatch_fill_paths(RECT, 0.0, row_mm, 4.0, 4)
    assert len(paths) == 2

    # Pass 1's rows are horizontal (angle 0), so their spacing shows up as
    # gaps between distinct y values across the whole path.
    pass1_ys = sorted({round(p[1], 3) for p in paths[0]})
    pass1_gaps = {round(b - a, 3) for a, b in zip(pass1_ys, pass1_ys[1:])}
    assert pass1_gaps == {expected}, \
        f"pass 1 spacing should be {expected}, measured gaps {pass1_gaps}"

    # Pass 2's rows are vertical (angle 90), so their spacing shows up as
    # gaps between distinct x values instead.
    pass2_xs = sorted({round(p[0], 3) for p in paths[1]})
    pass2_gaps = {round(b - a, 3) for a, b in zip(pass2_xs, pass2_xs[1:])}
    assert pass2_gaps == {expected}, \
        f"pass 2 spacing should be {expected} too, measured gaps {pass2_gaps}"


def test_crosshatch_chains_pass_two_off_pass_ones_last_point():
    """`start_near` for the second pass is pass 1's own last point — the same
    handoff `stitch_shape` uses between its underlay and fill — so pass 2's
    column-entry ordering follows on from wherever pass 1 left the needle,
    not from a fresh top-left-corner start."""
    start = (5.0, 5.0)
    paths = _crosshatch_fill_paths(RECT, 0.0, machine.FILL_ROW_MM, 4.0, 4, start)
    assert len(paths) == 2
    entry = paths[0][-1]
    # A single-column shape only has one path to enter, from whichever of its
    # two ends is nearer `entry` — the observable proof that pass 2 was
    # planned FROM pass 1's exit rather than from `start` or from a bare
    # top-left default.
    assert math.dist(paths[1][0], entry) <= math.dist(paths[1][-1], entry)


def test_crosshatch_degrades_sensibly_on_a_too_thin_shape():
    """Same too_thin sliver `test_a_shape_too_narrow_to_fill_is_reported_not_
    silently_sewn` uses, run through `stitch_shape` at the crosshatch
    technique: the wider per-pass spacing must not crash or silently drop
    the shape — it still has to sew, and still has to say it's thin."""
    sliver = Polygon([(0, 0), (60, 0), (60, machine.MIN_FILL_WIDTH_MM * 0.6),
                      (0, machine.MIN_FILL_WIDTH_MM * 0.6)])
    runs, report = stitch_shape(sliver, "S1", angle_deg=0.0, row_mm=0.4, stitch_mm=4.0,
                                underlay_style="none", trim_at_mm=3.0,
                                technique="crosshatch")
    assert report["too_thin"] is True
    assert runs, "flagged is not the same as skipped — it still has to be sewn"

    # And on a shape thin enough that the WIDENED per-pass spacing genuinely
    # finds no row in one direction — pass 1 comes back empty while pass 2
    # (rows running the shape's long way) still sews — the direct function
    # must not raise, and must still fall back to whatever pass 2 finds.
    thinner = Polygon([(0, 0), (60, 0), (60, 0.3), (0, 0.3)])
    paths = _crosshatch_fill_paths(thinner, 0.0, 0.4, 4.0, 4)
    assert paths, "pass 2 alone should still sew something on this fixture"


# --- Wave fill (sinusoidal row wobble) --------------------------------------

def test_wave_row_points_leaves_the_two_row_ends_exactly_on_the_boundary():
    """Same edge-crispness invariant `test_row_ends_land_on_the_shape_edge`
    pins for plain tatami: whatever the wave does to the interior, x0/x1
    must come back untouched, at the row's own unperturbed y."""
    x0, x1, y, stitch_mm, staggers = 0.0, 60.0, 5.0, 3.0, 4
    for row_index in range(4):
        pts = _wave_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False)
        assert pts[0] == (x0, y)
        assert pts[-1] == (x1, y)


def test_wave_row_points_interior_y_matches_the_documented_sine_formula():
    """The exact claim `machine.WAVE_AMPLITUDE_MM`/`WAVE_LENGTH_MM`'s own
    comments make: interior y is y + WAVE_AMPLITUDE_MM * sin(2*pi*x/
    WAVE_LENGTH_MM + phase), phase 0 on even rows and pi on odd rows —
    checked against every interior point actually emitted, not trusted from
    the implementation."""
    x0, x1, y, stitch_mm, staggers = 0.0, 60.0, 5.0, 3.0, 4
    for row_index in range(4):
        pts = _wave_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False)
        phase = 0.0 if row_index % 2 == 0 else math.pi
        interior = pts[1:-1]
        assert interior, "sanity: a 60mm row at 3mm stitches must have interior points"
        for x, py in interior:
            expected = y + machine.WAVE_AMPLITUDE_MM * math.sin(
                2.0 * math.pi * x / machine.WAVE_LENGTH_MM + phase)
            assert py == pytest.approx(expected, abs=1e-9)


def test_wave_row_points_amplitude_is_bounded_and_actually_reached():
    """The wobble must never exceed WAVE_AMPLITUDE_MM (it would eat into the
    density budget the row spacing already committed to), and over a span
    several wavelengths long it must actually get close to that amplitude
    somewhere, not just theoretically allow it."""
    x0, x1, y, stitch_mm = 0.0, 60.0, 5.0, 0.5
    pts = _wave_row_points(x0, x1, y, 0, stitch_mm, 1, reverse=False)
    deltas = [py - y for _, py in pts[1:-1]]
    assert max(abs(d) for d in deltas) <= machine.WAVE_AMPLITUDE_MM + 1e-9
    assert max(deltas) > machine.WAVE_AMPLITUDE_MM * 0.9, \
        "60mm at a 4mm wavelength should sample near a peak somewhere"


def test_wave_row_points_measured_period_matches_wave_length_mm():
    """Independent of the formula-matching test above: find successive
    local maxima in the emitted y-offsets and confirm their x-spacing is
    WAVE_LENGTH_MM — measured from the data, the same 'don't trust the code
    path' discipline `test_crosshatch.py`'s `_dominant_row_angle_deg` holds
    itself to for crosshatch's own angle claim. stitch_mm=0.25 divides
    MIN_STITCH_MM's 1.0 mm floor exactly, so the interior grid samples at a
    clean, uniform 1.0 mm (the floor, not stitch_mm — `_row_points_at_
    phase` never accepts two penetrations closer than MIN_STITCH_MM) rather
    than a spacing that beats unevenly against the sine period."""
    x0, x1, y, stitch_mm = 0.0, 60.0, 5.0, 0.25
    pts = _wave_row_points(x0, x1, y, 0, stitch_mm, 1, reverse=False)
    xs = [x for x, _ in pts[1:-1]]
    ys = [py - y for _, py in pts[1:-1]]
    peaks = [xs[i] for i in range(1, len(xs) - 1) if ys[i] > ys[i - 1] and ys[i] > ys[i + 1]]
    assert len(peaks) >= 3, f"need several peaks over 60mm at a 4mm period, got {peaks}"
    gaps = [round(b - a, 2) for a, b in zip(peaks, peaks[1:])]
    for g in gaps:
        assert g == pytest.approx(machine.WAVE_LENGTH_MM, abs=0.05)


def test_wave_row_points_adjacent_rows_move_opposite_ways_at_the_same_x():
    """staggers=1 gives every row the identical interior x grid (no van der
    Corput offset), isolating the wave's own row-to-row phase flip: at any
    given x, row 0 and row 1 must move opposite ways — the mechanism that
    keeps the wave from stacking into a corrugated-cardboard look instead of
    reading as texture."""
    x0, x1, y, stitch_mm = 0.0, 60.0, 5.0, 3.0
    row0 = _wave_row_points(x0, x1, y, 0, stitch_mm, 1, reverse=False)
    row1 = _wave_row_points(x0, x1, y, 1, stitch_mm, 1, reverse=False)
    xs0 = [x for x, _ in row0[1:-1]]
    xs1 = [x for x, _ in row1[1:-1]]
    assert xs0 == xs1, "sanity: staggers=1 must align both rows' x grids"
    for (x, y0), (_, y1) in zip(row0[1:-1], row1[1:-1]):
        assert (y0 - y) == pytest.approx(-(y1 - y), abs=1e-9)


def test_wave_row_points_degenerate_rows_pass_through_unperturbed():
    """A row too short to hold an interior penetration (`_row_points`
    returns one point, or two) has nothing for the wave to perturb — must
    come back exactly as `_row_points` produced it, not crash on an
    interior slice that doesn't exist."""
    tiny = _wave_row_points(0.0, 0.2, 5.0, 0, 3.0, 4, reverse=False)
    assert tiny == _row_points(0.0, 0.2, 5.0, 0, 3.0, 4, reverse=False)
    two_point = _wave_row_points(0.0, 1.5, 5.0, 0, 3.0, 4, reverse=False)
    assert two_point == _row_points(0.0, 1.5, 5.0, 0, 3.0, 4, reverse=False)


def test_fill_paths_wave_technique_keeps_row_ends_on_the_edge_but_perturbs_interior():
    """Wired through `_fill_paths` (not called on `_wave_row_points`
    directly): row ends in the emitted column must still sit at exactly
    their row's own unperturbed y, while interior points must actually
    differ from it — the wiring-level version of the two unit tests above."""
    row_mm, stitch_mm, staggers = 2.0, 1.0, 4
    expected_ys = {round(y, 6) for _, y, _ in _row_spans(RECT, row_mm)}
    tatami_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers)
    wave_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers, technique="wave")
    assert wave_paths != tatami_paths, "wave technique must actually change the emitted path"

    edge_ys = {round(y, 6) for x, y in wave_paths[0] if abs(x - 0.0) < 1e-6 or abs(x - 40.0) < 1e-6}
    assert edge_ys, "must still land on the shape's own left/right edges"
    assert edge_ys <= expected_ys, "row ends must be unperturbed, not wave-shifted"

    interior_ys = {round(y, 6) for x, y in wave_paths[0] if 1e-6 < x < 40.0 - 1e-6}
    assert not (interior_ys <= expected_ys), "interior points must actually be perturbed"


# --- Chevron fill (zigzag row texture) --------------------------------------

def test_chevron_row_points_leaves_the_two_row_ends_exactly_on_the_boundary():
    x0, x1, y, stitch_mm, staggers = 0.0, 40.0, 5.0, 3.0, 4
    for row_index in range(3):
        pts = _chevron_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False)
        assert pts[0] == (x0, y)
        assert pts[-1] == (x1, y)


def test_chevron_row_points_alternates_amplitude_every_interior_stitch():
    """The exact claim `machine.CHEVRON_AMPLITUDE_MM`'s comment makes: every
    interior point sits at exactly +-CHEVRON_AMPLITUDE_MM off the row, and
    the sign flips every single interior stitch (period two stitches) —
    both measured directly off the emitted points."""
    x0, x1, y, stitch_mm, staggers = 0.0, 40.0, 5.0, 3.0, 4
    for row_index in range(3):
        pts = _chevron_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False)
        interior = pts[1:-1]
        assert len(interior) >= 4, "need several interior points to prove the alternation"
        offsets = [round(py - y, 6) for _, py in interior]
        assert all(abs(abs(o) - machine.CHEVRON_AMPLITUDE_MM) < 1e-9 for o in offsets), offsets
        signs = [1 if o > 0 else -1 for o in offsets]
        assert all(a != b for a, b in zip(signs, signs[1:])), \
            f"row {row_index}: sign must flip every interior stitch, got {signs}"
        assert signs[0] == 1, "first interior point starts +amplitude, by convention"


def test_chevron_row_points_degenerate_rows_pass_through_unperturbed():
    tiny = _chevron_row_points(0.0, 0.2, 5.0, 0, 3.0, 4, reverse=False)
    assert tiny == _row_points(0.0, 0.2, 5.0, 0, 3.0, 4, reverse=False)


def test_fill_paths_chevron_technique_keeps_row_ends_on_the_edge_but_perturbs_interior():
    row_mm, stitch_mm, staggers = 2.0, 1.0, 4
    expected_ys = {round(y, 6) for _, y, _ in _row_spans(RECT, row_mm)}
    tatami_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers)
    chevron_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers, technique="chevron")
    assert chevron_paths != tatami_paths

    edge_ys = {round(y, 6) for x, y in chevron_paths[0] if abs(x - 0.0) < 1e-6 or abs(x - 40.0) < 1e-6}
    assert edge_ys
    assert edge_ys <= expected_ys

    interior_ys = {round(y, 6) for x, y in chevron_paths[0] if 1e-6 < x < 40.0 - 1e-6}
    assert not (interior_ys <= expected_ys)


# --- Brick fill (2-phase running-bond stagger) ------------------------------

def test_brick_row_points_leaves_the_two_row_ends_exactly_on_the_boundary():
    x0, x1, y, stitch_mm, staggers = 0.0, 40.0, 5.0, 3.0, 4
    for row_index in range(4):
        pts = _brick_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False)
        assert pts[0] == (x0, y)
        assert pts[-1] == (x1, y)


def test_brick_row_points_use_exactly_the_documented_period_two_phase():
    """The exact claim: even rows' interior grid at phase 0, odd rows at
    phase stitch_mm/2. Checked by delegating to `_row_points_at_phase`
    directly at each expected phase, rather than hand-deriving the resulting
    x positions -- so this pins the PHASE RULE, not incidental grid
    arithmetic."""
    x0, x1, y, stitch_mm, staggers = 0.0, 40.0, 5.0, 3.0, 4
    for row_index, expected_phase in ((0, 0.0), (1, 1.5), (2, 0.0), (3, 1.5)):
        assert _brick_row_points(x0, x1, y, row_index, stitch_mm, staggers, reverse=False) == \
               _row_points_at_phase(x0, x1, y, expected_phase, stitch_mm, reverse=False)


def test_brick_row_points_diverges_from_the_van_der_corput_stagger():
    """Consecutive rows' interior grids must be offset by exactly
    stitch_mm/2 -- NOT the old van-der-Corput pattern `_row_points` uses.
    Row 2 is where the two rules provably diverge at the default
    FILL_STAGGERS=4: `_stagger_slots(4) == (0, 2, 1, 3)` puts row 2 at phase
    stitch_mm/4, while brick's own period-2 rule keeps it at phase 0."""
    x0, x1, y, stitch_mm, staggers = 0.0, 40.0, 5.0, 3.0, 4
    assert _stagger_phase(2, staggers, stitch_mm) == pytest.approx(stitch_mm / 4.0)
    old_row2 = _row_points(x0, x1, y, 2, stitch_mm, staggers, reverse=False)
    new_row2 = _brick_row_points(x0, x1, y, 2, stitch_mm, staggers, reverse=False)
    assert old_row2 != new_row2


def test_brick_row_points_ignores_the_staggers_argument():
    """Brick's phase rule is a plain function of row parity and stitch_mm
    only -- `staggers` is accepted purely to match every other row-point
    function's call signature (`_fill_paths` dispatches on one shared
    signature), and changing it must not change brick's own output."""
    x0, x1, y, stitch_mm = 0.0, 40.0, 5.0, 3.0
    a = _brick_row_points(x0, x1, y, 1, stitch_mm, 4, reverse=False)
    b = _brick_row_points(x0, x1, y, 1, stitch_mm, 8, reverse=False)
    assert a == b


def test_fill_paths_brick_technique_keeps_row_ends_on_the_edge_and_differs_from_tatami():
    row_mm, stitch_mm, staggers = 2.0, 1.0, 4
    expected_ys = {round(y, 6) for _, y, _ in _row_spans(RECT, row_mm)}
    tatami_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers)
    brick_paths = _fill_paths(RECT, 0.0, row_mm, stitch_mm, staggers, technique="brick")
    assert brick_paths != tatami_paths, "brick technique must actually change the emitted path"

    edge_ys = {round(y, 6) for x, y in brick_paths[0] if abs(x - 0.0) < 1e-6 or abs(x - 40.0) < 1e-6}
    assert edge_ys
    assert edge_ys <= expected_ys, "row ends must still land exactly on the shape edge"


def test_scanlines_start_inside_the_shape_not_on_its_edge():
    """A scanline exactly on a horizontal edge intersects it as a whole edge or
    as nothing, depending on float noise. The half-row inset avoids the case."""
    rows = _row_spans(RECT, 0.4)
    assert rows[0][1] > 0.0
    assert rows[-1][1] < 20.0
    # Row indices are spatial, so the stagger phase means the same thing on
    # every shape regardless of which scanlines happened to find geometry.
    assert [r[0] for r in rows] == list(range(len(rows)))


def test_row_spans_repairs_a_self_intersecting_polygon_instead_of_raising():
    """Stage 5's pull compensation can hand fill an invalid polygon.

    Stage 4 validates every region it emits (`stage4_vectorize` runs
    `make_valid`), so fill never used to guard. Pull compensation happens after
    that, and on `photo_sunset_backlit.png` at the DEFAULT 80 mm it produced a
    self-intersecting polygon; GEOS then raised TopologyException out of
    `_row_spans`' `intersection` and the whole digitize failed. At 80 mm only,
    on that one fixture, which is why a green suite never saw it.

    A bowtie is the minimal self-intersection. Before the guard this raised;
    the contract is that it returns spans for the repaired geometry. Verified
    load-bearing: reverting the guard fails this test with GEOSException.

    The guard's companion `is_empty` early-return is NOT pinned here -- no
    input was found that is invalid AND repairs to empty, and a test that
    passes with the guard reverted would be worse than no test at all.
    """
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    assert not bowtie.is_valid, "fixture must actually be invalid to test the guard"

    rows = _row_spans(bowtie, 1.0)

    assert rows, "expected spans from the repaired polygon, got none"
    for _i, y, spans in rows:
        for x0, x1 in spans:
            assert x1 >= x0
            assert bowtie.buffer(0).intersects(LineString([(x0, y), (x1, y)]))


# --- path-order selection (stage6_fill._reorder_for_fewer_cuts) --------------
#
# These pin the LOGIC rather than a stitch count on a real fixture, deliberately.
# Neither byte-identical golden exercises this code at all -- measured: 0 shapes
# accepted on `enthusiast_logo.png` and `logo_whitebg.png` -- so a green suite is
# no evidence about it, and a pinned count on a real fixture would break on every
# unrelated pipeline change instead.


def _slotted_shape():
    """A slot that nearly spans the shape: two lobes 8 mm apart in a straight
    line, but a ring detour past the travel budget. Crossing is unroutable;
    moving along a lobe is not."""
    poly = Polygon([(0, 0), (100, 0), (100, 40), (0, 40)],
                   [[(10, 8), (90, 8), (90, 12), (10, 12)]])
    return poly, _inset_ring(poly, machine.TRAVEL_INSET_MM), poly.buffer(0.01)


def test_reorder_prefers_a_reachable_path_over_a_nearer_unroutable_one():
    """The defect this whole change exists for.

    `_fill_paths` picks the next column by straight-line distance, so on a holed
    shape it repeatedly hops ACROSS a hole where travel cannot follow and
    `fill_region` must cut — when a path the same distance away on the same side
    would have cost nothing. The cut is manufactured by the choice.
    """
    poly, ring, slack = _slotted_shape()
    across = [(50.0, 14.0), (52.0, 14.0)]      # other lobe, 8 mm away
    same_lobe = [(58.0, 6.0), (60.0, 6.0)]     # same lobe, also 8 mm away
    first = [(48.0, 6.0), (50.0, 6.0)]
    last = [(20.0, 6.0), (22.0, 6.0)]
    entry = (46.0, 6.0)

    # The premise: equal distance, opposite routability.
    assert math.dist(first[-1], across[0]) == math.dist(first[-1], same_lobe[0])
    assert travel_path(poly, ring, first[-1], across[0], slack) is None
    assert travel_path(poly, ring, first[-1], same_lobe[0], slack) is not None

    incoming = [first, across, same_lobe, last]
    before = _order_cost(incoming, poly, ring, slack, entry, 3.0)
    out = _reorder_for_fewer_cuts(incoming, poly, ring, slack, entry, 3.0)
    after = _order_cost(out, poly, ring, slack, entry, 3.0)

    assert out[1][0] == same_lobe[0], "should follow the reachable path, not the nearer one"
    # Cuts are equal here (2 either way): the far lobe has to be reached
    # eventually and always costs one. The win on this geometry is travel --
    # 15 stitches down to 3 -- which is why the selector scores the combined
    # cost and not cuts alone. Asserting on cuts here would fail while the
    # code is working, which is how the first draft of this test read.
    assert _score(after) < _score(before), f"{before} -> {after}"


def test_reorder_pins_the_final_path_so_the_shape_exits_where_it_did():
    """`fill_region` hands the NEXT shape `runs[-1].points[-1]` as its entry, so
    moving this shape's exit silently changes that shape's cost — outside the
    comparison that approved this one. Per-design never-worse (Kent, 2026-08-21)
    does not follow from per-shape non-worsening without this."""
    poly, ring, slack = _slotted_shape()
    paths = [[(48.0, 6.0), (50.0, 6.0)], [(50.0, 14.0), (52.0, 14.0)],
             [(58.0, 6.0), (60.0, 6.0)], [(20.0, 6.0), (22.0, 6.0)]]
    out = _reorder_for_fewer_cuts(paths, poly, ring, slack, (46.0, 6.0), 3.0)
    assert out[-1] == paths[-1], "the last path must not move or flip"
    assert out[-1][-1] == paths[-1][-1], "exit point must be byte-identical"


def test_reorder_leaves_a_cut_free_order_untouched():
    """No cut to buy means nothing to win, and the walk is not paid for."""
    poly, ring, slack = _slotted_shape()
    paths = [[(20.0, 6.0), (22.0, 6.0)], [(30.0, 6.0), (32.0, 6.0)],
             [(40.0, 6.0), (42.0, 6.0)], [(50.0, 6.0), (52.0, 6.0)]]
    entry = (18.0, 6.0)
    assert _order_cost(paths, poly, ring, slack, entry, 3.0)[0] == 0
    assert _reorder_for_fewer_cuts(paths, poly, ring, slack, entry, 3.0) is paths


def test_score_prices_a_cut_at_the_trim_stitch_equivalent():
    """Kent set 25 stitches per trim (2026-08-21). One cut must be worth exactly
    that many travel stitches, or the cap is not the number he chose."""
    assert _score((1, 0.0)) == _TRIM_STITCH_EQUIVALENT
    assert _score((0, _TRIM_STITCH_EQUIVALENT)) == _score((1, 0.0))
    assert _score((1, 0.0)) < _score((0, _TRIM_STITCH_EQUIVALENT + 1))
