"""The edge cap's repeated-cone route (MASTER_SCOPE defect 18), at its source.

Stage 7 appends the cap after all the artwork, one block per cone. Where that
first cap block wears the cone of the LAST artwork block, the two are
consecutive same-thread blocks -- a machine stop that has the operator cut
and re-thread the spool already on the machine, and the one repeat
`tools/cone_revisits.py` reads at gap 1 (`bg_uncertain`, cone 3363, both
garments, 2026-10-20). `cfg.merge_adjacent_same_thread` (ON since 2026-08-28)
already folds such pairs inside the artwork; the cap was the one seam it did
not reach. It reaches it now: the cap's stretches sew at the end of that block,
still jump + trim + tied exactly as a block start -- every stitch and cut the
same, in the same order, one stop fewer.

NOT `edge_cap_fold_into_colour` (PR #714, OFF and staying OFF): that one moves
a cap stretch AHEAD of later artwork. This moves nothing.
"""
from __future__ import annotations

from tests.test_cap_fold import (ABUT, APART, bar, is_cap, plan_for, points,
                                 region, stats)

ONE = [region(bar(20, 30), "S", 3, 0)]


def _seams(blocks) -> list[int]:
    """Indices i where block i and i+1 sew one cone with no operator step."""
    return [i for i in range(len(blocks) - 1)
            if blocks[i].thread_index == blocks[i + 1].thread_index
            and blocks[i].step is None and blocks[i + 1].step is None]


def test_old_path_repeats_the_cone_across_the_cap_seam():
    """The reproduction: a one-colour design sews its cap as a second block in
    the same cone, straight after the artwork."""
    old = plan_for(ONE, merge_adjacent_same_thread=False)
    assert [b.thread_index for b in old.blocks] == [3, 3]
    assert all(is_cap(r) for r in old.blocks[1].runs)
    assert stats(old).color_changes == 1


def test_the_cap_sews_in_the_last_blocks_cone_without_a_stop():
    new = plan_for(ONE)
    assert [b.thread_index for b in new.blocks] == [3]
    assert _seams(new.blocks) == []
    runs = new.blocks[0].runs
    first_cap = next(i for i, r in enumerate(runs) if is_cap(r))
    # The cap still sews AFTER every artwork row, and still opens cut + lifted.
    assert all(is_cap(r) for r in runs[first_cap:])
    assert runs[first_cap].jump and runs[first_cap].trim


def test_it_moves_no_stitch_and_no_cut_only_the_stop():
    """Counted off the emitted machine stream, on every fixture here."""
    for regions in (ONE, APART, ABUT):
        old = plan_for(regions, merge_adjacent_same_thread=False)
        new = plan_for(regions)
        assert points(new.blocks) == points(old.blocks)
        s_old, s_new = stats(old), stats(new)
        assert s_new.stitch_count == s_old.stitch_count
        assert s_new.trims == s_old.trims
        joined = len(_seams(old.blocks))
        assert s_new.color_changes == s_old.color_changes - joined
        assert len(new.blocks) == len(old.blocks) - joined
        assert _seams(new.blocks) == []


def test_a_cap_in_a_different_cone_keeps_its_own_block():
    """Only a SAME-cone seam joins: no cap block moves past another block."""
    for regions in (APART, ABUT):
        new = plan_for(regions)
        caps = [b for b in new.blocks if all(is_cap(r) for r in b.runs)]
        assert caps, "each fixture still ends in a cap block of its own"
        last_art = next(b for b in reversed(new.blocks)
                        if not all(is_cap(r) for r in b.runs))
        assert all(c.thread_index != last_art.thread_index for c in caps[:1])
