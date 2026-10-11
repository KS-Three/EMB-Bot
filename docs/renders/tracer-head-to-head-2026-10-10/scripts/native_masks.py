"""For every run dir: bring the work-grid label map back down to the
source's own pixel grid (nearest) and dump one padded PNG per label under
masks_native/, so a tracer can be tried on 1-px stairs instead of the
upscaled ones. Writes native.json with the per-axis scale and origins."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

PAD = 2

for d in map(Path, sys.argv[1:]):
    meta = json.loads((d / "meta.json").read_text())
    labels = np.load(d / "labels.npy")
    H, W = labels.shape
    ux, uy = meta["upscale"]
    out = d / "masks_native"
    out.mkdir(exist_ok=True)
    if max(ux, uy) < 1.05:
        (d / "native.json").write_text(json.dumps({"skip": True}))
        continue
    Wn, Hn = int(round(W / ux)), int(round(H / uy))
    small = cv2.resize(labels.astype(np.float32), (Wn, Hn), interpolation=cv2.INTER_NEAREST).astype(np.int32)
    items = []
    for lab in np.unique(small):
        if lab == 0:
            continue
        ys, xs = np.nonzero(small == lab)
        y0, x0, y1, x1 = ys.min(), xs.min(), ys.max() + 1, xs.max() + 1
        pad = np.full((y1 - y0 + 2 * PAD, x1 - x0 + 2 * PAD), 255, np.uint8)
        pad[PAD:-PAD, PAD:-PAD][small[y0:y1, x0:x1] == lab] = 0
        cv2.imwrite(str(out / f"m{lab - 1:04d}.png"), pad)
        items.append({"i": int(lab - 1), "y0": int(y0), "x0": int(x0)})
    (d / "native.json").write_text(json.dumps(
        {"skip": False, "sx": W / Wn, "sy": H / Hn, "masks": items}))
    print(d.name, f"{W}x{H} -> {Wn}x{Hn}", len(items), "labels")
