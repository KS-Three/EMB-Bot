"""`cfg.extra["lettering_columns_through_last"]` (built OFF 2026-11-19): at a
T junction the butting stroke is sewn first and the stroke it butts WHOLE,
over its root -- the professional's order on Gaulke Roofing LC
(`c golke logo LC.DST`, 95.2 mm): the T is its stem, then one bar across; the
E its middle arm, then one column top arm -> stem -> bottom arm.

Replayed on the four STEEL letters exactly as stage 7 hands them to the
Column lane at 95.2 mm left chest under `lettering_columns_reading_order`
(`testdata/gaulke95_lane_letters.json`; `pull_keep`, a geometry, is not
recorded).
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import columns, stitches
from digitizer_core.columns import _THROUGH_LAST, _through_last_walk, through_last_scope

LETTERS = Path(__file__).resolve().parent.parent / "testdata" / "gaulke95_lane_letters.json"


def _letter(key):
    v = json.loads(LETTERS.read_text(encoding="utf-8"))[key]
    kw = {k: (tuple(x) if isinstance(x, list) else x) for k, x in v["kw"].items() if k != "_skipped"}
    return Polygon(v["exterior"], v["holes"]), kw


def _sew(key, on: bool):
    poly, kw = _letter(key)
    with through_last_scope(on):
        runs, rep = columns.lettering_columns_shape(poly, key, **kw)
    return poly, runs, rep


def _satins(runs):
    return [r for r in runs if r.kind == stitches.SATIN and len(r.points) >= 2]


def _ground(runs):
    return unary_union([LineString(r.points).buffer(0.2) for r in _satins(runs)])


@pytest.fixture(scope="module")
def sewn():
    return {(k, on): _sew(k, on) for k in ("T", "E1", "E2", "L") for on in (False, True)}


def test_config_default_is_on_and_pre_flip_is_off():
    # ON since 2026-11-19 (Kent: "satin_overlap_run (Recommended), outline_loop_split_shared, through_last,
    # e_top_arm + top_slab"; then "Hold OFF, fix the leg (Recommended)")
    from digitizer_core import PipelineConfig
    from tests.conftest import PRE_FLIP
    assert PipelineConfig().lettering_columns_through_last is True
    assert PRE_FLIP["lettering_columns_through_last"] is False
    assert PipelineConfig(lettering_columns_through_last=False).lettering_columns_through_last is False


def test_walk_is_kept_only_with_no_longer_hop_in():
    import inspect
    from digitizer_core import columns
    assert "kp[4] <= kb[4]" in inspect.getsource(columns.column_runs)


def test_off_sets_nothing():
    with through_last_scope(False):
        assert _THROUGH_LAST.get() is False
    with through_last_scope(True):
        assert _THROUGH_LAST.get() is True
    assert _THROUGH_LAST.get() is False


def test_t_bar_is_one_satin_after_the_stem(sewn):
    poly, off, _ = sewn[("T", False)]
    _, on, rep = sewn[("T", True)]
    w = poly.bounds[2] - poly.bounds[0]

    def bar_runs(runs):
        return [r for r in _satins(runs)
                if max(y for _x, y in r.points) - min(y for _x, y in r.points) < 0.5 * w]
    # today: the bar in two halves, the stem sewn between them
    assert len(bar_runs(off)) == 2
    bars = bar_runs(on)
    assert len(bars) == 1, "the bar sews whole"
    xs = [x for x, _y in bars[0].points]
    assert max(xs) - min(xs) >= 0.9 * w
    sat = _satins(on)
    assert sat.index(bars[0]) == len(sat) - 1, "the bar is the last satin, over the stem's top"
    assert rep.get("through_last") == 1


@pytest.mark.parametrize("key", ["E1", "E2"])
def test_e_stem_is_one_column_after_the_middle_arm(sewn, key):
    poly, off, _ = sewn[(key, False)]
    _, on, rep = sewn[(key, True)]
    h = poly.bounds[3] - poly.bounds[1]

    def tall(runs):
        return [r for r in _satins(runs)
                if max(y for _x, y in r.points) - min(y for _x, y in r.points) >= 0.9 * h]
    assert not tall(off), "today the stem sews in two halves"
    t = tall(on)
    assert len(t) == 1, "top arm, stem and bottom arm are one satin"
    sat = _satins(on)
    assert sat.index(t[0]) == len(sat) - 1, "the middle arm is sewn first, under the stem"
    assert rep.get("through_last") == 1


@pytest.mark.parametrize("key", ["T", "E1", "E2", "L"])
def test_a_reorder_removes_no_geometry_and_adds_no_trim(sewn, key):
    _, off, _ = sewn[(key, False)]
    _, on, _ = sewn[(key, True)]
    a, b = _ground(off), _ground(on)
    assert b.area >= 0.98 * a.area
    assert a.difference(b).area <= 0.02 * a.area
    assert sum(bool(r.trim) for r in on) <= sum(bool(r.trim) for r in off)


def test_l_has_no_junction_and_is_unchanged(sewn):
    _, off, _ = sewn[("L", False)]
    _, on, rep = sewn[("L", True)]
    assert [(r.points, r.kind, r.jump, r.trim) for r in on] == [(r.points, r.kind, r.jump, r.trim) for r in off]
    assert "through_last" not in rep


@pytest.mark.parametrize("on", [False, True])
def test_steel_l_keeps_its_foot(sewn, on):
    # the review pack's "STEEI" (ref ef11041f, `lettering_columns_reading_order`
    # at 80 mm): the L's satin covered its stem only and the foot showed only
    # where a travel run happened to lie along it. On this ref the L is one
    # folded column: its satin covers the whole letter, the foot included.
    poly, runs, _ = sewn[("L", on)]
    x0, y0, x1, y1 = poly.bounds
    foot = poly.intersection(Polygon([(x0 + 0.5 * (x1 - x0), y1 - 0.25 * (y1 - y0)), (x1, y1 - 0.25 * (y1 - y0)),
                                      (x1, y1), (x0 + 0.5 * (x1 - x0), y1)]))
    g = _ground(runs)
    assert foot.area > 0.5
    assert g.intersection(foot).area >= 0.95 * foot.area
    assert g.intersection(poly).area >= 0.95 * poly.area


def _span(ci, i0, i1, na, nb):
    return dict(ci=ci, i0=i0, i1=i1, na=na, nb=nb)


def test_walk_satin_is_every_spans_last_visit():
    # a T: bar column 0 split at its junction (node 1) into spans 0 (end 0 -> 1)
    # and 1 (1 -> end 2); the stem, column 1, butts it at node 1, tip node 3
    nodes = [(0.0, 0.0), (2.0, 0.0), (4.0, 0.0), (2.0, 4.0)]
    spans = [_span(0, 0, 5, 0, 1), _span(0, 5, 10, 1, 2), _span(1, 0, 10, 1, 3)]
    junctions = [dict(ci=1, end=0, through=0, k=5)]
    # the postman's walk from the bar's right end: right half, stem, left half
    comp = [(1, 2, 1), (2, 1, 3), (2, 3, 1), (0, 1, 0)]
    walk = _through_last_walk(comp, nodes, spans, junctions, None)
    assert walk[0][1] == 2, "keeps the walk's entry"
    assert walk[-1][2] == 0, "keeps the walk's exit"
    for (_s, _a, b), (_s2, a2, _b2) in zip(walk, walk[1:]):
        assert b == a2, "a walk is contiguous"
    legs = columns._trail_legs(walk, spans)
    sat = [lg for lg in legs if lg["sat"]]
    assert [lg["ci"] for lg in sat] == [1, 0], "the stem's satin, then the bar's"
    assert sorted((sat[1]["i0"], sat[1]["i1"])) == [0, 10], "the bar in one leg, end to end"


def test_walk_entered_at_a_branch_tip_sews_it_straight_in():
    # the E: column 0 the folded top arm -> stem -> bottom arm, split at its
    # junction (node 1); the middle arm, column 1, tip node 3. The postman's
    # walk enters at the arm's tip and ends at the junction (not a column end)
    nodes = [(3.0, 0.0), (0.0, 2.5), (3.0, 5.0), (3.0, 2.5)]
    spans = [_span(0, 0, 16, 0, 1), _span(0, 16, 31, 1, 2), _span(1, 0, 5, 1, 3)]
    junctions = [dict(ci=1, end=0, through=0, k=16)]
    comp = [(2, 3, 1), (0, 1, 0), (0, 0, 1), (1, 1, 2), (1, 2, 1)]
    walk = _through_last_walk(comp, nodes, spans, junctions, None)
    assert walk[0] == (2, 3, 1), "the arm sewn straight in from its tip, no run-out"
    for (_s, _a, b), (_s2, a2, _b2) in zip(walk, walk[1:]):
        assert b == a2
    assert walk[-1][2] in (0, 2), "a walk that ended at the junction ends at a column end"
    legs = columns._trail_legs(walk, spans)
    sat = [lg for lg in legs if lg["sat"]]
    assert [lg["ci"] for lg in sat] == [1, 0]
    assert sorted((sat[1]["i0"], sat[1]["i1"])) == [0, 31], "the folded column in one leg"


def test_walk_refuses_two_through_columns():
    # an H: the bar butts BOTH stems
    nodes = [(0, 0), (0, 2), (0, 4), (3, 0), (3, 2), (3, 4)]
    spans = [_span(0, 0, 5, 0, 1), _span(0, 5, 10, 1, 2), _span(1, 0, 5, 3, 4),
             _span(1, 5, 10, 4, 5), _span(2, 0, 7, 1, 4)]
    junctions = [dict(ci=2, end=0, through=0, k=5), dict(ci=2, end=-1, through=1, k=5)]
    comp = [(0, 0, 1), (4, 1, 4), (2, 4, 3), (2, 3, 4), (3, 4, 5), (1, 1, 2)]
    assert _through_last_walk(comp, nodes, spans, junctions, None) is None
