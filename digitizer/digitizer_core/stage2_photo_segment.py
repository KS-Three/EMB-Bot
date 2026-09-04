"""Stage 2 (photo path) — SEEDS superpixels + perceptual region-merging.

Drop-in alternative to `stage2_quantize.quantize()` for photo-classified
designs (`docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-
former.md`). Same output contract (`Quant`: labels HxW int with -1
background, thread_indices, cluster_rgb, warnings) so everything downstream
— stage 3's small-region absorb, stage 4 vectorize — runs unchanged. This
stage owns segmentation quality only; nothing downstream needs to know
which superpixel algorithm exists behind it.

**SLIC -> SEEDS, retuned 2026-08-07** (this pass): the oversegmentation
step was `skimage.segmentation.slic` from this module's original build
through 2026-08-06. A standalone benchmark isolating the superpixel
algorithm as the only variable (SLIC vs. `cv2.ximgproc.
createSuperpixelSEEDS`, every downstream step — RAG construction, area-
ratio protection, merge, CC split, min-area floor — held byte-identical)
found SEEDS produces measurably tighter boundaries on real busy fixtures
(`drone_render.png`, `summit_badge.png`) at matched region counts. Swapped
in, with `MERGE_DELTAE00_THRESH` retuned to match (see that constant's own
docstring for the full sweep) — the old SLIC-era sweep table lower in this
file is kept only as the historical record of how the PRIOR threshold was
chosen, not something to re-derive from. Internal identifiers
(`slic_labels`, `slic_count`, the `slic_segments` warning field) keep their
original names deliberately — `slic_segments` is a warning-schema field
other code may already read by name, and the local variables are just
"whatever the oversegmentation step produced", true regardless of which
algorithm is behind them.

Why global k-means (stage2_quantize) is wrong for photos: it clusters color
independent of spatial adjacency, so a smooth photographic gradient gets
partitioned into ordered bands, and any per-pixel noise near a band boundary
flips assignment unpredictably — "dithers gradients into speckle". SEEDS
first groups pixels that are BOTH close in color AND close in space (so a
superpixel never straddles a real photographic edge), then a Region
Adjacency Graph merges superpixels that are perceptually close (CIEDE2000)
regardless of where they sit in the image — consolidating a soft gradient
into a handful of clean regions instead of a per-pixel patchwork.

Pipeline, in order (the plan's 7-step contract):
  1. SEEDS oversegmentation, Lab space, foreground only (`prep.bg_mask`
     excluded — same convention `stage2_quantize` uses for its own
     clustering; SEEDS itself has no native mask parameter, so the module
     runs it over the whole canvas and zeroes non-foreground pixels
     afterward — see `_seeds_superpixels`'s own docstring for the
     foreground-density compensation this requires).
  2. RAG construction (`skimage.graph.rag_mean_color`), mean color in Lab.
  3. Hierarchical merge (`skimage.graph.merge_hierarchical`) on a CIEDE2000
     edge-weight threshold (reusing `skimage.color.deltaE_ciede2000` — the
     same ΔE machinery `threads.py` and `stage6_blend.py` already import,
     not a new color-distance implementation), with two local threshold
     tightenings applied on top of the one global threshold: the small-vs-
     large area-ratio guard (`AREA_RATIO_PROTECT_THRESH`) and, added
     2026-08-07, the boundary-contrast guard (`BOUNDARY_CONTRAST_HARD_LAB`)
     that resolved this module's own SEEDS-era `summit_badge.png`
     regression. Both are independent and compose; see each constant's own
     docstring. The merge compares region MEAN colors, which is blind to
     whether two regions physically meet across a step edge or a smooth
     ramp — the boundary-contrast guard is what supplies that missing
     information, measured once per superpixel pair up front (~31 ms on a
     900x900 / 1,072-superpixel fixture) and carried through merges as a
     length-weighted sum.
  4. Min-area floor: sub-detail regions force-merge into whichever neighbor
     shares the longest boundary — literally `stage3_segment
     .resolve_small_regions`, reused rather than reinvented.
  5. Face-local threshold drop: `_face_local_threshold` — REAL as of
     2026-08-04 (YuNet face priors, `stage1_photo_prep.detect_faces_seam`):
     edges touching a detected face's ellipse merge against a locally
     halved threshold so eyes/mouth survive as their own regions. No
     detections (or no detector) = the pre-face-priors path, bit for bit.
  6. Palette selection: chart-restricted weighted k-medoids over the
     surviving regions' mean Lab colors (`palette.select_palette` —
     technique-menu row 13, build-order step 7), region weight = area ×
     class multiplier via `palette.region_weight`. Region CLASSES: "eyes"
     and "skin" come from the YuNet face priors via `_region_classes`
     (real as of 2026-08-04); "subject"/"background" are ALSO real now
     (wired 2026-08-05, see `_region_classes`' docstring) whenever
     `remove_background_seam` actually ran and produced a real mask this
     run — a non-face region majority-inside that mask classes
     "background", otherwise "subject". No real rembg mask (flag off, or
     it degraded to its no-op fallback) means every non-face region still
     stays class None and weighs plain area, exactly the prior behaviour.
     Before step 7 this line was a per-region `chart.nearest_index` snap,
     which scattered a multi-shade ramp across near-duplicate spools from
     different families — the measured before/after lives in `palette.py`'s
     docstring.
  7. `Quant` output, plus the info-level `PHOTO_SEGMENT_REGION_COUNT`
     (`count` = real region count, `thread_colors` = palette size — fixed
     2026-08-04, see that warning's own inline comment) and
     `PHOTO_PALETTE_SELECTED` warnings.

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
from skimage import graph as skgraph

from .config import PipelineConfig
from .palette import region_weight, select_palette
from .stage1_prep import Prep
from .stage2_quantize import Quant, _quantize_population
from .stage3_segment import RegionMask, resolve_small_regions
from .threads import chart_for, rgb_to_lab
from .warnings_codes import (PHOTO_BLEND_DISSOLVED, PHOTO_PALETTE_SELECTED,
                             PHOTO_SEGMENT_REGION_COUNT, PHOTO_SHADE_DEMAND,
                             TONAL_REGIONS_SPLIT, warn)

# --- Step 1: SEEDS oversegmentation -------------------------------------------
#
# Target FOREGROUND superpixel count. The plan's own range is 800-2000 (the
# figure SLIC's own `n_segments` used to be handed directly); 1200 sits in
# the middle, same figure the SLIC era shipped. `cv2.ximgproc.
# createSuperpixelSEEDS` has no mask parameter — see `_seeds_superpixels`'s
# docstring for why this constant is a target for the FOREGROUND superpixel
# count, not the raw `num_superpixels` argument SEEDS itself is constructed
# with (that argument is scaled up by `_seeds_superpixels` to compensate for
# whatever fraction of the canvas is background).
SEEDS_TARGET_FG_SUPERPIXELS = 1200

# Floor on the foreground-area fraction used to scale the SEEDS request —
# bounds the requested count (and so runtime/memory) when the foreground is
# a tiny sliver of the canvas. Below this floor, the scaling stops keeping
# pace with a shrinking foreground and `SEEDS_MAX_REQUESTED_SUPERPIXELS`
# becomes the effective limiter instead.
SEEDS_MIN_FG_FRAC = 0.05

# Hard cap on the raw `num_superpixels` SEEDS is constructed with, regardless
# of how small the foreground fraction is — a second, independent bound
# alongside `SEEDS_MIN_FG_FRAC` (belt and suspenders: the frac floor bounds
# the scale factor, this bounds the product). Measured: `drone_render.png`
# (18.5% foreground, the smallest fraction of any fixture this module is
# tested against) needs a request of ~6,500 to land ~1,600 real foreground
# superpixels and completes in ~2s; 20,000 gives comfortable headroom for a
# busier real photo with a smaller subject before either bound engages.
SEEDS_MAX_REQUESTED_SUPERPIXELS = 20000

# `num_levels`: SEEDS' own block-hierarchy depth (see `createSuperpixelSEEDS`
# docs) — more levels refine the grid-to-boundary fit further at more CPU/
# memory cost. `prior`: 3x3 shape-smoothing strength, range [0, 5]. Both left
# at OpenCV's own commonly-used sample defaults — the benchmark that
# motivated this swap isolated the ALGORITHM (SEEDS vs. SLIC) as its one
# variable and measured a boundary-precision win at these defaults; this
# module's own retuning effort (below, `MERGE_DELTAE00_THRESH` and the
# area-ratio family) targets the RAG-merge stage that consumes SEEDS' output,
# not SEEDS' own internal knobs, which were not swept separately.
SEEDS_NUM_LEVELS = 4
SEEDS_PRIOR = 2
SEEDS_HISTOGRAM_BINS = 5
SEEDS_DOUBLE_STEP = True
SEEDS_NUM_ITERATIONS = 10

# --- Step 3: hierarchical merge -----------------------------------------------
#
# CIEDE2000 edge-weight threshold for `merge_hierarchical`.
#
# **Retuned 2026-08-04** (`docs/superpowers/plans/2026-08-03-gradient-tier-
# fragmentation-and-enclosed-white-defects.md`, "Direction 1" + "Direction
# 3"): the value below was tuned only against `region_blobs.png`'s
# synthetic within-blob shade structure (see the superseded note beneath
# this one) and was never validated against a real ramp before this pass —
# its own prior docstring said so. Once "gradient"-classified designs
# started routing through this module (see `pipeline.run_stages`'s stage 2
# dispatch), that gap became load-bearing: a quality audit ran the real
# pipeline on `testdata/photo/drone_render.png` (a busy, photo-realistic
# commissioned logo, not a toy fixture) and found `thresh=10.0` still
# produced 153-196 regions — far outside the plan's own 20-80 accept band
# (F4 criteria), just a smaller miss than plain k-means's 192-231.
#
# Swept 10/15/18/19/20/22/25/30 on TWO independent real busy fixtures —
# `drone_render.png` and `testdata/photo/summit_badge.png` (a second,
# unrelated commissioned-style multi-gradient badge built for this pass
# specifically because no other real gradient-classified fixture in this
# repo has drone_render's complexity — see that file's own header comment
# in the test suite for how/why it was built) — through the FULL pipeline
# (`pipeline.run_stages`, stages 1-4: `len(PipelineResult.regions)`, the
# same "final shapes" metric the plan doc's own F4 acceptance criteria and
# the quality audit both count against, not a stage-2-only proxy):
#
#     thresh   drone_render  summit_badge
#     10.0     174           84
#     15.0     119           53
#     18.0      70           36
#     19.0      67           33
#     20.0      65           30
#     22.0      62           27
#     25.0      58           26
#     30.0      47           19  <- summit_badge falls below the 20-region floor
#
# 20.0 is the smallest threshold that lands BOTH fixtures inside [20, 80]
# with real headroom on both sides (drone_render: 65, 15 clear of the
# ceiling; summit_badge: 30, 10 clear of the floor) — also the same value
# the audit's own single-fixture sweep on drone_render alone had already
# flagged as "lands inside the accept band", now confirmed on a second,
# structurally independent fixture (and against the full pipeline, not
# just stage 2) rather than trusted from one data point or one stage.
# 30.0 was rejected specifically because it pushes summit_badge (19) OUT of
# the accept band on its low side — proof the sweep is finding a real
# two-sided elbow, not just picking the highest threshold that still "looks
# okay" on the one fixture with the most room to spare. Simple ramps
# (`gradient_ramp_linear.png`, `gradient_ramp_radial.png`, both genuinely
# 2 final regions at every threshold tried — see the regression tests) and
# the enclosed-white-icon repro (`repro_gradient_white_icon.png`, 23 final
# regions at 20.0, its 4 enclosed-icon shapes among them — see the
# `_quantize_population` enclosed-population split above `segment()`, added
# this same pass, without which they silently stopped being their own
# regions at all) do NOT over-merge into fewer regions than their real
# content needs; see the regression tests pinning both.
#
# **Superseded 2026-08-07 by the SLIC -> SEEDS swap below — kept for the
# historical record of how 20.0 was chosen under SLIC; do not re-derive from
# this table, the numbers no longer apply to the shipped code.**
#
# **Retuned 2026-08-07 for SEEDS** (this module's superpixel step swapped
# `skimage.segmentation.slic` for `cv2.ximgproc.createSuperpixelSEEDS` — see
# the module docstring and `_seeds_superpixels`'s own docstring for the full
# story). SEEDS' raw output at the SAME 20.0 threshold FRAGMENTS worse than
# SLIC did on both real busy fixtures — drone_render.png 65 -> 106 regions,
# summit_badge.png 30 -> 42 — the opposite of the standalone benchmark's own
# "SEEDS needs LESS aggressive merging" framing; measured directly, the
# threshold had to move UP, not down, to reach the same accept band. Swept
# 18/20/22/24/26/28/30/32/35 on the same two fixtures, same methodology
# (`pipeline.run_stages`, `len(PipelineResult.regions)`, full pipeline not
# stage-2-only):
#
#     thresh   drone_render  summit_badge
#     18.0     117           43
#     20.0     106           42
#     22.0      78           39
#     24.0      78           39
#     26.0      74           39
#     28.0      72           38
#     30.0      72           38
#     32.0      68           38
#     35.0      64           36
#
# Two real differences from the SLIC-era sweep, both consistent with SEEDS
# genuinely producing cleaner boundaries on this content, not just a shifted
# elbow: (1) summit_badge stays comfortably clear of the 20-region floor
# across the ENTIRE swept range (36-43), never approaching it the way it did
# under SLIC (19 at thresh=30, the reason 30.0 was rejected there) — a
# higher threshold no longer trades fragmentation-fixing for content loss on
# this fixture's OWN region-count signal (see AREA_RATIO_PROTECT_THRESH's
# docstring below for a real content-loss failure this signal does NOT
# catch); (2) drone_render's curve is flatter and takes longer to clear the
# 80-ceiling with real margin (78 at 22.0-24.0, only 2 clear) than SLIC's
# equivalent curve did. 26.0 is chosen: the smallest threshold in the swept
# set past the 22.0/24.0 plateau with real headroom on the tighter fixture
# (drone_render: 74, 6 clear of the 80 ceiling) while summit_badge (39) sits
# nowhere near either band edge — mirroring the original selection's own
# "smallest threshold with headroom on both sides" rule, adapted to SEEDS'
# flatter curve (22.0/24.0 were rejected for having almost no margin on
# drone_render's side; going past 26.0 bought steadily less additional
# margin on drone_render for no measurable benefit elsewhere).
#
# Gradient-ramp over-segmentation risk (flagged going into this pass as
# SEEDS' extra boundary sensitivity could fragment a smooth 2-color ramp
# that should stay one region) — measured directly, NOT assumed: swept the
# same threshold range against `gradient_ramp_linear.png` and `gradient_
# ramp_radial.png` through the full pipeline. Both stayed at or under their
# SLIC-era counts at every threshold tried (linear: 2 regions at 20-35;
# radial: 2 at 20-26, dropping to 1 at 30-35, still inside the tests' own
# >=1 floor) — the flagged risk did NOT materialize; if anything, the higher
# threshold this retune needed for drone_render's sake makes ramp
# over-segmentation LESS likely, not more.
MERGE_DELTAE00_THRESH = 26.0

# Superseded 2026-08-04, kept for the historical record (do not re-derive
# from this number): the ORIGINAL measurement below only ever exercised
# `region_blobs.png`'s synthetic within-blob shade sweep, never a real
# gradient design.
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


def _seeds_superpixels(rgb: np.ndarray, base_valid: np.ndarray) -> np.ndarray:
    """Step 1: `cv2.ximgproc.createSuperpixelSEEDS`, foreground only —
    SEEDS' replacement for `skimage.segmentation.slic(..., mask=base_valid)`.

    Produces a label array in the SAME convention the rest of this module
    (and `debugviz`) already expects from the SLIC era: 0 = excluded
    (background or enclosed), 1..N = superpixel id, every excluded pixel
    reading exactly 0. Not necessarily CONTIGUOUS 1..N (some ids may only
    ever have covered excluded pixels and so never appear post-mask) —
    the same non-guarantee SLIC's own masked output already had, and
    nothing downstream (`np.unique(...[...>0])`, `bincount` sized off
    `.max()+1`) assumes contiguity.

    **No native mask, unlike `slic`**: `createSuperpixelSEEDS` has no mask
    parameter — it always segments whatever canvas it is handed. Masking
    happens AFTER `iterate()`: excluded pixels are zeroed in the output
    regardless of what raw id SEEDS gave them.

    **Cropped to the foreground bounding box first — found necessary, not
    just an optimization** (2026-08-07): an earlier version of this function
    ran SEEDS over the FULL h x w canvas (background included) and masked
    afterward. That reproduced `test_min_area_floor_absorbs_a_tiny_sliver`
    as a real failure, not a fixture-tuning issue: on that fixture (a small
    18x18px foreground sliver sitting mostly on open background, ~64%
    foreground globally), most of the sliver's own pixels got absorbed into
    a neighboring background-dominated SEEDS block before the mask was ever
    applied — SEEDS' grid-based block growth doesn't stay inside foreground
    territory the way SLIC's masked clustering does, so a thin, small,
    background-adjacent feature can lose most of its extent to a
    background-majority superpixel that never becomes its own RAG node.
    What survived post-mask was a scattered ~45px remnant instead of the
    fixture's drawn 324px — proof this was a real boundary-fidelity
    regression on isolated small foreground content, not a threshold or
    constant that needed retuning. Cropping to the foreground's own bounding
    box before calling SEEDS fixes it directly: within the crop, foreground
    density is always >= the whole-canvas density (measured: `drone_render.
    png` 18.5% globally -> 47.6% within its own bbox; the sliver fixture
    96%+ within its bbox, since the bbox is dominated by the two big flat
    blocks the sliver sits between) — background gets far less of SEEDS'
    grid to claim, so a small foreground feature is far less likely to be
    swallowed by a background-majority block before the mask ever runs (the
    fixture's own regression is fixed by this crop alone, confirmed by the
    regression test in this module's test file). A crop can still contain
    SOME background (an irregular/concave foreground shape's bbox is not
    100% foreground) — the post-`iterate()` masking step above is what
    still handles that residue, exactly as it did pre-crop.

    **`cv2`'s own uint8 Lab, not `threads.rgb_to_lab`'s skimage float64
    Lab — found necessary, not a style choice** (2026-08-07): the first
    working version of this function fed SEEDS this module's existing
    skimage Lab (`rgb_to_lab`, full `float64` precision, the same array the
    RAG/merge machinery downstream needs). That SEGFAULTS `seeds.iterate()`
    — reproduced deterministically, isolated to content, not shape or
    superpixel count (a same-size random-noise array never crashed; the
    real `gradient_ramp_linear.png` crop crashed at every `num_superpixels`
    and `num_levels` tried, including the smallest) — on any image whose
    a*/b* channels span an unusually NARROW range, exactly what a clean
    2-color gradient's Lab representation looks like (measured range on the
    crashing crop: a* only -7.2..-2.1, b* only -23.0..-13.2, both under 10
    units wide against skimage Lab's full a*/b* domain). Root cause not
    fully bisected past that point (this is `cv2.ximgproc`'s own C++
    histogram-binning code, not this repo's), but the practical fix is
    clean: convert to `cv2.cvtColor(..., COLOR_RGB2Lab)` — OpenCV's own
    uint8 Lab convention (L/a*/b* all rescaled into 0-255), the color space
    its own docs recommend and presumably what its own test suite actually
    exercises — SOLELY for this function's own SEEDS call. Confirmed this
    does not reproduce the crash on the same crop, at the same request
    count, with the same `num_levels`. `lab_img` (skimage, full-precision)
    stays exactly what `rag_mean_color`/`merge_hierarchical`/
    `deltaE_ciede2000` use for everything downstream — this function reads
    `rgb` instead and computes its own SEEDS-only Lab locally, so this
    workaround cannot leak imprecision into the perceptual merge math.

    **Foreground-density compensation**: SEEDS' `num_superpixels` argument
    requests a count over the WHOLE crop, not the foreground alone — see
    above for why a photo's foreground can still be well under 100% of its
    own bbox. This function requests
    `SEEDS_TARGET_FG_SUPERPIXELS / max(bbox_fg_frac, SEEDS_MIN_FG_FRAC)`,
    capped at `SEEDS_MAX_REQUESTED_SUPERPIXELS`, so the count that actually
    lands on foreground pixels tracks the same ~1200 density SLIC's masked
    computation always targeted. Measured on the real fixtures (bbox
    fg_frac, requested -> actual foreground superpixel count):
    `drone_render.png` (0.476, 2519 -> 982), `summit_badge.png` (0.795,
    1510 -> 1072), `gradient_ramp_linear.png` (1.0, 1200 -> 735),
    `gradient_ramp_radial.png` (0.786, 1527 -> 832), `region_blobs.png`
    (0.661, 1815 -> 774) — all landing in the same several-hundred-to-
    low-thousands band the SLIC era's own ~1150-on-region_blobs measurement
    was in (SEEDS' own block-hierarchy quantizes the achievable count more
    coarsely than SLIC's k-means-style target, so `actual` consistently
    lands somewhat under `requested` here — expected, not a bug; `_seeds_
    superpixels` never depends on hitting the request exactly, only on
    landing in the right order of magnitude).
    """
    h, w = base_valid.shape
    out = np.zeros((h, w), np.int64)
    if not base_valid.any():
        return out
    ys, xs = np.where(base_valid)
    y0, y1 = int(ys.min()), int(ys.max()) + 1
    x0, x1 = int(xs.min()), int(xs.max()) + 1
    crop_valid = base_valid[y0:y1, x0:x1]
    crop_lab = cv2.cvtColor(np.ascontiguousarray(rgb[y0:y1, x0:x1], dtype=np.uint8), cv2.COLOR_RGB2Lab)
    bbox_fg_frac = float(crop_valid.mean())
    requested = int(round(SEEDS_TARGET_FG_SUPERPIXELS / max(bbox_fg_frac, SEEDS_MIN_FG_FRAC)))
    requested = max(1, min(requested, SEEDS_MAX_REQUESTED_SUPERPIXELS))
    ch, cw = crop_valid.shape
    seeds = cv2.ximgproc.createSuperpixelSEEDS(
        cw, ch, 3, requested, SEEDS_NUM_LEVELS, SEEDS_PRIOR,
        SEEDS_HISTOGRAM_BINS, SEEDS_DOUBLE_STEP,
    )
    seeds.iterate(crop_lab, SEEDS_NUM_ITERATIONS)
    raw = seeds.getLabels().astype(np.int64)
    crop_out = np.zeros((ch, cw), np.int64)
    crop_out[crop_valid] = raw[crop_valid] + 1
    out[y0:y1, x0:x1] = crop_out
    return out


def _merge_mean_color(g, src: int, dst: int) -> None:
    g.nodes[dst]["total color"] += g.nodes[src]["total color"]
    g.nodes[dst]["pixel count"] += g.nodes[src]["pixel count"]
    g.nodes[dst]["mean color"] = g.nodes[dst]["total color"] / g.nodes[dst]["pixel count"]
    # "fg pixel count" tracks REAL foreground area only, deliberately
    # excluding whatever mass node 0 (the excluded/background aggregate —
    # see the "SLIC's mask convention" comment in `segment` below) ever
    # contributes, however many merges removed. `.get(..., "pixel count")`
    # is a defensive fallback only; `segment()` always initializes this
    # attribute on every node before any merge runs, so the fallback never
    # actually fires in this module's own call path.
    g.nodes[dst]["fg pixel count"] = (
        g.nodes[dst].get("fg pixel count", g.nodes[dst]["pixel count"])
        + g.nodes[src].get("fg pixel count", g.nodes[src]["pixel count"])
    )
    # Face membership is sticky: a merged region touching a face keeps its
    # protection (`.get` so the attribute's absence — every no-face run —
    # stays a byte-for-byte no-op).
    if g.nodes[src].get("face"):
        g.nodes[dst]["face"] = True


# --- Small-vs-large area-ratio merge protection (2026-08-05 regression fix) --
#
# **THE BUG this protects against** (found by a real before/after audit on
# `testdata/photo/summit_badge.png` at `PipelineConfig(target_width_mm=120.0,
# garment_id="left_chest")`, right after `MERGE_DELTAE00_THRESH` moved
# 10.0 -> 20.0 above): that retune fixed the fragmentation defect it was
# aimed at, but it ALSO opened a second, opposite failure the region-count
# band alone could not see — region count landed inside [20, 80] for two
# different reasons at once, one good (less fragmentation) and one bad (real
# design elements disappearing). On `summit_badge.png`, the badge's black
# ring/inner-circle/crosshair complex — a real, humanly-obvious, sharply
# distinct design element — got RAG-merged wholesale into the huge
# background-colored superpixel cluster that fills the space around and
# behind the badge (itself foreground, not `bg_mask`: the flood-fill
# background detector can't reach it through the black ring from the image
# border, so it segments like any other foreground content). Measured
# directly (see the regression test + this module's own instrumentation
# notes in the fix's PR): the black complex's own coherent cluster (43,934
# px, 63.5% black, mean Lab ~[14, 4, -9] — genuinely dark, not a SLIC-
# diluted sliver) merges into the 595,475 px background-lookalike cluster
# (mean Lab ~[24, 1, 3]) at a measured edge weight of dE00=16.19 — UNDER the
# new 20.0 threshold, but safely OVER the old 10.0 one. So this is not a
# "SLIC lost the thin stroke" bug primarily (the thin ring OUTLINE does get
# diluted by SLIC's ~23px superpixel footprint vs. its own ~6-8px stroke
# width, mean Lab pulled from ~14 to ~31 — a real, secondary effect on the
# thinnest parts) — it is dominantly a threshold bug: a real ~13 dE00 gap
# between two GENUINELY different colors, that the old 10.0 threshold
# correctly treated as distinct and the new 20.0 threshold does not, exactly
# because the new threshold had to widen past 13 to close the fragmentation
# gap on other fixtures.
#
# **Why area ratio, not reverting the threshold**: reverting
# `MERGE_DELTAE00_THRESH` to 10.0 undoes PR #45 wholesale (the very
# fragmentation this module exists to fix). What actually distinguishes this
# failure from a legitimate redundant-band merge is the SIZE mismatch, not
# the color gap alone — a smooth gradient's oversegmentation noise merges
# adjacent bands of comparable size (`region_blobs.png`'s own concentric
# shade sweep, the drone/summit gradient rings), while this bug merges a
# modest, coherent, already-consolidated shape into something an order of
# magnitude bigger. Mirrors the precedent `FACE_MERGE_FACTOR` already sets
# for `_face_local_threshold`: rather than one global threshold, protected
# edges get a locally tighter one, implemented as the same "divide the
# weight, so it takes a smaller true dE00 to still clear the inflated
# number" trick.
#
# **Calibration**: the measured critical merge above sits at ratio 13.6
# (595475 / 43934) and weight 16.19 (`_area_ratio_factor`'s ratio =
# max(px)/min(px) of the two candidate nodes at merge time). A first pass at
# `12.0/0.5` (the tightest pairing that still catches that specific event)
# fixed summit_badge.png (recovered from ~1% to ~80% of the source's own
# near-black pixel area — see the regression test) but pushed
# `drone_render.png` from its documented 65 regions to 83 — OUT of the [20,
# 80] band, i.e. it protected some merges in that fixture that were actually
# legitimate band-to-band consolidation, not this bug. Swept ratio in
# {12, 15, 16, 18, 20} x factor in {0.5, 0.6, 0.65, 0.7} through the FULL
# pipeline (`run_stages`, both busy fixtures, `len(PipelineResult.regions)` —
# the same F4 metric `MERGE_DELTAE00_THRESH`'s own sweep above used):
#
#   ratio  factor  summit_badge  drone_render  summit dark-recovery
#   12.0   0.50    70            83 OUT        80.3%
#   15.0   0.50    68            83 OUT        79.2%
#   20.0   0.50    62            79            79.2%
#   12.0   0.60    63            79            81.0%
#   15.0   0.60    60            78            80.2%
#   15.0   0.70    58            78            80.2%
#   18.0   0.60    56            75            80.2%
#   16.0   0.65    58            75            79.2%
#
# `18.0/0.6` is the chosen pair: both fixtures land well clear of both band
# edges in this sweep table (summit_badge 56, drone_render 75) while keeping
# summit_badge's dark-area recovery at 80.2%, in the same range every other
# tested pairing achieved (79-81%) — recovery is not sensitive to the exact
# pair once protection fires at all; region count against the accept band is
# what actually discriminates. `AREA_RATIO_MERGE_FACTOR=0.6` drops the
# effective LOCAL threshold to `20.0 * 0.6 = 12.0` for a protected edge —
# tighter than the ordinary 20.0, looser than the old global 10.0, because
# this only has to stop ONE specific failure mode (small-coherent-shape into
# much-bigger-lookalike-cluster), not redo the whole fragmentation-vs-quality
# tradeoff the base threshold already settled.
#
# **Two follow-up fixes landed after this sweep, both improving headroom
# further** (see `_init_fg_pixel_counts` and `AREA_RATIO_MIN_SMALL_PX`'s own
# docstrings for the bugs each one closes) — re-measured with BOTH follow-
# ups in place, same ratio/factor, same two fixtures: summit_badge 34
# regions (83.7% dark-area recovery, up from 80.2%), drone_render 68 (right
# at the pre-this-fix baseline of 65) — both with substantially more margin
# than the numbers in the sweep table above, which predate those two fixes.
# The sweep table itself is kept as the historical record of how
# `18.0/0.6` was chosen; it is not what ships today's actual numbers.
AREA_RATIO_PROTECT_THRESH = 18.0
AREA_RATIO_MERGE_FACTOR = 0.6

# **SUPERSEDED 2026-08-07, later the same day — read this first.** Everything
# below is the SLIC -> SEEDS pass's own record of the summit_badge.png
# regression it shipped as `xfail(strict=True)`. That regression is FIXED,
# and not by this constant family (whose values are still correct and still
# unchanged at 18.0/0.6/1000): see `BOUNDARY_CONTRAST_HARD_LAB`'s docstring
# further down for the fix. Two claims below are now known to be wrong, and
# are left in place only because the rest of the trail is still accurate and
# still useful — do not re-derive from either of them:
#
#   * "the merge walks a CHAIN ... rather than ever presenting ONE large-
#     ratio edge" — re-instrumenting every merge on the fixture shows the
#     complex is destroyed by one identifiable big-into-big merge (65,467 px
#     into 348,309 px at dE00 16.06). The edge exists; its size RATIO is
#     just 5.3, far under the 18.0 this family looks for.
#   * "may require a fundamentally different mechanism, not simple constant
#     retuning" — correct in its conclusion, and that mechanism is boundary
#     contrast, measured on the pixels that actually touch across the shared
#     boundary rather than on region mean colors.
#
# **2026-08-07, SLIC -> SEEDS swap: re-measured, NOT re-derived — values kept,
# a real regression on summit_badge.png's black complex documented instead
# of silently papered over.** The task this pass was built against explicitly
# called for re-measuring whether this constant family is still needed and
# still correctly calibrated once the superpixel algorithm underneath it
# changed. It is NOT: `test_summit_badge_black_complex_survives_full_
# pipeline` (full pipeline, `MERGE_DELTAE00_THRESH=26.0`, these exact ratio/
# factor/floor values) recovers only ~9-11% of the source's near-black pixel
# area, down from the SLIC-era 83.7% this constant family was built to
# guarantee — a real, measured, UNRESOLVED regression, not a rounding
# difference. Root-caused (see the diagnostic trail this docstring
# summarizes; full scripts are not part of this repo, the findings are):
# under SLIC, the badge's black ring/circle/crosshair complex consolidated
# into ONE large (~43,934 px) coherent RAG node well before ever touching
# the background, so a single big-vs-big edge weight (measured 16.19 dE00)
# was the whole story, and area-ratio protection (a SIZE-mismatch guard) was
# exactly the right tool. Under SEEDS, the same complex starts life
# fragmented into ~150-260 much smaller (~750-800 px) individual superpixels
# — SEEDS' own block-based growth does not consolidate disconnected same-
# colored content the way SLIC's spatially-local clustering did — and the
# RAG's hierarchical merge walks a CHAIN of small, comparable-size,
# progressively-diluted edges from pure black through intermediate boundary
# tones out to the background, rather than ever presenting ONE large-
# ratio edge for this constant family to catch. Confirmed empirically, not
# assumed: at the OLD SLIC-tuned values, recovery is threshold-sensitive with
# a razor-sharp cliff between raw dE00 16.05 (99.0% recovery) and 16.1 (9.6%)
# — the same ~16 dE00 critical gap SLIC found, meaning this IS structurally
# the same underlying color gap, just no longer reachable through a single
# protectable edge. Every re-derivation attempted this pass either failed to
# move recovery (lowering `AREA_RATIO_MIN_SMALL_PX` alone, tried down to 200,
# left recovery flat at ~9-10% because the *ratio* condition never fired
# early in the chain) or fixed recovery at the cost of breaking OTHER
# already-validated behavior (ratio=3.0/factor=0.3/floor=50 restored ~99-107%
# recovery but pushed drone_render.png from 74 to 122 regions — blowing
# through the 80-region accept band `MERGE_DELTAE00_THRESH` above was tuned
# against — and pushed `gradient_ramp_radial.png` from 1-2 regions to 8,
# edging toward the over-segmentation risk this same pass explicitly ruled
# out at the chosen threshold). No combination tried decoupled "protect this
# one real complex" from "stop legitimate small-into-large absorption
# broadly" the way the original SLIC-era tuning cleanly did. Per this task's
# own instructions ("if real measurement contradicts ... report that
# honestly ... do not force the full swap through if the evidence doesn't
# support it end to end"): reported here, in `MASTER_SCOPE.md`, and in the
# PR description, with `test_summit_badge_black_complex_survives_full_
# pipeline` marked `xfail(strict=True)` (not deleted, not weakened) so this
# stays a live, visible regression marker rather than a silently-lowered
# bar. `test_area_ratio_protection_is_load_bearing_for_that_fixture`'s own
# synthetic proxy fixture no longer reproduces the failure at all under
# SEEDS (it separates into 2 regions with protection DISABLED, same as
# with it) — a real, different, and much less concerning finding: SEEDS
# handles that CLEAN idealized geometry (one thin ring, no dilution chain)
# fine on its own; the real regression only shows up on `summit_badge.png`'s
# actual pixel content, which the synthetic fixture (built for the SLIC-era
# failure mode) does not reproduce. That test's own assertion is updated to
# match, with the same reasoning inline.
#
# Absolute floor on the SMALLER side's own "fg pixel count" for area-ratio
# protection to apply at all — found necessary by
# `test_face_local_threshold_splits_shades_that_merge_outside_a_face`
# (pre-existing, this fix's own first pass broke it): that fixture's two
# solid color blocks meet along a hard edge, and this module's own upscale
# step (`stage1_prep`, Lanczos) smears a handful of small (97-274 px)
# blended-color superpixels along that seam — genuine interpolation noise,
# not a design feature, but tiny-vs-the-50,000+-px blocks it sits beside is
# EXACTLY the shape (moderate color gap + extreme size ratio) area-ratio
# protection is built to catch, so it blocked those slivers from doing the
# ordinary small-into-large absorb they always used to (with_face went
# 2 -> 7, a small but real fragmentation regression of the same kind PR #45
# fixed, just contained to this one edge case instead of systemic). Raw
# pixel count, not mm² — this module's own resolution floor
# (`min_px_per_mm`) can already put mm² well above what "clearly noise"
# means (this fixture's own slivers measure 6-17 mm² at its 4.0 px/mm floor,
# which would have wrongly exempted them too), where a fixed pixel count set
# well between the noise slivers (97-274 px here) and every real protected
# case actually measured (summit_badge's critical small side: 9,980 px; this
# module's own synthetic regression fixture: ~5,900+ px pre-floor) does not.
# Below this floor, an edge is judged purely by color (the ordinary/face
# threshold, whichever applies) exactly as it was before this fix existed.
AREA_RATIO_MIN_SMALL_PX = 1000


def _area_ratio_factor(px_a, px_b) -> float:
    """1.0 (no protection) unless one side is >= `AREA_RATIO_PROTECT_THRESH`
    times bigger than the other AND the smaller side clears
    `AREA_RATIO_MIN_SMALL_PX` — see both constants' own docstrings above.
    Callers must pass "fg pixel count" (real foreground area), never raw
    "pixel count" — see `_init_fg_pixel_counts`'s own docstring for why node
    0's mass must never reach this function."""
    if px_a <= 0 or px_b <= 0:
        return 1.0
    big = max(px_a, px_b)
    small = min(px_a, px_b)
    if small >= AREA_RATIO_MIN_SMALL_PX and big / small >= AREA_RATIO_PROTECT_THRESH:
        return AREA_RATIO_MERGE_FACTOR
    return 1.0


def _init_fg_pixel_counts(rag) -> None:
    """Seed every node's "fg pixel count" before any merge runs: node 0's
    real-foreground area is 0 (it is the aggregate of every EXCLUDED pixel —
    background and, when present, the enclosed population — deliberately
    left in the graph per this module's own mask convention comment in
    `segment` below, but semantically it is not a design region and must
    never be treated as one); every other node starts equal to its own real "pixel
    count". Found the hard way (`test_face_local_threshold_splits_shades_
    that_merge_outside_a_face`, a synthetic fixture that is mostly excluded
    canvas around two small foreground blocks): without this split, node 0's
    huge raw pixel count contaminates whatever real node it eventually
    merges into, making area-ratio protection fire on legitimate same-color
    consolidation transitively routed through node 0 and fragmenting a
    single real region into several — background mass silently posing as
    foreground mass. `_merge_mean_color` carries "fg pixel count" forward on
    every merge the same way it already carries "pixel count"; every
    `_area_ratio_factor` call site below reads "fg pixel count", never the
    raw one."""
    for n, d in rag.nodes(data=True):
        d["fg pixel count"] = 0 if n == 0 else d["pixel count"]


def _area_ratio_initial_adjust(rag) -> None:
    """Apply the same small-vs-large protection to the INITIAL edge weights
    `rag_mean_color` computed (plain Euclidean Lab distance, not dE00 —
    `merge_hierarchical` never rewrites an edge's weight until one of its
    endpoints is actually merged). Covers the edge case where two very
    differently sized SLIC superpixels are already adjacent before any merge
    has touched their shared edge; every later recompute goes through
    `_weight_mean_color` below, which reapplies this same rule on live
    (post-merge) pixel counts. Runs unconditionally (unlike the face drop,
    which only runs when detections exist) — area imbalance is a property of
    the segmentation itself, not an optional detector output. Requires
    `_init_fg_pixel_counts` to have already run on `rag`."""
    for u, v, d in rag.edges(data=True):
        factor = _area_ratio_factor(rag.nodes[u]["fg pixel count"], rag.nodes[v]["fg pixel count"])
        if factor != 1.0:
            d["weight"] = float(d["weight"]) / factor


# --- Boundary-contrast merge protection (2026-08-07, SEEDS regression fix) ---
#
# **What this fixes**: the `summit_badge.png` black-complex regression the
# SLIC -> SEEDS swap shipped as `xfail(strict=True)` (see `AREA_RATIO_PROTECT_
# THRESH`'s docstring above for that pass's own investigation trail, kept
# verbatim as the historical record). Recovery of the badge's black ring/
# inner-circle/crosshair area went from the SLIC era's 83.7% to 9.1% under
# SEEDS, and no re-derivation of the area-ratio constant family recovered it
# without pushing `drone_render.png` out of the 20-80 region accept band.
#
# **The prior pass's stated root cause is not what the merge log actually
# shows** — re-measured directly this pass by instrumenting every merge
# `merge_hierarchical` performs on this fixture (superpixel ids, live
# foreground pixel counts, raw dE00, and how much source-black pixel mass
# each side carries). That trail concluded the black complex "starts
# fragmented into ~150-260 much smaller superpixels" and that the merge
# "walks a CHAIN of small, comparable-size, progressively-diluted edges ...
# rather than ever presenting ONE large-ratio edge for this constant family
# to catch". The first half is true (129 majority-black SEEDS superpixels,
# median ~416 px). The second half is not: those fragments DO consolidate
# with each other first, and the complex is destroyed by ONE identifiable
# merge, the 1043rd of 1052 —
#
#     65,467 px (49,369 of them source-black, mean Lab L*=11.4)
#       into 348,309 px (214 source-black, mean Lab L*=31.1)  at dE00 16.06
#
# — under the 26.0 global threshold. So area-ratio protection did not fail
# because there was no single large edge to catch; it failed because that
# edge's SIZE RATIO is 5.3, nowhere near the 18.0 an extreme-mismatch guard
# is looking for. This is a big-region-into-big-region merge, which
# `_area_ratio_factor` is by construction blind to, and lowering its ratio
# far enough to see a 5.3 (the prior pass tried 3.0) necessarily also
# catches ordinary comparable-size band consolidation everywhere else —
# exactly the drone_render/gradient-ramp breakage that pass measured. The
# constant family was never the right tool for this failure; no value of it
# is.
#
# **The mechanism that does separate them**: how hard the actual image edge
# along the two regions' SHARED BOUNDARY is. `merge_hierarchical` compares
# region MEAN colors, which says nothing about whether the pixels physically
# meet across a step edge or a smooth ramp. Two regions whose means sit 16
# dE00 apart can be either (a) two halves of one continuous gradient, cut at
# an arbitrary interior position where neighbouring pixels differ by
# essentially nothing, or (b) two different design elements meeting at a
# drawn edge where neighbouring pixels differ enormously. Only (b) is
# content destruction. Measured across all four tuning fixtures, on the
# final large merge each one performs (mean per-pixel-pair Lab distance
# across the shared boundary, `_boundary_contrast_stats` below):
#
#     fixture / merge                       raw dE00   boundary contrast
#     gradient_ramp_linear  (final merge)     16.09      0.54
#     gradient_ramp_radial  (final merge)     15.88      0.64
#     summit_badge          (merge 1043)      16.06     31.31   <- destroys
#     summit_badge          (merges 1035/37)  11-13      0.46
#     drone_render          (merges 854-943)  15-24     18.5-39.7
#
# A ~50x gap, not a marginal one: a gradient's interior cut reads ~0.5, a
# real drawn edge reads 18-40. Swept 1.0/2.0/3.0/6.0/10.0/14.0/18.0/25.0/32.0
# through the full pipeline: every value from 1.0 to 25.0 gives the same
# result (summit_badge recovery 106.9%, drone_render 74 regions), and 32.0
# fails only because it has risen past summit_badge's own 31.31 boundary so
# the protection stops firing at all. The real window is therefore bounded
# by the fixtures themselves — above the ramps' 0.64, at or below the
# complex's 31.31 — and `BOUNDARY_CONTRAST_HARD_LAB = 6.0` sits ~10x clear
# of the lower edge and ~5x clear of the upper one. This is the load-bearing
# new idea, and it is measured, not assumed.
#
# **Why a second, size gate is still needed**: boundary contrast alone
# correctly protects summit_badge (recovery 9.1% -> 106.9%) and correctly
# leaves both gradient ramps untouched (2 regions each, unchanged) — but
# `drone_render.png` is a photo-realistic render whose every subject/
# foliage/lettering boundary is also a genuine hard edge, so protecting all
# of them fragments it from 74 to 99 regions. The gate that separates them
# is the size of the SMALLER side as a fraction of the design's own
# foreground: summit_badge's black complex is 11.3% of its foreground, while
# drone_render's largest hard-edge merge candidate is 7.4%.
#
# `BOUNDARY_CONTRAST_MIN_SMALL_FRAC = 0.09` sits between them. Be honest
# about what that margin is: measured window (0.074, 0.113], a ~1.5x gap
# defined by two fixtures, not the ~50x the contrast gate itself enjoys.
# Swept 0.02/0.04/0.06/0.075/0.08/0.09/0.10/0.11/0.115/0.13 through the full
# pipeline; drone_render reads 93/90/89/74/74/74/74/74/74/74 (so the gate has
# to reach ~0.075 before drone_render is back to its shipped count) and
# summit_badge's recovery holds at 106.9% through 0.11, then falls back to
# 9.1% at 0.115 and 0.13 — the gate having risen past the complex's own
# 11.3%, where it simply stops firing.
#
# What makes 0.09 safe DESPITE that thin margin is a structural property,
# not the number itself: a region must be >= 9% of the foreground for this
# protection to fire at all, so at most ~11 regions in any design can ever
# be protected. The mechanism therefore cannot add more than ~10 regions to
# ANY design's final count, whatever its content — it structurally cannot
# reproduce the "122 regions" blowout the prior pass's area-ratio
# re-derivations caused, because those fired on unboundedly many small
# regions. A fixture that lands just the wrong side of 0.09 loses the
# protection (degrading to exactly today's shipped behavior, the safe
# direction) rather than over-fragmenting.
#
# A fraction, not the absolute pixel count `AREA_RATIO_MIN_SMALL_PX` uses,
# specifically because this one has to hold across target widths:
# `stage1_prep`'s upscale makes raw pixel counts scale with
# `cfg.target_width_mm`, and the equivalent absolute-px gate (measured
# window 25,000-65,000 px, swept 1,000-80,000) is only that wide because
# summit_badge happens to be measured at 120mm and drone_render at 90mm —
# re-running drone_render at 120mm moves it into that window and breaks it.
# The fraction is invariant to that. `BOUNDARY_CONTRAST_MIN_SMALL_PX` is
# kept alongside as a plain absolute floor for the same reason
# `AREA_RATIO_MIN_SMALL_PX` exists (a tiny design's 9% is still noise), and
# is deliberately the same 1,000 px that constant already established as
# "clearly above interpolation-sliver scale" — see its docstring.
#
# **A third gate was measured and rejected, recorded so it is not re-derived
# from scratch**: gating on each region's INTERNAL Lab colour spread (rms
# about its own mean) separates the same two fixtures just as well — summit
# badge's complex reads 8.85/6.66 (flat design content) against
# drone_render's 13.7-26.1 (textured photographic content), and a gate at
# 10.0-12.0 holds drone_render at exactly 74 with summit_badge at 106.9%.
# It was not chosen because it needs a new per-node sum-of-squares attribute
# maintained through every merge, its measured window (10.0-12.0, a 1.2x
# gap) is no wider than the fraction gate's, and — the deciding reason — it
# has no equivalent of the bound above: nothing stops an arbitrary number of
# small flat regions from being protected at once.
#
# Threshold DROP, not a hard block: the same "divide the weight so it takes
# a smaller true dE00 to still clear the inflated number" dual that
# `FACE_MERGE_FACTOR` and `AREA_RATIO_MERGE_FACTOR` already use under
# `merge_hierarchical`'s single global threshold.
#
# Expressed as `13.0 / MERGE_DELTAE00_THRESH` rather than a typed-in ratio,
# following the precedent `FACE_MERGE_FACTOR` set for exactly this situation
# (see its own docstring): the number that has to hold is the ABSOLUTE local
# threshold of 13.0 dE00, because what it must sit below — summit_badge's
# fatal 16.06 dE00 merge — is a property of image content, not of whatever
# elbow the base threshold happens to be tuned to for fragmentation's sake.
# A hand-typed ratio would silently drift off that 13.0 the next time
# `MERGE_DELTAE00_THRESH` moves; this does not.
#
# Swept 0.2/0.3/0.4/0.45/0.5/0.55/0.6/0.62/0.65/0.7 (as a raw ratio, at the
# shipped 26.0 base): every value from 0.2 through 0.6 gives identical
# results on all four fixtures (summit_badge 106.9%, drone_render 74, both
# ramps 2), and 0.62 collapses summit_badge to 0.0% — the local threshold
# having just crossed 16.06 (26.0 x 0.62 = 16.12), letting the fatal merge
# back through. That cliff is razor-sharp and is the same one the prior
# pass independently measured from the other side (recovery 99.0% at raw
# dE00 16.05 vs 9.6% at 16.10). 0.5 is chosen rather than the 0.6 nearest
# the cliff: it sits mid-window with ~19% margin below the 0.6177 (=
# 16.06 / 26.0) where protection provably stops working, and costs nothing
# measurable anywhere — the whole 0.2-0.6 range is flat.
BOUNDARY_CONTRAST_HARD_LAB = 6.0
BOUNDARY_CONTRAST_MERGE_FACTOR = 13.0 / MERGE_DELTAE00_THRESH
BOUNDARY_CONTRAST_MIN_SMALL_FRAC = 0.09
BOUNDARY_CONTRAST_MIN_SMALL_PX = 1000


def _boundary_contrast_stats(lab_img: np.ndarray, labels: np.ndarray) -> dict:
    """Per-superpixel-pair boundary contrast: `{packed_pair: [sum, count]}`
    over every 4-neighbour pixel pair that straddles a boundary between two
    DIFFERENT foreground superpixels.

    "Contrast" is plain Euclidean Lab distance between the two touching
    pixels, deliberately not CIEDE2000: this is a bulk per-pixel statistic
    over hundreds of thousands of pairs (dE00 on that many pairs costs more
    than the rest of this stage), and the signal it has to resolve is a ~50x
    separation between "gradient interior" (~0.5) and "drawn edge" (18-40),
    which no reasonable perceptual-vs-Euclidean discrepancy can close. The
    dE00 machinery stays where it decides actual merges (`_weight_mean_
    color`); this only decides whether an edge is eligible for a tighter
    threshold. Reads the same full-precision `lab_img` the RAG itself is
    built from, so the two never disagree about what colour a pixel is.

    Pairs are keyed `min(a, b) * K + max(a, b)` (K = `labels.max() + 1`) so
    the accumulation is one `np.unique`/`reduceat` over an integer array
    rather than a Python loop over boundary pixels. Background/excluded
    pixels (label 0, this module's own mask convention) are skipped on both
    sides — node 0 is not a design region and its boundary is the design's
    silhouette, not an edge between two design elements.

    **4-neighbour, while the RAG itself is built with `connectivity=2`**
    (8-neighbour) — deliberate, and it is why `_boundary_contrast_factor`
    treats a missing statistic as "no protection". Two superpixels touching
    only diagonally are RAG-adjacent but have no 4-neighbour boundary, so
    they get `blen == 0` and are judged by the ordinary threshold exactly as
    before. That is the right answer rather than a gap: a purely diagonal
    contact is a corner, not a shared edge, and a mean "contrast across the
    boundary" computed from one or two corner-touching pixel pairs would be
    noise, not evidence. Anything with a real shared border — every case this
    protection is meant to judge — has 4-neighbour pairs by construction."""
    K = int(labels.max()) + 1
    h, w = labels.shape
    keys: list[np.ndarray] = []
    dists: list[np.ndarray] = []
    for dy, dx in ((0, 1), (1, 0)):
        a = labels[: h - dy, : w - dx]
        b = labels[dy:, dx:]
        m = (a != b) & (a > 0) & (b > 0)
        if not m.any():
            continue
        aa = a[m].astype(np.int64)
        bb = b[m].astype(np.int64)
        keys.append(np.minimum(aa, bb) * K + np.maximum(aa, bb))
        dists.append(
            np.linalg.norm(
                lab_img[: h - dy, : w - dx][m] - lab_img[dy:, dx:][m], axis=1
            )
        )
    if not keys:
        return {}
    key = np.concatenate(keys)
    dist = np.concatenate(dists)
    order = np.argsort(key, kind="stable")
    key = key[order]
    dist = dist[order]
    uniq, start = np.unique(key, return_index=True)
    sums = np.add.reduceat(dist, start)
    counts = np.diff(np.append(start, len(dist)))
    return {int(k): (float(s), int(c)) for k, s, c in zip(uniq, sums, counts)}


def _attach_boundary_contrast(rag, lab_img: np.ndarray, labels: np.ndarray) -> None:
    """Seed every edge's `bsum`/`blen` (summed boundary contrast and boundary
    length in pixel pairs) and stash the design's total foreground pixel
    count on the graph, before any merge runs.

    Carried as a SUM and a COUNT rather than a mean because that is what
    survives merging: when regions A1 and A2 both border B and then merge,
    the new A-B boundary's mean contrast is the length-weighted mean of the
    two, which is exactly `(bsum1 + bsum2) / (blen1 + blen2)`.
    `_weight_mean_color` does that addition on every recompute — see its own
    comment — so a merged super-region's boundary statistic stays honest no
    matter how deep the merge tree gets. An edge with no recorded boundary
    (`blen == 0`, e.g. an edge incident on node 0, which
    `_boundary_contrast_stats` skips by design) reads as unprotected."""
    acc = _boundary_contrast_stats(lab_img, labels)
    K = int(labels.max()) + 1
    for u, v, d in rag.edges(data=True):
        s, c = acc.get(min(u, v) * K + max(u, v), (0.0, 0))
        d["bsum"] = s
        d["blen"] = c
    rag.graph["fg total"] = int((labels > 0).sum())


def _boundary_contrast_factor(bsum, blen, px_a, px_b, fg_total) -> float:
    """1.0 (no protection) unless the shared boundary is a genuinely hard
    image edge AND both sides are substantial regions — see the constants'
    own docstring above. Callers must pass "fg pixel count" (real foreground
    area) for `px_a`/`px_b`, the same discipline `_area_ratio_factor`
    requires and for the same reason (`_init_fg_pixel_counts`).

    Every degenerate input returns 1.0 — no boundary recorded (`blen == 0`,
    which also covers the RAG-connectivity note in `_boundary_contrast_
    stats`) and no known foreground total both fall back to "judge this edge
    exactly the way the pre-2026-08-07 engine did". That direction is
    deliberate: this function can only ever make the merge threshold
    TIGHTER, so failing open means failing to shipped behavior, while
    failing closed would mean fragmenting a design on the strength of a
    statistic that was never actually measured."""
    if blen <= 0 or fg_total <= 0:
        return 1.0
    if bsum / blen < BOUNDARY_CONTRAST_HARD_LAB:
        return 1.0
    small = min(px_a, px_b)
    if small < BOUNDARY_CONTRAST_MIN_SMALL_PX:
        return 1.0
    if small < BOUNDARY_CONTRAST_MIN_SMALL_FRAC * fg_total:
        return 1.0
    return BOUNDARY_CONTRAST_MERGE_FACTOR


def _boundary_contrast_initial_adjust(rag) -> None:
    """Apply boundary-contrast protection to the INITIAL edge weights
    `rag_mean_color` computed, exactly as `_area_ratio_initial_adjust` does
    for its own rule and for the same reason (`merge_hierarchical` never
    rewrites an edge's weight until one of its endpoints actually merges, so
    an edge that is never touched would otherwise never be judged). Requires
    `_init_fg_pixel_counts` and `_attach_boundary_contrast` to have already
    run on `rag`. In practice this pass is a formality on real fixtures — a
    single raw SEEDS superpixel is never 9% of the foreground — but it keeps
    the initial and recomputed weights judged by the same rule instead of
    two subtly different ones."""
    fg_total = rag.graph.get("fg total", 0)
    for u, v, d in rag.edges(data=True):
        factor = _boundary_contrast_factor(
            d.get("bsum", 0.0), d.get("blen", 0),
            rag.nodes[u]["fg pixel count"], rag.nodes[v]["fg pixel count"],
            fg_total,
        )
        if factor != 1.0:
            d["weight"] = float(d["weight"]) / factor


def _weight_mean_color(g, src: int, dst: int, n: int) -> dict:
    da = g.nodes[dst]["mean color"].reshape(1, 3)
    na = g.nodes[n]["mean color"].reshape(1, 3)
    w = float(deltaE_ciede2000(da, na)[0])
    # The face-local threshold drop's recompute half — see
    # `_face_local_threshold`. No-face runs never set the attribute, so `w`
    # is untouched there (the pre-face-priors float, bit for bit).
    if g.nodes[dst].get("face") or g.nodes[n].get("face"):
        w /= FACE_MERGE_FACTOR
    # Small-vs-large area-ratio protection — see its own docstring above.
    # Composes with the face drop above (both are independent local
    # tightenings of the same global threshold): a small region touching a
    # face AND facing an extreme size mismatch gets both factors applied.
    # "fg pixel count", not "pixel count" — see `_init_fg_pixel_counts`.
    w /= _area_ratio_factor(g.nodes[dst]["fg pixel count"], g.nodes[n]["fg pixel count"])
    # Boundary-contrast protection — see its own docstring above. This runs
    # DURING `RAG.merge_nodes`, which calls this function once per neighbour
    # `n` of the pair being merged and only removes `src` from the graph
    # afterwards — so both `g[src][n]` and `g[dst][n]` are still readable
    # here, and the merged region's boundary against `n` is precisely the
    # union of those two boundaries. Summing both sides' `bsum`/`blen` is
    # therefore the exact length-weighted combination, not an approximation;
    # whichever of the two edges does not exist simply contributes nothing.
    bsum = 0.0
    blen = 0
    for x in (src, dst):
        if g.has_edge(x, n):
            e = g[x][n]
            bsum += e.get("bsum", 0.0)
            blen += e.get("blen", 0)
    w /= _boundary_contrast_factor(
        bsum, blen,
        g.nodes[dst]["fg pixel count"], g.nodes[n]["fg pixel count"],
        g.graph.get("fg total", 0),
    )
    # `bsum`/`blen` ride along on the returned attribute dict so the new edge
    # carries them forward — `RAG.add_edge` unpacks whatever this returns as
    # the edge's attributes, so this is how the statistic survives an
    # arbitrarily deep merge tree.
    return {"weight": w, "bsum": bsum, "blen": blen}


# --- Face priors (photo plan §2 row 2, wired 2026-08-04) ----------------------
#
# `face_regions` throughout this module is what `stage1_photo_prep.
# detect_faces_seam` returned: a list of FaceRegion (box + 5 landmarks +
# score, raster px), or None. `pipeline.run_stages` only passes a non-empty
# list when the photo_prep double gate held AND YuNet found faces; every
# other run takes the exact pre-face-priors path.

# How far the merge threshold drops inside a face: an edge touching a face
# superpixel has its weight divided by this factor, which under the one
# global `merge_hierarchical` threshold is exactly a local threshold of
# MERGE_DELTAE00_THRESH * factor.
#
# **Retuned 2026-08-04 alongside `MERGE_DELTAE00_THRESH`'s 10.0 -> 20.0
# move** (see that constant's docstring): this factor moved 0.5 -> 0.25 in
# the same commit, on purpose, so the face-local ABSOLUTE tolerance stays
# 20.0 * 0.25 = 5.0 dE00 — identical to the original 10.0 * 0.5 = 5.0 this
# was measured against (`tests/test_face_priors.py::
# test_face_local_threshold_splits_shades_that_merge_outside_a_face`, which
# still passes unchanged because the absolute number it exercises did not
# move). The eye/mouth split target is a property of face anatomy — how far
# apart an iris and eyelid actually measure after CLAHE — not of whatever
# elbow best collapses a design-wide gradient's color bands, so retuning the
# region-count threshold must not silently retune face protection along
# with it. Original reasoning for why 5.0 dE00 is the right absolute figure
# (kept, still true): the plan's own eye/mouth motivation needs shade steps
# the ORIGINAL global elbow was tuned to merge (a blob's internal band
# sweep, ~15-20 dE00 end to end in 3-4 bands) to survive inside a face —
# one binary octave down from that original 10.0 elbow is the smallest move
# that reliably splits them, and eyes/mouth vs surrounding skin measure
# well apart even after CLAHE.
#
# **Retuned again 2026-08-07 alongside `MERGE_DELTAE00_THRESH`'s 20.0 -> 26.0
# SEEDS-era move** (see that constant's own docstring for why the base
# threshold moved): same precedent this constant itself set for
# `AREA_RATIO_PROTECT_THRESH`'s docstring — decouple the face-local ABSOLUTE
# tolerance from whatever the base threshold happens to be. Expressed as
# `5.0 / MERGE_DELTAE00_THRESH` rather than a re-typed literal specifically
# so it keeps deriving the same 5.0 dE00 absolute figure automatically the
# next time the base threshold moves, instead of silently drifting the way a
# hand-copied literal would if someone edited one constant without noticing
# the other. Confirmed unchanged behavior: `test_face_local_threshold_
# splits_shades_that_merge_outside_a_face` still passes at this new value
# (0.1923...), same as it did at 0.25 under the old 20.0 base — the absolute
# number the test exercises never moved.
FACE_MERGE_FACTOR = 5.0 / MERGE_DELTAE00_THRESH

# A superpixel "is face" when the majority of its pixels sit inside a face
# ellipse; a surviving region is classed "eyes"/"skin" when the majority of
# ITS pixels sit inside an eye disk / face ellipse. Majority, not any-touch:
# a background region grazing a face boundary must not inherit protection.
FACE_MAJORITY_FRAC = 0.5

# Same majority-vote pattern as FACE_MAJORITY_FRAC, applied to the rembg
# subject/background mask (plan step 3, wired 2026-08-05): a region classes
# "background" when the majority of its pixels sit inside the mask, else
# "subject". Kept as its own named constant rather than reusing
# FACE_MAJORITY_FRAC directly — it happens to share the same 0.5 value today,
# but the two answer different questions (face anatomy vs. a whole-image
# cutout) and there is no reason a future retune of one should silently move
# the other.
BG_MAJORITY_FRAC = 0.5

# Eye-disk radius as a fraction of the face box WIDTH. YuNet's interpupil
# distance runs ~0.4x its box width (measured on the astronaut detection:
# eyes 47 px apart in a 90 px box), so 0.12 gives each eye a disk about
# half the interpupil gap across — covers iris + lids without the two disks
# ever fusing across the nose bridge.
EYE_RADIUS_FRAC = 0.12


def _face_ellipse_mask(shape: tuple[int, int], face_regions) -> np.ndarray:
    """(H, W) bool — the plan row 2 "elliptical importance masks": one
    filled ellipse inscribed in each detected face box."""
    m = np.zeros(shape, np.uint8)
    for f in face_regions:
        x, y, w, h = f.box_px
        cv2.ellipse(
            m,
            (int(round(x + w / 2.0)), int(round(y + h / 2.0))),
            (max(1, int(round(w / 2.0))), max(1, int(round(h / 2.0)))),
            0, 0, 360, 1, -1,
        )
    return m.astype(bool)


def _eye_disk_mask(shape: tuple[int, int], face_regions) -> np.ndarray:
    """(H, W) bool — a disk over each eye landmark (YuNet landmarks 0-1)."""
    m = np.zeros(shape, np.uint8)
    for f in face_regions:
        r = max(1, int(round(EYE_RADIUS_FRAC * f.box_px[2])))
        for lx, ly in f.landmarks_px[:2]:
            cv2.circle(m, (int(round(lx)), int(round(ly))), r, 1, -1)
    return m.astype(bool)


def _face_local_threshold(rag, slic_labels: np.ndarray, face_mask: np.ndarray) -> None:
    """Step 5 of the plan's contract, REAL as of 2026-08-04: drop the merge
    threshold locally inside detected faces so eyes/mouth survive as their
    own regions instead of fusing into skin.

    `merge_hierarchical` takes ONE global threshold, so the drop is
    implemented as its exact dual: every edge that touches a face node has
    its weight INFLATED by 1/FACE_MERGE_FACTOR, both here (the initial
    weights `rag_mean_color` computed) and in `_weight_mean_color` (every
    recompute after a merge) — under the unchanged global threshold that is
    identical to judging face-local edges against a threshold of
    MERGE_DELTAE00_THRESH * FACE_MERGE_FACTOR. Mutates `rag` in place: tags
    each node's `face` membership (majority-of-pixels inside the ellipse
    mask) and inflates the initial face-edge weights. Never called on a
    no-face run — those never build a mask, and their nodes never carry the
    attribute, which is what keeps them byte-identical to the
    pre-face-priors engine."""
    labels = np.unique(slic_labels[slic_labels > 0])
    if labels.size == 0:
        return
    n_bins = int(slic_labels.max()) + 1
    total = np.bincount(slic_labels.ravel(), minlength=n_bins)
    inside = np.bincount(slic_labels[face_mask].ravel(), minlength=n_bins)
    for lbl in labels:
        node = int(lbl)
        if node in rag.nodes:
            rag.nodes[node]["face"] = bool(
                total[node] > 0
                and inside[node] / total[node] >= FACE_MAJORITY_FRAC
            )
    for u, v, d in rag.edges(data=True):
        if rag.nodes[u].get("face") or rag.nodes[v].get("face"):
            d["weight"] = float(d["weight"]) / FACE_MERGE_FACTOR


def _region_classes(
    kept: list[RegionMask], face_regions, bg_mask: np.ndarray | None = None
) -> list[str | None]:
    """Step 7's class labels (palette.CLASS_MULTIPLIERS vocabulary).

    "eyes"/"skin" come from the YuNet face priors — REAL as of 2026-08-04,
    the two classes a face detection can honestly assert:

    * "eyes" — the majority of the region's pixels sit inside an eye disk
      (landmarks 0-1, `_eye_disk_mask`); checked first, so a small dark
      region ON an eye outranks the skin ellipse it also sits in.
    * "skin" — the majority of the region's pixels sit inside a face
      ellipse (`_face_ellipse_mask`).

    "subject"/"background" are ALSO real now — wired 2026-08-05 — for any
    region that didn't already class "eyes"/"skin": "background" when the
    majority of the region's pixels sit inside `bg_mask`, else "subject"
    (`BG_MAJORITY_FRAC`, same majority-vote pattern as the face classes).

    `bg_mask` MUST be the real rembg-derived subject/background mask
    (`stage1_photo_prep.remove_background_seam`'s own return value, True =
    background) from a run where it actually succeeded this pass — NOT
    `Prep.bg_mask`, which by the time this runs may be nothing more than
    stage 1's border-flood default merged in. Border-flood only knows
    "touches the border", not "is background", so passing it here would
    make a dishonest "background" claim about interior regions it never
    actually assessed. The caller (`pipeline.run_stages`) enforces this:
    `bg_mask=None` unless `remove_background_seam` returned a real mask,
    exactly the same no-op-on-failure discipline `face_regions` already
    gets. `bg_mask=None` means every non-face region stays class None and
    `palette.region_weight` degrades to plain area for it — the pre-rembg
    behaviour, bit for bit. No faces (None or empty) and no `bg_mask` means
    every region is None — the original pre-face-priors behaviour."""
    if not kept:
        return []
    shape = kept[0].frame_shape
    face_mask = _face_ellipse_mask(shape, face_regions) if face_regions else None
    eyes_mask = _eye_disk_mask(shape, face_regions) if face_regions else None
    classes: list[str | None] = []
    for r in kept:
        area = r.area
        if area == 0:
            classes.append(None)
            continue
        sl = r.frame_slice()
        if eyes_mask is not None and int((r.crop & eyes_mask[sl]).sum()) / area >= FACE_MAJORITY_FRAC:
            classes.append("eyes")
        elif face_mask is not None and int((r.crop & face_mask[sl]).sum()) / area >= FACE_MAJORITY_FRAC:
            classes.append("skin")
        elif bg_mask is not None:
            bg_frac = int((r.crop & bg_mask[sl]).sum()) / area
            classes.append("background" if bg_frac >= BG_MAJORITY_FRAC else "subject")
        else:
            classes.append(None)
    return classes


# --- Tonal region splitting --------------------------------------------------
#
# A region is the unit that owns ONE thread. Everything downstream assumes it:
# `kept_masks_to_quant` takes a region's MEAN Lab as its colour,
# `select_palette` snaps that mean to one spool, and `stage7_sequence` sews a
# block per spool. So a region whose pixels disagree with each other cannot be
# rendered honestly no matter what the fill tier does — the mean is the only
# colour it is allowed to have.
#
# That is what Kent's owl ran into (2026-08-12). Segmentation is clean — 27
# regions, correct silhouette — but the body is a single 4200 mm2 region whose
# lightness spans 81 of the 100 points of L*, so it sews as one flat pale mass.
# The blend fill tier was supposed to rescue exactly this and cannot: its
# shade decomposition computes per-shade threads that `stage7_sequence` never
# reads (verified on `gradient_ramp_linear.png` — 4 shades chosen, 1 colour
# change emitted), so every shade sews in the region's one thread anyway.
#
# Splitting HERE instead is what makes the existing model carry it: each part
# becomes a region in its own right, gets its own mean, its own palette
# weight, and its own spool. Nothing downstream changes. The thread budget
# stays governed by `select_palette`'s chart-restricted k-medoids and
# `cfg.max_colors` exactly as before — parts that land on the same spool are
# deduped back into one label by the loop below, so this can never spend more
# colours than the palette step already allows.
#
# Deliberately lightness quantiles, not a colour k-means: deterministic (this
# module feeds byte-identity goldens), cheap, and aimed at the failure
# actually observed — tonal range flattened away, not hue confusion.

# Perceptual distance between a region's dark and light ends before splitting
# it is worth doing. Matches `stage6_blend.SHADE_STEP_DELTAE * 2`, the point
# at which that module's own `_choose_shade_count` first asks for a 3rd shade.
TONAL_SPLIT_MIN_DELTAE = 18.0
# Measured off percentiles, not min/max: a single specular pixel or one dark
# outlier should not be able to declare a flat region "tonal".
TONAL_SPLIT_PCTILE = (5.0, 95.0)
# A region has to be big enough that its parts are still sewable. Below this
# the split just manufactures slivers for `resolve_small_regions` to absorb
# again. Kent's owl body is 4200 mm2; its irises are 4-17 mm2 and stay whole.
TONAL_SPLIT_MIN_AREA_MM2 = 150.0
# Each CONNECTED COMPONENT of a part must clear this or it is folded back
# into the largest part. Swept on Kent's owl (8 / 20 / 40 mm2 -> 87 / 60 /
# 57 final regions and 14,883 / 13,554 / 13,393 stitches): the curve is
# steep below 20 and flat above it, so 40 buys the last of the available
# reduction without discarding shading anyone would notice. Far above the
# run-tier floor on purpose — a tonal part is only worth its own thread
# stop if it is a visible AREA, not merely sewable.
TONAL_SPLIT_MIN_PART_MM2 = 40.0
TONAL_SPLIT_MAX_PARTS = 4
# Morphological cleanup on each part before it becomes a region, in pixels.
# A photo's tone map is speckled at the pixel scale; without this the parts
# are confetti rather than areas. Small on purpose — removing quantisation
# artefacts, not reshaping the subject.
TONAL_SPLIT_CLEAN_PX = 3


def _percentile_extremes_deltae(lab: np.ndarray) -> float:
    """CIEDE2000 between the mean Lab of a region's darkest and lightest
    decile-ish bands. -> 0.0 when there aren't enough pixels to say."""
    if len(lab) < 24:
        return 0.0
    lo_c, hi_c = np.percentile(lab[:, 0], TONAL_SPLIT_PCTILE)
    lo = lab[lab[:, 0] <= lo_c]
    hi = lab[lab[:, 0] >= hi_c]
    if not len(lo) or not len(hi):
        return 0.0
    return float(deltaE_ciede2000(
        lo.mean(axis=0).reshape(1, 3), hi.mean(axis=0).reshape(1, 3))[0])


def split_tonal_regions(
    p: Prep, kept: list[RegionMask], split_tonal: bool = False
) -> tuple[list[RegionMask], int]:
    """Split regions whose own pixels span more tone than one thread can tell.

    -> (regions, split_count). Every returned mask is a subset of the input
    mask it came from, the parts of one input region are disjoint, and their
    union is exactly the original — so this can neither lose artwork nor
    create overlap for stage 5 to resolve.
    """
    if not split_tonal:
        return kept, 0

    px_per_mm = p.px_per_mm
    px_area_mm2 = 1.0 / (px_per_mm * px_per_mm) if px_per_mm > 0 else 0.0
    if px_area_mm2 <= 0:
        return kept, 0

    out: list[RegionMask] = []
    split_count = 0
    for r in kept:
        px = r.area
        area_mm2 = px * px_area_mm2
        if area_mm2 < TONAL_SPLIT_MIN_AREA_MM2:
            out.append(r)
            continue
        # Crop-space throughout (2026-08-24). Boolean indexing walks the
        # True positions in row-major order, and a bbox window preserves
        # that order exactly, so `lab` is the same pixels in the same
        # sequence the frame-sized mask produced.
        rsl = r.frame_slice()
        lab = rgb_to_lab(p.rgb[rsl][r.crop].reshape(-1, 3))
        span = _percentile_extremes_deltae(lab)
        if span < TONAL_SPLIT_MIN_DELTAE:
            out.append(r)
            continue

        n = int(np.clip(round(span / 9.0), 2, TONAL_SPLIT_MAX_PARTS))
        # Quantile edges, so each part holds a comparable pixel COUNT rather
        # than a comparable slice of the L* axis — a region that is mostly
        # midtone with a small bright rim splits into useful areas either way.
        edges = np.percentile(lab[:, 0], np.linspace(0, 100, n + 1)[1:-1])
        # Was frame-sized float64 — 47 MB per region at 5.88 MP, and the
        # bulk of the 0.45 GB of >4 MB `np.full` allocations measured on
        # that frame. Crop-sized it is a few KB.
        full_l = np.full(r.crop.shape, np.nan, np.float64)
        full_l[r.crop] = lab[:, 0]
        bucket = np.digitize(full_l, edges)

        parts: list[np.ndarray] = []
        for b in range(n):
            m = r.crop & (bucket == b)
            if not m.any():
                continue
            m8 = m.astype(np.uint8)
            if TONAL_SPLIT_CLEAN_PX > 1:
                k = np.ones((TONAL_SPLIT_CLEAN_PX, TONAL_SPLIT_CLEAN_PX), np.uint8)
                # NO border pad here, and that is load-bearing rather than an
                # omission. PR #230 added one on the reasoning that `m` used to
                # be frame-sized so its surround was real background — and that
                # pad is what CHANGED the result: `morphologyEx`'s own default
                # border already reproduces the frame-sized behaviour on the
                # crop, while explicit zeros erode a ring the frame never lost.
                # Measured on baby_deck_laugh: with the pad the region set
                # fingerprints 7ff30d08 (area 13468.796), without it
                # fb8c422f (13468.237) — the exact pre-#230 value.
                m8 = cv2.morphologyEx(m8, cv2.MORPH_OPEN, k)
                m8 = cv2.morphologyEx(m8, cv2.MORPH_CLOSE, k)
            # Re-clip: closing can bulge a part past the region it came from,
            # and two parts that both bulged would overlap.
            m = (m8 > 0) & r.crop
            # Spatial coherence, and the single most important constraint
            # here. A tonal bucket is scattered across the region by
            # construction — the mid-tones of a feathered breast are
            # everywhere — and stage 4 vectorises each connected component
            # into its OWN polygon, each with its own underlay and its own
            # entry/exit. Handing the split through unfiltered turned Kent's
            # owl into 130 regions and 14,905 stitches against 7,721, nearly
            # all of it perimeter and travel rather than coverage. Keeping
            # only components that are individually worth sewing is what
            # makes the difference between "shading" and "confetti"; the
            # crumbs fall through to `leftover` below and rejoin the body.
            num, comp = cv2.connectedComponents(m.astype(np.uint8))
            for c in range(1, num):
                piece = comp == c
                if piece.sum() * px_area_mm2 >= TONAL_SPLIT_MIN_PART_MM2:
                    parts.append(piece)

        if len(parts) < 2:
            out.append(r)
            continue

        # Opening/closing can leave a pixel in two parts, or in none. Resolve
        # both so the union is exactly `r.crop` and the parts are disjoint:
        # first-come wins an overlap, and whatever is left over joins the
        # largest part. Without this, stage 5 would see regions that overlap
        # each other and artwork would silently vanish between them.
        claimed = np.zeros_like(r.crop)
        disjoint: list[np.ndarray] = []
        for m in parts:
            m = m & ~claimed
            claimed |= m
            disjoint.append(m)
        leftover = r.crop & ~claimed
        if leftover.any():
            biggest = max(range(len(disjoint)), key=lambda i: int(disjoint[i].sum()))
            disjoint[biggest] |= leftover
        disjoint = [m for m in disjoint if m.any()]
        if len(disjoint) < 2:
            out.append(r)
            continue

        for m in disjoint:
            # Parts are subsets of the parent, so they share its origin and
            # frame — no re-cropping, which keeps the split provably
            # coordinate-identical to the parent it came from.
            out.append(RegionMask(crop=m, origin=r.origin,
                                  frame_shape=r.frame_shape,
                                  layer=r.layer, source=r.source))
        split_count += 1

    return out, split_count


# --- Stage-2 shade demand (cfg.shade_palette_demand) --------------------------
#
# Option (b) of docs/superpowers/plans/2026-08-23-shade-palette-binding.md:
# the palette should contain the dark/light anchors the shade decomposition
# will need, which means `select_palette` has to SEE the shades — at stage 2,
# four stages before `stage6_streamline._shade_layers` computes them. The
# ordering inversion is shallow because everything `_shade_layers` keys on is
# already in stage 2's hands: the darkness field is a blur of `p.rgb`'s own
# luminance, the shade count is a constants-only formula, and the bucketing
# is nearest-canonical-center over that field. `_shade_demand_points` below
# re-derives that decomposition per kept region — the same field, the same
# formula, the same bucket means, and the same ≤2500-px seeded sampling
# `_sample_pixels` applies (measured 2026-08-23: mirroring the sampling is
# what makes the proxy track the estimator on sparkler_dusk; a full-mask
# proxy recovered only 16% of the oracle palette's benefit there, the
# sampled one over 100%) — and hands each shade's mean Lab in as one
# weighted demand row.
#
# The constants are MIRRORED from stage 6, not imported — the same lockstep
# arrangement `palette.PALETTE_EXCESS_DELTAE` keeps with
# `stage6_blend.SHADE_STEP_DELTAE` and `stage4_vectorize._PHOTO_CLASSES`
# keeps with stage 7's: stage6_blend drags shapely and the fill machinery
# into any importer, this early-stage module has no other reason to pull
# that in, and a broken cross-pin should fail a test
# (tests/test_shade_palette_demand.py), not an import.
_SHADE_DEMAND_BLUR_MM = 0.6        # = stage6_streamline.STREAMLINE_BLUR_MM
_SHADE_DEMAND_MIN_SAMPLES = 12     # = stage6_streamline._SHADE_MIN_SAMPLES
_SHADE_DEMAND_MAX_SAMPLES = 2500   # = stage6_blend.RAMP_MAX_SAMPLES
_SHADE_DEMAND_SAMPLE_SEED = 0      # = stage6_blend.RAMP_SAMPLE_SEED
_SHADE_DEMAND_STEP_DELTAE = 9.0    # = stage6_blend.SHADE_STEP_DELTAE
_SHADE_DEMAND_COUNT_MIN = 3        # = stage6_blend.SHADE_COUNT_MIN
_SHADE_DEMAND_COUNT_MAX = 5        # = stage6_blend.SHADE_COUNT_MAX


def _shade_demand_count(delta_e: float) -> int:
    """`stage6_blend._choose_shade_count`, verbatim formula — mirrored for
    the same no-stage-6-import reason as the constants above, and pinned
    against the original across the whole input range by the test file."""
    n = round(delta_e / _SHADE_DEMAND_STEP_DELTAE) + 1
    return max(_SHADE_DEMAND_COUNT_MIN, min(_SHADE_DEMAND_COUNT_MAX, n))


def _shade_demand_points(
    p: Prep, kept: list[RegionMask], weights: list[float]
) -> tuple[list[np.ndarray], list[float], int]:
    """Proxy shade Lab targets for `select_palette`, per kept region.

    -> (labs, point_weights, regions_with_demand). Each kept region with at
    least `_SHADE_DEMAND_MIN_SAMPLES` pixels contributes one row per
    non-empty shade bucket: the bucket's mean Lab, weighted by the region's
    own selection weight (`weights[i]` — area × class multiplier, the same
    number its mean-colour row carries) times the bucket's pixel share, so a
    region's shade rows together weigh exactly what the region itself does.
    Regions under the floor contribute nothing, mirroring `_shade_layers`'
    degenerate single-shade path (which sews the region's own thread — a
    spool the region's mean row already argues for).

    The decomposition mirrors `stage6_streamline._shade_layers` +
    `stage6_blend._shade_lab_colors` exactly, INCLUDING `_sample_pixels`'
    seeded ≤`_SHADE_DEMAND_MAX_SAMPLES` cap — a proxy should replicate the
    estimator it predicts, sampling and all (the module comment above
    carries the sparkler_dusk measurement that made this structural rule
    concrete). Deterministic: the RNG is seeded per region, exactly as
    `_sample_pixels` seeds per call.
    """
    gray = cv2.cvtColor(p.rgb, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0
    sigma = max(0.5, _SHADE_DEMAND_BLUR_MM * p.px_per_mm)
    dark = 1.0 - cv2.GaussianBlur(gray, (0, 0), sigma)

    labs: list[np.ndarray] = []
    point_weights: list[float] = []
    regions_with_demand = 0
    for region_w, r in zip(weights, kept):
        cys, cxs = np.nonzero(r.crop)
        ys, xs = cys + r.origin[0], cxs + r.origin[1]
        px = len(xs)
        if px < _SHADE_DEMAND_MIN_SAMPLES:
            continue
        if px > _SHADE_DEMAND_MAX_SAMPLES:
            rng = np.random.default_rng(_SHADE_DEMAND_SAMPLE_SEED)
            idx = rng.choice(px, size=_SHADE_DEMAND_MAX_SAMPLES, replace=False)
            ys, xs = ys[idx], xs[idx]
        ts = dark[ys, xs]
        lab = rgb_to_lab(p.rgb[ys, xs].reshape(-1, 3))
        i0, i1 = int(np.argmin(ts)), int(np.argmax(ts))
        extremes = float(deltaE_ciede2000(lab[i0:i0 + 1], lab[i1:i1 + 1])[0])
        n = _shade_demand_count(extremes)
        centers = np.array([i / (n - 1) for i in range(n)], np.float64)
        nearest = np.argmin(np.abs(ts[:, None] - centers[None, :]), axis=1)
        counted = False
        for i in range(n):
            sel = lab[nearest == i]
            if not len(sel):
                # An empty bucket's `_shade_lab_colors` fallback is the
                # overall mean at zero share — zero weight, and
                # `select_palette` rightly refuses non-positive weights, so
                # it contributes no row (the analysis convention the
                # 2026-08-23 proxy measurement used).
                continue
            labs.append(sel.mean(axis=0))
            point_weights.append(float(region_w) * (len(sel) / len(ts)))
            counted = True
        if counted:
            regions_with_demand += 1
    return labs, point_weights, regions_with_demand


def dissolve_phantom_blends(
    labels: np.ndarray,
    valid: np.ndarray,
    lab_img: np.ndarray,
    cfg: PipelineConfig,
    bg_edge_rgb: np.ndarray | None,
    px_per_mm: float,
) -> tuple[np.ndarray, np.ndarray | None, list[dict]]:
    """Fold every merged label that is a COLOUR BLEND of its own two sides
    into whichever side it is nearer. -> (labels, drop_mask, warnings).

    `drop_mask` marks the pixels whose nearer side was the PAGE — halo that
    belongs to the background, not to any shape. None when there are none.

    The flat lane's rule, ported to this one. `stage2_quantize.
    _quantize_population` has dissolved phantom blend clusters since the
    lane existed, and its comment says why in the terms this function
    reuses: *"the outermost halo of every shape is a blend of that shape and
    whatever lies outside it, and background is excluded from clustering, so
    without this endpoint those halos survive as phantom thread layers
    (measured on the golden fixture: two extra pale threads, plus ~30 sliver
    regions that then had to be absorbed downstream)"*. That is verbatim the
    Bridge Bar defect, one lane over: `docs/kent-review-2026-09-03.md` bills
    it at four grey cones and half the design's trims, sewing the JPEG's
    ringing around the black spokes.

    The colour test is the flat lane's, unchanged: `cfg.merge_delta_e` for
    how close to the line between two colours still reads as a blend of
    them, and the same 0.15-0.85 window on where it lands, so the two lanes
    answer that question the same way and can be compared directly. Only the
    edge-fraction gate differs, and it has to -- see
    `_PHOTO_PHANTOM_EDGE_FRAC`.

    ONE deliberate difference, and it makes this stricter rather than looser.
    The flat lane tests a candidate against every OTHER cluster, which is
    safe when there are at most `max_colors` of them; this lane arrives with
    tens (57 on Bridge Bar), and "between some pair of 56 colours" is a test
    almost any colour passes. Endpoints here are the candidate's own
    ADJACENT labels only -- which is also the truer question, since ringing
    is a blend of the two things it physically lies between, not of two
    colours elsewhere in the design.

    The flat lane is untouched by this, on purpose: its goldens stay
    byte-identical by construction rather than by re-measurement.
    """
    from .stage2_quantize import _edge_mask

    ids = np.unique(labels[valid])
    n_ids = len(ids)
    if n_ids < 3:
        # Two labels cannot have anything between them, and one cannot
        # either. Nothing to test, and no array to rewrite.
        return labels, None, []

    # Everything below works in a COMPACTED label space over the foreground
    # pixels only -- `code` runs 0..n_ids-1, `ids[code]` maps back. The
    # obvious `{j: valid & (labels == j)}` costs one frame-sized bool per
    # label, which on a 27 px/mm badge with 50-odd labels is several hundred
    # megabytes for arrays that are read once: the memory ceiling scope
    # defect 11 was about, reached by a new route. Bincounts over one flat
    # index cost the foreground, once.
    edge = _edge_mask(labels, valid)
    code_v = np.searchsorted(ids, labels[valid])
    counts = np.bincount(code_v, minlength=n_ids)
    edge_counts = np.bincount(code_v[edge[valid]], minlength=n_ids)
    lab_v = lab_img[valid].reshape(-1, 3)
    means_arr = np.stack(
        [np.bincount(code_v, weights=lab_v[:, c], minlength=n_ids) for c in range(3)],
        axis=1,
    ) / np.maximum(counts, 1)[:, None]
    means = {j: means_arr[j] for j in range(n_ids)}

    # Adjacency in the same 4-connected sense `_edge_mask` uses, so a label
    # pair is adjacent here exactly when it contributes edge pixels there.
    code_frame = np.full(labels.shape, -1, np.int64)
    code_frame[valid] = code_v
    adj: dict[int, set[int]] = {j: set() for j in range(n_ids)}
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(code_frame, (dy, dx), (0, 1))
        touch = (code_frame >= 0) & (sh >= 0) & (sh != code_frame)
        if touch.any():
            for a, b in np.unique(np.stack([code_frame[touch], sh[touch]], 1), axis=0):
                adj[int(a)].add(int(b))
    # The page is an endpoint no label can be, because stage 1 took it out of
    # `valid` before this lane ever saw it -- the same reason the flat lane
    # needs `bg_edge_rgb`. A label touching background borders it.
    #
    # `bg_from_alpha` declines: under an alpha cutout the background is the
    # GARMENT, and the RGB sitting under transparency is whatever the
    # exporter happened to leave there (`Prep.bg_edge_rgb`'s own caveat, which
    # says any check comparing artwork against "the background colour" must
    # decline when it is set). Without a page endpoint the pass still runs --
    # it just cannot fold the outer band of a cutout's halo, which is the
    # right answer when nobody knows what colour that band is blending into.
    bg_endpoint = (
        rgb_to_lab(np.asarray(bg_edge_rgb, np.float64).reshape(1, 3))[0]
        if bg_edge_rgb is not None else None
    )
    if bg_endpoint is not None:
        outside = ~valid
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            touch = valid & np.roll(outside, (dy, dx), (0, 1))
            for a in np.unique(code_frame[touch]):
                if int(a) >= 0:
                    adj[int(a)].add(_PAGE)

    # Each phantom names the side of its OWN step that it is nearer, which
    # is always one of its own neighbours. The flat lane instead sends a
    # phantom to the nearest surviving colour anywhere in the design; that
    # is safe with at most `max_colors` clusters and wrong here. Measured on
    # Bridge Bar: the outermost grey ring around the black spokes (L 87)
    # finds YELLOW (L 86) nearest and lands in the disc's own label, on the
    # far side of the black it was ringing -- 3,989 px moved and the
    # component count did not shift by one, because as many shapes split as
    # merged. Sending it to one of its two endpoints cannot do that.
    target: dict[int, int] = {}
    for j in range(n_ids):
        n = int(counts[j])
        if not n:
            continue
        if float(edge_counts[j]) / n < _PHOTO_PHANTOM_EDGE_FRAC:
            continue
        ends: list[tuple[int, np.ndarray]] = [
            (o, means[o]) for o in sorted(adj[j]) if o != _PAGE and counts[o]
        ]
        if _PAGE in adj[j] and bg_endpoint is not None:
            ends.append((_PAGE, bg_endpoint))
        side = _blend_side(means[j], ends, cfg.merge_delta_e)
        if side is not None:
            target[j] = side

    if not target:
        return labels, None, []

    # Follow each chain to whatever it finally rests on: a stack of rings
    # (black -> Whale -> Cobblestone -> Skylight -> page) hands every ring
    # to the one inside it, so an unresolved pointer would leave a phantom
    # wearing another phantom's id. Cycles cannot happen through a strictly
    # nearer endpoint, but a raster is not a proof -- the guard is cheap.
    def settle(j: int) -> int:
        seen = {j}
        while j in target:
            j = target[j]
            if j in seen:
                return _PAGE if j == _PAGE else j
            seen.add(j)
        return j

    # One remap table, one pass. `remap[c]` is the compacted label pixel `c`
    # ends up wearing; `to_page` marks the ones that leave the design.
    remap = np.arange(n_ids)
    to_page = np.zeros(n_ids, bool)
    dissolved_px = dropped_px = 0
    for j in sorted(target):
        dest = settle(j)
        if dest == _PAGE:
            # Page-side of the step: these pixels are more background than
            # artwork, and the true edge is the midpoint they sit outside.
            # Keeping them would grow every shape by the full halo stack.
            to_page[j] = True
            dropped_px += int(counts[j])
        else:
            remap[j] = dest
        dissolved_px += int(counts[j])

    out = labels.copy()
    out[valid] = ids[remap[code_v]]
    drop = None
    if dropped_px:
        drop = np.zeros(labels.shape, bool)
        drop[valid] = to_page[code_v]

    px2mm2 = 1.0 / max(px_per_mm ** 2, 1e-9)
    return out, drop, [warn(
        PHOTO_BLEND_DISSOLVED,
        f"{len(target)} color(s) were edge-only blends of the shapes either "
        f"side of them — compression or anti-alias halos, not artwork — and "
        f"were folded into the nearer side instead of sewing as their own "
        f"thread.",
        count=len(target),
        area_mm2=round(dissolved_px * px2mm2, 1),
        returned_to_background_mm2=round(dropped_px * px2mm2, 1),
    )]


# The virtual endpoint standing for the removed background. Negative so it
# can never collide with a real label id.
_PAGE = -1

# What "exists only at edges" means on THIS lane. `cfg.aa_phantom_edge_frac`
# is 0.9, and it can be that strict on the flat lane because the majority
# filter runs immediately before it and has already thinned every halo to
# about one pixel; a one-pixel band is all edge by construction. This lane
# runs no majority filter, so a halo arrives 2-4 px wide and its interior
# pixels are not edge pixels: on `logo_bridge_bar.jpg` at 4 px/mm the grey
# ringing labels read 0.545-1.000 and NONE of the large ones reach 0.9, which
# is why the first cut of this dissolve fired on 14 sub-floor labels and left
# every cone standing. 0.5 states the rule in the terms this lane can
# actually measure -- more than half of this colour's pixels lie on a
# boundary.
#
# It is NOT the discriminator, and should not be read as one: on that fixture
# two real-artwork labels also clear it (0.562 and 0.619, both ~2 mm² slivers
# by the red and teal lettering). What keeps them is `_is_blend`. This is the
# cheap first gate that keeps the O(n²) endpoint search off the 20-odd labels
# that are plainly interior fields.
_PHOTO_PHANTOM_EDGE_FRAC = 0.5


def _blend_side(cj: np.ndarray, ends: list[tuple[int, np.ndarray]],
                tol_de: float) -> int | None:
    """Which of `ends` is `cj` a blend TOWARD? -> that endpoint's id, or None.

    The flat lane's collinearity test (`stage2_quantize.
    _quantize_population`) — window and tolerance included, so the two lanes
    cannot drift apart on the question they both ask — with the answer
    carried back instead of a bare yes. Of every pair `cj` sits between, the
    tightest fit wins, and within that pair the nearer end: a ring at t 0.2
    belongs to the shape, at t 0.8 to whatever is beyond it.
    """
    best: tuple[float, int] | None = None
    for a in range(len(ends)):
        for b in range(a + 1, len(ends)):
            (ia, ca), (ib, cb) = ends[a], ends[b]
            ab = cb - ca
            L = float(np.dot(ab, ab))
            if L <= 0:
                continue
            t = float(np.dot(cj - ca, ab)) / L
            if not (0.15 < t < 0.85):
                continue
            off = float(np.linalg.norm(cj - (ca + t * ab)))
            if off < tol_de and (best is None or off < best[0]):
                best = (off, ia if t < 0.5 else ib)
    return None if best is None else best[1]


def kept_masks_to_quant(
    p: Prep,
    cfg: PipelineConfig,
    kept: list[RegionMask],
    floor_warnings: list[dict],
    *,
    face_regions=None,
    bg_mask: np.ndarray | None = None,
    raw_count: int,
    merged_count: int,
    raw_unit_label: str = "superpixels",
    oversegment_labels: np.ndarray | None = None,
    split_tonal: bool = False,
    shade_demand: bool = False,
) -> Quant:
    """Steps 6-7, shared by EVERY photo-path region former.

    Given `kept` — a list of non-overlapping `RegionMask`s that already
    cleared `stage3_segment.resolve_small_regions`' floor — this does all of
    the work that has nothing to do with WHICH segmenter produced them:
    per-region mean Lab, area x class weighting, chart-restricted weighted
    k-medoids palette selection, spool dedupe into final labels ordered by
    descending area, the separate enclosed population, the
    `PHOTO_SEGMENT_REGION_COUNT` / `PHOTO_PALETTE_SELECTED` warnings, and the
    debug viz.

    Extracted from `segment()` 2026-08-10 so the SAM2 region former
    (`stage2_sam2_segment.sam2_segment_seam`) reuses it instead of copying
    it. Several decisions in here are regression fixes with measured
    defects behind them (`main_thread_colors` vs `len(thread_indices)`, the
    enclosed population's separate label block, the deliberate choice NOT to
    trust the merged label array's own 0/nonzero background convention) —
    two copies of this logic would silently drift apart on exactly those.

    Parameters that differ per segmenter:
      * `raw_count` / `merged_count` — the two provenance numbers the region-
        count warning reports. SLIC+RAG passes its superpixel count and its
        post-merge label count; SAM2 passes its raw mask count and its
        post-overlap-resolution label count.
      * `raw_unit_label` — the noun `raw_count` is measured in. Defaults to
        the classical path's own wording so its warning text is unchanged.
      * `oversegment_labels` — the pre-merge label array for
        `debugviz.stage2_photo_slic`. `None` skips that one viz.

    The warning EXTRA field is still named `slic_segments` on both paths, on
    purpose: it is a warning-schema field other code may already read by
    name, and this module's own docstring already establishes that the
    `slic_*` identifiers mean "whatever the oversegmentation step produced".

    `shade_demand` (2026-08-23, `cfg.shade_palette_demand`'s EXPERIMENT —
    see `_shade_demand_points` above): True appends each kept region's proxy
    shade Labs as extra weighted rows to the `select_palette` call, so the
    palette contains the anchors the stage-6 shade decomposition will bind
    to, and records the full medoid set on `Quant.palette_spools` for the
    stage-7 bind. The extra rows shape the MEDOID SET only — each region
    still snaps to its own nearest selected spool exactly as before, and the
    demand rows themselves never become labels. False (the default every
    pre-existing caller gets) runs the identical `select_palette` call this
    function has always made — byte-identical by construction, and pinned by
    the photo-lane golden. Gating (photo classes only, flag off = never) is
    the CALLER's job — `pipeline.run_stages` derives and passes the bool,
    the same division of labour the stage-7 bind keeps with `_shade_layers`.
    """
    h, w = p.rgb.shape[:2]
    flat_rgb = p.rgb.reshape(-1, 3)
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    slic_count = raw_count

    # Before anything reads a region's MEAN colour, give tonally-diverse
    # regions the chance to become several regions. Placed here rather than in
    # either region former so both the classical and SAM2 paths get it from
    # one implementation — the same reason this function exists.
    regions_before_split = len(kept)
    kept, tonal_splits = split_tonal_regions(p, kept, split_tonal=split_tonal)

    # --- 6. Palette selection (chart-restricted weighted k-medoids) -----------
    # (Step 5, the face-local threshold drop, already ran inside the RAG
    # merge above when detections exist.)
    # Was a per-region `chart.nearest_index` snap before step 7; now the
    # whole region set selects a bounded palette TOGETHER — a fur ramp's
    # regions share consolidated family shades instead of each grabbing its
    # own near-duplicate spool. Weights are area × class multiplier;
    # `_region_classes` maps eye/skin regions from the YuNet detections and
    # subject/background regions from a real rembg mask (everything else —
    # and every run with neither — stays None = plain area).
    chart = chart_for(cfg)
    region_labs = [
        rgb_to_lab(p.rgb[r.frame_slice()][r.crop]
                   .reshape(-1, 3).mean(axis=0, keepdims=True))[0]
        for r in kept
    ]
    classes = _region_classes(kept, face_regions, bg_mask)
    weights = [
        region_weight(r.area, c) for r, c in zip(kept, classes)
    ]
    sel_labs = np.array(region_labs, np.float64).reshape(-1, 3)
    sel_weights = np.array(weights, np.float64)
    # Stage-2 shade demand (`shade_demand` — see this function's docstring
    # and `_shade_demand_points`): extra weighted rows APPENDED after the
    # region rows, so `selection.region_spools[:len(kept)]` below is exactly
    # the per-region mapping the unmodified call returns — the demand rows
    # steer which spools get selected, never which label a region becomes.
    demand_points = 0
    demand_regions = 0
    if shade_demand and kept:
        demand_labs, demand_weights, demand_regions = _shade_demand_points(
            p, kept, weights)
        demand_points = len(demand_labs)
        if demand_points:
            sel_labs = np.vstack(
                [sel_labs, np.asarray(demand_labs, np.float64).reshape(-1, 3)])
            sel_weights = np.concatenate(
                [sel_weights, np.asarray(demand_weights, np.float64)])
    selection = select_palette(
        sel_labs,
        sel_weights,
        chart,
        max_k=cfg.max_colors,
    )
    region_spools = selection.region_spools[:len(kept)]
    # `selection.max_excess_de00` spans every row it selected over; with
    # demand rows in the call that includes the shades, and the
    # PHOTO_PALETTE_SELECTED warning below has always meant the REGIONS'
    # worst excess — so recompute it region-side when (and only when) the
    # row set grew. The no-demand value is the selection's own, untouched.
    if demand_points:
        region_dist = deltaE_ciede2000(
            sel_labs[:len(kept), None, :], np.asarray(chart.lab)[None, :, :])
        region_excess_de00 = float(
            (region_dist[np.arange(len(kept)), np.asarray(region_spools)]
             - region_dist.min(axis=1)).max()) if len(kept) else 0.0
    else:
        region_excess_de00 = selection.max_excess_de00

    # Same convention `stage2_quantize.quantize` ends on: dedupe regions
    # that snapped to the same spool into one final label, ordered by
    # descending total sewn area (largest color first) for determinism.
    by_spool: dict[int, list[int]] = {}
    for i, s in enumerate(region_spools):
        by_spool.setdefault(s, []).append(i)
    ordered_spools = sorted(
        by_spool.items(),
        key=lambda kv: -sum(kept[i].area for i in kv[1]),
    )

    out = np.full((h, w), -1, np.int32)
    thread_indices: list[int] = []
    for new_label, (spool, idxs) in enumerate(ordered_spools):
        thread_indices.append(spool)
        for i in idxs:
            # `out[slice]` is a view, so the boolean assignment writes
            # through to `out` exactly as the frame-sized mask did.
            out[kept[i].frame_slice()][kept[i].crop] = new_label
    # Captured BEFORE the enclosed population (below) appends its own spools
    # onto the end of `thread_indices` — this is the thread-color count for
    # the same population `count`/`len(kept)` below describes (the main
    # region-former body only), so the two numbers in the warning stay
    # comparable (`count >= thread_colors` always holds: color-consolidation
    # can only shrink a region count, never grow it). The enclosed population
    # is a structurally separate, always-small population already reported by
    # its own `BACKGROUND_ENCLOSED` warning (stage 1) — folding its spools
    # into this count would let it exceed `len(kept)` for a reason that has
    # nothing to do with the region former's own consolidation, re-introducing
    # a different flavor of the same "these two numbers don't obviously agree"
    # confusion this fix exists to remove.
    main_thread_colors = len(thread_indices)

    # --- enclosed population, quantized separately, appended as its own
    # trailing label block -- the exact merge-back `stage2_quantize.quantize`
    # does for the same population (see the split's own comment above `segment`
    # opens with).
    enc_warnings: list[dict] = []
    if has_enclosed:
        enc_labels, enc_spools, enc_warnings = _quantize_population(
            flat_rgb, enclosed, h, w, cfg, p.bg_edge_rgb
        )
        base_k = len(thread_indices)
        enc_valid = enc_labels >= 0
        out[enc_valid] = enc_labels[enc_valid] + base_k
        thread_indices = thread_indices + enc_spools

    warnings: list[dict] = list(floor_warnings) + enc_warnings
    if tonal_splits:
        warnings.append(
            warn(
                TONAL_REGIONS_SPLIT,
                f"{tonal_splits} region{'s' if tonal_splits != 1 else ''} "
                "carried more light-to-dark range than a single thread can "
                f"show, and {'were' if tonal_splits != 1 else 'was'} split so "
                "the shading can sew in separate colors.",
                count=tonal_splits,
                regions_before=regions_before_split,
                regions_after=len(kept),
            )
        )
    warnings.append(
        warn(
            PHOTO_SEGMENT_REGION_COUNT,
            # `len(kept)` is the real region count this warning's own name
            # promises — one entry per surviving RegionMask after the region
            # former's own merge and the min-area floor, BEFORE palette
            # selection can consolidate several regions onto one spool. Fixed
            # 2026-08-04: this used to report `len(thread_indices)` (the
            # number of THREAD COLORS the palette settled on, always <= the
            # region count, frequently much smaller once several regions snap
            # to the same spool) under a message claiming to report regions —
            # so the number a caller actually saw here was color count
            # wearing a region-count label, and the real region count never
            # surfaced anywhere in this warning. `PHOTO_PALETTE_SELECTED`
            # below already reports both correctly (`colors`/`regions`); this
            # fix makes THIS warning's own numbers agree with its own name
            # instead of relying on a reader cross-referencing the other one.
            # Both `count` and `thread_colors` describe the main region-former
            # body only (see `main_thread_colors` above) — an enclosed
            # design's separate population is reported by `BACKGROUND_
            # ENCLOSED` (stage 1), not folded in here.
            f"Photo segmentation produced {len(kept)} region"
            f"{'s' if len(kept) != 1 else ''} "
            f"({slic_count} {raw_unit_label}, {merged_count} after merging), "
            f"consolidated to {main_thread_colors} thread color"
            f"{'s' if main_thread_colors != 1 else ''}.",
            count=len(kept),
            thread_colors=main_thread_colors,
            slic_segments=slic_count,
            merged_regions=merged_count,
        )
    )
    warnings.append(
        warn(
            PHOTO_PALETTE_SELECTED,
            # `main_thread_colors`, not `len(thread_indices)`: this message
            # and its `colors` field describe what `select_palette` actually
            # chose over — the main population, `kept` — and an enclosed
            # design's separate population (appended to `thread_indices`
            # above, never part of this k-medoids selection) must not silently
            # inflate that number. Kept consistent with
            # `PHOTO_SEGMENT_REGION_COUNT`'s own same-scope `thread_colors`
            # field just above (added in the same pass this comment was).
            f"Palette selected {main_thread_colors} thread"
            f"{'s' if main_thread_colors != 1 else ''} "
            f"for {len(kept)} region{'s' if len(kept) != 1 else ''} "
            "(chart-restricted weighted k-medoids).",
            colors=main_thread_colors,
            regions=len(kept),
            # Region-side by contract (this warning's own docstring in
            # warnings_codes.py) — `region_excess_de00` IS
            # `selection.max_excess_de00` whenever no demand rows were fed,
            # see its computation above.
            max_excess_de00=round(region_excess_de00, 3),
        )
    )
    if demand_points:
        anchors = sorted(set(selection.medoids) - set(region_spools))
        warnings.append(
            warn(
                PHOTO_SHADE_DEMAND,
                f"Shade demand fed into palette selection: {demand_points} "
                f"proxy shade color{'s' if demand_points != 1 else ''} from "
                f"{demand_regions} region{'s' if demand_regions != 1 else ''} "
                f"joined the selection, which chose "
                f"{len(selection.medoids)} spool"
                f"{'s' if len(selection.medoids) != 1 else ''} "
                f"({len(anchors)} shade-only anchor"
                f"{'s' if len(anchors) != 1 else ''} no region claims).",
                points=demand_points,
                regions_with_demand=demand_regions,
                palette_k=len(selection.medoids),
                anchors=len(anchors),
            )
        )

    if cfg.debug_dir:
        from . import debugviz

        dbg = Path(cfg.debug_dir)
        if oversegment_labels is not None:
            debugviz.stage2_photo_slic(dbg, p.rgb, oversegment_labels)
        mean_rgb = {
            new_label: tuple(int(v) for v in chart[spool].rgb)
            for new_label, (spool, _idxs) in enumerate(ordered_spools)
        }
        # Enclosed-population labels sit past `len(ordered_spools) - 1` (see
        # the enclosed merge-back above) — give them a debug fill color too
        # so the viz doesn't silently leave them un-tinted.
        mean_rgb.update({
            base_k + i: tuple(int(v) for v in chart[spool].rgb)
            for i, spool in enumerate(thread_indices[base_k:])
        } if has_enclosed else {})
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
        # Only when demand actually joined the selection (see the field's
        # own docstring): the FULL medoid set, anchors included, for the
        # stage-7 shade bind. None on every pre-existing path.
        palette_spools=(
            [int(m) for m in selection.medoids] if demand_points else None
        ),
    )


def segment(p: Prep, cfg: PipelineConfig, face_regions=None, bg_mask=None,
            split_tonal=False, shade_demand=False, design_ramp=None) -> Quant:
    h, w = p.rgb.shape[:2]
    valid = ~p.bg_mask
    flat_rgb = p.rgb.reshape(-1, 3)

    # `Prep.enclosed_mask` pixels (BACKGROUND_ENCLOSED — bg-colored icon
    # linework or a donut hole, not border-connected) run through their own
    # SEPARATE population here, mirroring the exact split
    # `stage2_quantize.quantize` already uses, for the same reason: an
    # enclosed patch's content has no business influencing (or being
    # influenced by) the design's own segmentation. Added 2026-08-04 when
    # "gradient" started routing through this module — SLIC/RAG groups
    # purely by color+space with no concept of "this component is a hole,
    # keep it distinguishable from what encloses it", so without this split
    # an enclosed white ring sitting inside a light band of the ramp could
    # get RAG-merged into its enclosing region before `stage4_vectorize.
    # tag_enclosed_background`'s post-vectorization overlap test ever runs —
    # measured directly on `repro_gradient_white_icon.png`: an earlier,
    # unsplit version of this function produced ZERO regions tagged
    # `enclosed_background` (down from 3 via `stage2_quantize`), silently
    # dropping the "toggle it back on in review" restore path
    # `BACKGROUND_ENCLOSED`'s own warning text promises. Reuses
    # `stage2_quantize`'s own per-population quantizer for the enclosed side
    # rather than teaching SLIC anything about holes — an enclosed patch is
    # exactly the small, simple-color content that function already handles
    # well, and it is the same code `stage2_quantize.quantize` itself runs
    # for this population, so the two segmenters treat enclosed content
    # identically regardless of which one handles the design's main body.
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    base_valid = valid & ~enclosed if has_enclosed else valid

    lab_img = rgb_to_lab(flat_rgb).reshape(h, w, 3)
    # The artwork's REAL colours, kept whatever the merge below does to
    # `lab_img`. The phantom-blend test asks whether a colour is an
    # interpolation of the two either side of it, which is only a
    # question about the raster as it was delivered — the same reason
    # the palette reads `p.rgb` rather than the merge's colour space.
    true_lab = lab_img
    if design_ramp is not None:
        # Kent's gradient ruling (2026-09-03): a design whose ramp fits
        # (`design_ramp.fit_design_ramp` — gradient class, gate passed; the
        # pipeline passes None for everything else) merges on Lab with the
        # sweep SUBTRACTED. Every superpixel of a smooth ramp then reads as
        # the same colour and the merge below joins them into one region,
        # where before it cut the sweep wherever the running mean colours
        # drifted `MERGE_DELTAE00_THRESH` apart — the sew-out's "blocky
        # bands" were those cuts, each piece then sewn flat in one thread.
        # An icon drawn ON the ramp loses nothing: its departure from the
        # sweep is what is left, and the boundary-contrast rule reads the
        # same edge it always did. SEEDS still oversegments the original
        # raster (it only supplies the oversegmentation), and the palette
        # below still reads `p.rgb` — only the merge's colour space moves.
        lab_img = design_ramp.flatten_lab(lab_img, p.px_per_mm)

    # --- 1. SEEDS, foreground only (enclosed pixels excluded) ---------------
    slic_labels = _seeds_superpixels(p.rgb, base_valid)
    slic_count = int(len(np.unique(slic_labels[slic_labels > 0])))

    # --- 2. RAG (Lab mean color) + 3. hierarchical merge --------------------
    if slic_count == 0:
        # Nothing foreground (fully-background image) — degenerate but
        # legal; skip straight to an all-background Quant rather than
        # calling into skimage with an empty graph.
        merged = np.zeros((h, w), np.int64)
        merged_count = 0
    else:
        # This module's own mask convention (`_seeds_superpixels`, née
        # SLIC's): label 0 is every excluded (background) pixel;
        # rag_mean_color builds a node for it anyway (a "mean color"
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
        # identity is instead read from the `base_valid` mask everywhere
        # below, never from the merged label array's own 0/nonzero
        # convention, so it does not matter which numeric id background
        # ends up wearing.
        rag = skgraph.rag_mean_color(lab_img, slic_labels, connectivity=2, mode="distance")
        # Small-vs-large area-ratio merge protection (regression fix, see
        # `AREA_RATIO_PROTECT_THRESH`'s own docstring) — runs unconditionally,
        # unlike the face drop just below, and BEFORE it so a face-adjacent
        # edge that also happens to be extreme-ratio gets both factors.
        # `_init_fg_pixel_counts` MUST run before `_area_ratio_initial_adjust`
        # — it seeds the "fg pixel count" attribute that keeps node 0's
        # (background/excluded) mass from ever counting as protected
        # foreground area, on this initial pass and every later recompute.
        _init_fg_pixel_counts(rag)
        _area_ratio_initial_adjust(rag)
        # Boundary-contrast merge protection (regression fix, see
        # `BOUNDARY_CONTRAST_HARD_LAB`'s own docstring) — like the area-ratio
        # rule just above it runs unconditionally, and it composes with it
        # rather than replacing it: the two catch different failures (extreme
        # size MISMATCH vs. two comparable-size regions meeting at a real
        # drawn edge), and `_weight_mean_color` applies both factors
        # independently. `_attach_boundary_contrast` must run before
        # `_boundary_contrast_initial_adjust` — it seeds the per-edge
        # `bsum`/`blen` and the graph-level foreground total that rule reads.
        _attach_boundary_contrast(rag, lab_img, slic_labels)
        _boundary_contrast_initial_adjust(rag)
        if face_regions:
            # Step 5 — the face-local threshold drop. Only a run that
            # actually has detections builds the mask or touches a weight;
            # everything else is the pre-face-priors graph, bit for bit.
            _face_local_threshold(
                rag, slic_labels, _face_ellipse_mask((h, w), face_regions)
            )
        merged = skgraph.merge_hierarchical(
            slic_labels,
            rag,
            thresh=MERGE_DELTAE00_THRESH,
            rag_copy=False,
            in_place_merge=True,
            merge_func=_merge_mean_color,
            weight_func=_weight_mean_color,
        )
        merged_count = int(len(set(np.unique(merged[base_valid]).tolist())))

    # --- 3.5 Phantom-blend dissolve -----------------------------------------
    # The flat lane has run this since before the photo lane existed
    # (`stage2_quantize._quantize_population`, "anti-alias: majority filter,
    # then phantom-blend dissolve"). This lane never got it, and Bridge Bar
    # is the bill: four grey cones -- Skylight, Saturn Grey, Silver, Umber --
    # sewing the JPEG's ringing around the black spokes. Off by default; see
    # `PipelineConfig.dissolve_phantom_blends`.
    if cfg.dissolve_phantom_blends and merged_count:
        merged, blend_drop, blend_warnings = dissolve_phantom_blends(
            merged, base_valid, true_lab, cfg,
            None if p.bg_from_alpha else p.bg_edge_rgb, p.px_per_mm)
        if blend_drop is not None:
            # Page-side halo leaves the foreground before regions are cut
            # from it, so nothing downstream ever sees those pixels as
            # artwork. `base_valid` is the only foreground the extraction
            # below reads.
            base_valid = base_valid & ~blend_drop
        merged_count = int(len(set(np.unique(merged[base_valid]).tolist())))
    else:
        blend_warnings = []

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
    for lbl in sorted(set(np.unique(merged[base_valid]).tolist())):
        # `& base_valid`: a merged label id is not on its own proof of
        # foreground (see the note above) — intersecting with the real
        # per-population mask is what actually keeps background AND
        # enclosed pixels out of every RegionMask here, regardless of which
        # id they ended up wearing.
        comp_mask = ((merged == lbl) & base_valid).astype(np.uint8)
        n_cc, cc, cc_stats, _ = cv2.connectedComponentsWithStats(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            # Cropped at birth (2026-08-24), same as the classical segmenter:
            # `connectedComponentsWithStats` hands back each component's box,
            # so no frame-sized bool per region is ever built.
            cx0, cy0, cw, ch = (int(v) for v in cc_stats[c, :4])
            regions.append(RegionMask(
                crop=np.ascontiguousarray(cc[cy0:cy0 + ch, cx0:cx0 + cw] == c),
                origin=(cy0, cx0), frame_shape=tuple(comp_mask.shape),
                layer=0, source="photo"))

    # chain_rescue=False: the chained-structure rescue is gated OFF on the
    # photo lane -- see stage3_segment.resolve_small_regions for the
    # measurement. Photo quantisation makes sub-floor fragments mutually
    # adjacent everywhere, so chaining stops discriminating here.
    kept, floor_warnings = resolve_small_regions(
        regions, cfg, p.px_per_mm, chain_rescue=False)

    return kept_masks_to_quant(
        p,
        cfg,
        kept,
        blend_warnings + floor_warnings,
        face_regions=face_regions,
        bg_mask=bg_mask,
        raw_count=slic_count,
        merged_count=merged_count,
        oversegment_labels=slic_labels,
        split_tonal=split_tonal,
        shade_demand=shade_demand,
    )
