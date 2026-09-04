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
3. **Emission.** N tatami bands, ONE shared fill angle per
   region — `SourcePixels.design_row_angle_deg` when the whole design fit
   one ramp (`detect_design_ramp_angle`: perpendicular to a linear sweep,
   level for a radial one, so every fragment of a fragmented gradient sews
   the same direction instead of each picking its own — this wins over a
   region's OWN ramp model regardless of that model's kind, widened
   2026-08-04, see `blend_fill`'s own comment), else
   `stage6_fill.principal_angle_deg` of this region alone. Each band is the
   part of the region whose ramp position falls in its own slice of [0, 1],
   sewn at the fill row `FILL_ROW_MM` (until 2026-09-03 at `FILL_ROW_MM *
   N`: one sparse layer per band, a third to a fifth of a fill, cloth
   between every pair of rows on the sew-out). Every band of a region sews
   on ONE row lattice (`_emit_bands`), and where the rows run along the
   seams each seam is FEATHERED (2026-09-04, Kent's call): a
   `machine.BLEND_FEATHER_MM` zone sewn by both shades, alternating thread
   row by row, via a row filter on each band's own fill. Where rows cross
   the bands, or `cfg.blend_feather_mm` is 0, the seam is hard and the band
   that sews first (the darker, by chart L*) extends under the later one by
   `cfg.overlap_mm`, the same underlap stage 5 gives a seam between two
   colours (2026-09-03).

**The design ramp (2026-09-03, Kent's gradient ruling).** When the whole
design's ramp fits (`design_ramp.fit_design_ramp`, carried here as
`SourcePixels.design_ramp`), steps 1 and 2 are answered once for the DESIGN
and every region that rides the ramp (`DesignRamp.rides`) sews the design's
bands — same shade count, same threads, band edges at the same millimetres
along the sweep — so a ramp the artwork cuts into pieces still reads as one
sweep. Stage 2 flattened the same ramp out of its merge, which is what makes
those pieces few. Regions that do not ride, and every design whose ramp
does not fit, take the per-region path above unchanged.

Coordinates are the same convention as everywhere past stage 4: millimetres,
origin at the artwork bbox center, y-axis down.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import Point, Polygon
from skimage.color import deltaE_ciede2000

from . import debugviz, machine
from .design_ramp import DESIGN_RAMP_R2_MIN as _DESIGN_RAMP_R2_MIN
from .design_ramp import DesignRamp, fit_design_ramp
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

# The symmetric 2%-of-ramp band overlap (`_BAND_OVERLAP_T`) is gone as of
# 2026-09-03: bands underlap by `cfg.overlap_mm`, earlier under later, in the
# band loop of `blend_fill` — the same physical seam rule stage 5 applies
# between colours.


@dataclass
class SourcePixels:
    """A region's pre-quantize raster, in the same mm<->px mapping stage 4
    uses (see `debugviz.stage4`'s `to_px`): `mm = (px - origin_px) /
    px_per_mm`, y-down in both spaces. `rgb` is (H, W, 3) uint8.
    """

    rgb: np.ndarray
    px_per_mm: float
    origin_px: tuple[float, float]
    # Set by `pipeline.finish_generation` once per design, from
    # `detect_design_ramp_angle` against the WHOLE foreground — not one
    # region. `blend_fill` uses this as the shared fill-row angle instead of
    # each region's own `stage6_fill.principal_angle_deg` when set: the fix
    # for the 2026-08-03 angle-fragmentation defect, where `gradient`-class
    # art still segments via plain k-means before blend treatment (23 regions
    # on the repro fixture), each fragment picking its own, independently
    # computed angle — a patchwork of differently-angled wedges instead of
    # one flowing sweep. None for every class this stage never runs on, and
    # for a `gradient` design whose own whole-design fit declined (no ramp
    # found, linear or radial) — same per-region angle as always in that
    # case. A radial design ramp carries 0.0 here: level rows (2026-09-04).
    design_row_angle_deg: float | None = None
    # True only when stage 0 classified the DESIGN "gradient" — set by
    # `pipeline.run_stages`, read by stage 7 to decide whether auto-tier
    # fill shapes route through `blend_fill`. Exists because "source pixels
    # are present" stopped implying "gradient class" the moment tiers that
    # read the raster WITHOUT wanting blend routing arrived (the detail
    # layer is the first): those opt-ins carry pixels for their own use and
    # must leave every fill shape on the exact tatami path it always took.
    gradient_class: bool = False
    # (H, W) bool, True = SUBJECT, aligned to `rgb` — set by
    # `pipeline.finish_generation` only when a real subject cutout ran
    # (`cfg.photo_prep_background_removal` + rembg actually succeeding), and
    # `None` in every other job this repo has ever produced.
    #
    # It exists because a tier that reads the raster reads ALL of it. The
    # detail layer proved that on 2026-08-24: on `baby_deck_laugh` with the
    # cutout on (subject = 10% of the frame), 10,813 of the FDoG block's
    # 11,835 stitches — 91.4% — landed in background rembg had already
    # removed, and 72.2% of every stitch in the whole design sewed nothing
    # but deck boards. The regions were fine; they respect `Prep.bg_mask`
    # already. Only the raster-reading tier did not, because until this
    # field existed there was nothing on `SourcePixels` for it to respect.
    #
    # Deliberately NOT `~Prep.bg_mask`, and the narrower choice costs
    # nothing. Handing stage 1's border-flood background to this tier as
    # well SOUNDS like the more general fix, but it is very close to inert:
    # a flooded background is uniform by construction and FDoG responds to a
    # luminance step, so there is nothing there for it to find. Measured
    # 2026-08-24 on `testdata/logo_whitebg.png` (flat class, detail layer
    # forced on, border flood covering 74.4% of the frame): 0 of the detail
    # block's 1,523 stitches sew flooded background. The whole gain is on
    # the cutout route, where the "background" is a photographed deck and
    # full of real edges.
    #
    # So the rembg scope is not a compromise — it is where the defect lives.
    # And it buys a guarantee the wider rule could not: a job that did not
    # opt into the cutout carries `None` here and `_mask_to_subject` returns
    # its input array BY IDENTITY, so no existing lane can have moved a
    # stitch.
    subject_mask: np.ndarray | None = None
    # The design ramp (`design_ramp.fit_design_ramp`), expressed in THIS
    # frame — set by `pipeline.finish_generation` for a gradient-class design
    # whose ramp passed the fit's gate, None otherwise. `blend_fill` sews
    # every region that RIDES it with the design's own bands (2026-09-03,
    # Kent's gradient ruling: one ramp, one shade scheme, one set of
    # threads, however many pieces the artwork cuts the sweep into).
    # `design_row_angle_deg` above is this ramp's row angle whenever both
    # are set; it stays its own field because the tatami fallback reads
    # only the angle, and a hand-built SourcePixels can carry one without
    # the other.
    design_ramp: DesignRamp | None = None

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


# The design-wide acceptance floor lives with the fit it gates now
# (`design_ramp.DESIGN_RAMP_R2_MIN`, 2026-09-03); re-exported here for the
# callers that always read it from this module.
DESIGN_RAMP_R2_MIN = _DESIGN_RAMP_R2_MIN


def detect_design_ramp_angle(design_prep: Prep, max_samples: int = RAMP_MAX_SAMPLES,
                             seed: int = RAMP_SAMPLE_SEED) -> float | None:
    """The one shared fill-row angle every blend group in a `gradient`
    design should sew at, or None (each region falls back to its own
    `stage6_fill.principal_angle_deg`, the pre-fix behaviour).

    Since 2026-09-03 a wrapper over `design_ramp.fit_design_ramp`: the angle
    is the fitted ramp's `row_angle_deg` — rows run along the sweep's
    iso-colour lines, perpendicular to its direction — and the fit's gate is
    the angle's gate. That fit is robust to the artwork sitting on the ramp
    (trimmed, then consensus), which this function's own plain least
    squares was not: at Studio defaults the confirmed repro
    (`repro_gradient_white_icon.png`) is full-bleed, stage 1 floods no
    background, the white icon (22% of the pixels) sits in the population,
    and every channel fit under the floor — the 2026-08-03 fix had quietly
    stopped applying to its own repro whenever the guards were on, which is
    every real job. The guards-off test kept passing because there the icon
    is flooded away and excluded. A RADIAL design ramp (2026-09-04) answers
    0.0: its bands are rings, which no line keeps a row inside, so its rows
    are level — the same answer `stage6_fill.principal_angle_deg` gives a
    disc, and the one that does not look like a mistake (`gradient_ramp_
    radial` fits linear at 0.00 and radial at 0.999; until the radial fit
    existed the design declined and every region took its own angle).

    When the robust fit's gate refuses, the plain fit this function always
    was (`legacy_design_ramp_angle`) still answers, so a design the gate
    turns away keeps exactly the shared angle it had: `region_blobs` (five
    hued blobs, a-plane r² 0.45 on the whole foreground) sewed every blob at
    -89.7° before the gate existed and still does. The gate is a gate on
    FLATTENING and on sewing the design's bands, where a false positive
    costs colour; a shared row angle costs nothing when it is wrong.
    """
    ramp = fit_design_ramp(design_prep, max_samples=max_samples, seed=seed)
    if ramp is not None:
        return ramp.row_angle_deg()
    return legacy_design_ramp_angle(design_prep, max_samples=max_samples, seed=seed)


def legacy_design_ramp_angle(design_prep: Prep, max_samples: int = RAMP_MAX_SAMPLES,
                             seed: int = RAMP_SAMPLE_SEED) -> float | None:
    """The 2026-08-03 whole-design angle fit, verbatim: L, a and b each fitted
    linear and radial against position over the stitched foreground
    (`~bg_mask` less `enclosed_mask`), the best of the six taken, an angle
    only from a linear winner at r² >= DESIGN_RAMP_R2_MIN. The fallback
    behind `detect_design_ramp_angle` since 2026-09-04; kept as it was so
    every design the robust gate refuses keeps its angle byte for byte."""
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

    # Rows run PERPENDICULAR to the ramp's axis (along its iso-colour lines):
    # rotate the fitted unit direction 90 degrees. A LINE, not a ray, so the
    # perpendicular's sign is irrelevant.
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
        # Long enough to clear the polygon's whole extent perpendicular to
        # the ramp from where the strip is anchored (on the ramp axis through
        # the origin, so the polygon's own distance from the origin counts).
        span = (math.hypot(maxx - minx, maxy - miny)
                + math.hypot(max(abs(minx), abs(maxx)), max(abs(miny), abs(maxy))) + 1.0)
        # The strip's edges are the iso-lines raw(x, y) = s_lo and = s_hi,
        # each anchored on the point of the ramp axis with exactly that
        # projection — so the clip lands where `model.t` says the band is.
        # Until 2026-09-03 the anchors were offset by the polygon's own bbox
        # centre (`cx + ux * s_lo`), which is only right when that centre
        # projects to 0 on the ramp: true of every blend test fixture (all
        # centred on the origin), false of a region anywhere else. Measured:
        # the linear fixture region shifted 30 mm along its ramp clipped its
        # first band to nothing, its second to a third, and sewed a third
        # less thread than the centred copy, a 30 x 53 mm end strip with no
        # thread at all. In situ, `gradient_ramp_linear.png` at 80 mm — two
        # regions centred at x -15 and +24 — left 46% of the ramp more than
        # 1 mm from any thread (audit, 2026-09-04). Every piece of a design
        # ramp is off-centre, so this had to go before the design's bands
        # could be trusted.
        c0x, c0y = ux * s_lo, uy * s_lo
        c1x, c1y = ux * s_hi, uy * s_hi
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

def blend_fill(region: Region, source_pixels: SourcePixels, cfg,
               start_near: tuple[float, float] | None = None,
               *, polygon: Polygon | None = None
               ) -> tuple[list[StitchRun], dict]:
    """Ramp region -> (stitches, report). Same `(runs, report)` contract as
    `stage6_fill.stitch_shape` and its other siblings, so stage 7 sequencing
    treats a blend group exactly like any other fill tier — including
    border eligibility, which depends on reading a real report back.

    `polygon` is what to SEW: stage 5's compensated outline — pull
    compensation plus the seam tongue under whichever colour sews after —
    the same `p.polygon` every other tier is handed. None sews the artwork.
    The COLOUR is always read from the artwork (`region.polygon`): whether
    the region rides the design ramp, its own ramp fit, its shade colours —
    a compensated outline reaches into the neighbours' pixels at every
    tongue, and a white icon's tongue would pull white into the sweep's
    profile. Until 2026-09-04 stage 7 handed this tier the region alone, so
    every blend region sewed its raw artwork: no pull compensation and no
    tongue, on the very seams the 2026-09-01 sew-out showed as bare fabric
    — while `tools/seam_underlap.py`, which reads stage 5's PLAN, reported
    the tongue present at 0.54 mm mean depth on the repro. Measured on the
    stitches: the repro's blend regions covered 0% of their tongue strips.

    `start_near` is where the needle already is — the same contract every
    other tier takes from stage 7's picking loop. Until 2026-08-31 this tier
    silently dropped it: both `stitch_shape` call sites below passed
    nothing, so every gradient-class region entered at its own
    geometry-default corner however far the needle was (measured on
    `repro_gradient_white_icon.png` at 80 mm: a 72.0 mm and a 46 mm hop
    inside single colour blocks — the criss-cross half of the 2026-09-01
    sew-out's fragmentation verdict). The fallback path hands it straight
    to tatami; the band path chains — the first band enters near the
    caller's cursor and every later part enters near wherever stitching
    actually ended, which costs band ORDER nothing (bands still sew 0..n-1;
    `_shade_blocks` re-sorts accepted shades dark→light downstream).
    """
    poly = region.polygon
    sew_poly = polygon if polygon is not None else region.polygon
    chart = chart_for(cfg)

    # Kent's gradient ruling (2026-09-03): when the DESIGN's ramp fits
    # (`SourcePixels.design_ramp`, gate in `design_ramp.py`) and this region
    # sits on it — its own pixels within the ramp's tolerance in every Lab
    # channel — it sews the design's bands: the shade scheme, the threads
    # and the band edges (in millimetres along the sweep) are the design's,
    # so the pieces an icon cuts a ramp into read as one sweep on cloth. A
    # region that does not ride (the icon itself, a flat badge on the
    # ground) takes the per-region path below, exactly as before.
    design = source_pixels.design_ramp
    if design is not None and region_rides_design_ramp(poly, source_pixels):
        n, shade_thread_idx = design_shade_scheme(design, chart)
        # The design's own model, linear or radial (2026-09-04): a radial
        # design's bands are its rings, clipped from the sewn outline by
        # `_band_clip`'s radial branch; its rows are level and cross the
        # rings, so `_emit_bands` gives its seams the hard underlap, not the
        # feather (a stitch-level dither at ring seams is a later item).
        model = RampModel(design.kind, design.direction, design.center,
                          design.lo, design.hi, design.r2)
        return _emit_bands(region, source_pixels, cfg, start_near, model, n,
                           shade_thread_idx, design.row_angle_deg(), chart,
                           best_r2=design.r2, design_bands=True,
                           sew_poly=sew_poly)

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
            sew_poly, region.shape_id, angle_deg=source_pixels.design_row_angle_deg,
            row_mm=machine.FILL_ROW_MM, stitch_mm=machine.FILL_STITCH_MM,
            underlay_style="none", trim_at_mm=machine.TRIM_AT_MM,
            start_near=start_near, under_cover=cfg.fill_travel_under_cover,
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

    shade_thread_idx = [chart.nearest_index(c) for c in shade_labs]

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
    # is right for a genuinely radial DESIGN (until 2026-09-04
    # `design_row_angle_deg` stayed None there, `detect_design_ramp_angle`
    # producing an angle only from a LINEAR whole-design fit; a radial
    # design ramp now carries 0.0, level rows, and a region of it that does
    # not ride sews level too), but SLIC+RAG's fewer, larger, more
    # organically-shaped fragments
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
    return _emit_bands(region, source_pixels, cfg, start_near, model, n,
                       shade_thread_idx, angle, chart, best_r2=best_r2,
                       design_bands=False, sew_poly=sew_poly)


def region_rides_design_ramp(poly: Polygon, source_pixels: SourcePixels) -> bool:
    """Does this region sit on the design's ramp (`DesignRamp.rides`, on the
    same pixel sample the per-region fit reads)? False when the design has
    no ramp or the region is too small to sample. Asked twice per region:
    here, to sew the design's bands, and by stage 7's tier ladder, to keep
    a riding region off the satin rung — a thin ring of the sweep sewn as
    satin is one thread all the way round, the repro's outer strip fuchsia
    where the source turns orange (render, 2026-09-04)."""
    design = source_pixels.design_ramp
    if design is None:
        return False
    mm_x, mm_y, rgb, _mask, _crop = _sample_pixels(poly, source_pixels)
    return len(mm_x) >= 12 and design.rides(mm_x, mm_y, rgb_to_lab(rgb))


def design_shade_scheme(design: DesignRamp, chart) -> tuple[int, list[int]]:
    """The design ramp's shade bands: how many, and the thread each snaps
    to — computed from the ramp's own consensus samples, so every region
    that rides the ramp gets the same answer. The extremes are the mean Lab
    of the samples in the ramp's first and last 5% (the per-region path
    reads its two single extreme pixels, which is noisier than a design
    deserves); the count is `_choose_shade_count` of their CIEDE2000
    distance, the colours `_shade_lab_colors` at the canonical positions."""
    t, lab = design.sample_t, design.sample_lab
    lo_sel, hi_sel = t <= 0.05, t >= 0.95
    lo = lab[lo_sel].mean(axis=0) if lo_sel.any() else lab[np.argmin(t)]
    hi = lab[hi_sel].mean(axis=0) if hi_sel.any() else lab[np.argmax(t)]
    delta = float(deltaE_ciede2000(lo[None, :], hi[None, :])[0])
    n = _choose_shade_count(delta)
    return n, [chart.nearest_index(c) for c in _shade_lab_colors(t, lab, n)]


def _emit_bands(region: Region, source_pixels: SourcePixels, cfg,
                start_near: tuple[float, float] | None, model: RampModel, n: int,
                shade_thread_idx: list[int], angle: float, chart, *,
                best_r2: float, design_bands: bool,
                sew_poly: Polygon | None = None) -> tuple[list[StitchRun], dict]:
    """Sew `region` as `n` shade bands of `model`, band `i` in thread
    `shade_thread_idx[i]`, rows at `angle`. The emission half of `blend_fill`,
    shared by the design-ramp path and the per-region path; `design_bands`
    only goes into the report. `sew_poly` is the outline to sew (stage 5's
    compensated one, see `blend_fill`); None sews the artwork."""
    poly = sew_poly if sew_poly is not None else region.polygon
    shade_rgbs = [tuple(int(v) for v in chart[t].rgb) for t in shade_thread_idx]
    # Every band is a fill and sews at the fill row. Until 2026-09-03 this
    # was `FILL_ROW_MM * n` — one layer per band at n times the row, so a
    # four-shade ramp put down a quarter of a fill and showed cloth between
    # every pair of rows (Kent's first sew-out finding, on the gradient
    # lane). The plan-contract test counted each row as n rows wide and read
    # the coverage as 1.0; it now measures the real thing.
    row_mm = machine.FILL_ROW_MM

    all_runs: list[StitchRun] = []
    layer_runs: list[list[StitchRun]] = []
    # Aggregated the same way `stitch_one` aggregates a group of shapes: OR
    # for too_thin (any band pinching to nothing is worth flagging), sum for
    # jumps, AND for empty (empty only if every band produced nothing).
    report = {"too_thin": False, "jumps": 0, "empty": False,
              "blend_shades": n, "blend_reject": RAMP_OK, "blend_best_r2": best_r2,
              "blend_design_ramp": design_bands}
    # The needle's running position across the band loop: the caller's
    # cursor first, then wherever the last emitted part actually ended —
    # each part enters near it instead of at its own top-left default.
    cur = start_near
    # Seams between shade bands follow stage 5's rule for seams between
    # colours (2026-09-03, Kent's seam ruling): the band that sews FIRST
    # extends under the one that sews after it by `cfg.overlap_mm`, and the
    # later band never grows back. Stage 7 sews a region's shade blocks
    # dark -> light by chart L*, so the earlier band is the darker of each
    # adjacent pair, and `t` runs 0 light -> 1 dark, so that is normally band
    # i + 1 reaching DOWN the ramp into band i. Read the snapped threads'
    # L* rather than assume it: two neighbouring bands can snap to threads
    # whose L* order inverts the ramp's. Until this the bands overlapped
    # symmetrically by 2% of the ramp (`_BAND_OVERLAP_T`), a fraction with no
    # millimetres behind it; the sew-out's seam trenches were the reason to
    # give the seam the same physical underlap every other seam gets.
    span_mm = max(1e-9, float(model.hi - model.lo))
    # Feathered seams (2026-09-04, Kent's call on the gradient ruling's
    # render): at every internal seam a zone `feather` wide, centred on the
    # seam, is sewn by both bands at twice the row, the upper band's grid
    # phased by one row, so the rows alternate thread at the fill row and
    # the bands read as one sweep instead of steps. Each band's solid part
    # stops half a zone short of the seam. Bounded so a narrow ramp keeps a
    # solid core in every shade; 0 is the hard seam below, with the underlap.
    feather = (machine.BLEND_FEATHER_MM if cfg.blend_feather_mm is None
               else max(0.0, float(cfg.blend_feather_mm)))
    feather = min(feather, 0.4 * span_mm / n)
    # Only where the rows run along the seams — the design path's angle is
    # the ramp's own perpendicular, and a per-region linear model whose fill
    # angle happens to match. Rows that CROSS the bands (a per-region model
    # at the shape's principal angle, or a radial model) get the hard seam:
    # alternating rows cannot blend a seam they cut across, and sewing the
    # zone as pieces of its own cost a trim per piece (measured, 2026-09-04).
    rows_along_seam = False
    if model.kind == "linear":
        ux, uy = model.direction
        perp = math.degrees(math.atan2(ux, -uy))
        d_ang = abs((angle - perp) % 180.0)
        rows_along_seam = min(d_ang, 180.0 - d_ang) < 0.5
    if not rows_along_seam:
        feather = 0.0
    t_f = feather / span_mm
    report["blend_feather_mm"] = feather
    # The hard seam's underlap: only where there is no feather zone to do
    # the blending — a feathered seam already has both threads across it.
    t_ov = 0.0 if t_f > 0 else max(0.0, float(cfg.overlap_mm or 0.0)) / span_mm
    l_star = [float(chart.lab[idx][0]) for idx in shade_thread_idx]

    # One row lattice for the whole region (2026-09-04): `stitch_shape` hangs
    # a part's rows off that part's OWN rotated bounding box, so two bands,
    # or a band and its feather zone, land on grids up to a row apart and
    # the seam shows a step. Every part here is phased onto the lattice the
    # region would have if sewn whole — `rot_miny + row * (k + 1/2)` — the
    # solid parts on every member, a zone's lower band on the even members
    # and its upper band on the odd ones, so the union is the fill row
    # everywhere and a hard seam's rows continue across it at the pitch.
    rot_miny = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False).bounds[1]

    def lattice_phase(part: Polygon, part_row_mm: float, offset_rows: float) -> float:
        part_miny = affinity.rotate(part, -angle, origin=(0, 0), use_radians=False).bounds[1]
        target = rot_miny + row_mm * (0.5 + offset_rows)
        return (target - part_miny - 0.5 * part_row_mm) % part_row_mm

    def sew_pieces(pieces, band_i: int, this_layer: list[StitchRun]) -> None:
        """Sew a band's pieces — `(part, row_mm, lattice offset, keep_row)` —
        nearest piece first from wherever the needle is. A band clip across
        a ring or a hole comes back in two or three parts; nearest-first
        keeps a band's left-side pieces together, then its right-side ones."""
        nonlocal cur
        pending = [pc for pc in pieces if not pc[0].is_empty and pc[0].area > 0]
        while pending:
            if cur is None:
                k = 0
            else:
                here = Point(cur)
                k = min(range(len(pending)), key=lambda j: pending[j][0].distance(here))
            part, part_row_mm, offset_rows, keep_row = pending.pop(k)
            runs, band_report = stitch_shape(
                part, f"{region.shape_id}-blend{band_i}", angle_deg=angle,
                row_mm=part_row_mm, stitch_mm=machine.FILL_STITCH_MM,
                underlay_style="none", trim_at_mm=machine.TRIM_AT_MM,
                start_near=cur, under_cover=cfg.fill_travel_under_cover,
                row_phase_mm=lattice_phase(part, part_row_mm, offset_rows),
                keep_row=keep_row,
            )
            if runs:
                cur = runs[-1].points[-1]
            # Stamp this band's own snapped thread on every run it produced —
            # stage 7's block assembly reads this to sew each accepted shade
            # in its own StitchBlock instead of collapsing all of them into
            # `region.thread_index`. Stamped here (not left for stage 7 to
            # infer) because this loop is the only place that still knows
            # which band index a run came from once `all_runs` flattens
            # every band together below.
            for run in runs:
                run.shade_thread_index = shade_thread_idx[band_i]
            if runs and this_layer:
                # `_band_clip` can hand back more than one disconnected part
                # for a single band (a ring-shaped region straddling the
                # ramp's hole, for instance), and a feathered band adds its
                # zone passes as parts of their own. Each part is its own
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
                # ring to bridge along in the first place.
                d = math.dist(this_layer[-1].points[-1], runs[0].points[0])
                runs[0].jump = True
                runs[0].trim = d > machine.TRIM_AT_MM
                report["jumps"] += 1
            this_layer.extend(runs)
            report["too_thin"] = report["too_thin"] or band_report["too_thin"]
            report["jumps"] += band_report["jumps"]

    for i in range(n):
        t_lo, t_hi = i / n, (i + 1) / n
        if i > 0 and l_star[i] <= l_star[i - 1]:
            t_lo -= t_ov                     # this band is darker than the one below: it sews first, reach down
        if i < n - 1 and l_star[i] < l_star[i + 1]:
            t_hi += t_ov                     # darker than the one above: it sews first, reach up
        if i > 0:
            t_lo += t_f / 2.0                # the solid part stops half a zone short of the seam below...
        if i < n - 1:
            t_hi -= t_f / 2.0                # ...and of the seam above
        # The first and last bands absorb whatever of the polygon lies
        # beyond the model's [lo, hi] (review, 2026-09-04): on the design
        # path that range is the design's, and a region can reach past it —
        # by pull compensation, by simplification, or because the fitted
        # range fell short of a far corner — and a clamp at 0 / 1 left such
        # a corner in no band at all (3% of the repro's frame piece, sewn by
        # nothing). The per-region path's range was the polygon's own vertex
        # range and this was a no-op there; since the sewn outline is stage
        # 5's compensated one (2026-09-04) it reaches `pull` past the artwork
        # the model was fitted on, on the radial path too — an outer ring
        # left in no band is a bare rim the width of the compensation.
        if model.kind == "linear":
            p_lo, p_hi = _vertex_range_linear(poly, model.direction)
        else:
            p_lo, p_hi = _vertex_range_radial(poly, model.center)
        reach_lo = min(0.0, (p_lo - model.lo) / span_mm - 1e-3)
        reach_hi = max(1.0, (p_hi - model.lo) / span_mm + 1e-3)
        t_lo = reach_lo if i == 0 else max(0.0, t_lo)
        t_hi = reach_hi if i == n - 1 else min(1.0, t_hi)
        this_layer: list[StitchRun] = []
        if t_f > 0:
            # Rows run along the seam, so a row has one ramp position and a
            # band's whole reach — its solid core plus half of each zone it
            # borders — is ONE fill with a row filter: every lattice row in
            # the core, and inside a zone only the even members for the
            # lower band or the odd members for the upper one. The other
            # band keeps the complementary rows, so across the zone the union
            # is the fill row, alternating thread row by row, and the band
            # stays one column walk (three separate clips per band cost the
            # repro 52 trims against 23 — every hop between a core and its
            # zone was a few millimetres over the trim rule).
            # `t_lo`/`t_hi` were pulled in by half a zone above; the reach
            # goes a whole zone back out, to the far edge of each zone.
            lo_reach = t_lo - (t_f if i > 0 else 0.0)
            hi_reach = t_hi + (t_f if i < n - 1 else 0.0)
            core_lo = i / n + t_f / 2.0
            core_hi = (i + 1) / n - t_f / 2.0

            def keep_row(y_rot: float, core_lo=core_lo, core_hi=core_hi, i=i) -> bool:
                pt = affinity.rotate(Point(0.0, y_rot), angle, origin=(0, 0), use_radians=False)
                t = model.t(pt.x, pt.y)
                k = int(round((y_rot - rot_miny) / row_mm - 0.5))
                if i > 0 and t < core_lo:
                    return k % 2 == 1        # the zone below: this band is the upper one
                if i < n - 1 and t > core_hi:
                    return k % 2 == 0        # the zone above: this band is the lower one
                return True

            pieces = [(part, row_mm, 0.0, keep_row)
                      for part in _band_clip(poly, model, lo_reach, hi_reach)]
        else:
            # The hard seam: the band's own clip, with the underlap above.
            pieces = [(part, row_mm, 0.0, None) for part in _band_clip(poly, model, t_lo, t_hi)]
        sew_pieces(pieces, i, this_layer)
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
