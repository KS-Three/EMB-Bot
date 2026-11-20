"""A star sews with its points: `cfg.satin_stars` (ON since 2026-11-19, Kent: "Flip ON").

Kent, on his Flag.webp (2026-11-19): "a triangle needs 3 points". The flag's 50
stars at 113.5 mm are 3.3 mm five-point stars; the Column lane (they came
tagged as lettering) and the skeleton tier both stopped every point where its
taper fell under the 0.5 mm cross floor, about 0.8 mm short of the tip, so
every star sewed as a blunt blob. ON, each point sews tip to centre with its
crosses square to its own axis, the tip reached by a walk under that satin.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.affinity import rotate, scale
from shapely.geometry import Point, Polygon, box

from digitizer_core import stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import read_star, star_satin


def _star(k=5, r_out=1.65, r_in=0.65, cx=0.0, cy=0.0, rot=90.0):
    pts = []
    for i in range(2 * k):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + 180.0 * i / k)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return Polygon(pts)


def test_ships_on():
    # Kent's flip, 2026-11-19; conftest's PRE_FLIP holds the OFF arm.
    assert PipelineConfig().satin_stars is True


@pytest.mark.parametrize("poly", [_star(), _star(k=6), _star(k=4, r_in=0.5), _star(r_out=8, r_in=3.2),
                                  rotate(_star(), 17, origin="centroid")])
def test_a_star_reads_as_one(poly):
    got = read_star(poly, 7.0)
    assert got is not None
    _c, tips, inner = got
    assert len(tips) == len(inner) == len(poly.exterior.coords) // 2


@pytest.mark.parametrize("poly", [
    Point(0, 0).buffer(2.0),                         # a circle is round, not pointed
    box(0, 0, 3, 3),                                 # a square
    Polygon([(0, 0), (4, 0), (2, 3)]),               # a triangle
    _star(r_in=1.4),                                 # inner corners near the tips: a gear, not a star
    scale(_star(), 2.5, 1.0),                        # stretched: its points are not alike
    _star(r_out=30, r_in=12),                        # a point's base past the satin ceiling
])
def test_other_shapes_do_not(poly):
    assert read_star(poly, 7.0) is None


def test_every_point_reaches_its_tip_and_every_cross_is_square_to_its_axis():
    poly = _star()
    star = read_star(poly, 7.0)
    runs, report = star_satin(poly, star, "S", spacing_mm=0.4, start_near=None)
    assert not report["empty"] and report["star_points"] == 5
    (cx, cy), tips, _inner = star
    pts = [q for r in runs for q in r.points]
    for t in tips:                                   # a needle on every tip
        assert min(math.dist(t, q) for q in pts) < 1e-9
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert len(sat) == 5                             # one pass per point: they sew alike
    assert len({len(s.points) for s in sat}) == 1
    for s in (r for r in runs if r.kind == stitches.SATIN):
        a0, b0 = s.points[0], s.points[1]
        mid = ((a0[0] + b0[0]) / 2, (a0[1] + b0[1]) / 2)
        tx, ty = min(tips, key=lambda t: math.dist(t, mid))     # the point this satin sews
        ux, uy = tx - cx, ty - cy
        n = math.hypot(ux, uy)
        for a, b in zip(s.points[0::2], s.points[1::2]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            assert abs((dx * ux + dy * uy) / (n * math.hypot(dx, dy))) < 1e-6   # square to the axis
            for q in (a, b):
                assert poly.buffer(1e-6).covers(Point(q))


def test_the_needle_never_leaves_the_star():
    # every stitch, walk, satin and step back, lies on the star: no travel on top outside it
    poly = _star()
    runs, _ = star_satin(poly, read_star(poly, 7.0), "S", spacing_mm=0.4, start_near=(5.0, 5.0))
    pts = [q for r in runs for q in r.points]
    assert all(poly.buffer(1e-6).covers(Point(q)) for q in pts)


# --- the pipeline, on a row of stars ------------------------------------------

@pytest.fixture(scope="module")
def stars():
    """White stars on navy, as the flag's canton: 1000 px over 40 mm."""
    import cv2
    art = np.full((400, 1000, 4), 255, np.uint8)
    art[:, :, :3] = (88, 40, 10)
    for j in range(4):
        poly = _star(r_out=82, r_in=32, cx=125 + 250 * j, cy=200, rot=-90)
        pts = np.array(poly.exterior.coords, np.int32)
        cv2.fillPoly(art, [pts], (255, 255, 255, 255))
    return art


def _tips_sewn(art, on):
    cfg = PipelineConfig(target_width_mm=40, forced_class="flat", edge_cap="none",
                         garment_id="left_chest", satin_stars=on)
    result, plan = digitize(art.copy(), cfg)
    out = []
    for rg in result.regions:
        star = read_star(rg.polygon, 7.0)
        if star is None:
            continue
        pts = [q for b in plan.blocks for r in b.runs if r.shape_id == rg.shape_id for q in r.points]
        out.append(max(min(math.dist(t, q) for q in pts) for t in star[1]))
    return out


def test_on_the_pipeline_every_tip_is_sewn(stars):
    on = _tips_sewn(stars, on=True)
    assert len(on) == 4
    assert max(on) < 0.05                  # a needle on every tip
    off = _tips_sewn(stars, on=False)
    assert min(off) > 0.3                  # today's: every star misses a tip by more
