"""Defect 20: the layer-density instrument and the per-region cap.

`layer_density.layer_stats` reports max/percentile FILL LAYERS per 1 mm
coverage cell; `cfg.tonal_split_layer_cap` (built OFF 2026-10-13) keeps whole
the tonal-split parents under fabric past the 3.5-layer ceiling. The cap's
decision is tested with the stages stubbed; the split veto and the OFF
byte-identity run through the real pipeline on a committed ramp.
OFF vs ON on the tonal fixtures: `tools/layer_density.py`.
"""
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from digitizer_core import PipelineConfig, machine, pipeline
from digitizer_core.layer_density import (CEILING_LAYERS, cells_past_ceiling_mm,
                                          layer_stats)
from digitizer_core.stage2_photo_segment import split_tonal_regions, tonal_veto_px
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from tests.conftest import own_thread_only

ROW = machine.FILL_ROW_MM
RAMP = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "gradient_ramp_linear.png"


def _fill(layers: int, size_mm: float = 10.0, x0: float = 0.0) -> list[StitchRun]:
    """`layers` full fills stacked on one square at `x0`."""
    runs = []
    for _ in range(layers):
        pts, y, flip = [], 0.0, False
        while y <= size_mm:
            row = [(x0, y), (x0 + size_mm, y)]
            pts.extend(reversed(row) if flip else row)
            y += ROW
            flip = not flip
        runs.append(StitchRun(pts))
    return runs


def _plan(*runs: list[StitchRun]) -> StitchPlan:
    return StitchPlan([StitchBlock(0, "0001", (0, 0, 0), [r for rs in runs for r in rs])], [{}])


# --- the instrument ---------------------------------------------------------

def test_one_fill_reads_one_layer():
    st = layer_stats(_plan(_fill(1)))
    assert st["p50"] == pytest.approx(1.0, abs=0.05)
    assert st["over_ceiling_mm2"] == 0.0 and st["ceiling"] == pytest.approx(3.5)


def test_stacked_fills_read_their_count_and_cross_the_ceiling():
    st = layer_stats(_plan(_fill(4)))
    assert st["max"] == pytest.approx(4.0, abs=0.25)
    assert st["p50"] == pytest.approx(4.0, abs=0.1)
    assert st["max"] >= CEILING_LAYERS
    assert st["over_ceiling_mm2"] > 50.0
    assert st["over_ceiling_mm2"] == pipeline.area_past_ceiling_mm2(_plan(_fill(4)))


def test_percentiles_are_ordered_and_count_sewn_cells_only():
    # one layer on the left square, four on a right square of equal size:
    # half the sewn cells read ~1, half ~4, so p50 sits between and p90 high.
    st = layer_stats(_plan(_fill(1, x0=0.0), _fill(4, x0=30.0)))
    assert st["p50"] <= st["p90"] <= st["p95"] <= st["p99"] <= st["max"]
    assert st["p90"] > 3.5 and st["p50"] < 4.0
    # the bare 20 mm gap between the squares is not counted as sewn fabric
    assert st["sewn_mm2"] < 2 * 13 * 13


def test_an_empty_plan_reads_zero():
    st = layer_stats(StitchPlan([], []))
    assert st["max"] == 0.0 and st["over_ceiling_mm2"] == 0.0


def test_hot_cells_sit_on_the_stack():
    pts = cells_past_ceiling_mm(_plan(_fill(1, x0=0.0), _fill(4, x0=30.0)))
    assert pts and all(29.0 <= x <= 41.0 and -1.0 <= y <= 11.0 for x, y in pts)
    assert cells_past_ceiling_mm(_plan(_fill(1))) == []


# --- the split veto -----------------------------------------------------------

class _PrepStub:
    def __init__(self, rgb, px_per_mm):
        self.rgb = rgb
        self.bg_mask = np.zeros(rgb.shape[:2], bool)
        self.px_per_mm = px_per_mm
        self.enclosed_mask = None
        self.art_bbox = (0, 0, rgb.shape[1], rgb.shape[0])


def _two_ramps():
    """Two splittable discs, left and right, each a light-to-dark sweep."""
    h, w = 240, 480
    yy, xx = np.mgrid[0:h, 0:w]
    ramp = np.clip((xx % 240 - 20) * (235.0 / 200), 10, 245).astype(np.uint8)
    rgb = np.repeat(ramp[:, :, None], 3, axis=2)
    left = np.hypot(xx - 120, yy - 120) < 100
    right = np.hypot(xx - 360, yy - 120) < 100
    return _PrepStub(rgb, 6.0), [RegionMask.from_full(left, layer=0),
                                 RegionMask.from_full(right, layer=1)]


def test_no_veto_is_the_split_unchanged():
    p, kept = _two_ramps()
    a, na = split_tonal_regions(p, kept, split_tonal=True)
    b, nb = split_tonal_regions(p, kept, split_tonal=True,
                                veto_px=tonal_veto_px(p, ()))
    assert tonal_veto_px(p, ()) is None
    assert na == nb == 2
    assert [(r.origin, r.crop.tobytes()) for r in a] == [(r.origin, r.crop.tobytes()) for r in b]


def test_a_vetoed_point_keeps_only_its_own_parent_whole():
    p, kept = _two_ramps()
    # plan-mm origin is the art bbox centre (240, 120) px; the right disc's
    # centre (360, 120) px is +20 mm in x at 6 px/mm.
    out, n = split_tonal_regions(p, kept, split_tonal=True,
                                 veto_px=tonal_veto_px(p, ((20.0, 0.0),)))
    assert n == 1
    whole = [r for r in out if r.layer == 1]
    assert len(whole) == 1 and whole[0].area == kept[1].area
    assert len([r for r in out if r.layer == 0]) >= 2


def test_a_point_just_outside_a_region_still_vetoes_it():
    p, kept = _two_ramps()
    # 1 mm past the right disc's right edge (460 px) -> x = (466-240)/6 mm
    out, n = split_tonal_regions(p, kept, split_tonal=True,
                                 veto_px=tonal_veto_px(p, (((466 - 240) / 6.0, 0.0),)))
    assert n == 1
    # 3 mm out is past the margin
    out, n = split_tonal_regions(p, kept, split_tonal=True,
                                 veto_px=tonal_veto_px(p, (((478 - 240) / 6.0, 0.0),)))
    assert n == 2


# --- the cap's decision (stages stubbed) ------------------------------------

@dataclass
class _Res:
    design_class: str
    veto: tuple


@pytest.fixture
def stub(monkeypatch):
    """The first plan stacks 4 layers on a square at x=30 and 1 at x=0;
    `outcome` says what a vetoed re-run plans."""
    calls, state = [], {"outcome": "fixed"}

    def run_stages(image, cfg, segmenter=None):
        calls.append(tuple(cfg.tonal_split_veto_mm))
        return _Res("photo_scene", tuple(cfg.tonal_split_veto_mm))

    def plan_stitches(res, cfg=None):
        if not res.veto:
            return _plan(_fill(1), _fill(4, x0=30.0))
        if state["outcome"] == "fixed":
            return _plan(_fill(1), _fill(1, x0=30.0))
        return _plan(_fill(1), _fill(5, x0=30.0))     # worse

    monkeypatch.setattr(pipeline, "run_stages",
                        own_thread_only(run_stages, pipeline.run_stages))
    monkeypatch.setattr(pipeline, "plan_stitches",
                        own_thread_only(plan_stitches, pipeline.plan_stitches))
    return calls, state


def test_off_is_one_pass(stub):
    calls, _ = stub
    res, _plan_ = pipeline.digitize("x", PipelineConfig())
    assert calls == [()] and res.veto == ()


def test_on_vetoes_the_hot_cells_and_keeps_the_lower_plan(stub):
    calls, _ = stub
    res, plan = pipeline.digitize("x", PipelineConfig(tonal_split_layer_cap=True))
    assert len(calls) == 2 and calls[0] == ()
    assert calls[1] and all(29.0 <= x <= 41.0 for x, _y in calls[1])
    assert res.veto == calls[1]
    assert layer_stats(plan)["over_ceiling_mm2"] == 0.0


def test_on_discards_a_rerun_that_does_not_help(stub):
    calls, state = stub
    state["outcome"] = "worse"
    res, plan = pipeline.digitize("x", PipelineConfig(tonal_split_layer_cap=True))
    assert len(calls) == 2 and res.veto == ()
    assert layer_stats(plan)["max"] == pytest.approx(4.0, abs=0.25)


def test_on_is_inert_where_the_split_is_off(stub):
    calls, _ = stub
    pipeline.digitize("x", PipelineConfig(tonal_split_layer_cap=True,
                                          split_tonal_regions=False))
    assert calls == [()]


# --- the real pipeline --------------------------------------------------------

def _ramp_cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=40.0, split_tonal_regions=True,
                          is_photographic=True, **kw)


def _fingerprint(res, plan):
    return ([(r.shape_id, r.thread_number, r.area_mm2, r.polygon.wkb) for r in res.regions],
            [(b.thread_index, [tuple(map(tuple, run.points)) for run in b.runs]) for b in plan.blocks],
            plan.palette)


def test_on_is_byte_identical_where_nothing_passes_the_ceiling():
    off = pipeline.digitize(RAMP, _ramp_cfg())
    assert layer_stats(off[1])["over_ceiling_mm2"] == 0.0, "fixture premise"
    on = pipeline.digitize(RAMP, _ramp_cfg(tonal_split_layer_cap=True))
    assert _fingerprint(*on) == _fingerprint(*off)


def test_the_veto_reaches_stage_two():
    """A veto at the design centre keeps the ramp's split parent whole."""
    split, _ = pipeline.digitize(RAMP, _ramp_cfg())
    whole, _ = pipeline.digitize(RAMP, _ramp_cfg(tonal_split_veto_mm=((0.0, 0.0),)))
    assert any(w.get("code") == "TONAL_REGIONS_SPLIT" for w in split.warnings)
    assert not any(w.get("code") == "TONAL_REGIONS_SPLIT" for w in whole.warnings)
    assert len(whole.regions) < len(split.regions)
