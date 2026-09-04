#!/usr/bin/env python
"""Satin as SEWN: what share of a design's stitches sit in a real zigzag
column, and how wide those columns are.

The question this answers is "does this file sew like a professional's",
and it is asked of the STITCHES — a plan-level count of shapes that took the
satin rung answers a different question, and this repo has twice paid for
confusing the two (`tools/seam_underlap.py` read stage 5's plan and hid a
month-long defect; `tools/sewn_compensation.py` is the precedent for doing
it this way).

It reads either our own `StitchPlan` or a decoded machine file, so ours and
a professional's digitizing of the SAME logo are measured by one instrument.

**A column, defined on the needle-down path.** Three consecutive
penetrations p0, p1, p2 form a CROSS when p1 sits off the chord p0->p2 by at
least `MIN_WIDTH_MM` and both legs are between `MIN_LEG_MM` and `MAX_LEG_MM`
long. That offset IS the width — the rail-to-rail distance a satin column is
cut to. Crosses count only inside a run of `MIN_RUN` whose offsets ALTERNATE
side: a column is thread crossing a spine and coming back, and the sign of
the offset is what says so.

Alternation rather than a turn-angle gate, and that is the whole design. A
zigzag's turn angle depends on its aspect: at the 0.4 mm satin pitch a
2.5 mm column turns 162 deg but a 0.7 mm column only 121 and a 0.5 mm column
103, so any fixed reversal threshold goes blind to narrow columns —
precisely the hairline satin this instrument exists to find (a first cut
gated at 120 deg could not see a column under 0.69 mm and read the Becker
corpus logo at 0.3% instead of its true share). Sign alternation is
scale-free. A tatami is excluded without an angle gate at all: its row turns
have one leg of a row spacing, far under `MIN_LEG_MM`.

**Reported.** `share` is crossing penetrations over all penetrations — the
number to compare against a professional file. The width distribution
(median, p10, p90, and the fractions under 0.7 and 1.0 mm) says whether the
columns that exist are sewable: `machine.SATIN_MIN_WIDTH_MM` is the floor a
needle can hold, and a population sitting under it is hairline satin, which
sews as thread-on-thread rather than as a stroke.

  .venv/bin/python tools/satin_columns.py becker_marine_logo.png --width 100
  .venv/bin/python tools/satin_columns.py --file testdata/reference/becker_hat_polo_large_beckers_logolc.dst
  .venv/bin/python tools/satin_columns.py logo_whitebg.png --file <pro.dst>   # both, side by side
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

# Leg length bounds. Below MIN_LEG_MM the "cross" is a tie-off or a
# short-stitch pair at a corner; above MAX_LEG_MM it is a travel or a fill
# row, not a satin leg (satin above ~12 mm is not sewable and this repo caps
# columns at machine.SATIN_MAX_WIDTH_MM = 5).
MIN_LEG_MM = 0.4
MAX_LEG_MM = 12.0
# Two crossings are a corner; a column is a sustained alternation. Measured
# on synthetic fills: at MIN_RUN 3 a tatami reads 0.0% crossing.
MIN_RUN = 3
# A cross with no WIDTH is thread doubling back along its own line — a bean
# stitch, a retrace, a travel sewn out and back — not a column. Without this
# floor those pass every other gate and dominate: the Becker corpus logo read
# 2.7% crossing at a MEDIAN column width of 0.00 mm before it was added.
# 0.1 mm is an order under anything sewable (machine.SATIN_MIN_WIDTH_MM), so
# it excludes only degenerate crosses, never a thin real one.
MIN_WIDTH_MM = 0.1
# The sewable-width marks the distribution is reported against.
THIN_MM = (0.7, 1.0)


def _crosses(points: list[tuple[float, float]]) -> tuple[np.ndarray, np.ndarray]:
    """-> (bool per penetration: in a sustained column, width mm per cross).

    A point is "in a column" when it is the apex of a qualifying cross that
    belongs to a run of at least `MIN_RUN`; the two feet of each such cross
    count too, which is what makes `share` a share of PENETRATIONS rather
    than of turns.
    """
    n = len(points)
    if n < 3:
        return np.zeros(n, bool), np.zeros(0)
    p = np.asarray(points, float)
    a, b, c = p[:-2], p[1:-1], p[2:]
    u, v = b - a, c - b
    lu, lv = np.hypot(*u.T), np.hypot(*v.T)
    # SIGNED offset of the apex from the chord a->c: its magnitude is the
    # column's width, its sign says which rail the apex is on.
    ac = c - a
    lac = np.hypot(*ac.T)
    area2 = ac[:, 0] * (a[:, 1] - b[:, 1]) - (a[:, 0] - b[:, 0]) * ac[:, 1]
    with np.errstate(invalid="ignore", divide="ignore"):
        signed = np.where(lac > 1e-9, area2 / np.maximum(lac, 1e-9), 0.0)
    width = np.abs(signed)

    ok = ((lu >= MIN_LEG_MM) & (lv >= MIN_LEG_MM)
          & (lu <= MAX_LEG_MM) & (lv <= MAX_LEG_MM)
          & (width >= MIN_WIDTH_MM))

    # Keep only crosses inside a run of MIN_RUN consecutive ones whose sides
    # ALTERNATE — thread crossing a spine and coming back.
    side = np.sign(signed)
    keep = np.zeros_like(ok)
    i = 0
    while i < len(ok):
        if not ok[i]:
            i += 1
            continue
        j = i + 1
        while j < len(ok) and ok[j] and side[j] == -side[j - 1]:
            j += 1
        if j - i >= MIN_RUN:
            keep[i:j] = True
        i = j

    inside = np.zeros(n, bool)
    idx = np.flatnonzero(keep)
    for k in idx:
        inside[k:k + 3] = True
    return inside, width[keep]


def measure(passes: list[list[tuple[float, float]]]) -> dict:
    """-> {share, penetrations, crossing, median_mm, p10_mm, p90_mm,
    under_0_7, under_1_0, columns}. `passes` are needle-down runs; a lift
    breaks a pass, because a column cannot span one."""
    total = 0
    crossing = 0
    widths: list[np.ndarray] = []
    for pts in passes:
        inside, w = _crosses(pts)
        total += len(pts)
        crossing += int(inside.sum())
        if len(w):
            widths.append(w)
    allw = np.concatenate(widths) if widths else np.zeros(0)
    out = {
        "penetrations": total,
        "crossing": crossing,
        "share": (crossing / total) if total else 0.0,
        "columns": int(len(allw)),
        "median_mm": float(np.median(allw)) if len(allw) else None,
        "p10_mm": float(np.percentile(allw, 10)) if len(allw) else None,
        "p90_mm": float(np.percentile(allw, 90)) if len(allw) else None,
    }
    for t in THIN_MM:
        key = f"under_{str(t).replace('.', '_')}"
        out[key] = float((allw < t).mean()) if len(allw) else None
    return out


def passes_from_plan(plan) -> list[list[tuple[float, float]]]:
    """Needle-down passes of one of our plans: every run's points, split at
    a lift (`run.jump`), so a column never spans a jump."""
    passes: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for _block, run in plan.iter_runs():
        if run.jump or not cur:
            if len(cur) >= 3:
                passes.append(cur)
            cur = []
        cur.extend(run.points)
    if len(cur) >= 3:
        passes.append(cur)
    return passes


def passes_from_file(path: Path) -> list[list[tuple[float, float]]]:
    """Needle-down passes of a machine file. Same split rule: a JUMP, TRIM or
    COLOR_CHANGE ends a pass. Coordinates are 0.1 mm units in DST/PES."""
    import pystitch

    pat = pystitch.read(str(path))
    if pat is None:
        raise SystemExit(f"unreadable: {path}")
    passes: list[list[tuple[float, float]]] = []
    cur: list[tuple[float, float]] = []
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            cur.append((x / 10.0, y / 10.0))
            continue
        if len(cur) >= 3:
            passes.append(cur)
        cur = []
    if len(cur) >= 3:
        passes.append(cur)
    return passes


def _row(label: str, m: dict) -> str:
    def mm(v):
        return "   —  " if v is None else f"{v:6.2f}"

    def pc(v):
        return "  — " if v is None else f"{v:3.0%}"
    return (f"  {label:34} {m['share']:6.1%} of {m['penetrations']:7,} "
            f"| cols {m['columns']:6,} median {mm(m['median_mm'])} "
            f"p10 {mm(m['p10_mm'])} p90 {mm(m['p90_mm'])} "
            f"| <0.7mm {pc(m['under_0_7'])} <1.0mm {pc(m['under_1_0'])}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("image", nargs="?", help="a path under testdata/, digitized by us")
    ap.add_argument("--file", type=Path, action="append", default=[],
                    help="a machine file to measure (repeatable) — e.g. a professional's")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    args = ap.parse_args(argv)
    if not args.image and not args.file:
        ap.error("give an image, a --file, or both")

    print(f"{'':36} {'crossing':>6} {'':>12} "
          f"| {'columns':>12} {'median':>7} {'p10':>10} {'p90':>10} | thin")
    if args.image:
        from digitizer_core import PipelineConfig
        from digitizer_core.pipeline import plan_stitches, run_stages
        path = Path(args.image)
        if not path.is_absolute():
            path = ROOT / "testdata" / args.image
        cfg = PipelineConfig(target_width_mm=args.width, garment_id=args.garment)
        result = run_stages(str(path), cfg)
        plan = plan_stitches(result, cfg)
        print(_row(f"ours {path.name} @ {args.width:g}mm", measure(passes_from_plan(plan))))
    for f in args.file:
        print(_row(f"file {f.name}", measure(passes_from_file(f))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
