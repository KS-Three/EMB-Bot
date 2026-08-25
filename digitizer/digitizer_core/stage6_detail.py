"""Stage 6 — the detail layer (photo plan, technique-menu row 11), first
slice: FDoG coherent line extraction emitted as BEAN RUNS on top of fills.

The row's point: photo details — edges, whiskers, panel lines — must never
merge into fill quantization. A fill tier renders tone; this layer renders
LINES, as discrete top objects sewn after everything else (plan row 14's
craft consensus: "details last"), in the light bean technique the border
machinery already sews (`stage6_border._bean_loop`'s corpus law: triple run
at 0.73 mm — reused here as constants and technique, on open polylines
instead of closed rings).

**FDoG, reimplemented from Kang, Lee & Chui, "Coherent Line Drawing", NPAR
2007** — the same paper, and the same machinery, as `directionfield.py`'s
ETF. LICENSE NOTE, load-bearing (the plan doc makes the constraint
explicit): GitHub reference implementations of FDoG carry unverified
licenses — this code is written from the paper's published algorithm alone,
not adapted from any repository. The algorithm, as the paper states it and
as implemented here:

1. **The flow** is the ETF field `directionfield.compute_direction_field`
   already produces (its whole reason to exist); this module is its second
   consumer after the streamline tier, and it reuses the streamline tier's
   own per-SourcePixels field cache (`stage6_streamline._field_for`) so a
   design running both tiers pays for ETF exactly once.
2. **Cross-flow DoG**: at each pixel x a one-dimensional difference-of-
   Gaussians `f(t) = G_sigma_c(t) - rho * G_sigma_s(t)` is applied to the
   image along the line PERPENDICULAR to the flow (the gradient direction),
   `F(x) = sum_t I(x + t*n(x)) f(t)` — the filter that responds where a
   line-shaped luminance dip/step crosses the flow.
3. **Along-flow accumulation**: F is accumulated along the flow curve
   through x, weighted by a Gaussian in arc length,
   `H(x) = sum_s G_sigma_m(s) F(z_s)` with `z_s` traced through the tangent
   field one pixel-step at a time (sign-aligned step to step — a tangent
   names a line, not a ray, the field's own documented contract). This is
   what makes the response COHERENT: a genuine contour reinforces itself
   along its own flow, isolated noise does not.
4. **Threshold**, the paper's own binarization: a pixel is line where
   `H < 0` and `1 + tanh(H) < tau`. One calibration note, measured not
   guessed: the paper's examples operate on integer-range luminance, where
   tanh saturates for any visible edge; this module's rasters are unit-
   range, so H is scaled by `FDOG_RESPONSE_GAIN` before the tanh to put the
   paper's own tau=0.5 operating point at the same place. The gain is
   calibrated on the committed synthetic fixtures (a 50%-contrast edge must
   detect with margin; uniform noise and flat color must not) and the
   calibration is pinned by `tests/test_stage6_detail.py`.

The line map is then thinned to single-pixel skeletons
(`skimage.morphology.skeletonize`), traced into polylines (deterministic
raster-order walks, endpoints first, straightest-continuation at
junctions), simplified, filtered by the machine's own sewable floor
(`machine.RUN_MIN_LOOP_MM` — the same three-bean-station rationale the run
tier's closed loops use), resampled at `machine.BEAN_STITCH_MM`, and
emitted as `machine.BEAN_PASSES`-pass bean runs — `stitches.BEAN`, the
kind the light outline tier already sews.

Sewing position: LAST, as its own color block appended after every artwork
block (stage 7 owns that seam) — details ride ON TOP of fills, and the
block's thread is the chart cone nearest (CIEDE2000) the median source
color sampled under the extracted lines themselves, so a graphite-dark
line map picks a graphite-dark cone rather than inheriting whatever thread
happened to sew last.

Strictly opt-in: nothing routes here except stage 7 on
`cfg.detail_layer = True`, and setting that flag is also what makes
`pipeline.run_stages` carry source pixels forward — the flat lane grows no
raster payload while the flag is off, and the suite's byte-identical tests
enforce that off means off. A design the extractor finds no lines for
(flat color, pure noise, all-highlight) emits NOTHING extra — no block, no
warning, honestly — rather than failing or inventing detail.

Travel: none. This layer sews on top of finished coverage with no topcoat
to bury a bridge under, so every hop between lines is the plain jump-or-
trim call (`run_outline`'s own rule, same reason): a needle-down bridge
across the art would be a visible float ACROSS THE DETAILS by
construction.

THE EYE-RECIPE SEAM (second slice, NOT built): the plan's full row 11 is
this layer PLUS the Embroidery Legacy eye recipe — pupil fill, dark iris,
and a minimal satin glint sewn LAST of all ("the glint is the difference
between a portrait and 'dead eyes'"). That half is deliberately absent
here, the same way `stage6_streamline`'s module docstring documented its
multi-color seam before building it, because it has a hard dependency this
repo does not yet satisfy: eye placement needs FACE LANDMARKS from the
plan's row 2 (`cv2.FaceDetectorYN` / YuNet, 5-point — present in the
wheel, NOT wired into any stage). When that lands, the seam is here: the
landmark ellipses select which extracted detail lines are eye-adjacent,
suppress bean runs inside the iris disc in favor of the pupil/iris fill
recipe, and append the satin glint as the final run of this block —
`detail_runs` already sews last, so the glint's LAST-of-all position falls
out of this module's existing seam rather than needing a new one.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import LineString
from skimage.morphology import skeletonize

from . import debugviz, machine, stitches
from .stage6_blend import SourcePixels
from .stage6_streamline import _field_for
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

# --- FDoG (Kang 2007) ---------------------------------------------------------

# Cross-flow DoG scales, the paper's own defaults: sigma_c sets the line
# width the filter responds to (one field pixel — stitch-scale detail, not
# region boundaries), sigma_s = 1.6 * sigma_c is the classic DoG surround
# ratio the paper states.
FDOG_SIGMA_C = 1.0
FDOG_SIGMA_S = 1.6

# The surround weight rho. The paper's stated default 0.99: the DoG sits
# just short of zero-sum, so flat color yields a small POSITIVE residue
# (never a line) while genuine dips go negative.
FDOG_RHO = 0.99

# Along-flow accumulation scale (arc length, px) — the coherence radius. The
# paper's default: a contour must agree with itself for ~3 px of flow either
# way before it counts, which is exactly what kills salt-and-pepper noise.
FDOG_SIGMA_M = 3.0

# The paper's binarization threshold tau on 1 + tanh(H). 0.5 is the paper's
# default operating point; lower finds fewer, stronger lines.
FDOG_TAU = 0.5

# H is computed on unit-range luminance here; the paper's tanh operating
# point assumes integer-range images (see module docstring, item 4). This
# gain restores that operating point. Calibrated by sweep on the synthetic
# fixtures (2026-08-04, this machine): at 80 the detection knee for a step
# edge sits at 20% contrast (40 -> 30%, 160 -> 15%), while flat color, iid
# uniform noise and sigma=12 Gaussian noise all still extract exactly zero
# lines at every gain tried (the coherence gate below is what holds that
# floor). 20% is "an edge a digitizer would actually draw a detail line
# on": fills render anything softer as tone. Pinned by
# tests/test_stage6_detail.py.
FDOG_RESPONSE_GAIN = 80.0

# A line pixel must also carry this much structure-tensor coherence — the
# SAME per-pixel statistic `RegionDirection.use_house_angle` gates regions
# on, applied at line-map resolution: a "line" whose own direction is
# statistically meaningless is noise, whatever its DoG response. Measured on
# the committed fixtures (tests pin this): iid uniform noise's strong-
# gradient pixels read coherence p90 0.39, a drawn circle/step edge reads
# 0.97+ — 0.6 sits in that gap with margin on both sides, the same
# wide-gap placement rationale as COHERENCE_FALLBACK_MIN's own 0.25.
DETAIL_MIN_COHERENCE = 0.6

# Kernel supports: the standard 3-sigma truncation.
_HALF_T = int(math.ceil(3.0 * FDOG_SIGMA_S))
_HALF_S = int(math.ceil(3.0 * FDOG_SIGMA_M))

# --- Vectorization ------------------------------------------------------------

# A traced line shorter than this does not sew: same floor and same
# three-bean-station rationale as the run tier's closed loops
# (machine.RUN_MIN_LOOP_MM's own comment) — under three stations the needle
# is re-entering its own holes, and a detail that small is lint, not a line.
DETAIL_MIN_LINE_MM = machine.RUN_MIN_LOOP_MM

# Polyline simplification tolerance, mm — the same figure stage 4 uses for
# artwork outlines (config.simplify_tol_mm's default): traced skeletons are
# pixel staircases, and bean stations at 0.73 mm cannot express sub-0.2 mm
# wiggle anyway.
DETAIL_SIMPLIFY_MM = 0.2

# A skeleton fragment under this many pixels is raster debris; dropped
# before it is even measured in mm.
_MIN_TRACE_PX = 3

_EPS = 1e-12


# --- The filter ---------------------------------------------------------------

def _gauss(t: np.ndarray, sigma: float) -> np.ndarray:
    return np.exp(-(t * t) / (2.0 * sigma * sigma)) / (math.sqrt(2.0 * math.pi) * sigma)


def _remap(img: np.ndarray, x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Bilinear sample of `img` at float positions, edge-replicated."""
    return cv2.remap(img, x.astype(np.float32), y.astype(np.float32),
                     cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def fdog_line_map(gray: np.ndarray, tangent: np.ndarray,
                  coherence: np.ndarray | None = None) -> np.ndarray:
    """Kang 2007's FDoG over one raster -> bool line map (True = line).

    `gray` is (H, W) float64 in [0, 1]; `tangent` is the ETF field's
    (H, W, 2) unit tangents (zero where the image is flat); `coherence`,
    when given, is the field's per-pixel anisotropy and gates the map at
    `DETAIL_MIN_COHERENCE` (see that constant — the noise/structure
    separation is measured, not assumed). Deterministic, no RNG.
    """
    h, w = gray.shape
    g32 = gray.astype(np.float32)
    tx = tangent[..., 0].astype(np.float32)
    ty = tangent[..., 1].astype(np.float32)
    # Cross-flow direction: the flow's perpendicular (the gradient line).
    nx, ny = -ty, tx

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Step 2 (module docstring): the 1-D DoG across the flow.
    ts = np.arange(-_HALF_T, _HALF_T + 1, dtype=np.float64)
    f = _gauss(ts, FDOG_SIGMA_C) - FDOG_RHO * _gauss(ts, FDOG_SIGMA_S)
    F = np.zeros((h, w), np.float32)
    for t, ft in zip(ts, f):
        if t == 0.0:
            F += np.float32(ft) * g32
            continue
        F += np.float32(ft) * _remap(g32, xx + np.float32(t) * nx,
                                     yy + np.float32(t) * ny)

    # Step 3: accumulate F along the flow, one pixel-step at a time, both
    # directions from each pixel, Gaussian-weighted in arc length. The step
    # direction is re-aligned against the previous step's (sign(dot)) so an
    # anti-parallel tangent continues the same curve instead of bouncing —
    # the same line-not-ray handling the streamline tracer uses.
    H = np.float32(_gauss(np.array([0.0]), FDOG_SIGMA_M)[0]) * F
    for sign in (1.0, -1.0):
        px, py = xx.copy(), yy.copy()
        dx, dy = np.float32(sign) * tx, np.float32(sign) * ty
        for s in range(1, _HALF_S + 1):
            stx = _remap(tx, px, py)
            sty = _remap(ty, px, py)
            dot = stx * dx + sty * dy
            flip = dot < 0.0
            stx = np.where(flip, -stx, stx)
            sty = np.where(flip, -sty, sty)
            # A zero tangent (flat pixel beyond ETF's reach) coasts straight.
            zero = (np.abs(stx) < _EPS) & (np.abs(sty) < _EPS)
            stx = np.where(zero, dx, stx)
            sty = np.where(zero, dy, sty)
            px = px + stx
            py = py + sty
            dx, dy = stx, sty
            wgt = np.float32(_gauss(np.array([float(s)]), FDOG_SIGMA_M)[0])
            H += wgt * _remap(F, px, py)

    # Step 4: the paper's binarization, at the calibrated operating point.
    Hs = FDOG_RESPONSE_GAIN * H.astype(np.float64)
    line = (Hs < 0.0) & ((1.0 + np.tanh(Hs)) < FDOG_TAU)
    # A pixel with no flow direction at all never carries a line: its "cross
    # flow" sampled the same point repeatedly and its response is not a
    # measurement of anything.
    line &= ~((np.abs(tx) < _EPS) & (np.abs(ty) < _EPS))
    if coherence is not None:
        line &= coherence >= DETAIL_MIN_COHERENCE
    return line


# --- Skeleton tracing ---------------------------------------------------------

_NBRS = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))


def _trace_polylines(skel: np.ndarray) -> list[list[tuple[int, int]]]:
    """Single-pixel skeleton -> pixel polylines [(x, y), ...], deterministic.

    Walks start at endpoints (exactly one 8-neighbour), raster order, then
    any remaining pixels (pure loops) raster order. At a junction the walk
    prefers the straightest continuation (max dot with the previous step,
    fixed neighbour order breaking ties), so a crossing splits into the two
    through-lines a person would draw rather than four stubs.
    """
    h, w = skel.shape
    remaining = skel.astype(bool).copy()

    # Endpoint detection on the ORIGINAL skeleton: neighbour count by shifts.
    nbr_count = np.zeros((h, w), np.int32)
    for dy, dx in _NBRS:
        shifted = np.zeros_like(remaining)
        ys0, ys1 = max(0, -dy), min(h, h - dy)
        xs0, xs1 = max(0, -dx), min(w, w - dx)
        if ys1 > ys0 and xs1 > xs0:
            shifted[ys0:ys1, xs0:xs1] = remaining[ys0 + dy:ys1 + dy, xs0 + dx:xs1 + dx]
        nbr_count += shifted.astype(np.int32)

    def walk(y: int, x: int) -> list[tuple[int, int]]:
        path = [(x, y)]
        remaining[y, x] = False
        pdy = pdx = 0
        while True:
            best = None
            for dy, dx in _NBRS:
                yy, xx2 = y + dy, x + dx
                if not (0 <= yy < h and 0 <= xx2 < w) or not remaining[yy, xx2]:
                    continue
                # Straightest continuation: maximize dot with previous step.
                score = pdy * dy + pdx * dx
                if best is None or score > best[0]:
                    best = (score, yy, xx2, dy, dx)
            if best is None:
                break
            _, y, x, pdy, pdx = best
            remaining[y, x] = False
            path.append((x, y))
        return path

    paths: list[list[tuple[int, int]]] = []
    ends = np.argwhere(remaining & (nbr_count == 1))
    for y, x in ends:
        if remaining[y, x]:
            p = walk(int(y), int(x))
            if len(p) >= _MIN_TRACE_PX:
                paths.append(p)
    # Whatever is left is loops (and junction remnants): raster order.
    for y, x in np.argwhere(remaining):
        if remaining[y, x]:
            p = walk(int(y), int(x))
            if len(p) >= _MIN_TRACE_PX:
                paths.append(p)
    return paths


# --- Extraction (px -> mm) ----------------------------------------------------

# One working pixel of slack at the subject boundary, applied as a single
# dilation of the resampled mask. NOT a physical constant and not tunable:
# the silhouette is the highest-value line FDoG finds on a cutout portrait
# (it is the outline of the subject), it sits exactly ON the boundary the
# mask splits at, and a majority-vote resample alone clips roughly half of
# it. One step is the smallest slack that keeps a boundary-straddling line
# whole; anything larger starts re-admitting the background this exists to
# remove.
_SUBJECT_SLACK_PX = 1


def _mask_to_subject(line_map: np.ndarray, sp: SourcePixels) -> np.ndarray:
    """Drop line pixels outside `sp.subject_mask`, or pass `line_map`
    straight back when there is no subject mask to respect.

    `line_map` lives at the FIELD's working resolution and the source mask
    at full resolution, so the mask is resampled down INTER_AREA — a
    per-cell subject fraction — and kept where the majority of the cell is
    subject, then dilated by `_SUBJECT_SLACK_PX` (see that constant). The
    target shape is taken from `line_map` itself rather than from the
    field's scale factor: the array in hand is the authority on what
    resolution it is at, and there is then no second source of truth to
    drift from it.

    The mask is applied to the LINE MAP rather than to the traced polylines
    for a reason worth stating: filtering afterwards would keep a line that
    merely starts inside the subject and then runs off across the
    background, because a polyline is kept or dropped whole. Cutting the
    raster first means such a line is traced only as far as the subject
    goes, and the part over bare fabric never becomes a bean run at all.

    `sp.subject_mask is None` — every job that did not opt into the rembg
    cutout — returns the input array unchanged, by identity, so this
    function cannot move a single existing stitch.
    """
    subject = sp.subject_mask
    if subject is None:
        return line_map
    h, w = line_map.shape[:2]
    if subject.shape[:2] != (h, w):
        subject = cv2.resize(subject.astype(np.float32), (w, h),
                             interpolation=cv2.INTER_AREA) >= 0.5
    keep = cv2.dilate(subject.astype(np.uint8),
                      np.ones((3, 3), np.uint8),
                      iterations=_SUBJECT_SLACK_PX).astype(bool)
    return line_map & keep


def extract_detail_lines(sp: SourcePixels) -> list[list[tuple[float, float]]]:
    """The full FDoG extraction over one design's source raster -> mm
    polylines (simplified, floor-filtered), possibly empty — an honest
    nothing for flat/noise rasters.

    Runs on the same downscaled raster, and the same cached field, as the
    streamline tier (`_field_for`): direction and line-ness are scale-local,
    and full-resolution FDoG costs seconds for no detail a 0.73 mm bean
    station could express.

    Confined to `sp.subject_mask` when the job carries one — see
    `_mask_to_subject`. Without a mask (every job that did not opt into the
    rembg cutout) this reads the whole raster exactly as it always has.
    """
    sampler = _field_for(sp)
    h, w = sp.rgb.shape[:2]
    if sampler.scale < 1.0:
        small = cv2.resize(sp.rgb, (max(1, int(round(w * sampler.scale))),
                                    max(1, int(round(h * sampler.scale)))),
                           interpolation=cv2.INTER_AREA)
    else:
        small = sp.rgb
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0

    line_map = fdog_line_map(gray, sampler.field.tangent,
                             sampler.field.coherence)
    line_map = _mask_to_subject(line_map, sp)
    if not line_map.any():
        return []
    skel = skeletonize(line_map)

    lines: list[list[tuple[float, float]]] = []
    for path in _trace_polylines(skel):
        mm = [sp.to_mm(x / sampler.scale, y / sampler.scale) for x, y in path]
        ls = LineString(mm).simplify(DETAIL_SIMPLIFY_MM, preserve_topology=False)
        if ls.is_empty or ls.geom_type != "LineString":
            continue
        if ls.length < DETAIL_MIN_LINE_MM:
            continue
        lines.append([(float(x), float(y)) for x, y in ls.coords])
    return lines


def _line_thread(lines: list[list[tuple[float, float]]], sp: SourcePixels,
                 cfg) -> tuple[int, tuple[int, int, int]]:
    """The chart cone nearest the lines' own median source color — a detail
    layer sews in the color the details actually are (usually near-black),
    never in whatever thread happened to sew last."""
    h, w = sp.rgb.shape[:2]
    samples = []
    for pts in lines:
        for x_mm, y_mm in pts:
            px, py = sp.to_px(x_mm, y_mm)
            xi = min(max(int(round(px)), 0), w - 1)
            yi = min(max(int(round(py)), 0), h - 1)
            samples.append(sp.rgb[yi, xi])
    med = np.median(np.asarray(samples, np.float64), axis=0)
    chart = chart_for(cfg)
    idx = chart.nearest_index(rgb_to_lab(med.reshape(1, 3))[0])
    return idx, tuple(int(v) for v in chart[idx].rgb)


# --- Emission -----------------------------------------------------------------

def _resample(pts: list[tuple[float, float]], pitch: float) -> list[tuple[float, float]]:
    """Arc-length resample at equal steps nearest `pitch` (the same equal-
    division rule `_ring_arc_samples` and the streamline resampler use)."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    n = max(2, round(total / pitch))
    out = [pts[0]]
    acc, j = 0.0, 0
    for i in range(1, n):
        t = total * i / n
        while j < len(seg) and acc + seg[j] < t:
            acc += seg[j]
            j += 1
        if j >= len(seg):
            break
        f = (t - acc) / seg[j] if seg[j] > _EPS else 0.0
        ax, ay = pts[j]
        bx, by = pts[j + 1]
        out.append((ax + (bx - ax) * f, ay + (by - ay) * f))
    out.append(pts[-1])
    return out


def _bean_line(pts: list[tuple[float, float]], passes: int) -> list[tuple[float, float]]:
    """An open polyline as a bean run: forward, back, forward — the same
    triple-run technique `_bean_loop` sews on closed rings, without the
    closure (an open line has ends, and the passes reverse at them)."""
    out = list(pts)
    for p in range(1, passes):
        leg = list(reversed(pts)) if p % 2 == 1 else list(pts)
        out.extend(leg[1:])
    return out


def detail_runs(sp: SourcePixels, cfg, entry: tuple[float, float] | None,
                trim_at_mm: float) -> tuple[list[StitchRun], dict]:
    """The detail layer for one design -> (runs, report).

    Report keys: the shared tier vocabulary (`empty`, `jumps`, `too_thin` —
    always False here, a line has no width to be too thin in) plus `lines`
    (emitted polylines) and, when lines exist, `thread_index` / `rgb` (the
    chart cone stage 7 opens the block with). Empty means exactly "emit no
    block": this layer rides on top of artwork that is already sewn, so
    unlike a fill tier there is nothing to fall back to and nothing lost.
    """
    report: dict = {"lines": 0, "jumps": 0, "empty": True, "too_thin": False}
    lines = extract_detail_lines(sp)
    if not lines:
        return [], report

    thread_idx, rgb = _line_thread(lines, sp, cfg)
    report["thread_index"] = thread_idx
    report["rgb"] = rgb

    # Sew order: nearest-neighbour over the lines, each entered from
    # whichever end is closer — the same economy the streamline tier's
    # ordering applies, deterministic (rounded distance, then index, end).
    remaining = list(range(len(lines)))
    ordered: list[list[tuple[float, float]]] = []
    cur = entry
    while remaining:
        if cur is None:
            pick, flip = remaining[0], 0
        else:
            best = None
            for i in remaining:
                for fb in (0, 1):
                    end = lines[i][0] if fb == 0 else lines[i][-1]
                    key = (round(math.dist(cur, end), 6), i, fb)
                    if best is None or key < best[0]:
                        best = (key, i, fb)
            pick, flip = best[1], best[2]
        pts = lines[pick] if flip == 0 else list(reversed(lines[pick]))
        remaining.remove(pick)
        ordered.append(pts)
        cur = pts[-1]

    runs: list[StitchRun] = []
    for pts in ordered:
        stations = _resample(pts, machine.BEAN_STITCH_MM)
        bean = _bean_line(stations, machine.BEAN_PASSES)
        if len(bean) < 2:
            continue
        # No travel, ever: this layer has no covering topcoat, so a hop
        # between lines is the plain jump-or-trim call (see module
        # docstring). Only BETWEEN lines — the hop into the block itself is
        # stage 7's forced color change, exactly as it is for every block.
        jump = trim = False
        if runs:
            d = math.dist(runs[-1].points[-1], bean[0])
            if d >= machine.TINY_STITCH_MM:
                jump = True
                trim = d > trim_at_mm
                report["jumps"] += 1
        runs.append(StitchRun(points=stitches.split_long_moves(bean),
                              kind=stitches.BEAN, jump=jump, trim=trim,
                              shape_id="detail"))
    report["lines"] = len(runs)
    report["empty"] = not runs

    if cfg.debug_dir and runs:
        debugviz.stage6_detail_lines(Path(cfg.debug_dir), sp.rgb,
                                     [[sp.to_px(x, y) for x, y in r.points]
                                      for r in runs if r.kind == stitches.BEAN])
    return runs, report
