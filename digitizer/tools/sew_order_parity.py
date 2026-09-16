#!/usr/bin/env python
"""Auto vs manual sew order — how often, and by how much, do the two
orderings disagree?

MASTER_SCOPE open item 16 (found 2026-09-13, recorded in
`tests/test_manual.py::test_copying_a_real_auto_digitized_design_through_manual_reproduces_it`):
auto-digitize orders colour blocks by PALETTE LAYER, manual mode orders them
by summed thread AREA, and the two agreed until a tiny region existed in an
early layer. This is the measurement half of that item: take every corpus
fixture, digitize it for real, copy EVERY surviving region verbatim into a
manual shape list (same rings, same thread, the tier the auto ladder actually
picked), re-plan it through `build_manual_result` + `plan_stitches`, and diff
the two plans.

Deliberately a REPORTING tool, the same shape as `tools/corpus_scorecard.py`:
it prints what diverges and by how much, and asserts nothing about which
order sews better. That question is a Gate 1 question (see ROADMAP) — the
cost of a wrong sew order is registration and distortion on cloth, which no
geometry here can measure.

Usage:
    .venv/bin/python tools/sew_order_parity.py [--garment left_chest]
                                               [--fixtures a.png b.png]
                                               [--json OUT.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import (PipelineConfig, build_manual_result,  # noqa: E402
                            plan_stitches, run_stages)
from digitizer_core.machine import SATIN_MAX_WIDTH_MM  # noqa: E402
from digitizer_core.stage6_satin import is_satin_candidate  # noqa: E402
# The same 26 committed fixtures tools/corpus_scorecard.py scores, so a
# divergence rate here is over the same corpus a quality number is.
from tools.corpus_scorecard import FIXTURES  # noqa: E402

TESTDATA = ROOT / "testdata"


def actual_tier(region, c: PipelineConfig) -> str:
    """The tier stage 7's own 'auto' ladder picked for this region — read the
    same way `test_manual.py::_actual_tier` reads it, so the manual copy
    forces what auto already chose rather than a guess."""
    satin_max = c.satin_max_width_mm or SATIN_MAX_WIDTH_MM
    if is_satin_candidate(region.polygon, satin_max):
        return "satin"
    if c.small_shape_rescue and region.area_mm2 < c.min_detail_mm ** 2:
        return "run"
    return "fill"


def kendall_swaps(a: list, b: list) -> int:
    """Adjacent-transposition distance between two orderings of the same
    multiset — 'how many swaps would it take', the plainest honest measure of
    'by how much'. Returns -1 when the two are not permutations."""
    if sorted(map(str, a)) != sorted(map(str, b)):
        return -1
    pos: dict = {}
    for i, x in enumerate(b):
        pos.setdefault(x, []).append(i)
    used: dict = {}
    idx = []
    for x in a:
        k = used.get(x, 0)
        used[x] = k + 1
        idx.append(pos[x][k])
    swaps = 0
    for i in range(len(idx)):
        for j in range(i + 1, len(idx)):
            if idx[i] > idx[j]:
                swaps += 1
    return swaps


def compare(name: str, c: PipelineConfig) -> dict:
    row: dict = {"fixture": name}
    t0 = time.time()
    auto_result = run_stages(TESTDATA / name, c)
    auto_plan = plan_stitches(auto_result, c)

    stitched = [r for r in auto_result.regions if r.meta.get("stitched", True)]
    row["regions"] = len(stitched)
    tiers = [actual_tier(r, c) for r in stitched]
    # What the auto path recorded for each region: a tier manual mode's
    # vocabulary cannot express is itself a divergence.
    row["auto_tiers"] = sorted({str(r.meta.get("tier", "auto")) for r in stitched})

    shapes = [
        {
            "polygon": list(r.polygon.exterior.coords),
            "holes": [list(h.coords) for h in r.polygon.interiors],
            "technique": t,
            "thread_index": r.thread_index,
        }
        for r, t in zip(stitched, tiers)
    ]
    try:
        manual_plan = plan_stitches(build_manual_result(shapes, c), c)
    except Exception as exc:                       # noqa: BLE001
        row["error"] = f"{type(exc).__name__}: {exc}"
        row["seconds"] = round(time.time() - t0, 1)
        return row

    a = [b.thread_number for b in auto_plan.blocks]
    m = [b.thread_number for b in manual_plan.blocks]
    row["auto_order"] = a
    row["manual_order"] = m
    row["same_order"] = a == m
    row["same_block_set"] = sorted(a) == sorted(m)
    row["swaps"] = kendall_swaps(a, m)
    row["first_divergence"] = (
        next((i for i, (x, y) in enumerate(zip(a, m)) if x != y),
             min(len(a), len(m)))
        if a != m else None
    )
    row["auto_blocks"] = len(a)
    row["manual_blocks"] = len(m)
    row["auto_color_changes"] = auto_plan.stats.color_changes
    row["manual_color_changes"] = manual_plan.stats.color_changes
    row["auto_trims"] = auto_plan.stats.trims
    row["manual_trims"] = manual_plan.stats.trims
    row["auto_stitches"] = auto_plan.stats.stitch_count
    row["manual_stitches"] = manual_plan.stats.stitch_count
    row["seconds"] = round(time.time() - t0, 1)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--garment", default="left_chest")
    ap.add_argument("--fixtures", nargs="*", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    names = args.fixtures if args.fixtures else FIXTURES
    rows = []
    for name in names:
        c = PipelineConfig(target_width_mm=80.0, garment_id=args.garment)
        try:
            row = compare(name, c)
        except Exception as exc:                   # noqa: BLE001
            row = {"fixture": name, "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        flag = ("ERR " if "error" in row
                else "ok  " if row.get("same_order") else "DIFF")
        print(f"{flag} {name:<42} "
              f"blocks {row.get('auto_blocks', '-')}/{row.get('manual_blocks', '-')}  "
              f"swaps {row.get('swaps', '-')}  "
              f"stops {row.get('auto_color_changes', '-')}/"
              f"{row.get('manual_color_changes', '-')}  "
              f"trims {row.get('auto_trims', '-')}/{row.get('manual_trims', '-')}  "
              f"{row.get('seconds', '-')}s", flush=True)
        if "error" in row:
            print(f"      {row['error']}", flush=True)
        elif not row.get("same_order"):
            print(f"      auto   {row['auto_order']}", flush=True)
            print(f"      manual {row['manual_order']}", flush=True)

    ok = [r for r in rows if "error" not in r]
    diff = [r for r in ok if not r["same_order"]]
    print(f"\n{len(diff)}/{len(ok)} fixtures diverge "
          f"({len(rows) - len(ok)} errored) on garment {args.garment}")
    if args.json:
        Path(args.json).write_text(json.dumps(rows, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
