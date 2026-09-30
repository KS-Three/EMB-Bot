"""Read the sew-out gate card back off a PHOTO — the probe behind closed-loop
sew-out calibration (docs/sewout-calibration-brief-2026-09-30.md).

## What this is

`tools/sewout_card.py` builds ONE hooping whose blocks vary exactly the
constants ROADMAP gate 1 says only cloth can settle: lock length, fill row
spacing, satin column width, travel step, small-text tier, seam underlap.
Today the answers come back as Kent's eyes on the fabric and a paper key.
This tool asks whether a phone photo of that same card can be turned into
NUMBERS — how far each satin bar pulled in, how much cloth shows through each
fill square, whether a seam opened, whether the small words still read — so
that a customer's own machine, fabric and stabilizer could write a fabric
profile instead of Kent hand-tuning a constant for everyone.

The measurement is DIFFERENTIAL, and that is the whole design. A thread
render and a photo disagree on what "the edge of a bar" is by a filament
width, by anti-aliasing, by how the cloth lights. So the reader never
compares a photo against nominal millimetres. It runs the SAME code on the
engine's own render of the card (`stitchviz.render_design`) and on the
photo, and reports the difference. Everything that biases both alike
cancels; what remains is what the cloth did.

## Method

 1. **Register.** Map the photo onto the card's plan frame (mm, y-down,
    origin at the sewn bounding box's top-left) at `READ_PX_PER_MM`. Three
    ways in, each honest about what it needs:
      * `corners=` — four pixel positions of the sewn bbox's corners (TL, TR,
        BR, BL). The oracle path: what a fiducial or a human click gives.
      * `auto` — threshold thread from fabric over the whole photo, take the
        ink's minimum-area rectangle as a first guess, then refine the
        homography with ECC (`cv2.findTransformECC`) against the plan's own
        rendered ink mask. Needs no marks on the card; absorbs any GLOBAL
        shrink into the registration, so it can only see local distortion.
      * fiducials — when the card carries four corner marks
        (`with_fiducials`, proposed, not sewn yet), their centroids map
        straight onto the plan and registration needs no artwork at all.
 2. **Segment thread from cloth** per feature: CIE76 distance from the
    fabric colour (the median of a ring just outside the feature's nominal
    box), Otsu-thresholded over the feature's ROI. No colour constant.
 3. **Measure.** A bar or square's sewn HEIGHT is the median per-column ink
    extent over the middle 80% of its columns; its WIDTH the same by rows.
    Coverage is the ink fraction inside the measured box eroded by half a
    thread. A seam pair's GAP is the median bare-cloth run crossing the
    seam line. A word gets its box, its coverage and, when tesseract is
    installed, what OCR reads on the photo against what it reads on the
    render (`digitizer_core.legibility` does the same for the review).
 4. **Compare** photo readings to render readings, feature by feature, and
    draft a fabric-profile delta from them: mean satin pull-in, mean fill
    coverage deficit, seam opening per underlap rung. The draft is a
    REPORT. Nothing here writes a constant — gate 1 is untouched.

## Calibration before cloth

No photo of a sewn card exists yet (`docs/sewout-card-2026-07-31.md`). So
`simulate_photo` fakes one: it applies KNOWN per-feature distortions to the
card design (a bar pulled in 0.3 mm across, pushed 0.4 mm along; a square
narrowed; a seam opened), renders it as thread on textured cloth, warps it
through a perspective, down-samples to phone resolution, blurs, adds sensor
noise and a JPEG round trip — then the reader must recover the distortions
it was given. `tests/test_sewout_reader.py` asserts it does, at TWO
different distortion sets, because recovering one value proves nothing (the
discipline `test_fill_pitch.py` set). What the simulator cannot fake, and
says so: thread thinning on real cloth, nap, puckering, a hoop's own
stretch. Those wait on Kent's photographs, which this tool is built to take.

Usage (from digitizer/):
    .venv/bin/python tools/sewout_reader.py --simulate [--px-per-mm 12] [--out DIR]
    .venv/bin/python tools/sewout_reader.py --photo card.jpg [--corners x,y x,y x,y x,y]
        [--design debug_out/sewout/EMBBOT_SEWOUT_CARD.design.json] [--json out.json]
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import shutil
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import stitchviz                                  # noqa: E402
from digitizer_core.stitchviz import UNITS_PER_MM, render_design     # noqa: E402

# The plan-frame raster every measurement is taken on. 20 px/mm is where
# `stitchviz.coverage` measures too: a 0.4 mm filament lands on 8 px, so a
# half-pixel edge is 0.025 mm and rounding cannot masquerade as pull.
READ_PX_PER_MM = 20.0
READ_PAD_MM = 3.0

# How far outside a feature's nominal box its ROI reaches, and the ring the
# fabric colour is read from. 1.5 mm is under half the tightest gap between
# neighbouring features on the card (satin bars: 5 mm apart), so a ROI never
# takes in a neighbour's thread.
ROI_MARGIN_MM = 1.5
FABRIC_RING_MM = (0.7, 1.5)

# The per-column extent is read over the middle of a bar, never its ends —
# a satin's end is where push shows and where the tie sits, and neither is
# the column's width.
INTERIOR_FRAC = 0.8

# An Otsu split narrower than this in Lab distance is noise, not thread.
MIN_INK_SEPARATION = 10.0

DEFAULT_DESIGN = ROOT / "debug_out" / "sewout" / "EMBBOT_SEWOUT_CARD.design.json"

# Feature roles, from the card's shape ids (tools/sewout_card.py). The words
# of block "5 TEXT" carry pipeline ids, so they are found by position.
BAR_PREFIXES = ("lock-", "satin-")
SQUARE_PREFIXES = ("fill-",)
SEAM_PREFIX = "seam-"
PATH_PREFIXES = ("straight-", "curve-")
WORD_GAP_MM = 3.0

FIDUCIAL_MM = 2.5
FIDUCIAL_GAP_MM = 1.0


# --- the card's layout, from its own design JSON -----------------------------

@dataclass
class Feature:
    name: str
    role: str                       # bar | square | seam | path | word
    block: int
    bbox_mm: tuple[float, float, float, float]   # plan frame: x0, y0, x1, y1
    shapes: tuple[str, ...] = ()


def _frame(design: dict) -> tuple[float, float, float, float]:
    """(x0_units, y1_units, W_mm, H_mm): the sewn bbox in design units, and
    the card's size. Plan frame = mm, y-down, origin at that bbox's TL."""
    b = stitchviz._bounds(design["stitches"])
    if b is None:
        raise ValueError("design has no stitches")
    x0, x1, y0, y1 = b
    return x0, y1, (x1 - x0) / UNITS_PER_MM, (y1 - y0) / UNITS_PER_MM


def _to_plan(design: dict, x_units: float, y_units: float) -> tuple[float, float]:
    x0, y1, _, _ = _frame(design)
    return (x_units - x0) / UNITS_PER_MM, (y1 - y_units) / UNITS_PER_MM


def _span_bbox(design: dict, spans: list[dict]) -> tuple[float, float, float, float]:
    xs: list[float] = []
    ys: list[float] = []
    st = design["stitches"]
    for sp in spans:
        for s in st[sp["i0"]:sp["i1"] + 1]:
            px, py = _to_plan(design, s["x"], s["y"])
            xs.append(px)
            ys.append(py)
    return min(xs), min(ys), max(xs), max(ys)


def features_from_design(design: dict) -> list[Feature]:
    """The card's measurable features and their NOMINAL boxes, read from the
    run-span index `adapter.plan_to_design` writes — never from the card
    builder's private constants, so a moved block moves its feature too."""
    runs = design.get("runs") or []
    by_shape: dict[tuple[int, str], list[dict]] = {}
    for r in runs:
        by_shape.setdefault((r["block"], r["shape"]), []).append(r)

    feats: list[Feature] = []
    # Words are clustered per RUN, not per shape: the four words come out of
    # four separate pipeline calls, and their shape ids collide (SEW's E and
    # INC's N both carry `Sda7eaa24` on the 2026-09-30 build), so a per-shape
    # box would span the whole line.
    words_block: dict[int, list[tuple[str, list[dict]]]] = {}
    for (block, shape), spans in by_shape.items():
        if shape.startswith(BAR_PREFIXES):
            core = [s for s in spans if s["kind"] == "satin"] or spans
            feats.append(Feature(shape, "bar", block, _span_bbox(design, core), (shape,)))
        elif shape.startswith(SQUARE_PREFIXES):
            core = [s for s in spans if s["kind"] == "fill"] or spans
            feats.append(Feature(shape, "square", block, _span_bbox(design, core), (shape,)))
        elif shape.startswith(SEAM_PREFIX):
            core = [s for s in spans if s["kind"] == "fill"] or spans
            feats.append(Feature(shape, "seam", block, _span_bbox(design, core), (shape,)))
        elif shape.startswith(PATH_PREFIXES):
            feats.append(Feature(shape, "path", block, _span_bbox(design, spans), (shape,)))
        elif shape == "__fiducial__":
            continue
        else:
            for s in spans:
                if s["kind"] != "travel":
                    words_block.setdefault(block, []).append((shape, [s]))

    # fill-C is two passes over one square: merge by prefix.
    merged: dict[str, Feature] = {}
    out: list[Feature] = []
    for f in feats:
        if f.role == "square" and f.name.startswith("fill-C"):
            key = "fill-C"
            if key in merged:
                m = merged[key]
                b = m.bbox_mm
                m.bbox_mm = (min(b[0], f.bbox_mm[0]), min(b[1], f.bbox_mm[1]),
                             max(b[2], f.bbox_mm[2]), max(b[3], f.bbox_mm[3]))
                m.shapes = tuple(sorted(m.shapes + f.shapes))
            else:
                merged[key] = Feature(key, "square", f.block, f.bbox_mm, f.shapes)
                out.append(merged[key])
        else:
            out.append(f)

    # Words: cluster a block's pipeline shapes by x gap.
    for block, items in words_block.items():
        boxes = [(_span_bbox(design, sp), shape) for shape, sp in items]
        boxes.sort(key=lambda t: t[0][0])
        cluster: list[tuple[tuple[float, float, float, float], str]] = []
        clusters: list[list] = []
        for bb, shape in boxes:
            if cluster and bb[0] - max(b[2] for b, _ in cluster) > WORD_GAP_MM:
                clusters.append(cluster)
                cluster = []
            cluster.append((bb, shape))
        if cluster:
            clusters.append(cluster)
        for i, cl in enumerate(clusters):
            bb = (min(b[0] for b, _ in cl), min(b[1] for b, _ in cl),
                  max(b[2] for b, _ in cl), max(b[3] for b, _ in cl))
            out.append(Feature(f"word-{i}", "word", block, bb,
                               tuple(sorted({s for _, s in cl}))))

    out.sort(key=lambda f: (f.block, f.bbox_mm[1], f.bbox_mm[0]))
    return out


# --- registration ----------------------------------------------------------

def plan_corners_px(W_mm: float, H_mm: float, px_per_mm: float = READ_PX_PER_MM,
                    pad_mm: float = READ_PAD_MM) -> np.ndarray:
    p = pad_mm * px_per_mm
    return np.array([[p, p], [p + W_mm * px_per_mm, p],
                     [p + W_mm * px_per_mm, p + H_mm * px_per_mm],
                     [p, p + H_mm * px_per_mm]], np.float32)


def _order_corners(pts: np.ndarray) -> np.ndarray:
    """TL, TR, BR, BL of four points, by the usual sum/diff rule."""
    pts = np.asarray(pts, np.float32).reshape(4, 2)
    s = pts.sum(axis=1)
    d = pts[:, 0] - pts[:, 1]
    return np.array([pts[np.argmin(s)], pts[np.argmax(d)],
                     pts[np.argmax(s)], pts[np.argmin(d)]], np.float32)


def ink_mask(img_bgr: np.ndarray, fabric_lab: np.ndarray | None = None
             ) -> tuple[np.ndarray, float]:
    """Thread-vs-cloth over a whole image: distance from the fabric colour
    (the median of the image border when not given), Otsu split. Returns the
    mask and the separation the split found (0 when it found nothing)."""
    lab = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2LAB).astype(np.float32)
    if fabric_lab is None:
        h, w = lab.shape[:2]
        m = max(2, min(h, w) // 40)
        ring = np.concatenate([lab[:m].reshape(-1, 3), lab[-m:].reshape(-1, 3),
                               lab[:, :m].reshape(-1, 3), lab[:, -m:].reshape(-1, 3)])
        fabric_lab = np.median(ring, axis=0)
    de = np.linalg.norm(lab - fabric_lab[None, None, :], axis=2)
    de8 = np.clip(de, 0, 255).astype(np.uint8)
    t, _ = cv2.threshold(de8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = de > t
    ink_med = float(np.median(de[mask])) if mask.any() else 0.0
    return mask, ink_med


def auto_corners(img_bgr: np.ndarray) -> np.ndarray:
    """The ink's minimum-area rectangle, as TL/TR/BR/BL. A first guess: under
    perspective the sewn bbox is not a rectangle, and the card's own ink does
    not reach its top-right corner, so this is coarse by construction."""
    mask, sep = ink_mask(img_bgr)
    if sep < MIN_INK_SEPARATION:
        raise ValueError("no thread found against the fabric")
    m8 = mask.astype(np.uint8)
    m8 = cv2.morphologyEx(m8, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(m8, connectivity=8)
    if n <= 1:
        raise ValueError("no thread found against the fabric")
    # Drop specks: anything under 0.2% of the largest component.
    areas = stats[1:, cv2.CC_STAT_AREA]
    keep = np.where(areas >= max(4, 0.002 * areas.max()))[0] + 1
    pts = np.column_stack(np.where(np.isin(lab, keep)))[:, ::-1].astype(np.float32)
    rect = cv2.minAreaRect(pts)
    return _order_corners(cv2.boxPoints(rect))


def fiducial_points(img_bgr: np.ndarray, design: dict
                    ) -> tuple[np.ndarray, np.ndarray]:
    """For a card built `with_fiducials`: the four marks' CENTROIDS in the
    photo, and where the plan puts them. Centroids, not hull corners — the
    ink's outer edge sits half a filament plus the photo's blur outside the
    penetrations, and mapping that edge onto the plan bbox shrinks every
    reading by ~0.7% (measured 2026-09-30: -0.1 to -0.15 mm on a 25 mm bar).
    A centroid has no such bias."""
    spans = [r for r in design.get("runs") or [] if r["shape"] == "__fiducial__"]
    if len(spans) != 4:
        raise ValueError("design carries no fiducials (see with_fiducials)")
    plan = []
    for sp in spans:
        x0, y0, x1, y1 = _span_bbox(design, [sp])
        plan.append(((x0 + x1) / 2, (y0 + y1) / 2))
    plan = _order_corners(np.array(plan, np.float32))
    mask, sep = ink_mask(img_bgr)
    if sep < MIN_INK_SEPARATION:
        raise ValueError("no thread found against the fabric")
    m8 = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, stats, cents = cv2.connectedComponentsWithStats(m8, connectivity=8)
    if n < 5:
        raise ValueError("fewer than four marks found")
    areas = stats[1:, cv2.CC_STAT_AREA]
    big = areas >= max(4, 0.002 * areas.max())
    ys, xs = np.where(np.isin(lab, np.where(big)[0] + 1))
    ext = np.array([[xs.min(), ys.min()], [xs.max(), ys.min()],
                    [xs.max(), ys.max()], [xs.min(), ys.max()]], np.float32)
    # Each mark is the component whose own bbox corner sits closest to the
    # ink's overall corner on that side.
    cbox = np.stack([stats[1:, cv2.CC_STAT_LEFT], stats[1:, cv2.CC_STAT_TOP],
                     stats[1:, cv2.CC_STAT_LEFT] + stats[1:, cv2.CC_STAT_WIDTH] - 1,
                     stats[1:, cv2.CC_STAT_TOP] + stats[1:, cv2.CC_STAT_HEIGHT] - 1], axis=1).astype(np.float32)
    corner_of = [cbox[:, [0, 1]], cbox[:, [2, 1]], cbox[:, [2, 3]], cbox[:, [0, 3]]]
    found = []
    for k in range(4):
        d = np.linalg.norm(corner_of[k] - ext[k][None, :], axis=1)
        d[~big] = np.inf
        j = int(np.argmin(d))
        found.append(cents[j + 1])
    return np.array(found, np.float32), plan


def rectify(img_bgr: np.ndarray, corners_px: np.ndarray, W_mm: float, H_mm: float,
            px_per_mm: float = READ_PX_PER_MM, pad_mm: float = READ_PAD_MM,
            dst_mm: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Warp the photo so the four corners land on the plan bbox at
    `px_per_mm` — or, with `dst_mm`, so four arbitrary photo points land on
    those plan-frame positions. Returns (image, H)."""
    if dst_mm is None:
        dst = plan_corners_px(W_mm, H_mm, px_per_mm, pad_mm)
    else:
        dst = (np.asarray(dst_mm, np.float32) + pad_mm) * px_per_mm
    H = cv2.getPerspectiveTransform(np.asarray(corners_px, np.float32), dst)
    w = int(round((W_mm + 2 * pad_mm) * px_per_mm))
    h = int(round((H_mm + 2 * pad_mm) * px_per_mm))
    return cv2.warpPerspective(img_bgr, H, (w, h), flags=cv2.INTER_LINEAR,
                               borderMode=cv2.BORDER_REPLICATE), H


def plan_ink_template(design: dict, px_per_mm: float = READ_PX_PER_MM,
                      pad_mm: float = READ_PAD_MM) -> np.ndarray:
    """The plan's own ink, float32 0..1, on the same raster `rectify` makes."""
    lo = render_design(design, px_per_mm=px_per_mm, fabric_bgr=(0, 0, 0),
                       pad_mm=pad_mm, lit=False).astype(np.int16)
    hi = render_design(design, px_per_mm=px_per_mm, fabric_bgr=(255, 255, 255),
                       pad_mm=pad_mm, lit=False).astype(np.int16)
    return (1.0 - np.abs(hi - lo).max(axis=2) / 255.0).astype(np.float32)


def refine_with_ecc(rect_img: np.ndarray, design: dict, px_per_mm: float = READ_PX_PER_MM,
                    pad_mm: float = READ_PAD_MM) -> tuple[np.ndarray, np.ndarray, float]:
    """Nudge a coarse rectification onto the plan by ECC between ink masks.
    Coarse-to-fine: a quarter-scale pass first, because ECC's basin is a few
    pixels wide and the minAreaRect guess can be off by more at full scale.
    Returns (image, warp 3x3, ecc correlation) — the input unchanged and
    correlation 0 when ECC does not converge."""
    tmpl = plan_ink_template(design, px_per_mm, pad_mm)
    mask, _ = ink_mask(rect_img)
    inp = mask.astype(np.float32)
    if inp.shape != tmpl.shape:
        inp = cv2.resize(inp, (tmpl.shape[1], tmpl.shape[0]), interpolation=cv2.INTER_AREA)
    warp = np.eye(3, dtype=np.float32)
    cc = 0.0
    try:
        for scale, sigma, iters in ((0.25, 3.0, 200), (1.0, 1.5, 100)):
            t = cv2.GaussianBlur(tmpl, (0, 0), sigma)
            i = cv2.GaussianBlur(inp, (0, 0), sigma)
            if scale != 1.0:
                t = cv2.resize(t, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                i = cv2.resize(i, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            S = np.diag([scale, scale, 1.0]).astype(np.float32)
            w_s = S @ warp @ np.linalg.inv(S)
            crit = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, iters, 1e-6)
            cc, w_s = cv2.findTransformECC(t, i, w_s.astype(np.float32),
                                           cv2.MOTION_HOMOGRAPHY, crit, None, 5)
            warp = (np.linalg.inv(S) @ w_s @ S).astype(np.float32)
    except cv2.error:
        return rect_img, np.eye(3, dtype=np.float32), 0.0
    out = cv2.warpPerspective(rect_img, warp, (tmpl.shape[1], tmpl.shape[0]),
                              flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
                              borderMode=cv2.BORDER_REPLICATE)
    return out, warp, float(cc)


# --- measurement -----------------------------------------------------------

@dataclass
class Reading:
    name: str
    role: str
    nominal_w_mm: float
    nominal_h_mm: float
    width_mm: float | None = None      # sewn extent along x (median by row)
    height_mm: float | None = None     # sewn extent along y (median by column)
    coverage: float | None = None      # ink fraction inside the eroded sewn box
    gap_mm: float | None = None        # seam pairs only
    ocr: str | None = None             # words only, when tesseract exists
    ink_separation: float = 0.0        # Lab distance thread vs cloth the split found
    note: str = ""


def _roi(img: np.ndarray, bbox_mm, px_per_mm: float, pad_mm: float, margin_mm: float
         ) -> tuple[np.ndarray, tuple[int, int]]:
    x0, y0, x1, y1 = bbox_mm
    c0 = int(math.floor((x0 - margin_mm + pad_mm) * px_per_mm))
    r0 = int(math.floor((y0 - margin_mm + pad_mm) * px_per_mm))
    c1 = int(math.ceil((x1 + margin_mm + pad_mm) * px_per_mm))
    r1 = int(math.ceil((y1 + margin_mm + pad_mm) * px_per_mm))
    c0, r0 = max(0, c0), max(0, r0)
    c1, r1 = min(img.shape[1], c1), min(img.shape[0], r1)
    return img[r0:r1, c0:c1], (r0, c0)


@dataclass
class _Seg:
    """A feature's thread-vs-cloth split: the mask, the Lab distance map it
    was cut from and the threshold, so an edge can be placed BETWEEN pixels."""
    mask: np.ndarray
    de: np.ndarray
    t: float
    origin: tuple[int, int]
    separation: float


def _feature_mask(img: np.ndarray, f: Feature, px_per_mm: float, pad_mm: float
                  ) -> tuple[np.ndarray, tuple[int, int], float]:
    s = _segment(img, f, px_per_mm, pad_mm)
    return s.mask, s.origin, s.separation


def _segment(img: np.ndarray, f: Feature, px_per_mm: float, pad_mm: float) -> _Seg:
    """Thread mask over the feature's ROI, fabric read from a ring just outside
    the nominal box."""
    roi, (r0, c0) = _roi(img, f.bbox_mm, px_per_mm, pad_mm, ROI_MARGIN_MM)
    lab = cv2.cvtColor(roi, cv2.COLOR_BGR2LAB).astype(np.float32)
    x0, y0, x1, y1 = f.bbox_mm
    yy, xx = np.mgrid[0:roi.shape[0], 0:roi.shape[1]]
    px = (xx + c0) / px_per_mm - pad_mm
    py = (yy + r0) / px_per_mm - pad_mm
    dx = np.maximum(np.maximum(x0 - px, px - x1), 0.0)
    dy = np.maximum(np.maximum(y0 - py, py - y1), 0.0)
    dist = np.hypot(dx, dy)
    ring = (dist >= FABRIC_RING_MM[0]) & (dist <= FABRIC_RING_MM[1])
    if ring.sum() < 20:
        ring = dist > FABRIC_RING_MM[0]
    fabric = np.median(lab[ring], axis=0)
    de = np.linalg.norm(lab - fabric[None, None, :], axis=2)
    de8 = np.clip(de, 0, 255).astype(np.uint8)
    t, _ = cv2.threshold(de8, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    mask = de > t
    # Only the feature's own thread: keep components that touch the nominal
    # box grown by a little, so a neighbour's edge at the ROI rim drops out.
    inside = (dist <= 0.6)
    n, lab_cc = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    keep = np.unique(lab_cc[inside & mask])
    keep = keep[keep > 0]
    mask = np.isin(lab_cc, keep)
    sep = float(np.median(de[mask]) - np.median(de[~mask & (dist > 0.3)])) if mask.any() else 0.0
    return _Seg(mask, de, float(t), (r0, c0), sep)


def _crossing(prof: np.ndarray, i: int, j: int, t: float) -> float:
    """Where `prof` crosses `t` between samples i (one side) and j (other),
    linearly. Falls back to the boundary between them when it does not."""
    a, b = float(prof[i]), float(prof[j])
    if (a - t) * (b - t) > 0 or a == b:
        return (i + j) / 2.0
    return i + (t - a) / (b - a) * (j - i)


def _extent(seg: _Seg, axis: int, px_per_mm: float) -> float | None:
    """Median ink extent along `axis` over the middle INTERIOR_FRAC of the
    lines that carry ink on the other axis — with each edge placed at the
    sub-pixel crossing of the distance map, so a 1 px raster does not
    quantize a 0.3 mm pull into 0.4."""
    mask, de, t = seg.mask, seg.de, seg.t
    has = mask.any(axis=axis)
    idx = np.where(has)[0]
    if len(idx) < 4:
        return None
    lo = idx[0] + (1 - INTERIOR_FRAC) / 2 * (idx[-1] - idx[0])
    hi = idx[-1] - (1 - INTERIOR_FRAC) / 2 * (idx[-1] - idx[0])
    lines = [i for i in idx if lo <= i <= hi] or list(idx)
    ext = []
    n = mask.shape[0] if axis == 0 else mask.shape[1]
    for i in lines:
        line = mask[:, i] if axis == 0 else mask[i, :]
        prof = de[:, i] if axis == 0 else de[i, :]
        on = np.where(line)[0]
        first, last = int(on[0]), int(on[-1])
        start = _crossing(prof, first - 1, first, t) if first > 0 else first - 0.5
        end = _crossing(prof, last + 1, last, t) if last < n - 1 else last + 0.5
        ext.append(end - start)
    return float(np.median(ext)) / px_per_mm


def _box_of(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    ys, xs = np.where(mask)
    if len(xs) == 0:
        return None
    return xs.min(), ys.min(), xs.max(), ys.max()


def measure_feature(img: np.ndarray, f: Feature, px_per_mm: float = READ_PX_PER_MM,
                    pad_mm: float = READ_PAD_MM, ocr: bool = False,
                    render_for_ocr: np.ndarray | None = None) -> Reading:
    x0, y0, x1, y1 = f.bbox_mm
    rd = Reading(f.name, f.role, round(x1 - x0, 3), round(y1 - y0, 3))
    seg = _segment(img, f, px_per_mm, pad_mm)
    mask, sep = seg.mask, seg.separation
    rd.ink_separation = round(sep, 1)
    if sep < MIN_INK_SEPARATION or not mask.any():
        rd.note = "no thread found"
        return rd
    if f.role != "seam":
        # A seam half abuts its partner, so its thread is connected to the
        # partner's and an extent would measure the PAIR. The seam's number
        # is its gap (`measure_seam_gap`); the half reports coverage only.
        rd.height_mm = _extent(seg, 0, px_per_mm)
        rd.width_mm = _extent(seg, 1, px_per_mm)
    if rd.height_mm is not None:
        rd.height_mm = round(rd.height_mm, 3)
    if rd.width_mm is not None:
        rd.width_mm = round(rd.width_mm, 3)
    box = _box_of(mask)
    if box is not None:
        bx0, by0, bx1, by1 = box
        e = max(1, int(round(stitchviz.THREAD_MM / 2 * px_per_mm)))
        inner = mask[by0 + e:by1 - e + 1, bx0 + e:bx1 - e + 1]
        if inner.size:
            rd.coverage = round(float(inner.mean()), 4)
    if ocr and f.role == "word":
        rd.ocr = _ocr(img, f, px_per_mm, pad_mm)
    return rd


def measure_seam_gap(img: np.ndarray, a: Feature, b: Feature,
                     px_per_mm: float = READ_PX_PER_MM, pad_mm: float = READ_PAD_MM
                     ) -> float | None:
    """Bare cloth across the seam between A (left) and B (right): for each
    row through the pair's middle, the longest ink-free run inside ±1 mm of
    the nominal seam line. Median, mm. 0.0 when the rows meet."""
    seam_x = (a.bbox_mm[2] + b.bbox_mm[0]) / 2.0
    y0 = max(a.bbox_mm[1], b.bbox_mm[1])
    y1 = min(a.bbox_mm[3], b.bbox_mm[3])
    pair = Feature("pair", "seam", a.block, (a.bbox_mm[0], y0, b.bbox_mm[2], y1))
    mask, (r0, c0), sep = _feature_mask(img, pair, px_per_mm, pad_mm)
    if sep < MIN_INK_SEPARATION:
        return None
    cs = int(round((seam_x - 1.0 + pad_mm) * px_per_mm)) - c0
    ce = int(round((seam_x + 1.0 + pad_mm) * px_per_mm)) - c0
    rs = int(round((y0 + 0.1 * (y1 - y0) + pad_mm) * px_per_mm)) - r0
    re = int(round((y1 - 0.1 * (y1 - y0) + pad_mm) * px_per_mm)) - r0
    gaps = []
    for r in range(max(0, rs), min(mask.shape[0], re)):
        line = mask[r, max(0, cs):min(mask.shape[1], ce)]
        best = run = 0
        for v in line:
            run = 0 if v else run + 1
            best = max(best, run)
        gaps.append(best)
    if not gaps:
        return None
    return round(float(np.median(gaps)) / px_per_mm, 3)


def _ocr(img: np.ndarray, f: Feature, px_per_mm: float, pad_mm: float) -> str | None:
    if shutil.which("tesseract") is None:
        return None
    try:
        import pytesseract
    except ImportError:
        return None
    roi, _ = _roi(img, f.bbox_mm, px_per_mm, pad_mm, 1.0)
    g = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    scale = max(1.0, 96.0 / max(1, g.shape[0]))
    g = cv2.resize(g, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    g = cv2.copyMakeBorder(g, 24, 24, 24, 24, cv2.BORDER_REPLICATE)
    try:
        return pytesseract.image_to_string(g, config="--psm 7").strip()
    except Exception:  # pragma: no cover — tesseract runtime failure
        return None


def read_card(img_bgr: np.ndarray, design: dict, corners_px: np.ndarray | None = None,
              mode: str = "auto", ocr: bool = False) -> dict:
    """Register a photo (or a render) to the card and measure every feature.

    mode: "corners" (needs corners_px), "auto" (minAreaRect + ECC), or
    "fiducials" (ink hull corners, for a card built `with_fiducials`).
    """
    _, _, W, H = _frame(design)
    if mode == "corners":
        if corners_px is None:
            raise ValueError("mode=corners needs corners_px")
        rect, _ = rectify(img_bgr, corners_px, W, H)
        ecc = None
    elif mode == "fiducials":
        src, dst = fiducial_points(img_bgr, design)
        rect, _ = rectify(img_bgr, src, W, H, dst_mm=dst)
        ecc = None
    elif mode == "auto":
        rect, _ = rectify(img_bgr, auto_corners(img_bgr), W, H)
        rect, _, ecc = refine_with_ecc(rect, design)
    else:
        raise ValueError(f"unknown mode {mode!r}")

    feats = features_from_design(design)
    readings = [measure_feature(rect, f, ocr=ocr) for f in feats]
    seams = {}
    by_name = {f.name: f for f in feats}
    for f in feats:
        if f.role == "seam" and f.name.startswith("seam-A-"):
            rung = f.name[len("seam-A-"):]
            b = by_name.get(f"seam-B-{rung}")
            if b is not None:
                seams[rung] = measure_seam_gap(rect, f, b)
    return {
        "mode": mode,
        "ecc": None if ecc is None else round(ecc, 4),
        "card_mm": [round(W, 2), round(H, 2)],
        "features": [asdict(r) for r in readings],
        "seam_gap_mm": seams,
        "_rectified": rect,
    }


# --- photo vs render ---------------------------------------------------------

def render_reference(design: dict) -> np.ndarray:
    """The engine's own picture of the card, on the same raster the photo is
    read on. Measured with the same code, so filament width and
    anti-aliasing cancel out of every delta."""
    return render_design(design, px_per_mm=READ_PX_PER_MM, pad_mm=READ_PAD_MM, lit=True)


def read_reference(design: dict, ocr: bool = False) -> dict:
    _, _, W, H = _frame(design)
    ref = render_reference(design)
    return read_card(ref, design, corners_px=plan_corners_px(W, H), mode="corners", ocr=ocr)


def compare(photo: dict, reference: dict) -> dict:
    """Per-feature deltas, photo minus render, and a DRAFT profile delta.
    Positive width/height delta = the cloth shows more thread extent than the
    plan drew; negative = it pulled in. Coverage delta negative = cloth shows
    through that the render did not have."""
    ref = {r["name"]: r for r in reference["features"]}
    rows = []
    for r in photo["features"]:
        q = ref.get(r["name"])
        if q is None:
            continue

        def d(k):
            if r.get(k) is None or q.get(k) is None:
                return None
            return round(r[k] - q[k], 3)
        rows.append({"name": r["name"], "role": r["role"],
                     "d_width_mm": d("width_mm"), "d_height_mm": d("height_mm"),
                     "d_coverage": d("coverage"),
                     "ocr_photo": r.get("ocr"), "ocr_render": q.get("ocr"),
                     "note": r.get("note", "")})
    seams = {}
    for rung, g in (photo.get("seam_gap_mm") or {}).items():
        g0 = (reference.get("seam_gap_mm") or {}).get(rung)
        seams[rung] = None if g is None or g0 is None else round(g - g0, 3)

    # Draft profile deltas. A satin column's rows run ACROSS the bar (the
    # zigzag is vertical on every card bar), so pull-in is the HEIGHT delta
    # and push is the WIDTH delta; a fill square's rows run along x, so its
    # pull-in is the width delta.
    bars = [x for x in rows if x["role"] == "bar" and x["d_height_mm"] is not None
            and not x["name"].startswith("lock-")]
    squares = [x for x in rows if x["role"] == "square" and x["d_coverage"] is not None]

    def mean_of(rows_, key, sign=1.0):
        vals = [x[key] for x in rows_ if x.get(key) is not None]
        return None if not vals else round(sign * float(np.mean(vals)), 4)

    draft = {
        "satin_pull_in_mm": mean_of(bars, "d_height_mm", -1.0),
        "satin_push_out_mm": mean_of(bars, "d_width_mm"),
        "fill_pull_in_mm": mean_of(squares, "d_width_mm", -1.0),
        "fill_coverage_deficit": mean_of(squares, "d_coverage", -1.0),
        "seam_opened_mm": seams,
        "basis": "photo minus the engine's render, same reader — a draft, not a constant (gate 1)",
    }
    return {"features": rows, "seam_gap_delta_mm": seams, "draft_profile_delta": draft}


# --- simulation: a fake phone photo with KNOWN distortions ------------------

@dataclass
class Distortion:
    shape: str                 # a shape id, exactly — or a prefix ending in "*"
    dx_mm: float = 0.0         # change in the feature's sewn WIDTH (x extent)
    dy_mm: float = 0.0         # change in its sewn HEIGHT (y extent)
    block: int | None = None

    def matches(self, shape_id: str) -> bool:
        if self.shape.endswith("*"):
            return shape_id.startswith(self.shape[:-1])
        return shape_id == self.shape


def distort(design: dict, distortions: list[Distortion]) -> dict:
    """Scale each named feature's stitches about its own centre so its bbox
    changes by (dx, dy). A pull-in of 0.3 mm across a bar is dy=-0.3.

    Coordinates are left in FLOAT design units on purpose. Rounding them to
    the 0.1 mm grid quantized a planted 0.3 and a planted 0.5 to the same
    0.4 (measured 2026-09-30), which read as a reader defect and was not.
    The renderer never needed integers; a machine file would, and this
    design is not written to one.

    Names match EXACTLY unless they end in "*": "seam-A-0" is one square,
    and a prefix would also take "seam-A-0.25" and "seam-A-0.5" with it."""
    d = copy.deepcopy(design)
    st = d["stitches"]
    for dist in distortions:
        spans = [r for r in d["runs"] if dist.matches(r["shape"])
                 and (dist.block is None or r["block"] == dist.block)]
        if not spans:
            raise ValueError(f"no runs match {dist.shape!r}")
        idx = [i for sp in spans for i in range(sp["i0"], sp["i1"] + 1)]
        xs = np.array([st[i]["x"] for i in idx], float)
        ys = np.array([st[i]["y"] for i in idx], float)
        cx, cy = (xs.min() + xs.max()) / 2, (ys.min() + ys.max()) / 2
        w, h = xs.max() - xs.min(), ys.max() - ys.min()
        sx = (w + dist.dx_mm * UNITS_PER_MM) / w if w > 0 else 1.0
        sy = (h + dist.dy_mm * UNITS_PER_MM) / h if h > 0 else 1.0
        for i in idx:
            st[i]["x"] = cx + (st[i]["x"] - cx) * sx
            st[i]["y"] = cy + (st[i]["y"] - cy) * sy
    return d


def with_fiducials(design: dict, size_mm: float = FIDUCIAL_MM,
                   gap_mm: float = FIDUCIAL_GAP_MM) -> dict:
    """The PROPOSED card change: four small satin squares just outside the
    sewn bbox's corners, in the first block's thread (no extra stop), so a
    photo registers off marks instead of off the artwork. Grows the card by
    2 * (gap + size) each way — 66 x 96 becomes 73 x 103, which is the
    reason this is a proposal and not the card."""
    d = copy.deepcopy(design)
    x0u, y1u, W, H = _frame(design)
    x1u = x0u + W * UNITS_PER_MM
    y0u = y1u - H * UNITS_PER_MM
    g, s = gap_mm * UNITS_PER_MM, size_mm * UNITS_PER_MM
    corners = [(x0u - g - s, y1u + g), (x1u + g, y1u + g),
               (x1u + g, y0u - g - s), (x0u - g - s, y0u - g - s)]
    step = int(round(stitchviz.THREAD_MM * UNITS_PER_MM))
    new: list[dict] = []
    spans: list[dict] = []
    for (cx, cy) in corners:
        pts = []
        n = int(s // step) + 1
        for i in range(n + 1):
            x = int(round(cx + min(s, i * step)))
            pts.append((x, int(round(cy))))
            pts.append((x, int(round(cy + s))))
        new.append({"x": pts[0][0], "y": pts[0][1], "type": "jump"})
        i0 = len(new)
        for x, y in pts:
            new.append({"x": x, "y": y, "type": "stitch"})
        spans.append({"i0": i0, "i1": len(new) - 1, "kind": "satin",
                      "shape": "__fiducial__", "role": "", "block": 0})
        new.append({"x": pts[-1][0], "y": pts[-1][1], "type": "trim"})
    off = len(new)
    for r in d["runs"]:
        r["i0"] += off
        r["i1"] += off
    d["stitches"] = new + d["stitches"]
    d["runs"] = spans + d["runs"]
    return d


def _pique(h: int, w: int, rng: np.random.Generator, amp: float = 0.07) -> np.ndarray:
    """A knit's texture: low-pass noise, ±amp, multiplicative."""
    n = rng.standard_normal((h, w)).astype(np.float32)
    n = cv2.GaussianBlur(n, (0, 0), 2.5)
    n /= max(1e-6, np.abs(n).max())
    return 1.0 + amp * n


def simulate_photo(design: dict, photo_px_per_mm: float = 12.0, seed: int = 0,
                   perspective: float = 0.04, fabric_bgr: tuple[int, int, int] = (196, 203, 208),
                   noise_sigma: float = 3.0, blur_sigma: float = 0.6, jpeg_q: int = 85
                   ) -> tuple[np.ndarray, np.ndarray]:
    """-> (photo BGR, true corners px of the plan bbox in that photo).

    Renders the design as thread on textured, unevenly lit cloth at 20 px/mm,
    warps the corners by up to `perspective` of the card's size, resamples
    to `photo_px_per_mm`, blurs, adds sensor noise and a JPEG round trip.
    Deterministic in `seed`.
    """
    rng = np.random.default_rng(seed)
    _, _, W, H = _frame(design)
    hi = render_design(design, px_per_mm=READ_PX_PER_MM, fabric_bgr=fabric_bgr,
                       pad_mm=READ_PAD_MM, lit=True).astype(np.float32)
    h, w = hi.shape[:2]
    # texture + lighting
    tex = _pique(h, w, rng)
    gx = np.linspace(-1, 1, w, dtype=np.float32)[None, :]
    gy = np.linspace(-1, 1, h, dtype=np.float32)[:, None]
    light = 1.0 + 0.10 * (0.6 * gx + 0.4 * gy)
    hi *= (tex * light)[:, :, None]
    hi = np.clip(hi, 0, 255)
    # perspective: jitter the four canvas corners
    src = np.array([[0, 0], [w, 0], [w, h], [0, h]], np.float32)
    jit = rng.uniform(-perspective, perspective, (4, 2)).astype(np.float32) * np.array([w, h], np.float32)
    dst = src + jit
    dst -= dst.min(axis=0)
    ow, oh = int(math.ceil(dst[:, 0].max())), int(math.ceil(dst[:, 1].max()))
    Hm = cv2.getPerspectiveTransform(src, dst)
    warped = cv2.warpPerspective(hi, Hm, (ow, oh), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_REPLICATE)
    # resample to the phone
    scale = photo_px_per_mm / READ_PX_PER_MM
    small = cv2.resize(warped, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    if blur_sigma > 0:
        small = cv2.GaussianBlur(small, (0, 0), blur_sigma)
    small = small + rng.normal(0, noise_sigma, small.shape).astype(np.float32)
    small = np.clip(small, 0, 255).astype(np.uint8)
    ok, buf = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, jpeg_q])
    photo = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    # where the plan bbox corners went
    pc = plan_corners_px(W, H).reshape(-1, 1, 2)
    true = cv2.perspectiveTransform(pc, Hm).reshape(4, 2) * scale
    return photo, true.astype(np.float32)


def overlay(rect_img: np.ndarray, design: dict, readings: dict) -> np.ndarray:
    """The rectified photo with each feature's nominal box and its reading."""
    out = rect_img.copy()
    for f, r in zip(features_from_design(design), readings["features"]):
        x0, y0, x1, y1 = f.bbox_mm
        p0 = (int((x0 + READ_PAD_MM) * READ_PX_PER_MM), int((y0 + READ_PAD_MM) * READ_PX_PER_MM))
        p1 = (int((x1 + READ_PAD_MM) * READ_PX_PER_MM), int((y1 + READ_PAD_MM) * READ_PX_PER_MM))
        cv2.rectangle(out, p0, p1, (0, 0, 255), 1)
        txt = f"{r['name']} {r['width_mm']}x{r['height_mm']}"
        if r.get("coverage") is not None:
            txt += f" c{r['coverage']:.2f}"
        cv2.putText(out, txt, (p0[0], max(10, p0[1] - 3)), cv2.FONT_HERSHEY_SIMPLEX,
                    0.35, (0, 0, 255), 1, cv2.LINE_AA)
    return out


# --- CLI ---------------------------------------------------------------------

def _load_design(path: Path) -> dict:
    if not path.exists():
        raise SystemExit(f"{path} not found — build it: PYTHONPATH=. .venv/bin/python tools/sewout_card.py")
    return json.loads(path.read_text(encoding="utf-8"))


def _strip(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def _cli_simulate(design: dict, px_per_mm: float, out: Path | None, seed: int) -> None:
    truth = [Distortion("satin-4mm", dx_mm=0.4, dy_mm=-0.3),
             Distortion("satin-5mm", dx_mm=0.4, dy_mm=-0.5),
             Distortion("fill-B-0.20", dx_mm=-0.4, dy_mm=0.0),
             Distortion("seam-A-0", dx_mm=-2.0, dy_mm=0.0)]
    bent = distort(design, truth)
    photo, true_corners = simulate_photo(bent, px_per_mm, seed=seed)
    ref = read_reference(design)
    report = {"photo_px_per_mm": px_per_mm, "truth": [asdict(t) for t in truth], "modes": {}}
    for mode in ("corners", "auto", "fiducials"):
        try:
            if mode == "fiducials":
                fid = with_fiducials(bent)
                p2, _ = simulate_photo(fid, px_per_mm, seed=seed)
                rd = read_card(p2, with_fiducials(design), mode="fiducials")
            else:
                rd = read_card(photo, design, corners_px=true_corners, mode=mode)
        except ValueError as e:
            report["modes"][mode] = {"error": str(e)}
            continue
        cmp = compare(rd, ref)
        report["modes"][mode] = {"ecc": rd["ecc"], "compare": cmp}
        if out is not None:
            out.mkdir(parents=True, exist_ok=True)
            shown = design if mode != "fiducials" else with_fiducials(design)
            ov = overlay(rd["_rectified"], shown, rd)
            cv2.imwrite(str(out / f"overlay_{mode}.jpg"), ov, [cv2.IMWRITE_JPEG_QUALITY, 80])
    if out is not None:
        out.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out / "sim_photo.jpg"), photo, [cv2.IMWRITE_JPEG_QUALITY, 90])
        cv2.imwrite(str(out / "render_reference.png"), render_reference(design))
        (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    for mode, r in report["modes"].items():
        print(f"== {mode} ==")
        if "error" in r:
            print("  ", r["error"])
            continue
        for row in r["compare"]["features"]:
            if row["role"] in ("bar", "square"):
                print(f"  {row['name']:<14} dW {row['d_width_mm']!s:>7} "
                      f"dH {row['d_height_mm']!s:>7} dC {row['d_coverage']!s:>8}")
        print("   seams:", r["compare"]["seam_gap_delta_mm"])
        print("   draft:", {k: v for k, v in r["compare"]["draft_profile_delta"].items() if k != "basis"})


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    ap.add_argument("--photo", type=Path, help="a photo of the sewn card")
    ap.add_argument("--corners", nargs=4, metavar="x,y",
                    help="pixel corners of the sewn bbox: TL TR BR BL")
    ap.add_argument("--mode", choices=("auto", "corners", "fiducials"), default=None)
    ap.add_argument("--ocr", action="store_true", help="read the words with tesseract when present")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--overlay", type=Path, help="write the rectified photo with readings drawn on")
    ap.add_argument("--simulate", action="store_true", help="fake a photo with known distortions and score the reader")
    ap.add_argument("--px-per-mm", type=float, default=12.0, help="simulated phone resolution")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", type=Path, help="--simulate: directory for the photo, overlays and report")
    a = ap.parse_args(argv)

    design = _load_design(a.design)
    if a.simulate:
        _cli_simulate(design, a.px_per_mm, a.out, a.seed)
        return
    if a.photo is None:
        ap.error("--photo or --simulate")
    img = cv2.imread(str(a.photo), cv2.IMREAD_COLOR)
    if img is None:
        raise SystemExit(f"cannot read {a.photo}")
    corners = None
    mode = a.mode or ("corners" if a.corners else "auto")
    if a.corners:
        corners = np.array([[float(v) for v in c.split(",")] for c in a.corners], np.float32)
    rd = read_card(img, design, corners_px=corners, mode=mode, ocr=a.ocr)
    ref = read_reference(design, ocr=a.ocr)
    result = {"photo": _strip(rd), "reference": _strip(ref), "compare": compare(rd, ref)}
    if a.overlay:
        cv2.imwrite(str(a.overlay), overlay(rd["_rectified"], design, rd))
    if a.json:
        a.json.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["compare"], indent=2))


if __name__ == "__main__":
    main()
