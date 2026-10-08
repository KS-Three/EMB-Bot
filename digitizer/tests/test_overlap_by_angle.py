"""`cfg.overlap_by_angle` — Law 26's angle-conditional underlap (defect 47).

Two fills abutting on a straight seam: the earlier one's tongue under the
later one is `pull + overlap`, and with the flag it deepens toward
`pull + overlap_parallel_mm` as the two fills' rows approach parallel. OFF
must be the engine before it, byte for byte; a satin on either side keeps
the scalar.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps

FABRIC = get_fabric("pique_knit")


def _pair(angle_a, angle_b, tier_b="fill"):
    # Left square sews first (layer 0), right square second (layer 1); the
    # seam is x = 0, 20 mm long. Both 20 mm wide, so neither reads satin.
    a = Region(shape_id="A", polygon=box(-20, 0, 0, 20), thread_index=0,
               thread_number="1000", area_mm2=400.0,
               meta={"layer": 0, "tier": "fill", "fill_angle_deg": angle_a})
    b = Region(shape_id="B", polygon=box(0, 0, 20, 20), thread_index=1,
               thread_number="2000", area_mm2=400.0,
               meta={"layer": 1, "tier": tier_b, "fill_angle_deg": angle_b})
    return [a, b]


def _tongue(regions, **kw):
    cfg = PipelineConfig(**kw)
    planned, _ = resolve_overlaps(regions, FABRIC, cfg)
    a = next(p for p in planned if p.shape_id == "A")
    return a.polygon.bounds[2]          # how far right of the seam A reaches


def test_off_is_the_scalar_underlap():
    pull = FABRIC.pull_comp_mm
    assert _tongue(_pair(0, 0)) == pytest.approx(pull + 0.25, abs=0.02)


def test_off_is_byte_identical_whatever_the_parallel_value():
    regs = _pair(0, 0)
    base = resolve_overlaps(regs, FABRIC, PipelineConfig())[0]
    other = resolve_overlaps(regs, FABRIC, PipelineConfig(overlap_parallel_mm=3.0))[0]
    assert [p.polygon.wkb for p in base] == [p.polygon.wkb for p in other]


@pytest.mark.parametrize("a,b,want", [
    (0, 0, 1.0),          # rows parallel: the law's woven figure
    (0, 180, 1.0),        # same axis, opposite heading
    (0, 90, 0.25),        # perpendicular: never less than today
    (30, 90, 0.25 + 0.75 * 0.5),   # 60 deg apart: |cos| = 0.5
])
def test_on_deepens_with_parallel_rows(a, b, want):
    pull = FABRIC.pull_comp_mm
    assert _tongue(_pair(a, b), overlap_by_angle=True) == pytest.approx(pull + want, abs=0.02)


def test_a_satin_neighbour_keeps_the_scalar():
    pull = FABRIC.pull_comp_mm
    regs = _pair(0, 0, tier_b="satin")
    assert _tongue(regs, overlap_by_angle=True) == pytest.approx(pull + 0.25, abs=0.02)


def test_the_tongue_never_leaves_the_later_shape():
    regs = _pair(0, 0)
    planned, _ = resolve_overlaps(regs, FABRIC, PipelineConfig(overlap_by_angle=True))
    a = next(p for p in planned if p.shape_id == "A")
    later = regs[1].polygon
    outside = a.polygon.difference(regs[0].polygon.buffer(FABRIC.pull_comp_mm + 1e-6))
    assert outside.difference(later.buffer(1e-6)).area < 1e-6
