"""`stage6_satin._cluster_junctions`: branch nodes a short skeleton edge
apart are one junction (quality review 2026-09-08, item 5; the PLUS at 1.25x
in `test_stroke_classify.py` was two 3-way nodes a pixel apart, 2026-09-09).
"""
from __future__ import annotations

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import machine
from digitizer_core import stage6_satin as s6

PLUS = Polygon([(9, 0), (12, 0), (12, 9), (21, 9), (21, 12), (12, 12),
                (12, 21), (9, 21), (9, 12), (0, 12), (0, 9), (9, 9)])


def _edge(pts, free_start, free_end):
    return {"pts": list(pts), "free_start": free_start, "free_end": free_end, "closed": False}


def test_a_split_crossing_becomes_one_four_way_node():
    # arms up and right meet at A=(9,4), arms left and down meet at B=(7,6),
    # A and B joined by the pixel (8,5): the crossing exactly as the raster
    # rendered the big PLUS
    A, B = (9, 4), (7, 6)
    edges = [
        _edge([(9, 0), (9, 1), (9, 2), (9, 3), A], True, False),        # up
        _edge([A, (10, 5), (11, 5), (12, 5), (13, 5)], False, True),    # right
        _edge([A, (8, 5), B], False, False),                             # the stub
        _edge([B, (6, 6), (5, 6), (4, 6), (3, 6)], False, True),        # left
        _edge([B, (8, 7), (8, 8), (8, 9), (8, 10)], False, True),       # down
    ]
    out = s6._cluster_junctions(edges, max_len_px=3.0, dt_mm=lambda p: 5.0 if p == A else 4.0)
    assert len(out) == 4, "the stub is gone, the four arms stay"
    nodes = {e["pts"][0] for e in out if not e["free_start"]} | \
            {e["pts"][-1] for e in out if not e["free_end"]}
    assert nodes == {A}, f"every arm now meets at the deeper node: {nodes}"
    left = next(e for e in out if e["pts"][-1] == (3, 6))
    assert left["pts"][:3] == [A, (8, 5), B], "re-rooted by way of the stub's own pixels"
    assert left["free_start"] is False and left["free_end"] is True


def test_a_long_edge_between_two_nodes_is_a_bar_and_stays():
    A, B = (0, 5), (12, 5)
    bar = _edge([A] + [(x, 5) for x in range(1, 12)] + [B], False, False)
    edges = [
        _edge([(0, 0), (0, 1), (0, 2), (0, 3), (0, 4), A], True, False),
        _edge([A, (0, 6), (0, 7), (0, 8), (0, 9), (0, 10)], False, True),
        bar,
        _edge([(12, 0), (12, 1), (12, 2), (12, 3), (12, 4), B], True, False),
        _edge([B, (12, 6), (12, 7), (12, 8), (12, 9), (12, 10)], False, True),
    ]
    out = s6._cluster_junctions(edges, max_len_px=3.0)
    assert out is edges, "nothing to contract: the very same list comes back"


def test_a_chain_of_three_nodes_collapses_onto_the_deepest():
    A, B, C = (5, 5), (7, 5), (9, 5)
    edges = [
        _edge([(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), A], True, False),
        _edge([A, (5, 6), (5, 7), (5, 8), (5, 9), (5, 10)], False, True),
        _edge([A, (6, 5), B], False, False),
        _edge([B, (7, 6), (7, 7), (7, 8), (7, 9), (7, 10)], False, True),
        _edge([B, (8, 5), C], False, False),
        _edge([C, (10, 5), (11, 5), (12, 5), (13, 5), (14, 5)], False, True),
        _edge([(9, 0), (9, 1), (9, 2), (9, 3), (9, 4), C], True, False),
    ]
    out = s6._cluster_junctions(edges, max_len_px=3.0, dt_mm=lambda p: {A: 3.0, B: 4.0, C: 3.5}[p] if p in (A, B, C) else 1.0)
    assert len(out) == 5
    ends = [e["pts"][0] for e in out if not e["free_start"]] + [e["pts"][-1] for e in out if not e["free_end"]]
    assert set(ends) == {B} and len(ends) == 5, "five arms, all at B"
    right = next(e for e in out if e["pts"][-1] == (14, 5))
    assert right["pts"][:3] == [B, (8, 5), C]


def test_a_loop_inside_a_junction_goes_and_the_tip_becomes_a_cap():
    # A stem ends in a tiny skeleton loop: node A, a 2-px stub to B, two
    # short paths back from B to A, and a self-loop at B — the emblem
    # bracket's tab tip. Every loop edge goes; the stem is left holding its
    # end at the deeper node with nothing else there.
    A, B = (5, 10), (5, 12)
    edges = [
        _edge([(5, 0), (5, 1), (5, 2), (5, 3), (5, 4), (5, 5), (5, 6), (5, 7), (5, 8), (5, 9), A], True, False),
        _edge([A, (5, 11), B], False, False),                                   # the stub
        _edge([B, (6, 13), (7, 12), (6, 11), A], False, False),                  # loop, one side
        _edge([B, (4, 13), (3, 13), (3, 12), (3, 11), (4, 10), A], False, False), # loop, other side
        _edge([B, (6, 14), (5, 15), (4, 14), B], False, False),                  # self-loop at B
    ]
    # the stub is 2 px, the loop's sides 4.4 and 6.8 px, the self-loop 5.7:
    # all within twice the 4 px threshold of this stroke
    out = s6._cluster_junctions(edges, max_len_px=4.0, dt_mm=lambda p: 4.0 if p == A else 3.0)
    assert len(out) == 1, [e["pts"] for e in out]
    assert out[0]["pts"][-1] == A and out[0]["free_end"] is False, \
        "the stem still ends at the node; capping it is _merge_through_junctions' job"


def test_a_ring_hanging_off_a_stem_is_not_junction_noise():
    # A counter the size of a letter: the loop edge is far longer than
    # twice the threshold, so it stays and the node keeps its three arms.
    A = (5, 10)
    ring = [A] + [(5 + int(round(6 * __import__("math").cos(t))), 16 + int(round(6 * __import__("math").sin(t))))
                  for t in [i * 0.2 for i in range(1, 31)]] + [A]
    ring = [p for i, p in enumerate(ring) if i == 0 or p != ring[i - 1]]
    edges = [
        _edge([(5, 0), (5, 2), (5, 4), (5, 6), (5, 8), A], True, False),
        _edge(ring, False, False),
    ]
    out = s6._cluster_junctions(edges, max_len_px=3.0)
    assert out is edges


def test_the_plus_decomposes_into_its_two_bars_at_both_scales():
    for scale in (1.0, 1.25):
        poly = affinity.scale(PLUS, scale, scale, origin="centroid") if scale != 1.0 else PLUS
        v = s6.classify_strokes(poly, machine.SATIN_MAX_WIDTH_MM)
        assert len(v.strokes) == 2, (scale, [(s.reason, s.stats.spine_len_mm) for s in v.strokes])
        lens = sorted(s.stats.spine_len_mm for s in v.strokes)
        assert lens[0] > 0.8 * lens[1], f"two bars of about the same length: {lens}"
