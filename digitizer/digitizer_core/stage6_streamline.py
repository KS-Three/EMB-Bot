"""Stage 6 — the streamline thread-paint tier (photo plan, technique-menu
row 10). Two slices, both here: mono (single color, the first slice) and
layered (the multi-color seam, below).

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
`cfg.fill_technique == "streamline"` (design-wide) or one shape's
review-screen `tier: "streamline"` override (shape-layers contract v1.6,
added alongside `tier: "sketch"`'s per-shape form) — and setting either is
also what makes `pipeline.run_stages` carry source pixels forward for
non-gradient classes: the flat lane grows no raster payload while neither
is set. Despite the module's row-10 framing (born in, and still primarily
exercised by, the photo-digitizing plan), NEITHER opt-in path is gated on
`design_class` anywhere in `stage7_sequence.py` — a manually-classified
("flat") design can select streamline fill on one shape, or on the whole
design, exactly like `tatami`/`contour`/`sketch` can. The direction field
it reads is always `directionfield.py`'s structure-tensor/ETF field over
this design's OWN prepped raster (`SourcePixels.rgb` — whatever art the
job was given, not necessarily a photograph), never a shape-geometry-
derived field (no medial-axis/skeleton tangent construction exists in this
codebase for that): a flat-lane shape with real raster texture (an
embossed logo, a scanned sketch, antialiased shading) gets genuine
structure-following lines the same way a photo does, and a shape whose
raster is genuinely flat/textureless gets the coherence gate's own
documented fallback — evenly-spaced PARALLEL lines at the shape's
`fill_angle_deg` override (or the house angle), never a crash or a
degenerate spiral. See `stage7_sequence.stitch_one`'s streamline branch
for the full per-shape precedence and the reasoning for not building a
shape-geometry-derived field instead.

THE MULTI-COLOR SEAM (second slice, built): the plan's full row 10 is
per-color-LAYER streamline sets, dark→light spool decomposition (3-5 chart
shades, layers sewn dark first), each layer's d_sep driven by that shade's
own coverage share rather than raw darkness. `cfg.streamline_mode ==
"layered"` (mono, the first slice, stays the default) routes here:
`_shade_layers` decomposes the region's own pixels into 3-5 chart shades —
reusing `stage6_blend`'s shade-selection machinery (`_sample_pixels`,
`_choose_shade_count`, `_shade_lab_colors`, `threads.chart_for`) rather than
reinventing it, the same way `darkness_sampler` was hoisted to `stage6_blend`
during the meander tier's build — and turns each shade's canonical position
into a triangular COVERAGE-SHARE map over this tier's own darkness field: 1.0
where that shade fully owns the pixel, tapering to 0 at the neighbouring
shades' centers, summing to 1 across shades at every point. `_trace_streamlines`
is then called once per shade with that map standing in for "darkness" —
nothing below it (`_d_sep`, the highlight cutoff, `_SampleGrid`) assumes
"darkness" means luminance, so the same function produces one evenly-spaced
streamline set per shade unmodified. One exception, deliberate: the
highlight cutoff itself is checked against RAW darkness inside each
membership map, not against the shade's own coverage share — a pixel the
raw image already reads as bare fabric must stay bare regardless of which
chart shade happens to be nearest it (the "lightest" shade's own canonical
position is, after all, near-white, so its raw-darkness-blind coverage
share would otherwise be highest exactly where nothing should sew at all).

`_trace_layer` (the mono slice's own trace/resample/order/emit sequence,
factored out so both modes share it) runs once per shade, and the layers
stack dark shade first: every shade boundary
is an unconditional colour change (`jump=True, trim=True` forced on the new
layer's first run, mirroring stage 7's own per-block forcing) and never
travel-bridged, because a spool change cuts thread regardless of what the
geometry would allow — sequencing WHICH shade becomes which physical thread
stop is still stage 5/7's concern (report carries `shade_thread_idx` /
`shade_rgb` dark-to-light for that), this module's job ends at hand-back.
The 8 mm no-topcoat travel cap (`STREAMLINE_TRAVEL_MAX_MM`) is unchanged by
this slice: it only ever gated bridging WITHIN one shade's own coverage-share
map, the same class of region the mono slice already measured it against,
and inter-layer boundaries never attempt a bridge at all.
"""
from __future__ import annotations

import math
from collections import deque
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely.geometry import Point
from skimage.color import deltaE_ciede2000

from . import debugviz, machine, stitches
from .directionfield import (RegionDirection, compute_direction_field,
                             region_direction)
from .regions import Region
from .stage6_blend import (SourcePixels, _choose_shade_count, _sample_pixels,
                           _shade_lab_colors)
from .stage6_fill import _inset_ring, travel_path
from .stitches import StitchRun
from .threads import chart_for, rgb_to_lab

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

    def region_summary(self, poly) -> RegionDirection:
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


# --- The multi-color seam: per-shade coverage-share decomposition -----------

# A region's own pixel population must clear this before shade decomposition
# is trusted at all — the same floor `stage6_blend.detect_ramp` applies to
# its own per-region sample before fitting a model. Below it there is no
# reliable signal to split into shades, so `_shade_layers` degrades to one
# shade (this region's already-assigned thread, full coverage everywhere) —
# mono in every way but name, never a crash on a sliver region.
_SHADE_MIN_SAMPLES = 12
# Below this darkness span, `cfg.shade_axis_normalize` leaves the axis
# absolute. Measured per-shape spans run median 0.21-0.38 (region-
# identification diagnosis, defect 1), so a real tonal region clears this by
# an order of magnitude; what it excludes is the flat region whose whole
# range is sampling noise, where normalising would stretch that noise across
# the full axis and invent shade structure that is not in the artwork.
_SHADE_AXIS_MIN_SPAN = 0.02


def _shade_layers(poly, source_pixels: SourcePixels, base_darkness, region: Region,
                  cfg, *, palette_indices: list[int] | None = None
                  ) -> list[tuple[int, tuple[int, int, int], object]]:
    """3-5 chart-shade decomposition of this region's own pixels, DARK SHADE
    FIRST. Each entry is `(thread_index, rgb, membership)`, where
    `membership(x_mm, y_mm) -> [0, 1]` is that shade's COVERAGE SHARE at a
    point — not luminance, per the docstring's "multi-color seam": a
    triangular split of `base_darkness` (this tier's own darkness field, the
    same one the mono slice drives `_trace_streamlines` with directly)
    against the shade's canonical position on the same [0, 1] scale
    `_shade_lab_colors` already uses (0 = light end, 1 = dark end), so shade
    i's membership is 1.0 exactly where `base_darkness` equals its own
    center, tapers linearly to 0 at each neighbour's center, and — because
    the centers are evenly spaced and every point falls between at most two
    of them — the shares sum to 1 at every point: a partition, not an
    independent per-shade re-measurement.

    Shade COUNT and COLOR reuse `stage6_blend`'s own machinery verbatim
    (`_sample_pixels`, `_choose_shade_count`, `_shade_lab_colors`,
    `threads.chart_for`) rather than reimplementing the CIEDE2000 chart snap
    — the house rule against near-duplicate logic that could drift, the same
    reason `darkness_sampler` was hoisted to `stage6_blend` during the
    meander tier's build. `base_darkness` (not the ramp position
    `blend_fill` buckets on) is what drives BOTH the shade split here and
    every downstream `_trace_streamlines` call — a photo region has no ramp
    to fit, only the same source-darkness field this tier has always read.

    **`palette_indices` (keyword-only, default None) is the shade-palette
    bind — `cfg.shade_palette_bind`, option (a) of
    docs/superpowers/plans/2026-08-23-shade-palette-binding.md, ON by default
    on the photo route since Kent's 2026-08-24 ruling.** None (or
    empty — the defensive degrade `revalidate_threads`' palette argument
    also has) is the full-chart `chart.nearest_index` snap this function has
    always run, byte-identical by construction. A non-empty list masks the
    snap to those chart indices: each shade still gets the perceptually
    nearest (CIEDE2000) spool, chosen from the spools the caller's plan will
    actually load. Two adjacent shades landing on ONE palette spool then
    merge into a single layer whose membership is the sum of their tents — a
    trapezoid: 1.0 across the merged centers' whole span, tapering to 0 one
    knot outside it, so the shares across layers still sum to 1 at every
    point (the partition survives the merge; a singleton "group" reduces to
    exactly the original tent). The merge is the honest half: `_shade_blocks`
    (stage 7) already buckets same-spool shades at the block level, so the
    sew side degrades gracefully without it — but the DECOMPOSITION (layer
    count, report fields, per-layer streamline sets) would keep listing
    shades that only look distinct. Non-adjacent shades on one spool stay
    separate layers, deliberately — their tents are not contiguous, a
    combined membership would sew the intervening shade's band too, and
    stage 7's bucketing already reunites them at sew time (its own
    docstring's "two non-adjacent bands can snap to the same cone" case).
    Gating (photo classes only, flag off = never) is the CALLER's job —
    `stage7_sequence.sequence` derives and passes the palette; this function
    only obeys the argument, mirroring how `revalidate_threads` obeys its
    own.
    """
    mm_x, mm_y, rgb, _mask, _crop = _sample_pixels(poly, source_pixels)
    if len(mm_x) < _SHADE_MIN_SAMPLES:
        rgb0 = tuple(int(v) for v in chart_for(cfg)[region.thread_index].rgb)
        return [(region.thread_index, rgb0, base_darkness)]

    ts = np.array([base_darkness(x, y) for x, y in zip(mm_x, mm_y)])
    lab = rgb_to_lab(rgb)
    extremes_delta_e = float(
        deltaE_ciede2000(lab[np.argmin(ts): np.argmin(ts) + 1],
                         lab[np.argmax(ts): np.argmax(ts) + 1])[0]
    )
    n = _choose_shade_count(extremes_delta_e)
    # The shade darkness axis (cfg.shade_axis_normalize — EXPERIMENT, default
    # off; config.py's comment carries the measurement). `lo`/`span` are
    # derived ONCE here and used by both the colour bucketing just below and
    # the membership tents further down, because those two have to describe
    # the same axis: a shade's colour is the mean of the samples nearest its
    # centre, so if the centre moves for one and not the other, the colour
    # stops describing where the tent peaks.
    #
    # Flag off is lo=0.0, span=1.0 — every expression reduces to the absolute
    # axis and the arithmetic is a no-op, which is the byte-identity
    # guarantee rather than a separate code path to keep in step.
    lo, span = 0.0, 1.0
    if cfg.shade_axis_normalize and len(ts):
        t_lo, t_hi = float(ts.min()), float(ts.max())
        # A span this small is a flat region, not a ramp: normalising it
        # would blow sampling noise up to the full axis and invent shade
        # structure out of nothing. Absolute is the honest fallback.
        if t_hi - t_lo >= _SHADE_AXIS_MIN_SPAN:
            lo, span = t_lo, t_hi - t_lo
    shade_labs = _shade_lab_colors((ts - lo) / span, lab, n)

    chart = chart_for(cfg)
    if palette_indices:
        # The shade-palette bind (docstring above): the same masked-argmin
        # shape `revalidate_threads`' own binding uses — the full per-spool
        # CIEDE2000 row, argmin restricted to the allowed subset — so the
        # two bindings cannot drift into two definitions of "nearest in the
        # palette".
        allowed = np.unique(np.asarray(list(palette_indices), dtype=np.int64))

        def _nearest_allowed(c: np.ndarray) -> int:
            ref = np.repeat(np.asarray(c, dtype=np.float64).reshape(1, 3),
                            len(allowed), axis=0)
            return int(allowed[int(np.argmin(
                deltaE_ciede2000(ref, chart.lab[allowed])))])

        thread_idx = [_nearest_allowed(c) for c in shade_labs]
    else:
        thread_idx = [chart.nearest_index(c) for c in shade_labs]
    rgbs = [tuple(int(v) for v in chart[t].rgb) for t in thread_idx]

    centers = [i / (n - 1) for i in range(n)]
    knot = 1.0 / (n - 1)

    def _membership_for(center: float):
        def membership(x: float, y: float) -> float:
            d = base_darkness(x, y)
            # The highlight cutoff is a fact about the FABRIC, not about
            # which shade a pixel is closest to: raw darkness below it means
            # bare fabric already reads as the highlight value (module
            # docstring, "darkness modulates d_sep"), and stitching even the
            # lightest chart shade there would be thread spent for no visual
            # change. That craft rule overrides every shade's own coverage
            # share, so it is checked against `base_darkness` here, before
            # the per-shade tent — not left to `_trace_streamlines`' own
            # cutoff test, which only ever sees whatever map THIS closure
            # hands it and has no notion of "raw" left to fall back on.
            if d < STREAMLINE_CUTOFF_DARKNESS:
                return 0.0
            # Onto the same axis the shade colours were bucketed on. Flag off
            # is lo=0.0/span=1.0, so this is `d` unchanged.
            return max(0.0, 1.0 - abs((d - lo) / span - center) / knot)
        return membership

    if palette_indices:
        # Merge ADJACENT same-spool shades (docstring above). Group runs of
        # equal bound spool over the light->dark center order, then give
        # each group the sum of its members' tents in closed form: a
        # trapezoid at 1.0 over [c_lo, c_hi] (adjacent tents already sum to
        # exactly 1 between their centers) falling to 0 one knot outside —
        # for a single-member group c_lo == c_hi and this IS the tent
        # `_membership_for` builds, same cutoff check first.
        def _band_membership_for(c_lo: float, c_hi: float):
            def membership(x: float, y: float) -> float:
                d = base_darkness(x, y)
                if d < STREAMLINE_CUTOFF_DARKNESS:
                    return 0.0
                if d < c_lo:
                    return max(0.0, 1.0 - (c_lo - d) / knot)
                if d > c_hi:
                    return max(0.0, 1.0 - (d - c_hi) / knot)
                return 1.0
            return membership

        groups: list[tuple[int, int]] = []  # inclusive [first, last] shade runs
        start = 0
        for i in range(1, n + 1):
            if i == n or thread_idx[i] != thread_idx[start]:
                groups.append((start, i - 1))
                start = i
        shades = [(thread_idx[a], rgbs[a],
                   _band_membership_for(centers[a], centers[b]))
                  for a, b in groups]
    else:
        shades = [(thread_idx[i], rgbs[i], _membership_for(centers[i])) for i in range(n)]
    # `centers` ascends light -> dark (index 0 is `_shade_lab_colors`' own
    # t=0 canonical position), so dark-shade-first is simply the reverse.
    shades.reverse()
    return shades


def _trace_layer(poly, tangent_at, darkness_map, ring, slack, shape_id: str
                 ) -> tuple[list[StitchRun], int, int]:
    """One shade's full trace-through-emission pass: the mono slice's own
    `_trace_streamlines` -> resample -> nearest-neighbour order -> travel-
    bridged emission sequence, factored out unchanged so the layered mode
    can run it once per shade (the docstring's "call the same
    `_trace_streamlines` once per shade with a per-shade darkness map") with
    no drift from what the mono slice already measures and tests.

    -> (this shade's runs, streamlines emitted, needle lifts raised tracing
    this ONE shade — a colour change into or out of this layer is the
    caller's concern, not counted here).
    """
    lines = _trace_streamlines(poly, tangent_at, darkness_map, _sweep_seeds(poly))

    paths = []
    for pts in lines:
        r = _resample(pts, STREAMLINE_STITCH_MM)
        if r is not None:
            paths.append(r)

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
    jumps = 0
    for path in ordered:
        pts = stitches.split_long_moves(path, machine.MAX_STITCH_MM)
        if len(pts) < 2:
            continue
        if runs:
            d = math.dist(runs[-1].points[-1], pts[0])
            bridge = (travel_path(poly, ring, runs[-1].points[-1], pts[0], slack)
                      if d <= STREAMLINE_TRAVEL_MAX_MM else None)
            if bridge is None:
                jumps += 1
                runs.append(StitchRun(points=pts, kind=stitches.FILL, jump=True,
                                      trim=d > machine.TRIM_AT_MM,
                                      shape_id=shape_id))
                continue
            middle = bridge[:-1]
            if middle:
                runs.append(StitchRun(points=middle, kind=stitches.TRAVEL,
                                      shape_id=shape_id))
        runs.append(StitchRun(points=pts, kind=stitches.FILL,
                              shape_id=shape_id))
    return runs, len(paths), jumps


def streamline_fill(region: Region, source_pixels: SourcePixels, cfg,
                    *, darkness_scale: float = 1.0,
                    streamline_mode: str | None = None,
                    shade_palette_indices: list[int] | None = None,
                    ) -> tuple[list[StitchRun], dict]:
    """One shape -> its streamline runs plus the standard tier report.

    `darkness_scale` attenuates the darkness field every downstream decision
    reads — d_sep, the highlight cutoff, layered mode's shade split alike —
    before any of them see it. 1.0 (the default) adds no wrapper at all, so
    every existing caller is byte-identical by construction; the sketch tier
    (stage6_sketch, technique row 12) is the one caller that passes less,
    which is exactly how it buys sparser lines and more bare fabric out of
    this tier's machinery without owning a second copy of any of it.

    Same `(runs, report)` contract as `stitch_shape` and every stage-6
    sibling: `too_thin`, `jumps` (needle lifts this tier itself raised),
    `empty` (produced nothing — for this tier that includes "the shape is
    entirely highlight", a correct outcome; stage 7's fallback ladder
    decides what happens next). Extras, informational: `streamlines`
    (emitted polylines, every shade's total in layered mode), `house_fallback`
    (the low-coherence parallel-line path was taken), `field_coherence` (the
    region summary the gate read).

    `streamline_mode == "layered"` (default `"mono"`) is the multi-color
    seam (module docstring): `layers`, `shade_thread_idx`, `shade_rgb` and
    `streamlines_by_layer` (all dark-to-light order) are added to the report,
    and `runs` stacks every shade's own runs in that order with an
    unconditional colour change (`jump`/`trim` forced True, never
    travel-bridged) at each shade boundary. Mono mode's own code path is
    untouched — same calls, same order — so it stays byte-identical to the
    tier as it shipped before this mode existed.

    Task 3 fix round 1 (photo/tonal v1): `streamline_mode` is now also an
    explicit KEYWORD ARGUMENT, `None` by default. `None` means "read
    `cfg.streamline_mode` exactly as before" — every existing caller (every
    call site in this codebase before this round) passes nothing here and
    is byte-identical by construction. A caller that DOES pass a value
    (currently: `stage7_sequence.sequence`, threading photo_subject's
    automatic route through) overrides `cfg.streamline_mode` for this one
    call without mutating `cfg` — jobs cache on it. `stage6_sketch.sketch_
    fill`'s own `mono_cfg` (which forces `cfg.streamline_mode="mono"` via
    `dataclasses.replace` before calling this function) is unaffected
    either way: it never passes this new argument, so it keeps reading its
    own already-forced `mono_cfg.streamline_mode`.

    `shade_palette_indices` (2026-08-23, the `cfg.shade_palette_bind`
    experiment) rides the same keyword pattern: None — the default, and what
    every caller gets unless the flag is on AND the design class is photo
    (`stage7_sequence.sequence` owns that gate) — is byte-identical to the
    parameter not existing. Non-empty, it is handed to `_shade_layers` as
    the allowed spool subset for the layered mode's per-shade chart snap
    (see that function's docstring for the bind and the adjacent-same-spool
    merge); mono mode never reads it — there is no per-shade snap to bind.
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
    if darkness_scale != 1.0:
        raw = darkness

        def darkness(x_mm: float, y_mm: float) -> float:
            return darkness_scale * raw(x_mm, y_mm)
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

    ring = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)

    _mode = streamline_mode if streamline_mode is not None else cfg.streamline_mode
    layered = str(_mode or "mono").lower() == "layered"
    if layered:
        shades = _shade_layers(poly, source_pixels, darkness, region, cfg,
                               palette_indices=shade_palette_indices)
        runs: list[StitchRun] = []
        total_streamlines = 0
        shade_thread_idx = []
        shade_rgb = []
        streamlines_by_layer = []
        for i, (thread_idx, rgb, membership) in enumerate(shades):
            layer_runs, n_lines, layer_jumps = _trace_layer(
                poly, tangent_at, membership, ring, slack,
                f"{region.shape_id}-shade{i}")
            report["jumps"] += layer_jumps
            total_streamlines += n_lines
            shade_thread_idx.append(thread_idx)
            shade_rgb.append(rgb)
            streamlines_by_layer.append(n_lines)
            if not layer_runs:
                continue
            # Task 3 (photo/tonal v1): stamp the chart thread THIS shade
            # snapped to on every one of its own runs — the same field
            # `stage6_blend.blend_fill` stamps on its band runs (`stitches.
            # StitchRun.shade_thread_index`), and the one thing stage 7's
            # `_shade_blocks` reads to split a group's flat run list into
            # per-shade StitchBlocks. Unset here, every shade's runs default
            # to `None` and `_shade_blocks` buckets them all under the
            # region's single base thread — dark->light shade COUNT would
            # still be right (the report above already carries it), but the
            # design would sew in one spool regardless, silently discarding
            # the whole point of "layered". Mono mode's own runs are
            # deliberately left unstamped (`None`, stage 7's documented
            # "this run sews in the region's one thread" default): there is
            # only ever one shade there, so the field would name nothing
            # `_shade_blocks` doesn't already fall back to.
            for r in layer_runs:
                r.shade_thread_index = thread_idx
            if runs:
                # A shade boundary is always a genuine thread/colour change —
                # never bridged, exactly like stage 7's own per-block forcing
                # (`ordered[0].jump = True; ordered[0].trim = True`) for a
                # brand-new colour stop. Not counted in report["jumps"]: that
                # key is needle lifts THIS TIER raised inside one thread, and
                # a colour change is not that (stage 7 does not count its own
                # equivalent forcing either).
                layer_runs[0].jump = True
                layer_runs[0].trim = True
            runs.extend(layer_runs)
        report["streamlines"] = total_streamlines
        report["layers"] = len(shades)
        report["shade_thread_idx"] = shade_thread_idx
        report["shade_rgb"] = shade_rgb
        report["streamlines_by_layer"] = streamlines_by_layer
    else:
        runs, n_lines, layer_jumps = _trace_layer(
            poly, tangent_at, darkness, ring, slack, region.shape_id)
        report["jumps"] += layer_jumps
        report["streamlines"] = n_lines

    if not runs:
        report["empty"] = True

    if cfg.debug_dir and runs:
        minx, miny, maxx, maxy = poly.bounds
        debugviz.stage6_streamline_paths(Path(cfg.debug_dir), runs,
                                         (maxx - minx, maxy - miny))

    return runs, report
