#!/usr/bin/env python
"""Chaining laws 59-62: what the links bought, and is any of it on bare cloth?

Runs each fixture twice — with `chain_links` off and on — and prints the
before/after the acceptance case asks for. The load-bearing column is BARE:
millimetres of every needle-down travel run's REAL sewn path (previous run's
last point -> link -> next run's first point, densified) that land further
than half a thread width from any emitted non-travel stitch of any colour.
That must not grow, or chaining is sewing floats on cloth instead of removing
trims.

This used to rebuild the cover from `p.polygon` for every shape in the block —
the same approximation `_link_cover` itself used to make, and the same one
that let both this tool and `tests/test_chaining.py::_uncovered_links` report
zero uncovered links on a design that measurably had thread hanging in open
air (see `PipelineConfig.chain_links`'s docstring for the numbers). Both are
now measured against what a needle actually sews, not what a shape's outline
claims it sews: this tool no longer trusts `_link_cover`'s own geometry at
all, the same way `tests/test_chaining.py::_thread_bare_mm` does not.

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


def thread_bare_mm(blocks, step_mm: float = 0.1) -> tuple[int, int, float, float]:
    """-> (links, exposed links, bare mm, worst clearance mm).

    Never looks at a polygon or at `_link_cover`'s own geometry: it asks where
    thread physically lands. One-point links are not skipped (a plain STITCH
    record with `jump=False` still sews the machine needle-down through it,
    and they are 37% of a real design's links), and the path measured is the
    REAL sewn one, not the route's stored interior — `_link_stitches` returns
    only that interior, so the first and last segment the needle actually
    sews are pulled in from the neighbouring runs' own endpoints.
    """
    runs = [r for b in blocks for r in b.runs]
    laid = [LineString(r.points) for r in runs
            if r.kind != stitches.TRAVEL and len(r.points) >= 2]
    if not laid:
        return 0, 0, 0.0, 0.0
    thread = unary_union(laid)
    half = machine.COVERAGE_THREAD_W_MM / 2.0

    links = exposed = 0
    bare_mm = worst = 0.0
    for i, run in enumerate(runs):
        if run.kind != stitches.TRAVEL:
            continue
        links += 1
        pts = list(run.points)
        if i and runs[i - 1].points:
            pts.insert(0, runs[i - 1].points[-1])
        if i + 1 < len(runs) and runs[i + 1].points:
            pts.append(runs[i + 1].points[0])
        if len(pts) < 2:
            continue
        path = LineString(pts)
        n = max(2, int(path.length / step_mm))
        bad = 0.0
        for k in range(n + 1):
            d = thread.distance(path.interpolate(k / n, normalized=True))
            if d > half:
                bad += path.length / n
                worst = max(worst, d)
        if bad:
            exposed += 1
        bare_mm += bad
    return links, exposed, bare_mm, worst


def measure(planned, fabric, cfg):
    blocks, warns = sequence(planned, fabric, cfg)
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
    links, exposed, bare_mm, worst = thread_bare_mm(blocks)
    # The file holds one trim fewer than the plan: the first block has no
    # thread to cut yet. Same correction preflight makes.
    file_trims = trims - 1 if trims else 0
    return {
        "st": count, "trims": trims, "file_trims": file_trims,
        "per_1k": round(1000.0 * file_trims / count, 2) if count else 0.0,
        "jumps": jumps, "links": links, "exposed": exposed,
        "bare_mm": round(bare_mm, 2), "worst_mm": round(worst, 4),
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
        # `base` carries whatever PipelineConfig.chain_links currently
        # defaults to (False as of 2026-08-02) — this must ask for chaining
        # explicitly, or "on" silently re-measures the same "off" config and
        # every before/after pair in this tool's output reads as a no-op.
        on = measure(planned, fabric,
                     PipelineConfig(target_width_mm=width, garment_id=garment,
                                    chain_links=True))
        print(f"=== {name} @ {width:g}mm / {garment}")
        for label, m in (("before", off), ("after", on)):
            print(f"    {label:<6} st={m['st']:<6} trims={m['trims']:<3} "
                  f"trims/1k={m['per_1k']:<5} jumps={m['jumps']:<3} "
                  f"links={m['links']:<3} exposed={m['exposed']:<3} "
                  f"bare={m['bare_mm']:<6} worst={m['worst_mm']}")


if __name__ == "__main__":
    main()
