"""Hairline strands from LINES, not from segmented regions (2026-10-13).

`cfg.hairline_from_lines`, default OFF, read only when `cfg.hairline` is on.

Why it exists. The hairline tier (`stage6_hairline`) sews a strand the
tracer delivered as a SHAPE. On the one real photograph in the corpus
(`testdata/photo/owl_kent.jpg`, PR #876's trial,
docs/hairline-photo-trial-2026-10-12.md) the photo lane's segmenter merges
the facial bristles into a few ragged regions — segmentation exists to merge
texture — so the tier sewed 3 strands, dropped 10, and left new bare fabric
where it carved its ribbons out of the fills. That doc's option 1, which the
director chose: feed the hairline walk from the detail layer's FDoG lines
(`stage6_detail`, Kang 2007), and sew them as run strands ON TOP of the fill
ground that is already there. Nothing is carved out of a fill, so the ground
under every strand is the shape's own full fill.

What runs, in order:

1. **Lines, both polarities.** `stage6_detail`'s FDoG response on the gray
   raster finds DARK lines (a luminance dip across the flow); the same
   filter on the inverted raster finds LIGHT ones — the owl's bristles are
   mostly white strands over a darker underlay, which a dark-only detector
   cannot see. The strength floor is the detector's own, unchanged: the
   paper's tau at the calibrated gain and the `DETAIL_MIN_COHERENCE` gate
   (`stage6_detail.fdog_threshold`). No new strength threshold.
2. **A strand, not an edge.** FDoG answers on the dark side of every step
   edge too — a feather bar's rim, the subject's outline. A strand is a
   RIDGE: its middle stands out from BOTH sides within a strand's width.
   Profiles across the line, on the source's L*, read the middle (the
   extreme within half a laid thread of the line) against each side (the
   sample differing most from it, between half the tier's widest strand,
   `ThreadProfile.hairline_max_width_mm`, and `_SIDE_REACH_PX` source pixels
   further out). The line's contrast is the median over its profiles of the
   SMALLER side's difference; it is a strand when that is at least
   `stage6_hairline._SRC_MIN_CONTRAST` (12) — the tier's own contrast floor,
   read along L* alone. A step edge, a ramp, or a line along the inside of
   a wide band has one side like its middle and reads near 0. This is the
   same question #876's `_line_contrasts` asks of a traced branch, asked of
   a detected line, written here so the two do not collide.
   **A strand, not a bar** (`cfg.hairline_lines_strand_test`, default OFF,
   2026-10-13). A thin bar is a ridge too: on owl_kent 31 of 75 strands
   were the breast barring. With the flag on, a ridge that sits in a stack
   of parallel lines of its own polarity is a bar and is not sewn
   (`stack_share`, the constants beside it). The same flag makes the run
   rules read the colour block's weight (`strand_blocks`' `block_wt`)
   instead of the design's.
3. **Stitch, the tier's rules.** Each strand is a run: `stitch_path` at
   `cfg.hairline_stitch_mm`, shortened on a curl to the curl tolerance of
   the block's thread (`_CURL_TOL_WIDTHS` x `hairline_run_width_mm`, so
   40 / 60 wt follow `cfg.thread_wt`), never under `machine.MIN_STITCH_MM`.
   A strand under `machine.RUN_MIN_LOOP_MM` is dropped and counted, as the
   tier counts its own (`HAIRLINE_TIER_SEWN`).
4. **Thread and order.** One colour block per polarity, sewn after every
   artwork block and the detail layer: strands over the ground. Its cone is
   the DESIGN's own thread nearest (CIEDE2000) the median source colour
   under that polarity's strands, so no new spool is bought for it.
   Within a block, nearest-neighbour from the needle, each strand entered
   from its nearer end; a hop is a jump, a trim past `trim_at_mm`
   (`detail_runs`' and `hairline_runs`' rule).

Where it applies: the photo lanes only (`LINE_CLASSES`), because that is
where strands do not arrive as shapes. On a drawn design (the hair
fixtures classify as `gradient`) a hair IS a shape and the region tier
already sews it; there this flag changes nothing, byte for byte, and the
tier runs as before. On a photo lane the region tier is replaced,
not stacked: no shape is carved (`pipeline.plan_stitches` hands stage 5 and
stage 7 an empty `HairlineSet`).

**On the gradient lane, a SUPPLEMENT** (`cfg.hairline_lines_gradient`,
default OFF, 2026-10-14; `supplements`). The Studio sends owl_kent down
`gradient` (#876's `studio` route), where the route above never runs. #915
measured why it must not simply be widened there: on drawn hair the region
tier sews every strand as a shape and saves thousands of stitches, and the
line route replacing it is a regression. So on `gradient` the region tier
runs exactly as it does, and the line route adds only the strands it laid
nothing near: a line with at least `_SUPPLEMENT_COVERED_SHARE` of its length
within the tier's run half-width plus one source pixel of a shape the tier
walked (`supplement_zone`) is not sewn, counted in `refused_region`. Needs
the strand test on too (it removes the barring, #897), else inert.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import math

import cv2
import numpy as np
import shapely

from . import machine, stitches
from .config import PHOTO_CLASSES
from .stage6_detail import fdog_response, fdog_threshold, field_gray, lines_from_map
from .stage6_hairline import _CURL_TOL_WIDTHS, _SRC_MIN_CONTRAST, _SRC_STEP_PX, stitch_path
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

# The lanes whose strands do not reach stage 6 as shapes (module docstring).
# The photo classes only. NOT `gradient`: the drawn hair fixtures
# (`hair_strands`, `hair_fine`) classify as gradient, and there the region
# tier already sews every strand as a shape (184 / 321 run branches, #876).
# The Studio sends owl_kent down the gradient lane too (#876's `studio`
# route), so that route is not covered yet; widening this is a measured
# follow-up, not a default.
LINE_CLASSES = tuple(PHOTO_CLASSES)

# How far past the widest strand's half-width a side sample reaches, in
# SOURCE pixels. One pixel: the side must be read where a strand of the
# tier's widest width has ended, and no further, or a wide band reads its
# far rim as a side and passes as a strand. CANDIDATE (geometry, unsewn,
# not swept): the measured effect is in the PR's census.
_SIDE_REACH_PX = 1.0

# A hole in the line map at most this many FIELD pixels across is the
# filter's ring artefact and is filled before thinning (`_fill_slits`).
# Resolution-bound raster cleanup, not a physical constant.
_SLIT_PX = 2.0

# Spacing of the cross-profiles along a line, in laid thread widths.
_PROFILE_STEP_WIDTHS = 1.0

# --- The strand test (`cfg.hairline_lines_strand_test`, default OFF) ---------
# A thin BAR passes the ridge test as well as a strand does: on owl_kent, 31
# of the line route's 75 strands are the thin dark parts of the breast
# barring (#882). What tells them apart is the company a line keeps: a bar
# is one of a STACK — parallel lines of its own polarity on both sides of it
# (the bars above and below), or two on one side at an even period (the
# stack's edge). A strand is not. Read at stations `_STACK_STEP_MM` apart
# along the line; at each, a ray along either normal looks for any line the
# detector found in the same polarity (ridge or not: a wide bar is still a
# bar), running within `_STACK_ANGLE_DEG` of the station's direction, between
# half the widest strand (`hairline_max_width_mm` / 2: nearer is the line's
# own other rim) and `_STACK_REACH_MM`. A line is a bar, and is not sewn, when
# at least `_STACK_SHARE` of its stations sit in a stack.
# Curvature, taper and the ends were measured too and do not separate the
# two on this photo (the PR's census): the bars curve as much as the
# bristles, both fade at the ends, and at 4.36 px/mm neither has a width
# profile to taper. All CANDIDATES (geometry of the file, unsewn, gate 1).
_STACK_STEP_MM = 0.5
_STACK_ANGLE_DEG = 20.0
_STACK_REACH_MM = 6.0
_STACK_SHARE = 0.4
# A second neighbour on one side at this multiple of the first's distance is
# the next bar of an evenly spaced stack.
_STACK_PERIOD = (1.6, 2.5)

SHAPE_ID = "hairline_lines"

# --- Chaining (`cfg.hairline_lines_chain`, default OFF) ----------------------
# The longest hop between two strands sewn needle-down instead of cut:
# `stage6_streamline.STREAMLINE_TRAVEL_MAX_MM`, the same cap for the same
# reason (a longer drag is a float across the art). A CANDIDATE, not a
# settled constant: no sew-out has judged what a dragged hop looks like
# over a fill (ROADMAP gate 3). The hop must also lie over thread the fills
# already laid (the caller's `hop_ok`), else it is cut as before.
HOP_MAX_MM = 8.0

# --- The gradient supplement (`cfg.hairline_lines_gradient`, default OFF) ----
# The lane the supplement runs on: where the region tier already sews drawn
# hair as shapes, and where the Studio sends owl_kent (#915).
GRADIENT_SUPPLEMENT_CLASSES = ("gradient",)
# A line whose share of length inside `supplement_zone` is at least this is
# the region tier's strand seen a second time, and is not sewn. Half: a line
# that merely crosses a walked shape keeps its free length. A CANDIDATE
# (geometry of the file, unsewn, gate 1); the measured split is in the PR.
_SUPPLEMENT_COVERED_SHARE = 0.5
# Sampling pitch along a line for that share (the chain's cover test's).
_SUPPLEMENT_STEP_MM = 0.1


def _fill_slits(line_map: np.ndarray) -> np.ndarray:
    """Fill every hole of the line map no wider than `_SLIT_PX` pixels.

    FDoG's response across a two-pixel antialiased line can dip at the
    line's exact middle, so the map holds the line as a thin RING; its
    skeleton is then two parallel tracks, and the walk sews the second as
    duplicate strands over the first (measured on a drawn fixture: 14 lines
    traced as 96 pieces, 22 of them over the loop floor and lying on top of
    a line already sewn). A hole that narrow is the filter's artefact, not
    background between two strands: two strands that close sew as one
    thread anyway.

    A straight line can instead come back as two parallel tracks that never
    join (a hole open at both ends), so a 3 x 3 closing first bridges any
    one-pixel gap between tracks; two strands one pixel apart are closer
    than a laid thread at any resolution this route sees."""
    line_map = cv2.morphologyEx(line_map.astype(np.uint8), cv2.MORPH_CLOSE,
                                np.ones((3, 3), np.uint8)).astype(bool)
    filled = line_map.copy()
    holes = (~line_map).astype(np.uint8)
    n, lab, stats, _c = cv2.connectedComponentsWithStats(holes, connectivity=4)
    h, w = line_map.shape
    dist = cv2.distanceTransform(holes, cv2.DIST_L2, 3)
    for i in range(1, n):
        x, y, bw, bh, _a = stats[i]
        if x == 0 or y == 0 or x + bw >= w or y + bh >= h:
            continue                       # touches the border: background
        comp = lab[y:y + bh, x:x + bw] == i
        if float(dist[y:y + bh, x:x + bw][comp].max()) <= _SLIT_PX / 2.0 + 1e-6:
            filled[y:y + bh, x:x + bw] |= comp
    return filled


def applies(cfg, design_class: str | None) -> bool:
    """Is the line route on for this design? Needs both flags and a raster
    lane (`LINE_CLASSES`)."""
    return bool(getattr(cfg, "hairline", False)
                and getattr(cfg, "hairline_from_lines", False)
                and design_class in LINE_CLASSES)


def supplements(cfg, design_class: str | None) -> bool:
    """Does the line route run as a SUPPLEMENT to the region tier on this
    design? `cfg.hairline_lines_gradient` on a gradient lane, with
    `hairline`, `hairline_from_lines` and `hairline_lines_strand_test` all
    on; any one off, False (inert)."""
    return bool(getattr(cfg, "hairline", False)
                and getattr(cfg, "hairline_from_lines", False)
                and getattr(cfg, "hairline_lines_strand_test", False)
                and getattr(cfg, "hairline_lines_gradient", False)
                and design_class in GRADIENT_SUPPLEMENT_CLASSES
                and not applies(cfg, design_class))


def supplement_zone(polygons, sp, cfg):
    """Where the region tier laid strands: the shapes it walked, grown by
    the tier's run half-width plus one source pixel (#915's proposal). An
    empty geometry when it walked none."""
    reach = (0.5 * machine.thread_profile(cfg.thread_wt).hairline_run_width_mm
             + 1.0 / sp.px_per_mm)
    polys = [p for p in polygons if p is not None and not p.is_empty]
    if not polys:
        return shapely.Polygon()
    zone = shapely.union_all([p.buffer(reach) for p in polys])
    shapely.prepare(zone)
    return zone


def covered_share(pts, zone) -> float:
    """Share of the polyline `pts` (mm) lying inside `zone`, sampled every
    `_SUPPLEMENT_STEP_MM`."""
    if zone is None or zone.is_empty or len(pts) < 2:
        return 0.0
    p = np.asarray(pts, np.float64)
    cum = np.r_[0.0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    n = max(2, int(cum[-1] / _SUPPLEMENT_STEP_MM) + 1)
    t = np.linspace(0.0, cum[-1], n)
    x, y = np.interp(t, cum, p[:, 0]), np.interp(t, cum, p[:, 1])
    return float(np.mean(shapely.contains_xy(zone, x, y)))


def _light(sp) -> np.ndarray:
    """(H, W) float32 L* of the source raster, full resolution."""
    h, w = sp.rgb.shape[:2]
    return rgb_to_lab(sp.rgb.reshape(-1, 3).astype(np.float64)).reshape(h, w, 3)[..., 0] \
        .astype(np.float32)


def _resample(pts, step: float):
    cum = [0.0]
    for a, b in zip(pts, pts[1:]):
        cum.append(cum[-1] + math.dist(a, b))
    total = cum[-1]
    if total <= 0:
        return []
    n = max(1, int(total // step))
    out = []
    j = 0
    for i in range(n + 1):
        s = min(total, (i + 0.5) * total / (n + 1))
        while j < len(cum) - 2 and cum[j + 1] < s:
            j += 1
        seg = cum[j + 1] - cum[j]
        f = (s - cum[j]) / seg if seg > 0 else 0.0
        (ax, ay), (bx, by) = pts[j], pts[j + 1]
        tx, ty = bx - ax, by - ay
        L = math.hypot(tx, ty) or 1.0
        out.append(((ax + tx * f, ay + ty * f), (-ty / L, tx / L)))
    return out


def ridge_contrast(pts, light: np.ndarray, sp, *, polarity: str,
                   core_mm: float, side0_mm: float, side1_mm: float,
                   step_mm: float) -> float:
    """Median over cross-profiles of how far the line's middle stands out
    from its LESS different side, in L* (positive = a strand of `polarity`).
    `core_mm`: half-width of the middle window; the sides are read between
    `side0_mm` and `side1_mm` either way. Profiles that leave the raster are
    skipped; no profile at all reads 0."""
    h, w = light.shape
    px_mm = sp.px_per_mm
    step_px = _SRC_STEP_PX
    def ts(a, b):
        n = max(2, int(math.ceil((b - a) * px_mm / step_px)) + 1)
        return np.linspace(a, b, n)
    t_core = ts(-core_mm, core_mm)
    t_side = ts(side0_mm, side1_mm)
    vals = []
    for (x, y), (nx, ny) in _resample(pts, step_mm):
        cx, cy = sp.to_px(x, y)
        def sample(t):
            X = (cx + t * nx * px_mm).astype(np.float32)
            Y = (cy + t * ny * px_mm).astype(np.float32)
            if X.min() < 0 or Y.min() < 0 or X.max() > w - 1 or Y.max() > h - 1:
                return None
            return cv2.remap(light, X.reshape(1, -1), Y.reshape(1, -1),
                             cv2.INTER_LINEAR).ravel()
        core, left, right = sample(t_core), sample(-t_side), sample(t_side)
        if core is None or left is None or right is None:
            continue
        if polarity == "dark":
            mid = float(core.min())
            c = min(float(left.max()), float(right.max())) - mid
        else:
            mid = float(core.max())
            c = mid - max(float(left.min()), float(right.min()))
        vals.append(c)
    return float(np.median(vals)) if vals else 0.0


def _segments(lines) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Every segment of `lines` -> (owner line index, start, direction,
    unit direction), for `stack_share`'s rays."""
    owner, a, b = [], [], []
    for k, pts in enumerate(lines):
        for p, q in zip(pts, pts[1:]):
            owner.append(k)
            a.append(p)
            b.append(q)
    if not owner:
        z = np.zeros((0, 2))
        return np.zeros(0, int), z, z, z
    A = np.asarray(a, np.float64)
    D = np.asarray(b, np.float64) - A
    U = D / (np.hypot(D[:, 0], D[:, 1])[:, None] + 1e-12)
    return np.asarray(owner, int), A, D, U


def _ray_hits(o, nrm, tan, own: int, segs, gap0_mm: float) -> np.ndarray:
    """Sorted distances along the ray `o + t * nrm` (gap0 < t < reach) at
    which it crosses a segment of another line running within
    `_STACK_ANGLE_DEG` of `tan`."""
    owner, A, D, U = segs
    den = nrm[0] * D[:, 1] - nrm[1] * D[:, 0]
    ok = np.abs(den) > 1e-9
    safe = np.where(ok, den, 1.0)
    AO = A - o
    t = (AO[:, 0] * D[:, 1] - AO[:, 1] * D[:, 0]) / safe
    u = (AO[:, 0] * nrm[1] - AO[:, 1] * nrm[0]) / safe
    par = np.abs(U @ tan) >= math.cos(math.radians(_STACK_ANGLE_DEG))
    m = (ok & (u >= 0.0) & (u <= 1.0) & (t > gap0_mm) & (t < _STACK_REACH_MM)
         & (owner != own) & par)
    return np.sort(t[m])


def stack_share(own: int, pts, segs, *, gap0_mm: float) -> float:
    """The share of stations along `pts` (line `own` of the polarity whose
    segments are `segs`) that sit inside a stack of parallel lines: one
    either side, or two on one side at `_STACK_PERIOD` times the first's
    distance. 0 for a line too short to hold a station."""
    p = np.asarray(pts, np.float64)
    d = np.hypot(*np.diff(p, axis=0).T)
    cum = np.r_[0.0, np.cumsum(d)]
    n = max(2, int(cum[-1] // _STACK_STEP_MM) + 1)
    t = np.linspace(0.0, cum[-1], n)
    q = np.c_[np.interp(t, cum, p[:, 0]), np.interp(t, cum, p[:, 1])]
    stations = hit = 0
    lo, hi = _STACK_PERIOD
    for i in range(1, len(q) - 1):
        tan = q[i + 1] - q[i - 1]
        tan = tan / (np.linalg.norm(tan) + 1e-12)
        nrm = np.array([-tan[1], tan[0]])
        stations += 1
        left = _ray_hits(q[i], -nrm, tan, own, segs, gap0_mm)
        right = _ray_hits(q[i], nrm, tan, own, segs, gap0_mm)
        stacked = bool(len(left) and len(right))
        for side in (left, right):
            if len(side) >= 2 and lo <= side[1] / side[0] <= hi:
                stacked = True
        hit += stacked
    return hit / stations if stations else 0.0


def extract_strands(sp, cfg, *, thread_wt: int | None = None,
                    polarities: tuple[str, ...] = ("dark", "light")
                    ) -> tuple[list[dict], dict]:
    """-> (strands, census). Each strand: `pts` (mm polyline), `polarity`,
    `length_mm`, `contrast` (L*), `strength` (median 1 + tanh(gain x H) on
    its pixels; the detector's floor is tau = 0.5). The census counts what
    the detector found and what the ridge test refused, per polarity; with
    `cfg.hairline_lines_strand_test` on, also what the strand test refused
    as a bar (`refused_bar`), and each strand carries its `stack` share.

    `thread_wt` (default `cfg.thread_wt`) sets the widths the ridge reads;
    `polarities` limits the read to some of the two."""
    from .stage6_detail import FDOG_RESPONSE_GAIN
    prof = machine.thread_profile(cfg.thread_wt if thread_wt is None else thread_wt)
    strand_test = bool(getattr(cfg, "hairline_lines_strand_test", False))
    sampler, gray = field_gray(sp)
    tangent, coherence = sampler.field.tangent, sampler.field.coherence
    light = _light(sp)
    src_px = 1.0 / sp.px_per_mm
    core = 0.5 * prof.hairline_run_width_mm
    side0 = 0.5 * prof.hairline_max_width_mm
    side1 = side0 + _SIDE_REACH_PX * src_px
    step = _PROFILE_STEP_WIDTHS * prof.width_mm
    census = {"found": {}, "refused_no_ridge": {}}
    if strand_test:
        census["refused_bar"] = {}
    strands: list[dict] = []
    for polarity, g in (("dark", gray), ("light", 1.0 - gray)):
        if polarity not in polarities:
            continue
        H = fdog_response(g, tangent)
        lmap = _fill_slits(fdog_threshold(H, tangent, coherence))
        lines = lines_from_map(lmap, sp, sampler.scale, min_len_mm=0.0)
        census["found"][polarity] = len(lines)
        refused = bars = 0
        segs = _segments(lines) if strand_test else None
        resp = 1.0 + np.tanh(FDOG_RESPONSE_GAIN * H.astype(np.float64))
        hh, ww = resp.shape
        for k, pts in enumerate(lines):
            c = ridge_contrast(pts, light, sp, polarity=polarity, core_mm=core,
                               side0_mm=side0, side1_mm=side1, step_mm=step)
            if c < _SRC_MIN_CONTRAST:
                refused += 1
                continue
            share = None
            if strand_test:
                share = stack_share(k, pts, segs, gap0_mm=side0)
                if share >= _STACK_SHARE:
                    bars += 1
                    continue
            rs = []
            for x, y in pts:
                px, py = sp.to_px(x, y)
                xi = min(max(int(round(px * sampler.scale)), 0), ww - 1)
                yi = min(max(int(round(py * sampler.scale)), 0), hh - 1)
                rs.append(resp[yi, xi])
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            strand = {"pts": pts, "polarity": polarity, "length_mm": length,
                      "contrast": c, "strength": float(np.median(rs))}
            if strand_test:
                strand["stack"] = share
            strands.append(strand)
        census["refused_no_ridge"][polarity] = refused
        if strand_test:
            census["refused_bar"][polarity] = bars
    return strands, census


def _thread_for(strands, sp, cfg, allowed: list[int]) -> int:
    """The design thread (one of `allowed`, chart indices) nearest the
    median source colour under `strands`; the chart's nearest when
    `allowed` is empty."""
    h, w = sp.rgb.shape[:2]
    samples = []
    for s in strands:
        for x, y in s["pts"]:
            px, py = sp.to_px(x, y)
            samples.append(sp.rgb[min(max(int(round(py)), 0), h - 1),
                                  min(max(int(round(px)), 0), w - 1)])
    med = np.median(np.asarray(samples, np.float64), axis=0)
    lab = rgb_to_lab(med.reshape(1, 3))[0]
    chart = chart_for(cfg)
    if not allowed:
        return chart.nearest_index(lab)
    from skimage.color import deltaE_ciede2000
    labs = chart.lab[np.asarray(allowed, int)]
    d = deltaE_ciede2000(np.repeat(lab.reshape(1, 3), len(allowed), axis=0), labs)
    return allowed[int(np.argmin(d))]


def _hop_stitches(a, b) -> list[tuple[float, float]]:
    """The needle-down walk from `a` to `b`, both exclusive: points at most
    `machine.TRAVEL_STITCH_MM` apart (the fills' own travel pitch). Empty
    when the hop is a single stitch."""
    n = max(1, math.ceil(math.dist(a, b) / machine.TRAVEL_STITCH_MM))
    return [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
            for i in range(1, n)]


def _sewable(group, cfg, thread_wt: int) -> tuple[list, int]:
    """-> ([(strand, stitch points)], dropped): the strands of `group` the
    tier's run rules sew at `thread_wt`'s curl tolerance."""
    tol = _CURL_TOL_WIDTHS * machine.thread_profile(thread_wt).hairline_run_width_mm
    keep, dropped = [], 0
    for s in group:
        if s["length_mm"] < machine.RUN_MIN_LOOP_MM:
            dropped += 1
            continue
        pts = stitch_path(s["pts"], cfg.hairline_stitch_mm, tol)
        if len(pts) < 2:
            dropped += 1
            continue
        keep.append((s, pts))
    return keep, dropped


def strand_blocks(sp, cfg, *, entry, trim_at_mm: float, allowed_threads: list[int],
                  block_wt: dict[int, int] | None = None, hop_ok=None,
                  exclude=None
                  ) -> tuple[list[tuple[int, list[StitchRun]]], dict]:
    """The line route for one design -> ([(thread_index, runs)], report).

    Report: `strands` (sewn), `dropped` (strand-tested lines under the loop
    floor, or with nothing left after the needle floor), `jumps`, and the
    extraction census (`found`, `refused_no_ridge`, per polarity).

    `block_wt` is stage 7's per-colour-block weight (`stage6_hairline.
    block_thread_wt`'s rule: the finest weight a shape of that thread names
    through `shape_overrides`). It is read only with
    `cfg.hairline_lines_strand_test` on: a polarity's block is chosen at the
    design weight as before, and when that thread's block names another
    weight, the polarity's strands are read again (ridge widths) and
    stitched (curl tolerance) at the block's weight, on the same thread.
    The report then carries `thread_wt` per polarity. With no override every
    block is at `cfg.thread_wt`, and nothing is read twice.

    `hop_ok(a, b) -> bool` (stage 7: the segment lies over laid thread) is
    read only with `cfg.hairline_lines_chain` on. A hop of at most
    `HOP_MAX_MM` for which it holds is sewn needle-down (a TRAVEL run at
    `TRAVEL_STITCH_MM`, the next strand not a jump) and counted in `hops` /
    `hop_mm`; every other hop is a jump, a trim past `trim_at_mm`, as before.

    `exclude` (the gradient supplement, `supplement_zone`): a strand with at
    least `_SUPPLEMENT_COVERED_SHARE` of its length inside it is not sewn,
    and the report counts it per polarity in `refused_region`. None: no
    such test, and no such key."""
    strand_test = bool(getattr(cfg, "hairline_lines_strand_test", False))
    bw = dict(block_wt or {}) if strand_test else {}
    strands, census = extract_strands(sp, cfg)
    report = {"strands": 0, "dropped": 0, "jumps": 0, **census,
              "sewn_by_polarity": {}}
    if exclude is not None:
        report["refused_region"] = {}

    def free(group, polarity):
        if exclude is None:
            return group
        out = [s for s in group
               if covered_share(s["pts"], exclude) < _SUPPLEMENT_COVERED_SHARE]
        report["refused_region"][polarity] = len(group) - len(out)
        return out
    if strand_test:
        report["thread_wt"] = {}
    chain = bool(getattr(cfg, "hairline_lines_chain", False)) and hop_ok is not None
    if chain:
        report.update(hops=0, hop_mm=0.0)
    out: list[tuple[int, list[StitchRun]]] = []
    cur = entry
    for polarity in ("dark", "light"):
        group = free([s for s in strands if s["polarity"] == polarity], polarity)
        keep, dropped = _sewable(group, cfg, cfg.thread_wt)
        wt = cfg.thread_wt
        thread = (_thread_for([s for s, _ in keep], sp, cfg, allowed_threads)
                  if keep else None)
        if thread is not None and bw.get(thread, cfg.thread_wt) != cfg.thread_wt:
            wt = bw[thread]
            group, again = extract_strands(sp, cfg, thread_wt=wt, polarities=(polarity,))
            for key, per in again.items():
                report[key][polarity] = per[polarity]
            group = free(group, polarity)
            keep, dropped = _sewable(group, cfg, wt)
        if strand_test:
            report["thread_wt"][polarity] = wt
        report["dropped"] += dropped
        report["sewn_by_polarity"][polarity] = len(keep)
        if not keep:
            continue
        remaining = list(range(len(keep)))
        runs: list[StitchRun] = []
        while remaining:
            if cur is None:
                pick, flip = remaining[0], 0
            else:
                best = None
                for i in remaining:
                    for fb in (0, 1):
                        end = keep[i][1][0] if fb == 0 else keep[i][1][-1]
                        key = (round(math.dist(cur, end), 6), i, fb)
                        if best is None or key < best[0]:
                            best = (key, i, fb)
                pick, flip = best[1], best[2]
            remaining.remove(pick)
            pts = keep[pick][1] if flip == 0 else list(reversed(keep[pick][1]))
            jump = trim = False
            if runs:
                d = math.dist(runs[-1].points[-1], pts[0])
                if d >= machine.TINY_STITCH_MM:
                    if chain and d <= HOP_MAX_MM and hop_ok(runs[-1].points[-1], pts[0]):
                        walk = _hop_stitches(runs[-1].points[-1], pts[0])
                        if walk:
                            runs.append(StitchRun(points=walk, kind=stitches.TRAVEL,
                                                  shape_id=SHAPE_ID))
                        report["hops"] += 1
                        report["hop_mm"] = round(report["hop_mm"] + d, 3)
                    else:
                        jump = True
                        trim = d > trim_at_mm
                        report["jumps"] += 1
            runs.append(StitchRun(points=stitches.split_long_moves(pts),
                                  kind=stitches.RUN, jump=jump, trim=trim,
                                  shape_id=SHAPE_ID))
            cur = pts[-1]
        report["strands"] += sum(1 for r in runs if r.kind == stitches.RUN)
        out.append((thread, runs))
    return out, report
