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


def counter_widths_mm(polys) -> list[float]:
    """Every counter (interior ring) of `polys`, as the diameter of its widest
    inscribed circle in mm (`shapely.ops.polylabel`, 0.01 mm tolerance) --
    `columns._wide_counters`' measure of how wide a counter is."""
    from shapely.ops import polylabel

    out: list[float] = []
    for poly in polys:
        for ring in getattr(poly, "interiors", ()):
            c = Polygon(ring).buffer(0)
            for q in _polys(c):
                if q.area > 0:
                    out.append(2.0 * float(polylabel(q, tolerance=0.01).distance(q.exterior)))
    return out


def line_min_counter_mm(group: list[Region], p: Prep, cap: float | None = None,
                        traced: dict[int, Polygon] | None = None) -> float | None:
    """The true-size switch's counter guard (`config.true_size_min_counter`):
    the narrowest SOURCE counter of a line's letters, in mm across -- each
    letter re-read from the raster (`_retrace`, the same read
    `restore_small_text` restores from, so the counters stage 4's sliver
    floor dropped count). A letter the retrace could not read is measured on
    its traced polygon. None: the line has no counter (it passes the guard)."""
    if traced is None:
        traced = _retrace(group, p, cap if cap else line_cap_mm(group))
    polys = [traced.get(i, r.polygon) for i, r in enumerate(group)]
    widths = counter_widths_mm(polys)
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


def _place_line(items: list[dict], bounds: Polygon, s_max: float, cap_mm: float):
    """One scale and one vertical move for the whole line -- two halves of a
    date either side of an emblem must keep one baseline -- and each
    cluster's own smallest sideways move. -> (s, dy, [dx per item]) or None."""
    shifts = _offsets(MAX_SHIFT_CAPS * cap_mm)
    steps = 8
    for k in range(steps + 1):
        s = s_max - (s_max - MIN_SCALE) * k / steps
        if s < MIN_SCALE - 1e-9:
            break
        grown = []
        for it in items:
            c = it["hull"].centroid
            widen = max(0.0, (MIN_STROKE_MM - s * it["stroke"]) / 2.0) if it["stroke"] > 0 else 0.0
            grown.append(affinity.scale(it["hull"], s, s, origin=(c.x, c.y)).buffer(widen + CLEAR_MM))
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


def enlarge_small_text(regions: list[Region], p: Prep, *, cap_mm: float) -> list[dict]:
    """Enlarge, in place, every line of lettering under `cap_mm`. See the
    module docstring. -> one report row per text cluster it considered."""
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

    for line in lines:
        try:
            line.sort(key=lambda it: it["hull"].bounds[0])
            ids = {id(r) for it in line for r in it["group"]}
            cap = float(np.median([it["cap"] for it in line]))
            for it in line:
                hull = it["hull"]
                near = hull.buffer(MAX_SCALE * max(cap_mm, hull.bounds[2] - hull.bounds[0]))
                blockers = []
                for r in regions:
                    if id(r) in ids or not r.polygon.intersects(near):
                        continue
                    # The ground the line sits on is not in its way.
                    if r.polygon.intersection(hull).area >= 0.5 * hull.area:
                        continue
                    blockers.append(r.polygon)
                it["obstacles"] = unary_union(blockers) if blockers else None
            found = _place_line(line, design, min(MAX_SCALE, cap_mm / cap), cap_mm)
            if found is None:
                for it in line:
                    it["row"]["skipped"] = "no_room"
                continue
            s, dy, dxs = found
            for it, dx in zip(line, dxs):
                widen = max(0.0, (MIN_STROKE_MM - s * it["stroke"]) / 2.0) if it["stroke"] > 0 else 0.0
                origin = (it["hull"].centroid.x, it["hull"].centroid.y)
                old_union = unary_union([r.polygon for r in it["group"]])
                for r, shape in zip(it["group"], it["shapes"]):
                    moved = affinity.translate(affinity.scale(shape, s, s, origin=origin), dx, dy)
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
                        r.meta["text_cluster_stroke_mm"] = float(r.meta["text_cluster_stroke_mm"]) * s + widen
                _fill_old_holes(regions, {id(r) for r in it["group"]}, old_union)
                it["row"].update(scale=round(s, 3), shift_mm=(round(dx, 2), round(dy, 2)),
                                 adopted=len(it["group"]) - it["members"], retraced=it["traced"],
                                 widened_mm=round(widen, 3))
        except Exception as exc:  # fail open
            for it in line:
                it["row"]["skipped"] = f"error:{type(exc).__name__}"
    return report


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
    wt =(thread_wts or {}).get(line[0].thread_index, default_wt)
    return narrow is None or narrow >= counter_floor_mm(floor_base_mm, wt)


def restore_small_text(regions: list[Region], p: Prep, *, cap_mm: float,
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

    `min_counter_mm` (`config.true_size_min_counter`, the switch's counter
    guard): a line whose narrowest source counter (`line_min_counter_mm`,
    over its letters and the ones it would adopt) is under `min_counter_mm x
    wt / 40` -- `wt` its thread's weight in `thread_wts`, else `default_wt`
    -- is left exactly as it was: nothing adopted, retraced or stripped. Its
    shapes are marked `GUARD_KEY` so the bean tagger leaves it too. A line
    with no counter passes."""
    report: list[dict] = []
    if not cap_mm or cap_mm <= 0 or not regions:
        return report
    clusters: dict[str, list[Region]] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid:
            clusters.setdefault(cid, []).append(r)
    claimed: set[int] = set()
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
            for r in strays:
                for k in _CLUSTER_TAGS:
                    r.meta.pop(k, None)
                r.meta["small_text_stray"] = True
            row.update(adopted=len(group) - len(members), retraced=len(traced),
                       strays=len(strays))
        except Exception as exc:  # fail open
            row["skipped"] = f"error:{type(exc).__name__}"
    return report
