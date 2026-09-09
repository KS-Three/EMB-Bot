"""`_skeleton_edges` on the three-pixel triangles `medial_axis` leaves: the
clique where three arms meet, and the filled L where a chain bends.

Both masks are `enthusiast_logo`'s H at 93 mm, its left stem on the ARTWORK
polygon (what `cfg.satin_rail_comp` hands stage 6), read off the pruned
skeleton on 2026-09-09 and cut at the crossbar's and the stem's far ends.
The old tracer made 11 edges of it: a 3 px self-loop at the junction
(10,24) -> (10,23) -> (11,24) -> (10,24), the corner twig from (15,2) dead-
ending on the L's filler (8,8), and the stem between them re-emitted by the
leftover pass as five 1-3 px free/free fragments -- each of which
`satin_stroke` extended to both caps, so the stem sewed five times over.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import stage6_satin as s6

# x -> across, y -> down; the same orientation `_skeleton_edges` reads.
H_LEFT_STEM = [
    "..................",
    "..................",
    "...............#..",
    "..............#...",
    ".............#....",
    "............#.....",
    "...........#......",
    "..........#.......",
    "........##........",
    "........#.........",
    "........#.........",
    ".........#........",
    "........#.........",
    "........#.........",
    "........#.........",
    "........#.........",
    ".........#........",
    "........#.........",
    ".........#........",
    ".........#........",
    ".........#........",
    ".........#........",
    ".........#........",
    "..........#.##.##.",
    "..........##..#..#",
    ".........#........",
    ".........#........",
    ".........#........",
    ".........#........",
    ".........#........",
    "........#.........",
    "........#.........",
]


def _mask(rows: list[str]) -> np.ndarray:
    return np.array([[1 if ch == "#" else 0 for ch in r] for r in rows], np.uint8)


def _pixels(mask: np.ndarray) -> set[tuple[int, int]]:
    ys, xs = np.nonzero(mask)
    return set(zip(xs.tolist(), ys.tolist()))


def _ends(e: dict) -> frozenset:
    return frozenset((e["pts"][0], e["pts"][-1]))


def test_junction_clique_and_corner_filler_trace_as_three_arms():
    mask = _mask(H_LEFT_STEM)
    edges = s6._skeleton_edges(mask)

    assert not any(e["pts"][0] == e["pts"][-1] and not e["closed"] for e in edges), \
        "a walk out of the junction came straight back to it"
    assert not any(e["free_start"] and e["free_end"] for e in edges), \
        "leftover fragments: a chain was stranded and re-emitted piecemeal"
    assert len(edges) == 3
    # the junction pixel to each of the three cut ends: the corner twig at the
    # top of the stem, the crossbar, the stem below the bar
    assert {_ends(e) for e in edges} == {
        frozenset({(10, 24), (15, 2)}),
        frozenset({(10, 24), (17, 24)}),
        frozenset({(10, 24), (8, 31)}),
    }
    for e in edges:
        # each arm: the junction at one end, a cut (free) end at the other
        assert e["free_start"] != e["free_end"]
        # a walked chain, not a jump: every step is one pixel
        for a, b in zip(e["pts"], e["pts"][1:]):
            assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1
    covered = {p for e in edges for p in e["pts"]}
    assert covered == _pixels(mask)


def test_corner_filler_entered_from_the_twig_does_not_dead_end():
    # The stem alone, its tail curving right so that its cut end sorts AFTER
    # the twig's and the walk enters the filled L from the twig. The old
    # tracer stepped from the L onto its filler (8,8), found both of the
    # filler's neighbours already walked, and ended the edge there: the
    # twig as one edge, the stem from the other end as another, the chain
    # broken at a pixel that is not a node.
    rows = list(H_LEFT_STEM[:23])
    for x in range(10, 17):
        rows.append("." * x + "#" + "." * (17 - x))
    mask = _mask(rows)
    edges = s6._skeleton_edges(mask)
    assert len(edges) == 1
    e = edges[0]
    assert e["free_start"] and e["free_end"] and not e["closed"]
    assert _ends(e) == frozenset({(15, 2), (16, 29)})
    for a, b in zip(e["pts"], e["pts"][1:]):
        assert max(abs(a[0] - b[0]), abs(a[1] - b[1])) == 1
    # the L's filler is the one pixel the chain leaves out
    assert _pixels(mask) - set(e["pts"]) == {(8, 8)}


@pytest.mark.parametrize("rows", [
    ["....", ".##.", ".##.", "...."],                     # a 2x2 block: no chain at all
    ["#...", ".#..", "..#.", "...#"],                     # a plain diagonal
    ["..#..", "..#..", "#####", "..#..", "..#.."],        # a clean cross
])
def test_skeletons_without_a_triangle_are_untouched(rows):
    """The two rules only fire on a dead end or a first step into the node's
    own clique; a skeleton with neither traces exactly as the port did."""
    mask = _mask(rows)
    edges = s6._skeleton_edges(mask)
    covered = {p for e in edges for p in e["pts"]}
    if rows[0] == "....":
        # four mutually adjacent pixels: every one has crossing number 1 and
        # three neighbours -- no node, no chain of two free neighbours
        assert edges == []
    else:
        assert covered == _pixels(mask)
        assert not any(e["free_start"] and e["free_end"] and len(e["pts"]) < 4
                       for e in edges if rows[0] != "#...")
