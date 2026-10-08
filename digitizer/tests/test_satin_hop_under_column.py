"""`cfg.satin_hop_under_column` — MASTER_SCOPE defect 6, built OFF.

Inside one satin shape the linking pass trims every hop past `trim_at`. On
Becker the hop from a stroke's underlay to its own column is 3.2 to 6.9 mm
on 14 of the 47 in-shape trims, and the column sewn next lies over all of
it. ON sews that hop needle-down as buried travel; OFF is the shipped pass.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from shapely.geometry import LineString

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from tools.satin_islands import islands

BECKER = Path(__file__).resolve().parent.parent / "testdata" / "becker_marine_logo.png"


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=100.0, garment_id="left_chest", **kw)


@pytest.fixture(scope="module")
def arms():
    gen = build_generation(str(BECKER), _cfg())
    out = {}
    for arm, cfg in (("off", _cfg()), ("on", _cfg(satin_hop_under_column=True))):
        out[arm] = plan_stitches(finish_generation(gen.fork(), cfg), cfg)
    return out


def _runs(plan):
    return [(r.kind, r.trim, r.jump, r.shape_id, list(r.points))
            for _b, r in plan.iter_runs()]


def test_the_flag_is_off_by_default():
    assert PipelineConfig().satin_hop_under_column is False


def test_off_is_the_shipped_plan(arms):
    cfg = _cfg()
    fresh = plan_stitches(finish_generation(build_generation(str(BECKER), cfg), cfg), cfg)
    assert _runs(arms["off"]) == _runs(fresh)


def test_on_sews_fewer_islands_inside_satin_shapes(arms):
    off, on = islands(arms["off"]), islands(arms["on"])
    assert on["shapes"] == off["shapes"]
    assert on["in_trims"] <= off["in_trims"] - 10, (off, on)
    assert arms["on"].stats.trims < arms["off"].stats.trims


def test_every_new_needle_down_hop_is_buried_under_the_next_column(arms):
    """The flag adds no run and drops none: it only stops cutting a hop. So
    the arms pair up run for run, and every run ON stopped cutting is a
    SATIN column whose own stitches cover the travel appended before it,
    none of it longer than a travel stitch."""
    off = [r for _b, r in arms["off"].iter_runs() if r.points]
    on = [r for _b, r in arms["on"].iter_runs() if r.points]
    assert len(on) == len(off)
    cured = 0
    for i in range(1, len(on)):
        if on[i].jump or not off[i].trim:
            continue
        cured += 1
        assert on[i].kind == stitches.SATIN
        assert on[i].shape_id == on[i - 1].shape_id
        # OFF ends the run in a tie-off before the cut; ON has no cut to tie
        # off for. The arms share everything up to there.
        a, b = on[i - 1].points, off[i - 1].points
        kept = next((k for k, (p, q) in enumerate(zip(a, b)) if p != q), min(len(a), len(b)))
        assert kept >= 2
        leg = on[i - 1].points[kept - 1:] + [on[i].points[0]]
        column = LineString(on[i].points).buffer(0.3)
        assert column.covers(LineString(leg))
        assert all(math.dist(p, q) <= machine.TRAVEL_STITCH_MM + 1e-6
                   for p, q in zip(leg, leg[1:]))
    assert cured >= 10
