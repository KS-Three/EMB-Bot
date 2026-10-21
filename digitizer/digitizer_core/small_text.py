"""Enlarge lettering too small to sew (`cfg.small_text_cap_mm`, 2026-10-13,
default OFF).

Kent, on Hotel Fremont's "EST 1895": *"the date is still showing up very
poorly."* Measured at 92.5 mm wide: the date is 1.9 mm tall with 0.27 mm
strokes, so every letter is on the run tier, and a 0.7 mm running stitch
cannot draw the 0.6 mm loops of an 8 or a 9 -- the date reads "1095". Five
existing lettering options were rendered on it and none made it legible; the
two that widen the stroke in place close the counters. The professional's
file for the same patch at the same width does not sew the date at the art's
size at all: its date is 3.6-3.9 mm tall, in satin. That is what this does.

For every text cluster (`textcluster.detect_text_clusters`) whose letters are
under the cap height asked for:

1. ADOPT the untagged shapes of the same thread sitting in the line. The
   tagger refuses a letter whose counters stage 4 dropped (Fremont's 8 is
   traced as a solid blob, 2.2 mm2 beside its neighbours' 1.0, and is in no
   cluster), and a date with one digit left small is worse than the defect.
2. RETRACE the letters from the source raster. Stage 4 drops every hole
   under its 0.56 mm2 sliver floor, so the polygons to be enlarged have
   already lost the counters the enlargement exists to keep. The raster
   still has them; ink against ground is read from the pixels under and
   around the cluster's own polygons, never from a global threshold.
3. SCALE the line uniformly about itself and PLACE it: the largest scale up
   to the cap (never past `MAX_SCALE`) and the smallest move at which the
   line, with `CLEAR_MM` around it, touches no other shape and stays inside
   the design. A line with nowhere to grow is left exactly as it was.
4. WIDEN a stroke still under `MIN_STROKE_MM` after the scale, unless that
   closes a counter.

Fails open throughout, the discipline of every tagger here: anything
uncertain leaves the cluster untouched. Off (None), nothing calls this and
the pipeline is byte-identical.

TRUE SIZE (`restore_small_text`, `cfg.small_text_restore_mm`). Kent on
the enlargement: "you can't change the font size for the final product."
Steps 1 and 2 alone, nothing scaled or moved, with the adopted letters
written into the cluster -- so bean letters, which sews the centreline of a
cluster member's source ink, sews the whole line, the 8 included.

Every number below is a CANDIDATE (ROADMAP gate 1). The cap height the flag
takes is the professional's on one file; nothing here has been sewn.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from shapely import affinity
from shapely.geometry import MultiPolygon, Polygon, box
from shapely.ops import unary_union

from .regions import Region
from .stage1_prep import Prep
from .stage5_overlap import WIDENED_LETTERING_KEY

# A line is never more than doubled. The professional's Fremont date is 1.9x
# the art's; past 2x the result stops being the customer's layout.
MAX_SCALE = 2.0
# Not worth moving a line for less than this.
MIN_SCALE = 1.15
# Fabric kept between the enlarged line's ARTWORK and every other shape.
# Stage 5 grows both by the fabric's pull (0.3 mm by default), so 0.4 here
# rendered the date's T and 1 touching the emblem between them.
CLEAR_MM = 0.8
# Drawn stroke the enlarged letter is widened to. Stage 5 adds the fabric's
# pull on top; with the default 0.3 mm that sews near 0.9, inside the
# professional's 0.8-1.0 mm on the same date.
MIN_STROKE_MM = 0.6
# How far a line may be moved to find room, as a multiple of the cap asked.
MAX_SHIFT_CAPS = 1.0
SHIFT_STEP_MM = 0.25
# A cluster whose box is much taller than its letters is not one horizontal
# line (an arc, a stack); this pass does not know how to grow one.
MAX_LINE_HEIGHT_RATIO = 1.6
# Ink and ground must differ by at least this (RGB distance) to retrace.
MIN_INK_CONTRAST = 30.0


def _polys(geom) -> list[Polygon]:
    if geom is None or geom.is_empty:
        return []
    if isinstance(geom, Polygon):
        return [geom]
    if isinstance(geom, MultiPolygon):
        return list(geom.geoms)
    return [g for g in getattr(geom, "geoms", []) if isinstance(g, Polygon)]


def _height(r: Region) -> float:
    b = r.polygon.bounds
    return b[3] - b[1]


def line_cap_mm(members: list[Region]) -> float:
    """A line's cap height as `restore_small_text` measures it: the median
    member height of its core (`_core`), or of every member when the cluster
    is too small to have one."""
    core = _core(members) or list(members)
    return float(np.median([_height(r) for r in core])) if core else 0.0


# The counter guard's measure, the counter census's (`tools/counter_census.py`,
# PR #964, 2026-10-15) so the guard acts where that table says it does: a
# hole rasterised at this many px/mm, its width twice the largest distance
# transform value inside it.
COUNTER_PX_PER_MM = 40.0
# Tracer dust is not a counter: a hole under this area (mm2, the census's
# floor), or narrower than SPECK_MM or SPECK_CAP_FRAC of the line's cap
# height, is not read. Becker's tracer leaves 0.05 / 0.14 mm specks in its
# 28 / 17 mm letters; Fremont's narrowest real counter is 0.44 mm in a
# 1.72 mm cap. Candidates, like the guard.
COUNTER_MIN_HOLE_MM2 = 0.003
SPECK_MM = 0.1
SPECK_CAP_FRAC = 0.05


def inscribed_width_mm(ring) -> float:
    """Twice the largest distance from inside the ring to its edge, in mm,
    on a `COUNTER_PX_PER_MM` raster (`tools/counter_census.py`'s measure)."""
    ppm = COUNTER_PX_PER_MM
    pts = np.asarray(ring.coords, np.float64)[:, :2]
    x0, y0 = pts.min(axis=0) - 0.1
    w = int(np.ceil((pts[:, 0].max() - x0 + 0.1) * ppm)) + 2
    h = int(np.ceil((pts[:, 1].max() - y0 + 0.1) * ppm)) + 2
    m = np.zeros((h, w), np.uint8)
    cv2.fillPoly(m, [np.round((pts - [x0, y0]) * ppm).astype(np.int32)], 1)
    if not m.any():
        return 0.0
    d = cv2.distanceTransform(m, cv2.DIST_L2, 5)
    return round(2.0 * float(d.max()) / ppm, 3)


def counter_widths_mm(polys, cap: float = 0.0) -> list[float]:
    """Every counter (interior ring) of `polys` wider than tracer dust
    (`COUNTER_MIN_HOLE_MM2`, `SPECK_MM`, `SPECK_CAP_FRAC` x `cap`), as its
    `inscribed_width_mm`."""
    speck = max(SPECK_MM, SPECK_CAP_FRAC * float(cap or 0.0))
    out: list[float] = []
    for poly in polys:
        for g in _polys(poly):
            for ring in g.interiors:
                if Polygon(ring).area < COUNTER_MIN_HOLE_MM2:
                    continue
                wd = inscribed_width_mm(ring)
                if wd >= speck:
                    out.append(wd)
    return out


def line_min_counter_mm(group: list[Region], p: Prep, cap: float | None = None,
                        traced: dict[int, Polygon] | None = None) -> float | None:
    """The true-size switch's counter guard (`config.true_size_min_counter`):
    the narrowest SOURCE counter of a line's letters, in mm across -- each
    letter re-read from the raster (`_retrace`, the same read
    `restore_small_text` restores from, so the counters stage 4's sliver
    floor dropped count). A letter the retrace could not read is measured on
    its traced polygon. None: the line has no counter (it passes the guard)."""
    cap = cap if cap else line_cap_mm(group)
    if traced is None:
        traced = _retrace(group, p, cap)
    polys = [traced.get(i, r.polygon) for i, r in enumerate(group)]
    widths = counter_widths_mm(polys, cap)
    return min(widths) if widths else None


def _adopt(members: list[Region], regions: list[Region], cap: float) -> list[Region]:
    """Untagged same-thread shapes of a letter's height sitting in the line."""
    group = list(members)
    taken = {id(r) for r in group}
    thread = members[0].thread_index
    grew = True
    while grew:
        grew = False
        x0 = min(r.polygon.bounds[0] for r in group)
        x1 = max(r.polygon.bounds[2] for r in group)
        y0 = min(r.polygon.bounds[1] for r in group)
        y1 = max(r.polygon.bounds[3] for r in group)
        for r in regions:
            if id(r) in taken or r.thread_index != thread or r.meta.get("text_cluster_id"):
                continue
            b = r.polygon.bounds
            h = b[3] - b[1]
            if not (0.5 * cap <= h <= 1.3 * cap) or (b[2] - b[0]) > 1.6 * cap:
                continue
            overlap = min(b[3], y1) - max(b[1], y0)
            if overlap < 0.6 * h:
                continue
            if b[2] < x0 - cap or b[0] > x1 + cap:
                continue
            group.append(r)
            taken.add(id(r))
            grew = True
    return group


def _retrace(group: list[Region], p: Prep, cap: float) -> dict[int, Polygon]:
    """Each member's letter re-read from the source raster, counters and all.
    -> {index in group: polygon in mm}; a member it could not read is absent."""
    ppm = float(p.px_per_mm)
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0
    h, w = p.rgb.shape[:2]
    pad = 0.5 * cap
    bx0 = min(r.polygon.bounds[0] for r in group) - pad
    by0 = min(r.polygon.bounds[1] for r in group) - pad
    bx1 = max(r.polygon.bounds[2] for r in group) + pad
    by1 = max(r.polygon.bounds[3] for r in group) + pad
    px0 = max(0, int(math.floor(bx0 * ppm + cx)))
    py0 = max(0, int(math.floor(by0 * ppm + cy)))
    px1 = min(w, int(math.ceil(bx1 * ppm + cx)) + 1)
    py1 = min(h, int(math.ceil(by1 * ppm + cy)) + 1)
    if px1 - px0 < 4 or py1 - py0 < 4:
        return {}
    crop = p.rgb[py0:py1, px0:px1].astype(np.float32)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, dtype=np.float64)
        out = np.empty((len(a), 2), dtype=np.float64)
        out[:, 0] = a[:, 0] * ppm + cx - px0
        out[:, 1] = a[:, 1] * ppm + cy - py0
        return np.round(out).astype(np.int32)

    own = np.zeros(crop.shape[:2], np.uint8)
    for r in group:
        for poly in _polys(r.polygon):
            cv2.fillPoly(own, [to_px(poly.exterior.coords)], 255)
            for ring in poly.interiors:
                cv2.fillPoly(own, [to_px(ring.coords)], 0)
    if not own.any():
        return {}
    k = max(3, int(round(0.35 * ppm)) | 1)
    near = cv2.dilate(own, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k)))
    core = cv2.erode(own, np.ones((3, 3), np.uint8))
    ink_px = crop[(core if core.any() else own) > 0]
    k2 = max(3, int(round(0.7 * ppm)) | 1)
    far = cv2.dilate(own, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k2, k2)))
    ground_px = crop[(far > 0) & (near == 0)]
    if len(ink_px) < 8 or len(ground_px) < 8:
        return {}
    ink = np.median(ink_px, axis=0)
    ground = np.median(ground_px, axis=0)
    axis = ink - ground
    span = float(np.dot(axis, axis))
    if span < MIN_INK_CONTRAST ** 2:
        return {}
    t = ((crop - ground) @ axis) / span
    mask = ((t > 0.5) & (near > 0)).astype(np.uint8)
    contours, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    if hier is None:
        return {}
    hier = hier[0]
    tol = 0.4 / ppm

    def to_mm(c) -> list[tuple[float, float]]:
        a = c.reshape(-1, 2).astype(np.float64)
        return [((x + px0 - cx) / ppm, (y + py0 - cy) / ppm) for x, y in a]

    comps: list[Polygon] = []
    for i, c in enumerate(contours):
        if hier[i][3] != -1 or len(c) < 4 or cv2.contourArea(c) < 6.0:
            continue
        holes = []
        j = hier[i][2]
        while j != -1:
            if len(contours[j]) >= 4 and cv2.contourArea(contours[j]) >= 4.0:
                holes.append(to_mm(contours[j]))
            j = hier[j][0]
        poly = Polygon(to_mm(c), holes).buffer(0).simplify(tol, preserve_topology=True)
        comps.extend(q for q in _polys(poly) if q.area > 0)
    out: dict[int, Polygon] = {}
    assigned: dict[int, list[Polygon]] = {}
    for comp in comps:
        best, best_a = None, 0.0
        for gi, r in enumerate(group):
            a = comp.intersection(r.polygon.buffer(0)).area
            if a > best_a:
                best, best_a = gi, a
        if best is not None:
            assigned.setdefault(best, []).append(comp)
    for gi, parts in assigned.items():
        merged = _polys(unary_union(parts))
        if not merged:
            continue
        biggest = max(merged, key=lambda q: q.area)
        # A retrace that lost most of the letter is not an improvement.
        if biggest.is_valid and biggest.area >= 0.5 * group[gi].polygon.area:
            out[gi] = biggest
    return out


def _core(members: list[Region]) -> list[Region]:
    """The members that really are one line of one ink. The tagger's clusters
    carry strays -- Fremont's tagline cluster holds its two black separator
    bars and a twist of the rope -- and a line is grown as a line or not at
    all, so they are set aside here rather than dragged along."""
    threads: dict[int, int] = {}
    for r in members:
        threads[r.thread_index] = threads.get(r.thread_index, 0) + 1
    thread = max(sorted(threads), key=lambda t: threads[t])
    same = [r for r in members if r.thread_index == thread]
    if len(same) < 3:
        return []
    cap = float(np.median([_height(r) for r in same]))
    mid = float(np.median([(r.polygon.bounds[1] + r.polygon.bounds[3]) / 2.0 for r in same]))
    return [r for r in same
            if 0.8 * cap <= _height(r) <= 1.25 * cap
            and abs((r.polygon.bounds[1] + r.polygon.bounds[3]) / 2.0 - mid) <= 0.5 * cap]


def _offsets(reach: float) -> list[float]:
    n = int(reach / SHIFT_STEP_MM + 1e-9)
    return sorted((i * SHIFT_STEP_MM for i in range(-n, n + 1)), key=lambda v: (abs(v), v))


def _sx(s: float, max_width_scale: float | None) -> float:
    """The sideways scale for height scale `s`: `s` itself (uniform), or at
    most `max_width_scale` (`cfg.small_text_cap_max_width_scale`)."""
    return s if not max_width_scale or max_width_scale <= 0 else min(s, float(max_width_scale))


# RE-SET (`cfg.small_text_cap_letter_gap_mm`, 2026-10-21, built OFF): the
# professional's raised small words, read across his jobs
# (`docs/pro-digitizer-rules-2026-10-21.md`, R4): every letter grown to the
# cap, the gaps between letters closed to 0.15-0.35 mm of VISIBLE fabric
# (1.38 -> 0.32 on Drone's AND DRONE, 0.37 -> 0.15 on Fremont's 1895), each
# letter widened into what that frees, and the line as wide as there is room
# for -- 1.01x the art on Drone (boxed by its dashes), 1.42-1.54x on
# Fremont's date (moved into free space). Condensed growth keeps the art's
# gaps scaled and widens every stroke outward into them: Fremont's grown
# words sewed letter into letter, and Drone's line, 5% wider, hit its dashes
# and was not grown at all.
# Each side of a letter's polygon sews this much further out than the
# polygon on the cloth: half the 40 wt laid thread less what the Column lane
# holds inside under `lettering_columns_small_bold` (its 0.11 mm rail inset,
# less a pull of 0.15 of the stroke). Read off our own file, not off a
# fabric: at 0.25 the Fremont words sewed 0.40-0.55 mm visible gaps for
# 0.25 asked (`tools/small_text_columns.py`, both files as DST), so 0.17 is
# the bridge from a polygon gap to the visible gap the pro's are read in.
SEWN_EDGE_MM = 0.17
# A gap inside one cluster at least this many times its median letter gap,
# and at least `WORD_SPACE_CAP` of the cap, is a SPACE between words: a
# cluster can hold several (Fremont's EAT | STAY, Drone's AND DRONE). Kept
# as drawn, never closed.
WORD_SPACE_RATIO = 2.0
WORD_SPACE_CAP = 0.5
# Letter widths are searched from the uniform scale (`f` = s) down to this
# share of the drawn width in `RESET_WIDTH_STEPS` steps, widest first. Below
# 1 the letters are condensed -- the condensed growth's own idea -- where
# the art's gaps were already tight and closing them frees nothing: the
# Fremont tagline's 0.3-0.5 mm, against the 0.75 mm plus widening a sewn
# 0.25 mm gap needs. A CANDIDATE, like every number of the re-set.
RESET_MIN_WIDTH = 0.8
RESET_WIDTH_STEPS = 8
# A cluster alone on its line moves sideways at most this share of the cap
# asked (`_place_line_reset`); height gives way first. Drone's AND DRONE at
# full growth fitted only 2.75 mm off centre, its dome icon under the middle.
RESET_MAX_SIDE_CAPS = 0.25
# Spacing a letter by its true distance to the one before it settles in a
# few moves (a diagonal pair -- A beside Y -- needs more than a square one).
RESET_SPACING_ITERS = 6


def _units(shapes) -> list[list[int]]:
    """A word's shapes grouped into letters, left to right: a shape whose
    x extent overlaps the letter before it by half the narrower of the two
    is part of it (a split stroke, a dot over its stem)."""
    units: list[list[int]] = []
    lo = hi = 0.0
    for i in sorted(range(len(shapes)), key=lambda k: shapes[k].bounds[0]):
        x0, _y0, x1, _y1 = shapes[i].bounds
        if units and min(hi, x1) - max(lo, x0) >= 0.5 * min(hi - lo, x1 - x0):
            units[-1].append(i)
            lo, hi = min(lo, x0), max(hi, x1)
        else:
            units.append([i])
            lo, hi = x0, x1
    return units


def _words(spans: list[tuple[float, float]], cap: float) -> list[list[int]]:
    """Letters (their x spans, left to right) grouped into words at the
    spaces (`WORD_SPACE_RATIO`, `WORD_SPACE_CAP`)."""
    gaps = [b[0] - a[1] for a, b in zip(spans, spans[1:])]
    med = float(np.median(gaps)) if gaps else 0.0
    words = [[0]] if spans else []
    for k, g in enumerate(gaps):
        if g >= max(WORD_SPACE_RATIO * med, WORD_SPACE_CAP * cap):
            words.append([k + 1])
        else:
            words[-1].append(k + 1)
    return words


def _stroke_target(it: dict, s: float, min_stroke_mm: float, bold_scale: float | None) -> float:
    """The drawn stroke a re-set letter is widened to: `min_stroke_mm`, or
    with `bold_scale` (`cfg.small_text_cap_bold_scale`) the art's stroke
    grown with the letter's HEIGHT and bolded by that factor when more. The
    pro's sewn column over the art's stroke at his scale: 0.90 / (0.30 x
    2.06) on Fremont, 1.26 / (0.59 x 1.57) on Drone, 1.26 / (0.61 x 1.29) on
    Proseal -- 1.45, 1.36, 1.60."""
    t = min_stroke_mm
    if bold_scale and bold_scale > 0 and it["stroke"] > 0:
        t = max(t, float(bold_scale) * s * it["stroke"])
    return t


def _bar_room(bar_w: float, widen: float, gap_mm: float) -> float:
    """Polygon-to-polygon room a bar of the line (`|`) needs between the
    letters either side: its width plus, each side, the letter gap the
    letters keep from each other."""
    return bar_w + 2.0 * (gap_mm + 2.0 * SEWN_EDGE_MM + widen)


def _reset_word(it: dict, s: float, f: float, gap_mm: float, min_stroke_mm: float,
                bold_scale: float | None, bars: list[Polygon] | None = None) -> dict:
    """One cluster re-set (comment at `SEWN_EDGE_MM`): every letter scaled
    `s` tall and `f` wide about its own centre, then laid left to right,
    each letter moved until its true distance to the one before it, once
    both are widened, is `gap_mm` of visible fabric; a space between words
    kept as drawn, or opened to hold a bar of the line that stood in it
    (`bars`, `_bar_room`). The cluster stays centred where it was.
    -> {"f", "widen", "moves": [(cx, dx) per shape], "units": [(x0, x1, cx,
    dx) per letter], "cy", "hull" (each word's convex hull), "ink", "laid"
    (per letter), "span"}."""
    shapes = it["shapes"]
    units = it.setdefault("units", _units(shapes))
    spans = []
    for u in units:
        xs = [v for i in u for v in (shapes[i].bounds[0], shapes[i].bounds[2])]
        spans.append((min(xs), max(xs)))
    words = it.setdefault("words", _words(spans, it["cap"]))
    c = it["hull"].centroid
    target = _stroke_target(it, s, min_stroke_mm, bold_scale)
    widen = max(0.0, (target - min(s, f) * it["stroke"]) / 2.0) if it["stroke"] > 0 else 0.0
    clear = gap_mm + 2.0 * SEWN_EDGE_MM + 2.0 * widen
    scaled = [unary_union([affinity.scale(shapes[i], f, s, origin=((a + b) / 2.0, c.y)) for i in u])
              for u, (a, b) in zip(units, spans)]
    offs = [0.0] * len(units)
    laid: list = [None] * len(units)
    right = None
    for word in words:
        for k, ui in enumerate(word):
            g = scaled[ui]
            if right is None:
                off = -g.bounds[0]
            elif k == 0:                # a space: the art's, the widening on top
                space = spans[ui][0] - spans[ui - 1][1] + 2.0 * widen
                for bar in bars or ():
                    bx0, _by0, bx1, _by1 = bar.bounds
                    if spans[ui - 1][1] <= (bx0 + bx1) / 2.0 <= spans[ui][0]:
                        space = max(space, _bar_room(bx1 - bx0, widen, gap_mm))
                off = right + space - g.bounds[0]
            else:
                prev = laid[ui - 1]
                off = prev.bounds[2] + clear - g.bounds[0]
                for _ in range(RESET_SPACING_ITERS):
                    d = prev.distance(affinity.translate(g, off, 0.0))
                    if d <= 1e-9:
                        off += 0.5 * clear      # overshot into it: back off
                        continue
                    if abs(d - clear) < 0.01:
                        break
                    off -= d - clear
            offs[ui] = off
            laid[ui] = affinity.translate(g, off, 0.0)
            right = laid[ui].bounds[2] if right is None else max(right, laid[ui].bounds[2])
    left = min(q.bounds[0] for q in laid)
    shift = c.x - (left + right) / 2.0
    moves = [None] * len(shapes)
    rows = []
    for ui, (u, (a, b)) in enumerate(zip(units, spans)):
        dxu = offs[ui] + shift
        rows.append((a, b, (a + b) / 2.0, dxu))
        for i in u:
            moves[i] = ((a + b) / 2.0, dxu)
    laid = [affinity.translate(q, shift, 0.0) for q in laid]
    hull = unary_union([unary_union([laid[ui] for ui in word]).convex_hull for word in words])
    x0, _y0, x1, _y1 = it["hull"].bounds
    return {"f": f, "widen": widen, "moves": moves, "units": rows, "cy": c.y, "hull": hull,
            "ink": unary_union(laid), "laid": laid, "span": (right - left) / max(x1 - x0, 1e-9)}


def _shifted(r: dict, t: float) -> dict:
    """A `_reset_word` answer moved `t` sideways."""
    return {**r, "moves": [(cx, d + t) for cx, d in r["moves"]],
            "units": [(a, b, cx, d + t) for a, b, cx, d in r["units"]],
            "laid": [affinity.translate(q, t, 0.0) for q in r["laid"]],
            "ink": affinity.translate(r["ink"], t, 0.0), "hull": affinity.translate(r["hull"], t, 0.0)}


def _reset_line(items: list[dict], s: float, f: float, gap_mm: float, min_stroke_mm: float,
                bold_scale: float | None, bars: list[Polygon] | None = None) -> list[dict]:
    """Every cluster of a line re-set (`_reset_word`), then the clusters laid
    left to right as one line about the line's own centre: between two, the
    art's space with the widening on top, or the room a bar standing there
    needs (`_bar_room`). Grown each about its own centre, Fremont's STAY ran
    into the bar before PLAY."""
    rs = [_reset_word(it, s, f, gap_mm, min_stroke_mm, bold_scale, bars) for it in items]
    if len(rs) < 2:
        return rs
    widen = max(r["widen"] for r in rs)
    art = [it["hull"].bounds for it in items]
    width = rs[0]["ink"].bounds[2] - rs[0]["ink"].bounds[0]
    spaces = []
    for k in range(1, len(rs)):
        lo, hi = art[k - 1][2], art[k][0]
        space = hi - lo + 2.0 * widen
        for bar in bars or ():
            bx0, _by0, bx1, _by1 = bar.bounds
            if lo <= (bx0 + bx1) / 2.0 <= hi:
                space = max(space, _bar_room(bx1 - bx0, widen, gap_mm))
        spaces.append(space)
        width += space + rs[k]["ink"].bounds[2] - rs[k]["ink"].bounds[0]
    cursor = (art[0][0] + art[-1][2]) / 2.0 - width / 2.0
    out = []
    for k, r in enumerate(rs):
        if k:
            cursor += spaces[k - 1]
        out.append(_shifted(r, cursor - r["ink"].bounds[0]))
        cursor += r["ink"].bounds[2] - r["ink"].bounds[0]
    return out


def _bar_moves(bars: list[Polygon], resets: list[dict], dxs: list[float], gap_mm: float):
    """Each bar of a re-set line moved sideways to the middle of the room
    between the letters that stood either side of it in the art (a letter's
    side is read from its ART centre); a bar at the line's end only steps
    clear. -> [dx per bar], or None when a bar has no room."""
    widen = max((r["widen"] for r in resets), default=0.0)
    out = []
    for bar in bars:
        bx0, _by0, bx1, _by1 = bar.bounds
        bc = (bx0 + bx1) / 2.0
        lo, hi = -math.inf, math.inf
        for r, dx in zip(resets, dxs):
            for (_a, _b, cx, _d), g in zip(r["units"], r["laid"]):
                if cx < bc:
                    lo = max(lo, g.bounds[2] + dx)
                else:
                    hi = min(hi, g.bounds[0] + dx)
        need = _bar_room(bx1 - bx0, widen, gap_mm)
        if hi - lo < need:
            return None
        if math.isinf(lo) and math.isinf(hi):
            out.append(0.0)
        elif math.isinf(lo):
            out.append(min(bc, hi - need / 2.0) - bc)
        elif math.isinf(hi):
            out.append(max(bc, lo + need / 2.0) - bc)
        else:
            out.append((lo + hi) / 2.0 - bc)
    return out


def _place_line_reset(items: list[dict], bounds: Polygon, s_max: float, cap_mm: float,
                      gap_mm: float, min_stroke_mm: float, bold_scale: float | None,
                      bars: list[Polygon] | None = None):
    """`_place_line` for a re-set line: the tallest scale, then the widest
    letters (`f` from `s` down to `RESET_MIN_WIDTH`) at which every cluster
    fits clear of every obstacle by `CLEAR_MM`, and every bar of the line
    (`bars`) has room between its letters (`_bar_moves`).
    -> (s, dy, [dx per item], [reset per item], [dx per bar]) or None."""
    shifts = _offsets(MAX_SHIFT_CAPS * cap_mm)
    # one cluster alone on its line stays near where it was drawn: a line
    # set about its own centre, slid sideways, is off-centre in the design
    side = shifts if len(items) > 1 else [v for v in shifts if abs(v) <= RESET_MAX_SIDE_CAPS * cap_mm]
    steps = 8
    for k in range(steps + 1):
        s = s_max - (s_max - MIN_SCALE) * k / steps
        if s < MIN_SCALE - 1e-9:
            break
        for j in range(RESET_WIDTH_STEPS + 1):
            f = s - (s - RESET_MIN_WIDTH) * j / RESET_WIDTH_STEPS
            resets = _reset_line(items, s, f, gap_mm, min_stroke_mm, bold_scale, bars)
            grown = [r["hull"].buffer(r["widen"] + it.get("clear", CLEAR_MM))
                     for it, r in zip(items, resets)]
            # the smallest move wins, |dy| + the largest |dx|: taking the
            # first dy that fits at any dx slid Drone's line 2.75 mm sideways
            # where a quarter millimetre up kept it centred
            best = None
            for dy in shifts:
                if best is not None and abs(dy) >= best[0]:
                    break
                dxs, placed = [], []
                for it, g0 in zip(items, grown):
                    hit = None
                    for dx in side:
                        if best is not None and abs(dy) + abs(dx) >= best[0]:
                            break
                        g = affinity.translate(g0, dx, dy)
                        if not bounds.contains(g):
                            continue
                        if it["obstacles"] is not None and g.intersects(it["obstacles"]):
                            continue
                        if any(g.intersects(q) for q in placed):
                            continue
                        hit = (dx, g)
                        break
                    if hit is None:
                        break
                    dxs.append(hit[0])
                    placed.append(hit[1])
                if len(dxs) == len(items):
                    moves = _bar_moves(bars or [], resets, dxs, gap_mm)
                    if moves is not None:
                        best = (abs(dy) + max(abs(v) for v in dxs), dy, dxs, moves)
            if best is not None:
                return s, best[1], best[2], resets, best[3]
    return None


def _place_line(items: list[dict], bounds: Polygon, s_max: float, cap_mm: float,
                max_width_scale: float | None = None, min_stroke_mm: float = MIN_STROKE_MM):
    """One scale and one vertical move for the whole line -- two halves of a
    date either side of an emblem must keep one baseline -- and each
    cluster's own smallest sideways move. -> (s, dy, [dx per item]) or None."""
    shifts = _offsets(MAX_SHIFT_CAPS * cap_mm)
    steps = 8
    for k in range(steps + 1):
        s = s_max - (s_max - MIN_SCALE) * k / steps
        if s < MIN_SCALE - 1e-9:
            break
        sx = _sx(s, max_width_scale)
        grown = []
        for it in items:
            c = it["hull"].centroid
            widen = max(0.0, (min_stroke_mm - min(s, sx) * it["stroke"]) / 2.0) if it["stroke"] > 0 else 0.0
            grown.append(affinity.scale(it["hull"], sx, s, origin=(c.x, c.y)).buffer(widen + CLEAR_MM))
        for dy in shifts:
            dxs, placed = [], []
            for it, g0 in zip(items, grown):
                hit = None
                for dx in shifts:
                    g = affinity.translate(g0, dx, dy)
                    if not bounds.contains(g):
                        continue
                    if it["obstacles"] is not None and g.intersects(it["obstacles"]):
                        continue
                    if any(g.intersects(q) for q in placed):
                        continue
                    hit = (dx, g)
                    break
                if hit is None:
                    break
                dxs.append(hit[0])
                placed.append(hit[1])
            if len(dxs) == len(items):
                return s, dy, dxs
    return None


def enlarge_small_text(regions: list[Region], p: Prep, *, cap_mm: float,
                       max_width_scale: float | None = None,
                       min_stroke_mm: float | None = None,
                       letter_gap_mm: float | None = None,
                       bold_scale: float | None = None) -> list[dict]:
    """Enlarge, in place, every line of lettering under `cap_mm`. See the
    module docstring. -> one report row per text cluster it considered.

    `letter_gap_mm` (`cfg.small_text_cap_letter_gap_mm`): RE-SET each word
    instead (comment at `SEWN_EDGE_MM`, `_place_line_reset`): letters this
    much visible fabric apart, each widened into its gaps, the line as wide
    as room allows; `max_width_scale` is not read. `bold_scale`
    (`cfg.small_text_cap_bold_scale`, re-set only): the stroke a letter is
    widened to grows with its height (`_stroke_target`). None: the growth
    above, byte for byte.

    `max_width_scale` (`cfg.small_text_cap_max_width_scale`): grow the
    letters TALLER by the full scale but WIDER by at most this -- condensed,
    the way the professional's Fremont file sets its small words (height
    1.55-2.1x the art, width 1.04-1.06x). None: uniform, byte for byte.

    `min_stroke_mm` (`cfg.small_text_cap_min_stroke_mm`): the drawn stroke a
    grown letter is widened to. None: `MIN_STROKE_MM`, byte for byte."""
    min_stroke_mm = float(min_stroke_mm) if min_stroke_mm and min_stroke_mm > 0 else MIN_STROKE_MM
    report: list[dict] = []
    if not cap_mm or cap_mm <= 0 or not regions:
        return report
    clusters: dict[str, list[Region]] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid:
            clusters.setdefault(cid, []).append(r)
    if not clusters:
        return report
    xs0, ys0, xs1, ys1 = zip(*(r.polygon.bounds for r in regions))
    design = box(min(xs0), min(ys0), max(xs1), max(ys1))
    claimed: set[int] = set()
    items: list[dict] = []
    for cid in sorted(clusters):
        row = {"cluster": cid, "members": len(clusters[cid])}
        report.append(row)
        try:
            members = _core(clusters[cid])
            if len(members) < 3:
                row["skipped"] = "not_one_line"
                continue
            cap = float(np.median([_height(r) for r in members]))
            row["cap_mm"] = round(cap, 3)
            if cap <= 0 or cap >= 0.9 * cap_mm:
                row["skipped"] = "tall_enough"
                continue
            group = [r for r in _adopt(members, regions, cap) if id(r) not in claimed]
            if len(group) < len(members):
                row["skipped"] = "member_claimed"
                continue
            line_h = max(r.polygon.bounds[3] for r in group) - min(r.polygon.bounds[1] for r in group)
            if line_h > MAX_LINE_HEIGHT_RATIO * cap:
                row["skipped"] = "not_one_line"
                continue
            traced = _retrace(group, p, cap)
            shapes = [traced.get(i, r.polygon) for i, r in enumerate(group)]
            hull = unary_union(shapes).convex_hull
            if hull.is_empty or hull.area <= 0:
                row["skipped"] = "degenerate"
                continue
            claimed.update(id(r) for r in group)
            items.append({
                "row": row, "group": group, "shapes": shapes, "hull": hull, "cap": cap,
                "members": len(members), "traced": len(traced),
                "stroke": 2.0 * float(members[0].meta.get("text_cluster_stroke_mm") or 0.0),
                "mid": (hull.bounds[1] + hull.bounds[3]) / 2.0,
            })
        except Exception as exc:  # fail open: never take the pipeline down
            row["skipped"] = f"error:{type(exc).__name__}"

    # Clusters of one ink and one size on one baseline are ONE line.
    lines: list[list[dict]] = []
    for it in items:
        for line in lines:
            ref = line[0]
            if (ref["group"][0].thread_index == it["group"][0].thread_index
                    and min(ref["cap"], it["cap"]) >= 0.8 * max(ref["cap"], it["cap"])
                    and abs(ref["mid"] - it["mid"]) <= 0.5 * min(ref["cap"], it["cap"])):
                line.append(it)
                break
        else:
            lines.append([it])

    reset = letter_gap_mm is not None and letter_gap_mm >= 0
    for line in lines:
        try:
            line.sort(key=lambda it: it["hull"].bounds[0])
            ids = {id(r) for it in line for r in it["group"]}
            cap = float(np.median([it["cap"] for it in line]))
            if reset:
                joined = _join_line_ends(line, regions, ids | claimed, cap)
                if joined:
                    ids |= {id(r) for r in joined}
                    claimed.update(id(r) for r in joined)
                    line[0]["row"]["joined"] = len(joined)
            # Condensed growth only (uniform keeps the old rule, byte for
            # byte), two kinds of shape in the line stop blocking it:
            # - a BAR across the line (the tagline's "|"): thin -- at most
            #   half a cap wide -- at least 0.8 cap tall, crossing the line's
            #   band inside its span. Left where and as it is; already as
            #   tall as the grown letters on Fremont (4.2 mm art, 5.3 the pro).
            # - a piece INSIDE one word -- a letter's counter kept as its own
            #   ground-coloured shape (the A's of EAT | STAY | PLAY) -- moves
            #   and grows with that word, or the word grows over its holes.
            bars: list[Region] = []
            inner: dict[int, list[Region]] = {}
            if reset or (max_width_scale and max_width_scale > 0):
                lx0 = min(it["hull"].bounds[0] for it in line)
                lx1 = max(it["hull"].bounds[2] for it in line)
                ly0 = min(it["hull"].bounds[1] for it in line)
                ly1 = max(it["hull"].bounds[3] for it in line)
                for r in regions:
                    if id(r) in ids:
                        continue
                    b = r.polygon.bounds
                    if (b[2] - b[0] <= 0.5 * cap and b[3] - b[1] >= 0.8 * cap and lx0 <= b[0] and b[2] <= lx1
                            and b[1] <= ly0 + 0.25 * (ly1 - ly0) and b[3] >= ly1 - 0.25 * (ly1 - ly0)):
                        bars.append(r)
                        continue
                    for k, it in enumerate(line):
                        if r.polygon.area < 0.5 * cap * cap and r.polygon.within(it["hull"].buffer(0.05)):
                            inner.setdefault(k, []).append(r)
                            break
            fids = {id(r) for r in bars} | {id(r) for rs in inner.values() for r in rs}
            for it in line:
                hull = it["hull"]
                near = hull.buffer(MAX_SCALE * max(cap_mm, hull.bounds[2] - hull.bounds[0]))
                blockers = []
                for r in regions:
                    if id(r) in ids or id(r) in fids or not r.polygon.intersects(near):
                        continue
                    # The ground the line sits on is not in its way.
                    if r.polygon.intersection(hull).area >= 0.5 * hull.area:
                        continue
                    blockers.append(r.polygon)
                it["obstacles"] = unary_union(blockers) if blockers else None
                if reset and it["obstacles"] is not None:
                    # re-set: no more room than the art itself left, up to
                    # CLEAR_MM -- Drone's A stands 0.97 mm off its dash in
                    # the art (the pro's: 0.8 visible), and 0.8 plus the
                    # widening around it slid the whole line 2.75 mm aside
                    it["clear"] = min(CLEAR_MM, float(hull.distance(it["obstacles"])))
            if reset:
                found = _place_line_reset(line, design, min(MAX_SCALE, cap_mm / cap), cap_mm,
                                          float(letter_gap_mm), min_stroke_mm, bold_scale,
                                          [r.polygon for r in bars])
            else:
                found = _place_line(line, design, min(MAX_SCALE, cap_mm / cap), cap_mm, max_width_scale,
                                    min_stroke_mm)
            if found is None:
                for it in line:
                    it["row"]["skipped"] = "no_room"
                    # What is in the way at the smallest growth, in place --
                    # report only, nothing reads it.
                    g = affinity.scale(it["hull"], _sx(MIN_SCALE, max_width_scale), MIN_SCALE,
                                       origin=(it["hull"].centroid.x, it["hull"].centroid.y)).buffer(CLEAR_MM)
                    hits = []
                    if not design.contains(g):
                        hits.append("design_edge")
                    if it["obstacles"] is not None and g.intersects(it["obstacles"]):
                        for r in regions:
                            if id(r) not in ids and id(r) not in fids and r.polygon.intersects(g) \
                                    and r.polygon.intersection(it["hull"]).area < 0.5 * it["hull"].area:
                                hits.append([r.thread_index, [round(v, 1) for v in r.polygon.bounds]])
                    it["row"]["blocked_by"] = hits[:6]
                continue
            if reset:
                _reset_apply(regions, line, bars, inner, found)
                continue
            s, dy, dxs = found
            sx = _sx(s, max_width_scale)
            for k, (it, dx) in enumerate(zip(line, dxs)):
                c = it["hull"].centroid
                for r in inner.get(k, []):
                    grown = affinity.translate(affinity.scale(r.polygon, sx, s, origin=(c.x, c.y)), dx, dy)
                    if isinstance(grown, Polygon) and grown.is_valid and not grown.is_empty:
                        r.polygon = grown
                        r.area_mm2 = float(grown.area)
                        r.meta["small_text_inner"] = round(s, 3)
            if bars or inner:
                line[0]["row"].update(bars=len(bars), inner=sum(len(v) for v in inner.values()))
            for it, dx in zip(line, dxs):
                widen = max(0.0, (min_stroke_mm - min(s, sx) * it["stroke"]) / 2.0) if it["stroke"] > 0 else 0.0
                origin = (it["hull"].centroid.x, it["hull"].centroid.y)
                old_union = unary_union([r.polygon for r in it["group"]])
                for r, shape in zip(it["group"], it["shapes"]):
                    moved = affinity.translate(affinity.scale(shape, sx, s, origin=origin), dx, dy)
                    final = moved
                    for w in (widen, widen / 2.0):
                        if w <= 1e-6:
                            break
                        fat = [q for q in _polys(moved.buffer(w)) if q.area > 0]
                        if len(fat) == 1 and len(fat[0].interiors) >= len(moved.interiors):
                            final = fat[0]
                            break
                    if not isinstance(final, Polygon) or not final.is_valid or final.is_empty:
                        continue
                    r.polygon = final
                    r.area_mm2 = float(final.area)
                    r.meta["small_text_enlarged"] = round(s, 3)
                    # The line now lies ON its ground, not in the holes the
                    # ground was traced with. Stage 5 clips every shape to
                    # what earlier colours left bare -- which sewed nine of
                    # Fremont's ten enlarged letters as nothing -- except
                    # lettering whose polygon IS its column. That is this.
                    r.meta[WIDENED_LETTERING_KEY] = round(max(widen, 1e-4), 4)
                    if r.meta.get("text_cluster_stroke_mm"):
                        r.meta["text_cluster_stroke_mm"] = float(r.meta["text_cluster_stroke_mm"]) * min(s, sx) + widen
                _fill_old_holes(regions, {id(r) for r in it["group"]}, old_union)
                it["row"].update(scale=round(s, 3), width_scale=round(sx, 3), shift_mm=(round(dx, 2), round(dy, 2)),
                                 adopted=len(it["group"]) - it["members"], retraced=it["traced"],
                                 widened_mm=round(widen, 3))
            if max_width_scale and max_width_scale > 0:
                carved = _carve_neighbours([r for it in line for r in it["group"]
                                            if r.meta.get("small_text_enlarged")])
                if carved:
                    line[0]["row"]["carved"] = carved
        except Exception as exc:  # fail open
            for it in line:
                it["row"]["skipped"] = f"error:{type(exc).__name__}"
    return report


# A re-set letter's counter is shrunk by the widening only while it keeps
# at least this width (mm, twice its deepest inside point); past that, by as
# much as leaves it so, or not at all. A sewn counter narrower than the
# 40 wt laid thread closes on the cloth anyway.
RESET_COUNTER_MIN_MM = 0.4


def _widen_keep_counters(poly: Polygon, widen: float):
    """`poly` widened by `widen` on its outline, each counter shrunk by at
    most as much as keeps it `RESET_COUNTER_MIN_MM` wide. The growth's own
    rule -- buffer whole, or by half, or not at all when that closes a
    counter -- left a re-set A, whose counter is 0.3 mm, at half the
    widening: its legs drawn 0.6 mm where its other strokes are 0.85, and
    the left one sewn as a travel run. -> a Polygon, or `poly` unchanged."""
    if widen <= 1e-6:
        return poly
    outer = [q for q in _polys(Polygon(poly.exterior).buffer(widen)) if q.area > 0]
    if len(outer) != 1:
        return poly
    holes = []
    for ring in poly.interiors:
        hole = Polygon(ring)
        keep = hole
        for w in (widen, widen * 0.75, widen * 0.5, widen * 0.25):
            cand = [q for q in _polys(hole.buffer(-w)) if q.area > 0]
            if len(cand) == 1 and inscribed_width_mm(cand[0].exterior) >= RESET_COUNTER_MIN_MM:
                keep = cand[0]
                break
        holes.append(keep)
    out = outer[0].difference(unary_union(holes)) if holes else outer[0]
    if not isinstance(out, Polygon) or not out.is_valid or out.is_empty \
            or len(out.interiors) < len(poly.interiors):
        return poly
    return out


def _join_line_ends(line: list[dict], regions: list[Region], taken: set[int], cap: float) -> list[Region]:
    """Re-set only: a letter-sized shape standing on the line's own band
    just past either end -- 0.8-1.25 cap tall, at most 2 caps wide and
    within 1.5 cap of the end -- joins the end cluster and grows and moves
    with it, whatever its thread. Drone's AND DRONE: our trace gives its
    first A a thread of its own, so it is in no cluster; the re-set grew
    the other seven letters and slid them 2.5 mm off it ("A   ND DRONE").
    -> the shapes joined."""
    lx0 = min(it["hull"].bounds[0] for it in line)
    lx1 = max(it["hull"].bounds[2] for it in line)
    ly0 = min(it["hull"].bounds[1] for it in line)
    ly1 = max(it["hull"].bounds[3] for it in line)
    joined = []
    for side in ("left", "right"):
        best = None
        for r in regions:
            if id(r) in taken or not isinstance(r.polygon, Polygon) or r.polygon.is_empty:
                continue
            x0, y0, x1, y1 = r.polygon.bounds
            h = y1 - y0
            if not (0.8 * cap <= h <= 1.25 * cap and x1 - x0 <= 2.0 * cap
                    and min(y1, ly1) - max(y0, ly0) >= 0.8 * h):
                continue
            gap = lx0 - x1 if side == "left" else x0 - lx1
            if -0.1 <= gap <= 1.5 * cap and (best is None or gap < best[0]):
                best = (gap, r)
        if best is None:
            continue
        r = best[1]
        it = line[0] if side == "left" else line[-1]
        it["group"].append(r)
        it["shapes"].append(r.polygon)
        it["hull"] = unary_union(it["shapes"]).convex_hull
        it.pop("units", None)
        it.pop("words", None)
        taken.add(id(r))
        joined.append(r)
    return joined


def _reset_apply(regions: list[Region], line: list[dict], bars: list[Region],
                 inner: dict[int, list[Region]], found) -> None:
    """Write a re-set line (`_place_line_reset`'s answer) into its regions:
    each shape scaled about its letter's centre and moved to its place, then
    widened as the growth widens; a word's inner pieces go with the letter
    they sit in. The meta keys are the growth's, so every reader downstream
    sees a grown letter."""
    s, dy, dxs, resets, bar_dxs = found
    for k, (it, dx, rs) in enumerate(zip(line, dxs, resets)):
        f, widen, cy = rs["f"], rs["widen"], rs["cy"]
        for r in inner.get(k, []):
            x = r.polygon.centroid.x
            _a, _b, cx, dxu = min(rs["units"], key=lambda u: 0.0 if u[0] <= x <= u[1]
                                  else min(abs(x - u[0]), abs(x - u[1])))
            grown = affinity.translate(affinity.scale(r.polygon, f, s, origin=(cx, cy)), dxu + dx, dy)
            if isinstance(grown, Polygon) and grown.is_valid and not grown.is_empty:
                r.polygon = grown
                r.area_mm2 = float(grown.area)
                r.meta["small_text_inner"] = round(s, 3)
        old_union = unary_union([r.polygon for r in it["group"]])
        for r, shape, (cx, dxu) in zip(it["group"], it["shapes"], rs["moves"]):
            moved = affinity.translate(affinity.scale(shape, f, s, origin=(cx, cy)), dxu + dx, dy)
            final = _widen_keep_counters(moved, widen)
            if not isinstance(final, Polygon) or not final.is_valid or final.is_empty:
                continue
            r.polygon = final
            r.area_mm2 = float(final.area)
            r.meta["small_text_enlarged"] = round(s, 3)
            r.meta["small_text_reset"] = True       # the regularizer leaves it as set
            r.meta[WIDENED_LETTERING_KEY] = round(max(widen, 1e-4), 4)
            if r.meta.get("text_cluster_stroke_mm"):
                r.meta["text_cluster_stroke_mm"] = float(r.meta["text_cluster_stroke_mm"]) * min(s, f) + widen
        _fill_old_holes(regions, {id(r) for r in it["group"]}, old_union)
        if inner.get(k):        # an inner piece stays inside its letter's (shrunk) counter
            ink = unary_union([r.polygon for r in it["group"]])
            for r in inner[k]:
                rest = [q for q in _polys(r.polygon.difference(ink)) if q.area > 0]
                if rest:
                    r.polygon = max(rest, key=lambda q: q.area)
                    r.area_mm2 = float(r.polygon.area)
        it["row"].update(scale=round(s, 3), span=round(rs["span"], 3), width_scale=round(f, 3),
                         shift_mm=(round(dx, 2), round(dy, 2)), adopted=len(it["group"]) - it["members"],
                         retraced=it["traced"], widened_mm=round(widen, 3), letters=len(rs["units"]))
    for bar, bdx in zip(bars, bar_dxs):     # each bar to the middle of its room
        if abs(bdx) < 1e-9:
            continue
        old = bar.polygon
        bar.polygon = affinity.translate(old, bdx, 0.0)
        bar.meta["small_text_bar_moved_mm"] = round(bdx, 3)
        _fill_old_holes(regions, {id(bar)}, old)
    if bars or inner:
        line[0]["row"].update(bars=len(bars), inner=sum(len(v) for v in inner.values()),
                              bar_moves=[round(v, 2) for v in bar_dxs])


# Fabric kept between two grown letters of one line (condensed growth). Each
# letter sews its own columns; where two overlapped, Fremont's tagline at cap
# 4.0 sewed both sets of crosses over each other (2026-10-21). Half the 40 wt
# laid width: the pull stage 5 adds still closes most of it on the cloth.
LETTER_GAP_MM = 0.2


def _carve_neighbours(letters: list[Region]) -> int:
    """Left to right, each grown letter gives way to the ones before it by
    `LETTER_GAP_MM`. A letter the cut would split or empty is left alone.
    -> how many letters were cut."""
    letters = sorted(letters, key=lambda r: r.polygon.bounds[0])
    done: list[Polygon] = []
    cut = 0
    for r in letters:
        before = [q for q in done if q.distance(r.polygon) < LETTER_GAP_MM]
        if before:
            rest = r.polygon.difference(unary_union(before).buffer(LETTER_GAP_MM))
            parts = [q for q in _polys(rest) if q.area > 0]
            if len(parts) == 1 and parts[0].is_valid and parts[0].area >= 0.6 * r.polygon.area:
                r.polygon = parts[0]
                r.area_mm2 = float(parts[0].area)
                cut += 1
        done.append(r.polygon)
    return cut


def _fill_old_holes(regions: list[Region], ids: set[int], old_union) -> None:
    """A ground cut around the letters where they used to be would leave
    letter-shaped bare fabric once they move. Close those holes."""
    if old_union.is_empty:
        return
    cover = old_union.buffer(0.15)
    for r in regions:
        if id(r) in ids or not isinstance(r.polygon, Polygon) or not r.polygon.interiors:
            continue
        if not r.polygon.intersects(cover):
            continue
        keep = []
        for ring in r.polygon.interiors:
            hole = Polygon(ring)
            if hole.area > 0 and hole.intersection(cover).area >= 0.8 * hole.area:
                continue
            keep.append(ring)
        if len(keep) != len(r.polygon.interiors):
            filled = Polygon(r.polygon.exterior, keep)
            if filled.is_valid:
                r.polygon = filled
                r.area_mm2 = float(filled.area)


_CLUSTER_TAGS = ("text_candidate", "text_cluster_id", "text_cluster_stroke_mm", "text_cluster_all_rescued")


GUARD_KEY = "small_text_true_size_guarded"
COUNTER_KEY = "small_text_min_counter_mm"


def _stray_line(strays: list[Region], keep_stray_lines: bool) -> list[Region]:
    """`keep_stray_lines`: the strays that are themselves a line of lettering
    (`_core`, three or more), else none."""
    kept = _core(strays) if keep_stray_lines and strays else []
    return kept if len(kept) >= 3 else []


def _release(kept: list[Region], new_cid: str, clusters: dict, order: list) -> str:
    """Another line that shared the tagger's cluster: its own cluster now,
    considered like any other."""
    for r in kept:
        r.meta["text_cluster_id"] = new_cid
        r.meta["small_text_stray_line"] = True
    clusters[new_cid] = kept
    order.append(new_cid)
    return new_cid


def passes_counter_guard(members: list[Region], p: Prep, floor_base_mm: float | None,
                         thread_wts: dict[int, int] | None = None,
                         default_wt: int = 40) -> bool:
    """Whether a text cluster passes the true-size switch's counter guard
    (`config.true_size_min_counter`), for a reader after `restore_small_text`
    (the bean tagger): the restore step's verdict when it measured the line
    (`GUARD_KEY` failed, `COUNTER_KEY` passed), else measured here on the
    cluster's core. None for the floor: no guard, every line passes."""
    if not floor_base_mm:
        return True
    if any(r.meta.get(GUARD_KEY) for r in members):
        return False
    if any(COUNTER_KEY in r.meta for r in members):
        return True
    from .config import counter_floor_mm
    line = _core(members) or list(members)
    if not line:
        return True
    try:
        narrow = line_min_counter_mm(line, p)
    except Exception:  # unmeasured: today's path, like a restore that fails
        return False
    wt = (thread_wts or {}).get(line[0].thread_index, default_wt)
    return narrow is None or narrow >= counter_floor_mm(floor_base_mm, wt)


def restore_small_text(regions: list[Region], p: Prep, *, cap_mm: float,
                       keep_stray_lines: bool = False,
                       min_counter_mm: float | None = None,
                       thread_wts: dict[int, int] | None = None,
                       default_wt: int = 40) -> list[dict]:
    """The true-size half of this module (`cfg.small_text_restore_mm`): no
    scale, no move. For every line of lettering under `cap_mm`, ADOPT the
    untagged letters of the line into its text cluster and RETRACE every
    letter from the source raster, so each keeps the counters stage 4
    dropped. A lettering tier that reads cluster members -- bean letters
    sews the centreline of a member's source ink -- then sees the whole
    line, the 8 included. -> one report row per cluster considered.

    `keep_stray_lines` (`cfg.small_text_keep_stray_lines`): strays that are
    themselves a line of lettering (`_core` finds three or more of one
    thread, one height, one baseline) keep their tags as a cluster of their
    own, and that cluster is considered in turn. At 65 mm the tagger puts
    Fremont's black THE in the tan date's cluster; stripped as strays, its
    three letters lost their lettering treatment, traced 1.8x fatter and the
    E closed (2026-10-14). False: every stray stripped, as before.

    `min_counter_mm` (`config.true_size_min_counter`, the switch's counter
    guard): a line whose narrowest source counter (`line_min_counter_mm`,
    over its letters and the ones it would adopt) is under `min_counter_mm x
    40 / wt` -- `wt` its thread's weight in `thread_wts`, else `default_wt`
    -- is left exactly as it was: nothing adopted, retraced or stripped. Its
    shapes are marked `GUARD_KEY` so the bean tagger leaves it too. A line
    with no counter passes. A guarded cluster stays whole, a stray line in it
    included (65 mm Fremont: THE in the date's cluster sews as on main):
    releasing it re-routes the rest of the design, the guarded lines with it."""
    report: list[dict] = []
    if not cap_mm or cap_mm <= 0 or not regions:
        return report
    clusters: dict[str, list[Region]] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid:
            clusters.setdefault(cid, []).append(r)
    claimed: set[int] = set()
    order = sorted(clusters)
    at = 0
    while at < len(order):
        cid = order[at]
        at += 1
        row = {"cluster": cid, "members": len(clusters[cid])}
        report.append(row)
        try:
            members = _core(clusters[cid])
            if len(members) < 3:
                row["skipped"] = "not_one_line"
                continue
            cap = float(np.median([_height(r) for r in members]))
            row["cap_mm"] = round(cap, 3)
            if cap <= 0 or cap >= cap_mm:
                row["skipped"] = "tall_enough"
                continue
            group = [r for r in _adopt(members, regions, cap) if id(r) not in claimed]
            if len(group) < len(members):
                row["skipped"] = "member_claimed"
                continue
            traced = _retrace(group, p, cap)
            if min_counter_mm:
                from .config import counter_floor_mm
                narrow = line_min_counter_mm(group, p, cap, traced=traced)
                wt = (thread_wts or {}).get(members[0].thread_index, default_wt)
                floor = counter_floor_mm(min_counter_mm, wt)
                row["min_counter_mm"] = None if narrow is None else round(narrow, 3)
                row["counter_floor_mm"] = round(floor, 3)
                if narrow is not None and narrow < floor:
                    # Under the switch's counter guard: today's path, untouched
                    # but for the mark that keeps the bean tagger off it too.
                    # The WHOLE cluster stays, a stray line in it included:
                    # releasing Fremont's THE from the guarded 65 mm date
                    # moved the black block's exit, so the tan block re-routed
                    # and the guarded tagline's runs were entered elsewhere --
                    # not today's path (measured 2026-10-15, PR #955).
                    for r in clusters[cid]:
                        r.meta[GUARD_KEY] = True
                    row["skipped"] = "below_min_counter"
                    continue
                for r in group:
                    r.meta[COUNTER_KEY] = row["min_counter_mm"]
            tags = {k: members[0].meta[k] for k in _CLUSTER_TAGS if k in members[0].meta}
            member_ids = {id(r) for r in members}
            for i, r in enumerate(group):
                shape = traced.get(i)
                if shape is not None and isinstance(shape, Polygon) and shape.is_valid and not shape.is_empty:
                    r.polygon = shape
                    r.area_mm2 = float(shape.area)
                    r.meta["small_text_restored"] = True
                if id(r) not in member_ids:
                    r.meta.update(tags)
                    r.meta["small_text_adopted"] = True
                claimed.add(id(r))
            # The tagger's strays leave the line. Fremont's tagline cluster
            # carries its two black separator bars and a twist of the rope;
            # bean letters reads a cluster's ink as one colour against its
            # ground, so with them in it the tagline was never read at all.
            # They sew as the ordinary shapes they are.
            line_ids = {id(r) for r in group}
            strays = [r for r in clusters[cid] if id(r) not in line_ids]
            kept = _stray_line(strays, keep_stray_lines)
            kept_ids = {id(r) for r in kept}
            for r in strays:
                if id(r) in kept_ids:
                    continue
                for k in _CLUSTER_TAGS:
                    r.meta.pop(k, None)
                r.meta["small_text_stray"] = True
            if kept:
                row["stray_line"] = _release(kept, f"{cid}.line{at}", clusters, order)
            row.update(adopted=len(group) - len(members), retraced=len(traced),
                       strays=len(strays))
        except Exception as exc:  # fail open
            row["skipped"] = f"error:{type(exc).__name__}"
    return report
