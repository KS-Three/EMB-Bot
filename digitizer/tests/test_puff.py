"""3D puff (docs/superpowers/specs/2026-11-19-3d-puff-design.md): config switch,
constants and the per-shape eligibility test."""
from __future__ import annotations

from types import SimpleNamespace

from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.stage6_puff import puff_eligible, wants_puff


def _region(w_mm: float, h_mm: float = 30.0, **meta):
    return SimpleNamespace(polygon=box(0, 0, h_mm, w_mm), meta=dict(meta))


def test_puff_off_by_default():
    cfg = PipelineConfig()
    assert cfg.puff is False
    assert cfg.puff_mode == "all"


def test_wants_puff_modes():
    off = PipelineConfig(puff=False)
    assert wants_puff(_region(4, puff=True), off) is False
    assert wants_puff(_region(4), off) is False

    allm = PipelineConfig(puff=True, puff_mode="all")
    assert wants_puff(_region(4), allm) is True
    assert wants_puff(_region(4, puff=False), allm) is False
    assert wants_puff(_region(4, puff=True), allm) is True

    sel = PipelineConfig(puff=True, puff_mode="select")
    assert wants_puff(_region(4), sel) is False
    assert wants_puff(_region(4, puff=False), sel) is False
    assert wants_puff(_region(4, puff=True), sel) is True


def test_puff_eligible_width():
    cfg = PipelineConfig(puff=True)
    assert puff_eligible(_region(4), cfg) == (True, "")
    # measure_width_mm is skeleton-based and reads a bar a little off its
    # nominal width (1.8 -> 1.9, 20 -> 12.2 on a 30 mm bar), so the expected
    # strings are the measured values, not the nominal ones.
    assert puff_eligible(_region(1.8), cfg) == (False, "too thin for foam (1.9 mm)")
    assert puff_eligible(_region(20), cfg) == (False, "too wide to puff (12.2 mm)")


def test_puff_eligible_ignores_flat_satin_ceiling():
    # 8 mm is past the flat satin ceiling (5.0) but inside the puff band.
    assert puff_eligible(_region(8), PipelineConfig(puff=True)) == (True, "")
