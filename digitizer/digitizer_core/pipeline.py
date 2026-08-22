"""Stage orchestration — the entry points callers use.

`run_stages` is stages 1-4: artwork in, thread-snapped mm polygons out.
`digitize` continues through stages 5-7 and returns stitches.

They are kept separate because they answer different questions. Stages 1-4 ask
"what shapes are in this artwork, in what threads" and their output is what a
review screen edits. Stages 5-7 ask "how does a machine sew that", and rerunning
them is cheap. The service (build step 8) re-plans stitches after every
parameter tweak while reusing one run of the expensive half.

`run_stages` itself splits once more, at the seam the review-edit contract
already drew: `build_generation` is everything through stage 4's computed
facts (classification, prep, quantize, segment, vectorize, tagging, ids) —
none of which reads the four review-edit config keys — and
`finish_generation` applies those edits and settles the palette. The service
caches a `Generation` across edits (see `digitizer_service.jobs`), which is
what takes a boundary-edit re-run from a full stage 0-7 cost to
`finish_generation` + `plan_stitches`. Every other caller just calls
`run_stages` and never sees the seam.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

from . import debugviz
from .config import PipelineConfig
from .fabrics import Fabric, fabric_for_garment, get_fabric
from .regions import (
    Region,
    apply_layer_overrides,
    apply_shape_edits,
    apply_shape_merges,
    apply_shape_splits,
)
from .stage0_classify import classify
from .stage1_photo_prep import (
    detect_faces_seam,
    face_detector_unavailable_reason,
    photo_prep,
    remove_background_seam,
)
from .stage1_prep import Prep, prep
from .stage2_photo_segment import segment as photo_segment
from .stage2_sam2_segment import sam2_segment_seam
from .stage2_quantize import Quant, quantize
from .stage3_segment import (
    ClassicalSegmenter,
    Segmenter,
    compact_layers,
    resolve_small_regions,
)
from .stage4_vectorize import revalidate_threads, tag_enclosed_background, vectorize
from .textcluster import detect_text_clusters, ocr_suggest_text, regularize_text_clusters
from .stage5_overlap import resolve_overlaps
from .stage6_blend import SourcePixels, detect_design_ramp_angle
from .stage7_sequence import PHOTO_CLASSES, depth_sort_layers, sequence
from .stitches import StitchPlan
from .threads import chart_for
from .warnings_codes import (
    DROPPED_SMALL_SHAPES,
    PALETTE_THREAD_MISMATCH,
    PHOTO_AUTO_TIER,
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
    PHOTO_FACE_PRIORS_UNAVAILABLE,
    PHOTO_FACES_DETECTED,
    PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
    SHAPES_LEFT_UNSEWN,
    warn,
)


# How many "min detail" squares a dropped shape has to cover before the
# DROPPED_SMALL_SHAPES warning stops calling it a detail. An order of magnitude
# past detail scale (22.5 mm² at the default 1.5 mm) is not a speck the eye
# would miss — it is a shape the user drew, and the warning has to say so.
NOT_A_DETAIL_FACTOR = 10


def effective_split_tonal(cfg: PipelineConfig, class_: str) -> bool:
    """Spec 2026-08-18 decision 2: photo classes carry tone via upstream
    splitting by default; the config flag remains the explicit override for
    every other class (gradient keeps the blend tier as its tonal carrier)."""
    return bool(cfg.split_tonal_regions) or class_ in PHOTO_CLASSES


def auto_photo_tier(cfg: PipelineConfig, class_: str, faces_present: bool) -> str | None:
    """Spec 2026-08-18 decision 3: the automatic photo tier map. Returns the
    fill_technique to apply, or None to leave the caller's config untouched.
    Only fires when the caller did NOT choose a fill_technique themselves —
    explicit caller config always wins, silently, same as before this
    function existed.

    `detail_layer` is NOT part of that explicit gate (F1, 2026-08-19
    fix-wave correction — it used to be). Spec decision 3 makes the detail
    layer ADDITIVE to the photo_subject route ("streamline + detail layer"),
    not an opt-out from it, so `cfg.detail_layer=True` alone must not
    suppress the auto-route the way an explicit `fill_technique` still does
    — see `plan_stitches`' own `effective_detail_layer` for how the two
    compose once this function has fired.

    `photo_scene` stays tatami in v1 — its tone already comes from
    `effective_split_tonal`'s region splitting above, not a source-reading
    fill tier (`run_stages`' own source_pixels gate keeps scenes off
    `want_tonal` for the same reason: no blend tier reads scene ramps yet,
    so carrying pixels forward for one would only be cost with no reader).

    `faces_present` is accepted, not consulted, here — it decides the
    CALLER's own `detail_layer` effective-on (see `run_stages`), never the
    tier name itself: a photo_subject with no detected faces still gets
    streamline, just without the extra detail block stitched on top.
    """
    explicit = (cfg.fill_technique or "tatami").lower() != "tatami"
    if explicit or class_ != "photo_subject":
        return None
    return "streamline"


@dataclass
class BackgroundInfo:
    detected: bool
    outline_mm: list[list[float]] | None = None
    stitched: bool = False


@dataclass
class PipelineResult:
    regions: list[Region]
    palette: list[dict]              # sew-order thread list
    background: BackgroundInfo
    px_per_mm: float
    design_size_mm: tuple[float, float]
    warnings: list[dict] = field(default_factory=list)
    segmenter: str = "classical"
    debug_dir: Path | None = None
    # Only populated when stage 0 classifies this design "gradient" — the
    # source_pixels the blend fill tier samples from during stitch planning.
    # None for every other class (flat included) so the common case carries
    # no extra raster data forward, and so a design's byte-for-byte identity
    # on the flat lane is unaffected by this field simply existing.
    source_pixels: SourcePixels | None = None
    # Stage 0's verdict, carried so plan_stitches can hand it to stage 7
    # (the photo underlay split keys on it). Defaults "flat" — a hand-built
    # PipelineResult gets exactly the pre-photo behaviour.
    design_class: str = "flat"
    # Fix round 2 (photo/tonal v1, spec decision 3): stage 1.5's face
    # detection verdict (`bool(face_regions)` in run_stages), carried for
    # the SAME "hand it to stage 7" reason `design_class` is — unlike the
    # fill-technique auto-route (a pure function of cfg + class_,
    # recomputable anywhere), whether faces were actually found is a
    # runtime fact stage 1.5 alone can answer; plan_stitches needs the real
    # value to resolve `auto_photo_tier`'s detail_layer effective-on
    # decision for stage 7's detail-layer gate, not just for run_stages'
    # own PHOTO_AUTO_TIER warning text. Defaults False — a hand-built
    # PipelineResult (every test that doesn't set it, every pre-photo
    # caller) gets exactly the pre-existing "no faces" behaviour.
    faces_present: bool = False

    @property
    def shape_ids(self) -> list[str]:
        return [r.shape_id for r in self.regions]


@dataclass
class Generation:
    """Stages 0-4, done: the expensive, review-edit-independent prefix of
    `run_stages`, everything from decode through vectorize/tagging with
    shape ids assigned — the state the shape-layers contract's edits apply
    TO. None of it reads `deleted_shape_ids` / `shape_overrides` /
    `merge_shape_ids` / `split_shapes` (verified by the generation-cache
    tests), which is the property that lets the service cache one of these
    across a whole editing session.

    A cached Generation must stay pristine while `finish_generation` mutates
    Region objects in place (`apply_shape_edits` recolors, re-polygons and
    stamps meta) and appends to warning lists — so every consumer goes
    through `fork()`, cold path included, and the cache only ever holds a
    Generation nothing has finished from.
    """

    classification_class: str
    classification_warnings: list[dict]
    p: Prep
    quant_thread_indices: list[int]
    quant_warnings: list[dict]
    regions: list[Region]
    dropped_areas: list[float]
    prep_warnings: list[dict]
    small_warnings: list[dict]
    resnap_warnings: list[dict]
    faces_present: bool
    seg_name: str
    # Gradient class only (None otherwise): the design-wide fill-row angle,
    # a pure function of `p` hoisted here so a cache hit does not re-fit it.
    design_row_angle_deg: float | None

    def fork(self) -> "Generation":
        """A copy safe to finish from, sharing what is immutable.

        Region.polygon is a shapely 2 geometry (immutable — a boundary
        override REPLACES it, never mutates it) and `p`'s rasters are only
        ever read downstream (stages 5-7 index into `rgb`, never assign),
        so both are shared. Region identity/meta and the warning lists are
        the in-place-mutation surface, so those are fresh per fork; meta
        gets a deep copy because nested values (a boundary_override's
        coordinate list) must not alias across requests either.
        """
        return Generation(
            classification_class=self.classification_class,
            classification_warnings=list(self.classification_warnings),
            p=self.p,
            quant_thread_indices=list(self.quant_thread_indices),
            quant_warnings=list(self.quant_warnings),
            regions=[replace(r, meta=copy.deepcopy(r.meta)) for r in self.regions],
            dropped_areas=list(self.dropped_areas),
            prep_warnings=list(self.prep_warnings),
            small_warnings=list(self.small_warnings),
            resnap_warnings=list(self.resnap_warnings),
            faces_present=self.faces_present,
            seg_name=self.seg_name,
            design_row_angle_deg=self.design_row_angle_deg,
        )


def _cone(chart, thread_index: int) -> dict:
    """One palette entry — the cone list's element shape, in one place.

    `run_stages` builds the per-LAYER list a review screen edits against and
    `plan_stitches` builds the per-BLOCK list the machine actually sews; the
    two answer different questions (see `StitchPlan.palette`) but they are the
    same kind of thing and must not drift into two spellings of it.
    """
    return {
        "brand": chart.label,
        "brand_id": chart.id,
        "number": chart[thread_index].number,
        "name": chart[thread_index].name,
        "rgb": list(chart[thread_index].rgb),
    }


def build_generation(
    image: str | Path | bytes | np.ndarray,
    cfg: PipelineConfig | None = None,
    segmenter: Segmenter | None = None,
) -> Generation:
    """Stages 0-4: artwork in, a `Generation` out — ids assigned, computed
    facts tagged, review edits NOT yet applied. `run_stages` composes this
    with `finish_generation`; the service caches the result across edits."""
    cfg = cfg or PipelineConfig()
    seg = segmenter or ClassicalSegmenter()
    dbg = Path(cfg.debug_dir) if cfg.debug_dir else None

    # Stage 0. Owns its own image decode (see its module docstring) — cheap,
    # and it means this call sits independently of everything stage 1 does.
    # Every class except "gradient" takes the exact code path this pipeline
    # already ran before stage 0 existed; "gradient" branches twice now: at
    # stage 2 (SLIC+RAG instead of k-means, see the dispatch below — 2026-08-04,
    # closing the fragment-count half of `docs/superpowers/plans/
    # 2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`'s
    # "Direction 1") and via source_pixels below, which the blend tier stage 7
    # reads regardless of which stage 2 path ran.
    classification = classify(image, cfg, forced_class=cfg.forced_class)

    p: Prep = prep(image, cfg)
    if dbg:
        debugviz.stage1(dbg, p.rgb, p.bg_mask)

    # Stage 1.5 — photo prep (plan §2 rows 3-4; build step 3 first slice).
    # DOUBLE-gated: the opt-in flag AND a photo classification, so neither
    # the default config nor a photo-classified design under default config
    # nor a non-photo design with the flag on ever takes this branch — the
    # flat/gradient lanes stay byte-identical by construction (and by the
    # byte-identical suites). Overwrites `p.rgb` in place of the stage-1
    # raster, so everything downstream that reads pixels — the photo region
    # former AND `source_pixels` for the tonal tiers — sees the prepped
    # image; that is the point (texture below the sewable floor should not
    # reach any consumer).
    prep_warnings: list[dict] = []
    face_regions = None
    # The REAL rembg-derived subject/background mask, distinct from
    # `p.bg_mask` (which, by the time `photo_segment` runs, may just be
    # stage 1's border-flood default — that mask was never meant to answer
    # "where does the subject end", only "what touches the border"). Stays
    # None unless `remove_background_seam` actually ran and succeeded THIS
    # run; see `stage2_photo_segment._region_classes` for why passing the
    # border-flood default here instead would be a dishonest "background"
    # claim about interior regions.
    subject_bg_mask: np.ndarray | None = None
    if cfg.photo_prep and classification.class_ in PHOTO_CLASSES:
        # rembg subject cutout (plan §2 row 1) — runs FIRST in this block,
        # before face detection and tone prep, because both of those read
        # `p.bg_mask` (tone prep's foreground-only percentile stretch;
        # face detection doesn't today, but a cleaner bg_mask can only help
        # a later consumer, never hurt this one). Its OWN opt-in flag on top
        # of photo_prep — see config.py's comment for why.
        if cfg.photo_prep_background_removal:
            bg_removed, bg_reason = remove_background_seam(p.rgb, p.px_per_mm, cfg)
            if bg_removed is None:
                # The documented no-op fallback: this environment cannot run
                # the isolated rembg subprocess (venv missing, worker
                # crashed, timed out, ...). The job proceeds with stage 1's
                # border-flood bg_mask exactly as before — and says so.
                prep_warnings.append(
                    warn(
                        PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
                        f"Background removal was skipped — {bg_reason}. "
                        "This photo keeps stage 1's border-flood background "
                        "only.",
                        reason=bg_reason,
                    )
                )
            else:
                subject_bg_mask = bg_removed
                frac_before = round(float(p.bg_mask.mean()), 3)
                p.bg_mask = p.bg_mask | bg_removed
                frac_after = round(float(p.bg_mask.mean()), 3)
                prep_warnings.append(
                    warn(
                        PHOTO_BACKGROUND_REMOVED,
                        "Background removed via rembg subject cutout — "
                        f"background pixel fraction {frac_before:.0%} -> "
                        f"{frac_after:.0%}.",
                        background_frac_before=frac_before,
                        background_frac_after=frac_after,
                    )
                )
        # YuNet face priors (plan §2 row 2) — detected on the raster BEFORE
        # texture kill, because a face the smoothing has already softened is
        # exactly the face most likely to slip under the detector; the boxes
        # and landmarks are pure geometry, valid on the prepped raster too
        # (same frame, same px). Behind the same double gate as photo_prep
        # itself so no non-photo (or non-opted-in) lane ever runs a net.
        faces = detect_faces_seam(p.rgb, cfg)
        if faces is None:
            # The documented no-op fallback: this environment cannot run the
            # detector (model missing/corrupt, or no cv2.FaceDetectorYN).
            # The job proceeds exactly as if no faces existed — and says so.
            reason = face_detector_unavailable_reason() or "detector unavailable"
            prep_warnings.append(
                warn(
                    PHOTO_FACE_PRIORS_UNAVAILABLE,
                    f"Face detection was skipped — {reason}. Faces in this "
                    "photo get no protective treatment this run.",
                    reason=reason,
                )
            )
        elif faces:
            face_regions = faces
            n = len(faces)
            prep_warnings.append(
                warn(
                    PHOTO_FACES_DETECTED,
                    f"{n} face{'s' if n != 1 else ''} detected — eyes and "
                    "skin get protective segmentation and palette weight.",
                    count=n,
                    faces=[
                        {
                            "span_mm": [
                                round(f.box_px[2] / p.px_per_mm, 1),
                                round(f.box_px[3] / p.px_per_mm, 1),
                            ],
                            "score": round(f.score, 3),
                        }
                        for f in faces
                    ],
                )
            )
        pp = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, cfg)
        p.rgb = pp.rgb
        prep_warnings.extend(pp.warnings)
        if dbg:
            debugviz.stage1_photo_prep(dbg, pp.rgb_tone, pp.rgb)

    # The SAM2 region former (2026-08-10, `docs/superpowers/plans/
    # 2026-08-10-sam2-segmentation.md`) gets FIRST refusal on the two PHOTO
    # classes only, behind its own opt-in flag. "gradient" is deliberately
    # excluded even though it routes to `photo_segment` too: a smooth ramp
    # has no distinct objects for an instance segmenter to find, and its
    # reason for being here (k-means dithers gradients into speckle) has
    # nothing to do with instance segmentation. Any failure at all — venv
    # not built, checkpoint download blocked, subprocess crash, timeout,
    # no usable regions — returns (None, reason) and this falls straight
    # through to the classical SLIC+RAG call below, exactly the same
    # degrade-and-say-so posture `remove_background_seam` gets above.
    q: Quant | None = None
    if cfg.photo_segment_sam2 and classification.class_ in PHOTO_CLASSES:
        q, sam2_reason = sam2_segment_seam(
            p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask,
            split_tonal=effective_split_tonal(cfg, classification.class_)
        )
        if q is None:
            prep_warnings.append(
                warn(
                    PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
                    f"SAM2 segmentation was skipped — {sam2_reason}. This "
                    "photo used the classical SLIC+RAG region former "
                    "instead.",
                    reason=sam2_reason,
                )
            )

    # "photo_subject"/"photo_scene"/"gradient" all branch here — only "flat"
    # still takes the plain quantize() call this pipeline has always made.
    # "gradient" joined 2026-08-04 (`docs/superpowers/plans/
    # 2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`,
    # "Direction 1"): global k-means clusters color independent of position,
    # so a smooth gradient dithers into per-pixel-adjacent ordered bands —
    # measured at 192-208 final regions on `testdata/photo/drone_render.png`,
    # a real busy commissioned gradient logo, ten times the plan's own 20-80
    # accept band. SLIC+RAG groups by color AND space first, so it does not
    # re-litigate the same dither — measured at 45-56 regions on the same
    # fixture with `MERGE_DELTAE00_THRESH` retuned for this (see that
    # constant's own docstring for the two-fixture derivation). `face_regions`
    # is always `None` for "gradient" (the block above only populates it
    # inside the `photo_subject`/`photo_scene` double-gate), which is exactly
    # the pre-face-priors, byte-identical-within-itself path `segment()`
    # already takes for any other no-face run — gradient art gets no face
    # treatment, on purpose, faces are not this class's concern. `subject_bg_
    # mask` is `None` there for the identical reason — it too is only ever
    # set inside that same double-gate.
    if q is None:
        q = (
            photo_segment(
                p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask,
                split_tonal=effective_split_tonal(cfg, classification.class_)
            )
            if classification.class_ in (*PHOTO_CLASSES, "gradient")
            else quantize(p, cfg)
        )
    if dbg:
        debugviz.stage2(dbg, q.labels, q.thread_indices, chart_for(cfg))

    masks = seg.segment(q, p, cfg)
    masks, small_warnings = resolve_small_regions(masks, cfg, p.px_per_mm, p.enclosed_mask)
    if dbg:
        debugviz.stage3(dbg, p.rgb, masks)

    # Vectorize against the FULL quant palette, then compact — a mask can be
    # dropped during simplification, so the palette can only be finalized
    # once the surviving geometry is known.
    regions: list[Region]
    regions, dropped_areas = vectorize(masks, q.thread_indices, p, cfg)

    # Post-vectorization: tag any Region that is substantially the enclosed
    # bg-colored area stage 1 found (see `tag_enclosed_background`'s
    # docstring for the overlap test and threshold). A computed FACT re-
    # derived every generation — like `layer`, unlike the review-screen
    # fields a resent `shape_overrides` carries forward on a stable id — so it
    # belongs before shape edits, not after.
    tag_enclosed_background(regions, p)

    # Fix #6.3 — re-ask the thread question against the pixels each shape's
    # FINAL polygon covers, now that simplification has moved the outline.
    # Runs AFTER `tag_enclosed_background` because that tag is one of its own
    # gates (an enclosed-background shape's colour is the background's by
    # definition), and before `detect_text_clusters` for the same reason both
    # of those run here: a computed fact re-derived every generation.
    resnap_warnings = revalidate_threads(regions, p, cfg)

    # Same ordering rationale as `tag_enclosed_background` immediately above:
    # a computed FACT re-derived every generation, so it belongs before shape
    # identity edits/overrides run, not after.
    detect_text_clusters(regions, p)

    # Regularization (Step 5): a genuine geometry change, not metadata, so it
    # runs immediately after tagging and still before shape identity edits —
    # a merge/split/boundary_override on a tagged shape should see the
    # regularized polygon, the same way it would see any other computed-fact
    # geometry from this generation.
    regularize_text_clusters(regions, p)

    # OCR-suggested text (Studio "Convert to text" entry point): a read-only,
    # additive per-member OCR read of each tagged member's FINAL polygon —
    # runs after regularization for the same "computed fact reflects this
    # generation's actual geometry" reasoning as the two passes above, never
    # feeds back into detection/regularization/geometry itself. See
    # `textcluster.py`'s module docstring, "OCR-suggested text" section.
    ocr_suggest_text(regions, p)

    # Gradient class: the one shared fill-row angle for the whole design
    # (2026-08-03 angle-fragmentation fix) — a pure function of `p`, hoisted
    # into the generation so a cache hit reuses the fit. `finish_generation`
    # assigns it onto `source_pixels`; see the comment there for who reads
    # it and who deliberately does not.
    design_row_angle_deg = (
        detect_design_ramp_angle(p) if classification.class_ == "gradient" else None
    )

    return Generation(
        classification_class=classification.class_,
        classification_warnings=classification.warnings,
        p=p,
        quant_thread_indices=list(q.thread_indices),
        quant_warnings=q.warnings,
        regions=regions,
        dropped_areas=dropped_areas,
        prep_warnings=prep_warnings,
        small_warnings=small_warnings,
        resnap_warnings=resnap_warnings,
        # `face_regions` is set only when stage 1.5 both ran (photo_prep's
        # double gate) AND found at least one face — see that block above.
        faces_present=bool(face_regions),
        seg_name=seg.name,
        design_row_angle_deg=design_row_angle_deg,
    )


def finish_generation(gen: Generation, cfg: PipelineConfig | None = None) -> PipelineResult:
    """Review edits + palette settlement: the cheap, edit-dependent tail of
    `run_stages`. Mutates `gen`'s regions and warning lists in place — hand
    it a `Generation.fork()`, never a cached original."""
    cfg = cfg or PipelineConfig()
    dbg = Path(cfg.debug_dir) if cfg.debug_dir else None
    p = gen.p
    regions = gen.regions
    prep_warnings = gen.prep_warnings

    # Shape identity edits (contract v1.5): merge/split BEFORE deletions/
    # overrides, on the same "ids assigned against the full generation"
    # reasoning `apply_shape_edits` already documents for itself — merge and
    # split consume some of THIS generation's ids and mint brand new ones, so
    # they must run first for a `shape_overrides`/`deleted_shape_ids` entry
    # (keyed on whatever ids exist after this point) to have a consistent set
    # to reference. See `regions.py`'s own module comment for why these two
    # mint new ids instead of riding `assign_shape_ids`' content-derived ones.
    regions, merge_edit_warnings = apply_shape_merges(regions, cfg.merge_shape_ids)
    regions, split_edit_warnings = apply_shape_splits(regions, cfg.split_shapes)

    # Review-screen edits (shape-layers contract v1). Here — after stage 4 has
    # assigned ids against the full generation, before the palette compacts —
    # so a deletion that empties a thread drops its cone from the color list,
    # and a recolor to a brand-new thread gains one. This is the single seam
    # both `digitize()` and a service re-digitize pass through.
    regions, quant_indices, edit_warnings = apply_shape_edits(
        regions, list(gen.quant_thread_indices), cfg.deleted_shape_ids,
        cfg.shape_overrides, chart_for(cfg))

    # Resolution of a region's effective "stitched" state: a
    # `shape_overrides[sid]["stitched"]` entry wins when present (the service
    # validates it in `_canonicalize_shape_edits`); otherwise an enclosed-
    # background-tagged region is unstitched by default, everything else
    # stitched. Deliberately read straight off cfg here, NOT through
    # `apply_shape_edits`'s meta write path: the default half depends on
    # `enclosed_background`, a fact re-tagged THIS generation, so override
    # and default belong in one expression after tagging — not split between
    # an edit pass and a fallback pass.
    shape_overrides = cfg.shape_overrides or {}
    for r in regions:
        r.meta["stitched"] = (shape_overrides.get(r.shape_id) or {}).get(
            "stitched", not r.meta.get("enclosed_background", False)
        )

    thread_indices, layer_warnings = compact_layers(regions, quant_indices)
    # Photo depth sequencing (plan §2 row 14): photo-classified designs (or
    # an explicit cfg.extra["photo_sequencing"] opt-in) replace stage 2's
    # largest-area-first layer order with background→foreground, dark→light,
    # details last — layers AND the returned thread_indices move together so
    # the palette stays the sew-order list. Flat and gradient never enter
    # this branch: their lanes stay byte-identical by construction, which
    # the byte-identical suites enforce. It sits here, after compaction
    # (dense layers, one thread each) and before apply_layer_overrides, so
    # an explicit review-screen layer override still beats the class
    # default — see depth_sort_layers' docstring for the whole contract.
    if gen.classification_class in PHOTO_CLASSES or bool(cfg.extra.get("photo_sequencing")):
        thread_indices = depth_sort_layers(regions, thread_indices, chart_for(cfg))
    # Explicit sew-order layers wait until the palette is settled: moving a
    # shape between layers must reorder sewing, never drop a thread from the
    # color list (see `apply_layer_overrides`).
    apply_layer_overrides(regions, cfg.shape_overrides)

    vec_warnings: list[dict] = []
    if gen.dropped_areas:
        floor = (cfg.min_detail_mm ** 2) * cfg.report_absorb_frac
        reportable = sum(1 for a in gen.dropped_areas if a >= floor)
        if reportable:
            # Say WHAT was lost, not just how many. This warning used to call
            # every drop a detail "too small or thin to hold a stitch" — and on
            # 2026-08-13 that sentence was describing a 2,787 mm² drop on
            # summit_badge.png (the whole badge body) and 944 + 718 mm² on
            # owl_kent.jpg. The stage 4 bug behind those is fixed, but the
            # wording is what kept it invisible: nobody investigates a lost
            # "detail". Anything an order of magnitude past detail scale is
            # reported as the real shape it is, with its area.
            largest = max(gen.dropped_areas)
            all_small = largest < (cfg.min_detail_mm ** 2) * NOT_A_DETAIL_FACTOR
            if all_small:
                message = (f"{reportable} detail{'s' if reportable != 1 else ''} were too "
                           "small or thin to hold a stitch and were removed.")
            else:
                message = (
                    f"{reportable} shape{'s' if reportable != 1 else ''} could not be "
                    f"turned into a sewable outline and "
                    f"{'were' if reportable != 1 else 'was'} removed "
                    f"(largest {largest:.0f} mm²)."
                )
            vec_warnings.append(
                warn(
                    DROPPED_SMALL_SHAPES,
                    message,
                    count=reportable,
                    cleaned_total=len(gen.dropped_areas),
                    largest_mm2=round(float(largest), 2),
                    all_small=bool(all_small),
                )
            )
    if dbg:
        debugviz.stage4(dbg, p.rgb, regions, p.px_per_mm, p.art_bbox, chart_for(cfg))

    x0, y0, x1, y1 = p.art_bbox
    design = ((x1 - x0) / p.px_per_mm, (y1 - y0) / p.px_per_mm)

    # Same mm<->px origin as bg_outline_mm below and as debugviz.stage4 —
    # SourcePixels.to_mm/to_px depend on this being the one true mapping.
    art_cx, art_cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    source_pixels = None
    # `faces_present`: the one signal `auto_photo_tier` (and this block's own
    # detail-layer decision) need out of stage 1.5's face detection
    # (`build_generation` records `bool(face_regions)`, set only when
    # `detect_faces_seam` both ran — behind `cfg.photo_prep`'s double gate —
    # AND found at least one face). A design that never entered stage 1.5 at
    # all (photo_prep off, the v1 default) therefore reads exactly like one
    # that did and found nothing: no faces, no auto-on detail layer.
    # Acceptable v1 behaviour, not a bug — the auto-route still picks the
    # right BASE tier either way (below), and turning photo_prep on is how a
    # caller gets the detail layer to ever fire automatically.
    faces_present = gen.faces_present
    # Spec 2026-08-18 decision 3 (`auto_photo_tier`): photo_subject's
    # automatic tier — streamline, plus the detail layer when faces were
    # found — unless the caller already chose a fill_technique themselves,
    # in which case `auto_tier` is None and both effective values below
    # collapse to exactly the caller's own config, same as every other
    # class. `detail_layer` alone does NOT suppress it (F1, 2026-08-19 —
    # see `auto_photo_tier`'s own docstring): the detail layer is additive
    # to the route, not an opt-out from it. This is the "later slice" the
    # block's old comment named.
    auto_tier = auto_photo_tier(cfg, gen.classification_class, faces_present)
    effective_fill_technique = auto_tier or cfg.fill_technique
    effective_detail_layer = cfg.detail_layer or (auto_tier is not None and faces_present)
    # Fix round 1, concern 4: the automatic route is LAYERED streamline
    # thread-paint (spec decision 3's own wording), never mono — see
    # `plan_stitches`' own identical computation, the one that actually
    # reaches stage 7's dispatch, for the full reasoning. Computed here too,
    # informationally, so the warning below can name it — this value itself
    # is not consumed by anything in `run_stages` (`want_tonal` below cares
    # only about the technique NAME, not its sub-mode).
    effective_streamline_mode = "layered" if auto_tier is not None else None
    if auto_tier is not None:
        prep_warnings.append(
            warn(
                PHOTO_AUTO_TIER,
                f"This photo was automatically routed to the {auto_tier} "
                f"fill tier ({effective_streamline_mode})" +
                (" with a detail layer for the detected faces"
                 if effective_detail_layer else "") +
                " — no fill_technique was set explicitly.",
                tier=auto_tier,
                detail_layer=effective_detail_layer,
                streamline_mode=effective_streamline_mode,
            )
        )
    # Two ways to earn a raster payload, both narrow on purpose: the
    # "gradient" classification (the blend tier reads it), or a
    # source-reading tier being effectively on — a mono tonal fill
    # (scan-line, meander, streamline) or the detail layer (stage6_detail,
    # which extracts its lines from the raster), each either the caller's
    # own explicit config choice or photo_subject's automatic route just
    # above. `effective_fill_technique`/`effective_detail_layer` are
    # identical to `cfg.fill_technique`/`cfg.detail_layer` for every class
    # `auto_photo_tier` returns None for (every class but photo_subject, and
    # photo_subject itself whenever the caller already chose explicitly) —
    # so the flat lane's byte-for-byte identity is untouched by this field
    # existing, exactly as before.
    want_tonal = (effective_fill_technique or "tatami").lower() in (
        "scanline_tonal", "meander_tonal", "streamline", "sketch") or effective_detail_layer
    # The per-shape form of the sketch/streamline opt-in (shape-layers
    # contract v1.3's `tier: "sketch"`, v1.6's `tier: "streamline"`): a
    # review-screen edit forcing ONE shape onto a raster-reading tier needs
    # the same source pixels the design-wide preset does, so requesting it
    # counts as the explicit opt-in too — this is precisely what makes a
    # manually-classified (flat-lane) shape able to reach streamline fill
    # without the whole design opting into `fill_technique="streamline"`.
    # Scanned here, not resolved — a stale id still warns downstream as
    # every stale edit does, and carrying pixels for it changes no stitch
    # (nothing else reads them unless a tier consumes them).
    want_tonal = want_tonal or any(
        str((ov or {}).get("tier", "")).lower() in ("sketch", "streamline")
        for ov in cfg.shape_overrides.values())
    if gen.classification_class == "gradient" or want_tonal:
        source_pixels = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm,
                                     origin_px=(art_cx, art_cy),
                                     gradient_class=(gen.classification_class
                                                     == "gradient"))
    if gen.classification_class == "gradient":
        # One shared fill-row angle for the whole design (2026-08-03 angle-
        # fragmentation fix) — fitted once, against `p`'s full foreground,
        # before stage 2 fragments it into however many k-means regions;
        # `build_generation` owns the fit (a pure function of `p`, cached
        # with it), this just carries it onto the payload. None when the
        # whole-design fit itself declines (no single shared direction
        # found): `blend_fill` falls back to each region's own angle exactly
        # as it always has in that case. Gradient-class only: the scanline
        # tier has its own grain-angle precedence and never reads this
        # field, and the streamline tier reads the direction FIELD instead,
        # never this either.
        source_pixels.design_row_angle_deg = gen.design_row_angle_deg

    bg_outline_mm = None
    if p.bg_outline_px is not None and len(p.bg_outline_px) >= 3:
        cx, cy = art_cx, art_cy
        pts = p.bg_outline_px.astype(np.float64)
        ring = np.column_stack(
            [(pts[:, 0] - cx) / p.px_per_mm, (pts[:, 1] - cy) / p.px_per_mm]
        )
        # Simplify with the same tolerance the region polygons use.
        simple = Polygon(ring).simplify(cfg.simplify_tol_mm, preserve_topology=True)
        if not simple.is_empty and simple.geom_type == "Polygon":
            bg_outline_mm = [[round(x, 3), round(y, 3)] for x, y in simple.exterior.coords]

    # Stage 3 and stage 4 can both drop shapes, and the review screen should
    # see ONE "n details removed" line, not one per pipeline stage.
    def merge_warnings(items: list[dict]) -> list[dict]:
        out: list[dict] = []
        by_code: dict[str, dict] = {}
        for w in items:
            prev = by_code.get(w["code"])
            if prev is None:
                copy = dict(w)
                by_code[w["code"]] = copy
                out.append(copy)
                continue
            for key in ("count", "cleaned_total", "intruded_px", "dropped"):
                if key in w:
                    prev[key] = prev.get(key, 0) + w[key]
            if "count" in prev:
                noun = "detail" if prev["count"] == 1 else "details"
                prev["message"] = (
                    f"{prev['count']} {noun} smaller than {cfg.min_detail_mm} mm "
                    "could not be sewn and were removed."
                    if w["code"] == DROPPED_SMALL_SHAPES
                    else prev["message"]
                )
        return out

    chart = chart_for(cfg)
    palette = [_cone(chart, t) for t in thread_indices]

    # The palette is per LAYER; a region's thread is per REGION, and
    # `revalidate_threads` above can move one without the other (it re-snaps a
    # shape's spool, deliberately, and never changes its layer). When it does,
    # this layer's palette entry names a cone no shape in the layer carries —
    # the operator loads it and it sews nothing, while the thread that IS sewn
    # is missing from the list. Stage 7 is unaffected (it partitions blocks by
    # the REGION's thread, see `stage6_applique.nn_group_key`), which is
    # exactly why this could stay invisible: only the human-facing color list
    # is wrong. Measured on the pro corpus, 2026-08-14: 5 of 23 designs.
    #
    # An explicit `layer` override is exempt, and only that: putting a shape
    # into another thread's layer is precisely what that override MEANS (see
    # `apply_layer_overrides` — it moves sew position, never the cone), so
    # reporting it would be reading the user's own instruction back to them.
    # Every other mismatch got there by accident.
    mismatched = [
        r for r in regions
        if r.meta["layer"] < len(palette)
        and palette[r.meta["layer"]]["number"] != r.thread_number
        and (shape_overrides.get(r.shape_id) or {}).get("layer") is None
    ]
    palette_warnings: list[dict] = []
    if mismatched:
        layers = sorted({r.meta["layer"] for r in mismatched})
        worst = max(mismatched, key=lambda r: r.area_mm2)
        palette_warnings.append(
            warn(
                PALETTE_THREAD_MISMATCH,
                f"{len(mismatched)} shape{'s' if len(mismatched) != 1 else ''} "
                f"sew in a thread the color list does not name for their layer "
                f"(largest: {worst.area_mm2:.0f} mm² sews in "
                f"{worst.thread_number}, the list says "
                f"{palette[worst.meta['layer']]['number']}).",
                count=len(mismatched),
                layers=layers,
                ids=sorted(r.shape_id for r in mismatched),
                listed=sorted({palette[r.meta["layer"]]["number"]
                               for r in mismatched}),
                actual=sorted({r.thread_number for r in mismatched}),
            )
        )

    return PipelineResult(
        regions=regions,
        palette=palette,
        background=BackgroundInfo(
            detected=bool(p.bg_mask.any()),
            outline_mm=bg_outline_mm,
            stitched=False,
        ),
        px_per_mm=p.px_per_mm,
        design_size_mm=design,
        warnings=merge_warnings(
            [*gen.classification_warnings, *p.warnings, *prep_warnings,
             *gen.quant_warnings, *gen.small_warnings, *vec_warnings,
             *gen.resnap_warnings, *merge_edit_warnings, *split_edit_warnings,
             *edit_warnings, *layer_warnings, *palette_warnings]
        ),
        segmenter=gen.seg_name,
        debug_dir=dbg,
        source_pixels=source_pixels,
        design_class=gen.classification_class,
        faces_present=faces_present,
    )


def run_stages(
    image: str | Path | bytes | np.ndarray,
    cfg: PipelineConfig | None = None,
    segmenter: Segmenter | None = None,
) -> PipelineResult:
    cfg = cfg or PipelineConfig()
    return finish_generation(build_generation(image, cfg, segmenter), cfg)


def fabric_for(cfg: PipelineConfig) -> Fabric:
    """An explicit fabric wins; otherwise the garment picks its usual one."""
    if cfg.fabric_id:
        return get_fabric(cfg.fabric_id)
    return fabric_for_garment(cfg.garment_id)


def plan_stitches(result: PipelineResult, cfg: PipelineConfig | None = None) -> StitchPlan:
    """Stages 5-7: regions -> stitches. Safe to re-run on one PipelineResult."""
    cfg = cfg or PipelineConfig()
    fabric = fabric_for(cfg)
    dbg = Path(cfg.debug_dir) if cfg.debug_dir else None

    # `result.regions` keeps every region — including enclosed-background
    # ones tagged unstitched by default — so a review screen has a real
    # shape to list and restore. Stitching itself excludes them here, the
    # one seam where "stitched: False" actually removes a shape from the
    # machine's work: stage 5 (resolve_overlaps) never sees an excluded
    # region, so its neighbor-interaction logic (pull comp, underlap, same-
    # thread keep-apart) is exactly what it always was for every OTHER
    # shape — an enclosed region touches nothing but the shape that
    # encloses it, and that shape's own polygon already carries this area
    # as a hole in its topology independent of whether the enclosed pixels
    # are separately vectorized (confirmed by reading `stage2_quantize.
    # quantize`: clustering is restricted to `~bg_mask` either way, and an
    # enclosed region's color differs from its enclosing shape's, so the
    # enclosing shape's own mask never included those pixels before this
    # slice either — only whether THEY got a Region of their own changed).
    stitched_regions = [r for r in result.regions if r.meta.get("stitched", True)]

    # ...and it SAYS SO. This exclusion used to be silent, and the silence hid
    # real damage for as long as it lasted: a layer whose every region is
    # skipped keeps its `compact_layers` palette slot (that pass counts
    # regions, and a skipped region is still a region), so the color list
    # carried a cone nothing sews — which then shifted every later block's
    # name under `adapter._thread_name`'s by-index lookup. A planned color
    # that disappears between the region list and the needle is the exact
    # failure class COOKBOOK.md's "hard-won lessons" says must be loud, so
    # this names the shapes and their area rather than counting them.
    skipped = [r for r in result.regions if not r.meta.get("stitched", True)]
    skip_warnings: list[dict] = []
    if skipped:
        overrides = cfg.shape_overrides or {}
        by_override = sum(
            1 for r in skipped
            if "stitched" in (overrides.get(r.shape_id) or {})
        )
        enclosed = sum(1 for r in skipped
                       if r.meta.get("enclosed_background", False))
        total = sum(r.area_mm2 for r in skipped)
        largest = max(skipped, key=lambda r: r.area_mm2)
        threads = sorted({r.thread_number for r in skipped})
        why = ("left out in review" if by_override == len(skipped)
               else "enclosed background, showing the garment through"
               if enclosed == len(skipped) else "enclosed background or "
               "left out in review")
        skip_warnings.append(
            warn(
                SHAPES_LEFT_UNSEWN,
                f"{len(skipped)} shape{'s' if len(skipped) != 1 else ''} "
                f"({total:.1f} mm², largest {largest.area_mm2:.1f} mm²) in "
                f"thread{'s' if len(threads) != 1 else ''} "
                f"{', '.join(threads)} "
                f"{'were' if len(skipped) != 1 else 'was'} planned but not "
                f"sewn — {why}.",
                count=len(skipped),
                ids=[r.shape_id for r in skipped],
                threads=threads,
                total_mm2=round(float(total), 2),
                largest_mm2=round(float(largest.area_mm2), 2),
                enclosed_background=enclosed,
                by_override=by_override,
            )
        )

    planned, overlap_warnings = resolve_overlaps(stitched_regions, fabric, cfg,
                                                 design_class=result.design_class)
    if dbg:
        debugviz.stage5(dbg, planned, result.design_size_mm, chart_for(cfg))

    # Fix round 1 (spec decision 3, concern 1): `sequence` must actually SEW
    # the photo_subject auto-route's decision, not just have `run_stages`
    # capture pixels for it and warn — the gap the first pass of this task
    # left open. Recomputed here (not frozen from the original `run_stages`
    # call) via the exact same pure helper `run_stages` calls, against
    # `result.design_class` — stage 0's verdict, carried on `PipelineResult`
    # for exactly this "hand it to stage 7" purpose (see that field's own
    # docstring) — and `result.faces_present`, carried the same way as of
    # fix round 2 (see that field's own docstring: a runtime fact, not
    # recomputable from cfg + class_ the way the tier decision is).
    # Recomputing the TIER (rather than freezing a value from the original
    # run_stages call) is deliberate: `plan_stitches` is documented "safe to
    # re-run" with a DIFFERENT cfg each time (a review-screen parameter
    # tweak), and an explicit `fill_technique` on THIS call's cfg must still
    # win over the auto-route on THIS call — exactly the "explicit caller
    # config always wins" contract `auto_photo_tier` already enforces, now
    # honoured on every re-plan too, not just the first one.
    auto_tier = auto_photo_tier(cfg, result.design_class, result.faces_present)
    effective_fill_technique = auto_tier or cfg.fill_technique
    # Concern 4: the automatic route is layered streamline thread-paint
    # (spec decision 3's own wording), never mono — mono would sew every
    # shade of a photo region in one thread, defeating the dark->light
    # tone chain Task 1's shade_thread_index emission and this task's
    # earlier streamline-layer shade-stamping fix both exist to carry.
    # Unconditional whenever the auto-route fires: `auto_photo_tier`'s own
    # "explicit" gate does not examine `cfg.streamline_mode` (only `fill_
    # technique`/`detail_layer`), so there is no separate caller override to
    # defer to here — same as `effective_fill_technique` above, `None` for
    # every class/config the auto-route does not fire for, which is what
    # keeps this a no-op for flat, gradient, photo_scene, and an
    # explicitly-configured photo_subject alike.
    effective_streamline_mode = "layered" if auto_tier is not None else None
    # Fix round 2 (Critical): the SAME formula `run_stages` uses for its own
    # `effective_detail_layer` (pipeline.py, the `PHOTO_AUTO_TIER` warning's
    # own "with a detail layer for the detected faces" text) — recomputed
    # here, not carried, for the identical re-plan-responsiveness reason
    # `effective_fill_technique` above is recomputed rather than frozen.
    # Before this round, only the WARNING read this formula; stage 7's own
    # detail-layer gate (below `sequence`, at its own :1519) still read raw
    # `cfg.detail_layer`, so a photo job with a detected face announced a
    # detail layer it never actually sewed — the exact defect class this
    # whole task exists to close for `fill_technique`/`streamline_mode`,
    # just one field later.
    effective_detail_layer = cfg.detail_layer or (auto_tier is not None
                                                  and result.faces_present)
    blocks, seq_warnings = sequence(planned, fabric, cfg,
                                    source_pixels=result.source_pixels,
                                    design_class=result.design_class,
                                    fill_technique=effective_fill_technique,
                                    streamline_mode=effective_streamline_mode,
                                    detail_layer=effective_detail_layer)

    # The plan's palette is the list of cones this plan actually sews, one per
    # BLOCK, in sew order — NOT `result.palette`, which is the per-LAYER list a
    # review screen edits against. They are different lists and the difference
    # is not cosmetic: a layer can vanish here (every member skipped above) and
    # a layer can split into several blocks (specialty steps, and a layer whose
    # shapes re-snapped onto two threads), so a positional read of the
    # layer list against blocks silently renames cones. Measured on the pro
    # corpus 2026-08-14, before this: 13 of 23 designs disagreed, and 22 of
    # the corpus's 96 blocks shipped under another cone's name.
    # `stats.thread_mm_by_color` is per block too, so a worksheet can finally
    # pair the two by index without lying.
    chart = chart_for(cfg)
    plan = StitchPlan(
        blocks=blocks,
        palette=[_cone(chart, b.thread_index) for b in blocks],
        warnings=[*result.warnings, *skip_warnings, *overlap_warnings,
                  *seq_warnings],
        design_size_mm=result.design_size_mm,
    )
    if dbg:
        debugviz.stage6(dbg, plan, result.design_size_mm)
    return plan


def digitize(
    image: str | Path | bytes | np.ndarray,
    cfg: PipelineConfig | None = None,
    segmenter: Segmenter | None = None,
) -> tuple[PipelineResult, StitchPlan]:
    """Artwork in, stitches out. Returns both halves: the regions a review
    screen edits, and the plan a machine sews."""
    cfg = cfg or PipelineConfig()
    result = run_stages(image, cfg, segmenter)
    return result, plan_stitches(result, cfg)
