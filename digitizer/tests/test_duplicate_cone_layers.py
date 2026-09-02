"""One cone, one layer (`cfg.merge_duplicate_cones`, default OFF).

Defect 18 — the SECOND spool-revisit mechanism, the one defect 16's fix
correctly ignores. Stage 2 quantizes to COLOURS, and two different quantized
colours can snap to the same physical cone. Nothing downstream deduped them,
so the palette declared one spool twice: the operator was sent to the rack
twice for it, and the second, smaller layer sewed a fragment late over
finished work.

Measured on `drone_render.png` @ 80 mm — the fixture the defect was found on.
The declared palette is 21 slots carrying only 17 distinct threads, with
**t16, t308, t119 and t101 each declared twice**; t16 sews at 46.1% and again
40 st at 98.9%, t119 at 77.1% and again 60 st at 99.4%. Both tail blocks
re-enter territory earlier blocks already sewed — the first sew-out's own
tail pattern reached by another route.

With the flag ON, on that fixture:

    blocks   19 -> 17      (two fewer machine stops)
    revisits  2 -> 0
    stitches 9486 -> 9321
    needle-up 1295.2 -> 1237.3 mm   (over 2 MORE lifts: short ones
                                     replacing long tail flights)
    tail     [t2, t16(40), t119(60)] -> [t101(119), t7(80), t2(57)]

Four cones fold but only two blocks disappear, because the downstream passes
were already folding t308 and t101 after the fact; this subsumes them and
gets the two they could not reach. `_hoist_same_thread` declines those two
correctly, not as a failure — by its point stage 5 has planned coverage
against the un-merged order. Doing it upstream means there is no reorder to
justify.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage3_segment import merge_duplicate_cone_layers
from digitizer_core.threads import CHART
from digitizer_core.warnings_codes import DUPLICATE_CONE_LAYERS_MERGED

from .conftest import cfg

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
DRONE = TESTDATA / "photo" / "drone_render.png"


def region(sid: str, thread: int, layer: int) -> Region:
    from shapely.geometry import Polygon
    poly = Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer})


def layers_of(regs) -> dict[str, int]:
    return {r.shape_id: r.meta["layer"] for r in regs}


# --- the pass, driven directly ------------------------------------------------

def test_a_palette_with_no_duplicate_cone_is_returned_untouched():
    """The identity case is what keeps every non-duplicating design
    byte-identical, so it is pinned rather than assumed."""
    regs = [region("A", 3, 0), region("B", 5, 1)]
    palette = [3, 5]
    out, warnings = merge_duplicate_cone_layers(regs, palette)
    assert out == [3, 5]
    assert warnings == []
    assert layers_of(regs) == {"A": 0, "B": 1}


def test_a_duplicate_cone_folds_into_the_FIRST_layer_that_declared_it():
    """Direction is forced, not chosen: stage 2 orders the palette
    largest-area-first, so a duplicate's second slot is by construction the
    smaller one. Folding it into the first keeps stage 2's area story."""
    regs = [region("BIG", 3, 0), region("MID", 5, 1), region("TAIL", 3, 2)]
    out, warnings = merge_duplicate_cone_layers(regs, [3, 5, 3])
    assert out == [3, 5], "the duplicate slot is gone from the palette"
    assert layers_of(regs) == {"BIG": 0, "MID": 1, "TAIL": 0}
    assert warnings[0]["code"] == DUPLICATE_CONE_LAYERS_MERGED
    assert warnings[0]["count"] == 1
    assert warnings[0]["cones"] == [3]


def test_layers_stay_dense_after_a_fold():
    """A hole in the layer numbering would desynchronize every later pass
    from the palette it indexes."""
    regs = [region("A", 3, 0), region("B", 5, 1), region("C", 3, 2),
            region("D", 7, 3)]
    out, _ = merge_duplicate_cone_layers(regs, [3, 5, 3, 7])
    assert out == [3, 5, 7]
    got = sorted({r.meta["layer"] for r in regs})
    assert got == list(range(len(out))), "layer indices must stay dense"
    # and each region still points at its own cone's slot
    for r in regs:
        assert out[r.meta["layer"]] == r.thread_index


def test_several_cones_fold_at_once():
    regs = [region("A", 3, 0), region("B", 5, 1), region("C", 3, 2),
            region("D", 5, 3), region("E", 9, 4)]
    out, warnings = merge_duplicate_cone_layers(regs, [3, 5, 3, 5, 9])
    assert out == [3, 5, 9]
    assert layers_of(regs) == {"A": 0, "B": 1, "C": 0, "D": 1, "E": 2}
    assert warnings[0]["count"] == 2
    assert warnings[0]["cones"] == [3, 5]


def test_three_declarations_of_one_cone_all_land_on_the_first():
    regs = [region("A", 3, 0), region("B", 3, 1), region("C", 3, 2)]
    out, warnings = merge_duplicate_cone_layers(regs, [3, 3, 3])
    assert out == [3]
    assert layers_of(regs) == {"A": 0, "B": 0, "C": 0}
    assert warnings[0]["count"] == 2


# --- the whole pipeline, on the fixture the defect was found on ---------------

@pytest.fixture(scope="module")
def drone_off():
    return digitize(DRONE, cfg(target_width_mm=80.0))


@pytest.fixture(scope="module")
def drone_on():
    return digitize(DRONE, cfg(target_width_mm=80.0, merge_duplicate_cones=True))


def test_the_default_is_off():
    assert PipelineConfig().merge_duplicate_cones is False


def test_the_fixture_still_declares_duplicate_cones(drone_off):
    """Guards the whole file against going vacuous: if quantization stops
    producing a duplicate here, every assertion below proves nothing."""
    _res, plan = drone_off
    cones = [b.thread_index for b in plan.blocks]
    assert len(cones) - len(set(cones)) >= 1, \
        "no cone revisit left on the fixture — re-pick it or retire this file"


def test_the_fold_removes_every_cone_revisit(drone_on):
    _res, plan = drone_on
    cones = [b.thread_index for b in plan.blocks]
    assert len(cones) == len(set(cones)), \
        f"a cone still sews twice: {cones}"


def test_the_fold_costs_the_operator_fewer_stops(drone_off, drone_on):
    """A block boundary is a colour change, and on a single head a colour
    change is the machine halting for a human. That is what this buys."""
    _o, off = drone_off
    _n, on = drone_on
    assert len(on.blocks) < len(off.blocks)


def test_the_fold_does_not_pay_for_itself_in_thread(drone_off, drone_on):
    """The reorder could have traded stops for flying. It does not: fewer
    stitches AND less needle-up travel, over slightly more lifts — short
    ones replacing the long flights back out to the tail fragments."""
    import math

    def needle_up_mm(plan):
        up, prev = 0.0, None
        for b in plan.blocks:
            for r in b.runs:
                if prev is not None and (r.jump or r.trim):
                    up += math.dist(prev, r.points[0])
                prev = r.points[-1]
        return up

    _o, off = drone_off
    _n, on = drone_on
    assert sum(b.stitch_count for b in on.blocks) <= \
        sum(b.stitch_count for b in off.blocks)
    assert needle_up_mm(on) < needle_up_mm(off)


def test_the_fold_reports_which_spools_it_merged(drone_on):
    _res, plan = drone_on
    w = [x for x in plan.warnings if x["code"] == DUPLICATE_CONE_LAYERS_MERGED]
    assert w, "the fold happened silently"
    assert w[0]["count"] >= 1
    assert w[0]["cones"], "the warning must name the spools"


def test_an_explicit_layer_override_still_beats_the_fold(drone_on):
    """The fold runs BEFORE `apply_layer_overrides`, which is the precedence
    every review-screen override gets: the user's explicit layer is applied
    against the final, folded numbering and is not undone by it.

    Layer indices have never been stable across config changes — compaction
    renumbers when a layer empties, and the depth sort and borders-last both
    reorder before overrides apply — so interpreting an override in the
    post-fold numbering is the existing contract, not a new hazard."""
    _res, plan = drone_on
    sid = next(r.shape_id for b in plan.blocks for r in b.runs if r.shape_id)
    _r2, pinned = digitize(DRONE, cfg(target_width_mm=80.0,
                                      merge_duplicate_cones=True,
                                      shape_overrides={sid: {"layer": 0}}))
    first = next(r.shape_id for b in pinned.blocks for r in b.runs if r.shape_id)
    assert first == sid, "a shape pinned to layer 0 must open the design"


def test_off_leaves_the_design_exactly_as_it_was(drone_off):
    """Gate-3 posture: the flag defaults OFF and OFF must mean the flag does
    not exist. Same blocks, same threads, same coordinates."""
    _o, base = drone_off
    _e, explicit = digitize(DRONE, cfg(target_width_mm=80.0,
                                       merge_duplicate_cones=False))
    assert len(base.blocks) == len(explicit.blocks)
    for a, b in zip(base.blocks, explicit.blocks):
        assert a.thread_index == b.thread_index
        assert [r.points for r in a.runs] == [r.points for r in b.runs]
