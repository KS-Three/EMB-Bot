"""column_travel_cover: travel the Column lane lays ON TOP of its own satin.

The Becker survey (2026-10-20) saw strands across MARINE's M, N and E in
the render and measured them with `travel_over.py`: per lettering shape,
the length of every travel run that lies on satin the same shape sewed
EARLIER (the satin's stitch path grown 0.25 mm). That reading is `over_mm`
here, unchanged. It counts travel that a LATER satin of the letter buries
too (the Euler walk's underpaths, by design), so this adds `exposed_mm`:
the part of `over_mm` that no later satin of the same shape covers -- the
strand a customer sees. `cut_candidates` counts connector chains (consecutive
travel runs, from where the last sewn run ends to where the next one starts)
whose exposed length passes `trim_at_mm`, the rule
`cfg.lettering_columns_cover_connectors` applies.

    cd digitizer
    .venv/Scripts/python -m tools.column_travel_cover [--off]

prints, per fixture: stitches, trims, travel, over, exposed -- for the
Becker MARINE logo at the pro's three sizes and the Hotel Fremont 81 mm hat
and enthusiast fixtures, the Studio's request (`tools.pro_pair.digitize`).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

HALO_MM = 0.25      # travel_over.py's footprint

FIXTURES = [
    ("becker 95.7 left_chest", "becker_marine_logo.png", 95.7, "left_chest"),
    ("becker 101.9 hat_front", "becker_marine_logo.png", 101.9, "hat_front"),
    ("becker 76.5 left_chest", "becker_marine_logo.png", 76.5, "left_chest"),
    ("becker 76.5 hat_front", "becker_marine_logo.png", 76.5, "hat_front"),
    ("fremont 81 hat_front", "photo/logo_hotel_fremont.webp", 81.0, "hat_front"),
    ("enthusiast 80 hat_front", "photo/enthusiast_logo.png", 80.0, "hat_front"),
]


def shape_travel(runs, limit_mm: float | None = None) -> dict:
    """One shape's runs, in sew order -> travel_mm, over_mm, exposed_mm and
    (with `limit_mm`) cut_candidates."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union

    pts = [[tuple(map(float, p[:2])) for p in r.points] for r in runs]
    halo = [LineString(p).buffer(HALO_MM) if str(r.kind) == "satin" and len(p) >= 2 else None
            for r, p in zip(runs, pts)]
    out = {"travel_mm": 0.0, "over_mm": 0.0, "exposed_mm": 0.0, "cut_candidates": 0}

    def on_top(line, k0, k1):
        earlier = [g for g in halo[:k0] if g is not None]
        if not earlier:
            return 0.0, 0.0
        on = line.intersection(unary_union(earlier))
        later = [g for g in halo[k1:] if g is not None]
        bare = on.difference(unary_union(later)) if later and not on.is_empty else on
        return on.length, bare.length

    for k, (r, p) in enumerate(zip(runs, pts)):
        if str(r.kind) != "travel" or len(p) < 2:
            continue
        line = LineString(p)
        over, bare = on_top(line, k, k + 1)
        out["travel_mm"] += line.length
        out["over_mm"] += over
        out["exposed_mm"] += bare
    if limit_mm is not None:
        k, n = 1, len(runs)
        while k < n:
            if str(runs[k].kind) != "travel" or runs[k].jump:
                k += 1
                continue
            j = k + 1
            while j < n and str(runs[j].kind) == "travel" and not runs[j].jump:
                j += 1
            if j < n and not runs[j].jump:
                path = [pts[k - 1][-1]] + [q for t in pts[k:j] for q in t] + [pts[j][0]]
                if on_top(LineString(path), k, j)[1] > limit_mm:
                    out["cut_candidates"] += 1
            k = j
    return out


def design_travel(plan, regions, limit_mm: float | None = None) -> dict:
    """Every lettering shape of a plan, summed (see `shape_travel`)."""
    let = {r.shape_id for r in regions if (r.meta or {}).get("text_cluster_id")}
    per: dict[str, list] = {}
    for _b, run in plan.iter_runs():
        if str(run.shape_id) in let:
            per.setdefault(str(run.shape_id), []).append(run)
    tot = {"travel_mm": 0.0, "over_mm": 0.0, "exposed_mm": 0.0, "cut_candidates": 0}
    for runs in per.values():
        for key, v in shape_travel(runs, limit_mm).items():
            tot[key] += v
    return tot


def main(argv=None) -> int:
    from dataclasses import replace
    from digitizer_core.pipeline import plan_stitches
    from tools.pro_pair import digitize

    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="substring of a fixture label")
    args = ap.parse_args(argv)
    print("fixture | arm | stitches | trims | travel mm | over mm | exposed mm")
    for label, art, width, garment in FIXTURES:
        if args.only and args.only not in label:
            continue
        d = digitize(DIGITIZER / "testdata" / art, width, garment)
        for arm in (False, True):
            cfg = replace(d.cfg, lettering_columns_cover_connectors=arm)
            plan = plan_stitches(d.result, cfg)
            t = design_travel(plan, d.result.regions)
            print(f"{label} | {'ON' if arm else 'OFF'} | {plan.stats.stitch_count} | "
                  f"{plan.stats.trims} | {t['travel_mm']:.1f} | "
                  f"{t['over_mm']:.1f} | {t['exposed_mm']:.1f}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
