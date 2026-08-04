"""Capture the M1 shapefield byte-identical golden.

Run ONCE, before digitizer_core/shapefield.py existed and before
stage6_satin.py/stage7_sequence.py gained the `cfg.extra["shapefield"]`
wiring — see docs/superpowers/plans/2026-08-04-m0-shape-lens-measurement.md
and docs/dt-first-architecture-2026-08-01.md section M1. Do NOT re-run this
after that change lands; that would defeat what
tests/test_shapefield_byte_identical.py pins. If the DT-first migration ever
needs a new golden (a deliberate, flagged behaviour change), regenerate with
git stash of the change under review, exactly like
tools/capture_flat_lane_golden.py does it.

Captures both PipelineResult-level facts (shape ids, areas, warnings) and
plan-level facts (every emitted stitch coordinate, plus raw DST bytes as a
sha256 hex digest — the bytes themselves are not JSON-safe and a hash is
sufficient to prove "not one byte moved").
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from digitizer_core import PipelineConfig
from digitizer_core.export import export_dst
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
OUT = TESTDATA / "shapefield_golden.json"

FIXTURES = ["logo_whitebg.png", "logo_alpha.png"]


def _snapshot(name: str) -> dict:
    result, plan = digitize(TESTDATA / name, PipelineConfig(target_width_mm=80.0))
    dst_bytes = export_dst(plan)
    return {
        "shape_ids": sorted(r.shape_id for r in result.regions),
        "areas_mm2": sorted(round(r.area_mm2, 4) for r in result.regions),
        "warnings": sorted(
            f"{w['code']}:{w.get('count', '')}" for w in result.warnings
        ),
        "stitch_count": sum(len(r.points) for _, r in plan.iter_runs()),
        "stitch_coords": [
            [round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs()
            for x, y in r.points
        ],
        "dst_sha256": hashlib.sha256(dst_bytes).hexdigest(),
        "dst_len": len(dst_bytes),
    }


def main() -> None:
    golden = {name: _snapshot(name) for name in FIXTURES}
    OUT.write_text(json.dumps(golden, indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote {OUT} ({sum(g['stitch_count'] for g in golden.values())} total stitches)")


if __name__ == "__main__":
    main()
