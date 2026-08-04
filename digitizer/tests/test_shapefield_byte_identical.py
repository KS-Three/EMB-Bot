"""The DT-first migration M1 hard invariant: `digitizer_core/shapefield.py`
existing, and `stage6_satin`/`stage7_sequence` gaining the
`cfg.extra["shapefield"]` wiring, must not move ONE byte of output when the
flag is absent — or explicitly set to any falsy value.

`testdata/shapefield_golden.json` was captured by
`tools/capture_shapefield_golden.py` BEFORE shapefield.py existed and before
stage6_satin.py/stage7_sequence.py had any `use_shapefield` plumbing (do not
re-run that script now — see its own docstring). This test re-runs the same
two fixtures through today's pipeline, with the flag unset AND with the flag
explicitly falsy, and asserts an exact match on every shape id, area,
warning, stitch coordinate and the DST bytes themselves (via sha256 — DST
bytes are not JSON-safe, so the golden stores a digest and length instead of
the raw bytes).

If this test ever goes red, the change under review is wrong — M1 is pure
infrastructure, not a numerics change. See
docs/dt-first-architecture-2026-08-01.md §2 (M1).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.export import export_dst
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
GOLDEN = json.loads((TESTDATA / "shapefield_golden.json").read_text(encoding="utf-8"))


def _snapshot(name: str, cfg: PipelineConfig) -> dict:
    result, plan = digitize(TESTDATA / name, cfg)
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


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flag_absent_is_byte_identical_to_the_pre_change_golden(fixture):
    cfg = PipelineConfig(target_width_mm=80.0)
    assert cfg.extra == {}, "flag must be absent for this arm of the test"
    assert _snapshot(fixture, cfg) == GOLDEN[fixture]


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
@pytest.mark.parametrize("falsy", [False, 0, "", None])
def test_flag_explicitly_falsy_is_byte_identical_to_the_pre_change_golden(fixture, falsy):
    cfg = PipelineConfig(target_width_mm=80.0, extra={"shapefield": falsy})
    assert _snapshot(fixture, cfg) == GOLDEN[fixture]


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flag_on_also_matches_the_golden(fixture):
    """Not the hard requirement (only flag-absent/falsy is), but proving the
    new path computes the SAME numbers as the old one is exactly what the
    module docstring promises — a faithful hoist, not a reimplementation.
    """
    cfg = PipelineConfig(target_width_mm=80.0, extra={"shapefield": True})
    assert _snapshot(fixture, cfg) == GOLDEN[fixture]


def test_golden_file_actually_covers_something():
    """A guard against the golden file silently becoming empty (e.g. a
    capture-script bug) and this whole test module passing vacuously."""
    assert len(GOLDEN) == 2
    for name, snap in GOLDEN.items():
        assert snap["stitch_count"] > 0, f"{name}: golden has zero stitches"
