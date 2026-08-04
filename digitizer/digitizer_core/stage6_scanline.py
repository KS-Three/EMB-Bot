"""Stage 6 — the scan-line mono tonal tier (photo plan, technique-menu row 8).

The PhotoFlash class: parallel scan rows across one grain, with local image
darkness deciding how much thread each stretch of row gets — the classic
newspaper-halftone / mono photo-stitch look. A sibling of `stage6_fill.py`
(tatami), `stage6_blend.py` (gradient blend) and the other tier modules, with
the same `(runs, report)` contract (`too_thin` / `jumps` / `empty`), the same
mm / y-down coordinates, and `SourcePixels` as its window onto the
pre-quantize raster — exactly how `stage6_blend` reads tone.

Darkness drives THREE things, each measurable from the emitted stitches:

1. **Which rows exist (row spacing).** Rows live on one base grid at
   `SCANLINE_ROW_MM` (0.45 mm — the top of Sfumato's published
   highest-density band, 0.35–0.45 mm, the plan's density bound for the mono
   tiers) and are decimated hierarchically by local darkness: highlights get
   every 4th row (1.8 mm spacing), midtones every 2nd (0.9 mm), shadows all
   of them (0.45 mm). Strides are nested powers of two so a surviving row
   never jumps position when the tone changes along it — a row is either on
   the grid or absent, and darkening admits MORE rows between the ones
   already there.
2. **Penetration pitch along the row.** 3.0 mm (FILL_STITCH_MM, the light
   end) down to `machine.MIN_STITCH_MM` (the needle floor) at full black —
   never below it, so the needle never lands beside its own hole.
3. **Zigzag amplitude around the row centerline.** 0 at the cutoff (a bare
   run line) up to `SCANLINE_AMP_MAX_MM` at full black — the line-weight
   modulation that makes shadows read solid.

Below the darkness cutoff a stretch of row sews NOTHING: fabric left bare as
the highlight value is the genre's whole point, and a shape that is entirely
highlight comes back `empty` — honestly reported, exactly like any other
tier that produced nothing. Stage 7 then applies its standing never-drop-
artwork contract and falls back to tatami for that shape (the same ladder the
contour and satin tiers document); if bare fabric is truly wanted there, the
review screen's delete is the tool, not a silent hole.

Row machinery: `_row_spans` (the rotated-frame scanline walk), the van der
Corput `_stagger_slots`, `_inset_ring`/`travel_path` (in-shape travel) and
`split_long_moves` are REUSED from `stage6_fill` — no second implementation
of any of them. The per-row penetration generator is this module's own:
`stage6_fill._row_points` pins both row ends to the boundary on a global
uniform stitch grid, which is structurally incompatible with a pitch that
varies point-to-point with tone and with rows that vanish mid-span over a
highlight, so adapting it would have meant rewriting everything but its
name.

The grain angle is deliberately NOT the per-shape principal axis: a photo's
scan grain must run one way across the whole design, so the precedence is
per-shape review override (`meta["fill_angle_deg"]`) > global
`cfg.fill_angle_deg` > 0.0 (horizontal — the classic look). Underlay is
none, per the mono-tier craft consensus the plan records (row 9's "no
underlay beneath" applies to the whole fabric-as-value class).

Strictly opt-in: nothing imports this module's emitter except stage 7, and
stage 7 only routes here on `cfg.fill_technique == "scanline_tonal"`.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import shapely
from shapely import affinity
from shapely.geometry import LineString, Point

from . import debugviz, machine, stitches
from .regions import Region
from .stage6_blend import SourcePixels
from .stage6_fill import _inset_ring, _row_spans, _stagger_slots, travel_path
from .stitches import StitchRun

# --- The darkness -> geometry mapping ---------------------------------------

# Base row pitch — the finest grain, used verbatim only in shadows. The top of
# Sfumato's highest-density band (0.35-0.45 mm), the plan's stated density
# bound for the mono tonal tiers.
SCANLINE_ROW_MM = 0.45

# Hierarchical decimation: (stride, darkness at which that stride switches
# in). Below the first threshold nothing sews at all — the highlight cutoff.
# Strides are nested powers of two ON PURPOSE: a row admitted at stride 4 is
# also admitted at 2 and 1, so darkening only ever ADDS rows between existing
# ones and a row never shifts position across a tone boundary.
SCANLINE_LEVEL_STRIDES = (4, 2, 1)
SCANLINE_LEVEL_DARKNESS = (0.08, 0.45, 0.75)

# Penetration pitch along a row, light end -> dark end. The light end matches
# tatami's own stitch length; the dark end is the needle floor and never goes
# under it.
SCANLINE_PITCH_MAX_MM = machine.FILL_STITCH_MM
SCANLINE_PITCH_MIN_MM = machine.MIN_STITCH_MM

# Zigzag half-width at full black. 0.6 keeps the longest emitted stitch at
# hypot(pitch, 2*amp) <= hypot(3.0, 1.2) ~= 3.2 mm — nowhere near the format
# ceiling — and lays ~1.4 coverage units in solid shadow at the 0.45 mm row
# pitch, a satin-weight dark without piling thread into a board.
SCANLINE_AMP_MAX_MM = 0.6

# Tone is sampled at grain scale, not pixel scale: a Gaussian blur of this
# radius (in mm) before sampling, so one dark pixel of JPEG noise cannot
# flip a row segment on or off.
SCANLINE_BLUR_MM = 0.6

# Scan step through a stretch that is sewing nothing — fine enough not to
# step over a feature narrower than the base row pitch would care about.
SCANLINE_SKIP_STEP_MM = 1.0


def _t(darkness: float) -> float:
    """Darkness normalized over the sewing range [cutoff, 1] -> [0, 1]."""
    cutoff = SCANLINE_LEVEL_DARKNESS[0]
    return min(1.0, max(0.0, (darkness - cutoff) / (1.0 - cutoff)))


def _pitch_mm(darkness: float) -> float:
    return SCANLINE_PITCH_MAX_MM - (SCANLINE_PITCH_MAX_MM - SCANLINE_PITCH_MIN_MM) * _t(darkness)


def _amp_mm(darkness: float) -> float:
    return SCANLINE_AMP_MAX_MM * _t(darkness)


def _stride_for(darkness: float) -> int | None:
    """The row stride local tone admits, or None below the highlight cutoff."""
    stride = None
    for s, d0 in zip(SCANLINE_LEVEL_STRIDES, SCANLINE_LEVEL_DARKNESS):
        if darkness >= d0:
            stride = s
    return stride


def _darkness_sampler(sp: SourcePixels):
    """-> darkness(x_mm, y_mm) in [0, 1], bilinear over a grain-scale blur of
    the source luminance. Deterministic — no RNG anywhere in this tier."""
    gray = cv2.cvtColor(sp.rgb, cv2.COLOR_RGB2GRAY).astype(np.float64) / 255.0
    sigma = max(0.5, SCANLINE_BLUR_MM * sp.px_per_mm)
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


def _span_segments(x0: float, x1: float, row_index: int, y: float,
                   darkness, to_orig, inside) -> list[list[tuple[float, float]]]:
    """Walk one span left to right, sampling tone in the ORIGINAL frame, and
    emit the row's penetrations in the rotated frame.

    -> zero or more polylines: a span breaks wherever local tone stops
    admitting this row (its stride, or the highlight cutoff), because the
    fabric there is the highlight and gets no thread.

    The first advance of each segment is stretched by the row's van der
    Corput stagger slot (1x-1.75x pitch) so penetrations never line up into
    vertical channels across rows — the same defect FILL_STAGGERS exists
    for, solved multiplicatively here because the pitch itself varies with
    tone and a fixed global grid does not exist to phase against.
    """
    slots = _stagger_slots(machine.FILL_STAGGERS)
    stagger = 1.0 + slots[row_index % machine.FILL_STAGGERS] / (2.0 * machine.FILL_STAGGERS)

    segments: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    flip = row_index % 2 == 0
    x = x0
    while True:
        d = darkness(*to_orig(x, y))
        stride = _stride_for(d)
        if stride is not None and row_index % stride == 0:
            amp = _amp_mm(d)
            # A zigzag offset near the shape's edge can reach past it; a
            # penetration outside the artwork is a defect whatever the tier,
            # so an offset that escapes collapses to the row centerline —
            # which is inside by construction (the span IS the polygon's own
            # scanline intersection).
            pt = (x, y + amp) if flip else (x, y - amp)
            if amp > 0.0 and not inside(pt):
                pt = (x, y)
            cur.append(pt)
            flip = not flip
            step = _pitch_mm(d)
            if len(cur) == 1:
                step *= stagger
        else:
            if len(cur) >= 2:
                segments.append(cur)
            cur = []
            step = SCANLINE_SKIP_STEP_MM
        if x >= x1 - 1e-9:
            break
        nxt = x + step
        if x1 - nxt < 0.5 * machine.MIN_STITCH_MM:
            # Too close to the end for another full stitch after it: land on
            # the end itself if that is a legal stitch, else stop here.
            if x1 - x >= machine.MIN_STITCH_MM:
                nxt = x1
            else:
                break
        x = nxt
    if len(cur) >= 2:
        segments.append(cur)
    return segments


def scanline_fill(region: Region, source_pixels: SourcePixels, cfg
                  ) -> tuple[list[StitchRun], dict]:
    """One shape -> its scan-line tonal runs plus the standard tier report.

    Same `(runs, report)` contract as `stitch_shape` and every other stage-6
    sibling: `too_thin` (nowhere wide enough for rows), `jumps` (travel that
    had to lift the needle), `empty` (produced nothing — for this tier that
    includes "the shape is entirely highlight", which is a correct outcome,
    not a failure; stage 7's fallback ladder decides what happens next).
    """
    poly = region.polygon
    report = {"too_thin": False, "jumps": 0, "empty": False}
    if poly.buffer(-machine.MIN_FILL_WIDTH_MM / 2.0).is_empty:
        report["too_thin"] = True

    shape_angle = region.meta.get("fill_angle_deg")
    angle = (float(shape_angle) if shape_angle is not None
             else cfg.fill_angle_deg if cfg.fill_angle_deg is not None
             else 0.0)

    rotated = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
    rows = _row_spans(rotated, SCANLINE_ROW_MM)

    shapely.prepare(rotated)

    def inside(pt: tuple[float, float]) -> bool:
        return rotated.covers(Point(pt))

    darkness = _darkness_sampler(source_pixels)
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)

    def to_orig(x: float, y: float) -> tuple[float, float]:
        return (x * ca - y * sa, x * sa + y * ca)

    # Serpentine over emitted rows: alternate scan direction per row that
    # actually produced something, so consecutive rows meet end to end and
    # travel between them stays short.
    paths_rot: list[list[tuple[float, float]]] = []
    emitted_rows = 0
    for ri, y, spans in rows:
        row_segs: list[list[tuple[float, float]]] = []
        for x0, x1 in spans:
            row_segs.extend(_span_segments(x0, x1, ri, y, darkness, to_orig, inside))
        if not row_segs:
            continue
        if emitted_rows % 2 == 1:
            row_segs = [list(reversed(s)) for s in reversed(row_segs)]
        paths_rot.extend(row_segs)
        emitted_rows += 1

    # Back into the original frame, exactly the way _fill_paths rotates back.
    paths: list[list[tuple[float, float]]] = []
    for path in paths_rot:
        rp = affinity.rotate(LineString(path), angle, origin=(0, 0),
                             use_radians=False)
        paths.append([(x, y) for x, y in rp.coords])

    runs: list[StitchRun] = []
    ring = _inset_ring(poly, machine.TRAVEL_INSET_MM)
    slack = poly.buffer(0.01)
    for path in paths:
        pts = stitches.split_long_moves(path, machine.MAX_STITCH_MM)
        if len(pts) < 2:
            continue
        if runs:
            bridge = travel_path(poly, ring, runs[-1].points[-1], pts[0], slack)
            if bridge is None:
                d = math.dist(runs[-1].points[-1], pts[0])
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
        debugviz.stage6_scanline_rows(Path(cfg.debug_dir), runs,
                                      (maxx - minx, maxy - miny))

    return runs, report
