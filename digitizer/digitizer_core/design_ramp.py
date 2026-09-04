"""The design ramp: one linear colour sweep fitted to a gradient-class
design's whole stitched foreground, robust to the artwork sitting on it.

Kent's gradient ruling (2026-09-03, on the sew-out's "blocky bands"): when
the design's ramp fits, the ramp is ONE region — segmented as one, sewn as
one set of shade bands — instead of whatever colour bands stage 2's
SLIC + RAG merge happens to cut a smooth sweep into (10 regions on the
Instagram-icon repro, each then sewn flat in one thread). Two consumers read
the fit this module produces:

* `stage2_photo_segment.segment` FLATTENS the Lab image by it before the
  region-adjacency merge (`DesignRamp.flatten_lab`): every pixel loses the
  sweep's own colour at its position, so the sweep's superpixels all read
  as one colour and merge, while an icon drawn ON the sweep keeps its full
  contrast against it and stays its own region.
* `stage6_blend.blend_fill` sews every region that RIDES the ramp
  (`DesignRamp.rides`) with the DESIGN's bands — one shade scheme, one set
  of threads, band edges at the same millimetres in every piece — so a ramp
  the artwork cuts into pieces (the icon's white ring cuts the repro's into
  three) still reads as one sweep on cloth. It also supplies the shared
  fill-row angle `stage6_blend.detect_design_ramp_angle` used to fit on its
  own (the 2026-08-03 angle-fragmentation fix); that function is now a
  wrapper over this fit, with its old plain fit kept as the fallback.

**Two models, two jobs.** The GATE and the DIRECTION come from a plane per
Lab channel (`val ~ a*x + b*y + c`): a sweep is linear along its axis by
definition, and a plane is what an illustration with a lightness trend
cannot satisfy. The COLOUR comes from a profile along that axis
(`profile`: per channel, the consensus samples' median in each of
`DESIGN_RAMP_PROFILE_KNOTS` bins of the ramp position `t`, interpolated),
because a real sweep is rarely planar in every channel: the repro is a hue
rotation, magenta to orange, an ARC in a*b*. Against the winning L* plane
its a* and b* scatter 7.9 and 9.4 (measured 2026-09-04); against the
profile 0.3 and 0.4. So the plane decides whether this is a sweep, and the
profile says what colour the sweep is at each position — which is what
flattening subtracts and what a region is measured against when it asks to
ride. Gating on the profile instead would let Kent's owl through (L*
profile scatter 3.6 against the plane's 5.4: a smooth illustration follows
ANY 1-D curve well enough), which is exactly the design the gate exists to
refuse.

**Why a robust fit, not the plain least squares the angle detector used.**
The plain plane fit reads the whole foreground, artwork included. On the
repro at Studio defaults (a full-bleed image: stage 1 refuses to flood a
background, `BACKGROUND_ABSENT`, so the white icon — 22% of the pixels — sits
in the population) it explains 3% of L* and 30% of b*, under the 0.4 floor,
and the design got no shared angle at all; the 2026-08-03 test only ever
pinned the guards-off configuration, where the icon is flooded away.
`_consensus_plane` fits, keeps the `DESIGN_RAMP_TRIM_FRAC` of samples
nearest the plane, refits, then admits every sample within
`DESIGN_RAMP_CONSENSUS_K` robust sigmas of THAT plane and fits once more on
the consensus. On the repro the consensus is 78% of the foreground — the
non-white pixels, to within a percent — and L* fits at r² 0.80 along the
diagonal. Measured 2026-09-03 on every gradient-classified fixture in
`testdata/photo` (best channel, consensus r² / inlier fraction / plane
sigma): repro L 0.80 / 0.78 / 2.3; `gradient_ramp_linear` L 1.00 / 1.00 /
0.5; `region_blobs` a 0.49 / 0.88 / 9.2; `owl_kent` L 0.60 / 0.71 / 5.4;
`golden_tee` L 0.27; `drone_render` b 0.18; `summit_badge` b 0.05;
`bridge_bar`, `hotel_fremont`, `gaulke`, `phone_ui` under 0.1;
`gradient_ramp_radial` linear 0.00 (radial 0.91).

**The gate is three numbers, and each one rejects a fixture the others
would pass.** `DESIGN_RAMP_R2_MIN` (0.4, the angle detector's own floor,
now on the consensus) rejects the busy logos. `DESIGN_RAMP_MIN_INLIER_FRAC`
(0.6) says the ramp must be MOST of the stitched design. And
`DESIGN_RAMP_MAX_SIGMA` (4.0 Lab units of plane scatter — under half of
`stage6_blend.SHADE_STEP_DELTAE`) is what separates a sweep from a coarse
trend across several flat colours: `region_blobs` (five hued blobs with
their own shade sweeps, a-plane r² 0.49 on 88% of pixels) and Kent's owl
(L 0.60) both clear r² and fraction and are refused on scatter, 9.2 and 5.4
against the repro's 2.3. Flattening either by a plane that explains a trend
but not the pixels would have merged blobs the plan's own tests keep apart.
A channel wins only if it passes all three; the winner is the passing
channel with the best r². A design the gate refuses is untouched: the same
stage 2, the same per-region blend fit, byte for byte — and the same shared
fill-row angle, because `stage6_blend.detect_design_ramp_angle` keeps its
2026-08-03 plain fit as the fallback when this gate refuses (`region_blobs`
sews at the -89.7° that plain fit gives it, as it did before this module
existed).

**Riding.** `DesignRamp.rides` is what lets a region sew the design's bands,
and it asks two things of the region's pixels: that
`DESIGN_RAMP_REGION_RIDE_FRAC` of them sit within the ramp's per-channel
tolerance of the profile (`tol`: three robust sigmas of the consensus
around the profile, never under `DESIGN_RAMP_CONSENSUS_FLOOR`), and that
the region's MEAN colour is within `DESIGN_RAMP_RIDE_MAX_DELTAE` of what the
profile predicts for it. The second guard is what refuses a flat badge of
another hue at the sweep's lightness whatever the tolerances happen to be.
Measured on the repro's pieces (mean-colour CIEDE2000 against the
prediction): the ramp pieces 0.3 / 3.9 / 4.4, the white pieces 41–43, two
slivers 18 and 22. One shade step (9.0) separates them with margin.

**The ramp's range is the whole stitched foreground's**, not the consensus
sample's: a 2,500-pixel sample of a square misses the last few millimetres
of a diagonal's corners (the projection's distribution is triangular
there), and a band scheme whose `hi` stops 6 mm short of a riding region's
far corner leaves that corner in no band (review, 2026-09-04: 3% of the
repro's frame piece). `stage6_blend._emit_bands` also lets its first and
last bands absorb any overshoot, for the same reason.

Coordinates: the fit runs in stage 1's frame — millimetres from the raster's
top-left corner, `px / px_per_mm`, y down — because that is where stage 2
needs it. `shifted` re-expresses the same ramp in another frame (stage 6
works from the artwork bbox centre); every quantity here is either
frame-invariant (`t`, direction, the profile, sigma, r²) or carried
through that shift.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace

import numpy as np
from skimage.color import deltaE_ciede2000

from .stage1_prep import Prep
from .threads import rgb_to_lab

# --- The gate ------------------------------------------------------------------

# Fraction of variance the winning channel's plane must explain on its
# consensus set. The value `stage6_blend.DESIGN_RAMP_R2_MIN` carried since
# 2026-08-03 (re-exported there), now judged on the consensus rather than the
# whole foreground: a busy logo's best channel reads 0.05–0.27 either way.
DESIGN_RAMP_R2_MIN = 0.4
# The consensus must be at least this much of the stitched foreground — a
# ramp is the design, not a feature of it. Repro 0.78; the synthetic ramps 1.0.
DESIGN_RAMP_MIN_INLIER_FRAC = 0.6
# Robust scatter (1.4826 x median |residual|, Lab units) of the winning channel
# around its PLANE on the consensus set, at most. Under half a shade step
# (SHADE_STEP_DELTAE 9); the separator between a sweep (repro 2.3, synthetic
# 0.5) and a trend across flat colours (region_blobs 9.2, owl 5.4) — see the
# module docstring for why this is the plane's scatter, not the profile's.
DESIGN_RAMP_MAX_SIGMA = 4.0

# The winning channel's plane must sweep at least this much (Lab units, max
# minus min of its prediction over the consensus). Not a fixture separator —
# a floor under the other three: with the winner chosen among passing
# channels, a channel that barely varies can fit its own quantization noise
# at high r² and tiny scatter (a two-colour step's a*, span 0.4, did exactly
# that). One shade step: a sweep with less colour than that has no bands to
# give. Repro L 18.9, the linear fixture 62.9.
DESIGN_RAMP_MIN_SPAN = 9.0

# --- The fit -------------------------------------------------------------------

# First pass keeps the samples nearest the plain plane. 0.75 clears the
# repro's 22% of white icon with margin; a design whose artwork is more than
# a quarter of it is not the case this exists for and fails the fraction gate.
DESIGN_RAMP_TRIM_FRAC = 0.75
# Second pass admits every sample within K robust sigmas of the trimmed plane,
# never tighter than FLOOR (Lab units) so a clean synthetic ramp whose sigma
# is ~0 still admits its own anti-aliased edge pixels. The same K and FLOOR
# set the per-channel riding tolerance around the profile.
DESIGN_RAMP_CONSENSUS_K = 3.0
DESIGN_RAMP_CONSENSUS_FLOOR = 2.0
# Knots of the per-channel colour profile along the sweep: the consensus
# samples' median in each of this many equal bins of t. 17 bins over an
# 80–110 mm sweep is a knot every 5–7 mm, coarser than any band (a fifth of
# the sweep at most) and far too coarse to trace an icon.
DESIGN_RAMP_PROFILE_KNOTS = 17
# Deterministic subsample, same count and seed the per-region ramp fit uses
# (`stage6_blend.RAMP_MAX_SAMPLES` / `RAMP_SAMPLE_SEED`).
DESIGN_RAMP_MAX_SAMPLES = 2500
DESIGN_RAMP_SAMPLE_SEED = 0
# A region rides the design ramp when this fraction of its own samples sits
# within the ramp's tolerance in ALL three channels. The white icon pieces on
# the repro read 0.0 (L* 60+ off the profile); the ramp pieces read 0.99.
DESIGN_RAMP_REGION_RIDE_FRAC = 0.8
# ...and its mean colour is within this CIEDE2000 distance of the profile's
# prediction for it — one shade step, `stage6_blend.SHADE_STEP_DELTAE` (a
# test keeps the two in lockstep). See the module docstring, "Riding".
DESIGN_RAMP_RIDE_MAX_DELTAE = 9.0

_MAD_TO_SIGMA = 1.4826


def _r2(residual: np.ndarray, total: np.ndarray) -> float:
    ss_res = float(np.sum(residual ** 2))
    ss_tot = float(np.sum((total - total.mean()) ** 2))
    if ss_tot <= 1e-9:
        return 0.0
    return 1.0 - ss_res / ss_tot


def _plane(a: np.ndarray, val: np.ndarray) -> np.ndarray:
    coef, *_ = np.linalg.lstsq(a, val, rcond=None)
    return coef


def _consensus_plane(a: np.ndarray, val: np.ndarray
                     ) -> tuple[np.ndarray, np.ndarray, float, float]:
    """Trimmed-then-consensus least squares of one channel against position.
    -> (coef, consensus mask, r² on the consensus, robust sigma on it)."""
    coef = _plane(a, val)
    res = np.abs(val - a @ coef)
    keep = res <= np.quantile(res, DESIGN_RAMP_TRIM_FRAC)
    coef = _plane(a[keep], val[keep])
    res = np.abs(val - a @ coef)
    sigma0 = _MAD_TO_SIGMA * float(np.median(res[keep]))
    cons = res <= max(DESIGN_RAMP_CONSENSUS_K * sigma0, DESIGN_RAMP_CONSENSUS_FLOOR)
    coef = _plane(a[cons], val[cons])
    pred = a[cons] @ coef
    r2 = _r2(val[cons] - pred, val[cons])
    sigma = _MAD_TO_SIGMA * float(np.median(np.abs(val[cons] - pred)))
    return coef, cons, r2, sigma


def _radial_r2(mm_x: np.ndarray, mm_y: np.ndarray, val: np.ndarray,
               center: tuple[float, float]) -> float:
    r = np.hypot(mm_x - center[0], mm_y - center[1])
    a = np.column_stack([r, np.ones_like(r)])
    coef = _plane(a, val)
    return _r2(val - a @ coef, val)


def _profile(t: np.ndarray, lab: np.ndarray, knots: int) -> np.ndarray:
    """(3, knots) per-channel median colour at equally spaced ramp positions;
    a bin with no sample takes the linear interpolation of its neighbours."""
    grid = np.linspace(0.0, 1.0, knots)
    bins = np.minimum((t * (knots - 1) + 0.5).astype(int), knots - 1)
    out = np.zeros((3, knots), np.float64)
    for c in range(3):
        vals = np.full(knots, np.nan)
        for k in range(knots):
            sel = bins == k
            if sel.any():
                vals[k] = float(np.median(lab[sel, c]))
        ok = ~np.isnan(vals)
        out[c] = np.interp(grid, grid[ok], vals[ok])
    return out


@dataclass(frozen=True)
class DesignRamp:
    """One linear colour sweep across a design. Immutable; `shifted` makes the
    frame-changed copy. Positions are mm in the frame the ramp was fitted (or
    shifted) into."""

    direction: tuple[float, float]   # unit vector along the sweep (y down)
    planes: np.ndarray               # (3, 3): per Lab channel, val ~= a*x + b*y + c — the gate's model
    profile: np.ndarray              # (3, KNOTS): the colour along the sweep at equal steps of t
    sigma: np.ndarray                # (3,) robust residual scatter per channel around the profile, consensus set
    tol: np.ndarray                  # (3,) per-channel riding tolerance (K sigma, floored)
    channel: int                     # the Lab channel whose plane won (0 L, 1 a, 2 b)
    r2: float                        # its r² on the consensus
    plane_sigma: float               # its robust scatter around the plane — what the gate judged
    inlier_frac: float               # consensus / stitched foreground samples
    lo: float                        # projection range of the WHOLE stitched foreground along `direction`
    hi: float
    sample_t: np.ndarray             # (K,) ramp position of every consensus sample
    sample_lab: np.ndarray           # (K, 3) its Lab

    # -- geometry ---------------------------------------------------------------

    @property
    def span_mm(self) -> float:
        return self.hi - self.lo

    def row_angle_deg(self) -> float:
        """The shared fill-row angle: rows run along the ramp's iso-colour lines,
        perpendicular to `direction`. A line, not a ray — the sign is moot."""
        ux, uy = self.direction
        return math.degrees(math.atan2(ux, -uy))

    def raw(self, x, y):
        ux, uy = self.direction
        return x * ux + y * uy

    def t(self, x, y):
        """Ramp position in [0, 1], clamped. Vectorized over numpy inputs."""
        if self.hi <= self.lo:
            return np.zeros_like(np.asarray(x, dtype=float))
        return np.clip((self.raw(x, y) - self.lo) / (self.hi - self.lo), 0.0, 1.0)

    def shifted(self, dx: float, dy: float) -> "DesignRamp":
        """The same ramp in the frame whose origin sits at (dx, dy) of this
        one: x' = x - dx, y' = y - dy. `t`, direction, profile, sigma, r²,
        samples all carry over unchanged; the planes' constants and the
        projection range move with the origin."""
        planes = self.planes.copy()
        planes[:, 2] += planes[:, 0] * dx + planes[:, 1] * dy
        shift = self.raw(dx, dy)
        return replace(self, planes=planes, lo=self.lo - shift, hi=self.hi - shift)

    # -- colour -----------------------------------------------------------------

    def colour_at(self, t) -> np.ndarray:
        """(..., 3) Lab the profile gives at ramp position(s) `t`."""
        t = np.asarray(t, dtype=float)
        grid = np.linspace(0.0, 1.0, self.profile.shape[1])
        return np.stack([np.interp(t, grid, self.profile[c]) for c in range(3)], axis=-1)

    def predict(self, mm_x: np.ndarray, mm_y: np.ndarray) -> np.ndarray:
        """(K, 3) Lab the ramp predicts at each position."""
        return self.colour_at(self.t(np.asarray(mm_x, dtype=float), np.asarray(mm_y, dtype=float)))

    def residual(self, mm_x: np.ndarray, mm_y: np.ndarray, lab: np.ndarray) -> np.ndarray:
        return np.asarray(lab, dtype=float) - self.predict(mm_x, mm_y)

    def rides(self, mm_x: np.ndarray, mm_y: np.ndarray, lab: np.ndarray,
              min_frac: float = DESIGN_RAMP_REGION_RIDE_FRAC,
              max_delta_e: float = DESIGN_RAMP_RIDE_MAX_DELTAE) -> bool:
        """Do these samples sit ON the ramp — within tolerance in every
        channel for at least `min_frac` of them, AND their mean colour within
        `max_delta_e` of the colour the ramp predicts? The per-region question
        `blend_fill` asks before sewing a region with the design's bands; see
        the module docstring, "Riding", for why both halves are needed."""
        if len(mm_x) == 0:
            return False
        lab = np.asarray(lab, dtype=float)
        pred = self.predict(mm_x, mm_y)
        within = np.all(np.abs(lab - pred) <= self.tol[None, :], axis=1)
        if float(within.mean()) < min_frac:
            return False
        delta = float(deltaE_ciede2000(lab.mean(axis=0)[None, :], pred.mean(axis=0)[None, :])[0])
        return delta <= max_delta_e

    def flatten_lab(self, lab_img: np.ndarray, px_per_mm: float) -> np.ndarray:
        """(H, W, 3) Lab with the sweep subtracted: every pixel reads as the
        ramp's mid colour plus its own departure from the profile at its
        position. Positions are `px / px_per_mm`, so this is only meaningful
        in the fitted (stage 1) frame — stage 2's."""
        h, w = lab_img.shape[:2]
        xs = np.arange(w, dtype=np.float64) / px_per_mm
        ys = np.arange(h, dtype=np.float64) / px_per_mm
        ux, uy = self.direction
        t = self.t(ux * xs[None, :] + 0.0 * ys[:, None], 0.0)  # projection along x...
        # ...plus the y component, done as one broadcast so the (H, W) grid
        # is built once. `raw` is linear, so the two parts add.
        t = np.clip(((ux * xs)[None, :] + (uy * ys)[:, None] - self.lo) / max(1e-9, self.hi - self.lo), 0.0, 1.0)
        at_mid = self.colour_at(0.5)
        sweep = self.colour_at(t)
        return lab_img.astype(np.float64) - sweep + at_mid[None, None, :]


def fit_design_ramp_pixels(rgb: np.ndarray, fg: np.ndarray, px_per_mm: float,
                           max_samples: int = DESIGN_RAMP_MAX_SAMPLES,
                           seed: int = DESIGN_RAMP_SAMPLE_SEED) -> DesignRamp | None:
    """Fit the ramp to the `fg` pixels of `rgb` (both (H, W[, 3]), fg True =
    stitched foreground). None when the gate refuses — see the module
    docstring for what each of its three numbers turns away."""
    all_ys, all_xs = np.nonzero(fg)
    if len(all_xs) < 12:
        return None
    if len(all_xs) > max_samples:
        rng = np.random.default_rng(seed)
        idx = rng.choice(len(all_xs), size=max_samples, replace=False)
    else:
        idx = np.arange(len(all_xs))
    xs, ys = all_xs[idx], all_ys[idx]
    mm_x = xs.astype(np.float64) / px_per_mm
    mm_y = ys.astype(np.float64) / px_per_mm
    lab = rgb_to_lab(rgb[ys, xs]).astype(np.float64)
    a = np.column_stack([mm_x, mm_y, np.ones_like(mm_x)])

    # Every channel is fitted; a channel is a candidate only if it passes all
    # three gates, and the winner is the best r² among the candidates — so a
    # channel with the best r² but too much scatter cannot block one that
    # fits cleanly (review, 2026-09-04).
    best = None
    for c in range(3):
        coef, cons, r2, sigma = _consensus_plane(a, lab[:, c])
        frac = float(cons.mean())
        if r2 < DESIGN_RAMP_R2_MIN or frac < DESIGN_RAMP_MIN_INLIER_FRAC \
                or sigma > DESIGN_RAMP_MAX_SIGMA:
            continue
        pred = a[cons] @ coef
        if float(pred.max() - pred.min()) < DESIGN_RAMP_MIN_SPAN:
            continue
        if best is None or r2 > best[3]:
            best = (c, coef, cons, r2, sigma, frac)
    if best is None:
        return None
    channel, coef, cons, r2, plane_sigma, inlier_frac = best
    # A sweep, not rings: the same channel on the same consensus must not be
    # explained better by distance from the centroid (the radial fixture's
    # linear r² is 0.00 against radial 0.91).
    centroid = (float(mm_x.mean()), float(mm_y.mean()))
    if _radial_r2(mm_x[cons], mm_y[cons], lab[cons, channel], centroid) > r2:
        return None
    mag = math.hypot(coef[0], coef[1])
    if mag <= 1e-9:
        return None
    direction = (float(coef[0] / mag), float(coef[1] / mag))

    planes = np.zeros((3, 3), np.float64)
    for c in range(3):
        planes[c] = _plane(a[cons], lab[cons, c])

    # The ramp's range is the WHOLE stitched foreground's projection, not the
    # sample's (see the module docstring, "The ramp's range").
    raw_all = (all_xs.astype(np.float64) / px_per_mm) * direction[0] \
        + (all_ys.astype(np.float64) / px_per_mm) * direction[1]
    lo, hi = float(raw_all.min()), float(raw_all.max())
    if hi - lo <= 1e-6:
        return None
    raw = mm_x[cons] * direction[0] + mm_y[cons] * direction[1]
    sample_t = np.clip((raw - lo) / (hi - lo), 0.0, 1.0)
    sample_lab = lab[cons]

    profile = _profile(sample_t, sample_lab, DESIGN_RAMP_PROFILE_KNOTS)
    grid = np.linspace(0.0, 1.0, DESIGN_RAMP_PROFILE_KNOTS)
    sigmas = np.zeros(3, np.float64)
    for c in range(3):
        res = np.abs(sample_lab[:, c] - np.interp(sample_t, grid, profile[c]))
        sigmas[c] = _MAD_TO_SIGMA * float(np.median(res))
    tol = np.maximum(DESIGN_RAMP_CONSENSUS_K * sigmas, DESIGN_RAMP_CONSENSUS_FLOOR)

    return DesignRamp(
        direction=direction, planes=planes, profile=profile, sigma=sigmas, tol=tol,
        channel=channel, r2=float(r2), plane_sigma=float(plane_sigma),
        inlier_frac=inlier_frac, lo=lo, hi=hi,
        sample_t=sample_t, sample_lab=sample_lab,
    )


def fit_design_ramp(design_prep: Prep, max_samples: int = DESIGN_RAMP_MAX_SAMPLES,
                    seed: int = DESIGN_RAMP_SAMPLE_SEED) -> DesignRamp | None:
    """The design ramp of a prepped design, or None. Fitted to the stitched
    foreground: `~bg_mask` less `enclosed_mask` (bg-coloured pixels not
    reachable from the border are unstitched by default and carry the
    background's colour, not the ramp's — letting them in is what broke the
    angle fit on its own repro in the first place, 2026-08-04)."""
    fg = ~design_prep.bg_mask
    enclosed = getattr(design_prep, "enclosed_mask", None)
    if enclosed is not None:
        fg = fg & ~enclosed
    return fit_design_ramp_pixels(design_prep.rgb, fg, design_prep.px_per_mm,
                                  max_samples=max_samples, seed=seed)
