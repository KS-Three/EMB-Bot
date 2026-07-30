#!/usr/bin/env python
"""Render every review case to per-stage debug PNGs and print the stats table.

Usage: .venv/Scripts/python tools/review_render.py baseline
       .venv/Scripts/python tools/review_render.py after
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.stage6_satin import is_satin_candidate  # noqa: E402

CASES = [
    ("logo_whitebg", ROOT / "testdata/logo_whitebg.png", "hat_front", 80.0),
    ("logo_alpha", ROOT / "testdata/logo_alpha.png", "left_chest", 80.0),
    ("serif_text", ROOT / "debug_out/cases/serif_text.png", "left_chest", 80.0),
    ("curved_ribbon", ROOT / "debug_out/cases/curved_ribbon.png", "pique_knit", 80.0),
    ("nested_colors", ROOT / "debug_out/cases/nested_colors.png", "left_chest", 70.0),
]


def main() -> None:
    tag = sys.argv[1] if len(sys.argv) > 1 else "baseline"
    rows = []
    for name, path, garment, width in CASES:
        if not path.exists():
            print("missing", path)
            continue
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                             debug_dir=ROOT / "debug_out" / tag / name)
        result, plan = digitize(path, cfg)
        s = plan.stats
        satin_shapes = sum(1 for r in result.regions
                           if is_satin_candidate(r.polygon, 3.0))
        # needle-up distance actually flown
        jump_mm = 0.0
        prev = None
        for _b, r in plan.iter_runs():
            if r.jump and prev is not None:
                jump_mm += math.dist(prev, r.points[0])
            prev = r.points[-1]
        rows.append((name, s.stitch_count, len(plan.blocks), s.trims, s.jumps,
                     len(result.regions), satin_shapes, round(jump_mm, 1),
                     round(s.thread_m_total, 2)))
    print(f"\n=== {tag} ===")
    hdr = ("case", "stitches", "colors", "trims", "jumps", "shapes",
           "satin", "jump_mm", "thread_m")
    print(("{:<15}" + "{:>10}" * 8).format(*hdr))
    for r in rows:
        print(("{:<15}" + "{:>10}" * 8).format(*[str(v) for v in r]))


if __name__ == "__main__":
    main()
