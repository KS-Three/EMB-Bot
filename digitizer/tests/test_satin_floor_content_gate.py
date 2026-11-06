"""Defect 2: `cfg.satin_floor_content_gate` widens Law 31's width floor from
the photo CLASSES to a design that is photographic by CONTENT
(`config.is_photographic`) but that stage 0 routed gradient.

Default OFF and byte-identical (the flat/gradient golden pins and
`test_photo_width_floor.py` cover the OFF side across the suite; the pins
here re-assert it at the seams the flag touches). The constant stays Law
31's printed 1.0 mm and no stage-0 threshold moves: the only new input is
the existing declaration / detection signal.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig, satin_floor_applies
from digitizer_core.pipeline import plan_stitches
from digitizer_core.stage5_overlap import _comp_axis
from digitizer_core.stage6_satin import (
    PHOTO_MIN_SATIN_WIDTH_MM,
    classify_ribbon,
    classify_strokes,
    is_satin_candidate,
)

from .test_photo_width_floor import (
    BAR,
    HAIRLINE,
    SATIN_MAX,
    _end_flared_stroke,
    _kinds,
    _one_shape_result,
)


def test_the_constant_is_still_laws_printed_one_millimetre():
    assert PHOTO_MIN_SATIN_WIDTH_MM == 1.0


def test_flag_defaults_off():
    assert PipelineConfig().satin_floor_content_gate is False


def test_floor_applies_off_by_default_everywhere():
    for cls in ("flat", "gradient"):
        v = classify_ribbon(HAIRLINE, SATIN_MAX, design_class=cls)
        assert v.satin and v.reason == "satin", (cls, v.reason)
        assert is_satin_candidate(HAIRLINE, SATIN_MAX, design_class=cls)


def test_floor_applies_floors_a_hairline_under_class_gradient():
    for cls in ("flat", "gradient"):
        v = classify_ribbon(HAIRLINE, SATIN_MAX, design_class=cls,
                            floor_applies=True)
        assert not v.satin and v.reason == "photo_width_floor", (cls, v.reason)
        assert not is_satin_candidate(HAIRLINE, SATIN_MAX, design_class=cls,
                                      floor_applies=True)


def test_floor_applies_keeps_a_normal_bar_satin():
    v = classify_ribbon(BAR, SATIN_MAX, design_class="gradient",
                        floor_applies=True)
    assert v.satin and v.reason == "satin", v.reason


def test_floor_applies_floors_the_promoted_ribbon_exit_too():
    flared = _end_flared_stroke()
    off = classify_ribbon(flared, SATIN_MAX, design_class="gradient")
    assert off.satin and off.reason == "promoted_ribbon", off.reason
    on = classify_ribbon(flared, SATIN_MAX, design_class="gradient",
                         floor_applies=True)
    assert not on.satin and on.reason == "photo_width_floor", on.reason


def test_the_per_stroke_branch_floors_too():
    """Splitting a region must not be a way round the widened floor either:
    `_stroke_rows` carries `floor_applies` exactly like `_floor_or`."""
    off = classify_strokes(HAIRLINE, SATIN_MAX, design_class="gradient")
    assert off.strokes and all(s.satin for s in off.strokes), \
        [(s.satin, s.reason) for s in off.strokes]
    on = classify_strokes(HAIRLINE, SATIN_MAX, design_class="gradient",
                          floor_applies=True)
    assert on.strokes and all(
        (not s.satin) and s.reason == "photo_width_floor" for s in on.strokes
    ), [(s.satin, s.reason) for s in on.strokes]
    assert on.region.reason == "photo_width_floor"


def test_satin_floor_applies_needs_flag_and_content():
    on = PipelineConfig(satin_floor_content_gate=True)
    assert satin_floor_applies(replace(on, is_photographic=True), "gradient")
    # no declaration: stage 0's class alone is not content
    assert not satin_floor_applies(on, "gradient")
    assert not satin_floor_applies(on, "flat")
    # the caller said no: outranks everything
    assert not satin_floor_applies(replace(on, is_photographic=False), "gradient")
    # flag off: a declared photo changes nothing
    assert not satin_floor_applies(
        PipelineConfig(is_photographic=True), "gradient")


def _plan(cfg, design_class="gradient", poly=HAIRLINE, detected=False):
    result = _one_shape_result(poly, design_class)
    result.detected_photographic = detected
    return plan_stitches(result, replace(cfg, preflight=False))


def test_stage7_hairline_under_gradient_declared_photo():
    base = PipelineConfig()
    assert "satin" in _kinds(_plan(base))
    # declared but flag OFF: byte-identical to undeclared
    assert "satin" in _kinds(_plan(replace(base, is_photographic=True)))
    # flag ON, nothing declared: a gradient logo keeps its hairline satin
    assert "satin" in _kinds(_plan(replace(base, satin_floor_content_gate=True)))
    # flag ON, "caller said no": same
    assert "satin" in _kinds(_plan(replace(
        base, satin_floor_content_gate=True, is_photographic=False)))
    # flag ON + declared: rerouted to the run
    on = _kinds(_plan(replace(base, satin_floor_content_gate=True,
                              is_photographic=True)))
    assert "satin" not in on and on & {"run", "bean"}, on


def test_stage7_detection_reaches_the_floor_through_apply_detection():
    cfg = PipelineConfig(satin_floor_content_gate=True, detect_photographic=True)
    hit = _kinds(_plan(cfg, detected=True))
    assert "satin" not in hit and hit & {"run", "bean"}, hit
    assert "satin" in _kinds(_plan(cfg, detected=False))


def test_stage7_normal_bar_stays_satin_when_the_gate_applies():
    cfg = PipelineConfig(satin_floor_content_gate=True, is_photographic=True)
    assert "satin" in _kinds(_plan(cfg, poly=BAR))


def test_stage5_compensation_follows_the_floor():
    """Stage 5 must read the same verdict as stage 7: a floored hairline is a
    run there, so it is not compensated along a satin axis."""
    region = _one_shape_result(HAIRLINE, "gradient").regions[0]
    base = PipelineConfig()
    _axis, is_satin = _comp_axis(region, base, SATIN_MAX, "gradient")
    assert is_satin
    on = replace(base, satin_floor_content_gate=True, is_photographic=True)
    _axis, is_satin = _comp_axis(region, on, SATIN_MAX, "gradient")
    assert not is_satin
