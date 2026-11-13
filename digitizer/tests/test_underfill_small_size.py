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
from digitizer_core.preflight import run_preflight
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


_GRADE_RANK = {"A": 4, "B": 3, "C": 2, "D": 1, "F": 0}
BLACK_WHITE_BLACK = ["0020 Black", "0015 White", "0020 Black"]
#: (width mm, forced_class, preflight grade floor). Floors are what main gave after this
#: change (2026-11-04), not a target; a better grade passes, a worse one fails.
#: Source: the Studio hat_front config on `logo_mfab_hat.png`, one run per row.
SWEEP = [
    (30.0, "flat", "B"), (30.0, None, "B"),
    (36.7, "flat", "C"), (36.7, None, "B"),
    (60.0, "flat", "C"), (60.0, None, "C"),
    (80.0, "flat", "B"), (80.0, None, "C"),
    (100.8, "flat", "B"), (100.8, None, "B"),
    (113.5, "flat", "B"), (113.5, None, "B"),
]
#: 60 mm, default route: black then white, no second black. The small line
#: "AND WELDING LLC" sews as white satin over the black instead of black riders
#: (rendered 2026-11-04). The same family as the 100.8 mm WELDING merge another
#: session is diagnosing; expected to fail until that lands. strict: when it
#: starts passing, this mark must go.
KNOWN_WRONG_ORDER = {(60.0, None)}


def _run(width_mm, forced, photo_work_grid=False):
    # photo_prep=False: the no-cutout lane CI runs (no rembg venv there). With the
    # venv the 60 mm default row sews in order; tests/test_mfab_cutout_lane.py.
    cfg = PipelineConfig(photo_prep=False, target_width_mm=width_mm, max_colors=6, satin=True,
                         detail_layer=False, edge_cap="none", sew_enclosed_white=True,
                         sew_enclosed_rgb=(255, 255, 255), faces_route_flat=True,
                         garment_id="hat_front", garment_rgb=(235, 232, 223),
                         forced_class=forced, photo_work_grid=photo_work_grid)
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
    res = finish_generation(build_generation(pix, cfg), cfg)
    plan = plan_stitches(res, cfg)
    design = plan_to_design(plan, name="t")
    return [c["name"] for c in design["colors"]], run_preflight(res, plan, cfg, image=pix)["grade"]


def _params():
    for w, forced, floor in SWEEP:
        marks = []
        if (w, forced) in KNOWN_WRONG_ORDER:
            marks.append(pytest.mark.xfail(strict=True, reason="small line sews white over black (see KNOWN_WRONG_ORDER)"))
        yield pytest.param(w, forced, floor, marks=marks, id=f"{w}-{forced or 'default'}")


@pytest.mark.parametrize("width,forced,floor", list(_params()))
def test_mfab_hat_size_sweep_order_and_grade(width, forced, floor):
    # the white keyline sews ON the black band, never under it, at every size; the
    # preflight grade does not fall below what it was when this was written
    blocks, grade = _run(width, forced)
    assert blocks == BLACK_WHITE_BLACK
    assert _GRADE_RANK[grade] >= _GRADE_RANK[floor], f"grade {grade} under the {floor} floor"


#: `cfg.photo_work_grid` (2026-11-05, OFF): the photo lane takes the 8 px/mm working grid
#: too. This art classes photo_scene at every width; at 60 and 100.8 mm it reaches the lane
#: at 6.7 and 4.0 px/mm with W and E joined by a one-pixel bridge (one untagged region, no
#: rider, merged into the black host). ON, the order is the 113.5 mm one at both widths.
@pytest.mark.parametrize("width,floor", [(60.0, "C"), (100.8, "B")])
def test_mfab_hat_photo_work_grid_keeps_the_small_line_black(width, floor):
    blocks, grade = _run(width, None, photo_work_grid=True)
    assert blocks == BLACK_WHITE_BLACK
    assert _GRADE_RANK[grade] >= _GRADE_RANK[floor], f"grade {grade} under the {floor} floor"
