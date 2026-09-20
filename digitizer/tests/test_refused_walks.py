"""`tools/refused_walks.py` — the anatomy of a refused between-stroke walk,
and `cfg.satin_walk_cursor_reach_mm`, the one relaxation the anatomy named
(built OFF 2026-09-20, Kent's pick).

Between two strokes the linking pass asks `_graph_travel` for a needle-down
path over the unsewn spine web; no path means a lift, and that is a trim. The
census (838 walks over the two MARINE fixtures and the nine corpus logos)
split the 343 refusals five ways and found that only one is relaxable: 176
were the needle sitting past `trim_at` from any node, and 47 of those have a
path once it reaches the web. All 118 `target_unsnapped` refusals and 128 of
the 176 are different components of the web, where a trim is correct.

Pinned: the tool's two mirrored thresholds against the real function (the
0.8 mm target snap and the caller's length cap), every reason it can report
on a web built here, the flag's default OFF and its inertness there, and —
ON — that the walk both reaches further AND sews the leg it buys, since a
leg past `trim_at` would otherwise be trimmed, which is the trim the walk
was for.
"""
from __future__ import annotations

import math

import pytest

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_satin as s6
from tools import refused_walks as rw


def _web(gap_mm: float = 0.0):
    """Two straight spines along y=0: nodes at x = 0,10 and x = 20+gap, 30+gap.
    One edge each, so the two are separate components when gap > 0."""
    nodes = [(0.0, 0.0), (10.0, 0.0), (20.0 + gap_mm, 0.0), (30.0 + gap_mm, 0.0)]
    edges = [{"a": 0, "b": 1, "k": 0, "len": 10.0, "pts": [nodes[0], nodes[1]]},
             {"a": 2, "b": 3, "k": 1, "len": 10.0, "pts": [nodes[2], nodes[3]]}]
    adj = {0: [0], 1: [0], 2: [1], 3: [1]}
    return nodes, edges, adj


def _call(cur, target, sewn=(), **kw):
    nodes, edges, adj = kw.pop("web", None) or _web()
    trim = kw.pop("trim_at_mm", machine.TRIM_AT_MM)
    path = s6._graph_travel(cur, target, set(sewn), set(), nodes, edges, adj,
                            trim_at_mm=trim, **kw)
    row = rw.classify(cur, target, set(sewn), set(), nodes, edges, adj,
                      trim_at_mm=trim, snap_to_open=kw.get("snap_to_open", False),
                      path=path, orig=s6._graph_travel)
    return path, row


def test_the_mirrored_target_snap_is_the_real_function_s():
    """`rw.SNAP_MM` is `_graph_travel`'s own literal: a target just inside it
    walks, one just outside refuses, and the tool names that refusal."""
    assert rw.SNAP_MM == 0.8
    inside, _ = _call((0.0, 0.0), (10.0, rw.SNAP_MM - 0.1))
    assert inside is not None
    outside, row = _call((0.0, 0.0), (10.0, rw.SNAP_MM + 0.1))
    assert outside is None and row["reason"] == "target_unsnapped"


def test_the_mirrored_cap_is_the_caller_s_and_names_a_path_thrown_away():
    """The caller keeps a path only while `plen <= max(20, 4 x direct)`; the
    tool reports one past that as `too_long` rather than as a success."""
    assert (rw.CAP_FLOOR_MM, rw.CAP_FACTOR) == (20.0, 4.0)
    # Cursor and target 1 mm apart across the web's ends: the path is 10 mm,
    # the cap max(20, 4) = 20 -> kept.
    path, row = _call((0.0, 0.0), (10.0, 0.0))
    assert path is not None and row["reason"] == "ok" and row["path_mm"] == 10.0
    # A 30 mm web walked for a 0.6 mm move: 4 x 0.6 is under the floor, so the
    # cap is 20 and a 30 mm path is refused by the caller, not by the walk.
    nodes = [(0.0, 0.0), (15.0, 0.0), (30.0, 0.0), (0.6, 0.0)]
    edges = [{"a": 0, "b": 1, "k": 0, "len": 15.0, "pts": [nodes[0], nodes[1]]},
             {"a": 1, "b": 2, "k": 1, "len": 15.0, "pts": [nodes[1], nodes[2]]},
             {"a": 2, "b": 3, "k": 2, "len": 30.0, "pts": [nodes[2], nodes[3]]}]
    adj = {0: [0], 1: [0, 1], 2: [1, 2], 3: [2]}
    path, row = _call((0.0, 0.0), (0.6, 0.0), web=(nodes, edges, adj))
    assert path is not None and row["reason"] == "too_long"
    assert row["path_mm"] > row["cap_mm"]


def test_each_refusal_reason_is_reported_on_a_web_built_to_produce_it():
    # cursor_unsnapped: the needle sits past trim_at from every node.
    path, row = _call((0.0, machine.TRIM_AT_MM + 1.0), (10.0, 0.0))
    assert path is None and row["reason"] == "cursor_unsnapped"
    assert row["cursor_miss_mm"] > machine.TRIM_AT_MM
    # ...and the tool prices it: this one IS rescued by a wider reach, and
    # reports the leg the needle would sew onto the web.
    # The ladder's first rung above `trim_at` that reaches: 4.0 for a 4.0 mm miss.
    assert row["rescued_at_mm"] == 4.0 and row["rescue_within_cap"] is True
    assert row["rescue_leg_mm"] == pytest.approx(machine.TRIM_AT_MM + 1.0, abs=0.01)

    # disconnected: both ends snap, no edge joins the two components.
    path, row = _call((0.0, 0.0), (20.0, 0.0))
    assert path is None and row["reason"] == "disconnected"

    # blocked_by_sewn: the only route is an already-sewn stroke.
    path, row = _call((0.0, 0.0), (10.0, 0.0), sewn=(0,))
    assert path is None and row["reason"] == "blocked_by_sewn"
    assert row["free_path_mm"] == 10.0          # what it would have walked

    # ok, and trivial (cursor and target snap to one node: no travel, no trim).
    path, row = _call((0.0, 0.0), (10.0, 0.0))
    assert path is not None and row["reason"] == "ok"
    path, row = _call((0.0, 0.0), (0.2, 0.0))
    assert path == [] and row["reason"] == "trivial"


def test_the_flag_is_off_by_default_and_off_changes_nothing():
    assert PipelineConfig().satin_walk_cursor_reach_mm == 0.0
    cur, target = (0.0, machine.TRIM_AT_MM + 1.0), (10.0, 0.0)
    nodes, edges, adj = _web()
    assert s6._graph_travel(cur, target, set(), set(), nodes, edges, adj,
                            trim_at_mm=machine.TRIM_AT_MM) is None
    assert s6._graph_travel(cur, target, set(), set(), nodes, edges, adj,
                            trim_at_mm=machine.TRIM_AT_MM, cursor_reach_mm=0.0) is None
    # A reach no wider than trim_at is the same rule too.
    assert s6._graph_travel(cur, target, set(), set(), nodes, edges, adj,
                            trim_at_mm=machine.TRIM_AT_MM,
                            cursor_reach_mm=machine.TRIM_AT_MM) is None


def test_on_the_walk_reaches_further_and_the_path_still_starts_on_the_web():
    """The reach is the walk's half of the flag. The caller's half — sewing
    the leg — is `satin_shape`'s, pinned in the source below, because a leg
    past `trim_at` that the walk does not carry is trimmed by the linking
    loop, which is the trim the walk was for."""
    cur, target = (0.0, machine.TRIM_AT_MM + 1.0), (10.0, 0.0)
    nodes, edges, adj = _web()
    path = s6._graph_travel(cur, target, set(), set(), nodes, edges, adj,
                            trim_at_mm=machine.TRIM_AT_MM, cursor_reach_mm=5.0)
    assert path is not None and len(path) >= 2
    assert math.dist(path[0], (0.0, 0.0)) < 1e-9          # starts ON the web
    assert math.dist(cur, path[0]) > machine.TRIM_AT_MM   # ...leaving the leg

    src = (rw.ROOT / "digitizer_core" / "stage6_satin.py").read_text(encoding="utf-8")
    i = src.find("cursor_reach_mm=walk_cursor_reach")
    assert i > 0, "the travel block no longer passes the reach"
    block = src[i:i + 1200]
    assert "path = [tuple(cursor)] + list(path)" in block
    assert "walk_cursor_reach > trim_at_mm" in block and "math.dist(cursor, path[0]) > trim_at_mm" in block


def test_the_tool_s_cases_are_the_census_s_fixtures_and_the_corpus():
    names = {n for n, *_ in rw.FIXTURES}
    assert {"marine127", "marine80"} <= names
    assert set(rw.REASONS) == {"ok", "trivial", "too_long", "cursor_unsnapped",
                               "target_unsnapped", "blocked_by_sewn", "disconnected"}
