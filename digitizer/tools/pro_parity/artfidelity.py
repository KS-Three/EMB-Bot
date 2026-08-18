"""How faithfully did the PRO reproduce the customer's artwork?

`scorecard.py` grades EMB-Bot on similarity to the pro's stitches. That is only
a fair proxy for digitizing quality if the pro's stitches are themselves a
faithful rendering of the artwork. Where a pro RE-COMPOSED the logo — filled
letters the art drew as outlines, moved a tagline closer, dropped detail too
small to sew, changed proportions to fit a cap front — an engine that
reproduces the artwork correctly is penalised for it, and no amount of engine
work can recover those points.

This instrument measures that ceiling. For each design it rasterises the
customer artwork's ink at the pro's own physical size and compares it to the
pro's stitch coverage:

    art_iou    - intersection over union, best shift within +/- SHIFT_MM
    pro_extra  - fraction of pro coverage that the artwork does not ask for
    art_missed - fraction of artwork ink the pro left unsewn

A low `art_iou` with high `pro_extra` is the signature of the pro filling what
the art outlined. High `art_missed` is the pro dropping detail.

Usage:
    python artfidelity.py <OUT>/real/<slug> [...]
"""
import csv
import sys
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

RES = 10.0          # px per mm
THREAD_W_MM = 0.40  # same stroke width prep_all paints coverage with
# A 0.50 mm paint width was tried on 2026-08-17 to suppress 1 px pinholes that
# integer endpoint rounding manufactures inside solid fills, and REVERTED the
# same day. Three reasons, all measured, kept here so nobody re-derives them:
#   1. It made the corpus WORSE, not better. Mean boundary distance over the
#      15 designs: 0.40 -> 1.205 mm, 0.50 -> 1.359, 0.70 -> 1.880, 0.90 ->
#      2.172. Widening the paint trades art_missed against pro_extra, so it
#      flatters under-covering designs and punishes over-covering ones — it is
#      a re-weighting, not a correction. It was picked by watching one design
#      improve (hotel_fremont_hat 2.607 -> 0.799) without checking the rest.
#   2. Its stated evidence did not exist. "Byte-stable from 0.50 to 0.60" is a
#      cv2.line thickness quantisation identity — tw 5 and tw 6 paint the
#      identical raster for ANY data — so only two distinct rasters were ever
#      sampled, and the metric had not converged (0.70 moves again).
#   3. It silently rebased this instrument's own published pro-side numbers:
#      at 0.40 the table in docs/pro-parity-real-art-2026-08-15.md reproduces
#      exactly, and every value moves at 0.50.
# If the pinhole artifact is worth fixing, a morphological close is the right
# depth — measured on hotel_fremont_hat it removes 99% of pinholes (203 -> 19)
# against this approach's 77%, and leaves pro_extra untouched at 0.004 where
# paint widening more than doubles it. That is an outline-preserving fix; this
# one displaces the outline that the boundary metric measures.
# Sibling probes (bare.py, holecrop.py, forkprobe.py) also paint 0.40 — keep
# any future change to this constant in step with them or the directory's
# probes stop agreeing about what "covered" means.
SHIFT_MM = 4.0      # alignment search half-window
SHIFT_STEP_MM = 0.4


def pro_mask(csv_path):
    """Coverage raster of the pro's stitches, plus its mm origin.

    Rows are stitches in sew order; `trim`/`jump` mark a move that laid NO
    thread, so the segment arriving at such a stitch is never painted.
    """
    xs, ys, brk = [], [], []
    with open(csv_path) as f:
        for r in csv.DictReader(f):
            xs.append(float(r["x_mm"]))
            ys.append(float(r["y_mm"]))
            brk.append(r["trim"] == "1" or r["jump"] == "1")
    x = np.asarray(xs); y = np.asarray(ys)
    x0, y0 = x.min(), y.min()
    w = int((x.max() - x0) * RES) + 8
    h = int((y.max() - y0) * RES) + 8
    m = np.zeros((h, w), np.uint8)
    tw = max(1, int(round(THREAD_W_MM * RES)))
    px = ((x - x0) * RES + 4).astype(np.int32)
    py = ((y - y0) * RES + 4).astype(np.int32)
    for k in range(1, len(px)):
        if brk[k]:
            continue
        cv2.line(m, (px[k - 1], py[k - 1]), (px[k], py[k]), 1, tw)
    return m.astype(bool)


def art_mask(art_path, width_mm):
    """Artwork ink, rasterised so its ink bbox is `width_mm` wide.

    Mirrors stage1_prep's own sizing rule (stage1_prep.py:317-319): the design's
    physical width is the width of the art's FOREGROUND bbox, not of the file.
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    ink = ink[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    target_w = max(1, int(round(width_mm * RES)))
    scale = target_w / ink.shape[1]
    target_h = max(1, int(round(ink.shape[0] * scale)))
    return cv2.resize(ink.astype(np.uint8), (target_w, target_h),
                      interpolation=cv2.INTER_AREA).astype(bool)


def ink_is_ambiguous(art_path):
    """Does `art_mask` know what the ink is on this artwork? Returns bool.

    `art_mask` has two modes and both assume the ink is one tonal population.
    Alpha-keyed art treats every opaque pixel as ink; opaque art treats every
    dark pixel as ink. Neither survives a logo that is a DARK PANEL with WHITE
    LETTERING knocked out of it: the alpha branch calls the whole panel ink
    including the letters, and the engine — which correctly leaves the white
    letters unsewn — is then charged for the hole it was right to leave.

    That is not hypothetical. It is why `hotel_fremont_*` and `bridge_*` read
    15-21 mm of "engine error" on 2026-08-17 while behaving correctly, and it
    drove a wrong attribution into a published doc before anyone noticed.

    So this does NOT try to fix the mask — silently re-deciding what counts as
    ink would change every published number for a judgement call the pro's own
    stitches may disagree with. It reports that the mask is unreliable here, so
    a caller can refuse to draw a conclusion instead of drawing a wrong one.

    Criterion: inside whatever `art_mask` calls ink, are BOTH a substantial
    dark population and a substantial light one present? The cut points below
    are judgement, not measurement — but the test is structural (bimodality),
    not fitted, and on the 15-design corpus it flags exactly the three designs
    whose boundary outliers were independently traced to this cause and stays
    quiet on the rest.
    """
    im = Image.open(art_path).convert("RGBA")
    a = np.asarray(im)
    if a[..., 3].min() < 255:
        ink = a[..., 3] > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    lum = a[..., :3].astype(np.int32).mean(axis=2)[ink]
    if lum.size == 0:
        return False
    dark = float((lum < 96).mean())
    light = float((lum > 160).mean())
    return min(dark, light) > 0.15


def best_iou(pro, art):
    """IoU at the best whole-pixel shift, art centred on pro to start."""
    H = max(pro.shape[0], art.shape[0]) + int(2 * SHIFT_MM * RES) + 4
    W = max(pro.shape[1], art.shape[1]) + int(2 * SHIFT_MM * RES) + 4

    def place(m, dx=0, dy=0):
        c = np.zeros((H, W), bool)
        oy = (H - m.shape[0]) // 2 + dy
        ox = (W - m.shape[1]) // 2 + dx
        c[oy:oy + m.shape[0], ox:ox + m.shape[1]] = m
        return c

    P = place(pro)
    step = max(1, int(round(SHIFT_STEP_MM * RES)))
    rng = range(-int(SHIFT_MM * RES), int(SHIFT_MM * RES) + 1, step)
    best = (-1.0, 0, 0, None)
    for dy in rng:
        for dx in rng:
            A = place(art, dx, dy)
            inter = np.count_nonzero(P & A)
            union = np.count_nonzero(P | A)
            iou = inter / union if union else 0.0
            if iou > best[0]:
                best = (iou, dx, dy, A)
    iou, dx, dy, A = best
    pro_extra = np.count_nonzero(P & ~A) / max(1, np.count_nonzero(P))
    art_missed = np.count_nonzero(A & ~P) / max(1, np.count_nonzero(A))
    return iou, pro_extra, art_missed, dx / RES, dy / RES


def main():
    print(f"{'design':22s} {'art_iou':>7s} {'pro_extra':>9s} {'art_missed':>10s} "
          f"{'shift_mm':>16s}")
    rows = []
    for d in sys.argv[1:]:
        d = Path(d)
        pcsv = d / "pro_stitches.csv"
        art = d / "art.png"
        if not (pcsv.exists() and art.exists()):
            continue
        P = pro_mask(pcsv)
        width_mm = P.shape[1] / RES
        A = art_mask(art, width_mm)
        iou, extra, missed, dx, dy = best_iou(P, A)
        rows.append(iou)
        print(f"{d.name:22s} {iou:7.3f} {extra:9.3f} {missed:10.3f} "
              f"{dx:7.1f},{dy:5.1f}", flush=True)
    if rows:
        print(f"\nmean art_iou: {sum(rows) / len(rows):.3f}  over {len(rows)} designs")


if __name__ == "__main__":
    main()
