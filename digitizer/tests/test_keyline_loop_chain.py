"""`cfg.keyline_loop_chain` (built OFF 2026-10-26): a keyline / outline band's
loops chained as the professional chains them.

The pro's MFab white is a few long satin chains: each loop is walked into from
the last, and 96-100% of every walk lies under white he sews after it. Ours
lifted loop to loop (`docs/keyline-loop-chain-2026-10-26.md`). Chained, each
loop starts (and ends) where it comes nearest the next, and the walk into a
loop runs under the loops still to sew (`monoline.bury_hops`). This pins: OFF
is the loops as they were; ON on two letters 2 mm apart the lift becomes a
walk, wholly under the second loop's satin; the band's first loop is entered
where it was; where no buried walk exists ON cuts what OFF cuts and lays no
exposed walk; and the scope sets nothing when off.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import stitches
from digitizer_core.stage6_border import _LOOP_CHAIN, keyline_runs, loop_chain_scope

B1, B2 = box(10, 10, 20, 30), box(22, 10, 32, 30)          # two letters, 2 mm apart
BAND = unary_union([B1.buffer(2.0, join_style=2), B2.buffer(2.0, join_style=2)]).difference(
    unary_union([B1, B2]))                                     # the keyline round both
HOLES = [(B1, 2.0), (B2, 2.0)]


def _sew(chain: bool):
    with loop_chain_scope(chain):
        return keyline_runs(BAND, "Sband", reach=BAND, entry=(0.0, 0.0), trim_at_mm=3.0,
                            underlay=True, holes=HOLES)


def _sig(runs):
    return [(r.kind, r.jump, r.trim, [(round(x, 4), round(y, 4)) for x, y in r.points]) for r in runs]


def test_the_scope_sets_nothing_when_off():
    with loop_chain_scope(False):
        assert _LOOP_CHAIN.get() is False
    with loop_chain_scope(True):
        assert _LOOP_CHAIN.get() is True
    assert _LOOP_CHAIN.get() is False


def test_off_the_loops_lift_between_letters():
    runs, report = _sew(False)
    assert report["loops"] == 2
    lifts = [r for r in runs[1:] if r.jump]
    assert lifts
    assert report["jumps"] == 2          # the entry's lift, and the lift between the letters


def test_on_the_lift_becomes_a_walk_under_the_next_loop():
    runs, report = _sew(True)
    assert report["loops"] == 2
    assert not any(r.jump for r in runs[1:])
    assert report["jumps"] == 1          # only the entry's own lift, as before
    walks = [i for i, r in enumerate(runs) if r.kind == stitches.TRAVEL]
    assert walks
    # every walk is covered by satin sewn after it (the second loop), within a
    # loop's width of its letter: the walk lies in the band B2's loop sews
    for i in walks:
        later = unary_union([LineString(r.points).buffer(0.3) for r in runs[i + 1:]
                             if r.kind == stitches.SATIN and len(r.points) > 1])
        walk = LineString(runs[i].points)
        outside = walk.difference(later).length
        assert outside <= 1.0 + 1e-6, outside


def test_each_loop_starts_where_it_comes_nearest_the_next():
    runs, _ = _sew(True)
    first_satin = next(r for r in runs if r.kind == stitches.SATIN)
    start = Point(first_satin.points[0])
    # the first loop (round B1, nearest the entry) starts on B1's side facing B2
    assert start.x > 19.0, start


def test_the_first_loop_is_entered_where_it_was():
    off, _ = _sew(False)
    on, _ = _sew(True)
    # OFF lifts into the first loop's start; ON lifts to that same point, then
    # walks round under that loop's own satin to its chained start
    assert on[0].kind == stitches.TRAVEL and on[0].jump
    was = next(r for r in off if r.kind == stitches.SATIN)
    assert math.dist(on[0].points[0], was.points[0]) < 1e-6
    first_satin = next(r for r in on if r.kind == stitches.SATIN)
    assert math.dist(on[0].points[-1], first_satin.points[0]) < 1e-6
    assert math.dist(was.points[0], first_satin.points[0]) > 5.0


def test_where_no_buried_walk_exists_it_cuts_what_off_cuts():
    # two letters 20 mm apart in a wide band: no walk from one loop to the
    # other lies under satin still to come, so ON lifts there as OFF does --
    # the chain never lays a long exposed walk
    far = box(40, 10, 50, 30)
    band = box(0, 0, 60, 40).difference(unary_union([B1, far]))
    holes = [(B1, 2.0), (far, 2.0)]
    sewn = []
    for chain in (False, True):
        with loop_chain_scope(chain):
            sewn.append(keyline_runs(band, "Sband", reach=band, entry=(2.0, 2.0), trim_at_mm=3.0,
                                     underlay=True, holes=holes))
    (off, off_rep), (on, on_rep) = sewn
    assert on_rep["jumps"] == off_rep["jumps"]
    assert sum(r.trim for r in on) == sum(r.trim for r in off)
    satins = [i for i, r in enumerate(on) if r.kind == stitches.SATIN]
    assert on[satins[1] - 1].jump               # the lift between the letters stays
    for i, r in enumerate(on):
        if r.kind == stitches.TRAVEL and i > 0 and on[i - 1].kind == stitches.TRAVEL:
            later = unary_union([LineString(q.points).buffer(0.3) for q in on[i + 1:]
                                 if q.kind == stitches.SATIN and len(q.points) > 1])
            assert LineString(r.points).difference(later).length <= 1.0 + 1e-6


def test_a_plan_sets_the_flag_from_its_config(monkeypatch):
    from digitizer_core import PipelineConfig, pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda _r, _c: seen.append(_LOOP_CHAIN.get()))
    pipeline.plan_stitches(object(), PipelineConfig(keyline_loop_chain=False))
    pipeline.plan_stitches(object(), PipelineConfig())   # ON by default (Kent 2026-10-27, "Every job (Recommended)")
    assert seen == [False, True]
    assert _LOOP_CHAIN.get() is False


def test_off_never_reaches_the_new_code(monkeypatch):
    from digitizer_core import stage6_border as sb

    def boom(*_a, **_k):
        raise AssertionError("keyline_loop_chain code reached with the flag off")

    monkeypatch.setattr(sb, "_bury_walks", boom)
    monkeypatch.setattr(sb, "_walk_into", boom)
    runs, report = _sew(False)
    assert report["loops"] == 2
