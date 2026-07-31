#!/usr/bin/env python
"""Measure the defects the debug renders show, so before/after is a number.

Usage: .venv/Scripts/python tools/audit.py
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core import machine, stitches  # noqa: E402

CASES = [
    ("logo_whitebg", ROOT / "testdata/logo_whitebg.png", "hat_front", 80.0),
    ("logo_alpha", ROOT / "testdata/logo_alpha.png", "left_chest", 80.0),
    ("serif_text", ROOT / "debug_out/cases/serif_text.png", "left_chest", 80.0),
    ("curved_ribbon", ROOT / "debug_out/cases/curved_ribbon.png", "pique_knit", 80.0),
    ("nested_colors", ROOT / "debug_out/cases/nested_colors.png", "left_chest", 70.0),
]


def audit(plan):
    short_fill = 0        # steps ALONG a fill row under MIN_STITCH_MM
    short_satin = 0
    fill_steps = 0
    trim_d = []
    jump_d = []
    travel_mm = 0.0
    satin_gap_max = 0.0
    prev_end = None
    for _b, run in plan.iter_runs():
        if run.jump and prev_end is not None:
            d = math.dist(prev_end, run.points[0])
            (trim_d if run.trim else jump_d).append(d)
        prev_end = run.points[-1]
        if run.kind == stitches.TRAVEL:
            travel_mm += run.length_mm
        if run.kind == stitches.FILL:
            # A fill path alternates long steps ALONG a row with short turns
            # between rows, and only the first kind has to clear the needle
            # minimum. A turn reverses direction; a step along a row keeps
            # going roughly the way the previous one did.
            pts = run.points
            for i in range(1, len(pts) - 1):
                a, b, c = pts[i - 1], pts[i], pts[i + 1]
                d = math.dist(b, c)
                if d < 1e-9:
                    continue
                ux, uy = (b[0] - a[0]), (b[1] - a[1])
                n = math.hypot(ux, uy)
                if n < 1e-9:
                    continue
                cos = ((c[0] - b[0]) * ux + (c[1] - b[1]) * uy) / (n * d)
                if cos < 0.5:
                    continue          # a row turn, not a stitch along the row
                fill_steps += 1
                if d < machine.MIN_STITCH_MM:
                    short_fill += 1
        if run.kind == stitches.SATIN:
            pts = run.points
            for i in range(0, len(pts) - 2):
                # Rails alternate A, B, A, B ... so two apart is the same rail.
                satin_gap_max = max(satin_gap_max, math.dist(pts[i], pts[i + 2]))
            for a, b in zip(pts, pts[1:]):
                if math.dist(a, b) < machine.SATIN_MIN_CROSS_MM:
                    short_satin += 1
    return {
        "trims": len(trim_d),
        "trim_min_mm": round(min(trim_d), 1) if trim_d else 0.0,
        "jumps": len(jump_d),
        "travel_mm": round(travel_mm, 1),
        "short_fill": short_fill,
        "satin_gap_max": round(satin_gap_max, 2),
    }


def main() -> None:
    for name, path, garment, width in CASES:
        if not path.exists():
            continue
        _r, plan = digitize(path, PipelineConfig(target_width_mm=width,
                                                 garment_id=garment))
        s = plan.stats
        a = audit(plan)
        codes = Counter(w["code"] for w in plan.warnings)
        print(f"{name:<15} st={s.stitch_count:<6} col={len(plan.blocks)} "
              f"trims={a['trims']:<3} (min {a['trim_min_mm']}mm) jumps={a['jumps']:<3} "
              f"travel={a['travel_mm']:<7} shortfill={a['short_fill']:<4} "
              f"satingap={a['satin_gap_max']}")
        if codes:
            print(" " * 15, dict(codes))


if __name__ == "__main__":
    main()
