"""`cfg.fill_bridge_cut` (default OFF): a fill bridge dearer than the cut it
avoids is lifted instead of sewn.

`_score` already says what a trim is worth (`_TRIM_STITCH_EQUIVALENT`, 25) and
what a stitch lying on finished fill is worth (`_EXPOSED_STITCH_WEIGHT`, 2) —
both Kent's, ratified 2026-09-03 — but it is only ever asked to compare two
whole column ORDERS. `emit` never asks it about one BRIDGE: any in-shape route
is sewn however exposed, and the thread is lifted only when no route exists.
Traced 2026-09-19 (`tools/travel_legs.py`): Becker's worst leg laps a finished
column for 24.5 mm to cross an 8.4 mm gap, a bridge that costs 34.6 at the
scorer's own rate against the cut's 25.

No constant is added or moved; the rule prices one bridge with the two the
scorer already has. The fixtures are shapely polygons on purpose — a traced
raster's outline differs by platform, and Becker's leg exists because of a
0.20 mm notch.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage6_fill import (
    _EXPOSED_STITCH_WEIGHT, _EXPOSED_TOLERANCE_MM, _TRIM_STITCH_EQUIVALENT,
    _cut_is_cheaper, _densify, _inset_ring, _order_cost, stitch_shape,
)

TRIM_AT = 3.0
ROW = 0.4

# A band with two legs hanging off it, rows horizontal. The band sews first;
# from the foot of the first leg the second leg's start is 30.9 mm away across
# the open gap, so the only in-shape route climbs back up the leg just sewn.
_COMB = unary_union([box(0, 0, 30, 6), box(0, 6, 10, 30), box(20, 6, 30, 30)])


def _sew(**kw):
    runs, _report = stitch_shape(_COMB, "S1", angle_deg=0.0, row_mm=ROW, stitch_mm=3.0,
                                 underlay_style="none", trim_at_mm=TRIM_AT, **kw)
    return runs


def _bridges(runs):
    """-> [(gap_mm, exposed_mm, cost)] per TRAVEL run, priced as `_score` prices."""
    sewn = None
    out = []
    for i, r in enumerate(runs):
        if r.kind == "fill" and len(r.points) > 1:
            fp = LineString(r.points).simplify(ROW / 2.0).buffer(ROW)
            sewn = fp if sewn is None else sewn.union(fp)
        elif r.kind == "travel":
            a, b = runs[i - 1].points[-1], runs[i + 1].points[0]
            route = [a] + list(r.points) + [b]
            over = 0.0 if sewn is None else LineString(route).intersection(sewn).length
            exposed = max(0.0, over - _EXPOSED_TOLERANCE_MM)
            cost = len(r.points) + exposed / machine.TRAVEL_STITCH_MM * _EXPOSED_STITCH_WEIGHT
            out.append((math.dist(a, b), exposed, cost))
    return out


def _fill_points(runs):
    return sorted(p for r in runs if r.kind == "fill" for p in r.points)


def test_the_flag_is_off_by_default():
    assert PipelineConfig().fill_bridge_cut is False


def test_a_long_bridge_on_finished_fill_is_dearer_than_the_cut():
    sewn = box(0, 0, 100, 10)
    a, b = (1.0, 5.0), (41.0, 5.0)
    assert _cut_is_cheaper(a, _densify(a, b, machine.TRAVEL_STITCH_MM), sewn, TRIM_AT)


def test_a_short_hop_on_finished_fill_is_not():
    sewn = box(0, 0, 100, 10)
    a, b = (1.0, 5.0), (9.0, 5.0)
    assert not _cut_is_cheaper(a, _densify(a, b, machine.TRAVEL_STITCH_MM), sewn, TRIM_AT)


def test_a_hidden_bridge_is_never_cut_however_long():
    """Travel under fill still to come is what the pros do; only thread that
    will SHOW is weighed against a cut."""
    elsewhere = box(0, 50, 100, 60)
    a, b = (1.0, 5.0), (91.0, 5.0)
    bridge = _densify(a, b, machine.TRAVEL_STITCH_MM)
    assert not _cut_is_cheaper(a, bridge, elsewhere, TRIM_AT)
    assert not _cut_is_cheaper(a, bridge, None, TRIM_AT)


def test_a_gap_under_trim_at_is_left_alone():
    """There the lift is a jump, not a cut, and DOCTRINE already priced that
    arm out (2026-09-11: 26 mm corpus-wide). This rule only trades against a
    real trim."""
    sewn = box(0, 0, 100, 40)
    a, b = (1.0, 5.0), (3.0, 5.0)
    loop = []
    cur = a
    for p in ((1.0, 35.0), (3.0, 35.0), b):
        loop.extend(_densify(cur, p, machine.TRAVEL_STITCH_MM))
        cur = p
    assert math.dist(a, b) < TRIM_AT
    assert not _cut_is_cheaper(a, loop, sewn, TRIM_AT)


def test_the_fixture_sews_a_bridge_dearer_than_a_cut_today():
    dear = [c for gap, _e, c in _bridges(_sew(under_cover=True)) if gap > TRIM_AT]
    assert dear and max(dear) > _TRIM_STITCH_EQUIVALENT, dear


def test_flag_on_sews_no_bridge_dearer_than_a_cut():
    off, on = _sew(under_cover=True), _sew(under_cover=True, cut_bridges=True)
    dear = [c for gap, _e, c in _bridges(on) if gap > TRIM_AT]
    assert all(c <= _TRIM_STITCH_EQUIVALENT for c in dear), dear
    assert sum(e for _g, e, _c in _bridges(on)) < sum(e for _g, e, _c in _bridges(off))
    assert sum(1 for r in on if r.trim) > sum(1 for r in off if r.trim)
    # Only travel and lifts move: every fill penetration is sewn either way.
    assert _fill_points(on) == _fill_points(off)


def test_flag_off_is_the_engine_as_it_was():
    base = _sew(under_cover=True)
    explicit = _sew(under_cover=True, cut_bridges=False)
    assert [(r.kind, r.points, r.jump, r.trim) for r in explicit] == \
        [(r.kind, r.points, r.jump, r.trim) for r in base]


def test_the_rule_is_inert_without_covered_routing():
    """Exposure is only tracked under `fill_travel_under_cover`; without it
    there is nothing to price, and the flag must change nothing."""
    plain = _sew(under_cover=False)
    flagged = _sew(under_cover=False, cut_bridges=True)
    assert [(r.kind, r.points, r.jump, r.trim) for r in flagged] == \
        [(r.kind, r.points, r.jump, r.trim) for r in plain]


def _stage7_hands_over(monkeypatch, **cfg_kw) -> list:
    """Stages 5-7 for real on a hand-built one-shape result (the pattern
    `test_photo_width_floor._one_shape_result` uses), with the real
    `stitch_shape` wrapped to record what stage 7 asked it for. The pipeline
    picks its own fill angle and sews this comb as one column, so the PLAN
    cannot show the flag -- what stage 7 hands over is the thing under test."""
    from digitizer_core import stage7_sequence
    from digitizer_core.pipeline import BackgroundInfo, PipelineResult, plan_stitches
    from digitizer_core.regions import Region
    from digitizer_core.threads import chart_for

    seen: list = []
    real = stage7_sequence.stitch_shape

    def recording(*a, **k):
        seen.append(k.get("cut_bridges"))
        return real(*a, **k)

    monkeypatch.setattr(stage7_sequence, "stitch_shape", recording)
    cfg = PipelineConfig(**cfg_kw)
    poly = unary_union([box(-25, -20, 25, -10), box(-25, -10, -11, 20), box(11, -10, 25, 20)])
    chart = chart_for(cfg)
    region = Region(shape_id="Scomb0001", polygon=poly, thread_index=0,
                    thread_number=chart[0].number, area_mm2=poly.area,
                    meta={"layer": 0, "stitched": True})
    plan_stitches(PipelineResult(
        regions=[region],
        palette=[{"brand": chart.label, "brand_id": chart.id,
                  "number": region.thread_number, "name": "x", "rgb": [0, 0, 0]}],
        background=BackgroundInfo(detected=False), px_per_mm=10.0,
        design_size_mm=(50.0, 40.0)), cfg)
    return seen


def test_the_config_flag_reaches_the_fill_tier(monkeypatch):
    assert _stage7_hands_over(monkeypatch) == [False]
    assert _stage7_hands_over(monkeypatch, fill_bridge_cut=True) == [True]


def test_every_site_that_passes_covered_routing_passes_the_cut_rule():
    """Seven call sites hand `stitch_shape` the covered-routing flag (five in
    stage 7, two in the blend tier) and the cut rule is inert without it, so
    the two travel together. A new site that copies one and not the other
    sews one tier by a different rule with nothing failing."""
    import re
    from pathlib import Path

    import digitizer_core
    sites = 0
    for f in sorted(Path(digitizer_core.__file__).parent.glob("*.py")):
        src = f.read_text(encoding="utf-8")
        for m in re.finditer(r"under_cover=cfg\.fill_travel_under_cover,", src):
            sites += 1
            call_end = src.index(")", m.end())
            assert "cut_bridges=cfg.fill_bridge_cut" in src[m.end():call_end], (
                f"{f.name}:{src.count(chr(10), 0, m.start()) + 1}")
    assert sites >= 7


def test_the_scorer_counts_the_lift_the_emitter_will_make():
    """DOCTRINE 2026-09-11: scorer and emitter must agree before any order
    guard can be trusted. Same paths, same order: one more cut, less exposed."""
    paths = [list(r.points) for r in _sew(under_cover=True) if r.kind == "fill"]
    ring = _inset_ring(_COMB, machine.TRAVEL_INSET_MM)
    slack = _COMB.buffer(0.01)
    off = _order_cost(paths, _COMB, ring, slack, None, TRIM_AT, ROW)
    on = _order_cost(paths, _COMB, ring, slack, None, TRIM_AT, ROW, cut_bridges=True)
    assert on[0] == off[0] + 1, (off, on)
    assert on[2] < off[2], (off, on)
