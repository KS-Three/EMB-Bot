"""`cfg.lettering_columns_inside_stagger` (2026-10-23, built OFF): the inside
of a satin pivot in the Column lane -- an L fold's corner
(`cfg.lettering_columns_corner_fold`), an S's curl -- sewn the professional's
way instead of by `stage6_satin._short_stitch_guard`.

Read with one rule on his hat DSTs and ours (`tools/inside_stagger.py`,
Fremont, Drone, MFab, Proseal, Becker): his full-length inner ends walk
~0.3 mm along the inner edge and almost never share a hole (2-5 re-entries
per band), and about one cross in three is shortened by ~20% of its length.
The guard shortens every other crowded cross by 35% (capped 0.6 mm) and
leaves the full-length ones in one hole: 16-79 re-entries per band.

`testdata/drone62_band_letters.json`: PRECISION's nine letters as stage 7
handed them to the lane at 62.6 mm Hat (the pro's design width).
"""
import hashlib
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, columns, machine
from digitizer_core import outline_cut as oc

DRONE = Path(__file__).resolve().parent.parent / "testdata" / "drone62_band_letters.json"
W = 1.4
#: an L: a 7 mm stem, a 5 mm foot, both W wide (y down)
L_SHAPE = Polygon([(0, 0), (W, 0), (W, 7 - W), (5, 7 - W), (5, 7), (0, 7)])
LANE = dict(fold_cuts=True, mitre_ends=True, rail_axis=True)
RUNS = dict(trim_at_mm=3.0, pull_mm=0.4, pull_floor_mm=1.5, underlay_style="none",
            square_ends=True, inside_connectors=True)
#: the lane's runs over PRECISION's letters with the flag off, captured on
#: the corner-fold lane (#1054) before this flag existed -- the same digest
#: from that commit's `digitizer_core` and from this one's, 2026-10-23
OFF_MD5 = {"plain": "5f7c9a7cb9cdb1ddd8c9fcb0d8dfb0e0", "corner_fold": "c43148d96b24e218e4757b23b9d1d9f0"}


def _drone_letters():
    out = {}
    for sid, v in json.loads(DRONE.read_text(encoding="utf-8")).items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        poly = Polygon(v["exterior"], v["holes"])
        if 9.5 < poly.bounds[1] < 11.0:
            out[sid] = (poly, kw)
    return out


@pytest.fixture(scope="module")
def drone():
    return _drone_letters()


def lane_md5(letters: dict, **extra) -> str:
    rows = []
    for name in sorted(letters):
        poly, kw = letters[name]
        runs, _rep = columns.lettering_columns_shape(poly, "pin", **kw, **extra)
        rows.append([name, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                            for r in runs for x, y in r.points]])
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _sew_l(**extra):
    cut = oc.letter_columns(L_SHAPE, 0.4, **LANE, corner_fold=True)
    return columns.column_runs(cut.columns, cut.poly, "t", **RUNS, **extra)


def _inner_ends(runs):
    """The folded L's satin penetrations on the inside-corner rail, in sew
    order: of the zigzag's two rails, the one that reaches the corner."""
    from digitizer_core.stage6_satin import strip_splits
    from digitizer_core.stitches import strip_ties
    pts = [p for r in runs if r.kind == "satin" for p in strip_splits(strip_ties(list(r.points)))]
    rails = (pts[0::2], pts[1::2])
    return min(rails, key=lambda r: min(math.dist(p, (W, 7 - W)) for p in r))


def _same_hole(ends, window: int = 8, eps: float = 0.1) -> int:
    return sum(1 for k in range(1, len(ends))
               if any(math.dist(ends[k], ends[m]) < eps for m in range(max(0, k - window), k)))


# --- the flag -------------------------------------------------------------------------

def test_flag_is_on_by_default():
    # Kent 2026-10-24, the flip sheet
    assert PipelineConfig().lettering_columns_inside_stagger is True


def test_stage7_wires_the_flag_and_nothing_else():
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(
        encoding="utf-8")
    assert '**({"inside_stagger": True} if cfg.lettering_columns_inside_stagger else {})' in src


def test_off_never_reaches_the_new_code(drone, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("inside_stagger code reached with the flag off")
    monkeypatch.setattr(columns, "_inside_stagger", boom)
    for poly, kw in list(drone.values())[:4]:
        columns.lettering_columns_shape(poly, "off", **kw)
        columns.lettering_columns_shape(poly, "off", **kw, corner_fold=True)


@pytest.mark.parametrize("arm", ["plain", "corner_fold"])
def test_off_is_byte_identical_to_the_lane_before_the_flag(drone, arm):
    extra = {"corner_fold": True} if arm == "corner_fold" else {}
    assert lane_md5(drone, **extra) == OFF_MD5[arm]


# --- the rule, on rails ---------------------------------------------------------------

def _pile(n_fan: int = 8, width: float = 2.0):
    """An L's inside corner as the lane hands it over: a leg's inner rail at
    pitch, every fold cross on one corner point, the other leg at pitch."""
    a = [(0.0, -1.6 + 0.4 * k) for k in range(4)]
    b = [(-width, y) for _x, y in a]
    for k in range(1, n_fan + 1):
        th = math.radians(180 + 90 * k / (n_fan + 1))
        a.append((0.0, 0.0))
        b.append((width * 1.3 * math.cos(th), -width * 1.3 * math.sin(th)))
    for k in range(1, 5):
        a.append((0.4 * k, 0.0))
        b.append((0.4 * k, width))
    return a, b


def test_on_a_pile_walks_and_never_reenters_a_hole():
    from digitizer_core.stage6_satin import _short_stitch_guard
    a, b = _pile()
    out = columns._inside_stagger(a, b)
    inner = [p for p, _q in out]
    guard = [p for p, _q in _short_stitch_guard(a, b)]
    assert _same_hole(guard) >= 3                       # the guard: the full ones on the corner
    assert _same_hole(inner) == 0
    # the full-length ones walk the corner: eight crosses on one point
    # become one hole per ~0.22 mm of the course round it (the reach cap
    # holds the legs' own crosses, so the pile gets under the 0.3 target)
    full = [p for p, (sa, sb), (pa, pb) in zip(inner, out, zip(a, b))
            if math.dist(sa, sb) >= math.dist(pa, pb) - 1e-6]
    steps = [math.dist(p, q) for p, q in zip(full, full[1:])]
    assert len(full) >= 8 and min(steps) > 0.15
    # and the legs beyond the reach are where the rail put them
    assert inner[:3] == a[:3] and inner[-2:] == a[-2:]


def test_on_short_stitches_are_a_fifth_of_the_cross_never_two_in_a_row():
    a, b = _pile()
    out = columns._inside_stagger(a, b)
    short = []
    for (pa, pb), (sa, sb) in zip(zip(a, b), out):
        cross, sewn = math.dist(pa, pb), math.dist(sa, sb)
        is_short = sewn < cross - 1e-6 and math.dist(sb, pb) < 1e-9
        short.append(is_short)
        if is_short:
            # pulled along its own cross by its share, not a fixed distance
            assert abs((cross - sewn) / cross - columns.STAGGER_SHORT_FRAC) < 1e-6
    assert any(short)
    assert not any(x and y for x, y in zip(short, short[1:]))
    # one full-length cross after a short one, then two, in turn: two in five
    assert sum(short) <= math.ceil(2 * len(short) / 5) + 1


def test_on_a_short_stitch_never_drops_under_the_floor():
    a = [(0.0, 0.0), (0.0, 0.1), (0.0, 0.2)]
    b = [(0.55, 0.0), (0.55, 0.1), (0.55, 0.2)]
    for pa, pb in columns._inside_stagger(a, b):
        assert math.dist(pa, pb) >= machine.SATIN_MIN_CROSS_MM


def test_on_an_uncrowded_column_is_untouched():
    a = [(0.0, 0.4 * k) for k in range(10)]
    b = [(1.4, 0.4 * k) for k in range(10)]
    assert columns._inside_stagger(a, b) == list(zip(a, b))


# --- the rule, sewn -------------------------------------------------------------------

def test_on_the_folded_l_corner_stops_reentering_one_hole():
    off, _ = _sew_l()
    on, rep = _sew_l(inside_stagger=True)
    assert rep["jumps"] == 0
    assert _same_hole(_inner_ends(on)) < _same_hole(_inner_ends(off))
    assert _same_hole(_inner_ends(on)) <= 1                 # OFF: 3


def test_on_drone_moves_every_number_toward_the_pro():
    """PRECISION through the folds, read by `tools.inside_stagger`: the
    numbers of the PR body's table (pro: same-hole 2, short frac 0.40,
    rel depth 0.23, pile 0.02)."""
    from tools import inside_stagger as IS
    from tools import column_harness as ch
    letters = _drone_letters()

    def read(**extra):
        sewn = {sid: (columns.lettering_columns_shape(poly, sid, **kw, **extra)[0], None, None)
                for sid, (poly, kw) in letters.items()}
        return IS.summary(IS.read(ch.ours_points(letters, sewn, list(letters))[0]))
    off, on = read(corner_fold=True), read(corner_fold=True, inside_stagger=True)
    pro = {"same_hole": 2, "short_frac": 0.40, "rel": 0.23, "pile": 0.02}
    for k, v in pro.items():
        assert abs(on[k] - v) < abs(off[k] - v), (k, off[k], on[k], v)
    assert on["same_hole"] <= 0.6 * off["same_hole"]          # 32 -> 17 measured
