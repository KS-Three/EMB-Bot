"""The hard invariant: adding stage 0 (classifier) and the gradient blend
tier must not change ONE byte of output for any flat-classified design.

`testdata/flat_lane_golden.json` was captured by
`tools/capture_flat_lane_golden.py` BEFORE stage0_classify.py or
stage6_blend.py existed (see that script's own docstring — do not re-run it
now, that would defeat what this test pins). This test re-runs the same
fixtures through today's pipeline and asserts an exact match: shape ids,
areas, warnings, and every emitted stitch coordinate.

If this test ever goes red, the change under review is wrong — not this
test. See CLAUDE.md's hard-stop facts and
docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
GOLDEN = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))


def _snapshot(name: str) -> dict:
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


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_lane_is_byte_identical_to_the_pre_change_golden(fixture):
    assert _snapshot(fixture) == GOLDEN[fixture]


def test_golden_file_actually_covers_something():
    """A guard against the golden file silently becoming empty (e.g. a
    capture-script bug) and this whole test module passing vacuously."""
    assert len(GOLDEN) == 4
    for name, snap in GOLDEN.items():
        assert snap["stitch_count"] > 0, f"{name}: golden has zero stitches"


def test_every_golden_fixture_still_classifies_as_flat():
    """The invariant only means anything if these fixtures actually take the
    unchanged code path — if stage 0 ever misclassifies one of them as
    gradient/photo, this test catches that BEFORE the byte-identical
    assertions above would (which would then be comparing against a golden
    captured under different, and now wrong, routing)."""
    from digitizer_core.stage0_classify import classify

    for name in GOLDEN:
        result = classify(TESTDATA / name, PipelineConfig())
        assert result.class_ == "flat", f"{name} classified as {result.class_!r}, not flat"
