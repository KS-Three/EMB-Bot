"""A gradient region whose blend tier accepts N shades must sew N color
blocks, not one. Repro of MASTER_SCOPE's 'every shade sews in one thread'
defect: gradient_ramp_linear.png accepts 4 shades and sewed 2 blocks.

Call shape confirmed against `digitizer_core/pipeline.py` (Step 1 read):
`run_stages` returns a `PipelineResult` with no `.design` attribute — the
stitch plan (and its `.blocks`) comes from `plan_stitches`, or from the
`digitize()` convenience wrapper that returns `(PipelineResult, StitchPlan)`
in one call, the idiom every other real-fixture test in this suite already
uses (see test_flat_lane_byte_identical.py, test_shape_overrides.py, etc.).
"""
from pathlib import Path

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import digitize

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
FIXTURE = TESTDATA / "photo" / "gradient_ramp_linear.png"


def test_accepted_shades_become_color_blocks():
    cfg = PipelineConfig()  # defaults: gradient class routes to blend tier
    _result, plan = digitize(FIXTURE, cfg)
    # The ramp's blend decomposition accepts 4 shades (measured 2026-08-15,
    # docs/blend-tier-never-fires-2026-08-15.md). Distinct thread indexes
    # across the plan's emitted stitch blocks must reflect them.
    distinct = {b.thread_index for b in plan.blocks}
    assert len(distinct) >= 3, (
        f"4-shade ramp sewed {len(distinct)} thread(s) — shade snap not read")
