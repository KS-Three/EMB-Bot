"""`cfg.pull_comp_by_stroke` (2026-10-22, built OFF): the Column lane's pull
compensation read off each column's own drawn stroke width, by the line
through the professional's hat files (`columns.pull_for_width`, the
measurements in its comment).

OFF, the lane is today's byte for byte (`test_column_small_bold.py` pins
the grown-Fremont fixture's md5; here, the new code is never reached). ON,
a synthetic column sews within 0.1 mm of the fit, a thin bar and a wide
stem of ONE letter get different pulls, and the preset gate holds.
"""
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, columns, stitches
from digitizer_core.fabrics import FABRICS, PULL_BY_STROKE_FABRICS, get_fabric, pull_by_stroke_for

HERE = Path(__file__).resolve().parent
LETTERS = HERE.parent / "testdata" / "fremont92_grown_letters.json"

KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.4, pull_floor_mm=1.5, square_ends=True,
          inside_connectors=True, fold_cuts=True, rail_axis=True)


def _fit(w: float) -> float:
    return columns.PULL_BY_STROKE_A * w + columns.PULL_BY_STROKE_B


def _satin_lengths(runs, within: Polygon | None = None):
    out = []
    for r in runs:
        if r.kind != stitches.SATIN:
            continue
        for a, b in zip(r.points, r.points[1:]):
            m = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
            if within is None or within.covers(Point(m)):
                out.append(math.dist(a, b))
    return sorted(out)


def _median(v):
    return v[len(v) // 2]


# --- OFF ------------------------------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().pull_comp_by_stroke is False


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("pull_comp_by_stroke code reached with the flag off")
    monkeypatch.setattr(columns, "pull_for_width", boom)
    monkeypatch.setattr(columns, "column_width", boom)
    data = json.loads(LETTERS.read_text(encoding="utf-8"))
    for name in sorted(data)[:6]:
        v = data[name]
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        columns.lettering_columns_shape(Polygon(v["exterior"], v["holes"]), name, **kw)
        columns.lettering_columns_shape(Polygon(v["exterior"], v["holes"]), name, **kw, small_bold=True)


# --- the fit --------------------------------------------------------------------

def test_the_fit_is_the_pro_s_four_job_medians():
    # per-job medians, sewn against drawn, the pro's hat files (2026-10-22)
    measured = [(0.85, 1.43), (1.29, 1.80), (2.61, 3.02), (4.22, 4.00)]
    for drawn, sewn in measured:
        assert abs(_fit(drawn) - sewn) <= 0.2, (drawn, sewn, _fit(drawn))


def test_pull_never_exceeds_the_preset_and_falls_with_width():
    for f in FABRICS:
        last = None
        for w in (0.3, 0.6, 0.85, 1.3, 2.0, 2.6, 3.0, 4.0, 5.0, 8.0):
            p = columns.pull_for_width(w, f.pull_comp_mm)
            assert 0.0 <= p <= f.pull_comp_mm
            if last is not None:
                assert p <= last + 1e-9
            last = p
    # the hat: a 0.85 mm stroke keeps today's 0.4 (the pro sews HOTEL
    # FREMONT at exactly our width); 2.6 mm gets about 0.23; 4 mm about 0.07
    assert columns.pull_for_width(0.85, 0.4) == pytest.approx(0.4)
    assert columns.pull_for_width(2.6, 0.4) == pytest.approx(0.228, abs=0.01)
    assert columns.pull_for_width(4.0, 0.4) == pytest.approx(0.068, abs=0.01)
    assert columns.pull_for_width(5.0, 0.4) == 0.0
    # another preset scales by its own pull
    assert columns.pull_for_width(2.6, 0.3) == pytest.approx(0.228 * 0.75, abs=0.01)


def test_column_width_is_the_median_station_cross():
    col = columns.Column(stations=[((0, 0), (0.8, 0)), ((0, 0.4), (0.6, 0.4)), ((0, 0.8), (2.0, 0.8))],
                         piece=Polygon(), kind="straight", axis=(0, 1), width_mm=1.0)
    assert columns.column_width(col) == pytest.approx(0.8)


# --- ON -------------------------------------------------------------------------

@pytest.mark.parametrize("W,L", [(0.85, 6.0), (2.5, 8.0)])
def test_on_a_synthetic_column_sews_at_the_fit(W, L):
    poly = Polygon([(0, 0), (W, 0), (W, L), (0, L)])
    runs, rep = columns.lettering_columns_shape(poly, "col", **KW, pull_by_stroke=True)
    assert rep["columns_unsewn"] == 0
    sewn = _median(_satin_lengths(runs))
    # the fit, or the preset's own pull where the fit asks for more (0.85 mm)
    expect = min(_fit(W), W + 2 * (KW["pull_mm"] - columns.RAIL_REACH_INSET_MM))
    assert abs(sewn - expect) <= 0.1, (W, sewn, expect)


def test_on_a_wide_column_sews_narrower_than_off():
    poly = Polygon([(0, 0), (2.5, 0), (2.5, 8.0), (0, 8.0)])
    off, _ = columns.lettering_columns_shape(poly, "off", **KW)
    on, _ = columns.lettering_columns_shape(poly, "on", **KW, pull_by_stroke=True)
    assert _median(_satin_lengths(off)) == pytest.approx(2.5 + 0.58, abs=0.05)
    assert _median(_satin_lengths(on)) < _median(_satin_lengths(off)) - 0.25


def test_on_each_column_gets_its_own_pull():
    # an H with 2.4 mm stems and a 0.7 mm crossbar: the bar keeps the
    # preset's 0.4, the stems get the fit's ~0.25
    H = Polygon([(0, 0), (2.4, 0), (2.4, 4.0), (5.2, 4.0), (5.2, 0), (7.6, 0), (7.6, 10),
                 (5.2, 10), (5.2, 4.7), (2.4, 4.7), (2.4, 10), (0, 10)])
    runs, rep = columns.lettering_columns_shape(H, "h", **KW, pull_by_stroke=True)
    assert rep["columns_unsewn"] == 0
    stems = Polygon([(0, 0), (2.4, 0), (2.4, 10), (0, 10)]).buffer(0.6)
    bar = Polygon([(2.6, 4.0), (5.0, 4.0), (5.0, 4.7), (2.6, 4.7)]).buffer(0.6)
    stem_w = _median(_satin_lengths(runs, stems))
    bar_w = _median(_satin_lengths(runs, bar))
    assert abs(stem_w - _fit(2.4)) <= 0.15, stem_w
    assert abs(bar_w - (0.7 + 2 * (0.4 - columns.RAIL_REACH_INSET_MM))) <= 0.15, bar_w


def test_on_small_bold_s_share_still_caps_it():
    poly = Polygon([(0, 0), (0.85, 0), (0.85, 3.5), (0, 3.5)])
    a, _ = columns.lettering_columns_shape(poly, "a", **KW, small_bold=True)
    b, _ = columns.lettering_columns_shape(poly, "b", **KW, small_bold=True, pull_by_stroke=True)
    assert _median(_satin_lengths(a)) == pytest.approx(_median(_satin_lengths(b)), abs=0.02)
    assert _median(_satin_lengths(b)) < 1.0


# --- the wiring -----------------------------------------------------------------

def test_the_preset_gate():
    assert PULL_BY_STROKE_FABRICS == ("structured_cap", "pique_knit", "jersey_tee")
    for f in FABRICS:
        assert pull_by_stroke_for(f, False) is False
        assert pull_by_stroke_for(f, True) is (f.id in PULL_BY_STROKE_FABRICS)
    assert pull_by_stroke_for(get_fabric("structured_cap"), True)
    assert not pull_by_stroke_for(get_fabric("canvas_tote"), True)


def test_stage7_passes_it_through_the_preset_gate():
    src = (HERE.parent / "digitizer_core" / "stage7_sequence.py").read_text(encoding="utf-8")
    assert 'if pull_by_stroke_for(fabric, cfg.pull_comp_by_stroke) else {}' in src
