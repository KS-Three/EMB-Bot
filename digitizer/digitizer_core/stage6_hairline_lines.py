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

Where it applies: the raster lanes only (`LINE_CLASSES`: gradient and the
photo classes), because that is where strands do not arrive as shapes. On
the flat lane a drawn hair IS a shape and the region tier already sews it
(hair_strands, hair_fine); there this flag changes nothing, byte for byte,
and the tier runs as before. On a raster lane the region tier is replaced,
not stacked: no shape is carved (`pipeline.plan_stitches` hands stage 5 and
stage 7 an empty `HairlineSet`).

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import math

import cv2
import numpy as np

from . import machine, stitches
from .config import PHOTO_CLASSES
from .stage6_detail import fdog_response, fdog_threshold, field_gray, lines_from_map
from .stage6_hairline import _CURL_TOL_WIDTHS, _SRC_MIN_CONTRAST, _SRC_STEP_PX, stitch_path
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

# The lanes whose strands do not reach stage 6 as shapes (module docstring).
LINE_CLASSES = ("gradient",) + tuple(PHOTO_CLASSES)

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

SHAPE_ID = "hairline_lines"


def _fill_slits(line_map: np.ndarray) -> np.ndarray:
    """Fill every hole of the line map no wider than `_SLIT_PX` pixels.

    FDoG's response across a two-pixel antialiased line can dip at the
    line's exact middle, so the map holds the line as a thin RING; its
    skeleton is then two parallel tracks, and the walk sews the second as
    duplicate strands over the first (measured on a drawn fixture: 14 lines
    traced as 96 pieces, 22 of them over the loop floor and lying on top of
    a line already sewn). A hole that narrow is the filter's artefact, not
    background between two strands: two strands that close sew as one
    thread anyway."""
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


def extract_strands(sp, cfg) -> tuple[list[dict], dict]:
    """-> (strands, census). Each strand: `pts` (mm polyline), `polarity`,
    `length_mm`, `contrast` (L*), `strength` (median 1 + tanh(gain x H) on
    its pixels; the detector's floor is tau = 0.5). The census counts what
    the detector found and what the ridge test refused, per polarity."""
    from .stage6_detail import FDOG_RESPONSE_GAIN
    prof = machine.thread_profile(cfg.thread_wt)
    sampler, gray = field_gray(sp)
    tangent, coherence = sampler.field.tangent, sampler.field.coherence
    light = _light(sp)
    src_px = 1.0 / sp.px_per_mm
    core = 0.5 * prof.hairline_run_width_mm
    side0 = 0.5 * prof.hairline_max_width_mm
    side1 = side0 + _SIDE_REACH_PX * src_px
    step = _PROFILE_STEP_WIDTHS * prof.width_mm
    census = {"found": {}, "refused_no_ridge": {}}
    strands: list[dict] = []
    for polarity, g in (("dark", gray), ("light", 1.0 - gray)):
        H = fdog_response(g, tangent)
        lmap = _fill_slits(fdog_threshold(H, tangent, coherence))
        lines = lines_from_map(lmap, sp, sampler.scale, min_len_mm=0.0)
        census["found"][polarity] = len(lines)
        refused = 0
        resp = 1.0 + np.tanh(FDOG_RESPONSE_GAIN * H.astype(np.float64))
        hh, ww = resp.shape
        for pts in lines:
            c = ridge_contrast(pts, light, sp, polarity=polarity, core_mm=core,
                               side0_mm=side0, side1_mm=side1, step_mm=step)
            if c < _SRC_MIN_CONTRAST:
                refused += 1
                continue
            rs = []
            for x, y in pts:
                px, py = sp.to_px(x, y)
                xi = min(max(int(round(px * sampler.scale)), 0), ww - 1)
                yi = min(max(int(round(py * sampler.scale)), 0), hh - 1)
                rs.append(resp[yi, xi])
            length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
            strands.append({"pts": pts, "polarity": polarity, "length_mm": length,
                            "contrast": c, "strength": float(np.median(rs))})
        census["refused_no_ridge"][polarity] = refused
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


def strand_blocks(sp, cfg, *, entry, trim_at_mm: float,
                  allowed_threads: list[int]) -> tuple[list[tuple[int, list[StitchRun]]], dict]:
    """The line route for one design -> ([(thread_index, runs)], report).

    Report: `strands` (sewn), `dropped` (strand-tested lines under the loop
    floor, or with nothing left after the needle floor), `jumps`, and the
    extraction census (`found`, `refused_no_ridge`, per polarity)."""
    prof = machine.thread_profile(cfg.thread_wt)
    strands, census = extract_strands(sp, cfg)
    report = {"strands": 0, "dropped": 0, "jumps": 0, **census,
              "sewn_by_polarity": {}}
    tol = _CURL_TOL_WIDTHS * prof.hairline_run_width_mm
    out: list[tuple[int, list[StitchRun]]] = []
    cur = entry
    for polarity in ("dark", "light"):
        group = [s for s in strands if s["polarity"] == polarity]
        keep = []
        for s in group:
            if s["length_mm"] < machine.RUN_MIN_LOOP_MM:
                report["dropped"] += 1
                continue
            pts = stitch_path(s["pts"], cfg.hairline_stitch_mm, tol)
            if len(pts) < 2:
                report["dropped"] += 1
                continue
            keep.append((s, pts))
        report["sewn_by_polarity"][polarity] = len(keep)
        if not keep:
            continue
        thread = _thread_for([s for s, _ in keep], sp, cfg, allowed_threads)
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
                    jump = True
                    trim = d > trim_at_mm
                    report["jumps"] += 1
            runs.append(StitchRun(points=stitches.split_long_moves(pts),
                                  kind=stitches.RUN, jump=jump, trim=trim,
                                  shape_id=SHAPE_ID))
            cur = pts[-1]
        report["strands"] += len(runs)
        out.append((thread, runs))
    return out, report
