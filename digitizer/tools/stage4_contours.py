#!/usr/bin/env python
"""Stage 4's largest-outer-contour keep: what a mask with two islands loses.

`stage4_vectorize.vectorize` traces each stage-3 mask with `RETR_CCOMP` and
keeps ONE outer contour, the largest (`outer = max(outers, ...)`). A mask
whose pixels form two separate islands of the same colour therefore sews
only the biggest and drops the rest with no warning — the stage-4 twin of
defect 61's stage-5 clip (PR #853).

Per fixture, matrix row and colour count, one `build_generation` with
stage 4's input captured, then per mask:

  * `outers` — how many outer contours `findContours` returns;
  * each island's area (mm², exact: its 8-connected pixel count / px²);
  * which one stage 4 keeps (the same `cv2.contourArea` key it uses) and the
    area dropped with the rest;
  * `above_floor` — whether a dropped island clears the floor stage 4 holds
    every region to (`min_area_mm2`, a quarter of `min_detail_mm²`, or the
    run tier's `RUN_MIN_AREA_MM2` + `RUN_MIN_LOOP_MM` rescue);
  * `claimed` — whether any region stage 4 emitted covers the dropped
    island. `ARTWORK_UNCOVERED` builds its "wanted" mask from region
    polygons (`preflight._uncovered_findings`), so an island no region
    claims is invisible to it by construction; this column is the
    empirical check of that.

    python -m tools.stage4_contours                        # drone, both garments
    python -m tools.stage4_contours --scorecard            # every corpus_scorecard FIXTURE x MATRIX
    python -m tools.stage4_contours --scorecard --max-colors 6   # the Studio's default
    python -m tools.stage4_contours photo/drone_render.png --matrix 0 --json

Report-only; changes nothing. Measured 2026-10-12, PR body.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import cv2  # noqa: E402
import numpy as np  # noqa: E402
from shapely.geometry import Point, Polygon  # noqa: E402

from digitizer_core import PipelineConfig, machine  # noqa: E402
from digitizer_core import pipeline  # noqa: E402
from digitizer_core.pipeline import build_generation  # noqa: E402
from digitizer_core.stage4_vectorize import _to_mm  # noqa: E402

DEFAULT = ("photo/drone_render.png",)


def floor_mm2(cfg) -> float:
    """Stage 4's sliver floor (`min_area_mm2` in `vectorize`)."""
    return (float(cfg.min_detail_mm) ** 2) * 0.25


def clears_floor(area_mm2: float, loop_mm: float, cfg) -> bool:
    """Would stage 4 keep a region of this area and perimeter? The sliver
    floor, or — a sub-detail mask only, which an island under the floor is —
    the run tier's rescue (`RUN_MIN_AREA_MM2` and `RUN_MIN_LOOP_MM`)."""
    if area_mm2 >= floor_mm2(cfg):
        return True
    return bool(cfg.small_shape_rescue
                and area_mm2 >= machine.RUN_MIN_AREA_MM2
                and loop_mm >= machine.RUN_MIN_LOOP_MM)


def census_masks(masks, p, cfg, regions=None) -> dict:
    """Every mask's outer-contour count and, for each mask with more than
    one, the islands stage 4 keeps and drops. `regions` (stage 4's output)
    answers whether any region claims a dropped island."""
    x0b, y0b, x1b, y1b = p.art_bbox
    cx, cy = (x0b + x1b) / 2.0, (y0b + y1b) / 2.0
    px2 = p.px_per_mm ** 2
    multi = []
    for idx, rm in enumerate(masks):
        y0, x0 = rm.origin
        padded = np.zeros((rm.crop.shape[0] + 2, rm.crop.shape[1] + 2), np.uint8)
        padded[1:-1, 1:-1] = rm.crop
        contours, hierarchy = cv2.findContours(
            padded, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE, offset=(x0 - 1, y0 - 1))
        if not contours or hierarchy is None:
            continue
        hier = hierarchy[0]
        outers = [i for i in range(len(contours)) if hier[i][3] == -1]
        if len(outers) < 2:
            continue
        kept = max(outers, key=lambda i: cv2.contourArea(contours[i]))
        # Exact island area: the 8-connected component the outer contour
        # traces, read from the contour's first pixel.
        _n, lab, stats, _c = cv2.connectedComponentsWithStats(padded, connectivity=8)
        islands = []
        for i in outers:
            px, py = contours[i].reshape(-1, 2)[0]
            comp = int(lab[py - (y0 - 1), px - (x0 - 1)])
            area = float(stats[comp, cv2.CC_STAT_AREA]) / px2
            ring = _to_mm(contours[i].reshape(-1, 2), cx, cy, p.px_per_mm)
            shell = Polygon(ring) if len(ring) >= 3 else None
            loop = float(shell.exterior.length) if shell is not None else 0.0
            isl = {"area_mm2": round(area, 3), "kept": i == kept,
                   "above_floor": clears_floor(area, loop, cfg)}
            if i != kept and regions is not None:
                # A dropped island is "claimed" when a region's polygon covers
                # its pixels — another region's ground, or nothing.
                pts = contours[i].reshape(-1, 2)
                cxm, cym = float(pts[:, 0].mean()), float(pts[:, 1].mean())
                probe = _to_mm(np.array([[cxm, cym]]), cx, cy, p.px_per_mm)[0]
                pt = Point(float(probe[0]), float(probe[1]))
                if shell is not None and shell.is_valid and not shell.contains(pt):
                    pt = shell.representative_point()
                isl["claimed"] = any(r.polygon.contains(pt) for r in regions)
                bx0, by0 = ring.min(axis=0)
                bx1, by1 = ring.max(axis=0)
                isl["bbox_mm"] = [round(float(v), 2) for v in (bx0, by0, bx1, by1)]
            islands.append(isl)
        dropped = [s for s in islands if not s["kept"]]
        multi.append({
            "mask": idx, "layer": int(rm.layer), "source": rm.source,
            "outers": len(outers),
            "islands": sorted(islands, key=lambda s: -s["area_mm2"]),
            "dropped_mm2": round(sum(s["area_mm2"] for s in dropped), 3),
            "dropped_above_floor_mm2": round(sum(s["area_mm2"] for s in dropped
                                                 if s["above_floor"]), 3),
            "unclaimed_above_floor": sum(1 for s in dropped
                                         if s["above_floor"] and not s.get("claimed", False)),
        })
    return {"masks": len(masks), "multi": multi}


def run(rel: str, cfg_kw: dict) -> dict:
    """One generation, stage 4's input and output captured, census taken."""
    seen: dict = {}
    orig = pipeline.vectorize

    def spy(masks, thread_indices, p, cfg):
        regions, dropped = orig(masks, thread_indices, p, cfg)
        seen.update(masks=list(masks), p=p, cfg=cfg, regions=list(regions))
        return regions, dropped

    pipeline.vectorize = spy
    try:
        build_generation(str(ROOT / "testdata" / rel), PipelineConfig(**cfg_kw))
    finally:
        pipeline.vectorize = orig
    c = census_masks(seen["masks"], seen["p"], seen["cfg"], seen["regions"])
    c.update(fixture=rel, cfg=cfg_kw, floor_mm2=round(floor_mm2(seen["cfg"]), 4))
    return c


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help="paths under testdata/")
    ap.add_argument("--scorecard", action="store_true",
                    help="every corpus_scorecard FIXTURE x MATRIX row")
    ap.add_argument("--matrix", type=int, default=None,
                    help="only this corpus_scorecard MATRIX row (0-based)")
    ap.add_argument("--max-colors", type=int, default=None)
    ap.add_argument("--json", action="store_true", help="one JSON line per run")
    args = ap.parse_args(argv)
    from tools.corpus_scorecard import FIXTURES, MATRIX
    rows = MATRIX if args.matrix is None else [MATRIX[args.matrix]]
    names = list(FIXTURES) if args.scorecard else (args.fixtures or list(DEFAULT))
    for rel in names:
        for m in rows:
            kw = dict(m)
            if args.max_colors:
                kw["max_colors"] = args.max_colors
            try:
                r = run(rel, kw)
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the sweep
                print(json.dumps({"fixture": rel, "cfg": kw,
                                  "error": f"{type(exc).__name__}: {exc}"}), flush=True)
                continue
            if args.json:
                print(json.dumps(r), flush=True)
                continue
            above = sum(x["dropped_above_floor_mm2"] for x in r["multi"])
            print(f"{rel} {kw.get('garment_id')} colours={kw.get('max_colors', 'default')}: "
                  f"{len(r['multi'])} of {r['masks']} masks multi-island, "
                  f"{sum(x['dropped_mm2'] for x in r['multi']):.2f} mm2 dropped, "
                  f"{above:.2f} mm2 above the {r['floor_mm2']} mm2 floor", flush=True)
            for x in r["multi"]:
                print(f"    mask {x['mask']} layer {x['layer']}: {x['outers']} outers, "
                      f"islands {[s['area_mm2'] for s in x['islands']]}, "
                      f"dropped {x['dropped_mm2']} mm2 "
                      f"(above floor {x['dropped_above_floor_mm2']}, "
                      f"unclaimed above floor {x['unclaimed_above_floor']})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
