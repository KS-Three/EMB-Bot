"""`cfg.lettering_columns` -- lettering as Columns cut from the letter's own
outline (`digitizer_core/outline_cut.py`, `digitizer_core/columns.py`; the
lettering-lane architecture, `docs/lettering-architecture-rd-2026-10-07.md`
§5 L4/L5, Kent's picks 2026-10-07).

Contracts pinned:

- the flag is built OFF, and OFF is byte-identical: the stage 7 hook and
  the `_sews_satin` branch are both behind the flag, so a run with the
  flag unset and one with it set False produce the same plan on a real
  lettering fixture, point for point;
- the cut is the construction the spike settled on synthetic letters: an I
  is one straight column, an L cuts once into two straight columns, a T
  cuts its stem from its bar, an O is one ring column whose rails are the
  outer ring and the counter;
- the Column engine honours the rules it claims: every station's ends sit
  on the piece's outline before the push and a pull outside it after, a
  cross under the floor is dropped and counted, a column's runs are linked
  by the satin tier's sew-or-jump rule, and the nearest-next order enters
  a column at the end nearer the needle;
- ON, through `digitize()` on Becker at 100 mm, every text-tagged MARINE
  letter sews satin runs from this lane (the plan counter says so), no
  letter sews a fill run, and the letters' satin runs and trims both fall
  against the skeleton tier -- the numbers the R&D report measured
  (34 runs / 42 trims -> 17 / 15 on 2026-10-07) are pinned as bounds, not
  as exact values, because the cut moves with the trace.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.columns import Column, column_runs, lettering_columns_shape
from digitizer_core.outline_cut import (REFINE_TRIGGER, _overlong, build_column, letter_columns,
                                        stroke_width)
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
BECKER = TESTDATA / "becker_marine_logo.png"


def _rect(x0, y0, x1, y1):
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def test_flag_is_built_off():
    assert PipelineConfig().lettering_columns is False


# ---------------------------------------------------------------- the cut

def test_an_i_is_one_straight_column():
    cut = letter_columns(_rect(0, 0, 2, 12))
    assert cut.cuts == []
    assert len(cut.columns) == 1 and not cut.unsewn
    col = cut.columns[0]
    assert col.kind == "straight"
    assert abs(abs(col.axis[1]) - 1.0) < 1e-6          # upright
    assert len(col.stations) >= 3
    for a, b in col.stations:
        assert abs(math.dist(a, b) - 2.0) < 0.05        # every cross spans the stem


def test_an_l_cuts_once_into_two_straight_columns():
    # stem 2 x 12, foot 8 x 2
    L = _rect(0, 0, 2, 12).union(_rect(0, 10, 8, 12))
    cut = letter_columns(L)
    assert len(cut.cuts) == 1
    assert len(cut.columns) == 2 and not cut.unsewn
    axes = sorted(abs(c.axis[1]) for c in cut.columns)
    assert axes[0] < 0.01 and axes[1] > 0.99             # one along x, one along y
    # the pieces tile the letter
    area = sum(c.piece.area for c in cut.columns)
    assert abs(area - cut.poly.area) < 0.2


def test_a_t_cuts_its_stem_from_its_bar():
    T = _rect(4, 0, 6, 12).union(_rect(0, 0, 10, 2))
    cut = letter_columns(T)
    assert len(cut.columns) == 2 and not cut.unsewn
    kinds = {c.kind for c in cut.columns}
    assert kinds == {"straight"}
    # the bar's column runs along x, the stem's along y
    assert sorted(abs(c.axis[1]) for c in cut.columns)[0] < 0.01


def test_an_o_is_one_ring_column_between_outline_and_counter():
    outer = Point(0, 0).buffer(6, 64)
    O = Polygon(outer.exterior.coords, [Point(0, 0).buffer(3.5, 64).exterior.coords])
    cut = letter_columns(O)
    assert cut.cuts == []
    assert len(cut.columns) == 1 and not cut.unsewn
    col = cut.columns[0]
    assert col.kind == "ring"
    ext, hole = cut.poly.exterior, cut.poly.interiors[0]
    for a, b in col.stations:
        da, db = ext.distance(Point(a)), hole.distance(Point(b))
        assert min(da, ext.distance(Point(b))) < 0.15 and min(db, hole.distance(Point(a))) < 0.15


def test_stations_sit_on_the_outline_and_pitch_follows_spacing():
    poly = _rect(0, 0, 3, 20)
    cut = letter_columns(poly, pitch_mm=0.2)
    col = cut.columns[0]
    for a, b in col.stations:
        assert poly.exterior.distance(Point(a)) < 1e-6 and poly.exterior.distance(Point(b)) < 1e-6
    ys = sorted(a[1] for a, _ in col.stations)
    gaps = [q - p for p, q in zip(ys, ys[1:])]
    assert all(abs(g - 0.2) < 1e-6 for g in gaps)


# -------------------------------------------------------------- the engine

def test_pull_lands_on_the_rails_and_the_floor_drops_a_cross():
    poly = _rect(0, 0, 2, 12)
    cut = letter_columns(poly)
    runs, report = column_runs(cut.columns, cut.poly, "s", trim_at_mm=3.0, pull_mm=0.3)
    assert not report["empty"] and report["columns"] == 1
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert len(sat) == 1
    xs = sorted({round(p[0], 3) for p in sat[0].points})
    assert xs[0] == pytest.approx(-0.3, abs=1e-6) and xs[-1] == pytest.approx(2.3, abs=1e-6)
    # a column narrower than the cross floor sews nothing, and says so
    thin = Column(stations=[((0, y), (0.3, y)) for y in (0.0, 0.5, 1.0, 1.5)],
                  piece=_rect(0, 0, 0.3, 2), kind="straight", axis=(0, 1), width_mm=0.3)
    runs2, rep2 = column_runs([thin], _rect(0, 0, 0.3, 2), "s", trim_at_mm=3.0)
    assert rep2["empty"] and rep2["thin_crosses"] == 4 and rep2["columns_unsewn"] == 1


def test_underlay_precedes_its_column_and_the_column_sews_back_over_it():
    poly = _rect(0, 0, 2, 12)
    cut = letter_columns(poly)
    runs, report = column_runs(cut.columns, cut.poly, "s", trim_at_mm=3.0, underlay_style="center")
    assert [r.kind for r in runs] == [stitches.UNDERLAY, stitches.SATIN]
    ul, sat = runs
    assert not sat.jump                                  # the hop is inside the letter and short
    assert math.dist(ul.points[-1], sat.points[0]) < 3.0
    assert all(abs(p[0] - 1.0) < 1e-6 for p in ul.points)   # centre run down the stem


def test_nearest_next_enters_the_second_column_at_its_near_end():
    # two separate stems side by side: the needle finishes stem 1 at its top
    # and must start stem 2 at ITS top, not travel to its bottom.
    a = letter_columns(_rect(0, 0, 2, 12)).columns[0]
    b = letter_columns(_rect(4, 0, 6, 12)).columns[0]
    runs, _ = column_runs([a, b], _rect(0, 0, 6, 12), "s", trim_at_mm=3.0, start_near=(1, 0))
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert len(sat) == 2
    end1, start2 = sat[0].points[-1], sat[1].points[0]
    assert abs(end1[1] - start2[1]) < 1.0


def test_split_comb_breaks_a_wide_cross():
    poly = _rect(0, 0, 8, 20)
    cut = letter_columns(poly)
    runs, _ = column_runs(cut.columns, cut.poly, "s", trim_at_mm=3.0,
                          split_above_mm=machine.SPLIT_SATIN_ABOVE_MM)
    sat = [r for r in runs if r.kind == stitches.SATIN][0]
    longest = max(math.dist(p, q) for p, q in zip(sat.points, sat.points[1:]))
    assert longest < machine.SPLIT_SATIN_ABOVE_MM


def test_shape_entry_point_reports_the_cut():
    L = _rect(0, 0, 2, 12).union(_rect(0, 10, 8, 12))
    runs, report = lettering_columns_shape(L, "s", trim_at_mm=3.0)
    assert report["cuts"] == 1 and report["columns"] == 2 and not report["empty"]
    assert {r.kind for r in runs} <= {stitches.SATIN, stitches.TRAVEL}
    assert sum(r.kind == stitches.SATIN for r in runs) == 2


# --------------------------------------------------------------- the walk

def _jumps(runs):
    return [r for r in runs if r.jump]


def test_an_h_walks_as_one_component_with_no_jump_inside_the_letter():
    """Two stems and a bar: the bar's ends land mid-stroke on both stems, so
    the span graph is one component with four odd nodes; the postman
    duplicates one span (walked as an underpath) and the trail sews every
    span once as satin with the needle never leaving the letter."""
    H = _rect(0, 0, 2, 12).union(_rect(8, 0, 10, 12)).union(_rect(0, 5, 10, 7))
    runs, report = lettering_columns_shape(H, "h", trim_at_mm=3.0, start_near=(1, 0))
    assert not report["empty"] and report["columns"] == 3
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert sum(len(r.points) for r in sat) > 0
    assert _jumps(runs) == []                 # one continuous walk
    # the whole letter is sewn: the zigzags, as 0.4 mm thread, cover the
    # letter inside its own edge (the triangles between adjacent crosses at
    # the rails are the zigzag's own, not a missing span)
    sewn = unary_union([LineString(r.points).buffer(0.3) for r in sat])
    inner = H.buffer(-0.3)
    assert sewn.intersection(inner).area >= 0.97 * inner.area
    # the duplicated span is walked as an underpath, not sewn twice as satin
    assert any(r.kind == stitches.TRAVEL for r in runs)


def test_a_t_walks_bar_then_stem_without_a_jump():
    T = _rect(4, 0, 6, 12).union(_rect(0, 0, 10, 2))
    runs, report = lettering_columns_shape(T, "t", trim_at_mm=3.0, start_near=(0, 0))
    assert report["columns"] == 2 and _jumps(runs) == []


# ------------------------------------------------------ the junction tuck

def test_a_t_sews_its_stem_first_and_tucks_it_under_the_bar():
    """The stem butts the bar mid-stroke: the walk starts at the stem's free
    end so the stem is sewn before the bar, and its satin runs on under the
    bar by the satin tier's junction tuck -- the bar then covers the seam.
    The bar is one unbroken satin run, not two halves meeting at the stem."""
    T = _rect(4, 0, 6, 12).union(_rect(0, 0, 10, 2))
    cut = letter_columns(T)
    # the needle within trim of the stem's foot, the columns in either
    # order: the postman must not pair the junction with the foot (that
    # doubled the stem and split the bar when the stem was column 0)
    for cols in (cut.columns, cut.columns[::-1]):
        runs, report = column_runs(cols, cut.poly, "t", trim_at_mm=3.0, start_near=(5, 12))
        assert report["junctions"] == 1 and report["tucks"] == 1
        sat = [r for r in runs if r.kind == stitches.SATIN]
        assert len(sat) == 2
        stem, bar = sat
        assert max(y for _, y in stem.points) > 10 and max(y for _, y in bar.points) <= 2.0
        assert min(y for _, y in stem.points) <= 2.0 - 0.3      # under the bar by the tuck
        assert min(y for _, y in stem.points) >= 1.0             # never past the bar's middle
        assert max(x for x, _ in bar.points) - min(x for x, _ in bar.points) > 9


def test_a_butt_sewn_after_its_stroke_reaches_the_cut_and_stops():
    """An H's bar has no free end, so it may sew after a stem it butts: that
    end is a plain butt, extended to the cut line (its last station sat up
    to a pitch short of it) and no further than one pitch past it."""
    H = _rect(0, 0, 2, 12).union(_rect(8, 0, 10, 12)).union(_rect(0, 5, 10, 7))
    runs, report = lettering_columns_shape(H, "h", trim_at_mm=3.0, start_near=(1, 0))
    assert report["junctions"] == 2
    sat = [r for r in runs if r.kind == stitches.SATIN]
    bar = [r for r in sat if max(x for x, _ in r.points) - min(x for x, _ in r.points) > 4]
    assert len(bar) == 1
    xs = [x for x, _ in bar[0].points]
    # the stems' inner edges are x = 2 and x = 8: both bar ends reach them,
    # the butt by less than a pitch, the tuck by no more than half a stem
    assert report["tucks"] == 1
    assert min(xs) <= 2.0 and max(xs) >= 8.0
    assert min(xs) >= 2.0 - 0.4 and max(xs) <= 8.0 + 1.0
    assert all(H.buffer(0.11).covers(Point(p)) for p in bar[0].points)


def test_two_separate_stems_are_two_components_joined_by_one_jump():
    a = letter_columns(_rect(0, 0, 2, 12)).columns[0]
    b = letter_columns(_rect(6, 0, 8, 12)).columns[0]
    poly = _rect(0, 0, 2, 12).union(_rect(6, 0, 8, 12))
    runs, report = column_runs([a, b], poly, "s", trim_at_mm=3.0, start_near=(1, 0))
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert len(sat) == 2 and report["jumps"] == 1
    # the second component is entered at the end nearer where the first finished
    end1, start2 = sat[0].points[-1], sat[1].points[0]
    assert abs(end1[1] - start2[1]) < 1.0


def test_the_walk_ends_toward_the_next_shape():
    """An H has four free stem ends; the postman pairs two and the trail runs
    between the other two. Stage 7 hands every shape the point where the
    next shape starts (`cfg.satin_exit_toward_next`, the satin tier's rule
    since 09-19), and the walk reserves its two ends for it: start nearest
    the needle, end nearest the next shape. Without it the walk ended where
    the pairing left it and the hop into the next letter was a trim
    (Fremont's entry trims rose 15 -> 21 under the lane)."""
    H = _rect(0, 0, 2, 12).union(_rect(8, 0, 10, 12)).union(_rect(0, 5, 10, 7))
    for nxt, corner in (((9, -0.5), (9, 0)), ((1, 12.5), (1, 12)), ((9, 12.5), (9, 12))):
        runs, report = lettering_columns_shape(H, "h", trim_at_mm=3.0, start_near=(1, -0.5), end_near=nxt)
        assert _jumps(runs) == []
        assert math.dist(runs[-1].points[-1], corner) < 1.5, nxt


# ------------------------------------------------------- the E/F stem cut

def _rounded_e():
    """A bold E whose slot ends are ROUNDED, as a traced E at 146 px is: the
    junction rules find at most one corner on it. Stem 0..4, arms to x = 12
    (the middle one to 10, short of the hull), slots 2 tall."""
    stem = _rect(0, 0, 4, 14)
    arms = [_rect(4, 0, 12, 4), _rect(4, 5.5, 10, 8.5), _rect(4, 10, 12, 14)]
    e = unary_union([stem] + arms)
    # round the slot ends: fill a small fillet at each inner corner
    fillets = [Point(4.5, y).buffer(0.6) for y in (4.5, 5.0, 9.0, 9.5)]
    return unary_union([e] + fillets).buffer(0.0)


def test_an_e_is_cut_into_a_stem_and_its_arms():
    """The slot backs are depth peaks along the hull pocket's outline, and
    the line through them is the stem's inner edge: three cuts, one per arm
    root, and the stem is ONE straight column running the letter's height.
    Without this the E sewed as three horizontal slabs, each a fanning L."""
    from digitizer_core.outline_cut import slot_cuts
    E = _rounded_e()
    cut = letter_columns(E)
    slots = [c for c in cut.cuts if c[2] == "slot"]
    assert len(slots) == 3
    assert all(abs(c[0][0] - c[1][0]) < 0.3 for c in slots)          # all on one upright line
    tall = [c for c in cut.columns if c.piece.bounds[3] - c.piece.bounds[1] > 12]
    assert len(tall) == 1 and tall[0].kind == "straight"
    assert tall[0].piece.bounds[2] < 6                               # the stem, not stem + arm
    assert len(cut.columns) == 4
    W = cut.W
    assert all(math.dist(a, b) <= 1.6 * W for c in cut.columns for a, b in c.stations)


def test_no_stem_cut_on_an_m_a_c_or_a_t():
    """One peak per pocket (C, T), or two whose line crosses a notch or
    leaves more than a stroke behind it (an M's bottom pocket reads as an
    E on its side): no slot cut."""
    from digitizer_core.outline_cut import slot_cuts
    M = Polygon([(0, 0), (2, 0), (5, 4), (8, 0), (10, 0), (10, 12), (8, 12), (8, 4.5),
                 (5, 8.5), (2, 4.5), (2, 12), (0, 12)])
    C = Point(0, 0).buffer(6).difference(Point(0, 0).buffer(4)).difference(_rect(2, -2, 7, 2))
    T = _rect(4, 0, 6, 12).union(_rect(0, 0, 10, 2))
    for name, shape in (("M", M), ("C", C), ("T", T)):
        cuts, _ = slot_cuts(shape, stroke_width(shape))
        assert cuts == [], name


def test_the_same_letter_cuts_the_same_every_time():
    """The spine is skimage's medial axis, which breaks ties with a random
    generator unless seeded; unseeded, an open ring cut twelve times in one
    process gave two different station sets (and a gaulke letter moved
    0.013 mm between calls). Every other medial_axis call in the engine
    passes rng=0; so does this one now."""
    import hashlib
    arc = Point(0, 0).buffer(6).difference(Point(0, 0).buffer(4)).difference(
        Polygon([(0, 0), (9, -1), (9, 4)]))

    def h(cut):
        return hashlib.md5(repr([[(tuple(map(float, a)), tuple(map(float, b))) for a, b in c.stations]
                                 for c in cut.columns]).encode()).hexdigest()

    assert len({h(letter_columns(arc)) for _ in range(12)}) == 1


# --------------------------------------------------------------- density

def test_each_rail_gets_a_needle_every_satin_spacing():
    """The engine's satin puts a penetration every SATIN_SPACING_MM on EACH
    rail (the flat zigzag A1, B1, A2, B2: both ends of every station).
    MARINE's I measured 0.40 mm per rail under the satin tier and 0.80 under
    the lane's first wiring, which put one end down per station. Pinned on
    a plain stem: both rails at the spacing, within a tenth."""
    stem = _rect(0, 0, 2, 12)
    runs, _ = lettering_columns_shape(stem, "stem", trim_at_mm=3.0)
    pts = [p for r in runs if r.kind == stitches.SATIN for p in r.points]
    left = sorted(p[1] for p in pts if p[0] < 0.5)
    right = sorted(p[1] for p in pts if p[0] > 1.5)
    for rail in (left, right):
        gaps = [b - a for a, b in zip(rail, rail[1:])]
        gaps = [g for g in gaps if g > 1e-6]
        med = sorted(gaps)[len(gaps) // 2]
        assert abs(med - machine.SATIN_SPACING_MM) < 0.1 * machine.SATIN_SPACING_MM
        assert len(rail) >= 12 / machine.SATIN_SPACING_MM * 0.9


# ---------------------------------------------------- slanted terminals

def _sewn(runs, r=0.3):
    return unary_union([LineString(x.points).buffer(r) for x in runs if x.kind == stitches.SATIN])


def test_a_straight_arm_fans_its_slanted_end():
    """An arm whose free end is cut on a slant (Becker's E arms): crosses
    square to the axis stop where the slant begins and the tip used to sew
    bare. Now the last square cross pivots on the shorter rail's end and
    fans along the slant to the tip."""
    arm = Polygon([(0, 0), (10, 0), (12, 2), (0, 2)])
    col = letter_columns(arm).columns[0]
    assert col.kind == "straight"
    runs, _ = lettering_columns_shape(arm, "arm", trim_at_mm=3.0)
    tip = Polygon([(10, 0), (12, 2), (10, 2)]).buffer(-0.2)
    assert tip.difference(_sewn(runs)).area < 0.05 * tip.area
    # the fan's crosses all share the shorter rail's end as their pivot
    fan = [st for st in col.stations if st[0][0] > 10.0 + 1e-6 or st[1][0] > 10.0 + 1e-6]
    assert len(fan) >= 3 and all(math.dist(st[0], (10, 0)) < 0.5 for st in fan)


def test_a_curved_piece_keeps_its_slanted_tip():
    """A quarter-circle band whose end is cut on a slant: the spike squared
    a free end by cutting the longer rail back to the shorter, which left
    every slanted tip short. Unsquared, the DTW pairing fans the longer
    rail, and the last cross lies on the slant itself."""
    import numpy as np
    a0 = math.atan2(1.0, 6.0)
    outer = [(6 * math.cos(t), 6 * math.sin(t)) for t in np.linspace(a0, math.pi / 2, 40)]
    inner = [(4 * math.cos(t), 4 * math.sin(t)) for t in np.linspace(math.pi / 2, 0, 40)]
    band = Polygon(outer + inner)                    # the closing edge IS the slant
    assert band.is_valid
    col = letter_columns(band).columns[0]
    assert col.kind == "curved"
    runs, _ = lettering_columns_shape(band, "band", trim_at_mm=3.0)
    tip = band.buffer(-0.15).intersection(box(3.5, -1, 7, 1.5))
    assert tip.difference(_sewn(runs)).area < 0.05 * tip.area
    last = col.stations[-1] if col.stations[-1][0][1] < col.stations[0][0][1] else col.stations[0]
    slant = LineString([(4, 0), outer[0]])
    assert slant.distance(Point(last[0])) < 0.15 and slant.distance(Point(last[1])) < 0.15


def test_a_round_cap_stays_square():
    """A symmetric shrink (a round cap, a taper) draws both sides in alike
    and is not a slant: it keeps the scan's square crosses rather than
    fanning from one arbitrary side."""
    import numpy as np
    cap = [(1 + math.cos(t), 10 + math.sin(t)) for t in np.linspace(0, math.pi, 24)]
    stem = Polygon([(0, 0), (2, 0)] + cap)            # (2, 10) round the cap to (0, 10)
    assert stem.is_valid
    col = letter_columns(stem).columns[0]
    assert col.kind == "straight"
    xs = {round(a[0], 3) for a, _ in col.stations} | {round(b[0], 3) for _, b in col.stations}
    # no shared pivot: no x value is hit by more than three station ends
    from collections import Counter
    ends = Counter(tuple(round(v, 3) for v in p) for st in col.stations for p in st)
    assert max(ends.values()) <= 2


def test_an_uncut_n_reports_the_diagonal_it_cannot_scan():
    """Stem and diagonal left as one piece scan as one upright column: each
    scanline meets the piece twice and only the longer segment is
    stationed. The rest is reported as dropped length and counts as
    over-long, so the second look cuts the piece instead of sewing the
    diagonal only where it happens to be the longer segment (Fremont's N,
    2.1 mm2 bare)."""
    N = Polygon([(0, 0), (1, 0), (1, 5.5), (4, 0), (5, 0), (5, 8), (4, 8), (4, 2.5), (1, 8), (0, 8)])
    W = stroke_width(N)
    col = build_column(N, [], W, 0.4)
    assert col is not None and col.kind == "straight"
    assert col.dropped_mm > 10.0
    long_mm, total_mm = _overlong(col, W)
    assert long_mm / total_mm > REFINE_TRIGGER
    runs, report = lettering_columns_shape(N, "n", trim_at_mm=3.0)
    inner = N.buffer(-0.15)
    assert inner.difference(_sewn(runs)).area < 0.03 * inner.area


# ------------------------------------------------------------- end to end

def _plan_points(plan):
    return [(b.thread_index, r.kind, r.jump, r.trim, tuple(r.points))
            for b in plan.blocks for r in b.runs]


def _letter_census(result, plan):
    ids = {r.shape_id for r in result.regions if r.meta.get("text_candidate")}
    satin = trims = fills = 0
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id not in ids:
                continue
            satin += r.kind == stitches.SATIN
            fills += r.kind == stitches.FILL
            trims += bool(r.trim)
    return ids, satin, trims, fills


@pytest.fixture(scope="module")
def becker_off():
    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6)
    return digitize(str(BECKER), cfg)


def test_off_is_byte_identical(becker_off):
    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                         lettering_columns=False)
    _, plan = digitize(str(BECKER), cfg)
    assert _plan_points(plan) == _plan_points(becker_off[1])


def test_on_every_marine_letter_sews_columns_with_fewer_runs_and_trims(becker_off):
    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                         lettering_columns=True)
    result, plan = digitize(str(BECKER), cfg)
    ids_on, satin_on, trims_on, fills_on = _letter_census(result, plan)
    ids_off, satin_off, trims_off, fills_off = _letter_census(*becker_off)
    assert ids_on == ids_off and len(ids_on) >= 6
    assert fills_on == 0
    # every MARINE letter (the six that sew; the band's five are holes of the
    # band and sew nothing on either arm) carries satin from this lane
    sewn = {r.shape_id for b in plan.blocks for r in b.runs if r.kind == stitches.SATIN}
    assert len(sewn & ids_on) == 6
    assert satin_on < satin_off and trims_on < trims_off
    assert satin_on <= 24 and trims_on <= 24       # 17 / 15 measured 2026-10-07; 34 / 42 off


def test_every_engine_medial_axis_call_is_seeded():
    """`skimage.morphology.medial_axis` breaks ties from OS entropy unless
    given `rng`. `outline_cut._spine_ends` called it unseeded and the Column
    lane sewed a different design on every run (golden_tee 8,312 / 8,318 /
    8,319 / 8,315 stitches over four runs, 2026-10-07) -- caught because two
    eye-pairs renders of one arm disagreed. Pinned on the source, since a
    tie only shows on some shapes and a run-twice test can pass by luck."""
    import ast
    from pathlib import Path

    core = Path(__file__).resolve().parents[1] / "digitizer_core"
    unseeded = []
    for f in sorted(core.rglob("*.py")):          # subpackages (calibration/) too
        tree = ast.parse(f.read_text(encoding="utf-8"))
        # `from skimage.morphology import medial_axis as ma` renames the callee
        names = {"medial_axis"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                names |= {a.asname for a in node.names if a.name == "medial_axis" and a.asname}
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call)
                    and getattr(node.func, "id", getattr(node.func, "attr", None)) in names):
                seeded = any(k.arg == "rng" and not (isinstance(k.value, ast.Constant)
                                                     and k.value.value is None)
                             for k in node.keywords)
                if not seeded:
                    unseeded.append(f"{f.relative_to(core)}:{node.lineno}")
    assert unseeded == []


def test_columns_on_golden_tee_is_deterministic_end_to_end():
    """Run the whole pipeline twice with `lettering_columns` ON and compare the
    sewn result. The source pin above catches the unseeded call; this catches
    any OTHER nondeterminism that reaches the plan (golden_tee varied by 7
    stitches over four runs before the seeding fix)."""
    from tools.flip_sheet import _stitch_digest

    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                         lettering_columns=True)
    src = str(TESTDATA / "photo" / "logo_golden_tee.jpg")
    _, a = digitize(src, cfg)
    _, b = digitize(src, cfg)
    assert _stitch_digest(a) == _stitch_digest(b)
    assert _plan_points(a) == _plan_points(b)
