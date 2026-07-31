#!/usr/bin/env python
"""Sew it, or fix it first — the operator's preflight from the command line.

Digitizes the artwork, scores the finished plan, and prints what will go
wrong on the machine before any hoop moves. Same report the service attaches
to a finished job.

Usage: .venv/Scripts/python tools/preflight_report.py ART.png
           [--width 90] [--garment left_chest] [--brand madeira-rayon]
           [--fabric pique_knit] [--border off] [--json]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.preflight import run_preflight  # noqa: E402

MARK = {"info": " i ", "warn": " ! ", "block": "!!!"}


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Preflight-score artwork before it reaches the machine.")
    ap.add_argument("image", help="artwork file (PNG, JPEG, WebP, TIFF)")
    ap.add_argument("--width", type=float, default=90.0,
                    help="finished embroidered width in mm (default 90)")
    ap.add_argument("--garment", default="left_chest",
                    help="garment id, picks the fabric preset (default left_chest)")
    ap.add_argument("--brand", default=None,
                    help="thread brand id, e.g. madeira-rayon (default isacord)")
    ap.add_argument("--fabric", default=None,
                    help="explicit fabric id; overrides the garment's preset")
    ap.add_argument("--border", default="off", choices=["off", "auto", "bean"])
    ap.add_argument("--json", action="store_true",
                    help="print the raw report as JSON instead of prose")
    args = ap.parse_args()

    path = Path(args.image)
    if not path.is_file():
        print(f"no such file: {path}", file=sys.stderr)
        return 2

    cfg = PipelineConfig(
        target_width_mm=args.width,
        garment_id=args.garment,
        thread_brand=args.brand,
        fabric_id=args.fabric,
        border=args.border,
    )
    result, plan = digitize(path, cfg)
    report = run_preflight(result, plan, cfg, image=path)

    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if not any(f["severity"] == "block" for f in report["findings"]) else 1

    m = report["metrics"]
    print(f"{path.name} @ {args.width:g}mm / {args.garment}"
          f" / {args.brand or 'isacord'}")
    print(f"grade {report['grade']}  score {report['score']}/100  "
          f"st={m['stitch_count']} trims/1k={m['trims_per_1000']} "
          f"shortsatin={m['satin_short_fraction']:.0%} "
          f"fillrow={m['fill_advance_mm']} satinadv={m['satin_advance_mm']} "
          f"dEmax={m['thread_worst_delta_e']}")
    if not report["findings"]:
        print("clean — nothing to fix before sewing.")
        return 0
    for f in report["findings"]:
        print(f"[{MARK[f['severity']]}] {f['code']}: {f['message']}")
    return 1 if any(f["severity"] == "block" for f in report["findings"]) else 0


if __name__ == "__main__":
    sys.exit(main())
