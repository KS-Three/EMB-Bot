import sys

import cv2
import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import build_generation

art, out, width = sys.argv[1], sys.argv[2], float(sys.argv[3])
SC = 22
tiles = []
for label, kw, col in (("shipped", {}, (0, 0, 220)), ("coverage_edges=True", {"coverage_edges": True}, (200, 90, 0))):
    gen = build_generation(art, PipelineConfig(target_width_mm=width, **kw))
    p = gen.p
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w_mm, h_mm = (x1 - x0) / p.px_per_mm + 2, (y1 - y0) / p.px_per_mm + 2
    W, H = int(w_mm * SC), int(h_mm * SC)
    a = cv2.resize(p.native_alpha, None, fx=p.upscale[0], fy=p.upscale[1], interpolation=cv2.INTER_NEAREST)
    M = np.float32([[p.px_per_mm / SC, 0, cx - w_mm / 2 * p.px_per_mm], [0, p.px_per_mm / SC, cy - h_mm / 2 * p.px_per_mm]])
    back = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP)
    img = cv2.cvtColor((255 - back // 4).astype(np.uint8), cv2.COLOR_GRAY2BGR)
    for r in gen.regions:
        if r.meta.get("enclosed_background"):
            continue
        for ring in [r.polygon.exterior, *r.polygon.interiors]:
            q = (np.asarray(ring.coords) + [w_mm / 2, h_mm / 2]) * SC * 16
            cv2.polylines(img, [np.round(q).astype(np.int32).reshape(-1, 1, 2)], True, col, 2, cv2.LINE_AA, 4)
    cv2.putText(img, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2, cv2.LINE_AA)
    tiles.append(img)
cv2.imwrite(out, np.vstack(tiles))
