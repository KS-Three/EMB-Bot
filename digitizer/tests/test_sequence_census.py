"""The cone roll-up in tools/sequence_census.py — the merge-candidate half.

MASTER_SCOPE's queue item 12 ("merge a tiny cone into an adjacent shade")
described this tool as already putting "per-cone stitch counts against
candidate delta-E in one run". It did not: the census reported no colour at
all, so the join was by hand, and the question sat parked as "unmeasurable on
the repro" without that being re-checked against the committed corpus.

These pin the roll-up's arithmetic and, more importantly, the two things it
must REFUSE to do: invent a merge partner for a one-cone design, and pick the
neighbouring stop instead of the nearest colour.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from tools.sequence_census import _cone_merge_candidates, census

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _blk(rgb):
    return SimpleNamespace(rgb=rgb)


def _ob(number, stitches, patches=1, trims=0, jumps=0):
    return {"number": number, "stitches": stitches, "patches": patches,
            "trims": trims, "jumps": jumps}


def test_one_cone_in_two_blocks_is_ONE_cone_costing_two_stops():
    """The whole reason this rolls up by thread number rather than by block.

    An operator loads a spool once per stop no matter how the planner split
    it, so "this cone costs 2 stops for 300 stitches" is the sentence the
    merge question is about — and a per-block table cannot say it. (That a
    cone holds several blocks at all is defects 16 and 18's subject.)
    """
    cones = _cone_merge_candidates(
        [_blk((200, 30, 30)), _blk((30, 30, 200)), _blk((200, 30, 30))],
        [_ob("1704", 100, patches=2), _ob("3902", 900), _ob("1704", 200, patches=3)],
        1200)

    by = {c["number"]: c for c in cones}
    assert len(cones) == 2
    assert by["1704"]["stitches"] == 300
    assert by["1704"]["stops_cost"] == 2
    assert by["1704"]["patches"] == 5
    assert by["1704"]["share_pct"] == pytest.approx(25.0)


def test_the_candidate_is_the_nearest_COLOUR_not_the_neighbouring_stop():
    """A merge trades a stop for a colour step, so only colour may pick the
    partner. Here the cone sewn immediately next is the far one, and the
    near one is two stops away — if sew order ever leaked into this choice,
    the tool would propose the expensive merge."""
    cones = _cone_merge_candidates(
        [_blk((200, 30, 30)), _blk((20, 200, 40)), _blk((205, 40, 35))],
        [_ob("A", 50), _ob("B", 900), _ob("C", 900)],
        1850)

    tiny = next(c for c in cones if c["number"] == "A")
    assert tiny["nearest"]["number"] == "C"
    assert tiny["nearest"]["delta_e"] < 5.0


def test_a_one_cone_design_gets_no_merge_partner_at_all():
    """Not itself, not None-shaped-like-a-cone, not a crash. A design with
    nothing to merge into must say so, or the caller reads `delta_e` 0.0 and
    concludes the merge is free."""
    cones = _cone_merge_candidates([_blk((10, 10, 10))], [_ob("0020", 500)], 500)
    assert len(cones) == 1 and cones[0]["nearest"] is None


def test_cones_are_listed_smallest_first():
    """The merge question is always asked of the tiny cone, so it reads first."""
    cones = _cone_merge_candidates(
        [_blk((0, 0, 0)), _blk((255, 255, 255)), _blk((128, 128, 128))],
        [_ob("X", 900), _ob("Y", 30), _ob("Z", 400)], 1330)
    assert [c["number"] for c in cones] == ["Y", "Z", "X"]


def test_a_far_apart_palette_offers_no_defensible_merge_and_the_tool_says_so():
    """The pin that keeps the instrument honest about its own limits.

    MASTER_SCOPE parked item 12 as "unmeasurable on the repro (no defensible
    merge pair)", and until 2026-09-04 the repro was this test's fixture: its
    closest two cones were ~33 delta-E apart. Kent's gradient ruling changed
    that fixture's nature — its sweep now sews as five shade bands 5–6 delta-E
    apart BY DESIGN, adjacent shades of one ramp, not cones the tool should
    be asked to merge — so the pin moved to `logo_whitebg` (five cones, the
    closest pair 23 delta-E: a different colour by any reading, not a shade
    step). A tool that offered a candidate here would be manufacturing one.
    """
    c = census(TESTDATA / "logo_whitebg.png", 80.0, False)
    cones = c["per_cone"]
    assert len(cones) > 1, "the premise: more than one cone to choose between"
    assert all(x["nearest"] for x in cones)
    assert min(x["nearest"]["delta_e"] for x in cones) > 20.0
    # And the section really is per-cone, not a copy of per_block.
    assert sum(x["stitches"] for x in cones) == c["stitches"]
