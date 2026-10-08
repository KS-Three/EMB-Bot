"""Defect 20's cure, `cfg.tonal_split_ceiling` (built OFF, 2026-10-08).

The decision is tested with the stages stubbed, so it runs in milliseconds;
the measurement on real art is `tools/tonal_stack_hist.py` (owl_kent.jpg,
split forced: 28 cells past the ceiling split, 5 whole).
"""
from dataclasses import dataclass

import pytest

from digitizer_core import PipelineConfig, machine, pipeline
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

ROW = machine.FILL_ROW_MM


def _fill(layers: int, size_mm: float = 10.0) -> StitchPlan:
    """`layers` full fills stacked on one square — n x 2.67 coverage units."""
    runs = []
    for _ in range(layers):
        pts, y, flip = [], 0.0, False
        while y <= size_mm:
            row = [(0.0, y), (size_mm, y)]
            pts.extend(reversed(row) if flip else row)
            y += ROW
            flip = not flip
        runs.append(StitchRun(pts))
    return StitchPlan([StitchBlock(0, "0001", (0, 0, 0), runs)], [{}])


def test_area_past_ceiling_reads_the_block_constant():
    assert pipeline.area_past_ceiling_mm2(_fill(1)) == 0.0
    assert pipeline.area_past_ceiling_mm2(_fill(3)) == 0.0       # under 3.5 layers
    assert pipeline.area_past_ceiling_mm2(_fill(4)) > 50.0       # past it


@dataclass
class _Res:
    design_class: str
    tag: str


@pytest.fixture
def stub(monkeypatch):
    """run_stages/plan_stitches stubbed: the split plan stacks `split`
    layers, the whole plan `whole`, and every call is recorded."""
    calls, layers = [], {"split": 4, "whole": 1}

    def run_stages(image, cfg, segmenter=None):
        calls.append(cfg.split_tonal_regions)
        return _Res("photo_scene", "whole" if cfg.split_tonal_regions is False else "split")

    monkeypatch.setattr(pipeline, "run_stages", run_stages)
    monkeypatch.setattr(pipeline, "plan_stitches", lambda r, cfg=None: _fill(layers[r.tag]))
    return calls, layers


def test_off_is_one_pass(stub):
    calls, _ = stub
    res, _plan = pipeline.digitize("x", PipelineConfig())
    assert res.tag == "split" and calls == [None]


def test_on_declines_a_split_that_stacks_past_the_ceiling(stub):
    calls, _ = stub
    res, plan = pipeline.digitize("x", PipelineConfig(tonal_split_ceiling=True))
    assert res.tag == "whole" and calls == [None, False]
    assert pipeline.area_past_ceiling_mm2(plan) == 0.0


def test_on_keeps_a_split_that_does_not_stack(stub):
    calls, layers = stub
    layers["split"] = 2
    res, _plan = pipeline.digitize("x", PipelineConfig(tonal_split_ceiling=True))
    assert res.tag == "split" and calls == [None, False]


def test_on_is_inert_where_the_split_is_off(stub, monkeypatch):
    calls, _ = stub
    res, _plan = pipeline.digitize(
        "x", PipelineConfig(tonal_split_ceiling=True, split_tonal_regions=False))
    assert res.tag == "whole" and calls == [False]
