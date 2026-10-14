"""The per-glyph SHAPE read of sewn lettering, as importable array logic.

Moved here from `tools/glyph_legibility.py` (#906, pull-aware since #935) so
preflight can read the same numbers on a finished job without importing a
tool. The tool keeps its CLI, its cases, its OCR second reader and its
statistics, and imports everything below from here; its docstring is still
the full account of what each reading means and what it is NOT (not a
sew-out, not a threshold). In short, per glyph, every reading in [0, 1]:

  strokes   medial-axis recall: how much of the source's skeleton has thread
            on it (a missing arm, a lost "1").
  clean     1 - the share of thread more than `COMP_TOL_MM` off the source ink.
  counters  Euler read, matched one to one: a source counter that holds a
            circle of half a thread must show as a hole in the thread; a hole
            in the thread where the source has none counts against it.
  space     the ridge of every bay and counter keeps a clear circle.

`legibility` is the weakest of strokes, clean and counters.

The second half of this module, `read_design_words`, is what preflight adds:
the word boxes come from the regions stage 4 tagged as lettering instead of
hand boxes, and the source is the prepped raster the design was traced from,
so the registration is the plan's own frame and no correlation search runs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

P = 20.0                    # working grid, px per mm
PAD_MM = 2.0                # render_design's own pad
COMP_TOL_MM = 0.50          # push compensation: thread this far off the ink is not "off"
SPACE_MIN_HALF_MM = 0.15    # a bay or counter is read when a circle this big fits in the source
SPACE_KEEP_HALF_MM = 0.10   # ... and it survives when thread leaves a clear circle this big
SKEL_TOL_MM = 0.15          # a skeleton point is "sewn" with thread this close
SHIFT_MM = 0.80             # per-glyph translation the read may take
MIN_GLYPH_MM2 = 0.12        # smaller source components are specks, not glyphs
GROUND_DIST = 60.0          # a thread this far (RGB) from the ground is ink
MIN_HOLE_DIAM_THREADS = 0.5  # a counter counts when a circle of this x thread fits in it
PULL_LINES = "ink"          # what the pull leaves of a thread-wide line: "ink" = the ones lying on the
                            # artwork's ink, "all", or "none" (a plain erosion); `--pull-lines`


# --- source ink ------------------------------------------------------------

def ground_colour(rgb: np.ndarray, alpha: np.ndarray, box_px=None, ring_only: bool = True) -> np.ndarray:
    """The mode colour (16-level quantised) of the RING around a word box (or
    around the whole image), 4% of its short side wide: the ground is what the
    lettering sits on, and a ring cannot be out-voted by heavy lettering the
    way the whole box can (Becker's letters are most of its ink). With
    `ring_only=False` the whole box votes: right when the box overhangs the
    ground it sits on (Bridge's lettering sits on a yellow disc and its box
    reaches the black rim and the white beyond)."""
    if box_px is not None:
        x0, y0, x1, y1 = box_px
        rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    h, w = rgb.shape[:2]
    k = max(2, int(0.04 * min(h, w)))
    ring = np.ones((h, w), bool)
    if ring_only:
        ring[k:h - k, k:w - k] = False
    px = rgb[ring & (alpha >= 128)].reshape(-1, 3)
    if len(px) == 0:
        return np.array([255.0, 255.0, 255.0], np.float32)
    q = (px // 16).astype(np.int32)
    key = q[:, 0] * 256 + q[:, 1] * 16 + q[:, 2]
    mode = np.bincount(key).argmax()
    sel = px[key == mode]
    return sel.mean(axis=0).astype(np.float32)


def otsu_threshold(dist: np.ndarray, floor: float = GROUND_DIST * 0.5) -> float:
    """Otsu on the colour distance from the ground, never under `floor`: a box
    that is all ground must not have its noise called ink."""
    d = np.clip(dist, 0, 441).astype(np.uint8)
    t, _ = cv2.threshold(d, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return float(max(t, floor))


def soft_ink(rgb: np.ndarray, alpha: np.ndarray, ground: np.ndarray,
             thr: float | None = None) -> tuple[np.ndarray, float]:
    """-> (soft ink field in [0, 1], threshold): colour distance from the
    ground over twice the threshold, so 0.5 is the Otsu split. Transparent
    pixels are ground."""
    dist = np.linalg.norm(rgb - ground[None, None, :], axis=2)
    dist = np.where(alpha >= 128, dist, 0.0)
    if thr is None:
        op = dist[alpha >= 128]
        thr = otsu_threshold(op) if op.size else GROUND_DIST
    return np.clip(dist / (2.0 * thr), 0, 1).astype(np.float32), thr


# --- the thread, as ink ------------------------------------------------------

def _colours(design: dict) -> list[tuple[int, int, int]]:
    cols = design.get("colors") or [{"r": 0, "g": 0, "b": 0}]
    return [(int(c["r"]), int(c["g"]), int(c["b"])) for c in cols]


def ink_blocks(design: dict, ground: np.ndarray, dist: float = GROUND_DIST) -> list[bool]:
    """Per colour block: is its thread distinguishable from the ground?"""
    return [float(np.linalg.norm(np.array(c, np.float32) - ground)) > dist
            for c in _colours(design)]


def thread_ink(design: dict, ground: np.ndarray, px_per_mm: float = P,
               thread_mm: float | None = None) -> tuple[np.ndarray, tuple[float, float]]:
    """-> (ink field in [0, 1], (x0_mm, y1_mm)): `render_design` of the
    non-ground blocks only, drawn black on white, flat (`lit=False`), at
    `thread_mm`. Ground-coloured blocks become jumps so the frame -- the stitch
    bounds -- is the design's own and does not move with the filter."""
    from . import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    keep = ink_blocks(design, ground)
    ci = 0
    recs = []
    for s in design.get("stitches") or []:
        k = s.get("type")
        if k == "color":
            ci += 1
            recs.append(s)
            continue
        if k == "stitch" and not (keep[min(ci, len(keep) - 1)]):
            recs.append({**s, "type": "jump"})
        else:
            recs.append(s)
    black = {"stitches": recs, "colors": [{"r": 0, "g": 0, "b": 0}] * max(1, len(keep))}
    img = stitchviz.render_design(black, px_per_mm=px_per_mm, fabric_bgr=(255, 255, 255),
                                  pad_mm=PAD_MM, lit=False, thread_mm=thread_mm)
    ink = 1.0 - img.mean(axis=2) / 255.0
    b = stitchviz._bounds(design.get("stitches") or [])
    x0 = b[0] / stitchviz.UNITS_PER_MM
    y1 = b[3] / stitchviz.UNITS_PER_MM
    return ink.astype(np.float32), (x0, y1)


# --- pull ---------------------------------------------------------------------

def pull_erode(T: np.ndarray, pull_mm: float, thread_mm: float, px_per_mm: float = P,
               ink: np.ndarray | None = None, lines: str | None = None) -> np.ndarray:
    """The thread mask after the cloth takes `pull_mm` back on every side.
    `pull_mm` <= 0 returns `T` itself, so the default is byte-for-byte today's
    read.

    Pull narrows what the engine pushed out: a satin column or a fill, wider
    than a thread. It does not erase a thin stroke, which has no push to take
    back (the tagline's 0.4 mm beans would vanish under a plain erosion and the
    read would bill the letter for the cloth). So whatever the erosion removes
    outright keeps its own medial axis, thickened to `thread_mm`, WHERE IT LIES
    ON THE ARTWORK'S INK (`ink`, a mask of the source ink grown half a thread;
    None keeps every such line). A thread-wide line off the ink, such as a run
    across the mouth of a bay or down the open side of an E, is not a stroke of
    the letter and the pull takes it with the rest. `lines` ("ink", "all",
    "none"; default `PULL_LINES`) is that rule, or its two edges, for a
    sensitivity run."""
    lines = PULL_LINES if lines is None else lines
    r = int(round(pull_mm * px_per_mm))
    if r < 1 or not T.any():
        return T
    # An enclosed gap too small to be a counter (the read does not count a hole
    # under MIN_HOLE_DIAM_THREADS of a thread across) is the render's own texture
    # between rows of a satin column. Erosion would grow it into one, so it is
    # closed first: the pull takes thread back from an EDGE, it does not part a
    # column down the middle.
    lab, n = ndi.label(ndi.binary_fill_holes(T) & ~T)
    if n:
        dt = ndi.distance_transform_edt(~T)
        diam = 2.0 * np.asarray(ndi.maximum(dt, lab, range(1, n + 1))) / px_per_mm
        small = np.zeros(n + 1, bool)
        small[1:] = diam < MIN_HOLE_DIAM_THREADS * thread_mm
        if small.any():
            T = T | small[lab]
    eroded = cv2.erode(T.astype(np.uint8), cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1,) * 2)) > 0
    rt = max(1, int(round(thread_mm / 2.0 * px_per_mm)))
    line = cv2.dilate(skeletonize(T).astype(np.uint8),
                      cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rt + 1,) * 2)) > 0
    if lines == "none":
        return eroded
    keep = line & T
    if lines == "ink" and ink is not None:
        keep &= ink
    return eroded | keep


# --- registration -------------------------------------------------------------

@dataclass
class Registration:
    """source px -> design-image px (the render grid at P px/mm):
    u = ax * sx + tx, v = ay * sy + ty. The two scales may differ: a
    professional's file is often drawn from a slightly different crop of the
    logo (Fremont's is 2.3% narrower in aspect than the artwork here)."""
    ax: float
    ay: float
    tx: float
    ty: float
    score: float

    @property
    def a(self) -> float:
        return (self.ax + self.ay) / 2.0

    @property
    def mm_per_src_px(self) -> float:
        return self.a / P

    def matrix(self) -> np.ndarray:
        return np.array([[self.ax, 0, self.tx], [0, self.ay, self.ty]], np.float64)

    def apply_box(self, x0, y0, x1, y1) -> tuple[float, float, float, float]:
        return (self.ax * x0 + self.tx, self.ay * y0 + self.ty,
                self.ax * x1 + self.tx, self.ay * y1 + self.ty)


def _bbox(mask: np.ndarray, level: float = 0.5):
    ys, xs = np.where(mask >= level)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


# --- one glyph --------------------------------------------------------------

def _holes(mask: np.ndarray, min_px: int = 0):
    """Enclosed background components of a binary mask: -> (labels, n)."""
    filled = ndi.binary_fill_holes(mask)
    lab, n = ndi.label(filled & ~mask)
    if min_px and n:
        sizes = ndi.sum(np.ones_like(lab), lab, range(1, n + 1))
        keep = np.zeros(n + 1, bool)
        keep[1:] = sizes >= min_px
        lab = np.where(keep[lab], lab, 0)
        lab, n = ndi.label(lab > 0)
    return lab, n


def _skeleton_width(mask: np.ndarray, px_per_mm: float) -> float:
    if not mask.any():
        return 0.0
    sk = skeletonize(mask)
    if not sk.any():
        return 0.0
    dt = ndi.distance_transform_edt(mask)
    return float(np.median(2.0 * dt[sk]) / px_per_mm)


def glyph_scores(S: np.ndarray, T: np.ndarray, thread_mm: float,
                 px_per_mm: float = P) -> dict:
    """The five readings of one sewn glyph. `S` the source glyph and `T` the
    thread inside its zone, both bool, same grid, already aligned."""
    a_s, a_t = float(S.sum()), float(T.sum())
    inter, union = float((S & T).sum()), float((S | T).sum())
    iou = inter / union if union else 0.0

    sk_s = skeletonize(S) if S.any() else S
    r_thr = max(1, int(round(thread_mm / 2.0 * px_per_mm)))
    ideal = S | (cv2.dilate(sk_s.astype(np.uint8),
                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r_thr + 1,) * 2)) > 0)
    ceil = a_s / float(ideal.sum()) if ideal.any() else 1.0
    shape = min(1.0, iou / ceil) if ceil > 0 else 0.0

    # strokes: skeleton points with thread on them
    t_dist = ndi.distance_transform_edt(~T) if T.any() else np.full(T.shape, 1e9)
    sk_n = int(sk_s.sum())
    recall = float((t_dist[sk_s] <= SKEL_TOL_MM * px_per_mm).mean()) if sk_n else 0.0

    # clean: thread more than the push compensation off the source ink
    s_dist = ndi.distance_transform_edt(~S)
    off = float((s_dist[T] > COMP_TOL_MM * px_per_mm).sum()) if a_t else 0.0
    clean = 1.0 - off / a_t if a_t else 0.0

    # counters (Euler). A hole counts when a circle of half a thread fits in it,
    # on either side: a pinhole in a satin column is not a counter and is not
    # seen by a reader.
    min_diam = MIN_HOLE_DIAM_THREADS * thread_mm
    min_px = int(0.02 * px_per_mm ** 2)
    lab_s, n_s_all = _holes(S, min_px)
    dt_s = ndi.distance_transform_edt(~S)
    feas = []
    for i in range(1, n_s_all + 1):
        hole = lab_s == i
        if 2.0 * float(dt_s[hole].max()) / px_per_mm >= min_diam:
            feas.append(hole)
    lab_t, n_t_all = _holes(T, min_px)
    dt_t = ndi.distance_transform_edt(~T) if T.any() else np.zeros(T.shape)
    t_holes = []
    for j in range(1, n_t_all + 1):
        hole = lab_t == j
        if 2.0 * float(dt_t[hole].max()) / px_per_mm >= min_diam:
            t_holes.append(hole)
    n_t = len(t_holes)
    # one-to-one: each sewn hole answers at most one source counter, so an "8"
    # whose waist was never sewn (two counters run into one) matches only one
    pairs = []
    for i, hole in enumerate(feas):
        for j, th in enumerate(t_holes):
            ov = float((hole & th).sum())
            if ov >= 0.25 * min(hole.sum(), th.sum()):
                pairs.append((ov, i, j))
    pairs.sort(reverse=True)
    used_s, used_t = set(), set()
    for _ov, i, j in pairs:
        if i not in used_s and j not in used_t:
            used_s.add(i)
            used_t.add(j)
    src_any = ndi.binary_fill_holes(S) & ~S
    spurious = [j for j in range(n_t) if j not in used_t and not (t_holes[j] & src_any).any()]
    denom = len(feas) + len(spurious)
    counters = 1.0 if denom == 0 else len(used_s) / denom

    comps_t = ndi.label(T)[1] if T.any() else 0
    comps_s = ndi.label(S)[1]
    euler_s = comps_s - len(feas)
    euler_t = comps_t - n_t

    # space: the core of the glyph's own negative space (inside its convex
    # hull, a quarter-millimetre or more from any ink: the mouth of an E, the
    # waist of an S, a counter) must stay bare. Thread poured into it is what
    # makes "THE" a blob, and it is what Euler cannot see in an open bay.
    pts = cv2.findNonZero(S.astype(np.uint8))
    space, space_px = 1.0, 0
    if pts is not None and len(pts) >= 3:
        hull = np.zeros(S.shape, np.uint8)
        cv2.fillConvexPoly(hull, cv2.convexHull(pts), 1)
        neg = (hull > 0) & ~S
        ridge = skeletonize(neg) & (s_dist >= SPACE_MIN_HALF_MM * px_per_mm)
        space_px = int(ridge.sum())
        if space_px:
            # the ridge of each bay and counter survives when thread leaves a
            # clear circle of SPACE_KEEP_HALF_MM around it
            kept = ridge & (t_dist >= SPACE_KEEP_HALF_MM * px_per_mm)
            space = float(kept.sum()) / space_px

    w_s, w_t = _skeleton_width(S, px_per_mm), _skeleton_width(T, px_per_mm)
    width_ratio = w_t / max(w_s, thread_mm) if w_t else 0.0

    # The headline is the WEAKEST of the three failure-mode readings, not their
    # mean: a geometric mean of four lets a missing arm (recall 0.66) read as
    # 0.89, and "can you read it" is lost by one failure. `legibility_space`
    # adds the negative-space read, which also bills thick-but-correct
    # lettering, so it is reported beside the headline and never folded in.
    legibility = min(recall, clean, counters)
    legibility_space = min(legibility, space)
    return {"legibility": round(legibility, 3), "legibility_space": round(legibility_space, 3),
            "shape": round(shape, 3),
            "iou": round(iou, 3), "iou_ceiling": round(ceil, 3),
            "strokes": round(recall, 3), "clean": round(clean, 3),
            "counters": round(counters, 3), "space": round(space, 3),
            "src_counters": n_s_all, "src_counters_openable": len(feas),
            "sewn_counters": n_t, "sewn_counters_spurious": len(spurious),
            "euler_src": int(euler_s), "euler_sewn": int(euler_t),
            "euler_match": bool(euler_s == euler_t),
            "sewn_pieces": int(comps_t),
            "stroke_w_src_mm": round(w_s, 3), "stroke_w_sewn_mm": round(w_t, 3),
            "width_ratio": round(width_ratio, 2),
            "area_src_mm2": round(a_s / px_per_mm ** 2, 3),
            "area_sewn_mm2": round(a_t / px_per_mm ** 2, 3)}


def counters_shut(row: dict) -> int:
    """How many of a glyph row's openable source counters the thread did not
    keep open: `counters` is kept / (openable + spurious), so kept is read
    back from it exactly (each term is a small integer)."""
    openable = int(row["src_counters_openable"])
    denom = openable + int(row["sewn_counters_spurious"])
    kept = int(round(row["counters"] * denom)) if denom else 0
    return max(0, openable - kept)


# --- a word -------------------------------------------------------------------

def _label_glyphs(S_box: np.ndarray, box_px, px_per_mm: float, keep_px=None,
                  drop_edge: bool | None = None):
    """Connected components of the source ink inside the word box, at least
    MIN_GLYPH_MM2. Without `keep_px`, any that touch the box edge are dropped
    (a neighbour cut by the box is not this word's glyph). With it -- the
    labelled letters' boxes, (x0, y0, x1, y1) in this grid -- a component is
    kept when its centroid is inside one of them, which is how a word box
    that also holds an anchor and waves (Bridge) reads only its letters.
    `drop_edge` asks for both tests at once (default: the edge test only
    without `keep_px`, today's two modes)."""
    if drop_edge is None:
        drop_edge = not keep_px
    x0, y0, x1, y1 = box_px
    lab, n = ndi.label(S_box)
    out = []
    for i in range(1, n + 1):
        m = lab == i
        area = m.sum() / px_per_mm ** 2
        if area < MIN_GLYPH_MM2:
            continue
        ys, xs = np.where(m)
        if keep_px:
            cx, cy = xs.mean(), ys.mean()
            if not any(k[0] <= cx <= k[2] and k[1] <= cy <= k[3] for k in keep_px):
                continue
        if drop_edge and (xs.min() <= x0 + 1 or ys.min() <= y0 + 1 or xs.max() >= x1 - 2 or ys.max() >= y1 - 2):
            continue
        out.append((i, m, (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)))
    out.sort(key=lambda t: t[2][0])
    return lab, out


def _best_shift(S: np.ndarray, T: np.ndarray, bb, R: int, px_per_mm: float):
    """Integer translation (dx, dy) of the thread, within +-R px, that
    maximises the correlation of the blurred glyph and the blurred thread over
    the glyph's window. -> (dx, dy)."""
    x0, y0, x1, y1 = bb
    m = int(0.4 * px_per_mm)
    H, W = S.shape
    ys0, ys1, xs0, xs1 = max(0, y0 - m), min(H, y1 + m), max(0, x0 - m), min(W, x1 + m)
    sig = 0.12 * px_per_mm
    tmpl = cv2.GaussianBlur(S[ys0:ys1, xs0:xs1].astype(np.float32), (0, 0), sig)
    pad = R
    t_pad = np.pad(T.astype(np.float32), pad, mode="constant")
    img = cv2.GaussianBlur(t_pad[ys0:ys1 + 2 * pad, xs0:xs1 + 2 * pad], (0, 0), sig)
    if img.shape[0] < tmpl.shape[0] or img.shape[1] < tmpl.shape[1] or not T[ys0:ys1, xs0:xs1].any():
        return 0, 0
    # mean-subtracted correlation, so thick thread is not favoured over right thread
    res = cv2.matchTemplate(img, tmpl, cv2.TM_CCOEFF_NORMED)
    j, i = np.unravel_index(int(np.nanargmax(res)), res.shape)
    return int(i) - pad, int(j) - pad


def read_glyphs(S_all: np.ndarray, T_all: np.ndarray, gbox, keep_px, thread_mm: float,
                px_per_mm: float = P, on_glyph=None, drop_edge: bool | None = None):
    """Score every source glyph of one word box. `S_all` the source ink and
    `T_all` the thread, both bool on one grid; `gbox` the word box and
    `keep_px` the letters' boxes in that grid (see `_label_glyphs`). Each
    glyph takes its own small translation (`SHIFT_MM`), and its zone is the
    pixels nearer it than any other glyph, within the push compensation and
    half a millimetre, plus its counters however wide. `on_glyph(row, S, T)`,
    when given, is called with each row and its window's masks before the row
    is kept (the tool's OCR reader).
    -> (rows, [{"S", "T", "win", "score"}], claimed thread mask)."""
    H, W = T_all.shape
    _lab, glyphs = _label_glyphs(S_all, gbox, px_per_mm, keep_px, drop_edge)
    rows: list[dict] = []
    dbg: list[dict] = []
    claimed = np.zeros((H, W), bool)
    if not glyphs:
        return rows, dbg, claimed
    # zones: each pixel belongs to its nearest source glyph (within a margin)
    marker = np.zeros((H, W), np.int32)
    for k, (_i, m, _bb) in enumerate(glyphs, 1):
        marker[m] = k
    dist, (iy, ix) = ndi.distance_transform_edt(marker == 0, return_indices=True)
    owner = marker[iy, ix]
    R = int(SHIFT_MM * px_per_mm)
    zone_r = (COMP_TOL_MM + 0.5) * px_per_mm  # a glyph's thread lives within comp + half a mm of it
    for k, (_i, m, bb) in enumerate(glyphs, 1):
        dxs, dys = _best_shift(m, T_all, bb, R, px_per_mm)
        T_sh = np.roll(np.roll(T_all, -dys, axis=0), -dxs, axis=1)
        # the zone is the glyph's own surroundings AND its counters, however
        # wide: thread poured into the middle of an "O" must be read, not cut.
        # A component's holes lie inside its own box, so they are filled there
        # (one pixel of ground around it): the same mask, without filling the
        # whole word's raster once per glyph.
        fy0, fy1 = max(0, bb[1] - 1), min(H, bb[3] + 1)
        fx0, fx1 = max(0, bb[0] - 1), min(W, bb[2] + 1)
        filled = np.zeros((H, W), bool)
        filled[fy0:fy1, fx0:fx1] = ndi.binary_fill_holes(m[fy0:fy1, fx0:fx1])
        zone = (owner == k) & ((dist <= zone_r) | filled)
        Tg = T_sh & zone
        claimed |= np.roll(np.roll(Tg, dys, axis=0), dxs, axis=1)
        pad = int(1.0 * px_per_mm)
        x0, y0, x1, y1 = bb
        win = (slice(max(0, y0 - pad), min(H, y1 + pad)), slice(max(0, x0 - pad), min(W, x1 + pad)))
        sc = glyph_scores(m[win], Tg[win], thread_mm, px_per_mm)
        sc["offset_mm"] = round(math.hypot(dxs, dys) / px_per_mm, 2)
        sc["bbox_mm"] = [round(v / px_per_mm, 2) for v in bb]
        if on_glyph is not None:
            on_glyph(sc, m[win], Tg[win])
        rows.append(sc)
        dbg.append({"S": m[win], "T": Tg[win], "win": win, "score": sc})
    return rows, dbg, claimed


# --- the same read on a finished job (preflight) ---------------------------------

# Which source components are a word's glyphs. The word box is the tagged
# members' union, grown along the line of text by this many letter heights
# (the median member's) on each side and across it by `WORD_BOX_MARGIN_MM`;
# a component inside it is a glyph when its centroid lies in one of the
# members' own boxes (grown by the margin) or in the LINE BAND -- the
# members' median top to median bottom, as long as the grown box. Two
# reasons. The tagger does not take every letter: on Hotel Fremont at 81 mm
# the text cluster for "1895" holds the 8 and the 5 only (the 1 and the 9
# trace as untagged runs), so the members' boxes alone would never see the
# shut 9; the band reads a missed letter on the word's line. And the tagger
# takes some things that are not letters: the tagline's cluster holds two of
# the ring's stars, and a union box would then read every star of the ring
# beside them; the band does not reach them, and the two tagged ones are
# read as the tagger's own call. A component touching the word box's edge is
# dropped as well (a frame or a rule that crosses the box is not a letter).
# Boxes are axis-aligned: an arched word is read through its members' boxes.
WORD_BOX_GROW_HEIGHTS = 1.0
WORD_BOX_MARGIN_MM = 0.30
# Every word is read on a crop of the render this much past its box: wider
# than the per-glyph shift, the zone and the window together, so a crop reads
# exactly what the whole render would.
CROP_MARGIN_MM = 3.0


def word_boxes(regions, cfg=None) -> list[tuple[str, list, tuple, list]]:
    """-> [(word key, member shape ids, word box, keep boxes)], boxes as
    (x0, y0, x1, y1) in plan mm, y down; the keep boxes are each member's
    grown box and then the line band (see `WORD_BOX_GROW_HEIGHTS`). One per
    word of text-tagged shapes: `words.is_text` / `words.word_key`,
    so `cfg.lettering_words` reads the one tagger's words (`word_id`) and the
    default the text cluster (`text_candidate`, `text_cluster_id`). Sorted by
    key, so the read is deterministic."""
    from . import words as _words
    by: dict[str, list] = {}
    for r in regions:
        if r.polygon is None or r.polygon.is_empty or not _words.is_text(r, cfg):
            continue
        key = _words.word_key(r, cfg)
        if key:
            by.setdefault(str(key), []).append(r)
    out = []
    for key in sorted(by):
        bs = [r.polygon.bounds for r in by[key]]
        x0, y0 = min(b[0] for b in bs), min(b[1] for b in bs)
        x1, y1 = max(b[2] for b in bs), max(b[3] for b in bs)
        # the word's letter height: the median member's, so two ornaments the
        # tagger put under a tagline do not stretch the reach to the union's
        h = float(np.median([b[3] - b[1] for b in bs]))
        g, e = WORD_BOX_GROW_HEIGHTS * h, WORD_BOX_MARGIN_MM
        keeps = [(b[0] - e, b[1] - e, b[2] + e, b[3] + e) for b in bs]
        keeps.append((x0 - g, float(np.median([b[1] for b in bs])) - e,
                      x1 + g, float(np.median([b[3] for b in bs])) + e))
        out.append((key, sorted(r.shape_id for r in by[key]),
                    (x0 - g, y0 - e, x1 + g, y1 + e), keeps))
    return out


def source_from_prep(p) -> tuple[np.ndarray, np.ndarray]:
    """-> (rgb float32, alpha uint8) of the prepped artwork the design was
    traced from, the way the tool reads its source: an alpha cutout's
    background is read on white (the tool composites on white), every pixel
    opaque."""
    rgb = p.rgb.astype(np.float32)
    if getattr(p, "bg_from_alpha", False):
        rgb[p.bg_mask] = 255.0
    return rgb, np.full(rgb.shape[:2], 255, np.uint8)


def read_design_words(p, regions, design: dict, cfg=None, pull_mm: float = 0.0,
                      thread_mm: float | None = None) -> list[dict]:
    """Every glyph of every text-tagged word of a finished design, read the
    way `tools/glyph_legibility.py` reads a word, with two differences that
    come from having the job in hand: the boxes are the tagged words'
    (`word_boxes`), and the source is the prepped raster `p` the design was
    traced from, so its pixel maps to the render through the plan's own frame
    (stage 4's mm = (px - centre of the art box) / px_per_mm) and no
    registration search runs. Each glyph still takes its own small shift.
    `pull_mm` erodes the thread as the tool's `--pull-mm` does.
    -> [{"word", "members", "box_mm", "rows"}], one per word, in key order;
    `rows` the tool's per-glyph rows (empty when the box holds no glyph)."""
    from . import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    boxes = word_boxes(regions, cfg)
    if not boxes or not (design.get("stitches") or []):
        return []
    rgb, alpha = source_from_prep(p)
    hs, ws = rgb.shape[:2]
    ax0, ay0, ax1, ay1 = p.art_bbox
    cx, cy, ppm = (ax0 + ax1) / 2.0, (ay0 + ay1) / 2.0, float(p.px_per_mm)
    cache: dict = {}
    soft_cache: dict = {}
    out = []
    for key, members, (x0, y0, x1, y1), keeps in boxes:
        box_px = (max(0, int(x0 * ppm + cx)), max(0, int(y0 * ppm + cy)),
                  min(ws, int(round(x1 * ppm + cx))), min(hs, int(round(y1 * ppm + cy))))
        row = {"word": key, "members": members,
               "box_mm": [round(v, 2) for v in (x0, y0, x1, y1)], "rows": []}
        out.append(row)
        if box_px[2] - box_px[0] < 2 or box_px[3] - box_px[1] < 2:
            continue
        G = ground_colour(rgb, alpha, box_px)
        gk = tuple(np.round(G / 8))
        if gk not in cache:
            cache[gk] = thread_ink(design, G, P, thread_mm)
            soft_cache[gk] = soft_ink(rgb, alpha, G)[0]
        thread_f, (dx0, dy1) = cache[gk]
        soft = soft_cache[gk]
        H, W = thread_f.shape
        k = P / ppm
        reg = Registration(ax=k, ay=k, tx=P * (-cx / ppm - dx0 + PAD_MM),
                           ty=P * (dy1 - cy / ppm + PAD_MM), score=1.0)
        # the word's crop of the render grid
        bx0, by0, bx1, by1 = reg.apply_box(*box_px)
        m = CROP_MARGIN_MM * P
        u0, v0 = max(0, int(bx0 - m)), max(0, int(by0 - m))
        u1, v1 = min(W, int(math.ceil(bx1 + m))), min(H, int(math.ceil(by1 + m)))
        if u1 - u0 < 2 or v1 - v0 < 2:
            continue
        M = reg.matrix().copy()
        M[0, 2] -= u0
        M[1, 2] -= v0
        soft_w = cv2.warpAffine(soft, M, (u1 - u0, v1 - v0), flags=cv2.INTER_CUBIC)
        gbox = (int(bx0) - u0, int(by0) - v0, int(bx1) - u0, int(by1) - v0)
        box_mask = np.zeros(soft_w.shape, bool)
        box_mask[max(0, gbox[1]):gbox[3], max(0, gbox[0]):gbox[2]] = True
        S_all = (soft_w >= 0.5) & box_mask
        T_all = thread_f[v0:v1, u0:u1] >= 0.5
        if pull_mm > 0:
            rt = max(1, int(round(thread_mm / 2.0 * P)))
            near_ink = cv2.dilate((soft_w >= 0.5).astype(np.uint8),
                                  cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rt + 1,) * 2)) > 0
            T_all = pull_erode(T_all, pull_mm, thread_mm, P, near_ink)
        keep_px = [tuple(v - o for v, o in zip(reg.apply_box(kx0 * ppm + cx, ky0 * ppm + cy,
                                                             kx1 * ppm + cx, ky1 * ppm + cy),
                                                (u0, v0, u0, v0)))
                   for kx0, ky0, kx1, ky1 in keeps]
        rows, _dbg, _claimed = read_glyphs(S_all, T_all, gbox, keep_px, thread_mm, P,
                                           drop_edge=True)
        for g in rows:      # the glyph's box back in the plan's mm (the row's own is the crop's)
            b = g["bbox_mm"]
            g["bbox_plan_mm"] = [round(b[0] + u0 / P + dx0 - PAD_MM, 2), round(b[1] + v0 / P - dy1 - PAD_MM, 2),
                                 round(b[2] + u0 / P + dx0 - PAD_MM, 2), round(b[3] + v0 / P - dy1 - PAD_MM, 2)]
        row["rows"] = rows
    return out


def design_metrics(read: list[dict], pull_mm: float = 0.0) -> dict:
    """`read_design_words`' output as preflight's metrics. None throughout
    when there is no text-tagged word or no glyph was found (a None is never
    a legible design). `glyph_legibility_words` is one compact row per word."""
    glyphs = [g for w in read for g in w["rows"]]
    if not glyphs:
        return {"glyph_legibility_min": None, "glyph_legibility_mean": None,
                "counters_shut": None, "glyph_legibility_glyphs": len(glyphs) if read else None,
                "glyph_legibility_pull_mm": round(float(pull_mm), 3) if read else None,
                "glyph_legibility_words": [] if read else None}
    words_out = []
    for w in read:
        rs = w["rows"]
        words_out.append({
            "word": w["word"], "members": len(w["members"]), "box_mm": w["box_mm"],
            "glyphs": len(rs),
            "legibility": round(float(np.mean([g["legibility"] for g in rs])), 3) if rs else None,
            "worst_glyph": round(float(min(g["legibility"] for g in rs)), 3) if rs else None,
            "counters_shut": sum(counters_shut(g) for g in rs),
            "counters_spurious": sum(int(g["sewn_counters_spurious"]) for g in rs),
            "glyph_counters": [g["counters"] for g in rs]})
    return {"glyph_legibility_min": round(float(min(g["legibility"] for g in glyphs)), 3),
            "glyph_legibility_mean": round(float(np.mean([g["legibility"] for g in glyphs])), 3),
            "counters_shut": int(sum(counters_shut(g) for g in glyphs)),
            "glyph_legibility_glyphs": len(glyphs),
            "glyph_legibility_pull_mm": round(float(pull_mm), 3),
            "glyph_legibility_words": words_out}
