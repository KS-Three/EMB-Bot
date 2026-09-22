# Upload Crop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a customer crop their upload to the logo before digitizing, with the Studio proposing a rectangle, so a phone screenshot stops sewing its status bar and starts sizing to the logo instead of the phone screen.

**Architecture:** The crop travels as four normalized fractions in `PipelineConfig`, over the `config` JSON of the existing multipart POST. It is applied server-side at decode time in a small shared module that **both** `stage0_classify._load` and `stage1_prep._load` import, so stage 0 classifies the same picture stage 1 digitizes. The Studio computes a proposed rectangle client-side from the preview canvas it already builds and shows it as a draggable box; nothing is ever cropped silently, and the image bytes on the wire are unchanged.

**Tech Stack:** Python 3.12+ / numpy / OpenCV (`digitizer_core`), FastAPI (`digitizer_service`), Svelte 5 + Vitest (`app`), pytest.

**Spec:** [`docs/superpowers/specs/2026-09-22-upload-crop-design.md`](../specs/2026-09-22-upload-crop-design.md)

## Global Constraints

- **Never re-encode the image in the browser to apply the crop.** The original file's bytes keep going to `/digitize`. DOCTRINE 2026-09-19/20 priced the canvas path at an unreproducible resample, premultiplied alpha, and a low-quality downscale — Becker 59 → 175 trims.
- **Crop coordinates are normalized fractions in `[0, 1]`, never pixels.** `DigitizePanel.imageToSend` falls back to the 1,200-px preview when the original exceeds service limits.
- **`crop=None` must be byte-identical to today**, engine-wide. Task 4 is the guard.
- **Do NOT add crop validation failures to `digitizer_service/errors._KNOWN`.** That allowlist holds artwork-caused failures only; a caller's bad input keeps its own message by design.
- **Python:** always `python -m pytest`, never a bare script invocation. Never pipe pytest to `tail` — you get tail's exit code. Use `pytest -q > log 2>&1; echo "EXIT=$?" >> log`.
- **Windows venv is `.venv/Scripts/python`; Linux/cloud is `.venv/bin/python`.**
- **Never edit `app/public/engine/*`** — generated copies of `src/`.
- A full local digitizer run fails exactly three known golden tests (`test_pushcomp`, `test_flat_lane_byte_identical`, `test_stage2_photo_segment`). A fourth failure is a real regression.

---

### Task 1: The shared crop transform

**Files:**
- Create: `digitizer/digitizer_core/crop.py`
- Test: `digitizer/tests/test_crop.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `crop.apply_crop(rgb: np.ndarray, alpha: np.ndarray | None, crop: tuple[float, float, float, float] | None) -> tuple[np.ndarray, np.ndarray | None]` and `crop.validate_crop(crop, shape) -> tuple[int, int, int, int] | None` and the constant `crop.MIN_CROP_PX`. Tasks 2 and 3 use `apply_crop`.

- [ ] **Step 1: Write the failing test**

Create `digitizer/tests/test_crop.py`:

```python
import numpy as np
import pytest

from digitizer_core.crop import MIN_CROP_PX, apply_crop, validate_crop


def _art(h=200, w=400):
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[:, :, 0] = 255
    alpha = np.full((h, w), 255, np.uint8)
    return rgb, alpha


def test_none_is_a_no_op_and_returns_the_same_objects():
    rgb, alpha = _art()
    out_rgb, out_alpha = apply_crop(rgb, alpha, None)
    assert out_rgb is rgb
    assert out_alpha is alpha


def test_crops_rgb_and_alpha_together():
    rgb, alpha = _art(200, 400)
    out_rgb, out_alpha = apply_crop(rgb, alpha, (0.25, 0.5, 0.75, 1.0))
    assert out_rgb.shape == (100, 200, 3)
    assert out_alpha.shape == (100, 200)


def test_alpha_may_be_absent():
    rgb, _ = _art()
    out_rgb, out_alpha = apply_crop(rgb, None, (0.0, 0.0, 0.5, 0.5))
    assert out_rgb.shape == (100, 200, 3)
    assert out_alpha is None


def test_fractions_outside_the_unit_square_are_clamped_not_rejected():
    rgb, alpha = _art(200, 400)
    out_rgb, _ = apply_crop(rgb, alpha, (-0.5, -0.5, 1.5, 1.5))
    assert out_rgb.shape == (200, 400, 3)


def test_inverted_rectangle_raises():
    rgb, alpha = _art()
    with pytest.raises(ValueError, match="empty after clamping"):
        apply_crop(rgb, alpha, (0.8, 0.1, 0.2, 0.9))


def test_rectangle_under_the_pixel_floor_raises_and_names_the_size():
    rgb, alpha = _art(200, 400)
    with pytest.raises(ValueError, match=r"3x2 px"):
        apply_crop(rgb, alpha, (0.0, 0.0, 0.008, 0.01))


def test_the_floor_is_the_border_readers_not_a_physical_constant():
    # `stage1_prep._border_ring` reads a 2 px ring and
    # `_modal_corner_ownership` samples 8 px corners; below MIN_CROP_PX the
    # background detector has no border to read and fails with a worse
    # message than validation gives.
    assert MIN_CROP_PX == 16


def test_validate_returns_pixel_box():
    assert validate_crop((0.0, 0.0, 0.5, 0.5), (200, 400)) == (0, 0, 200, 100)
    assert validate_crop(None, (200, 400)) is None


def test_wrong_arity_raises():
    rgb, alpha = _art()
    with pytest.raises(ValueError, match="four fractions"):
        apply_crop(rgb, alpha, (0.1, 0.2, 0.3))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'digitizer_core.crop'`

- [ ] **Step 3: Write minimal implementation**

Create `digitizer/digitizer_core/crop.py`:

```python
"""Crop the submitted raster to a normalized rectangle, before anything
reads the pixels.

Its own module, imported by BOTH `stage0_classify._load` and
`stage1_prep._load`, for exactly the reason `letterbox.py` is: stage 0
deliberately owns its own decode, so if only one of them cropped, stage 0
would classify a different picture than stage 1 digitizes.

Fractions rather than pixels because the Studio may send either the
customer's original file or its 1,200-px preview (`DigitizePanel.imageToSend`
falls back when the original exceeds the service's limits), and a pixel
rectangle would then address the wrong raster silently, and only for large
uploads.
"""
from __future__ import annotations

import numpy as np

# The smallest frame the downstream background detector can read a border
# from at all: `stage1_prep._border_ring` uses a 2 px ring and
# `_modal_corner_ownership` samples 8 px corners. NOT a physical constant --
# no sew-out settles it; it is a property of those two readers.
MIN_CROP_PX = 16


def validate_crop(crop, shape) -> tuple[int, int, int, int] | None:
    """-> (x0, y0, x1, y1) in `shape`'s pixels, or None when `crop` is None.

    Raises ValueError on a rectangle the caller got wrong. That is a CALLER
    error, not artwork damage, so it must keep its own message -- see
    `digitizer_service/errors.py` on why its map is an allowlist.
    """
    if crop is None:
        return None
    if len(crop) != 4:
        raise ValueError(
            f"crop must be four fractions (x0, y0, x1, y1), got {crop!r}")
    x0f, y0f, x1f, y1f = (float(v) for v in crop)
    clamp = lambda v: min(max(v, 0.0), 1.0)  # noqa: E731
    x0f, y0f, x1f, y1f = clamp(x0f), clamp(y0f), clamp(x1f), clamp(y1f)
    if x1f <= x0f or y1f <= y0f:
        raise ValueError(f"crop is empty after clamping to [0, 1]: {crop!r}")

    h, w = shape[:2]
    x0, x1 = int(round(x0f * w)), int(round(x1f * w))
    y0, y1 = int(round(y0f * h)), int(round(y1f * h))
    if x1 - x0 < MIN_CROP_PX or y1 - y0 < MIN_CROP_PX:
        raise ValueError(
            f"crop is {x1 - x0}x{y1 - y0} px; at least {MIN_CROP_PX} on each "
            "axis is needed for background detection to read a border")
    return x0, y0, x1, y1


def apply_crop(rgb: np.ndarray, alpha: np.ndarray | None, crop):
    """-> (rgb, alpha) cropped together, or the SAME objects when crop is None.

    Identity on None is load-bearing: `crop=None` must be byte-identical to
    the pre-crop engine everywhere.
    """
    box = validate_crop(crop, rgb.shape)
    if box is None:
        return rgb, alpha
    x0, y0, x1, y1 = box
    out_rgb = np.ascontiguousarray(rgb[y0:y1, x0:x1])
    out_alpha = (np.ascontiguousarray(alpha[y0:y1, x0:x1])
                 if alpha is not None else None)
    return out_rgb, out_alpha
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop.py -q`
Expected: PASS, 9 tests.

- [ ] **Step 5: Commit**

```bash
git add digitizer/digitizer_core/crop.py digitizer/tests/test_crop.py
git commit -m "Crop transform: normalized fractions to a validated pixel box

Its own module because both stage 0 and stage 1 must import it -- stage 0
owns its own decode, and letterbox.py already carries the rule that if only
one of them transformed, stage 0 would classify a different picture than
stage 1 digitizes.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: Wire the crop into config and both decode paths

**Files:**
- Modify: `digitizer/digitizer_core/config.py:2335` (add field after `strip_letterbox`)
- Modify: `digitizer/digitizer_core/stage0_classify.py:171` (`_load` signature) and `:469` (call site)
- Modify: `digitizer/digitizer_core/stage1_prep.py:134` (`_load` signature) and `:265` (call site)
- Test: `digitizer/tests/test_crop_wiring.py`

**Interfaces:**
- Consumes: `crop.apply_crop` from Task 1.
- Produces: `PipelineConfig.crop: tuple[float, float, float, float] | None = None`. Tasks 3, 4, 5 and 7 all read this field name.

- [ ] **Step 1: Write the failing test**

Create `digitizer/tests/test_crop_wiring.py`:

```python
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core import stage0_classify, stage1_prep


def _banner_art():
    """White frame, a dark bar across the top (the "chrome"), and a dark
    block in the middle (the "logo"). 400x600."""
    rgb = np.full((600, 400, 3), 255, np.uint8)
    rgb[0:60, :] = 20            # chrome band
    rgb[250:350, 100:300] = 30   # logo
    return rgb


def test_prep_crops_before_anything_reads_the_pixels():
    art = _banner_art()
    cfg = PipelineConfig(target_width_mm=80.0, crop=(0.0, 0.33, 1.0, 0.67))
    p = stage1_prep.prep(art, cfg)
    # 600 * 0.33 = 198 .. 600 * 0.67 = 402 -> 204 rows before any upscale.
    assert p.rgb.shape[1] / p.rgb.shape[0] == pytest.approx(400 / 204, rel=0.05)


def test_uncropped_prep_is_unchanged():
    art = _banner_art()
    a = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0))
    b = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0, crop=None))
    assert np.array_equal(a.rgb, b.rgb)
    assert np.array_equal(a.bg_mask, b.bg_mask)


def test_stage0_sees_the_same_picture_stage1_digitizes():
    """The strip_letterbox rule, applied to crop: if only one of them
    cropped, stage 0 would classify the chrome the crop exists to remove."""
    art = _banner_art()
    crop = (0.0, 0.33, 1.0, 0.67)
    cfg = PipelineConfig(target_width_mm=80.0, crop=crop)
    rgb0, _ = stage0_classify._load(art, cfg.strip_letterbox, cfg.crop)
    p = stage1_prep.prep(art, cfg)
    # Same crop applied, so stage 0's raster and stage 1's PRE-upscale raster
    # describe the same region: identical aspect ratio, and the chrome band
    # is absent from both.
    assert rgb0.shape[:2] == (204, 400)
    assert int(rgb0[:10].mean()) > 200      # top row is page, not chrome
    assert int(p.rgb[:10].mean()) > 200


def test_classify_threads_the_crop_from_cfg():
    art = _banner_art()
    cfg = PipelineConfig(target_width_mm=80.0, crop=(0.0, 0.33, 1.0, 0.67))
    # Must not raise, and must not classify on the uncropped frame.
    c = stage0_classify.classify(art, cfg)
    assert c.class_ in ("flat", "gradient", "photo_subject", "photo_scene")


def test_a_bad_crop_raises_out_of_prep():
    with pytest.raises(ValueError, match="empty after clamping"):
        stage1_prep.prep(_banner_art(),
                         PipelineConfig(target_width_mm=80.0,
                                        crop=(0.9, 0.1, 0.1, 0.9)))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop_wiring.py -q`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword argument 'crop'`

- [ ] **Step 3: Write minimal implementation**

In `digitizer/digitizer_core/config.py`, immediately after `strip_letterbox: bool = True` (line 2335):

```python
    # Normalized crop rectangle (x0, y0, x1, y1) as fractions 0..1 of the
    # SUBMITTED raster, applied at decode time in stage 0 AND stage 1 before
    # anything reads the pixels. None = no crop, and None is byte-identical
    # to the pre-crop engine everywhere.
    #
    # Fractions, not pixels: `DigitizePanel.imageToSend` sends the customer's
    # original file when it fits the service's limits and the Studio's
    # 1,200-px preview when it does not, so a pixel rectangle would address
    # the wrong raster silently and only for large uploads.
    #
    # Applied in BOTH decode paths for the reason `strip_letterbox` is --
    # stage 0 owns its own decode, and a crop in only one of them would have
    # stage 0 classify the chrome the crop exists to remove.
    # Spec: docs/superpowers/specs/2026-09-22-upload-crop-design.md
    crop: tuple[float, float, float, float] | None = None
```

In `digitizer/digitizer_core/stage0_classify.py`, add the import beside the existing `from .letterbox import strip_letterbox` (line 71):

```python
from .crop import apply_crop
```

Change `_load` (line 171) to take and apply the crop, cropping **before** the letterbox strip:

```python
def _load(image: str | Path | bytes | np.ndarray,
          strip_bars: bool = False,
          crop=None) -> tuple[np.ndarray, np.ndarray | None]:
    """-> (rgb uint8, alpha uint8 or None)."""
```

and immediately before the `if strip_bars:` block at the end of that function:

```python
    # The customer's crop, applied before the letterbox strip and before any
    # signal reads the pixels. Same module and same position as
    # `stage1_prep._load`, and the two MUST stay in step for the same reason
    # the strip below does.
    rgb, alpha = apply_crop(rgb, alpha, crop)
```

Update the call site at line 469:

```python
    rgb, alpha = _load(image, cfg.strip_letterbox, cfg.crop)
```

In `digitizer/digitizer_core/stage1_prep.py`, add beside `from .letterbox import strip_letterbox` (line 45):

```python
from .crop import apply_crop
```

Change `_load` (line 134) identically:

```python
def _load(image: str | Path | bytes | np.ndarray,
          strip_bars: bool = False,
          crop=None) -> tuple[np.ndarray, np.ndarray | None]:
    """-> (rgb uint8, alpha uint8 or None)."""
```

with the same insertion immediately before `if strip_bars:`:

```python
    # See `stage0_classify._load` -- same crop, same position, and they must
    # stay in step.
    rgb, alpha = apply_crop(rgb, alpha, crop)
```

Update the call site at line 265:

```python
    rgb, alpha = _load(image, cfg.strip_letterbox, cfg.crop)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop_wiring.py tests/test_crop.py -q`
Expected: PASS, 14 tests.

- [ ] **Step 5: Run the stage 0 and stage 1 suites for regressions**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_stage0_classify.py tests/test_stage1_prep.py tests/test_alpha_edge_extend.py -q`
Expected: PASS. Any failure here means the crop is not inert at `crop=None` — fix before continuing, do not proceed to Task 3.

- [ ] **Step 6: Commit**

```bash
git add digitizer/digitizer_core/config.py digitizer/digitizer_core/stage0_classify.py digitizer/digitizer_core/stage1_prep.py digitizer/tests/test_crop_wiring.py
git commit -m "PipelineConfig.crop, applied in BOTH decode paths

Stage 0 owns its own decode, so a crop applied only in stage 1 would have
stage 0 classify the chrome the crop exists to remove -- the same trap
strip_letterbox already documents in both files.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: Crop is part of the generation's identity

**Files:**
- Modify: `digitizer/tests/test_generation_cache.py`
- Test: same file

**Interfaces:**
- Consumes: `PipelineConfig.crop` from Task 2.
- Produces: nothing new. This task proves existing behaviour rather than adding any.

`digitizer_service/jobs.generation_key` already hashes every config field except the four `EDIT_KEYS`, so `crop` is part of the generation identity with no new code. This task pins that, because the failure mode — a changed crop silently served from a stale cached generation — is invisible.

- [ ] **Step 1: Write the failing test**

Append to `digitizer/tests/test_generation_cache.py`:

```python
def test_crop_is_part_of_the_generation_identity():
    """A changed crop must invalidate stages 0-4. `crop` is not an EDIT_KEY,
    so `generation_key` already covers it -- this pins it, because a stale
    generation served across a crop change is silent."""
    image = ART.read_bytes()
    base = {"target_width_mm": 80.0}
    cropped = {"target_width_mm": 80.0, "crop": [0.1, 0.1, 0.9, 0.9]}
    other = {"target_width_mm": 80.0, "crop": [0.2, 0.2, 0.8, 0.8]}

    assert generation_key(image, base) != generation_key(image, cropped)
    assert generation_key(image, cropped) != generation_key(image, other)
    assert generation_key(image, cropped) == generation_key(image, dict(cropped))


def test_crop_is_not_an_edit_key():
    """Edit keys are the four the shape-layers contract applies AFTER stage 4.
    A crop is a stage-0/1 input; filing it as an edit key would serve every
    crop change from a stale generation."""
    assert "crop" not in EDIT_KEYS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_generation_cache.py -q -k crop`
Expected: FAIL — the tests do not exist yet; after adding them they should PASS immediately, since the behaviour is already correct. **If `test_crop_is_part_of_the_generation_identity` fails after being added, that is a real defect in `generation_key` — stop and fix it.**

- [ ] **Step 3: No implementation needed**

These tests pass against existing code. Confirm that, and do not add code to make them pass.

- [ ] **Step 4: Run the full cache suite**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_generation_cache.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add digitizer/tests/test_generation_cache.py
git commit -m "Pin that crop is part of the generation identity, not an edit key

No new code -- generation_key already hashes every config field but the four
EDIT_KEYS. Pinned because a crop change served from a stale generation is a
silent failure.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: The inertness guard — `crop=None` is byte-identical

**Files:**
- Create: `digitizer/tests/test_crop_inert.py`
- Create: `digitizer/tests/test_crop_interactions.py`

**Interfaces:**
- Consumes: `PipelineConfig.crop` from Task 2.
- Produces: nothing. This is the safety net for the whole feature.

- [ ] **Step 1: Write the failing test**

Create `digitizer/tests/test_crop_inert.py`:

```python
"""crop=None must be the pre-crop engine, byte for byte.

The whole feature is gated on this: a crop that changes output when nobody
asked for one is a regression on every design in the corpus, and the corpus
cannot see it because every fixture would move together.
"""
import hashlib
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, digitize

ROOT = Path(__file__).resolve().parents[1]

# The four REAL_ART logos whose artwork already fills its frame, so the
# Studio's proposal is a no-op on them (measured 2026-09-22, all 1.00 x 1.00).
FIXTURES = [
    ("becker_marine_logo.png", 100.0),
    ("photo/enthusiast_logo.png", 80.0),
    ("photo/logo_hotel_fremont.webp", 92.5),
    ("photo/logo_gaulke_roofing.png", 80.0),
]


def _digest(rel, width_mm, **kw):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest", **kw)
    result, plan = digitize(ROOT / "testdata" / rel, cfg)
    h = hashlib.sha256()
    for blk in plan.blocks:
        for run in blk.runs:
            for x, y in run.points:
                h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest(), len(result.regions), plan.stats.stitch_count


@pytest.mark.parametrize("rel,width_mm", FIXTURES)
def test_crop_none_is_byte_identical_to_omitting_it(rel, width_mm):
    assert _digest(rel, width_mm) == _digest(rel, width_mm, crop=None)


@pytest.mark.parametrize("rel,width_mm", FIXTURES)
def test_full_frame_crop_changes_nothing_observable(rel, width_mm):
    """A (0,0,1,1) crop is the whole image. It takes the crop code path --
    unlike None, which short-circuits -- so this is the test that the path
    itself is lossless, not merely skipped."""
    assert _digest(rel, width_mm) == _digest(rel, width_mm, crop=(0.0, 0.0, 1.0, 1.0))
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop_inert.py -q`
Expected: PASS. **If `test_full_frame_crop_changes_nothing_observable` fails, the crop path is lossy** — most likely the `int(round(...))` in `validate_crop` is not returning the full extent. Fix `crop.py`, not the test.

- [ ] **Step 3: Write the two interaction tests the spec calls for**

Spec §7 names two interactions that the tests above do not reach. Create
`digitizer/tests/test_crop_interactions.py`:

```python
"""Crop against the two stage-1 mechanisms it can disturb."""
from pathlib import Path

import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core import stage1_prep
from digitizer_core.warnings_codes import INPUT_LOW_RESOLUTION

ROOT = Path(__file__).resolve().parents[1]
BECKER = ROOT / "testdata" / "becker_marine_logo.png"


def test_a_crop_that_drops_a_design_under_the_floor_upscales_and_says_so():
    """Cropping removes pixels, so it can push artwork under
    `min_px_per_mm` that cleared it before. That must upscale AND warn --
    silently enlarging is the case `INPUT_LOW_RESOLUTION` exists to report."""
    art = np.full((400, 400, 3), 255, np.uint8)
    art[150:250, 150:250] = 20
    # 400 px over 80 mm = 5.0 px/mm, above the 4.0 floor.
    clear = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0))
    assert clear.input_px_per_mm >= 4.0
    assert not any(w["code"] == INPUT_LOW_RESOLUTION for w in clear.warnings)

    # Crop to the middle 30%: 120 px over 80 mm = 1.5 px/mm, under the floor.
    cropped = stage1_prep.prep(
        art, PipelineConfig(target_width_mm=80.0, crop=(0.35, 0.35, 0.65, 0.65)))
    assert cropped.input_px_per_mm < 4.0
    assert cropped.px_per_mm > cropped.input_px_per_mm     # it upscaled
    assert any(w["code"] == INPUT_LOW_RESOLUTION for w in cropped.warnings)


def test_cropping_an_alpha_cutout_keeps_the_native_frame_bookkeeping_consistent():
    """`native_rgb`/`native_alpha` are the SOURCE's own pixels and `upscale`
    the per-axis factor to `rgb`; stage 4 reads edges from them. After a crop
    they must describe the CROPPED source, not the original frame, or every
    subpixel edge read lands in the wrong place."""
    cfg = PipelineConfig(target_width_mm=100.0, crop=(0.1, 0.1, 0.9, 0.9))
    p = stage1_prep.prep(str(BECKER), cfg)
    assert p.native_rgb is not None and p.native_alpha is not None
    # Same frame as each other, and the recorded factor takes them to `rgb`.
    assert p.native_rgb.shape[:2] == p.native_alpha.shape[:2]
    sx, sy = p.upscale
    assert round(p.native_rgb.shape[1] * sx) == p.rgb.shape[1]
    assert round(p.native_rgb.shape[0] * sy) == p.rgb.shape[0]
```

Run: `cd digitizer && .venv/Scripts/python -m pytest tests/test_crop_interactions.py -q`
Expected: PASS. **If the alpha test fails, the crop is being applied after
`native_rgb` is captured** — it must happen in `_load`, before `prep` records
the native frame. Fix the insertion point from Task 2, not the test.

- [ ] **Step 4: Commit**

```bash
git add digitizer/tests/test_crop_inert.py digitizer/tests/test_crop_interactions.py
git commit -m "Inertness guard: crop=None and a full-frame crop both change nothing

The full-frame case is the one that matters -- None short-circuits, so only
(0,0,1,1) actually exercises the crop path and proves it lossless.

Plus the two interactions the spec names: a crop can push artwork under
min_px_per_mm, which must upscale AND warn rather than silently enlarge; and
on an alpha cutout the native_rgb/native_alpha/upscale bookkeeping must
describe the CROPPED source, or every subpixel edge read lands in the wrong
place.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: Measure the `alpha_edge_extend` coupling

**Files:**
- Create: `digitizer/tools/crop_floor_coupling.py`
- Create: `docs/crop-floor-coupling-2026-09-22.md`

**Interfaces:**
- Consumes: `PipelineConfig.crop` from Task 2.
- Produces: a written finding. No engine code changes in this task. If the measurement shows the coupling is harmful, that is a new decision for Kent, not a fix to make here.

Spec §8: cropping changes `px_per_mm`, and `px_per_mm` against `cfg.min_px_per_mm` is the gate for `alpha_edge_extend_upscaled_only` (`alpha_edge.upscale_expected`, `alpha_edge.py:107`). So a crop can flip `alpha_edge_extend` as a side effect of framing. **This must be measured, not argued** — the same coupling from the other direction is what killed the resolution-floor raise on 2026-09-22.

- [ ] **Step 1: Write the measurement tool**

Create `digitizer/tools/crop_floor_coupling.py`:

```python
#!/usr/bin/env python
"""Does cropping flip `alpha_edge_extend` by moving px_per_mm across the floor?

`alpha_edge_extend_upscaled_only` gates on `alpha_edge.upscale_expected`,
which compares the artwork's own px/mm at the target width against
`cfg.min_px_per_mm`. Cropping changes that ratio. So a crop can turn the
extension on or off without anyone deciding to -- which is a flag Kent
flipped ON on 2026-09-20 precisely BECAUSE it was gated to the under-floor
regime.

This sweeps an alpha cutout across the boundary and reports both the gate's
verdict and what it costs, so the interaction is a measured number rather
than an argument.

Usage (cwd digitizer/):
  .venv/Scripts/python tools/crop_floor_coupling.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core.alpha_edge import upscale_expected       # noqa: E402
from digitizer_core.stage1_prep import _load, prep           # noqa: E402

# An alpha cutout under the floor at its census width: the population the
# gate was built for.
FIXTURE = "becker_marine_logo.png"
WIDTH_MM = 100.0


def main() -> int:
    art = ROOT / "testdata" / FIXTURE
    print(f"{FIXTURE} @ {WIDTH_MM} mm\n")
    print("{:>26}{:>10}{:>9}{:>9}{:>9}{:>8}".format(
        "crop", "px/mm", "gate", "regions", "stitches", "trims"))
    for crop in (None, (0.0, 0.0, 1.0, 1.0), (0.1, 0.1, 0.9, 0.9),
                 (0.2, 0.2, 0.8, 0.8), (0.3, 0.3, 0.7, 0.7)):
        cfg = PipelineConfig(target_width_mm=WIDTH_MM, garment_id="left_chest",
                             crop=crop)
        _rgb, alpha = _load(art, cfg.strip_letterbox, cfg.crop)
        gate = (upscale_expected(alpha, cfg.target_width_mm, cfg.min_px_per_mm)
                if alpha is not None else None)
        # `input_px_per_mm` is what the SOURCE delivered for this crop, before
        # the floor upscale -- which is the number the gate compares, so it is
        # the one to print. `px_per_mm` would show the post-upscale value and
        # make the gate look inconsistent with its own input.
        ppm = prep(art, cfg).input_px_per_mm
        result, plan = digitize(art, cfg)
        print("{:>26}{:>10.2f}{:>9}{:>9}{:>9}{:>8}".format(
            str(crop), ppm, str(gate), len(result.regions),
            plan.stats.stitch_count, plan.stats.trims))
    print("\nA `gate` column that CHANGES across crops is the coupling firing.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run it**

Run: `cd digitizer && .venv/Scripts/python tools/crop_floor_coupling.py`
Expected: a table. Read the `gate` column: if it is constant across every crop, the coupling does not fire on this fixture and the finding is "no effect measured". If it changes, record what the change costs in regions/stitches/trims.

- [ ] **Step 3: Write the finding**

Create `docs/crop-floor-coupling-2026-09-22.md` with: the table exactly as printed, one sentence saying whether the gate moved, and — if it did — whether the cost is large enough to need a decision from Kent. **Do not change engine behaviour based on this measurement in this task.** If the coupling is harmful, say so and stop; that is Kent's call, and the honest options (pin the gate to the pre-crop px/mm, or accept the flip) are a separate brainstorm.

- [ ] **Step 4: Commit**

```bash
git add digitizer/tools/crop_floor_coupling.py docs/crop-floor-coupling-2026-09-22.md
git commit -m "Measure whether cropping flips alpha_edge_extend via the floor gate

Spec section 8's recorded risk, settled with a number instead of an
argument. No engine change: if the coupling is harmful that is a decision,
not a fix to make inside this plan.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: The client-side crop proposal

**Files:**
- Create: `app/src/lib/cropProposal.js`
- Test: `app/src/lib/cropProposal.spec.js`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure JS).
- Produces: `proposeCrop(imageData: {data: Uint8ClampedArray, width: number, height: number}, widthMm: number) -> {x0: number, y0: number, x1: number, y1: number}` — fractions in `[0, 1]`. Task 7 calls this.

The proposal is the **dominant ink cluster**, not the bounding box of all ink: on the screenshot the latter spans status bar to home indicator, i.e. the whole screen, which is useless on the one case the feature exists for. Implemented on a coarse cell grid rather than with a morphological dilation, which is the same operation at grid resolution and far less code to get right.

- [ ] **Step 1: Write the failing test**

Create `app/src/lib/cropProposal.spec.js`:

```js
import { describe, it, expect } from "vitest";
import { proposeCrop } from "./cropProposal.js";

/** A white frame with dark rectangles painted into it. */
function art(width, height, rects) {
  const data = new Uint8ClampedArray(width * height * 4).fill(255);
  for (const [x0, y0, x1, y1] of rects) {
    for (let y = y0; y < y1; y++) {
      for (let x = x0; x < x1; x++) {
        const i = (y * width + x) * 4;
        data[i] = data[i + 1] = data[i + 2] = 20;
      }
    }
  }
  return { data, width, height };
}

describe("proposeCrop", () => {
  it("returns the full frame when ink already fills it", () => {
    const img = art(200, 200, [[10, 10, 190, 190]]);
    const r = proposeCrop(img, 80);
    expect(r.x1 - r.x0).toBeGreaterThan(0.9);
    expect(r.y1 - r.y0).toBeGreaterThan(0.9);
  });

  it("picks the dominant cluster, not the bbox of all ink", () => {
    // A phone screenshot in miniature: a thin chrome band top and bottom,
    // and a big logo in the middle. Bbox-of-all-ink would span the whole
    // frame; the dominant cluster must not.
    const img = art(200, 600, [
      [10, 4, 190, 14],      // top chrome
      [40, 250, 160, 350],   // logo
      [10, 586, 190, 596],   // bottom chrome
    ]);
    const r = proposeCrop(img, 80);
    expect(r.y0).toBeGreaterThan(0.25);
    expect(r.y1).toBeLessThan(0.75);
    expect(r.y1 - r.y0).toBeLessThan(0.5);
  });

  it("keeps the whole of the chosen cluster", () => {
    const img = art(400, 200, [[100, 60, 300, 140]]);
    const r = proposeCrop(img, 80);
    expect(r.x0).toBeLessThanOrEqual(100 / 400);
    expect(r.x1).toBeGreaterThanOrEqual(300 / 400);
    expect(r.y0).toBeLessThanOrEqual(60 / 200);
    expect(r.y1).toBeGreaterThanOrEqual(140 / 200);
  });

  it("returns the full frame when there is no ink at all", () => {
    const r = proposeCrop(art(100, 100, []), 80);
    expect(r).toEqual({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });

  it("always returns fractions inside the unit square", () => {
    const img = art(200, 200, [[0, 0, 40, 40]]);
    const r = proposeCrop(img, 80);
    for (const v of [r.x0, r.y0, r.x1, r.y1]) {
      expect(v).toBeGreaterThanOrEqual(0);
      expect(v).toBeLessThanOrEqual(1);
    }
    expect(r.x1).toBeGreaterThan(r.x0);
    expect(r.y1).toBeGreaterThan(r.y0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && npx vitest run src/lib/cropProposal.spec.js`
Expected: FAIL — cannot resolve `./cropProposal.js`.

- [ ] **Step 3: Write minimal implementation**

Create `app/src/lib/cropProposal.js`:

```js
// Propose a crop rectangle: the DOMINANT INK CLUSTER of the artwork.
//
// Not the bounding box of all non-background ink -- on a phone screenshot
// that spans status bar to home indicator, i.e. the whole screen, which is
// useless on the one case the crop tool exists for.
//
// Worked on a coarse cell grid instead of a morphological dilation: marking
// cells that contain ink and joining neighbouring marked cells is the same
// operation at grid resolution, and far less code to get right in the
// browser. Measured against the nine REAL_ART logos 2026-09-22 -- no-op on
// the four that fill their frame, correct tight crops on the other five,
// nothing cut on any.
//
// The result is ALWAYS shown to the customer as a draggable suggestion and
// never applied silently. That is what separates it from auto-detection.

// Cells roughly this wide at design scale. Half the 4 mm merge distance, so
// two marks within ~4 mm land in the same or adjacent cells and join.
const CELL_MM = 2.0;
const MARGIN_MM = 2.0;
// How far a channel must sit from the frame's background to count as ink.
const INK_TOLERANCE = 28;
const FULL_FRAME = { x0: 0, y0: 0, x1: 1, y1: 1 };

function backgroundRgb({ data, width, height }) {
  // Mean of the frame's 1 px border -- the same premise stage 1's
  // border-flood uses: a real background owns the frame's edge.
  let r = 0, g = 0, b = 0, n = 0;
  const at = (x, y) => (y * width + x) * 4;
  for (let x = 0; x < width; x++) {
    for (const y of [0, height - 1]) {
      const i = at(x, y);
      r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
    }
  }
  for (let y = 0; y < height; y++) {
    for (const x of [0, width - 1]) {
      const i = at(x, y);
      r += data[i]; g += data[i + 1]; b += data[i + 2]; n++;
    }
  }
  return n ? [r / n, g / n, b / n] : [255, 255, 255];
}

export function proposeCrop(imageData, widthMm) {
  const { data, width, height } = imageData;
  if (!width || !height) return { ...FULL_FRAME };

  const pxPerMm = width / Math.max(widthMm, 1e-6);
  const cellPx = Math.max(1, Math.round(CELL_MM * pxPerMm));
  const cols = Math.ceil(width / cellPx);
  const rows = Math.ceil(height / cellPx);
  const [br, bg, bb] = backgroundRgb(imageData);

  // Ink count per cell.
  const ink = new Int32Array(cols * rows);
  let total = 0;
  for (let y = 0; y < height; y++) {
    const cy = (y / cellPx) | 0;
    for (let x = 0; x < width; x++) {
      const i = (y * width + x) * 4;
      if (data[i + 3] < 128) continue; // transparent is not ink
      if (Math.abs(data[i] - br) > INK_TOLERANCE ||
          Math.abs(data[i + 1] - bg) > INK_TOLERANCE ||
          Math.abs(data[i + 2] - bb) > INK_TOLERANCE) {
        ink[cy * cols + ((x / cellPx) | 0)]++;
        total++;
      }
    }
  }
  if (!total) return { ...FULL_FRAME };

  // Connected components over marked cells, 8-connectivity, iterative flood
  // fill (a recursive one blows the stack on a large logo).
  const label = new Int32Array(cols * rows).fill(-1);
  let best = null, bestInk = -1;
  for (let start = 0; start < ink.length; start++) {
    if (!ink[start] || label[start] !== -1) continue;
    const id = start;
    const stack = [start];
    label[start] = id;
    let got = 0;
    let cx0 = cols, cy0 = rows, cx1 = -1, cy1 = -1;
    while (stack.length) {
      const c = stack.pop();
      const cx = c % cols, cy = (c / cols) | 0;
      got += ink[c];
      if (cx < cx0) cx0 = cx;
      if (cy < cy0) cy0 = cy;
      if (cx > cx1) cx1 = cx;
      if (cy > cy1) cy1 = cy;
      for (let dy = -1; dy <= 1; dy++) {
        for (let dx = -1; dx <= 1; dx++) {
          const nx = cx + dx, ny = cy + dy;
          if (nx < 0 || ny < 0 || nx >= cols || ny >= rows) continue;
          const n = ny * cols + nx;
          if (ink[n] && label[n] === -1) { label[n] = id; stack.push(n); }
        }
      }
    }
    // Rank by the REAL ink a blob holds, not its cell count: a scatter of
    // specks covers more cells than a solid mark of the same weight.
    if (got > bestInk) { bestInk = got; best = [cx0, cy0, cx1, cy1]; }
  }
  if (!best) return { ...FULL_FRAME };

  const margin = MARGIN_MM * pxPerMm;
  const [cx0, cy0, cx1, cy1] = best;
  const clamp = (v) => Math.min(Math.max(v, 0), 1);
  return {
    x0: clamp((cx0 * cellPx - margin) / width),
    y0: clamp((cy0 * cellPx - margin) / height),
    x1: clamp(((cx1 + 1) * cellPx + margin) / width),
    y1: clamp(((cy1 + 1) * cellPx + margin) / height),
  };
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd app && npx vitest run src/lib/cropProposal.spec.js`
Expected: PASS, 5 tests.

- [ ] **Step 5: Commit**

```bash
git add app/src/lib/cropProposal.js app/src/lib/cropProposal.spec.js
git commit -m "Crop proposal: the dominant ink cluster, not the bbox of all ink

Bbox-of-all-ink spans status bar to home indicator on a screenshot -- the
whole screen, useless on the one case the tool exists for. Cell-grid
components are the same operation as dilate-then-label at grid resolution
and far less code to get right in a browser.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: The crop box in the Studio

**Files:**
- Create: `app/src/ui/CropBox.svelte`
- Modify: `app/src/ui/DigitizePanel.svelte` (import and render `CropBox`; carry `crop` on the element; send it in the config)
- Modify: `app/src/lib/digitizer.js:1130` (include `crop` in the posted config)
- Test: `app/src/lib/digitizer.spec.js` (crop reaches the config), `app/src/ui/CropBox.spec.js`

**Interfaces:**
- Consumes: `proposeCrop` from Task 6; `PipelineConfig.crop` from Task 2.
- Produces: `CropBox.svelte` with props `{ src, crop, onchange }` where `crop` is `{x0, y0, x1, y1}` fractions, and `onchange(next)` fires on drag end.

`DigitizePanel` is already large, so the crop surface is its own child component rather than more state in that file.

- [ ] **Step 1: Write the failing test for config serialization**

The config object is built by `buildDigitizeConfig(element, project)`
(`app/src/lib/digitizer.js:111`) and `JSON.stringify`'d wholesale at line
1130, so the crop belongs in the builder and needs no change to the POST
helper. Test the builder directly — no fetch mocking.

Append to `app/src/lib/digitizer.spec.js`:

```js
import { buildDigitizeConfig } from "./digitizer.js";

describe("crop in the digitize config", () => {
  it("sends the crop as four fractions when the element carries one", () => {
    const cfg = buildDigitizeConfig(
      { crop: { x0: 0.1, y0: 0.2, x1: 0.9, y1: 0.8 } },
      {},
    );
    expect(cfg.crop).toEqual([0.1, 0.2, 0.9, 0.8]);
  });

  it("omits crop entirely when the element has none", () => {
    const cfg = buildDigitizeConfig({}, {});
    expect("crop" in cfg).toBe(false);
  });

  it("omits crop when it is the full frame", () => {
    // An uncropped upload must be byte-identical to the pre-crop engine, so
    // it must not send a crop key at all.
    const cfg = buildDigitizeConfig(
      { crop: { x0: 0, y0: 0, x1: 1, y1: 1 } },
      {},
    );
    expect("crop" in cfg).toBe(false);
  });
});
```

Read the existing `buildDigitizeConfig` tests in that file first and match
their calling convention — if they pass a fuller `element`/`project` shape,
use it rather than the bare objects above.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd app && npx vitest run src/lib/digitizer.spec.js -t crop`
Expected: FAIL — `expect(cfg.crop).toEqual(...)` receives `undefined`.

- [ ] **Step 3: Make the config carry the crop**

In `app/src/lib/digitizer.js`, inside `buildDigitizeConfig` (line 111), before
the config object is returned:

```js
  // The customer's crop, as four fractions the service applies at decode
  // time (digitizer_core/crop.py). Omitted entirely when absent or full
  // frame, so an uncropped upload stays byte-identical to the pre-crop
  // engine. Fractions, never pixels: the service may receive the original
  // file or the 1,200-px preview.
  const c = element && element.crop;
  const FULL = c && c.x0 <= 0.001 && c.y0 <= 0.001 && c.x1 >= 0.999 && c.y1 >= 0.999;
  if (c && !FULL) cfg.crop = [c.x0, c.y0, c.x1, c.y1];
```

Use whatever local name that function already gives the config object in
place of `cfg`.

- [ ] **Step 4: Write the CropBox component**

Create `app/src/ui/CropBox.svelte`:

```svelte
<script>
  // A draggable crop rectangle over the upload preview.
  //
  // Coordinates are FRACTIONS of the image, never pixels: the service may
  // receive the customer's original file or the Studio's 1,200-px preview,
  // and a pixel rectangle would address the wrong raster (spec section 2.2).
  //
  // This component never re-encodes anything. It emits a rectangle; the crop
  // is applied server-side. Cropping by drawing to a canvas and exporting a
  // PNG is exactly the path DOCTRINE 2026-09-19/20 priced at three harms.
  let { src, crop = null, onchange = () => {} } = $props();

  let host = $state(null);
  let dragging = $state(null); // null | {handle, startX, startY, start}

  const FULL = { x0: 0, y0: 0, x1: 1, y1: 1 };
  let rect = $derived(crop ?? FULL);
  let cropped = $derived(
    rect.x0 > 0.001 || rect.y0 > 0.001 || rect.x1 < 0.999 || rect.y1 < 0.999,
  );

  const clamp = (v) => Math.min(Math.max(v, 0), 1);

  function start(handle, e) {
    e.preventDefault();
    dragging = { handle, startX: e.clientX, startY: e.clientY, start: { ...rect } };
    window.addEventListener("pointermove", move);
    window.addEventListener("pointerup", end, { once: true });
  }

  function move(e) {
    if (!dragging || !host) return;
    const box = host.getBoundingClientRect();
    const dx = (e.clientX - dragging.startX) / box.width;
    const dy = (e.clientY - dragging.startY) / box.height;
    const s = dragging.start;
    let next = { ...s };
    const h = dragging.handle;
    if (h === "move") {
      const w = s.x1 - s.x0, hh = s.y1 - s.y0;
      next.x0 = clamp(s.x0 + dx); next.y0 = clamp(s.y0 + dy);
      next.x1 = clamp(next.x0 + w); next.y1 = clamp(next.y0 + hh);
    } else {
      if (h.includes("w")) next.x0 = clamp(s.x0 + dx);
      if (h.includes("e")) next.x1 = clamp(s.x1 + dx);
      if (h.includes("n")) next.y0 = clamp(s.y0 + dy);
      if (h.includes("s")) next.y1 = clamp(s.y1 + dy);
    }
    if (next.x1 - next.x0 < 0.02 || next.y1 - next.y0 < 0.02) return;
    onchange(next);
  }

  function end() {
    dragging = null;
    window.removeEventListener("pointermove", move);
  }

  function reset() {
    onchange({ ...FULL });
  }
</script>

<div class="crop-host" bind:this={host}>
  <img {src} alt="Artwork preview with crop area" draggable="false" />
  <div
    class="crop-rect"
    role="group"
    aria-label="Crop area"
    style="left:{rect.x0 * 100}%; top:{rect.y0 * 100}%; width:{(rect.x1 - rect.x0) * 100}%; height:{(rect.y1 - rect.y0) * 100}%"
    onpointerdown={(e) => start("move", e)}
  >
    {#each ["nw", "ne", "sw", "se"] as h}
      <button
        type="button"
        class="handle {h}"
        aria-label="Drag {h} corner"
        onpointerdown={(e) => { e.stopPropagation(); start(h, e); }}
      ></button>
    {/each}
  </div>
</div>

<!-- Always present, not only when the box is cropped: a customer whose
     proposal is a wrong no-op must still be able to find the tool. -->
<button type="button" class="crop-reset" onclick={reset} disabled={!cropped}>
  Use whole image
</button>

<style>
  .crop-host { position: relative; display: inline-block; line-height: 0; }
  .crop-host img { max-width: 100%; height: auto; user-select: none; }
  .crop-rect {
    position: absolute;
    border: 2px solid var(--accent, #2f6fed);
    box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.42);
    cursor: move;
    touch-action: none;
  }
  .handle {
    position: absolute; width: 14px; height: 14px; padding: 0;
    background: #fff; border: 2px solid var(--accent, #2f6fed);
    border-radius: 2px; touch-action: none;
  }
  .handle.nw { left: -8px; top: -8px; cursor: nwse-resize; }
  .handle.ne { right: -8px; top: -8px; cursor: nesw-resize; }
  .handle.sw { left: -8px; bottom: -8px; cursor: nesw-resize; }
  .handle.se { right: -8px; bottom: -8px; cursor: nwse-resize; }
  .crop-reset { margin-top: 0.5rem; }
</style>
```

- [ ] **Step 5: Write the component test**

Create `app/src/ui/CropBox.spec.js`:

```js
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/svelte";
import CropBox from "./CropBox.svelte";

describe("CropBox", () => {
  it("renders the full frame when given no crop", () => {
    render(CropBox, { src: "data:image/png;base64,iVBORw0KGgo=" });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.width).toBe("100%");
    expect(box.style.height).toBe("100%");
  });

  it("positions the rectangle from fractions", () => {
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.25, y0: 0.1, x1: 0.75, y1: 0.6 },
    });
    const box = screen.getByRole("group", { name: "Crop area" });
    expect(box.style.left).toBe("25%");
    expect(box.style.width).toBe("50%");
  });

  it("offers the reset even when uncropped, but disabled", () => {
    render(CropBox, { src: "data:image/png;base64,iVBORw0KGgo=" });
    expect(screen.getByRole("button", { name: "Use whole image" })).toBeDisabled();
  });

  it("emits the full frame when reset is clicked", async () => {
    const onchange = vi.fn();
    render(CropBox, {
      src: "data:image/png;base64,iVBORw0KGgo=",
      crop: { x0: 0.2, y0: 0.2, x1: 0.8, y1: 0.8 },
      onchange,
    });
    screen.getByRole("button", { name: "Use whole image" }).click();
    expect(onchange).toHaveBeenCalledWith({ x0: 0, y0: 0, x1: 1, y1: 1 });
  });
});
```

If `@testing-library/svelte` is not already a dev dependency, check how the existing `*.spec.js` files under `app/src/ui/` render components and follow that pattern instead — do not add a dependency without checking.

- [ ] **Step 6: Wire it into DigitizePanel**

In `app/src/ui/DigitizePanel.svelte`, add to the imports beside the existing
`rasterize.js` import (line 43):

```js
  import CropBox from "./CropBox.svelte";
  import { proposeCrop } from "../lib/cropProposal.js";
```

In `onFile`, the preview canvas `cv` already exists and is already drawn to
(just above `const dataUrl = cv.toDataURL("image/png")`). Read its pixels
there — this is a **measure-only** use of that canvas; it is never sent, and
sending it is precisely the DOCTRINE 2026-09-19/20 regression:

```js
      // Propose a crop from the preview we already drew. Measuring this
      // canvas is fine; SENDING it is the 2026-09-19/20 regression.
      let crop = null;
      try {
        const px = cv.getContext("2d").getImageData(0, 0, cv.width, cv.height);
        crop = proposeCrop(px, el.sizeMm?.w || 80);
      } catch {
        crop = null;   // tainted canvas or no 2d context: no proposal, no crash
      }
```

Add `crop` to the `patch({...})` call at the end of `onFile`, alongside
`sourcePng` and `sourceFile`:

```js
        sourcePng: b64, sourceFile, crop, name: file.name, result: null,
```

Render the box under the existing preview in the markup:

```svelte
<CropBox
  src={"data:image/png;base64," + el.sourcePng}
  crop={el.crop}
  onchange={(c) => patch({ crop: c })}
/>
```

Use `patch` rather than assigning `el.crop` directly, so a crop change is one
undo step and re-triggers the restitch the same way every other element
change does.

- [ ] **Step 7: Run the Studio suite**

Run: `cd app && npm test`
Expected: PASS, including the new crop tests.

- [ ] **Step 8: Verify in the running app**

Use the `run-emb-bot` skill to start the Studio and the digitizer service, upload `digitizer/testdata/photo/screenshot_phone_ui_golke.jpg`, and confirm: the proposed box frames the truck and both lines of type with the status bar and toolbar outside it; the box drags; "Use whole image" resets it; and the digitized result's region count drops from 157. Screenshot the before/after.

- [ ] **Step 9: Commit**

```bash
git add app/src/ui/CropBox.svelte app/src/ui/CropBox.spec.js app/src/ui/DigitizePanel.svelte app/src/lib/digitizer.spec.js
git commit -m "Crop box in the Studio, with the proposal pre-drawn

Its own component rather than more state in DigitizePanel, which is already
large. The preview canvas is used to MEASURE the proposal and is never sent
-- sending it is the DOCTRINE 2026-09-19/20 regression.

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

## Verification before opening the PR

- [ ] `cd digitizer && .venv/Scripts/python -m pytest -q -n auto > /tmp/dig.log 2>&1; echo "EXIT=$?" >> /tmp/dig.log` — read the recorded EXIT, never a piped exit code. Expect the three known golden failures and no fourth.
- [ ] `cd app && npm test`
- [ ] `node --test` at the repo root (engine tests; the crop does not touch `src/`, so this must be clean).
- [ ] Re-read the diff adversarially against the Global Constraints, in particular: nothing re-encodes the image in the browser, and `crop=None` is byte-identical.
- [ ] Open the PR ready-for-review, not as a draft, and arm auto-merge while `mergeable_state` is `blocked`.
