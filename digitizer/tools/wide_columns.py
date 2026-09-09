"""The band above the satin width cap, read off the corpus — the instrument
for the wide-column policy (quality review 2026-09-08, item 4).

Per fixture and design width: every region the shipped classifier refuses
on width (`dt_p90_cap`, `width_cap`), with the doubled p90 medial radius it
was refused on, its typical width (twice the mean radius), and its area — so
"what would a ceiling of X admit" is a table, not a guess. `--ceiling`
marks the admissible rows. With `--compare`, both flag settings of
`cfg.wide_columns` are digitized and the plan is read for what the policy
costs where it fires: stitches, trims, sewn tiers per shape, the satin runs'
self-crossing pairs (the defect the per-station cap was built against,
2026-08-05), and preflight's coverage_max and uncovered.

Usage:
  python tools/wide_columns.py [--widths 80 100] [--ceiling 6.5] [--compare] [cases ...]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize, machine, run_stages   # noqa: E402
from digitizer_core.preflight import run_preflight                          # noqa: E402
from digitizer_core.stage6_satin import classify_ribbon                     # noqa: E402
from digitizer_core.stitches import strip_ties                              # noqa: E402
from curve_tiers import CASES                                                # noqa: E402

ROOT = HERE.parent


def _seg_cross(p1, p2, p3, p4) -> np.ndarray:
    """Vectorised proper-intersection test for segment arrays (N, 2) each."""
    def orient(a, b, c):
        return (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
    d1 = orient(p3, p4, p1); d2 = orient(p3, p4, p2); d3 = orient(p1, p2, p3); d4 = orient(p1, p2, p4)
    return ((d1 * d2) < 0) & ((d3 * d4) < 0)


def crossing_pairs(points: list[tuple[float, float]], window: int = 40) -> int:
    """Non-adjacent segment pairs of one run that properly cross, counted
    within `window` segments of each other — where a fold or a fan puts
    them. The 2026-08-05 measurement counted 2580 on one apex this way (all
    pairs, shapely); a window keeps a corpus pass affordable."""
    p = np.asarray(points, float)
    if len(p) < 4:
        return 0
    a, b = p[:-1], p[1:]
    n = len(a)
    total = 0
    for k in range(2, min(window, n - 1) + 1):
        m = n - k
        hit = _seg_cross(a[:m], b[:m], a[k:k + m], b[k:k + m])
        total += int(hit.sum())
    return total


def band_rows(rel: str, kw: dict, width_mm: float, ceiling: float) -> list[dict]:
    cfg = PipelineConfig(target_width_mm=width_mm, **kw)
    result = run_stages(ROOT / "testdata" / rel, cfg)
    dc = getattr(result, "design_class", None) or (result.stage0.design_class if getattr(result, "stage0", None) else "flat")
    satin_max = cfg.satin_max_width_mm or machine.SATIN_MAX_WIDTH_MM
    rows = []
    for r in result.regions:
        if r.polygon is None or r.polygon.is_empty or r.meta.get("enclosed_background"):
            continue
        v = classify_ribbon(r.polygon, satin_max, design_class=dc, full_metrics=True)
        if v.reason not in ("dt_p90_cap", "width_cap"):
            continue
        p90 = v.metrics.get("dt_p90_mm", float("nan"))
        # the typical width: area over (spine length x explained) is exactly
        # 2 x the mean radius in mm (`_DtStats`'s own arithmetic)
        spine = v.metrics.get("spine_len_mm", 0.0); expl = v.metrics.get("explained", 0.0)
        typical = (r.area_mm2 / (spine * expl)) if spine > 0 and expl > 0 else float("nan")
        rows.append({"shape_id": r.shape_id, "area": r.area_mm2, "reason": v.reason,
                     "p90": p90, "typical": typical, "admissible": bool(p90 <= ceiling)})
    return rows


def compare(rel: str, kw: dict, width_mm: float) -> dict:
    out = {}
    for flag in (False, True):
        cfg = PipelineConfig(target_width_mm=width_mm, wide_columns=flag, **kw)
        result, plan = digitize(ROOT / "testdata" / rel, cfg)
        rep = run_preflight(result, plan, cfg, image=ROOT / "testdata" / rel)
        kinds: dict[str, dict[str, int]] = {}
        crossings = 0
        for _b, run in plan.iter_runs():
            k = kinds.setdefault(run.shape_id, {})
            k[run.kind] = k.get(run.kind, 0) + len(run.points)
            if run.kind == "satin":
                crossings += crossing_pairs(strip_ties(run.points))
        m = rep["metrics"]
        out[flag] = {"stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
                     "crossings": crossings, "coverage_max": m.get("coverage_max"),
                     "unc_worst": m.get("uncovered_worst_mm2"), "unc_total": m.get("uncovered_total_mm2"),
                     "tiers": {s: max(k, key=k.get) for s, k in kinds.items()}}
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="+", default=[80.0, 100.0])
    ap.add_argument("--ceiling", type=float, default=6.5)
    ap.add_argument("--compare", action="store_true")
    a = ap.parse_args(argv)
    names = a.cases or list(CASES)
    print(f"regions refused on width, ceiling {a.ceiling} mm (cap {machine.SATIN_MAX_WIDTH_MM})")
    for name in names:
        rel, kw = CASES[name]
        for w in a.widths:
            kw2 = {k: v for k, v in kw.items() if k != "target_width_mm"}
            rows = band_rows(rel, kw2, w, a.ceiling)
            adm = [r for r in rows if r["admissible"]]
            print(f"== {name:12} {w:5.0f} mm: refused on width {len(rows):2}  admissible at {a.ceiling}: {len(adm):2}"
                  f"  ({sum(r['area'] for r in adm):7.1f} mm2 of {sum(r['area'] for r in rows):7.1f})")
            for r in sorted(rows, key=lambda r: -r["area"])[:12]:
                print(f"     {r['shape_id']} {r['area']:7.1f} mm2  p90 {r['p90']:5.2f}  typical {r['typical']:5.2f}  {r['reason']:10} {'ADMISSIBLE' if r['admissible'] else ''}")
            if a.compare:
                c = compare(rel, kw2, w)
                off, on = c[False], c[True]
                moved = {s: (off["tiers"].get(s), on["tiers"].get(s)) for s in set(off["tiers"]) | set(on["tiers"])
                         if off["tiers"].get(s) != on["tiers"].get(s)}
                print(f"     OFF->ON: stitches {off['stitches']} -> {on['stitches']}  trims {off['trims']} -> {on['trims']}"
                      f"  crossings {off['crossings']} -> {on['crossings']}  coverage_max {off['coverage_max']} -> {on['coverage_max']}"
                      f"  uncovered worst {off['unc_worst']} -> {on['unc_worst']} total {off['unc_total']} -> {on['unc_total']}")
                for s, (x, y) in sorted(moved.items()):
                    print(f"        {s}: {x} -> {y}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
