"""Becker-shaped input with a known answer: one colour, shape in alpha only.
Takes the truth run's layer with the most boundary, writes it at native
resolution as a single-colour RGBA PNG (hard alpha; the INTER_AREA downscale
in capture.py then leaves the coverage ramp a real low-res export has)."""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

src, out = Path(sys.argv[1]), Path(sys.argv[2])
meta = json.loads((src / "meta.json").read_text())
lab = np.load(src / "labels.npy")
layer_of = np.zeros(lab.max() + 1, np.int32) - 1
for m in meta["masks"]:
    layer_of[m["i"] + 1] = m["layer"]
lay = layer_of[lab]
best, score = None, -1
for L in np.unique(lay[lay >= 0]):
    m = lay == L
    edge = (m[:, 1:] != m[:, :-1]).sum() + (m[1:, :] != m[:-1, :]).sum()
    if edge > score:
        best, score = L, edge
m = lay == best
img = np.zeros((*m.shape, 4), np.uint8)
img[..., :3] = (120, 40, 20)
img[..., 3] = m * 255
cv2.imwrite(str(out), img)
print(out.name, "layer", int(best), "boundary px", int(score), "area share %.3f" % m.mean())
