"""Crops: art (approximate window, mapped by whole-design extents, for LOOKING only) beside a render
of the side's DST in its thread colours. Renders stay in the scratch folder."""
import math
from pathlib import Path
import numpy as np
import cv2
import reader

RPPM = 12.0
BG = (150, 150, 150)


def render(pts, cols, win, hi=None):
    x0, y0, x1, y1 = win
    W, H = int((x1 - x0) * RPPM), int((y1 - y0) * RPPM)
    img = np.full((H, W, 3), BG, np.uint8)
    tw = max(1, int(round(0.4 * RPPM)))
    for bi, b in enumerate(reader.blocks_of(pts)):
        pal = [(30, 30, 30), (240, 240, 240), (220, 50, 50), (50, 80, 220), (40, 170, 60), (240, 200, 0),
               (170, 60, 200), (0, 200, 200), (240, 130, 0), (120, 70, 30), (255, 120, 200)]
        rgb = cols[bi]["rgb"] if cols else pal[bi % len(pal)]
        bgr = (int(rgb[2]), int(rgb[1]), int(rgb[0]))
        for s in reader.segments(b):
            if s is None:
                continue
            a = (int((s[0] - x0) * RPPM), int((s[1] - y0) * RPPM))
            c = (int((s[2] - x0) * RPPM), int((s[3] - y0) * RPPM))
            cv2.line(img, a, c, bgr, tw, cv2.LINE_AA)
    if hi is not None:
        hx0, hy0, hx1, hy1 = hi
        cv2.rectangle(img, (int((hx0 - x0) * RPPM), int((hy0 - y0) * RPPM)),
                      (int((hx1 - x0) * RPPM), int((hy1 - y0) * RPPM)), (0, 255, 255), 1)
    return img


def art_ink_box(img):
    if img.ndim == 3 and img.shape[2] == 4 and img[:, :, 3].min() < 250:
        m = img[:, :, 3] > 20
    else:
        rgb = img[:, :, :3].astype(int)
        corner = np.median(np.concatenate([rgb[0, :], rgb[-1, :], rgb[:, 0], rgb[:, -1]]), axis=0)
        m = np.abs(rgb - corner).sum(axis=2) > 40
    ys, xs = np.nonzero(m)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def art_crop(art_path, design_box, win, size):
    img = cv2.imread(str(art_path), cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    ax0, ay0, ax1, ay1 = art_ink_box(img)
    dx0, dy0, dx1, dy1 = design_box
    sx, sy = (ax1 - ax0) / (dx1 - dx0), (ay1 - ay0) / (dy1 - dy0)
    x0, y0, x1, y1 = win
    px0, py0 = int(ax0 + (x0 - dx0) * sx), int(ay0 + (y0 - dy0) * sy)
    px1, py1 = int(ax0 + (x1 - dx0) * sx), int(ay0 + (y1 - dy0) * sy)
    if img.shape[2] == 4:
        a = img[:, :, 3:4].astype(float) / 255
        img = (img[:, :, :3] * a + np.array(BG[::-1]) * (1 - a)).astype(np.uint8)
    pad = max(0, -px0, -py0, px1 - img.shape[1], py1 - img.shape[0]) + 2
    img = cv2.copyMakeBorder(img, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=BG)
    c = img[py0 + pad:py1 + pad, px0 + pad:px1 + pad]
    if c.size == 0:
        return None
    return cv2.resize(c, size, interpolation=cv2.INTER_CUBIC)


def label(img, text):
    out = cv2.copyMakeBorder(img, 22, 0, 0, 0, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    cv2.putText(out, text, (4, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return out


def sheet(path, pts, cols, art, piece_box, title, pad=4.0, min_mm=14.0):
    xs = [p[0] for p in pts if p[2] == "S"]; ys = [p[1] for p in pts if p[2] == "S"]
    design_box = (min(xs), min(ys), max(xs), max(ys))
    bx0, by0, bx1, by1 = piece_box
    cx, cy = (bx0 + bx1) / 2, (by0 + by1) / 2
    hw = max((bx1 - bx0) / 2 + pad, min_mm / 2); hh = max((by1 - by0) / 2 + pad, min_mm / 2)
    win = (cx - hw, cy - hh, cx + hw, cy + hh)
    st = render(pts, cols, win, hi=piece_box)
    tiles = [label(st, title)]
    if art is not None:
        a = art_crop(art, design_box, win, (st.shape[1], st.shape[0]))
        if a is not None:
            tiles.insert(0, label(a, "art (approx. window)"))
    h = max(t.shape[0] for t in tiles)
    tiles = [cv2.copyMakeBorder(t, 0, h - t.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
    cv2.imwrite(str(path), np.hstack(tiles))
