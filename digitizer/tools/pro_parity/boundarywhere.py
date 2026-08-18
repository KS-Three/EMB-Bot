"""WHERE is the boundary error? Attribution probe for enginefidelity outliers.

enginefidelity.py reports one Hausdorff number per design; several designs sit
at 17-24 mm worst-point distance while their IoU is 0.93+. This probe answers
the only question that matters about such a pair: where are those far points,
and which side owns them — art ink the engine never covered (unsewn element,
enclosed background), or engine cover the art never asked for (displaced or
invented geometry)?

Per design it writes `boundarywhere_<slug>.png` next to the design dir's own
files: art-only outline in green, engine-only in red, coincident pixels in
near-black, and the worst-distance boundary pixels circled — blue circles for
art-side points far from any engine boundary ("engine missed this"), magenta
for engine-side points far from any art boundary ("engine added this"). Plus
a text summary of the top clusters and which side they belong to.

Two things this probe does NOT tell you. The printed cluster coordinates are
in the padded shift-search frame, not design mm — use them to find the spot
on the emitted PNG, never as a design coordinate. And a same-colour outline
pair says nothing about whether the artwork's ink was readable in the first
place: `art_mask` thresholds dark-on-light, so light ink on a dark ground
reads as solid and the engine gets charged for correctly leaving it unsewn.

Usage:
    python boundarywhere.py <OUT>/real/<slug> [...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artfidelity import RES, SHIFT_MM, art_mask, best_iou  # noqa: E402
from enginefidelity import _boundary, _place, engine_mask  # noqa: E402

TOP_K = 4          # worst clusters to report per side
CLUSTER_MM = 5.0   # points closer than this are one cluster


def _far_points(src_b, dst_b):
    """(dist_px, y, x) for every src boundary pixel, sorted far-first."""
    dt = cv2.distanceTransform((~dst_b).astype(np.uint8), cv2.DIST_L2,
                               cv2.DIST_MASK_PRECISE)
    ys, xs = np.nonzero(src_b)
    d = dt[ys, xs]
    order = np.argsort(-d)
    return [(float(d[i]), int(ys[i]), int(xs[i])) for i in order]


def _clusters(pts, k=TOP_K, r_px=CLUSTER_MM * RES):
    out = []
    for d, y, x in pts:
        if d <= 0:
            break
        if any((y - cy) ** 2 + (x - cx) ** 2 <= r_px ** 2 for _, cy, cx in out):
            continue
        out.append((d, y, x))
        if len(out) == k:
            break
    return out


def probe(design_dir):
    d = Path(design_dir)
    E = engine_mask(d / "ours_stitches.csv")
    A = art_mask(d / "art.png", E.shape[1] / RES)
    iou, _, _, dx_mm, dy_mm = best_iou(E, A)
    H = max(E.shape[0], A.shape[0]) + int(2 * SHIFT_MM * RES) + 4
    W = max(E.shape[1], A.shape[1]) + int(2 * SHIFT_MM * RES) + 4
    Ep = _place(E, H, W)
    Ap = _place(A, H, W, int(round(dx_mm * RES)), int(round(dy_mm * RES)))
    be, ba = _boundary(Ep), _boundary(Ap)

    art_far = _clusters(_far_points(ba, be))    # art ink far from engine cover
    eng_far = _clusters(_far_points(be, ba))    # engine cover far from art ink

    # Draw order matters and used to lie. Painting art green then engine red
    # let red overwrite every coincident pixel — on hotel_fremont_hat that is
    # 836 of 2862 art-boundary pixels (29.2%), which made "the art outline is
    # only at the outer border" readable off the render when 43.9% of it is
    # interior. Coincident pixels now get their own colour instead.
    vis = np.full((H, W, 3), 255, np.uint8)
    both = ba & be
    vis[ba] = (0, 160, 0)      # art only: green
    vis[be] = (0, 0, 220)      # engine only: red (BGR)
    vis[both] = (40, 40, 40)   # both agree: near-black
    for dist, y, x in art_far:
        cv2.circle(vis, (x, y), int(2.0 * RES), (200, 80, 0), 2)   # blue-ish
    for dist, y, x in eng_far:
        cv2.circle(vis, (x, y), int(2.0 * RES), (200, 0, 200), 2)  # magenta
    out_png = d / f"boundarywhere_{d.name}.png"
    cv2.imwrite(str(out_png), vis)

    print(f"\n== {d.name}  iou {iou:.3f}  shift {dx_mm:.1f},{dy_mm:.1f} mm")
    for label, side in (("ART far from ENGINE (engine missed)", art_far),
                        ("ENGINE far from ART (engine added)", eng_far)):
        print(f"  {label}:")
        for dist, y, x in side:
            print(f"    {dist / RES:6.1f} mm at ({x / RES:.0f},{y / RES:.0f}) mm")
    print(f"  -> {out_png.name}")


def main():
    for a in sys.argv[1:]:
        p = Path(a)
        if (p / "ours_stitches.csv").exists() and (p / "art.png").exists():
            probe(p)


if __name__ == "__main__":
    main()
