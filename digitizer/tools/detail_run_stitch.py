"""The detail layer sewn as a bean or as a run: what changes (2026-10-14)

    python -m tools.detail_run_stitch run --image owl_kent [--pictures]
    python -m tools.detail_run_stitch md5 --image owl_kent     # bean arm's md5 only

`cfg.detail_layer_stitch` (`stage6_detail`): "bean" (default) sews each FDoG
line as the 0.73 mm three-pass bean; "run" sews it ONCE at
`stage6_detail.DETAIL_RUN_STITCH_MM` (a candidate, gate 1). PR #928 measured
the bean's cost on owl_kent: +5,267 stitches under the 1.0 mm needle floor.

Arms, on #928's route (`tools.detail_vs_lines`: photo lane forced, `photo_prep`
off, 127 mm, 40 wt), one `run_stages` per image, one `plan_stitches` per arm:

    off   - detail_layer off
    bean  - detail_layer on, detail_layer_stitch "bean" (today's output)
    run   - detail_layer on, detail_layer_stitch "run"

Per arm: stitches, trims, stitches under 1 mm (`hairline_lines_trial.
short_stitches`), thread laid, thread and flight over bare fabric
(`hairline_travel.measure_plan`), uncovered artwork new against OFF in mm2
(`hairline_renders.bare_cells`, preflight's instrument), the detail block's
own stitches and its stitches under 1 mm, and the plan md5. `md5` prints the
bean arm's md5 alone, so the same command run against another checkout's
`digitizer_core` checks "bean" is byte-for-byte that checkout's output.

Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import cv2

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools.detail_vs_lines import (  # noqa: E402
    IMAGES, ROUTE, WIDTH_MM, WT, _hstack, _label, densest_window, render_arm, _crop)
from tools.hairline_lines_trial import measure, write_jpeg  # noqa: E402
from tools.hairline_renders import bare_cells, bare_new_mm2  # noqa: E402
from tools.hairline_travel import measure_plan  # noqa: E402

OUT = ROOT.parent / "docs" / "renders" / "claude-detail-layer-run-stitch"
ARMS = {"off": None, "bean": "bean", "run": "run"}
BOX_MM = (14.0, 9.0)
FULL_W = 520


def arm_cfg(arm: str) -> PipelineConfig:
    mode = ARMS[arm]
    extra = {} if mode is None else {"detail_layer": True}
    if mode == "run":
        extra["detail_layer_stitch"] = "run"
    return PipelineConfig(target_width_mm=WIDTH_MM, thread_wt=WT, **ROUTE, **extra)


def detail_numbers(plan) -> dict:
    runs = [r for b in plan.blocks for r in b.runs if r.shape_id == "detail"]
    legs = [math.dist(a, c) for r in runs for a, c in zip(r.points, r.points[1:])]
    return {"detail_runs": len(runs),
            "detail_stitches": sum(len(r.points) for r in runs),
            "detail_under_1mm": sum(1 for d in legs if 0.01 < d < machine.MIN_STITCH_MM),
            "detail_thread_m": round(sum(legs) / 1000.0, 3),
            "detail_max_mm": round(max(legs), 3) if legs else 0.0}


def run_image(image: str, arms: list[str], pictures: bool) -> dict:
    path = IMAGES[image]
    result = run_stages(path, arm_cfg("bean"))       # carries source pixels
    p = preflight.prep(path, arm_cfg("off"), design_class=result.design_class)
    rows, plans, base = {}, {}, None
    for arm in arms:
        plan = plan_stitches(result, arm_cfg(arm))
        row = measure(plan)
        row.pop("hairline", None)
        t = measure_plan(plan, with_legacy=False)
        row.update({k: t[k] for k in ("thread_bare_mm", "flight_bare_mm")})
        row.update(detail_numbers(plan))
        bare = bare_cells(plan, result, p)
        row["bare_new_mm2"] = 0.0 if base is None else round(bare_new_mm2(bare, base), 2)
        if arm == "off":
            base = bare
        rows[arm], plans[arm] = row, plan
        print(image, arm, json.dumps({k: row[k] for k in (
            "stitches", "trims", "under_1mm", "detail_under_1mm", "bare_new_mm2", "md5")}),
            flush=True)
    if pictures and {"bean", "run"} <= set(plans):
        _pictures(image, plans)
    return {"image": image, "class": result.design_class, "route": ROUTE,
            "width_mm": WIDTH_MM, "thread_wt": WT, "arms": rows}


def _pictures(image: str, plans: dict) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pts = [p for b in plans["bean"].blocks for r in b.runs if r.shape_id == "detail"
           for p in r.points]
    box = densest_window(pts, BOX_MM)
    full, zoom = [], []
    for arm in ("off", "bean", "run"):
        if arm not in plans:
            continue
        r = render_arm(plans[arm], arm, WT)
        k = FULL_W / r["img"].shape[1]
        full.append(_label(cv2.resize(r["img"], None, fx=k, fy=k,
                                      interpolation=cv2.INTER_AREA), arm))
        if box is not None:
            zoom.append(_label(_crop(r["img"], r["meta"], box)[0], arm))
    write_jpeg(OUT / f"{image}_full.jpg", _hstack(full))
    if zoom:
        write_jpeg(OUT / f"{image}_zoom.jpg", _hstack(zoom))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("run", "md5"))
    ap.add_argument("--image", choices=sorted(IMAGES), required=True)
    ap.add_argument("--pictures", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "md5":
        result = run_stages(IMAGES[a.image], arm_cfg("bean"))
        print(a.image, "bean md5", measure(plan_stitches(result, arm_cfg("bean")))["md5"])
        return 0
    out = run_image(a.image, list(ARMS), a.pictures)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{a.image}.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
