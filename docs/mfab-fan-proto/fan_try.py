"""Try fan_satin on a corpus design's small enclosed counters; draw ours-fan beside the pro.
argv: corpus_dir name out.png [max_cross]"""
import math
import pickle
import sys
from pathlib import Path

corpus, name, outp = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
maxc = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
sys.path.insert(0, str(Path(__file__).parent))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

from fan_proto import fan_satin, wedge  # noqa: E402

cap = pickle.load(open(corpus / "off" / f"{name}.pkl", "rb"))
cands = []
for poly, ti, sid, meta in cap["regions"]:
    if poly.geom_type != "Polygon" or not (4.0 <= poly.area <= 60.0) or not meta.get("enclosed_background"):
        continue
    t = wedge(poly)
    if t is None or t[0] in (t[1], t[2]):
        continue
    cands.append((sid, poly, meta, t))
print(name, "three-sided shapes 4-60 mm2:", len(cands))
tiles = []
for sid, poly, meta, t in cands[:12]:
    r = fan_satin(poly, max_cross_mm=maxc)
    b = poly.bounds
    cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    half = max(b[2] - b[0], b[3] - b[1]) / 2 + 1.0
    S = 300 / (2 * half)
    img = np.full((300, 300, 3), (40, 40, 40), np.uint8)

    def px(p):
        return (int(round((p[0] - cx + half) * S)), int(round((p[1] - cy + half) * S)))
    cv2.polylines(img, [np.array([px(p) for p in poly.exterior.coords], np.int32)], True, (0, 200, 255), 1)
    info = "no fan"
    if r is not None:
        under, sat, info = r
        for a, c in zip(under[:-1], under[1:]):
            cv2.line(img, px(a), px(c), (0, 140, 255), 1, cv2.LINE_AA)
        w = max(1, int(0.38 * S))
        for a, c in zip(sat[:-1], sat[1:]):
            cv2.line(img, px(a), px(c), (120, 120, 120), w + 2, cv2.LINE_AA)
            cv2.line(img, px(a), px(c), (240, 240, 240), w, cv2.LINE_AA)
    cv2.putText(img, f"{sid} {poly.area:.1f}mm2 {info}"[:60], (3, 12), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (0, 255, 255), 1)
    print(" ", sid, round(poly.area, 1), "ti", ti, {k: meta.get(k) for k in ("enclosed_background", "text_cluster_id") if k in meta}, info)
    tiles.append(img)
if tiles:
    rows = [np.hstack(tiles[i:i + 4] + [np.zeros_like(tiles[0])] * (4 - len(tiles[i:i + 4]))) for i in range(0, len(tiles), 4)]
    cv2.imwrite(str(outp), np.vstack(rows))
