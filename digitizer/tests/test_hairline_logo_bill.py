"""`tools/hairline_logo_bill.py`: its OFF row IS the plain pipeline.

The bill is only worth reading if its baseline column is today's output, so
the first test digitizes one small fixture the plain way (`run_stages` +
`plan_stitches`, `cfg.hairline` left at its default) and counts the plan
without the tool's help. The second pins that the tool sees hair where there
is hair (so a zero on a logo means "none", not "the instrument is blind").
"""
from __future__ import annotations

import math

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import plan_stitches, run_stages
from tools import hairline_logo_bill as hlb

SMALL = {"target_width_mm": 30.0, "garment_id": "left_chest"}


def _raw_counts(plan) -> tuple[int, int, float]:
    stitches = trims = 0
    mm = 0.0
    for b in plan.blocks:
        for r in b.runs:
            stitches += len(r.points)
            trims += 1 if r.trim else 0
            mm += sum(math.dist(a, c) for a, c in zip(r.points, r.points[1:]))
    return stitches, trims, round(mm / 1000.0, 3)


def test_off_row_matches_the_plain_pipeline():
    row = hlb.run_one("logo_alpha.png", SMALL, wt=40)
    cfg = PipelineConfig(**SMALL)
    assert not cfg.hairline and not cfg.hairline_over_ground
    plain = plan_stitches(run_stages(hlb.TESTDATA / "logo_alpha.png", cfg), cfg)
    stitches, trims, metres = _raw_counts(plain)
    off = row["off"]
    assert (off["stitches"], off["trims"], off["thread_m"]) == (stitches, trims, metres)
    assert off["hairline_sewn"] == {"shapes": 0, "strands": 0, "dropped": 0}
    assert set(row) >= {"off", "on", "on_gnd"}
    assert row["on"]["candidate_count"] == len(row["on"]["candidates"])


def test_the_tool_sees_hair_where_there_is_hair():
    row = hlb.run_one("synthetic/hair_fine.png",
                      {"target_width_mm": 40.0, "forced_class": "flat"}, wt=40)
    assert row["off"]["hairline_sewn"]["shapes"] == 0
    assert row["on"]["candidate_count"] > 0
    assert row["on"]["hairline_sewn"]["shapes"] > 0
    assert row["on"]["resewn_count"] > 0
    assert row["on"]["stitches"] != row["off"]["stitches"]
    limit = machine.thread_profile(40).hairline_max_width_mm
    assert all(c["width_mm"] <= limit for c in row["on"]["candidates"])
