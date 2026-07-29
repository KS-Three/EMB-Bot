# Digitizer Step 1 — Core Pipeline Skeleton (Stages 1–4)

Status: DRAFT for adversarial critique. Blueprint: Kent's Auto-Digitizing Engine
Blueprint v2.1 + the v2.2 amendments grilled 2026-07-29 (see memory /
conversation). Professional quality is the non-negotiable constraint.

## Scope (blueprint build-order step 1)

Stages 1–4 of digitizer-core on hardcoded synthetic test logos, classical
segmentation only (SAM 2 is step 2), including basic alpha/border-flood
background masking and a thread chart, with visual debug output per stage.
No FastAPI (step 8), no stitch planning (step 3+), no EMB-Bot integration
(step 10).

## Deviations from blueprint (deliberate, flag if wrong)

1. **Full Isacord chart instead of ~20-color stub.** The blueprint stubbed the
   chart because hand-transcription was assumed expensive; Kent's 2026-07-29
   chart ruling (facts-doctrine data OK in both products) makes the full
   398-color Isacord chart free — generate `threads_isacord.py` from
   `tools/palettes/InkStitch Isacord Polyester.gpl` via a build script. This
   kills the blueprint's own worry that "every later chart change invalidates
   the goldens": the chart never changes again.
2. **Synthetic test logos, not found art.** Generated deterministically by
   `tools/make_test_logo.py` (committed as PNGs in `testdata/`): known
   geometry lets tests assert exact structure, zero licensing questions, and
   they seed the golden suite. Two variants: white-background JPEG-like PNG
   and transparent-alpha PNG of the same art. Art contains: a filled circle
   (blob→fill later), a ring (hole preservation), a thin bar ~2mm (satin-width
   candidate), a sub-1.5mm dot (must be dropped w/ warning), two touching
   shapes in different colors, anti-aliased edges everywhere (exercises AA
   handling), drawn in 5 flat colors + white bg.

## Package layout (new top-level dir in the EMB-Bot repo)

```
digitizer/
  pyproject.toml          # digitizer-core; deps: numpy, opencv-python-headless,
                          # scikit-image, scipy, shapely; dev: pytest
  README.md               # what/why/how to run + license policy note
  .gitignore              # .venv/, __pycache__/, debug_out/, *.egg-info
  digitizer_core/
    __init__.py
    config.py             # PipelineConfig dataclass: target_width_mm,
                          # max_colors=12, seed=0, min_detail_mm=1.5,
                          # bg_tolerance, aa_iterations, simplify_tol_mm=0.2 …
    threads.py            # Thread dataclass, Lab ΔE (CIE76) nearest, snap+merge
    threads_isacord.py    # GENERATED full Isacord chart (script below)
    stage1_prep.py        # load (alpha-aware), background mask, denoise, upscale
    stage2_quantize.py    # Lab k-means (seeded), auto-k, AA reassignment, snap
    stage3_segment.py     # Segmenter ABC + ClassicalSegmenter; small-region absorb
    stage4_vectorize.py   # contours w/ holes → simplified shapely polys, mm space
    regions.py            # Region dataclass + geometry-stable shape_id
    warnings_codes.py     # enumerated codes (machine-readable from day one)
    pipeline.py           # run_stages(image_bytes|path, config) → PipelineResult
    debugviz.py           # per-stage PNG dumps when debug_dir set
  tools/
    make_test_logo.py     # deterministic synthetic logo generator
    gen_isacord.py        # .gpl → threads_isacord.py
  testdata/
    logo_whitebg.png, logo_alpha.png   (committed goldens)
  tests/
    test_threads.py test_stage1.py test_stage2.py test_stage3.py
    test_stage4.py test_pipeline.py
```

## Stage contracts

**Units rule:** pixels through stage 3; stage 4 output converts to the JSON
contract's space — **mm floats, origin at design center, y-axis DOWN**. The
px→mm factor comes from `target_width_mm / artwork_px_width` where artwork
width is the non-background bbox width (established in stage 1).

- **Stage 1** `prep(image_bytes, cfg) -> Prep{rgb: HxWx3 u8, bg_mask: HxW bool,
  px_per_mm: float, warnings}`
  - Alpha present → bg = alpha < 128 (blueprint: transparent never stitched).
  - No alpha → border flood: dominant border color (mode of border ring in
    quantized Lab), flood-fill inward with Lab tolerance, **border-connected
    only**. Guard (v2.1): erode the foreground convex hull by a margin
    (~3 mm equivalent); flooded pixels deep inside → `BACKGROUND_UNCERTAIN`
    warning (region still masked, review UI decides).
  - Bilateral denoise (edge-preserving, light).
  - If px_per_mm < ~10 (i.e. <0.1 mm/px is NOT met — floor: resolution should
    give ≥ ~4 px per mm at target size) → Lanczos upscale to reach it, capped
    at 4×; below that after cap → `INPUT_LOW_RESOLUTION` warning.
- **Stage 2** `quantize(prep, cfg) -> Quant{labels: HxW int, palette:
  [ThreadRef], warnings}`
  - Foreground pixels only (bg excluded from clustering).
  - Convert to Lab (skimage or cv2 — pick ONE and pin; Lab space per blueprint).
  - `cv2.setRNGSeed(cfg.seed)` before `cv2.kmeans` (attempts=5, KMEANS_PP);
    auto-k: run k=2..min(12, distinct-ish colors), pick elbow (inertia
    improvement < threshold). Deterministic given fixed seed.
  - AA-halo pass: edge pixels (3×3 neighborhood has ≥2 labels) get majority
    label of non-edge neighbors, iterated cfg.aa_iterations (2); clusters
    whose members are >90% edge pixels are dissolved into nearest cluster
    (phantom blend colors).
  - Snap each cluster center to nearest Isacord thread (ΔE CIE76 in Lab);
    clusters landing on the same thread MERGE. Cap check: if post-merge count
    > cfg.max_colors → keep the max_colors largest by pixel count, reassign
    the rest to nearest kept thread, warn `COLOR_CAP_APPLIED`.
- **Stage 3** `segment(quant, prep, cfg) -> [RegionMask{mask, thread_idx}]`
  - `Segmenter` ABC (`segment(labels, rgb) -> [RegionMask]`);
    `ClassicalSegmenter`: per thread layer, `cv2.connectedComponents`.
  - Small-region rule: area < (cfg.min_detail_mm * px_per_mm)² → absorb into
    the neighboring region with the longest shared boundary; if none (isolated)
    → drop; either way count it and warn `DROPPED_SMALL_SHAPES` (n).
- **Stage 4** `vectorize(region_masks, prep, cfg) -> [Region]`
  - `cv2.findContours(RETR_CCOMP)` per mask → outer shell + holes;
    Douglas-Peucker at cfg.simplify_tol_mm (converted to px); shapely
    `Polygon(shell, holes)`, `make_valid`, drop empty.
  - Convert px → mm, translate so design bbox center = (0,0), y-down.
  - `Region{shape_id, polygon, thread_idx, area_mm2, source: "classical"}`
  - **shape_id** (contract requirement): `"S" + blake2s(round(centroid_x, 1),
    round(centroid_y, 1), round(area_mm2 ∕ tol), thread_number)[:8]` — stable
    across runs, tolerant of sub-0.1mm float jitter, and (later) tolerant
    across classical↔SAM boundary refinements.
- **PipelineResult**: `{regions, background: {detected, outline_mm, stitched:
  False}, palette, px_per_mm, warnings: [{code, message}], debug_dir}`

## Debug artifacts (cfg.debug_dir)

stage1_bg.png (bg mask overlay), stage1_denoised.png, stage2_labels.png
(random-color label viz), stage2_snapped.png (thread-color rendering),
stage3_regions.png (per-region outline overlay), stage4_vectors.png (polygons
+ holes drawn over faded source). These are the visual record Kent reviews.

## Tests (pytest, all offline, all deterministic)

1. Chart: generated Isacord module has ≥390 entries, all with number/name/rgb;
   nearest-thread on exact chart colors returns themselves.
2. Stage 1: white-bg logo → bg detected, excluded, NOT uncertain; alpha logo →
   same fg mask (IoU ≥ 0.99 vs white-bg variant); a white shape TOUCHING the
   border (third fixture) → `BACKGROUND_UNCERTAIN` fires.
3. Stage 2: exactly 5 thread layers on the synthetic logo (AA halos minted no
   phantom layer); layer thread numbers stable across two runs; same result
   both runs (byte-identical labels).
4. Stage 3: known region count; the sub-1.5mm dot is gone + warning present;
   touching different-color shapes remain separate regions.
5. Stage 4: ring region polygon has exactly 1 hole; all polygons valid; total
   |design bbox width − target_width_mm| < 0.5; y-down orientation asserted
   (topmost art feature has smaller y than bottommost).
6. Pipeline: run twice → identical shape_ids, areas, warnings; runs from bytes
   and from path agree.
7. Determinism canary: pipeline hash (sorted shape_ids + areas rounded) pinned
   as a golden value in-test (regenerate intentionally only).

## Environment

Windows, Python 3.14.6 (`C:\Python314`), venv at `digitizer/.venv` (gitignored).
RISK: cp314 wheels for opencv-python-headless — being verified in parallel; if
unavailable, fall back to installing Python 3.12 alongside and pinning the venv
to it (document in README). PyTorch/cp314 is a step-2 concern, noted now.

## Non-goals for step 1 (resist creep)

Preflight scoring (step 9 hardening; only structural warnings here), SAM
(step 2), stitch planning/underlay/pull comp (steps 3–6), pyembroidery export
(step 3/8), FastAPI (step 8), EMB-Bot UI (step 10).
