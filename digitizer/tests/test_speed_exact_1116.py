"""The 2026-11-16 speed pass changes no number: each cut against the code it replaced.

Every function here was rewritten for speed only. Each test holds the new form
equal -- `==` on floats, not `approx` -- to the old one, restated in the test.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box

from digitizer_core import columns, outline_cut, stage2_quantize
from digitizer_core import stage6_border as border
from digitizer_core.stitches import StitchRun


# --- stage 2: the distinct-colour count ------------------------------------------------

@pytest.mark.parametrize("n, levels", [(1, 4), (500, 3), (20_000, 256), (20_000, 5)])
def test_distinct_colors_is_the_row_wise_unique(n, levels):
    rng = np.random.default_rng(n + levels)
    rgb = rng.integers(0, levels, size=(n, 3)).astype(np.uint8)
    assert stage2_quantize._distinct_colors(rgb) == len(np.unique(rgb, axis=0))


def test_distinct_colors_other_dtypes_take_the_old_call():
    rgb = np.array([[0.5, 0.25, 1.0], [0.5, 0.25, 1.0], [0.0, 0.0, 0.0]])
    assert stage2_quantize._distinct_colors(rgb) == 2


# --- the Column lane: rail samples and the pairing table -------------------------------

def test_along_is_interpolate_point_by_point():
    ring = Polygon([(0, 0), (7.3, 0.4), (9.1, 5.2), (3.3, 8.8), (-1.2, 4.1)]).exterior
    line = LineString([(0, 0), (1.7, 2.9), (4.4, 3.1), (4.5, 9.0)])
    for geom in (ring, line):
        dists = np.arange(0, geom.length + 0.05, 0.05)
        want = [geom.interpolate(t).coords[0] for t in dists]
        assert outline_cut._along(geom, dists) == want
    assert outline_cut._along(line, []) == []
    t0, L = 3.21, ring.length                                   # `ring_rails`' wrapped walk
    want = [ring.interpolate((t0 + t) % L).coords[0] for t in np.arange(0, L, 0.05)]
    assert outline_cut._along(ring, (t0 + np.arange(0, L, 0.05)) % L) == want


def _dtw_loop(D: np.ndarray) -> np.ndarray:
    """`_pair_rails`' table as it was filled until 2026-11-16."""
    n, m = D.shape
    C = np.full((n, m), np.inf)
    C[0, 0] = D[0, 0]
    for j in range(1, m):
        C[0, j] = C[0, j - 1] + D[0, j]
    for i in range(1, n):
        C[i, 0] = C[i - 1, 0] + D[i, 0]
        row, prev = C[i], C[i - 1]
        for j in range(1, m):
            row[j] = D[i, j] + min(prev[j], prev[j - 1], row[j - 1])
    return C


@pytest.mark.parametrize("n, m", [(1, 1), (1, 6), (6, 1), (2, 2), (3, 9), (9, 3), (40, 57), (61, 61)])
def test_dtw_cost_is_the_cell_loop(n, m):
    rng = np.random.default_rng(100 * n + m)
    D = rng.random((n, m)) * 3.0
    assert np.array_equal(outline_cut._dtw_cost(D), _dtw_loop(D))


def test_pair_rails_on_a_bend_is_unchanged_by_the_table():
    A = [(0.0, 0.0), (5.0, 0.0), (8.0, 3.0), (8.0, 9.0)]
    B = [(0.0, 1.2), (4.5, 1.2), (6.8, 3.5), (6.8, 9.0)]
    got = outline_cut._pair_rails(A, B, 0.4)
    assert len(got) > 20
    assert all(len(pa) == 2 and len(pb) == 2 for pa, pb in got)
    # monotone along both rails
    la, lb = LineString(A), LineString(B)
    sa = [la.project(Point(pa)) for pa, _ in got]
    sb = [lb.project(Point(pb)) for _, pb in got]
    assert sa == sorted(sa) and sb == sorted(sb)


# --- the Column lane: the sewn judge's knot count --------------------------------------

def _knots_loop(runs) -> tuple[int, int]:
    """`sewn_knots`' (short, crossed) as it was counted until 2026-11-16."""
    from digitizer_core.outline_cut import SEWN_SHORT_FRAC
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    sat = [np.asarray(strip_splits(strip_ties(list(r.points))), dtype=float)
           for r in runs if r.kind == "satin"]
    runs4 = [p for p in sat if len(p) >= 4]
    lines = [LineString(p) for p in runs4]
    short = crossed = 0
    for k, pts in enumerate(runs4):
        others = [ln for j, ln in enumerate(lines) if j != k]
        if not others:
            continue
        legs = [LineString([pts[i], pts[i + 1]]) for i in range(len(pts) - 1)]
        length = np.array([lg.length for lg in legs])
        real = length > 0.05
        if not real.any():
            continue
        med = float(np.median(length[real]))
        hit = set()
        for i in np.nonzero(real)[0]:
            for j in np.nonzero(real[i + 2:])[0] + i + 2:
                if legs[i].crosses(legs[j]):
                    hit.update((int(i), int(j)))
        for i in np.nonzero(real)[0]:
            m = legs[i].interpolate(0.5, normalized=True)
            if min(o.distance(m) for o in others) >= med:
                continue
            short += bool(length[i] < SEWN_SHORT_FRAC * med)
            crossed += int(i) in hit
    return short, crossed


def _zigzag(spine, width: float, pitch: float, rng, jitter: float) -> list[tuple[float, float]]:
    line = LineString(spine)
    pts = []
    for k, t in enumerate(np.arange(0.0, line.length, pitch)):
        p, q = line.interpolate(t), line.interpolate(min(line.length, t + 0.01))
        dx, dy = q.x - p.x, q.y - p.y
        d = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / d, dx / d
        side = 1.0 if k % 2 == 0 else -1.0
        w = width / 2.0 * side * (1.0 + jitter * rng.standard_normal())
        along = jitter * 2.0 * rng.standard_normal()
        pts.append((p.x + nx * w + dx / d * along, p.y + ny * w + dy / d * along))
    return pts


@pytest.mark.parametrize("seed", range(6))
def test_sewn_knots_counts_what_the_leg_loop_counted(seed):
    rng = np.random.default_rng(seed)
    runs = [
        StitchRun(points=_zigzag([(0, 0), (9, 0.5), (12, 6)], 1.6, 0.4, rng, 0.35), kind="satin"),
        StitchRun(points=_zigzag([(4, -3), (5, 2), (4.5, 8)], 1.4, 0.4, rng, 0.35), kind="satin"),
        StitchRun(points=_zigzag([(11, 5), (12, 6.2), (15, 6.5)], 1.2, 0.4, rng, 0.5), kind="satin"),
        StitchRun(points=[(0, 0), (30, 30)], kind="run"),
    ]
    _folds, short, crossed = outline_cut.sewn_knots(runs)
    assert (short, crossed) == _knots_loop(runs)
    if seed == 0:
        assert short + crossed > 0          # the fixture does knot: the count is not vacuous


# --- keylines: a cross no outline edge touches -----------------------------------------

def _outline() -> MultiPolygon:
    body = box(0, 0, 30, 18).difference(Point(8, 9).buffer(4.0, 24)).difference(box(16, 4, 26, 7))
    gear = Point(50, 9).buffer(7.0, 12).difference(Point(50, 9).buffer(3.0, 9))
    return MultiPolygon([body, gear])


def test_unobstructed_cross_is_the_overlay_wherever_it_answers():
    clamp = _outline()
    rng = np.random.default_rng(7)
    asked = answered = full = zero = 0
    rays = []
    for poly in clamp.geoms:                    # crosses cast from the outline itself
        for ring in [poly.exterior, *poly.interiors]:
            for t in np.arange(0.0, ring.length, 0.21):
                p, q = ring.interpolate(t), ring.interpolate((t + 0.05) % ring.length)
                d = math.hypot(q.x - p.x, q.y - p.y)
                if d < 1e-9:
                    continue
                nx, ny = -(q.y - p.y) / d, (q.x - p.x) / d
                for sign in (1.0, -1.0):
                    for width in (0.4, 1.5, 3.0):
                        rays.append((p.x, p.y, sign * nx, sign * ny, width))
                        # ... and a hair off it, as `band_thickness` casts them
                        rays.append((p.x + sign * nx * 1e-4, p.y + sign * ny * 1e-4,
                                     sign * nx, sign * ny, width))
    for _ in range(3000):                       # and from anywhere, any way
        a = rng.random() * 2.0 * math.pi
        rays.append((rng.random() * 62 - 2, rng.random() * 22 - 2, math.cos(a), math.sin(a),
                     rng.random() * 6.0))
    for px, py, nx, ny, width in rays:
        asked += 1
        got = border._cross_unobstructed(px, py, px + nx * width, py + ny * width, clamp)
        if got is None:
            continue
        answered += 1
        full += got > 0.0
        zero += got == 0.0
        assert got == border._exact_cross_overlay(px, py, nx, ny, width, clamp), (px, py, nx, ny, width)
        assert border._exact_cross(px, py, nx, ny, width, clamp) == got
    assert answered > 0.3 * asked and full > 100 and zero > 100


def test_unobstructed_cross_leaves_other_clamps_to_the_overlay():
    line = LineString([(0, 0), (5, 0)])
    assert border._cross_unobstructed(1.0, -1.0, 1.0, 1.0, line) is None
    assert border._cross_unobstructed(1.0, -1.0, 1.0, 1.0, Polygon()) is None
    bowtie = Polygon([(0, 0), (4, 4), (4, 0), (0, 4)])           # not valid
    assert border._cross_unobstructed(1.0, 0.5, 1.0, 1.5, bowtie) is None
    sq = box(0, 0, 4, 4)
    assert border._cross_unobstructed(1.0, 1.0, 1.0, 1.0 + 1e-6, sq) is None    # too short to read


# --- shaped bands: every sample's partner on the ring ----------------------------------

def _gear(teeth: int, r_in: float, r_out: float, n_ring: int, kinks: bool):
    """(band, hole): a toothed band round a coarse ring, the ring kinked or not."""
    outer = []
    for k in range(teeth * 4):
        a = 2.0 * math.pi * k / (teeth * 4)
        r = r_out if k % 4 in (1, 2) else r_out - 1.1
        outer.append((r * math.cos(a), r * math.sin(a)))
    ring = []
    for k in range(n_ring):
        a = 2.0 * math.pi * k / n_ring
        r = r_in * (1.0 + (0.004 if kinks and k % 7 == 3 else 0.0))
        ring.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(outer, [ring]), Polygon(ring)


@pytest.mark.parametrize("n_ring, kinks, block", [(59, True, 1_000_000), (59, True, 700),
                                                   (4, False, 1_000_000), (4, False, 300),
                                                   (180, False, 5_000)])
def test_square_partners_is_the_per_sample_reading(monkeypatch, n_ring, kinks, block):
    from digitizer_core import shaped_band as sb
    band, hole = _gear(17, 20.0, 23.5, n_ring, kinks)
    seen = []
    real = sb._square_partners

    def spy(*args):
        seen.append(args)
        return real(*args)
    monkeypatch.setattr(sb, "_square_partners", spy)
    monkeypatch.setattr(sb, "_PARTNER_BLOCK", block)
    sb._read_band(band, hole)       # a square ring's band is too thick to sew; its reading still runs
    assert len(seen) == 1
    P, nearest, S3, R3, LO3, HI3, longest, total = seen[0]
    want = np.array([sb._square_partner_alone(i, *seen[0]) for i in range(len(P))])
    got = real(*seen[0])
    assert np.array_equal(got, want)
    if n_ring > 4:
        assert (got != np.asarray(nearest, float)).sum() > len(P) // 4  # partners were found

    # a lap seam that steps back one unit in the last place: the samples that
    # read a chord end there are read alone, and the answer is still the loop's
    lap = len(S3) // 3
    S3b = S3.copy()
    S3b[lap - 1] = np.nextafter(S3b[lap], np.inf)
    S3b[2 * lap - 1] = np.nextafter(S3b[2 * lap], np.inf)
    assert (S3b[1:] < S3b[:-1]).sum() == 2
    args = (P, nearest, S3b, R3, LO3, HI3, longest, total)
    want_b = np.array([sb._square_partner_alone(i, *args) for i in range(len(P))])
    assert np.array_equal(real(*args), want_b)


# --- the Column lane: a letter's rails pushed once -------------------------------------

def _stem() -> tuple[columns.Column, Polygon]:
    poly = box(0.0, 0.0, 1.6, 9.0)
    stations = [((0.0, y), (1.6, y)) for y in np.arange(0.2, 8.9, 0.4).tolist()]
    return columns.Column(stations=stations, piece=poly, kind="straight", axis=(0.0, 1.0),
                          width_mm=1.6), poly


def test_sewn_rails_memo_returns_what_the_push_returns(monkeypatch):
    col, poly = _stem()
    hold = columns.end_face_hold([col], poly)
    want = columns._sewn_rails(col, poly, 0.2, 0.3, hold, None)
    calls = []
    real = columns._sewn_rails

    def counted(*a, **k):
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(columns, "_sewn_rails", counted)
    assert columns.sewn_rails(col, poly, 0.2, 0.3, hold, None) == want      # no memo: straight through
    assert len(calls) == 1
    token = columns._RAILS_MEMO.set({})
    try:
        first = columns.sewn_rails(col, poly, 0.2, 0.3, hold, None)
        again = columns.sewn_rails(col, poly, 0.2, 0.3, hold, None)
        assert first == want and again == want
        assert len(calls) == 2                                              # pushed once
        first[0].append("mine")                                             # the caller's own lists
        assert columns.sewn_rails(col, poly, 0.2, 0.3, hold, None) == want
        # anything the push reads makes another entry
        assert columns.sewn_rails(col, poly, 0.25, 0.3, hold, None) != want
        assert columns.sewn_rails(col, poly, 0.2, 0.3, None, None) == real(col, poly, 0.2, 0.3, None, None)
        moved = columns.Column(stations=[((a[0], a[1] + 0.1), (b[0], b[1] + 0.1)) for a, b in col.stations],
                               piece=poly, kind="straight", axis=(0.0, 1.0), width_mm=1.6)
        assert columns.sewn_rails(moved, poly, 0.2, 0.3, hold, None) == real(moved, poly, 0.2, 0.3, hold, None)
        assert len(calls) == 5              # the first push, then one per new key
    finally:
        columns._RAILS_MEMO.reset(token)
    assert columns._RAILS_MEMO.get() is None
