"""`tools/forbid_gap_bill.py` (WoK 44): the OFF row IS the plain pipeline.

The bill is only worth reading if its OFF arm reports what an ordinary
`digitize` would, and the weld spy reads zero there (the rule never ran).
One small fixture, because the full corpus is an hour of CPU.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pytest  # noqa: E402

from digitizer_core import PipelineConfig, digitize  # noqa: E402
from digitizer_core import stage5_overlap  # noqa: E402
from tools import forbid_gap_bill as bill  # noqa: E402

FIXTURE = "photo/region_blobs.png"      # small; 1 strip at 0.8 mm (PR #857 census)


@pytest.fixture(scope="module")
def row():
    gap, weld = stage5_overlap.gap_bridges, stage5_overlap._weld_part
    r = bill.bill_row(FIXTURE)
    r['_restored'] = stage5_overlap.gap_bridges is gap and stage5_overlap._weld_part is weld
    return r


def test_off_row_matches_plain_pipeline_counts(row):
    cfg = PipelineConfig(target_width_mm=bill.WIDTH_MM, garment_id="left_chest")
    _, plan = digitize(ROOT / "testdata" / FIXTURE, cfg)
    off = row["off"]
    assert off["stitches"] == plan.stats.stitch_count
    assert off["trims"] == plan.stats.trims
    assert off["color_changes"] == plan.stats.color_changes
    # OFF never reaches the rule: no gap_bridges call, no weld.
    assert (off["calls"], off["strips"], off["attempted"], off["failed"]) == (0, 0, 0, 0)
    assert off["strip_mm2"] == 0.0


def test_on_row_reads_the_rule_and_the_spy_restores_stage5(row):
    assert row['_restored']
    on = row["on"]
    assert on["calls"] >= 1 and on["strips"] >= 1
    assert on["succeeded"] + on["failed"] == on["attempted"] >= 1
    assert on["strip_mm2"] > 0.0
    assert bill.md_row(row).startswith("| photo/region_blobs.png |")
