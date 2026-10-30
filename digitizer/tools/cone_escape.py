#!/usr/bin/env python
"""Where do the cones past "Colors (max N)" come from, on the SEWN design?

`tools/resnap_escape.py` counts the cones stage 4's re-snap adds to the
REGIONS. This reads the other end: every thread the PLAN's blocks load, each
attributed to its source, against the threads the regions wear after the
stage-4 cap. Written for the photo-style census's item 3 (2026-10-27), which
found sewn designs loading 13 / 8 / 8 / 7 cones against a promised 6; the
attribution found two mechanisms, neither the one the census named:

  LATE    a region whose thread changed AFTER `enforce_color_cap` ran --
          "Sew white areas" recolouring the fields it sews (both leaks on
          main, isometric_icon and watercolor: six artwork cones + White)
  STRAY   a block thread no region wears -- the blend tier's shade bands,
          the layered streamline's shades, the detail layer (flower_macro
          forced gradient: 7 strays of 9-57 mm, each a colour change)

Per image: class, cap, the region threads after the stage-4 cap and at
plan time, every block thread with its stitches, sewn mm and how many of
its runs carry a shade stamp, the late regions, and `colors_used` as the
corpus tool counts it. The config is the Studio's own request at 80 mm on a
left chest (`tools.fremont_triage.studio_request`); `--set FIELD=JSON`
overrides a field (the other arm of a flag: `--set color_cap_sewn=true`,
or `--set forced_class='"gradient"'` to send a photograph down the gradient
lane). One image per process, cwd `digitizer/`:

    python -m tools.cone_escape testdata/photo/logo_golden_tee.jpg
    python -m tools.cone_escape testdata/photo/corpus/isometric_icon.png --set color_cap_sewn=true
    python -m tools.cone_escape IMG... --json out.json   # one record per image

Probes `pipeline.enforce_color_cap`, NOT `stage4_vectorize`'s: `pipeline`
binds the name at import, so patching the defining module does nothing
(the trap `resnap_escape.py` records).
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.cone_escape",
                                 description=__doc__.split("\n\n")[0])
    ap.add_argument("images", nargs="+", type=Path)
    ap.add_argument("--set", action="append", default=[], metavar="FIELD=JSON",
                    help="override a request field; repeatable")
    ap.add_argument("--json", type=Path, help="append one record per image to this file")
    a = ap.parse_args(argv)
    sys.path.insert(0, os.getcwd())
    from tools.photo_corpus import parse_sets, request_config
    overrides = parse_sets(a.set)
    records = []
    for img in a.images:
        rec = probe(img, {**request_config(), **overrides})
        records.append(rec)
        print_record(rec)
    if a.json:
        prior = json.loads(a.json.read_text(encoding="utf-8")) if a.json.exists() else []
        a.json.write_text(json.dumps(prior + records, indent=1, default=str), encoding="utf-8")
    return 0


def probe(img: Path, req: dict) -> dict:
    """One image through classify -> build -> finish -> plan, every block
    thread attributed. `req` is the Studio request (dict) the worker parses."""
    from digitizer_core import PipelineConfig
    from digitizer_core import pipeline as pl
    from digitizer_core.adapter import plan_to_design
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.stage0_classify import classify
    from digitizer_core.threads import chart_for
    from digitizer_service.app import _decode, _parse_config
    from tools.photo_corpus import distinct_threads

    seen: dict = {}
    real = pl.enforce_color_cap

    def spy(regions, chart, max_colors, **kw):
        out = real(regions, chart, max_colors, **kw)
        if "after" not in seen:          # the stage-4 pass; the flag's second pass is a later call
            seen["after"] = {int(r.thread_index) for r in regions}
        return out

    data = img.read_bytes()
    t0 = time.time()
    cfg = PipelineConfig(**_parse_config(json.dumps(req)))
    pixels = _decode(data)
    classify(pixels, cfg, forced_class=cfg.forced_class)
    pl.enforce_color_cap = spy
    try:
        gen = build_generation(pixels, cfg, exif_source=data)
        t1 = time.time()
        result = finish_generation(gen.fork(), cfg)
    finally:
        pl.enforce_color_cap = real
    plan = plan_stitches(result, cfg)
    t2 = time.time()
    design = plan_to_design(plan, name="probe")
    chart = chart_for(cfg)

    region_threads: dict[int, int] = {}
    for r in result.regions:
        region_threads[int(r.thread_index)] = region_threads.get(int(r.thread_index), 0) + 1
    post_cap = seen.get("after", set(region_threads))
    blocks: dict[int, dict] = {}
    for b in plan.blocks:
        e = blocks.setdefault(int(b.thread_index), {"blocks": 0, "stitches": 0, "mm": 0.0,
                                                    "shaded_runs": 0, "shapes": set()})
        e["blocks"] += 1
        for run in b.runs:
            pts = run.points
            e["stitches"] += len(pts)
            e["mm"] += sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))
            e["shaded_runs"] += run.shade_thread_index is not None
            if getattr(run, "shape_id", ""):
                e["shapes"].add(run.shape_id)
    late = [{"shape": r.shape_id, "thread": int(r.thread_index), "number": r.thread_number,
             "area_mm2": round(float(r.area_mm2 or 0.0), 2),
             "sew_enclosed_white": r.meta.get("sew_enclosed_white"),
             "stitched": r.meta.get("stitched")}
            for r in result.regions if int(r.thread_index) not in post_cap]
    return {
        "image": img.name, "class": gen.classification_class, "cap": int(cfg.max_colors),
        "post_cap_threads": sorted(post_cap), "region_threads": sorted(region_threads),
        "block_threads": {t: {"number": chart[t].number, "blocks": e["blocks"], "stitches": e["stitches"],
                              "mm": round(e["mm"], 1), "shaded_runs": e["shaded_runs"],
                              "shapes": len(e["shapes"]), "in_regions": t in region_threads}
                          for t, e in sorted(blocks.items())},
        "late": late, "strays": sorted(t for t in blocks if t not in region_threads),
        "colors_used": len(distinct_threads(design.get("colors") or [])),
        "color_blocks": len(design.get("colors") or []),
        "stitches": sum(e["stitches"] for e in blocks.values()),
        "cap_warnings": [w for w in plan.warnings if w.get("code") == "COLOR_CAP_APPLIED"],
        "overrides": {k: v for k, v in req.items()},
        "t_stages_s": round(t1 - t0, 1), "t_plan_s": round(t2 - t1, 1),
    }


def print_record(rec: dict) -> None:
    kept = rec["colors_used"] <= rec["cap"]
    print(f"{rec['image']}: {rec['class']}  cap {rec['cap']}  regions after stage-4 cap "
          f"{len(rec['post_cap_threads'])}, at plan {len(rec['region_threads'])}; blocks load "
          f"{len(rec['block_threads'])}; colors_used {rec['colors_used']} "
          f"({'kept' if kept else 'BROKEN'})  [{rec['t_stages_s']} + {rec['t_plan_s']} s]")
    for t, e in rec["block_threads"].items():
        tag = "" if e["in_regions"] else "  STRAY"
        print(f"   t{t:>4} {e['number']:>6} blocks={e['blocks']} st={e['stitches']:>6} "
              f"mm={e['mm']:>9} shaded_runs={e['shaded_runs']:>4} shapes={e['shapes']:>3}{tag}")
    for l in rec["late"]:
        print(f"   LATE {l['shape']} -> t{l['thread']} {l['number']} {l['area_mm2']} mm2 "
              f"sew_enclosed_white={l['sew_enclosed_white']} stitched={l['stitched']}")
    for w in rec["cap_warnings"]:
        print(f"   {w['code']} {{{', '.join(f'{k}={v}' for k, v in w.items() if k not in ('code', 'message'))}}}")


if __name__ == "__main__":
    raise SystemExit(main())
