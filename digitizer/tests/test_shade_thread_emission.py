"""A gradient region whose blend tier accepts N shades must sew N color
blocks, not one. Repro of MASTER_SCOPE's 'every shade sews in one thread'
defect: gradient_ramp_linear.png accepts 4 shades and sewed 2 blocks.

Call shape confirmed against `digitizer_core/pipeline.py` (Step 1 read):
`run_stages` returns a `PipelineResult` with no `.design` attribute — the
stitch plan (and its `.blocks`) comes from `plan_stitches`, or from the
`digitize()` convenience wrapper that returns `(PipelineResult, StitchPlan)`
in one call, the idiom every other real-fixture test in this suite already
uses (see test_flat_lane_byte_identical.py, test_shape_overrides.py, etc.).

Review round 1 added the two unit tests below, directly against
`_shade_blocks` and `_chain`: the job-level test above proves shade
partitioning fires on real artwork, but the committed fixture's own 4 bands
stay chart-index-contiguous (each of its 4 emitted blocks is a single run),
and `chain_links` defaults False, so neither the same-cone rejoin recompute
nor `_chain`'s shade guard was ever actually exercised by the suite. Both
are unit-level on purpose: the job-level path cannot control either input
precisely enough to hit them deliberately.
"""
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, fabric_for_garment, stitches
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import _chain, _shade_blocks, sequence
from digitizer_core.stitches import StitchRun
from digitizer_core.threads import CHART

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
FIXTURE = TESTDATA / "photo" / "gradient_ramp_linear.png"


def test_accepted_shades_become_color_blocks():
    cfg = PipelineConfig()  # defaults: gradient class routes to blend tier
    _result, plan = digitize(FIXTURE, cfg)
    # The ramp's blend decomposition accepts 4 shades (measured 2026-08-15,
    # docs/blend-tier-never-fires-2026-08-15.md). Distinct thread indexes
    # across the plan's emitted stitch blocks must reflect them.
    distinct = {b.thread_index for b in plan.blocks}
    assert len(distinct) >= 3, (
        f"4-shade ramp sewed {len(distinct)} thread(s) — shade snap not read")


# --- Unit coverage for _shade_blocks' same-cone rejoin recompute -----------

def test_shade_blocks_rejoins_a_same_cone_band_and_recomputes_its_seam():
    """`_choose_shade_count`/`_shade_lab_colors` (stage6_blend.py:471-488)
    build each band's average Lab color independently by nearest-t bucket,
    then each band snaps to a chart cone independently via
    `chart.nearest_index` — nothing enforces a monotonic chart index across
    bands, so two NON-ADJACENT bands can land on the same cone. The
    committed gradient_ramp_linear.png fixture happens to stay contiguous
    (each of its 4 emitted blocks is a single run), so this path needs a
    hand-built A-B-A shade_thread_index sequence — no new image fixture.

    band0 and band2 both snap to shade A; band1 (between them in `ordered`'s
    own spatial/band order) snaps to shade B. Proves three things
    `_shade_blocks` must get right:
      - partition membership: shade A's block holds BOTH band0 and band2,
        not just band0 (a plain contiguous split would drop band2 into its
        own third block, or misfile it under `base_thread`);
      - order: shade A before shade B, purely by chart L*, regardless of
        which one happened to be first in the flat band order;
      - the seam recompute: band2's jump/trim, exactly as stage 6 would
        have left them (stamped against distance to its FLAT neighbour
        band1, ~49mm away — a real cut), answer the wrong question once
        band1 is pulled into its own block. The real neighbour is band0,
        0.02mm away, and the recompute must find that and clear the stale
        cut rather than leave it or hand it back to `_chain` (these two
        runs were never flat-adjacent, so `_chain` never even saw them as a
        pair).
    """
    chart = CHART
    # Two real chart cones, found by their own L* rather than hardcoded —
    # if the chart ever changes, the fixture still asks the right question
    # (mirrors test_photo_sequencing.py's DARK/LIGHT picks).
    a, b = sorted(range(len(chart)), key=lambda i: chart.lab[i][0])[:2]
    if chart.lab[a][0] == chart.lab[b][0]:
        pytest.skip("chart has no two distinct L* values to order by")

    def run(x0, x1, shade):
        return StitchRun(points=[(x0, 0.0), (x1, 0.0)], shape_id="ramp",
                         shade_thread_index=shade)

    band0 = run(0.0, 1.0, a)      # shade A, opens the flat sequence
    band1 = run(50.0, 51.0, b)    # shade B, far away — its own block
    band2 = run(1.02, 2.0, a)     # shade A again, 0.02mm from band0's end
    # band2's own flags exactly as a same-shade-boundary jump stamped
    # against its FLAT neighbour band1 would read: a real, ~49mm cut.
    band2.jump = True
    band2.trim = True

    blocks = _shade_blocks([band0, band1, band2], base_thread=a,
                           chart=chart, trim_at=3.0)

    # Order: dark (a) before light (b) — exactly two blocks, not three.
    assert [blk.thread_index for blk in blocks] == [a, b]

    # Partition membership: shade A's block is band0 THEN band2, in that
    # order; shade B's block is band1 alone.
    shade_a_block, shade_b_block = blocks
    assert shade_a_block.runs[0] is band0
    assert shade_a_block.runs[1] is band2
    assert len(shade_a_block.runs) == 2
    assert shade_b_block.runs == [band1]

    # Boundary flags: every block's own first run opens on a real cut.
    assert band0.jump and band0.trim
    assert band1.jump and band1.trim

    # The rejoin recompute actually fired: band0 -> band2 is 0.02mm, far
    # under TINY_STITCH_MM (0.5mm), so band2 must no longer carry the stale
    # jump/trim it arrived with (which answered "how far to band1", not
    # "how far to band0").
    assert not band2.jump and not band2.trim, (
        "rejoin recompute did not fire against the real (band0) neighbour")


# --- Unit coverage for _chain's shade-boundary guard ------------------------

def test_chain_refuses_to_bridge_a_shade_boundary():
    """`_chain`'s shade guard (`out[-1].shade_thread_index !=
    run.shade_thread_index`, both sides normalized against `base_thread`
    the same way `_shade_blocks` buckets — F7, 2026-08-19): untested by the
    committed suite before this — `chain_links` defaults False
    (`PipelineConfig`) and no committed fixture combines it with a
    blend-routed region, so the guard's `!=` branch never actually ran
    under pytest, even though it is provably inert for every existing
    design (every run's `shade_thread_index` is `None` there).

    Built directly against `_chain`, on the smallest input that lets it try
    to bridge at all — the same shape `test_chaining.py`'s own
    `test_a_gap_a_later_colour_covers_is_sewn_not_cut` uses: two same-colour
    bars 6mm apart, a third, later-sewn shape fully covering the gap, so
    geometry alone says a bridge is legal. `chain_links=False` builds the
    block so the boundary is still a plain, un-chained `jump=True`, then
    `_chain` runs exactly once, directly — so the guard is the only thing
    that can explain a difference between the cases below.
    """
    fabric = fabric_for_garment("left_chest")

    def region(poly, layer, name, thread):
        return Region(shape_id=name, polygon=poly, thread_index=thread,
                     thread_number=f"{1000 + thread}", area_mm2=poly.area,
                     meta={"layer": layer, "tier": "fill"})

    def bar(x0, x1):
        return Polygon([(x0, 0), (x1, 0), (x1, 10), (x0, 10)])

    def unchained_boundary():
        regions = [region(bar(0, 10), 0, "Sleft", 0),
                   region(bar(16, 26), 0, "Sright", 0),
                   region(Polygon([(10, 0), (16, 0), (16, 10), (10, 10)]),
                          1, "Sbridge", 1)]
        conf = PipelineConfig(garment_id="left_chest", chain_links=False)
        planned, _ = resolve_overlaps(regions, fabric, conf)
        blocks, _ = sequence(planned, fabric, conf)
        sewn = [p for p in planned if p.sew_index == 0]
        runs = list(blocks[0].runs)
        for i, r in enumerate(runs):
            if i and r.shape_id == "Sright" and runs[i - 1].shape_id == "Sleft":
                assert r.jump and r.trim, "fixture sanity: starts as a plain cut"
                return runs, sewn
        raise AssertionError("never found the Sleft->Sright boundary")

    def crossing(left_shade, right_shade):
        runs, sewn = unchained_boundary()
        base_thread = sewn[0].region.thread_index
        for r in runs:
            if r.shape_id == "Sleft":
                r.shade_thread_index = left_shade
            elif r.shape_id == "Sright":
                r.shade_thread_index = right_shade
        out, _linked = _chain(runs, sewn, base_thread, None)
        for i, r in enumerate(out):
            if i and r.shape_id == "Sright" and out[i - 1].shape_id != "Sright":
                return out[i - 1], r
        raise AssertionError("never found the crossing in chained output")

    # Control: identical shade on both sides still bridges, same as any
    # ordinary same-colour gap (proves the guard isn't just refusing
    # everything).
    _prev_same, cross_same = crossing(5, 5)
    assert not cross_same.jump and not cross_same.trim, (
        "a same-shade gap under full cover should still chain")

    # F7: `None` (the pre-blend default carried by every run that never
    # went through the blend tier) against the group's own explicit base
    # thread must normalize to the SAME key `_shade_blocks` buckets it
    # under, and bridge — not refuse. Before the fix `_chain` compared
    # `None != base_thread` raw and cut a gap that costs nothing to bury,
    # a needless trim on every ordinary, non-blend design chaining ever
    # touches (every such run's `shade_thread_index` is `None` on one or
    # both sides of *some* boundary the moment even one run in the group
    # carries an explicit `base_thread` tag).
    _runs0, _sewn0 = unchained_boundary()
    base_thread = _sewn0[0].region.thread_index
    _prev_none, cross_none = crossing(None, base_thread)
    assert not cross_none.jump and not cross_none.trim, (
        "None (pre-blend default) must normalize to base_thread and bridge "
        "like any other same-shade gap under full cover")

    # The guard: different shade, identical geometry, must refuse.
    _prev_diff, cross_diff = crossing(5, 7)
    assert cross_diff.kind != stitches.TRAVEL, (
        "a shade-boundary link would be sewn in the wrong thread")
    assert cross_diff.jump and cross_diff.trim, (
        "a shade boundary must stay a cut even though geometry covers it")
