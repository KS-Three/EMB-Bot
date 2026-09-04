#!/usr/bin/env python
"""Compensation as SEWN: how much of each region's compensation strip — stage
5's sewing polygon minus the artwork, i.e. pull compensation all round plus
the seam tongue under whichever colour sews after — its own thread covers.

`tools/seam_underlap.py` reads the PLAN: it measures stage 5's polygons and
says how deep the tongue is meant to be. This reads the STITCHES, and is the
instrument that would have caught the blend tier sewing its raw artwork for
a month (2026-08-05 to 2026-09-04) while the plan carried a 0.54 mm tongue
on the repro. Thread "covers" a point when a stitch line passes within one
fill row of it; that tolerance leaks a strip of the edge rows into the
measure, so an uncompensated region reads ~25-35%, not 0.

  .venv/bin/python tools/sewn_compensation.py photo/repro_gradient_white_icon.png
  .venv/bin/python tools/sewn_compensation.py photo/region_blobs.png --width 80 --garment hat_front
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from shapely.geometry import LineString
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, machine, run_stages  # noqa: E402
from digitizer_core.pipeline import fabric_for, plan_stitches  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def measure_plan(planned, plan) -> list[dict]:
    """-> one row per planned region: artwork and strip areas, the fraction of
    each covered within a fill row of its own thread, and whether it sewed as
    blend bands."""
    runs_by_shape: dict[str, list] = {}
    for block in plan.blocks:
        for run in block.runs:
            runs_by_shape.setdefault(run.shape_id.split("-blend")[0], []).append(run)
    row = machine.FILL_ROW_MM
    rows = []
    for p in planned:
        runs = runs_by_shape.get(p.shape_id, [])
        if not runs:
            continue
        thread = unary_union([LineString(r.points).buffer(row)
                              for r in runs if len(r.points) > 1])
        art = p.region.polygon
        strip = p.polygon.difference(art)
        rows.append({
            "shape_id": p.shape_id,
            "blend": any("-blend" in r.shape_id for r in runs),
            "kinds": sorted({r.kind for r in runs}),
            "art_mm2": art.area,
            "art_covered": thread.intersection(art).area / art.area if art.area else 0.0,
            "strip_mm2": strip.area,
            "strip_covered": (thread.intersection(strip).area / strip.area
                              if strip.area > 0 else None),
        })
    return rows


def measure_image(image: Path, width_mm: float, garment: str | None) -> list[dict]:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    result = run_stages(image, cfg)
    planned, _w = resolve_overlaps(result.regions, fabric_for(cfg), cfg, result.design_class)
    return measure_plan(planned, plan_stitches(result, cfg))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="+", help="paths under testdata/, or absolute")
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--garment", default="left_chest")
    args = ap.parse_args(argv)
    for name in args.images:
        path = Path(name) if Path(name).is_absolute() else TESTDATA / name
        rows = measure_image(path, args.width, args.garment)
        print(f"{name} @ {args.width:g}mm/{args.garment}: {len(rows)} regions sewn")
        print(f"  {'shape':12} {'tier':6} {'art mm2':>8} {'art cov':>8} {'strip mm2':>10} {'strip cov':>10}")
        blend_strip = blend_cov = 0.0
        for r in sorted(rows, key=lambda r: -r["art_mm2"]):
            sc = "-" if r["strip_covered"] is None else f"{r['strip_covered']:.0%}"
            print(f"  {r['shape_id']:12} {'blend' if r['blend'] else '/'.join(r['kinds'])[:6]:6} "
                  f"{r['art_mm2']:8.0f} {r['art_covered']:8.0%} {r['strip_mm2']:10.1f} {sc:>10}")
            if r["blend"] and r["strip_covered"] is not None:
                blend_strip += r["strip_mm2"]
                blend_cov += r["strip_covered"] * r["strip_mm2"]
        if blend_strip:
            print(f"  blend regions: {blend_strip:.1f} mm2 of strip, {blend_cov / blend_strip:.0%} covered")
    return 0


if __name__ == "__main__":
    sys.exit(main())
