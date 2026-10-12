"""Stage 4 keeps ONE outer contour per mask — the largest (`vectorize`'s
`outer = max(outers, ...)`). That drops ink only if a mask reaching stage 4
holds two separate islands, and stage 3 never builds one: every mask is a
`connectedComponentsWithStats(connectivity=8)` component, and the one place
a mask grows (`RegionMask.union_from`, `resolve_small_regions` absorbing a
sliver) unions it with a neighbour its 3x3 halo touches — 8-adjacent, so
still one component, which `findContours` traces as one outer border.

Measured 2026-10-12 (`tools/stage4_contours.py`, PR body): 0 multi-island
masks of 7,106 over every corpus_scorecard FIXTURE (26) x MATRIX row (2) at
the default colour count and at the Studio's 6 — 104 generations. These tests pin the two halves of that: the
latent drop is real for a mask that DOES carry two islands (and the census
sees it), and the stage-3 invariant that keeps it latent holds where it is
easiest to break — a sliver touching its absorber only at a corner — and on
a real fixture end to end.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage2_quantize import Quant
from digitizer_core.stage3_segment import ClassicalSegmenter, RegionMask, resolve_small_regions
from digitizer_core.stage4_vectorize import vectorize
from tools.stage4_contours import census_masks, floor_mm2

PPM = 10.0


def _prep(h: int, w: int) -> Prep:
    return Prep(rgb=np.zeros((h, w, 3), np.uint8), bg_mask=np.zeros((h, w), bool),
                px_per_mm=PPM, art_bbox=(0, 0, w, h))


def _two_islands() -> np.ndarray:
    mask = np.zeros((100, 100), bool)
    mask[10:50, 10:50] = True        # 16.0 mm² — the island stage 4 keeps
    mask[70:85, 70:85] = True        # 2.25 mm² — above the 0.5625 mm² floor, dropped
    return mask


def test_two_island_mask_sews_only_the_largest():
    """The latent drop, pinned: a mask with two islands of one colour comes
    out of stage 4 as ONE region, the smaller island gone with no warning
    and no `dropped` entry (only a whole mask vanishing is reported)."""
    p, cfg = _prep(100, 100), PipelineConfig()
    regions, dropped = vectorize([RegionMask.from_full(_two_islands(), layer=0)], [0], p, cfg)
    assert len(regions) == 1 and dropped == []
    assert regions[0].area_mm2 == pytest.approx(16.0, rel=0.1)
    assert regions[0].polygon.bounds[0] < 0          # the upper-left island, in mm about the centre


def test_census_reports_the_dropped_island():
    p, cfg = _prep(100, 100), PipelineConfig()
    masks = [RegionMask.from_full(_two_islands(), layer=0)]
    regions, _ = vectorize(masks, [0], p, cfg)
    c = census_masks(masks, p, cfg, regions)
    assert c["masks"] == 1 and len(c["multi"]) == 1
    m = c["multi"][0]
    assert m["outers"] == 2
    assert [s["area_mm2"] for s in m["islands"]] == [16.0, 2.25]   # exact pixel counts
    assert m["dropped_mm2"] == 2.25
    assert m["dropped_above_floor_mm2"] == 2.25 and 2.25 > floor_mm2(cfg)
    dropped = [s for s in m["islands"] if not s["kept"]][0]
    assert dropped["claimed"] is False                # no region covers it: preflight's blind spot
    assert m["unclaimed_above_floor"] == 1


def test_census_is_silent_on_a_single_island():
    p, cfg = _prep(100, 100), PipelineConfig()
    one = np.zeros((100, 100), bool)
    one[10:50, 10:50] = True
    one[20:30, 20:30] = False                         # a hole is not a second island
    c = census_masks([RegionMask.from_full(one, layer=0)], p, cfg)
    assert c["multi"] == []


def test_absorption_across_a_corner_keeps_one_island():
    """The invariant that keeps the drop latent, at its weakest point: a
    sliver touching the shape it is absorbed into ONLY diagonally. The 3x3
    halo reaches it, so it is absorbed, and the union is still one
    8-connected component — one outer contour, nothing for stage 4 to drop."""
    labels = np.full((80, 80), -1, np.int32)
    labels[10:50, 10:50] = 0                          # the absorber
    labels[50:53, 50:53] = 1                          # 9 px sliver, corner to corner
    q = Quant(labels=labels, thread_indices=[0, 1], cluster_rgb=np.zeros((2, 3)))
    p, cfg = _prep(80, 80), PipelineConfig()
    masks = ClassicalSegmenter().segment(q, p, cfg)
    assert len(masks) == 2
    kept, _w = resolve_small_regions(masks, cfg, PPM, None)
    assert len(kept) == 1 and kept[0].area == 40 * 40 + 9, "the sliver must have been absorbed"
    assert census_masks(kept, p, cfg)["multi"] == []


def test_corpus_masks_reach_stage4_as_single_islands():
    """End to end on real artwork with absorption in it: every mask the
    pipeline hands stage 4 is one island. If this goes red, stage 3 has
    started building multi-island masks and `vectorize` is dropping every
    island but the largest — run `tools/stage4_contours.py --scorecard`."""
    from tools.stage4_contours import run
    r = run("photo/enthusiast_logo.png", {"target_width_mm": 80.0, "garment_id": "left_chest"})
    assert r["masks"] > 10
    assert r["multi"] == [], r["multi"]
