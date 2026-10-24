"""tools/letter_pieces: the reader behind docs/big-letter-construction-2026-10-24.md.

Synthetic zigzags only -- the reader's three rules, pinned so a change to one
shows up here before it moves a number in the doc.
"""
import math

import numpy as np

from tools import letter_pieces as lp


def _zigzag(x0, y0, y1, width, pitch=0.4, legs=1):
    """An upright satin column from y0 to y1, crosses horizontal, each cross
    sewn in `legs` collinear stitches (our split satin)."""
    pts = []
    y, left = y0, True
    while y <= y1:
        a, b = (x0, y), (x0 + width, y + pitch / 2)
        if not left:
            a, b = b, a
        for k in range(legs):
            t = k / legs
            pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
        y += pitch / 2
        left = not left
    return np.array(pts, float)


def _pieces(pts):
    out = []
    for ch in lp.chains(lp.fuse(pts)):
        out += [p for p in lp.split_turns(ch) if len(p) >= lp.MIN_PIECE]
    return out


def test_split_cross_counts_once():
    whole = _pieces(_zigzag(0, 0, 10, 4.0))
    split2 = _pieces(_zigzag(0, 0, 10, 6.0, legs=2))
    split3 = _pieces(_zigzag(0, 0, 10, 7.7, legs=3))
    assert len(whole) == len(split2) == len(split3) == 1
    assert abs(len(split2[0]) - len(whole[0])) <= 1
    assert abs(len(split3[0]) - len(whole[0])) <= 1
    assert math.isclose(np.median([s[4] for s in split3[0]]), 7.7, abs_tol=0.05)


def test_turn_cuts_a_chain():
    """A new object starting where the last ended, at a new angle, is a cut."""
    up = _zigzag(0, 0, 6, 4.0)
    # the same column's crosses turned 60 deg, continuing from its last point
    rot = math.radians(60)
    R = np.array([[math.cos(rot), -math.sin(rot)], [math.sin(rot), math.cos(rot)]])
    tail = (_zigzag(0, 0, 6, 4.0) - [0, 0]) @ R.T + up[-1]
    assert len(_pieces(np.vstack([up, tail]))) == 2


def test_a_run_stitch_breaks_the_chain():
    col = _zigzag(0, 0, 5, 4.0)
    run = np.array([col[-1] + (0, 0.3 * k) for k in range(1, 8)])
    col2 = _zigzag(col[-1][0], col[-1][1] + 2.4, col[-1][1] + 7.4, 4.0)
    assert len(_pieces(np.vstack([col, run, col2]))) == 2


def test_lock_stitch_is_not_a_piece():
    lock = np.array([(0, 0), (1.2, 0), (0, 0), (1.2, 0), (0, 0), (1.2, 0)], float)
    assert _pieces(lock) == [] or all(
        sum(float(np.hypot(*(b[2] - a[2]))) for a, b in zip(p, p[1:])) < lp.MIN_SPINE_MM
        for p in _pieces(lock))
