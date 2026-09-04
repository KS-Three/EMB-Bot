"""The design ramp: one colour sweep — linear, or radial since 2026-09-04 —
fitted to a gradient-class design's whole stitched foreground, robust to
the artwork sitting on it.

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
`gradient_ramp_radial` linear 0.00 (radial 0.91 about the centroid).

**The radial ramp (2026-09-04).** A sweep can be rings as well as a plane:
`gradient_ramp_radial` is a disc light at its centre, and until the radial
fit existed the design declined (linear 0.00), stage 2 cut the disc into a
4,069 mm² ring and a 924 mm² core, the ring was refused by the per-region
fit (`speckled`) and sewed flat in one thread, and the core got three rings
of its own — 81% of the sweep lost its gradient. The radial model is
`val ~ p*r + q`, r the distance from a centre that is FITTED, not the
centroid: `_radial_center_gn` is Gauss-Newton on (cx, cy, p, q) from the
centroid, each centre step capped at 20 mm, and `_consensus_radial` mirrors
`_consensus_plane` — fit all, keep the nearest 75%, refit the CENTRE and the
line on the trimmed set (refitting the line alone reads the fixture's sigma
at 7–13 instead of 0.1), consensus at K sigma floored, refit. Its position
`raw` is the radius, so `t`, the profile, `rides`, `flatten_lab` and stage
6's band clip are the same code; `row_angle_deg` is 0.0 (rows cross the
rings, level being the answer that does not look like a mistake), and
`shifted` moves the centre while the radii stay.

**Radial beats linear only outright, under its own gate.** The plane's
gate is unchanged and runs first; the best passing radial fit replaces the
best passing plane only when its r² is strictly higher, so every linear
design is byte for byte what it was. The radial gate reuses the fraction,
scatter and span floors and adds three of its own: r² ≥ 0.6 (a line about
a free centre has a whole extra point to land on), the centre NEAR the
design on the sweep's own scale — refused when the foreground starts
farther from the centre than the sweep is long, `lo > hi - lo` (a plane
is a radial ramp whose centre sits at infinity — Gauss-Newton walks it off
the design; a bounding box would also refuse a half-disc sunrise or a
corner glow, whose centre sits ON the edge), and at most 2 BLANK knots of
the 17 profile bins along the radius (a bin under half in the consensus):
the sweep must be present all along the radius, not only in its rings.
Measured 2026-09-04 at Studio defaults, best channel, consensus r² /
inlier fraction / sigma / span, then the gate's verdict:

    gradient_ramp_radial   L 0.999 / 0.99 / 0.37 / 62.6  centre (78.2, 50.8)
                           on the disc's, 0 blank        PASS — 5 shades
    gradient_ramp_linear   L 0.999 / 1.00 / 0.50 / 63.0  centre 1,250 mm out,
                           lo 15x the sweep              center_far
    repro (white icon)     L 0.787 / 0.78 / 2.23 / 18.4  centre 360 mm out,
                           lo 4x the sweep               center_far
    summit_badge           L 0.931 / 0.74 / 1.99 / 40.7  10 of 17 blank:
                           the emblem IS the centre      knots
    owl_kent               L 0.447                       r2
    region_blobs           a 0.543 (sigma 10.7)          r2
    logo_golden_tee        L 0.358                       r2
    logo_bridge_bar        b 0.384                       r2
    screenshot_phone_ui    L 0.259                       r2
    drone_render           b 0.178                       r2
    logo_gaulke_roofing    a 0.044                       r2
    logo_hotel_fremont     a 0.014                       r2

The linear fixture and the repro come out of the fit byte-identical to the
linear-only module (every field, `flatten_lab`, `shifted` — compared
against the previous revision); every design listed refused stays refused.
The radial fixture at 80 mm / left chest: 2 regions → 1, 4 blocks → 5,
the whole disc sewn as the design's rings. A synthetic sweep that goes
FLAT at the rim on a square foreground is refused on knots (4 of 17 blank
in the flat corners) — the gate reads "no sweep here" the same way for a
flat corner as for a flat emblem.

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

# --- The radial gate (2026-09-04) ---------------------------------------------
#
# A radial ramp (`val ~ p*r + q`, r the distance from a FITTED centre) shares
# the plane's fraction, scatter and span gates and adds three of its own; a
# radial ramp wins only by passing all of them AND beating the best plane's
# r² outright (see `fit_design_ramp_pixels`).
#
# r² floor above the plane's 0.4: a line in radius about a free centre has a
# whole extra point to land on, and the busy fixtures reach higher radial r²
# than linear. The module docstring's table has the measured spread.
DESIGN_RAMP_RADIAL_R2_MIN = 0.6
# The sweep must be PRESENT along the whole radius, not only in its rings:
# of the `DESIGN_RAMP_PROFILE_KNOTS` bins of t (the same bins the profile
# is read in), one whose consensus fraction — consensus samples over all
# samples landing in it — is under this is BLANK, and more than
# `_MAX_BLANK_KNOTS` blank bins refuses. `summit_badge`'s emblem IS its
# centre, so its L* line fits the ring around it (r² clears the floor) with
# 10 of 17 bins blank; the radial fixture blanks 0; a concentric ring icon
# 3 mm wide drawn on the sweep blanks exactly 1 (`test_design_ramp`), which
# is what the allowance of 2 is for. A bin no sample reaches reads 0.
DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC = 0.5
DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS = 2
# The centre must be NEAR the design, on the sweep's own scale: refused
# when the foreground starts farther from the centre than the sweep is
# long (`lo > hi - lo`, lo/hi the foreground's radius range about it). A
# LINEAR sweep is a radial one whose centre sits at infinity, and the
# Gauss-Newton centre of a plane runs off the design — `gradient_ramp_linear`
# lands 1,250 mm out (lo 15x the sweep), the repro 360 mm (4x) — so this
# is what keeps a radial model from ever claiming a plane it fits by a
# hair. NOT a bounding-box test (review, 2026-09-04): a sweep's centre can
# sit ON the foreground's edge — a half-disc sunrise, a quarter-disc corner
# glow, common logo classes — and the fitted centre then lands a hundredth
# of a millimetre either side of it; the box refused both (the corner
# glow fell to the plane, r² 0.94, and got straight diagonal bands). A
# half-disc, a corner glow, an annulus and a spotlight all keep lo small.
# Gauss-Newton on the centre: at most this many iterations per pass, each
# centre step capped at this many mm — so a runaway centre moves at most
# ITERS x CAP = 600 mm per pass, 1,800 mm over `_consensus_radial`'s three
# passes: far enough to fail the scale test, never to NaN.
DESIGN_RAMP_RADIAL_GN_ITERS = 30
DESIGN_RAMP_RADIAL_STEP_CAP_MM = 20.0

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


# --- The radial fit (2026-09-04) ------------------------------------------------

def _radial_center_gn(mm_x: np.ndarray, mm_y: np.ndarray, val: np.ndarray,
                      c0: tuple[float, float],
                      iters: int = DESIGN_RAMP_RADIAL_GN_ITERS,
                      step_cap_mm: float = DESIGN_RAMP_RADIAL_STEP_CAP_MM
                      ) -> tuple[float, float]:
    """The least-squares centre of `val ~ p*r + q`, r the distance from it:
    Gauss-Newton on (cx, cy, p, q) from `c0`, the centre's step capped at
    `step_cap_mm`, and (p, q) re-solved exactly (they are linear given the
    centre) after every step. Stops when the centre settles. A plane has no
    finite centre — Gauss-Newton then walks it away at the cap each step,
    which is what the scale gate in `_radial_fits` reads."""
    cx, cy = float(c0[0]), float(c0[1])
    ones = np.ones_like(val)

    def line(cx: float, cy: float) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
        dx, dy = mm_x - cx, mm_y - cy
        r = np.maximum(np.hypot(dx, dy), 1e-9)
        p, q = _plane(np.column_stack([r, ones]), val)
        return dx, dy, r, float(p), float(q)

    dx, dy, r, p, q = line(cx, cy)
    for _ in range(iters):
        e = val - (p * r + q)
        jac = np.column_stack([p * dx / r, p * dy / r, -r, -ones])
        step, *_ = np.linalg.lstsq(jac, -e, rcond=None)
        mag = math.hypot(step[0], step[1])
        if mag > step_cap_mm:
            step = step * (step_cap_mm / mag)
            mag = step_cap_mm
        cx, cy = cx + float(step[0]), cy + float(step[1])
        dx, dy, r, p, q = line(cx, cy)
        if mag < 1e-4:
            break
    return cx, cy


def _consensus_radial(mm_x: np.ndarray, mm_y: np.ndarray, val: np.ndarray,
                      c0: tuple[float, float]
                      ) -> tuple[tuple[float, float], np.ndarray, np.ndarray, float, float]:
    """`_consensus_plane` for the radial model: fit all, keep the
    `DESIGN_RAMP_TRIM_FRAC` nearest, refit the CENTRE and the line on the
    trimmed set, admit everything within K robust sigmas (floored), refit.
    -> (center, (p, q), consensus mask, r² on the consensus, robust sigma).
    The centre is refitted at every pass, not only the line: refitting the
    line alone on the trimmed set, about the all-sample centre, reads the
    radial fixture's sigma at 7–13 Lab units instead of 0.1."""
    def fit(sel: np.ndarray, c: tuple[float, float]):
        center = _radial_center_gn(mm_x[sel], mm_y[sel], val[sel], c)
        r = np.hypot(mm_x - center[0], mm_y - center[1])
        a = np.column_stack([r, np.ones_like(r)])
        return center, _plane(a[sel], val[sel]), a

    center, coef, a = fit(np.ones(len(val), bool), c0)
    res = np.abs(val - a @ coef)
    keep = res <= np.quantile(res, DESIGN_RAMP_TRIM_FRAC)
    center, coef, a = fit(keep, center)
    res = np.abs(val - a @ coef)
    sigma0 = _MAD_TO_SIGMA * float(np.median(res[keep]))
    cons = res <= max(DESIGN_RAMP_CONSENSUS_K * sigma0, DESIGN_RAMP_CONSENSUS_FLOOR)
    center, coef, a = fit(cons, center)
    pred = a[cons] @ coef
    r2 = _r2(val[cons] - pred, val[cons])
    sigma = _MAD_TO_SIGMA * float(np.median(np.abs(val[cons] - pred)))
    return center, coef, cons, r2, sigma


def _blank_knots(t: np.ndarray, cons: np.ndarray, knots: int) -> int:
    """How many of the `knots` bins of t (binned as `_profile` bins them)
    hold under `DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC` of their samples in the
    consensus — bins the sweep is not in. A bin no sample reaches counts."""
    bins = np.minimum((t * (knots - 1) + 0.5).astype(int), knots - 1)
    n_all = np.bincount(bins, minlength=knots)
    n_cons = np.bincount(bins[cons], minlength=knots)
    frac = n_cons / np.maximum(n_all, 1)
    return int(np.sum(frac < DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC))


RADIAL_OK = ""
RADIAL_REJECT_R2 = "r2"
RADIAL_REJECT_INLIER_FRAC = "inlier_frac"
RADIAL_REJECT_SIGMA = "sigma"
RADIAL_REJECT_SPAN = "span"
RADIAL_REJECT_CENTER = "center_far"
RADIAL_REJECT_KNOTS = "knots"


@dataclass(frozen=True)
class RadialFit:
    """One Lab channel's radial fit and what its gate made of it. What the
    module docstring's fixture table is measured with, and what a test
    asserts a refusal's REASON on; `fit_design_ramp_pixels` takes the best
    passing one. Positions are mm in the fitted frame."""

    channel: int
    center: tuple[float, float]
    coef: np.ndarray          # (p, q): val ~= p * r + q on the consensus
    cons: np.ndarray          # (N,) bool, the consensus over the sample
    r2: float                 # on the consensus
    inlier_frac: float        # consensus / sample
    sigma: float              # robust scatter around the line, consensus set
    span: float               # max - min of the line's prediction over the consensus
    lo: float                 # radius range of the WHOLE stitched foreground about `center`
    hi: float
    center_near: bool         # the foreground starts no farther from the centre than the sweep is long (lo <= hi - lo)
    blank_knots: int          # bins of t the sweep is not in (`_blank_knots`)
    reason: str               # RADIAL_OK, or the first gate that refused

    @property
    def passes(self) -> bool:
        return self.reason == RADIAL_OK


def _sample_foreground(fg: np.ndarray, px_per_mm: float, max_samples: int, seed: int):
    """-> (all_xs, all_ys, mm_x, mm_y, xs, ys) — every foreground pixel, and
    the deterministic subsample the fits read (mm and px). None under 12."""
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
    return all_xs, all_ys, mm_x, mm_y, xs, ys


def _radial_fits(mm_x: np.ndarray, mm_y: np.ndarray, lab: np.ndarray,
                 all_mm_x: np.ndarray, all_mm_y: np.ndarray) -> list[RadialFit]:
    """Every channel's radial fit, gated. `all_mm_*` is the whole stitched
    foreground: its radius range about the centre is the ramp's [lo, hi],
    and the same range is the centre's scale test (`lo <= hi - lo`)."""
    c0 = (float(mm_x.mean()), float(mm_y.mean()))
    out = []
    for c in range(3):
        center, coef, cons, r2, sigma = _consensus_radial(mm_x, mm_y, lab[:, c], c0)
        frac = float(cons.mean())
        r = np.hypot(mm_x - center[0], mm_y - center[1])
        pred = coef[0] * r[cons] + coef[1]
        span = float(pred.max() - pred.min()) if cons.any() else 0.0
        r_all = np.hypot(all_mm_x - center[0], all_mm_y - center[1])
        lo, hi = float(r_all.min()), float(r_all.max())
        near = lo <= hi - lo
        t = np.clip((r - lo) / max(1e-9, hi - lo), 0.0, 1.0)
        blank = _blank_knots(t, cons, DESIGN_RAMP_PROFILE_KNOTS)
        if r2 < DESIGN_RAMP_RADIAL_R2_MIN:
            reason = RADIAL_REJECT_R2
        elif frac < DESIGN_RAMP_MIN_INLIER_FRAC:
            reason = RADIAL_REJECT_INLIER_FRAC
        elif sigma > DESIGN_RAMP_MAX_SIGMA:
            reason = RADIAL_REJECT_SIGMA
        elif span < DESIGN_RAMP_MIN_SPAN:
            reason = RADIAL_REJECT_SPAN
        elif not near:
            reason = RADIAL_REJECT_CENTER
        elif blank > DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS:
            reason = RADIAL_REJECT_KNOTS
        else:
            reason = RADIAL_OK
        out.append(RadialFit(channel=c, center=(float(center[0]), float(center[1])),
                             coef=coef, cons=cons, r2=float(r2), inlier_frac=frac,
                             sigma=float(sigma), span=span, lo=lo, hi=hi,
                             center_near=near, blank_knots=blank, reason=reason))
    return out


def radial_candidates(rgb: np.ndarray, fg: np.ndarray, px_per_mm: float,
                      max_samples: int = DESIGN_RAMP_MAX_SAMPLES,
                      seed: int = DESIGN_RAMP_SAMPLE_SEED) -> list[RadialFit]:
    """The three channels' radial fits of the `fg` pixels of `rgb`, on the
    same sample `fit_design_ramp_pixels` reads — the diagnostic behind the
    docstring's table and the refusal-reason tests. Empty under 12 pixels."""
    sample = _sample_foreground(fg, px_per_mm, max_samples, seed)
    if sample is None:
        return []
    all_xs, all_ys, mm_x, mm_y, xs, ys = sample
    lab = rgb_to_lab(rgb[ys, xs]).astype(np.float64)
    return _radial_fits(mm_x, mm_y, lab, all_xs.astype(np.float64) / px_per_mm,
                        all_ys.astype(np.float64) / px_per_mm)


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
    """One colour sweep across a design — linear along `direction`, or radial
    about `center` (`kind`). Immutable; `shifted` makes the frame-changed
    copy. Positions are mm in the frame the ramp was fitted (or shifted)
    into. Everything colour reads the ramp position `t`, which `raw` alone
    makes kind-specific; only `raw`, `row_angle_deg` and `shifted` branch."""

    direction: tuple[float, float] | None  # linear: unit vector along the sweep (y down); None for radial
    planes: np.ndarray               # (3, 3): per Lab channel, the gate's model — linear val ~= a*x + b*y + c; radial (p, q, 0), val ~= p*r + q
    profile: np.ndarray              # (3, KNOTS): the colour along the sweep at equal steps of t
    sigma: np.ndarray                # (3,) robust residual scatter per channel around the profile, consensus set
    tol: np.ndarray                  # (3,) per-channel riding tolerance (K sigma, floored)
    channel: int                     # the Lab channel whose model won (0 L, 1 a, 2 b)
    r2: float                        # its r² on the consensus
    plane_sigma: float               # its robust scatter around the plane (radial: the line) — what the gate judged
    inlier_frac: float               # consensus / stitched foreground samples
    lo: float                        # range of `raw` over the WHOLE stitched foreground: projection along `direction`, or radius about `center`
    hi: float
    sample_t: np.ndarray             # (K,) ramp position of every consensus sample
    sample_lab: np.ndarray           # (K, 3) its Lab
    kind: str = "linear"             # "linear" | "radial"
    center: tuple[float, float] | None = None  # radial: the centre (mm, this frame); None for linear

    # -- geometry ---------------------------------------------------------------

    @property
    def span_mm(self) -> float:
        return self.hi - self.lo

    def row_angle_deg(self) -> float:
        """The shared fill-row angle: rows run along the ramp's iso-colour lines,
        perpendicular to `direction`. A line, not a ray — the sign is moot.
        A radial ramp's iso-lines are rings, which no row runs along; its
        rows are LEVEL (0.0) — the answer that does not look like a mistake,
        and the one `stage6_fill.principal_angle_deg` gives a disc."""
        if self.kind == "radial":
            return 0.0
        ux, uy = self.direction
        return math.degrees(math.atan2(ux, -uy))

    def raw(self, x, y):
        """Position along the sweep before normalisation: the projection on
        `direction`, or the distance from `center`. Vectorized."""
        if self.kind == "radial":
            cx, cy = self.center
            return np.hypot(np.asarray(x, dtype=float) - cx, np.asarray(y, dtype=float) - cy)
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
        projection range move with the origin. A radial ramp's centre moves
        with it instead, and its radii — `lo`, `hi`, the line in `planes` —
        are what they were, a distance being frame-invariant."""
        if self.kind == "radial":
            cx, cy = self.center
            return replace(self, center=(cx - dx, cy - dy))
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

    def _raw_grid(self, w: int, h: int, px_per_mm: float) -> np.ndarray:
        """(H, W) `raw` at every pixel centre of a w x h raster, positions
        `px / px_per_mm` — built as one broadcast, not a per-pixel call."""
        xs = np.arange(w, dtype=np.float64) / px_per_mm
        ys = np.arange(h, dtype=np.float64) / px_per_mm
        if self.kind == "radial":
            cx, cy = self.center
            return np.hypot((xs - cx)[None, :], (ys - cy)[:, None])
        ux, uy = self.direction
        return (ux * xs)[None, :] + (uy * ys)[:, None]

    def flatten_lab(self, lab_img: np.ndarray, px_per_mm: float) -> np.ndarray:
        """(H, W, 3) Lab with the sweep subtracted: every pixel reads as the
        ramp's mid colour plus its own departure from the profile at its
        position. Positions are `px / px_per_mm`, so this is only meaningful
        in the fitted (stage 1) frame — stage 2's."""
        h, w = lab_img.shape[:2]
        t = np.clip((self._raw_grid(w, h, px_per_mm) - self.lo) / max(1e-9, self.hi - self.lo), 0.0, 1.0)
        at_mid = self.colour_at(0.5)
        sweep = self.colour_at(t)
        return lab_img.astype(np.float64) - sweep + at_mid[None, None, :]


def _colour_model(sample_t: np.ndarray, sample_lab: np.ndarray
                  ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """-> (profile, sigma, tol): the colour along the sweep, the consensus
    samples' robust scatter around it per channel, and the riding tolerance."""
    profile = _profile(sample_t, sample_lab, DESIGN_RAMP_PROFILE_KNOTS)
    grid = np.linspace(0.0, 1.0, DESIGN_RAMP_PROFILE_KNOTS)
    sigmas = np.zeros(3, np.float64)
    for c in range(3):
        res = np.abs(sample_lab[:, c] - np.interp(sample_t, grid, profile[c]))
        sigmas[c] = _MAD_TO_SIGMA * float(np.median(res))
    tol = np.maximum(DESIGN_RAMP_CONSENSUS_K * sigmas, DESIGN_RAMP_CONSENSUS_FLOOR)
    return profile, sigmas, tol


def _radial_ramp(fit: RadialFit, mm_x: np.ndarray, mm_y: np.ndarray,
                 lab: np.ndarray) -> DesignRamp | None:
    """The DesignRamp of a passing radial fit: every channel's line in radius
    on the winning consensus (as `planes` rows (p, q, 0)), the profile along
    the radius, the range being the whole foreground's radii."""
    cx, cy = fit.center
    cons = fit.cons
    if fit.hi - fit.lo <= 1e-6:
        return None
    r = np.hypot(mm_x[cons] - cx, mm_y[cons] - cy)
    a_r = np.column_stack([r, np.ones_like(r)])
    planes = np.zeros((3, 3), np.float64)
    for c in range(3):
        planes[c, :2] = _plane(a_r, lab[cons, c])
    sample_t = np.clip((r - fit.lo) / (fit.hi - fit.lo), 0.0, 1.0)
    sample_lab = lab[cons]
    profile, sigmas, tol = _colour_model(sample_t, sample_lab)
    return DesignRamp(
        direction=None, planes=planes, profile=profile, sigma=sigmas, tol=tol,
        channel=fit.channel, r2=float(fit.r2), plane_sigma=float(fit.sigma),
        inlier_frac=fit.inlier_frac, lo=fit.lo, hi=fit.hi,
        sample_t=sample_t, sample_lab=sample_lab,
        kind="radial", center=(cx, cy),
    )


def fit_design_ramp_pixels(rgb: np.ndarray, fg: np.ndarray, px_per_mm: float,
                           max_samples: int = DESIGN_RAMP_MAX_SAMPLES,
                           seed: int = DESIGN_RAMP_SAMPLE_SEED) -> DesignRamp | None:
    """Fit the ramp to the `fg` pixels of `rgb` (both (H, W[, 3]), fg True =
    stitched foreground). None when the gate refuses — see the module
    docstring for what each of its numbers turns away.

    Linear first, radial second, and radial beats linear only outright: the
    best plane among the channels passing the plane's gate is the linear
    candidate; the best radial fit among the channels passing the radial
    gate (`_radial_fits`) wins instead only when its r² strictly beats that
    plane's (or there is no passing plane). A linear design is therefore
    untouched by the radial fit's existence — same plane, same profile, byte
    for byte — and a design that fits neither is refused as before. The
    linear winner still faces the centroid-radial check below, which turns
    away a ring-shaped sweep the radial gate itself refused."""
    sample = _sample_foreground(fg, px_per_mm, max_samples, seed)
    if sample is None:
        return None
    all_xs, all_ys, mm_x, mm_y, xs, ys = sample
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

    # The radial model (2026-09-04): its own gate, and it must beat the plane.
    radial = [f for f in _radial_fits(mm_x, mm_y, lab, all_xs.astype(np.float64) / px_per_mm,
                                      all_ys.astype(np.float64) / px_per_mm) if f.passes]
    if radial:
        top = max(radial, key=lambda f: f.r2)
        if best is None or top.r2 > best[3]:
            return _radial_ramp(top, mm_x, mm_y, lab)
    if best is None:
        return None
    channel, coef, cons, r2, plane_sigma, inlier_frac = best
    # A sweep, not rings: the same channel on the same consensus must not be
    # explained better by distance from the centroid (the radial fixture's
    # linear r² is 0.00 against radial 0.91). Still the answer for a ring
    # sweep the radial gate refused (too few knots, a centre off the design).
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
    profile, sigmas, tol = _colour_model(sample_t, sample_lab)

    return DesignRamp(
        direction=direction, planes=planes, profile=profile, sigma=sigmas, tol=tol,
        channel=channel, r2=float(r2), plane_sigma=float(plane_sigma),
        inlier_frac=inlier_frac, lo=lo, hi=hi,
        sample_t=sample_t, sample_lab=sample_lab,
    )


def stitched_foreground(design_prep: Prep) -> np.ndarray:
    """(H, W) bool: the pixels the ramp is fitted to — `~bg_mask` less
    `enclosed_mask` (bg-coloured pixels not reachable from the border are
    unstitched by default and carry the background's colour, not the
    ramp's — letting them in is what broke the angle fit on its own repro
    in the first place, 2026-08-04)."""
    fg = ~design_prep.bg_mask
    enclosed = getattr(design_prep, "enclosed_mask", None)
    if enclosed is not None:
        fg = fg & ~enclosed
    return fg


def fit_design_ramp(design_prep: Prep, max_samples: int = DESIGN_RAMP_MAX_SAMPLES,
                    seed: int = DESIGN_RAMP_SAMPLE_SEED) -> DesignRamp | None:
    """The design ramp of a prepped design, or None. Fitted to
    `stitched_foreground`."""
    return fit_design_ramp_pixels(design_prep.rgb, stitched_foreground(design_prep),
                                  design_prep.px_per_mm, max_samples=max_samples, seed=seed)
