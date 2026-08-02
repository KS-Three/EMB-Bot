#!/usr/bin/env python
"""Chaining laws 59-62: what the links bought, and are any of them uncovered?

Runs each fixture twice — with `chain_links` off and on — and prints the
before/after the acceptance case asks for. The load-bearing column is
UNCOVERED: for every needle-down travel run the plan emits, it re-tests the
run's whole path against the covering geometry stage 5 computed. A link that
is not buried is a visible float on bare fabric, which is worse than the trim
it replaced, so this number must be zero.

The check is deliberately re-derived here rather than trusted from stage 7:
stage 7 builds each route so that it is covered, and this asks the finished
stitches whether it did.

Usage: .venv/Scripts/python tools/chain_probe.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core.pipeline import fabric_for, run_stages  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from digitizer_core.stage7_sequence import sequence  # noqa: E402

CASES = [
    ("benchmark", Path(r"C:\Users\EE-LT-11030\Downloads\enthusiast enterprises logo.png"),
     "left_chest", 90.0),
    ("logo_whitebg", ROOT / "testdata/logo_whitebg.png", "left_chest", 80.0),
    ("ribbon_curve", ROOT / "testdata/ribbon_curve.png", "left_chest", 80.0),
    ("logo_alpha", ROOT / "testdata/logo_alpha.png", "left_chest", 80.0),
]


def uncovered_travel(planned, blocks) -> tuple[int, int, float]:
    """-> (travel runs, uncovered travel runs, travel mm).

    A travel run is covered when its entire path lies inside the geometry its
    own colour block will sew plus everything that sews after that block —
    exactly `_link_cover`'s definition, rebuilt from stage 5's `covered_by`.
    """
    by_index: dict[int, list] = {}
    for p in planned:
        by_index.setdefault(p.sew_index, []).append(p)
    cover_for = {}
    for si, group in by_index.items():
        parts = [p.polygon for p in group]
        seen = []
        for p in group:
            c = p.covered_by
            if c is not None and not c.is_empty and not any(c is s for s in seen):
                seen.append(c)
        parts.extend(seen)
        cover_for[si] = unary_union(parts).buffer(machine.LINK_COVER_TOL_MM)

    ids = {p.shape_id: p.sew_index for p in planned}
    total = bad = 0
    mm = 0.0
    for b in blocks:
        si = next((ids[r.shape_id] for r in b.runs if r.shape_id in ids), None)
        cover = cover_for.get(si)
        for run in b.runs:
            if run.kind != stitches.TRAVEL:
                continue
            total += 1
            mm += run.length_mm
            if cover is None or len(run.points) < 2:
                continue
            if not cover.covers(LineString(run.points)):
                bad += 1
    return total, bad, mm


def measure(planned, fabric, cfg):
    blocks, warns = sequence(planned, fabric, cfg)
    plan = type("P", (), {"blocks": blocks})
    trims = jumps = count = 0
    prev = None
    for b in blocks:
        for run in b.runs:
            trims += int(run.trim)
            jumps += int(run.jump and not run.trim)
            for pt in run.points:
                if prev is None or math.dist(pt, prev) >= 0.01:
                    count += 1
                prev = pt
    travel_n, bad, travel_mm = uncovered_travel(planned, blocks)
    # The file holds one trim fewer than the plan: the first block has no
    # thread to cut yet. Same correction preflight makes.
    file_trims = trims - 1 if trims else 0
    return {
        "st": count, "trims": trims, "file_trims": file_trims,
        "per_1k": round(1000.0 * file_trims / count, 2) if count else 0.0,
        "jumps": jumps, "travel_n": travel_n, "travel_mm": round(travel_mm, 1),
        "uncovered": bad,
    }


def main() -> None:
    for name, path, garment, width in CASES:
        if not path.exists():
            print(f"{name}: MISSING {path}")
            continue
        base = PipelineConfig(target_width_mm=width, garment_id=garment)
        result = run_stages(path, base)
        fabric = fabric_for(base)
        planned, _ = resolve_overlaps(result.regions, fabric, base)
        off = measure(planned, fabric,
                      PipelineConfig(target_width_mm=width, garment_id=garment,
                                     chain_links=False))
        # resolve_overlaps is pure, but sequence mutates run flags, so re-plan.
        planned, _ = resolve_overlaps(result.regions, fabric, base)
        on = measure(planned, fabric, base)
        print(f"=== {name} @ {width:g}mm / {garment}")
        for label, m in (("before", off), ("after", on)):
            print(f"    {label:<6} st={m['st']:<6} trims={m['trims']:<3} "
                  f"trims/1k={m['per_1k']:<5} jumps={m['jumps']:<3} "
                  f"travel={m['travel_mm']:<7} runs={m['travel_n']:<3} "
                  f"UNCOVERED={m['uncovered']}")


if __name__ == "__main__":
    main()
