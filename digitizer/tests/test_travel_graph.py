"""Stage 6 travel web — _build_travel_graph and _graph_travel.

First unit tests for the needle-down travel walk (before M2 there were
none — the walk was only ever exercised through whole-shape goldens).
The M2 lever these pin: _graph_travel's cursor-side snap. The needle
sits wherever the previous run ended — often a cap-extended point a
millimetre or two off the spine web — and a strict 0.8mm snap killed
the whole walk there, turning a walkable move into a trim. The fix
retries the CURSOR side against the nearest node within the linking
loop's existing trim_at_mm bound (the same bound that decides sew vs
jump at :2414). Target side stays strict: the target is a stroke start
the graph was built from, so missing it means the web genuinely does
not reach there.

These tests pin the BEHAVIOUR, not the corpus count: a previously
failing cursor snap now walks; a genuinely far cursor still returns
None (and therefore still trims).
"""
from __future__ import annotations

import math

from digitizer_core.stage6_satin import Stroke, _build_travel_graph, _graph_travel

# The linking loop's default bound in the real pipeline (PipelineConfig
# trim_at_mm=3.0). Passed explicitly here because _graph_travel takes it
# from its caller — the VALUE is the caller's business, not this module's.
TRIM_AT_MM = 3.0


def _stroke(*pts: tuple[float, float]) -> Stroke:
    return Stroke(spine=list(pts), free_start=True, free_end=True, closed=False)


def _web():
    """Two strokes meeting at (10, 0): an L of spine web.

    Nodes end up at (0,0), (10,0), (10,10); interior spine points are
    edge geometry, not snap candidates.
    """
    strokes = [
        _stroke((0.0, 0.0), (5.0, 0.0), (10.0, 0.0)),
        _stroke((10.0, 0.0), (10.0, 5.0), (10.0, 10.0)),
    ]
    return _build_travel_graph(strokes)


# ---------------------------------------------------------------- graph build

def test_build_travel_graph_merges_shared_endpoint():
    """Endpoints within 0.5mm share a node — the L has 3 nodes, 2 edges."""
    nodes, edges, adj = _web()
    assert len(nodes) == 3
    assert len(edges) == 2
    shared = [i for i, q in enumerate(nodes) if math.dist(q, (10.0, 0.0)) <= 0.5]
    assert len(shared) == 1
    # The shared node carries both edges — the walk can turn the corner.
    assert len(adj[shared[0]]) == 2


# ------------------------------------------------------------ cursor-side snap

def test_travel_walks_when_cursor_snaps_within_baseline():
    """Regression pin: a cursor inside the original 0.8mm snap still walks."""
    nodes, edges, adj = _web()
    path = _graph_travel((0.5, 0.0), (10.0, 10.0), set(), set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is not None and len(path) >= 2
    assert math.dist(path[0], (0.0, 0.0)) <= 0.5
    assert math.dist(path[-1], (10.0, 10.0)) <= 0.5


def test_cursor_snap_failure_retries_within_trim_bound():
    """M2: cursor 1.5mm off the web (0.8 < d <= trim_at_mm) now walks.

    Before the fix this returned None and the linking loop trimmed a
    move the web could carry needle-down.
    """
    nodes, edges, adj = _web()
    path = _graph_travel((0.0, 1.5), (10.0, 10.0), set(), set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is not None and len(path) >= 2
    # The walk starts ON the web, at the retried node — the short leg
    # from the true cursor onto it is the linking loop's job, and it is
    # within the same bound that loop sews needle-down.
    assert math.dist(path[0], (0.0, 0.0)) <= 1e-9
    assert math.dist(path[-1], (10.0, 10.0)) <= 0.5


def test_cursor_beyond_trim_bound_still_trims():
    """A genuinely far cursor (> trim_at_mm from every node) still
    returns None — the caller falls through to the trim, as before."""
    nodes, edges, adj = _web()
    assert min(math.dist((0.0, 5.0), q) for q in nodes) > TRIM_AT_MM
    path = _graph_travel((0.0, 5.0), (10.0, 10.0), set(), set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is None


def test_target_side_snap_stays_strict():
    """The retry is cursor-side ONLY: a target 1.5mm off the web still
    fails even though it is inside the trim bound."""
    nodes, edges, adj = _web()
    path = _graph_travel((0.0, 0.0), (10.0, 11.5), set(), set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is None


def test_retry_prefers_nearest_node():
    """The retry snaps to the NEAREST node, not the first within bound."""
    nodes, edges, adj = _web()
    # (9.0, 1.0) is 1.41mm from (10,0) and much farther from the others.
    path = _graph_travel((9.0, 1.0), (0.0, 0.0), set(), set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is not None and len(path) >= 2
    assert math.dist(path[0], (10.0, 0.0)) <= 1e-9
    assert math.dist(path[-1], (0.0, 0.0)) <= 0.5


def test_retry_still_respects_sewn_edges():
    """A retried snap gains no new rights: sewn strokes stay forbidden,
    so a cursor rescued by the retry with no unsewn route still trims."""
    nodes, edges, adj = _web()
    path = _graph_travel((0.0, 1.5), (10.0, 10.0), {0}, set(),
                         nodes, edges, adj, trim_at_mm=TRIM_AT_MM)
    assert path is None
