"""How faithfully did the ENGINE reproduce the customer's artwork?

`artfidelity.py` measures the pro against the art — the ceiling. This is its
engine-side twin: the same rasterisation, the same shift search, pointed at
`ours_stitches.csv` instead of `pro_stitches.csv`, so the two instruments'
numbers are comparable design-by-design. The scorecard cannot see this at
all: its coverage component is agreement with the PRO's stitches, and it has
no outline term — a 20 mm circle RDP'd into a 20-gon and a faithful circle
can score identically there (docs/scope-digest/measurement.md:8-12 names
engine-vs-artwork coverage as the open need).

Per design:

    art_iou       - engine coverage vs art ink, IoU at best shift
    engine_extra  - fraction of engine coverage the artwork does not ask for
    art_missed    - fraction of artwork ink the engine left unsewn
    haus_mm       - symmetric Hausdorff between art and engine cover OUTLINES,
                    at the best-IoU alignment, in mm
    meanb_mm      - symmetric mean boundary distance, same alignment

`haus_mm` is the number curve coarseness moves (sagitta of the RDP chords);
`meanb_mm` separates "one bad notch" from "everything is off".

Inherited limit (same as artfidelity.py): the shift search pins at the window
boundary on re-composed layouts, so designs the pro re-arranged read low by
construction — compare trends per design, not absolutes across designs.

Usage:
    python enginefidelity.py <OUT>/real/<slug> [...]
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from artfidelity import (  # noqa: E402
    RES,
    SHIFT_MM,
    THREAD_W_MM,
    art_mask,
    best_iou,
    pro_mask,
)


# pro_mask pads its canvas by 4 px on each side (artfidelity.py's `+ 8` / `+ 4`).
MASK_PAD_PX = 8

# Floor of this instrument, measured 2026-08-17 on a synthetic perfect engine
# (fill rows exactly covering the art square) AFTER the pad correction above.
# The pad fix removed the false `art_missed` entirely (0.042 -> 0.000 on a
# 10 mm square) but NOT the boundary residual: that is SHIFT_STEP_MM = 0.4
# alignment quantisation plus the 1 px raster quantum, and it does not cancel
# between arms. Measured 0.30-0.32 mm haus, 0.12-0.14 mm boundary across
# 10-100 mm squares; rounded up here.
#
# Read these before quoting any delta. The 2026-08-17 ladder's first verdict
# cited <=0.04 mm differences as evidence that a lever was dead — an order of
# magnitude inside this floor.
FLOOR_HAUS_MM = 0.35
FLOOR_MEANB_MM = 0.15


def engine_mask(csv_path):
    """Coverage raster of the engine's stitches (`ours_stitches.csv`).

    prep_all writes the same trim/jump semantics as the pro-side export (a
    move arriving at a trim/jump row laid no thread), so the pro-side raster
    routine applies unchanged.
    """
    return pro_mask(csv_path)


def _boundary(mask):
    """Outline pixels of a boolean mask (mask minus its 3x3 erosion)."""
    m = mask.astype(np.uint8)
    er = cv2.erode(m, np.ones((3, 3), np.uint8), borderValue=0)
    return mask & ~er.astype(bool)


def boundary_distance_mm(a, b, res=RES):
    """(hausdorff_mm, mean_mm) between the outlines of two same-shape masks.

    Symmetric: directed distances are taken both ways; Hausdorff is the max,
    the mean is the average over both boundaries' pixels. Raises ValueError on
    a non-bool input, an empty mask, or a shape mismatch — an empty side means
    the caller fed a design that produced no coverage, which is its own
    finding, not a zero.

    The dtype check is not pedantry. `_boundary` on a uint8 mask returns uint8,
    and the `~dst` below then flips 1 -> 254 instead of True -> False, so every
    pixel is nonzero, `distanceTransform` sees an all-foreground image, and the
    function returns OpenCV's saturation sentinel: the same pair of squares
    that reads (7.071, 5.248) as bool reads (6553.6, 6553.6) as uint8 — a
    plausible-looking number, past every other guard, with no exception.
    """
    for name, m in (("a", a), ("b", b)):
        if m.dtype != bool:
            raise ValueError(f"{name} must be a bool mask, got {m.dtype}")
    if a.shape != b.shape:
        raise ValueError(f"shape mismatch: {a.shape} vs {b.shape}")
    if not a.any() or not b.any():
        raise ValueError("empty mask")
    ba, bb = _boundary(a), _boundary(b)
    if not ba.any() or not bb.any():
        raise ValueError("empty boundary")

    def directed(src, dst):
        # Distance from every src outline pixel to the nearest dst outline
        # pixel: exact L2 distance transform of the dst-outline complement.
        dt = cv2.distanceTransform(
            (~dst).astype(np.uint8), cv2.DIST_L2, cv2.DIST_MASK_PRECISE
        )
        vals = dt[src]
        return float(vals.max()), float(vals.sum()), int(vals.size)

    max_ab, sum_ab, n_ab = directed(ba, bb)
    max_ba, sum_ba, n_ba = directed(bb, ba)
    haus = max(max_ab, max_ba) / res
    mean = (sum_ab + sum_ba) / (n_ab + n_ba) / res
    return haus, mean


def _place(m, H, W, dx=0, dy=0):
    c = np.zeros((H, W), bool)
    oy = (H - m.shape[0]) // 2 + dy
    ox = (W - m.shape[1]) // 2 + dx
    c[oy : oy + m.shape[0], ox : ox + m.shape[1]] = m
    return c


def main():
    print(
        f"{'design':22s} {'art_iou':>7s} {'eng_extra':>9s} {'art_missed':>10s} "
        f"{'haus_mm':>7s} {'meanb_mm':>8s} {'shift_mm':>14s}"
    )
    ious, hauses, means = [], [], []
    for d in sys.argv[1:]:
        d = Path(d)
        ecsv = d / "ours_stitches.csv"
        art = d / "art.png"
        if not (ecsv.exists() and art.exists()):
            continue
        E = engine_mask(ecsv)
        # pro_mask's canvas is the stitch span PLUS a fixed 8 px margin
        # (artfidelity.py's `+ 8`). Scaling the artwork to the canvas rather
        # than to the span stretched it 0.8 mm wider than the engine on every
        # design — measured 2026-08-17, a flawless reproduction read
        # art_missed 0.042 at 10 mm and haus 0.28 mm at any size. Subtract the
        # margin so a perfect engine can actually score zero.
        width_mm = (E.shape[1] - MASK_PAD_PX) / RES
        A = art_mask(art, width_mm)
        iou, extra, missed, dx_mm, dy_mm = best_iou(E, A)
        # Re-place both in the shift-search frame at the winning alignment so
        # the boundary metric is computed on the same geometry the IoU chose.
        H = max(E.shape[0], A.shape[0]) + int(2 * SHIFT_MM * RES) + 4
        W = max(E.shape[1], A.shape[1]) + int(2 * SHIFT_MM * RES) + 4
        Ep = _place(E, H, W)
        Ap = _place(A, H, W, int(round(dx_mm * RES)), int(round(dy_mm * RES)))
        try:
            haus, meanb = boundary_distance_mm(Ep, Ap)
        except ValueError as e:
            print(f"{d.name:22s} {iou:7.3f} {extra:9.3f} {missed:10.3f} "
                  f"{'—':>7s} {'—':>8s}  ({e})", flush=True)
            continue
        ious.append(iou); hauses.append(haus); means.append(meanb)
        print(
            f"{d.name:22s} {iou:7.3f} {extra:9.3f} {missed:10.3f} "
            f"{haus:7.2f} {meanb:8.3f} {dx_mm:6.1f},{dy_mm:5.1f}",
            flush=True,
        )
    if ious:
        n = len(ious)
        print(
            f"\nmean art_iou {sum(ious)/n:.3f} · mean haus {sum(hauses)/n:.2f} mm "
            f"· mean boundary {sum(means)/n:.3f} mm · over {n} designs"
        )
        print(
            f"instrument floor: haus {FLOOR_HAUS_MM:.2f} mm, boundary "
            f"{FLOOR_MEANB_MM:.2f} mm — smaller deltas are not signal"
        )


if __name__ == "__main__":
    main()
