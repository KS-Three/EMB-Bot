"""Counters and slots per letter: artwork against the stitched output.

Built 2026-10-11 for Waiting-on-Kent item 38 (ship `coverage_edges` with
the Column lane, or not). `docs/coverage-edges-under-columns-2026-10-11.md`
saw, in pictures only, Becker's A lose its counter and the notch between its
legs at 50 mm, and the E's lower slot narrow at both sizes. PR #818 asked
for an instrument before any flip. This is it. It flips nothing.

What it reads, per letter
-------------------------
* **Counter**: an enclosed hole in the letter (the A's triangle, the R's
  bowl). Area in mm^2.
* **Slot**: a concavity of the letter's convex hull at least
  `SLOT_DEPTH_RATIO` as deep as its mouth is long (the E's two slots, the
  notch between the A's legs). Its width is a BOTTLENECK: the diameter of
  the largest disc that can travel from the slot's inner half out to its
  mouth band (`MOUTH_BAND` of its depth). A straight channel reads its own
  width; a channel the thread pinches part way out reads the pinch; a V
  notch reads its width about half way in. Thread within one thread width
  of the hull line is not an obstacle for the width: a single stitch laid
  across the mouth leaves the gap behind it as wide as it was, and the slot
  is reported `bridged` instead.

Both sides are read on ONE grid, `PX_PER_MM` (0.025 mm a pixel):

* **Artwork**: the file at native resolution, scaled to the design's width
  by the rule `artfidelity_self.art_ink_field` uses (the ink bbox is the
  design width). Alpha is read as the continuous coverage the file stores
  and cut at 0.5, so an anti-aliased edge lands where the file says it is;
  an opaque file uses the darkness rule. Each ink pixel takes the nearest
  thread colour of the design, and a letter is one connected component of
  one colour.
* **Stitched**: every needle-down segment of the thread colour that best
  matches the letter (IoU in its window), drawn as a ribbon
  `machine.COVERAGE_THREAD_W_MM` wide on `stitchviz._frame`'s pixels (the
  same footprint `render_design(lit=False)` paints). Not the polygon. The
  stitched frame is placed on the artwork by `artfidelity_self.register`'s
  shift, the registration every ink instrument shares, refined per letter
  by up to `REFINE_MM`.

Which components are letters: those more than half covered by thread
of a text-tagged shape, under either tagger (`text_candidate`,
`lettering_group`, or the L1 tagger's `word_id`), so the set does not move
when `lettering_words` flips.

Flags (both use the 0.4 mm thread, `machine.COVERAGE_THREAD_W_MM`):

* a counter **closes** when the artwork's is at least one thread squared
  (0.16 mm^2) and the stitched one is under it;
* a slot **narrows** when the artwork's width is at least one thread and
  the stitched width is under it.

A feature the artwork already draws under one thread is reported, marked
`art_sub_thread`, and never flagged: it was never sewable.

Usage, from `digitizer/` with the digitizer venv::

    python -m tools.counter_slots --fixture becker --widths 50,80 \
        --arms shipped,coverage_edges,columns_words,coverage_columns \
        --out OUTDIR [--cache DIR] [--crops A,E]

Writes OUTDIR/<fixture>.json and OUTDIR/<fixture>.md (the table). With
`--assert-inert ARM_A,ARM_B` it exits 1 unless the two arms produce the
same stitches and the same table (the opaque-file control: `coverage_edges`
reads alpha, so it must change nothing on an opaque file).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

from digitizer_core import machine
from digitizer_core.stitchviz import _frame

THREAD_MM = float(machine.COVERAGE_THREAD_W_MM)
PX_PER_MM = 40.0
PAD_MM = 2.0
# A component smaller than this is not a glyph (dots of anti-aliasing).
MIN_GLYPH_MM2 = 0.3
# An artwork counter under this is resampling noise, not a drawn counter.
MIN_COUNTER_MM2 = 0.02
# A concavity is a slot only if it is this big, this deep, and deeper than
# SLOT_DEPTH_RATIO of its mouth. On Becker's MARINE at 50 and 80 mm the
# flank wedges beside each letter's left stem read 0.07-0.10 (depth over
# mouth) and the shallowest real notches read 0.26-0.29 (the R's, between
# bowl and leg; the A's, between its legs); the cut sits between them.
# A slot's width is the bottleneck from its inner half out to this outer
# fraction of its depth (geodesic from the mouth): far enough in that a
# stitch laid along the hull line, across the mouth, cannot be the pinch.
MOUTH_BAND = 0.2
MIN_SLOT_MM2 = 0.05
MIN_SLOT_DEPTH_MM = 0.3
SLOT_DEPTH_RATIO = 0.2
# The window around a glyph, and how far past its artwork hull the stitched
# side may count thread (a neighbour's thread beyond this cannot reach a
# counter or slot, which both live inside the hull).
WINDOW_MM = 1.0
HULL_REACH_MM = THREAD_MM
# Per-letter refinement of the shared registration, which searches a 0.1 mm
# grid: a slot 0.4 mm wide cannot afford that half-step against the hull.
REFINE_MM = 0.1
# Below this IoU between a letter's artwork and its thread, the letter is
# reported `unread` with no features: the thread that lies there is not a
# rendering of that letter (Becker's MARINE reads 0.73-0.90).
MIN_LETTER_IOU = 0.25
TEXT_KEYS = ("text_candidate", "lettering_group", "word_id")

ARMS = {
    "shipped": {},
    "coverage_edges": {"coverage_edges": True},
    "columns_words": {"lettering_columns": True, "lettering_words": True},
    "coverage_columns": {"coverage_edges": True, "lettering_columns": True,
                         "lettering_words": True},
}


# --------------------------------------------------------------------------
# Raster geometry, one window at a time
# --------------------------------------------------------------------------

def _border_labels(lab: np.ndarray) -> set:
    return set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])).tolist())


def holes(solid: np.ndarray) -> tuple[np.ndarray, list[int]]:
    """-> (label image of the background, labels of ENCLOSED components).
    Background is 4-connected, the letter 8-connected, the usual pair."""
    n, lab = cv2.connectedComponents((~solid).astype(np.uint8), connectivity=4)
    edge = _border_labels(lab)
    return lab, [k for k in range(1, n) if k not in edge]


def fill_holes(solid: np.ndarray) -> np.ndarray:
    lab, ks = holes(solid)
    return solid | np.isin(lab, ks)


def hull_mask(solid: np.ndarray) -> np.ndarray:
    m = np.zeros(solid.shape, np.uint8)
    pts = cv2.findNonZero(solid.astype(np.uint8))
    if pts is not None:
        cv2.fillConvexPoly(m, cv2.convexHull(pts), 1)
    return m.astype(bool)


def _dilate(m: np.ndarray, r_px: int) -> np.ndarray:
    if r_px <= 0:
        return m
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_px + 1, 2 * r_px + 1))
    return cv2.dilate(m.astype(np.uint8), k).astype(bool)


_CROSS = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))


def _mouth(comp: np.ndarray, hull: np.ndarray) -> np.ndarray:
    """The concavity's pixels that touch the outside of the hull."""
    out = cv2.dilate((~hull).astype(np.uint8), _CROSS).astype(bool)
    return comp & out


def geodesic(comp: np.ndarray, seeds: np.ndarray) -> np.ndarray:
    """Distance in px from `seeds` inside `comp` (8-neighbour, diagonal
    sqrt 2); inf outside or unreachable."""
    from skimage.graph import MCP_Geometric
    cost = np.where(comp, 1.0, np.inf)
    starts = np.argwhere(seeds & comp)
    if len(starts) == 0:
        return np.full(comp.shape, np.inf)
    d, _ = MCP_Geometric(cost, fully_connected=True).find_costs(starts)
    d = np.where(comp, d, np.inf)
    return d


def _linked(region: np.ndarray, a: np.ndarray, b: np.ndarray) -> bool:
    n, lab = cv2.connectedComponents(region.astype(np.uint8), connectivity=8)
    la = set(np.unique(lab[a & region]).tolist()) - {0}
    lb = set(np.unique(lab[b & region]).tolist()) - {0}
    return bool(la & lb)


def bottleneck_px(comp: np.ndarray, dt: np.ndarray, src: np.ndarray,
                  dst: np.ndarray) -> float:
    """Largest r such that `comp & (dt >= r)` still links `src` to `dst`
    (a maximin path), in px of distance transform; 0 when none links.
    `dst` pixels are free: the path only has to REACH the band."""
    vals = np.unique(dt[comp & (dt > 0)])
    dst = dst & comp
    if len(vals) == 0 or not _linked(comp, src, dst):
        return 0.0
    lo, hi = 0, len(vals) - 1          # vals[lo] links; find the last that does
    if not _linked((comp & (dt >= vals[0])) | dst, src, dst):
        return 0.0
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if _linked((comp & (dt >= vals[mid])) | dst, src, dst):
            lo = mid
        else:
            hi = mid - 1
    return float(vals[lo])


def width_mm(r_px: float, ppm: float) -> float:
    """A channel w px wide has distance-transform ridge floor((w+1)/2): w is
    2r-1 (odd) or 2r (even), so 2r-0.5 is within half a pixel either way."""
    return 0.0 if r_px <= 0 else max(0.0, 2.0 * r_px - 0.5) / ppm


def _dist_to(solid: np.ndarray) -> np.ndarray:
    return cv2.distanceTransform((~solid).astype(np.uint8), cv2.DIST_L2,
                                 cv2.DIST_MASK_PRECISE)


def _centroid(m: np.ndarray, ppm: float) -> tuple[float, float]:
    ys, xs = np.nonzero(m)
    return round(float(xs.mean()) / ppm, 3), round(float(ys.mean()) / ppm, 3)


@dataclass
class Shape:
    """The artwork's counters and slots in one glyph window."""
    solid: np.ndarray
    hull: np.ndarray
    counters: list = field(default_factory=list)   # dicts, with "mask"
    slots: list = field(default_factory=list)      # dicts, with "mask", "inner"


def read_art(solid: np.ndarray, ppm: float) -> Shape:
    """Counters and slots of one glyph's artwork mask (bool window)."""
    hull = hull_mask(solid)
    sh = Shape(solid, hull)
    lab, ks = holes(solid)
    for k in ks:
        m = lab == k
        a = m.sum() / ppm ** 2
        if a >= MIN_COUNTER_MM2:
            sh.counters.append({"mask": m, "area_mm2": float(a), "at": _centroid(m, ppm)})
    filled = fill_holes(solid)
    conc = hull & ~filled
    n, clab = cv2.connectedComponents(conc.astype(np.uint8), connectivity=4)
    dt = _dist_to(filled)
    for k in range(1, n):
        m = clab == k
        a = m.sum() / ppm ** 2
        if a < MIN_SLOT_MM2:
            continue
        mouth = _mouth(m, hull)
        if not mouth.any():
            continue
        g = geodesic(m, mouth)
        depth = float(g[np.isfinite(g)].max()) / ppm
        # The mouth is a run of hull edge: its length is the long side of
        # its pixels' bounding rectangle (a pixel count would read a
        # diagonal chord up to sqrt 2 long).
        mouth_mm = max(cv2.minAreaRect(cv2.findNonZero(mouth.astype(np.uint8)))[1]) / ppm
        if depth < MIN_SLOT_DEPTH_MM or depth < SLOT_DEPTH_RATIO * mouth_mm:
            continue
        # One concavity can hold several slots: an E whose middle arm stops
        # short of the hull has ONE concavity and two slots. Each connected
        # piece of the concavity's inner half is its own slot, and each is
        # measured by its own bottleneck out to the shared mouth band.
        n_in, ilab = cv2.connectedComponents((m & (g >= 0.5 * depth * ppm)).astype(np.uint8),
                                             connectivity=8)
        outer = m & (g <= MOUTH_BAND * depth * ppm)
        for j in range(1, n_in):
            inner = ilab == j
            r = bottleneck_px(m, dt, inner, outer)
            sh.slots.append({"mask": m, "inner": inner, "outer": outer,
                             "strip": m & (g <= THREAD_MM * ppm),
                             "area_mm2": float(a),
                             "depth_mm": float(g[inner].max()) / ppm,
                             "mouth_mm": float(mouth_mm),
                             "width_mm": width_mm(r, ppm), "at": _centroid(inner, ppm)})
    # Top to bottom, then left to right, so "first slot" means the same
    # feature in every arm and the E's lower slot is its second.
    sh.counters.sort(key=lambda c: (c["at"][1], c["at"][0]))
    sh.slots.sort(key=lambda s: (s["at"][1], s["at"][0]))
    return sh


def read_sewn(art: Shape, sewn: np.ndarray, ppm: float) -> dict:
    """The stitched reading of each of the artwork's counters and slots.

    `sewn` is the letter colour's thread in the same window. Only thread
    within `HULL_REACH_MM` of the artwork's hull counts; both features live
    inside the hull, and a neighbour's thread past that reach would only
    invent enclosures between letters."""
    reach = _dilate(art.hull, int(round(HULL_REACH_MM * ppm)))
    sewn = sewn & reach
    lab, ks = holes(sewn)
    enclosed = np.isin(lab, ks)
    counters = []
    for c in art.counters:
        hit = set(np.unique(lab[c["mask"] & enclosed]).tolist()) - {0}
        if hit:
            m = np.isin(lab, list(hit))
            status = "open"
        else:
            m = c["mask"] & ~sewn            # open to the outside, or gone
            status = "breached" if m.any() else "closed"
        a = float(m.sum() / ppm ** 2)
        if status == "open" and a < THREAD_MM ** 2:
            status = "closed"
        counters.append({"area_mm2": a, "status": status})
    # Slots are read on the cloth the thread leaves, NOT hole-filled. One
    # stitch laid across a slot's mouth does not narrow the gap behind it:
    # thread within one thread width of the hull line, in the slot, or
    # outside the hull is not an obstacle for the WIDTH, and a slot whose
    # cloth no longer reaches the outside is reported `bridged`, a
    # different defect. The gap may run up to one thread past the
    # artwork's slot, so a slot the thread recedes from can read wider than
    # drawn; it stays inside the hull.
    cloth = ~sewn
    grow = int(round(THREAD_MM * ppm))
    outside = ~art.hull
    slots = []
    for s in art.slots:
        obst = sewn & art.hull & ~s["strip"]
        dt = _dist_to(obst)
        region = ~obst & art.hull & _dilate(s["mask"], grow)
        inner, outer = region & s["inner"], region & s["outer"]
        open_frac = float(inner.sum()) / max(1, int(s["inner"].sum()))
        r = bottleneck_px(region, dt, inner, outer) if inner.any() and outer.any() else 0.0
        w = width_mm(r, ppm)
        bridged = bool(inner.any()) and not _linked(cloth, inner, outside)
        status = "closed" if w <= 0 else ("bridged" if bridged else "open")
        slots.append({"width_mm": w, "inner_open_frac": round(open_frac, 3),
                      "status": status})
    return {"counters": counters, "slots": slots}


def compare(art: Shape, sewn: dict) -> dict:
    """The per-glyph row: artwork against stitched, with the two flags."""
    t2 = THREAD_MM ** 2
    cs, ss = [], []
    for a, s in zip(art.counters, sewn["counters"]):
        sub = a["area_mm2"] < t2
        cs.append({"at_mm": a["at"], "art_mm2": round(a["area_mm2"], 3),
                   "sewn_mm2": round(s["area_mm2"], 3), "status": s["status"],
                   "art_sub_thread": sub,
                   "closes": (not sub) and s["area_mm2"] < t2})
    for a, s in zip(art.slots, sewn["slots"]):
        sub = a["width_mm"] < THREAD_MM
        ss.append({"at_mm": a["at"], "art_width_mm": round(a["width_mm"], 3),
                   "sewn_width_mm": round(s["width_mm"], 3),
                   "art_depth_mm": round(a["depth_mm"], 3),
                   "inner_open_frac": s["inner_open_frac"],
                   "status": s["status"], "art_sub_thread": sub,
                   "narrows": (not sub) and s["width_mm"] < THREAD_MM})
    return {"counters": cs, "slots": ss}


# --------------------------------------------------------------------------
# Artwork and stitches on one canvas
# --------------------------------------------------------------------------

def _rgb(c: dict) -> tuple[int, int, int]:
    return int(c.get("r", 0)), int(c.get("g", 0)), int(c.get("b", 0))


def art_raster(image: str | Path, width_mm: float, ppm: float = PX_PER_MM):
    """-> (ink bool, rgb uint8) of the artwork, its ink bbox `width_mm` wide
    at `ppm`. The bbox is `art_ink_field`'s (alpha > 16, else darkness), so
    the registration shift applies unchanged; the edge is the file's own
    0.5 contour."""
    a = np.asarray(Image.open(image).convert("RGBA"))
    if a[..., 3].min() < 255:
        box = a[..., 3] > 16
        cov = a[..., 3].astype(np.float32) / 255.0
    else:
        box = a[..., :3].astype(np.int32).sum(axis=2) < 720
        cov = box.astype(np.float32)
    ys, xs = np.nonzero(box)
    sl = (slice(ys.min(), ys.max() + 1), slice(xs.min(), xs.max() + 1))
    cov, rgb = cov[sl], np.ascontiguousarray(a[..., :3][sl])
    tw = max(1, int(round(width_mm * ppm)))
    scale = tw / cov.shape[1]
    th = max(1, int(round(cov.shape[0] * scale)))
    interp = cv2.INTER_LINEAR if scale >= 1 else cv2.INTER_AREA
    ink = cv2.resize(cov, (tw, th), interpolation=interp) >= 0.5
    rgb = cv2.resize(rgb, (tw, th), interpolation=interp)
    return ink, rgb


@dataclass
class Glyph:
    gid: int
    colour: tuple            # artwork's median RGB
    box: tuple               # (y0, y1, x0, x1) in the ARTWORK raster
    solid: np.ndarray        # bool, the box's pixels of this component
    area_mm2: float


def art_glyphs(ink: np.ndarray, rgb: np.ndarray, palette: list[tuple],
               ppm: float = PX_PER_MM) -> list[Glyph]:
    """One glyph per connected component of one palette colour."""
    pal = np.array(palette, np.float32)
    d = ((rgb[..., None, :].astype(np.float32) - pal[None, None]) ** 2).sum(-1)
    layer = np.where(ink, d.argmin(-1), -1)
    out = []
    for ci in range(len(palette)):
        n, lab, stats, _ = cv2.connectedComponentsWithStats(
            (layer == ci).astype(np.uint8), connectivity=8)
        for k in range(1, n):
            x, y, w, h, area = stats[k]
            if area / ppm ** 2 < MIN_GLYPH_MM2:
                continue
            sl = (slice(y, y + h), slice(x, x + w))
            m = lab[sl] == k
            med = np.median(rgb[sl][m], axis=0)
            out.append(Glyph(len(out), tuple(int(v) for v in med), (y, y + h, x, x + w),
                             m, float(area / ppm ** 2)))
    return out


def thread_rasters(design: dict, tagged: set, ppm: float = PX_PER_MM):
    """-> (per-colour thread masks {rgb: bool}, tagged-shape thread mask),
    in `stitchviz._frame`'s pixels, every needle-down segment a ribbon one
    thread wide, colour advanced through the stream as `render_design`
    does."""
    st = design["stitches"]
    (h, w), to_px = _frame(st, ppm, PAD_MM)
    colors = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    shape_at = {}
    for r in design.get("runs", []):
        for i in range(r["i0"], r["i1"] + 1):
            shape_at[i] = r.get("shape") or ""
    tw = max(2, int(round(THREAD_MM * ppm)))
    masks: dict = {}
    tag = np.zeros((h, w), np.uint8)
    ci, prev = 0, None
    cur = _rgb(colors[0])
    for i, s in enumerate(st):
        k = s.get("type")
        if k == "color":
            ci += 1
            if ci < len(colors):
                cur = _rgb(colors[ci])
            prev = None
            continue
        if k != "stitch":
            prev = None
            continue
        p = to_px(s)
        if prev is not None and prev != p:
            m = masks.setdefault(cur, np.zeros((h, w), np.uint8))
            cv2.line(m, prev, p, 1, tw)
            if shape_at.get(i) in tagged:
                cv2.line(tag, prev, p, 1, tw)
        prev = p
    return {c: m.astype(bool) for c, m in masks.items()}, tag.astype(bool)


def tagged_shapes(result) -> set:
    return {r.shape_id for r in result.regions
            if any((r.meta or {}).get(k) for k in TEXT_KEYS)}


def palette_of(design: dict) -> list[tuple]:
    seen = []
    for c in design.get("colors") or []:
        if _rgb(c) not in seen:
            seen.append(_rgb(c))
    return seen


def measure(image: str | Path, design: dict, tagged: set,
            glyphs: list[Glyph] | None = None, ppm: float = PX_PER_MM,
            want_windows: bool = False, words: list[str] | None = None) -> dict:
    """Every letter's counters and slots, artwork against stitched."""
    from tools.artfidelity_self import register_design
    reg = register_design(image, design)
    width = float(design["widthMM"])
    ink, rgb = art_raster(image, width, ppm)
    if glyphs is None:
        glyphs = art_glyphs(ink, rgb, palette_of(design), ppm)
    masks, tag = thread_rasters(design, tagged, ppm)
    h, w = tag.shape
    ha, wa = ink.shape
    margin = int((WINDOW_MM + 3.0) * ppm)
    H, W = max(h, ha) + 2 * margin, max(w, wa) + 2 * margin
    sy, sx = (H - h) // 2, (W - w) // 2
    ay = (H - ha) // 2 + int(round(reg.dy_mm * ppm))
    ax = (W - wa) // 2 + int(round(reg.dx_mm * ppm))
    pal = list(masks)
    win = int(WINDOW_MM * ppm)
    rows = []
    for g in glyphs:
        y0, y1, x0, x1 = g.box
        # window in canvas coordinates, and the same window in each frame
        cy0, cy1, cx0, cx1 = ay + y0 - win, ay + y1 + win, ax + x0 - win, ax + x1 + win
        solid = np.zeros((cy1 - cy0, cx1 - cx0), bool)
        solid[win:win + (y1 - y0), win:win + (x1 - x0)] = g.solid

        def cut(m, ddy=0, ddx=0):
            out = np.zeros(solid.shape, bool)
            ty0, tx0 = cy0 - sy + ddy, cx0 - sx + ddx
            yy0, xx0 = max(0, ty0), max(0, tx0)
            yy1, xx1 = min(h, ty0 + solid.shape[0]), min(w, tx0 + solid.shape[1])
            if yy1 > yy0 and xx1 > xx0:
                out[yy0 - ty0:yy1 - ty0, xx0 - tx0:xx1 - tx0] = m[yy0:yy1, xx0:xx1]
            return out
        t = cut(tag)
        letter = bool((t & solid).sum() > 0.5 * solid.sum())
        if not letter:
            continue
        # The letter's thread is the colour whose thread best MATCHES its
        # artwork in the window (IoU), not the nearest RGB: a quantised
        # palette can sew a letter in a spool that is not its nearest match,
        # and a background fill sewn under the letter covers it too but
        # spills over the whole window.
        if pal:
            def _iou(c):
                m = cut(masks[c])
                u = np.count_nonzero(m | solid)
                return np.count_nonzero(m & solid) / u if u else 0.0
            thread_c = max(pal, key=_iou)
            full = masks[thread_c]
        else:
            thread_c, full = None, np.zeros(tag.shape, bool)
        # Refine the whole-design registration (a 0.1 mm grid) per letter:
        # the best whole-pixel shift within REFINE_MM by IoU of this
        # letter's artwork against its colour's thread.
        best = (-1.0, 0, 0)
        rr = int(round(REFINE_MM * ppm))
        for ddy in range(-rr, rr + 1):
            for ddx in range(-rr, rr + 1):
                sh = cut(full, ddy, ddx)
                u = np.count_nonzero(sh | solid)
                iou = np.count_nonzero(sh & solid) / u if u else 0.0
                if iou > best[0]:
                    best = (iou, ddy, ddx)
        sewn = cut(full, best[1], best[2])
        art = read_art(solid, ppm)
        if best[0] < MIN_LETTER_IOU:
            # Its own colour's thread barely lies on it: nothing here is a
            # reading of THIS letter's counters, so none is reported.
            row = {"counters": [], "slots": [], "unread": True}
        else:
            row = compare(art, read_sewn(art, sewn, ppm))
            row["unread"] = False
        row.update({"glyph": g.gid, "refine_px": [best[1], best[2]],
                    "letter_iou": round(best[0], 3), "art_rgb": list(g.colour),
                    "thread_rgb": list(thread_c) if thread_c else None,
                    "area_mm2": round(g.area_mm2, 2),
                    # artwork-frame centre, mm, y down: arm-independent key
                    "cx_mm": round((x0 + x1) / 2 / ppm, 2),
                    "cy_mm": round((y0 + y1) / 2 / ppm, 2),
                    "h_mm": round((y1 - y0) / ppm, 2)})
        if want_windows:
            row["_window"] = (cy0 - sy + best[1], cx0 - sx + best[2], art, sewn)
        rows.append(row)
    name_lines(rows, words)
    return {"width_mm": width, "shift_mm": [reg.dx_mm, reg.dy_mm],
            "letters": rows}


def name_lines(rows: list[dict], words: list[str] | None = None) -> None:
    """Group letters into lines (by vertical overlap) and number them left
    to right: `L1.3` is line 1's third letter. With `words` (one per line,
    top to bottom) and matching counts, the letter itself names it."""
    rows.sort(key=lambda r: r["cy_mm"])
    lines: list[list[dict]] = []
    for r in rows:
        if lines and abs(r["cy_mm"] - np.mean([q["cy_mm"] for q in lines[-1]])) < 0.5 * r["h_mm"]:
            lines[-1].append(r)
        else:
            lines.append([r])
    for li, ln in enumerate(lines):
        ln.sort(key=lambda r: r["cx_mm"])
        for k, r in enumerate(ln):
            r["line"], r["pos"] = li + 1, k + 1
            r["name"] = f"L{li + 1}.{k + 1}"
            if words and li < len(words) and len(words[li]) == len(ln):
                r["name"] = f"{words[li]}:{words[li][k]}"
    rows.sort(key=lambda r: (r["line"], r["pos"]))


# --------------------------------------------------------------------------
# The matrix: fixtures x widths x arms
# --------------------------------------------------------------------------

FIXTURES = {
    # BECKER is knocked OUT of a dark panel (its letters are cloth, not
    # ink), so the only ink letters are MARINE's.
    "becker": ("becker_marine_logo.png", "left_chest", ["MARINE"]),
    "hotel_fremont": ("photo/logo_hotel_fremont.webp", "patch", None),
    "golden_tee": ("photo/logo_golden_tee.jpg", "left_chest", None),
}


def _art(fixture: str) -> Path:
    return Path(__file__).resolve().parent.parent / "testdata" / FIXTURES[fixture][0]


def digitize(fixture: str, width: float, arm: str, cache: Path | None):
    """-> (design, tagged shape ids), from `cache` when it holds the cell."""
    key = f"{fixture}-{int(width)}mm-{arm}"
    if cache is not None and (cache / f"{key}.json").exists():
        d = json.loads((cache / f"{key}.json").read_text(encoding="utf-8"))
        return d["design"], set(d["tagged"])
    from tools.eye_pairs.features import base_cfg, digitize_once
    _rel, garment, _w = FIXTURES[fixture]
    cfg = base_cfg(width, garment, **ARMS[arm])
    _gen, result, _plan, design = digitize_once(_art(fixture), cfg)
    tagged = tagged_shapes(result)
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
        (cache / f"{key}.json").write_text(json.dumps(
            {"design": design, "tagged": sorted(tagged)}), encoding="utf-8")
    return design, tagged


def _strip(res: dict) -> dict:
    return {**res, "letters": [{k: v for k, v in r.items() if not k.startswith("_")}
                               for r in res["letters"]]}


def _fmt_counter(c: dict) -> str:
    flag = " **CLOSES**" if c["closes"] else ""
    sub = " (art < 1 thread)" if c["art_sub_thread"] else ""
    return f"{c['art_mm2']:.2f} / {c['sewn_mm2']:.2f} {c['status']}{flag}{sub}"


def _fmt_slot(s: dict) -> str:
    flag = " **NARROWS**" if s["narrows"] else ""
    sub = " (art < 1 thread)" if s["art_sub_thread"] else ""
    return f"{s['art_width_mm']:.2f} / {s['sewn_width_mm']:.2f} {s['status']}{flag}{sub}"


def table(report: dict) -> str:
    """Markdown: one row per letter that has a counter or a slot. Counters
    `art / sewn mm^2`, slots `art / sewn min-width mm`."""
    out = []
    for cell, res in report.items():
        out.append(f"\n### {cell}\n")
        unread = [r["name"] for r in res["letters"] if r.get("unread")]
        if unread:
            out.append(f"Unread (letter IoU under {MIN_LETTER_IOU}): {', '.join(unread)}\n")
        out.append("| letter | counters art / sewn mm² | slots art / sewn width mm | IoU |")
        out.append("|---|---|---|---|")
        for r in res["letters"]:
            if not r["counters"] and not r["slots"]:
                continue
            cs = "; ".join(_fmt_counter(c) for c in r["counters"]) or "-"
            ss = "; ".join(_fmt_slot(s) for s in r["slots"]) or "-"
            out.append(f"| {r['name']} | {cs} | {ss} | {r['letter_iou']} |")
    return "\n".join(out) + "\n"


def _signature(res: dict) -> list:
    return [(r["name"], r["counters"], r["slots"]) for r in res["letters"]]


def crops(cells: dict, names: list[str], out: Path, ppm: float, scale: int = 2) -> None:
    """One sheet per (width, letter): the arms side by side, each the thread
    render of the letter's window with the artwork's edge in green and its
    counters and slots in magenta."""
    from digitizer_core.stitchviz import render_design
    by_width: dict = {}
    for (fixture, width, arm), (design, res) in cells.items():
        by_width.setdefault((fixture, width), []).append((arm, design, res))
    for (fixture, width), arms in by_width.items():
        renders = {arm: render_design(d, px_per_mm=ppm, pad_mm=PAD_MM) for arm, d, _ in arms}
        for name in names:
            tiles = []
            for arm, _d, res in arms:
                row = next((r for r in res["letters"] if r["name"].endswith(":" + name)
                            or r["name"] == name), None)
                if row is None or "_window" not in row:
                    continue
                ty, tx, art, _sewn = row["_window"]
                img = renders[arm]
                hh, ww = art.solid.shape
                tile = np.full((hh, ww, 3), 240, np.uint8)
                yy0, xx0 = max(0, ty), max(0, tx)
                yy1, xx1 = min(img.shape[0], ty + hh), min(img.shape[1], tx + ww)
                tile[yy0 - ty:yy1 - ty, xx0 - tx:xx1 - tx] = img[yy0:yy1, xx0:xx1]
                tile = cv2.resize(tile, (ww * scale, hh * scale), interpolation=cv2.INTER_NEAREST)
                masks = [(art.solid, (60, 200, 60))]
                masks += [(c["mask"], (200, 0, 200)) for c in art.counters]
                masks += [(s["mask"], (200, 0, 200)) for s in art.slots]
                for m, col in masks:
                    big = cv2.resize(m.astype(np.uint8), (ww * scale, hh * scale),
                                     interpolation=cv2.INTER_NEAREST)
                    cs, _ = cv2.findContours(big, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
                    cv2.drawContours(tile, cs, -1, col, 1)
                bar = np.full((28, tile.shape[1], 3), 235, np.uint8)
                cv2.putText(bar, f"{arm} {int(width)} mm", (4, 20), cv2.FONT_HERSHEY_SIMPLEX,
                            0.5, (20, 20, 20), 1, cv2.LINE_AA)
                tiles.append(np.vstack([bar, tile]))
            if not tiles:
                continue
            H = max(t.shape[0] for t in tiles)
            tiles = [cv2.copyMakeBorder(t, 0, H - t.shape[0], 0, 6, cv2.BORDER_CONSTANT,
                                        value=(255, 255, 255)) for t in tiles]
            safe = name.replace(":", "-")
            # JPEG: the PNG sheets ran 1.6-3.7 MB each in a public repo.
            cv2.imwrite(str(out / f"{fixture}-{int(width)}mm-{safe}.jpg"), np.hstack(tiles),
                        [cv2.IMWRITE_JPEG_QUALITY, 88])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fixture", required=True, choices=sorted(FIXTURES))
    ap.add_argument("--widths", default="80")
    ap.add_argument("--arms", default="shipped,coverage_edges")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--crops", default="", help="letter names, e.g. A,E")
    ap.add_argument("--assert-inert", default="",
                    help="ARM_A,ARM_B: exit 1 unless both give the same stitches and table")
    ap.add_argument("--digitize-only", action="store_true")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    words = FIXTURES[a.fixture][2]
    image = _art(a.fixture)
    widths = [float(w) for w in a.widths.split(",")]
    arms = a.arms.split(",")
    names = [n for n in a.crops.split(",") if n]
    report, cells, designs = {}, {}, {}
    for width in widths:
        glyphs = None
        for arm in arms:
            design, tagged = digitize(a.fixture, width, arm, a.cache)
            if a.digitize_only:
                print(f"digitized {a.fixture} {int(width)} {arm}", flush=True)
                continue
            if glyphs is None:
                # The FIRST arm's palette fixes the artwork's letters for
                # every arm at this width, so rows join on the same glyph.
                ink, rgb = art_raster(image, float(design["widthMM"]))
                glyphs = art_glyphs(ink, rgb, palette_of(design))
            res = measure(image, design, tagged, glyphs, want_windows=bool(names), words=words)
            key = f"{a.fixture} {int(width)} mm {arm}"
            report[key] = _strip(res)
            cells[(a.fixture, width, arm)] = (design, res)
            designs[(width, arm)] = design
            n_c = sum(len(r["counters"]) for r in res["letters"])
            n_s = sum(len(r["slots"]) for r in res["letters"])
            flags = sum(c["closes"] for r in res["letters"] for c in r["counters"]) + \
                sum(s["narrows"] for r in res["letters"] for s in r["slots"])
            print(f"{key}: {len(res['letters'])} letters, {n_c} counters, {n_s} slots, "
                  f"{flags} flags", flush=True)
    if a.digitize_only:
        return 0
    rc = 0
    if a.assert_inert:
        x, y = a.assert_inert.split(",")
        inert = {}
        for width in widths:
            same_st = designs[(width, x)]["stitches"] == designs[(width, y)]["stitches"]
            same_tab = _signature(report[f"{a.fixture} {int(width)} mm {x}"]) == \
                _signature(report[f"{a.fixture} {int(width)} mm {y}"])
            inert[f"{int(width)} mm"] = {"same_stitches": same_st, "same_table": same_tab}
            rc |= 0 if (same_st and same_tab) else 1
        report["_inert"] = {"arms": [x, y], **inert}
        print("inert:", json.dumps(inert), flush=True)
    (a.out / f"{a.fixture}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    (a.out / f"{a.fixture}.md").write_text(
        table({k: v for k, v in report.items() if not k.startswith("_")}), encoding="utf-8")
    if names:
        crops(cells, names, a.out, PX_PER_MM)
    return rc


if __name__ == "__main__":
    sys.exit(main())
