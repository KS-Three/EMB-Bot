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
     (real as of 2026-08-04); "subject"/"background" still await rembg
     (see `_region_classes`' docstring), so non-face regions stay class
     None and weigh plain area. Before step 7 this line was a per-region
     `chart.nearest_index` snap, which scattered a multi-shade ramp across
     near-duplicate spools from different families — the measured
     before/after lives in `palette.py`'s docstring.
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
from skimage.segmentation import slic
from skimage import graph as skgraph

from .config import PipelineConfig
from .palette import region_weight, select_palette
from .stage1_prep import Prep
from .stage2_quantize import Quant, _quantize_population
from .stage3_segment import RegionMask, resolve_small_regions
from .threads import chart_for, rgb_to_lab
from .warnings_codes import PHOTO_PALETTE_SELECTED, PHOTO_SEGMENT_REGION_COUNT, warn

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
MERGE_DELTAE00_THRESH = 20.0

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


def _merge_mean_color(g, src: int, dst: int) -> None:
    g.nodes[dst]["total color"] += g.nodes[src]["total color"]
    g.nodes[dst]["pixel count"] += g.nodes[src]["pixel count"]
    g.nodes[dst]["mean color"] = g.nodes[dst]["total color"] / g.nodes[dst]["pixel count"]
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
# edges (summit_badge 56 — 36 clear of the floor, 24 clear of the ceiling;
# drone_render 75 — 5 clear of the ceiling, the tightest margin in the
# table, still real headroom) while keeping summit_badge's dark-area
# recovery at 80.2%, in the same range every other tested pairing achieved
# (79-81%) — recovery is not sensitive to the exact pair once protection
# fires at all; region count against the accept band is what actually
# discriminates. `AREA_RATIO_MERGE_FACTOR=0.6` drops the effective LOCAL
# threshold to `20.0 * 0.6 = 12.0` for a protected edge — tighter than the
# ordinary 20.0, looser than the old global 10.0, because this only has to
# stop ONE specific failure mode (small-coherent-shape into much-bigger-
# lookalike-cluster), not redo the whole fragmentation-vs-quality tradeoff
# the base threshold already settled.
AREA_RATIO_PROTECT_THRESH = 18.0
AREA_RATIO_MERGE_FACTOR = 0.6


def _area_ratio_factor(px_a, px_b) -> float:
    """1.0 (no protection) unless one side is >= `AREA_RATIO_PROTECT_THRESH`
    times bigger than the other, in which case `AREA_RATIO_MERGE_FACTOR` —
    see the constants' own docstring above."""
    if px_a <= 0 or px_b <= 0:
        return 1.0
    big = max(px_a, px_b)
    small = min(px_a, px_b)
    if big / small >= AREA_RATIO_PROTECT_THRESH:
        return AREA_RATIO_MERGE_FACTOR
    return 1.0


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
    the segmentation itself, not an optional detector output."""
    for u, v, d in rag.edges(data=True):
        factor = _area_ratio_factor(rag.nodes[u]["pixel count"], rag.nodes[v]["pixel count"])
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
    w /= _area_ratio_factor(g.nodes[dst]["pixel count"], g.nodes[n]["pixel count"])
    return {"weight": w}


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
FACE_MERGE_FACTOR = 0.25

# A superpixel "is face" when the majority of its pixels sit inside a face
# ellipse; a surviving region is classed "eyes"/"skin" when the majority of
# ITS pixels sit inside an eye disk / face ellipse. Majority, not any-touch:
# a background region grazing a face boundary must not inherit protection.
FACE_MAJORITY_FRAC = 0.5

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


def _region_classes(kept: list[RegionMask], face_regions) -> list[str | None]:
    """Step 7's class labels (palette.CLASS_MULTIPLIERS vocabulary), from
    the YuNet face priors — REAL as of 2026-08-04 for the two classes a
    face detection can honestly assert:

    * "eyes" — the majority of the region's pixels sit inside an eye disk
      (landmarks 0-1, `_eye_disk_mask`); checked first, so a small dark
      region ON an eye outranks the skin ellipse it also sits in.
    * "skin" — the majority of the region's pixels sit inside a face
      ellipse (`_face_ellipse_mask`).

    "subject"/"background" REMAIN a documented seam: they need plan step
    3's rembg subject mask (`stage1_photo_prep.remove_background_seam`,
    still a no-op — the numba/numpy conflict recorded there), and nothing
    in a face box can honestly say where the subject's torso ends. Until
    rembg lands, every non-face region stays class None and
    `palette.region_weight` degrades to plain area for it, by that module's
    own documented contract. No faces (None or empty) means every region is
    None — the pre-face-priors behaviour, bit for bit."""
    if not face_regions or not kept:
        return [None] * len(kept)
    shape = kept[0].mask.shape
    face_mask = _face_ellipse_mask(shape, face_regions)
    eyes_mask = _eye_disk_mask(shape, face_regions)
    classes: list[str | None] = []
    for r in kept:
        area = int(r.mask.sum())
        if area == 0:
            classes.append(None)
            continue
        if int((r.mask & eyes_mask).sum()) / area >= FACE_MAJORITY_FRAC:
            classes.append("eyes")
        elif int((r.mask & face_mask).sum()) / area >= FACE_MAJORITY_FRAC:
            classes.append("skin")
        else:
            classes.append(None)
    return classes


def segment(p: Prep, cfg: PipelineConfig, face_regions=None) -> Quant:
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

    # --- 1. SLIC, foreground only (enclosed pixels excluded) ----------------
    slic_labels = slic(
        lab_img,
        n_segments=SLIC_N_SEGMENTS,
        compactness=SLIC_COMPACTNESS,
        start_label=1,
        mask=base_valid,
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
        # identity is instead read from the `base_valid` mask everywhere
        # below, never from the merged label array's own 0/nonzero
        # convention, so it does not matter which numeric id background
        # ends up wearing.
        rag = skgraph.rag_mean_color(lab_img, slic_labels, connectivity=2, mode="distance")
        # Small-vs-large area-ratio merge protection (regression fix, see
        # `AREA_RATIO_PROTECT_THRESH`'s own docstring) — runs unconditionally,
        # unlike the face drop just below, and BEFORE it so a face-adjacent
        # edge that also happens to be extreme-ratio gets both factors.
        _area_ratio_initial_adjust(rag)
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
        n_cc, cc = cv2.connectedComponents(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            regions.append(RegionMask(mask=(cc == c), layer=0, source="photo"))

    kept, floor_warnings = resolve_small_regions(regions, cfg, p.px_per_mm)

    # --- 6. Palette selection (chart-restricted weighted k-medoids) -----------
    # (Step 5, the face-local threshold drop, already ran inside the RAG
    # merge above when detections exist.)
    # Was a per-region `chart.nearest_index` snap before step 7; now the
    # whole region set selects a bounded palette TOGETHER — a fur ramp's
    # regions share consolidated family shades instead of each grabbing its
    # own near-duplicate spool. Weights are area × class multiplier;
    # `_region_classes` maps eye/skin regions from the YuNet detections
    # (everything else — and every no-face run — stays None = plain area).
    chart = chart_for(cfg)
    region_labs = [
        rgb_to_lab(p.rgb[r.mask].reshape(-1, 3).mean(axis=0, keepdims=True))[0]
        for r in kept
    ]
    classes = _region_classes(kept, face_regions)
    weights = [
        region_weight(int(r.mask.sum()), c) for r, c in zip(kept, classes)
    ]
    selection = select_palette(
        np.array(region_labs, np.float64).reshape(-1, 3),
        np.array(weights, np.float64),
        chart,
        max_k=cfg.max_colors,
    )
    region_spools = selection.region_spools

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
    # Captured BEFORE the enclosed population (below) appends its own spools
    # onto the end of `thread_indices` — this is the thread-color count for
    # the same population `count`/`len(kept)` below describes (the SLIC+RAG
    # main body only), so the two numbers in the warning stay comparable
    # (`count >= thread_colors` always holds: color-consolidation can only
    # shrink a region count, never grow it). The enclosed population is a
    # structurally separate, always-small population already reported by its
    # own `BACKGROUND_ENCLOSED` warning (stage 1) — folding its spools into
    # this count would let it exceed `len(kept)` for a reason that has
    # nothing to do with SLIC+RAG's own consolidation, re-introducing a
    # different flavor of the same "these two numbers don't obviously agree"
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
    warnings.append(
        warn(
            PHOTO_SEGMENT_REGION_COUNT,
            # `len(kept)` is the real region count this warning's own name
            # promises — one entry per surviving RegionMask after SLIC+RAG
            # merge and the min-area floor, BEFORE palette selection can
            # consolidate several regions onto one spool. Fixed 2026-08-04:
            # this used to report `len(thread_indices)` (the number of
            # THREAD COLORS the palette settled on, always <= the region
            # count, frequently much smaller once several regions snap to
            # the same spool) under a message claiming to report regions —
            # so the number a caller actually saw here was color count
            # wearing a region-count label, and the real region count never
            # surfaced anywhere in this warning. `PHOTO_PALETTE_SELECTED`
            # below already reports both correctly (`colors`/`regions`); this
            # fix makes THIS warning's own numbers agree with its own name
            # instead of relying on a reader cross-referencing the other one.
            # Both `count` and `thread_colors` describe the SLIC+RAG main
            # body only (see `main_thread_colors` above) — an enclosed
            # design's separate population is reported by `BACKGROUND_
            # ENCLOSED` (stage 1), not folded in here.
            f"Photo segmentation produced {len(kept)} region"
            f"{'s' if len(kept) != 1 else ''} "
            f"({slic_count} superpixels, {merged_count} after merging), "
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
            # chose over — the main SLIC+RAG population, `kept` — and an
            # enclosed design's separate population (appended to
            # `thread_indices` above, never part of this k-medoids selection)
            # must not silently inflate that number. Kept consistent with
            # `PHOTO_SEGMENT_REGION_COUNT`'s own same-scope `thread_colors`
            # field just above (added in the same pass this comment was).
            f"Palette selected {main_thread_colors} thread"
            f"{'s' if main_thread_colors != 1 else ''} "
            f"for {len(kept)} region{'s' if len(kept) != 1 else ''} "
            "(chart-restricted weighted k-medoids).",
            colors=main_thread_colors,
            regions=len(kept),
            max_excess_de00=round(selection.max_excess_de00, 3),
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
    )
