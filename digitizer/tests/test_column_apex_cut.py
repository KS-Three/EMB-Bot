"""`cfg.lettering_columns_apex_cut` (2026-10-25, built OFF): where two
strokes meet at an acute tip -- the M's V, each of a W's three apexes, an
N's diagonal into its stem -- the Column lane sews the tip as ONE column
whose crosses span both strokes, cut off them along that cross
(`outline_cut._apex_cuts`).

Read with one rule on the professional's DSTs and ours
(`tools/letter_pieces.py`, Becker MARINE at four widths, MFab AND WELDING
hat and LC, PROSEAL): through every such tip he sews one piece, crosses
within 16 deg of the line of text, spanning both strokes. The junction
rules mitre the tip instead -- a cut from the crotch down the bisector to
the point, two columns fanning into one seam, half a stroke each (MARINE's
M) -- or, past the mitre's reach, leave the tip whole and pivot one column
through it (MFab's W). `lettering_columns_corner_fold` refuses an acute tip
(`long_way`), so it never reached these.

`testdata/apex_letters.json`: MARINE's M and N at 76.5 mm Hat (Becker hat
small) and MFab's W and N at 104.9 mm Hat, each as stage 7 handed it to
the lane (polygon and keyword arguments, `corner_fold` on, as #1057 flips
it), captured 2026-10-25 from main at 82b0bf28 with the md5 of the runs the
lane sewed then (`off_md5`); and MARINE's M at 101.9 mm (hat large), its
region polygon only (`cut_only`), for the cut.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point, Polygon

from digitizer_core import PipelineConfig, columns, pipeline
from digitizer_core import outline_cut as oc

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "apex_letters.json"
LANE = dict(fold_cuts=True, mitre_ends=True, rail_axis=True)


def _v(half_deg: float = 20.0, w: float = 1.2, h: float = 8.0) -> Polygon:
    """A V: two `w`-wide strokes `2 * half_deg` apart, meeting at a point
    (0, h) at the bottom (y down), the crotch on the axis above it."""
    a = math.radians(half_deg)
    xo = h * math.tan(a)
    xi = xo - w / math.cos(a)
    yc = h - (w / math.cos(a)) / math.tan(a)
    return Polygon([(-xo, 0), (-xi, 0), (0, yc), (xi, 0), (xo, 0), (0, h)])


W_L = 1.4
#: an L corner (legs 90 deg apart): `corner_fold`'s, not this rule's
L_SHAPE = Polygon([(0, 0), (W_L, 0), (W_L, 7 - W_L), (5, 7 - W_L), (5, 7), (0, 7)])


def _cut(poly, on: bool):
    with oc.apex_cut_scope(on):
        return oc.letter_columns(poly, 0.4, **LANE)


def _letters():
    out = {}
    for lab, v in json.loads(LETTERS.read_text(encoding="utf-8")).items():
        if v.get("cut_only"):
            continue
        kw = dict(v["kw"])
        for k in ("start_near", "end_near"):
            if kw.get(k) is not None:
                kw[k] = tuple(kw[k])
        out[lab] = (Polygon(v["exterior"], v["holes"]), v["shape_id"], kw, v["off_md5"])
    return out


def _sew(lab: str, on: bool):
    poly, sid, kw, _md5 = _letters()[lab]
    with oc.apex_cut_scope(on):
        return columns.lettering_columns_shape(poly, sid, **kw)


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(str(r.kind).encode())
        for x, y in r.points:
            h.update(f"{x:.6f},{y:.6f};".encode())
        h.update(b"|")
    return h.hexdigest()


def _covering(cols, p, tol: float = 0.21) -> list[int]:
    """The columns with a station cross within `tol` of point p (half the
    0.4 mm pitch and a hair: every point of a sewn column is that close)."""
    out = []
    for i, c in enumerate(cols):
        if any(LineString(s).distance(Point(p)) <= tol for s in c.stations):
            out.append(i)
    return out


def _cross_deg(s) -> float:
    (ax, ay), (bx, by) = s
    d = math.degrees(math.atan2(by - ay, bx - ax)) % 180.0
    return min(d, 180.0 - d)


# --- the flag and its wiring -------------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_apex_cut is False


def test_the_scope_sets_the_flag_and_puts_it_back():
    assert oc._APEX_CUT.get() is False
    with oc.apex_cut_scope(True):
        assert oc._APEX_CUT.get() is True
    assert oc._APEX_CUT.get() is False
    with oc.apex_cut_scope(False):
        assert oc._APEX_CUT.get() is False


def test_plan_stitches_sets_it_for_its_own_plan_only(monkeypatch):
    # `outline_cut` takes no config and the lane's call chain is not this
    # flag's (columns.py / stage 7): the plan sets it round its own body
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._APEX_CUT.get())
    assert pipeline.plan_stitches(None, PipelineConfig(lettering_columns_apex_cut=True)) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._APEX_CUT.get() is False


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("apex_cut code reached with the flag off")
    monkeypatch.setattr(oc, "_apex_cuts", boom)
    monkeypatch.setattr(oc, "_apex_tip_piece", boom)
    for poly in (_v(), _v(35.0, 1.2, 6.0), L_SHAPE):
        _cut(poly, False)
    _sew("mfab105_W", False)


# --- OFF: the defect, pinned, and byte for byte -------------------------------------

@pytest.mark.parametrize("lab", ["marine76_M", "marine76_N", "mfab105_W", "mfab105_N"])
def test_off_sews_exactly_what_main_sewed(lab):
    # md5 of the runs main sewed for this letter before the flag existed
    runs, _rep = _sew(lab, False)
    assert _md5(runs) == _letters()[lab][3]


def test_off_the_ms_v_is_a_mitre_two_half_columns_meet_down_the_middle():
    poly, _sid, _kw, _ = _letters()["marine76_M"]
    cut = _cut(poly, False)
    assert "mitre" in [c[2] for c in cut.cuts]
    # MARINE's M at 76.5 mm: crotch (-30.22, 13.26), tip (-29.87, 19.63)
    for f in (0.7, 0.85):
        p = (-30.22 + 0.35 * f, 13.26 + 6.37 * f)
        assert len(_covering(cut.columns, p)) == 2


# --- ON ---------------------------------------------------------------------------

@pytest.mark.parametrize("half,w,h", [(20.0, 1.2, 8.0), (35.0, 1.2, 6.0)])
def test_on_a_v_tip_is_one_column_square_to_its_axis(half, w, h):
    off, on = _cut(_v(half, w, h), False), _cut(_v(half, w, h), True)
    assert "apex" in [c[2] for c in on.cuts] and "mitre" not in [c[2] for c in on.cuts]
    tip = [c for c in on.columns if c.piece.distance(Point(0.0, h)) < 0.05]
    assert len(tip) == 1
    t = tip[0]
    # crosses square to the V's axis: level, spanning both strokes
    assert max(_cross_deg(s) for s in t.stations) < 2.0
    assert max(math.dist(*s) for s in t.stations) > 1.4 * w
    assert oc.pivot_sweep(t.stations) == 0.0
    # down to the point, and one column all the way: no seam on the axis
    assert min(abs(s[0][1] - h) for s in t.stations) < 0.45
    yc = h - (w / math.cos(math.radians(half))) / math.tan(math.radians(half))
    for f in (0.6, 0.8):
        assert len(_covering(on.columns, (0.0, yc + (h - yc) * f))) == 1
    # OFF pivots a column through the tip or meets two there
    assert max(oc.pivot_sweep(c.stations) for c in off.columns) > 40.0


def test_on_an_l_corner_is_left_to_the_corner_rules():
    # legs 90 deg apart: the pro folds an L (`corner_fold`); this rule refuses it
    off, on = _cut(L_SHAPE, False), _cut(L_SHAPE, True)
    assert on.cuts == off.cuts
    assert [c.stations for c in on.columns] == [c.stations for c in off.columns]
    assert "square" in oc._APEX_WHY


def test_on_the_ms_v_tip_is_one_column_of_level_crosses():
    poly, _sid, _kw, _ = _letters()["marine76_M"]
    on = _cut(poly, True)
    assert "mitre" not in [c[2] for c in on.cuts]
    for f in (0.7, 0.85):
        p = (-30.22 + 0.35 * f, 13.26 + 6.37 * f)
        hit = _covering(on.columns, p)
        assert len(hit) == 1
        assert max(_cross_deg(s) for s in on.columns[hit[0]].stations) < 2.0


def test_on_a_v_between_its_stems_cuts_at_the_crotch():
    # MARINE's M at 101.9 mm: the junction rules already cut beside the
    # crotch, so the tip's cross fits there; the V then runs at its width
    # between the stems' edges before it closes (a shoulder, then a point)
    v = json.loads(LETTERS.read_text(encoding="utf-8"))["marine102_M"]
    poly = Polygon(v["exterior"], v["holes"])
    off, on = _cut(poly, False), _cut(poly, True)
    assert "mitre" in [c[2] for c in off.cuts] and "mitre" not in [c[2] for c in on.cuts]
    assert "apex_stub" not in [c[2] for c in on.cuts]       # the cross runs through the crotch
    crotch, tip = (-40.25, 17.66), (-39.81, 26.18)
    for f in (0.5, 0.7, 0.85):
        p = (crotch[0] + (tip[0] - crotch[0]) * f, crotch[1] + (tip[1] - crotch[1]) * f)
        assert len(_covering(off.columns, p)) == 2
        hit = _covering(on.columns, p)
        assert len(hit) == 1
        assert max(_cross_deg(s) for s in on.columns[hit[0]].stations) < 2.0


def test_on_mfabs_w_is_seven_columns_like_the_pro_and_no_tip_fans():
    # the pro's AND WELDING W at 104.9 mm: 7 pieces, each tip one piece
    poly, _sid, _kw, _ = _letters()["mfab105_W"]
    off, on = _cut(poly, False), _cut(poly, True)
    assert len(on.columns) == 7 and len(off.columns) == 4
    tips = [(-13.24, 12.05), (-14.48, 5.26), (-9.92, 11.64)]
    for q in tips:
        hit = [c for c in on.columns if c.piece.distance(Point(q)) < 0.05]
        assert hit and min(oc.pivot_sweep(c.stations) for c in hit) == 0.0
    assert sum(c[2] == "apex" for c in on.cuts) >= 3


def test_on_marines_n_is_left_as_it_is():
    # its slab corner and its foot do not close as a V does (the pro sews
    # the slab as its own piece, the foot's stem and diagonal side by side)
    off, _ = _sew("marine76_N", False)
    on, _ = _sew("marine76_N", True)
    assert _md5(on) == _md5(off)


@pytest.mark.parametrize("lab", ["marine76_M", "mfab105_W", "mfab105_N"])
def test_on_sews_every_piece_and_loses_no_cover(lab):
    poly = _letters()[lab][0]
    off_runs, _ = _sew(lab, False)
    on_runs, rep = _sew(lab, True)
    assert rep["columns_unsewn"] == 0 and not rep["empty"]
    assert columns.satin_cover(on_runs, poly) >= columns.satin_cover(off_runs, poly) - 0.01
