"""A planned color that never reaches the needle has to say so (2026-08-14).

Found while scoring the 23-design professional corpus. `ours_regions.json`
listed regions — real shapes, with ids, threads and areas — that produced zero
rows in `ours_stitches.csv`, and nothing anywhere said a word about it. The
hunt found three separate things behind that one symptom:

1. `plan_stitches` drops every region with `meta["stitched"] is False` (the
   enclosed-background default, or a review-screen override). That drop is
   INTENDED — but it was silent, on 104 regions across 20 of the 23 corpus
   designs, up to 36.7 mm² each.

2. Because it was silent, its consequence went unnoticed: `compact_layers`
   keeps a palette slot for any layer that still holds a Region, stitched or
   not, so a layer whose every member was skipped left a cone in the color
   list that nothing sews. 13 of the 23 designs returned a palette that did
   not match the blocks they sew.

3. `adapter._thread_name` read that palette BY BLOCK INDEX. One phantom entry
   ahead of a block and the block ships under the previous cone's NAME while
   keeping its own correct NUMBER — which is why nobody caught it by eye.
   Measured before the fix: `golf_hat` block 3 (thread 0020, black) labelled
   "0020 Tangerine"; 22 of the corpus's 96 blocks wrong across 6 of its 23
   designs, worst `hotel_fremont_patch` at 7 of 8.

Point 1 is now `SHAPES_LEFT_UNSEWN`, naming the shapes and their area — the
COOKBOOK.md "hard-won lesson" from stage 4's dropped-region bug, which hid for
days behind a warning that only counted. Points 2 and 3 are fixed: the plan's
palette is built from its own blocks, and the adapter only takes a name from
an entry that agrees with the block's thread number.
"""
from __future__ import annotations

from digitizer_core.adapter import plan_to_design
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stitches import FILL, StitchBlock, StitchPlan, StitchRun
from digitizer_core.warnings_codes import SHAPES_LEFT_UNSEWN

from .conftest import TESTDATA, cfg

PLAN_CFG_KW = {"garment_id": "left_chest"}


def _warning(plan, code):
    found = [w for w in plan.warnings if w["code"] == code]
    assert len(found) <= 1, f"{code} emitted {len(found)} times"
    return found[0] if found else None


# --- 1. the skip is loud ----------------------------------------------------


def test_skipped_shapes_are_named_with_their_area(whitebg):
    """`logo_whitebg.png`'s ring hole is enclosed background: a real Region,
    unstitched by default, 154 mm² of it. Before this fix the plan said
    nothing about it at all."""
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    skipped = [r for r in whitebg.regions if not r.meta.get("stitched", True)]
    assert skipped, "fixture no longer exercises the unstitched path"

    w = _warning(plan, SHAPES_LEFT_UNSEWN)
    assert w is not None, "a planned shape was dropped with no warning"
    assert w["count"] == len(skipped)
    assert set(w["ids"]) == {r.shape_id for r in skipped}
    assert set(w["threads"]) == {r.thread_number for r in skipped}
    # The area is the number that separates "a speck" from "the whole badge",
    # so it has to be IN the warning, not inferable from it.
    assert w["total_mm2"] == round(sum(r.area_mm2 for r in skipped), 2)
    assert w["largest_mm2"] == round(max(r.area_mm2 for r in skipped), 2)
    assert w["enclosed_background"] == sum(
        1 for r in skipped if r.meta.get("enclosed_background")
    )
    # The prose has to carry the same facts — a UI that only prints messages
    # must not be strictly less informed than one that reads `extra`.
    assert f"{w['largest_mm2']:.1f}" in w["message"]
    for number in w["threads"]:
        assert number in w["message"]


def test_a_design_with_nothing_skipped_stays_quiet(ribbon):
    """One-color satin fixture, no enclosed background: the warning must not
    fire, or it becomes noise and stops being read."""
    plan = plan_stitches(ribbon, cfg(**PLAN_CFG_KW))
    assert all(r.meta.get("stitched", True) for r in ribbon.regions)
    assert _warning(plan, SHAPES_LEFT_UNSEWN) is None


def test_the_skip_names_the_shapes_the_plan_actually_left_out(whitebg):
    """The warning is only worth anything if its ids are exactly the shapes
    missing from the stitches — not a stale list computed somewhere else."""
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    sewn = {run.shape_id for _b, run in plan.iter_runs()}
    w = _warning(plan, SHAPES_LEFT_UNSEWN)
    for sid in w["ids"]:
        assert sid not in sewn


# --- 2. the plan's palette is the list of cones it sews ---------------------


def test_plan_palette_has_exactly_one_entry_per_block(whitebg):
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    assert len(plan.palette) == len(plan.blocks)
    for entry, block in zip(plan.palette, plan.blocks):
        assert entry["number"] == block.thread_number
        assert tuple(entry["rgb"]) == tuple(block.rgb)


def test_a_layer_that_sews_nothing_leaves_no_cone_in_the_plan(whitebg):
    """The regression proper. `result.palette` is the per-LAYER list and
    still carries the skipped layer's cone (the review screen needs a row to
    restore it from) — the PLAN's palette must not, because that is the list
    of cones a human loads onto the machine."""
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    skipped = [r for r in whitebg.regions if not r.meta.get("stitched", True)]
    dead_layers = {r.meta["layer"] for r in skipped} - {
        r.meta["layer"] for r in whitebg.regions if r.meta.get("stitched", True)
    }
    assert dead_layers, "fixture no longer has a layer that sews nothing"

    dead_cones = {whitebg.palette[L]["number"] for L in dead_layers}
    sewn_cones = {b.thread_number for b in plan.blocks}
    for number in dead_cones:
        assert number not in [e["number"] for e in plan.palette] or number in sewn_cones
    assert len(whitebg.palette) > len(plan.palette)


# --- 3. a block is never labelled with another cone's name -----------------


def _misaligned_plan() -> StitchPlan:
    """`golf_hat`'s exact shape, in miniature: a palette one entry longer
    than the block list, with the phantom cone sitting BEFORE the last block
    so a positional read shifts every name after it."""
    def block(number, rgb):
        return StitchBlock(
            thread_index=0, thread_number=number, rgb=rgb,
            runs=[StitchRun(points=[(0.0, 0.0), (1.0, 1.0)], kind=FILL)],
        )

    return StitchPlan(
        blocks=[block("1300", (255, 153, 51)), block("0020", (0, 0, 0))],
        palette=[
            {"number": "1300", "name": "Tangerine", "rgb": [255, 153, 51]},
            {"number": "9999", "name": "Phantom", "rgb": [1, 2, 3]},
            {"number": "0020", "name": "Black", "rgb": [0, 0, 0]},
        ],
        design_size_mm=(10.0, 10.0),
    )


def test_a_drifted_palette_can_never_rename_a_block():
    """Even handed a palette that does not describe the blocks, the adapter
    must not put "Phantom" on a black cone. Before the fix this returned
    '0020 Phantom'."""
    design = plan_to_design(_misaligned_plan())
    names = [c["name"] for c in design["colors"]]

    assert names == ["1300 Tangerine", "0020 Black"]


def test_an_unnamed_cone_beats_a_misnamed_one():
    """No entry anywhere matches the block's thread: the label falls back to
    the number alone. A gap is honest; a wrong name is not."""
    plan = _misaligned_plan()
    plan.palette = [{"number": "5510", "name": "Emerald", "rgb": [0, 128, 0]}]
    design = plan_to_design(plan)

    assert [c["name"] for c in design["colors"]] == ["1300", "0020"]


def test_the_shipped_design_labels_every_block_with_its_own_cone(whitebg):
    """End to end on the repo's own fixture: number and name in each label
    describe the same thread."""
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    design = plan_to_design(plan)
    numbers = {e["number"]: e["name"] for e in plan.palette}

    assert len(design["colors"]) == len(plan.blocks)
    for color, block in zip(design["colors"], plan.blocks):
        number, _, name = color["name"].partition(" ")
        assert number == block.thread_number
        assert name == numbers[block.thread_number]


# --- the enclosed-background policy itself is unchanged ---------------------


def test_making_the_skip_loud_did_not_start_sewing_it(whitebg):
    """Loudness is the whole fix; the policy is untouched. The skipped shapes
    still produce no stitches."""
    plan = plan_stitches(whitebg, cfg(**PLAN_CFG_KW))
    sewn = {run.shape_id for _b, run in plan.iter_runs()}
    for r in whitebg.regions:
        if not r.meta.get("stitched", True):
            assert r.shape_id not in sewn


def test_an_override_that_restores_a_shape_silences_the_warning():
    """`shape_overrides[sid]["stitched"] = True` puts the shape back — and
    with nothing left out, the warning stops firing. Pins that the warning
    tracks the real exclusion set rather than the enclosed tag."""
    base = run_stages(TESTDATA / "logo_whitebg.png", cfg())
    skipped = [r.shape_id for r in base.regions if not r.meta.get("stitched", True)]
    assert skipped

    restored = run_stages(
        TESTDATA / "logo_whitebg.png",
        cfg(shape_overrides={sid: {"stitched": True} for sid in skipped}),
    )
    plan = plan_stitches(restored, cfg(**PLAN_CFG_KW))

    assert all(r.meta["stitched"] for r in restored.regions)
    assert _warning(plan, SHAPES_LEFT_UNSEWN) is None
    assert len(plan.palette) == len(plan.blocks)
