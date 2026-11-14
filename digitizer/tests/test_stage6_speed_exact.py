"""`_seam_apart` (2026-11-13, speed only) must show up in the clock and nowhere else.

It clears a pair of fill sections before `_seam_side` is asked about them, and
may only clear a pair `_seam_side` answers 0 for. Checked here against
`_seam_side` itself on random sections, and end to end through
`_order_for_seams` and `_seam_faults` against the unpruned pair loop.
"""
import random

import pytest

from digitizer_core import stage6_fill as F

ROW = 0.4


def _random_rows(rng, v0):
    rows = []
    v = v0
    for _ in range(rng.randint(0, 6)):
        v += rng.choice((0.15, 0.3, 0.4, 0.45, 1.0, 2.0))
        u0 = rng.uniform(-5, 5)
        rows.append((v, u0, u0 + rng.uniform(0.0, 3.0)))
    return rows


@pytest.mark.parametrize("row_mm", [0.15, 0.4])
def test_seam_apart_only_clears_pairs_seam_side_calls_zero(row_mm):
    rng = random.Random(7)
    cleared = kept = 0
    for _ in range(20000):
        a = _random_rows(rng, rng.uniform(-2, 2))
        b = _random_rows(rng, rng.uniform(-2, 2))
        if F._seam_apart(F._seam_box(a), F._seam_box(b), row_mm):
            assert F._seam_side(a, b, row_mm) == 0
            cleared += 1
        else:
            kept += 1
    assert cleared > 1000 and kept > 1000             # both arms exercised


def test_a_pair_exactly_one_adj_apart_is_not_cleared():
    """The window `_seam_side` reads is closed at `va + adj`: a row there is in it."""
    adj = max(0.6, 1.5 * ROW)
    a = [(0.0, 0.0, 10.0)]
    b = [(0.0 + adj, 0.0, 10.0)]
    assert F._seam_side(a, b, ROW) == 1
    assert not F._seam_apart(F._seam_box(a), F._seam_box(b), ROW)


def _section(rng, x0, y0, rows):
    path = []
    for k in range(rows):
        y = y0 + k * ROW
        xa, xb = x0 + rng.uniform(0, 0.3), x0 + 6.0 + rng.uniform(0, 0.3)
        path.extend([(xa, y), (xb, y)] if k % 2 == 0 else [(xb, y), (xa, y)])
    return path


@pytest.mark.parametrize("seed", range(30))
def test_seam_order_and_faults_match_the_unpruned_pair_loop(seed, monkeypatch):
    rng = random.Random(seed)
    paths = [_section(rng, rng.randint(0, 3) * 6.5, rng.randint(0, 4) * 4 * ROW, rng.randint(1, 4))
             for _ in range(rng.randint(2, 12))]
    entry = (rng.uniform(-5, 25), rng.uniform(-5, 10))
    angle = rng.choice((0.0, 17.0, 90.0))
    fast = (F._order_for_seams(paths, angle, entry, ROW), F._seam_faults(paths, angle, ROW))
    monkeypatch.setattr(F, "_seam_apart", lambda *a: False)
    slow = (F._order_for_seams(paths, angle, entry, ROW), F._seam_faults(paths, angle, ROW))
    assert fast == slow
