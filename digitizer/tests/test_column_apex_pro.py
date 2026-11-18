"""`cfg.lettering_columns_apex_pro` (2026-11-14, built OFF as a `cfg.extra` key; ON since
2026-11-15, Kent's flip): a
down-pointing V tip is cut the way the pro's Becker MARINE files cut it
(`docs/apex-pro-construction-2026-11-14.md`, `outline_cut._APEX_PRO`):

- ONE split line from the crotch, continuing the right-hand leg's inner edge
  across the joint (not apex_cut's level cross, not the OFF mitre);
- the piece holding the point (the right-hand leg and the point) is one
  column of LEVEL crosses from the point up;
- an up-pointing tip (an A's apex) is left as OFF.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import LineString, Point

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from tests.test_column_apex_cut import LANE, LETTERS, _v


def _poly(lab: str):
    import json
    from shapely.geometry import Polygon
    v = json.loads(LETTERS.read_text(encoding="utf-8"))[lab]
    return Polygon(v["exterior"], v["holes"])


def _cut(poly, pro: bool, apex: bool = False):
    with oc.apex_cut_scope(apex), oc.apex_pro_scope(pro):
        return oc.letter_columns(poly, 0.4, **LANE)


def _same(a, b) -> bool:
    return a.cuts == b.cuts and [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._APEX_PRO.get() is False
    with oc.apex_pro_scope(True):
        assert oc._APEX_PRO.get() is True
    assert oc._APEX_PRO.get() is False


def test_plan_stitches_sets_it_from_the_field_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._APEX_PRO.get())
    assert pipeline.plan_stitches(None, PipelineConfig()) is False     # OFF again since 2026-11-17 (Kent's revert)
    on = replace(PipelineConfig(), lettering_columns_apex_pro=True)
    assert pipeline.plan_stitches(None, on) is True
    assert oc._APEX_PRO.get() is False


def test_off_is_the_lane_as_it_was():
    for poly in (_v(20.0, 1.2, 8.0), _poly("marine102_M"), _poly("marine102_A")):
        assert _same(_cut(poly, False), oc.letter_columns(poly, 0.4, **LANE))


def _level(col) -> bool:
    return all(abs(a[1] - b[1]) < 1e-6 for a, b in col.stations)


def test_marine_m_one_split_and_the_point_sewn_level_from_the_point_up():
    poly = _poly("marine102_M")
    lc = _cut(poly, True)
    splits = [c for c in lc.cuts if c[2] == "apex_pro"]
    assert len(splits) == 1
    assert "mitre" not in [c[2] for c in lc.cuts]
    (a, b, _r, L) = splits[0]
    # the split runs down-LEFT from the crotch: it continues the right leg's
    # inner edge, so its two ends differ in x and in y (not a level cross)
    assert abs(a[0] - b[0]) > 0.3 * L and abs(a[1] - b[1]) > 0.3 * L
    point = (-39.80575044171564, 26.179763867608436)        # the V's point (the fixture's vertex)
    owner = [c for c in lc.columns if c.piece.distance(Point(point[0], point[1] - 0.3)) < 1e-6]
    assert len(owner) == 1 and _level(owner[0])
    assert owner[0].piece.distance(LineString([a, b])) < 1e-6
    ys = [s[0][1] for s in owner[0].stations]
    # from the point (its lowest cross within a millimetre of it) ...
    assert max(ys) > point[1] - 1.0
    # ... up past the crotch and on up the right leg
    assert min(ys) < min(a[1], b[1]) - 1.0


def test_marine_m_the_left_stem_ends_level_at_the_crotch_and_the_fan_takes_its_top():
    poly = _poly("marine102_M")
    lc = _cut(poly, True)
    crotch_y = 17.661480318266765                          # the V's crotch (the fixture's vertex)
    sh = [c for c in lc.cuts if c[2] == "apex_pro_shoulder"]
    assert len(sh) == 1
    (a, b, _r, _L) = sh[0]
    assert abs(a[1] - crotch_y) < 1e-6 and abs(b[1] - crotch_y) < 1e-6      # level, at the crotch's height
    assert min(a[0], b[0]) < -48.0                                          # right across the stem
    # the stem's column stops there; the fan above it reaches the letter's top
    stem = [c for c in lc.columns if c.piece.distance(Point(-46.0, 25.0)) < 1e-6]
    fan = [c for c in lc.columns if c.piece.distance(Point(-46.0, 15.5)) < 1e-6]
    assert len(stem) == 1 and len(fan) == 1 and stem[0] is not fan[0]
    assert min(y for s in stem[0].stations for _x, y in s) > crotch_y - 0.5


def test_an_a_apex_points_up_and_is_left_as_off():
    poly = _poly("marine102_A")
    assert _same(_cut(poly, True), _cut(poly, False))


def test_a_3mm_v_takes_the_split():
    lc = _cut(_v(20.0, 3.0, 12.0), True)
    assert [c[2] for c in lc.cuts].count("apex_pro") == 1


def test_a_stroke_under_the_read_width_is_left_as_off():
    # MFab's 1.2 mm WELDING: no pro reading reached it (`APEX_PRO_MIN_W_MM`)
    poly = _v(20.0, 1.2, 8.0)
    assert _same(_cut(poly, True), _cut(poly, False))
