#!/usr/bin/env python
"""Does EMB-Bot sew the same logo whether the customer sends the master file
or the JPEG they actually have?

Why (2026-11-21). Every fixture here is scored as committed. A customer's
file is whatever their email, website or social page handed them, which is
almost always a JPEG — often re-saved, often a shrunk thumbnail. No
instrument asked whether that changes what sews. This one makes the
deliveries from each logo's committed file and compares each digitize with
the same logo digitized from the file as committed (the reference), so the
score says what the DELIVERY cost, not what the engine cannot do at all.

Deliveries (`DELIVERIES`):

  q95 / q75 / q50 / q30   one JPEG save at that quality (4:2:0 chroma, as
                          every browser and phone writes it)
  q75x2                   saved at q75, opened, saved at q75 again (an
                          email forward, a CMS re-upload)
  thumb                   shrunk to 60% (INTER_AREA) then q70 — the copy a
                          social page serves

A source with transparency is flattened onto white first, as a JPEG export
does; that changes the background, so `flat_white` (the PNG flattened,
lossless) is run too, separating "lost its alpha" from "got compressed".

Scored with `tools/lowres_detail.score` (agree, fine) on the regions,
rasterised in the design's own millimetre frame, plus the routing (stage 0
class), the thread count and the plan's stitches and trims. `cones+` /
`cones-` count threads the delivery adds or drops against the reference's
set (CIE76 > 25 from every reference thread = a different cone). A delivery
whose art box moves more than 3 mm is refused as a different design, as
`lowres_detail` does.

    .venv/bin/python -m tools.delivery_jpeg                       # every logo, every delivery
    .venv/bin/python -m tools.delivery_jpeg --logos tires drone --deliveries q50 q30 --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from tools.lowres_detail import FRAME_TOL_MM, SAME_COLOUR_DE, _rasterise, score  # noqa: E402

LOGOS = {
    "becker": "becker_marine_logo.png",
    "enthusiast": "photo/enthusiast_logo.png",
    "fremont": "photo/logo_hotel_fremont.webp",
    "golden_tee": "photo/logo_golden_tee.jpg",
    "bridge": "photo/logo_bridge_bar.jpg",
    "drone": "photo/drone_render.png",
    "whitebg": "logo_whitebg.png",
    "tires": "logo_script_tires.png",
    "gaulke": "photo/logo_gaulke_roofing.png",
}

# name -> list of (scale, jpeg quality) saves, applied in order. scale 1 and
# quality None is a lossless PNG write (only `flat_white` uses it).
DELIVERIES = {
    "flat_white": [(1.0, None)],
    "q95": [(1.0, 95)],
    "q75": [(1.0, 75)],
    "q50": [(1.0, 50)],
    "q30": [(1.0, 30)],
    "q75x2": [(1.0, 75), (1.0, 75)],
    "thumb": [(0.6, 70)],
}


def flatten_on_white(raw: np.ndarray) -> np.ndarray:
    """BGR(A) -> BGR, alpha composited over white (what a JPEG export does)."""
    if raw.ndim == 2:
        return cv2.cvtColor(raw, cv2.COLOR_GRAY2BGR)
    if raw.shape[2] == 3:
        return raw
    a = raw[:, :, 3:4].astype(np.float32) / 255.0
    out = raw[:, :, :3].astype(np.float32) * a + 255.0 * (1.0 - a)
    return np.clip(np.round(out), 0, 255).astype(np.uint8)


def deliver(raw: np.ndarray, steps: list[tuple[float, int | None]]) -> np.ndarray:
    """Apply one delivery's saves to a BGR(A) image; returns BGR bytes-decoded."""
    img = flatten_on_white(raw)
    for scale, q in steps:
        if scale != 1.0:
            img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        if q is not None:
            ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, q])
            assert ok
            img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    return img


def _one(args) -> dict:
    logo, rel, width, delivery, plan_too, scratch = args
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_core.threads import chart_for

    path = ROOT / "testdata" / rel
    if delivery != "ref":
        raw = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
        img = deliver(raw, DELIVERIES[delivery])
        path = Path(scratch) / f"{logo}__{delivery}.png"     # lossless carrier of the decoded JPEG
        cv2.imwrite(str(path), img)
    cfg = PipelineConfig(target_width_mm=width, garment_id="left_chest", max_colors=6)
    gen = build_generation(str(path), cfg)
    result = finish_generation(gen.fork(), cfg)
    chart = chart_for(cfg)
    rgb, mask = _rasterise(result, chart)
    used = sorted({r.thread_index for r in result.regions if r.meta.get("stitched", True)})
    row = {"logo": logo, "arm": delivery, "class": gen.classification_class,
           "regions": sum(1 for r in result.regions if r.meta.get("stitched", True)),
           "threads": len(used),
           "thread_rgb": [list(map(int, chart[i].rgb)) for i in used],
           "size_mm": [round(v, 1) for v in result.design_size_mm]}
    if plan_too:
        plan = plan_stitches(result, cfg)
        row.update(stitches=plan.stats.stitch_count, trims=plan.stats.trims)
    return {"row": row, "rgb": rgb, "mask": mask}


def cone_diff(ref_rgb: list, arm_rgb: list) -> tuple[int, int]:
    """(added, dropped): threads with no reference thread within SAME_COLOUR_DE
    CIE76, and reference threads with no arm thread within it."""
    from digitizer_core.threads import rgb_to_lab
    if not ref_rgb or not arm_rgb:
        return len(arm_rgb), len(ref_rgb)
    a = rgb_to_lab(np.asarray(ref_rgb, np.float64))
    b = rgb_to_lab(np.asarray(arm_rgb, np.float64))
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return int((d.min(axis=0) > SAME_COLOUR_DE).sum()), int((d.min(axis=1) > SAME_COLOUR_DE).sum())


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--logos", nargs="+", default=list(LOGOS), choices=list(LOGOS))
    ap.add_argument("--deliveries", nargs="+", default=list(DELIVERIES), choices=list(DELIVERIES))
    ap.add_argument("--width", type=float, default=80.0)
    ap.add_argument("--no-plan", action="store_true")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)

    with tempfile.TemporaryDirectory() as scratch:
        jobs = []
        for logo in a.logos:
            jobs.append((logo, LOGOS[logo], a.width, "ref", not a.no_plan, scratch))
            jobs += [(logo, LOGOS[logo], a.width, d, not a.no_plan, scratch) for d in a.deliveries]
        with ProcessPoolExecutor(max_workers=a.workers) as ex:
            done = list(ex.map(_one, jobs))

    by_logo: dict[str, list[dict]] = {}
    for d in done:
        by_logo.setdefault(d["row"]["logo"], []).append(d)
    rows = []
    print(f"at {a.width:g} mm, left chest, each delivery scored against the logo as committed")
    print(f"{'logo':11s} {'arm':10s} {'class':10s} {'reg':>4s} {'thr':>3s} {'+':>2s} {'-':>2s} "
          f"{'stitches':>8s} {'trims':>5s} {'agree':>6s} {'fine':>6s}")
    for logo, ds in by_logo.items():
        ref = next(d for d in ds if d["row"]["arm"] == "ref")
        for d in ds:
            r = d["row"]
            r["cones_added"], r["cones_dropped"] = cone_diff(ref["row"]["thread_rgb"], r["thread_rgb"])
            moved = max(abs(x - y) for x, y in zip(r["size_mm"], ref["row"]["size_mm"]))
            if moved > FRAME_TOL_MM:
                r["refused"] = f"art box differs from the reference by {moved:.1f} mm"
                print(f"{logo:11s} {r['arm']:10s} {r['class']:10s} refused: {r['refused']} "
                      f"(size {r['size_mm']} vs {ref['row']['size_mm']})")
            else:
                r.update(score(ref["rgb"], ref["mask"] > 0, d["rgb"], d["mask"] > 0))
                print(f"{logo:11s} {r['arm']:10s} {r['class']:10s} {r['regions']:4d} {r['threads']:3d} "
                      f"{r['cones_added']:2d} {r['cones_dropped']:2d} {r.get('stitches', 0):8d} "
                      f"{r.get('trims', 0):5d} {r['agree']:6.3f} {r['fine']:6.3f}")
            rows.append(r)
    if a.json:
        a.json.write_text(json.dumps({"width_mm": a.width, "rows": rows}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
