#!/usr/bin/env python
"""Which satin/fill gate rejected the ground the PRO sewed as satin?

MASTER_SCOPE live defect 5: the engine sews about the right AMOUNT of satin
(pro 53.6% / ours 47.7%) in substantially the wrong PLACES (0.278 corrected
agreement). `stage6_satin.is_satin_candidate` is three consecutive rejection
gates with no path that promotes a shape back to satin, so every
pro-satin-sewn-as-fill cell is one of those three firing. This probe says
WHICH, and by how much the shape missed.

It is an instrument, not engine code: nothing here is imported by the
pipeline. Design: `docs/superpowers/specs/2026-08-16-satin-routing-gate-
attribution-design.md`.

Method, and its one deliberate reuse
------------------------------------
The join to the pro's ground truth is `scorecard.py`'s own `cell_stats` and
registration — the same 2 mm cells and the same translation search the score
reports — so a number here can be read against a number there. What is NOT
reused is the verdict under test: that comes from `classify_ribbon` directly,
on the artwork polygon `prep_all.run_ours` recorded in `ours_regions.json`,
which is the same object stage 7 hands the classifier.

`classify_ribbon` runs with `full_metrics=True`, so a shape the width cap
rejected still reports what the distance transform would have said about it.
The pipeline never does that — it costs a medial axis per shape — but a probe
asking "would another gate have taken this one?" needs the answer.

Usage
-----
    PYTHONPATH=. python tools/pro_parity/gateprobe.py <prepped-design-dir>...
    PYTHONPATH=. python tools/pro_parity/gateprobe.py --csv out.csv <dirs>...

A prepped design directory is what `prep_all.py` / `prep_both.py` write:
`pro_stitches.csv`, `ours_stitches.csv`, `ours_regions.json`.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import shapely.wkt
from shapely.affinity import translate
from shapely.geometry import Point
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scorecard  # noqa: E402
from digitizer_core import machine  # noqa: E402
from digitizer_core.stage6_satin import classify_ribbon  # noqa: E402

TYPE_NAMES = {0: "run", 1: "satin", 2: "fill"}

# How far past its own gate a rejected shape sat, in that gate's units. A
# promotion path is cheap when the misses cluster just past the line and
# expensive when they are scattered, which is the whole reason slice 1 runs
# before slice 2.
MARGIN_UNITS = {
    "width_cap": "mm over the 2A/P cap",
    "aspect": "below the 3.0 aspect the gate demands",
    "dt_irregular": "dt_cv over the 0.5 the regularity term allows",
    "dt_p90_cap": "mm over the cap, on the DT's p90",
}


def _margin(reason: str, m: dict, cap: float) -> float | None:
    if reason == "width_cap":
        return m["ribbon_w"] - cap
    if reason == "aspect":
        return 3.0 - m["aspect"]
    if reason == "dt_irregular":
        return m["dt_cv"] - 0.5
    if reason == "dt_p90_cap":
        return m["dt_p90_mm"] - cap
    return None


def _cells_of(poly, bb, pt_shape) -> list[tuple[int, int]]:
    """The 2 mm cells whose CENTRE falls inside the polygon.

    Centres rather than any-overlap: a cell's stitch-type reading is a
    property of what was sewn across the whole cell, so crediting a shape with
    a cell it only clips the corner of would attribute the pro's verdict about
    a NEIGHBOURING shape to this one.
    """
    x0, y0, _x1, _y1 = bb
    H, W = pt_shape
    px0, py0, px1, py1 = poly.bounds
    j0 = max(0, int((px0 - x0) / scorecard.CELL))
    j1 = min(W - 1, int((px1 - x0) / scorecard.CELL) + 1)
    i0 = max(0, int((py0 - y0) / scorecard.CELL))
    i1 = min(H - 1, int((py1 - y0) / scorecard.CELL) + 1)
    if j1 < j0 or i1 < i0:
        return []
    ready = prep(poly)
    out = []
    for i in range(i0, i1 + 1):
        cy = y0 + (i + 0.5) * scorecard.CELL
        for j in range(j0, j1 + 1):
            cx = x0 + (j + 0.5) * scorecard.CELL
            if ready.contains(Point(cx, cy)):
                out.append((i, j))
    return out


def probe_design(dirpath: Path, cap: float) -> list[dict]:
    slug = dirpath.name
    regions_path = dirpath / "ours_regions.json"
    if not regions_path.exists():
        print(f"  {slug}: no ours_regions.json — prepped before 2026-08-16?")
        return []
    regions = json.loads(regions_path.read_text())
    if not regions or "wkt" not in regions[0]:
        print(f"  {slug}: ours_regions.json carries no `wkt` — re-prep needed")
        return []

    _pro_rows, pro, _psrc, _pt = scorecard.load_side(dirpath, "pro", slug)
    _our_rows, our, _osrc, _ot = scorecard.load_side(dirpath, "ours", slug)
    dx, dy, _iou = scorecard.register(pro, our, scorecard.bounds(pro, our))
    our_r = scorecard.shifted(our, dx, dy)
    bb = scorecard.bounds(pro, our_r)
    _pa, pt, _ptot = scorecard.cell_stats(pro, bb)
    _oa, ot, _otot = scorecard.cell_stats(our_r, bb)

    rows = []
    for r in regions:
        poly = shapely.wkt.loads(r["wkt"])
        if poly.is_empty:
            continue
        # Registration aligns OUR stitches onto the pro's frame, so our
        # polygons move with them. Classification itself is translation
        # invariant, so the verdict is taken on the polygon as recorded.
        v = classify_ribbon(poly, cap, full_metrics=True)
        cells = _cells_of(translate(poly, dx, dy), bb, pt.shape)
        pro_hist: Counter = Counter()
        our_hist: Counter = Counter()
        for i, j in cells:
            if pt[i, j] >= 0:
                pro_hist[int(pt[i, j])] += 1
            if ot[i, j] >= 0:
                our_hist[int(ot[i, j])] += 1
        pro_dom = pro_hist.most_common(1)[0][0] if pro_hist else -1
        our_dom = our_hist.most_common(1)[0][0] if our_hist else -1
        rows.append({
            "design": slug,
            "shape_id": r["shape_id"],
            "area_mm2": r["area_mm2"],
            "tier": r.get("tier"),
            "cells": len(cells),
            "pro_cells": sum(pro_hist.values()),
            "pro_satin_cells": pro_hist.get(1, 0),
            "pro_fill_cells": pro_hist.get(2, 0),
            "pro_run_cells": pro_hist.get(0, 0),
            "pro_dominant": TYPE_NAMES.get(pro_dom, "none"),
            "our_sewn_dominant": TYPE_NAMES.get(our_dom, "none"),
            "verdict": "satin" if v.satin else "fill",
            "reason": v.reason,
            "margin": _margin(v.reason, v.metrics, cap),
            **{k: round(x, 4) for k, x in v.metrics.items()},
        })
    return rows


def summarise(rows: list[dict], cap: float) -> None:
    graded = [r for r in rows if r["pro_cells"] > 0]
    print(f"\n{len(rows)} shapes across "
          f"{len({r['design'] for r in rows})} designs; "
          f"{len(graded)} land on ground the pro also sewed.\n")

    # The defect, restated on this population: ground the pro satins that our
    # classifier declines to satin.
    lost = defaultdict(lambda: {"cells": 0, "shapes": 0, "margins": []})
    for r in graded:
        if r["pro_dominant"] != "satin" or r["verdict"] == "satin":
            continue
        g = lost[r["reason"]]
        g["cells"] += r["pro_satin_cells"]
        g["shapes"] += 1
        if r["margin"] is not None:
            g["margins"].append(r["margin"])

    total_pro_satin = sum(r["pro_satin_cells"] for r in graded)
    lost_cells = sum(g["cells"] for g in lost.values())
    print(f"PRO-SATIN GROUND WE DECLINE TO SATIN: {lost_cells} of "
          f"{total_pro_satin} cells ({_pct(lost_cells, total_pro_satin)})\n")
    print(f"{'gate':<14}{'shapes':>7}{'cells':>8}{'share':>8}   "
          f"median margin (p90)   units")
    for reason, g in sorted(lost.items(), key=lambda kv: -kv[1]["cells"]):
        if g["margins"]:
            med = float(np.median(g["margins"]))
            p90 = float(np.percentile(g["margins"], 90))
            margin = f"{med:>10.2f} ({p90:.2f})"
        else:
            margin = f"{'—':>10}        "
        print(f"{reason:<14}{g['shapes']:>7}{g['cells']:>8}"
              f"{_pct(g['cells'], lost_cells):>8}   {margin}   "
              f"{MARGIN_UNITS.get(reason, '')}")

    # The other direction, which the confusion matrix says is nearly as large.
    over = [r for r in graded
            if r["pro_dominant"] == "fill" and r["verdict"] == "satin"]
    over_cells = sum(r["pro_fill_cells"] for r in over)
    total_pro_fill = sum(r["pro_fill_cells"] for r in graded)
    print(f"\nPRO-FILL GROUND WE WOULD SATIN: {over_cells} of "
          f"{total_pro_fill} cells ({_pct(over_cells, total_pro_fill)}) "
          f"across {len(over)} shapes")
    if over:
        widths = [r["ribbon_w"] for r in over]
        print(f"  their ribbon widths: median {np.median(widths):.2f} mm, "
              f"p90 {np.percentile(widths, 90):.2f} mm (cap {cap})")

    # Live defect 2: satin under the width the machine can hold.
    hair = [r for r in graded
            if r["verdict"] == "satin" and 0 < r["dt_p90_mm"] < 1.0]
    print(f"\nSUB-1mm SATIN (live defect 2): {len(hair)} shapes classify satin "
          f"at a DT p90 width under 1.0 mm")


def _pct(a: int, b: int) -> str:
    return f"{100.0 * a / b:.1f}%" if b else "—"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("dirs", nargs="+", help="prepped design directories")
    ap.add_argument("--csv", help="write the per-shape table here")
    ap.add_argument("--cap", type=float, default=machine.SATIN_MAX_WIDTH_MM)
    args = ap.parse_args()

    rows: list[dict] = []
    for d in args.dirs:
        p = Path(d)
        if not (p / "ours_stitches.csv").exists():
            continue
        print(f"probing {p.name} ...", flush=True)
        try:
            rows.extend(probe_design(p, args.cap))
        except Exception as exc:                      # noqa: BLE001
            print(f"  {p.name}: FAILED — {type(exc).__name__}: {exc}")

    if not rows:
        print("nothing probed")
        return
    if args.csv:
        keys = list(rows[0].keys())
        with open(args.csv, "w", newline="") as f:
            f.write(",".join(keys) + "\n")
            for r in rows:
                f.write(",".join("" if r[k] is None else str(r[k])
                                 for k in keys) + "\n")
        print(f"wrote {args.csv} ({len(rows)} shapes)")
    summarise(rows, args.cap)


if __name__ == "__main__":
    main()
