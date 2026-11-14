"""Subject edge recall: how much of the artwork's strong-edge detail the sewn
result still draws. A preflight METRIC only (`subject_edge_recall`), never a
finding and never in the grade (Kent 2026-10-02: no warning reaches the
customer without his word).

Why it exists: build walkthrough 2026-11-13, item 2 -- the toadstool photo
lost its spotted cap's companion and its stem to a flat olive blob and
preflight still said B 76. Measured 2026-11-14 over the 39-row Commons corpus
against Kent's grades of the same renders (`docs/subject-loss-2026-11-14.md`,
`tools/subject_detail.py`): rows he ticked "detail lost" or "can't tell what
it is" read lower than rows he graded Good/Great, Somers' D +0.88
[+0.63, +1.00] (13 vs 5). Every Good row is flat art, and "the class is not
flat" alone reads +0.77, so it is NOT shown to measure more than photo-ness;
no threshold, no finding until a sitting grades photos Good.

The sewn picture is a thread map: every needle-down run drawn 0.45 mm wide in
its thread colour, in sew order, on the garment colour, on stage 1's re-read
grid (capped at WORK_PX_PER_MM), mapped exactly as `preflight.
_uncovered_findings` maps plan millimetres. Both pictures go to CIE Lab and
are smoothed (sigma 0.3 mm). A strong edge is a CIE76 step of EDGE_DE or more
across 1 mm inside the artwork (`~bg_mask`, 1 mm in from the border); recall
is the share of the artwork's strong edges with a strong thread-map edge
within MATCH_MM. None when the artwork has no strong edge.
"""
from __future__ import annotations

import cv2
import numpy as np

EDGE_DE = 15.0        # CIE76 step across EDGE_SPAN_MM that counts as a strong edge
EDGE_SPAN_MM = 1.0
MATCH_MM = 1.0        # a source edge is kept if the thread map has one this close
SMOOTH_MM = 0.3       # Gaussian sigma for both pictures
THREAD_W_MM = 0.45    # drawn width of one needle-down run
BORDER_MM = 1.0       # edges this close to the raster border are ignored
WORK_PX_PER_MM = 8.0  # both pictures are read on at most this grid
DEFAULT_GARMENT_RGB = (235, 232, 223)   # the Studio's Natural garment


class Grid:
    """The four fields of a Prep this module reads, resampled to at most
    WORK_PX_PER_MM (every constant is in millimetres, so the grid is free)."""

    def __init__(self, p):
        f = min(1.0, WORK_PX_PER_MM / float(p.px_per_mm))
        h, w = np.asarray(p.bg_mask).shape
        size = (max(1, int(round(w * f))), max(1, int(round(h * f))))
        self.rgb = p.rgb if f == 1.0 else cv2.resize(p.rgb, size, interpolation=cv2.INTER_AREA)
        bg = np.asarray(p.bg_mask, np.uint8)
        self.bg_mask = (bg if f == 1.0 else cv2.resize(bg, size, interpolation=cv2.INTER_NEAREST)) > 0
        self.art_bbox = tuple(v * f for v in p.art_bbox)
        self.px_per_mm = float(p.px_per_mm) * f


def lab(rgb: np.ndarray, sigma_px: float) -> np.ndarray:
    f = rgb.astype(np.float32) / 255.0
    if sigma_px > 0:
        f = cv2.GaussianBlur(f, (0, 0), sigma_px)
    return cv2.cvtColor(f, cv2.COLOR_RGB2LAB)


def edge_strength(lab_img: np.ndarray, half_px: int) -> np.ndarray:
    """Largest CIE76 step across 2*half_px pixels, over 4 directions."""
    d = max(1, half_px)
    pad = cv2.copyMakeBorder(lab_img, d, d, d, d, cv2.BORDER_REPLICATE)
    h, w = lab_img.shape[:2]
    best = np.zeros((h, w), np.float32)
    for dy, dx in ((0, 1), (1, 0), (1, 1), (1, -1)):
        a = pad[d + dy * d: d + dy * d + h, d + dx * d: d + dx * d + w]
        b = pad[d - dy * d: d - dy * d + h, d - dx * d: d - dx * d + w]
        best = np.maximum(best, np.sqrt(((a - b) ** 2).sum(axis=2)))
    return best


def thread_map(p, segments, garment_rgb) -> np.ndarray:
    """`segments`: [(rgb, Nx2 plan-mm points)] in sew order -> RGB raster on
    `p`'s grid."""
    h, w = p.bg_mask.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out = np.empty((h, w, 3), np.uint8)
    out[:] = np.array(garment_rgb, np.uint8)
    th = max(1, int(round(THREAD_W_MM * p.px_per_mm)))
    for rgb, pts in segments:
        a = np.asarray(pts, np.float64)
        if len(a) < 2:
            continue
        px = np.column_stack([a[:, 0] * p.px_per_mm + cx, a[:, 1] * p.px_per_mm + cy])
        cv2.polylines(out, [np.round(px).astype(np.int32)], False,
                      tuple(int(c) for c in rgb), th, lineType=cv2.LINE_8)
    return out


def plan_segments(plan) -> list:
    """[(rgb, points mm)] from a StitchPlan, sew order, needle-down runs only."""
    return [(tuple(block.rgb), run.points) for block, run in plan.iter_runs()]


class Pictures:
    """Source and thread map on one grid, in smoothed Lab, plus the artwork
    area the readings judge."""

    def __init__(self, p, segments, garment_rgb):
        g = Grid(p)
        self.grid = g
        ppm = g.px_per_mm
        art = ~np.asarray(g.bg_mask, bool)
        b = max(1, int(round(BORDER_MM * ppm)))
        inner = np.zeros_like(art)
        inner[b:-b, b:-b] = True
        self.area = art & inner
        sigma = SMOOTH_MM * ppm
        self.src = lab(g.rgb, sigma)
        self.sew = lab(thread_map(g, segments, garment_rgb or DEFAULT_GARMENT_RGB), sigma)


def edge_readings(pic: Pictures) -> dict:
    """-> {edge_recall, edge_density, strong_px}; recall None without a strong edge."""
    ppm = pic.grid.px_per_mm
    n_area = int(pic.area.sum())
    if n_area == 0:
        return {"edge_recall": None, "edge_density": None, "strong_px": 0}
    half = int(round(EDGE_SPAN_MM * ppm / 2.0))
    strong_s = (edge_strength(pic.src, half) >= EDGE_DE) & pic.area
    strong_t = edge_strength(pic.sew, half) >= EDGE_DE
    r = max(1, int(round(MATCH_MM * ppm)))
    near_t = cv2.dilate(strong_t.astype(np.uint8),
                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))) > 0
    n_strong = int(strong_s.sum())
    return {"edge_recall": round(float((near_t & strong_s).sum() / n_strong), 4) if n_strong else None,
            "edge_density": round(n_strong / n_area, 5), "strong_px": n_strong}


def metrics(p, plan, cfg) -> dict:
    """The preflight metric: `subject_edge_recall`."""
    pic = Pictures(p, plan_segments(plan), getattr(cfg, "garment_rgb", None))
    return {"subject_edge_recall": edge_readings(pic)["edge_recall"]}
