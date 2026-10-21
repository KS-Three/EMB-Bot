"""`cfg.lettering_columns_small_bold` (2026-10-21, built OFF): the Column lane
sews a letter under 5 mm like the pro's ~4 mm bold satin letters.

Kent ruled "match the pro" for Fremont's small words: `small_text_cap_mm`
4.0, `small_text_cap_max_width_scale` 1.05 and `small_text_cap_min_stroke_mm`
0.85 grow EST 1895, THE and EAT | STAY | PLAY to the pro's ~4 mm at the
patch's 92.5 mm Hat width. The lane then sewed them as blobs: a fixed 0.4 mm
pull a rail on a 0.8 mm stroke (median satin stitch 1.23 mm, the pro's 0.86),
and every serif block fanned from its inner corner. Under 0.4 mm of pull a
smaller pull alone dropped whole serifs and bars under the 0.5 mm cross floor.

`testdata/fremont92_grown_letters.json`: those 21 grown letters and three
HOTEL FREMONT letters (6.8 mm), each with the kwargs stage 7 handed the lane,
captured from the pipeline at 92.5 mm Hat with the three growth flags above.
"""
import hashlib
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core import columns
from digitizer_core import outline_cut as oc

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "fremont92_grown_letters.json"
#: the lane's runs on all 24 letters with the flag OFF -- identical on this
#: branch and on its base (1d1d3356, main + the growth flags), 2026-10-21
OFF_LANE_MD5 = "6e816f0b52159e812b654ce7409ef1c0"


def _letters():
    data = json.loads(LETTERS.read_text(encoding="utf-8"))
    out = {}
    for name, v in data.items():
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[name] = (Polygon(v["exterior"], v["holes"]), kw)
    return out


def lane_md5(letters: dict, **extra) -> str:
    rows = []
    for name in sorted(letters):
        poly, kw = letters[name]
        runs, _rep = columns.lettering_columns_shape(poly, "pin", **kw, **extra)
        rows.append([name, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                            for r in runs for x, y in r.points]])
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


@pytest.fixture(scope="module")
def letters():
    return _letters()


@pytest.fixture(scope="module")
def small(letters):
    return {k: v for k, v in letters.items() if not k.startswith("BIG_")}


def _sewn(letters, **extra):
    """-> (satin stitch lengths, columns_unsewn, per-letter runs)."""
    lengths, unsewn, runs_of = [], 0, {}
    for name, (poly, kw) in letters.items():
        runs, rep = columns.lettering_columns_shape(poly, name, **{**kw, **extra})
        unsewn += rep["columns_unsewn"]
        runs_of[name] = runs
        for r in runs:
            if r.kind == stitches.SATIN:
                lengths += [math.dist(a, b) for a, b in zip(r.points, r.points[1:])]
    return sorted(lengths), unsewn, runs_of


def _median(v):
    return v[len(v) // 2]


@pytest.fixture(scope="module")
def off(small):
    return _sewn(small)


@pytest.fixture(scope="module")
def on(small):
    return _sewn(small, small_bold=True)


# --- OFF ------------------------------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_small_bold is False


def test_off_is_byte_identical_to_base(letters):
    assert lane_md5(letters) == OFF_LANE_MD5


def test_off_never_reaches_the_new_code(small, monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("small_bold code reached with the flag off")
    monkeypatch.setattr(columns, "_floor_crosses", boom)
    monkeypatch.setattr(oc, "_straight_rescan", boom)
    for poly, kw in list(small.values())[:8]:
        columns.lettering_columns_shape(poly, "off", **kw)


# --- the defects, pinned OFF, and ON --------------------------------------------------

def test_off_the_hat_pull_sews_the_strokes_half_again_too_wide(off):
    assert _median(off[0]) > 1.15            # the pro's tagline: 0.86


def test_on_the_pull_is_a_share_of_the_stroke(on):
    # the pro's median sewn satin stitch on these words: 0.81-0.90 mm
    assert 0.75 <= _median(on[0]) <= 0.95


def test_on_no_piece_is_lost(small, on):
    # a small pull alone (0.1 mm, the pro's width) drops whole serifs and bars
    _l, unsewn, _r = _sewn(small, pull_mm=0.1)
    assert unsewn >= 5
    assert on[1] == 0


def test_on_no_column_pivots_past_the_fan_limit(small):
    def worst(**kw):
        out = 0.0
        for poly, k in small.values():
            cut = oc.letter_columns(poly, pitch_mm=k["spacing_mm"], fold_cuts=k["fold_cuts"],
                                    mitre_ends=k["square_ends"], rail_axis=k["rail_axis"], **kw)
            # a ring turns round its counter (the 8's): the pro's fan there too
            out = max([out] + [oc.pivot_sweep(c.stations) for c in cut.columns if c.kind != "ring"])
        return out
    assert worst() > 80.0                     # a serif block fanned from its inner corner
    assert worst(small_bold=True) <= oc.SMALL_BOLD_FAN_DEG


def test_on_fewer_crossed_zigzag_legs(off, on):
    def crossed(runs_of):
        return sum(int(oc.sewn_knots(r)[2]) for r in runs_of.values())
    assert crossed(off[2]) > 150
    assert crossed(on[2]) < crossed(off[2]) / 5


def test_floor_crosses_widens_about_the_middle():
    st = [((0.0, 0.0), (0.0, 0.3)), ((0.4, 0.1), (0.4, 0.4)), ((0.8, 0.2), (0.8, 0.2))]
    out = columns._floor_crosses(st, 0.5)
    for (a, b), (a0, b0) in zip(out, st):
        assert math.dist(a, b) == pytest.approx(0.5)
        m0 = ((a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2)
        assert ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) == pytest.approx(m0)
    # the pointless cross takes its neighbour's direction
    assert out[2][0][0] == pytest.approx(0.8)


def test_a_thin_bar_sews_at_the_floor():
    # a 4 mm H whose crossbar is 0.35 mm: at the stroke's own pull it is
    # under the 0.5 mm floor and was dropped; ON it sews
    H = Polygon([(0, 0), (0.8, 0), (0.8, 1.8), (1.7, 1.8), (1.7, 0), (2.5, 0), (2.5, 4),
                 (1.7, 4), (1.7, 2.15), (0.8, 2.15), (0.8, 4), (0, 4)])
    kw = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.4, pull_floor_mm=1.5, square_ends=True,
              inside_connectors=True, fold_cuts=True, rail_axis=True)
    _r, off_rep = columns.lettering_columns_shape(H, "h", **{**kw, "pull_mm": 0.1})
    runs, rep = columns.lettering_columns_shape(H, "h", **kw, small_bold=True)
    assert off_rep["columns_unsewn"] >= 1
    assert rep["columns_unsewn"] == 0
    bar = Polygon([(0.8, 1.8), (1.7, 1.8), (1.7, 2.15), (0.8, 2.15)]).buffer(0.15)
    inside = sum(1 for r in runs if r.kind == stitches.SATIN for p in r.points if bar.covers(Point(p)))
    assert inside >= 4


def test_stage7_passes_it_only_under_5mm():
    # the 6.8 mm HOTEL FREMONT is never touched: stage 7 gates on `_small`
    src = (Path(__file__).resolve().parent.parent / "digitizer_core" / "stage7_sequence.py").read_text(
        encoding="utf-8")
    assert 'if cfg.lettering_columns_small_bold and _small else {}' in src
    assert machine.SATIN_UNDERLAY_MIN_EXTENT_MM == 5.0
