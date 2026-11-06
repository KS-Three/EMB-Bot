#!/usr/bin/env python
"""Measure DENSITY_STACKED on the photo scorecard rows that gained it after
2026-10-05 (docs/density-stacked-photo-rows-2026-11-05.md). Measurement only.

Digitizes each (fixture, garment) at the scorecard's own MATRIX config, one arm
at a time and SERIALLY, records stitches / DENSITY_STACKED extra / the
cutout-refused warning / the shapes piled on the worst patch, and optionally
renders the plan (stitchviz, lit) with the worst patch circled.

    .venv/Scripts/python tools/density_stacked_rows.py --arm head --out run.json
    .venv/Scripts/python tools/density_stacked_rows.py --arm cutout_off --render DIR
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.preflight import run_preflight  # noqa: E402
from digitizer_core.stitchviz import render_design  # noqa: E402
from tools.thread_path_render import plan_mm_to_px  # noqa: E402

ROWS = [
    ("photo/photo_chrome_specular.png", "hat_front"),
    ("photo/photo_dof_meadow.png", "left_chest"),
    ("photo/photo_dof_meadow.png", "hat_front"),
    ("photo/photo_sunset_backlit.png", "left_chest"),
    ("photo/photo_sunset_backlit.png", "hat_front"),
]
ARMS = {
    "head": {},
    "cutout_off": {"photo_cutout_min_kept": 0.0},
    "cap_off": {"color_cap_sewn": False},
    "floor_off": {"dark_ink_floor_rescue": False},
    "tonal_ceiling_on": {"tonal_split_ceiling": True},
    "border_outline_off": {"border_from_outline": False},
    "border_size_off": {"border_by_size": False},
    "fabric_edges_off": {"border_by_size_fabric_edges": False},
    "dark_thin_off": {"keep_dark_thin_strokes": False},
    "border_both_off": {"border_from_outline": False, "border_by_size": False},
}


def _piled(plan, result, at, radius):
    ax, ay = at
    best, info = {}, {}
    for _b, run in plan.iter_runs():
        if not run.shape_id or not run.points:
            continue
        d = min(math.hypot(x - ax, y - ay) for x, y in run.points)
        if d <= radius:
            e = info.setdefault(run.shape_id, {"kinds": {}, "d": d})
            e["kinds"][run.kind + (":" + run.role if run.role else "")] = \
                e["kinds"].get(run.kind + (":" + run.role if run.role else ""), 0) + len(run.points)
            e["d"] = min(e["d"], d)
    regs = {r.shape_id: r for r in result.regions}
    out = []
    for sid, e in sorted(info.items(), key=lambda kv: kv[1]["d"]):
        r = regs.get(sid)
        out.append({"shape": sid, "thread": r.thread_number if r else None,
                    "area_mm2": round(r.area_mm2, 1) if r else None,
                    "source": r.source if r else None, "kinds": e["kinds"]})
    return out


def one(fixture, garment, arm, render_dir):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id=garment, **ARMS[arm])
    path = ROOT / "testdata" / fixture
    t0 = time.time()
    result, plan = digitize(path, cfg)
    rep = run_preflight(result, plan, cfg, image=path)
    ds = [f for f in rep["findings"] if f["code"] == "DENSITY_STACKED"]
    row = {"fixture": fixture, "garment": garment, "arm": arm,
           "score": rep["score"], "grade": rep["grade"],
           "stitches": rep["metrics"].get("stitch_count"),
           "design_class": getattr(result, "design_class", None),
           "findings": sorted(f"{f['code']}:{f['severity']}" for f in rep["findings"]),
           "warn_codes": sorted({w.get("code", "?") for w in plan.warnings}
                                | {w.get("code", "?") for w in getattr(result, "warnings", []) or []}),
           "seconds": round(time.time() - t0, 1), "density": None}
    if ds:
        ex = ds[0]["extra"]
        row["density"] = {k: ex.get(k) for k in (
            "peak_units", "p95_units", "over_warn_mm2", "patches",
            "worst_patch_mm2", "worst_patch_at_mm")}
        at = ex["worst_patch_at_mm"]
        rad = max(math.sqrt(ex["worst_patch_mm2"]) / 2.0, 1.0)
        row["piled"] = _piled(plan, result, at, rad)
    if render_dir is not None:
        design = plan_to_design(plan)
        ppm = 12.0
        img = render_design(design, px_per_mm=ppm, lit=True)
        if ds:
            to_px = plan_mm_to_px(design, ppm)
            cx, cy = to_px(*at)
            r = int(max(rad, 2.0) * ppm)
            cv2.circle(img, (int(cx), int(cy)), r + 4, (0, 0, 255), 3, cv2.LINE_AA)
        stem = Path(fixture).stem
        out = Path(render_dir) / f"{stem}_{garment}_{arm}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(out), img)
        row["render"] = out.name
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", required=True, choices=sorted(ARMS))
    ap.add_argument("--out", default=None)
    ap.add_argument("--render", default=None)
    ap.add_argument("--ci-path", action="store_true",
                    help="hide the rembg venv, as on CI / the cloud capture")
    ap.add_argument("--only", default=None, help="substring filter on fixture/garment")
    a = ap.parse_args()
    if a.ci_path:
        from digitizer_core import stage1_photo_prep as _s1
        _s1.REMBG_VENV_PYTHON = Path("/nonexistent/python")
    rows = []
    for fx, g in ROWS:
        if a.only and a.only not in f"{fx}/{g}":
            continue
        try:
            row = one(fx, g, a.arm, a.render)
        except Exception as exc:  # noqa: BLE001
            row = {"fixture": fx, "garment": g, "arm": a.arm, "error": repr(exc)}
        rows.append(row)
        print(json.dumps(row), flush=True)
        if a.out:
            Path(a.out).write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main()
