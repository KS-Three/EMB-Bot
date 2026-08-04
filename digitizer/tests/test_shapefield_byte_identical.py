"""The DT-first migration M1 hard invariant: `cfg.extra["shapefield"]` —
absent, explicitly falsy, or on — must not move ONE byte of output. The
shapefield path is a faithful hoist of stage6_satin's own inline
rasterize + `medial_axis` call, not a reimplementation, so every flag state
must produce identical stitches.

HISTORY — why this compares runtime-vs-runtime and not against a stored
golden. The original version of this file froze a `shapefield_golden.json`
captured on PR #2's branch before merge, and asserted every flag state
matched it. That golden went stale within hours of merging, through no
fault of M1's: PR #3 (enclosed background regions become real, restorable
Regions — c1b9e35) legitimately changed both fixtures' region sets, because
`logo_whitebg.png`/`logo_alpha.png` each carry an enclosed donut hole that
now survives as a tagged, unstitched Region. All 12 golden comparisons went
red on post-merge main while the M1 invariant itself was perfectly intact —
the frozen snapshot was testing "nothing anywhere in the pipeline ever
changes," which is not M1's claim and collides with every future legitimate
behavior change (it also bakes in environment-specific float behavior, the
same class of problem as the three long-standing golden-hash failures).

What M1 actually promises is narrower and permanent: WHATEVER the pipeline
produces today, the shapefield flag does not change it. That is testable at
runtime forever, on any machine, through any future behavior change: run
the same fixture with the flag absent and with every other flag state, and
assert exact equality of the full snapshot (shape ids, areas, warnings,
every stitch coordinate, the DST bytes). If THIS goes red, the change under
review broke the hoist's faithfulness — that is always a real bug. See
docs/dt-first-architecture-2026-08-01.md §2 (M1).
"""
from __future__ import annotations

import hashlib

from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.export import export_dst
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FIXTURES = ["logo_alpha.png", "logo_whitebg.png"]


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


@pytest.fixture(scope="module")
def flag_absent_snapshots() -> dict[str, dict]:
    """The reference arm, computed once: today's pipeline with the flag
    absent — the exact code path that shipped before M1 existed."""
    out = {}
    for name in FIXTURES:
        cfg = PipelineConfig(target_width_mm=80.0)
        assert cfg.extra == {}, "flag must be absent for the reference arm"
        out[name] = _snapshot(name, cfg)
    return out


def test_reference_arm_actually_covers_something(flag_absent_snapshots):
    """Guard against the whole module passing vacuously on empty output."""
    assert len(flag_absent_snapshots) == 2
    for name, snap in flag_absent_snapshots.items():
        assert snap["stitch_count"] > 0, f"{name}: reference has zero stitches"


@pytest.mark.parametrize("fixture", FIXTURES)
@pytest.mark.parametrize("falsy", [False, 0, "", None])
def test_flag_explicitly_falsy_is_byte_identical_to_flag_absent(
    fixture, falsy, flag_absent_snapshots
):
    cfg = PipelineConfig(target_width_mm=80.0, extra={"shapefield": falsy})
    assert _snapshot(fixture, cfg) == flag_absent_snapshots[fixture]


@pytest.mark.parametrize("fixture", FIXTURES)
def test_flag_on_is_byte_identical_to_flag_absent(fixture, flag_absent_snapshots):
    """The faithful-hoist promise itself: the shapefield path computes the
    SAME numbers as the inline path it hoisted, on real fixtures, end to
    end through DST bytes."""
    cfg = PipelineConfig(target_width_mm=80.0, extra={"shapefield": True})
    assert _snapshot(fixture, cfg) == flag_absent_snapshots[fixture]
