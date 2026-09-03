#!/usr/bin/env python
"""Effective adjacent-row pitch of a fill field — the UNION of every pass.

Why this exists (2026-09-03). `tools/fill_pitch.py` reads row pitch PER
NEEDLE-DOWN PASS from an autocorrelation of the cross-row projection profile.
It was calibrated on the engine's own plans and recovers 0.400 there. Pointed
at the professional's files it read 0.38-0.40 mm (scope-history 2026-09-02),
which the record then took as "the pro does NOT sew half our pitch". Read the
same fields as ROWS instead — cluster the perpendicular coordinate of every
row segment's midpoint and count the rows per millimetre — and the pro's
Hotel Fremont patch ground is ONE pass with **51 rows in 7 mm, 0.14 mm
apart**, and the pro's Becker letter bodies 0.15 mm. Ours: 0.40 on every
fill (Fremont ground, Becker MARINE, the icon repro's blend bands). The
autocorrelation locks onto a professional tatami's penetration-offset cycle
(the split pattern repeats every ~3 rows, and 3 x 0.14 is 0.42), not the row
pitch, so it over-reads a dense pro fill by about 2.7x. This reading is
direct: rows are counted, not inferred from a period.

Two things this settles and one it does not:
  * The cloth sees the union. Two interleaved 0.40 passes offset 0.20 read
    0.20 here and 0.40 per pass — which is exactly the case the per-pass
    instrument cannot see (`test_row_pitch_union.py` pins it).
  * The professional's adjacent-row pitch on two commissioned files is
    0.14-0.15 mm; Law 19's "2x light" was conservative, the ratio is ~2.7.
  * It does NOT set `machine.FILL_ROW_MM`. ROADMAP gate 1: cloth settles the
    constant; this measures the professional's choice and ours.

Method. Take every needle-down segment longer than 1.5 mm, find the dominant
direction (histogram of segment angles mod 180 deg), keep segments within
8 deg of it, rotate so rows are horizontal, and slide an 8 mm window to the
densest spot. Inside it, sort the perpendicular coordinates of the segment
midpoints, merge anything within 0.08 mm into one row, and report the median
gap between consecutive rows plus rows per millimetre. Underlay at another
angle is excluded by the angle gate; underlay at the SAME angle would count
as rows, which is correct — it covers cloth too.

    .venv/bin/python tools/row_pitch_union.py --pattern path.pes [--block 0]
    .venv/bin/python tools/row_pitch_union.py --image testdata/logo_whitebg.png --width 80
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

MIN_SEGMENT_MM = 1.5
ANGLE_GATE_DEG = 8.0
WINDOW_MM = 8.0
ROW_MERGE_MM = 0.08


def segments_from_pattern(path: Path, block: int | None = None) -> list[tuple[tuple[float, float], tuple[float, float]]]:
    """Needle-down segments (mm) of a machine file, optionally one colour block."""
    import pystitch

    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    segs = []
    prev = None
    bi = 0
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            p = (x / 10.0, y / 10.0)
            if prev is not None and (block is None or bi == block):
                segs.append((prev, p))
            prev = p
            continue
        prev = None
        if cmd == pystitch.COLOR_CHANGE:
            bi += 1
    return segs


def segments_from_plan(plan, kinds: tuple[str, ...] = ("fill",), shape_prefix: str | None = None):
    """Needle-down segments of a `StitchPlan`, filtered by run kind and shape id."""
    segs = []
    for _bi, run in plan.iter_runs():
        if run.kind not in kinds:
            continue
        if shape_prefix and not run.shape_id.startswith(shape_prefix):
            continue
        pts = run.points
        for i in range(len(pts) - 1):
            segs.append((pts[i], pts[i + 1]))
    return segs


def union_pitch(segs, window_mm: float = WINDOW_MM) -> dict | None:
    """-> {'pitch_mm', 'p25', 'p75', 'rows', 'rows_per_mm', 'angle_deg', 'window_segments'} or None."""
    if len(segs) < 50:
        return None
    a = np.array([[s[0][0], s[0][1], s[1][0], s[1][1]] for s in segs], dtype=float)
    d = a[:, 2:] - a[:, :2]
    length = np.hypot(d[:, 0], d[:, 1])
    long = length > MIN_SEGMENT_MM
    if long.sum() < 20:
        return None
    ang = np.mod(np.arctan2(d[long, 1], d[long, 0]), np.pi)
    hist, edges = np.histogram(ang, bins=180, range=(0.0, np.pi))
    theta = edges[int(np.argmax(hist))] + np.pi / 360.0
    seg_ang = np.mod(np.arctan2(d[:, 1], d[:, 0]) - theta + np.pi / 2, np.pi) - np.pi / 2
    keep = long & (np.abs(seg_ang) < math.radians(ANGLE_GATE_DEG))
    c, s = math.cos(-theta), math.sin(-theta)
    mid = (a[:, :2] + a[:, 2:]) / 2.0
    u = mid[:, 0] * c - mid[:, 1] * s
    v = mid[:, 0] * s + mid[:, 1] * c
    u, v = u[keep], v[keep]
    if len(u) < 20:
        return None
    best = None
    half = window_mm / 2.0
    for uc in np.arange(u.min(), u.max() + 1e-9, 2.0):
        for vc in np.arange(v.min(), v.max() + 1e-9, 2.0):
            m = (np.abs(u - uc) < half) & (np.abs(v - vc) < half)
            n = int(m.sum())
            if best is None or n > best[0]:
                best = (n, m)
    n, m = best
    vv = np.sort(v[m])
    if len(vv) < 4:
        return None
    rows = [float(vv[0])]
    for x in vv[1:]:
        if x - rows[-1] > ROW_MERGE_MM:
            rows.append(float(x))
    if len(rows) < 3:
        return None
    gaps = np.diff(rows)
    return {
        "pitch_mm": float(np.median(gaps)),
        "p25": float(np.percentile(gaps, 25)),
        "p75": float(np.percentile(gaps, 75)),
        "rows": len(rows),
        "rows_per_mm": float(len(rows) / (rows[-1] - rows[0])) if rows[-1] > rows[0] else float("nan"),
        "angle_deg": float(math.degrees(theta)),
        "window_segments": n,
    }


def _report(label: str, r: dict | None) -> None:
    if r is None:
        print(f"{label}: not enough fill rows to read")
        return
    print(f"{label}: {r['rows']} rows in the densest {WINDOW_MM:g} mm window -> pitch {r['pitch_mm']:.3f} mm "
          f"(p25 {r['p25']:.3f}, p75 {r['p75']:.3f}), {r['rows_per_mm']:.2f} rows/mm, row angle {r['angle_deg']:.0f} deg")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--pattern", type=Path, help="a DST/PES/EXP machine file")
    src.add_argument("--image", type=Path, help="digitize this artwork and read the plan's fill rows")
    ap.add_argument("--block", type=int, default=None, help="only this colour block of the pattern")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default=None)
    args = ap.parse_args(argv)
    if args.pattern:
        _report(f"{args.pattern.name}" + (f" block {args.block}" if args.block is not None else ""),
                union_pitch(segments_from_pattern(args.pattern, args.block)))
        return 0
    from digitizer_core import PipelineConfig, digitize

    cfg = PipelineConfig(target_width_mm=args.width, garment_id=args.garment)
    _result, plan = digitize(args.image, cfg)
    _report(f"{args.image.name} @ {args.width:g} mm, fill runs", union_pitch(segments_from_plan(plan)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
