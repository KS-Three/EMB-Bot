"""Do `subpixel_edges` and `curve_turn_deg` change the SHIPPED fill angle?

Three arms per prepped corpus design: shipped (both flags on), `curve_turn_deg`
off, and both off. Every automatic fill-angle choice
(`stage6_fill.best_fill_angle_deg`) is recorded with its shape's id,
centroid, area and vertex count. In the shipped arm it also records the
column MARGIN between the winning angle and the runner-up: 0 means an exact
column tie decided only by closeness to the PCA angle.

Shapes are matched across arms by `shape_id` first. The flags nudge outlines,
and a `shape_id` is a hash of the rounded centroid, so a shape near a rounding
boundary can be renamed; those fall back to the nearest centroid within 1 mm
whose area is within 10%. Anything still unmatched is reported and NOT counted
as changed, so the changed counts are a floor.

    cd digitizer
    PRO_PARITY_OUT=<prepped corpus> .venv/Scripts/python -m tools.pro_parity.angleflags

Writes `angleflags.json` (every record) into PRO_PARITY_OUT and prints the
summary. Findings: docs/flag-runtime-bills-2026-09-12.md, "The two flags turn
fill rows".
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

from shapely import affinity

from digitizer_core import stage6_fill as S6
from digitizer_core.pipeline import plan_stitches, run_stages

from .prep_all import parity_config

OUT = Path(os.environ.get("PRO_PARITY_OUT", "pro_parity_out"))
ARMS = [("shipped", {}),
        ("curve_off", {"curve_turn_deg": None}),
        ("both_off", {"subpixel_edges": False, "curve_turn_deg": None})]
# `machine_lc` is the same art as `machine_hat` (33,921 vs 33,898 stitches);
# counting both would count one design's fills twice.
DUPLICATES = {"machine_lc"}
TURN_DEG = 10.0


def _width_mm(meta: dict) -> float:
    return (meta["size_px"][0] - 2 * meta["pad_px"]) / meta["scale_px_per_mm"]


def angular_dist(a: float, b: float) -> float:
    """Row directions are axial: 0 and 180 degrees are the same rows."""
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def column_margin(poly, row_mm: float) -> int | None:
    """Columns the runner-up angle needs beyond the winner (same ranking key
    as `best_fill_angle_deg`). None when fewer than two angles cut anything."""
    pca = S6.principal_angle_deg(poly)
    cands = [i * (180.0 / S6._FILL_ANGLE_CANDIDATES)
             for i in range(S6._FILL_ANGLE_CANDIDATES)] + [pca]
    keys = []
    for angle in cands:
        rot = affinity.rotate(poly, -angle, origin=(0, 0), use_radians=False)
        cols = len(S6._columns(S6._row_spans(rot, row_mm)))
        if cols:
            keys.append((cols, angular_dist(angle, pca), angle))
    keys.sort()
    return keys[1][0] - keys[0][0] if len(keys) >= 2 else None


def match(ship: list[dict], other: list[dict]) -> list[tuple[dict, dict | None]]:
    """Pair each shipped record with at most one record from `other`."""
    pairs, used, by_id = [], set(), {}
    for j, o in enumerate(other):
        by_id.setdefault(o["shape_id"], []).append(j)
    for s in ship:
        same = [j for j in by_id.get(s["shape_id"], []) if j not in used]
        if same:
            j = min(same, key=lambda j: math.hypot(other[j]["cx"] - s["cx"],
                                                   other[j]["cy"] - s["cy"]))
            used.add(j)
            pairs.append((s, other[j]))
            continue
        best = None
        for j, o in enumerate(other):
            if j in used:
                continue
            dist = math.hypot(o["cx"] - s["cx"], o["cy"] - s["cy"])
            if dist <= 1.0 and abs(o["area"] - s["area"]) <= 0.10 * max(s["area"], 1e-9):
                if best is None or dist < best[0]:
                    best = (dist, j)
        if best:
            used.add(best[1])
            pairs.append((s, other[best[1]]))
        else:
            pairs.append((s, None))
    return pairs


def record(slugs: list[str]) -> list[dict]:
    shipped_search = S6.best_fill_angle_deg
    rec: list[dict] = []
    state = {"arm": "", "slug": ""}

    def wrapped(poly, row_mm):
        angle = shipped_search(poly, row_mm)
        c = poly.centroid
        row = {"arm": state["arm"], "slug": state["slug"],
               # the only production caller is stitch_shape, whose
               # `shape_id` parameter is the shape being filled
               "shape_id": sys._getframe(1).f_locals.get("shape_id"),
               "cx": c.x, "cy": c.y, "area": poly.area,
               "verts": len(poly.exterior.coords)
               + sum(len(i.coords) for i in poly.interiors),
               "angle": angle}
        if state["arm"] == "shipped":
            row["margin"] = column_margin(poly, row_mm)
        rec.append(row)
        return angle

    S6.best_fill_angle_deg = wrapped
    try:
        t0 = time.time()
        for slug in slugs:
            d = OUT / slug
            width = _width_mm(json.loads((d / "art_meta.json").read_text()))
            for arm, over in ARMS:
                state.update(arm=arm, slug=slug)
                cfg = parity_config(width, None)
                for k, v in over.items():
                    setattr(cfg, k, v)
                plan_stitches(run_stages(str(d / "art.png"), cfg), cfg)
            n = sum(1 for r in rec if r["slug"] == slug and r["arm"] == "shipped")
            print(f"[{slug}] {n} auto-angle shapes  ({time.time()-t0:.0f}s)", flush=True)
    finally:
        S6.best_fill_angle_deg = shipped_search
    return rec


def summarise(rec: list[dict]) -> str:
    lines = []
    slugs = sorted({r["slug"] for r in rec} - DUPLICATES)
    for arm in ("curve_off", "both_off"):
        rows = []
        for slug in slugs:
            ship = [r for r in rec if r["slug"] == slug and r["arm"] == "shipped"]
            oth = [r for r in rec if r["slug"] == slug and r["arm"] == arm]
            rows += [(slug, s, o) for s, o in match(ship, oth)]
        matched = [(g, s, o) for g, s, o in rows if o is not None]
        turned = [(g, s, o) for g, s, o in matched
                  if angular_dist(s["angle"], o["angle"]) > TURN_DEG]
        area = sum(s["area"] for _, s, _ in matched)
        t_area = sum(s["area"] for _, s, _ in turned)
        big = sorted({g for g, s, _ in turned if s["area"] >= 200})
        lines.append(f"\n=== shipped vs {arm} ({', '.join(sorted(DUPLICATES))} "
                     f"dropped as a duplicate) ===")
        lines.append(f"  {len(rows)} auto-angle shapes, {len(matched)} matched, "
                     f"{len(rows) - len(matched)} unmatched (not counted as turned)")
        lines.append(f"  rows turn >{TURN_DEG:g} deg on {len(turned)} shapes = "
                     f"{t_area:.0f} of {area:.0f} mm2 of matched fill "
                     f"({t_area / max(area, 1e-9) * 100:.0f}%)")
        lines.append(f"  designs whose >=200 mm2 fill turns: {len(big)} -> {', '.join(big)}")
        for g, s, o in sorted(turned, key=lambda t: -t[1]["area"])[:10]:
            lines.append(f"    {g:<20} {s['area']:8.1f} mm2  {s['angle']:8.2f} -> "
                         f"{o['angle']:8.2f}  margin {s.get('margin')}")
    ship = [r for r in rec if r["arm"] == "shipped" and r["slug"] not in DUPLICATES]
    lines.append(f"\n=== how the shipped angle is decided ({len(ship)} choices) ===")
    for name, pick in (("exact column tie (PCA tiebreak)", lambda m: m == 0),
                       ("won by 1 column", lambda m: m == 1),
                       ("won by >=2 columns", lambda m: m is not None and m >= 2)):
        sel = [r for r in ship if pick(r.get("margin"))]
        lines.append(f"  {name:<32} {len(sel):3d} shapes, "
                     f"{sum(r['area'] for r in sel):7.0f} mm2")
    return "\n".join(lines)


def main():
    man = json.loads((OUT / "manifest.json").read_text())
    slugs = [a for a in sys.argv[1:] if not a.startswith("-")] or \
        [e["slug"] for e in man if e.get("ok")]
    rec = record(slugs)
    (OUT / "angleflags.json").write_text(json.dumps(rec, indent=1))
    print(summarise(rec), flush=True)


if __name__ == "__main__":
    main()
