"""`satin_join_square`'s straightening keeps a member that is BENDING into
its corner (defect 60, 2026-10-07): the apex cap `_STRAIGHT_MAX_MOVE_HALVES`.

ENTHUSIAST's two S's at 80 mm (half-width 0.87 mm) had each bowl read as a
join corner -- a pull-comped inner bowl is a sharp reflex vertex at that
size -- and `_straighten_member_end` projected both members' apexes 0.80 /
0.82 mm (0.92 half-widths) onto their fitted lines, so the two ends no
longer met and the bowl's wedge sewed bare: the fixture's first lost element
of over 1 mm2. Over the corpus under the flag the apex displacement is p50
0.92 half-widths on enthusiast, 0.22 on Fremont, 0.12 on Becker. Over the
cap the member keeps its bend, exactly as before the flip; under it the
straightening is unchanged (`test_join_corner_straight.py` pins that on
Fremont's E).
"""
from __future__ import annotations

import math

from digitizer_core import stage6_satin as s6


def _bent_member(half: float, radius_halves: float, n: int = 40) -> list[tuple[float, float]]:
    """A member that runs straight for 4 half-widths and then bends through a
    quarter circle of `radius_halves` half-widths into its corner end: an S
    bowl at `radius_halves` ~ 1.3, an L's medial-axis rounding at ~ 0.5."""
    r = radius_halves * half
    pts = [(0.0, 0.0)]
    for i in range(1, 17):
        pts.append((4.0 * half * i / 16, 0.0))
    for i in range(1, n + 1):
        t = (math.pi / 2) * i / n
        pts.append((4.0 * half + r * math.sin(t), r - r * math.cos(t)))
    return pts


def _apex_shift(piece, out) -> float:
    return math.dist(piece[-1], out[-1])


def test_a_bowl_read_as_a_corner_keeps_its_bend_under_the_cap():
    half = 0.87
    piece = _bent_member(half, radius_halves=1.3)
    out = s6._straighten_member_end(piece, True, half)
    assert out == piece, "the bend's apex sits far off the member's line; the member must keep it"


def test_the_same_bend_straightens_with_the_cap_lifted(monkeypatch):
    half = 0.87
    piece = _bent_member(half, radius_halves=1.3)
    monkeypatch.setattr(s6, "_STRAIGHT_MAX_MOVE_HALVES", math.inf)
    out = s6._straighten_member_end(piece, True, half)
    assert out != piece
    shift = _apex_shift(piece, out)
    monkeypatch.undo()
    assert shift > s6._STRAIGHT_MAX_MOVE_HALVES * half, (shift, half)   # the case the cap exists for


def test_a_corners_rounding_still_straightens():
    """An L's medial axis rounds its corner over about half a half-width:
    the apex sits close to the member's line, under the cap, and the end is
    squared exactly as the flip intended."""
    half = 0.87
    piece = _bent_member(half, radius_halves=0.45)
    out = s6._straighten_member_end(piece, True, half)
    assert out != piece
    shift = _apex_shift(piece, out)
    assert 0.0 < shift <= s6._STRAIGHT_MAX_MOVE_HALVES * half, (shift, half)
    # and the straightened end lies on the member's own line (y = 0)
    assert abs(out[-1][1]) < 0.05 * half
