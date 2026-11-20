"""Flow follow-ups (Kent, 2026-11-19: like shapes sew alike). Both ON since 2026-11-19.

1. `cfg.satin_rect_lock_in_column`: the flag's "red dot". A stripe's
   last cross is followed by `stitches.tie_off`'s bounce, 0.8 mm along the cross
   itself (the cap face); the preview draws it as a nub at every stripe end on
   the last-sewn colour. ON, the lock retraces the last cross instead.
2. `cfg.read_primitives`: a traced rectangle / circle / triangle sews
   as the ideal shape (`primitives.read_primitive`).
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.affinity import rotate
from shapely.geometry import Point, Polygon, box

from digitizer_core import stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.primitives import read_primitive, read_regions
from digitizer_core.regions import Region
from tests.conftest import FLOW_2026_11_19_OFF, PRE_FLIP


# --- primitives ---------------------------------------------------------------

def _round_corners(poly, r):
    return poly.buffer(-r).buffer(r)


@pytest.mark.parametrize("poly,kind", [
    (_round_corners(box(0, 0, 12, 12), 0.3), "rect"),               # a square, tracing's rounded corners
    (_round_corners(box(0, 0, 20, 8), 0.3), "rect"),
    (rotate(_round_corners(box(0, 0, 20, 8), 0.25), 23, origin="centroid"), "rect"),
    (Point(3, 4).buffer(5.0, 8).simplify(0.02), "circle"),          # a faceted circle
    (_round_corners(Polygon([(0, 0), (14, 0), (7, 12)]), 0.3), "triangle"),
])
def test_a_simple_shape_is_read(poly, kind):
    got = read_primitive(poly)
    assert got is not None and got[0] == kind
    assert poly.hausdorff_distance(got[1]) <= (0.33 if kind == "triangle" else 0.2)


def test_a_rectangle_a_hair_off_the_axes_snaps_to_them():
    tilted = rotate(_round_corners(box(0, 0, 60, 4), 0.2), 0.04, origin="centroid")
    ideal = read_primitive(tilted)[1]
    assert ideal.equals(box(*tilted.bounds))                    # axis-aligned, not tilted 0.04 deg
    real = read_primitive(rotate(_round_corners(box(0, 0, 60, 4), 0.2), 3.0, origin="centroid"))[1]
    assert not real.equals(box(*real.bounds))                   # a real tilt is kept


def test_twin_shapes_become_one_shape():
    a = _round_corners(box(0, 0, 12, 12), 0.1)
    b = _round_corners(box(30, 5, 42, 17), 0.4)
    ia, ib = read_primitive(a)[1], read_primitive(b)[1]
    assert ia.area == pytest.approx(ib.area, abs=1e-6)
    assert ia.area == pytest.approx(144.0, abs=1e-6)


@pytest.mark.parametrize("poly", [
    box(0, 0, 12, 12),                                              # already exact
    Point(0, 0).buffer(5.0, 32).union(Point(7, 0).buffer(5.0, 32)),  # two circles
    box(0, 0, 12, 12).difference(box(4, 4, 8, 8)),                  # a hole
    _round_corners(box(0, 0, 12, 12), 2.0),                         # a drawn rounded square
    Polygon([(0, 0), (10, 0), (10, 5), (5, 5), (5, 10), (0, 10)]),  # an L
    Polygon([(0, 0), (14, 0), (7, 12)]).buffer(-1).buffer(1.6),     # a pillow, not a triangle
    box(0, 0, 1.0, 1.0),                                            # under the size floor
    Point(0, 0).buffer(6.0, 8).intersection(box(-6, -6, 6, 2)),     # a cut circle
])
def test_other_shapes_are_left_alone(poly):
    assert read_primitive(poly) is None


def test_regions_swap_polygon_and_area_only():
    poly = _round_corners(box(0, 0, 12, 12), 0.3)
    r = Region(shape_id="Sabc", polygon=poly, thread_index=3, thread_number="X",
               area_mm2=poly.area, meta={"k": 1})
    (out,) = read_regions([r])
    assert out.shape_id == "Sabc" and out.thread_index == 3 and out.meta["k"] == 1
    assert out.meta["primitive"] == "rect"
    assert out.area_mm2 == pytest.approx(144.0, abs=1e-6)
    assert read_regions([out])[0] is out                            # idempotent


def test_ships_on_and_false_is_the_old_engine():
    # Kent, 2026-11-19: "satin_rect_lock_in_column (Recommended), read_primitives"
    for k in ("satin_rect_lock_in_column", "read_primitives"):
        assert getattr(PipelineConfig(), k) is True
        assert PRE_FLIP[k] is False
        assert getattr(PipelineConfig(**{k: False}), k) is False


# --- the lock -----------------------------------------------------------------

RED = (66, 25, 179)
GOLD = (40, 190, 240)
ROW_PX = 48
STRIPES = 5


@pytest.fixture(scope="module")
def stripes():
    art = np.full((ROW_PX * STRIPES, 1200, 4), 255, np.uint8)
    for i in range(STRIPES):
        art[i * ROW_PX:(i + 1) * ROW_PX, :, :3] = RED if i % 2 == 0 else GOLD
    return art


def _sew(art, **flags):
    cfg = PipelineConfig(target_width_mm=100, forced_class="flat", edge_cap="none",
                         garment_id="left_chest", garment_rgb=(235, 232, 223), **flags)
    return digitize(art.copy(), cfg)[1]


def _tails(plan):
    """Length of the last two stitches of every satin run, mm."""
    out = []
    for b in plan.blocks:
        for r in b.runs:
            if r.kind == stitches.SATIN and len(r.points) > 8:
                p = r.points
                out.append(max(math.dist(p[-2], p[-1]), math.dist(p[-3], p[-2])))
    return out


def test_off_the_lock_bounces_along_the_cap_face(stripes):
    plan = _sew(stripes, **FLOW_2026_11_19_OFF)
    assert any(t < 1.0 for t in _tails(plan))            # the 0.8 mm nub


def test_on_the_lock_retraces_the_last_cross(stripes):
    off = _sew(stripes, **FLOW_2026_11_19_OFF)
    on = _sew(stripes, read_primitives=False)
    t = _tails(on)
    assert t and min(t) > 3.0                             # every tail is a whole cross
    n_off = sum(len(r.points) for b in off.blocks for r in b.runs)
    n_on = sum(len(r.points) for b in on.blocks for r in b.runs)
    assert abs(n_on - n_off) <= 4 * STRIPES * 2           # a lock for a lock, not more thread
    # same geometry otherwise: the needle never leaves the art's extent
    xs = [p[0] for b in on.blocks for r in b.runs for p in r.points]
    xo = [p[0] for b in off.blocks for r in b.runs for p in r.points]
    assert max(xs) <= max(xo) + 1e-9 and min(xs) >= min(xo) - 1e-9


def test_a_run_not_in_the_set_is_tied_as_before():
    run = stitches.StitchRun(points=[(0, 0), (0, 4), (0.4, 0), (0.4, 4)], kind=stitches.SATIN, shape_id="S1")
    other = stitches.StitchRun(points=list(run.points), kind=stitches.SATIN, shape_id="S1")
    stitches.tie_off(run, {"S2#satin"})
    stitches.tie_off(other, None)
    assert run.points == other.points
    locked = stitches.StitchRun(points=list(other.points[:4]), kind=stitches.SATIN, shape_id="S1")
    stitches.tie_off(locked, {"S1#satin"})
    assert locked.points[:4] == list(other.points[:4])
    assert len(locked.points) == 5 and locked.points[-1] == (0.4, 0)   # back over the last cross
