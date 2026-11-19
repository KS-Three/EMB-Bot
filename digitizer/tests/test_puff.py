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
    # Thin uses the skeleton mean (reads 1.8 as 1.9); wide uses the widest
    # inscribed circle, which is exact on a bar (the mean read 14 as 9.8).
    assert puff_eligible(_region(1.8), cfg) == (False, "too thin for foam (1.9 mm)")
    assert puff_eligible(_region(14), cfg) == (False, "too wide to puff (14.0 mm)")


def test_puff_eligible_ignores_flat_satin_ceiling():
    # 8 mm is past the flat satin ceiling (5.0) but inside the puff band.
    assert puff_eligible(_region(8), PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_ring_uses_ring_width_not_hole_blind_circle():
    from shapely.geometry import Point
    ring = Point(0, 0).buffer(10, 64).difference(Point(0, 0).buffer(6, 64))
    reg = SimpleNamespace(polygon=ring, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_multipolygon_does_not_raise():
    from shapely.geometry import MultiPolygon
    mp = MultiPolygon([box(0, 0, 30, 4), box(0, 20, 30, 24)])
    reg = SimpleNamespace(polygon=mp, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")
