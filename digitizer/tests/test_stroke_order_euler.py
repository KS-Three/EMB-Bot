"""`cfg.satin_stroke_order = "euler"` — a satin shape's strokes sewn along ONE
walk of its travel web (`stage6_satin._euler_stroke_order`, lettering
construction plan step 2, 2026-09-19).

The shipped order (`_order_strokes`, "nearest") sews whichever stroke's
preferred entry is closest to the needle next, and travels between strokes
along the UNSEWN web (`_graph_travel`) or trims when no unsewn path is left;
on a letter of several strokes that path is gone after the first few, so the
hop inside the letter is a trim. The Euler order is the font engine's
`routeGlyph` construction: Chinese-postman duplication where a dead end
forces it, a Hierholzer trail, each stroke sewn at its LAST visit so every
travel leg lies under a column sewn later. A stroke is walked THROUGH — the
column enters where the walk arrives and leaves by the other end, its
underlay chained backwards from that entry — and the cursor may snap to the
nearest node it can still leave from (`snap_to_open`).

Contracts pinned: OFF ("nearest", the default) is byte-identical to the
shipped engine; on synthetic webs the walk visits every stroke once, an
open path needs no duplicate, a T's dead end is walked twice, and between
consecutive strokes an unsewn path always exists; on the plan's own fixture
(MARINE in `manga_impact` at 80 mm, built at test time) the trims fall, the
stitches do not rise, nothing goes uncovered, and travel appears.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from digitizer_core import stitches
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import run_preflight

from tests.test_house_from_line import _word_raster


def _stroke(*pts, free_start=True, free_end=True):
    return s6.Stroke(spine=[tuple(map(float, p)) for p in pts],
                     free_start=free_start, free_end=free_end, closed=False)


def _walk(strokes, start=(0.0, 0.0)):
    nodes, edges, adj = s6._build_travel_graph(strokes)
    order, entry = s6._euler_stroke_order(nodes, edges, adj, len(strokes), start)
    return nodes, edges, adj, order, entry


def _exit_node(nodes, strokes, k, entry):
    sp = strokes[k].spine
    p = sp[-1] if entry.get(k, True) else sp[0]
    return min(range(len(nodes)), key=lambda i: math.dist(p, nodes[i]))


def _entry_node(nodes, strokes, k, entry):
    sp = strokes[k].spine
    p = sp[0] if entry.get(k, True) else sp[-1]
    return min(range(len(nodes)), key=lambda i: math.dist(p, nodes[i]))


def _unsewn_path(nodes, edges, adj, a, b, sewn, allow):
    """BFS over edges of strokes not in `sewn` (or in `allow`)."""
    seen = {a}
    frontier = [a]
    while frontier:
        u = frontier.pop()
        if u == b:
            return True
        for ei in adj.get(u, []):
            e = edges[ei]
            if e["k"] in sewn and e["k"] not in allow:
                continue
            v = e["b"] if e["a"] == u else e["a"]
            if v not in seen:
                seen.add(v)
                frontier.append(v)
    return a == b


def _walk_covers_every_hop(strokes):
    nodes, edges, adj, order, entry = _walk(strokes)
    assert sorted(order) == list(range(len(strokes)))
    sewn: set[int] = set()
    for prev, nxt in zip(order, order[1:]):
        sewn.add(prev)
        assert _unsewn_path(nodes, edges, adj, _exit_node(nodes, strokes, prev, entry),
                            _entry_node(nodes, strokes, nxt, entry), sewn, {nxt}), (order, prev, nxt)
    return order, entry


def test_the_default_is_the_shipped_order():
    assert PipelineConfig().satin_stroke_order == "nearest"


def test_an_open_path_of_strokes_is_one_walk_with_no_duplicate():
    # three strokes end to end: a -- b -- c -- d
    strokes = [_stroke((0, 0), (10, 0)), _stroke((10, 0), (20, 0)), _stroke((20, 0), (30, 0))]
    order, entry = _walk_covers_every_hop(strokes)
    assert order == [0, 1, 2]
    assert entry == {0: True, 1: True, 2: True}


def test_a_t_walks_its_dead_end_twice_and_sews_the_bar_last():
    # bar (0,0)-(20,0) with a stem from its middle: the stem is a dead end,
    # so it is walked down (travel) and sewn back up, then the bar sews.
    bar = _stroke((0, 0), (10, 0), (20, 0))
    stem = _stroke((10, 0), (10, 10))
    order, entry = _walk_covers_every_hop([bar, stem])
    assert order[-1] == 0                                      # the bar last, over the stem's leg
    assert order[0] == 1


def test_an_e_is_one_walk_whatever_its_stem_sews_when():
    """Four odd nodes (three arm tips and the middle junction): two get paired
    by duplication, the trail runs tip to tip, and the stem may sew in the
    middle of it -- the contract is that every hop has an unsewn path, not
    which stroke comes last."""
    stem = _stroke((0, 0), (0, 5), (0, 10))
    arms = [_stroke((0, 0), (8, 0)), _stroke((0, 5), (6, 5)), _stroke((0, 10), (8, 10))]
    _walk_covers_every_hop([stem, *arms])


def test_two_islands_are_two_walks():
    a = [_stroke((0, 0), (10, 0)), _stroke((10, 0), (10, 10))]
    b = [_stroke((50, 0), (60, 0)), _stroke((60, 0), (60, 10))]
    nodes, edges, adj, order, entry = _walk([*a, *b])
    assert sorted(order) == [0, 1, 2, 3]
    assert set(order[:2]) == {0, 1} and set(order[2:]) == {2, 3}     # the nearer island first


def test_a_stub_loop_does_not_decide_a_strokes_entry():
    # a cut that lands one sample from a spine's end leaves a 0.2 mm stub
    # whose ends merge into one node -- a self-loop the walk must ignore
    bar = _stroke((0, 0), (0.2, 0), (10, 0), (20, 0))
    stem = _stroke((0.2, 0), (0.2, 10))
    nodes, edges, adj = s6._build_travel_graph([bar, stem])
    assert any(e["a"] == e["b"] for e in edges)
    _walk_covers_every_hop([bar, stem])


# --- through the pipeline ---------------------------------------------------

@pytest.fixture(scope="module")
def marine(tmp_path_factory) -> Path:
    p = tmp_path_factory.mktemp("word") / "marine80.png"
    cv2.imwrite(str(p), _word_raster("MARINE", 80.2))
    return p


def _plan(art: Path, **kw):
    cfg = PipelineConfig(target_width_mm=80.2, garment_id="left_chest", max_colors=6, **kw)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return cfg, result, plan


def _counts(plan):
    trims = travel = 0
    for _b, run in plan.iter_runs():
        trims += 1 if getattr(run, "trim", False) else 0
        travel += 1 if run.kind == stitches.TRAVEL else 0
    return plan.stats.stitch_count, trims, travel


@pytest.fixture(scope="module")
def nearest(marine):
    return _plan(marine)


@pytest.fixture(scope="module")
def euler(marine):
    return _plan(marine, satin_stroke_order="euler")


def test_nearest_explicitly_is_the_default(marine, nearest):
    _cfg, _r, explicit = _plan(marine, satin_stroke_order="nearest")
    a = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in nearest[2].iter_runs()]
    b = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in explicit.iter_runs()]
    assert a == b


def test_the_walk_trims_less_and_sews_no_more_on_the_fixture(nearest, euler):
    st_n, trims_n, travel_n = _counts(nearest[2])
    st_e, trims_e, travel_e = _counts(euler[2])
    assert trims_e <= trims_n - 10, (trims_n, trims_e)                      # measured 45 -> 27
    assert st_e <= st_n, (st_n, st_e)                                       # 2,564 -> 2,482
    assert travel_e > travel_n                                              # 3 -> 17 legs


def test_the_walk_leaves_nothing_uncovered(euler, marine):
    cfg, result, plan = euler
    pf = run_preflight(result, plan, cfg, image=str(marine))
    assert pf["metrics"].get("uncovered_total_mm2", 0.0) == 0.0
    assert "THREAD_ON_BARE_FABRIC" not in {w["code"] for w in pf.get("warnings", [])}
