"""Direction field — dense stitch-orientation from image structure.

Technique-menu row 6 of `docs/photo-digitizing-plan-2026-07-31.md`: the
foundational piece for the streamline/portrait tiers (row 10). "Stitch
direction that follows image structure (hair flow, fur growth)" is the
plan's stated biggest visible gap between our output and every commercial
auto tool; this module computes that direction, per pixel and per region.
NOT yet wired into stitch emission — nothing in the pipeline imports this
module; row 10 (the streamline tier) is the slice that will consume it.

Two stages, per the plan's own recipe:

1. **Structure tensor** (`skimage.feature.structure_tensor`): per-pixel
   local gradient covariance -> orientation of the dominant edge tangent
   (the minor eigenvector — the direction along which intensity varies
   LEAST, i.e. along the stripe/hair/edge, not across it) plus a coherence
   score `(l1 - l2) / (l1 + l2)` in [0, 1] — 1 where the neighborhood has
   one clear direction, 0 where it is isotropic (noise, flat color).
2. **ETF smoothing**, reimplemented from the published description in
   Kang, Lee & Chui, "Coherent Line Drawing", NPAR 2007 (the edge tangent
   flow construction). LICENSE NOTE, load-bearing: GitHub reference
   implementations of ETF carry unverified licenses — this code is written
   from the paper's math alone (the plan doc makes that constraint
   explicit), not adapted from any repository. The filter is a nonlinear
   vector smoothing: each pixel's tangent becomes the normalized weighted
   sum of its neighbors' tangents inside a radius-r disc, weighted by
     - w_m, the magnitude weight `(1/2)(1 + tanh(eta * (g_hat(y) - g_hat(x))))`
       — neighbors sitting on STRONGER edges pull harder, so weak/noisy
       pixels inherit direction from nearby real structure while strong
       edges keep their own;
     - w_d, the direction weight `|t(x) . t(y)|` — aligned neighbors count,
       perpendicular ones do not;
   with each neighbor's vector sign-flipped by `phi = sign(t(x) . t(y))`
   so anti-parallel tangents reinforce instead of cancelling (a tangent is
   a LINE direction; its sign is arbitrary). A few iterations propagate
   dominant directions along features — exactly the "hair flow" behavior
   the portrait tier needs.

Angle convention everywhere here: DEGREES MOD 180 (a line, not a ray),
`atan2(ty, tx)` with y-axis DOWN — the same convention
`stage6_fill.principal_angle_deg` returns and the fill emitters consume.
Because the mm<->px mapping used past stage 4 (`stage6_blend.SourcePixels`)
is a pure scale + translation with y down in both spaces, an angle measured
in pixel space IS the angle in mm space; no conversion is needed.

Everything is deterministic: no RNG anywhere, seeded or otherwise.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Polygon
from skimage.feature import structure_tensor

from . import debugviz

# --- Tunables ----------------------------------------------------------------

# Gaussian window of the structure tensor, px. Sets the scale of "local":
# big enough to average over pixel noise, small enough that a hair strand's
# direction is not blurred into its neighbor's.
TENSOR_SIGMA = 2.0

# ETF neighborhood radius (px) and iteration count. Kang 2007 reports the
# flow stabilizing in a small number of iterations; 3 with a radius-5 disc
# propagates a strong edge's direction ~15 px, plenty at stitch scale.
ETF_RADIUS_PX = 5
ETF_ITERATIONS = 3
# Steepness of the magnitude weight's tanh. eta = 1 is the paper's stated
# default; higher sharpens "strong edges win" toward a step function.
ETF_ETA = 1.0

# Below this region coherence the dominant angle is statistically
# meaningless — the caller should fall back to the house angle (the
# fabric/config default) instead of trusting `angle_deg`. Measured against
# the committed synthetic fixtures: parallel stripes read 0.97+, uniform
# noise reads under 0.10, flat color reads 0.0 — the gap is wide, and 0.25
# sits in it with margin on both sides (`tests/test_directionfield.py`
# pins all three readings).
COHERENCE_FALLBACK_MIN = 0.25

_EPS = 1e-12


# --- Dense field --------------------------------------------------------------

@dataclass(frozen=True)
class DirectionField:
    """Dense per-pixel orientation over one image raster.

    `tangent` is (H, W, 2) float64 — unit vectors (tx, ty), y-down, sign
    arbitrary (a tangent names a line, not a ray; consumers must treat t
    and -t as equal, which is why every angle here is mod 180). Zero where
    the image carries no gradient at all (flat color).
    `coherence` is (H, W) in [0, 1] — the structure tensor's anisotropy.
    `magnitude` is (H, W) in [0, 1] — gradient magnitude, image-normalized.
    """

    tangent: np.ndarray
    coherence: np.ndarray
    magnitude: np.ndarray

    def angle_deg_at(self, x: int, y: int) -> float:
        """Tangent angle at pixel (col x, row y), degrees mod 180."""
        tx, ty = self.tangent[y, x]
        return math.degrees(math.atan2(ty, tx)) % 180.0


def _to_gray(image: np.ndarray) -> np.ndarray:
    if image.ndim == 3:
        return cv2.cvtColor(image.astype(np.uint8), cv2.COLOR_RGB2GRAY).astype(np.float64)
    return image.astype(np.float64)


def _shifted(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """`out[y, x] = a[y + dy, x + dx]`, zero outside — out-of-image
    neighbors simply contribute nothing to the ETF sum."""
    h, w = a.shape[:2]
    out = np.zeros_like(a)
    y0, y1 = max(0, -dy), min(h, h - dy)
    x0, x1 = max(0, -dx), min(w, w - dx)
    if y1 > y0 and x1 > x0:
        out[y0:y1, x0:x1] = a[y0 + dy:y1 + dy, x0 + dx:x1 + dx]
    return out


def _etf_pass(tx: np.ndarray, ty: np.ndarray, mag: np.ndarray,
              radius: int, eta: float) -> tuple[np.ndarray, np.ndarray]:
    """One ETF smoothing iteration per Kang 2007 (see module docstring):
    t_new(x) = normalize( sum_y phi(x,y) t(y) w_s w_m w_d ) over the
    radius-r disc. Vectorized as a loop over the disc's pixel offsets,
    each offset handled as one whole-image shifted-array operation."""
    acc_x = np.zeros_like(tx)
    acc_y = np.zeros_like(ty)
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dy * dy + dx * dx > radius * radius:
                continue  # w_s: hard disc
            sx = _shifted(tx, dy, dx)
            sy = _shifted(ty, dy, dx)
            sm = _shifted(mag, dy, dx)
            dot = tx * sx + ty * sy
            # w_m * w_d, with phi folded in as the sign of dot itself:
            # phi * w_d = sign(dot) * |dot| = dot.
            w = 0.5 * (1.0 + np.tanh(eta * (sm - mag))) * dot
            acc_x += w * sx
            acc_y += w * sy
    norm = np.hypot(acc_x, acc_y)
    keep = norm > _EPS
    safe = np.where(keep, norm, 1.0)
    return np.where(keep, acc_x / safe, 0.0), np.where(keep, acc_y / safe, 0.0)


def compute_direction_field(image: np.ndarray, *, sigma: float = TENSOR_SIGMA,
                            etf_radius_px: int = ETF_RADIUS_PX,
                            etf_iterations: int = ETF_ITERATIONS) -> DirectionField:
    """(H, W[, 3]) image -> DirectionField on the same raster.

    `etf_iterations=0` returns the raw structure-tensor field — kept
    reachable on purpose so the smoothing's effect stays measurable
    (`tests/test_directionfield.py` asserts ETF improves a noise-injected
    stripe field, and that assertion needs the unsmoothed baseline).
    """
    gray = _to_gray(image)

    # Structure tensor in skimage's 'rc' (row, col) order: Arr = <gy gy>,
    # Arc = <gy gx>, Acc = <gx gx>. Rewritten to x/y: Axx = Acc, Axy = Arc,
    # Ayy = Arr.
    arr, arc, acc = structure_tensor(gray, sigma=sigma, mode="constant", order="rc")
    axx, axy, ayy = acc, arc, arr

    # Eigen-decomposition, closed form. Major eigenvector = dominant
    # GRADIENT direction (across the edge); the tangent is its
    # perpendicular. 2*theta form dodges the eigenvector special cases.
    half_trace = 0.5 * (axx + ayy)
    root = np.sqrt((0.5 * (axx - ayy)) ** 2 + axy ** 2)
    l1, l2 = half_trace + root, half_trace - root
    denom = l1 + l2
    coherence = np.where(denom > _EPS, (l1 - l2) / np.where(denom > _EPS, denom, 1.0), 0.0)

    theta_grad = 0.5 * np.arctan2(2.0 * axy, axx - ayy)
    theta_tan = theta_grad + math.pi / 2.0
    tx, ty = np.cos(theta_tan), np.sin(theta_tan)

    # Normalized gradient magnitude for the ETF's w_m, and to zero out the
    # tangent where there is no gradient at all (flat color must not carry
    # a phantom direction into the smoothing).
    gx = cv2.Sobel(gray, cv2.CV_64F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_64F, 0, 1, ksize=3)
    raw_mag = np.hypot(gx, gy)
    peak = float(raw_mag.max())
    magnitude = raw_mag / peak if peak > _EPS else np.zeros_like(raw_mag)

    flat = magnitude <= _EPS
    tx = np.where(flat, 0.0, tx)
    ty = np.where(flat, 0.0, ty)

    for _ in range(etf_iterations):
        tx, ty = _etf_pass(tx, ty, magnitude, etf_radius_px, ETF_ETA)

    return DirectionField(tangent=np.dstack([tx, ty]),
                          coherence=coherence, magnitude=magnitude)


# --- Per-region summary (what the streamline tier will consume) ---------------

@dataclass(frozen=True)
class RegionDirection:
    """One region's dominant stitch direction.

    `angle_deg`: degrees mod 180, LINE convention (`principal_angle_deg`'s),
    y-down — feed it straight to a fill emitter's `angle_deg`.
    `coherence`: in [0, 1] — the length of the magnitude-and-coherence
    weighted resultant of the region's doubled tangent angles. High only
    when the region's pixels AGREE on one direction; low both for noise
    (each pixel isotropic) and for structured-but-conflicting content
    (e.g. concentric rings, where every direction occurs equally).
    When it is below `COHERENCE_FALLBACK_MIN`, `angle_deg` is noise —
    use the house angle instead (`use_house_angle` says exactly that).
    """

    angle_deg: float
    coherence: float

    @property
    def use_house_angle(self) -> bool:
        return self.coherence < COHERENCE_FALLBACK_MIN


def region_direction(field: DirectionField, mask: np.ndarray) -> RegionDirection:
    """Dominant angle + coherence over `mask` (bool, same H x W as the field).

    Angles live on a half-circle, so averaging happens in doubled-angle
    space (the standard axial-statistics move, and the same one the
    structure tensor itself is built on): each unit tangent (tx, ty) maps
    to (tx^2 - ty^2, 2 tx ty) = (cos 2t, sin 2t), those are averaged with
    per-pixel weight `magnitude * coherence` (structured pixels vote,
    flat/noisy ones barely do), and the resultant's half-angle is the
    dominant direction while its length is the agreement score.
    """
    if mask.shape != field.coherence.shape:
        raise ValueError(f"mask shape {mask.shape} != field shape {field.coherence.shape}")
    m = mask.astype(bool)
    if not m.any():
        return RegionDirection(angle_deg=0.0, coherence=0.0)

    tx = field.tangent[..., 0][m]
    ty = field.tangent[..., 1][m]
    w = (field.magnitude * field.coherence)[m]
    total = float(w.sum())
    if total <= _EPS:
        return RegionDirection(angle_deg=0.0, coherence=0.0)

    # Unit tangents make tx^2 + ty^2 = 1, so these ARE cos/sin of 2*theta;
    # zero tangents (flat pixels) contribute a zero vector, exactly right.
    c2 = float((w * (tx * tx - ty * ty)).sum()) / total
    s2 = float((w * (2.0 * tx * ty)).sum()) / total
    resultant = math.hypot(c2, s2)
    angle = math.degrees(0.5 * math.atan2(s2, c2)) % 180.0
    return RegionDirection(angle_deg=angle, coherence=resultant)


def region_direction_for_polygon(field: DirectionField, poly: Polygon,
                                 source_pixels) -> RegionDirection:
    """`region_direction` for a region given as an mm-space polygon plus the
    mm<->px mapping the pipeline already carries
    (`stage6_blend.SourcePixels`, or anything with its `to_px`): the
    polygon is rasterized onto the field's grid with the same
    `to_px`-then-`fillPoly` convention `stage6_blend._crop_and_mask` uses,
    holes subtracted, and summarized. The returned angle needs no
    conversion back to mm space — see the module docstring.
    """
    mask = np.zeros(field.coherence.shape, np.uint8)

    def ring_px(coords) -> np.ndarray:
        return np.array([source_pixels.to_px(x, y) for x, y in coords], np.int32)

    cv2.fillPoly(mask, [ring_px(poly.exterior.coords)], 255)
    for hole in poly.interiors:
        cv2.fillPoly(mask, [ring_px(hole.coords)], 0)
    return region_direction(field, mask.astype(bool))


# --- Debug artifact -----------------------------------------------------------

def write_debug_artifact(field: DirectionField, rgb: np.ndarray, cfg) -> None:
    """The `cfg.debug_dir` gate, same shape as every stage's own debug hook
    (written when set, never in the hot path). Callers that computed a
    field over `rgb` call this unconditionally; it no-ops without a dir."""
    if cfg.debug_dir:
        debugviz.direction_field(Path(cfg.debug_dir), rgb, field)
