"""Per-letter sheets for Kent: artwork / traced polygon / refit polygon /
the pro's outline where one exists, one row per letter, all at one scale.
No verdict is drawn on them -- the eye is his.

Panels, left to right:
  1. the source pixels (nearest-neighbour, so each pixel shows)
  2. the traced polygon (stage 4, today) in red over the faded artwork
  3. the refit: traced in grey beneath, lines blue, arcs orange,
     pass-through pieces (unexplained residue) grey, corners as dots;
     a refused letter shows its reason instead
  4. the pro's sewn outline (green) over the faded artwork, when given
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

PX_PER_MM = 18
PAD_MM = 1.5
MAX_PANEL_PX = 720
MIN_PANEL_PX = 260
GUTTER = 8
LABEL_H = 22


def art_mapping(d: dict):
    """mm (design frame, origin at the art box centre, y down) -> source px."""
    iw, ih = d["image_size"]
    fx = d.get("art_box_frac") or (0.0, 0.0, 1.0, 1.0)
    span_x = (fx[2] - fx[0]) * iw
    span_y = (fx[3] - fx[1]) * ih
    w_mm, h_mm = d["design_size_mm"]
    sx = span_x / w_mm
    sy = span_y / h_mm if h_mm else sx
    cx = (fx[0] + fx[2]) / 2 * iw
    cy = (fx[1] + fx[3]) / 2 * ih
    return lambda x, y: (cx + x * sx, cy + y * sy), (sx + sy) / 2


def load_art(path: Path) -> np.ndarray:
    im = Image.open(path).convert("RGBA")
    a = np.asarray(im).astype(np.float32)
    rgb, alpha = a[..., :3], a[..., 3:4] / 255.0
    out = rgb * alpha + 255.0 * (1 - alpha)
    return out.astype(np.uint8)[..., ::-1].copy()          # BGR for cv2


def _ring_px(coords, x0, y0, s) -> np.ndarray:
    P = np.asarray(coords, float)
    return np.round((P - (x0, y0)) * s).astype(np.int32)


def _panel_art(art: np.ndarray, mapping, box, s: float, fade: float = 1.0) -> np.ndarray:
    x0, y0, x1, y1 = box
    W, H = int(round((x1 - x0) * s)), int(round((y1 - y0) * s))
    # source px corners
    px0, py0 = mapping(x0, y0)
    px1, py1 = mapping(x1, y1)
    # sample the artwork with nearest neighbour onto the panel grid
    xs = np.linspace(px0, px1, W, endpoint=False)
    ys = np.linspace(py0, py1, H, endpoint=False)
    xi = np.clip(np.floor(xs).astype(int), 0, art.shape[1] - 1)
    yi = np.clip(np.floor(ys).astype(int), 0, art.shape[0] - 1)
    panel = art[yi][:, xi].copy()
    if fade < 1.0:
        panel = (panel.astype(np.float32) * fade + 255.0 * (1 - fade)).astype(np.uint8)
    return panel


def _draw_poly(panel, poly, x0, y0, s, colour, thick=2):
    for ring in [poly.exterior, *poly.interiors]:
        cv2.polylines(panel, [_ring_px(ring.coords, x0, y0, s)], True, colour, thick, cv2.LINE_AA)


def _draw_prims(panel, row, x0, y0, s):
    """The refit's primitives in the world frame."""
    from fit import arc_points, frame_axes, from_frame
    u, v = frame_axes(row.prior.line_deg)
    for rf in row.fit.rings:
        for p in rf.prims:
            if p.kind == "line":
                pts = from_frame(np.array([p.p0, p.p1]), u, v)
                col = (200, 90, 20)
            elif p.kind == "arc":
                pts = from_frame(arc_points(p.c, p.r, p.a0, p.a1, p.ccw), u, v)
                col = (20, 140, 240)
            else:
                continue
            cv2.polylines(panel, [_ring_px(pts, x0, y0, s)], False, col, 2, cv2.LINE_AA)
        # pass-through pieces: the rebuilt ring is drawn beneath in grey anyway
    for ring in [row.refit.exterior, *row.refit.interiors]:
        for q in _ring_px(ring.coords, x0, y0, s):
            cv2.circle(panel, tuple(int(t) for t in q), 2, (40, 40, 40), -1, cv2.LINE_AA)


def _label(panel, text):
    bar = np.full((LABEL_H, panel.shape[1], 3), 235, np.uint8)
    cv2.putText(bar, text, (4, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([bar, panel])


def letter_row(d: dict, art: np.ndarray, row, pro_poly=None, px_per_mm: float = PX_PER_MM) -> np.ndarray:
    mapping, _src_s = art_mapping(d)
    b = row.traced.bounds
    if pro_poly is not None and not pro_poly.is_empty:
        pb = pro_poly.bounds
        b = (min(b[0], pb[0]), min(b[1], pb[1]), max(b[2], pb[2]), max(b[3], pb[3]))
    box = (b[0] - PAD_MM, b[1] - PAD_MM, b[2] + PAD_MM, b[3] + PAD_MM)
    s = px_per_mm
    big = max(box[2] - box[0], box[3] - box[1]) * s
    if big > MAX_PANEL_PX:
        s = MAX_PANEL_PX / max(box[2] - box[0], box[3] - box[1])
    elif big < MIN_PANEL_PX:                     # a 5 mm letter still gets a panel to judge
        s = MIN_PANEL_PX / max(box[2] - box[0], box[3] - box[1])
    x0, y0 = box[0], box[1]
    f = row.fit
    panels = []
    panels.append(_label(_panel_art(art, mapping, box, s), f"{row.char or '?'} {row.shape_id} artwork"))
    p2 = _panel_art(art, mapping, box, s, fade=0.35)
    _draw_poly(p2, row.traced, x0, y0, s, (30, 30, 220))
    for ring in [row.traced.exterior, *row.traced.interiors]:
        for q in _ring_px(ring.coords, x0, y0, s):
            cv2.circle(p2, tuple(int(t) for t in q), 2, (30, 30, 220), -1, cv2.LINE_AA)
    panels.append(_label(p2, f"traced  {len(row.traced.exterior.coords) - 1} verts"))
    p3 = _panel_art(art, mapping, box, s, fade=0.35)
    _draw_poly(p3, row.traced, x0, y0, s, (170, 170, 170), 1)
    if f.status == "refit":
        _draw_prims(p3, row, x0, y0, s)
        txt = f"refit  L{f.n_line} A{f.n_arc} P{f.n_pass}  max move {f.moved_max_mm:.2f} mm (cap {row.prior.tol_mm:.2f})"
    elif f.status == "pass":
        txt = f"untouched: {f.reason} (cap {row.prior.tol_mm:.2f} < grid {row.prior.grid_px_mm:.3f} mm)"
    else:
        # the attempt it refused, in magenta, so the refusal can be judged too
        if f.rings:
            from fit import frame_axes, from_frame
            u, v = frame_axes(row.prior.line_deg)
            for rf in f.rings:
                cv2.polylines(p3, [_ring_px(from_frame(rf.coords, u, v), x0, y0, s)], True,
                              (200, 40, 200), 1, cv2.LINE_AA)
        txt = f"REFUSED: {f.reason}  (max move {f.moved_max_mm:.2f}, unexplained {f.unexplained_share:.0%})"
    panels.append(_label(p3, txt))
    if pro_poly is not None:
        p4 = _panel_art(art, mapping, box, s, fade=0.35)
        if not pro_poly.is_empty:
            geoms = getattr(pro_poly, "geoms", [pro_poly])
            for g in geoms:
                _draw_poly(p4, g, x0, y0, s, (40, 160, 40))
        panels.append(_label(p4, "pro (sewn outline, registered)"))
    H = max(p.shape[0] for p in panels)
    out = []
    for p in panels:
        if p.shape[0] < H:
            p = np.vstack([p, np.full((H - p.shape[0], p.shape[1], 3), 255, np.uint8)])
        out.append(p)
        out.append(np.full((H, GUTTER, 3), 255, np.uint8))
    return np.hstack(out)


def letter_sheet(d: dict, art_path: Path, rows, out_path: Path, pro: dict | None = None,
                 px_per_mm: float = PX_PER_MM, title: str | None = None) -> Path:
    art = load_art(art_path)
    strips = []
    for row in rows:
        pro_poly = (pro or {}).get(row.shape_id) if pro is not None else None
        strips.append(letter_row(d, art, row, pro_poly, px_per_mm))
        strips.append(np.full((GUTTER, strips[-1].shape[1], 3), 255, np.uint8))
    W = max(s.shape[1] for s in strips)
    strips = [np.hstack([s, np.full((s.shape[0], W - s.shape[1], 3), 255, np.uint8)]) if s.shape[1] < W else s
              for s in strips]
    sheet = np.vstack(strips)
    if title:
        bar = np.full((28, W, 3), 215, np.uint8)
        cv2.putText(bar, title, (6, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (20, 20, 20), 1, cv2.LINE_AA)
        sheet = np.vstack([bar, sheet])
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out_path), sheet)
    return out_path
