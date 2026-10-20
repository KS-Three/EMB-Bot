"""Render the 10 worst Becker reversal vertices with cv2: source pixels, mask
trace, pre-fit read, final read point (by flag), output polygon.

usage: python render_worst.py SCRATCH WIDTH OUT.png [ARM LABEL]  (after worst_reversals.py SCRATCH WIDTH [CFG])"""
import pickle
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[4] / "digitizer"))
S = Path(sys.argv[1]); w = sys.argv[2]; out = Path(sys.argv[3])
ARM = sys.argv[4] if len(sys.argv) > 4 else "native read ON (today)"
cap = pickle.loads((S / f"becker_{w}.pkl").read_bytes())
d = pickle.load(open(S / f"diag_{w}.pkl", "rb"))
p = cap["p"]
sx, sy = p.upscale
a = p.native_alpha.astype(float) / 255.0
rgb = p.native_rgb.astype(float)
comp = (rgb * a[..., None] + 255.0 * (1 - a[..., None])).clip(0, 255).astype(np.uint8)
comp = cv2.cvtColor(comp, cv2.COLOR_RGB2BGR)
# lighten so the overlay reads
comp = (comp.astype(float) * 0.55 + 255 * 0.45).astype(np.uint8)

K = 44          # screen px per source px
R = 4.5         # half-window, source px
P = int(2 * R * K)
GREEN, ORANGE, MAGENTA, RED, BLUE, CYAN, GREY = (40, 160, 40), (0, 140, 255), (200, 0, 200), (30, 30, 220), (200, 90, 0), (220, 200, 0), (120, 120, 120)


def down(xy):
    xy = np.asarray(xy, float)
    return np.stack([(xy[..., 0] + .5) / sx - .5, (xy[..., 1] + .5) / sy - .5], -1)


picked = []
for rv in d["revs"]:
    at = down(rv["at"])
    if all(np.hypot(*(at - down(q["at"]))) > 1.5 for q in picked):
        picked.append(rv)
    if len(picked) == 10:
        break


def panel(rv):
    at = down(rv["at"])
    ox, oy = at[0] - R, at[1] - R

    def T(xy):
        xy = np.atleast_2d(xy)
        return np.round(np.stack([(xy[:, 0] - ox) * K, (xy[:, 1] - oy) * K], 1)).astype(np.int32)

    img = np.full((P, P, 3), 255, np.uint8)
    for yy in range(int(np.floor(oy)) - 1, int(np.ceil(oy + 2 * R)) + 2):
        for xx in range(int(np.floor(ox)) - 1, int(np.ceil(ox + 2 * R)) + 2):
            if 0 <= yy < comp.shape[0] and 0 <= xx < comp.shape[1]:
                tl = T([xx - .5, yy - .5])[0]
                cv2.rectangle(img, tuple(tl), tuple(tl + K), tuple(int(c) for c in comp[yy, xx]), -1)
                cv2.rectangle(img, tuple(tl), tuple(tl + K), (225, 225, 225), 1)
    for ring in d["rings"]:
        raw, up, pre = down(ring["raw"]), down(ring["up"]), down(ring["pre_up"])
        near = np.hypot(raw[:, 0] - at[0], raw[:, 1] - at[1]) < R * 1.6
        if not near.any():
            continue
        cv2.polylines(img, [T(raw)], True, GREY, 1, cv2.LINE_AA)
        acc, cor, fit = ring["acc"], ring["corner"], ring["fitted"]
        for i in np.flatnonzero(near):
            q = tuple(T(up[i])[0])
            if fit[i]:
                pr = tuple(T(pre[i])[0])
                cv2.line(img, pr, q, RED, 1, cv2.LINE_AA)
                cv2.drawMarker(img, pr, RED, cv2.MARKER_TILTED_CROSS, 7, 1)
                cv2.drawMarker(img, q, RED, cv2.MARKER_TRIANGLE_UP, 11, 2)
            elif cor[i] and not acc[i]:
                cv2.drawMarker(img, q, MAGENTA, cv2.MARKER_SQUARE, 10, 2)
            elif cor[i]:
                cv2.circle(img, q, 5, ORANGE, 2, cv2.LINE_AA)
            elif acc[i]:
                cv2.circle(img, q, 3, GREEN, -1, cv2.LINE_AA)
            else:
                cv2.drawMarker(img, q, GREY, cv2.MARKER_DIAMOND, 7, 1)
    cv2.polylines(img, [T(down(rv["ring"]))], True, BLUE, 2, cv2.LINE_AA)
    cv2.circle(img, tuple(T(at)[0]), 14, CYAN, 2, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (P, 38), (255, 255, 255), -1)
    cv2.putText(img, f"turn {rv['ang']:.0f} deg  src ({at[0]:.1f},{at[1]:.1f})", (6, 15), cv2.FONT_HERSHEY_SIMPLEX, .45, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.putText(img, rv["cat"][4:], (6, 32), cv2.FONT_HERSHEY_SIMPLEX, .42, (0, 0, 0), 1, cv2.LINE_AA)
    cv2.rectangle(img, (0, 0), (P - 1, P - 1), (0, 0, 0), 1)
    return img


tiles = [panel(rv) for rv in picked]
while len(tiles) < 10:
    tiles.append(np.full((P, P, 3), 255, np.uint8))
grid = np.vstack([np.hstack(tiles[:5]), np.hstack(tiles[5:])])
legend = np.full((70, grid.shape[1], 3), 255, np.uint8)
txt = [f"Becker at {p.input_px_per_mm:.2f} px/mm, {ARM}: the 10 worst outline reversals, one per location. Squares = source pixels (alpha over white).",
       "grey dotted: mask trace (pixel centres)   green dot: read point   orange ring: corner placed by its two profile reads   magenta square: unread corner kept at pixel centre",
       "red x -> red triangle: corner moved by the side-line fit (_fit_corners)   blue: output polygon   cyan ring: the reversal vertex"]
for k, t in enumerate(txt):
    cv2.putText(legend, t, (8, 20 + 20 * k), cv2.FONT_HERSHEY_SIMPLEX, .5, (0, 0, 0), 1, cv2.LINE_AA)
cv2.imwrite(str(out), np.vstack([legend, grid]))
print("wrote", out, len(picked))
