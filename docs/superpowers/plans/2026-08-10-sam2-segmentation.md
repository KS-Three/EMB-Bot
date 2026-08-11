# SAM2 Photo Segmentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give photo-classified designs (`photo_subject` / `photo_scene`) an optional SAM2-backed region former that runs in its own isolated venv as a subprocess, and degrades silently to today's SLIC+RAG segmenter whenever SAM2 is missing, slow, or broken.

**Architecture:** Three moving parts. (1) The `kept regions -> Quant` tail of `stage2_photo_segment.segment()` — mean-Lab color, class weights, `select_palette`, spool dedupe, label array, warnings, debug viz — is extracted into one shared function `kept_masks_to_quant()` that both segmenters call, proven byte-identical against a pre-refactor golden. (2) A standalone `sam2_worker.py` runs SAM2's `SAM2AutomaticMaskGenerator` under an isolated venv (`digitizer/sam2_isolated/`), resolves SAM2's overlapping instance masks into one non-overlapping `(H, W)` int32 label map, and writes it as an `.npz`. (3) A never-raises seam `sam2_segment_seam()` shells out to that worker with an explicit `subprocess.run(timeout=…)`, turns the label map into `RegionMask`s, runs them through the same `resolve_small_regions` floor the classical path uses, and calls the shared tail. `pipeline.run_stages` tries the seam only for photo classes with the opt-in flag on, and falls back to `photo_segment()` with a warning code on any failure.

**Tech Stack:** Python 3.12, numpy, OpenCV (`opencv-contrib-python-headless`), scikit-image, pytest. Isolated venv only: PyTorch (CPU wheels), torchvision, Meta's `sam2` package installed from `github.com/facebookresearch/sam2`, `hydra-core`, `iopath`, `opencv-python-headless`, Pillow.

## Global Constraints

- SAM2 engages **only** when `classification.class_ in ("photo_subject", "photo_scene")`. `"gradient"` must NOT trigger SAM2 — it keeps routing to `stage2_photo_segment.segment()` (SLIC+RAG) exactly as today. `"flat"` never reaches this code path at all (`stage2_quantize.quantize`, untouched).
- SAM2's weights and dependencies live in an **isolated, optional venv** at `digitizer/sam2_isolated/venv/`, never in the shared `digitizer/.venv`. Checkpoint downloads on first real use into a cache dir outside the repo. Neither the venv nor the checkpoint is committed.
- When SAM2 is unavailable for **any** reason (venv not built, worker script missing, checkpoint download failed, subprocess crash, subprocess timeout, unusable output), fall back **silently** to `stage2_photo_segment.segment()`. The job completes. A warning code records why. Never a hard error, never an exception escaping the seam.
- Default checkpoint tier is `"tiny"` (SAM 2.1 Hiera-Tiny). This machine has ~13.5 GB free disk and **no GPU** — CPU-only inference. Disk footprint and per-image latency outrank maximum segmentation accuracy.
- SAM2 is installed **from Meta's own GitHub repo** (`https://github.com/facebookresearch/sam2`, distribution name `SAM-2`, import package `sam2`). **NEVER** `pip install sam2` — that is an unrelated third-party PyPI package.
- The subprocess call MUST pass an explicit `timeout=` to `subprocess.run`. `digitizer_service/jobs.py`'s `JobRegistry` is a single-worker `ThreadPoolExecutor` with no per-job timeout and no cancellation of a running job — this `timeout=` is the only thing standing between a hung SAM2 call and a starved job queue.
- Every new config field name follows `config.py`'s existing convention (`photo_prep_background_removal`, `photo_prep_background_removal_model`, `photo_prep_background_removal_timeout_s`): `<feature-family>_<knob>`, snake_case, `_s` suffix on second-valued timeouts, documented with a comment block explaining the gate and the failure mode.
- Warning codes are **append-only** (`warnings_codes.py` header: "never renumber or reuse").
- The classical SLIC+RAG lane's output must not change by one pixel or one label after the Task 1 refactor. The `slic_segments` warning field name is kept for the SAM2 path too — `stage2_photo_segment.py`'s own module docstring already establishes that these names are deliberately algorithm-neutral ("whatever the oversegmentation step produced").
- Run tests as `.venv/Scripts/python -m pytest` from `digitizer/` (never the bare `pytest` script — `digitizer/README.md` line 115 explains why).
- Do NOT use PowerShell regex round-trips (`(Get-Content -Raw) -replace … | Set-Content`) on any source file in this repo — it silently corrupts UTF-8 (repo `CLAUDE.md` hard-stop fact #3). Use the Edit/Write tools.
- **Verify before Task 1 executes:** the exact SAM2 install command in `digitizer/sam2_isolated/README.md` was written against `github.com/facebookresearch/sam2`'s README/INSTALL.md as fetched 2026-08-10. Re-check Meta's current README before running it — repo name, checkpoint URLs and config paths are the things most likely to have moved.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `digitizer/digitizer_core/stage2_photo_segment.py` (modify) | Keeps the SLIC+RAG oversegmentation/merge front half. Gains `kept_masks_to_quant()` — the shared `kept regions -> Quant` tail both segmenters call. |
| `digitizer/tools/capture_photo_lane_golden.py` (create) | One-off capture of `segment()`'s own `Quant` on the photo/gradient fixtures, run BEFORE the extraction. |
| `digitizer/testdata/photo_lane_segment_golden.json` (create, generated) | The captured pre-refactor snapshot. |
| `digitizer/tests/test_photo_lane_byte_identical.py` (create) | Asserts the classical lane's stage-2 output still matches that snapshot exactly. |
| `digitizer/sam2_isolated/README.md` (create) | What the isolated venv is, how to build it, where the checkpoint comes from, how to sanity-check it by hand. |
| `digitizer/sam2_isolated/requirements.txt` (create) | The isolated venv's non-torch, non-sam2 pins. |
| `digitizer/digitizer_core/sam2_worker.py` (create) | Standalone bridge script. Zero `digitizer_core` imports. Loads SAM2, runs automatic mask generation, resolves overlaps, writes an `.npz`. |
| `digitizer/digitizer_core/stage2_sam2_segment.py` (create) | Module-level path constants, `sam2_segmentation_unavailable_reason()`, and `sam2_segment_seam()` — the never-raises caller-side seam. |
| `digitizer/digitizer_core/config.py` (modify) | The five `photo_segment_sam2*` fields. |
| `digitizer/digitizer_core/warnings_codes.py` (modify) | `PHOTO_SAM2_SEGMENTED`, `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`. |
| `digitizer/digitizer_core/pipeline.py` (modify) | Stage-2 dispatch: try the seam for photo classes, fall back with a warning. |
| `digitizer/.gitignore` (modify) | Ignore `sam2_isolated/venv/`. |
| `digitizer/README.md` (modify) | One paragraph pointing at `sam2_isolated/`. |
| `digitizer/tests/test_sam2_worker.py` (create) | The worker's CLI contract and isolation, testable with no SAM2 installed. |
| `digitizer/tests/test_sam2_segment.py` (create) | Availability check, seam failure modes, seam happy path against a synthetic worker output, pipeline gate + fallback. |

---

### Task 1: Extract the shared `kept regions -> Quant` tail, proven byte-identical

**Files:**
- Create: `digitizer/tools/capture_photo_lane_golden.py`
- Create: `digitizer/tests/test_photo_lane_byte_identical.py`
- Create (generated): `digitizer/testdata/photo_lane_segment_golden.json`
- Modify: `digitizer/digitizer_core/stage2_photo_segment.py:1324-1477`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  ```python
  # digitizer_core/stage2_photo_segment.py
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
  ) -> Quant: ...
  ```
- Also produces, for the test module: `FIXTURES: list[str]`, `_snapshot(key: str) -> dict`, `GOLDEN_PATH: Path` in `tests/test_photo_lane_byte_identical.py`.

**This task inverts red-green on purpose.** It is a pure extraction: the test must be GREEN before the refactor and GREEN after. A test that goes red first here would mean the golden was captured wrong, not that the refactor is missing. Steps 1-4 build and prove the harness against unmodified code; steps 5-7 do the extraction and re-prove.

- [ ] **Step 1: Write the byte-identity test module**

Create `digitizer/tests/test_photo_lane_byte_identical.py`:

```python
"""The Task-1 hard invariant: extracting `stage2_photo_segment.segment()`'s
`kept regions -> Quant` tail into the shared `kept_masks_to_quant()` must not
move ONE pixel or ONE label on the classical SLIC+RAG lane.

`testdata/photo_lane_segment_golden.json` is captured by
`tools/capture_photo_lane_golden.py`, run once BEFORE the extraction lands.
This module re-runs the same fixtures through today's `segment()` and asserts
an exact match on the full `Quant`: the label array's sha256, the thread
index list, the pre-snap cluster colors, and every warning dict.

SCOPE, deliberately narrow (the lesson `tests/test_shapefield_byte_identical.py`
records in its own HISTORY section): this golden pins STAGE 2's output only,
not the whole pipeline's. A frozen whole-pipeline snapshot goes stale the
first time anything downstream legitimately changes, and then tests
"nothing anywhere ever changes" instead of the claim it was written for.
Stage 2's own output moving IS this file's claim, so it only goes red for a
real stage-2 change — at which point the change's author re-runs the capture
script deliberately, the same way `testdata/flat_lane_golden.json` documents
its own two deliberate re-captures.

If this goes red during the extraction, the extraction is wrong — not this
test.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import segment

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
GOLDEN_PATH = TESTDATA / "photo_lane_segment_golden.json"

# Every committed fixture that can route through `segment()`, chosen for
# structural variety rather than count: two real busy gradient designs (the
# pair `MERGE_DELTAE00_THRESH` was itself tuned against), the synthetic blob
# fixture, a fur ramp, the enclosed-white-icon repro (the ONLY fixture that
# exercises the tail's separate enclosed population), and a photo-class stub.
# The trailing "#bgmask" key re-runs one fixture with a real `bg_mask`
# argument so the tail's `_region_classes` subject/background branch — and
# therefore `palette.region_weight`'s class multipliers — is covered too.
FIXTURES = [
    "photo/drone_render.png",
    "photo/summit_badge.png",
    "photo/region_blobs.png",
    "photo/fur_ramp.png",
    "photo/repro_gradient_white_icon.png",
    "photo/photo_subject_stub.png",
    "photo/region_blobs.png#bgmask",
]

GOLDEN: dict = (
    json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    if GOLDEN_PATH.is_file()
    else {}
)


def _jsonable(value):
    """numpy scalars/arrays out of the warning dicts become plain JSON."""
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_jsonable(v) for v in value.tolist()]
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _synthetic_bg_mask(shape: tuple[int, int]) -> np.ndarray:
    """A deterministic stand-in for a real rembg subject/background mask:
    the left half is background. Nothing about it needs to be plausible —
    it exists so the tail's class-weight branch runs on a fixed input."""
    mask = np.zeros(shape, bool)
    mask[:, : shape[1] // 2] = True
    return mask


def _snapshot(key: str) -> dict:
    name, _, variant = key.partition("#")
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(TESTDATA / name, cfg)
    bg_mask = _synthetic_bg_mask(p.rgb.shape[:2]) if variant == "bgmask" else None
    q = segment(p, cfg, face_regions=None, bg_mask=bg_mask)
    return {
        "shape": list(q.labels.shape),
        "labels_dtype": str(q.labels.dtype),
        "labels_sha256": hashlib.sha256(
            np.ascontiguousarray(q.labels, dtype=np.int32).tobytes()
        ).hexdigest(),
        "thread_indices": [int(i) for i in q.thread_indices],
        "cluster_rgb": [
            [round(float(v), 6) for v in row]
            for row in np.asarray(q.cluster_rgb, np.float64).reshape(-1, 3)
        ],
        "warnings": [_jsonable(w) for w in q.warnings],
    }


@pytest.mark.parametrize("fixture", FIXTURES)
def test_photo_lane_stage2_is_byte_identical_to_the_pre_refactor_golden(fixture):
    assert GOLDEN, f"{GOLDEN_PATH} missing — run tools/capture_photo_lane_golden.py"
    assert _snapshot(fixture) == GOLDEN[fixture]


def test_golden_file_actually_covers_something():
    """A guard against the golden silently becoming empty (a capture-script
    bug) and this whole module passing vacuously — the same guard
    tests/test_flat_lane_byte_identical.py keeps over its own golden."""
    assert sorted(GOLDEN.keys()) == sorted(FIXTURES)
    for name, snap in GOLDEN.items():
        assert snap["thread_indices"], f"{name}: golden has zero thread colors"
        assert snap["warnings"], f"{name}: golden has zero warnings"
```

- [ ] **Step 2: Write the capture tool**

Create `digitizer/tools/capture_photo_lane_golden.py`:

```python
#!/usr/bin/env python
"""One-off: capture the pre-refactor photo-lane stage-2 golden.

Run ONCE, from `digitizer/`, BEFORE `stage2_photo_segment.segment()`'s
`kept regions -> Quant` tail is extracted into `kept_masks_to_quant()`:

    .venv/Scripts/python tools/capture_photo_lane_golden.py

`tests/test_photo_lane_byte_identical.py` then re-runs the same fixtures
through the post-extraction code and asserts an exact match. Do not re-run
this script to make that test go green — that defeats the invariant it
exists to pin. Re-run it only for a change that deliberately, knowingly
moves stage 2's own output, and say so in the commit message (see
`testdata/flat_lane_golden.json`'s own documented re-captures for the
precedent).

The snapshot helper lives in the test module, not here, so the two can
never drift apart.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.test_photo_lane_byte_identical import (  # noqa: E402
    FIXTURES,
    GOLDEN_PATH,
    _snapshot,
)


def main() -> None:
    golden = {key: _snapshot(key) for key in FIXTURES}
    GOLDEN_PATH.write_text(json.dumps(golden, indent=1), encoding="utf-8")
    for key, snap in golden.items():
        print(
            f"{key}: {len(snap['thread_indices'])} threads, "
            f"{len(snap['warnings'])} warnings, labels {snap['labels_sha256'][:12]}"
        )


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Capture the golden against UNMODIFIED `segment()`**

Run, from `digitizer/`:

```bash
.venv/Scripts/python tools/capture_photo_lane_golden.py
```

Expected: seven lines printed, one per key in `FIXTURES`, each with a non-zero thread count, and `testdata/photo_lane_segment_golden.json` on disk. This takes a couple of minutes — `drone_render.png` alone runs SEEDS over a busy 900x900 raster.

- [ ] **Step 4: Run the new test against UNMODIFIED `segment()` — it must PASS**

Run: `.venv/Scripts/python -m pytest tests/test_photo_lane_byte_identical.py -q`
Expected: 8 passed. A failure here means the snapshot is not deterministic run-to-run, which must be fixed before the extraction — the refactor cannot be proven safe against a moving target.

Commit the harness before touching any source:

```bash
git add digitizer/tools/capture_photo_lane_golden.py digitizer/tests/test_photo_lane_byte_identical.py digitizer/testdata/photo_lane_segment_golden.json
git commit -m "test: pin stage-2 photo-lane output before the kept->Quant extraction"
```

- [ ] **Step 5: Add `kept_masks_to_quant()` to `stage2_photo_segment.py`**

Insert this function immediately above `def segment(` (currently line 1196), after `_region_classes`. It is the existing tail verbatim, with four mechanical changes and nothing else: locals that were computed at the top of `segment()` (`h`, `w`, `flat_rgb`, `enclosed`, `has_enclosed`) are recomputed from `p` (all are pure functions of `p`, and `segment()` never mutates `p.rgb`); `slic_count` is now the `raw_count` parameter; the message's unit noun is the `raw_unit_label` parameter, defaulting to the existing `"superpixels"`; and the SLIC debug viz is guarded on `oversegment_labels is not None`, which the classical caller always satisfies.

```python
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
    """
    h, w = p.rgb.shape[:2]
    flat_rgb = p.rgb.reshape(-1, 3)
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    slic_count = raw_count

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
        rgb_to_lab(p.rgb[r.mask].reshape(-1, 3).mean(axis=0, keepdims=True))[0]
        for r in kept
    ]
    classes = _region_classes(kept, face_regions, bg_mask)
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
            max_excess_de00=round(selection.max_excess_de00, 3),
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
    )
```

- [ ] **Step 6: Replace the tail of `segment()` with a call to it**

In `segment()`, delete everything from the `# --- 6. Palette selection` comment block (currently line 1324) through the closing `)` of the `return Quant(...)` (currently line 1477), and replace it with:

```python
    return kept_masks_to_quant(
        p,
        cfg,
        kept,
        floor_warnings,
        face_regions=face_regions,
        bg_mask=bg_mask,
        raw_count=slic_count,
        merged_count=merged_count,
        oversegment_labels=slic_labels,
    )
```

The line immediately above the replacement stays untouched:

```python
    kept, floor_warnings = resolve_small_regions(regions, cfg, p.px_per_mm)
```

- [ ] **Step 7: Run the byte-identity test — it must still PASS**

Run: `.venv/Scripts/python -m pytest tests/test_photo_lane_byte_identical.py -q`
Expected: 8 passed, identical to Step 4. Any failure means the extraction changed behavior — fix the extraction, never the golden.

Then the surrounding suites:

Run: `.venv/Scripts/python -m pytest tests/test_stage2_photo_segment.py tests/test_flat_lane_byte_identical.py tests/test_photo_prep.py tests/test_background_removal.py tests/test_face_priors.py -q`
Expected: all pass, no new failures. (`tests/test_flat_lane_byte_identical.py::test_flat_lane_is_byte_identical_to_the_pre_change_golden[logo_alpha.png]` is a known pre-existing environment failure documented in `COOKBOOK.md` — it must not go from pass to fail, but if it was already failing before this task it stays failing.)

- [ ] **Step 8: Commit**

```bash
git add digitizer/digitizer_core/stage2_photo_segment.py
git commit -m "refactor: extract kept_masks_to_quant() shared by every photo region former"
```

---

### Task 2: Isolated SAM2 venv scaffolding and the standalone worker script

**Files:**
- Create: `digitizer/sam2_isolated/README.md`
- Create: `digitizer/sam2_isolated/requirements.txt`
- Create: `digitizer/digitizer_core/sam2_worker.py`
- Modify: `digitizer/.gitignore`
- Test: `digitizer/tests/test_sam2_worker.py`

**Interfaces:**
- Consumes: nothing from Task 1.
- Produces, for Task 4:
  - CLI contract: `<venv python> sam2_worker.py <input_image> <output_npz> <checkpoint_tier> <points_per_side> <min_mask_region_area>` — exactly 5 arguments after the script name.
  - Exit codes: `0` success, `2` bad usage/arguments, `3` import failed, `4` checkpoint unavailable, `5` mask generation failed, `6` writing the output failed.
  - Output `.npz` keys: `labels` `(H, W) int32` (`-1` = no mask covered this pixel, otherwise a label id), `area` `(N,) int64`, `predicted_iou` `(N,) float32`, `stability_score` `(N,) float32`, `raw_mask_count` `int64` scalar. Arrays are indexed by label id.
  - Module constants: `CHECKPOINTS: dict[str, tuple[str, str]]` (tier -> (checkpoint filename, hydra config name)), `CHECKPOINT_BASE_URL: str`.

**API-verification note for the implementer.** The following were read from `github.com/facebookresearch/sam2`'s `main` branch on 2026-08-10 and are used verbatim below: `SAM2AutomaticMaskGenerator.__init__`'s keyword names and defaults, its `generate(image: np.ndarray) -> List[Dict[str, Any]]` signature, the mask-record keys (`segmentation`, `area`, `bbox`, `predicted_iou`, `point_coords`, `stability_score`, `crop_box`), `build_sam2(config_file, ckpt_path=None, device="cuda", mode="eval", hydra_overrides_extra=[], apply_postprocessing=True, **kwargs)`, the fact that `sam2/__init__.py` registers the hydra config module so `config_file` is passed as a plain `configs/sam2.1/…yaml` string with no `initialize()` call of your own, and the checkpoint URLs. **What was NOT verified:** Meta's own `notebooks/automatic_mask_generator_example.ipynb` could not be read in full, so whether their AMG example passes `apply_postprocessing=False` is unconfirmed. The code below omits the argument and takes `build_sam2`'s default, which is what the repo README's own image-prediction snippet does. If the first real run (Task 6) produces poor masks, trying `apply_postprocessing=False` is the first thing to check against Meta's current notebook.

- [ ] **Step 1: Write the worker's CLI-contract test**

Create `digitizer/tests/test_sam2_worker.py`:

```python
"""`digitizer_core/sam2_worker.py`'s contract, tested WITHOUT a SAM2 install.

The worker's real work (loading SAM2, running automatic mask generation)
cannot run in the shared venv by design — that is the whole point of
`digitizer/sam2_isolated/`. What IS testable here, and what this file pins,
is everything the caller depends on that happens before any heavy import:
the argv contract, the exit codes for every argument-level failure, the
checkpoint table, and the isolation guarantee itself (zero digitizer_core
imports, so the script runs standalone in a venv with no digitizer_core
installed). The real end-to-end run is Task 6's manual acceptance step.
"""
from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

from digitizer_core import sam2_worker

WORKER = Path(sam2_worker.__file__).resolve()


def _run(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(WORKER), *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


def test_wrong_argument_count_exits_2():
    proc = _run("in.png", "out.npz")
    assert proc.returncode == 2
    assert "usage: sam2_worker.py" in proc.stderr


def test_unknown_checkpoint_tier_exits_2():
    proc = _run("in.png", "out.npz", "enormous", "16", "9")
    assert proc.returncode == 2
    assert "unknown checkpoint tier" in proc.stderr


def test_non_numeric_grid_argument_exits_2():
    proc = _run("in.png", "out.npz", "tiny", "sixteen", "9")
    assert proc.returncode == 2
    assert "bad numeric argument" in proc.stderr


def test_zero_points_per_side_exits_2():
    proc = _run("in.png", "out.npz", "tiny", "0", "9")
    assert proc.returncode == 2
    assert "points_per_side must be >= 1" in proc.stderr


@pytest.mark.skipif(
    importlib.util.find_spec("sam2") is not None,
    reason="sam2 is importable in this interpreter, so the import cannot fail",
)
def test_missing_sam2_dependency_exits_3():
    """Run under the SHARED venv, where sam2/torch are deliberately absent:
    the worker must report an honest import failure with exit code 3, not
    a traceback, so the seam can turn it into one plain-English reason."""
    proc = _run("in.png", "out.npz", "tiny", "16", "9")
    assert proc.returncode == 3
    assert "sam2_worker: import failed" in proc.stderr


def test_worker_imports_nothing_from_digitizer_core():
    """The isolation guarantee: this script runs under a venv that has no
    digitizer_core installed, so a single package-relative or absolute
    digitizer_core import would break it at runtime in exactly the
    environment it exists to serve. Same guarantee rembg_worker.py's own
    docstring makes."""
    tree = ast.parse(WORKER.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(a.name for a in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "relative import in a standalone worker script"
            imported.append(node.module or "")
    assert not [m for m in imported if m.split(".")[0] == "digitizer_core"]


def test_checkpoint_table_is_meta_hosted_and_self_consistent():
    """Guards the one substitution this integration must never suffer: the
    unrelated third-party PyPI package named `sam2`, or a mirror of its
    weights. Meta's own release host is the only allowed source."""
    assert sam2_worker.CHECKPOINT_BASE_URL.startswith(
        "https://dl.fbaipublicfiles.com/segment_anything_2/"
    )
    assert sam2_worker.CHECKPOINTS["tiny"] == (
        "sam2.1_hiera_tiny.pt",
        "configs/sam2.1/sam2.1_hiera_t.yaml",
    )
    for tier, (filename, config_name) in sam2_worker.CHECKPOINTS.items():
        assert filename.endswith(".pt"), tier
        assert config_name.startswith("configs/sam2.1/"), tier
        assert config_name.endswith(".yaml"), tier
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_worker.py -q`
Expected: collection error — `ImportError: cannot import name 'sam2_worker' from 'digitizer_core'`.

- [ ] **Step 3: Write the worker script**

Create `digitizer/digitizer_core/sam2_worker.py`:

```python
"""Standalone SAM2 automatic-mask-generation worker.

RUNS IN THE ISOLATED VENV documented at digitizer/sam2_isolated/README.md —
never under the shared digitizer/.venv, and never imported for its heavy
dependencies by the main digitizer_core package. SAM2 needs PyTorch and
torchvision (>= 2.5.1 / >= 0.20.1 per Meta's INSTALL.md); the shared venv
exists to run a deterministic, offline, CPU-only geometry pipeline against
exact-pinned numpy/OpenCV that feed golden tests, and dropping a
multi-gigabyte deep-learning stack into it would put those pins at the mercy
of torch's own transitive resolution. Same isolation, same reason, and the
same subprocess bridge as rembg_worker.py — see that file and
digitizer/rembg_isolated/README.md for the pattern this mirrors.

This script is invoked as a subprocess by
`stage2_sam2_segment.sam2_segment_seam`, pointed at the isolated venv's own
python interpreter. It must import NOTHING from digitizer_core, only the
standard library plus the isolated venv's own installed packages (numpy,
torch, PIL, sam2), so it runs standalone with no digitizer_core install
there.

Usage:
    <isolated venv python> sam2_worker.py \\
        <input_image> <output_npz> <checkpoint_tier> \\
        <points_per_side> <min_mask_region_area>

  * <checkpoint_tier> is a key of CHECKPOINTS below ("tiny" is the shipped
    default: smallest disk footprint and fastest CPU inference, which is
    what an embroidery-scale flat-region split needs — not fine-grained
    natural-scene accuracy).
  * <points_per_side> is SAM2's own prompt-grid density.
  * <min_mask_region_area> is a PIXEL area floor handed straight to SAM2's
    `min_mask_region_area`; the caller derives it from the same
    `(cfg.min_detail_mm * px_per_mm) ** 2` formula every other
    "too small to sew" floor in this codebase uses.

Output: a compressed .npz at <output_npz> with
  * labels           (H, W) int32 — per-pixel label id, -1 where no SAM2
                     mask covered the pixel. SAM2's automatic generator
                     returns OVERLAPPING instance masks and does not tile
                     the image; this array is the resolved, non-overlapping
                     assignment (see _paint_labels for the priority rule).
  * area             (N,) int64   — SAM2's own reported mask area, by label id
  * predicted_iou    (N,) float32 — SAM2's own quality estimate, by label id
  * stability_score  (N,) float32 — SAM2's own stability score, by label id
  * raw_mask_count   int64 scalar — how many masks the generator returned
                     before overlap resolution

Exit code 0 = success, npz written. Any other exit code means failure and
the reason is on stderr: 2 = bad arguments, 3 = import failed, 4 = the
checkpoint could not be cached, 5 = mask generation failed, 6 = writing the
output failed. The caller treats ANY nonzero exit code, and any timeout, as
"unavailable" and degrades silently to the classical SLIC+RAG segmenter —
never a hard pipeline error, since the isolated venv's presence, network
status and checkpoint cache are environment facts, not caller mistakes.
"""
from __future__ import annotations

import os
import sys
import tempfile
import urllib.request
from pathlib import Path

# SAM 2.1 checkpoints, from Meta's own release host. tier -> (checkpoint
# filename, hydra config name). The config names are resolved by hydra
# against the `sam2` package's own config module, which `sam2/__init__.py`
# registers on import — they are NOT filesystem paths and must be passed to
# build_sam2 exactly as written, extension included.
CHECKPOINTS: dict[str, tuple[str, str]] = {
    "tiny": ("sam2.1_hiera_tiny.pt", "configs/sam2.1/sam2.1_hiera_t.yaml"),
    "small": ("sam2.1_hiera_small.pt", "configs/sam2.1/sam2.1_hiera_s.yaml"),
    "base_plus": ("sam2.1_hiera_base_plus.pt", "configs/sam2.1/sam2.1_hiera_b+.yaml"),
    "large": ("sam2.1_hiera_large.pt", "configs/sam2.1/sam2.1_hiera_l.yaml"),
}
CHECKPOINT_BASE_URL = "https://dl.fbaipublicfiles.com/segment_anything_2/092824/"

# Seconds allowed for the FIRST-use checkpoint download. Deliberately shorter
# than the caller's own subprocess timeout so a stalled download reports a
# specific reason (exit 4) instead of dying anonymously as a timeout.
DOWNLOAD_TIMEOUT_S = 240


def _cache_dir() -> Path:
    """Where checkpoints live between runs. Outside the repo, and outside
    both venvs, so rebuilding either does not re-download ~150 MB. Honors
    SAM2_CHECKPOINT_DIR the way rembg honors U2NET_HOME."""
    env = os.environ.get("SAM2_CHECKPOINT_DIR")
    if env:
        return Path(env)
    return Path.home() / ".cache" / "sam2"


def _ensure_checkpoint(tier: str) -> Path:
    """Return the cached checkpoint path, downloading it on first use.

    Downloads to a sibling .part file and renames on success, so an
    interrupted or truncated download is never left behind wearing the real
    filename — the failure mode that would otherwise poison every later run
    with an unloadable cache entry.
    """
    filename = CHECKPOINTS[tier][0]
    dest_dir = _cache_dir()
    dest = dest_dir / filename
    if dest.is_file() and dest.stat().st_size > 0:
        return dest

    dest_dir.mkdir(parents=True, exist_ok=True)
    url = CHECKPOINT_BASE_URL + filename
    handle, tmp_name = tempfile.mkstemp(dir=str(dest_dir), suffix=".part")
    os.close(handle)
    tmp = Path(tmp_name)
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_S) as response:
            with tmp.open("wb") as out:
                while True:
                    chunk = response.read(1 << 20)
                    if not chunk:
                        break
                    out.write(chunk)
        if tmp.stat().st_size == 0:
            raise OSError(f"downloaded 0 bytes from {url}")
        os.replace(tmp, dest)
    finally:
        if tmp.exists():
            tmp.unlink()
    return dest


def _paint_labels(records, shape, np):
    """Resolve SAM2's overlapping instance masks into one non-overlapping
    label array, plus its per-label stat arrays.

    PRIORITY RULE: paint in DESCENDING area order, so a smaller mask always
    lands on top of any larger mask it sits inside. This is the convention
    SAM's own visualizations use, and it is the right one for embroidery:
    the nested detail (an eye inside a face, a badge inside a jacket) is
    exactly the region that must survive as its own sewable shape, while the
    enclosing region loses only the pixels it can most afford. Ranking by
    `predicted_iou` instead would let one large confident mask erase every
    small feature inside it — the opposite failure. Ties break on
    `predicted_iou` descending, then on the generator's own ordering, so the
    output is deterministic for a fixed input.

    Label ids are assigned in paint order, so label 0 is the largest mask.
    """
    order = sorted(
        range(len(records)),
        key=lambda i: (
            -int(records[i]["area"]),
            -float(records[i]["predicted_iou"]),
            i,
        ),
    )
    labels = np.full(shape, -1, np.int32)
    area = np.zeros(len(order), np.int64)
    predicted_iou = np.zeros(len(order), np.float32)
    stability_score = np.zeros(len(order), np.float32)
    for new_id, i in enumerate(order):
        record = records[i]
        labels[np.asarray(record["segmentation"], bool)] = new_id
        area[new_id] = int(record["area"])
        predicted_iou[new_id] = float(record["predicted_iou"])
        stability_score[new_id] = float(record["stability_score"])
    return labels, area, predicted_iou, stability_score


def main(argv: list[str]) -> int:
    if len(argv) != 6:
        print(
            "usage: sam2_worker.py <input_image> <output_npz> <checkpoint_tier> "
            "<points_per_side> <min_mask_region_area>",
            file=sys.stderr,
        )
        return 2

    in_path, out_path, tier = argv[1], argv[2], argv[3]
    if tier not in CHECKPOINTS:
        print(
            f"sam2_worker: unknown checkpoint tier {tier!r} "
            f"(known: {sorted(CHECKPOINTS)})",
            file=sys.stderr,
        )
        return 2
    try:
        points_per_side = int(argv[4])
        min_mask_region_area = int(argv[5])
    except ValueError as exc:
        print(f"sam2_worker: bad numeric argument: {exc}", file=sys.stderr)
        return 2
    if points_per_side < 1:
        print("sam2_worker: points_per_side must be >= 1", file=sys.stderr)
        return 2

    try:
        import numpy as np
        import torch
        from PIL import Image
        from sam2.automatic_mask_generator import SAM2AutomaticMaskGenerator
        from sam2.build_sam import build_sam2
    except Exception as exc:  # environment problem (missing deps), not logic
        print(f"sam2_worker: import failed: {exc}", file=sys.stderr)
        return 3

    try:
        checkpoint = _ensure_checkpoint(tier)
    except Exception as exc:
        print(f"sam2_worker: checkpoint unavailable: {exc}", file=sys.stderr)
        return 4

    try:
        image = np.array(Image.open(in_path).convert("RGB"))
        # CPU-only by construction: this machine has no GPU, and the isolated
        # venv installs CPU torch wheels. No autocast — bfloat16 autocast is a
        # CUDA-path optimization in Meta's own examples and buys nothing here.
        model = build_sam2(CHECKPOINTS[tier][1], str(checkpoint), device="cpu")
        generator = SAM2AutomaticMaskGenerator(
            model,
            points_per_side=points_per_side,
            points_per_batch=64,
            min_mask_region_area=max(0, min_mask_region_area),
            output_mode="binary_mask",
            multimask_output=True,
        )
        with torch.inference_mode():
            records = generator.generate(image)
    except Exception as exc:
        print(f"sam2_worker: mask generation failed: {exc}", file=sys.stderr)
        return 5

    try:
        labels, area, predicted_iou, stability_score = _paint_labels(
            records, image.shape[:2], np
        )
        np.savez_compressed(
            out_path,
            labels=labels,
            area=area,
            predicted_iou=predicted_iou,
            stability_score=stability_score,
            raw_mask_count=np.int64(len(records)),
        )
    except Exception as exc:
        print(f"sam2_worker: writing the output failed: {exc}", file=sys.stderr)
        return 6

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_worker.py -q`
Expected: 7 passed (or 6 passed / 1 skipped if `sam2` happens to be importable in the shared venv).

- [ ] **Step 5: Write the isolated venv's requirements file**

Create `digitizer/sam2_isolated/requirements.txt`:

```
# Isolated SAM2 venv — see README.md in this directory for what this is and
# why it is separate from digitizer/.venv.
#
# torch, torchvision and sam2 itself are NOT in this file, on purpose:
#   * torch/torchvision must come from PyTorch's CPU wheel index, not PyPI
#     (on Linux the PyPI torch wheel bundles CUDA and is several GB — this
#     machine has ~13.5 GB free and no GPU), so they need their own
#     --index-url and are installed by their own pip command in README.md.
#   * sam2 must come from Meta's GitHub repo. The PyPI package literally
#     named `sam2` is an UNRELATED third-party project — never install it.
#     See README.md for the exact git+https command.
#
# What IS here is the one dependency SAM2's own setup.py leaves out of its
# core install but its automatic mask generator needs: cv2, imported by
# sam2.utils.amg.remove_small_regions, which runs whenever
# min_mask_region_area > 0 — and the worker always passes a real min area
# derived from cfg.min_detail_mm. Headless, matching the shared venv's own
# choice, because nothing here ever opens a window.
opencv-python-headless>=4.7.0
```

- [ ] **Step 6: Write the isolated venv README**

Create `digitizer/sam2_isolated/README.md`:

```markdown
# Isolated SAM2 venv (photo region former — SAM2 lane)

SAM2 cannot be installed into the shared `digitizer/.venv`: it needs PyTorch
>= 2.5.1 and torchvision >= 0.20.1 (Meta's own `INSTALL.md`), a
multi-gigabyte dependency stack with its own numpy expectations. The shared
venv exists to run a deterministic, offline, CPU-only geometry pipeline
against exact-pinned `numpy==2.5.1` and `opencv-contrib-python-headless==5.0.0.93`
that feed golden tests — pins `pyproject.toml` says to "bump deliberately,
never by accident". Putting torch next to them hands that resolution to
torch's own transitive graph.

Same fix as `rembg_isolated/`, for the same reason: run SAM2 in its OWN venv
and talk to it as a subprocess. Nothing in `digitizer/.venv` changes.

`digitizer_core/stage2_sam2_segment.sam2_segment_seam` shells out to
`digitizer_core/sam2_worker.py` (a standalone script — no `digitizer_core`
imports, so it needs nothing installed here but torch, sam2 and their own
deps), running it under THIS directory's venv's python interpreter, never
the shared one.

## Build it

From the repo's `digitizer/` directory. Three pip commands, in this order —
they are separate on purpose (see `requirements.txt`'s own comment).

```
python3.12 -m venv sam2_isolated/venv
```

1. CPU-only torch, from PyTorch's own CPU wheel index (NOT PyPI — on Linux
   the PyPI wheel bundles CUDA and is several GB larger, and this machine
   has no GPU):

```
sam2_isolated/venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.5.1" "torchvision>=0.20.1"                                    # POSIX
sam2_isolated\venv\Scripts\pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.5.1" "torchvision>=0.20.1"   # Windows
```

2. SAM2 itself, from **Meta's own GitHub repo**. `SAM2_BUILD_CUDA=0` skips
   the optional CUDA extension, which needs a matching CUDA toolkit and a
   compiler and buys nothing on a CPU-only box — Meta's `INSTALL.md`
   documents both the env var and that skipping it "shouldn't affect the
   results in most cases".

```
SAM2_BUILD_CUDA=0 sam2_isolated/venv/bin/pip install \
    "git+https://github.com/facebookresearch/sam2.git"                      # POSIX
$env:SAM2_BUILD_CUDA=0; sam2_isolated\venv\Scripts\pip install "git+https://github.com/facebookresearch/sam2.git"   # Windows PowerShell
```

**Never `pip install sam2`.** The PyPI package with that exact name is an
unrelated third-party project. Meta's distribution is named `SAM-2` and is
only published on GitHub; the import package it provides is `sam2`.

3. The one remaining dependency SAM2's core install leaves out:

```
sam2_isolated/venv/bin/pip install -r sam2_isolated/requirements.txt        # POSIX
sam2_isolated\venv\Scripts\pip install -r sam2_isolated\requirements.txt    # Windows
```

That's it — no `digitizer_core` install needed in this venv (the worker
script is standalone by design). `stage2_sam2_segment.py` looks for the
interpreter at `sam2_isolated/venv/bin/python` (POSIX) or
`sam2_isolated/venv/Scripts/python.exe` (Windows) by default; nothing else
to configure.

**This venv is NOT committed** (see `digitizer/.gitignore`) and is a
workstation/deploy-time setup step, the same shape as building
`digitizer/.venv` or `rembg_isolated/venv`. Without it built,
`photo_segment_sam2` degrades to the documented fallback
(`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`): the photo lane uses the classical
SLIC+RAG region former, exactly as it does today. Every other part of the
pipeline is unaffected.

## Disk

Budget roughly 2-3 GB for this venv on top of the checkpoint. The machine
this was written on had 13.5 GB free (measured 2026-08-10) — enough, but not
by a comfortable margin. **Check `df -h` / free space again immediately
before building**, since other work may have consumed it since.

## The checkpoint

`sam2.1_hiera_tiny.pt` (the shipped default tier) is **not committed** — it
is far past the "couple hundred KB" line `digitizer_core/model_data/README.md`
draws for committed inference models. `sam2_worker.py` downloads it itself,
on first real use, from Meta's own release host
(`https://dl.fbaipublicfiles.com/segment_anything_2/092824/sam2.1_hiera_tiny.pt`)
into `~/.cache/sam2/`, or wherever the `SAM2_CHECKPOINT_DIR` env var points.
Every call after the first reuses the cached file, no network needed. The
download goes to a `.part` file and is renamed only on success, so an
interrupted download never poisons the cache.

Available tiers, smallest first: `tiny`, `small`, `base_plus`, `large`
(`cfg.photo_segment_sam2_checkpoint`). `tiny` is the default and the only
one this integration has been built around: CPU-only inference makes the
larger tiers slow enough to be self-defeating against the caller's timeout,
and embroidery-scale regions (floored at `cfg.min_detail_mm`, 1.5 mm) do not
need fine-grained natural-scene accuracy.

If the machine has no route to `dl.fbaipublicfiles.com`, the first real job
pays for it as a slow/failed subprocess call — which
`photo_segment_sam2_timeout_s` bounds, and which still degrades to the
classical segmenter rather than failing the job. Pre-warming the cache by
hand (below) is the fix, not something this repo needs to script.

## Sanity-check it by hand

```
sam2_isolated/venv/bin/python digitizer_core/sam2_worker.py \
    testdata/photo/drone_render.png /tmp/sam2.npz tiny 16 36
```

Exit code 0 and an `.npz` at `/tmp/sam2.npz` means the venv and the
checkpoint cache are both working. Inspect it from the SHARED venv:

```
.venv/Scripts/python -c "import numpy as np; d=np.load('/tmp/sam2.npz'); print(d['labels'].shape, d['labels'].dtype, int(d['raw_mask_count']), sorted(set(d['labels'].ravel().tolist()))[:5])"
```

Expect the label array to match the input image's `(H, W)`, dtype `int32`,
a raw mask count in the tens-to-low-hundreds, and `-1` present (SAM2 does
not tile the image; uncovered pixels are normal and the seam handles them).

The FIRST run also pays for the checkpoint download (~150 MB) and torch's
own import, so time it separately from the second — the second run is the
one whose duration should inform `photo_segment_sam2_timeout_s`.
```

- [ ] **Step 7: Ignore the venv**

Edit `digitizer/.gitignore` — add `sam2_isolated/venv/` directly beneath the existing `rembg_isolated/venv/` line, so the file reads:

```
.venv/
rembg_isolated/venv/
sam2_isolated/venv/
__pycache__/
*.pyc
*.egg-info/
debug_out/
.pytest_cache/
build/
dist/
```

Verify: `git status --short digitizer/` must not list anything under `digitizer/sam2_isolated/venv/` after the venv is built.

- [ ] **Step 8: Commit**

```bash
git add digitizer/sam2_isolated/README.md digitizer/sam2_isolated/requirements.txt digitizer/digitizer_core/sam2_worker.py digitizer/tests/test_sam2_worker.py digitizer/.gitignore
git commit -m "feat: standalone SAM2 worker script and isolated-venv scaffolding"
```

---

### Task 3: Config fields, warning codes, and the availability check

**Files:**
- Modify: `digitizer/digitizer_core/config.py:99` (insert after `photo_prep_background_removal_timeout_s`)
- Modify: `digitizer/digitizer_core/warnings_codes.py:68` (insert after `PHOTO_PALETTE_SELECTED`)
- Create: `digitizer/digitizer_core/stage2_sam2_segment.py`
- Test: `digitizer/tests/test_sam2_segment.py`

**Interfaces:**
- Consumes: `digitizer_core.sam2_worker` (Task 2) only as a file on disk, not as an import.
- Produces:
  ```python
  # digitizer_core/config.py -- PipelineConfig fields
  photo_segment_sam2: bool = False
  photo_segment_sam2_checkpoint: str = "tiny"
  photo_segment_sam2_points_per_side: int = 16
  photo_segment_sam2_max_side_px: int = 1024
  photo_segment_sam2_timeout_s: float = 180.0

  # digitizer_core/warnings_codes.py
  PHOTO_SAM2_SEGMENTED = "PHOTO_SAM2_SEGMENTED"
  PHOTO_SAM2_SEGMENTATION_UNAVAILABLE = "PHOTO_SAM2_SEGMENTATION_UNAVAILABLE"

  # digitizer_core/stage2_sam2_segment.py
  SAM2_WORKER_PATH: Path
  SAM2_VENV_PYTHON: Path
  def _default_sam2_venv_python() -> Path: ...
  def sam2_segmentation_unavailable_reason() -> str | None: ...
  ```

- [ ] **Step 1: Write the failing tests**

Create `digitizer/tests/test_sam2_segment.py` with this first section (later tasks append to the same file):

```python
"""SAM2 photo segmentation — `digitizer_core/stage2_sam2_segment.py`.

What this file pins, section by section:

1. The environment-only availability check: worker script missing and
   isolated venv missing each produce one honest reason; both present
   produces None. Mirrors tests/test_background_removal.py section 2.
2. The seam's never-raises contract in every runtime failure mode (timeout,
   nonzero exit, launch failure, unreadable output, shape mismatch, no
   usable regions) — all mock `subprocess.run` directly, so they need no
   SAM2 install and always run.
3. The seam's happy path against a SYNTHETIC worker output: a hand-built
   label map goes in, a real `Quant` built by the shared
   `kept_masks_to_quant` tail comes out. The real SAM2 install is Task 6's
   manual acceptance step, not this file's job.
4. The pipeline gate: photo classes with the flag on try SAM2; "gradient"
   and "flat" never do; any failure falls back to the classical segmenter
   with PHOTO_SAM2_SEGMENTATION_UNAVAILABLE and the job still completes.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig

from .test_flat_lane_byte_identical import GOLDEN

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FIXTURE = TESTDATA / "photo" / "region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- 1. Availability: environment-only, two file-existence facts -------------


def test_missing_worker_script_gives_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", tmp_path / "not_there.py")
    reason = s2.sam2_segmentation_unavailable_reason()
    assert reason is not None and "worker script missing" in reason


def test_missing_isolated_venv_gives_a_reason(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", tmp_path / "worker.py")
    (tmp_path / "worker.py").write_text("", encoding="utf-8")
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", tmp_path / "venv" / "bin" / "python")
    reason = s2.sam2_segmentation_unavailable_reason()
    assert reason is not None and "isolated SAM2 venv not found" in reason
    assert "sam2_isolated/README.md" in reason


def test_both_present_is_available(monkeypatch, tmp_path):
    import digitizer_core.stage2_sam2_segment as s2

    worker = tmp_path / "worker.py"
    python = tmp_path / "python"
    worker.write_text("", encoding="utf-8")
    python.write_text("", encoding="utf-8")
    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", worker)
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", python)
    assert s2.sam2_segmentation_unavailable_reason() is None


def test_the_real_worker_script_is_actually_on_disk():
    """The half of the availability check this repo controls: the worker
    script ships with the package, so only the venv half should ever be the
    reason SAM2 is unavailable in a real checkout."""
    import digitizer_core.stage2_sam2_segment as s2

    assert s2.SAM2_WORKER_PATH.is_file()


# --- 1b. The config gate's defaults ------------------------------------------


def test_sam2_is_off_by_default_with_the_documented_defaults():
    cfg = PipelineConfig()
    assert cfg.photo_segment_sam2 is False
    assert cfg.photo_segment_sam2_checkpoint == "tiny"
    assert cfg.photo_segment_sam2_points_per_side == 16
    assert cfg.photo_segment_sam2_max_side_px == 1024
    assert cfg.photo_segment_sam2_timeout_s == 180.0


def test_the_default_checkpoint_tier_is_one_the_worker_knows():
    from digitizer_core import sam2_worker

    assert PipelineConfig().photo_segment_sam2_checkpoint in sam2_worker.CHECKPOINTS
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: collection/import errors — `ModuleNotFoundError: No module named 'digitizer_core.stage2_sam2_segment'` and `TypeError: PipelineConfig.__init__() got an unexpected keyword argument` style failures.

- [ ] **Step 3: Add the config fields**

In `digitizer/digitizer_core/config.py`, insert this block immediately after `photo_prep_background_removal_timeout_s: float = 60.0` (line 99) and before the `# Stage 3` comment:

```python
    # Stage 2 (photo path) — SAM2 region former (digitizer/sam2_isolated/,
    # see its README.md). A SEPARATE opt-in flag, gated on the PHOTO classes
    # only: this flag must be True AND stage 0 must classify the design
    # photo_subject/photo_scene (forced_class counts). "gradient" designs
    # route through stage2_photo_segment for an unrelated reason (avoiding
    # k-means dithering on a smooth ramp) and deliberately do NOT get SAM2 —
    # a gradient has no "distinct objects" for an instance segmenter to find,
    # and SLIC+RAG is already tuned against two real gradient fixtures. "flat"
    # never reaches this code path at all. Default False; with it off the
    # pipeline is exactly what it was before this lane existed. When on and
    # the isolated venv is missing/broken/times out, the documented fallback
    # applies (PHOTO_SAM2_SEGMENTATION_UNAVAILABLE): the classical SLIC+RAG
    # region former runs instead and the job still completes.
    photo_segment_sam2: bool = False
    # Which SAM 2.1 checkpoint tier the worker loads — a key of
    # sam2_worker.CHECKPOINTS ("tiny" | "small" | "base_plus" | "large").
    # "tiny" is the default and the only tier this lane was built around:
    # inference here is CPU-only, so the larger tiers get slow enough to be
    # self-defeating against the timeout below, and embroidery-scale regions
    # (floored at min_detail_mm) do not need fine-grained natural-scene
    # accuracy. An unknown name is rejected by the worker (exit 2) and
    # degrades to the classical fallback like any other worker failure.
    photo_segment_sam2_checkpoint: str = "tiny"
    # SAM2's own automatic-mask-generator prompt-grid density. SAM2's library
    # default is 32 (1024 prompts); 16 (256 prompts) quarters the mask-decoder
    # work, which is the dominant CPU cost here. PRINCIPLED STARTING POINT,
    # NOT A MEASURED ONE: the reasoning is that a prompt grid finer than the
    # min-detail floor only produces masks that resolve_small_regions will
    # absorb anyway. Needs a real-image sweep (Task 6) before anyone treats
    # it as tuned — see docs/pro-digitizing-playbook.md's own "measured, not
    # guessed" framing.
    photo_segment_sam2_points_per_side: int = 16
    # Longest side, in px, of the raster handed to the worker. SAM2's image
    # encoder resizes its input to 1024x1024 internally, so sending more than
    # this costs I/O and post-processing without giving the encoder more to
    # work with; the returned label map is nearest-neighbour upsampled back
    # to full resolution, which preserves region identity exactly and costs
    # at most a pixel of boundary precision — well inside the tolerance
    # stage 4 already applies via simplify_tol_mm. 0 or negative disables the
    # downscale entirely. ALSO A STARTING POINT: the boundary-precision half
    # of that claim is reasoned, not measured.
    photo_segment_sam2_max_side_px: int = 1024
    # Subprocess timeout, seconds. This is the ONLY bound this architecture
    # has on a hung SAM2 call: digitizer_service/jobs.py's JobRegistry is a
    # single-worker ThreadPoolExecutor with no per-job timeout and no
    # cancellation of a running job, so a call that never returns starves
    # every queued job behind it. Read this number as a starvation bound, not
    # a performance target. 180s (3x rembg's 60s) because SAM2 on CPU is a
    # heavier call than a background-removal net: one Hiera-tiny image-encoder
    # pass at 1024x1024 plus points_per_side^2 prompts through the mask
    # decoder in batches of 64, plus NMS — and the FIRST call also pays a
    # one-time ~150 MB checkpoint download and torch import. UNMEASURED on
    # this hardware; Task 6 times a real run and this number should come down
    # to roughly 2x the observed warm-cache p95 once it has.
    photo_segment_sam2_timeout_s: float = 180.0
```

- [ ] **Step 4: Add the warning codes**

In `digitizer/digitizer_core/warnings_codes.py`, insert after the `PHOTO_PALETTE_SELECTED` line (line 68) and before the `# Stage 3` comment:

```python

# Stage 2 (photo path) — SAM2 region former. Rides its own opt-in flag
# (cfg.photo_segment_sam2) PLUS a photo_subject/photo_scene classification;
# "gradient" deliberately does not qualify (see config.py's comment).
# Info, not a problem: the isolated-venv SAM2 subprocess ran and its instance
# masks became this design's regions instead of SLIC+RAG's superpixel merge.
# extra: {"raw_masks": int, "regions": int, "checkpoint": str}
PHOTO_SAM2_SEGMENTED = "PHOTO_SAM2_SEGMENTED"
# SAM2 segmentation was gated ON but cannot run here (isolated SAM2 venv not
# built, worker script missing, checkpoint download failed, subprocess crashed
# or timed out, output unusable, ...) — the documented fallback: the classical
# SLIC+RAG region former runs instead and the job still completes.
# extra: {"reason": str}
PHOTO_SAM2_SEGMENTATION_UNAVAILABLE = "PHOTO_SAM2_SEGMENTATION_UNAVAILABLE"
```

- [ ] **Step 5: Create the seam module with its constants and availability check**

Create `digitizer/digitizer_core/stage2_sam2_segment.py`:

```python
"""Stage 2 (photo path) — SAM2 region former.

An OPTIONAL alternative front half for `stage2_photo_segment.segment()`, for
photo_subject/photo_scene designs only. Same output contract (`Quant`), and
literally the same back half: this module produces a list of non-overlapping
`RegionMask`s from SAM2's instance masks and then hands them to
`stage2_photo_segment.kept_masks_to_quant`, the shared tail the classical
SLIC+RAG lane also calls. The ONLY difference between the two segmenters is
how the region list gets built; palette selection, spool dedupe, the enclosed
population and the warnings are one implementation, not two.

Why SAM2 might beat SLIC+RAG here: SLIC/SEEDS group pixels that are close in
BOTH color and space, then merge on a perceptual color threshold — so a
region boundary is wherever color changes enough, which is not always where
an object ends. SAM2 segments by learned visual saliency, so a subject whose
interior varies smoothly (a face, a jacket, a dog) can come back as one mask
instead of a color-ramp's worth of merged superpixels. Whether that actually
improves the SEWN result is an open, measurable question — see this lane's
plan doc, `docs/superpowers/plans/2026-08-10-sam2-segmentation.md`, and its
Task 6 acceptance criteria. Nothing here assumes it does.

Why a subprocess: SAM2 needs PyTorch, which cannot go in the shared venv —
see `digitizer/sam2_isolated/README.md` and `sam2_worker.py`'s own docstring.
The bridge, its timeout, and its never-raises contract mirror
`stage1_photo_prep.remove_background_seam` exactly.
"""
from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_photo_segment import kept_masks_to_quant
from .stage2_quantize import Quant
from .stage3_segment import RegionMask, resolve_small_regions
from .warnings_codes import PHOTO_SAM2_SEGMENTED, warn

# Where the isolated SAM2 venv + its worker script live. Module-level
# constants (not cfg fields) so tests can monkeypatch them exactly the way
# stage1_photo_prep's REMBG_* constants are monkeypatched, without threading
# a path override through PipelineConfig for something that is a deploy-time
# file location, not a per-job parameter.
SAM2_WORKER_PATH = Path(__file__).resolve().parent / "sam2_worker.py"
_SAM2_ISOLATED_DIR = Path(__file__).resolve().parents[1] / "sam2_isolated"


def _default_sam2_venv_python() -> Path:
    """POSIX venvs put the interpreter under bin/, Windows under Scripts/.
    Prefer whichever actually exists; POSIX is the default name used in the
    "missing" reason message when neither does (matching this repo's other
    tooling, which targets POSIX first — see COOKBOOK.md)."""
    posix = _SAM2_ISOLATED_DIR / "venv" / "bin" / "python"
    windows = _SAM2_ISOLATED_DIR / "venv" / "Scripts" / "python.exe"
    if windows.is_file() and not posix.is_file():
        return windows
    return posix


SAM2_VENV_PYTHON = _default_sam2_venv_python()


def sam2_segmentation_unavailable_reason() -> str | None:
    """None when the isolated SAM2 venv + worker script look runnable here;
    otherwise one honest sentence why not.

    ENVIRONMENT-ONLY: a per-call runtime failure (a subprocess crash, a
    timeout, a first-use checkpoint download failing on a machine with no
    route to Meta's release host) is not knowable from files on disk alone,
    so it is NOT covered here — `sam2_segment_seam` reports that half itself,
    in its own return value. The two never disagree about the
    environment-level half because both read the exact same two paths. Same
    split, for the same reason, as
    `stage1_photo_prep.background_removal_unavailable_reason`.
    """
    if not SAM2_WORKER_PATH.is_file():
        return f"SAM2 worker script missing at {SAM2_WORKER_PATH}"
    if not SAM2_VENV_PYTHON.is_file():
        return (
            f"isolated SAM2 venv not found at {SAM2_VENV_PYTHON} — see "
            "digitizer/sam2_isolated/README.md to build it"
        )
    return None
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: 6 passed.

- [ ] **Step 7: Commit**

```bash
git add digitizer/digitizer_core/config.py digitizer/digitizer_core/warnings_codes.py digitizer/digitizer_core/stage2_sam2_segment.py digitizer/tests/test_sam2_segment.py
git commit -m "feat: SAM2 config gate, warning codes, and availability check"
```

---

### Task 4: The caller-side seam — subprocess, region list, shared tail

**Files:**
- Modify: `digitizer/digitizer_core/stage2_sam2_segment.py`
- Test: `digitizer/tests/test_sam2_segment.py` (append sections 2 and 3)

**Interfaces:**
- Consumes: `stage2_photo_segment.kept_masks_to_quant(...)` (Task 1), `sam2_worker.py`'s CLI and `.npz` contract (Task 2), `sam2_segmentation_unavailable_reason()` and the five `photo_segment_sam2*` config fields (Task 3).
- Produces:
  ```python
  # digitizer_core/stage2_sam2_segment.py
  def sam2_segment_seam(
      p: Prep,
      cfg: PipelineConfig,
      face_regions=None,
      bg_mask: np.ndarray | None = None,
  ) -> tuple[Quant | None, str | None]: ...
  ```
  `(quant, None)` on success, `(None, reason)` on any failure. Never raises.

**Design decisions this task locks in, and their status.**

1. **Overlap resolution** happens in the worker (Task 2, `_paint_labels`): largest mask painted first, so smaller nested masks win the pixels they share. Ties break on `predicted_iou` then generator order. *Principled, not measured* — the justification is domain reasoning (nested detail is what an embroiderer needs to keep as its own shape), not a fixture sweep.
2. **Minimum-area floor**: no new threshold is invented. The worker is handed `min_mask_region_area = int((cfg.min_detail_mm * p.px_per_mm * scale) ** 2)`, where `scale` is the same downscale ratio `_downscale_for_sam2` applied to the image — the identical `min_detail_mm`-based formula `stage3_segment.resolve_small_regions` and `stage1_photo_prep._clean_background_mask` already use, corrected into the coordinate space the worker actually operates in (the worker only ever sees the downscaled image, not the full-res raster `px_per_mm` describes — an unscaled floor over-filters by `1/scale²`, corrected post-review in Task 4's fix round 1). Whatever survives still goes through the real `resolve_small_regions` call, exactly as the classical path's regions do. *Established, measured elsewhere in this codebase; the scale correction itself is arithmetic, not a new measurement.*
3. **Pixels no SAM2 mask covers** (`-1` in the label map) are not discarded — SAM2's automatic generator does not tile the image, and dropping those pixels would delete real artwork. They are treated as one more label id, split into connected components like every other, and then absorbed or kept by `resolve_small_regions` on their own merits. *Structural, not tunable.*
4. **Region construction** mirrors `segment()`'s own step 4 verbatim: every label id, intersected with `base_valid`, split into 8-connected components, one `RegionMask` per component. The enclosed population is excluded from `base_valid` here for exactly the reason `segment()` excludes it — `kept_masks_to_quant` quantizes it separately.

- [ ] **Step 1: Write the failing tests**

Append to `digitizer/tests/test_sam2_segment.py`:

```python
# --- 2/3. The seam: happy path and every runtime failure mode ---------------
# All of these mock subprocess.run, so none needs a SAM2 install.


def _prepped(fixture: Path = FIXTURE, **cfg_kw):
    from digitizer_core.stage1_prep import prep

    cfg = _cfg(**cfg_kw)
    return prep(fixture, cfg), cfg


def _available(monkeypatch):
    """Make the environment-level check pass without touching the disk."""
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "sam2_segmentation_unavailable_reason", lambda: None)
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", Path("/fake/worker.py"))
    return s2


def _fake_worker(labels_for):
    """Build a subprocess.run stand-in that writes the npz `labels_for(h, w)`
    returns, reading the real temp input PNG the seam just wrote so the
    shapes always agree."""

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, **kwargs):
        in_path, out_path = cmd[2], cmd[3]
        image = cv2.imread(str(in_path), cv2.IMREAD_COLOR)
        assert image is not None, "the seam did not write a readable input image"
        h, w = image.shape[:2]
        labels = labels_for(h, w)
        n = int(labels.max()) + 1 if labels.max() >= 0 else 0
        np.savez_compressed(
            out_path,
            labels=labels.astype(np.int32),
            area=np.array([int((labels == i).sum()) for i in range(n)], np.int64),
            predicted_iou=np.full(n, 0.9, np.float32),
            stability_score=np.full(n, 0.95, np.float32),
            raw_mask_count=np.int64(n),
        )
        return _Proc()

    return _run


def _quadrant_labels(h: int, w: int) -> np.ndarray:
    """Four big blocks plus an uncovered stripe — a stand-in for SAM2 output
    that exercises real regions AND the -1 (no mask covered this pixel)
    case the seam has to handle."""
    labels = np.full((h, w), -1, np.int32)
    labels[: h // 2, : w // 2] = 0
    labels[: h // 2, w // 2:] = 1
    labels[h // 2:, : w // 2] = 2
    labels[h // 2:, w // 2: w - w // 8] = 3
    return labels


def test_seam_returns_a_real_quant_from_a_worker_label_map(monkeypatch):
    s2 = _available(monkeypatch)
    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_quadrant_labels))

    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)

    assert reason is None
    assert quant is not None
    assert quant.labels.shape == p.rgb.shape[:2]
    assert quant.labels.dtype == np.int32
    assert quant.thread_indices, "no thread colors came out of palette selection"
    assert quant.cluster_rgb.shape == (len(quant.thread_indices), 3)
    assert quant.labels.max() < len(quant.thread_indices)

    from digitizer_core.warnings_codes import (
        PHOTO_PALETTE_SELECTED,
        PHOTO_SAM2_SEGMENTED,
        PHOTO_SEGMENT_REGION_COUNT,
    )

    codes = [w["code"] for w in quant.warnings]
    # The shared tail's own two warnings prove kept_masks_to_quant ran.
    assert PHOTO_SEGMENT_REGION_COUNT in codes
    assert PHOTO_PALETTE_SELECTED in codes
    assert PHOTO_SAM2_SEGMENTED in codes
    region_count = next(
        w for w in quant.warnings if w["code"] == PHOTO_SEGMENT_REGION_COUNT
    )
    assert "SAM2 masks" in region_count["message"]
    segmented = next(w for w in quant.warnings if w["code"] == PHOTO_SAM2_SEGMENTED)
    assert segmented["checkpoint"] == cfg.photo_segment_sam2_checkpoint
    assert segmented["raw_masks"] == 4


def test_seam_passes_the_documented_argv_to_the_worker(monkeypatch):
    s2 = _available(monkeypatch)
    seen: list[list[str]] = []
    inner = _fake_worker(_quadrant_labels)

    def _spy(cmd, **kwargs):
        seen.append([str(c) for c in cmd])
        assert kwargs["timeout"] == 180.0, "the starvation bound was not passed"
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        return inner(cmd, **kwargs)

    monkeypatch.setattr(s2.subprocess, "run", _spy)
    p, cfg = _prepped()
    s2.sam2_segment_seam(p, cfg)

    assert len(seen) == 1
    cmd = seen[0]
    assert len(cmd) == 7
    # str(Path("/fake/python")) is "\\fake\\python" on Windows — compare the
    # basename, not the whole path, so this test is not OS-specific.
    assert Path(cmd[0]).name == "python"
    assert cmd[1].endswith("worker.py")
    assert cmd[4] == "tiny"
    assert cmd[5] == "16"
    assert int(cmd[6]) == int((cfg.min_detail_mm * p.px_per_mm) ** 2)


def test_seam_downscales_to_the_configured_max_side(monkeypatch):
    s2 = _available(monkeypatch)
    sizes: list[tuple[int, int]] = []

    def _run(cmd, **kwargs):
        image = cv2.imread(str(cmd[2]), cv2.IMREAD_COLOR)
        sizes.append(image.shape[:2])
        return _fake_worker(_quadrant_labels)(cmd, **kwargs)

    monkeypatch.setattr(s2.subprocess, "run", _run)
    p, cfg = _prepped(photo_segment_sam2_max_side_px=64)
    quant, reason = s2.sam2_segment_seam(p, cfg)

    assert reason is None
    assert max(sizes[0]) == 64, f"worker saw {sizes[0]}, expected a 64px long side"
    # ...and the label map still comes back at full resolution.
    assert quant.labels.shape == p.rgb.shape[:2]


def test_unavailable_environment_short_circuits_before_any_subprocess(monkeypatch):
    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(
        s2, "sam2_segmentation_unavailable_reason", lambda: "venv not built (test)"
    )

    def _boom(*a, **kw):
        raise AssertionError("subprocess.run must not be reached")

    monkeypatch.setattr(s2.subprocess, "run", _boom)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason == "venv not built (test)"


def test_subprocess_timeout_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    def _raise_timeout(*a, **kw):
        raise subprocess.TimeoutExpired(cmd="sam2_worker.py", timeout=1.0)

    monkeypatch.setattr(s2.subprocess, "run", _raise_timeout)
    p, cfg = _prepped(photo_segment_sam2_timeout_s=1.0)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "timed out" in reason


def test_subprocess_nonzero_exit_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 5
        stdout = ""
        stderr = "sam2_worker: mask generation failed: boom\n"

    monkeypatch.setattr(s2.subprocess, "run", lambda *a, **kw: _Proc())
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "exited 5" in reason and "boom" in reason


def test_launch_failure_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    def _raise_oserror(*a, **kw):
        raise OSError("no such file")

    monkeypatch.setattr(s2.subprocess, "run", _raise_oserror)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "failed to launch" in reason


def test_missing_output_file_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr(s2.subprocess, "run", lambda *a, **kw: _Proc())
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "no readable output" in reason


def test_wrong_shape_output_degrades_to_none_with_a_reason(monkeypatch):
    s2 = _available(monkeypatch)
    monkeypatch.setattr(
        s2.subprocess,
        "run",
        _fake_worker(lambda h, w: np.zeros((h + 7, w), np.int32)),
    )
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "label map" in reason


def test_no_usable_regions_degrades_to_none_rather_than_an_empty_design(monkeypatch):
    """A worker that technically succeeded but produced nothing sewable must
    fall back to the classical segmenter, not hand the pipeline a design with
    zero regions."""
    s2 = _available(monkeypatch)

    def _empty(h, w):
        return np.full((h, w), -1, np.int32)

    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_empty))
    p, cfg = _prepped()
    # Force every leftover component under the sewable floor so the floor
    # itself, not the label map, is what empties the region list.
    p.bg_mask = np.ones(p.rgb.shape[:2], bool)
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None and "no usable regions" in reason


def test_seam_never_raises_on_a_worker_that_writes_garbage(monkeypatch):
    """The contract that matters most: whatever the worker does, the seam
    returns a tuple. Mirrors remove_background_seam's own never-raises
    guarantee."""
    s2 = _available(monkeypatch)

    class _Proc:
        returncode = 0
        stdout = ""
        stderr = ""

    def _run(cmd, **kwargs):
        Path(cmd[3]).write_bytes(b"not an npz at all")
        return _Proc()

    monkeypatch.setattr(s2.subprocess, "run", _run)
    p, cfg = _prepped()
    quant, reason = s2.sam2_segment_seam(p, cfg)
    assert quant is None
    assert reason is not None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: the 11 new tests fail with `AttributeError: module 'digitizer_core.stage2_sam2_segment' has no attribute 'sam2_segment_seam'`; the 6 from Task 3 still pass.

- [ ] **Step 3: Implement the seam**

Append to `digitizer/digitizer_core/stage2_sam2_segment.py`:

```python
def _downscale_for_sam2(
    rgb: np.ndarray, max_side_px: int
) -> np.ndarray:
    """Shrink the raster to `max_side_px` on its long side, or return it
    untouched. INTER_AREA because this is a downsample and it is the right
    filter for one — the same choice `tests/test_background_removal.py`'s own
    fixture helper makes."""
    h, w = rgb.shape[:2]
    longest = max(h, w)
    if max_side_px <= 0 or longest <= max_side_px:
        return rgb
    scale = max_side_px / float(longest)
    new_w = max(1, int(round(w * scale)))
    new_h = max(1, int(round(h * scale)))
    return cv2.resize(rgb, (new_w, new_h), interpolation=cv2.INTER_AREA)


def _upsample_labels(labels: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    """Nearest-neighbour upsample of a label array to `shape`.

    Done with numpy index arithmetic, not `cv2.resize`: OpenCV's resize does
    not accept CV_32S input, and round-tripping label ids through float32
    to work around that is a silent-corruption risk this code has no reason
    to take. Nearest-neighbour is the only correct filter for label data —
    any interpolation would invent label ids that no mask ever produced.
    """
    h, w = shape
    src_h, src_w = labels.shape[:2]
    if (src_h, src_w) == (h, w):
        return labels
    ys = np.clip((np.arange(h) * src_h) // h, 0, src_h - 1)
    xs = np.clip((np.arange(w) * src_w) // w, 0, src_w - 1)
    return labels[ys][:, xs]


def _regions_from_label_map(
    labels: np.ndarray, base_valid: np.ndarray
) -> list[RegionMask]:
    """One RegionMask per 8-connected component of every label id.

    Mirrors `stage2_photo_segment.segment`'s own step 4 exactly, including
    the `& base_valid` intersection: a label id is not on its own proof of
    foreground, and intersecting with the real per-population mask is what
    keeps background AND enclosed pixels out of every RegionMask regardless
    of which id they wear.

    The `-1` id — pixels no SAM2 mask covered — is deliberately NOT special-
    cased. SAM2's automatic generator returns instance masks, not a partition,
    so uncovered foreground is normal and expected; dropping it would delete
    real artwork from the design. Its components compete for survival on
    exactly the same terms as every other region, in `resolve_small_regions`.
    """
    regions: list[RegionMask] = []
    for lbl in sorted(set(np.unique(labels[base_valid]).tolist())):
        comp_mask = ((labels == lbl) & base_valid).astype(np.uint8)
        n_cc, cc = cv2.connectedComponents(comp_mask, connectivity=8)
        for c in range(1, n_cc):
            regions.append(RegionMask(mask=(cc == c), layer=0, source="photo_sam2"))
    return regions


def sam2_segment_seam(
    p: Prep,
    cfg: PipelineConfig,
    face_regions=None,
    bg_mask: np.ndarray | None = None,
) -> tuple[Quant | None, str | None]:
    """SAM2-backed stage 2, run in the isolated venv documented at
    `digitizer/sam2_isolated/README.md` — NEVER the shared `digitizer/.venv`.

    Returns `(quant, reason)`:
      * `(quant, None)` — the worker ran and produced usable regions. `quant`
        is a full `Quant`, built by the same `kept_masks_to_quant` tail the
        classical lane uses, plus a `PHOTO_SAM2_SEGMENTED` info warning.
      * `(None, reason)` — cannot run here (isolated venv/worker missing, per
        `sam2_segmentation_unavailable_reason`) OR the subprocess failed at
        runtime (timeout, crash, unreadable output, a first-use checkpoint
        download failing, no usable regions, ...). One honest sentence either
        way. The documented fallback: the caller runs
        `stage2_photo_segment.segment()` instead and says so via
        `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`.

    Never raises: every failure mode funnels into the `(None, reason)` arm so
    a SAM2 problem degrades a job, never crashes it — the same contract
    `stage1_photo_prep.remove_background_seam` gives rembg failures.

    The `timeout=` on the subprocess call below is load-bearing beyond the
    usual hygiene: `digitizer_service/jobs.py`'s JobRegistry is a
    single-worker ThreadPoolExecutor with no per-job timeout and no
    cancellation, so this is the only thing that stops a hung SAM2 call from
    starving every queued job behind it.
    """
    reason = sam2_segmentation_unavailable_reason()
    if reason is not None:
        return None, reason

    h, w = p.rgb.shape[:2]
    enclosed = p.enclosed_mask
    has_enclosed = enclosed is not None and enclosed.any()
    base_valid = (~p.bg_mask & ~enclosed) if has_enclosed else ~p.bg_mask

    # The same "too small to sew" area the min-detail floor means everywhere
    # else in this codebase (stage3_segment.resolve_small_regions,
    # stage1_photo_prep._clean_background_mask) — handed to SAM2 so it drops
    # sub-sewable masks itself instead of shipping thousands of them back
    # over the pipe. Whatever survives still faces the real floor below.
    #
    # CORRECTED post-review (task-4 fix round 1): the worker only ever sees
    # `small`, not the full-resolution raster, so the floor must be computed
    # in THAT image's pixels — px_per_mm describes the full-res image, so it
    # is scaled down by the same ratio the image itself was downscaled by.
    # An unscaled floor here over-filters by 1/scale^2 (4x-15x at this
    # lane's default 1024px cap on real commissioned-size source art),
    # silently deleting the nested detail this whole feature exists to keep.
    small = _downscale_for_sam2(p.rgb, cfg.photo_segment_sam2_max_side_px)
    scale = max(small.shape[:2]) / float(max(h, w))
    min_mask_region_area = int((cfg.min_detail_mm * p.px_per_mm * scale) ** 2)

    with tempfile.TemporaryDirectory(prefix="sam2_seam_") as tmp:
        in_path = Path(tmp) / "in.png"
        out_path = Path(tmp) / "masks.npz"
        if not cv2.imwrite(str(in_path), cv2.cvtColor(small, cv2.COLOR_RGB2BGR)):
            return None, "failed to write a temp input image for the SAM2 worker"

        try:
            proc = subprocess.run(
                [
                    str(SAM2_VENV_PYTHON),
                    str(SAM2_WORKER_PATH),
                    str(in_path),
                    str(out_path),
                    str(cfg.photo_segment_sam2_checkpoint),
                    str(int(cfg.photo_segment_sam2_points_per_side)),
                    str(min_mask_region_area),
                ],
                capture_output=True,
                text=True,
                timeout=cfg.photo_segment_sam2_timeout_s,
            )
        except subprocess.TimeoutExpired:
            return None, (
                "SAM2 worker timed out after "
                f"{cfg.photo_segment_sam2_timeout_s:g}s"
            )
        except OSError as exc:
            return None, f"failed to launch the isolated SAM2 venv: {exc}"

        if proc.returncode != 0:
            tail = (proc.stderr or "").strip().splitlines()
            detail = tail[-1] if tail else "no stderr output"
            return None, f"SAM2 worker exited {proc.returncode}: {detail}"

        try:
            with np.load(out_path, allow_pickle=False) as data:
                raw_labels = np.asarray(data["labels"], np.int32)
                raw_mask_count = int(data["raw_mask_count"])
        except Exception as exc:  # noqa: BLE001 -- any unreadable output degrades
            return None, f"SAM2 worker reported success but wrote no readable output: {exc}"

    if raw_labels.shape[:2] != small.shape[:2]:
        return None, (
            f"SAM2 worker returned a {raw_labels.shape[:2]} label map for a "
            f"{small.shape[:2]} image"
        )

    labels = _upsample_labels(raw_labels, (h, w))
    regions = _regions_from_label_map(labels, base_valid)
    merged_count = len(set(np.unique(labels[base_valid]).tolist()))
    kept, floor_warnings = resolve_small_regions(regions, cfg, p.px_per_mm)
    if not kept:
        return None, (
            f"SAM2 produced no usable regions ({raw_mask_count} raw masks, "
            f"{len(regions)} components, all below the "
            f"{cfg.min_detail_mm:g} mm detail floor)"
        )

    quant = kept_masks_to_quant(
        p,
        cfg,
        kept,
        floor_warnings,
        face_regions=face_regions,
        bg_mask=bg_mask,
        raw_count=raw_mask_count,
        merged_count=merged_count,
        raw_unit_label="SAM2 masks",
        oversegment_labels=labels,
    )
    quant.warnings.append(
        warn(
            PHOTO_SAM2_SEGMENTED,
            f"SAM2 segmentation produced {len(kept)} region"
            f"{'s' if len(kept) != 1 else ''} from {raw_mask_count} raw mask"
            f"{'s' if raw_mask_count != 1 else ''} "
            f"({cfg.photo_segment_sam2_checkpoint} checkpoint, CPU).",
            raw_masks=raw_mask_count,
            regions=len(kept),
            checkpoint=cfg.photo_segment_sam2_checkpoint,
        )
    )
    return quant, None
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: 17 passed (6 from Task 3 + 11 new).

- [ ] **Step 5: Prove the shared tail is still safe**

Run: `.venv/Scripts/python -m pytest tests/test_photo_lane_byte_identical.py -q`
Expected: 8 passed — adding a second caller of `kept_masks_to_quant` must not have moved the classical lane.

- [ ] **Step 6: Commit**

```bash
git add digitizer/digitizer_core/stage2_sam2_segment.py digitizer/tests/test_sam2_segment.py
git commit -m "feat: SAM2 segmentation seam with subprocess timeout and silent fallback"
```

---

### Task 5: Pipeline dispatch wiring

**Files:**
- Modify: `digitizer/digitizer_core/pipeline.py:31-60` (imports), `digitizer/digitizer_core/pipeline.py:245-249` (stage 2 dispatch)
- Modify: `digitizer/README.md:62` (insert a paragraph before `## Run`)
- Test: `digitizer/tests/test_sam2_segment.py` (append section 4)

**Interfaces:**
- Consumes: `stage2_sam2_segment.sam2_segment_seam(p, cfg, face_regions=…, bg_mask=…) -> (Quant | None, str | None)` (Task 4), `PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` (Task 3).
- Produces: no new public names. `pipeline.sam2_segment_seam` becomes a module-level import so tests can monkeypatch it the way `tests/test_background_removal.py` monkeypatches `pipeline_module.remove_background_seam`.

- [ ] **Step 1: Write the failing tests**

Append to `digitizer/tests/test_sam2_segment.py`:

```python
# --- 4. The pipeline gate and the fallback ----------------------------------


def _spy_seam(monkeypatch, result):
    """Replace pipeline's SAM2 seam with a recorder. Returns the call log."""
    import digitizer_core.pipeline as pipeline_module

    calls: list[dict] = []

    def _seam(p, cfg, face_regions=None, bg_mask=None):
        calls.append({"face_regions": face_regions, "bg_mask": bg_mask})
        return result

    monkeypatch.setattr(pipeline_module, "sam2_segment_seam", _seam)
    return calls


def _spy_photo_segment(monkeypatch):
    import digitizer_core.pipeline as pipeline_module

    real = pipeline_module.photo_segment
    calls: list[int] = []

    def _spy(p, cfg, face_regions=None, bg_mask=None):
        calls.append(1)
        return real(p, cfg, face_regions=face_regions, bg_mask=bg_mask)

    monkeypatch.setattr(pipeline_module, "photo_segment", _spy)
    return calls


def test_photo_class_with_the_flag_on_uses_sam2_and_skips_slic(monkeypatch):
    from digitizer_core.pipeline import run_stages
    from digitizer_core.stage1_prep import prep
    from digitizer_core.stage2_sam2_segment import sam2_segment_seam

    cfg = _cfg(forced_class="photo_subject", photo_segment_sam2=True)
    p = prep(FIXTURE, cfg)

    import digitizer_core.stage2_sam2_segment as s2

    monkeypatch.setattr(s2, "sam2_segmentation_unavailable_reason", lambda: None)
    monkeypatch.setattr(s2, "SAM2_VENV_PYTHON", Path("/fake/python"))
    monkeypatch.setattr(s2, "SAM2_WORKER_PATH", Path("/fake/worker.py"))
    monkeypatch.setattr(s2.subprocess, "run", _fake_worker(_quadrant_labels))

    quant, reason = sam2_segment_seam(p, cfg)
    assert reason is None

    seam_calls = _spy_seam(monkeypatch, (quant, None))
    slic_calls = _spy_photo_segment(monkeypatch)
    result = run_stages(FIXTURE, cfg)

    assert len(seam_calls) == 1
    assert slic_calls == [], "the classical segmenter ran even though SAM2 succeeded"
    assert result.regions, "the job itself must still complete"

    from digitizer_core.warnings_codes import (
        PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
        PHOTO_SAM2_SEGMENTED,
    )

    codes = {w["code"] for w in result.warnings}
    assert PHOTO_SAM2_SEGMENTED in codes
    assert PHOTO_SAM2_SEGMENTATION_UNAVAILABLE not in codes


def test_unavailable_sam2_falls_back_to_slic_and_says_so(monkeypatch):
    from digitizer_core.pipeline import run_stages
    from digitizer_core.warnings_codes import PHOTO_SAM2_SEGMENTATION_UNAVAILABLE

    seam_calls = _spy_seam(monkeypatch, (None, "isolated SAM2 venv not found (test)"))
    slic_calls = _spy_photo_segment(monkeypatch)
    result = run_stages(
        FIXTURE, _cfg(forced_class="photo_scene", photo_segment_sam2=True)
    )

    assert len(seam_calls) == 1
    assert slic_calls == [1], "the classical fallback did not run"
    hits = [
        w for w in result.warnings
        if w["code"] == PHOTO_SAM2_SEGMENTATION_UNAVAILABLE
    ]
    assert len(hits) == 1
    assert hits[0]["reason"] == "isolated SAM2 venv not found (test)"
    assert result.regions, "the job itself must still complete"


def test_gradient_class_never_triggers_sam2(monkeypatch):
    """The locked routing rule: 'gradient' routes to stage2_photo_segment for
    an unrelated reason (avoiding k-means dithering) and must NOT pick up
    SAM2 along the way."""
    from digitizer_core.pipeline import run_stages
    from digitizer_core.warnings_codes import (
        PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
        PHOTO_SAM2_SEGMENTED,
    )

    seam_calls = _spy_seam(monkeypatch, (None, "should not be called"))
    slic_calls = _spy_photo_segment(monkeypatch)
    result = run_stages(
        FIXTURE, _cfg(forced_class="gradient", photo_segment_sam2=True)
    )

    assert seam_calls == []
    assert slic_calls == [1]
    codes = {w["code"] for w in result.warnings}
    assert PHOTO_SAM2_SEGMENTED not in codes
    assert PHOTO_SAM2_SEGMENTATION_UNAVAILABLE not in codes


def test_flag_off_never_calls_the_seam(monkeypatch):
    from digitizer_core.pipeline import run_stages

    seam_calls = _spy_seam(monkeypatch, (None, "should not be called"))
    run_stages(FIXTURE, _cfg(forced_class="photo_subject", photo_segment_sam2=False))
    assert seam_calls == []


def test_flat_class_never_calls_the_seam(monkeypatch):
    from digitizer_core.pipeline import run_stages

    seam_calls = _spy_seam(monkeypatch, (None, "should not be called"))
    run_stages(FIXTURE, _cfg(forced_class="flat", photo_segment_sam2=True))
    assert seam_calls == []


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_lane_is_byte_identical_with_the_sam2_flag_on(fixture):
    """The classification half of the gate: turning photo_segment_sam2 on
    must not move one byte for a flat-classified design — mirrors
    test_background_removal.py::test_flat_lane_is_byte_identical_with_the_flag_on.
    `GOLDEN` is imported at the top of this module from
    tests/test_flat_lane_byte_identical.py — that file is the record of truth
    for the flat lane and is not touched by this change."""
    from digitizer_core.pipeline import digitize

    result, plan = digitize(
        TESTDATA / fixture,
        PipelineConfig(target_width_mm=80.0, photo_segment_sam2=True),
    )
    snap = {
        "shape_ids": sorted(r.shape_id for r in result.regions),
        "areas_mm2": sorted(round(r.area_mm2, 4) for r in result.regions),
        "warnings": sorted(
            f"{w['code']}:{w.get('count', '')}" for w in result.warnings
        ),
        "stitch_count": sum(len(r.points) for _, r in plan.iter_runs()),
        "stitch_coords": [
            [round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs()
            for x, y in r.points
        ],
    }
    assert snap == GOLDEN[fixture]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: the six new test functions fail with `AttributeError: <module 'digitizer_core.pipeline'> does not have the attribute 'sam2_segment_seam'`.

- [ ] **Step 3: Wire the dispatch**

In `digitizer/digitizer_core/pipeline.py`, add the seam import directly beneath the existing `from .stage2_photo_segment import segment as photo_segment` (line 38):

```python
from .stage2_photo_segment import segment as photo_segment
from .stage2_sam2_segment import sam2_segment_seam
from .stage2_quantize import Quant, quantize
```

Add the warning code to the existing `from .warnings_codes import (...)` block (lines 53-60), keeping the block alphabetical:

```python
from .warnings_codes import (
    DROPPED_SMALL_SHAPES,
    PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE,
    PHOTO_BACKGROUND_REMOVED,
    PHOTO_FACE_PRIORS_UNAVAILABLE,
    PHOTO_FACES_DETECTED,
    PHOTO_SAM2_SEGMENTATION_UNAVAILABLE,
    warn,
)
```

Then replace the stage-2 dispatch expression (currently lines 245-249):

```python
    q: Quant = (
        photo_segment(p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask)
        if classification.class_ in ("photo_subject", "photo_scene", "gradient")
        else quantize(p, cfg)
    )
```

with:

```python
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
    if cfg.photo_segment_sam2 and classification.class_ in (
        "photo_subject",
        "photo_scene",
    ):
        q, sam2_reason = sam2_segment_seam(
            p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask
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
            photo_segment(p, cfg, face_regions=face_regions, bg_mask=subject_bg_mask)
            if classification.class_ in ("photo_subject", "photo_scene", "gradient")
            else quantize(p, cfg)
        )
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `.venv/Scripts/python -m pytest tests/test_sam2_segment.py -q`
Expected: 26 passed — 17 from Tasks 3-4, plus 5 gate tests and 4 parametrized flat-lane cases (one per `GOLDEN` fixture). Or 25 passed / 1 failed on `logo_alpha.png` only if that fixture's pre-existing environment failure documented in `COOKBOOK.md` is present in this checkout — confirm by running the same parametrized case in `tests/test_background_removal.py`, which has the identical structure.

- [ ] **Step 5: Run the whole suite**

Run: `.venv/Scripts/python -m pytest -q`
Expected: no failures that were not already failing before this plan started. Compare against a `git stash && .venv/Scripts/python -m pytest -q` baseline if anything looks ambiguous.

- [ ] **Step 6: Document it in the digitizer README**

In `digitizer/README.md`, insert this paragraph between the tesseract paragraph ending `...always falls back to an empty textarea.` (line 62) and the `## Run` heading (line 64):

```markdown
The optional SAM2 region former for photo-classified designs
(`cfg.photo_segment_sam2`) needs its own isolated venv plus a downloaded
checkpoint — `digitizer/sam2_isolated/README.md` has the build steps, the
disk budget and the by-hand sanity check. It is off by default and, without
it built, degrades to the classical SLIC+RAG region former with a
`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE` warning — the job still completes and
nothing else in the pipeline changes.
```

- [ ] **Step 7: Commit**

```bash
git add digitizer/digitizer_core/pipeline.py digitizer/tests/test_sam2_segment.py digitizer/README.md
git commit -m "feat: route photo-classified designs through SAM2 with silent SLIC+RAG fallback"
```

---

### Task 6: Live acceptance — build the venv, run real SAM2, measure the corpus

**Files:**
- No source changes. This task produces measurements and, if they warrant it, one follow-up commit adjusting `photo_segment_sam2_timeout_s` / `photo_segment_sam2_points_per_side` in `digitizer/digitizer_core/config.py` with the measured numbers written into their comments.

**Interfaces:**
- Consumes: everything from Tasks 1-5.
- Produces: measured values for the two config constants currently marked "principled starting point, not measured", and a go/no-go on whether SAM2 improves photo-lane segmentation at all.

**This task is NOT gated by the automated suite.** It needs a real SAM2 install, a real ~150 MB checkpoint, and minutes of CPU time per image. Everything above ships and passes without it — that is the point of the fallback. Do not skip it and do not claim SAM2 works until it has run.

- [ ] **Step 1: Check disk headroom FIRST**

The machine this plan was written on had 13.5 GB free (measured 2026-08-10). The venv needs roughly 2-3 GB and the checkpoint another ~150 MB, and other work may have consumed the margin since. Check before building, not after:

```bash
python -c "import shutil; t = shutil.disk_usage('C:/'); print('free GB', round(t.free / 1e9, 1))"
```

Expected: a number comfortably above 4. **If it is under 4 GB, stop and reclaim space before continuing** — a pip install that runs out of disk halfway leaves a broken venv that the availability check will happily report as "present".

- [ ] **Step 2: Build the isolated venv**

Follow `digitizer/sam2_isolated/README.md`'s "Build it" section exactly, from `digitizer/`. Re-read Meta's current README at https://github.com/facebookresearch/sam2 first and confirm the repo URL and install command still match what that file says — that check is called out in this plan's Global Constraints for a reason.

Verify:

```bash
sam2_isolated/venv/Scripts/python -c "import torch, sam2; print(torch.__version__, torch.cuda.is_available())"
```

Expected: a torch version >= 2.5.1 and `False` for CUDA. `True` would mean a GPU build got installed — harmless, but it means the CPU wheel index was not used and the venv is larger than budgeted.

- [ ] **Step 3: Run the worker by hand against a real fixture, twice, timed**

```bash
sam2_isolated/venv/Scripts/python digitizer_core/sam2_worker.py testdata/photo/drone_render.png debug_out/sam2_first.npz tiny 16 36
sam2_isolated/venv/Scripts/python digitizer_core/sam2_worker.py testdata/photo/drone_render.png debug_out/sam2_warm.npz tiny 16 36
```

Expected: exit code 0 both times. The FIRST run also downloads the checkpoint and pays torch's cold import; the SECOND is the warm-cache number that matters. Record both wall-clock durations.

Inspect the output from the shared venv:

```bash
.venv/Scripts/python -c "import numpy as np; d = np.load('debug_out/sam2_warm.npz'); print(d['labels'].shape, d['labels'].dtype, int(d['raw_mask_count']), len(set(d['labels'].ravel().tolist())))"
```

Expected: shape matching `drone_render.png`'s, dtype `int32`, a raw mask count in the tens to low hundreds, and a distinct-label count of the same order. A raw mask count of 0 or in the thousands both mean `points_per_side` / `min_mask_region_area` need work before anything downstream is worth measuring.

- [ ] **Step 4: Set the timeout from the measured number**

If the warm run took `T` seconds, set `photo_segment_sam2_timeout_s` to roughly `2 * T` rounded up to a round number, floor 60. Edit the constant in `digitizer/digitizer_core/config.py` and **replace the "UNMEASURED on this hardware" sentence in its comment** with the real measurement: the fixture, the machine, the cold and warm durations, and the date. Do the same for `photo_segment_sam2_points_per_side` if Step 3 showed the grid density needs to move. If a value did not change, still update its comment to say it was measured and confirmed, with the same detail.

Then re-run the seam against the real worker end to end:

```bash
.venv/Scripts/python -c "
from pathlib import Path
from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_sam2_segment import sam2_segment_seam, sam2_segmentation_unavailable_reason
print('available:', sam2_segmentation_unavailable_reason())
cfg = PipelineConfig(target_width_mm=80.0, photo_segment_sam2=True)
p = prep(Path('testdata/photo/drone_render.png'), cfg)
q, reason = sam2_segment_seam(p, cfg)
print('reason:', reason)
print('threads:', None if q is None else len(q.thread_indices))
print([w['message'] for w in (q.warnings if q else [])])
"
```

Expected: `available: None`, `reason: None`, a thread count inside `cfg.max_colors`, and both the `PHOTO_SEGMENT_REGION_COUNT` and `PHOTO_SAM2_SEGMENTED` messages.

- [ ] **Step 5: Measure the corpus, before and after**

`tools/corpus_scorecard.py`'s `MATRIX` does not carry `photo_segment_sam2`, so it scores the classical lane by default. Capture that baseline first, then re-capture with SAM2 on and diff:

```bash
.venv/Scripts/python tools/corpus_scorecard.py capture
git stash push digitizer/testdata/corpus_scorecard_baseline.json   # keep the classical baseline
```

Then temporarily add `"photo_segment_sam2": True` to both entries of `MATRIX` in `tools/corpus_scorecard.py`, run:

```bash
.venv/Scripts/python tools/corpus_scorecard.py diff
```

and **revert that `MATRIX` edit** afterwards — it is a measurement tool, not a config change. Read the output rather than just checking the exit code; the script's own docstring is explicit that it is a reporting tool, not a gate.

- [ ] **Step 6: Judge it against real acceptance criteria, and record the verdict**

The criteria are about segmentation quality, not a target score. A separate investigation into why three fixtures score low on the scorecard is running in parallel and is **not** complete — do not assume SAM2 was supposed to fix those, and do not use their scores as this lane's pass/fail.

For each `photo_subject` / `photo_scene` fixture, compare classical vs SAM2 on:

1. **Region count** — `PHOTO_SEGMENT_REGION_COUNT`'s `count`. The photo plan's own accept band is 20-80 final regions. SAM2 landing inside it when the classical lane does not is a win; SAM2 falling outside it when the classical lane is inside is a regression.
2. **Boundary agreement with the artwork** — render both with `cfg.debug_dir` set and compare `stage2_photo_merged.png` side by side. The question is whether region edges land on real object edges. This one is a human look, not a number, and saying so is more honest than inventing a metric for it.
3. **Preflight score and findings** — from the scorecard diff. Newly-appearing `block`-severity findings are the one signal `corpus_scorecard.py` itself is willing to call a regression outright.
4. **Wall-clock cost per job** — measured in Step 3. A large quality win that costs three minutes per photo on a single-worker queue is still a product decision, not an automatic yes.

Write the verdict — the numbers, the side-by-side impressions, and the recommendation on whether `photo_segment_sam2` should default to `True` for photo classes — into `digitizer/docs/` as a dated measurement note, following `docs/photo-prep-deps-probe-2026-08-04.md`'s shape. If SAM2 does not beat the classical lane on these fixtures, that is a legitimate and useful outcome: the flag stays `False`, the fallback means nothing regresses, and the note records what was measured so nobody re-litigates it from scratch.

- [ ] **Step 7: Commit the measurements**

```bash
git add digitizer/digitizer_core/config.py digitizer/docs/
git commit -m "docs: measured SAM2 CPU timings and corpus comparison; tune timeout from real numbers"
```

---

## Self-Review

**1. Spec coverage.**

| Requirement | Task |
| --- | --- |
| SAM2 only for `photo_subject`/`photo_scene`, never `gradient`, never `flat` | Task 5 Step 3 (dispatch condition), Task 5 Step 1 (`test_gradient_class_never_triggers_sam2`, `test_flat_class_never_calls_the_seam`, `test_flat_lane_is_byte_identical_with_the_sam2_flag_on`) |
| Isolated optional venv, weights downloaded on first use, mirroring rembg | Task 2 (README, requirements, worker `_ensure_checkpoint`), Task 2 Step 7 (`.gitignore`) |
| Silent fallback on unavailable / timeout / failure | Task 4 (seam's `(None, reason)` arm, 9 failure-mode tests), Task 5 (pipeline fallback branch + warning code) |
| Smallest checkpoint default, CPU-only, disk-aware | Task 3 (`photo_segment_sam2_checkpoint = "tiny"`), Task 2 (`device="cpu"`, CPU wheel index), Task 6 Step 1 (disk check) |
| Install from Meta's GitHub, never the PyPI `sam2` | Task 2 (README build steps, requirements comment, `test_checkpoint_table_is_meta_hosted_and_self_consistent`), Global Constraints (re-verify before Task 1) |
| Mirror `rembg_isolated/README.md` structure | Task 2 Step 6 — build it / disk / the checkpoint / sanity-check it by hand |
| Mirror `rembg_worker.py` structure | Task 2 Step 3 — argv CLI, per-mode exit codes, one docstring explaining the isolation, zero `digitizer_core` imports (enforced by test) |
| Mirror `stage1_photo_prep`'s module-level constants + `*_unavailable_reason()` | Task 3 Step 5 |
| Mirror `remove_background_seam`'s exact shape | Task 4 Step 3 — `tempfile.TemporaryDirectory`, `subprocess.run(capture_output=True, text=True, timeout=…)`, `TimeoutExpired`/`OSError`/nonzero-exit all to `(None, reason)`, never raises |
| Mirror `config.py` field naming | Task 3 Step 3 — `photo_segment_sam2*`, matching `photo_prep_background_removal*`'s shape and comment depth |
| New warning code registered like `PHOTO_BACKGROUND_REMOVAL_UNAVAILABLE` | Task 3 Step 4 |
| Extract the reusable `kept -> Quant` tail, shared by both segmenters | Task 1 Steps 5-6; consumed by Task 4 Step 3 |
| Byte-identical regression test proving the classical lane didn't move | Task 1 Steps 1-4, 7; re-run in Task 4 Step 5 |
| Refactor FIRST, before any SAM2 code | Task ordering — Task 1 is the first task and commits before Task 2 begins |
| Explicit `subprocess.run` timeout as the only queue-starvation bound | Task 3 Step 3 (`photo_segment_sam2_timeout_s` comment), Task 4 Step 3 (docstring + call), Task 4 Step 1 (`test_seam_passes_the_documented_argv_to_the_worker` asserts the kwarg) |
| Timeout default justified | Task 3 Step 3 — 180 s, reasoned from CPU-only tiny-checkpoint cost, explicitly flagged unmeasured, measured in Task 6 Step 4 |
| Overlap resolution rule, with the real SAM2 fields | Task 2 Step 3 `_paint_labels` — `area`, `predicted_iou` (both verified against Meta's source) |
| Min-area floor consistent with existing `min_detail_mm` floors | Task 4 Step 3 — `(cfg.min_detail_mm * px_per_mm) ** 2` to the worker, then the real `resolve_small_regions` |
| Masks feed the shared tail | Task 4 Step 3 `_regions_from_label_map` -> `resolve_small_regions` -> `kept_masks_to_quant` |
| Principled-vs-measured honesty | Task 3 Step 3 comments, Task 4's "Design decisions" table, Task 6 Step 4 |
| Live/manual verification task with disk + slowness caveats | Task 6 |
| Success criteria framed as segmentation quality, not a score number | Task 6 Step 6 |

No gaps found.

**2. Placeholder scan.** No "TBD", "TODO", "implement later", "add appropriate error handling", "similar to Task N", or "write tests for the above" appears in any step. Every code step carries a complete code block. Every test step names the exact command and its expected output. Three things are deliberately marked as unverified rather than invented, which is the opposite of a placeholder: (a) whether Meta's AMG notebook passes `apply_postprocessing=False` — flagged in Task 2's API-verification note, with the code taking `build_sam2`'s documented default; (b) `photo_segment_sam2_points_per_side` and `photo_segment_sam2_timeout_s` as reasoned-not-measured starting points, with Task 6 Step 4 assigned to replace them; (c) the exact install command needing a re-check against Meta's current README, called out in Global Constraints. Everything else — `SAM2AutomaticMaskGenerator`'s kwargs, `generate()`'s signature, the mask-record keys, `build_sam2`'s signature and hydra behavior, the checkpoint URLs and config names, `SAM-2` as the distribution name — was read from Meta's own source on 2026-08-10.

**3. Type consistency.** `kept_masks_to_quant` is defined once in Task 1 and called with matching keyword names in Task 1 Step 6 (`raw_count=slic_count, merged_count=merged_count, oversegment_labels=slic_labels`) and Task 4 Step 3 (`raw_count=raw_mask_count, merged_count=merged_count, raw_unit_label="SAM2 masks", oversegment_labels=labels`) — no positional/keyword drift, and `floor_warnings` is positional in both. `sam2_segment_seam`'s `(Quant | None, str | None)` return is unpacked identically in Task 4's tests and Task 5's dispatch. `sam2_segmentation_unavailable_reason()` returns `str | None` and is used only in a `is not None` test. The five config field names are spelled identically in Task 3 Step 3 (definitions), Task 3 Step 1 (defaults test), Task 4 Step 3 (four of five read by the seam), and Task 5 Step 3 (`photo_segment_sam2` in the gate). Both warning-code constant names match between Task 3 Step 4, Task 4 Step 3 (`PHOTO_SAM2_SEGMENTED`), Task 5 Step 3 (`PHOTO_SAM2_SEGMENTATION_UNAVAILABLE`) and every test that imports them. The worker's argv order (`in, out, tier, points_per_side, min_mask_region_area`) matches between Task 2 Step 3's `main()`, Task 2 Step 1's CLI tests, Task 4 Step 3's `subprocess.run` list and Task 4 Step 1's `_fake_worker` (`cmd[2]` = input, `cmd[3]` = output) and argv assertion (`cmd[4]`/`cmd[5]`/`cmd[6]`). The `.npz` key names match between the worker's `np.savez_compressed`, the seam's `np.load` reads, and the tests' synthetic writer. `RegionMask(mask=…, layer=…, source=…)` matches `stage3_segment.RegionMask`'s real field names.
