"""One letter's satin stitches, arms side by side, over its traced polygon:
satin penetrations and legs (green), travel (orange), the polygon (black),
and the polygon's ink more than the thread half-width (0.2 mm) from any
satin leg (red). The caption carries that bare area and the stitch count.

usage (cwd digitizer/): python render_letter.py DIR fx sid out.png [arms] [px_per_mm]
Reads DIR/<fx>-<arm>.design.json and DIR/<fx>-on.json (from run_arms.py).
"""
import json
import sys

import cv2
import numpy as np
from shapely import wkt

d, fx, sid, out = sys.argv[1:5]
arms = (sys.argv[5] if len(sys.argv) > 5 else "off,before,after").split(",")
S = float(sys.argv[6]) if len(sys.argv) > 6 else 40.0
poly = wkt.loads(json.load(open(f"{d}/{fx}-on.json"))["letters"][sid]["wkt"])
x0, y0, x1, y1 = poly.bounds
x0, y0, x1, y1 = x0 - 0.8, y0 - 0.8, x1 + 0.8, y1 + 0.8
W, H = int((x1 - x0) * S), int((y1 - y0) * S) + 30
px = lambda p: (int(round((p[0] - x0) * S)), int(round((p[1] - y0) * S)) + 30)
NAMES = {"off": "shipped (lane OFF)", "before": "lane ON, main", "after": "lane ON, this PR"}
panels = []
for arm in arms:
    D = json.load(open(f"{d}/{fx}-{arm}.design.json"))
    st = D["stitches"]
    img = np.full((H, W, 3), 255, np.uint8)
    ink = np.zeros((H, W), np.uint8)
    cv2.fillPoly(ink, [np.array([px(c) for c in poly.exterior.coords], np.int32)], 1)
    for h in poly.interiors:
        cv2.fillPoly(ink, [np.array([px(c) for c in h.coords], np.int32)], 0)
    thr = np.zeros((H, W), np.uint8)
    n = 0
    legs = []
    for r in D["runs"]:
        if r.get("shape") != sid:
            continue
        prev = None
        for i in range(r["i0"], r["i1"] + 1):
            s = st[i]
            if s.get("type") != "stitch":
                prev = None
                continue
            n += 1
            p = px((s["x"] / 10.0, -s["y"] / 10.0))
            if prev is not None:
                legs.append((prev, p, r.get("kind")))
                cv2.line(thr, prev, p, 1, max(1, int(round(0.4 * S))))
            prev = p
    img[ink > 0] = (225, 225, 225)
    img[(ink > 0) & (thr == 0)] = (40, 40, 230)
    for p, q, k in legs:
        cv2.line(img, p, q, (40, 140, 40) if k == "satin" else (0, 140, 230), 1)
    cv2.polylines(img, [np.array([px(c) for c in poly.exterior.coords], np.int32)], True, (0, 0, 0), 1)
    for h in poly.interiors:
        cv2.polylines(img, [np.array([px(c) for c in h.coords], np.int32)], True, (0, 0, 0), 1)
    bare = float(((ink > 0) & (thr == 0)).sum()) / S / S
    cv2.putText(img, f"{NAMES.get(arm, arm)}: bare {bare:.2f} mm2, {n} st", (6, 20),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
    print(arm, round(bare, 2), n)
    panels += [img, np.full((H, 6, 3), 80, np.uint8)]
cv2.imwrite(out, np.hstack(panels[:-1]))
