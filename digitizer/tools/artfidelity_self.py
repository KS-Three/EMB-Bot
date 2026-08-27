"""Does OUR stitch-out look like the artwork? No professional reference.

The pro-parity family all measure EMB-Bot against somebody else's file:
`scorecard.py` grades us on similarity to one professional rendition,
`selfconsistency.py` measures how much two professionals disagree with each
other, and `artfidelity.py` asks how faithfully the PRO reproduced the
customer's art. Every one of them needs a professional file to exist for the
design in hand, and every one of them inherits that professional's discretion
as part of the yardstick.

This is the missing cell in that matrix: picture in, thread out, nothing else.
It asks the question ROADMAP phase 1 is actually phrased in terms of — does
the metric's ranking agree with Kent's eye — on any artwork at all, including
the twelve fixtures no professional ever digitized.

Three components, each 0..1, each measuring something the others cannot:

    coverage   registered ink IoU — is thread where the ink is?
    colour     median CIEDE2000 excess over the best AVAILABLE spool, per
               REGION — was each shape put on the best thread the chart had?
    structure  multi-scale SSIM over the ink/thread coverage fields — does it
               have the same shape at every scale, not just the same area?

    ARTFID = 100 * (0.40*coverage + 0.25*colour + 0.35*structure)

## Provenance — read this before quoting a number against the artifact

This file was REBUILT on 2026-08-27. The original was written the previous
session, validated into an artifact, and lost with its container before it was
ever pushed; the artifact survived and is the only record.

Recovered exactly from that artifact:
  * the three component definitions (its own footer prose, quoted above);
  * the composite weights. Least squares over the 14 published rows returns
    0.3986 / 0.2498 / 0.3517, sum 1.0001, max residual 0.08 on a 0-100 scale
    — entirely explained by the artifact rounding components to 3 decimals and
    the composite to 1. 0.40 / 0.25 / 0.35 reproduces all 14 rows to within
    0.08. That is a recovery, not a guess.
  * the two refusal classes, and which fixtures fall in them.

A THIRD refusal class was added 2026-08-27, after the rebuild shipped and was
not in the artifact at all: `INK_SATURATION_MAX`. `summit_badge` is a badge on
a dark grey vignette backdrop, and the opaque-art ink rule calls that backdrop
ink too — 100.0% of the frame. Coverage became an IoU against all-ones, which
rewarded the engine for sewing a background stage 1 was right to remove, and
the row was ranked 7th of 9 on the strength of it. The artifact's own table
scored that fixture too, so its 69.1 there is subject to the same defect. Found
by sweeping `bg_tolerance_lab` and chasing why one fixture moved 16.8 points.

NOT recoverable, and therefore STATED CHOICES here, each flagged at its
constant: the ink-mask threshold, the registration window and step, the SSIM
scale count and window, the colour scale constant, and the subject-mismatch
cut. They are chosen to match the sibling probes in this directory's parent
where a sibling has already settled them, and are marked judgement where no
sibling has.

**So the artifact's table is a historical record, not a reproduction target.**
This build's numbers may differ from it, and where they do, the difference is
this rebuild's free parameters and not a change in the engine. Do not report a
delta against that table as an engine regression or an engine gain. The first
run of this file establishes a NEW baseline; comparisons start there.

## The composite is provisional, and hard gate 4 is why

ROADMAP hard gate 4 refuses a quality claim on a raw agreement number. A single
blended 0-100 is exactly the shape that gate distrusts: the weights decide the
ranking, and nothing has yet earned them except that they reproduce the table
they were solved from. `--components` prints the three separately and is the
honest default for anything that has to survive scrutiny; the composite exists
because a ranking needs one sortable column, and it stays provisional until
Kent's marks on the validation artifact either confirm the order or change it.

Usage:
    python -m tools.artfidelity_self <image> [<image> ...]
    python -m tools.artfidelity_self --all          # the tracked fixture set
    python -m tools.artfidelity_self --all --csv out.csv
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from skimage.color import deltaE_ciede2000
from skimage.metrics import structural_similarity

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402
from digitizer_core.preflight import (DELTA_E_CLEARLY_DIFFERENT,  # noqa: E402
                                      _region_color_errors, run_preflight)
from digitizer_core.stage1_prep import prep  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402
from digitizer_core.threads import chart_for  # noqa: E402

# --------------------------------------------------------------------------
# Constants. Every one of these was a free parameter in the lost original.
# --------------------------------------------------------------------------

RES = 10.0
# px per mm for every raster this file compares. NOT a free choice: the sibling
# probes in tools/pro_parity (artfidelity.py, bare.py, holecrop.py,
# forkprobe.py) all rasterise at 10.0, and artfidelity.py's THREAD_W_MM comment
# is explicit that a probe which drifts off the family constant stops agreeing
# with the others about what "covered" means. Keep in step or move all of them.

SHIFT_MM = 4.0
SHIFT_STEP_MM = 0.4
# Registration search half-window and step, copied from artfidelity.py's
# `best_iou` so that a coverage number here and a coverage number there are
# registered the same way. Translation only — like the scorecard, this never
# rescales, because a rescaling registration would hide a size error as a
# alignment success.

WEIGHTS = (0.40, 0.25, 0.35)   # coverage, colour, structure
# Recovered by least squares over the validation artifact's 14 rows; see the
# module docstring. Provisional in the sense that gate 4 means: they reproduce
# the table they were solved from and have earned nothing else yet.

COLOUR_SCALE_DE = DELTA_E_CLEARLY_DIFFERENT   # 10.0
# The median excess that drives `colour` to 0. JUDGEMENT, not measurement —
# but not an arbitrary one: preflight already calls 10.0 the point where two
# colours are CLEARLY DIFFERENT rather than merely visibly so, and a component
# that bottoms out exactly where the shipped instrument stops splitting hairs
# is at least consistent with the rest of the codebase.
#
# Do NOT read this constant as recovered. Fourteen rounded rows cannot pin it,
# and the rebuilt colour column measurably does NOT track the artifact's on the
# mildly-tonal designs — see the module docstring's provenance section. The
# scale is a stated choice; the artifact's column is not evidence for it.

SSIM_SCALES = 4
SSIM_WIN = 7
# Multi-scale SSIM: `SSIM_SCALES` octaves, each a 2x box-area downsample of
# the last, arithmetic mean over the scales that fit. JUDGEMENT. The classic
# Wang MS-SSIM weighting is deliberately NOT used: its five exponents are
# fitted to human ratings of natural-image distortion, and thread on cloth is
# neither. An unweighted mean says plainly "agree at every scale we can
# measure" and has no fitted constants to misattribute a result to. Scales
# whose smaller side cannot hold a `SSIM_WIN` window are skipped, not padded —
# padding invents structure where the pyramid ran out.

_FLOOR_SAMPLE_PX = 512
# Pixels per REGION used to search the chart for that region's floor. The floor
# is a median over the region's pixels and converges long before its full
# sample: preflight hands us up to 4096 px a region, and 4096 x 398 spools x a
# photo's worth of regions is minutes of CIEDE2000 for a digit that does not
# move. Taken as a fixed stride (`np.linspace`), not a random draw, so the
# sample is a deterministic function of the image — this instrument has no seed
# to carry, and a metric that moves between two runs of one input cannot be a
# baseline. The SAME subsample scores the assigned thread and the floor, so the
# two are always commensurable and the excess can never come out negative
# through a sampling mismatch.

INK_SATURATION_MAX = 0.90
# Refusal: the fraction of the FRAME that `art_ink_field` calls ink. At the
# top of this range the mask has not separated ink from ground, and `coverage`
# — an IoU against a mask that is almost all ones — degenerates into "what
# fraction of the canvas did you sew", which is not fidelity. `structure` reads
# the same field, so the whole row goes with it.
#
# Found 2026-08-27, the day after this file shipped, by chasing a 16.8-point
# ARTFID step on `summit_badge`. That fixture is a badge on a DARK GREY
# VIGNETTE BACKDROP, and `art_ink_field`'s opaque-art rule (mean RGB < 240)
# calls the backdrop ink too — 100.0% of the frame. Stage 1 removes that
# backdrop, correctly; coverage then charges us 21 points for it, and rewards
# any setting that sews the backdrop instead. The metric was upside down on
# that row, and it was ranked 7th of 9 on the strength of it.
#
# JUDGEMENT, with room on both sides rather than a fitted cut: measured over
# the tracked set, legitimate fixtures run 4.7%-62.9% and `summit_badge` is
# 100.0%. (`logo_gaulke_roofing` reads 84.7% but is already refused as a
# subject mismatch.) A genuinely full-bleed artwork would also land here, and
# would also be unscoreable by ink IoU for the same reason — so refusing is
# right in both cases, not just the broken-mask one.
#
# Deliberately NOT defined as "the mask disagrees with the engine's own
# background decision", which is the sharper-looking test: it would make the
# instrument refuse to score exactly the designs where stage 1 wrongly floods,
# hiding the defect class hard gate 3 exists to keep visible. This criterion
# reads the artwork alone and asks nothing of the engine.

MISMATCH_MAX = 3.0
# Refusal: ink area vs sewn area, larger over smaller. Above this the mask and
# the engine are not looking at the same picture and no component on the row
# means anything. JUDGEMENT. The artifact's one subject-mismatch row measured
# 5.1x, and every scored row sits far below 3.0, so the cut separates the
# observed populations with room on both sides; it is not fitted to them.

# The tracked fixture set, in the artifact's own order. Paths are relative to
# `digitizer/testdata`.
FIXTURES = (
    "bg_uncertain.png",
    "logo_alpha.png",
    "logo_whitebg.png",
    "ribbon_curve.png",
    "logo_script_tires.png",
    "becker_marine_logo.png",
    "photo/enthusiast_logo.png",
    "photo/summit_badge.png",
    "photo/region_blobs.png",
    "photo/logo_hotel_fremont.webp",
    "photo/logo_bridge_bar.jpg",
    "photo/drone_render.png",
    "photo/logo_golden_tee.jpg",
    "photo/logo_gaulke_roofing.png",
)


# --------------------------------------------------------------------------
# Artwork side
# --------------------------------------------------------------------------

def art_ink_field(art_path: str | Path, width_mm: float) -> np.ndarray:
    """Artwork ink as a 0..1 field, its ink bbox rasterised `width_mm` wide.

    Lifted from `pro_parity/artfidelity.py:art_mask` — same two-branch ink
    rule (alpha when the file carries one, else darkness), same sizing rule,
    which is stage1_prep's own: the design's physical width is the width of
    the art's FOREGROUND bbox, not of the file (stage1_prep.py:317-319).

    The one deliberate difference is that this returns a CONTINUOUS field
    rather than `artfidelity.py`'s boolean. INTER_AREA downsampling of a
    boolean gives real coverage fractions at the edges, and SSIM reads that
    anti-aliased boundary as the soft edge it physically is; thresholding it
    back to a hard mask would manufacture staircase structure that neither
    the artwork nor the thread has. `coverage` re-thresholds at 0.5 for its
    IoU, so the boolean reading is still available and still matches the
    sibling probe.
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    if len(xs) == 0:
        return np.zeros((1, 1), np.float64)
    ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    target_w = max(1, int(round(width_mm * RES)))
    scale = target_w / ink.shape[1]
    target_h = max(1, int(round(ink.shape[0] * scale)))
    out = cv2.resize(ink.astype(np.float32), (target_w, target_h),
                     interpolation=cv2.INTER_AREA).astype(np.float64)
    # INTER_AREA accumulates in float32 and overshoots a solid interior to
    # ~1.0000002. Harmless to look at, not harmless to use: `ms_ssim` passes
    # `data_range=1.0`, and a field outside its declared range makes that a
    # lie. `stitch_coverage_field` clamps for the same reason, so both sides
    # of every comparison are honestly 0..1.
    return np.clip(out, 0.0, 1.0)


def ink_saturation(art_path: str | Path) -> float:
    """Fraction of the FRAME that `art_ink_field`'s rule calls ink, 0..1.

    Measured on the uncropped image, before `art_ink_field` crops to the ink
    bbox — the crop is what hides this failure, because a mask that claims the
    whole frame crops to the whole frame and then looks like a perfectly
    ordinary solid design.
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    return float(ink.mean())


def ink_is_ambiguous(art_path: str | Path) -> bool:
    """Does `art_ink_field` know what the ink is here? Verbatim in criterion
    from `pro_parity/artfidelity.py:ink_is_ambiguous`, and for the same
    reason: a dark panel with light shapes KNOCKED OUT of it defeats both ink
    branches, so the engine is charged for a hole it was right to leave.

    That instrument's docstring carries the evidence (it drove a wrong
    attribution into a published doc on 2026-08-17). Reproduced here rather
    than imported because `tools/pro_parity` is a sibling package this file
    does not otherwise depend on, and a shared import would couple the two
    instruments' refusal behaviour — if one of them ever needs to change its
    mind about what ink is, the other should not silently follow.
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    lum = a[..., :3].astype(np.int32).mean(axis=2)[ink]
    if lum.size == 0:
        return False
    dark = float((lum < 96).mean())
    light = float((lum > 160).mean())
    return min(dark, light) > 0.15


# --------------------------------------------------------------------------
# Thread side
# --------------------------------------------------------------------------

def stitch_coverage_field(design: dict) -> np.ndarray:
    """Our stitches as a 0..1 coverage field at `RES` px/mm.

    The same two-render trick `stitchviz.coverage` uses for its scalar: render
    once on black cloth and once on white, and whatever still differs is cloth
    showing through. Partial (anti-aliased) coverage therefore counts
    partially, which that function's docstring argues is the physically honest
    reading — half a filament's width over a pixel hides half its cloth — and
    it is what makes this field directly comparable to `art_ink_field`'s.

    `lit=False` deliberately: the lit renderer shades a filament as a cylinder
    for the human eye, and that shading is a lighting model, not coverage.
    Measuring it would score us on how convincing the preview looks.
    """
    lo = render_design(design, px_per_mm=RES, fabric_bgr=(0, 0, 0),
                       lit=False).astype(np.int16)
    hi = render_design(design, px_per_mm=RES, fabric_bgr=(255, 255, 255),
                       lit=False).astype(np.int16)
    show_through = np.abs(hi - lo).max(axis=2) / 255.0
    return np.clip(1.0 - show_through, 0.0, 1.0).astype(np.float64)


# --------------------------------------------------------------------------
# Registration, shared by coverage and structure
# --------------------------------------------------------------------------

def _place(field: np.ndarray, H: int, W: int, dx: int = 0,
           dy: int = 0) -> np.ndarray:
    canvas = np.zeros((H, W), np.float64)
    oy = (H - field.shape[0]) // 2 + dy
    ox = (W - field.shape[1]) // 2 + dx
    canvas[oy:oy + field.shape[0], ox:ox + field.shape[1]] = field
    return canvas


def register(ours: np.ndarray, art: np.ndarray) -> tuple[float, np.ndarray,
                                                         np.ndarray, float,
                                                         float]:
    """Best whole-pixel shift of `art` onto `ours`, art centred to start.

    -> (iou, ours_placed, art_placed, dx_mm, dy_mm)

    Searched on the BOOLEAN reading of both fields at 0.5, exactly as
    `artfidelity.py:best_iou` searches its masks, so that the alignment this
    picks is the alignment that instrument would pick. The continuous fields
    are then placed at that same offset for SSIM — one registration serves
    both components, so `coverage` and `structure` can never disagree about
    where the design is.
    """
    pad = int(2 * SHIFT_MM * RES) + 4
    H = max(ours.shape[0], art.shape[0]) + pad
    W = max(ours.shape[1], art.shape[1]) + pad

    O_f = _place(ours, H, W)
    O_b = O_f >= 0.5
    o_count = int(np.count_nonzero(O_b))

    step = max(1, int(round(SHIFT_STEP_MM * RES)))
    span = int(SHIFT_MM * RES)
    best = (-1.0, 0, 0)
    for dy in range(-span, span + 1, step):
        for dx in range(-span, span + 1, step):
            A_b = _place(art, H, W, dx, dy) >= 0.5
            union = np.count_nonzero(O_b | A_b)
            if not union:
                continue
            iou = np.count_nonzero(O_b & A_b) / union
            if iou > best[0]:
                best = (iou, dx, dy)

    iou, dx, dy = best
    if o_count == 0 and iou < 0:
        iou = 0.0
    return (max(0.0, iou), O_f, _place(art, H, W, dx, dy),
            dx / RES, dy / RES)


def ms_ssim(a: np.ndarray, b: np.ndarray) -> float:
    """Arithmetic-mean SSIM over up to `SSIM_SCALES` octaves. See the constant
    for why the mean is unweighted and why short pyramids are truncated rather
    than padded. Both inputs are 0..1 fields on the same canvas."""
    vals: list[float] = []
    x, y = a, b
    for _ in range(SSIM_SCALES):
        if min(x.shape) < SSIM_WIN:
            break
        vals.append(float(structural_similarity(
            x, y, data_range=1.0, win_size=SSIM_WIN)))
        if min(x.shape) < 2 * SSIM_WIN:
            break
        x = cv2.resize(x, (x.shape[1] // 2, x.shape[0] // 2),
                       interpolation=cv2.INTER_AREA)
        y = cv2.resize(y, (y.shape[1] // 2, y.shape[0] // 2),
                       interpolation=cv2.INTER_AREA)
    if not vals:
        return 0.0
    return float(np.clip(sum(vals) / len(vals), 0.0, 1.0))


# --------------------------------------------------------------------------
# Colour
# --------------------------------------------------------------------------

def region_excess_over_best(lab_px: np.ndarray, assigned: int,
                            chart_lab: np.ndarray) -> float:
    """One region's median PER-PIXEL `deltaE(thread we sewed) - deltaE(that
    pixel's own best spool in the chart)`.

    The subtraction happens per pixel and the median is taken afterwards. That
    ordering is not a detail — it is the only version of this component that
    can fire at all, and getting it wrong is what the rebuild did twice on
    2026-08-27. All three readings are faithful to the artifact's phrase
    "median CIEDE2000 excess over the best available spool"; two of them are
    dead, and both are dead for the same reason — the floor was something the
    engine had already optimised, so the excess was zero by construction.

      1. **Floor = best spool the design ALREADY sews** (preflight's
         `_best_loaded_spool_error`). Identically zero: stage 4 has by then
         snapped every region to its nearest loaded spool, so the assigned
         thread IS the floor. That check is a rescoring escape — it suppresses
         a false THREAD_MATCH_POOR when a free swap was available and not
         taken — and read as a fidelity measure it calls every design perfect.
         Measured: colour 1.000 on all fourteen fixtures.

      2. **Floor = best SINGLE spool for the whole region**, i.e.
         `median(d_assigned) - min_spool median(d_spool)`. Also ~zero, for the
         same reason one step removed: picking the chart spool that best serves
         a region is exactly what stage 4 does. Measured: 1.000 on the tonal
         designs too, including `region_blobs`, which the artifact scored
         0.625.

      3. **Floor = each PIXEL's own best spool** — this one. A region is
         charged for the pixels its single assigned thread cannot serve *when
         a better thread for those pixels existed on the chart*. That is
         tonal-compression error, which is the thing the component is named
         for, and it is not something any stage of the pipeline has already
         minimised: one thread per region cannot be every pixel's best.

    A colour no thread reproduces is still not charged — the floor moves with
    the pixel, so an unrepresentable colour raises `d_assigned` and
    `d.min(axis=1)` together and cancels. The chart is 398 spools and the world
    is continuous; this measures our choice, never that gap.

    Per REGION rather than over pooled pixels, per `_region_color_errors`:
    each region is scored against its own pixels and its own spool, "never
    pooled across the regions sharing a thread. Pooling was this instrument's
    original sin" (documented twice in
    docs/photo-quality-root-cause-2026-08-11.md, measured on drone_render:
    pooled 9.2 -> 33.6 across a change whose per-region worst HALVED). Note
    what that ruling is actually about — collapsing a region's pixels to one
    summary COLOUR before measuring. Aggregating per-pixel ERRORS is not the
    same act, and preflight does it itself inside every region.

    Scored on a fixed-stride subsample (`_FLOOR_SAMPLE_PX`); assigned thread
    and floor read the same subsample, so the subtraction is always
    commensurable.
    """
    if len(lab_px) > _FLOOR_SAMPLE_PX:
        take = np.linspace(0, len(lab_px) - 1, _FLOOR_SAMPLE_PX).astype(np.int64)
        lab_px = lab_px[take]

    # (N, S) CIEDE2000 of every pixel against every spool.
    n, s_count = len(lab_px), len(chart_lab)
    d = deltaE_ciede2000(
        np.repeat(lab_px[:, None, :], s_count, axis=1).reshape(-1, 3),
        np.tile(chart_lab, (n, 1)),
    ).reshape(n, s_count)

    # Subtract PER PIXEL, then take the median of the excesses — not the
    # difference of two medians. That ordering is the whole component (see the
    # docstring): `d.min(axis=1)` is each pixel's OWN best spool, so a region
    # whose pixels want different threads is charged for the ones its single
    # assigned thread cannot serve. Taking medians first instead asks only
    # whether a better SINGLE spool existed for the whole region, which is the
    # question stage 4 already answered "no" to by construction.
    per_pixel_excess = d[:, assigned] - d.min(axis=1)
    return float(max(0.0, np.median(per_pixel_excess)))


def colour_score(image, result, cfg: PipelineConfig) -> tuple[float, float | None]:
    """-> (0..1 score, median per-region excess delta-E).

    For each region: how much worse is the spool we assigned it than the best
    spool the chart offered for its pixels? Median over regions, then
    `1 - median/COLOUR_SCALE_DE`, clamped.

    "The best AVAILABLE spool" is the whole point of the subtraction. A colour
    no thread reproduces is not an engine defect — the chart is 398 spools and
    the world is continuous — so this charges us only for the gap between what
    we chose and the best choice that existed. A flat spot-colour logo scores
    1.000 by construction: its regions ARE the best available spools for their
    pixels. Tonal artwork is where the number moves, because compressing a
    smooth ramp into a handful of cones puts regions on threads that
    demonstrably better threads were available for.

    Median over REGIONS, never over pooled pixels — see
    `region_excess_over_best` for the two ways the floor was got wrong first,
    and why pooling is this repo's settled anti-pattern rather than a taste
    call.

    Returns `(1.0, None)` when no region is scoreable — a design too small or
    too thin to sample cannot be charged for colour it was never measured on.
    """
    p = prep(image, cfg)
    rows = _region_color_errors(p, result, cfg)
    if not rows:
        return 1.0, None

    chart = chart_for(cfg)
    excess = [region_excess_over_best(r["_lab_px"], int(r["thread_index"]),
                                      chart.lab)
              for r in rows]
    median_excess = float(np.median(excess))
    score = float(np.clip(1.0 - median_excess / COLOUR_SCALE_DE, 0.0, 1.0))
    return score, median_excess


# --------------------------------------------------------------------------
# One design
# --------------------------------------------------------------------------

def score_image(image_path: str | Path,
                cfg: PipelineConfig | None = None) -> dict:
    """Digitize `image_path` and score the result against its own artwork.

    Every returned value is a plain Python scalar or string, safe at a JSON or
    CSV boundary. `refusal` is None on a scored row, or the reason this row
    must not be read as an engine result.
    """
    cfg = cfg or PipelineConfig()
    image_path = Path(image_path)

    result, plan = digitize(image_path, cfg)
    design = plan_to_design(plan)

    ours = stitch_coverage_field(design)
    art = art_ink_field(image_path, float(design["widthMM"]))

    coverage, O_f, A_f, dx_mm, dy_mm = register(ours, art)
    structure = ms_ssim(O_f, A_f)
    colour, median_excess = colour_score(image_path, result, cfg)

    composite = 100.0 * (WEIGHTS[0] * coverage
                         + WEIGHTS[1] * colour
                         + WEIGHTS[2] * structure)

    # Refusals. Both are reported WITH their components rather than in place of
    # them: the artifact showed refused rows so the refusals stayed visible,
    # and hiding a row is how a fixture set quietly shrinks to the ones that
    # flatter it. `mismatch` is checked first — when the two rasters are not
    # the same picture, "is the ink ambiguous" is not the interesting problem.
    ink_px = float((art >= 0.5).sum())
    sewn_px = float((ours >= 0.5).sum())
    saturation = ink_saturation(image_path)

    refusal = None
    mismatch = None
    if ink_px == 0 or sewn_px == 0:
        # One side is empty, so there is no ratio to report — an "inf x"
        # in the refusal text would read like a measurement. Say which side.
        refusal = ("nothing to compare: no ink found in the artwork"
                   if ink_px == 0 else
                   "nothing to compare: the engine sewed nothing")
    else:
        mismatch = max(ink_px, sewn_px) / min(ink_px, sewn_px)
        if mismatch > MISMATCH_MAX:
            refusal = f"subject mismatch, {mismatch:.1f}x"
        elif saturation > INK_SATURATION_MAX:
            # Checked before ambiguity: when the mask claims the whole frame
            # there is no ink/ground split for "is the ink ambiguous" to be a
            # question about.
            refusal = f"ink mask saturates the frame, {saturation:.0%}"
        elif ink_is_ambiguous(image_path):
            refusal = "ink ambiguous (knocked-out lettering)"

    pre = run_preflight(result, plan, cfg, image=image_path)

    return {
        "fixture": image_path.name,
        "route": result.design_class,
        "stitches": int(plan.stats.stitch_count),
        "preflight_grade": pre["grade"],
        "preflight_score": int(pre["score"]),
        "coverage": round(coverage, 3),
        "colour": round(colour, 3),
        "structure": round(structure, 3),
        "artfid": round(composite, 1),
        "median_excess_de": (None if median_excess is None
                             else round(median_excess, 2)),
        # Two scalar columns rather than one list: this dict goes straight to
        # `csv.DictWriter` for the CI baseline artifact, and a list lands there
        # as the string "[0.4, -1.2]" that every reader then has to re-parse.
        "shift_x_mm": round(dx_mm, 1),
        "shift_y_mm": round(dy_mm, 1),
        "subject_ratio": None if mismatch is None else round(mismatch, 2),
        "ink_saturation": round(saturation, 3),
        "refusal": refusal,
    }


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def _print_table(rows: list[dict], components_only: bool) -> None:
    scored = [r for r in rows if r["refusal"] is None]
    refused = [r for r in rows if r["refusal"] is not None]

    head = (f"{'fixture':26s} {'route':13s} {'cov':>6s} {'col':>6s} "
            f"{'str':>6s}")
    if not components_only:
        head += f" {'ARTFID':>7s}"
    head += f"  {'grade':>5s} {'stitches':>8s}"
    print(head)
    print("-" * len(head))

    for r in sorted(scored, key=lambda r: -r["artfid"]):
        line = (f"{r['fixture']:26s} {r['route']:13s} {r['coverage']:6.3f} "
                f"{r['colour']:6.3f} {r['structure']:6.3f}")
        if not components_only:
            line += f" {r['artfid']:7.1f}"
        line += (f"  {r['preflight_grade']:>5s} "
                 f"{r['stitches']:8d}")
        print(line)

    if refused:
        print("\nRefused — components shown, but do not read them as engine "
              "results:")
        for r in sorted(refused, key=lambda r: -r["artfid"]):
            line = (f"{r['fixture']:26s} {r['route']:13s} {r['coverage']:6.3f} "
                    f"{r['colour']:6.3f} {r['structure']:6.3f}")
            if not components_only:
                line += f" {r['artfid']:7.1f}"
            line += f"  {r['preflight_grade']:>5s} {r['stitches']:8d}"
            print(line)
            print(f"{'':26s} -> {r['refusal']}")

    if scored and not components_only:
        mean = sum(r["artfid"] for r in scored) / len(scored)
        print(f"\nmean ARTFID {mean:.1f} over {len(scored)} scored "
              f"({len(refused)} refused)")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Score EMB-Bot's own stitch-out against the artwork it "
                    "was given. No professional reference.")
    ap.add_argument("images", nargs="*",
                    help="artwork paths, or names under digitizer/testdata")
    ap.add_argument("--all", action="store_true",
                    help="score the tracked fixture set")
    ap.add_argument("--components", action="store_true",
                    help="print the three components only, no composite "
                         "(ROADMAP hard gate 4's preferred reading)")
    ap.add_argument("--csv", type=Path, default=None,
                    help="also write every column to this CSV")
    args = ap.parse_args(argv)

    names = list(FIXTURES) if args.all else args.images
    if not names:
        ap.error("give image paths or --all")

    rows = []
    paths = _resolve(names)
    for i, path in enumerate(paths, 1):
        if not path.exists():
            print(f"skip (missing): {path}", file=sys.stderr)
            continue
        # Progress to stderr, flushed, as each fixture lands. A full-set run
        # digitizes fourteen designs and several take minutes apiece; without
        # this the whole thing is silent until the table prints at the end,
        # which in a CI log is indistinguishable from a hang. `artfidelity.py`
        # flushes per design for the same reason.
        print(f"[{i}/{len(paths)}] {path.name} ...", file=sys.stderr, flush=True)
        row = score_image(path)
        rows.append(row)
        note = f" REFUSED: {row['refusal']}" if row["refusal"] else ""
        print(f"[{i}/{len(paths)}] {path.name} {row['route']} "
              f"cov {row['coverage']:.3f} col {row['colour']:.3f} "
              f"str {row['structure']:.3f} -> {row['artfid']:.1f}{note}",
              file=sys.stderr, flush=True)

    if not rows:
        print("nothing scored", file=sys.stderr)
        return 1

    _print_table(rows, args.components)

    if args.csv:
        args.csv.parent.mkdir(parents=True, exist_ok=True)
        with open(args.csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            w.writeheader()
            for r in rows:
                w.writerow(r)
        print(f"\nwrote {args.csv}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
