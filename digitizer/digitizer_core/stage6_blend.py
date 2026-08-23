"""Stage 6 — the gradient blend fill tier.

A sibling of `stage6_fill.py` (tatami), `stage6_satin.py` and
`stage6_border.py`, invoked only when the global classification is
`gradient` (`docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md`,
"stage6_blend.py contract"). Returns `(runs, report)` — the same contract
every sibling tier function uses (`stitch_shape`/`satin_shape`/`contour_fill`
all return this pair), so `stage7_sequence.stitch_one` can drop this tier
into its existing ladder without a special case for the return shape. Three
things happen here, in order:

1. **Ramp detection.** Fit the region's pre-quantize pixels against a linear
   and a radial gradient model. A real ramp leaves a small, STRUCTURED
   residual (low local variance, a systematic direction) — noise or
   photographic texture leaves a large, unstructured one. Whichever model
   fits best wins; if neither fits well, or the local variance reads as
   speckle, this falls back to ordinary tatami (`stage6_fill.stitch_shape`)
   exactly as any other fill-classified shape would sew — a real fallback
   path, not a placeholder.
2. **Shade decomposition.** 3-5 chart shades, picked by averaging the Lab
   color of the pixels nearest each shade's canonical position along the
   ramp and snapping each average to the nearest thread (`threads.py`'s
   existing CIEDE2000 lookup — no new color model here beyond the
   barycentric split itself).
3. **Emission.** N interleaved tatami layers, ONE shared fill angle per
   region — `SourcePixels.design_row_angle_deg` when the whole design fit a
   single linear ramp (`detect_design_ramp_angle`, so every fragment of a
   fragmented gradient sews the same direction instead of each picking its
   own — this wins over a region's OWN ramp model regardless of that
   model's kind, widened 2026-08-04, see `blend_fill`'s own comment), else
   `stage6_fill.principal_angle_deg` of this region alone. Each layer is
   restricted to a band of the ramp centered on its own shade
   and sewn at `stage6_fill.stitch_shape`'s ordinary row spacing of
   `FILL_ROW_MM * N`. Adjacent bands overlap by a small margin so the
   shades blend at the seam instead of leaving a hard edge, which is also
   what pushes total coverage over 1.0 (see `_BAND_OVERLAP_T`).

Coordinates are the same convention as everywhere past stage 4: millimetres,
origin at the artwork bbox center, y-axis down.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point, Polygon
from skimage.color import deltaE_ciede2000

from . import debugviz, machine
from .regions import Region
from .stage1_prep import Prep
from .stage6_fill import principal_angle_deg, stitch_shape
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

# --- Ramp detection ----------------------------------------------------------

# Fraction of variance the winning model must explain before this is called a
# ramp at all. Tuned against the committed synthetic ramps (which fit at
# 0.9+) and a flat-noise fixture (which fits at ~0, being unstructured).
RAMP_R2_MIN = 0.5
# Local (pixel-to-pixel) variance vs. global variance, within the region. A
# smooth ramp's local variance is a sliver of its global spread; speckle's
# local variance approaches the global figure because neighbours disagree as
# often as far-apart pixels do.
RAMP_SPECKLE_MAX = 0.35
# Deterministic subsample: fitting the whole region is not needed for a
# low-order model, and a fixed count + seed keeps this stage as free of RNG
# surprises as stage0_classify's own signals are meant to be.
RAMP_MAX_SAMPLES = 2500
RAMP_SAMPLE_SEED = 0

# --- Shade decomposition ------------------------------------------------------

SHADE_COUNT_MIN = 3
SHADE_COUNT_MAX = 5
# Target perceptual step (CIEDE2000) per shade band. The extremes' total
# distance divided by this, clamped to [SHADE_COUNT_MIN, SHADE_COUNT_MAX],
# is how many shades a ramp gets — a subtle ramp costs fewer shades than a
# saturated light-to-dark sweep.
SHADE_STEP_DELTAE = 9.0

# --- Emission ------------------------------------------------------------------

# How far an internal band boundary reaches into its neighbour, as a fraction
# of the [0, 1] ramp position. Two effects fall out of one number: adjacent
# shades overlap enough to blend at the seam instead of leaving a hard edge,
# and total emitted coverage rises above 1.0 by `2 * this * (N - 1)` — 0.08 at
# N=3, 0.16 at N=5, comfortably inside the [1.0, 1.2] band the plan specifies.
_BAND_OVERLAP_T = 0.02


@dataclass
class SourcePixels:
    """A region's pre-quantize raster, in the same mm<->px mapping stage 4
    uses (see `debugviz.stage4`'s `to_px`): `mm = (px - origin_px) /
    px_per_mm`, y-down in both spaces. `rgb` is (H, W, 3) uint8.
    """

    rgb: np.ndarray
    px_per_mm: float
    origin_px: tuple[float, float]
    # Set by `pipeline.run_stages` once per design, from
    # `detect_design_ramp_angle` against the WHOLE foreground — not one
    # region. `blend_fill` uses this as the shared fill-row angle instead of
    # each region's own `stage6_fill.principal_angle_deg` when set: the fix
    # for the 2026-08-03 angle-fragmentation defect, where `gradient`-class
    # art still segments via plain k-means before blend treatment (23 regions
    # on the repro fixture), each fragment picking its own, independently
    # computed angle — a patchwork of differently-angled wedges instead of
    # one flowing sweep. None for every class this stage never runs on, and
    # for a `gradient` design whose own whole-design fit declined (no single
    # linear direction found) — same per-region angle as always in that case.
    design_row_angle_deg: float | None = None
    # True only when stage 0 classified the DESIGN "gradient" — set by
    # `pipeline.run_stages`, read by stage 7 to decide whether auto-tier
    # fill shapes route through `blend_fill`. Exists because "source pixels
    # are present" stopped implying "gradient class" the moment tiers that
    # read the raster WITHOUT wanting blend routing arrived (the detail
    # layer is the first): those opt-ins carry pixels for their own use and
    # must leave every fill shape on the exact tatami path it always took.
    gradient_class: bool = False

    def to_px(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        return (x_mm * self.px_per_mm + self.origin_px[0],
                y_mm * self.px_per_mm + self.origin_px[1])

    def to_mm(self, x_px: float, y_px: float) -> tuple[float, float]:
        return ((x_px - self.origin_px[0]) / self.px_per_mm,
                (y_px - self.origin_px[1]) / self.px_per_mm)


def darkness_sampler(sp: SourcePixels, blur_mm: float):
    """-> darkness(x_mm, y_mm) in [0, 1], bilinear over a `blur_mm`-scale
    Gaussian blur of the source luminance. Deterministic — no RNG.

    Shared by the mono tonal tiers (`stage6_scanline`, `stage6_meander`): both
    render tone by reading local darkness at grain scale, and if each carried
    its own copy the two tiers would eventually read the same pixel as two
    different darknesses — a drift class this module, as the home of
    `SourcePixels`, exists to prevent. The blur radius stays each tier's own
    knob; the sampling semantics (grain-scale blur so one dark pixel of JPEG
    noise cannot flip a stitch decision, bilinear between pixels, clamped at
    the raster edge) are the shared contract.
    """
    gray = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0
    sigma = max(0.5, blur_mm * sp.px_per_mm)
    blur = cv2.GaussianBlur(gray, (0, 0), sigma)
    h, w = blur.shape

    def darkness(x_mm: float, y_mm: float) -> float:
        px, py = sp.to_px(x_mm, y_mm)
        fx = min(max(px, 0.0), w - 1.0)
        fy = min(max(py, 0.0), h - 1.0)
        x0, y0 = int(fx), int(fy)
        x1, y1 = min(x0 + 1, w - 1), min(y0 + 1, h - 1)
        tx, ty = fx - x0, fy - y0
        v = (blur[y0, x0] * (1 - tx) * (1 - ty) + blur[y0, x1] * tx * (1 - ty)
             + blur[y1, x0] * (1 - tx) * ty + blur[y1, x1] * tx * ty)
        return 1.0 - float(v)

    return darkness


@dataclass
class RampModel:
    """A fitted gradient. `t(x, y)` maps an mm point to its normalized
    position along the ramp, 0 at the light/near end, 1 at the dark/far end,
    clamped in between."""

    kind: str  # "linear" | "radial"
    direction: tuple[float, float] | None  # linear: unit vector
    center: tuple[float, float] | None     # radial: mm center
    lo: float
    hi: float
    r2: float

    def raw(self, x: float, y: float) -> float:
        if self.kind == "linear":
            ux, uy = self.direction
            return x * ux + y * uy
        cx, cy = self.center
        return math.hypot(x - cx, y - cy)

    def t(self, x: float, y: float) -> float:
        if self.hi <= self.lo:
            return 0.0
        s = self.raw(x, y)
        return min(1.0, max(0.0, (s - self.lo) / (self.hi - self.lo)))


def _crop_and_mask(poly: Polygon, sp: SourcePixels) -> tuple[np.ndarray, np.ndarray, int, int]:
    """-> (rgb crop, bool mask, x0_px, y0_px). Empty mask if nothing to sample."""
    minx, miny, maxx, maxy = poly.bounds
    x0, y0 = sp.to_px(minx, miny)
    x1, y1 = sp.to_px(maxx, maxy)
    x0i, x1i = int(math.floor(min(x0, x1))), int(math.ceil(max(x0, x1)))
    y0i, y1i = int(math.floor(min(y0, y1))), int(math.ceil(max(y0, y1)))
    h, w = sp.rgb.shape[:2]
    x0i, y0i = max(0, x0i), max(0, y0i)
    x1i, y1i = min(w, x1i), min(h, y1i)
    if x1i <= x0i or y1i <= y0i:
        return np.zeros((0, 0, 3), np.uint8), np.zeros((0, 0), bool), x0i, y0i

    crop = sp.rgb[y0i:y1i, x0i:x1i]
    mask = np.zeros(crop.shape[:2], np.uint8)

    def ring_px(coords) -> np.ndarray:
        pts = []
        for x, y in coords:
            px, py = sp.to_px(x, y)
            pts.append((px - x0i, py - y0i))
        return np.array(pts, np.int32)

    cv2.fillPoly(mask, [ring_px(poly.exterior.coords)], 255)
    for hole in poly.interiors:
        cv2.fillPoly(mask, [ring_px(hole.coords)], 0)
    return crop, mask.astype(bool), x0i, y0i


def _sample_pixels(poly: Polygon, sp: SourcePixels, max_samples: int = RAMP_MAX_SAMPLES,
                   seed: int = RAMP_SAMPLE_SEED
                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """-> (mm_x, mm_y, rgb (K,3) uint8, mask, crop) sampled inside the polygon.

    `mask`/`crop` are returned too so callers needing the whole raster (the
    speckle test) do not redo the fill/crop pass.
    """
    crop, mask, x0, y0 = _crop_and_mask(poly, sp)
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        empty = np.zeros(0, np.float64)
        return empty, empty, np.zeros((0, 3), np.uint8), mask, crop
    if len(xs) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(xs), size=max_samples, replace=False)
        xs, ys = xs[idx], ys[idx]
    rgb = crop[ys, xs]
    mm = np.array([sp.to_mm(x + x0, y + y0) for x, y in zip(xs, ys)])
    return mm[:, 0], mm[:, 1], rgb, mask, crop


def _r2(residual: np.ndarray, total: np.ndarray) -> float:
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((total - total.mean()) ** 2))
    if ss_tot <= 1e-9:
        return 0.0
    return 1.0 - ss_res / ss_tot


def _fit_linear(mm_x: np.ndarray, mm_y: np.ndarray, val: np.ndarray
                ) -> tuple[tuple[float, float], float]:
    """Least-squares plane val ~= a*x + b*y + c. -> (unit direction, r2)."""
    a = np.column_stack([mm_x, mm_y, np.ones_like(mm_x)])
    coef, *_ = np.linalg.lstsq(a, val, rcond=None)
    pred = a @ coef
    r2 = _r2(val - pred, val)
    mag = math.hypot(coef[0], coef[1])
    direction = (coef[0] / mag, coef[1] / mag) if mag > 1e-9 else (1.0, 0.0)
    return direction, r2


def _fit_radial(mm_x: np.ndarray, mm_y: np.ndarray, val: np.ndarray,
                center: tuple[float, float]) -> float:
    """Least-squares val ~= p*r + q about a fixed center. -> r2."""
    r = np.hypot(mm_x - center[0], mm_y - center[1])
    a = np.column_stack([r, np.ones_like(r)])
    coef, *_ = np.linalg.lstsq(a, val, rcond=None)
    pred = a @ coef
    return _r2(val - pred, val)


def _speckle_ratio(crop: np.ndarray, mask: np.ndarray) -> float:
    """Local (pixel-to-pixel) variance over global variance, inside the mask.

    A ramp's neighbouring pixels barely differ relative to the ramp's own
    overall spread; photographic texture's do, because texture has energy at
    the pixel scale the way a ramp structurally cannot.

    The mask is eroded a few pixels first. A curved region's own OUTLINE is a
    hard edge against whatever sits outside it, and the Laplacian kernel at a
    mask pixel next to that boundary reads that outside jump, not texture
    inside the shape — measured on the radial ramp fixture, a smooth disc,
    where the raw ratio came in at 1.45 (misread as speckle) and the eroded
    one at 0.17 (correctly read as smooth) purely from excluding that ring.
    """
    eroded = cv2.erode(mask.astype(np.uint8), np.ones((5, 5), np.uint8)) > 0
    if eroded.sum() < 9:
        eroded = mask
    if eroded.sum() < 9:
        return 0.0
    gray = cv2.cvtColor(crop, cv2.COLOR_RGB2GRAY).astype(np.float64)
    lap = cv2.Laplacian(gray, cv2.CV_64F, ksize=3)
    local_var = float(np.var(lap[eroded]))
    global_var = float(np.var(gray[eroded])) + 1e-6
    return local_var / global_var


def _vertex_range_linear(poly: Polygon, direction: tuple[float, float]) -> tuple[float, float]:
    ux, uy = direction
    pts = list(poly.exterior.coords)
    for ring in poly.interiors:
        pts.extend(ring.coords)
    proj = [x * ux + y * uy for x, y in pts]
    return min(proj), max(proj)


def _vertex_range_radial(poly: Polygon, center: tuple[float, float]) -> tuple[float, float]:
    cx, cy = center
    pts = list(poly.exterior.coords)
    for ring in poly.interiors:
        pts.extend(ring.coords)
    dists = [math.hypot(x - cx, y - cy) for x, y in pts]
    lo = 0.0 if poly.contains(Point(cx, cy)) else min(dists)
    return lo, max(dists)


# Why a region was NOT accepted as a ramp. Reported per-region by
# `blend_fill` so the warning the user actually sees can describe what
# happened instead of what was promised at classification time — the
# 2026-08-12 measurement on Kent's owl found all 25 regions rejected (24
# on r2, 1 on speckle) while the app still announced decomposition. These
# are internal diagnostic strings, not user copy.
RAMP_OK = ""
RAMP_REJECT_FEW_SAMPLES = "few_samples"
RAMP_REJECT_LOW_R2 = "low_r2"
RAMP_REJECT_SPECKLED = "speckled"


def detect_ramp_detail(poly: Polygon, sp: SourcePixels,
                       speckle_r2_override: float | None = None,
                       ) -> tuple[RampModel | None, str, float]:
    """-> (model or None, rejection reason, best r2 seen).

    The measuring half of `detect_ramp`, split out so callers that need to
    explain a rejection (`blend_fill`, for the user-facing warning) get the
    same numbers the decision was made on rather than re-deriving them.
    `detect_ramp` stays the plain model-or-None entry point every existing
    caller already uses.

    `speckle_r2_override` (cfg.blend_speckle_r2_override — see that field's
    comment for the measurement and Kent's 2026-08-23 funding of it): when
    set, a region whose best r² is at or above the bar passes the speckle
    gate regardless of its texture — the fit quality vouches for it. None,
    the default, is the shipped gate exactly.
    """
    mm_x, mm_y, rgb, mask, crop = _sample_pixels(poly, sp)
    if len(mm_x) < 12:
        return None, RAMP_REJECT_FEW_SAMPLES, 0.0
    lab = rgb_to_lab(rgb)
    lightness = lab[:, 0]

    direction, r2_linear = _fit_linear(mm_x, mm_y, lightness)
    centroid = poly.centroid
    r2_radial = _fit_radial(mm_x, mm_y, lightness, (centroid.x, centroid.y))

    best_r2 = max(r2_linear, r2_radial)
    if best_r2 < RAMP_R2_MIN:
        return None, RAMP_REJECT_LOW_R2, best_r2
    vouched = speckle_r2_override is not None and best_r2 >= speckle_r2_override
    if not vouched and _speckle_ratio(crop, mask) > RAMP_SPECKLE_MAX:
        return None, RAMP_REJECT_SPECKLED, best_r2

    if r2_linear >= r2_radial:
        lo, hi = _vertex_range_linear(poly, direction)
        return RampModel("linear", direction, None, lo, hi, r2_linear), RAMP_OK, best_r2
    center = (centroid.x, centroid.y)
    lo, hi = _vertex_range_radial(poly, center)
    return RampModel("radial", None, center, lo, hi, r2_radial), RAMP_OK, best_r2


def detect_ramp(poly: Polygon, sp: SourcePixels) -> RampModel | None:
    """-> the winning ramp model, or None (fall back to ordinary tatami)."""
    return detect_ramp_detail(poly, sp)[0]


# Design-wide acceptance floor, deliberately lower than (and separate from)
# RAMP_R2_MIN. `detect_design_ramp_angle` below picks the BEST of 6 fits
# (L/a/b, each linear and radial) instead of one channel, and that matters:
# measured on the confirmed repro fixture (a real diagonal purple -> pink ->
# orange gradient, `testdata/photo/repro_gradient_white_icon.png`), L barely
# correlates with position at all (r2 0.003) because the ramp is a hue
# rotation, not a lightness slope — the per-region `detect_ramp` this design
# angle exists to fix would have missed it too, on the same evidence, were
# it not for whichever fragment happened to sample a patch small enough for
# hue to look locally linear. The b* (blue-yellow) channel alone carries it,
# at r2 0.45 — real signal, comfortably clear of the ~0.05 noise floor the
# same fixture's L and a channels read at, just short of RAMP_R2_MIN's 0.5
# (tuned for a single-channel, per-region fit, a different question). 0.4
# leaves margin on both sides: above the noise floor, below every measured
# true positive (0.45 here, 0.994-0.999 on the committed synthetic ramps).
DESIGN_RAMP_R2_MIN = 0.4


def detect_design_ramp_angle(design_prep: Prep, max_samples: int = RAMP_MAX_SAMPLES,
                             seed: int = RAMP_SAMPLE_SEED) -> float | None:
    """The one shared fill-row angle every blend group in a `gradient`
    design should sew at, or None (each region falls back to its own
    `stage6_fill.principal_angle_deg`, the pre-fix behaviour).

    Deliberately NOT `detect_ramp` reused at design scope: that function
    fits a single channel (lightness) against position, which is exactly
    the axis a hue-driven ramp (this defect's own confirmed repro) does not
    vary along. This fits L, a AND b independently (`_fit_linear`/
    `_fit_radial`, same machinery, one call per channel) and takes whichever
    of the 6 (channel, kind) results explains the most variance — the
    channel that actually carries the gradient wins regardless of which one
    it is. Only a LINEAR winner produces an angle: a radial ramp's bands are
    concentric rings, and no single line direction keeps a row inside one
    band, so per-region behaviour is left alone for those (a known,
    documented gap — see
    `docs/superpowers/plans/2026-08-03-gradient-tier-fragmentation-and-enclosed-white-defects.md`).

    Sampled straight from `design_prep.rgb` / `~design_prep.bg_mask` (the
    whole design's foreground), not any one region's polygon — this runs
    once per design, before stage 2 fragments it into however many k-means
    regions.

    `enclosed_mask` pixels (BACKGROUND_ENCLOSED — bg-colored areas not
    reachable from the canvas border, unstitched by default since
    2026-08-04) are EXCLUDED from the fit. Before that change they sat
    inside `bg_mask` and were never sampled; when they moved to foreground,
    letting them into this fit silently broke the angle-fragmentation fix
    on the fix's own repro fixture — the white icon linework is a large,
    positionally-clustered population whose color has nothing to do with
    the gradient, and it dragged every channel's best r2 below
    DESIGN_RAMP_R2_MIN (the detector returned None, every fragment fell
    back to its own per-region angle, the patchwork came back). Excluding
    them restores this detector's intended population: the design's own
    ramp-carrying, stitched-by-default foreground.
    """
    fg = ~design_prep.bg_mask
    enclosed = getattr(design_prep, "enclosed_mask", None)
    if enclosed is not None:
        fg = fg & ~enclosed
    all_ys, all_xs = np.nonzero(fg)
    if len(all_xs) < 12:
        return None

    mm_x_all = all_xs.astype(np.float64) / design_prep.px_per_mm
    mm_y_all = all_ys.astype(np.float64) / design_prep.px_per_mm

    if len(all_xs) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(all_xs), size=max_samples, replace=False)
    else:
        idx = np.arange(len(all_xs))
    mm_x, mm_y = mm_x_all[idx], mm_y_all[idx]
    lab = rgb_to_lab(design_prep.rgb[all_ys[idx], all_xs[idx]])
    centroid_mm = (float(mm_x_all.mean()), float(mm_y_all.mean()))

    best_r2, best_kind, best_direction = -1.0, None, None
    for c in range(3):
        val = lab[:, c]
        direction, r2_linear = _fit_linear(mm_x, mm_y, val)
        if r2_linear > best_r2:
            best_r2, best_kind, best_direction = r2_linear, "linear", direction
        r2_radial = _fit_radial(mm_x, mm_y, val, centroid_mm)
        if r2_radial > best_r2:
            best_r2, best_kind = r2_radial, "radial"

    if best_r2 < DESIGN_RAMP_R2_MIN or best_kind != "linear":
        return None

    # Rows should stay inside one color band as long as possible, so they run
    # PERPENDICULAR to the ramp's own axis (parallel to its iso-color lines)
    # — rotate the fitted unit direction 90 degrees. `angle_deg` names a
    # LINE, not a ray (`_fill_paths` only ever rotates a polygon by it), so
    # the perpendicular's sign is irrelevant — +90 or -90 picks the same line.
    ux, uy = best_direction
    return math.degrees(math.atan2(ux, -uy))


# --- Shade decomposition ------------------------------------------------------

def _choose_shade_count(delta_e: float) -> int:
    n = round(delta_e / SHADE_STEP_DELTAE) + 1
    return max(SHADE_COUNT_MIN, min(SHADE_COUNT_MAX, n))


def _shade_lab_colors(ts: np.ndarray, lab: np.ndarray, n: int) -> list[np.ndarray]:
    """Average Lab color of the samples nearest each of `n` canonical ramp
    positions (0, 1/(n-1), ..., 1) — the barycentric bucketing that turns a
    continuous ramp into n discrete, chart-snappable shades."""
    centers = [i / (n - 1) for i in range(n)] if n > 1 else [0.5]
    nearest = np.argmin(
        np.abs(ts[:, None] - np.array(centers)[None, :]), axis=1
    )
    out = []
    overall_mean = lab.mean(axis=0)
    for i in range(n):
        sel = lab[nearest == i]
        out.append(sel.mean(axis=0) if len(sel) else overall_mean)
    return out


def _polygon_parts(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if geom.geom_type == "Polygon":
        return [geom]
    return [g for g in getattr(geom, "geoms", []) if g.geom_type == "Polygon" and not g.is_empty]


def _band_clip(poly: Polygon, model: RampModel, t_lo: float, t_hi: float) -> list[Polygon]:
    """The part of `poly` whose ramp position falls in [t_lo, t_hi]."""
    if model.hi <= model.lo:
        return _polygon_parts(poly)
    s_lo = model.lo + t_lo * (model.hi - model.lo)
    s_hi = model.lo + t_hi * (model.hi - model.lo)

    if model.kind == "linear":
        ux, uy = model.direction
        vx, vy = -uy, ux  # perpendicular
        minx, miny, maxx, maxy = poly.bounds
        span = math.hypot(maxx - minx, maxy - miny) + 1.0
        cx = (minx + maxx) / 2.0
        cy = (miny + maxy) / 2.0
        # A generously long strip perpendicular to the ramp direction,
        # bounded along it by [s_lo, s_hi]; long enough to clear the whole
        # polygon's own projected extent in the perpendicular direction.
        c0x, c0y = cx + ux * s_lo, cy + uy * s_lo
        c1x, c1y = cx + ux * s_hi, cy + uy * s_hi
        strip = Polygon([
            (c0x + vx * span, c0y + vy * span),
            (c0x - vx * span, c0y - vy * span),
            (c1x - vx * span, c1y - vy * span),
            (c1x + vx * span, c1y + vy * span),
        ])
        return _polygon_parts(poly.intersection(strip.buffer(0)))

    cx, cy = model.center
    outer = Point(cx, cy).buffer(max(s_hi, 0.0), quad_segs=64)
    band = outer if s_lo <= 1e-9 else outer.difference(Point(cx, cy).buffer(s_lo, quad_segs=64))
    return _polygon_parts(poly.intersection(band))


# --- Emission ------------------------------------------------------------------

def blend_fill(region: Region, source_pixels: SourcePixels, cfg
               ) -> tuple[list[StitchRun], dict]:
    """Ramp region -> (stitches, report). Same `(runs, report)` contract as
    `stage6_fill.stitch_shape` and its other siblings, so stage 7 sequencing
    treats a blend group exactly like any other fill tier — including
    border eligibility, which depends on reading a real report back.
    """
    poly = region.polygon
    model, reject, best_r2 = detect_ramp_detail(
        poly, source_pixels,
        speckle_r2_override=cfg.blend_speckle_r2_override)
    if model is None:
        # Not a ramp (or too speckled to trust as one) — ordinary tatami,
        # the same call every other fill-classified shape gets, report and
        # all. This is the branch EVERY k-means fragment of a real gradient
        # actually takes, not an edge case: post-quantize color bands are
        # already near-uniform internally, so a fragment's own pre-quantize
        # sample rarely carries enough of a residual ramp to pass
        # `detect_ramp`'s gates (confirmed on the repro fixture — all 23
        # regions fall back here). Passing the shared design angle instead of
        # None here is therefore the actual fix for the 2026-08-03
        # angle-fragmentation defect: without it, every fragment falls back
        # to `stitch_shape`'s own default (`principal_angle_deg` of that
        # fragment's own, often small and irregular, silhouette) and the
        # patchwork is exactly 23 independent PCA axes. None when this
        # design has no shared angle (not gradient-classified, or the
        # whole-design fit itself declined) preserves the untouched default.
        runs, report = stitch_shape(
            poly, region.shape_id, angle_deg=source_pixels.design_row_angle_deg,
            row_mm=machine.FILL_ROW_MM, stitch_mm=machine.FILL_STITCH_MM,
            underlay_style="none", trim_at_mm=machine.TRIM_AT_MM,
        )
        # Routed to blend, sewn flat. Stage 7 aggregates these across the
        # design so the warning the user reads can say decomposition did
        # NOT happen — the classification-time copy only ever described the
        # routing, and on a real photograph every region lands here.
        report["blend_shades"] = 0
        report["blend_reject"] = reject
        report["blend_best_r2"] = best_r2
        return runs, report

    mm_x, mm_y, rgb, _mask, _crop = _sample_pixels(poly, source_pixels)
    lab = rgb_to_lab(rgb)
    ts = np.array([model.t(x, y) for x, y in zip(mm_x, mm_y)])

    extremes_delta_e = float(
        deltaE_ciede2000(lab[np.argmin(ts): np.argmin(ts) + 1],
                         lab[np.argmax(ts): np.argmax(ts) + 1])[0]
    ) if len(ts) else 0.0
    n = _choose_shade_count(extremes_delta_e)
    shade_labs = _shade_lab_colors(ts, lab, n)

    chart = chart_for(cfg)
    shade_thread_idx = [chart.nearest_index(c) for c in shade_labs]
    shade_rgbs = [tuple(int(v) for v in chart[t].rgb) for t in shade_thread_idx]

    # The whole-design angle (set once per design, see
    # `SourcePixels.design_row_angle_deg`) wins whenever it exists: every
    # fragment then sews its rows in the SAME direction instead of each
    # independently re-deriving its own from its own, possibly tiny, slice of
    # the gradient — the 2026-08-03 angle-fragmentation fix.
    #
    # **Widened 2026-08-04** (routing "gradient" through `stage2_photo_
    # segment`'s SLIC+RAG instead of plain k-means): this used to gate on
    # `model.kind == "linear"` too — a region whose OWN fit came back radial
    # kept its own `principal_angle_deg` regardless, on the reasoning that no
    # single line direction fits a set of concentric bands. That reasoning
    # is right for a genuinely radial DESIGN (`design_row_angle_deg` stays
    # None there — `detect_design_ramp_angle` only ever produces an angle
    # from a LINEAR whole-design fit, so this branch never even applies to
    # one), but SLIC+RAG's fewer, larger, more organically-shaped fragments
    # exposed a case that gate did not distinguish: a genuinely LINEAR whole
    # design (`design_row_angle_deg` IS set) where a single small, irregular
    # leftover fragment's OWN `detect_ramp` spuriously reads "radial" —
    # `RAMP_R2_MIN`'s r2 gate has no minimum fragment SIZE, so a centroid-
    # based radial fit can explain a small sample's variance well by chance.
    # Measured on `repro_gradient_white_icon.png`: two ~4.5mm2 fragments
    # (single fill row each) read radial and fell to their own noisy
    # `principal_angle_deg`, landing 2.7deg off the other fragments' shared
    # ~-45.4deg — small in absolute terms, but exactly the "some fragments
    # picked their own angle" defect this whole mechanism exists to close,
    # now that the fragment population can include shapes small enough to
    # overfit. Once the design-wide fit has already established ONE linear
    # direction for the whole gradient, a region-local "radial" reading on a
    # sliver of it is far more likely overfitting than real local structure,
    # so it no longer overrides the shared angle. `model.kind` still governs
    # everything else about a radial fragment (its own band-clipping still
    # follows `model.center`, only the FILL ROW ANGLE changed here).
    angle = source_pixels.design_row_angle_deg
    if angle is None:
        angle = principal_angle_deg(poly)
    row_mm = machine.FILL_ROW_MM * n

    all_runs: list[StitchRun] = []
    layer_runs: list[list[StitchRun]] = []
    # Aggregated the same way `stitch_one` aggregates a group of shapes: OR
    # for too_thin (any band pinching to nothing is worth flagging), sum for
    # jumps, AND for empty (empty only if every band produced nothing).
    report = {"too_thin": False, "jumps": 0, "empty": False,
              "blend_shades": n, "blend_reject": RAMP_OK, "blend_best_r2": best_r2}
    for i in range(n):
        t_lo = max(0.0, i / n - (0.0 if i == 0 else _BAND_OVERLAP_T))
        t_hi = min(1.0, (i + 1) / n + (0.0 if i == n - 1 else _BAND_OVERLAP_T))
        parts = _band_clip(poly, model, t_lo, t_hi)
        this_layer: list[StitchRun] = []
        for part in parts:
            if part.is_empty or part.area <= 0:
                continue
            runs, band_report = stitch_shape(
                part, f"{region.shape_id}-blend{i}", angle_deg=angle,
                row_mm=row_mm, stitch_mm=machine.FILL_STITCH_MM,
                underlay_style="none", trim_at_mm=machine.TRIM_AT_MM,
            )
            # Stamp this band's own snapped thread on every run it produced —
            # stage 7's block assembly reads this to sew each accepted shade
            # in its own StitchBlock instead of collapsing all of them into
            # `region.thread_index`. Stamped here (not left for stage 7 to
            # infer) because this loop is the only place that still knows
            # which band index `i` a run came from once `all_runs` flattens
            # every band together below.
            for run in runs:
                run.shade_thread_index = shade_thread_idx[i]
            if runs and this_layer:
                # `_band_clip` can hand back more than one disconnected part
                # for a single band (a ring-shaped region straddling the
                # ramp's hole, for instance). Each part is its own
                # `stitch_shape` call, so its first run always starts with
                # `jump=False` — correct in isolation, wrong once stitched
                # back to back with the part before it, which leaves a bare
                # straight stitch across whatever real gap separates the two
                # parts. Mark it explicitly rather than let that default
                # stand. Unlike `stitch_shape`'s own `emit()`, this never
                # tries a `travel_path` bridge first: a bridge would route
                # along an inset ring using the CURRENT part's thread, but
                # the gap here is between two pieces of the same shade, so
                # there is nothing wrong-colored about a plain jump — and no
                # ring to bridge along in the first place (the two parts
                # aren't nested, `_band_clip` split them because they are not
                # even touching).
                d = math.dist(this_layer[-1].points[-1], runs[0].points[0])
                runs[0].jump = True
                runs[0].trim = d > machine.TRIM_AT_MM
                report["jumps"] += 1
            this_layer.extend(runs)
            report["too_thin"] = report["too_thin"] or band_report["too_thin"]
            report["jumps"] += band_report["jumps"]
        if this_layer and all_runs:
            # Same fix as the parts-within-a-band stitch above, one level up:
            # the seam between one shade band's runs and the next band's runs
            # was left at StitchRun's jump=False default, so machine export
            # drew a bare straight stitch across the gap between bands
            # instead of a jump/trim. Mark it explicitly, same as above.
            # Same gap, one level up: the first run of a new shade band
            # starts with `jump=False` by the same `stitch_shape`-in-
            # isolation default, but the point it starts from is wherever
            # the PREVIOUS band's stitching ended — a different shade, sewn
            # over a different (overlapping) clip of the polygon, so the two
            # points are almost never coincident. Bridging along an inset
            # ring here would be actively wrong, not just unavailable: it
            # would carry the previous band's shade across the seam into
            # this band's territory, visibly smearing the wrong color at
            # every band boundary. A plain jump (mirroring `emit()`'s
            # fallback, without attempting its bridge) is the correct
            # behavior for a boundary that is a shade change, not a same-
            # color topology gap.
            d = math.dist(all_runs[-1].points[-1], this_layer[0].points[0])
            this_layer[0].jump = True
            this_layer[0].trim = d > machine.TRIM_AT_MM
            report["jumps"] += 1
        all_runs.extend(this_layer)
        layer_runs.append(this_layer)

    report["empty"] = not all_runs

    if cfg.debug_dir:
        dbg = Path(cfg.debug_dir)
        minx, miny, maxx, maxy = poly.bounds
        debugviz.stage6_blend_shades(dbg, shade_rgbs)
        debugviz.stage6_blend_rows(dbg, layer_runs, shade_rgbs, (maxx - minx, maxy - miny))

    return all_runs, report
