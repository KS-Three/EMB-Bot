"""`cfg.lettering_columns_apex_pro_joints` (2026-11-14, built OFF as a `cfg.extra` key; ON since
2026-11-15, Kent's flip):
the joints `apex_pro` read but did not build, cut the way the pro's Becker
MARINE files cut them (`docs/apex-pro-construction-2026-11-14.md`, section 5;
`outline_cut._APEX_PRO_JOINTS`):

- an N's top-left: the stem stops on a level line `APEX_PRO_NECK_W` stroke
  widths below the top, and the diagonal's piece takes the stem's top;
- an N's foot: the diagonal ends on a level line `APEX_PRO_FOOT_W` W above the
  baseline, and the stem's piece takes the foot below it;
- a flat-topped A (a counter pointed on top): a band `APEX_PRO_CAP_W` W deep
  across the top, crossed upright.
"""
from __future__ import annotations

import json
from dataclasses import replace

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from tests.test_column_apex_cut import LANE, LETTERS


def _poly(lab: str) -> Polygon:
    v = json.loads(LETTERS.read_text(encoding="utf-8"))[lab]
    return Polygon(v["exterior"], v["holes"])


def _cut(poly, joints: bool, pro: bool = False):
    with oc.apex_pro_scope(pro), oc.apex_pro_joints_scope(joints):
        return oc.letter_columns(poly, 0.4, **LANE)


def _same(a, b) -> bool:
    return a.cuts == b.cuts and [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._APEX_PRO_JOINTS.get() is False
    with oc.apex_pro_joints_scope(True):
        assert oc._APEX_PRO_JOINTS.get() is True
    assert oc._APEX_PRO_JOINTS.get() is False


def test_plan_stitches_sets_it_from_the_field_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._APEX_PRO_JOINTS.get())
    assert pipeline.plan_stitches(None, PipelineConfig()) is True      # ON since 2026-11-15
    off = replace(PipelineConfig(), lettering_columns_apex_pro_joints=False)
    assert pipeline.plan_stitches(None, off) is False
    assert oc._APEX_PRO_JOINTS.get() is False


def test_off_is_the_lane_as_it_was():
    for lab in ("marine76_N", "marine102_A", "marine102_M"):
        poly = _poly(lab)
        assert _same(_cut(poly, False), oc.letter_columns(poly, 0.4, **LANE))


def test_n_top_the_stem_stops_level_and_the_diagonal_takes_its_top():
    poly = _poly("marine76_N")
    lc = _cut(poly, True)
    W = lc.W
    top = lc.poly.bounds[1]
    sh = [c for c in lc.cuts if c[2] == "apex_pro_shoulder"]
    assert len(sh) == 1
    (a, b, _r, _L) = sh[0]
    assert abs(a[1] - b[1]) < 1e-6 and abs(a[1] - (top + oc.APEX_PRO_NECK_W * W)) < 1e-6
    # the stem's top-left corner is sewn by the piece that also holds the diagonal
    x0 = lc.poly.bounds[0]
    corner = Point(x0 + 0.6 * W, top + 0.2 * W)
    m = a if a[0] > b[0] else b                  # the cut's end on the stem's inner edge
    diag = Point(m[0] + 0.5 * W, m[1] + 1.0 * W)     # just inside the diagonal, below the cap
    owner = [c for c in lc.columns if c.piece.distance(corner) < 1e-6]
    assert len(owner) == 1 and owner[0].piece.distance(diag) < 1e-6


def test_n_foot_the_diagonal_ends_level_and_the_stem_takes_the_foot():
    poly = _poly("marine76_N")
    lc = _cut(poly, True)
    W = lc.W
    base = lc.poly.bounds[3]
    ft = [c for c in lc.cuts if c[2] == "apex_pro_foot"]
    assert len(ft) == 1
    (a, b, _r, _L) = ft[0]
    assert abs(a[1] - b[1]) < 1e-6 and abs(a[1] - (base - oc.APEX_PRO_FOOT_W * W)) < 1e-6
    m = a if a[0] > b[0] else b                      # on the right stem's inner edge line
    tail = Point(m[0] - 0.05, m[1] + 0.05)             # the diagonal's tail, just under the line
    stem = Point(lc.poly.bounds[2] - 0.5 * W, base - 3.0 * W)
    owner = [c for c in lc.columns if c.piece.distance(tail) < 1e-6]
    assert len(owner) == 1 and owner[0].piece.distance(stem) < 1e-6


def test_flat_a_top_is_a_band_crossed_upright():
    poly = _poly("marine102_A")
    lc = _cut(poly, True)
    W = lc.W
    top = lc.poly.bounds[1]
    caps = [c for c in lc.cuts if c[2] == "apex_pro_cap"]
    assert len(caps) == 1
    y = caps[0][0][1]
    assert abs(y - (top + oc.APEX_PRO_CAP_W * W)) < 1e-6
    band = [c for c in lc.columns if c.piece.distance(Point(caps[0][0][0] + 2.0, y - 0.3)) < 1e-6]
    assert len(band) == 1
    assert all(abs(p[0] - q[0]) < 1e-6 for p, q in band[0].stations)       # upright crosses


def test_a_flat_topped_counter_is_an_o_not_an_a():
    # ProSeal's O took the band before the pointed-counter test: a square ring
    # has a flat top and a counter flat on top
    ring = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(3, 3), (7, 3), (7, 7), (3, 7)]])
    assert "apex_pro_cap" not in [c[2] for c in _cut(ring, True).cuts]


def test_with_apex_pro_the_m_is_cut_once():
    # the M's V belongs to apex_pro; the joints rule leaves a joint it cut alone
    poly = _poly("marine102_M")
    assert _same(_cut(poly, True, pro=True), _cut(poly, False, pro=True))
