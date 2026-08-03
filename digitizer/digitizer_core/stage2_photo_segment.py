"""Stage 2 (photo path) — SLIC superpixels + perceptual region-merging.

Drop-in alternative to `stage2_quantize.quantize()` for photo-classified
designs (`docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-
former.md`). Same output contract (`Quant`: labels HxW int with -1
background, thread_indices, cluster_rgb, warnings) so everything downstream
— stage 3's small-region absorb, stage 4 vectorize — runs unchanged. This
stage owns segmentation quality only; nothing downstream needs to know SLIC
exists.

Why global k-means (stage2_quantize) is wrong for photos: it clusters color
independent of spatial adjacency, so a smooth photographic gradient gets
partitioned into ordered bands, and any per-pixel noise near a band boundary
flips assignment unpredictably — "dithers gradients into speckle". SLIC
first groups pixels that are BOTH close in color AND close in space (so a
superpixel never straddles a real photographic edge), then a Region
Adjacency Graph merges superpixels that are perceptually close (CIEDE2000)
regardless of where they sit in the image — consolidating a soft gradient
into a handful of clean regions instead of a per-pixel patchwork.

Pipeline, in order (the plan's 7-step contract):
  1. SLIC oversegmentation, Lab space, foreground only (`prep.bg_mask`
     excluded — same convention `stage2_quantize` uses for its own
     clustering).
  2. RAG construction (`skimage.graph.rag_mean_color`), mean color in Lab.
  3. Hierarchical merge (`skimage.graph.merge_hierarchical`) on a CIEDE2000
     edge-weight threshold (reusing `skimage.color.deltaE_ciede2000` — the
     same ΔE machinery `threads.py` and `stage6_blend.py` already import,
     not a new color-distance implementation).
  4. Min-area floor: sub-detail regions force-merge into whichever neighbor
     shares the longest boundary — literally `stage3_segment
     .resolve_small_regions`, reused rather than reinvented.
  5. Face-local threshold drop: `_face_local_threshold` — documented no-op
     for this slice (step 3's face priors don't exist yet; see the plan
     doc's "Deviations").
  6. Thread snapping: each surviving region's mean Lab color -> nearest
     thread, via the same `chart.nearest_index` call `stage2_quantize`
     makes.
  7. `Quant` output, plus the info-level `PHOTO_SEGMENT_REGION_COUNT`
     warning.

**Import path note**: `skimage.future.graph` (the source research doc's
path) does not exist in this venv's scikit-image (0.26.0) — `RAG` /
`merge_hierarchical` / `rag_mean_color` live at `skimage.graph` now. Same
functions, moved module (confirmed present before writing this module).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000
from skimage.segmentation import slic
from skimage import graph as skgraph

from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_quantize import Quant
from .stage3_segment import RegionMask, resolve_small_regions
from .threads import chart_for, rgb_to_lab
from .warnings_codes import PHOTO_SEGMENT_REGION_COUNT, warn

# --- Step 1: SLIC oversegmentation -------------------------------------------
#
# Target superpixel count. The plan's own range is 800-2000; 1200 sits in the
# middle and was what got measured against `testdata/photo/region_blobs.png`
# below — high enough that no single superpixel straddles two of the
# fixture's blobs (each ~150px radius; a superpixel at this density is a
# handful of px across), low enough that the RAG stays cheap to merge
# (measured: ~1150 foreground superpixels on the fixture, merges in well
# under a second).
SLIC_N_SEGMENTS = 1200
# Low compactness: the plan calls for irregular (not grid-like) boundaries,
# because a photographic region's true edge is whatever shape the color
# actually takes, not a hexagon. 10 is SLIC's own conservative default and
# was not worth moving — raising it visibly squared off the fixture's
# circular blobs into a honeycomb (measured, not shipped), and the final
# regions after RAG merging looked the same either way once the boundary was
# no longer a raw superpixel edge.
SLIC_COMPACTNESS = 10.0

# --- Step 3: hierarchical merge -----------------------------------------------
#
# CIEDE2000 edge-weight threshold for `merge_hierarchical`. Measured against
# `region_blobs.png`: each blob's own internal peak->edge shade sweep spans
# roughly 15-20 dE00 end to end, so a threshold near the middle of that
# range consolidates one blob's concentric shade bands into 3-4 regions
# without reaching across the (much larger, ~35-50 dE00) gap between two
# *different* blobs' hues. Swept 2/3/4/5/6/8/10/15: region count fell from
# 352 (thresh=2, barely more than raw SLIC) to 6 (thresh=15, blobs start
# visibly under-merging into flat discs, losing the shade gradient
# entirely). thresh=10 is the elbow — 12 regions pre-floor, ~4 clean bands
# per blob, no two different-hue blobs merged into each other.
MERGE_DELTAE00_THRESH = 10.0


def _merge_mean_color(g, src: int, dst: int) -> None:
    g.nodes[dst]["total color"] += g.nodes[src]["total color"]
    g.nodes[dst]["pixel count"] += g.nodes[src]["pixel count"]
    g.nodes[dst]["mean color"] = g.nodes[dst]["total color"] / g.nodes[dst]["pixel count"]


def _weight_mean_color(g, src: int, dst: int, n: int) -> dict:
    da = g.nodes[dst]["mean color"].reshape(1, 3)
    na = g.nodes[n]["mean color"].reshape(1, 3)
    return {"weight": float(deltaE_ciede2000(da, na)[0])}


def _face_local_threshold(face_regions) -> None:
    """Documented no-op (step 4 deviation #1): lowering the merge threshold
    near a detected face so eyes/mouth survive as their own regions needs
    step 3's face priors, which don't exist yet. `face_regions` is accepted
    (always `None` today) so wiring a real value in later is additive, not a
    rewrite of this module's call sites."""
    return None


def segment(p: Prep, cfg: PipelineConfig, face_regions=None) -> Quant:
    _face_local_threshold(face_regions)

    h, w = p.rgb.shape[:2]
    valid = ~p.bg_mask
    lab_img = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(h, w, 3)

    # --- 1. SLIC, foreground only -------------------------------------------
    slic_labels = slic(
        lab_img,
        n_segments=SLIC_N_SEGMENTS,
        compactness=SLIC_COMPACTNESS,
        start_label=1,
        mask=valid,
        channel_axis=-1,
        convert2lab=False,
    )
    slic_count = int(len(np.unique(slic_labels[slic_labels > 0])))

    # --- 2. RAG (Lab mean color) + 3. hierarchical merge --------------------
    if slic_count == 0:
        # Nothing foreground (fully-background image) — degenerate but
        # legal; skip straight to an all-background Quant rather than
        # calling into skimage with an empty graph.
        merged = np.zeros((h, w), np.int64)
        merged_count = 0
    else:
        # SLIC's mask convention: label 0 is every excluded (background)
        # pixel; rag_mean_color builds a node for it anyway (a "mean color"
        # of pixels that were never meant to cluster). Node 0 is
        # deliberately LEFT IN the graph here — `rag.remove_node(0)` looks
        # like the obvious guard, and was tried first, but
        # `merge_hierarchical` remaps its output by the SURVIVING nodes'
        # enumeration index, not their graph id (`for ix, (n, d) in
        # enumerate(rag.nodes(data=True))`). Remove node 0 first and
        # whichever real foreground node happens to enumerate first
        # collides with it: on `region_blobs.png`'s own sliver-fixture
        # cousin (a two-block synthetic used while tuning this), an entire
        # ~22,000px red block silently relabeled to 0 and vanished into
        # "background" (measured — see this module's test file). Background
        # identity is instead read from the `valid` mask everywhere below,
        # never from the merged label array's own 0/nonzero convention, so
        # it does not matter which numeric id background ends up wearing.
        rag = skgraph.rag_mean_color(lab_img, slic_labels, connectivity=2, mode="distance")
        merged = skgraph.merge_hierarchical(
            slic_labels,
            rag,
            thresh=MERGE_DELTAE00_THRESH,
            rag_copy=False,
            in_place_merge=True,
            merge_func=_merge_mean_color,
            weight_func=_weight_mean_color,
        )
        merged_count = int(len(set(np.unique(merged[valid]).tolist())))

    # --- 4. Min-area floor ---------------------------------------------------
    # `merge_hierarchical` only ever merges graph-adjacent nodes, but a
    # single merged label can still cover more than one connected component
    # in practice — SLIC's own small-fragment cleanup can leave a handful of
    # orphan pixels sharing a distant segment's id (measured on the
    # fixture). Splitting into true connected components here is what makes
    # `resolve_small_regions`'s bbox/halo geometry (built for one-blob-per-
    # RegionMask) meaningful, and it is the same idiom `ClassicalSegmenter`
    # already uses one stage over for the classical path — not new
    # machinery, applied one step earlier.
    regions: list[RegionMask] = []
    for lbl in sorted(set(np.unique(merged[valid]).tolist())):
        # `& valid`: a merged label id is not on its own proof of
        # foreground (see the note above) — intersecting with the real
        # background mask is what actually keeps background pixels out of
        # every RegionMask, regardless of which id they ended up wearing.
        comp_mask = ((merged == lbl) & valid).astype(np.uint8)
        n_cc, cc = cv2.connectedComponents(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            regions.append(RegionMask(mask=(cc == c), layer=0, source="photo"))

    kept, floor_warnings = resolve_small_regions(regions, cfg, p.px_per_mm)

    # --- 6. Thread snapping ---------------------------------------------------
    # (Step 5, face-local threshold, already ran as a no-op above.)
    chart = chart_for(cfg)
    region_labs = [
        rgb_to_lab(p.rgb[r.mask].reshape(-1, 3).mean(axis=0, keepdims=True))[0]
        for r in kept
    ]
    region_spools = [chart.nearest_index(lab) for lab in region_labs]

    # Same convention `stage2_quantize.quantize` ends on: dedupe regions
    # that snapped to the same spool into one final label, ordered by
    # descending total sewn area (largest color first) for determinism.
    by_spool: dict[int, list[int]] = {}
    for i, s in enumerate(region_spools):
        by_spool.setdefault(s, []).append(i)
    ordered_spools = sorted(
        by_spool.items(),
        key=lambda kv: -sum(int(kept[i].mask.sum()) for i in kv[1]),
    )

    out = np.full((h, w), -1, np.int32)
    thread_indices: list[int] = []
    for new_label, (spool, idxs) in enumerate(ordered_spools):
        thread_indices.append(spool)
        for i in idxs:
            out[kept[i].mask] = new_label

    warnings: list[dict] = list(floor_warnings)
    warnings.append(
        warn(
            PHOTO_SEGMENT_REGION_COUNT,
            f"Photo segmentation produced {len(thread_indices)} region"
            f"{'s' if len(thread_indices) != 1 else ''} "
            f"({slic_count} superpixels, {merged_count} after merging).",
            count=len(thread_indices),
            slic_segments=slic_count,
            merged_regions=merged_count,
        )
    )

    if cfg.debug_dir:
        from . import debugviz

        dbg = Path(cfg.debug_dir)
        debugviz.stage2_photo_slic(dbg, p.rgb, slic_labels)
        mean_rgb = {
            new_label: tuple(int(v) for v in chart[spool].rgb)
            for new_label, (spool, _idxs) in enumerate(ordered_spools)
        }
        debugviz.stage2_photo_merged(dbg, p.rgb, out, mean_rgb)
        debugviz.stage2_photo_regions(
            dbg, slic_count, merged_count, len(thread_indices),
            [int((out == lbl).sum()) for lbl in range(len(thread_indices))],
        )

    return Quant(
        labels=out,
        thread_indices=thread_indices,
        cluster_rgb=np.array([chart[s].rgb for s in thread_indices], np.float64),
        warnings=warnings,
    )
