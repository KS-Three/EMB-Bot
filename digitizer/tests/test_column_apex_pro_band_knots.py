"""`cfg.extra["lettering_columns_apex_pro_band_knots"]` (2026-11-15, built OFF):
a gate on `apex_pro_joints`' flat A (`outline_cut._APEX_BAND_KNOTS`).

The fold look's sewn judge refuses a cut that sews more SHORT legs, or more
CROSSED legs, than the cut it is measured against, each count on its own.
Under a flat A's band, at Becker LC large (95.7 mm), the band took two short
legs off the level cut across the A's left leg. The diagonal cut main takes
there was then refused for its two short legs, although it sews two fewer
folds and six fewer crossed legs. The leg below the crossbar sewed as one
curved column with the bar, at a steep slant where the pro and main sew it
level. ON, in a letter that carries a band, short and crossed legs are one
knot count.

`testdata/becker96_A_letter.json`: that A as stage 7 hands it to the lane
(`columns.lettering_columns_shape`), with the lane flags it passes.
"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, columns, pipeline
from digitizer_core import outline_cut as oc

A96 = Path(__file__).resolve().parent.parent / "testdata" / "becker96_A_letter.json"


def _letter():
    v = json.loads(A96.read_text(encoding="utf-8"))["marine96_A"]
    kw = dict(v["kw"])
    for k in ("start_near", "end_near"):
        if kw.get(k) is not None:
            kw[k] = tuple(kw[k])
    return Polygon(v["exterior"], v["holes"]), v["shape_id"], kw


def _sew(knots: bool, joints: bool = True):
    poly, sid, kw = _letter()
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(joints), \
            oc.fold_cap_flared_scope(True), oc.apex_band_knots_scope(knots):
        runs, _report = columns.lettering_columns_shape(poly, sid, **kw)
    return poly, runs


def _key(runs):
    return [(r.points, r.kind, r.jump, r.trim) for r in runs]


def _leg_angles(poly, runs) -> list[float]:
    """Degrees off level of the satin crosses in the left leg below the
    crossbar (the counter's foot is at y 23.8, the baseline at 29.7)."""
    x0 = poly.bounds[0]
    out = []
    for r in runs:
        if r.kind != "satin":
            continue
        for a, b in zip(r.points[:-1], r.points[1:]):
            mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
            if x0 + 0.5 < mx < x0 + 4.0 and 24.5 < my < 28.5 and math.dist(a, b) > 1.0:
                d = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
                out.append(min(d, 180.0 - d))
    return sorted(out)


def _median(xs):
    return xs[len(xs) // 2]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._APEX_BAND_KNOTS.get() is False
    with oc.apex_band_knots_scope(True):
        assert oc._APEX_BAND_KNOTS.get() is True
    assert oc._APEX_BAND_KNOTS.get() is False


def test_plan_stitches_sets_it_from_the_extra_key_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._APEX_BAND_KNOTS.get())
    on = replace(PipelineConfig(), extra={"lettering_columns_apex_pro_band_knots": True})
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._APEX_BAND_KNOTS.get() is False


def test_without_a_band_it_changes_nothing():
    # no `apex_pro_joints`, no band: the judge reads as it always has
    _p, off = _sew(knots=False, joints=False)
    _p, on = _sew(knots=True, joints=False)
    assert _key(on) == _key(off)


def test_off_the_left_leg_below_the_bar_sews_steep():
    poly, runs = _sew(knots=False)
    ang = _leg_angles(poly, runs)
    assert ang and _median(ang) > 45.0


def test_on_the_left_leg_sews_level_as_main_and_the_pro_do():
    poly, runs = _sew(knots=True)
    ang = _leg_angles(poly, runs)
    assert ang and _median(ang) < 10.0
