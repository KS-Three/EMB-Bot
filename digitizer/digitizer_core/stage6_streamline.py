"""Stage 6 — the streamline thread-paint tier (photo plan, technique-menu
row 10), FIRST SLICE: single color.

The plan's "what no auto tool has" tier: run stitches that FOLLOW image
structure — fur, hair, panel flow — instead of cutting across it at one
global angle. Two published pieces of math, composed:

1. **The direction field** (`directionfield.py`, technique row 6): structure
   tensor + ETF smoothing, already built and tested against analytic truth.
   This module is its first consumer.
2. **Evenly-spaced streamline placement, reimplemented from Jobard & Lefer,
   "Creating Evenly-Spaced Streamlines of Arbitrary Density" (Visualization
   in Scientific Computing '97)**. LICENSE NOTE, load-bearing: the plan doc
   flags Liu et al. CGF 2023's `embroidery-streamlines` repo as read-first
   but license-unverified — this code is written from the Jobard–Lefer
   paper's published algorithm alone (seed queue + d_sep/d_test spacing
   tests), not adapted from any repository.

The J–L algorithm, as implemented here: trace a streamline through the
tangent field from a seed, stepping both directions until it leaves the
region, enters highlight, or comes within `d_test = 0.5 * d_sep` of an
already-accepted streamline; every accepted streamline then queues candidate
seeds one `d_sep` to each side of each of its sample points, and a candidate
becomes a new streamline only if it still sits at least `d_sep` from
everything accepted so far. Seeds at d_sep, stop at d_test — that gap is the
paper's whole trick: lines settle at ~d_sep apart but may taper toward each
other before dying, which is what makes the texture read as flow rather
than as contour plot. A deterministic raster-order sweep re-seeds any
pocket the queue never reached (disconnected mask parts, shadow islands).

**Darkness modulates d_sep** (the row-10 spec: "d_sep = row pitch modulated
by luminance"): dark fabric gets tight spacing (`STREAMLINE_D_SEP_DARK_MM`),
light fabric gets sparse spacing, and above the highlight cutoff nothing
sews at all — fabric left bare as the highlight value, the same craft rule
the mono tiers document. A shape that is ENTIRELY highlight comes back
`empty`, honestly; stage 7's standing never-drop-artwork ladder then falls
back to tatami (bare-fabric-on-purpose is a review-screen delete, not a
fill tier's unilateral call).

**Low coherence falls back to the house angle** — the direction field's own
documented contract (`RegionDirection.use_house_angle`): where the region's
pixels do not agree on a direction (noise, flat color), the tangent field is
replaced by a constant field at the house angle and the same J–L machinery
emits evenly-spaced parallel lines. One code path, two behaviors, and the
fallback is measurably NOT spaghetti (angle uniformity is pinned in
`tests/test_stage6_streamline.py`).

Streamlines are resampled at `STREAMLINE_STITCH_MM` (the plan's 2.5–4 mm
run-stitch band) and emitted as run geometry: `(runs, report)` with the
shared tier contract (`too_thin` / `jumps` / `empty`), mm / y-down
coordinates, `SourcePixels` as the window onto the pre-quantize raster —
exactly how `stage6_blend` and the scan-line tier read tone. Underlay is
none: this is the fabric-as-value class (plan row 9's craft consensus).
Travel between streamlines reuses `stage6_fill.travel_path` — straight
inside the shape, along the edge, or an honest counted jump.

Strictly opt-in: nothing routes here except stage 7 on
`cfg.fill_technique == "streamline"`, and setting that flag is also what
makes `pipeline.run_stages` carry source pixels forward for non-gradient
classes — the flat lane grows no raster payload while the flag is off.

THE MULTI-COLOR SEAM (next slice, deliberately not built): the plan's full
row 10 is per-color-LAYER streamline sets, dark→light spool decomposition
(3–5 chart shades, layers sewn dark first), each layer's d_sep driven by
that shade's own coverage share rather than raw darkness. The seam is
`streamline_fill`'s signature: a layer decomposition would call the same
`_trace_streamlines` once per shade with a per-shade darkness map (shade
membership weight instead of luminance) and stack the returned polylines
into per-thread runs — everything below `streamline_fill` is already
per-map, nothing assumes "darkness" means luminance. Sequencing dark→light
is stage 5/7 layer ordering, not this module's concern.
"""
from __future__ import annotations

import math
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely.geometry import Point

from . import debugviz, machine, stitches
from .directionfield import compute_direction_field, region_direction
from .regions import Region
from .stage6_blend import SourcePixels
from .stage6_fill import _inset_ring, travel_path
from .stitches import StitchRun

# --- The darkness -> spacing mapping -----------------------------------------

# Streamline separation at full black. Two thread widths: solid-reading fur
# strokes without piling a satin-density mat of full-length runs.
STREAMLINE_D_SEP_DARK_MM = 0.8

# Separation just above the highlight cutoff — the sparsest line the tier
# draws before it draws nothing. 4x the dark end, the same light:dark ratio
# the scan-line tier's stride ladder spans.
STREAMLINE_D_SEP_LIGHT_MM = 3.2

# Below this darkness (luminance above ~0.92) nothing sews: fabric is the
# highlight value. Matches the scan-line tier's cutoff so the two mono tiers
# agree on what "highlight" means.
STREAMLINE_CUTOFF_DARKNESS = 0.08

# d_test = this fraction of local d_sep — the Jobard–Lefer termination
# distance. 0.5 is the paper's own recommendation: lines may approach to
# half their seeding distance before stopping, which is what lets them taper.
STREAMLINE_D_TEST_FRAC = 0.5

# --- Tracing -----------------------------------------------------------------

# Integration step (RK2 midpoint). One thread width: fine enough to follow
# stitch-scale curvature, and it doubles as the sample spacing the spacing
# grid stores, so proximity tests see the line as a line rather than dots.
STREAMLINE_STEP_MM = 0.4

# A streamline may not re-approach its OWN samples closer than d_test unless
# they are within this many steps behind the head — the loop-closure guard
# (a field cell rotating 360 degrees would otherwise trace a spiral forever).
# 20 steps = 8 mm of arc; nothing at stitch scale curls tighter on purpose.
STREAMLINE_SELF_GAP_STEPS = 20

# Hard caps, safety only: 2000 steps/direction is 800 mm of run — four times
# across the biggest hoop — and a shape will never legitimately hold more
# streamlines than its area over (min d_sep)^2.
STREAMLINE_MAX_STEPS_PER_DIR = 2000
STREAMLINE_MAX_LINES = 20000

# --- Emission ----------------------------------------------------------------

# Resample pitch: the plan's own band for streamline run stitches is
# 2.5–4 mm; 3.0 is its center and FILL_STITCH_MM, the corpus-median run.
# Each polyline divides its arc length into equal steps nearest this pitch,
# so every emitted stitch lands in the band except on lines shorter than
# one full stitch.
STREAMLINE_STITCH_MM = machine.FILL_STITCH_MM

# A streamline shorter than this is the needle re-entering its own holes,
# not a flow stroke. Two needle-floor stitches.
STREAMLINE_MIN_LEN_MM = 2.0

# Needle-down travel between streamlines is only allowed across gaps up to
# this long — 2.5x the sparsest line spacing, so a hop to a neighbouring
# stroke stays sewn (it lands beside thread that hides it) while anything
# longer becomes a counted jump instead. This tier leaves fabric bare on
# purpose and has no covering topcoat, so a long needle-down bridge is a
# visible float ACROSS THE ART by construction — measured on the drone
# fixture before this cap existed: 11 bridges over 8 mm, the worst 55.9 mm
# straight across the design. A trim is invisible; that is not.
STREAMLINE_TRAVEL_MAX_MM = 8.0

# Tone is sampled at grain scale, not pixel scale — same rationale and same
# number as the scan-line tier: one dark pixel of JPEG noise must not summon
# a streamline.
STREAMLINE_BLUR_MM = 0.6

# The direction field is computed on a downscaled raster capped at this many
# pixels on the long side. Direction is scale-local: at any real hoop size
# this still leaves several field pixels per millimetre, and full-resolution
# ETF costs tens of seconds for no directional information a stitch can use
# (measured in test_directionfield's own drone-render note).
_FIELD_MAX_DIM = 512


# --- Field access ------------------------------------------------------------

class _FieldSampler:
    """The design's direction field, computed once per SourcePixels and
    sampled in mm space. Cached on the SourcePixels instance itself (the
    same lifetime as the raster it derives from) so a multi-shape design
    pays for ETF exactly once."""

    def __init__(self, sp: SourcePixels):
        h, w = sp.rgb.shape[:2]
        self.scale = min(1.0, _FIELD_MAX_DIM / max(h, w))
        if self.scale < 1.0:
            small = cv2.resize(sp.rgb, (max(1, int(round(w * self.scale))),
                                        max(1, int(round(h * self.scale)))),
                               interpolation=cv2.INTER_AREA)
        else:
            small = sp.rgb
        self.field = compute_direction_field(small)
        self.sp = sp

    def _px(self, x_mm: float, y_mm: float) -> tuple[int, int]:
        px, py = self.sp.to_px(x_mm, y_mm)
        h, w = self.field.coherence.shape
        xi = min(max(int(round(px * self.scale)), 0), w - 1)
        yi = min(max(int(round(py * self.scale)), 0), h - 1)
        return xi, yi

    def tangent_at(self, x_mm: float, y_mm: float) -> tuple[float, float]:
        xi, yi = self._px(x_mm, y_mm)
        tx, ty = self.field.tangent[yi, xi]
        return float(tx), float(ty)

    def region_summary(self, poly) -> "RegionDirection":
        """`directionfield.region_direction` over the polygon, rasterized
        onto the (possibly downscaled) field grid with the same
        to_px-then-fillPoly convention the polygon API uses."""
        mask = np.zeros(self.field.coherence.shape, np.uint8)

        def ring_px(coords) -> np.ndarray:
            pts = []
            for x, y in coords:
                px, py = self.sp.to_px(x, y)
                pts.append((px * self.scale, py * self.scale))
            return np.array(pts, np.int32)

        cv2.fillPoly(mask, [ring_px(poly.exterior.coords)], 255)
        for hole in poly.interiors:
            cv2.fillPoly(mask, [ring_px(hole.coords)], 0)
        return region_direction(self.field, mask.astype(bool))


def _field_for(sp: SourcePixels) -> _FieldSampler:
    cached = getattr(sp, "_streamline_field", None)
    if cached is None:
        cached = _FieldSampler(sp)
        sp._streamline_field = cached
    return cached


def _darkness_sampler(sp: SourcePixels):
    """-> darkness(x_mm, y_mm) in [0, 1], bilinear over a grain-scale blur
    of the source luminance. Deterministic — no RNG anywhere in this tier."""
    gray = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0
    sigma = max(0.5, STREAMLINE_BLUR_MM * sp.px_per_mm)
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


def _d_sep(darkness: float) -> float:
    """Local streamline separation: dark = tight, light = sparse."""
    t = min(1.0, max(0.0, (darkness - STREAMLINE_CUTOFF_DARKNESS)
                     / (1.0 - STREAMLINE_CUTOFF_DARKNESS)))
    return (STREAMLINE_D_SEP_LIGHT_MM
            + (STREAMLINE_D_SEP_DARK_MM - STREAMLINE_D_SEP_LIGHT_MM) * t)


# --- The Jobard–Lefer placement ----------------------------------------------

class _SampleGrid:
    """Spatial hash over every accepted streamline sample. Cell size is the
    MAXIMUM d_sep, so any query radius the tier ever uses is answered by the
    3x3 cell neighborhood."""

    def __init__(self):
        self.cell = STREAMLINE_D_SEP_LIGHT_MM
        self.cells: dict[tuple[int, int], list[int]] = {}
        self.pts: list[tuple[float, float]] = []
        self.line: list[int] = []
        self.step: list[int] = []

    def _key(self, x: float, y: float) -> tuple[int, int]:
        return (int(math.floor(x / self.cell)), int(math.floor(y / self.cell)))

    def add(self, x: float, y: float, line_id: int, step_idx: int) -> None:
        idx = len(self.pts)
        self.pts.append((x, y))
        self.line.append(line_id)
        self.step.append(step_idx)
        self.cells.setdefault(self._key(x, y), []).append(idx)

    def blocked(self, x: float, y: float, radius: float,
                own_line: int | None = None, own_step: int = 0) -> bool:
        """Any sample within `radius`? Samples on `own_line` block only when
        they sit more than the self-gap behind the head (loop closure);
        recent own samples are the line's own tail and never block."""
        r2 = radius * radius
        kx, ky = self._key(x, y)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                for idx in self.cells.get((kx + dx, ky + dy), ()):
                    px, py = self.pts[idx]
                    if (px - x) ** 2 + (py - y) ** 2 >= r2:
                        continue
                    if (own_line is not None and self.line[idx] == own_line
                            and abs(own_step - self.step[idx]) <= STREAMLINE_SELF_GAP_STEPS):
                        continue
                    return True
        return False


def _orient(t: tuple[float, float], ref: tuple[float, float]) -> tuple[float, float]:
    """A tangent names a line, not a ray (directionfield's contract): pick
    the sign that continues in `ref`'s direction. A zero tangent (flat
    pixel the ETF could not reach) coasts straight on."""
    tx, ty = t
    if tx == 0.0 and ty == 0.0:
        return ref
    if tx * ref[0] + ty * ref[1] < 0.0:
        return (-tx, -ty)
    return (tx, ty)


def _trace_streamlines(poly, tangent_at, darkness, seeds_hint: list[tuple[float, float]]
                       ) -> list[list[tuple[float, float]]]:
    """Jobard–Lefer evenly-spaced streamline placement over `poly`.

    `tangent_at(x, y)` is the (line-convention) direction field;
    `darkness(x, y)` drives local d_sep and the highlight cutoff;
    `seeds_hint` is the deterministic raster-order sweep of fallback seeds
    (queue-generated candidates always take priority, per the paper).

    -> accepted streamlines as mm polylines at STREAMLINE_STEP_MM pitch.
    """
    room = shapely.from_wkb(shapely.to_wkb(poly))
    shapely.prepare(room)
    grid = _SampleGrid()
    lines: list[list[tuple[float, float]]] = []

    def valid_point(x: float, y: float) -> bool:
        return (room.covers(Point(x, y))
                and darkness(x, y) >= STREAMLINE_CUTOFF_DARKNESS)

    def trace_dir(x: float, y: float, ref: tuple[float, float], line_id: int,
                  step_sign: int) -> list[tuple[float, float]]:
        """One direction from the seed (RK2 midpoint), seed point excluded."""
        out: list[tuple[float, float]] = []
        px, py = x, y
        d = ref
        for i in range(1, STREAMLINE_MAX_STEPS_PER_DIR + 1):
            d0 = _orient(tangent_at(px, py), d)
            if d0 == (0.0, 0.0):
                break
            mx, my = px + 0.5 * STREAMLINE_STEP_MM * d0[0], py + 0.5 * STREAMLINE_STEP_MM * d0[1]
            d1 = _orient(tangent_at(mx, my), d0)
            n = math.hypot(*d1)
            if n < 1e-12:
                break
            nx = px + STREAMLINE_STEP_MM * d1[0] / n
            ny = py + STREAMLINE_STEP_MM * d1[1] / n
            if not valid_point(nx, ny):
                break
            if grid.blocked(nx, ny, STREAMLINE_D_TEST_FRAC * _d_sep(darkness(nx, ny)),
                            own_line=line_id, own_step=i * step_sign):
                break
            out.append((nx, ny))
            grid.add(nx, ny, line_id, i * step_sign)
            px, py, d = nx, ny, d1
        return out

    queue: deque[tuple[float, float]] = deque()

    def try_line(sx: float, sy: float) -> bool:
        """Seed acceptance (>= d_sep from everything), then the trace."""
        if not valid_point(sx, sy):
            return False
        if grid.blocked(sx, sy, _d_sep(darkness(sx, sy))):
            return False
        d0 = tangent_at(sx, sy)
        if d0 == (0.0, 0.0):
            return False
        line_id = len(lines)
        grid.add(sx, sy, line_id, 0)
        fwd = trace_dir(sx, sy, d0, line_id, +1)
        bwd = trace_dir(sx, sy, (-d0[0], -d0[1]), line_id, -1)
        pts = list(reversed(bwd)) + [(sx, sy)] + fwd
        lines.append(pts)
        # Candidate seeds one LOCAL d_sep to each side of each sample — the
        # paper's queue. Normals come from the line's own step direction.
        for j in range(1, len(pts)):
            ax, ay = pts[j - 1]
            bx, by = pts[j]
            seg = math.hypot(bx - ax, by - ay)
            if seg < 1e-9:
                continue
            nx, ny = -(by - ay) / seg, (bx - ax) / seg
            sep = _d_sep(darkness(bx, by))
            queue.append((bx + nx * sep, by + ny * sep))
            queue.append((bx - nx * sep, by - ny * sep))
        return True

    for hx, hy in seeds_hint:
        if len(lines) >= STREAMLINE_MAX_LINES:
            break
        try_line(hx, hy)
        # Drain the queue before the sweep advances: queue-driven seeds are
        # what produce the even d_sep lattice; the sweep only rescues
        # pockets the lattice could not reach from here.
        while queue and len(lines) < STREAMLINE_MAX_LINES:
            qx, qy = queue.popleft()
            try_line(qx, qy)
    return lines


def _sweep_seeds(poly) -> list[tuple[float, float]]:
    """Deterministic raster-order fallback seeds: a grid at the DARK d_sep
    over the polygon bounds. Most are rejected in one distance query each;
    they exist so no disconnected pocket of the mask goes unseeded."""
    minx, miny, maxx, maxy = poly.bounds
    step = STREAMLINE_D_SEP_DARK_MM
    out = []
    ny = max(1, int(math.ceil((maxy - miny) / step)))
    nx = max(1, int(math.ceil((maxx - minx) / step)))
    for iy in range(ny + 1):
        for ix in range(nx + 1):
            out.append((minx + ix * step, miny + iy * step))
    return out


# --- Resampling and emission --------------------------------------------------

def _resample(pts: list[tuple[float, float]], pitch: float
              ) -> list[tuple[float, float]] | None:
    """Arc-length resample at ~pitch (equal steps nearest it), or None for a
    line too short to be a stitch stroke at all."""
    if len(pts) < 2:
        return None
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    total = sum(seg)
    if total < STREAMLINE_MIN_LEN_MM:
        return None
    n = max(1, round(total / pitch))
    targets = [total * i / n for i in range(1, n)]
    out = [pts[0]]
    acc = 0.0
    j = 0
    for t in targets:
        while j < len(seg) and acc + seg[j] < t:
            acc += seg[j]
            j += 1
        if j >= len(seg):
            break
        f = (t - acc) / seg[j] if seg[j] > 1e-12 else 0.0
        ax, ay = pts[j]
        bx, by = pts[j + 1]
        out.append((ax + (bx - ax) * f, ay + (by - ay) * f))
    out.append(pts[-1])
    return out


def streamline_fill(region: Region, source_pixels: SourcePixels, cfg
                    ) -> tuple[list[StitchRun], dict]:
    """One shape -> its streamline runs plus the standard tier report.

    Same `(runs, report)` contract as `stitch_shape` and every stage-6
    sibling: `too_thin`, `jumps` (needle lifts this tier itself raised),
    `empty` (produced nothing — for this tier that includes "the shape is
    entirely highlight", a correct outcome; stage 7's fallback ladder
    decides what happens next). Extras, informational: `streamlines`
    (emitted polylines), `house_fallback` (the low-coherence parallel-line
    path was taken), `field_coherence` (the region summary the gate read).
    """
    poly = region.polygon
    report = {"too_thin": False, "jumps": 0, "empty": False,
              "streamlines": 0, "house_fallback": False, "field_coherence": 0.0}
    if poly.is_empty:
        report["empty"] = True
        return [], report
    if poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
        report["too_thin"] = True

    darkness = _darkness_sampler(source_pixels)
    sampler = _field_for(source_pixels)
    rd = sampler.region_summary(poly)
    report["field_coherence"] = round(rd.coherence, 4)

    if rd.use_house_angle:
        # The direction field's own documented fallback: the region's pixels
        # do not agree on a direction, so its angle is noise. The HOUSE
        # angle takes over — per-shape review override > global config > the
        # classic horizontal — and the same J–L machinery draws parallel
        # lines through a constant field.
        report["house_fallback"] = True
        shape_angle = region.meta.get("fill_angle_deg")
        angle = (float(shape_angle) if shape_angle is not None
                 else cfg.fill_angle_deg if cfg.fill_angle_deg is not None
                 else 0.0)
        a = math.radians(angle)
        const = (math.cos(a), math.sin(a))

        def tangent_at(x: float, y: float) -> tuple[float, float]:
            return const
    else:
        # A coherent region can still hold locally FLAT pixels (zero
        # gradient, beyond ETF's propagation reach — the middle of a solid
        # dark patch). Those must not become bare holes in a dark area, so
        # a zero tangent inherits the region's own dominant angle instead
        # of refusing to seed.
        ra = math.radians(rd.angle_deg)
        region_dir = (math.cos(ra), math.sin(ra))

        def tangent_at(x: float, y: float) -> tuple[float, float]:
            t = sampler.tangent_at(x, y)
            return t if t != (0.0, 0.0) else region_dir

    lines = _trace_streamlines(poly, tangent_at, darkness, _sweep_seeds(poly))

    paths = []
    for pts in lines:
        r = _resample(pts, STREAMLINE_STITCH_MM)
        if r is not None:
            paths.append(r)
    report["streamlines"] = len(paths)

    # Sew order: nearest-neighbour over the polylines, each entered from
    # whichever end is closer — the same economy _fill_paths applies to its
    # columns. Deterministic: rounded distance, then index, then end.
    ordered: list[list[tuple[float, float]]] = []
    remaining = list(range(len(paths)))
    cur: tuple[float, float] | None = None
    while remaining:
        if cur is None:
            pick, flip = remaining[0], 0
        else:
            best = None
            for i in remaining:
                for fb in (0, 1):
                    end = paths[i][0] if fb == 0 else paths[i][-1]
                    key = (round(math.dist(cur, end), 6), i, fb)
                    if best is None or key < best[0]:
                        best = (key, i, fb)
            pick, flip = best[1], best[2]
        pts = paths[pick] if flip == 0 else list(reversed(paths[pick]))
        remaining.remove(pick)
        ordered.append(pts)
        cur = pts[-1]

    runs: list[StitchRun] = []
    ring = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    for path in ordered:
        pts = stitches.split_long_moves(path, machine.MAX_STITCH_MM)
        if len(pts) < 2:
            continue
        if runs:
            d = math.dist(runs[-1].points[-1], pts[0])
            bridge = (travel_path(poly, ring, runs[-1].points[-1], pts[0], slack)
                      if d <= STREAMLINE_TRAVEL_MAX_MM else None)
            if bridge is None:
                report["jumps"] += 1
                runs.append(StitchRun(points=pts, kind=stitches.FILL, jump=True,
                                      trim=d > machine.TRIM_AT_MM,
                                      shape_id=region.shape_id))
                continue
            middle = bridge[:-1]
            if middle:
                runs.append(StitchRun(points=middle, kind=stitches.TRAVEL,
                                      shape_id=region.shape_id))
        runs.append(StitchRun(points=pts, kind=stitches.FILL,
                              shape_id=region.shape_id))

    if not runs:
        report["empty"] = True

    if cfg.debug_dir and runs:
        minx, miny, maxx, maxy = poly.bounds
        debugviz.stage6_streamline_paths(Path(cfg.debug_dir), runs,
                                         (maxx - minx, maxy - miny))

    return runs, report
