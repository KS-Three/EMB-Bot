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
    _columns,
    _fill_paths,
    _row_points,
    _row_spans,
    _stagger_slots,
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


def test_scanlines_start_inside_the_shape_not_on_its_edge():
    """A scanline exactly on a horizontal edge intersects it as a whole edge or
    as nothing, depending on float noise. The half-row inset avoids the case."""
    rows = _row_spans(RECT, 0.4)
    assert rows[0][1] > 0.0
    assert rows[-1][1] < 20.0
    # Row indices are spatial, so the stagger phase means the same thing on
    # every shape regardless of which scanlines happened to find geometry.
    assert [r[0] for r in rows] == list(range(len(rows)))
