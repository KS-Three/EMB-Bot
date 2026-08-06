"""Stage orchestration — the entry points callers use.

`run_stages` is stages 1-4: artwork in, thread-snapped mm polygons out.
`digitize` continues through stages 5-7 and returns stitches.

They are kept separate because they answer different questions. Stages 1-4 ask
"what shapes are in this artwork, in what threads" and their output is what a
review screen edits. Stages 5-7 ask "how does a machine sew that", and rerunning
them is cheap. The service (build step 8) re-plans stitches after every
parameter tweak while reusing one run of the expensive half.
"""
from __future__ import annotations

from dataclasses import dataclass, field
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
from .stage2_quantize import Quant, quantize
from .stage3_segment import (
    ClassicalSegmenter,
    Segmenter,
    compact_layers,
    resolve_small_regions,
)
from .stage4_vectorize import tag_enclosed_background, vectorize
from .textcluster import detect_text_clusters, regularize_text_clusters
from .stage5_overlap import resolve_overlaps
from .stage6_blend import SourcePixels, detect_design_ramp_angle
from .stage7_sequence import PHOTO_CLASSES, depth_sort_layers, sequence
from .stitches import StitchPlan
from .threads import chart_for
from .warnings_codes import (
    DROPPED_SMALL_SHAPES,
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
    PHOTO_FACE_PRIORS_UNAVAILABLE,
    PHOTO_FACES_DETECTED,
    warn,
)


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

    @property
    def shape_ids(self) -> list[str]:
        return [r.shape_id for r in self.regions]


def run_stages(
    image: str | Path | bytes | np.ndarray,
    cfg: PipelineConfig | None = None,
    segmenter: Segmenter | None = None,
) -> PipelineResult:
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
    if cfg.photo_prep and classification.class_ in ("photo_subject", "photo_scene"):
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

    # "photo_subject"/"photo_scene"/"gradient" all branch here now — only
    # "flat" still takes the plain quantize() call this pipeline has always
    # made. "gradient" joined 2026-08-04 (`docs/superpowers/plans/
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
    q: Quant = (
        photo_segment(p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask)
        if classification.class_ in ("photo_subject", "photo_scene", "gradient")
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
    # fields `match_shape_ids` carries forward — so it belongs before shape
    # edits, not after.
    tag_enclosed_background(regions, p)

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

    # Shape identity edits (contract v1.5): merge/split BEFORE deletions/
    # overrides, on the same "ids assigned against the full generation"
    # reasoning `apply_shape_edits` already documents for itself — merge and
    # split consume some of THIS generation's ids and mint brand new ones, so
    # they must run first for a `shape_overrides`/`deleted_shape_ids` entry
    # (keyed on whatever ids exist after this point) to have a consistent set
    # to reference. See `regions.py`'s own module comment for why these two
    # mint new ids instead of riding `assign_shape_ids`/`match_shape_ids`.
    regions, merge_edit_warnings = apply_shape_merges(regions, cfg.merge_shape_ids)
    regions, split_edit_warnings = apply_shape_splits(regions, cfg.split_shapes)

    # Review-screen edits (shape-layers contract v1). Here — after stage 4 has
    # assigned ids against the full generation, before the palette compacts —
    # so a deletion that empties a thread drops its cone from the color list,
    # and a recolor to a brand-new thread gains one. This is the single seam
    # both `digitize()` and a service re-digitize pass through.
    regions, quant_indices, edit_warnings = apply_shape_edits(
        regions, list(q.thread_indices), cfg.deleted_shape_ids,
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
    if classification.class_ in PHOTO_CLASSES or bool(cfg.extra.get("photo_sequencing")):
        thread_indices = depth_sort_layers(regions, thread_indices, chart_for(cfg))
    # Explicit sew-order layers wait until the palette is settled: moving a
    # shape between layers must reorder sewing, never drop a thread from the
    # color list (see `apply_layer_overrides`).
    apply_layer_overrides(regions, cfg.shape_overrides)

    vec_warnings: list[dict] = []
    if dropped_areas:
        floor = (cfg.min_detail_mm ** 2) * cfg.report_absorb_frac
        reportable = sum(1 for a in dropped_areas if a >= floor)
        if reportable:
            vec_warnings.append(
                warn(
                    DROPPED_SMALL_SHAPES,
                    f"{reportable} detail{'s' if reportable != 1 else ''} were too "
                    "small or thin to hold a stitch and were removed.",
                    count=reportable,
                    cleaned_total=len(dropped_areas),
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
    # Two ways to earn a raster payload, both narrow on purpose: the
    # "gradient" classification (the blend tier reads it), or the caller
    # EXPLICITLY opting into a source-reading tier — a mono tonal fill
    # (scan-line, meander, streamline) or the detail layer (stage6_detail,
    # which extracts its lines from the raster) — a per-request config
    # choice, never an automatic route (automatic photo routing is a later
    # slice). Every other configuration carries no pixels forward and the
    # flat lane's byte-for-byte identity is untouched by this field
    # existing.
    want_tonal = (cfg.fill_technique or "tatami").lower() in (
        "scanline_tonal", "meander_tonal", "streamline", "sketch") or cfg.detail_layer
    # The per-shape form of the sketch opt-in (shape-layers contract v1.3,
    # `tier: "sketch"`): a review-screen edit forcing ONE shape to sketch
    # rendering needs the same raster the design-wide preset does, so
    # requesting it counts as the explicit opt-in too. Scanned here, not
    # resolved — a stale id still warns downstream as every stale edit
    # does, and carrying pixels for it changes no stitch (nothing else
    # reads them unless a tier consumes them).
    want_tonal = want_tonal or any(
        str((ov or {}).get("tier", "")).lower() == "sketch"
        for ov in cfg.shape_overrides.values())
    if classification.class_ == "gradient" or want_tonal:
        source_pixels = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm,
                                     origin_px=(art_cx, art_cy),
                                     gradient_class=(classification.class_
                                                     == "gradient"))
    if classification.class_ == "gradient":
        # One shared fill-row angle for the whole design (2026-08-03 angle-
        # fragmentation fix) — computed here, once, against `p`'s full
        # foreground, before stage 2 fragments it into however many k-means
        # regions. None when the whole-design fit itself declines (no single
        # shared direction found): `blend_fill` falls back to each region's
        # own angle exactly as it always has in that case. Gradient-class
        # only: the scanline tier has its own grain-angle precedence and
        # never reads this field, and the streamline tier reads the
        # direction FIELD instead, never this either.
        source_pixels.design_row_angle_deg = detect_design_ramp_angle(p)

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
    palette = [
        {
            "brand": chart.label,
            "brand_id": chart.id,
            "number": chart[t].number,
            "name": chart[t].name,
            "rgb": list(chart[t].rgb),
        }
        for t in thread_indices
    ]

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
            [*classification.warnings, *p.warnings, *prep_warnings, *q.warnings,
             *small_warnings, *vec_warnings, *merge_edit_warnings, *split_edit_warnings,
             *edit_warnings, *layer_warnings]
        ),
        segmenter=seg.name,
        debug_dir=dbg,
        source_pixels=source_pixels,
        design_class=classification.class_,
    )


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
    planned, overlap_warnings = resolve_overlaps(stitched_regions, fabric, cfg,
                                                 design_class=result.design_class)
    if dbg:
        debugviz.stage5(dbg, planned, result.design_size_mm, chart_for(cfg))

    blocks, seq_warnings = sequence(planned, fabric, cfg,
                                    source_pixels=result.source_pixels,
                                    design_class=result.design_class)

    plan = StitchPlan(
        blocks=blocks,
        palette=result.palette,
        warnings=[*result.warnings, *overlap_warnings, *seq_warnings],
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
