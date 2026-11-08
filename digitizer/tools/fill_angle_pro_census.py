#!/usr/bin/env python
"""The pro's fill angle inside each of our fill shapes, over the committed
tripwire pairs -- the measurement `cfg.extra["fill_angle_pro_offset"]`'s angle
(`machine.FILL_ANGLE_PRO_DEG`) is read from (2026-11-07,
`docs/fill-angle-pro-offset-2026-11-07.md`).

    python -m tools.fill_angle_pro_census measure --runs DIR --figures OUT.json [--on | --slant] [--only SLUG ...]
    python -m tools.fill_angle_pro_census report --runs DIR [--rows] [--json OUT]

`measure` IS `tools.tripwire measure` (same digitize, same DST, same figures,
`--figures` is a tripwire pass), with one addition: stage 7's fill calls are
spied and DIR/<slug>/shapes.json gets, per fill shape, its polygon (stitch
frame, mm, y-down), the row angle it sewed, its principal axis and aspect, and
the PRO's angle inside it -- the doubled-angle mean of the pro's cells of type
fill (`scorecard.cell_stats`) whose centre lies inside the shape inset by
1 mm. Both DSTs go through one reader with NO mirror (a mirror out-scores the
true frame on near-symmetric art: Fremont's field read 108 deg mirrored, 72
true), translation-only registration (`scorecard.register`). `--on` sets the
flag (`extra.fill_angle_pro_offset`). No word reading.

`report` prints, per job and pooled, the pro's angle against the nearest
axis (0/90), against the shape's principal axis and against ours. Kappa is
the tripwire's (chance-corrected, floor 0); this tool prints no agreement of
its own.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics as st
import sys
from pathlib import Path

os.environ.setdefault("OPENCV_IPP", "avx2")
DIGITIZER = Path(__file__).resolve().parent.parent
for p in (DIGITIZER, DIGITIZER / "tools", DIGITIZER / "tools" / "pro_parity"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

FLAG = "fill_angle_pro_offset"
SLANT = "fill_angle_pro_slant"    # `--slant`: the per-shape sign + trims guard


# ------------------------------------------------------------------ measure
def census(plan, result, fills: dict, ours_dst: Path, pro_dst: Path) -> dict:
    import numpy as np
    from shapely.affinity import translate
    from shapely.geometry import Point
    import design_direction as dd
    import scorecard as sc
    from digitizer_core.stage6_fill import principal_angle_deg

    ours = dd.pro_segs(ours_dst, False)
    pro = dd.pro_segs(pro_dst, False)
    oxs = [q[0] for q in ours] + [q[2] for q in ours]
    oys = [q[1] for q in ours] + [q[3] for q in ours]
    pxs = [q[0] for q in pro] + [q[2] for q in pro]
    pys = [q[1] for q in pro] + [q[3] for q in pro]
    pro = sc.shifted(pro, (min(oxs) + max(oxs)) / 2 - (min(pxs) + max(pxs)) / 2,
                     (min(oys) + max(oys)) / 2 - (min(pys) + max(pys)) / 2)
    rdx, rdy, iou = sc.register(pro, ours, sc.bounds(pro, ours))
    our_r = sc.shifted(ours, rdx, rdy)
    bb = sc.bounds(pro, our_r)
    pa, pt, _ = sc.cell_stats(pro, bb)
    x0, y0, _x1, _y1 = bb
    by_shape: dict = {}
    for _b, run in plan.iter_runs():
        by_shape.setdefault(run.shape_id, []).append(run)
    meta = {r.shape_id: (r.meta or {}) for r in result.regions}
    rows = []
    for sid, info in fills.items():
        poly = info["poly"]
        angs, lens = [], []
        for r in by_shape.get(sid, []):
            if r.kind == "fill":
                a, ln = dd.run_direction(list(r.points))
                if a is not None:
                    angs.append(a)
                    lens.append(ln)
        sewn, _r = dd.doubled_mean(angs, lens)
        inner = translate(poly, rdx, rdy).buffer(-1.0)
        vals, satin_cells = [], 0
        if not inner.is_empty:
            minx, miny, maxx, maxy = inner.bounds
            for i in range(max(0, int((miny - y0) / sc.CELL) - 1), min(pa.shape[0], int((maxy - y0) / sc.CELL) + 2)):
                for j in range(max(0, int((minx - x0) / sc.CELL) - 1), min(pa.shape[1], int((maxx - x0) / sc.CELL) + 2)):
                    if np.isnan(pa[i, j]) or not inner.covers(Point(x0 + (j + 0.5) * sc.CELL, y0 + (i + 0.5) * sc.CELL)):
                        continue
                    if pt[i, j] == 2:
                        vals.append(math.degrees(pa[i, j]) % 180.0)
                    elif pt[i, j] == 1:
                        satin_cells += 1
        pm, pr = dd.doubled_mean(vals, [1.0] * len(vals))
        m = meta.get(sid, {})
        rows.append({"shape": sid, "area_mm2": round(poly.area, 1), "aspect": round(dd.aspect_of(poly), 3),
                     "pca_deg": round(principal_angle_deg(poly) % 180.0, 2),
                     "angle_arg": None if info["angle_arg"] is None else round(float(info["angle_arg"]), 2),
                     "sewn_deg": None if sewn is None else round(sewn, 2),
                     "pro_fill_cells": len(vals), "pro_satin_cells": satin_cells,
                     "pro_deg": None if pm is None else round(pm, 2), "pro_R": round(pr, 3),
                     "house_deg": m.get("satin_angle_deg"), "poly_wkt": poly.simplify(0.05).wkt})
    return {"iou": round(iou, 3), "shift_mm": [round(rdx, 2), round(rdy, 2)], "shapes": rows}


def measure(runs: Path, figures: Path, on: bool, only: list[str] | None, slant: bool = False) -> int:
    from digitizer_core import stage7_sequence as s7
    from digitizer_core.export import write_dst
    from tools import pro_baseline as pb
    from tools import pro_pair
    from tools import tripwire as tw
    extra = {f"extra.{SLANT}": True} if slant else ({f"extra.{FLAG}": True} if on else None)

    def digitize(runs_dir: Path, slugs: list[str]) -> None:     # pro_baseline.digitize, plus the spy
        for s in slugs:
            garment, width, art, pro_dst, *_ = pb.JOBS[s]
            fills: dict = {}
            real = s7.stitch_shape

            def spy(poly, shape_id, **kw):
                fills.setdefault(shape_id, {"poly": poly, "angle_arg": kw.get("angle_deg")})
                return real(poly, shape_id, **kw)

            s7.stitch_shape = spy
            try:
                d = pro_pair.digitize(pb.resolve(art), width, garment, extra)
            finally:
                s7.stitch_shape = real
            out = runs_dir / s
            out.mkdir(parents=True, exist_ok=True)
            write_dst(d.plan, out / "ours.dst")
            (out / "design.json").write_text(json.dumps(d.design), encoding="utf-8")
            print(s, d.plan.stats.stitch_count, d.plan.stats.trims, flush=True)
            try:
                c = census(d.plan, d.result, fills, out / "ours.dst", pb.resolve(pro_dst))
            except Exception as e:                       # noqa: BLE001 -- a row, not a crash
                c = {"error": f"{type(e).__name__}: {e}"[:300]}
            (out / "shapes.json").write_text(json.dumps(c, indent=1), encoding="utf-8")

    pb.digitize = digitize
    out = tw.measure(runs, only or tw.committed_jobs(), False, None)
    out["flag"] = {FLAG: bool(on), SLANT: bool(slant)}
    figures.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


# ------------------------------------------------------------------ report
def _sdiff(a: float, b: float) -> float:
    """signed a - b for two lines, in (-90, 90]"""
    d = (a - b) % 180.0
    return d - 180.0 if d > 90.0 else d


def _off_axis(a: float) -> float:
    """signed offset of line a from the nearest of 0/90, in (-45, 45]"""
    d = a % 90.0
    return d - 90.0 if d > 45.0 else d


def _quart(xs: list[float]) -> str:
    if not xs:
        return "n 0"
    xs = sorted(xs)
    n = len(xs)
    q = lambda f: xs[min(n - 1, int(f * (n - 1) + 0.5))]           # noqa: E731
    return f"n {n}, median {st.median(xs):.1f}, p25 {q(.25):.1f}, p75 {q(.75):.1f}, range {xs[0]:.1f} to {xs[-1]:.1f}"


def report(runs: Path, rows_out: bool, json_out: Path | None, min_cells: int = 2) -> int:
    pooled, largest = [], []
    for d in sorted(p for p in runs.iterdir() if (p / "shapes.json").exists()):
        j = json.loads((d / "shapes.json").read_text(encoding="utf-8"))
        if "error" in j:
            print(f"{d.name}: {j['error']}")
            continue
        rows = [r for r in j["shapes"] if r["pro_deg"] is not None and r["sewn_deg"] is not None
                and r["pro_fill_cells"] >= min_cells]
        for r in rows:
            r.update(job=d.name, pro_off_axis=_off_axis(r["pro_deg"]), ours_off_axis=_off_axis(r["sewn_deg"]),
                     pro_vs_pca=_sdiff(r["pro_deg"], r["pca_deg"]), pro_vs_ours=_sdiff(r["pro_deg"], r["sewn_deg"]))
        pooled += rows
        if rows:
            big = max(rows, key=lambda r: r["area_mm2"])
            largest.append(big)
            print(f"{d.name:22s} usable {len(rows)}/{len(j['shapes'])}  largest {big['area_mm2']:.0f} mm2: "
                  f"pro {big['pro_deg']:.1f} (off axis {big['pro_off_axis']:+.1f})  ours {big['sewn_deg']:.1f}  pca {big['pca_deg']:.1f}")
        else:
            print(f"{d.name:22s} usable 0/{len(j['shapes'])}")
        if rows_out:
            for r in sorted(rows, key=lambda r: -r["area_mm2"]):
                print(f"    {r['shape']:12s} {r['area_mm2']:8.1f} mm2 aspect {r['aspect']:4.2f} cells {r['pro_fill_cells']:3d}  "
                      f"pro {r['pro_deg']:6.1f} ours {r['sewn_deg']:6.1f} pca {r['pca_deg']:6.1f}  "
                      f"pro off axis {r['pro_off_axis']:+6.1f}  pro-pca {r['pro_vs_pca']:+6.1f}  pro-ours {r['pro_vs_ours']:+6.1f}")
    print()
    print(f"pooled over {len(pooled)} shapes (>= {min_cells} pro fill cells):")
    for key in ("pro_off_axis", "ours_off_axis", "pro_vs_pca", "pro_vs_ours"):
        print(f"  |{key}| {_quart([abs(r[key]) for r in pooled])}")
    print(f"largest fill per job: |pro off axis| {_quart([abs(r['pro_off_axis']) for r in largest])}; "
          f"sign + on {sum(r['pro_off_axis'] > 0 for r in largest)} of {len(largest)}")
    if json_out:
        json_out.write_text(json.dumps({"pooled": pooled, "largest": largest}, indent=1), encoding="utf-8")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=("measure", "report"))
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--figures", type=Path)
    ap.add_argument("--on", action="store_true")
    ap.add_argument("--slant", action="store_true")
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--rows", action="store_true")
    ap.add_argument("--json", dest="json_out", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "measure":
        if not a.figures:
            ap.error("measure needs --figures")
        return measure(a.runs, a.figures, a.on, a.only, a.slant)
    return report(a.runs, a.rows, a.json_out)


if __name__ == "__main__":
    sys.exit(main())
