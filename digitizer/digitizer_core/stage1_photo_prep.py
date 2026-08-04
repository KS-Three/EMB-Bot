"""Stage 1.5 — photo prep: tone rescue + texture kill for photo classes.

Photo plan (docs/photo-digitizing-plan-2026-07-31.md) §2 rows 3-4, the
zero-new-dependency half of build step 3. Runs on `Prep.rgb` AFTER stage 1
and BEFORE the photo region former (`stage2_photo_segment`), and ONLY when
BOTH gates hold: `cfg.photo_prep` is True (opt-in, default False) AND stage 0
classified the design `photo_subject`/`photo_scene` (or the caller forced
that class). Flat and gradient lanes never enter this module — their
byte-for-byte identity is enforced by the byte-identical suites and pinned
again in `tests/test_photo_prep.py`.

What it does, in order:

1. **Tone prep** (§2 row 3, "[M present]" — plain cv2): a percentile
   contrast stretch of L (of Lab) measured over the FOREGROUND only (a big
   white canvas must not flatten the stretch), then CLAHE on L (clip 2-3,
   tiles 8x8 — the plan's own numbers, exposed as
   `cfg.photo_prep_clahe_clip` / `cfg.photo_prep_clahe_tiles`). Rescues
   shadow detail before region forming; costs milliseconds.

2. **Texture kill** (§2 row 4): erase weave/pores/JPEG grain BELOW the
   sewable detail floor while keeping real structure, so segmentation sees
   manufactured "flat art" instead of per-pixel noise. The kill scale is
   physical, not a pixel constant: `cfg.min_detail_mm * px_per_mm` — texture
   the machine cannot sew anyway. Techniques (`cfg.photo_prep_texture_kill`):

   * `"bilateral"` (DEFAULT, zero-dep, "[M present]") — iterated
     `cv2.bilateralFilter` at the kill scale.
   * `"meanshift"` (zero-dep, "[M present]") — `cv2.pyrMeanShiftFiltering`,
     the flatter posterizing alternative.
   * `"rolling_guidance"` — THE CONTRIB SEAM. `cv2.ximgproc.
     rollingGuidanceFilter` needs the opencv-contrib wheel; the repo ships
     it since 2026-08-04 (`opencv-contrib-python-headless==5.0.0.93` in
     requirements.txt/pyproject.toml, golden-verified before the swap). When
     `cv2.ximgproc` is absent (an env installed before the swap, or a
     hand-built one on the plain wheel), this FALLS BACK to `"bilateral"`
     and says so in the PHOTO_PREP_APPLIED warning's `fallback` key — never
     an error, because which wheel is installed is an environment fact, not
     a caller mistake.
   * `"none"` — tone prep only.

**Contrib-swap probe record (2026-08-04, this sandbox, kept here so nobody
re-derives it):** `opencv-contrib-python-headless==5.0.0.93` (the exact
contrib twin of the shipped `opencv-python-headless` pin) installs cleanly
from PyPI through this environment's proxy, imports as cv2 5.0.0, and
carries `ximgproc.rollingGuidanceFilter` and `ximgproc.l0Smooth`. The full
digitizer suite run against a probe venv with the contrib wheel (everything
else version-identical to the shipped venv) is the plan's gate — see
docs/photo-prep-deps-probe-2026-08-04.md for the run record. **The swap is
APPLIED as of later 2026-08-04**: requirements.txt and pyproject.toml now
pin `opencv-contrib-python-headless==5.0.0.93`, re-verified golden-safe in
a fresh venv (see the probe doc's addendum). This module needed no change
— it feature-detects `cv2.ximgproc` either way.

**rembg seam** (§2 row 1, part of build step 3) is `remove_background_seam`
at the bottom of this module — a documented no-op today, with the 2026-08-04
probe results in its docstring so wiring it is an environment decision, not
a research task.

**YuNet face priors** (§2 row 2) are REAL as of this slice:
`detect_faces_seam` runs `cv2.FaceDetectorYN` against the committed model at
`model_data/face_detection_yunet_2023mar.onnx` (sha256-verified at load) and
returns `FaceRegion`s. The model-dir convention this slice picked: small
committed inference models live in `digitizer_core/model_data/` — the same
shape as the existing `digitizer_core/chart_data/` convention for committed
data files; see `model_data/README.md` for source/sha/license per model.
Consumers: `pipeline.run_stages` (behind the same photo_prep double gate as
this module's own entry point), `stage2_photo_segment._face_local_threshold`
and `._region_classes` (protective segmentation + palette class weights),
and preflight's `_face_size_findings` (the face-size guard, via the
PHOTO_FACES_DETECTED warning).
"""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig
from .warnings_codes import PHOTO_PREP_APPLIED, warn

# Percentiles for the L-channel contrast stretch, measured over foreground.
# 2/98 rather than min/max so a handful of outlier pixels (a specular
# glint, a crushed shadow) cannot pin the stretch and neuter it.
STRETCH_LO_PCT = 2.0
STRETCH_HI_PCT = 98.0

# Texture-kill scale clamps, in px. The physical scale is
# cfg.min_detail_mm * px_per_mm; below 2px the filters are no-ops and above
# 15px bilateral's cost grows without visible benefit at stitch scale
# (structure that big is REAL detail the segmenter should see).
KILL_PX_MIN = 2
KILL_PX_MAX = 15

# bilateral: iterated passes at moderate color sigma beat one pass at
# double strength — same total smoothing, less edge halo. MEASURED
# 2026-08-04 against the seeded grain-step synthetic in
# tests/test_photo_prep.py (grain sigma 8 px-iid, CLAHE-amplified to ~27
# std): 2 passes @ sigmaColor 25 left 0.93x of the grain standing —
# useless — while 3 @ 40 leaves 0.43x with the step edge at 1.02x of its
# amplitude; 4 @ 40 reaches 0.24x but was not needed to clear the tier's
# job. Constants, not config: a filter idiom, not a design decision.
BILATERAL_PASSES = 3
BILATERAL_SIGMA_COLOR = 40.0

# rolling guidance's own color sigma — NOT shared with bilateral's, because
# the two filters read the knob differently: RGF's joint-bilateral iterations
# re-anchor on the (already-smoothed) guidance image, so at bilateral's 40 it
# leaves 0.69-0.72x of the same seeded grain standing regardless of
# iterations (measured 2026-08-04, contrib probe venv, same grain-step
# synthetic), while 60 reaches 0.19x at the default 4 iterations (0.07x at
# 8, not needed) with the step edge at 1.02x. Sweep: 40/60/80 x 4/8 iters.
RGF_SIGMA_COLOR = 60.0

# meanshift color window: big enough to fuse CLAHE-amplified grain, small
# enough that two genuinely different thread-worthy colors never fuse.
# Same 2026-08-04 sweep: sr=20 left 0.31-0.76x of the grain depending on
# amplitude; sr=25 crushes it to 0.07-0.12x with the edge untouched
# (1.01x), and sr=30+ bought nothing further.
MEANSHIFT_SR = 25.0

TEXTURE_KILL_TECHNIQUES = ("bilateral", "meanshift", "rolling_guidance", "none")


@dataclass
class PhotoPrepResult:
    rgb: np.ndarray                 # (H, W, 3) uint8 RGB, prepped
    rgb_tone: np.ndarray            # after tone prep, before texture kill (debug)
    technique: str                  # texture-kill technique actually used
    fallback: bool                  # rolling_guidance requested but unavailable
    tone_ms: float
    texture_ms: float
    warnings: list[dict] = field(default_factory=list)


# --- 1. Tone prep -------------------------------------------------------------

def _tone_prep(rgb: np.ndarray, fg: np.ndarray, cfg: PipelineConfig) -> np.ndarray:
    """Percentile contrast stretch of L (foreground-measured) + CLAHE on L."""
    lab = cv2.cvtColor(rgb, cv2.COLOR_RGB2LAB)
    L = lab[:, :, 0]

    l_fg = L[fg]
    if l_fg.size:
        lo = float(np.percentile(l_fg, STRETCH_LO_PCT))
        hi = float(np.percentile(l_fg, STRETCH_HI_PCT))
        if hi - lo >= 1.0:  # a flat-luminance image has nothing to stretch
            stretched = (L.astype(np.float32) - lo) * (255.0 / (hi - lo))
            L = np.clip(stretched, 0, 255).astype(np.uint8)

    tiles = max(1, int(cfg.photo_prep_clahe_tiles))
    clahe = cv2.createCLAHE(
        clipLimit=float(cfg.photo_prep_clahe_clip), tileGridSize=(tiles, tiles)
    )
    lab[:, :, 0] = clahe.apply(L)
    return cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)


# --- 2. Texture kill ----------------------------------------------------------

def _kill_scale_px(px_per_mm: float, cfg: PipelineConfig) -> int:
    return int(np.clip(round(cfg.min_detail_mm * px_per_mm), KILL_PX_MIN, KILL_PX_MAX))


def _bilateral(rgb: np.ndarray, kill_px: int) -> np.ndarray:
    out = rgb
    for _ in range(BILATERAL_PASSES):
        out = cv2.bilateralFilter(
            out, d=0, sigmaColor=BILATERAL_SIGMA_COLOR, sigmaSpace=float(kill_px)
        )
    return out

def _meanshift(rgb: np.ndarray, kill_px: int) -> np.ndarray:
    # pyrMeanShiftFiltering wants sp as a spatial window radius; the kill
    # scale IS that radius. Works on 3-channel 8-bit directly.
    return cv2.pyrMeanShiftFiltering(rgb, sp=float(kill_px), sr=MEANSHIFT_SR)


def _rolling_guidance(rgb: np.ndarray, kill_px: int) -> np.ndarray:
    """Requires the contrib wheel — caller has already verified
    cv2.ximgproc exists before dispatching here."""
    # sigmaSpace is the "scale" knob: structures smaller than roughly this
    # are erased, larger ones are restored by the guidance iterations —
    # exactly the scale-aware contract §2 row 4 wants.
    return cv2.ximgproc.rollingGuidanceFilter(
        rgb, sigmaColor=RGF_SIGMA_COLOR, sigmaSpace=float(kill_px)
    )


def _texture_kill(rgb: np.ndarray, kill_px: int, technique: str) -> tuple[np.ndarray, str, bool]:
    """-> (rgb, technique actually used, fallback?)."""
    if technique == "none":
        return rgb, "none", False
    if technique == "rolling_guidance":
        if hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "rollingGuidanceFilter"):
            return _rolling_guidance(rgb, kill_px), "rolling_guidance", False
        # Contrib not installed (a pre-swap env; requirements.txt ships the
        # contrib wheel since 2026-08-04) — degrade to the zero-dep default
        # rather than failing a job over a wheel.
        return _bilateral(rgb, kill_px), "bilateral", True
    if technique == "meanshift":
        return _meanshift(rgb, kill_px), "meanshift", False
    if technique == "bilateral":
        return _bilateral(rgb, kill_px), "bilateral", False
    raise ValueError(
        f"unknown photo_prep_texture_kill {technique!r} — one of {TEXTURE_KILL_TECHNIQUES}"
    )


# --- Entry point --------------------------------------------------------------

def photo_prep(rgb: np.ndarray, bg_mask: np.ndarray, px_per_mm: float,
               cfg: PipelineConfig) -> PhotoPrepResult:
    """Tone prep + texture kill. Pure function of its inputs (deterministic:
    no RNG anywhere in this module), returns a NEW rgb array — the caller
    (pipeline.run_stages) decides what to overwrite."""
    fg = ~bg_mask

    t0 = time.perf_counter()
    rgb_tone = _tone_prep(rgb, fg, cfg)
    tone_ms = (time.perf_counter() - t0) * 1000.0

    kill_px = _kill_scale_px(px_per_mm, cfg)
    t1 = time.perf_counter()
    rgb_out, used, fallback = _texture_kill(
        rgb_tone, kill_px, cfg.photo_prep_texture_kill
    )
    texture_ms = (time.perf_counter() - t1) * 1000.0

    msg = (
        f"Photo prep applied: tone (CLAHE clip {cfg.photo_prep_clahe_clip:g}, "
        f"{cfg.photo_prep_clahe_tiles}x{cfg.photo_prep_clahe_tiles} tiles) + "
        f"texture kill '{used}' at {kill_px} px."
    )
    if fallback:
        msg += (
            " ('rolling_guidance' was requested but cv2.ximgproc is not "
            "installed — fell back to 'bilateral'.)"
        )
    warnings = [
        warn(
            PHOTO_PREP_APPLIED,
            msg,
            technique=used,
            fallback=fallback,
            kill_px=kill_px,
            tone_ms=round(tone_ms, 1),
            texture_ms=round(texture_ms, 1),
        )
    ]
    return PhotoPrepResult(
        rgb=rgb_out,
        rgb_tone=rgb_tone,
        technique=used,
        fallback=fallback,
        tone_ms=tone_ms,
        texture_ms=texture_ms,
        warnings=warnings,
    )


# --- Build-step-3 dependency seams ---------------------------------------------
# rembg (below) is still a documented no-op; the YuNet face priors that used
# to share this section are real — see the YuNet block further down.

def remove_background_seam(rgb: np.ndarray, cfg: PipelineConfig) -> np.ndarray | None:
    """SEAM (photo plan §2 row 1): rembg subject cutout — binary subject
    mask + morphology at stitch scale, islands under min-sew-area dropped.
    Returns None (no mask, callers change nothing) until rembg is wired.

    Probe record, 2026-08-04, this sandbox (full detail in
    docs/photo-prep-deps-probe-2026-08-04.md):

    * `pip install rembg onnxruntime` succeeds through the proxy
      (rembg 2.0.77, onnxruntime 1.28.0).
    * The `isnet-general-use.onnx` model (178 MB) downloads fine from
      rembg's GitHub release URL through the proxy — model availability is
      NOT the blocker.
    * THE BLOCKER: rembg 2.0.77 unconditionally imports pymatting -> numba,
      and numba 0.66.0 requires numpy<2.5 while this repo's venv pins
      numpy 2.5.1 — `import rembg` raises ImportError("Numba needs NumPy
      2.4 or less") outright. Wiring rembg therefore needs one of: a numba
      release supporting numpy 2.5, a rembg release that lazies the
      pymatting import (matting is unused here — thread can't render
      alpha), or an isolated-process/venv harness for the cutout call.
      Do NOT downgrade the shared venv's numpy to force it — the k-means
      goldens' exact pins outrank a cutout dependency.
    """
    return None


# --- YuNet face priors (photo plan §2 row 2 — REAL as of this slice) ----------
#
# The model is COMMITTED (232,589 bytes — small enough that vendoring beats a
# download-cache policy) at `model_data/face_detection_yunet_2023mar.onnx`,
# fetched 2026-08-04 from opencv/opencv_zoo's LFS media endpoint
# (https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/
# face_detection_yunet/face_detection_yunet_2023mar.onnx — the plain raw URLs
# serve a 403 / the 131-byte LFS pointer; probe record in
# docs/photo-prep-deps-probe-2026-08-04.md §3). Model license: MIT (the
# opencv_zoo YuNet directory's own license — plan §2 row 2 "[P]");
# provenance/sha are also recorded in `model_data/README.md`.
YUNET_MODEL_PATH = Path(__file__).resolve().parent / "model_data" / (
    "face_detection_yunet_2023mar.onnx")
# sha256 of the model as fetched — matches the upstream LFS pointer's oid,
# verified at download AND re-verified at every load (cached per file stat):
# a truncated/corrupted checkout must degrade to the documented no-op, never
# feed garbage weights to the detector.
YUNET_MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

# Detection knobs — YuNet's own published defaults, not tuned here: the
# consumers of a detection (merge-threshold drop, palette weights, the
# preflight size guard) are all conservative-protective, so the detector's
# stock operating point is the right one until a measurement says otherwise.
YUNET_SCORE_THRESHOLD = 0.9
YUNET_NMS_THRESHOLD = 0.3
YUNET_TOP_K = 5000

# sha verification cache, keyed by (path, size, mtime_ns) so an edited file
# re-hashes but a steady one hashes once per process. 232 KB, so even a miss
# costs a millisecond — the cache exists to keep per-job cost at zero, not
# because hashing is expensive.
_MODEL_HASH_OK: dict[tuple[str, int, int], bool] = {}


@dataclass(frozen=True)
class FaceRegion:
    """One YuNet detection, in RASTER PIXELS of the image it was run on
    (the stage-1 prep raster — the same frame `Prep.bg_mask`, SLIC labels
    and every RegionMask live in; divide by `Prep.px_per_mm` for mm)."""
    box_px: tuple[float, float, float, float]      # x, y, w, h
    # YuNet's 5 landmarks, in its own fixed order: right eye, left eye,
    # nose tip, right mouth corner, left mouth corner.
    landmarks_px: tuple[tuple[float, float], ...]
    score: float


def face_detector_unavailable_reason() -> str | None:
    """None when YuNet can run here; otherwise one honest sentence why not.

    Shared by `detect_faces_seam` (to decide) and `pipeline.run_stages` (to
    say so in the PHOTO_FACE_PRIORS_UNAVAILABLE warning) so the two can
    never disagree about why detection was skipped.
    """
    if not hasattr(cv2, "FaceDetectorYN"):
        return "cv2.FaceDetectorYN is not present in this OpenCV build"
    path = YUNET_MODEL_PATH
    if not path.is_file():
        return f"YuNet model file missing at {path}"
    st = path.stat()
    key = (str(path), st.st_size, st.st_mtime_ns)
    if key not in _MODEL_HASH_OK:
        _MODEL_HASH_OK[key] = (
            hashlib.sha256(path.read_bytes()).hexdigest() == YUNET_MODEL_SHA256
        )
    if not _MODEL_HASH_OK[key]:
        return (f"YuNet model file at {path} fails its sha256 integrity "
                "check (corrupted or wrong-version download)")
    return None


def detect_faces_seam(rgb: np.ndarray, cfg: PipelineConfig) -> list[FaceRegion] | None:
    """Photo plan §2 row 2: YuNet 5-landmark face detection on the prep-stage
    raster.

    Returns:
      * `None` — the detector CANNOT run here (no `cv2.FaceDetectorYN`,
        model file missing, or model integrity check failed). The documented
        no-op: callers change nothing, exactly the pre-slice behaviour, and
        `pipeline.run_stages` says so in a PHOTO_FACE_PRIORS_UNAVAILABLE
        warning (reason from `face_detector_unavailable_reason`).
      * `[]` — the detector ran and found no faces.
      * a list of `FaceRegion` — detections in raster px, ordered by
        descending score (ties by x then y) for determinism.

    `cfg` is accepted for signature stability with the other stage-1.5
    entry points (nothing in it is read today — the detector runs at YuNet's
    stock operating point, see the YUNET_* constants).

    Deterministic: same raster, same model file, same detections —
    `cv2.FaceDetectorYN` has no RNG (verified by back-to-back runs on the
    same frame while wiring this).
    """
    del cfg  # reserved — see docstring
    if face_detector_unavailable_reason() is not None:
        return None
    h, w = rgb.shape[:2]
    detector = cv2.FaceDetectorYN.create(
        str(YUNET_MODEL_PATH), "", (int(w), int(h)),
        YUNET_SCORE_THRESHOLD, YUNET_NMS_THRESHOLD, YUNET_TOP_K,
    )
    # YuNet was trained on OpenCV-convention BGR frames; the pipeline's
    # rasters are RGB (stage 1's contract), so convert rather than feeding
    # swapped channels to the net.
    _rc, rows = detector.detect(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    if rows is None:
        return []
    faces = [
        FaceRegion(
            box_px=(float(r[0]), float(r[1]), float(r[2]), float(r[3])),
            landmarks_px=tuple(
                (float(r[4 + 2 * i]), float(r[5 + 2 * i])) for i in range(5)
            ),
            score=float(r[14]),
        )
        for r in np.asarray(rows, np.float64)
    ]
    faces.sort(key=lambda f: (-f.score, f.box_px[0], f.box_px[1]))
    return faces
