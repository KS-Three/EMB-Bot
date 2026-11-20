"""`cfg.extra["lettering_columns_a_cap_centered"]` (2026-11-17, built OFF):
a gate on `apex_pro_joints`' flat A (`outline_cut._A_CAP_CENTERED`).

The A's band reads "a counter pointed on top under a straight top run".
Becker MARINE's R passes it: its counter is a pentagon whose top vertex sits at
the counter's left edge, so the R was cut by the A's full-width level band,
the slab sewn apart from the bowl. The pro sews slab + bowl as one piece
(`docs/big-letter-construction-2026-10-24.md`, R row). ON, the band needs the
counter's top vertex in the middle third of the counter's width.

`testdata/marine102_R_letter.json`: the R of Becker's 102 mm hat as stage 7
hands it to the lane (the polygon `letter_columns` receives).
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from tests._apex_letters import LANE, LETTERS

R102 = Path(__file__).resolve().parent.parent / "testdata" / "marine102_R_letter.json"


def _r() -> Polygon:
    v = json.loads(R102.read_text(encoding="utf-8"))
    return Polygon(v["exterior"], v["holes"])


def _a() -> Polygon:
    v = json.loads(LETTERS.read_text(encoding="utf-8"))["marine102_A"]
    return Polygon(v["exterior"], v["holes"])


def _cut(poly, centered: bool):
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), \
            oc.fold_cap_flared_scope(True), oc.a_cap_centered_scope(centered):
        return oc.letter_columns(poly, 0.4, **LANE)


def _key(lc):
    return lc.cuts, [c.stations for c in lc.columns]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._A_CAP_CENTERED.get() is False
    with oc.a_cap_centered_scope(True):
        assert oc._A_CAP_CENTERED.get() is True
    assert oc._A_CAP_CENTERED.get() is False


def test_plan_stitches_sets_it_from_the_extra_key_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._A_CAP_CENTERED.get())
    on = replace(PipelineConfig(), extra={"lettering_columns_a_cap_centered": True})
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._A_CAP_CENTERED.get() is False


def test_off_the_r_is_cut_by_the_a_band_across_its_whole_width():
    lc = _cut(_r(), False)
    bands = [k for k in lc.cuts if k[2] == "apex_pro_cap"]
    assert len(bands) == 1
    x0, _t, x1, _b = lc.poly.bounds
    assert abs(bands[0][0][1] - bands[0][1][1]) < 1e-6           # level
    assert bands[0][3] > 0.8 * (x1 - x0)                           # edge to edge: slab apart from bowl
    assert len(lc.columns) == 4


def test_on_the_r_has_no_band_and_slab_and_bowl_are_one_piece():
    off, on = _cut(_r(), False), _cut(_r(), True)
    assert not [k for k in on.cuts if k[2] == "apex_pro_cap"]
    assert len(on.columns) == len(off.columns) - 1
    # the stem's top-left cap and the stem are still cut as before
    assert [k for k in on.cuts if k[2] == "apex_pro_shoulder"]


def test_a_flat_topped_a_keeps_its_band_with_the_flag_on():
    a = _a()
    off, on = _cut(a, False), _cut(a, True)
    assert [k for k in off.cuts if k[2] == "apex_pro_cap"]
    assert _key(on) == _key(off)


def test_off_is_the_lane_as_it_was():
    r = _r()
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True):
        plain = oc.letter_columns(r, 0.4, **LANE)
    assert _key(_cut(r, False)) == _key(plain)
