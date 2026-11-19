"""A rectangle sews as a rectangle: `cfg.extra["satin_rectangles"]` (built OFF 2026-11-19).

Kent's Flag.webp at 113.5 mm (the Studio, 2026-11-19, "I thought you fixed the
Flag!?"; then "a square needs to be square"): the skeleton tier's spine forks
into each stripe's corners and stops short of the end, so a stripe's end was
rounded by up to 0.46 mm and the flag's right edge wandered 2.9 mm. ON, a true
rectangle of any length takes the straight-slot column path, rails held at the
seam with the colour already down (`cfg.satin_seam_hold`): every end square to
0.04 mm, stripe heights as today's.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.affinity import rotate
from shapely.geometry import Point, Polygon, box

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import is_rectangle_bar, is_straight_slot


def test_built_off():
    assert not (PipelineConfig().extra or {}).get("satin_rectangles")


@pytest.mark.parametrize("poly", [
    box(0, 0, 68.0, 4.6),                           # a flag stripe at 113.5 mm
    rotate(box(0, 0, 40.0, 3.0), 30, origin="centroid"),
    box(0, 0, 9.0, 4.0),                            # short ones too
])
def test_a_rectangle_reads_as_one(poly):
    assert is_rectangle_bar(poly, 7.0)


@pytest.mark.parametrize("poly", [
    box(0, 0, 12.0, 3.0).buffer(-1.0).buffer(1.0),  # 1 mm round corners: fills 0.976, sits 0.41 off
    box(0, 0, 12.0, 3.0).buffer(-1.5).buffer(1.5),  # a stadium
    Point(0, 0).buffer(5.0).union(Point(9, 0).buffer(5.0)),
    Polygon([(0, 0), (30, 0), (15, 4)]),            # a triangle has three points
    box(0, 0, 40.0, 9.0),                           # wider than the satin ceiling
    box(0, 0, 4.0, 4.0),                            # a square: not a bar
    box(0, 0, 40.0, 4.0).difference(box(10, 1, 12, 3)),   # a hole
])
def test_other_shapes_do_not(poly):
    assert not is_rectangle_bar(poly, 7.0)


def test_the_slot_test_is_unchanged_by_it():
    # a stripe is far past the slot's elongation 4: the slot path never took it
    assert not is_straight_slot(box(0, 0, 68.0, 4.6), 7.0)


# --- the whole pipeline, on stripes alone ------------------------------------

RED = (66, 25, 179)     # BGR, as an array reaches stage 0
GOLD = (40, 190, 240)
NAVY = (88, 40, 10)
STRIPES = 7
ROW_PX = 48             # 4 mm at 100 mm wide


@pytest.fixture(scope="module")
def stripes():
    """`test_satin_flag_stripes`' art: opaque BGRA, stripes and a canton."""
    art = np.full((ROW_PX * STRIPES, 1200, 4), 255, np.uint8)
    for i in range(STRIPES):
        art[i * ROW_PX:(i + 1) * ROW_PX, :, :3] = RED if i % 2 == 0 else GOLD
    art[:ROW_PX * 4, :480, :3] = NAVY
    return art


def _sew(art, on: bool):
    cfg = PipelineConfig(target_width_mm=100, forced_class="flat", edge_cap="none",
                         garment_id="left_chest", garment_rgb=(235, 232, 223),
                         **({"extra": {"satin_rectangles": True}} if on else {}))
    return digitize(art.copy(), cfg)[1]


def _right_ends(plan) -> list[float]:
    """For each satin shape that reaches the art's right edge: how far its top
    rail's last needle and its bottom rail's last needle differ, mm."""
    shapes: dict[str, list] = {}
    for b in plan.blocks:
        for r in b.runs:
            if r.kind == "satin":
                shapes.setdefault(r.shape_id, []).extend(r.points)
    xmax = max(p[0] for pts in shapes.values() for p in pts)
    out = []
    for pts in shapes.values():
        a = np.asarray(pts, float)
        if a[:, 0].max() < xmax - 1.0:
            continue
        lo, hi = np.percentile(a[:, 1], 5), np.percentile(a[:, 1], 95)
        top = a[a[:, 1] >= hi - 0.2, 0].max()
        bot = a[a[:, 1] <= lo + 0.2, 0].max()
        out.append(abs(top - bot))
    return out


def test_every_stripe_ends_square(stripes):
    ends = _right_ends(_sew(stripes, on=True))
    assert len(ends) >= STRIPES - 1
    assert max(ends) < 0.1


def test_the_seam_hold_still_holds(stripes):
    """The last colour sews its art height, not a pull wider on each seam."""
    plan = _sew(stripes, on=True)
    block = [b for b in plan.blocks if any(r.kind == "satin" for r in b.runs)][-1]
    shapes: dict[str, list] = {}
    for run in block.runs:
        if run.kind == "satin":
            shapes.setdefault(run.shape_id, []).extend(p[1] for p in run.points)
    h = float(np.median([np.percentile(v, 95) - np.percentile(v, 5) for v in shapes.values()]))
    assert h == pytest.approx(100.0 * ROW_PX / 1200, abs=0.1)
