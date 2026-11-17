"""`cfg.merge_chroma_guard`: a colour does not merge into a neutral.

Precision Drone (2026-11-17): the region merge weighs edges in CIEDE2000,
which put the vivid dark-blue sky 21-23 from the black ring, under the 26.0
threshold, and the ring swallowed sky and water. The numbers below are the
ones read off that merge.
"""
from __future__ import annotations

import networkx as nx
import numpy as np

from digitizer_core import stage2_photo_segment as s2
from digitizer_core.config import PipelineConfig

BLACK = np.array([10.0, 1.0, -4.0])
BLUE = np.array([27.0, 15.0, -45.0])
GREY = np.array([45.0, 0.5, -1.0])
NAVY_GREY = np.array([20.0, 4.0, -9.0])       # a bluish dark neutral, chroma ~10
ORANGE = np.array([65.0, 35.0, 65.0])
ORANGE2 = np.array([70.0, 28.0, 70.0])


def _graph(a, b, guard: bool):
    g = nx.Graph()
    for i, lab in enumerate((a, b)):
        g.add_node(i, **{"mean color": lab.astype(np.float64), "fg pixel count": 10_000, "pixel count": 10_000})
    g.add_node(2, **{"mean color": a.astype(np.float64), "fg pixel count": 10_000, "pixel count": 10_000})
    g.add_edge(0, 1, weight=0.0, bsum=0.0, blen=0)
    g.graph["fg total"] = 30_000
    if guard:
        g.graph["chroma_guard"] = True
    return g


def _w(a, b, guard):
    # the weight of the edge between node 0 (colour `a`) and neighbour 1 (colour `b`)
    return s2._weight_mean_color(_graph(a, b, guard), 2, 0, 1)["weight"]


def test_the_drones_merge_is_under_the_threshold_without_the_guard():
    assert _w(BLACK, BLUE, False) < s2.MERGE_DELTAE00_THRESH


def test_the_guard_lifts_a_colour_against_a_neutral_over_the_threshold():
    assert _w(BLACK, BLUE, True) > s2.MERGE_DELTAE00_THRESH
    assert _w(BLUE, BLACK, True) > s2.MERGE_DELTAE00_THRESH
    assert _w(GREY, ORANGE, True) > s2.MERGE_DELTAE00_THRESH


def test_the_guard_leaves_every_other_pair_alone():
    for a, b in ((BLACK, GREY), (BLACK, NAVY_GREY), (ORANGE, ORANGE2), (BLUE, BLUE + 3.0),
                 (NAVY_GREY, BLUE)):          # chroma 10 is neutral, but 10 vs 47 IS a gap: see below
        if s2._chroma_gap(a, b):
            continue
        assert _w(a, b, True) == _w(a, b, False)
    assert not s2._chroma_gap(BLACK, GREY)
    assert not s2._chroma_gap(ORANGE, ORANGE2)
    assert not s2._chroma_gap(BLACK, NAVY_GREY)


def test_chroma_gap_needs_one_neutral_and_one_colour():
    assert s2._chroma_gap(BLACK, BLUE) and s2._chroma_gap(BLUE, BLACK)
    assert not s2._chroma_gap(BLUE, ORANGE)                         # two colours: dE00's business
    mid = np.array([40.0, 12.0, -16.0])                             # chroma 20: neither
    assert not s2._chroma_gap(BLACK, mid) and not s2._chroma_gap(mid, BLUE)


def test_off_is_the_weight_it_always_was():
    g = _graph(BLACK, BLUE, False)
    assert "chroma_guard" not in g.graph
    # Kent 2026-11-17: "Flip ON (Recommended)". The frozen snapshot keeps False.
    from tests.conftest import PRE_FLIP
    assert PipelineConfig().merge_chroma_guard is True
    assert PRE_FLIP["merge_chroma_guard"] is False
