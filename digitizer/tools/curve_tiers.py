#!/usr/bin/env python
"""Per-shape tier diff for `PipelineConfig.curve_turn_deg`: off vs on.

The flip evidence the #327 review asked for (2026-09-03, defect 22): a
design-level stitch delta cannot see a shape changing tier, so every shape
is listed with its tier (satin / fill / run / other), its penetrations and
its vertex count under the flag OFF and ON, every tier change is called out,
and the design totals come with `tools/curve_fidelity.py`'s roughness.

    .venv/bin/python tools/curve_tiers.py [case ...] [--turn 15] [--all]

`--all` prints every shape; the default prints only the shapes whose tier
or penetration count moved. Cases: whitebg, alpha, ribbon, becker, fremont,
drone, enthusiast (93 mm, left_chest), gaulke, sunset, meadow, or a path
under `testdata/`.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize  # noqa: E402
import curve_fidelity as cf  # noqa: E402

CASES = {
    "whitebg": ("logo_whitebg.png", {}),
    "alpha": ("logo_alpha.png", {}),
    "ribbon": ("ribbon_curve.png", {}),
    "becker": ("becker_marine_logo.png", {}),
    "fremont": ("photo/logo_hotel_fremont.webp", dict(max_colors=3, forced_class="flat", border="off")),
    "drone": ("photo/drone_render.png", {}),
    "enthusiast": ("photo/enthusiast_logo.png", dict(target_width_mm=93.0, garment_id="left_chest")),
    "gaulke": ("photo/logo_gaulke_roofing.png", {}),
    "sunset": ("photo/photo_sunset_backlit.png", {}),
    "meadow": ("photo/photo_dof_meadow.png", {}),
}
ORDER = ("satin", "fill", "run", "border", "bean", "underlay", "travel", "tie")


def shapes(result, plan) -> dict[str, tuple[str, int, int, tuple[float, float], float]]:
    """shape_id -> (tier, penetrations, vertices, centroid, area)."""
    pens: dict[str, dict[str, int]] = {}
    for _b, run in plan.iter_runs():
        d = pens.setdefault(run.shape_id, {})
        d[run.kind] = d.get(run.kind, 0) + len(run.points)
    out = {}
    for r in result.regions:
        d = pens.get(r.shape_id, {})
        tier = next((k for k in ("satin", "fill", "run", "border", "bean") if d.get(k)), "other" if d else "dropped")
        verts = len(r.polygon.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in r.polygon.interiors)
        c = r.polygon.centroid
        out[r.shape_id] = (tier, sum(v for k, v in d.items() if k not in ("travel", "tie")), verts,
                           (c.x, c.y), r.polygon.area)
    return out


def pair(off: dict, on: dict) -> list[tuple[str, str]]:
    """Shape ids are content-derived and move when the polygon moves; pair
    OFF and ON shapes by id first, then by nearest centroid within 1 mm and
    area within 30%, so a re-id'd shape reads as itself, not as one shape
    dropped and another appearing."""
    pairs, used = [], set()
    for sid in off:
        if sid in on:
            pairs.append((sid, sid))
            used.add(sid)
    for sid, (_t, _p, _v, (x, y), a) in off.items():
        if sid in on:
            continue
        best = None
        for oid, (_t2, _p2, _v2, (x2, y2), a2) in on.items():
            if oid in used:
                continue
            d = ((x - x2) ** 2 + (y - y2) ** 2) ** 0.5
            if d < 1.0 and abs(a - a2) <= 0.3 * max(a, a2) and (best is None or d < best[0]):
                best = (d, oid)
        if best:
            pairs.append((sid, best[1]))
            used.add(best[1])
        else:
            pairs.append((sid, None))
    for oid in on:
        if oid not in used:
            pairs.append((None, oid))
    return pairs


def main(argv: list[str]) -> None:
    turn = float(argv[argv.index("--turn") + 1]) if "--turn" in argv else 15.0
    show_all = "--all" in argv
    names = [a for i, a in enumerate(argv) if not a.startswith("--") and (i == 0 or argv[i - 1] != "--turn")]
    for name in names or list(CASES):
        rel, kw = CASES.get(name, (name, {}))
        rows = {}
        for tag, val in (("off", 0.0), ("on", turn)):
            cfg = dict(target_width_mm=80.0)
            cfg.update(kw)
            cfg["curve_turn_deg"] = val
            result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
            m = cf.measure([pts for _k, _s, pts in cf.traces(plan)])
            rows[tag] = (shapes(result, plan), plan.stats.stitch_count, plan.stats.trims, m.get("roughness_deg", float("nan")))
        off, on = rows["off"][0], rows["on"][0]
        tiers = {t: (sum(1 for v in off.values() if v[0] == t), sum(1 for v in on.values() if v[0] == t))
                 for t in ("satin", "fill", "run", "other", "dropped")}
        print(f"## {name}  st {rows['off'][1]} -> {rows['on'][1]}  trims {rows['off'][2]} -> {rows['on'][2]}  "
              f"verts {sum(v[2] for v in off.values())} -> {sum(v[2] for v in on.values())}  "
              f"roughness {rows['off'][3]:.2f} -> {rows['on'][3]:.2f}  "
              f"tiers " + " ".join(f"{t}:{a}->{b}" for t, (a, b) in tiers.items() if a or b))
        moved = 0
        absent = ("absent", 0, 0, (0.0, 0.0), 0.0)
        for sid, oid in sorted(pair(off, on), key=lambda t: t[0] or t[1]):
            a, b = off.get(sid, absent), on.get(oid, absent)
            flag = "TIER" if a[0] != b[0] else ("" if a[1] == b[1] else "pen")
            if flag == "TIER" or show_all or (flag and "--pens" in argv):
                moved += flag == "TIER"
                label = sid if sid == oid else f"{sid} -> {oid}"
                print(f"  {label:24s} {a[0]:>7} -> {b[0]:<7} pen {a[1]:5d} -> {b[1]:<5d} verts {a[2]:4d} -> {b[2]:<4d} "
                      f"area {a[4]:6.1f} -> {b[4]:<6.1f} {flag}")
        if not moved and not show_all:
            print("  (no tier or penetration change on any shape)")


if __name__ == "__main__":
    main(sys.argv[1:])
