"""Tangle reader: WHERE the top thread runs in many directions at once.

    python -m tools.tangle_fault_reader run --run DIR --out DIR [--only SLUG ...]
    python -m tools.fault_reader_harness score --fault tangle --marks M --flags DIR ...

The sixth reader scored by `tools.fault_reader_harness`, for the fault the
two-reader prime grader places most often that no computed number reads:
stitches that tangle, pile up, fan or cross where they should flow ("a
tangle of fanned stitches", "crossover stitch bars pile up"; Kent's "Random
Cross over stitch", "no flow here in the stitching"). `select_tangle_pins`
picks the pins. What is fixed before any result is
`docs/tangle-fault-reader-2026-11-19.md`; the constants below are that page's.

It reads stitches only (no artwork, no pipeline, no session):

  1. VISIBLE ANGLE. Every penetration segment (two consecutive `stitch`
     records with no colour change, jump or trim between, at least
     `MIN_SEG_MM` long) is drawn in sewing order as a line `THREAD_MM` wide
     at `PXMM`, carrying its axial angle in `BIN_DEG` bins. A later segment
     overwrites an earlier one, so each pixel holds the direction of the
     thread on top: underlay and covered fill do not count.
  2. DIRECTIONS. Around each pixel, within `RADIUS_MM`, the share of covered
     pixels in each bin, smoothed round the circle by a Gaussian of
     `SMOOTH_BINS`, and its Shannon entropy H. `D = exp(H) / exp(H1)`, where
     H1 is the entropy of a single direction under the same smoothing, so D
     is "how many clean directions' worth": 1 inside a fill or a straight
     satin, about 2 on the seam between two columns, more where thread runs
     every way. Judged only where at least `MIN_COVER` of the disc is thread.
  3. FLAGS. Local maxima of D at or above `FLAG_D`, strongest first, no two
     within `SPACING_MM`; strength = D. CANDIDATES (for the harness's
     `chance_pick` null): the same spread over every judged pixel, whatever
     its D: every place this reader could have flagged.

Output per design, in the harness's format: `<item>.flags.json` (`flags`,
`candidates`, `px_per_mm`, `pad_mm`) and `<item>.mask.npz` (`mask` = thread
pixels, `cand` = judged pixels). Frame: `defect_marks.mark_mm` (design mm
from the stitch bounding box's top-left, y down), so pixel = (mm + pad) * PXMM.
REPORTING ONLY: not a preflight metric, not a gate.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

PXMM = 12.0               # == defect_marks.PXMM, the harness masks' scale
PAD_MM = 2.0              # == defect_marks.PAD_MM
UNITS_PER_MM = 10.0       # == stitchviz.UNITS_PER_MM
THREAD_MM = 0.4           # == stitchviz.THREAD_MM
MIN_SEG_MM = 0.3          # shorter has no direction worth reading
BIN_DEG = 10              # 18 axial bins
SMOOTH_BINS = 1.0         # Gaussian sigma round the circle, in bins
RADIUS_MM = 1.0           # the neighbourhood read at each pixel
MIN_COVER = 0.5           # share of that disc that must be thread
FLAG_D = 2.5              # more spread than two clean directions
SPACING_MM = 2.0          # == edge_fault_reader.MERGE_MM
NBINS = 180 // BIN_DEG


# ------------------------------------------------------------ pure helpers ----

def segments(stitches: list[dict]) -> list[tuple[float, float, float, float]]:
    """(x0, y0, x1, y1) in design units of each penetration segment, in
    sewing order. Colour changes, jumps, trims and ends break the thread."""
    out, prev = [], None
    for s in stitches:
        kind = s.get("type")
        if kind != "stitch":
            prev = None
            continue
        p = (float(s["x"]), float(s["y"]))
        if prev is not None and math.hypot(p[0] - prev[0], p[1] - prev[1]) >= MIN_SEG_MM * UNITS_PER_MM:
            out.append((prev[0], prev[1], p[0], p[1]))
        prev = p
    return out


def frame(stitches: list[dict], pxmm: float = PXMM, pad_mm: float = PAD_MM):
    """-> ((h, w), x0, y1): the same box `stitchviz._frame` draws (stitches
    and jumps), so pixels land where the pins' renders put them."""
    xs = [s["x"] for s in stitches if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in stitches if s.get("type") in ("stitch", "jump")]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    w = max(8, int(((x1 - x0) / UNITS_PER_MM + 2 * pad_mm) * pxmm))
    h = max(8, int(((y1 - y0) / UNITS_PER_MM + 2 * pad_mm) * pxmm))
    return (h, w), x0, y1


def axial_bin(dx: float, dy: float) -> int:
    """Axial angle of (dx, dy) in [0, 180) degrees -> bin 0..NBINS-1."""
    a = math.degrees(math.atan2(dy, dx)) % 180.0
    return min(NBINS - 1, int(a // BIN_DEG))


def angle_image(stitches: list[dict], pxmm: float = PXMM, pad_mm: float = PAD_MM) -> np.ndarray:
    """uint8 image: 0 = no thread, else 1 + the bin of the top thread there."""
    import cv2
    (h, w), x0, y1 = frame(stitches, pxmm, pad_mm)
    img = np.zeros((h, w), np.uint8)
    tw = max(2, int(round(THREAD_MM * pxmm)))
    for ax, ay, bx, by in segments(stitches):
        pa = (int(round(((ax - x0) / UNITS_PER_MM + pad_mm) * pxmm)), int(round(((y1 - ay) / UNITS_PER_MM + pad_mm) * pxmm)))
        pb = (int(round(((bx - x0) / UNITS_PER_MM + pad_mm) * pxmm)), int(round(((y1 - by) / UNITS_PER_MM + pad_mm) * pxmm)))
        cv2.line(img, pa, pb, 1 + axial_bin(bx - ax, ay - by), tw)     # image y runs down
    return img


def _circ_kernel() -> np.ndarray:
    k = np.arange(-3, 4)
    g = np.exp(-0.5 * (k / SMOOTH_BINS) ** 2)
    return g / g.sum()


def _entropy(p: np.ndarray, axis: int = 0) -> np.ndarray:
    with np.errstate(divide="ignore", invalid="ignore"):
        t = np.where(p > 0, p * np.log(p), 0.0)
    return -t.sum(axis)


H1 = float(_entropy(_circ_kernel()))     # one clean direction, smoothed


def directions(hist: np.ndarray) -> np.ndarray:
    """`hist` (NBINS, ...) of shares -> D, the effective number of clean
    directions (1 for one bin). Zero where the histogram is empty."""
    g = _circ_kernel()
    sm = np.zeros_like(hist, dtype=np.float64)
    for off, wgt in zip(range(-3, 4), g):
        sm += wgt * np.roll(hist, off, axis=0)
    tot = sm.sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        p = np.where(tot > 0, sm / np.where(tot > 0, tot, 1), 0.0)
    return np.where(tot > 0, np.exp(_entropy(p, 0)) / math.exp(H1), 0.0)


def d_field(img: np.ndarray, pxmm: float = PXMM) -> tuple[np.ndarray, np.ndarray]:
    """-> (D per pixel, judged mask): `directions` of the disc histogram
    around each pixel, judged where the disc is at least MIN_COVER thread
    and the pixel itself is thread."""
    import cv2
    r = max(1, int(round(RADIUS_MM * pxmm)))
    yy, xx = np.mgrid[-r:r + 1, -r:r + 1]
    k = ((xx ** 2 + yy ** 2) <= r * r).astype(np.float32)
    k /= k.sum()
    hist = np.stack([cv2.filter2D((img == b + 1).astype(np.float32), -1, k, borderType=cv2.BORDER_CONSTANT)
                     for b in range(NBINS)]).astype(np.float64)
    cover = hist.sum(0)
    judged = (cover >= MIN_COVER) & (img > 0)
    return np.where(judged, directions(hist), 0.0), judged


def spread(points: np.ndarray, strength: np.ndarray, spacing_px: float) -> list[int]:
    """Indices of `points` (N, 2 as x, y px) kept strongest first, no two
    within `spacing_px`. Stable on ties (input order)."""
    order = np.argsort(-strength, kind="stable")
    cell = spacing_px
    grid: dict = {}
    keep = []
    s2 = spacing_px * spacing_px
    for i in order:
        x, y = points[i]
        cx, cy = int(x // cell), int(y // cell)
        ok = True
        for gx in (cx - 1, cx, cx + 1):
            for gy in (cy - 1, cy, cy + 1):
                for (qx, qy) in grid.get((gx, gy), ()):
                    if (qx - x) ** 2 + (qy - y) ** 2 < s2:
                        ok = False
                        break
                if not ok:
                    break
            if not ok:
                break
        if ok:
            grid.setdefault((cx, cy), []).append((x, y))
            keep.append(int(i))
    return keep


def read_design(design: dict, pxmm: float = PXMM, pad_mm: float = PAD_MM) -> dict:
    """-> {"flags", "candidates", "mask", "cand", "px_per_mm", "pad_mm"}."""
    import cv2
    stitches = design.get("stitches") or []
    img = angle_image(stitches, pxmm, pad_mm)
    D, judged = d_field(img, pxmm)
    sp = SPACING_MM * pxmm

    def pts(sel):
        ys, xs = np.nonzero(sel)
        return np.stack([xs, ys], 1).astype(float), D[ys, xs]

    peak = judged & (D >= cv2.dilate(D.astype(np.float32), np.ones((3, 3), np.uint8)) - 1e-9)
    P, S = pts(peak & (D >= FLAG_D))
    flags = [{"x_mm": round(P[i, 0] / pxmm - pad_mm, 2), "y_mm": round(P[i, 1] / pxmm - pad_mm, 2),
              "strength": round(float(S[i]), 3)} for i in spread(P, S, sp)]
    C, CS = pts(judged)
    cands = [{"x_mm": round(C[i, 0] / pxmm - pad_mm, 2), "y_mm": round(C[i, 1] / pxmm - pad_mm, 2),
              "strength": round(float(CS[i]), 3)} for i in spread(C, CS, sp)]
    return {"flags": flags, "candidates": cands, "mask": img > 0, "cand": judged,
            "px_per_mm": pxmm, "pad_mm": pad_mm}


# --------------------------------------------------------------------- cli ----

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="read every <slug>.json capture in --run")
    r.add_argument("--run", type=Path, required=True, help="a prime_grader / defect_marks capture dir")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", nargs="*")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    for f in sorted(a.run.glob("*.json")):
        slug = f.stem
        if a.only and slug not in a.only:
            continue
        rec = json.loads(f.read_text(encoding="utf-8"))
        if rec.get("state") not in (None, "done") or not (rec.get("design") or {}).get("stitches"):
            print(slug, "skipped: no finished design")
            continue
        res = read_design(rec["design"])
        iid = f"L_{slug}"
        np.savez_compressed(a.out / f"{iid}.mask.npz", mask=res.pop("mask"), cand=res.pop("cand"))
        res["stitches"] = len(rec["design"]["stitches"])
        (a.out / f"{iid}.flags.json").write_text(json.dumps(res) + "\n", encoding="utf-8")
        print(f"{iid:24s} flags {len(res['flags']):4d} candidates {len(res['candidates']):5d}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
