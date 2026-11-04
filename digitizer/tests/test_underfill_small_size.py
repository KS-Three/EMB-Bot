"""The under-fill ring floor follows the design's size (2026-11-04).

MFab hat at DADE's fixed 36.7 mm: the black band is 139 mm2, under the absolute
`RING_MIN_AREA_MM2` (200), so `silhouette_underfill` read no ring, white sewed
first and the black band sewed over it -- `['0015 White', '0020 Black']`, a solid
black blob once rendered. At 113.5 mm the band is ~1,330 mm2 and the order is
black, white, black. The band is 26% of the design's box at both sizes, so the
floor is held to `RING_MIN_BOX_FRAC` of the box (200 at 5,000 mm2: designs that
size and larger are unchanged).
"""
from __future__ import annotations

import cv2
import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, silhouette_underfill as su
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.adapter import plan_to_design
from digitizer_core.regions import Region

from .conftest import TESTDATA


def _reg(sid, poly):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area, source="test", meta={"layer": 0})


def test_floor_is_200_on_a_big_design_and_shrinks_on_a_small_one():
    big = [_reg("a", box(0, 0, 113.5, 44))]                # 4,994 mm2
    small = [_reg("a", box(0, 0, 36.7, 14.35))]            # 527 mm2
    assert su._ring_floor(big) == pytest.approx(199.8, abs=0.5)
    assert su._ring_floor([_reg("a", box(0, 0, 200, 100))]) == su.RING_MIN_AREA_MM2
    assert su._ring_floor(small) == su.RING_MIN_FLOOR_MM2
    assert su._ring_floor([]) == su.RING_MIN_AREA_MM2


def _blocks(width_mm, forced):
    cfg = PipelineConfig(target_width_mm=width_mm, max_colors=6, satin=True,
                         detail_layer=False, edge_cap="none", sew_enclosed_white=True,
                         sew_enclosed_rgb=(255, 255, 255), faces_route_flat=True,
                         garment_id="hat_front", garment_rgb=(235, 232, 223),
                         forced_class=forced)
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
    res = finish_generation(build_generation(pix, cfg), cfg)
    design = plan_to_design(plan_stitches(res, cfg), name="t")
    return [c["name"] for c in design["colors"]]


@pytest.mark.parametrize("width", [36.7, 113.5])
def test_mfab_hat_flat_sews_black_white_black_at_both_sizes(width):
    # the white keyline sews ON the black band, never under it
    assert _blocks(width, "flat") == ["0020 Black", "0015 White", "0020 Black"]
