#!/usr/bin/env python
"""Can you READ the sewn lettering? A per-glyph shape read of the thread.

Why it exists. PR #898 (Kent's Hotel Fremont at 81 mm, Hat) showed that
`ARTWORK_UNCOVERED` never fires when "1895" sews as "098": a bean outline
laid over a 0.2 mm stroke covers the ink, so coverage cannot see wrong letter
SHAPES. `tools/legibility.py` (OCR of a whole text cluster) cannot either:
tesseract's word model fills in a missing arm, a tagline that is not a text
cluster is invisible to it, and a ragged "EST" still reads "EST". Before any
small-lettering flip (`small_print_floor`, `lettering_columns_small_stem`, the
Fremont 1895 ink fix, column end shapes) the repo needs a number that
tracks "can you read it". This is that number. It changes no engine code; it
reads a finished design.

What it compares, per GLYPH. The source glyph is a connected component of the
artwork's ink inside a labelled word box. The sewn glyph is the same place
read out of the THREAD: `stitchviz.render_design` (the repo's thread renderer,
at `thread_mm` filament width) of only the blocks that are not the ground
colour, thresholded to ink. Both go on one 20 px/mm grid. The source is
registered to the design by a whole-design correlation (the design may be a
DST from a pro, with no frame), then each glyph gets a small translation of
its own, because the question is shape and not where the pull compensation
put it. The offset is reported, never scored.

Five readings per glyph, each in [0, 1] unless said:

  shape      thread-vs-source IoU, divided by its CEILING. A 0.22 mm stroke
             sewn with 0.40 mm thread cannot score above 0.55 IoU however
             well it is sewn (memory `letterform-fidelity-2026-08-26`: IoU
             "saturates on small letters" -- an E scoring 0.534 against a
             0.580 ceiling while sewing as an L). The ceiling is the IoU of
             the source against the best thread could do: the source plus its
             medial axis thickened to thread width.
  strokes    medial-axis recall: how much of the source's skeleton has thread
             on it. A missing arm, a lost "1" and an E sewn as an L all drop
             here, and they do NOT drop IoU much on a small letter.
  clean      1 - the share of thread more than `TOL_MM` off the source ink:
             accents, ticks, blobs poured into a counter.
  counters   Euler read. Source counters wide enough to be openable (an
             inscribed circle of at least half a thread) must show as a hole
             in the thread; a hole in the thread where the source has none
             counts against it. 8 and 9 sewn as blobs, and an A or R with its
             counter shut, drop here. IoU, recall and clean cannot see this:
             a counter 0.3 mm wide is inside thread tolerance of the ink
             around it.
  width      sewn stroke width over max(source stroke width, thread): a
             legible stroke is as wide as the thread allows and not a blob.
             Reported as a ratio, not scored.

`legibility` is the geometric mean of the four scores, so one failed reading
drags the glyph: a glyph with shut counters cannot be rescued by a good
outline. A word's number is the mean over its glyphs; the worst glyph is
reported beside it, because a word with one lost digit reads wrong.

OCR is a SECOND reader, not part of the number: tesseract on each glyph
alone (psm 10, no language model, so no filling in), the thread read against
the source read. `ocr_recovered` is the share of glyphs whose source reads
confidently and whose thread reads as the same character, with a Wilson 95%
interval. Without the `tesseract` binary every OCR field says
"OCR UNAVAILABLE" and the geometric number stands alone; it never silently
passes.

What this is NOT. Not a sew-out (ROADMAP gate 1): it reads where thread
lands in a render, with no pull, no push, no nap. Not a threshold: no cut-off
is claimed, only an ordering, and it was developed on the same handful of
cases it is validated on (n words is small; the confidence interval says so).
Ground-coloured thread sewn OVER ink is not seen as hiding it. The ground
colour is the mode colour of the word box's artwork.

    .venv/Scripts/python -m tools.glyph_legibility --case fremont81 --design D.json
    .venv/Scripts/python -m tools.glyph_legibility --list
    .venv/Scripts/python -m tools.glyph_legibility --validate OUT_DIR --renders DOCS_DIR
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

P = 20.0                    # working grid, px per mm
PAD_MM = 2.0                # render_design's own pad
TOL_MM = 0.20               # thread this far off the source ink is "off"
SKEL_TOL_MM = 0.15          # a skeleton point is "sewn" with thread this close
SHIFT_MM = 0.60             # per-glyph translation the read may take
MIN_GLYPH_MM2 = 0.12        # smaller source components are specks, not glyphs
GROUND_DIST = 60.0          # a thread this far (RGB) from the ground is ink
MIN_HOLE_PX_DIAM_MM = 0.5   # openable counter: inscribed diameter >= this x thread
OCR_CONF_MIN = 60.0         # source read below this is no truth to compare to

# Kent's seven circles and the Fremont words, as boxes in FRACTIONS of the
# artwork (x0, y0, x1, y1), the same boxes `tools/fremont_triage.ROIS` uses
# for the red circles, plus the two big words Kent did not circle.
FREMONT_BOXES = {
    "est": (0.380, 0.190, 0.460, 0.256),
    "1895": (0.537, 0.190, 0.620, 0.256),
    "the": (0.440, 0.315, 0.562, 0.397),
    "tagline": (0.344, 0.684, 0.680, 0.782),
}


def tesseract_available() -> bool:
    return shutil.which("tesseract") is not None


# --- source ink ------------------------------------------------------------

def load_source(path) -> tuple[np.ndarray, np.ndarray]:
    """-> (rgb float32 HxWx3, alpha uint8 HxW). An image with no alpha is
    opaque."""
    raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if raw is None:
        raise SystemExit(f"unreadable artwork: {path}")
    if raw.ndim == 2:
        raw = cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
    alpha = raw[..., 3] if raw.shape[2] == 4 else np.full(raw.shape[:2], 255, np.uint8)
    rgb = cv2.cvtColor(raw[..., :3], cv2.COLOR_BGR2RGB).astype(np.float32)
    return rgb, alpha


def ground_colour(rgb: np.ndarray, alpha: np.ndarray, box_px=None) -> np.ndarray:
    """The mode colour (16-level quantised) of the opaque pixels, optionally
    inside `box_px` (x0, y0, x1, y1). The ground is what most of a word box is."""
    if box_px is not None:
        x0, y0, x1, y1 = box_px
        rgb, alpha = rgb[y0:y1, x0:x1], alpha[y0:y1, x0:x1]
    px = rgb[alpha >= 128].reshape(-1, 3)
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
    from digitizer_core import stitchviz
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


def design_from_pes(path, flip_y: bool = True) -> dict:
    """A stitch file -> the EMB-Bot `Design` dict (0.1 mm, y up), through
    pystitch. `flip_y`: pystitch reports y down, a design is y up."""
    import pystitch
    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable stitch file: {path}")
    colors = []
    for t in pat.threadlist:
        colors.append({"r": int(t.get_red()), "g": int(t.get_green()), "b": int(t.get_blue())})
    sign = -1.0 if flip_y else 1.0
    recs = []
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            recs.append({"x": float(x), "y": sign * float(y), "type": "stitch"})
        elif cmd == pystitch.JUMP:
            recs.append({"x": float(x), "y": sign * float(y), "type": "jump"})
        elif cmd == pystitch.TRIM:
            recs.append({"x": float(x), "y": sign * float(y), "type": "trim"})
        elif cmd == pystitch.COLOR_CHANGE:
            recs.append({"x": float(x), "y": sign * float(y), "type": "color"})
    if not colors:
        colors = [{"r": 0, "g": 0, "b": 0}]
    return {"stitches": recs, "colors": colors}


# --- registration -------------------------------------------------------------

@dataclass
class Registration:
    """source px -> design-image px (the render grid at P px/mm):
    u = a * sx + tx, v = a * sy + ty, one uniform scale `a` (design px per
    source px)."""
    a: float
    tx: float
    ty: float
    score: float
    mm_per_src_px: float

    def matrix(self) -> np.ndarray:
        return np.array([[self.a, 0, self.tx], [0, self.a, self.ty]], np.float64)


def _bbox(mask: np.ndarray, level: float = 0.5):
    ys, xs = np.where(mask >= level)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def register(src_soft: np.ndarray, thread: np.ndarray, px_per_mm: float = P,
             search_scale: float = 0.03, reg_ppm: float = 4.0,
             search_mm: float = 1.5) -> Registration:
    """Fit one uniform scale and a translation taking the whole source ink onto
    the whole thread ink: bbox centres and widths first, then a scale search
    (+-3%) with a normalised cross-correlation over translation, at 4 px/mm."""
    sb, tb = _bbox(src_soft), _bbox(thread, 0.3)
    if sb is None or tb is None:
        raise SystemExit("nothing to register: no source ink or no thread")
    sw, tw = sb[2] - sb[0], tb[2] - tb[0]
    a0 = tw / sw                              # design px per source px
    k = reg_ppm / px_per_mm
    th = cv2.resize(thread, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
    th = cv2.GaussianBlur(th, (0, 0), 0.25 * reg_ppm)
    H, W = th.shape
    tn = float(np.sqrt((th * th).sum())) or 1.0
    best = None
    scx, scy = (sb[0] + sb[2]) / 2.0, (sb[1] + sb[3]) / 2.0
    tcx, tcy = (tb[0] + tb[2]) / 2.0, (tb[1] + tb[3]) / 2.0
    R = int(search_mm * reg_ppm)
    for f in np.linspace(1 - search_scale, 1 + search_scale, 25):
        a = a0 * f
        ar = a * k
        M = np.array([[ar, 0, tcx * k - scx * ar], [0, ar, tcy * k - scy * ar]], np.float64)
        w = cv2.warpAffine(src_soft, M, (W, H), flags=cv2.INTER_AREA if ar < 1 else cv2.INTER_LINEAR)
        w = cv2.GaussianBlur(w, (0, 0), 0.25 * reg_ppm)
        wn = float(np.sqrt((w * w).sum())) or 1.0
        # correlation over integer shifts within +-R, by FFT
        F = np.fft.rfft2(th, s=(H + 2 * R, W + 2 * R))
        G = np.fft.rfft2(w, s=(H + 2 * R, W + 2 * R))
        cc = np.fft.irfft2(F * np.conj(G), s=(H + 2 * R, W + 2 * R))
        # shift (dy, dx) of w onto th: index modulo
        best_here = None
        for dy in range(-R, R + 1):
            row = cc[dy % cc.shape[0]]
            for dx in range(-R, R + 1):
                v = row[dx % cc.shape[1]]
                if best_here is None or v > best_here[0]:
                    best_here = (v, dx, dy)
        sc = best_here[0] / (tn * wn)
        if best is None or sc > best[0]:
            best = (sc, a, best_here[1], best_here[2], M)
    sc, a, dx, dy, M = best
    tx = (tcx * k - scx * a * k + dx) / k
    ty = (tcy * k - scy * a * k + dy) / k
    return Registration(a=a, tx=tx, ty=ty, score=float(sc), mm_per_src_px=a / px_per_mm)


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

    # clean: thread off the source ink
    s_dist = ndi.distance_transform_edt(~S)
    off = float((s_dist[T] > TOL_MM * px_per_mm).sum()) if a_t else 0.0
    clean = 1.0 - off / a_t if a_t else 0.0

    # counters (Euler)
    lab_s, n_s_all = _holes(S, int(0.02 * px_per_mm ** 2))
    dt_s = ndi.distance_transform_edt(~S)
    feas = []
    for i in range(1, n_s_all + 1):
        hole = lab_s == i
        diam = 2.0 * float(dt_s[hole].max()) / px_per_mm
        if diam >= MIN_HOLE_PX_DIAM_MM * thread_mm:
            feas.append(hole)
    lab_t, n_t = _holes(T, int(0.01 * px_per_mm ** 2))
    t_holes = [lab_t == j for j in range(1, n_t + 1)]
    matched_s, matched_t = 0, set()
    for hole in feas:
        best = None
        for j, th in enumerate(t_holes):
            ov = float((hole & th).sum())
            if ov >= 0.25 * min(hole.sum(), th.sum()) and (best is None or ov > best[0]):
                best = (ov, j)
        if best is not None:
            matched_s += 1
            matched_t.add(best[1])
    spurious = [j for j in range(n_t) if j not in matched_t
                and not any((t_holes[j] & lab_s_h).any() for lab_s_h in
                            [lab_s == i for i in range(1, n_s_all + 1)])]
    denom = len(feas) + len(spurious)
    counters = 1.0 if denom == 0 else matched_s / denom

    comps_t = ndi.label(T)[1] if T.any() else 0
    comps_s = ndi.label(S)[1]
    euler_s = comps_s - n_s_all
    euler_t = comps_t - n_t

    w_s, w_t = _skeleton_width(S, px_per_mm), _skeleton_width(T, px_per_mm)
    width_ratio = w_t / max(w_s, thread_mm) if w_t else 0.0

    parts = [max(shape, 1e-3), max(recall, 1e-3), max(clean, 1e-3), max(counters, 1e-3)]
    legibility = float(np.exp(np.mean(np.log(parts))))
    return {"legibility": round(legibility, 3), "shape": round(shape, 3),
            "iou": round(iou, 3), "iou_ceiling": round(ceil, 3),
            "strokes": round(recall, 3), "clean": round(clean, 3),
            "counters": round(counters, 3),
            "src_counters": n_s_all, "src_counters_openable": len(feas),
            "sewn_counters": n_t, "sewn_counters_spurious": len(spurious),
            "euler_src": int(euler_s), "euler_sewn": int(euler_t),
            "euler_match": bool(euler_s == euler_t),
            "sewn_pieces": int(comps_t),
            "stroke_w_src_mm": round(w_s, 3), "stroke_w_sewn_mm": round(w_t, 3),
            "width_ratio": round(width_ratio, 2),
            "area_src_mm2": round(a_s / px_per_mm ** 2, 3),
            "area_sewn_mm2": round(a_t / px_per_mm ** 2, 3)}


# --- OCR, as a second reader -------------------------------------------------

def _ocr_char(mask: np.ndarray, px_per_mm: float = P) -> tuple[str, float]:
    """One tesseract read of a single glyph mask (psm 10, no language model):
    the most confident reading over the repo's three preprocessing variants."""
    from digitizer_core import legibility as core
    img = np.where(mask, 0, 255).astype(np.uint8)
    img = cv2.copyMakeBorder(img, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    best = ("", -1.0)
    for blur_mm, thin_mm in core.VARIANTS_MM:
        txt, conf = core.ocr(img, 10, blur_mm * px_per_mm, thin_mm * px_per_mm)
        t = core.normalise(txt)[:1]
        if t and conf > best[1]:
            best = (t, conf)
    return best


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """Wilson score interval for k of n; None when n is 0."""
    if n == 0:
        return None
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, c - h), min(1.0, c + h)


# --- a word -------------------------------------------------------------------

@dataclass
class WordResult:
    name: str
    glyphs: list = field(default_factory=list)
    stray_mm2: float = 0.0
    registration: dict = field(default_factory=dict)
    ocr: object = "OCR UNAVAILABLE"
    ground: list = field(default_factory=list)

    def summary(self) -> dict:
        g = self.glyphs
        sc = [x["legibility"] for x in g]
        out = {"word": self.name, "glyphs": len(g),
               "legibility": round(float(np.mean(sc)), 3) if sc else None,
               "worst_glyph": round(float(min(sc)), 3) if sc else None,
               "shape": round(float(np.mean([x["shape"] for x in g])), 3) if g else None,
               "strokes": round(float(np.mean([x["strokes"] for x in g])), 3) if g else None,
               "clean": round(float(np.mean([x["clean"] for x in g])), 3) if g else None,
               "counters": round(float(np.mean([x["counters"] for x in g])), 3) if g else None,
               "euler_match": f"{sum(x['euler_match'] for x in g)}/{len(g)}",
               "stray_mm2": round(self.stray_mm2, 3),
               "max_offset_mm": round(max((x["offset_mm"] for x in g), default=0.0), 2),
               "ocr": self.ocr}
        return out


def _label_glyphs(S_box: np.ndarray, box_px, px_per_mm: float):
    """Connected components of the source ink inside the word box, at least
    MIN_GLYPH_MM2, dropping any that touch the box edge (a neighbour cut by
    the box is not this word's glyph)."""
    x0, y0, x1, y1 = box_px
    lab, n = ndi.label(S_box)
    out = []
    for i in range(1, n + 1):
        m = lab == i
        area = m.sum() / px_per_mm ** 2
        if area < MIN_GLYPH_MM2:
            continue
        ys, xs = np.where(m)
        if xs.min() <= x0 + 1 or ys.min() <= y0 + 1 or xs.max() >= x1 - 2 or ys.max() >= y1 - 2:
            continue
        out.append((i, m, (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)))
    out.sort(key=lambda t: t[2][0])
    return lab, out


def _best_shift(S: np.ndarray, T: np.ndarray, bb, R: int, px_per_mm: float):
    """Integer translation (dx, dy) of the thread, within +-R px, that
    maximises the correlation of the blurred glyph and the blurred thread over
    the glyph's window. -> (dx, dy)."""
    x0, y0, x1, y1 = bb
    m = R + int(0.4 * px_per_mm)
    H, W = S.shape
    ys0, ys1, xs0, xs1 = max(0, y0 - m), min(H, y1 + m), max(0, x0 - m), min(W, x1 + m)
    s = cv2.GaussianBlur(S[ys0:ys1, xs0:xs1].astype(np.float32), (0, 0), 0.12 * px_per_mm)
    best = (-1.0, 0, 0)
    t_pad = np.pad(T.astype(np.float32), R + m, mode="constant")
    for dy in range(-R, R + 1):
        for dx in range(-R, R + 1):
            ty0, tx0 = ys0 + dy + R + m, xs0 + dx + R + m
            t = t_pad[ty0:ty0 + s.shape[0], tx0:tx0 + s.shape[1]]
            t = cv2.GaussianBlur(t, (0, 0), 0.12 * px_per_mm)
            v = float((s * t).sum())
            if v > best[0]:
                best = (v, dx, dy)
    return best[1], best[2]


def read_word(name: str, rgb: np.ndarray, alpha: np.ndarray, box_frac, design: dict,
              thread_mm: float | None = None, use_ocr: bool = True,
              reg: Registration | None = None, thread_cache: dict | None = None,
              src_full_cache: dict | None = None) -> tuple[WordResult, dict]:
    """Score every glyph of one labelled word. -> (WordResult, debug arrays
    for the panel renderer)."""
    from digitizer_core import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    h, w = rgb.shape[:2]
    fx0, fy0, fx1, fy1 = box_frac
    box_px = (int(fx0 * w), int(fy0 * h), int(fx1 * w), int(fy1 * h))
    G = ground_colour(rgb, alpha, box_px)
    key = tuple(np.round(G / 8))
    cache = thread_cache if thread_cache is not None else {}
    if key not in cache:
        cache[key] = thread_ink(design, G, P, thread_mm)
    thread_f, (dx0, dy1) = cache[key]
    soft_box, thr = soft_ink(rgb, alpha, G)
    if reg is None:
        gl_all = ground_colour(rgb, alpha)
        soft_all, _ = soft_ink(rgb, alpha, gl_all)
        reg = register(soft_all, thread_f)
    H, W = thread_f.shape
    soft_w = cv2.warpAffine(soft_box, reg.matrix(), (W, H), flags=cv2.INTER_CUBIC)
    # restrict to the word box
    bx = np.array([[box_px[0], box_px[1]], [box_px[2], box_px[3]]], np.float64)
    bu = bx @ np.array([[reg.a, 0], [0, reg.a]]) + np.array([reg.tx, reg.ty])
    gbox = (int(bu[0, 0]), int(bu[0, 1]), int(bu[1, 0]), int(bu[1, 1]))
    box_mask = np.zeros((H, W), bool)
    box_mask[max(0, gbox[1]):gbox[3], max(0, gbox[0]):gbox[2]] = True
    S_all = (soft_w >= 0.5) & box_mask
    T_all = thread_f >= 0.5
    lab, glyphs = _label_glyphs(S_all, gbox, P)
    res = WordResult(name=name, ground=[int(v) for v in G],
                     registration={"scale_mm_per_src_px": round(reg.mm_per_src_px, 6),
                                   "ncc": round(reg.score, 3)})
    dbg = {"S": S_all, "T": T_all, "box": gbox, "glyphs": []}
    if not glyphs:
        return res, dbg
    # zones: each pixel belongs to its nearest source glyph (within a margin)
    marker = np.zeros((H, W), np.int32)
    for k, (_i, m, _bb) in enumerate(glyphs, 1):
        marker[m] = k
    dist, (iy, ix) = ndi.distance_transform_edt(marker == 0, return_indices=True)
    owner = marker[iy, ix]
    R = int(SHIFT_MM * P)
    zone_r = (TOL_MM * 2.0 + SHIFT_MM) * P
    claimed = np.zeros((H, W), bool)
    ocr_ok = use_ocr and tesseract_available()
    if not use_ocr:
        res.ocr = "OCR OFF (--no-ocr)"
    k_ok = n_read = 0
    ocr_rows = []
    for k, (_i, m, bb) in enumerate(glyphs, 1):
        dxs, dys = _best_shift(m, T_all, bb, R, P)
        T_sh = np.roll(np.roll(T_all, -dys, axis=0), -dxs, axis=1)
        # the zone is the glyph's own surroundings AND its counters, however
        # wide: thread poured into the middle of an "O" must be read, not cut
        zone = (owner == k) & ((dist <= zone_r) | ndi.binary_fill_holes(m))
        Tg = T_sh & zone
        claimed |= np.roll(np.roll(Tg, dys, axis=0), dxs, axis=1)
        pad = int(1.0 * P)
        x0, y0, x1, y1 = bb
        win = (slice(max(0, y0 - pad), min(H, y1 + pad)), slice(max(0, x0 - pad), min(W, x1 + pad)))
        sc = glyph_scores(m[win], Tg[win], thread_mm, P)
        sc["offset_mm"] = round(math.hypot(dxs, dys) / P, 2)
        sc["bbox_mm"] = [round(v / P, 2) for v in bb]
        if ocr_ok:
            st, sconf = _ocr_char(m[win])
            tt, tconf = _ocr_char(Tg[win])
            readable = bool(st) and sconf >= OCR_CONF_MIN
            sc["ocr_src"], sc["ocr_src_conf"] = st, round(max(sconf, 0), 1)
            sc["ocr_sewn"], sc["ocr_sewn_conf"] = tt, round(max(tconf, 0), 1)
            sc["ocr_readable_src"] = readable
            sc["ocr_recovered"] = bool(readable and tt == st)
            if readable:
                n_read += 1
                k_ok += int(tt == st)
        res.glyphs.append(sc)
        dbg["glyphs"].append({"S": m[win], "T": Tg[win], "win": win, "score": sc})
    # thread in the word box that no glyph zone claims: strays
    unclaimed = T_all & box_mask & ~claimed
    unclaimed &= ndi.distance_transform_edt(~S_all) > zone_r
    res.stray_mm2 = float(unclaimed.sum()) / P ** 2
    if ocr_ok:
        ci = wilson(k_ok, n_read)
        res.ocr = {"read_on_source": n_read, "recovered": k_ok,
                   "rate": None if not n_read else round(k_ok / n_read, 3),
                   "ci95": None if ci is None else [round(ci[0], 3), round(ci[1], 3)]}
    return res, dbg


# --- the cases ------------------------------------------------------------------

# Source artwork and the word boxes (fractions of the artwork) for each case.
# Fremont's boxes are `tools/fremont_triage.ROIS` for Kent's four legibility
# circles, plus the two big words he did not circle. Becker and Bridge boxes
# come from the labelled lines of `testdata/lettering_truth.json` through
# `truth_boxes` (the region polygons of those shape ids at the corpus size);
# they are pinned in `PINNED_TRUTH_BOXES` so a read needs no digitize, and
# `--truth-boxes` recomputes them.
CASES: dict[str, dict] = {
    "fremont": {
        "source": "photo/logo_hotel_fremont.webp",
        "boxes": {**FREMONT_BOXES,
                  "hotel": (0.025, 0.415, 0.400, 0.590),
                  "fremont": (0.430, 0.415, 0.970, 0.590)},
    },
    "becker": {"source": "becker_marine_logo.png", "boxes": {}, "truth": "becker"},
    "bridge": {"source": "photo/logo_bridge_bar.jpg", "boxes": {}, "truth": "bridge"},
}

# What each run is, and what Kent (or the repo) says about each word. A word
# with no label is reported and left out of the ranking statistics.
#   illegible: Kent's red circles 1-4 on his 81 mm Hat stitch-out (#898).
#   legible:   words Kent did not circle on that same job; the professional's
#              own Fremont and Becker files (the zip in the repo root,
#              `testdata/reference/becker_*.pes`); Becker and Bridge from the
#              lane's own output, which the director named legible.
KENT_ILLEGIBLE = ("est", "1895", "the", "tagline")
_PRO_FREMONT = {w: "legible" for w in (*KENT_ILLEGIBLE, "hotel", "fremont")}
RUNS: dict[str, dict] = {
    "ours_fremont81": {"case": "fremont", "labels": {
        **{w: "illegible" for w in KENT_ILLEGIBLE}, "hotel": "legible", "fremont": "legible"}},
    "ours_fremont925": {"case": "fremont", "labels": {}},
    "pro_fremont_hat": {"case": "fremont", "labels": dict(_PRO_FREMONT)},
    "pro_fremont_patch": {"case": "fremont", "labels": dict(_PRO_FREMONT)},
    "ours_becker": {"case": "becker", "labels": {"BECKER": "legible", "MARINE": "legible"}},
    "pro_becker": {"case": "becker", "labels": {"BECKER": "legible", "MARINE": "legible"}},
    "ours_bridge": {"case": "bridge", "labels": {
        "Bridge": "legible", "BAR & RESTAURANT": "legible"}},
}


def truth_boxes(name: str, margin_mm: float = 0.3) -> dict[str, tuple]:
    """Word boxes, as fractions of the artwork, from the labelled lines of
    `testdata/lettering_truth.json`: the union of each line's region polygons
    at the corpus size, through the prep frame, grown by `margin_mm`.
    Runs stages 1-4 of the pipeline."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    rel, width, garment = REAL_ART[name]
    truth = json.loads((ROOT / "testdata" / "lettering_truth.json").read_text())
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg)
    p = gen.p
    h, w = p.bg_mask.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out = {}
    for line, ids in truth["fixtures"][name]["lines"].items():
        polys = [r.polygon for r in gen.regions if r.shape_id in set(ids)]
        if not polys:
            continue
        b = [q.bounds for q in polys]
        bx = (min(v[0] for v in b) - margin_mm, min(v[1] for v in b) - margin_mm,
              max(v[2] for v in b) + margin_mm, max(v[3] for v in b) + margin_mm)
        out[line] = tuple(round(v, 4) for v in (
            (bx[0] * p.px_per_mm + cx) / w, (bx[1] * p.px_per_mm + cy) / h,
            (bx[2] * p.px_per_mm + cx) / w, (bx[3] * p.px_per_mm + cy) / h))
    return out


def make_design(name: str) -> dict:
    """The lane's own design for `becker` / `bridge` at their corpus size
    (`tools/thin_strokes.REAL_ART`, the Studio's six colours): the Design dict."""
    from digitizer_core import PipelineConfig
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    rel, width, garment = REAL_ART[name]
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    gen = build_generation(str(ROOT / "testdata" / rel), cfg)
    result = finish_generation(gen.fork(), cfg)
    return plan_to_design(plan_stitches(result, cfg))


def load_design(path) -> dict:
    path = Path(path)
    if path.suffix.lower() == ".json":
        return json.loads(path.read_text())
    return design_from_pes(path)


PINNED_TRUTH_BOXES: dict[str, dict] = {"becker": {}, "bridge": {}}


def read_case(case: str, design: dict, thread_mm: float | None = None,
              use_ocr: bool = True, words: list[str] | None = None):
    """Score every labelled word of `case` in `design`.
    -> ([WordResult], {word: debug}, Registration)."""
    spec = CASES[case]
    rgb, alpha = load_source(ROOT / "testdata" / spec["source"])
    boxes = spec["boxes"] or PINNED_TRUTH_BOXES[spec["truth"]]
    return read_arrays(rgb, alpha, boxes, design, thread_mm, use_ocr, words)


def read_arrays(rgb: np.ndarray, alpha: np.ndarray, boxes: dict, design: dict,
                thread_mm: float | None = None, use_ocr: bool = True,
                words: list[str] | None = None):
    """`read_case` on an artwork already in memory (the tests' synthetic
    glyphs come in here)."""
    from digitizer_core import stitchviz
    thread_mm = stitchviz.THREAD_MM if thread_mm is None else thread_mm
    cache: dict = {}
    ground = ground_colour(rgb, alpha)
    cache[tuple(np.round(ground / 8))] = thread_ink(design, ground, P, thread_mm)
    soft_all, _ = soft_ink(rgb, alpha, ground)
    reg = register(soft_all, cache[tuple(np.round(ground / 8))][0])
    out, dbg = [], {}
    for name, box in boxes.items():
        if words and name not in words:
            continue
        r, d = read_word(name, rgb, alpha, box, design, thread_mm, use_ocr, reg, cache)
        out.append(r)
        dbg[name] = d
    return out, dbg, reg


# --- statistics ------------------------------------------------------------------

BOOTSTRAP = 2000


def auc(pos: list[float], neg: list[float]) -> float | None:
    """P(a legible score is above an illegible one), ties half. None when
    either side is empty."""
    if not pos or not neg:
        return None
    p, n = np.asarray(pos, float)[:, None], np.asarray(neg, float)[None, :]
    return float(((p > n).sum() + 0.5 * (p == n).sum()) / (p.size * n.size))


def cluster_auc_ci(groups_pos: list[list[float]], groups_neg: list[list[float]],
                   seed: int = 7, n_boot: int = BOOTSTRAP) -> dict:
    """AUC with a 95% percentile interval, resampling whole CLUSTERS (words)
    within each side, because the glyphs of one word are not independent.
    With few clusters the interval is wide, and that is the honest answer."""
    rng = np.random.default_rng(seed)
    flat = lambda gs: [v for g in gs for v in g]            # noqa: E731
    point = auc(flat(groups_pos), flat(groups_neg))
    if point is None:
        return {"auc": None, "ci95": None, "n_pos": len(groups_pos), "n_neg": len(groups_neg)}
    vals = []
    for _ in range(n_boot):
        ip = rng.integers(0, len(groups_pos), len(groups_pos))
        ineg = rng.integers(0, len(groups_neg), len(groups_neg))
        a = auc(flat([groups_pos[i] for i in ip]), flat([groups_neg[i] for i in ineg]))
        if a is not None:
            vals.append(a)
    lo, hi = np.percentile(vals, [2.5, 97.5]) if vals else (None, None)
    return {"auc": round(point, 3), "ci95": [round(float(lo), 3), round(float(hi), 3)],
            "n_pos": len(groups_pos), "n_neg": len(groups_neg)}


def validate(results: dict[str, list[WordResult]]) -> dict:
    """The ranking statistics over every labelled word of every run.
    `results` is run id -> its WordResults."""
    rows = []
    for run, words in results.items():
        labels = RUNS[run]["labels"]
        for w in words:
            lab = labels.get(w.name)
            if lab:
                rows.append((run, w, lab))
    pos = [(r, w) for r, w, lab in rows if lab == "legible"]
    neg = [(r, w) for r, w, lab in rows if lab == "illegible"]
    out: dict = {"n_legible_words": len(pos), "n_illegible_words": len(neg)}
    for key in ("legibility", "worst_glyph"):
        ps = [w.summary()[key] for _r, w in pos]
        ns = [w.summary()[key] for _r, w in neg]
        out[f"word_{key}"] = {
            **cluster_auc_ci([[v] for v in ps], [[v] for v in ns]),
            "max_illegible": max(ns) if ns else None,
            "min_legible": min(ps) if ps else None,
            "margin": round(min(ps) - max(ns), 3) if ps and ns else None}
    gp = [[g["legibility"] for g in w.glyphs] for _r, w in pos]
    gn = [[g["legibility"] for g in w.glyphs] for _r, w in neg]
    out["glyph_legibility"] = cluster_auc_ci(gp, gn)
    # Does the geometric number agree with the second reader? Over glyphs whose
    # SOURCE reads, AUC of legibility for "thread read as the same character".
    if not tesseract_available():
        out["ocr_cross_check"] = "OCR UNAVAILABLE"
    else:
        ok, bad = [], []
        for words in results.values():
            for w in words:
                o = [g for g in w.glyphs if g.get("ocr_readable_src")]
                if o:
                    ok.append([g["legibility"] for g in o if g["ocr_recovered"]])
                    bad.append([g["legibility"] for g in o if not g["ocr_recovered"]])
        ok, bad = [x for x in ok if x], [x for x in bad if x]
        out["ocr_cross_check"] = {
            "question": "AUC of glyph legibility for 'OCR recovered the source character'",
            **cluster_auc_ci(ok, bad)}
    return out


# --- panels ---------------------------------------------------------------------

def _tile(S: np.ndarray, T: np.ndarray, scale: int) -> np.ndarray:
    """Source (red), thread (blue), both (dark purple) on white, one glyph."""
    img = np.full(S.shape + (3,), 255, np.uint8)
    img[S & ~T] = (60, 60, 230)            # BGR: red = source only (thread missing)
    img[T & ~S] = (230, 120, 40)           # blue = thread only (excess)
    img[S & T] = (70, 40, 60)              # both
    return cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_NEAREST)


def word_panel(word: WordResult, dbg: dict, title: str, scale: int = 4) -> np.ndarray:
    """One strip per word: a tile per glyph (red = source the thread misses,
    blue = thread off the source, dark = agree), its five readings under it."""
    tiles = []
    for g in dbg["glyphs"]:
        t = _tile(g["S"], g["T"], scale)
        sc = g["score"]
        lines = [f"{sc['legibility']:.2f}",
                 f"sh {sc['shape']:.2f} st {sc['strokes']:.2f}",
                 f"cl {sc['clean']:.2f} co {sc['counters']:.2f}"]
        if "ocr_src" in sc:
            lines.append(f"ocr {sc['ocr_src'] or '-'}>{sc['ocr_sewn'] or '-'}")
        pad = np.full((16 * len(lines) + 4, max(t.shape[1], 118), 3), 245, np.uint8)
        for i, ln in enumerate(lines):
            cv2.putText(pad, ln, (3, 13 + 16 * i), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (20, 20, 20), 1, cv2.LINE_AA)
        w = pad.shape[1]
        t = np.pad(t, ((0, 0), (0, w - t.shape[1]), (0, 0)), constant_values=255)
        tiles.append(np.vstack([t, pad]))
    if not tiles:
        return np.full((40, 400, 3), 255, np.uint8)
    hh = max(t.shape[0] for t in tiles)
    tiles = [np.pad(t, ((0, hh - t.shape[0]), (0, 4), (0, 0)), constant_values=255) for t in tiles]
    strip = np.hstack(tiles)
    s = word.summary()
    bar = np.full((22, strip.shape[1], 3), 225, np.uint8)
    cv2.putText(bar, f"{title}: legibility {s['legibility']:.2f}, worst glyph {s['worst_glyph']:.2f}",
                (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA)
    return np.vstack([bar, strip])


# --- output ------------------------------------------------------------------------

def table(runs: dict[str, list[WordResult]]) -> str:
    lines = [f"{'run':18} {'word':17} {'gl':>3} {'LEGIBILITY':>10} {'worst':>6} {'shape':>6} {'strok':>6} "
             f"{'clean':>6} {'ctrs':>6} {'euler':>6} {'stray':>6} {'offmm':>6}  ocr recovered"]
    for run, words in runs.items():
        for w in words:
            s = w.summary()
            if s["legibility"] is None:
                lines.append(f"{run:18} {w.name:17}   0  NO GLYPHS FOUND")
                continue
            o = s["ocr"]
            ocr = o if isinstance(o, str) else (
                f"{o['recovered']}/{o['read_on_source']}" + ("" if o["ci95"] is None else
                                                              f" [{o['ci95'][0]:.2f}-{o['ci95'][1]:.2f}]"))
            lab = RUNS.get(run, {}).get("labels", {}).get(w.name, "")
            lines.append(f"{run:18} {w.name:17} {s['glyphs']:3d} {s['legibility']:10.3f} {s['worst_glyph']:6.3f} "
                         f"{s['shape']:6.3f} {s['strokes']:6.3f} {s['clean']:6.3f} {s['counters']:6.3f} "
                         f"{s['euler_match']:>6} {s['stray_mm2']:6.2f} {s['max_offset_mm']:6.2f}  {ocr}"
                         f"{'  <' + lab + '>' if lab else ''}")
    return "\n".join(lines)


def _design_path(d: Path, run: str) -> Path | None:
    for ext in (".json", ".pes", ".PES"):
        p = d / f"{run}{ext}"
        if p.exists():
            return p
    return None


def run_validation(src_dir: Path, renders: Path | None, json_out: Path | None,
                   thread_mm: float | None, use_ocr: bool = True) -> int:
    results: dict[str, list[WordResult]] = {}
    dbgs: dict = {}
    regs: dict = {}
    missing = []
    for run, spec in RUNS.items():
        p = _design_path(src_dir, run)
        if p is None:
            missing.append(run)
            continue
        words, dbg, reg = read_case(spec["case"], load_design(p), thread_mm, use_ocr)
        results[run], dbgs[run] = words, dbg
        regs[run] = {"scale_mm_per_src_px": round(reg.mm_per_src_px, 6), "ncc": round(reg.score, 3)}
    print(table(results))
    if missing:
        print("\nMISSING RUNS (not scored): " + ", ".join(missing))
    stats = validate(results)
    print("\n" + json.dumps(stats, indent=1))
    if not tesseract_available():
        print("\nOCR UNAVAILABLE: the tesseract binary is not on PATH; the geometric number stands alone.")
    if json_out:
        json_out.write_text(json.dumps({
            "thread_mm": thread_mm, "ocr": "available" if tesseract_available() and use_ocr else "OCR UNAVAILABLE",
            "missing_runs": missing, "registrations": regs, "statistics": stats,
            "runs": {r: [{**w.summary(), "glyph_rows": w.glyphs} for w in ws] for r, ws in results.items()}},
            indent=1))
    if renders:
        renders.mkdir(parents=True, exist_ok=True)
        for run, words in results.items():
            for w in words:
                if w.glyphs:
                    img = word_panel(w, dbgs[run][w.name], f"{run} / {w.name}")
                    cv2.imwrite(str(renders / f"{run}__{w.name.replace(' ', '_').replace('&', 'and')}.png"), img)
    return 0


def main(argv=None) -> int:
    from tools._console import utf8_console
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--list", action="store_true", help="list cases, runs and labels")
    ap.add_argument("--case", choices=sorted(CASES))
    ap.add_argument("--design", type=Path, help="a Design .json, or a .pes/.dst/.exp stitch file")
    ap.add_argument("--validate", type=Path, metavar="DIR",
                    help="score every run in RUNS found in DIR as <run>.json|.pes")
    ap.add_argument("--make", type=Path, metavar="DIR",
                    help="write ours_becker.json and ours_bridge.json into DIR (digitizes both)")
    ap.add_argument("--truth-boxes", choices=("becker", "bridge", "fremont"))
    ap.add_argument("--thread-mm", type=float, default=None)
    ap.add_argument("--no-ocr", action="store_true")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--renders", type=Path)
    a = ap.parse_args(argv)
    if a.list:
        print(json.dumps({"cases": {k: v.get("boxes") or PINNED_TRUTH_BOXES.get(v.get("truth"))
                                    for k, v in CASES.items()}, "runs": RUNS}, indent=1))
        return 0
    if a.truth_boxes:
        print(json.dumps(truth_boxes(a.truth_boxes), indent=1))
        return 0
    if a.make:
        a.make.mkdir(parents=True, exist_ok=True)
        for name in ("becker", "bridge"):
            (a.make / f"ours_{name}.json").write_text(json.dumps(make_design(name)))
            print("wrote", a.make / f"ours_{name}.json")
        return 0
    if a.validate:
        return run_validation(a.validate, a.renders, a.json, a.thread_mm, not a.no_ocr)
    if a.case and a.design:
        words, dbg, reg = read_case(a.case, load_design(a.design), a.thread_mm, not a.no_ocr)
        print(table({"design": words}))
        if not tesseract_available():
            print("\nOCR UNAVAILABLE: the tesseract binary is not on PATH.")
        if a.json:
            a.json.write_text(json.dumps([{**w.summary(), "glyph_rows": w.glyphs} for w in words], indent=1))
        if a.renders:
            a.renders.mkdir(parents=True, exist_ok=True)
            for w in words:
                if w.glyphs:
                    cv2.imwrite(str(a.renders / f"{w.name.replace(' ', '_')}.png"),
                                word_panel(w, dbg[w.name], w.name))
        return 0
    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
