"""Two colour blocks that sew the IDENTICAL cone, back to back, cost the
operator a stop that buys nothing: cut the thread, load the spool already on
the machine, carry on.

Measured on `testdata/photo/owl_kent.jpg` at 100 mm with
`is_photographic=True` (Kent's own owl, 2026-08-28): 17 blocks over 12
spools, and two of the sixteen stops separate same-thread blocks — t46 at
blocks 3-4 and t12 at 14-15. Folding those gives 15 blocks / 14 stops with
the stitch count UNCHANGED, which is the whole point: this is bookkeeping,
not a geometry change.

The unit tests drive `_merge_adjacent_same_thread` directly with hand-built
blocks, the same posture `test_shade_thread_emission.py` takes for
`_shade_blocks`: the job-level path cannot control adjacency and thread
identity precisely enough to hit the seam-recompute branch on purpose.

The non-adjacent case (the same cone revisited with other colours between —
t4 at blocks 0/2/7 on that same owl run) is deliberately NOT merged here and
is pinned as such below: joining those WOULD reorder stitches across other
colours, which stage 5 has already planned coverage against.
"""
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage7_sequence import _merge_adjacent_same_thread
from digitizer_core.stitches import StitchBlock, StitchRun


TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _run(x0, x1, jump=False, trim=False):
    return StitchRun(points=[(x0, 0.0), (x1, 0.0)], shape_id="s",
                     jump=jump, trim=trim)


def _block(thread, runs):
    return StitchBlock(thread_index=thread, thread_number=str(thread),
                       rgb=(1, 2, 3), runs=runs)


def test_adjacent_same_thread_blocks_fold_into_one():
    a, b = _run(0.0, 1.0), _run(1.2, 2.0, jump=True, trim=True)
    out = _merge_adjacent_same_thread([_block(7, [a]), _block(7, [b])],
                                      trim_at=3.0)
    assert [blk.thread_index for blk in out] == [7]
    assert out[0].runs == [a, b], "both blocks' runs, in their original order"


def test_different_threads_are_never_folded():
    a, b = _run(0.0, 1.0), _run(1.2, 2.0)
    out = _merge_adjacent_same_thread([_block(7, [a]), _block(9, [b])],
                                      trim_at=3.0)
    assert [blk.thread_index for blk in out] == [7, 9]


def test_same_thread_separated_by_another_colour_is_left_alone():
    """The revisit case. Folding it would move stitches across the colour
    between them, which stage 5 planned its coverage against — so this pass
    must NOT touch it, however tempting the stop saving looks."""
    a, mid, c = _run(0.0, 1.0), _run(5.0, 6.0), _run(1.2, 2.0)
    out = _merge_adjacent_same_thread(
        [_block(7, [a]), _block(9, [mid]), _block(7, [c])], trim_at=3.0)
    assert [blk.thread_index for blk in out] == [7, 9, 7]


def test_the_absorbed_block_s_opener_is_recomputed_on_distance():
    """A block opener carries an unconditional `jump=True, trim=True` from
    `_shade_blocks`. Mid-block that is the wrong answer, so it is re-asked on
    plain distance — the same rule `_shade_blocks` uses for a rejoin."""
    a = _run(0.0, 1.0)
    near = _run(1.02, 2.0, jump=True, trim=True)   # 0.02mm — under TINY
    out = _merge_adjacent_same_thread([_block(7, [a]), _block(7, [near])],
                                      trim_at=3.0)
    assert len(out) == 1
    assert not near.jump and not near.trim, "stale opener cut was not cleared"


def test_a_far_seam_keeps_its_cut():
    """Distance decides both ways: a genuinely long hop still trims, because
    a float that long is one someone removes with scissors."""
    a = _run(0.0, 1.0)
    far = _run(50.0, 51.0, jump=True, trim=True)
    out = _merge_adjacent_same_thread([_block(7, [a]), _block(7, [far])],
                                      trim_at=3.0)
    assert len(out) == 1
    assert far.jump and far.trim, "a 49mm seam must still be cut"


@pytest.mark.parametrize("blocks", [[], [None]])
def test_degenerate_inputs_are_a_no_op(blocks):
    src = [] if blocks == [] else [_block(7, [_run(0.0, 1.0)])]
    assert len(_merge_adjacent_same_thread(src, trim_at=3.0)) == len(src)


def test_flat_artwork_is_byte_identical_with_the_flag_either_way():
    """The merge only fires where two adjacent blocks share a thread, which
    no flat design measured here produces — so the flat lane, and every
    golden pinned on it, must be untouched by the default flip."""
    img = TESTDATA / "logo_whitebg.png"
    _r1, off = digitize(img, PipelineConfig(merge_adjacent_same_thread=False))
    _r2, on = digitize(img, PipelineConfig(merge_adjacent_same_thread=True))

    def shape(plan):
        return [(b.thread_index, [tuple(r.points) for r in b.runs])
                for b in plan.blocks]

    assert shape(off) == shape(on)


def test_ties_are_applied_exactly_once_across_the_merge():
    """`apply_ties` is not idempotent — its own docstring warns that tying
    twice "doubles the lock into eight stitches of thread piled in one spot".
    The merge defers tying so it happens once, on the surviving blocks; if it
    ever ran twice the stitch count would jump."""
    img = TESTDATA / "photo/owl_kent.jpg"
    cfg = dict(target_width_mm=100.0, is_photographic=True)
    _r1, off = digitize(img, PipelineConfig(**cfg,
                                            merge_adjacent_same_thread=False))
    _r2, on = digitize(img, PipelineConfig(**cfg,
                                           merge_adjacent_same_thread=True))
    n_off = sum(len(r.points) for b in off.blocks for r in b.runs)
    n_on = sum(len(r.points) for b in on.blocks for r in b.runs)
    assert n_on == n_off, "merging changed the stitch count — ties doubled?"
    assert len(on.blocks) < len(off.blocks), "nothing merged on the owl"
    # No two adjacent blocks may share a thread once the pass has run.
    seq = [b.thread_index for b in on.blocks]
    assert all(x != y for x, y in zip(seq, seq[1:]))
