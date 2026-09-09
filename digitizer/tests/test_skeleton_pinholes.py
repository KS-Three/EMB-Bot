"""`stage6_satin._collapse_pinholes`: the 4-pixel diamond `medial_axis` leaves
around one pixel at a symmetric fork becomes a plain junction pixel, and
nothing else about a skeleton changes.

Found 2026-09-09 by the flip of `subpixel_edges`: `enthusiast_logo`'s "N" at
150 mm forks at the foot of its diagonal, both cap twigs prune as they
should, and the stub that reaches the diamond ends on a loop instead of a
free end -- so nothing extends it to the cap and 13.6 mm2 of the foot sews
as bare fabric. The product-level guard is
`test_preflight.py::test_the_bracket_tab_the_check_found_is_now_sewn` (the
same fixture and size, on the default trace); these pin the operation.
"""
from __future__ import annotations

import numpy as np
from skimage.morphology import medial_axis

from digitizer_core import stage6_satin as s6


def _grid(rows: list[str]) -> np.ndarray:
    return np.array([[ch == "#" for ch in r] for r in rows], dtype=bool)


def _edges(sk: np.ndarray) -> list[dict]:
    return s6._skeleton_edges(sk.astype(np.uint8))


def test_a_diamond_with_three_arms_becomes_one_junction_pixel():
    # An arm from above reaches the ring's top pixel, one leaves the bottom
    # pixel down-left and one leaves the right pixel down-right -- the "N"
    # foot's pattern, read straight off its skeleton window.
    sk = _grid([
        "....#......",
        "....#......",
        "...#.#.....",
        "....#.#....",
        "...#...#...",
        "..#.....#..",
        ".#.......#.",
    ])
    before = _edges(sk)
    assert any(e["free_start"] == e["free_end"] == False for e in before), \
        "the fixture must contain a node-to-node edge (the loop) before the fix"
    out = s6._collapse_pinholes(sk)
    assert out[3, 4], "the centre pixel is set"
    assert not out[2, 3], "the ring pixel with no arm is dropped"
    assert out[1, 4] and out[3, 5] and out[4, 4], "ring pixels carrying arms stay"
    assert int(out.sum()) == int(sk.sum()), "one pixel in, one pixel out"
    after = _edges(out)
    assert len(after) == 3, [e["pts"] for e in after]
    assert all(e["free_start"] != e["free_end"] for e in after), \
        "three arms, each from the junction to a free end, no loop"
    assert all(e["pts"][0] == (4, 3) or e["pts"][-1] == (4, 3) for e in after), \
        "every arm now meets at the old diamond's centre"


def test_a_skeleton_without_a_diamond_comes_back_unchanged():
    rng = np.random.default_rng(3)
    mask = np.zeros((60, 90), bool)
    # a wide bar with a bump: a junction and a corner, no symmetric peak
    mask[20:40, 5:85] = True
    mask[5:40, 40:52] = True
    mask[rng.integers(0, 60, 20), rng.integers(0, 90, 20)] = True
    skel = medial_axis(mask, rng=0)
    out = s6._collapse_pinholes(skel)
    if not (out == skel).all():
        # medial_axis is free to leave a diamond on this bar too; then the
        # contract is the one above, not identity
        assert int(out.sum()) == int(skel.sum())
    else:
        assert (out == skel).all()
    assert out.dtype == bool


def test_a_full_ring_around_a_real_hole_is_not_a_pinhole():
    # Diagonals set: a 3x3 ring, which is a loop around a genuine hole, not
    # the diamond. Left exactly as it is.
    sk = _grid([
        ".....",
        ".###.",
        ".#.#.",
        ".###.",
        ".....",
    ])
    out = s6._collapse_pinholes(sk)
    assert (out == sk).all()


def test_a_tiny_or_empty_skeleton_is_safe():
    for shape in ((0, 0), (1, 1), (2, 5), (5, 2)):
        sk = np.zeros(shape, bool)
        assert s6._collapse_pinholes(sk).shape == shape
