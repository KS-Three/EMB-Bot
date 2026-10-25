"""`letter_band.rail_classes`: rail wobble on RUN windows, apart from the
windows that cross a corner or leave the outline (2026-10-25).

Synthetic satin columns on synthetic outlines. The per-letter p90
(`rail_jitter`) is kept as it is; these pin what the class split adds: a
straight stem reads nothing, a real wobble on a stem still reads on its run
windows, and an L's corner reads in the corner class only
(`.claude/memory/column-rail-fit-negative-2026-10-25.md`).
"""
import numpy as np
from shapely.geometry import Polygon

from tools import letter_band as lb

PULL = 0.3


def _zigzag(left, right):
    """A satin column from two rails of equal point count: left[0], right[0],
    left[1], right[1], ..."""
    out = []
    for a, b in zip(left, right):
        out += [tuple(a), tuple(b)]
    return np.array(out, float)


def _stem(h=20.0, w=4.0, pitch=0.4, jag=None):
    """An upright stem's column, rails at the pull outside x = 0 and x = w;
    `jag(y)` moves the left rail sideways."""
    ys = np.arange(0.0, h + 1e-9, pitch)
    left = [(-PULL + (jag(y) if jag else 0.0), y) for y in ys]
    right = [(w + PULL, y) for y in ys]
    return _zigzag(left, right)


def _rect(h=20.0, w=4.0):
    return Polygon([(0, 0), (w, 0), (w, h), (0, h)])


def test_the_classes_are_rail_jitter_cause_s_rule_on_every_window():
    col = _stem()
    c = lb.rail_classes([col], _rect())
    assert c["run"] + c["corner"] + c["stray"] == c["n"] > 40


def test_a_straight_stem_reads_nothing_on_its_run_windows():
    c = lb.rail_classes([_stem()], _rect())
    assert c["run"] > 20
    assert c["run_p90"] < 1e-9
    assert c["stray"] == 0


def test_a_wobbling_stem_still_reads_its_wobble_on_run_windows():
    """The split must not hide a real wobble: a rail 0.15 mm off its line,
    in and out every 2 mm along a straight outline, is run windows, read."""
    c = lb.rail_classes([_stem(jag=lambda y: 0.15 * np.sin(y * np.pi / 2))], _rect())
    straight = lb.rail_classes([_stem()], _rect())
    assert c["corner"] == straight["corner"]       # the stem's end windows, by its end corners
    assert c["stray"] == 0
    assert c["run_p90"] > 0.08


def _l_column():
    """An L sewn as ONE column folding round its corner, the way a corner
    fold sews it: the stem x 0..4 down to the foot y 16..20, out to x 16.
    Down the stem the crosses are square; at the corner they pivot round the
    inside corner while the outside walks round the convex corner (0, 20);
    along the foot they are square again."""
    pitch = 0.4
    outer, inner = [], []
    for y in np.arange(0.0, 16.0, pitch):                      # the stem
        outer.append((-PULL, y))
        inner.append((4.0 + PULL, y))
    walk = [(-PULL, y) for y in np.arange(16.0, 20.0 + PULL, pitch)] +            [(x, 20.0 + PULL) for x in np.arange(0.0, 4.0, pitch)]
    # the inside ends spread 0.4 mm either side of the inside corner (the
    # pro's inner-end spread, `inside_stagger`): a pivot on ONE point has
    # no chord, and `column_segments` would end the column there
    P0 = np.array([4.0 + PULL, 16.0 - PULL - 0.4])
    P1 = np.array([4.0 + PULL + 0.4, 16.0 - PULL])
    for q, t in zip(walk, np.linspace(0.0, 1.0, len(walk))):   # the fold
        outer.append(q)
        inner.append(tuple(P0 + (P1 - P0) * t))
    for x in np.arange(4.0, 16.0 + 1e-9, pitch):               # the foot
        outer.append((x, 20.0 + PULL))
        inner.append((x, 16.0 - PULL))
    return _zigzag(outer, inner)


L_SHAPE = Polygon([(0, 0), (4, 0), (4, 16), (16, 16), (16, 20), (0, 20)])


def test_an_l_reads_its_corner_in_the_corner_class_only():
    col = _l_column()
    c = lb.rail_classes([col], L_SHAPE)
    assert c["corner"] > 0 and c["run"] > 20 and c["stray"] == 0
    assert c["run_p90"] < 0.01                     # both arms are straight
    assert c["corner_p90"] > 0.1                   # the turn reads, in the corner class


def test_today_s_per_letter_reading_counts_the_corner_as_wobble():
    """`rail_jitter`, the per-letter reading every table so far quoted, is
    not touched: on the L its biggest residuals are the corner's."""
    j = lb.rail_jitter([_l_column()])
    c = lb.rail_classes([_l_column()], L_SHAPE, fused=False)
    assert len(j) == c["n"]                        # the same windows, classed
    assert float(np.max(j)) > 0.3 and c["run_p90"] < 0.01


def test_no_windows_reads_none_not_zero():
    short = _stem(h=2.0)
    c = lb.rail_classes([short], _rect(h=2.0))
    assert c["n"] == 0 and c["run_p90"] is None and c["p90"] is None
