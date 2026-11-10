#!/usr/bin/env python
"""Is a THREAD_MATCH_POOR block a wrong thread, or a chart limit?

For every graded row at or past the block line (raw dE00 > 10, footprint at
or above the 5 mm2 floor), prints the assigned spool's error beside two
floors, each scored with the grader's own estimator (median of per-pixel
CIEDE2000 over the row's pixels, `preflight._region_color_errors`):

  best loaded   the closest spool this design already sews
  best chart    the closest spool on the WHOLE brand chart (398 on Isacord)

When "best chart" is still past the block line, no thread the brand sells
clears the finding: the pixels themselves spread wider than 10 dE00
(anti-aliased thin strokes, JPEG chroma bleed, hatching, noise). That is a
chart limit, recorded, not fixed. When "best chart" clears the line and
"best loaded" does not, the fix is a cone; when "best loaded" clears it, the
fix is a reassignment.

It also prints the median-colour nearest thread (collapse first, then snap),
which is NOT what the grader scores; it is there so a reader can see when a
region's average colour sits on a thread its per-pixel spread still fails.

Written for the defect-28 leftovers (`docs/thread-match-leftovers-2026-11-10.md`).

    .venv/Scripts/python tools/thread_chart_floor.py
    .venv/Scripts/python tools/thread_chart_floor.py photo/logo_bridge_bar.jpg --garment hat_front
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

#: The three defect-28 leftovers measured 2026-11-10 on main 333147fd.
DEFAULT_FIXTURES = [
    "photo/logo_bridge_bar.jpg",
    "photo/screenshot_phone_ui_golke.jpg",
    "photo/photo_subject_stub.png",
]


def floors(fixture: str, garment: str, width_mm: float = 80.0) -> list[dict]:
    """-> one dict per block-eligible row, worst first."""
    import numpy as np
    from skimage.color import deltaE_ciede2000

    from digitizer_core import PipelineConfig, digitize
    from digitizer_core import preflight as pf
    from digitizer_core.threads import chart_for

    path = ROOT / "testdata" / fixture
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result, plan = digitize(path, cfg)
    p = pf.prep(path, cfg, design_class=result.design_class)
    view = pf._two_tone_view(p, plan, cfg)
    rows = pf._region_color_errors(view, result, plan, cfg)
    chart = chart_for(cfg)
    loaded = sorted({b.thread_index for b in plan.blocks
                     if any(len(r.points) for r in b.runs)})
    out = []
    for row in rows:
        if row["delta_e"] <= pf.DELTA_E_CLEARLY_DIFFERENT:
            continue
        if row["footprint_mm2"] < pf._THREAD_MATCH_MIN_PATCH_MM2:
            continue
        lab = row["_lab_px"]
        errs = np.array([np.median(deltaE_ciede2000(lab, chart.lab[i].reshape(1, 3)))
                         for i in range(len(chart.lab))])
        best = int(np.argmin(errs))
        bl = min(loaded, key=lambda i: errs[i])
        med = np.median(lab, axis=0).reshape(1, 3)
        e_med = deltaE_ciede2000(np.repeat(med, len(chart.lab), 0), chart.lab)
        mi = int(np.argmin(e_med))
        q = np.percentile(lab[:, 0], [5, 50, 95])
        out.append({
            "design_class": result.design_class,
            "shape_id": row["shape_id"],
            "footprint_mm2": row["footprint_mm2"],
            "assigned": chart[row["thread_index"]].number,
            "assigned_de": row["delta_e"],
            "best_loaded": chart[bl].number,
            "best_loaded_de": float(errs[bl]),
            "best_chart": chart[best].number,
            "best_chart_de": float(errs[best]),
            "median_colour_nearest": chart[mi].number,
            "median_colour_de": float(e_med[mi]),
            "L_p5_p50_p95": [round(float(v), 1) for v in q],
            "verdict": ("chart limit" if errs[best] > pf.DELTA_E_CLEARLY_DIFFERENT
                        else "reassign" if errs[bl] <= pf.DELTA_E_CLEARLY_DIFFERENT
                        else "needs a cone"),
        })
    return sorted(out, key=lambda r: -r["assigned_de"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("fixtures", nargs="*", default=DEFAULT_FIXTURES,
                    help="paths under digitizer/testdata/")
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--width-mm", type=float, default=80.0)
    args = ap.parse_args(argv)
    for fx in args.fixtures:
        rows = floors(fx, args.garment, args.width_mm)
        print(f"== {fx} {args.garment} {args.width_mm:g} mm: {len(rows)} block-eligible rows")
        for r in rows:
            print(f"  {r['shape_id']:<22} {r['footprint_mm2']:7.1f} mm2  "
                  f"assigned {r['assigned']} {r['assigned_de']:5.1f} | "
                  f"best loaded {r['best_loaded']} {r['best_loaded_de']:5.1f} | "
                  f"best chart {r['best_chart']} {r['best_chart_de']:5.1f} | "
                  f"median-colour {r['median_colour_nearest']} {r['median_colour_de']:4.1f} | "
                  f"L* p5/50/95 {r['L_p5_p50_p95']} | {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
