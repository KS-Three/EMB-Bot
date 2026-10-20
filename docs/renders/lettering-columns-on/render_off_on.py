"""Thread renders of one fixture with the Column lane OFF and ON (the new
default), same size, same scale, plus a zoom panel on a lettering shape where
the detail is under 1 mm.

usage (cwd digitizer/): python ../docs/renders/lettering-columns-on/render_off_on.py fixture width OUT.png [zoom_index]

Layout: top row the whole design (OFF | ON) at 14 px/mm; bottom row the same
2nd-largest lettering shape (0-based `zoom_index` picks another) at 60 px/mm
with a 1 mm scale bar. The renderer is `digitizer_core.stitchviz.render_design`
(the thread render, not a vector proof). OFF is `lettering_columns=False`;
ON is the shipped default (`lettering_words` OFF in both).
"""
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.getcwd())
from digitizer_core.columns import is_lettering  # noqa: E402
from digitizer_core.stitchviz import _frame, render_design  # noqa: E402
from tools.eye_pairs.features import base_cfg, digitize_once  # noqa: E402
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402

fx, width, out = sys.argv[1], float(sys.argv[2]), sys.argv[3]
zi = int(sys.argv[4]) if len(sys.argv) > 4 else 1
rel, _w, garment = REAL_ART[fx]
image = ROOT / "testdata" / rel
FULL, ZOOM = 14.0, 60.0
PAD = 2.0


def run(**kw):
    cfg = base_cfg(width, garment, **kw)
    _g, result, _p, design = digitize_once(image, cfg)
    return cfg, result, design


cfg_off, res_off, d_off = run(lettering_columns=False)
cfg_on, res_on, d_on = run()
assert cfg_off.lettering_columns is False and cfg_on.lettering_columns is True

letters = sorted((r for r in res_on.regions if is_lettering(r, cfg_on)),
                 key=lambda r: -r.polygon.area)
zi = min(zi, len(letters) - 1)
x0, y0, x1, y1 = letters[zi].polygon.bounds
cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
half = max(max(x1 - x0, y1 - y0) / 2 + 1.0, 4.0)


def label(img, text):
    bar = np.full((34, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, text, (8, 23), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def panels(design):
    st = design["stitches"]
    full = render_design(design, FULL, pad_mm=PAD)
    big = render_design(design, ZOOM, pad_mm=PAD)
    _hw, to_px = _frame(st, ZOOM, PAD)
    # polygon mm frame -> design units: x = 10 X, y = -10 Y (see stage7/adapter)
    pa = to_px({"x": 10 * (cx - half), "y": -10 * (cy - half)})
    pb = to_px({"x": 10 * (cx + half), "y": -10 * (cy + half)})
    xa, xb = sorted((pa[0], pb[0]))
    ya, yb = sorted((pa[1], pb[1]))
    crop = big[max(0, ya):yb, max(0, xa):xb].copy()
    # 1 mm scale bar
    cv2.line(crop, (10, crop.shape[0] - 12), (10 + int(ZOOM), crop.shape[0] - 12), (0, 0, 0), 3)
    cv2.putText(crop, "1 mm", (10, crop.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)
    return full, crop


def n(d, k):
    return sum(1 for s in d["stitches"] if s["type"] == k)


def info(d):
    return f"{n(d, 'stitch')} st, {n(d, 'trim')} trims, {n(d, 'color')} colour changes"


f_off, z_off = panels(d_off)
f_on, z_on = panels(d_on)
H = max(f_off.shape[0], f_on.shape[0])
W = max(f_off.shape[1], f_on.shape[1])
pad = lambda im, h, w: cv2.copyMakeBorder(im, 0, h - im.shape[0], 0, w - im.shape[1],
                                          cv2.BORDER_CONSTANT, value=(255, 255, 255))
top = np.hstack([label(pad(f_off, H, W), f"{fx} {width:g} mm  lettering_columns OFF (before): {info(d_off)}"),
                 np.full((H + 34, 8, 3), 80, np.uint8),
                 label(pad(f_on, H, W), f"{fx} {width:g} mm  lettering_columns ON (default now): {info(d_on)}")])
ZH = max(z_off.shape[0], z_on.shape[0])
ZW = max(z_off.shape[1], z_on.shape[1])
bot = np.hstack([label(pad(z_off, ZH, ZW), f"zoom, letter {letters[zi].shape_id}, 60 px/mm: OFF"),
                 np.full((ZH + 34, 8, 3), 80, np.uint8),
                 label(pad(z_on, ZH, ZW), "same crop: ON")])
w = max(top.shape[1], bot.shape[1])
img = np.vstack([cv2.copyMakeBorder(top, 0, 0, 0, w - top.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)),
                 np.full((8, w, 3), 80, np.uint8),
                 cv2.copyMakeBorder(bot, 0, 0, 0, w - bot.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255))])
cv2.imwrite(out, img)
print(out, img.shape, info(d_off), "|", info(d_on), "| zoom letter", letters[zi].shape_id)
