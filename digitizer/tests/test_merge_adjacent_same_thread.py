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


# --- The non-adjacent half: _hoist_same_thread -----------------------------
#
# Unlike the adjacent merge, this one genuinely reorders stitches, so every
# test below is really asking the same question: does the geometry gate let
# through exactly the reorders that cannot move a seam, and refuse the rest?

from digitizer_core.stage7_sequence import (_block_thread_geom,
                                            _hoist_same_thread)


def _at(thread, x0, x1):
    """One block of one run, laid along y=0 from x0 to x1."""
    return _block(thread, [_run(x0, x1)])


def test_a_revisit_is_hoisted_when_it_clears_everything_it_jumps():
    # t7 at 0-1 and again at 4-5; the t9 between them sits far away at 50.
    out = _hoist_same_thread([_at(7, 0, 1), _at(9, 50, 51), _at(7, 4, 5)],
                             trim_at=3.0, margin_mm=0.5)
    assert [b.thread_index for b in out] == [7, 7, 9]


def test_a_revisit_is_refused_when_it_would_cross_geometry_it_touches():
    """The coverage question is real here: t9 lies between the two t7 blocks
    in space as well as in order, so stage 5 planned which of them extends
    under the other. Leaving the revisit in place is the correct answer."""
    out = _hoist_same_thread([_at(7, 0, 10), _at(9, 5, 6), _at(7, 4, 5)],
                             trim_at=3.0, margin_mm=0.5)
    assert [b.thread_index for b in out] == [7, 9, 7]


def test_abutting_counts_as_touching_and_is_refused():
    """Zero gap is still order-dependent — stage 5 picks which of two touching
    shapes extends underneath from their sew order. The margin is what makes
    a shared seam read as unsafe rather than as clear space."""
    # The gap that matters is between the MOVER and what it jumps over, not
    # between the target and the crossed block: 0.2mm from t9's end (2.0) to
    # the mover's start (2.2).
    blocks = [_at(7, 0, 1), _at(9, 1.2, 2.0), _at(7, 2.2, 3.0)]
    assert [b.thread_index for b in _hoist_same_thread(
        blocks, trim_at=3.0, margin_mm=0.5)] == [7, 9, 7]
    # Same geometry, margin small enough that 0.2mm reads as clear: allowed.
    blocks2 = [_at(7, 0, 1), _at(9, 1.2, 2.0), _at(7, 2.2, 3.0)]
    assert [b.thread_index for b in _hoist_same_thread(
        blocks2, trim_at=3.0, margin_mm=0.05)] == [7, 7, 9]


def test_margin_zero_still_gates_on_real_intersection():
    """0 disables the pass at the call site, but the function itself must not
    treat a zero margin as 'reorder anything' — overlapping geometry is
    unsafe at any tolerance."""
    out = _hoist_same_thread([_at(7, 0, 10), _at(9, 5, 6), _at(7, 4, 5)],
                             trim_at=3.0, margin_mm=0.0)
    assert [b.thread_index for b in out] == [7, 9, 7]


def test_fewer_than_three_blocks_cannot_have_a_revisit():
    src = [_at(7, 0, 1), _at(7, 4, 5)]
    assert _hoist_same_thread(src, trim_at=3.0, margin_mm=0.5) == src


def test_an_empty_block_is_never_treated_as_clear_space():
    """A block with no sewable geometry returns None, and None must read as
    'cannot prove this is safe', not as 'nothing in the way'."""
    empty = _block(9, [])
    assert _block_thread_geom(empty, 0.5) is None
    out = _hoist_same_thread([_at(7, 0, 1), empty, _at(7, 4, 5)],
                             trim_at=3.0, margin_mm=0.5)
    assert [b.thread_index for b in out] == [7, 9, 7]


def test_a_one_point_run_still_has_geometry():
    """The 2026-08-18 chaining rebuild found the shipped instruments skipped
    one-point links. A degenerate run is a real needle position and must not
    silently become clear space."""
    b = _block(7, [StitchRun(points=[(1.0, 1.0)], shape_id="s")])
    g = _block_thread_geom(b, 0.5)
    assert g is not None and not g.is_empty


def test_the_hoist_moves_no_stitches_and_changes_no_pixels_on_the_owl():
    """The whole safety argument, end to end: if the gate is right, reordering
    disjoint blocks cannot change what the design looks like. A changed render
    would mean the gate let through a reorder that moved a seam."""
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.stitchviz import render_png_bytes

    img = TESTDATA / "photo/owl_kent.jpg"
    off = digitize(img, PipelineConfig(target_width_mm=100.0,
                                       hoist_same_thread_margin_mm=0.0))[1]
    on = digitize(img, PipelineConfig(target_width_mm=100.0))[1]

    assert len(on.blocks) < len(off.blocks), "no revisit was hoisted at all"
    n_off = sum(len(r.points) for b in off.blocks for r in b.runs)
    n_on = sum(len(r.points) for b in on.blocks for r in b.runs)
    assert n_on == n_off, "hoisting changed the stitch count"
    assert (render_png_bytes(plan_to_design(off), px_per_mm=8.0)
            == render_png_bytes(plan_to_design(on), px_per_mm=8.0)), (
        "the render moved — the disjointness gate let a real seam reorder through")


def test_flat_artwork_is_untouched_by_the_hoist_too():
    img = TESTDATA / "logo_whitebg.png"
    off = digitize(img, PipelineConfig(hoist_same_thread_margin_mm=0.0))[1]
    on = digitize(img, PipelineConfig())[1]
    shape = lambda p: [(b.thread_index, [tuple(r.points) for r in b.runs])
                       for b in p.blocks]
    assert shape(off) == shape(on)
