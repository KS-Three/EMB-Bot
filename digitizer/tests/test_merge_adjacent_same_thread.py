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
    ever ran twice the stitch count would jump.

    Until 2026-08-31 this drove the owl end-to-end, because the pipeline's
    own re-snaps supplied same-thread adjacency for free. Both job-level
    split sources are now consolidated UPSTREAM of stage 7 — pipeline
    re-snaps by `rehome_resnapped_regions`, review-screen recolors by
    `apply_shape_edits`' own layer-move (regions.py: "the layer moves with
    it") — so no committed artwork reaches the merge with anything to fold
    (the owl sews 12 blocks with the flag OFF; pinned below). The invariant
    is exercised where the file's unit tests already live: `sequence()` on
    hand-built regions whose thread identity is forced, the one lane —
    upstream state this pipeline no longer produces, or a future split
    source — the pass still exists to serve."""
    from digitizer_core import fabric_for_garment
    from digitizer_core.stage5_overlap import resolve_overlaps
    from digitizer_core.stage7_sequence import sequence
    from shapely.geometry import Polygon as _Poly
    from digitizer_core.regions import Region

    fabric = fabric_for_garment("left_chest")

    def region(x0, layer, name, thread):
        poly = _Poly([(x0, 0), (x0 + 10, 0), (x0 + 10, 10), (x0, 10)])
        return Region(shape_id=name, polygon=poly, thread_index=thread,
                      thread_number=f"{1000 + thread}", area_mm2=poly.area,
                      meta={"layer": layer, "tier": "fill"})

    def blocks_with(merge: bool):
        # t7 at layers 0 and 2 with t9 between — [t7, t9, t7] raw. The
        # shapes sit 20 mm apart, far beyond both the hoist margin (their
        # order provably cannot move a seam) and trim_at (every block
        # boundary stays a real cut, so tie sites agree across the two
        # variants and only a DOUBLED tie could move the stitch count).
        regions = [region(0, 0, "Sa", 7), region(30, 1, "Sb", 9),
                   region(60, 2, "Sc", 7)]
        conf = PipelineConfig(garment_id="left_chest",
                              merge_adjacent_same_thread=merge)
        planned, _ = resolve_overlaps(regions, fabric, conf)
        blocks, _ = sequence(planned, fabric, conf)
        return blocks

    off, on = blocks_with(False), blocks_with(True)
    assert [b.thread_index for b in off] == [7, 9, 7]
    n_off = sum(len(r.points) for b in off for r in b.runs)
    n_on = sum(len(r.points) for b in on for r in b.runs)
    assert n_on == n_off, "merging changed the stitch count — ties doubled?"
    assert len(on) < len(off), "nothing merged"
    # No two adjacent blocks may share a thread once the pass has run.
    seq = [b.thread_index for b in on]
    assert all(x != y for x, y in zip(seq, seq[1:]))


def test_the_pipelines_own_output_no_longer_needs_the_merge():
    """The owl, flag OFF, must sew NO adjacent same-thread blocks: the
    re-snap splits that used to produce them (t46 at blocks 3-4, t12 at
    14-15, 2026-08-28) are consolidated upstream by
    `rehome_resnapped_regions` now, so merge-off equals merge-on. If this
    ever fails, a NEW split source has appeared — find it before reaching
    for the merge to paper over it."""
    img = TESTDATA / "photo/owl_kent.jpg"
    _r, off = digitize(img, PipelineConfig(target_width_mm=100.0,
                                           is_photographic=True,
                                           merge_adjacent_same_thread=False))
    seq = [b.thread_index for b in off.blocks]
    assert all(x != y for x, y in zip(seq, seq[1:])), (
        f"adjacent same-thread blocks are back: {seq}"
    )


# --- The non-adjacent half: _hoist_same_thread -----------------------------
#
# Unlike the adjacent merge, this one genuinely reorders stitches, so every
# test below is really asking the same question: does the geometry gate let
# through exactly the reorders that cannot move a seam, and refuse the rest?

from shapely.geometry import LineString

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
    assert _block_thread_geom(empty) is None
    out = _hoist_same_thread([_at(7, 0, 1), empty, _at(7, 4, 5)],
                             trim_at=3.0, margin_mm=0.5)
    assert [b.thread_index for b in out] == [7, 9, 7]


def test_a_one_point_run_still_has_geometry():
    """The 2026-08-18 chaining rebuild found the shipped instruments skipped
    one-point links. A degenerate run is a real needle position and must not
    silently become clear space."""
    b = _block(7, [StitchRun(points=[(1.0, 1.0)], shape_id="s")])
    g = _block_thread_geom(b)
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


def test_block_geometry_is_not_buffered():
    """Regression guard, 2026-08-28. The first cut buffered each block's thread
    by the margin and tested `intersects`. That is correct and unusably slow:
    it inflates thousands of short segments into one polygon with an enormous
    vertex count, and on repro_gradient_white_icon.png it took the digitize
    from 11.0s to 64.0s -- past tests/test_service.py's 60s job poll, which is
    the only reason it surfaced at all, and in an unrelated test.

    The margin is applied as a DISTANCE instead. Asserting the geometry's type
    pins that decision deterministically, where a timing assertion would be
    flaky on a loaded container.
    """
    b = _block(7, [_run(0.0, 1.0), _run(5.0, 6.0)])
    g = _block_thread_geom(b)
    assert g.geom_type in ("LineString", "MultiLineString"), (
        f"block geometry is {g.geom_type} — buffering is back, and with it a "
        "~6x digitize slowdown that only an unrelated test's timeout catches")
    assert g.area == 0.0, "a buffered geometry would have area"


def test_within_margin_matches_a_plain_distance_test():
    """The bbox reject in front of `distance` is an optimisation, so it must
    never change the answer — including for the diagonal case a naive
    axis-only reject gets wrong."""
    from digitizer_core.stage7_sequence import _within_margin
    a = LineString([(0.0, 0.0), (1.0, 0.0)])
    for bx, by, margin in [(1.2, 0.0, 0.5), (1.2, 0.0, 0.1),
                           (5.0, 5.0, 0.5), (1.1, 1.1, 2.0),
                           (0.5, 0.0, 0.0), (1.05, 1.05, 0.05)]:
        b = LineString([(bx, by), (bx + 1.0, by)])
        assert _within_margin(a, b, margin) == (a.distance(b) <= margin), (
            f"bbox reject changed the answer at ({bx}, {by}) margin {margin}")
