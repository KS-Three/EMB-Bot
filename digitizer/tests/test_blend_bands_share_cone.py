"""`cfg.blend_bands_share_cone` — defect 18's band half (2026-10-11).

Blend bands of two parent regions that snap to one cone sew as two blocks:
`_shade_blocks` buckets a cone only WITHIN one group. `_hoist_same_thread`
declines them because a band always abuts its own parent's other shades.
`_fold_band_cones` may ignore exactly that contact — a group's block order is
`_shade_blocks`' L* sort, which stage 5 never planned — and must keep the
hoist's proof against every block of ANOTHER group it jumps.

Synthetic and instant, like `test_merge_adjacent_same_thread.py`'s hoist
half: each block is one run along y=0, so "touching" is read off x.
"""

from digitizer_core.config import PipelineConfig
from digitizer_core.stage7_sequence import (_fold_band_cones,
                                            _hoist_same_thread,
                                            _merge_adjacent_same_thread)
from digitizer_core.stitches import StitchBlock, StitchRun

G1 = (1, "", 3)
G2 = (2, "", 4)
G3 = (3, "", 5)


def _blk(thread, x0, x1, band=True, tag="s"):
    run = StitchRun(points=[(x0, 0.0), (x1, 0.0)], shape_id=tag,
                    jump=True, trim=True,
                    shade_thread_index=thread if band else None)
    return StitchBlock(thread_index=thread, thread_number=str(thread),
                       rgb=(1, 2, 3), runs=[run])


def _groups(*pairs):
    """[(group, block), ...] -> (blocks, run_group)."""
    blocks = [b for _g, b in pairs]
    return blocks, {id(r): g for g, b in pairs for r in b.runs}


def _fold(blocks, run_group, margin=0.5):
    out = _fold_band_cones(blocks, run_group, margin)
    return _merge_adjacent_same_thread(out, trim_at=3.0)


def test_default_is_off():
    assert PipelineConfig().blend_bands_share_cone is False


def test_a_band_crosses_its_own_parents_shades_but_the_hoist_will_not():
    """G1's cone-7 band, then G1's cone-8 band abutting both, then G2's
    cone-7 band. The hoist refuses (G2's band touches G1's cone-8 band); the
    fold sinks G1's cone-7 band past its OWN sibling and the two join."""
    blocks, rg = _groups((G1, _blk(7, 0, 1)), (G1, _blk(8, 1, 2)),
                         (G2, _blk(7, 2, 3)))
    hoisted = _hoist_same_thread(list(blocks), trim_at=3.0, margin_mm=0.5)
    assert [b.thread_index for b in hoisted] == [7, 8, 7]
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [8, 7]


def test_the_parents_keep_their_order_inside_the_shared_cone():
    a, b = _blk(7, 0, 1, tag="first"), _blk(7, 2, 3, tag="second")
    blocks, rg = _groups((G1, a), (G1, _blk(8, 1, 2)), (G2, b))
    out = _fold(blocks, rg)
    assert [r.shape_id for r in out[-1].runs] == ["first", "second"]


def test_a_hoist_is_preferred_when_the_later_band_clears():
    """G2's band is far from everything it jumps but its own parent's darker
    shade, so it moves UP and G1's lighter shade keeps its place."""
    blocks, rg = _groups((G1, _blk(7, 0, 1)), (G1, _blk(8, 1, 2)),
                         (G2, _blk(9, 40, 41)), (G2, _blk(7, 41, 42)))
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [7, 8, 9]


def test_another_groups_block_it_touches_refuses_both_moves():
    """G3 sits between the two bands in space AND in order: stage 5 planned
    which of them extends under it. The revisit correctly stays."""
    blocks, rg = _groups((G1, _blk(7, 0, 1)), (G3, _blk(5, 0.5, 2.5)),
                         (G2, _blk(7, 2, 3)))
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [7, 5, 7]


def test_plain_blocks_are_left_to_the_hoist():
    """No shade stamp on either: not a band, not this pass's business."""
    blocks, rg = _groups((G1, _blk(7, 0, 1, band=False)),
                         (G1, _blk(8, 1, 2, band=False)),
                         (G2, _blk(7, 2, 3, band=False)))
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [7, 8, 7]


def test_a_step_boundary_is_never_welded():
    """`nn_group_key`'s contract: two steps never share a block."""
    s1, s2 = (1, "twill", 3), (2, "", 4)
    blocks, rg = _groups((s1, _blk(7, 0, 1)), (s1, _blk(8, 1, 2)),
                         (s2, _blk(7, 2, 3)))
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [7, 8, 7]


def test_a_block_joined_across_groups_is_not_its_own_sibling():
    """A block the adjacent merge already joined across G1 and G3 carries
    both parents, so G1's band may not treat it as G1's own shade."""
    joined = _blk(8, 1, 2)
    joined.runs.append(StitchRun(points=[(1.0, 0.0), (1.5, 0.0)],
                                 shade_thread_index=8))
    blocks = [_blk(7, 0, 1), joined, _blk(7, 2, 3)]
    rg = {id(blocks[0].runs[0]): G1, id(joined.runs[0]): G1,
          id(joined.runs[1]): G3, id(blocks[2].runs[0]): G2}
    out = _fold(blocks, rg)
    assert [b.thread_index for b in out] == [7, 8, 7]


def test_nothing_to_fold_returns_the_same_list():
    blocks, rg = _groups((G1, _blk(7, 0, 1)), (G2, _blk(8, 5, 6)),
                         (G3, _blk(9, 10, 11)))
    assert _fold_band_cones(blocks, rg, 0.5) is blocks


# --- Wiring, through the real pipeline ---------------------------------------

from pathlib import Path

import pytest

from digitizer_core import stage7_sequence
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _plan_bytes(plan):
    return [(b.thread_number, [(r.points, r.jump, r.trim, r.kind)
                               for r in b.runs]) for b in plan.blocks]


@pytest.fixture(scope="module")
def ramp_runs():
    """`gradient_ramp_linear` at 80 mm: five blend bands of ONE parent, so
    the pass runs and must find nothing of its own to fold."""
    calls: list[int] = []
    real = stage7_sequence._fold_band_cones

    def spy(blocks, run_group, margin):
        calls.append(len(blocks))
        return real(blocks, run_group, margin)

    mp = pytest.MonkeyPatch()
    mp.setattr(stage7_sequence, "_fold_band_cones", spy)
    try:
        art = TESTDATA / "photo" / "gradient_ramp_linear.png"
        off = digitize(art, PipelineConfig(target_width_mm=80.0))[1]
        n_off = len(calls)
        on = digitize(art, PipelineConfig(target_width_mm=80.0,
                                          blend_bands_share_cone=True))[1]
    finally:
        mp.undo()
    return off, on, n_off, len(calls) - n_off


def test_off_never_reaches_the_pass(ramp_runs):
    _off, _on, n_off, _n_on = ramp_runs
    assert n_off == 0


def test_on_reaches_the_pass_and_one_parents_bands_are_untouched(ramp_runs):
    """One parent's bands already share a cone inside `_shade_blocks`; the
    fold has nothing to add, so ON is byte-identical here."""
    off, on, _n_off, n_on = ramp_runs
    assert n_on == 1
    assert _plan_bytes(on) == _plan_bytes(off)
