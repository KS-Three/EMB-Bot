"""`outline_cut`'s per-letter memo (`_MEMO`, 2026-10-26) must change nothing:
every letter cuts to exactly the columns, cuts and unsewn pieces it cut
before, under every flag the lane carries, and a caller still owns what it
is handed. The memo-free reference is the same module with `build_column`
and `pair_rails` pointed back at their uncached constructions."""
import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import outline_cut as oc
from digitizer_core.columns import Column


def _canon(x):
    """Exact, comparable form: WKB for geometry, every float as itself."""
    if x is None or isinstance(x, (bool, int, float, str)):
        return x
    if isinstance(x, np.generic):
        return ("np", x.dtype.str, x.item())
    if hasattr(x, "wkb") and hasattr(x, "geom_type"):
        return ("g", x.wkb)
    if isinstance(x, Column):
        return ("col", _canon(x.stations), _canon(x.piece), x.kind, _canon(x.axis),
                _canon(x.width_mm), _canon(x.rail_a), _canon(x.rail_b), _canon(x.dropped_mm))
    if isinstance(x, np.ndarray):
        return ("nd", x.dtype.str, x.shape, x.tobytes())
    if isinstance(x, dict):
        return ("d", tuple(sorted((k, _canon(v)) for k, v in x.items())))
    if isinstance(x, (list, tuple)):
        return (type(x).__name__, tuple(_canon(v) for v in x))
    return ("?", repr(x))


def _cut(poly, kw):
    c = oc.letter_columns(poly, **kw)
    return _canon((c.poly, c.W, c.cuts, c.columns, c.unsewn))


LETTERS = {
    "E": Polygon([(0, 0), (6, 0), (6, 1.2), (1.2, 1.2), (1.2, 2.4), (5, 2.4), (5, 3.6), (1.2, 3.6),
                  (1.2, 4.8), (6, 4.8), (6, 6), (0, 6)]),
    "M": Polygon([(0, 0), (2, 0), (5, 4), (8, 0), (10, 0), (10, 12), (8, 12), (8, 4.5), (5, 8.5),
                  (2, 4.5), (2, 12), (0, 12)]),
    "N": Polygon([(0, 0), (1, 0), (1, 5.5), (4, 0), (5, 0), (5, 8), (4, 8), (4, 2.5), (1, 8), (0, 8)]),
    "O": Polygon([(0, 0), (8, 0), (8, 10), (0, 10)], [[(1.4, 1.4), (6.6, 1.4), (6.6, 8.6), (1.4, 8.6)]]),
    "o": box(0, 0, 6, 6).buffer(1.0).difference(box(1.6, 1.6, 4.4, 4.4).buffer(0.6)),
    "L": Polygon([(0, 0), (6, 0), (6, 1.2), (1.2, 1.2), (1.2, 8), (0, 8)]),
}


def _judge(pc, cols):
    """A deterministic stand-in for the sewn judge, so `_judged_overlong` runs."""
    n = sum(len(c.stations) for c in cols if c is not None)
    return (n % 3, n % 2, 0)


FLAGS = [
    {},
    {"fold_cuts": True, "judge": _judge},
    {"fold_cuts": True, "judge": _judge, "mitre_ends": True, "rail_axis": True},
    {"small_bold": True},
    {"small_bold": True, "simplify_mm": 0.1, "corner_fold": True},
    {"apex_cut": True, "corner_fold": True, "fold_cuts": True, "judge": _judge},
]


@pytest.mark.parametrize("name", sorted(LETTERS))
@pytest.mark.parametrize("fi", range(len(FLAGS)))
def test_a_letter_cuts_exactly_as_it_did_without_the_memo(monkeypatch, name, fi):
    poly, kw = LETTERS[name], dict(FLAGS[fi], pitch_mm=0.4)
    with_memo = _cut(poly, kw)
    with monkeypatch.context() as m:
        m.setattr(oc, "build_column", lambda piece, cut_lines, W, pitch_mm, mitre_ends=False,
                  rail_axis=None: oc._build_column(piece, cut_lines, W, pitch_mm, mitre_ends,
                                                   oc._RAIL_AXIS.get() if rail_axis is None else rail_axis))
        m.setattr(oc, "pair_rails", oc._pair_rails)
        without = _cut(poly, kw)
    assert with_memo == without


def test_the_memo_lives_only_inside_a_letter():
    assert oc._MEMO.get() is None
    oc.letter_columns(LETTERS["E"], 0.4, fold_cuts=True, judge=_judge)
    assert oc._MEMO.get() is None
    # outside a letter build_column is the plain construction, every call
    c1 = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
    c2 = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
    assert c1 is not c2 and _canon(c1) == _canon(c2)


def test_a_caller_owns_what_it_is_handed():
    token = oc._MEMO.set({})
    try:
        a = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
        b = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
        assert a is not b and a.stations is not b.stations and _canon(a) == _canon(b)
        a.stations.clear()
        a.rail_a.clear()
        c = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
        assert _canon(c) == _canon(b) and c.stations
        r1 = oc.pair_rails([(0, 0), (5, 0)], [(0, 1), (5, 1)], 0.4)
        r1.clear()
        assert oc.pair_rails([(0, 0), (5, 0)], [(0, 1), (5, 1)], 0.4) == \
            oc._pair_rails([(0, 0), (5, 0)], [(0, 1), (5, 1)], 0.4)
    finally:
        oc._MEMO.reset(token)


def test_the_key_tells_the_context_apart():
    """A column built under small_bold is not handed to a caller outside it."""
    token = oc._MEMO.set({})
    try:
        plain = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
        t2 = oc._SMALL_BOLD.set(True)
        try:
            bold = oc.build_column(LETTERS["L"], [], 1.2, 0.4)
        finally:
            oc._SMALL_BOLD.reset(t2)
        t3 = oc._SMALL_BOLD.set(True)
        try:
            want = oc._build_column(LETTERS["L"], [], 1.2, 0.4, False, False)
        finally:
            oc._SMALL_BOLD.reset(t3)
        assert _canon(bold) == _canon(want)
        assert _canon(plain) == _canon(oc._build_column(LETTERS["L"], [], 1.2, 0.4, False, False))
    finally:
        oc._MEMO.reset(token)
