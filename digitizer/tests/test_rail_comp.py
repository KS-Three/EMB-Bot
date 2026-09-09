"""`cfg.satin_rail_comp` — pull compensation on the rails, not the polygon.
DEFAULT OFF (quality review 2026-09-08 item 6, built 2026-09-09).

Stage 5 grows every shape by the fabric's pull with a round join and the
satin tier skeletonises the grown polygon: arcs on every corner, slots
2 x pull narrower, a skeleton that welds across them. ON, a satin-tier shape
keeps its artwork polygon in stage 5 and `_rail_points` moves each rail
outward by the same pull, held back where a counter would close under
`min_detail_mm`. The AMOUNT never changes (gate 1); where it lands does.

What these tests guarantee: OFF is the shipped path; ON sews a satin shape
on its artwork with rails one pull outside it and caps not lengthened; a
counter is held open; fills and widened lettering are untouched.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_satin as s6
from digitizer_core import stage7_sequence as s7
from digitizer_core.pipeline import digitize, fabric_for
from digitizer_core.stage5_overlap import widened_lettering
from digitizer_core.stitches import strip_ties
from tests.conftest import TESTDATA

PULL = fabric_for(PipelineConfig(garment_id="left_chest")).pull_comp_mm


def _png(path: Path, ink: np.ndarray, px_per_mm: float = 10.0) -> None:
    cv2.imwrite(str(path), ink)


def _bar_png(path: Path, w_mm: float, h_mm: float, px_per_mm: float = 10.0) -> None:
    W, H = int((w_mm + 20) * px_per_mm), int((h_mm + 20) * px_per_mm)
    img = np.full((H, W, 3), 255, np.uint8)
    x0, y0 = int(10 * px_per_mm), int(10 * px_per_mm)
    img[y0:y0 + int(h_mm * px_per_mm), x0:x0 + int(w_mm * px_per_mm)] = (20, 20, 20)
    _png(path, img)


def _ring_png(path: Path, outer_mm: float, hole_mm: float, px_per_mm: float = 10.0) -> None:
    W = H = int((outer_mm + 20) * px_per_mm)
    img = np.full((H, W, 3), 255, np.uint8)
    o0 = int(10 * px_per_mm)
    img[o0:o0 + int(outer_mm * px_per_mm), o0:o0 + int(outer_mm * px_per_mm)] = (20, 20, 20)
    h0 = o0 + int((outer_mm - hole_mm) / 2 * px_per_mm)
    img[h0:h0 + int(hole_mm * px_per_mm), h0:h0 + int(hole_mm * px_per_mm)] = (255, 255, 255)
    _png(path, img)


def _sewn(path: Path, **kw):
    """-> (result, plan, {shape_id: the polygon satin_shape received})."""
    seen: dict = {}
    real = s6.satin_shape

    def spy(poly, shape_id, **kwargs):
        seen[shape_id] = poly
        return real(poly, shape_id, **kwargs)

    s7.satin_shape = spy
    try:
        result, plan = digitize(path, PipelineConfig(garment_id="left_chest", **kw))
    finally:
        s7.satin_shape = real
    return result, plan, seen


def _satin_points(plan, shape_id: str) -> list:
    """The shape's satin penetrations, lock stitches stripped — a tie is 3 mm
    of thread bounced on one point and would read as an overshoot."""
    return [p for _b, r in plan.iter_runs() if r.kind == "satin" and r.shape_id == shape_id
            for p in strip_ties(r.points)]


def _outside(points, poly: Polygon) -> float:
    """How far the farthest point sits outside the polygon, mm — past its
    outer edge or into one of its counters."""
    return max((poly.boundary.distance(Point(p)) if not poly.covers(Point(p)) else 0.0)
               for p in points)


def test_the_flag_is_off_by_default():
    """The amount is gate 1's; where it lands is Kent's on the render."""
    assert PipelineConfig().satin_rail_comp is False
    assert PULL > 0, "the polo preset stopped carrying a pull, so nothing here is measurable"


def test_a_bar_is_sewn_on_its_artwork_with_rails_one_pull_outside_and_caps_not_lengthened(tmp_path):
    """OFF the bar is sewn on a polygon grown all round — the rails one pull
    outside AND the caps one pull past the artwork's ends. ON the polygon
    is the artwork: the rails still sit one pull outside (the widening the
    fabric's pull earns is untouched) and the caps stop at the artwork."""
    png = tmp_path / "bar.png"
    _bar_png(png, 24.0, 3.0)
    off_r, off_p, off_seen = _sewn(png, target_width_mm=24.0)
    on_r, on_p, on_seen = _sewn(png, target_width_mm=24.0, satin_rail_comp=True)
    sid = next(iter(on_seen))
    art = next(r.polygon for r in on_r.regions if r.shape_id == sid)
    assert not off_seen[sid].equals(art), "OFF must still sew the grown polygon"
    assert on_seen[sid].equals(art), "ON must sew the artwork polygon"
    off_pts, on_pts = _satin_points(off_p, sid), _satin_points(on_p, sid)
    assert len(on_pts) > 40 and len(off_pts) > 40
    # rails: one pull outside the artwork, both ways
    assert abs(_outside(on_pts, art) - PULL) < 0.08, _outside(on_pts, art)
    assert abs(_outside(off_pts, art) - PULL) < 0.08, _outside(off_pts, art)
    # caps: OFF reaches a pull past the artwork's ends, ON stops at them
    x0, _y0, x1, _y1 = art.bounds
    off_reach = max(max(p[0] for p in off_pts) - x1, x0 - min(p[0] for p in off_pts))
    on_reach = max(max(p[0] for p in on_pts) - x1, x0 - min(p[0] for p in on_pts))
    assert off_reach > 0.6 * PULL, off_reach
    assert on_reach < 0.12, on_reach


def test_the_hole_guard_keeps_a_small_counter_at_the_detail_floor(tmp_path):
    """A 9 mm ring (3.5 mm wide) with a 2.0 mm counter on a 1.5 mm floor: the
    naive push would leave the counter 1.4 mm across in the file. Held, each
    rail takes a quarter millimetre and the counter keeps its 1.5; a wide
    counter takes the full pull."""
    png = tmp_path / "ring.png"
    _ring_png(png, 9.0, 2.0)
    r, p, seen = _sewn(png, target_width_mm=9.0, satin_rail_comp=True)
    sid = next(iter(seen))
    art = next(rg.polygon for rg in r.regions if rg.shape_id == sid)
    assert seen[sid].equals(art) and len(art.interiors) == 1, "the ring must sew as satin on its artwork"
    hole = Polygon(art.interiors[0])
    cx, cy = hole.centroid.x, hole.centroid.y
    pts = _satin_points(p, sid)
    inner = min(max(abs(q[0] - cx), abs(q[1] - cy)) for q in pts)
    # the counter's half-width (1.0) less the held push (0.25) = 0.75 from centre
    floor_half = PipelineConfig().min_detail_mm / 2.0
    assert inner >= floor_half - 0.06, f"a rail sits {inner:.2f} mm from the counter's centre"
    # and the outside rails carry the full pull
    outer = max(art.exterior.distance(Point(q)) for q in pts if not art.buffer(1e-6).covers(Point(q))
                and hole.exterior.distance(Point(q)) > 0.5)
    assert abs(outer - PULL) < 0.08, outer

    wide = tmp_path / "wide_ring.png"
    _ring_png(wide, 14.0, 8.0)
    r2, p2, seen2 = _sewn(wide, target_width_mm=14.0, satin_rail_comp=True)
    sid2 = next(iter(seen2))
    art2 = next(rg.polygon for rg in r2.regions if rg.shape_id == sid2)
    hole2 = Polygon(art2.interiors[0])
    pts2 = _satin_points(p2, sid2)
    deepest = max(hole2.exterior.distance(Point(q)) for q in pts2 if hole2.covers(Point(q)))
    assert abs(deepest - PULL) < 0.08, f"a wide counter should take the whole pull, took {deepest:.2f}"


def test_the_end_cutback_owes_only_the_push_on_rails(tmp_path):
    """Under directional comp the cutback is `pull + PUSH` because the buffer
    lengthened the column; on the artwork nothing did, so it is PUSH alone --
    and the two land the column's END STATION in the same place, `PUSH` short
    of the artwork cap. Measured by the last cross's midpoint: the crosses
    at a bar's ends lean a few degrees on the skeleton both paths share
    (the skeleton is the grown polygon's under the flag too), so the
    outermost NEEDLE point sits nearer the cap than the station does --
    0.16 mm on this bar, the same OFF and ON -- and is not what the cutback
    positions. The flag moves the column's width, never its length."""
    png = tmp_path / "bar.png"
    _bar_png(png, 24.0, 3.0)
    _r, off_p, off_seen = _sewn(png, target_width_mm=24.0, directional_comp=True)
    r, on_p, on_seen = _sewn(png, target_width_mm=24.0, directional_comp=True, satin_rail_comp=True)
    sid = next(iter(on_seen))
    assert set(off_seen) == set(on_seen)
    art = next(rg.polygon for rg in r.regions if rg.shape_id == sid)
    x0, _y0, x1, _y1 = art.bounds

    def short(plan):
        pts = _satin_points(plan, sid)
        mids = [(pts[i][0] + pts[i + 1][0]) / 2.0 for i in range(0, len(pts) - 1, 2)]
        return min(x1 - max(mids), min(mids) - x0)

    assert abs(short(on_p) - machine.PUSH_CUTBACK_MM) < 0.1, short(on_p)
    assert abs(short(on_p) - short(off_p)) < 0.05, (short(off_p), short(on_p))


def test_on_the_wordmark_every_satin_shape_sews_on_its_artwork():
    """The drone wordmark: OFF every satin shape sews on a polygon grown all
    round its artwork; ON the artwork is contained and what lies outside it
    is only the underlap tongue under a later colour (and the clip of an
    earlier one) -- less than half of OFF's growth band on every shape."""
    art = TESTDATA / "photo" / "drone_render.png"
    off_r, _off_p, off_seen = _sewn(art)
    on_r, _on_p, on_seen = _sewn(art, satin_rail_comp=True)
    art_by_id = {rg.shape_id: rg.polygon for rg in on_r.regions}
    assert len(on_seen) >= 30 and set(on_seen) == set(off_seen)
    total_off = total_on = 0.0
    for s in on_seen:
        a = art_by_id[s]
        extra_off = off_seen[s].difference(a).area
        extra_on = on_seen[s].difference(a).area
        # never more outside the artwork than the grown polygon had (a
        # letter on an earlier colour is clipped back to it either way)
        assert extra_on <= extra_off + 1e-6, f"{s}: ON carries {extra_on:.2f} mm2 outside its artwork, OFF {extra_off:.2f}"
        total_off += extra_off
        total_on += extra_on
    assert total_on < 0.5 * total_off, (total_on, total_off)


def test_widened_lettering_keeps_its_compensated_column(tmp_path):
    """The column floor's population is classified and sewn on the polygon
    stage 5 grows for it (2026-09-09); rail comp must leave that alone. The
    fixture is the widened-lettering tests' own thin bars."""
    from unittest.mock import patch
    from tests.test_widened_lettering_tier import _thin_bars, FLOOR_MM, _OCR_GATE_PATH
    art = tmp_path / "bars.png"
    _thin_bars(art)
    with patch(_OCR_GATE_PATH, return_value=False):
        r, _p, seen = _sewn(art, target_width_mm=50.0, lettering_min_column_mm=FLOOR_MM,
                            satin_rail_comp=True)
    widened = [rg for rg in r.regions if widened_lettering(rg) and rg.shape_id in seen]
    assert len(widened) >= 5, "the fixture stopped widening any glyph"
    for rg in widened:
        assert not seen[rg.shape_id].equals(rg.polygon), \
            f"{rg.shape_id}: a widened glyph lost its column to rail comp"
        assert seen[rg.shape_id].area > rg.polygon.area * 1.3


def test_push_rails_pushes_a_pinched_cross_and_leaves_a_directionless_one():
    """`_push_rails`: a pinched 0.2 mm cross is pushed to 0.8 — the cross the
    grown polygon would have carried, and what the drop check must see; a
    cross whose two rails sit on the same point has nothing to push along
    and stays degenerate."""
    poly = Polygon([(0, 0), (10, 0), (10, 4), (0, 4)])
    a = [(5.0, 2.1), (6.0, 3.0), (7.0, 2.0)]
    b = [(5.0, 1.9), (6.0, 1.0), (7.0, 2.0)]
    pa, pb = s6._push_rails(a, b, poly, 0.3, 1.5)
    assert abs(math.dist(pa[0], pb[0]) - 0.8) < 1e-9
    assert abs(math.dist(pa[1], pb[1]) - (2.0 + 0.6)) < 1e-9
    assert pa[2] == a[2] and pb[2] == b[2]
