"""Stage 1 — load, background masking, denoise, resolution check.

Conventions pinned here and relied on downstream:
  * Images are held as **RGB** uint8 (cv2 loads BGR; converted on the way in).
  * `bg_mask` True means "background — never stitched".
  * `px_per_mm` derives from the ARTWORK bbox width (not the image width)
    against cfg.target_width_mm, because the user sizes the design, not the
    canvas padding around it.

Background rules (blueprint v2.1):
  * Alpha channel present -> transparent is background, full stop.
  * Otherwise a border flood: pixels close to the dominant border color AND
    connected to the border. Restricting to border-connected components is
    what stops an interior white shape from being eaten...
  * ...but an ENCLOSED bg-colored area (a donut hole) is not automatically
    background either — it joins `fg` like any other pixel and is reported
    as BACKGROUND_ENCLOSED, but the pixels themselves become a real `Region`
    downstream (see `Prep.enclosed_mask` and `stage4_vectorize.
    tag_enclosed_background`), tagged `enclosed_background` and unstitched
    by DEFAULT rather than deleted outright — review can toggle it back on.
  * Uncertainty guard: if border-connected background intrudes deeper than
    cfg.bg_margin_mm inside the artwork's convex hull, the flood probably ate
    real art (white text touching a white border) -> BACKGROUND_UNCERTAIN.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from .config import PipelineConfig
from .threads import rgb_to_lab
from .warnings_codes import (
    BACKGROUND_ENCLOSED,
    BACKGROUND_UNCERTAIN,
    INPUT_LOW_RESOLUTION,
    warn,
)


@dataclass
class Prep:
    rgb: np.ndarray          # (H, W, 3) uint8, RGB
    bg_mask: np.ndarray      # (H, W) bool, True = background
    px_per_mm: float
    art_bbox: tuple[int, int, int, int]  # x0, y0, x1, y1 (px, x1/y1 exclusive)
    # px_per_mm as the INPUT delivered it, before the resolution-floor
    # Lanczos upscale below. The upscale changes `px_per_mm` because every
    # downstream px<->mm mapping must use the raster as it now is, but it
    # manufactures pixels, not information — so any question about whether
    # the SOURCE resolves detail at the target size (preflight's photo
    # resolution guard) must read this, never `px_per_mm`.
    input_px_per_mm: float = 0.0
    # True when the background came from the alpha channel rather than a
    # border color flood. An alpha cutout's background is the GARMENT, whose
    # color this pipeline cannot know (the RGB under transparency is whatever
    # the exporter left there — see bg_edge_rgb's caveat below), so any check
    # comparing artwork against "the background color" must decline when this
    # is set.
    bg_from_alpha: bool = False
    bg_outline_px: np.ndarray | None = None  # (N, 2) largest border-bg contour
    # Mean color of the background pixels hugging the artwork edge. Stage 2
    # needs it as a virtual endpoint when testing whether a cluster is an
    # anti-alias blend: the outermost halo blends art toward THIS color, and
    # without it those halos survive as phantom thread layers.
    bg_edge_rgb: np.ndarray | None = None
    # (H, W) bool, True where a pixel matched the background color/alpha test
    # but is NOT connected to the true canvas border (a donut hole, or white
    # icon linework enclosed by a colored logo). These pixels are part of
    # `fg` — not excluded — so later stages can find them without re-deriving
    # the border-flood: `stage4_vectorize.tag_enclosed_background` uses this
    # to tag the Region(s) they end up in. None when no such pixels exist,
    # mirroring `bg_outline_px`/`bg_edge_rgb` above.
    enclosed_mask: np.ndarray | None = None
    warnings: list[dict] = field(default_factory=list)


def _load(image: str | Path | bytes | np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
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
        return cv2.cvtColor(raw, cv2.COLOR_GRAY2RGB), None
    if raw.shape[2] == 4:
        rgb = cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2RGB)
        return rgb, raw[:, :, 3]
    return cv2.cvtColor(raw, cv2.COLOR_BGR2RGB), None


def _border_ring(shape: tuple[int, int], width: int = 2) -> np.ndarray:
    h, w = shape
    m = np.zeros((h, w), bool)
    m[:width, :] = True
    m[-width:, :] = True
    m[:, :width] = True
    m[:, -width:] = True
    return m


def _dominant_border_color(rgb: np.ndarray) -> np.ndarray:
    """Modal border color, found by coarse binning so anti-aliased border
    pixels vote together instead of splitting into unique values."""
    ring = _border_ring(rgb.shape[:2])
    px = rgb[ring].reshape(-1, 3).astype(np.int32)
    binned = px // 16
    keys = binned[:, 0] * 65536 + binned[:, 1] * 256 + binned[:, 2]
    vals, counts = np.unique(keys, return_counts=True)
    win = vals[int(np.argmax(counts))]
    sel = keys == win
    return px[sel].mean(axis=0)


def _color_close_mask(rgb: np.ndarray, color: np.ndarray, tol: float) -> np.ndarray:
    """True where the pixel is within `tol` CIE76 of `color` (both RGB 0-255)."""
    h, w = rgb.shape[:2]
    lab = rgb_to_lab(rgb.reshape(-1, 3)).reshape(h, w, 3)
    ref = rgb_to_lab(np.asarray(color, dtype=np.float64).reshape(1, 3))[0]
    d = lab - ref.reshape(1, 1, 3)
    return np.sqrt(np.einsum("ijk,ijk->ij", d, d)) <= tol


def _border_connected(mask: np.ndarray) -> np.ndarray:
    """Subset of `mask` whose components touch the image border."""
    n, labels = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    if n <= 1:
        return np.zeros_like(mask)
    ring = _border_ring(mask.shape[:2], width=1)
    touching = set(np.unique(labels[ring & mask])) - {0}
    if not touching:
        return np.zeros_like(mask)
    return np.isin(labels, list(touching))


def prep(image: str | Path | bytes | np.ndarray, cfg: PipelineConfig) -> Prep:
    rgb, alpha = _load(image)
    warnings: list[dict] = []

    if cfg.denoise:
        # Edge-preserving; on flat art this is nearly a no-op, which is the
        # point — it cleans JPEG mosquito noise without softening boundaries.
        rgb = cv2.bilateralFilter(rgb, d=5, sigmaColor=30, sigmaSpace=5)

    h, w = rgb.shape[:2]
    bg_outline_px = None

    # A FULLY-opaque alpha channel carries zero background information and
    # must not be treated as ground truth that "nothing is background" —
    # measured live 2026-08-04: Studio's DigitizePanel re-encodes every
    # upload through a canvas, which manufactures an opaque alpha channel
    # onto RGB art. Routed through the alpha branch, that killed background
    # detection outright on the enclosed-region repro fixture (bg detected:
    # False — the white canvas itself would SEW) and silently disabled
    # BACKGROUND_ENCLOSED for every panel upload. An image whose alpha never
    # dips below the threshold behaves exactly like its RGB twin instead.
    # Every committed alpha fixture has real transparency (checked:
    # logo_alpha / drone_render / enthusiast_logo all carry 300k+ pixels
    # under 128), so this changes nothing for genuine cutouts.
    if alpha is not None and not (alpha < 128).any():
        alpha = None

    bg_from_alpha = alpha is not None
    if alpha is not None:
        bg = alpha < 128
        border_bg = _border_connected(bg)
        # Was `bg & ~border_bg`, then folded back into `bg` below — an
        # enclosed transparent hole was therefore indistinguishable from
        # ordinary background and never became stitchable. Now `enclosed`
        # stays OUT of `bg`, so it joins `fg` a few lines down.
        enclosed = bg & ~border_bg
        bg = border_bg
    else:
        bg_color = _dominant_border_color(rgb)
        close = _color_close_mask(rgb, bg_color, cfg.bg_tolerance_lab)
        border_bg = _border_connected(close)
        enclosed = close & ~border_bg
        # Was `border_bg | enclosed` — the same fold described above, for the
        # far more common no-alpha path (BACKGROUND_ENCLOSED's usual trigger:
        # bg-colored icon linework enclosed by the surrounding artwork).
        bg = border_bg

    # Same guard as before the fold-in existed (`not (border_bg.any() or
    # enclosed.any())`, which is what `not bg.any()` used to mean when `bg`
    # still included `enclosed`): only a total detection miss resets
    # everything to empty. A design whose ONLY background match is fully
    # enclosed (no border-connected background at all) is real and must
    # survive this guard now that `enclosed` carries real, taggable pixels.
    if not (border_bg.any() or enclosed.any()):
        bg = np.zeros((h, w), bool)
        border_bg = bg
        enclosed = bg

    fg = ~bg
    if not fg.any():
        raise ValueError("no foreground pixels — the whole image reads as background")

    ys, xs = np.nonzero(fg)
    art_bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
    art_w_px = max(1, art_bbox[2] - art_bbox[0])
    px_per_mm = art_w_px / float(cfg.target_width_mm)
    input_px_per_mm = px_per_mm   # recorded before the upscale below

    # --- uncertainty guard --------------------------------------------------
    # PER-COMPONENT hulls, not one hull over all the artwork: a logo is
    # normally several separated elements, and a global hull spans the gaps
    # between them, so ordinary background between shapes would fire the
    # warning on every clean multi-element logo (measured: it did).
    # The question this asks is narrower and right: did the flood push deep
    # inside a SINGLE element's own footprint — the signature of a white
    # glyph touching a white border being swallowed.
    # Enclosed background is excluded (a donut hole belongs inside its hull).
    # KNOWN false-positive class, accepted because this is a warning and not
    # a behavior change: one deeply concave element (a big "C" or "U") has
    # legitimate background inside its own hull.
    if border_bg.any():
        margin_px = int(round(cfg.bg_margin_mm * px_per_mm))
        min_intrusion_px = int(round((cfg.bg_intrusion_min_mm * px_per_mm) ** 2))
        n_fg, fg_cc = cv2.connectedComponents(fg.astype(np.uint8), connectivity=8)
        kernel = (
            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (margin_px * 2 + 1,) * 2)
            if margin_px > 0
            else None
        )
        intruded = 0
        for c in range(1, n_fg):
            comp = fg_cc == c
            cys, cxs = np.nonzero(comp)
            if len(cxs) < 3 or len(cxs) * len(cys) == 0:
                continue
            if comp.sum() < min_intrusion_px:
                continue  # too small to reason about
            hull_pts = cv2.convexHull(np.column_stack([cxs, cys]).astype(np.int32))
            hull = np.zeros((h, w), np.uint8)
            cv2.fillConvexPoly(hull, hull_pts, 1)
            inner = cv2.erode(hull, kernel) if kernel is not None else hull
            intruded += int(np.count_nonzero(border_bg & (inner > 0)))
        if intruded >= min_intrusion_px:
            warnings.append(
                warn(
                    BACKGROUND_UNCERTAIN,
                    "Background detection reached deep inside a shape — confirm in "
                    "review that nothing was removed by mistake.",
                    intruded_px=intruded,
                )
            )
        cnts, _ = cv2.findContours(
            border_bg.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        if cnts:
            biggest = max(cnts, key=cv2.contourArea)
            bg_outline_px = biggest.reshape(-1, 2)

    if enclosed.any():
        n_enc, _ = cv2.connectedComponents(enclosed.astype(np.uint8), connectivity=8)
        warnings.append(
            warn(
                BACKGROUND_ENCLOSED,
                "Enclosed background-colored areas are treated as holes and left "
                "unstitched — toggle them on in review if they should sew.",
                count=max(0, n_enc - 1),
            )
        )

    # --- resolution floor ---------------------------------------------------
    if px_per_mm < cfg.min_px_per_mm:
        want = min(cfg.upscale_cap, cfg.min_px_per_mm / px_per_mm)
        new_size = (int(round(w * want)), int(round(h * want)))
        rgb = cv2.resize(rgb, new_size, interpolation=cv2.INTER_LANCZOS4)
        bg = (
            cv2.resize(bg.astype(np.uint8), new_size, interpolation=cv2.INTER_NEAREST) > 0
        )
        if enclosed.any():
            enclosed = (
                cv2.resize(enclosed.astype(np.uint8), new_size,
                           interpolation=cv2.INTER_NEAREST) > 0
            )
        px_per_mm *= want
        art_bbox = tuple(int(round(v * want)) for v in art_bbox)  # type: ignore[assignment]
        if bg_outline_px is not None:
            bg_outline_px = (bg_outline_px.astype(np.float64) * want).astype(np.int32)
        if px_per_mm < cfg.min_px_per_mm:
            warnings.append(
                warn(
                    INPUT_LOW_RESOLUTION,
                    f"Image resolution is low for a {cfg.target_width_mm:.0f} mm design "
                    "— fine detail may be lost.",
                    px_per_mm=round(px_per_mm, 2),
                )
            )

    # Color the artwork's outer anti-alias band blends toward (see Prep).
    # Measured from the background side of the boundary, so it is correct for
    # both an opaque backdrop and an alpha cutout (where it picks up whatever
    # RGB sits under the transparency).
    bg_edge_rgb = None
    if bg.any():
        near_fg = (
            cv2.dilate((~bg).astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
        ) & bg
        if near_fg.any():
            bg_edge_rgb = rgb[near_fg].reshape(-1, 3).mean(axis=0)

    return Prep(
        rgb=rgb,
        bg_mask=bg,
        px_per_mm=px_per_mm,
        art_bbox=art_bbox,  # type: ignore[arg-type]
        input_px_per_mm=input_px_per_mm,
        bg_from_alpha=bg_from_alpha,
        bg_outline_px=bg_outline_px,
        bg_edge_rgb=bg_edge_rgb,
        enclosed_mask=enclosed if enclosed.any() else None,
        warnings=warnings,
    )
