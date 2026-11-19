"""`lettering_columns_hairline_leave` (built OFF 2026-11-19): a hairline whose
stations run through a HEAVIER column, blob-wide, leaves it at once; ends,
parallel strokes and columns of equal weight are untouched."""
from __future__ import annotations

import math

from digitizer_core import hairline_leave as hl
from digitizer_core.columns import Column
from digitizer_core.script_strokes import _ribbon


def _col(mids, lens, ang_deg):
    out = []
    for (x, y), L in zip(mids, lens):
        dx, dy = L / 2 * math.cos(math.radians(ang_deg)), L / 2 * math.sin(math.radians(ang_deg))
        out.append(((x - dx, y - dy), (x + dx, y + dy)))
    return Column(stations=out, piece=_ribbon(out), kind="curved", axis=None, width_mm=sorted(map(lambda s: math.dist(*s), out))[len(out) // 2])


def _stem():
    return _col([(0.0, 0.4 * i - 8) for i in range(41)], [2.4] * 41, 0.0)      # horizontal crosses, x -1.2..1.2


def _hair(blob=True):
    xs = [-6.0 + 0.4 * i for i in range(31)]
    lens = [0.7 + (1.4 if blob and abs(x) <= 2.0 else 0.0) for x in xs]       # blob-wide where it crosses the stem
    return _col([(x, 0.0) for x in xs], lens, 90.0)


def test_off_by_default():
    assert hl.armed() is False
    with hl.hairline_leave_scope(True):
        assert hl.armed() is True
    assert hl.armed() is False


def test_blob_stations_shrink_to_the_hairline():
    stem, hair = _stem(), _hair()
    out, n = hl.leave_columns([stem, hair], None)
    assert n > 0 and out[0] is stem
    lens = [math.dist(*s) for s in out[1].stations]
    assert max(lens) <= 0.8                                                    # no blob-wide cross is left
    assert len(out[1].stations) == len(hair.stations)
    # the stations outside the merge are the very ones that were there
    assert out[1].stations[0] == hair.stations[0] and out[1].stations[-1] == hair.stations[-1]


def test_no_blob_means_no_change():
    stem, hair = _stem(), _hair(blob=False)
    out, n = hl.leave_columns([stem, hair], None)
    assert n == 0 and out[1] is hair


def test_equal_weight_columns_are_left_alone():
    a = _hair()
    b = _col([(0.0, 0.4 * i - 6) for i in range(31)], [0.8] * 31, 0.0)
    out, n = hl.leave_columns([a, b], None)
    assert n == 0


def test_end_of_a_column_is_never_touched():
    stem = _stem()
    hair = _col([(-1.0 + 0.4 * i, 0.0) for i in range(12)], [2.1] * 12, 90.0)      # starts INSIDE the stem
    out, n = hl.leave_columns([stem, hair], None)
    assert n == 0


def test_one_column_passes_through():
    c = _stem()
    out, n = hl.leave_columns([c], None)
    assert n == 0 and out == [c]


def test_toat_machine_hat_h_hairline_leaves_the_stem():
    """On the real plan (flag forced ON): the h's arch x stem pair loses its turned overlap
    (5.95 mm2 OFF on 2026-11-19), and the stations outside the merge are unchanged."""
    import itertools
    from digitizer_core import end_overlap as eo, script_strokes as ss
    from tools import pro_baseline as pb, pro_pair

    def word_columns(extra):
        seen = []
        orig = ss._patches
        ss._patches = lambda poly, cols, *a, **k: (seen.append(cols), orig(poly, cols, *a, **k))[1]
        try:
            garment, width, art, *_ = pb.JOBS["toat_machine_hat"]
            pro_pair.digitize(pb.resolve(art), width, garment, extra)
        finally:
            ss._patches = orig
        return seen[0]

    def turned(cols, i, j):
        qi, qj = eo._quads(cols[i]), eo._quads(cols[j])
        ai = [eo._ang(s) for s in cols[i].stations]
        aj = [eo._ang(s) for s in cols[j].stations]
        return sum(p.intersection(r).area for (a, p), (b, r) in itertools.product(enumerate(qi), enumerate(qj))
                   if p is not None and r is not None and eo._turn(ai[a + 1], aj[b + 1]) > 30 and p.intersects(r))

    off = word_columns({})
    on = word_columns({"extra.lettering_columns_hairline_leave": True})
    assert turned(off, 3, 5) > 4.0
    assert turned(on, 3, 5) < 1.0
    assert len(on[3].stations) == len(off[3].stations)
