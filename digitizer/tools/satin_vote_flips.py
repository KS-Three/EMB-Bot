#!/usr/bin/env python
"""How often the satin-vs-fill verdict flips under a pixel of erosion, with
a stability arm (`cfg.extra["satin_fill_vote"]`, or `["satin_fill_hysteresis"]`
with `--arm hysteresis`) OFF and ON, over a census's regions.

MEASUREMENT ONLY. Reads the OFF arm `tools.satin_fill_census digitize` wrote
(`RUNS/<slug>/ours.json`: every region's polygon and meta) and asks the
classifier four questions per sewn region, on the SAME polygon both arms saw:

  off        `classify_ribbon` as shipped, on the polygon as drawn
  off_eroded the same, on the polygon eroded by `--erode-px` classifier pixels
             (`stage6_satin._RASTER_PX_PER_MM`: 1 px = 0.167 mm)
  on / on_eroded   the same two, with the arm on: `vote=True` (`--arm vote`,
             the default) or `hysteresis=True` (`--arm hysteresis`, 2026-11-07)

A region FLIPS under an arm when its two readings differ; it CHANGES when the
ON reading differs from the OFF one. The width ceiling per region follows
`stage7_sequence._satin_ceiling_for` (no ceiling and the per-stroke rung for a
text-cluster member under `satin_lettering_split`); the design class is taken
as flat, which is what every committed pair is (Law 31's floor applies to the
photo classes only, so the class cannot move a verdict here). This is the
classifier's flip count, not the sewn plan's: a tier the user forced, or a
word tier, is not re-asked.

    python -m tools.satin_vote_flips --runs OFF_DIR [--arm vote|hysteresis] [--erode-px 1.0] [--only SLUG ...]

With `--arm hysteresis`, `--json` rows also carry the ON reading's `reason` and
which bands abstained (`hyst`), so a changed or flipping region can be read as a
margin, not a bare bool.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")   # the test env's IPP path (tests/conftest.py)

DIGITIZER = Path(__file__).resolve().parent.parent
for p in (str(DIGITIZER), str(DIGITIZER / "tools")):
    if p not in sys.path:
        sys.path.insert(0, p)

SEWN = ("fill", "satin", "run", "bean", "border")
#: the classifier keyword each `--arm` turns on
ARMS = {"vote": "vote", "hysteresis": "hysteresis"}


class _Region:
    """Just what `is_text` and the ceiling helper read."""

    def __init__(self, polygon, meta):
        self.polygon = polygon
        self.meta = meta


def _eroded(poly, px: float):
    from digitizer_core.stage6_satin import _RASTER_PX_PER_MM
    e = poly.buffer(-px / _RASTER_PX_PER_MM)
    if e.is_empty:
        return None
    if e.geom_type == "MultiPolygon":
        e = max(e.geoms, key=lambda g: g.area)
    return e if e.geom_type == "Polygon" else None


def job_rows(slug: str, runs: Path, erode_px: float, arm: str = "vote") -> list[dict]:
    import shapely.wkt
    from digitizer_core import PipelineConfig
    from digitizer_core.machine import satin_ceiling_mm
    from digitizer_core.stage6_satin import classify_ribbon
    from digitizer_core.stage7_sequence import _satin_ceiling_for
    from digitizer_service.app import _parse_config
    from tools import pro_pair
    from tools.pro_baseline import JOBS

    garment, width, *_ = JOBS[slug]
    cfg = PipelineConfig(**_parse_config(json.dumps(pro_pair.request(width, garment))))
    info = json.loads((runs / slug / "ours.json").read_text(encoding="utf-8"))
    rows = []
    for r in info["regions"]:
        if not any(k.split(":")[0] in SEWN for k in (r.get("kinds") or {})):
            continue
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        if not poly.is_valid:
            poly = poly.buffer(0)
        if poly.geom_type != "Polygon":
            continue
        reg = _Region(poly, r.get("meta") or {})
        cap, per_stroke, _fold = _satin_ceiling_for(reg, cfg, satin_ceiling_mm(cfg))
        kw = dict(per_stroke=per_stroke, polygon_axis=cfg.satin_polygon_axis,
                  area_weighted=cfg.classify_area_weighted)
        small = _eroded(poly, erode_px)
        on_kw = {**kw, ARMS[arm]: True}
        on = classify_ribbon(poly, cap, **on_kw)
        row = {"id": r["id"], "area": round(poly.area, 1), "lettering": math.isinf(cap),
               "off": classify_ribbon(poly, cap, **kw).satin,
               "on": on.satin}
        if arm == "hysteresis":
            row["reason"] = on.reason
            row["hyst"] = [k[5:] for k in ("hyst_aspect", "hyst_cv") if on.metrics.get(k)]
        if small is not None:
            row["off_eroded"] = classify_ribbon(small, cap, **kw).satin
            row["on_eroded"] = classify_ribbon(small, cap, **on_kw).satin
        rows.append(row)
    return rows


def summarise(per_job: dict[str, list[dict]]) -> dict:
    tot = {"regions": 0, "graded": 0, "changed": 0, "flip_off": 0, "flip_on": 0,
           "changed_fill_to_satin": 0, "changed_satin_to_fill": 0}
    jobs = {}
    for slug, rows in per_job.items():
        j = {"regions": len(rows), "graded": 0, "changed": 0, "flip_off": 0, "flip_on": 0}
        for r in rows:
            if r["off"] != r["on"]:
                j["changed"] += 1
                tot["changed_fill_to_satin" if r["on"] else "changed_satin_to_fill"] += 1
            if "off_eroded" in r:
                j["graded"] += 1
                j["flip_off"] += r["off"] != r["off_eroded"]
                j["flip_on"] += r["on"] != r["on_eroded"]
        jobs[slug] = j
        for k in ("regions", "graded", "changed", "flip_off", "flip_on"):
            tot[k] += j[k]
    return {"jobs": jobs, "total": tot}


def table(summary: dict, erode_px: float) -> str:
    L = [f"| job | regions | changed OFF->ON | flips under {erode_px:g} px erosion OFF | ON |",
         "|---|---|---|---|---|"]
    for s, j in summary["jobs"].items():
        L.append(f"| {s} | {j['regions']} | {j['changed']} | {j['flip_off']} | {j['flip_on']} |")
    t = summary["total"]
    L.append(f"| **total** | {t['regions']} | {t['changed']} (fill->satin {t['changed_fill_to_satin']}, "
             f"satin->fill {t['changed_satin_to_fill']}) | {t['flip_off']} | {t['flip_on']} |")
    return "\n".join(L)


def main(argv=None) -> int:
    from tools.pro_baseline import JOBS
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--runs", type=Path, required=True, help="the OFF arm's runs dir")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--erode-px", type=float, default=1.0)
    ap.add_argument("--arm", choices=tuple(ARMS), default="vote",
                    help="which stability arm ON means (default: the vote)")
    ap.add_argument("--json", type=Path, help="write per-region rows here")
    a = ap.parse_args(argv)
    per_job = {}
    for s in JOBS:
        if (a.only and s not in a.only) or not (a.runs / s / "ours.json").exists():
            continue
        per_job[s] = job_rows(s, a.runs, a.erode_px, a.arm)
        j = summarise({s: per_job[s]})["total"]
        print(s, "regions", j["regions"], "changed", j["changed"],
              "flips off/on", j["flip_off"], j["flip_on"], flush=True)
    summary = summarise(per_job)
    if a.json:
        a.json.write_text(json.dumps({"erode_px": a.erode_px, "arm": a.arm, "summary": summary,
                                      "rows": per_job}, indent=1),
                          encoding="utf-8")
    print()
    print(table(summary, a.erode_px))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
