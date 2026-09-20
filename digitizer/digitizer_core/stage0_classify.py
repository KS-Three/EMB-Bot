"""Stage 0 -- 4-way input classifier (flat / gradient / photo_subject /
photo_scene). Runs before stage 1 so `pipeline.py` can route the whole
design at once:
`docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md`,
"stage0_classify.py contract".

Deliberately standalone: this module owns its own image decode and its own
throwaway k-means, duplicating a few lines of `stage1_prep._load` and
`stage2_quantize._kmeans`/`_assign` rather than importing across stages, so
it works today with nothing wired into `pipeline.py` yet.

**Signals** (see the plan doc for the contract; thresholds tuned against
every fixture in `testdata/` and `testdata/photo/` -- numbers noted next to
each constant below):

* `unique_color_mass` -- fraction of pixels whose color, after a light
  quantize (throwaway k-means at k=16, Lab space, same construction as
  stage 2's own), differs from the 3x3-neighborhood mode of that
  quantization. Flat art holds together locally after a light quantize
  (near zero); photographic pixels do not (high).
* `gradient_smoothness` -- mean local variance of the Sobel gradient
  magnitude, over the parts of the image that are NOT near a detected edge.
  A smooth ramp's neighbours barely disagree with each other (low, but
  non-zero); flat art has essentially no gradient signal to disagree about
  (near zero); photographic texture disagrees a lot (high). Measured on a
  region with almost no smooth interior left after edge-exclusion (the
  noise stub -- 99% of it is "near an edge" once real edges are dilated),
  which falls back to the raw magnitude variance instead of reporting a
  false zero.
* `alpha_softness` -- fraction of alpha values strictly between 8 and 247,
  when an alpha channel exists (0.0, a neutral reading, when it does not).
  Photo cutouts trend soft; flat logo exports trend binary. Not a primary
  decision axis here -- both real fixtures in this corpus (`enthusiast_logo`,
  `drone_render`) measure low regardless of their target class -- but
  carried in `signals` for the review record and for whoever tunes this
  next against portrait/pet fixtures in step 3+.

**Decision**: a plain two-level thresholded tree, not ML.
`unique_color_mass` gates flat/gradient territory vs. photo territory;
within photo territory `gradient_smoothness` gates scene vs. subject; within
non-photo territory `gradient_smoothness` gates flat vs. gradient. Each gate
reports a confidence (0.5 at the threshold, 1.0 once clear of it by a full
margin); the overall confidence is the weakest gate actually used. Below
`CONFIDENCE_FLOOR`, a would-be non-flat result is discarded for the safe
default (`flat`) plus `CLASSIFICATION_UNCERTAIN` -- this codebase does not
silently guess "photo".

**Real-fixture note** (read before ever touching the thresholds below):
`drone_render.png` is a real AI-rendered drone/thermal logo, not a plain
gradient ramp -- it has a metallic background, glow halos, and a small
inset photographic scene. Its raw Sobel-variance signal (~4.5) actually
reads ROUGHER than the synthetic `photo_scene_stub` (~0.66). What keeps it
out of photo territory is `unique_color_mass` (~0.16): despite looking
busy, a 16-color quantize holds up almost everywhere in it (smooth bands,
not per-pixel texture), which is exactly the "founding complaint" case this
classifier exists to route into the new blend tier instead of flattening it
to mush. `unique_color_mass` is therefore the primary photo/non-photo gate,
not `gradient_smoothness` -- swapping that order would misroute this fixture
to `photo_scene`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .alpha_edge import extend_opaque_colour
from .config import PipelineConfig
from .letterbox import strip_letterbox
from .threads import rgb_to_lab
from .warnings_codes import (
    CLASSIFICATION_SEED_UNSTABLE,
    CLASSIFICATION_UNCERTAIN,
    CLASSIFIED_GRADIENT,
    CLASSIFIED_PHOTO_SCENE,
    CLASSIFIED_PHOTO_SUBJECT,
    warn,
)

_CEILING_COPY = {
    # States the ROUTING, which is all this stage actually knows. Whether a
    # region decomposes is per-region and decided far later, in
    # `stage6_blend.detect_ramp`; the old copy promised decomposition
    # outright and was wrong on every real photograph measured (Kent's owl,
    # 2026-08-12: 25 regions routed, 0 decomposed). Stage 7 raises
    # BLEND_NO_REGIONS_DECOMPOSED when the answer comes back "none".
    CLASSIFIED_GRADIENT: (
        "Classified as a gradient/photo blend, so shapes are routed to the "
        "blend fill tier. Each region is then tested on its own: those that "
        "fit a smooth ramp are split into a few thread shades, and the rest "
        "sew as one flat color."
    ),
    CLASSIFIED_PHOTO_SUBJECT: (
        "Classified as a photo with a subject (portrait/pet/product). "
        "Portrait/pet handling isn't built yet, so results will be low "
        "quality until it ships."
    ),
    CLASSIFIED_PHOTO_SCENE: (
        "Classified as a photographic scene. Scenery handling isn't built "
        "yet, so results will be low quality until it ships."
    ),
    CLASSIFICATION_UNCERTAIN: (
        "Couldn't confidently classify this artwork, so it's being treated "
        "as flat art. If it's actually a photo or gradient, expect lower "
        "quality than usual until you override the class."
    ),
    CLASSIFICATION_SEED_UNSTABLE: (
        "This artwork sits close enough to the line that the classifier's "
        "own random seed decides the answer. The class above is one draw of "
        "several that disagree — check it in review before trusting it."
    ),
}


@dataclass
class Classification:
    class_: str
    confidence: float
    signals: dict
    warnings: list[dict] = field(default_factory=list)


# --- Tunable thresholds ------------------------------------------------------
# See the module docstring's "Real-fixture note" before changing any of
# these -- they were tuned against the real drone-render/enthusiast-logo
# pair, not just the synthetic stubs.

# unique_color_mass: k for the throwaway quantize (plan says "k=16").
UCM_K = 16
UCM_NEIGHBORHOOD = 3  # local-mode window, px

# gradient_smoothness: Sobel is computed on a normalized [0, 1] gray image
# (not 0-255) so a genuinely flat interior reads as an actual zero rather
# than an 8-bit rounding artifact. The local-variance figures are then
# scaled by GRAD_VAR_SCALE purely so the threshold constants below read as
# ordinary numbers instead of needing five leading zeros.
GRAD_VAR_SCALE = 1000.0
GRAD_VAR_WIN = 5                # local-variance window, px
GRAD_VAR_MIN_WINDOW_FRAC = 0.6  # a window needs this much non-edge coverage to count
CANNY_LOW, CANNY_HIGH = 40, 120
CANNY_DILATE_PX = 3              # widen detected edges before excluding them

# unique_color_mass >= this -> photo territory (subject or scene); below ->
# flat/gradient territory. Measured: drone_render 0.159 (non-photo side),
# photo_scene_stub 0.426 (photo side) -- comfortable margin either way.
UCM_PHOTO_MIN = 0.28
UCM_MARGIN = 0.08

# Within non-photo territory, gradient_smoothness >= this -> gradient, else
# flat. Measured: every flat fixture (including the real enthusiast_logo)
# <0.0006; every gradient ramp and the real drone_render >=0.005.
GRAD_VAR_GRADIENT_MIN = 0.0015
GRAD_VAR_GRADIENT_MARGIN = 0.0008

# Within photo territory, gradient_smoothness >= this -> photo_subject
# (fine texture/noise with no smooth interior left after edge-exclusion),
# else -> photo_scene. Measured: photo_scene_stub 0.66, photo_subject_stub
# 184 (its "everything is an edge" fallback) -- both comfortably clear.
GRAD_VAR_SUBJECT_MIN = 8.0
GRAD_VAR_SUBJECT_MARGIN = 3.0

# Below this confidence, a would-be non-flat decision is discarded for the
# safe default instead -- see CLASSIFICATION_UNCERTAIN above.
CONFIDENCE_FLOOR = 0.55


# --- Image loading (standalone -- see module docstring) ---------------------

def _load(image: str | Path | bytes | np.ndarray,
          strip_bars: bool = False) -> tuple[np.ndarray, np.ndarray | None]:
    """-> (rgb uint8, alpha uint8 or None)."""
    if isinstance(image, np.ndarray):
        raw = image
    elif isinstance(image, (bytes, bytearray)):
        raw = cv2.imdecode(np.frombuffer(bytes(image), np.uint8), cv2.IMREAD_UNCHANGED)
    else:
        raw = cv2.imread(str(image), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise ValueError("could not decode image")
    if raw.ndim == 2:
        rgb, alpha = cv2.cvtColor(raw, cv2.COLOR_GRAY2RGB), None
    elif raw.shape[2] == 4:
        rgb, alpha = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2RGB), raw[:, :, 3]
    else:
        rgb, alpha = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB), None
    # Same strip as `stage1_prep._load`, behind the same `cfg.strip_letterbox`
    # flag, and the two MUST stay in step: this module deliberately owns its
    # own decode, so if only one stripped, stage 0 would classify a different
    # picture than stage 1 digitizes.
    if strip_bars:
        return strip_letterbox(rgb, alpha)
    return rgb, alpha


def _fg_mask(rgb: np.ndarray, alpha: np.ndarray | None) -> np.ndarray:
    """Alpha<=127 is background, full stop -- same rule stage 1 uses. No
    alpha channel means every pixel is foreground for this stage's purposes;
    stage 1's own border-flood background detection has not run yet."""
    if alpha is not None:
        return alpha > 127
    return np.ones(rgb.shape[:2], bool)


# --- unique_color_mass -------------------------------------------------------

def _kmeans_lab(lab: np.ndarray, k: int, seed: int, iters: int = 40,
                 fit_max: int = 20_000) -> np.ndarray:
    """Deterministic seeded k-means++ in Lab space -- same construction as
    `stage2_quantize._kmeans` (cv2.kmeans's RNG is not a determinism
    guarantee this repo controls), duplicated locally rather than imported
    because this quantize is throwaway, discarded after the one signal it
    feeds."""
    n = len(lab)
    fit = lab
    if n > fit_max:
        idx = np.linspace(0, n - 1, fit_max).astype(np.int64)
        fit = lab[idx]

    rng = np.random.default_rng(seed)
    centers = np.empty((k, lab.shape[1]), np.float64)
    centers[0] = fit[rng.integers(len(fit))]
    d2 = ((fit - centers[0]) ** 2).sum(1)
    for i in range(1, k):
        total = d2.sum()
        if total <= 0:
            centers[i] = centers[i - 1]
            continue
        centers[i] = fit[rng.choice(len(fit), p=d2 / total)]
        d2 = np.minimum(d2, ((fit - centers[i]) ** 2).sum(1))

    for _ in range(iters):
        assigned = _assign(fit, centers)
        moved = False
        for j in range(k):
            sel = assigned == j
            if not sel.any():
                continue
            new = fit[sel].mean(0)
            if not np.allclose(new, centers[j], atol=1e-6):
                centers[j] = new
                moved = True
        if not moved:
            break
    return centers


def _assign(lab: np.ndarray, centers: np.ndarray, chunk: int = 200_000) -> np.ndarray:
    out = np.empty(len(lab), np.int32)
    for s in range(0, len(lab), chunk):
        block = lab[s:s + chunk]
        d = ((block[:, None, :] - centers[None, :, :]) ** 2).sum(2)
        out[s:s + chunk] = np.argmin(d, axis=1)
    return out


def _unique_color_mass(rgb: np.ndarray, fg: np.ndarray, seed: int) -> float:
    """Fraction of foreground pixels whose quantized color differs from the
    3x3-neighborhood mode of that quantization."""
    h, w = rgb.shape[:2]
    if not fg.any():
        return 0.0
    idx = np.nonzero(fg.reshape(-1))[0]
    px = rgb.reshape(-1, 3)[idx]
    lab = rgb_to_lab(px.astype(np.float64))
    k = max(1, min(UCM_K, len(np.unique(px, axis=0))))
    centers = _kmeans_lab(lab, k, seed)
    assigned = _assign(lab, centers)

    labels = np.full(h * w, -1, np.int32)
    labels[idx] = assigned
    labels = labels.reshape(h, w)

    win = (UCM_NEIGHBORHOOD, UCM_NEIGHBORHOOD)
    counts = np.empty((k, h, w), np.float32)
    for j in range(k):
        counts[j] = cv2.boxFilter((labels == j).astype(np.float32), -1, win, normalize=False)
    mode = np.argmax(counts, axis=0)

    diff = (mode != labels) & fg
    return float(diff.sum()) / float(fg.sum())


# --- gradient_smoothness ------------------------------------------------------

def _gradient_smoothness(rgb: np.ndarray, fg: np.ndarray) -> float:
    """Mean local variance of the Sobel gradient magnitude, over the parts
    of the foreground that are NOT near a detected edge -- a hard color
    boundary would otherwise swamp either a "flat" or a "smooth ramp"
    reading. See the module docstring's fallback note for what happens when
    edge-exclusion leaves nothing to measure."""
    if not fg.any():
        return 0.0

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    mag = cv2.magnitude(gx, gy)

    edges = cv2.Canny((gray * 255).astype(np.uint8), CANNY_LOW, CANNY_HIGH)
    edges = cv2.dilate(edges, np.ones((CANNY_DILATE_PX, CANNY_DILATE_PX), np.uint8))
    non_edge = (fg & (edges == 0)).astype(np.float32)

    win = (GRAD_VAR_WIN, GRAD_VAR_WIN)
    count = cv2.boxFilter(non_edge, -1, win, normalize=False)
    safe_count = np.maximum(count, 1.0)
    mean = cv2.boxFilter(mag * non_edge, -1, win, normalize=False) / safe_count
    mean_sq = cv2.boxFilter((mag * mag) * non_edge, -1, win, normalize=False) / safe_count
    local_var = mean_sq - mean * mean

    min_count = GRAD_VAR_MIN_WINDOW_FRAC * GRAD_VAR_WIN * GRAD_VAR_WIN
    valid = (non_edge > 0) & (count >= min_count)
    if valid.any():
        return float(local_var[valid].mean()) * GRAD_VAR_SCALE

    # No window has a real "smooth interior" left to measure -- everything
    # near this pixel reads as an edge, which is itself the signal (on the
    # noise stub, 37% of pixels are direct Canny edges and 99% are within
    # one dilation of one). Fall back to the raw magnitude variance over the
    # whole foreground rather than reporting a false zero.
    return float(mag[fg].var()) * GRAD_VAR_SCALE


# --- alpha_softness ------------------------------------------------------------

def _alpha_softness(alpha: np.ndarray | None) -> float:
    """Fraction of alpha values strictly between 8 and 247. None (no alpha
    channel) reports as 0.0 -- a neutral reading, since there is nothing
    here to be soft or hard."""
    if alpha is None:
        return 0.0
    return float(((alpha > 8) & (alpha < 247)).mean())


# --- decision ------------------------------------------------------------------

def _gate_confidence(value: float, threshold: float, margin: float) -> float:
    """0.5 exactly at the threshold (a coin flip), rising to 1.0 once
    `value` clears the threshold by a full `margin` in either direction."""
    if margin <= 0:
        return 1.0
    return float(min(1.0, 0.5 + 0.5 * abs(value - threshold) / margin))


def _seed_sweep_signals(rgb: np.ndarray, fg: np.ndarray, cfg: PipelineConfig,
                        ucm: float) -> tuple[dict, list[dict]]:
    """Report what `unique_color_mass` does across OTHER k-means seeds.

    ## What this fixes, and what it deliberately does NOT

    `unique_color_mass` is a randomised statistic — `_kmeans_lab` seeds
    k-means++ from `cfg.seed` — and `_gate_confidence` measures how far ONE
    draw sits from the gate. So the printed confidence says "far from the
    line", never "reproducible", and the two are not the same claim. On
    `logo_script_tires.png` they come apart completely: the reading is
    0.1962-0.3608 across seeds 0-11, **5 of 12 cross `UCM_PHOTO_MIN` and the
    default seed 0 is the MAXIMUM of the twelve**, yet the verdict prints
    `photo_scene` at confidence 1.0000 (measured 2026-09-14; DOCTRINE
    "A signal's number is not a claim about the artwork until you know WHICH
    PIXELS made it" recorded the same spread on 2026-09-11).

    **This function only ever ADDS signals and a warning. It does not touch
    `confidence`, and must not.** Confidence is load-bearing for routing —
    `classify` demotes a non-flat verdict to `flat` below `CONFIDENCE_FLOOR`
    — so folding seed disagreement into it would move artwork between lanes,
    which is stage-0 recalibration and refused by ROADMAP hard gate 2
    without real tonal artwork. The demotion is one line away on purpose:
    Kent's call 2026-09-14 was reporting only.

    ## Why it is OFF by default

    A sweep costs one full `_unique_color_mass` per extra seed, and that is
    not cheap: 9.36 s per seed on `logo_script_tires.png`, 6.03 s on
    `summit_badge.png`, 5.08 s on `logo_gaulke_roofing.png` (measured
    2026-09-14). Twelve seeds is 112 s on the first of those — an order of
    magnitude past the whole rest of stage 0. `cfg.stage0_seed_sweep = 0`
    (the default) takes exactly the pre-existing single-draw path and adds
    nothing but the `unique_color_mass_seed` field, so every existing
    verdict, warning list and debug dump is unchanged.

    Set it to N > 1 to pay for the answer when someone is asking the
    question — a review screen, a corpus probe, or a session deciding
    whether a surprising verdict is real. `tools/stage0_signal_origin.py`
    remains the offline instrument with the per-zone attribution; this is
    the same reading from inside the pipeline, where the verdict is made.
    """
    n = int(getattr(cfg, "stage0_seed_sweep", 0) or 0)
    if n <= 1:
        return {}, []

    seeds = [s for s in range(cfg.seed, cfg.seed + n)]
    values = [ucm if s == cfg.seed else _unique_color_mass(rgb, fg, s)
              for s in seeds]
    crossings = sum(1 for v in values if v >= UCM_PHOTO_MIN)

    out = {
        "unique_color_mass_seed_min": float(min(values)),
        "unique_color_mass_seed_max": float(max(values)),
        "unique_color_mass_seed_n": len(values),
        # How many of the swept seeds land on the PHOTO side of the gate.
        # 0 or n means every draw agrees; anything between is the verdict
        # being decided by the RNG rather than by the artwork.
        "unique_color_mass_gate_crossings": crossings,
    }
    warnings: list[dict] = []
    if 0 < crossings < len(values):
        warnings.append(warn(
            CLASSIFICATION_SEED_UNSTABLE,
            _CEILING_COPY[CLASSIFICATION_SEED_UNSTABLE],
            seeds=len(values), crossings=crossings,
            value_min=round(float(min(values)), 4),
            value_max=round(float(max(values)), 4),
            gate=UCM_PHOTO_MIN, seed_used=cfg.seed,
        ))
    return out, warnings


def _write_debug(cfg: PipelineConfig, result: Classification) -> None:
    if not cfg.debug_dir:
        return
    dbg = Path(cfg.debug_dir)
    dbg.mkdir(parents=True, exist_ok=True)
    lines = [f"class: {result.class_}", f"confidence: {result.confidence:.4f}", "signals:"]
    for k, v in result.signals.items():
        lines.append(f"  {k}: {v:.6f}" if isinstance(v, float) else f"  {k}: {v!r}")
    if result.warnings:
        lines.append("warnings:")
        for w in result.warnings:
            lines.append(f"  {w['code']}: {w['message']}")
    (dbg / "stage0_classification.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# The only four classes this function can return, and therefore the only four
# `forced_class` values that mean anything. Every downstream consumer tests
# MEMBERSHIP against a subset of these (`pipeline.py`'s
# `class_ in ("photo_subject", "photo_scene")`, `== "gradient"`,
# `stage7_sequence.PHOTO_CLASSES` and its stage6_satin mirror
# `_PHOTO_CLASSES`), so an unrecognized value matches none of them and
# silently takes the flat path — a mis-measurement that looks like a
# clean run. Hence the check in `classify`.
CLASSES = ("flat", "gradient", "photo_subject", "photo_scene")


def classify(image: str | Path | bytes | np.ndarray, cfg: PipelineConfig,
             forced_class: str | None = None) -> Classification:
    """4-way input classification. `forced_class` (the escape hatch cfg's
    real `forced_class` field will thread through once `config.py` is
    wired) skips signal computation entirely and returns that class at
    confidence 1.0.

    Raises `ValueError` on a `forced_class` outside `CLASSES`. It used to
    accept any string and hand it back at confidence 1.0 with no warning,
    which meant a typo — `photo` for `photo_subject`, say — routed the whole
    run down the flat lane while reporting complete success. Callers taking
    the value from outside the process validate FIRST so the user sees their
    own error: `digitizer_service.app._validate_config_dict` returns 400, and
    `tools/pro_parity/prep_all.py` exits with the valid list.
    """
    if forced_class is not None:
        if forced_class not in CLASSES:
            raise ValueError(
                f"forced_class {forced_class!r} is not one of {', '.join(CLASSES)}"
            )
        result = Classification(class_=forced_class, confidence=1.0, signals={}, warnings=[])
        _write_debug(cfg, result)
        return result

    rgb, alpha = _load(image, cfg.strip_letterbox)
    # In step with stage 1 (`cfg.alpha_edge_extend`): the signals below mask
    # to `fg`, but `_gradient_smoothness`'s kernel sits on the edge and reads
    # what is under the alpha whatever the mask says — Becker with black
    # underneath classified "gradient" from a raster stage 1 had already
    # extended (measured 2026-09-20).
    if cfg.alpha_edge_extend and alpha is not None and (alpha < 255).any():
        rgb = extend_opaque_colour(rgb, alpha, cfg.alpha_edge_extend_px)
    fg = _fg_mask(rgb, alpha)

    ucm = _unique_color_mass(rgb, fg, cfg.seed)
    grad_var = _gradient_smoothness(rgb, fg)
    alpha_soft = _alpha_softness(alpha)
    signals = {
        "unique_color_mass": ucm,
        "gradient_smoothness": grad_var,
        "alpha_softness": alpha_soft,
        # WHICH draw produced `unique_color_mass` above. Recorded always,
        # because the statistic is randomised and the number alone does not
        # say so -- see `_seed_sweep_signals`.
        "unique_color_mass_seed": cfg.seed,
    }
    sweep_signals, sweep_warnings = _seed_sweep_signals(rgb, fg, cfg, ucm)
    signals.update(sweep_signals)

    is_photo = ucm >= UCM_PHOTO_MIN
    photo_gate_conf = _gate_confidence(ucm, UCM_PHOTO_MIN, UCM_MARGIN)

    if is_photo:
        is_subject = grad_var >= GRAD_VAR_SUBJECT_MIN
        sub_gate_conf = _gate_confidence(grad_var, GRAD_VAR_SUBJECT_MIN, GRAD_VAR_SUBJECT_MARGIN)
        confidence = min(photo_gate_conf, sub_gate_conf)
        class_ = "photo_subject" if is_subject else "photo_scene"
    else:
        is_gradient = grad_var >= GRAD_VAR_GRADIENT_MIN
        grad_gate_conf = _gate_confidence(grad_var, GRAD_VAR_GRADIENT_MIN, GRAD_VAR_GRADIENT_MARGIN)
        confidence = min(photo_gate_conf, grad_gate_conf)
        class_ = "gradient" if is_gradient else "flat"

    warnings: list[dict] = list(sweep_warnings)
    if class_ != "flat" and confidence < CONFIDENCE_FLOOR:
        class_ = "flat"
        warnings.append(warn(CLASSIFICATION_UNCERTAIN, _CEILING_COPY[CLASSIFICATION_UNCERTAIN]))

    if class_ == "gradient":
        warnings.append(warn(CLASSIFIED_GRADIENT, _CEILING_COPY[CLASSIFIED_GRADIENT]))
    elif class_ == "photo_subject":
        warnings.append(warn(CLASSIFIED_PHOTO_SUBJECT, _CEILING_COPY[CLASSIFIED_PHOTO_SUBJECT]))
    elif class_ == "photo_scene":
        warnings.append(warn(CLASSIFIED_PHOTO_SCENE, _CEILING_COPY[CLASSIFIED_PHOTO_SCENE]))

    result = Classification(class_=class_, confidence=confidence, signals=signals, warnings=warnings)
    _write_debug(cfg, result)
    return result
