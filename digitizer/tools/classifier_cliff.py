#!/usr/bin/env python
"""Does the satin/fill verdict hold still as the design is resized?

The acceptance instrument for `cfg.classify_area_weighted`. The 2026-09-12 gap
audit (§4.2, inv. 3) measured the defect as a CLIFF in size: nine 1 mm steps
between 60 and 108 mm swing becker's sewn satin share by >= 17 points, and
87 -> 88 mm crosses 42.5% -> 12.8% at +73% stitches. Nothing about the artwork
changes across such a step, so any swing is the instrument, not the design.

This digitizes one fixture at every width in a range and reads the SEWN share
of satin (`tools/satin_columns.py` on the emitted plan -- penetrations in a
real zigzag column, not a count of shapes that took the tier), so the number
is what comes off the machine. Per arm it prints the share at each width and
the worst 1 mm STEP, which is the statistic the cliff is about: a classifier
that is merely wrong is fixable, one that is unstable cannot be measured
against at all.

Usage (cwd digitizer/):
  python tools/classifier_cliff.py [--fixture becker_marine_logo.png]
                                   [--from 80] [--to 100] [--step 1]
                                   [--arms shipped area] [--workers 5]
                                   [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

ARMS = {"shipped": {}, "area": {"classify_area_weighted": True}}


def _one(args) -> dict:
    rel, width, arm = args
    from digitizer_core import PipelineConfig, digitize
    from satin_columns import measure, passes_from_plan

    cfg = PipelineConfig(target_width_mm=width, garment_id="left_chest", **ARMS[arm])
    result, plan = digitize(ROOT / "testdata" / rel, cfg)
    col = measure(passes_from_plan(plan))
    satin = sum(1 for r in result.regions
                if getattr(r, "meta", {}).get("tier") == "satin")
    return {"width_mm": width, "arm": arm, "share": round(col["share"], 4),
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
            "satin_regions": satin, "regions": len(result.regions)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--fixture", default="becker_marine_logo.png")
    ap.add_argument("--from", dest="lo", type=float, default=80.0)
    ap.add_argument("--to", dest="hi", type=float, default=100.0)
    ap.add_argument("--step", type=float, default=1.0)
    ap.add_argument("--arms", nargs="*", default=list(ARMS))
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--json", default=None)
    a = ap.parse_args(argv)

    widths, w = [], a.lo
    while w <= a.hi + 1e-9:
        widths.append(round(w, 3))
        w += a.step
    jobs = [(a.fixture, w, arm) for arm in a.arms for w in widths]
    with ProcessPoolExecutor(max_workers=a.workers) as ex:
        rows = list(ex.map(_one, jobs))

    print(f"{a.fixture} — sewn satin share by design width\n")
    print(f"{'width':>7}" + "".join(f"{arm:>12}" for arm in a.arms))
    by = {(r["arm"], r["width_mm"]): r for r in rows}
    for width in widths:
        line = f"{width:>7.1f}"
        for arm in a.arms:
            r = by.get((arm, width))
            line += f"{(r['share'] if r else float('nan')):>12.3f}"
        print(line)
    print()
    for arm in a.arms:
        series = [by[(arm, w)]["share"] for w in widths if (arm, w) in by]
        steps = [abs(b - a_) for a_, b in zip(series, series[1:])]
        worst = max(range(len(steps)), key=lambda i: steps[i]) if steps else None
        print(f"{arm:>10}: span {min(series):.3f}-{max(series):.3f} "
              f"({max(series) - min(series):.3f}), worst 1 mm step "
              f"{steps[worst]:.3f} at {widths[worst]:.0f}->{widths[worst + 1]:.0f} mm"
              if worst is not None else f"{arm}: no data")
    if a.json:
        Path(a.json).write_text(json.dumps(rows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
