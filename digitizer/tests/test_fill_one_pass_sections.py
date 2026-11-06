"""`cfg.fill_one_pass_sections` (built OFF 2026-11-06, defect 6): a fill's
sections in one pass, the way the professional sews a field.

Re-measured on the flipped main (`docs/fill-one-pass-sections-2026-11-06.md`):
the five committed Becker pairs cut between two sections of ONE fill 9 times,
the pro 0. Every one is at a fork: `fill_seam_order`'s single progression sews
the body of a field first, then one lobe to its bottom, and the other lobe is
then walled off behind finished fill, so the hop to it is cut
(`fill_bridge_cut_exposed`). The pro runs through the lobe still to come.

ON, seam order's progression is re-planned with `_order_for_seams`' `reach`:
among the sections free to go, one the needle reaches hidden (over unsewn
ground, or under rows still to come) goes before the nearest, and the fill
phase sews those hidden routes. The lay is read first and the re-plan is kept
only if it removes a hop past `machine.LINK_MAX_GAP_MM` (one stage 7's
`_bury_trims_under_later` could never sew down, the kind that reaches the
DST), cuts no more in all and lays no more thread on finished fill than seam
order's own order (`stage6_fill._one_pass_sections`). A shape it does not
re-plan sews exactly as without the switch.

The fixture is a shapely polygon on purpose (a traced raster's outline differs
by platform): a body with two lobes below it, Becker's field in miniature.
"""
from __future__ import annotations

import hashlib
import json
import math

import pytest
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, fill_section_travel, stage6_fill, stitches
from digitizer_core.stage6_fill import (_ONE_PASS, _footprint, _order_for_seams, _section_rows,
                                        _seam_side, _uv, cut_exposed_scope, one_pass_scope,
                                        seam_order_scope, seam_priced_scope, stitch_shape)
from tests.test_fill_seam_order import _rows_of

ROW = 0.4
TRIM_AT = 3.0
# A body with two lobes hanging from it, a notch of bare cloth between them. The
# lobes are long enough that the hop from one's bottom to the other's top is past
# `machine.LINK_MAX_GAP_MM`: a cut stage 7 could never bury, the kind the Becker
# fields carry to the DST.
FORK = unary_union([box(0, 0, 40, 10), box(0, 10, 14, 54), box(26, 10, 40, 54)])


def _sew(on: bool, shape=FORK, **kw):
    """The plan's ambient flags as main runs them (seam order, priced, exposed
    bridges cut), the switch `on` or off."""
    args = dict(angle_deg=0.0, row_mm=ROW, stitch_mm=3.0, underlay_style="none",
                trim_at_mm=TRIM_AT, start_near=(0.0, 0.0), under_cover=True, cut_bridges=True)
    args.update(kw)
    with seam_order_scope(True), seam_priced_scope(True), cut_exposed_scope(True), one_pass_scope(on):
        runs, _report = stitch_shape(shape, "F", **args)
    return runs


def _md5(runs) -> str:
    rows = [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
            for r in runs for x, y in r.points]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _cuts(runs) -> int:
    return sum(1 for r in runs if r.trim)


def _seam_faults(runs, angle=0.0) -> tuple[int, int]:
    """(ridges, flips) over the fill sections, `tests/test_fill_seam_order.py`'s reader."""
    fills = [r for r in runs if r.kind == stitches.FILL and len(r.points) > 4]
    rows = [_section_rows(r.points, angle) for r in fills]
    dirs = [1 if _uv(r.points[-1], angle)[1] > _uv(r.points[0], angle)[1] else -1 for r in fills]
    ridge = flip = 0
    for a in range(len(fills)):
        for b in range(a + 1, len(fills)):
            side = _seam_side(rows[a], rows[b], ROW)
            if side == 0:
                continue
            if dirs[a] != dirs[b]:
                flip += 1
            elif side != dirs[a]:
                ridge += 1
    return ridge, flip


# --------------------------------------------------------------------- OFF --

def test_the_switch_is_off_by_default():
    assert PipelineConfig().fill_one_pass_sections is False
    assert not _ONE_PASS.get()


def test_plan_stitches_reads_the_flag(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: seen.append(_ONE_PASS.get()))
    pipeline.plan_stitches(None, PipelineConfig())
    pipeline.plan_stitches(None, PipelineConfig(fill_one_pass_sections=True))
    assert seen == [False, True]
    assert not _ONE_PASS.get()


def test_off_never_reaches_the_new_code(monkeypatch):
    """Off, neither the re-plan nor a hidden route is ever asked for: the
    engine as it was, `fill_section_travel` included."""
    def boom(*_a, **_k):
        raise AssertionError("fill_one_pass_sections reached with the switch off")
    monkeypatch.setattr(stage6_fill, "_one_pass_sections", boom)
    monkeypatch.setattr(fill_section_travel, "bridge", boom)
    _sew(False)
    with one_pass_scope(False):
        assert not _ONE_PASS.get()


def test_off_is_the_engine_as_it_was():
    off = _md5(_sew(False))
    with one_pass_scope(True):
        pass
    assert _md5(_sew(False)) == off
    assert _md5(_sew(False, under_cover=False, cut_bridges=False)) == \
        _md5(_sew(True, under_cover=False, cut_bridges=False)), "without cover there is nothing to plan"


# ---------------------------------------------------------------------- ON --

def test_the_fork_cuts_off_and_not_on():
    """Seam order's progression walls the second lobe in and cuts to it; the
    switch sews the field in one pass, the same rows, no ridge and no flip."""
    off, on = _sew(False), _sew(True)
    assert _cuts(off) >= 1, "the fixture must cut at its fork with the switch off"
    assert _cuts(on) < _cuts(off)
    assert _seam_faults(on) == (0, 0)
    assert sorted(p for r in on if r.kind == stitches.FILL for p in r.points) == \
        sorted(p for r in off if r.kind == stitches.FILL for p in r.points), "the same rows, reordered"


def test_the_new_travel_lies_under_rows_still_to_come():
    """ROADMAP gate 3's letter: every travel run ON adds is covered by fill
    sewn AFTER it, to within the exposure tolerance at its two ends."""
    off, on = _sew(False), _sew(True)
    old = {tuple(map(tuple, r.points)) for r in off if r.kind == stitches.TRAVEL}
    new = [k for k, r in enumerate(on) if r.kind == stitches.TRAVEL
           and tuple(map(tuple, r.points)) not in old]
    assert new, "the switch sews at least one hidden route on the fork"
    for k in new:
        leg = [on[k - 1].points[-1], *on[k].points, on[k + 1].points[0]]
        later = unary_union([_footprint(r.points, ROW) for r in on[k + 1:]
                             if r.kind == stitches.FILL and len(r.points) > 1])
        bare = LineString(leg).difference(later).length
        assert bare <= 2 * stage6_fill._EXPOSED_TOLERANCE_MM, (k, bare)


def test_reach_picks_a_reachable_free_section_over_the_nearest():
    """Two lobes free at once below a body (bottom-up progression): nearest
    first takes the near lobe; `reach` that only reaches the far one takes it."""
    near, far = _rows_of(10.0, 20.0, 0.0, 10.0), _rows_of(10.0, 20.0, 30.0, 40.0)
    body = _rows_of(0.0, 10.0, 0.0, 40.0)
    entry = (0.0, 20.0)
    plain = _order_for_seams([body, near, far], 0.0, entry, ROW, lambda _o: 0.0)
    assert plain[0][0][0] < 20.0, "nearest-first starts in the near lobe"
    asked = []

    def reach(cur, head, sewn, todo):
        asked.append((cur, head, sewn is None, len(todo)))
        return head[0] >= 30.0
    out = _order_for_seams([body, near, far], 0.0, entry, ROW, lambda _o: 0.0, reach=reach)
    lobes = [p[0][0] >= 30.0 for p in out if min(y for _x, y in p) >= 10.0 - 1e-9]
    assert lobes == [True, False], "the reachable lobe goes before the nearer one"
    # both progressions were planned with it: in the one that starts at the
    # lobes, it was asked before anything was sewn, with every path to come
    assert any(sewn_none and n == 3 for _c, _h, sewn_none, n in asked)
    # and the seam rule still holds: no section starts before its upstream ones
    ys = [_uv(p[0], 0.0)[1] for p in out]
    assert ys == sorted(ys) or ys == sorted(ys, reverse=True), "one progression across the rows"


@pytest.mark.parametrize("worse", ["more_cuts", "more_exposure"])
def test_the_gate_still_holds(monkeypatch, worse):
    """A re-plan that cuts more, or lays more thread on finished fill, is
    refused however cheap it prices: ON then sews seam order's own order."""
    real = stage6_fill._order_cost_walk
    calls = {"n": 0}

    def walk(order, *a, **k):
        steps = list(real(order, *a, **k))
        if k.get("hidden_row_mm") is not None:     # the switch's own pricing
            calls["n"] += 1
            if calls["n"] > 1:                      # a re-plan; the first is the incoming order
                cost = steps[-1]
                steps[-1] = {"more_cuts": (cost[0] + 1, 0.0, 0.0),
                             "more_exposure": (max(0, cost[0] - 1), 0.0, cost[2] + 1.0)}[worse]
        yield from steps
    monkeypatch.setattr(stage6_fill, "_order_cost_walk", walk)
    assert _md5(_sew(True)) == _md5(_sew(False))
    assert calls["n"] >= 2, "the re-plan was priced"


def test_the_fork_hop_is_a_long_one():
    """The fixture's cut is past `LINK_MAX_GAP_MM`, so stage 7 could never bury
    it: the switch acts only on cuts of that kind."""
    from digitizer_core import machine
    off = _sew(False)
    runs = [r for r in off if r.points]
    gaps = [math.dist(runs[i - 1].points[-1], r.points[0]) for i, r in enumerate(runs) if i and r.trim]
    assert gaps and max(gaps) > machine.LINK_MAX_GAP_MM


def test_a_re_plan_that_only_moves_short_cuts_is_refused(monkeypatch):
    """Stage 7 buries a cut hop under later thread, never one past
    `LINK_MAX_GAP_MM`; a re-plan that cuts less but leaves as many long hops is
    refused (Becker's hat: 9 -> 7 cuts in stage 6, 1 -> 2 in the DST; three
    jobs moved for no cut)."""
    from digitizer_core import machine
    off = _md5(_sew(False))
    monkeypatch.setattr(machine, "LINK_MAX_GAP_MM", 1000.0)   # no hop here is a long one
    assert _md5(_sew(True)) == off
    monkeypatch.setattr(machine, "LINK_MAX_GAP_MM", 1.0)      # every cut hop here is a long one
    # the fork's re-plan cuts 1 -> 0 and has no long hop left: taken
    assert _md5(_sew(True)) != off
    real = stage6_fill._order_cost_walk
    calls = {"n": 0}

    def walk(order, *a, **k):
        steps = list(real(order, *a, **k))
        if k.get("hidden_row_mm") is not None:
            calls["n"] += 1
            if calls["n"] > 1 and len(steps) >= 3:
                # the same final price with one cut fewer, but that cut taken at
                # a hop of the order's own: a long one under the 1 mm cap
                steps[-2] = (steps[-2][0] + 1, steps[-2][1], steps[-2][2])
                steps[-1] = (steps[-1][0] + 1, steps[-1][1], steps[-1][2])
        yield from steps
    monkeypatch.setattr(stage6_fill, "_order_cost_walk", walk)
    assert _md5(_sew(True)) == off
