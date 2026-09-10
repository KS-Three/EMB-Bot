#!/usr/bin/env python
"""What colour does stage 2 hand the palette for each region — and is it a
colour any pixel carries?

The SLIC+RAG lane (every gradient- and photo-classified design, six of seven
real logos) represents each region by the plain MEAN of its Lab pixels when
it selects the palette. A big flat region with things drawn on it — Bridge
Bar's yellow disc with its black lettering, bird and rope — carries every
anti-aliased inclusion edge inside its mask, and the mean lands 12 ΔE00
towards lime, on a colour no pixel has; the palette then rightly spends a
spool on Limelight (#442's test run, DOCTRINE 2026-09-10).

This census reads, for every region of every corpus fixture that reaches
that lane: its area weight, its mean, its per-channel median, the "modal
mean" (the mean over the pixels within DELTA_E_VISIBLE of the median), the
ΔE00 from the mean to each, and the chart's nearest spool under each — so
the choice of statistic behind `cfg.robust_region_colour` is a measurement
and not a preference. `mean` is the engine's own OFF point (the RGB mean,
converted once), so "moves the spool" is against what the shipped engine
actually hands the palette. It changes nothing.

    .venv/bin/python -m tools.region_colour                 # all corpus fixtures
    .venv/bin/python -m tools.region_colour --fixture photo/logo_bridge_bar.jpg
    .venv/bin/python -m tools.region_colour --json build/region_colour.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from digitizer_core import stage2_photo_segment as s2
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.threads import chart_for

BIMODAL_DE00 = 10.0     # preflight.DELTA_E_CLEARLY_DIFFERENT: mean-to-median this far apart


def _spy_regions(art: Path, cfg: PipelineConfig):
    """Run stages 0-4 with `_region_pixels_rgb` wrapped, collecting every
    region's RGB pixel array in the order the palette saw them."""
    captured: list[np.ndarray] = []
    orig = s2._region_pixels_rgb

    def spy(p, r):
        px = orig(p, r)
        captured.append(px)
        return px

    s2._region_pixels_rgb = spy
    try:
        result = run_stages(art, cfg)
    finally:
        s2._region_pixels_rgb = orig
    return result, captured


def census(art: Path, cfg: PipelineConfig) -> dict:
    result, regions = _spy_regions(art, cfg)
    chart = chart_for(cfg)
    rows = []
    for px in regions:
        cands = s2.region_colour_candidates(px)
        mean = cands["mean"]
        row = {"area_px": int(len(px))}
        spools = {}
        for name, lab in cands.items():
            idx = int(chart.nearest_index(lab)) if hasattr(chart, "nearest_index") else int(
                np.argmin(s2.deltaE_ciede2000(lab.reshape(1, 3), chart.lab)))
            spools[name] = chart[idx].number
            row[f"{name}_de00_from_mean"] = round(float(s2.deltaE_ciede2000(
                mean.reshape(1, 3), lab.reshape(1, 3))[0]), 2)
        row["spool"] = spools
        row["median_moves_spool"] = spools["median"] != spools["mean"]
        row["modal_moves_spool"] = spools["modal_mean"] != spools["mean"]
        row["bimodal"] = bool(row["median_de00_from_mean"] > BIMODAL_DE00)
        rows.append(row)
    total = sum(r["area_px"] for r in rows) or 1
    return {
        "fixture": str(art),
        "class": result.design_class,
        "regions": len(rows),
        "median_moved": sum(r["median_moves_spool"] for r in rows),
        "modal_moved": sum(r["modal_moves_spool"] for r in rows),
        "median_moved_area_frac": round(sum(r["area_px"] for r in rows if r["median_moves_spool"]) / total, 4),
        "modal_moved_area_frac": round(sum(r["area_px"] for r in rows if r["modal_moves_spool"]) / total, 4),
        "bimodal": sum(r["bimodal"] for r in rows),
        "worst_mean_to_median_de00": max((r["median_de00_from_mean"] for r in rows), default=0.0),
        "rows": rows,
    }


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA
    from tools.corpus_scorecard import FIXTURES

    ap = argparse.ArgumentParser()
    ap.add_argument("--fixture", action="append", default=None,
                    help="path under testdata/ (repeatable); default: the scorecard corpus")
    ap.add_argument("--json", type=Path, default=None)
    ap.add_argument("--width", type=float, default=80.0)
    args = ap.parse_args(argv)
    names = args.fixture or list(FIXTURES)
    out = []
    print(f"| fixture (class) | regions | median: moved / area | modal: moved / area | bimodal | worst mean→median ΔE00 |")
    print("|---|---:|---|---|---:|---:|")
    for name in names:
        art = TESTDATA / name
        cfg = PipelineConfig(target_width_mm=args.width, garment_id="left_chest")
        c = census(art, cfg)
        out.append(c)
        if not c["regions"]:
            print(f"| `{Path(name).stem}` ({c['class']}) | 0 — flat lane | | | | |", flush=True)
            continue
        print(f"| `{Path(name).stem}` ({c['class']}) | {c['regions']} "
              f"| {c['median_moved']} / {c['median_moved_area_frac']:.1%} "
              f"| {c['modal_moved']} / {c['modal_moved_area_frac']:.1%} "
              f"| {c['bimodal']} | {c['worst_mean_to_median_de00']:.1f} |", flush=True)
    lane = [c for c in out if c["regions"]]
    print(f"\nSLIC-lane fixtures: {len(lane)} of {len(out)}; regions {sum(c['regions'] for c in lane)}; "
          f"median moves the spool of {sum(c['median_moved'] for c in lane)} regions, the modal mean of "
          f"{sum(c['modal_moved'] for c in lane)}; bimodal regions {sum(c['bimodal'] for c in lane)}.")
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(out, indent=1))
        print("wrote", args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
