"""The pro's sewn outline, per letter, registered into the engine's frame.

Reader for a commercial DST/PES (pystitch, the repo's MIT reader): each
colour block's needle-down passes, the satin crosses in them, and the
"sewn outline" as the closing of the crosses' union (buffer out, buffer
back, so the outline is the rails' envelope and not a thread-width larger).

Registration is a similarity (uniform scale from the two designs' widths,
y flipped from the file's y-up, then a translation found by maximising the
raster IoU between the pro's lettering and ours) -- the same shape of
search `tools/pro_parity/pairframe.register_pair` does between two files,
written here against region polygons instead of a second stitch file.
Per letter, the pro's component nearest our letter's centroid is matched,
and two readings are reported: in the registered frame as is, and after
centring the pro letter on ours (shape alone, placement removed).

The Becker file is the committed copy
`testdata/reference/becker_hat_polo_large_beckers_logolc.dst` (95.7 x 58.3
mm, the fixture's own width) -- `scratch_kent/` holds the same bytes.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pystitch
from shapely.geometry import LineString, MultiPolygon, Polygon
from shapely.ops import unary_union

THREAD_MM = 0.4
SATIN_MIN_MM = 0.6        # a satin cross is at least this long ...
SATIN_MAX_MM = 7.0        # ... and at most this (the pro's p99 is 6.2)
CLOSE_MM = 0.3            # closing radius: joins crosses up to 0.6 mm apart


def passes_of(path: Path) -> list[list[np.ndarray]]:
    """Colour blocks of needle-down passes, in mm, y-up as the file has it."""
    pat = pystitch.read(str(path))
    out: list[list[np.ndarray]] = [[]]
    cur: list[tuple[float, float]] = []
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            continue
        if len(cur) >= 2:
            out[-1].append(np.array(cur))
        cur = []
        if cmd == pystitch.COLOR_CHANGE:
            out.append([])
        elif cmd == pystitch.END:
            break
    if len(cur) >= 2:
        out[-1].append(np.array(cur))
    return [b for b in out if b]


def satin_crosses(passes: list[np.ndarray]) -> list[LineString]:
    """Consecutive stitches that zigzag: a cross is a stitch in the satin
    length band whose predecessor and successor both turn back on it."""
    crosses = []
    for P in passes:
        if len(P) < 3:
            continue
        d = np.diff(P, axis=0)
        L = np.hypot(*d.T)
        for i in range(len(d)):
            if not (SATIN_MIN_MM <= L[i] <= SATIN_MAX_MM):
                continue
            # a zigzag reverses on BOTH sides of a cross; a fill row reverses
            # only at its end, so one-sided reversals are not crosses
            sides = []
            for j in (i - 1, i + 1):
                if 0 <= j < len(d) and L[j] > 1e-6:
                    sides.append(float(d[i] @ d[j]) / (L[i] * L[j]) < -0.5)
            if sides and all(sides):
                crosses.append(LineString([P[i], P[i + 1]]))
    return crosses


def sewn_outline(crosses: list[LineString]) -> Polygon | MultiPolygon:
    if not crosses:
        return Polygon()
    u = unary_union([c.buffer(CLOSE_MM, cap_style=2) for c in crosses])
    return u.buffer(-CLOSE_MM)


@dataclass
class Registration:
    scale: float
    dx: float
    dy: float
    iou: float
    flip_y: bool = True

    def apply(self, geom):
        from shapely.affinity import affine_transform
        # x' = s x + dx ; y' = (-)s y + dy  -- both y conventions are tried on
        # the whole design and the better IoU decides (`pro_letters_for`)
        sy = -self.scale if self.flip_y else self.scale
        return affine_transform(geom, [self.scale, 0, 0, sy, self.dx, self.dy])


def _raster(geoms, box, ppm: float) -> np.ndarray:
    x0, y0, x1, y1 = box
    H, W = int((y1 - y0) * ppm) + 1, int((x1 - x0) * ppm) + 1
    m = np.zeros((H, W), np.uint8)
    for g in geoms:
        for poly in getattr(g, "geoms", [g]):
            if poly.is_empty:
                continue
            cv2.fillPoly(m, [np.round((np.asarray(poly.exterior.coords) - (x0, y0)) * ppm).astype(np.int32)], 1)
            for h in poly.interiors:
                cv2.fillPoly(m, [np.round((np.asarray(h.coords) - (x0, y0)) * ppm).astype(np.int32)], 0)
    return m


def register(pro_outline, ours: list[Polygon], pro_width_mm: float, our_width_mm: float,
             search_mm: float = 4.0, ppm: float = 10.0, flip_y: bool = True) -> Registration:
    """Scale from the widths, flip y (or not), centre the bounding boxes,
    then the translation that maximises raster IoU (coarse 0.5 mm, then
    0.1 mm)."""
    s = our_width_mm / pro_width_mm
    base = Registration(s, 0.0, 0.0, 0.0, flip_y)
    pro0 = base.apply(pro_outline)
    ob = unary_union(ours).bounds
    pb = pro0.bounds
    dx0 = (ob[0] + ob[2]) / 2 - (pb[0] + pb[2]) / 2
    dy0 = (ob[1] + ob[3]) / 2 - (pb[1] + pb[3]) / 2
    box = (min(ob[0], pb[0] + dx0) - search_mm - 1, min(ob[1], pb[1] + dy0) - search_mm - 1,
           max(ob[2], pb[2] + dx0) + search_mm + 1, max(ob[3], pb[3] + dy0) + search_mm + 1)
    A = _raster(ours, box, ppm).astype(bool)
    from shapely.affinity import translate
    best = (-1.0, dx0, dy0)

    def iou_at(dx, dy):
        B = _raster([translate(pro0, dx, dy)], box, ppm).astype(bool)
        inter = (A & B).sum()
        return inter / max((A | B).sum(), 1)

    for step, rad in ((0.5, search_mm), (0.1, 0.6)):
        cx, cy = best[1], best[2]
        for dx in np.arange(cx - rad, cx + rad + 1e-9, step):
            for dy in np.arange(cy - rad, cy + rad + 1e-9, step):
                v = iou_at(dx, dy)
                if v > best[0]:
                    best = (v, dx, dy)
    return Registration(s, float(best[1]), float(best[2]), float(best[0]), flip_y)


def overlay_png(pro_geom, design: list[Polygon], letters: list[Polygon], path: Path,
                ppm: float = 8.0) -> Path:
    """Our design (grey), our letters (red outline) and the registered pro
    geometry (green) in one frame, for the eye that checks a registration."""
    b = unary_union(design).bounds
    pb = pro_geom.bounds
    x0, y0 = min(b[0], pb[0]) - 2, min(b[1], pb[1]) - 2
    x1, y1 = max(b[2], pb[2]) + 2, max(b[3], pb[3]) + 2
    H, W = int((y1 - y0) * ppm) + 1, int((x1 - x0) * ppm) + 1
    im = np.full((H, W, 3), 255, np.uint8)

    def px(coords):
        return np.round((np.asarray(coords) - (x0, y0)) * ppm).astype(np.int32)

    for g in design:
        for poly in getattr(g, "geoms", [g]):
            cv2.fillPoly(im, [px(poly.exterior.coords)], (200, 200, 200))
            for h in poly.interiors:
                cv2.fillPoly(im, [px(h.coords)], (255, 255, 255))
    for poly in getattr(pro_geom, "geoms", [pro_geom]):
        if poly.is_empty:
            continue
        cv2.polylines(im, [px(poly.exterior.coords)], True, (40, 160, 40), 1, cv2.LINE_AA)
        for h in poly.interiors:
            cv2.polylines(im, [px(h.coords)], True, (40, 160, 40), 1, cv2.LINE_AA)
    for poly in letters:
        cv2.polylines(im, [px(poly.exterior.coords)], True, (30, 30, 220), 1, cv2.LINE_AA)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), im)
    return path


@dataclass
class LetterMatch:
    shape_id: str
    pro: Polygon | None
    hausdorff: float | None
    iou: float | None
    hausdorff_centred: float | None
    iou_centred: float | None


def _iou(a, b) -> float:
    ia = a.intersection(b).area
    return ia / max(a.union(b).area, 1e-9)


def compare(our: Polygon, pro: Polygon | None) -> tuple:
    if pro is None or pro.is_empty:
        return None, None, None, None
    from shapely.affinity import translate
    h = our.hausdorff_distance(pro)
    i = _iou(our, pro)
    c1, c2 = our.centroid, pro.centroid
    pc = translate(pro, c1.x - c2.x, c1.y - c2.y)
    return float(h), float(i), float(our.hausdorff_distance(pc)), float(_iou(our, pc))


def match_letters(pro_outline, reg: Registration, letters: dict[str, Polygon]) -> dict[str, Polygon | None]:
    """Our shape_id -> the pro component with the largest overlap (None when
    nothing overlaps). Components are the registered outline's polygons."""
    P = reg.apply(pro_outline)
    comps = [g for g in getattr(P, "geoms", [P]) if not g.is_empty]
    # A letter the pro sews as a satin BORDER round unsewn ground (Becker's
    # white band letters: black fill with the letter as a hole, then a black
    # satin ring round it) is the ring's HOLE, so holes are candidates too.
    cands = list(comps) + [Polygon(h.coords) for g in comps for h in g.interiors]
    out: dict[str, Polygon | None] = {}
    for sid, poly in letters.items():
        best, best_a = None, 0.0
        for g in cands:
            if not g.is_valid:
                continue
            a = g.intersection(poly).area
            if a > best_a:
                best, best_a = g, a
        out[sid] = best
    return out


def thread_footprint(passes: list[np.ndarray]) -> Polygon | MultiPolygon:
    """Every stitch of a block, buffered to thread width: the whole design's
    sewn area, for the whole-design registration."""
    segs = [LineString([P[i], P[i + 1]]) for P in passes for i in range(len(P) - 1)
            if math.dist(P[i], P[i + 1]) <= 12.0]
    return unary_union([s.buffer(THREAD_MM / 2, cap_style=2) for s in segs]) if segs else Polygon()


def pro_letters_for(path: Path, letters: dict[str, Polygon], design: list[Polygon],
                    our_width_mm: float) -> tuple[dict[str, Polygon | None], Registration, int, Registration]:
    """Everything in one call. Registration is found on the WHOLE design
    (every pro stitch's footprint against every region of ours) -- both
    sides are the full logo, so the bounding boxes agree and the IoU search
    has one basin. The lettering block is then the one whose satin outline
    overlaps our letters most, and the registration is refined on it with a
    short search. Returns (our shape_id -> pro letter, refined registration,
    block index, whole-design registration)."""
    blocks = passes_of(path)
    outlines = [sewn_outline(satin_crosses(b)) for b in blocks]
    all_pts = np.vstack([np.vstack(b) for b in blocks])
    pro_w = float(all_pts[:, 0].max() - all_pts[:, 0].min())
    whole = unary_union([thread_footprint(b) for b in blocks])
    reg0 = max((register(whole, design, pro_w, our_width_mm, search_mm=3.0, ppm=6.0, flip_y=f)
                for f in (True, False)), key=lambda r: r.iou)
    # each letter takes the block whose satin outline overlaps it most (a
    # white band letter and a black MARINE letter live in different blocks)
    block_of: dict[str, int] = {}
    for sid, poly in letters.items():
        scores = [reg0.apply(o).intersection(poly).area if not o.is_empty else 0.0 for o in outlines]
        if max(scores) > 0:
            block_of[sid] = int(np.argmax(scores))
    # refine the registration per block on that block's letters alone,
    # starting from the whole-design answer, with a short search
    from shapely.affinity import translate
    regs: dict[int, Registration] = {}
    out: dict[str, Polygon | None] = {sid: None for sid in letters}
    for bi in sorted(set(block_of.values())):
        ours = {sid: p for sid, p in letters.items() if block_of[sid] == bi}
        pro_b = reg0.apply(outlines[bi])
        ob = unary_union(list(ours.values())).bounds
        box = (ob[0] - 3, ob[1] - 3, ob[2] + 3, ob[3] + 3)
        A = _raster(list(ours.values()), box, 10.0).astype(bool)
        best = (-1.0, 0.0, 0.0)
        for step, rad in ((0.2, 1.0), (0.05, 0.25)):
            cx, cy = best[1], best[2]
            for dx in np.arange(cx - rad, cx + rad + 1e-9, step):
                for dy in np.arange(cy - rad, cy + rad + 1e-9, step):
                    B = _raster([translate(pro_b, dx, dy)], box, 10.0).astype(bool)
                    v = (A & B).sum() / max((A | B).sum(), 1)
                    if v > best[0]:
                        best = (float(v), float(dx), float(dy))
        reg = Registration(reg0.scale, reg0.dx + best[1], reg0.dy + best[2], best[0], reg0.flip_y)
        regs[bi] = reg
        out.update(match_letters(outlines[bi], reg, ours))
    return out, regs, block_of, reg0, whole, outlines
