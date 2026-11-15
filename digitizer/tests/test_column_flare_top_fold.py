"""`cfg.extra["lettering_columns_flare_top_fold"]` (2026-11-15, built OFF):
MARINE's I carries the top-left wedge its E and R carry, with no arm for
`fold_cap_flared`'s cap to run along, so the cut sews it as one straight stem
crossed level to the top. The pro (all five Becker files) folds it: upright
crosses over the wedge above its tip, a fan pivoting on the stem's edge at the
tip's height round the top-right corner, and the stem's level crosses below
(`outline_cut._FLARE_TOP_FOLD`).

`testdata/becker_I_letters.json`: the I's region at Becker hat large (102 mm)
and chest small (76 mm).
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

from shapely.geometry import LineString, Point, Polygon, box

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from tests.test_column_apex_cut import LANE

I_LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "becker_I_letters.json"


def _poly(lab: str) -> Polygon:
    v = json.loads(I_LETTERS.read_text(encoding="utf-8"))[lab]
    return Polygon(v["exterior"], v["holes"])


def _cut(poly, on: bool):
    with oc.flare_top_fold_scope(on):
        return oc.letter_columns(poly, 0.4, corner_fold=True, **LANE)


def _same(a, b) -> bool:
    return a.cuts == b.cuts and [c.stations for c in a.columns] == [c.stations for c in b.columns]


def _deg_off_upright(s) -> float:
    (ax, ay), (bx, by) = s
    d = math.degrees(math.atan2(abs(bx - ax), abs(by - ay)))
    return d


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._FLARE_TOP_FOLD.get() is False
    with oc.flare_top_fold_scope(True):
        assert oc._FLARE_TOP_FOLD.get() is True
    assert oc._FLARE_TOP_FOLD.get() is False


def test_plan_stitches_sets_it_from_the_extra_key_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._FLARE_TOP_FOLD.get())
    on = replace(PipelineConfig(), extra={"lettering_columns_flare_top_fold": True})
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._FLARE_TOP_FOLD.get() is False


def test_the_wedge_is_read_at_both_sizes():
    for lab in ("marine102_I", "marine76_I"):
        lc = _cut(_poly(lab), False)
        w = oc._top_wedge(lc.poly, lc.W)
        assert w is not None, lab
        q, tip, notch, p = w
        top = lc.poly.bounds[1]
        assert 1.1 * lc.W < tip[1] - top < 1.2 * lc.W          # MARINE's I: 1.16-1.17 W
        assert abs(p[1] - tip[1]) < 1e-9 and tip[0] < p[0] < q[0]


def test_a_plain_stem_has_no_wedge():
    lc = _cut(box(0.0, 0.0, 4.0, 16.0), True)
    assert oc._top_wedge(lc.poly, lc.W) is None
    assert [c.kind for c in lc.columns] == ["straight"]


def test_off_is_the_lane_as_it_was():
    for lab in ("marine102_I", "marine76_I"):
        poly = _poly(lab)
        assert _same(_cut(poly, False), oc.letter_columns(poly, 0.4, corner_fold=True, **LANE))


def test_on_the_i_is_one_column_folded_round_the_wedge():
    for lab in ("marine102_I", "marine76_I"):
        lc = _cut(_poly(lab), True)
        assert [c.kind for c in lc.columns] == ["folded"], lab
        col = lc.columns[0]
        q, tip, notch, p = oc._top_wedge(lc.poly, lc.W)
        st = col.stations
        # it starts upright over the wedge, left of the pivot
        assert _deg_off_upright(st[0]) < 10.0 and max(st[0][0][0], st[0][1][0]) < p[0]
        # the fan: crosses from the pivot, one of them reaching the top-right corner's neighbourhood
        fan = [s for s in st if math.dist(s[0], p) < 1e-6 or math.dist(s[1], p) < 1e-6]
        x1, top = lc.poly.bounds[2], lc.poly.bounds[1]
        assert len(fan) >= 5
        assert any(math.dist(e, (x1, top)) < 0.5 for s in fan for e in s)
        # and it ends on the stem's level crosses
        assert _deg_off_upright(st[-1]) > 80.0
        # the wedge's upper half is sewn (a cross within half a pitch of its middle)
        mid = ((q[0] + tip[0]) / 2 + 0.15, (q[1] + tip[1]) / 2 + 0.6)
        assert lc.poly.contains(Point(mid))
        assert any(LineString(s).distance(Point(mid)) <= 0.21 for s in st)
