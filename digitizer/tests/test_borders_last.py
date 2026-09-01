"""Borders-last craft sequencing (`cfg.borders_last`, default OFF).

Kent's first physical sew-out (Instagram-icon test, 80 mm on pique polo,
reported 2026-08-31) surfaced the defect this rule exists for: the design's
satin borders sewed FIRST — the inner-circle border went in "right away", and
the decoded DST confirmed the entire white glyph (5,453 stitches of border
satin) at 0%, with seven background cones sewing around and against it. On
the committed repro fixture (`testdata/photo/repro_gradient_white_icon.png`)
the outer satin border sews at 0.5% of the design, before its own thread's
fills. Craft layering is the reverse: fills go down first, edge/border satin
rides on top of the seams it covers, details land late and stay crisp.

Two halves, both settled BEFORE geometry exists so stage 5's coverage
planning and stage 7's jump/trim derivation follow one consistent story (the
same argument `depth_sort_layers` already makes — no post-hoc reorder, no
`_hoist_same_thread`-style safety proof needed):

- **Across threads** (`borders_last_layers`, called by the pipeline between
  `compact_layers`/`depth_sort_layers` and `apply_layer_overrides`):
  satin-dominated layers sew after fill-dominated layers, relative order
  preserved within each class.
- **Within a thread block** (`sequence`'s picking loop): satin-tier shapes
  are picked after every non-satin shape in their group, so interior detail
  satin lands late in its own cone. An explicit `sew_order` pin still beats
  the bias, the same precedence every review-screen override gets.

The unit tests drive `borders_last_layers` directly with hand-built regions,
the same posture `test_merge_adjacent_same_thread.py` takes for its passes.

The flag defaults ON since Kent's 2026-09-01 ruling ("ON for
flat+gradient"): the defect was his own sewn garment, so OFF-by-default kept
it in his own exports. The layer half is gated OFF on the photo-sequencing
lane (there the layer order IS the depth story — depth_sort_layers'
contract says the satin classifier is not a depth cue), pinned below.
Golden blast radius was MEASURED at the flip, OFF-vs-ON on one machine so
platform numerics cancel: of the eight committed golden keys exactly one
moves — `photo/enthusiast_logo.png`, the key already deselected in CI and
locally red for platform numerics — so no judged golden changed and its
ubuntu re-capture stands as the follow-up (config.py's comment carries the
numbers).
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core.machine import SATIN_MAX_WIDTH_MM
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_satin import is_satin_candidate
from digitizer_core.stage7_sequence import borders_last_layers, sequence
from digitizer_core.threads import CHART

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FAB = get_fabric("pique_knit")


# --- helpers -----------------------------------------------------------------

def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: int, layer: int,
           meta: dict | None = None) -> Region:
    m = {"layer": layer}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta=m)


# The three shapes every test below builds from. The sanity test pins what
# the classifier says about them, so a classifier change cannot quietly turn
# the whole file vacuous.
RIBBON = bar(30, 2)      # a long thin band: satin
BIG = bar(30, 30)        # a large field: fill
BLOB = bar(3, 3)         # a compact dot (Kent's icon has one): fill


def test_the_fixture_shapes_classify_as_intended():
    assert is_satin_candidate(RIBBON, SATIN_MAX_WIDTH_MM)
    assert not is_satin_candidate(BIG, SATIN_MAX_WIDTH_MM)
    assert not is_satin_candidate(BLOB, SATIN_MAX_WIDTH_MM)


def layers_of(regions: list[Region]) -> dict[str, int]:
    return {r.shape_id: r.meta["layer"] for r in regions}


def plan_for(regions: list[Region], fabric=FAB, design_class: str = "flat",
             **cfg_kw):
    """Stage 5 then stage 7, the way pipeline.py runs them (the layer pass is
    exercised separately — these are the within-group tests' harness)."""
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, fabric, c)
    blocks, warnings = sequence(planned, fabric, c, design_class=design_class)
    return SimpleNamespace(blocks=blocks, warnings=warnings)


def sew_rank(plan) -> dict[str, tuple[int, int]]:
    """shape_id -> (block index, first-sewn rank), from the emitted runs."""
    order: dict[str, tuple[int, int]] = {}
    for bi, b in enumerate(plan.blocks):
        for r in b.runs:
            if r.shape_id and r.shape_id not in order:
                order[r.shape_id] = (bi, len(order))
    return order


# --- the layer pass, driven directly -----------------------------------------

def test_a_satin_layer_moves_after_the_fill_layer_it_precedes():
    regs = [region(RIBBON, "SAT", 3, 0), region(BIG, "FIL", 5, 1)]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"FIL": 0, "SAT": 1}
    assert ti == [5, 3], "the palette must move with the layers"
    assert [r.shape_id for r in regs] == ["FIL", "SAT"], \
        "regions re-sorted into the stage-4 stable order"


def test_a_satin_dominated_layer_with_a_small_fill_member_still_moves():
    """Kent's glyph exactly: two satin rings and one compact dot share the
    white thread. An every-region-must-be-satin test would let the dot pin
    the whole layer early; dominance by stitched area moves it."""
    regs = [
        region(RIBBON, "RING", 3, 0),
        region(BLOB, "DOT", 3, 0),
        region(BIG, "FIL", 5, 1),
    ]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"FIL": 0, "RING": 1, "DOT": 1}
    assert ti == [5, 3]


def test_a_fill_dominated_layer_with_a_satin_accent_stays():
    regs = [
        region(BIG, "FIL", 3, 0),
        region(bar(30, 2, cy=20), "ACC", 3, 0),
        region(bar(28, 28, cx=40), "FIL2", 5, 1),
    ]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"FIL": 0, "ACC": 0, "FIL2": 1}
    assert ti == [3, 5]


def test_relative_order_is_preserved_within_each_class():
    regs = [
        region(bar(30, 2, cy=-20), "SX", 2, 0),
        region(BIG, "FA", 3, 1),
        region(bar(30, 2, cy=20), "SY", 5, 2),
        region(bar(28, 28, cx=40), "FB", 7, 3),
    ]
    ti = borders_last_layers(regs, [2, 3, 5, 7], PipelineConfig())
    assert layers_of(regs) == {"FA": 0, "FB": 1, "SX": 2, "SY": 3}
    assert ti == [3, 7, 2, 5]


def test_a_pinned_satin_tier_counts_without_the_classifier():
    regs = [region(BIG, "PIN", 3, 0, meta={"tier": "satin"}),
            region(bar(28, 28, cx=40), "FIL", 5, 1)]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"FIL": 0, "PIN": 1}
    assert ti == [5, 3]


def test_a_pinned_fill_tier_never_counts_as_satin():
    regs = [region(RIBBON, "PINFIL", 3, 0, meta={"tier": "fill"}),
            region(BIG, "FIL", 5, 1)]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"PINFIL": 0, "FIL": 1}
    assert ti == [3, 5]


def test_with_the_satin_switch_off_auto_ribbons_stay_put():
    """cfg.satin False sends every auto shape to fill, so nothing here is a
    border and the order must not move."""
    regs = [region(RIBBON, "SAT", 3, 0), region(BIG, "FIL", 5, 1)]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig(satin=False))
    assert layers_of(regs) == {"SAT": 0, "FIL": 1}
    assert ti == [3, 5]


def test_unstitched_regions_get_no_vote():
    """An enclosed-background ribbon that sews nothing must not drag its
    layer into the satin class."""
    regs = [
        region(RIBBON, "GHOST", 3, 0, meta={"stitched": False}),
        region(BLOB, "DOT", 3, 0),
        region(BIG, "FIL", 5, 1),
    ]
    ti = borders_last_layers(regs, [3, 5], PipelineConfig())
    assert layers_of(regs) == {"GHOST": 0, "DOT": 0, "FIL": 1}
    assert ti == [3, 5]


def test_degenerate_inputs_are_a_no_op():
    assert borders_last_layers([], [3, 5], PipelineConfig()) == [3, 5]
    regs = [region(RIBBON, "SAT", 3, 0)]
    assert borders_last_layers(regs, [3], PipelineConfig()) == [3]
    assert layers_of(regs) == {"SAT": 0}


# --- the emitted plan, across threads ----------------------------------------

def test_emitted_plan_border_satin_block_sews_after_the_fill_block():
    def regs():
        return [region(RIBBON, "SAT", 3, 0), region(BIG, "FIL", 5, 1)]

    baseline = plan_for(regs())
    assert [b.thread_index for b in baseline.blocks] == [3, 5], \
        "baseline: the satin layer sews first, the defect being fixed"

    moved = regs()
    borders_last_layers(moved, [3, 5], PipelineConfig())
    plan = plan_for(moved)
    assert [b.thread_index for b in plan.blocks] == [5, 3]
    assert plan.blocks[0].runs[0].shape_id == "FIL", \
        "the first thread the machine puts down is the fill's"


# --- the emitted plan, within one thread block --------------------------------

def _one_thread_regions():
    """One cone, a big fill and a satin ribbon. The ribbon sits at the
    group's far edge, so the flag-OFF start rule (farthest from the group
    centre) provably picks it first — the contrast the ON assertions need."""
    return [region(BIG, "FIL", 3, 0),
            region(bar(30, 2, cy=30), "SAT", 3, 0)]


def test_within_a_block_satin_sews_after_fills_when_the_flag_is_on():
    off = sew_rank(plan_for(_one_thread_regions(), borders_last=False))
    assert off["SAT"] < off["FIL"], \
        "flag OFF pins the travel-only order: the ribbon sews first"

    on = sew_rank(plan_for(_one_thread_regions(), borders_last=True))
    assert on["FIL"] < on["SAT"], \
        "flag ON: the fill sews before the satin in the same block"
    assert on["FIL"][0] == on["SAT"][0], "same thread, same block either way"


def test_a_sew_order_pin_still_beats_the_within_block_bias():
    regs = _one_thread_regions()
    regs[1].meta["sew_order"] = 0
    on = sew_rank(plan_for(regs, borders_last=True))
    assert on["SAT"] < on["FIL"], \
        "an explicit review-screen pin outranks the craft default"


def test_borders_last_defaults_on():
    """Kent's 2026-09-01 flip ruling, recorded as a failing test the day the
    default silently changes again."""
    assert PipelineConfig().borders_last is True


def test_photo_sequencing_lane_keeps_its_layer_order():
    """The flip ruling's photo gate, end to end: on the photo-sequencing
    lane the block-level layer order is the depth story
    (background → dark→light → details), and `depth_sort_layers`' own
    contract refuses the satin classifier as a depth cue — so the LAYER
    half must not run there, flag or no flag. The within-group half still
    does (it orders shapes inside one cone and cannot touch the ramp).
    `photo_sequencing` opts this gradient fixture into the photo sew-order
    lane without dragging in the photo fill tiers, so the comparison
    isolates exactly the gate."""
    img = TESTDATA / "photo" / "repro_gradient_white_icon.png"

    def plan_with(flag: bool):
        _res, plan = digitize(img, PipelineConfig(
            target_width_mm=90.0, borders_last=flag,
            extra={"photo_sequencing": True}))
        return plan

    off, on = plan_with(False), plan_with(True)
    assert ([b.thread_index for b in on.blocks]
            == [b.thread_index for b in off.blocks]), \
        "the layer half ran on the photo-sequencing lane — depth story moved"
    # The within-group half still applies: the two arms disagree about the
    # order shapes sew inside their blocks.
    assert sew_rank(on) != sew_rank(off), \
        "the within-group half went dormant on the photo lane too"


# --- the repro fixture, end to end -------------------------------------------

def test_repro_fixture_border_satin_sews_after_its_cone_s_fills():
    """The committed repro of Kent's sew-out: flag ON, no block may sew a
    satin-classified shape before a fill-classified shape of its own cone.
    (Flag OFF the pink border ring is the first thread down at 0.0% — the
    defect the fixture exists to hold still.)"""
    img = TESTDATA / "photo" / "repro_gradient_white_icon.png"
    result, plan = digitize(img, PipelineConfig(target_width_mm=90.0,
                                                borders_last=True))
    satin_by_id = {
        r.shape_id: is_satin_candidate(r.polygon, SATIN_MAX_WIDTH_MM,
                                       design_class=result.design_class)
        for r in result.regions
    }
    ranks = sew_rank(SimpleNamespace(blocks=plan.blocks))
    by_block: dict[int, list[str]] = {}
    for sid, (bi, _rank) in ranks.items():
        by_block.setdefault(bi, []).append(sid)
    checked = 0
    for bi, sids in by_block.items():
        fills = [ranks[s] for s in sids if not satin_by_id[s]]
        satins = [ranks[s] for s in sids if satin_by_id[s]]
        if fills and satins:
            checked += 1
            assert max(fills) < min(satins), (
                f"block {bi}: a satin shape sews before a fill of its own "
                f"cone ({sids})")
    assert checked, "no mixed block found — the fixture stopped exercising this"
    first = plan.blocks[0].runs[0].shape_id
    assert not satin_by_id[first], \
        "the first thread the machine puts down is still border satin"
