"""One-off: capture the pre-change flat-lane golden snapshot.

Run once, before stage0_classify/stage6_blend exist, to pin what "byte
identical" means. tests/test_flat_lane_byte_identical.py loads this file and
re-runs the same fixtures through the post-change pipeline, asserting an
exact match. Do not re-run this script after the change lands — regenerating
it would defeat the test it exists to pin.
"""

from __future__ import annotations

import json
from pathlib import Path

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
OUT = Path(__file__).resolve().parent.parent / "testdata" / "flat_lane_golden.json"

FIXTURES = [
    "logo_whitebg.png",
    "logo_alpha.png",
    "ribbon_curve.png",
    "photo/enthusiast_logo.png",
]


def snapshot(name: str) -> dict:
    result, plan = digitize(TESTDATA / name, PipelineConfig(target_width_mm=80.0))
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
    }


def main() -> None:
    golden = {name: snapshot(name) for name in FIXTURES}
    OUT.write_text(json.dumps(golden, indent=1), encoding="utf-8")
    for name, snap in golden.items():
        print(f"{name}: {len(snap['shape_ids'])} shapes, {snap['stitch_count']} stitches")


if __name__ == "__main__":
    main()
