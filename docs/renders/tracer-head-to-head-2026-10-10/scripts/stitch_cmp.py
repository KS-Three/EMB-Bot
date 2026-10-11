"""Becker through to stitches, flag off and on: counts by block kind,
warnings, and a drawing of what the needle does."""
import collections
import dataclasses
import sys

import cv2
import numpy as np

from digitizer_core import PipelineConfig, digitize

art, out, width = sys.argv[1], sys.argv[2], float(sys.argv[3])
SC = 22
tiles = []
for label, kw in (("shipped", {}), ("coverage_edges=True", {"coverage_edges": True})):
    result, plan = digitize(art, PipelineConfig(target_width_mm=width, **kw))
    if not tiles:
        print("plan fields:", [f.name for f in dataclasses.fields(plan)])
        print("block fields:", [f.name for f in dataclasses.fields(plan.blocks[0])])
    kinds = collections.Counter()
    npts = collections.Counter()
    allpts = []
    if not tiles:
        r0 = plan.blocks[0].runs[0]
        print("run type:", type(r0).__name__, [f.name for f in dataclasses.fields(r0)] if dataclasses.is_dataclass(r0) else np.asarray(r0).shape)
    for b in plan.blocks:
        for r in b.runs:
            pts = np.asarray(r.points if hasattr(r, "points") else (r.stitches if hasattr(r, "stitches") else r), float)
            k = str(getattr(r, "kind", None) or getattr(r, "tier", None) or getattr(r, "role", "?"))
            kinds[k] += 1; npts[k] += len(pts); allpts.append(pts[:, :2])
    codes = collections.Counter(w.get("code") for w in list(result.warnings) + list(getattr(plan, "warnings", [])))
    P = np.vstack(allpts)
    print(f"{label}: blocks {len(plan.blocks)} stitches {len(P)}  by kind {dict(npts)}  blocks/kind {dict(kinds)}")
    print("   warnings:", dict(codes))
    lo, hi = P.min(0) - 1, P.max(0) + 1
    img = np.full((int((hi[1] - lo[1]) * SC), int((hi[0] - lo[0]) * SC), 3), 255, np.uint8)
    for pts in allpts:
        q = np.round((pts - lo) * SC * 16).astype(np.int32)
        cv2.polylines(img, [q.reshape(-1, 1, 2)], False, (60, 40, 20), 1, cv2.LINE_AA, 4)
    cv2.putText(img, label, (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 200), 2, cv2.LINE_AA)
    tiles.append(img)
w = max(t.shape[1] for t in tiles)
tiles = [cv2.copyMakeBorder(t, 0, 0, 0, w - t.shape[1], cv2.BORDER_CONSTANT, value=(255, 255, 255)) for t in tiles]
cv2.imwrite(out, np.vstack(tiles))
