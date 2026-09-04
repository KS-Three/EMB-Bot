"""Defect 16's remainder — a re-snapped region must sew WITH its cone.

`revalidate_threads` re-snaps a drifted region onto a better cone without
moving it to that cone's LAYER, so `nn_group_key`'s
`(sew_index, step_key, thread_index)` splits one spool across layers sewing
at different positions. Stage 7's merge/hoist passes (PRs #291/#293) rejoin
the cases they can PROVE safe after the fact; everything touching stays
split — measured on `repro_gradient_white_icon.png` at 80 mm as a 50-stitch
t204 cone at 99.6% of the design, re-entering territory sewn at 0%.

`rehome_resnapped_regions` is the upstream fix stage 7's own module
docstring prescribes for sequencing overrides: edit the layer BEFORE stage 5
plans coverage, so every seam is planned against the order actually sewn and
no after-the-fact disjointness proof is needed. It moves ONLY regions the
pipeline itself re-snapped (`meta["thread_resnapped_de00"]`) — a review-
screen recolor is an explicit user act and keeps its position.
"""
from __future__ import annotations

from pathlib import Path

from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize, run_stages
from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import rehome_resnapped_regions
from digitizer_core.threads import CHART

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
REPRO = TESTDATA / "photo" / "repro_gradient_white_icon.png"


def _region(sid: str, layer: int, thread: int, resnapped: bool = False,
            step_key: str | None = None) -> Region:
    poly = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)])
    r = Region(shape_id=sid, polygon=poly, thread_index=thread,
               thread_number=CHART[thread].number, area_mm2=poly.area)
    r.meta["layer"] = layer
    if resnapped:
        r.meta["thread_resnapped_de00"] = 12.3
    if step_key is not None:
        r.meta["step_key"] = step_key
    return r


def test_resnapped_region_moves_to_the_layer_owning_its_cone():
    # L0 declares t5, L1 declares t9. The L1 region re-snapped onto t5, so it
    # belongs at L0's sew position — one spool, one position.
    regions = [
        _region("Sa", layer=0, thread=5),
        _region("Sb", layer=1, thread=5, resnapped=True),
    ]
    moved = rehome_resnapped_regions(regions, [5, 9])
    assert moved == 1
    assert regions[1].meta["layer"] == 0


def test_earliest_declaring_layer_wins_when_cones_duplicate():
    regions = [
        _region("Sa", layer=0, thread=5),
        _region("Sb", layer=2, thread=5),
        _region("Sc", layer=3, thread=5, resnapped=True),
    ]
    moved = rehome_resnapped_regions(regions, [5, 9, 5, 7])
    assert moved == 1
    assert regions[2].meta["layer"] == 0


def test_unmarked_regions_never_move():
    # Same split shape, but nothing says the PIPELINE re-snapped it — a
    # review-screen recolor lands exactly here and must keep its position.
    regions = [
        _region("Sa", layer=0, thread=5),
        _region("Sb", layer=1, thread=5),
    ]
    assert rehome_resnapped_regions(regions, [5, 9]) == 0
    assert regions[1].meta["layer"] == 1


def test_a_cone_no_layer_declares_stays_put():
    regions = [
        _region("Sa", layer=0, thread=5),
        _region("Sb", layer=1, thread=7, resnapped=True),
    ]
    assert rehome_resnapped_regions(regions, [5, 9]) == 0
    assert regions[1].meta["layer"] == 1


def test_step_regions_are_never_rehomed():
    # An appliqué step's stop sequence is an operator instruction; §0's
    # consequence 3 (nn_group_key) keeps step regions out of every pool and
    # this pass must too.
    regions = [
        _region("Sa", layer=0, thread=5),
        _region("Sb", layer=1, thread=5, resnapped=True, step_key="applique:1"),
    ]
    assert rehome_resnapped_regions(regions, [5, 9]) == 0
    assert regions[1].meta["layer"] == 1


def test_region_already_home_is_not_counted():
    regions = [_region("Sa", layer=0, thread=5, resnapped=True)]
    assert rehome_resnapped_regions(regions, [5]) == 0
    assert regions[0].meta["layer"] == 0


def test_repro_sews_one_block_per_spool_end_to_end():
    """The measured defect, closed: at defaults the repro's re-snaps split
    White across three layers and Fuchsia across two, sewing 4 blocks with a
    50-stitch Fuchsia revisit at 99.6% that re-enters the design's first-sewn
    territory. Rehomed, every spool sews exactly once and the palette names
    only cones that actually sew."""
    cfg = PipelineConfig(target_width_mm=80.0)
    result, plan = digitize(REPRO, cfg)

    threads = [b.thread_index for b in plan.blocks]
    assert len(threads) == len(set(threads)), (
        f"a spool is revisited across colour changes: {threads}"
    )
    # The operator's cone list and the sewn blocks agree — no cone listed
    # that nothing sews (the stale pre-rehome palette named 6 for 3 sewn).
    # Since 2026-09-04 the repro's ramp pieces sew as shade bands, each in
    # the thread its shade snapped to (`shade_thread_index` on the run), so
    # the sewn spools are the regions' cones plus exactly those shades.
    sewn = {b.thread_index for b in plan.blocks}
    region_threads = {r.thread_index for r in result.regions
                      if r.meta.get("stitched", True)}
    shade_threads = {r.shade_thread_index for _b, r in plan.iter_runs()
                     if r.shade_thread_index is not None}
    assert region_threads <= sewn
    assert sewn - region_threads <= shade_threads, sewn - region_threads


def test_flag_off_reproduces_the_split():
    """`rehome_resnapped=False` keeps the pre-2026-08-31 behaviour reachable
    and tested (the family posture `merge_adjacent_same_thread` documents):
    the repro's re-snap split comes back — one spool sewing more than one
    block — which is also the lever the sequencing A/B measured with."""
    cfg = PipelineConfig(target_width_mm=80.0, rehome_resnapped=False,
                         merge_adjacent_same_thread=False)
    _result, plan = digitize(REPRO, cfg)
    threads = [b.thread_index for b in plan.blocks]
    assert len(threads) > len(set(threads)), (
        f"expected the un-rehomed split to revisit a spool: {threads}"
    )


def test_repro_regions_sit_in_their_cones_layer():
    cfg = PipelineConfig(target_width_mm=80.0)
    result = run_stages(REPRO, cfg)
    # Layer -> the thread its regions actually sew must be one-to-one for
    # every non-step region (the repro has no steps).
    by_layer: dict[int, set[int]] = {}
    for r in result.regions:
        by_layer.setdefault(r.meta["layer"], set()).add(r.thread_index)
    threads_seen: set[int] = set()
    for layer in sorted(by_layer):
        ts = by_layer[layer]
        assert len(ts) == 1, f"layer {layer} sews {ts}"
        t = ts.pop()
        assert t not in threads_seen, f"thread {t} owns two layers"
        threads_seen.add(t)
