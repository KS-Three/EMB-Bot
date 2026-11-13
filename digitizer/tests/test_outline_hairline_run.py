"""`cfg.border_from_outline_hairline_run` (built OFF 2026-11-13, Kent: "Build
guard, OFF") and the keyline bean it sews (`keyline_bean`).

`border_from_outline` sews the art's own outline as one satin loop at the
art's thickness clamped to `machine.OUTLINE_WIDTH_MM` (1.5 to 2.5 mm). The
1.5 floor was read off outlines 0.8 mm and up. Kent's keyline logo (a red wordmark, 2026-11-13) draws a
0.36-0.42 mm white keyline (at 100 mm wide) and sewed 1.50 mm loops, 3.7x the
art. ON, an outline the hairline tier's width gate admits whole (median width
at or under 0.6 mm at 40 wt) sews as a bean on its centreline.

Kent, the same day: "When you are doing bean stitch outlines, you need to
look at it as if you are building a swiss watch, and not a playhouse out of
logs." So the tests below pin the line itself: a needle point exactly on
every corner, even stations between, the loop closed on its first hole, three
passes in the same holes, no stretch of band sewn twice, no fill past the
line, and the line sewn after the fill it edges.
"""
from __future__ import annotations

import hashlib
import math

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, keyline_bean, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines, digitize
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

FLAG = "border_from_outline_hairline_run"
PITCH = machine.BEAN_STITCH_MM

#: a 30 x 12 mm face inside a keyline of the given thickness
FACE = box(-15, -6, 15, 6)


def _ring(width_mm: float, body=FACE):
    return body.buffer(width_mm, join_style=2).difference(body)


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _plan(width_mm: float, *, outline_meta: dict | None = None, extra=(), **cfg_kw):
    """The body (layer 0) then its outline (layer 1), both sewn -> (runs, warnings)."""
    outline = _ring(width_mm)
    b = _region("Sbody", FACE, 0, 0)
    o = _region("Souter", outline, 1, 1, **(outline_meta or {}))
    regions = [b, o, *extra]
    planned = [PlannedRegion(region=r, polygon=r.polygon, sew_index=r.meta["layer"]) for r in regions]
    cfg = PipelineConfig(underlay=False, **cfg_kw)
    outlines = _art_outlines(regions, cfg)
    if cfg.border_from_outline:
        assert outlines and "Souter" in outlines, "the fixture must read as an art outline"
    blocks, warnings = sequence(planned, fabric_for_garment("hat_front"), cfg, art_outlines=outlines)
    return [r for blk in blocks for r in blk.runs], warnings


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _kinds(runs, shape_id: str) -> set[str]:
    return {r.kind for r in runs if r.shape_id == shape_id} - {stitches.TRAVEL}


def _steps(pts) -> list[float]:
    return [math.dist(a, b) for a, b in zip(pts, pts[1:])]


# --- the flag ---------------------------------------------------------------

def test_built_off():
    assert getattr(PipelineConfig(), FLAG) is False


def test_the_numbers_this_leans_on():
    """No constant of its own: if one of these moves, re-read the guard."""
    assert machine.OUTLINE_WIDTH_MM[0] == 1.5
    assert machine.thread_profile(40).hairline_max_width_mm == pytest.approx(0.6)
    assert (machine.BEAN_STITCH_MM, machine.BEAN_PASSES) == (0.73, 3)


# --- the line: stations -----------------------------------------------------

def test_a_needle_point_exactly_on_every_corner():
    ring = list(box(0, 0, 10, 4).exterior.coords)
    pts = keyline_bean.stations(ring)
    for corner in [(0.0, 0.0), (10.0, 0.0), (10.0, 4.0), (0.0, 4.0)]:
        assert corner in pts


def test_stations_between_corners_are_even_and_near_the_bean_pitch():
    ring = list(box(0, 0, 10, 4).exterior.coords)
    pts = keyline_bean.stations(ring)
    steps = _steps(pts + pts[:1])
    assert min(steps) >= 0.5 * PITCH and max(steps) <= 1.5 * PITCH
    # each side is one even division of its own length
    top = sorted(p[0] for p in pts if p[1] == 0.0)
    gaps = {round(b - a, 9) for a, b in zip(top, top[1:])}
    assert len(gaps) == 1


def test_a_ring_with_no_corner_is_stationed_evenly_all_round():
    circle = Point(0, 0).buffer(5.0, quad_segs=64)
    pts = keyline_bean.stations(list(circle.exterior.coords))
    assert len(pts) == round(circle.exterior.length / PITCH)
    steps = _steps(pts + pts[:1])
    assert max(steps) - min(steps) < 0.01
    # the thread never leaves the circle by more than a hair
    assert LineString(pts + pts[:1]).hausdorff_distance(circle.exterior) < 0.02


def test_two_corners_closer_than_a_needle_hole_are_one():
    # a 0.2 mm chamfer on one corner of a square: two 45 degree turns, not corners,
    # and a 90 degree notch 0.3 mm wide: its two inner corners are 0.3 mm apart
    notch = Polygon([(0, 0), (10, 0), (10, 10), (5.15, 10), (5.15, 9), (4.85, 9), (4.85, 10), (0, 10)])
    ring = [(float(x), float(y)) for x, y in notch.exterior.coords][:-1]
    kept = [ring[i] for i in keyline_bean.corners(ring)]
    assert ((5.15, 9.0) in kept) != ((4.85, 9.0) in kept)
    pts = keyline_bean.stations(ring + ring[:1])
    assert min(_steps(pts + pts[:1])) >= 0.29


# --- the line: one keyline ----------------------------------------------------

def test_the_centreline_is_the_bodys_edge_moved_out_half_the_keyline():
    loops = keyline_bean.centrelines(_ring(0.4))
    assert len(loops) == 1
    assert keyline_bean.keyline_width_mm(_ring(0.4)) == pytest.approx(0.4, abs=0.01)
    xs = sorted({round(x, 3) for x, _y in loops[0]})
    assert xs[0] == pytest.approx(-15.2, abs=0.005) and xs[-1] == pytest.approx(15.2, abs=0.005)
    # mitred: the face's sharp corner is a sharp corner of the line
    assert any(math.dist(p, (15.2, 6.2)) < 0.01 for p in loops[0])


def test_the_bean_closes_on_its_first_hole_and_reuses_every_hole():
    runs, report = keyline_bean.keyline_bean_runs(_ring(0.4), "Souter", entry=None, trim_at_mm=7.0)
    assert not report["empty"] and report["loops"] == 1 and report["corners"] == 4
    (run,) = runs
    assert run.kind == stitches.RUN
    pts = [tuple(p) for p in run.points]
    assert pts[0] == pts[-1]
    holes = set(pts)
    assert len(pts) == machine.BEAN_PASSES * len(holes) + 1     # three passes, same holes
    line = LineString(keyline_bean.centrelines(_ring(0.4))[0])
    assert max(line.distance(Point(p)) for p in holes) < 1e-9   # every hole on the centreline
    assert max(_steps(pts)) <= 1.5 * PITCH


def test_a_band_two_bodies_share_is_sewn_once():
    """Two faces 0.4 mm apart inside one keyline: the strip between them is
    on both centrelines. The second loop sews only its own arc, and that arc
    starts and ends in holes the first loop made."""
    a, b = box(-10, -3, 0, 3), box(0.4, -3, 10.4, 3)
    band = unary_union([a, b]).buffer(0.4, join_style=2).difference(unary_union([a, b]))
    runs, report = keyline_bean.keyline_bean_runs(band, "Souter", entry=None, trim_at_mm=7.0)
    assert report["loops"] == 1 and report["arcs"] == 1
    first, arc = ([tuple(p) for p in r.points] for r in runs)
    assert first[0] == first[-1] and arc[0] != arc[-1]
    assert arc[0] in set(first) and arc[-1] in set(first)
    strip = box(0.0, -3.0, 0.4, 3.0)
    inner = [p for p in set(arc) - {arc[0], arc[-1]}]
    assert inner and not any(strip.buffer(0.01).contains(Point(p)) for p in inner)


def test_a_keyline_with_a_tail_no_loop_follows_is_handed_back():
    tail = LineString([(15.4, 0), (40, 0)]).buffer(0.2, cap_style=2)
    runs, report = keyline_bean.keyline_bean_runs(unary_union([_ring(0.4), tail]), "Souter",
                                                  entry=None, trim_at_mm=7.0)
    assert runs == [] and report["empty"]


# --- sew order and the fill under the line ----------------------------------

def test_keylines_sew_last():
    regs = [_region("Sword", FACE, 0, 0), _region("Skey", _ring(0.4), 1, 1),
            _region("Sparen", box(20, -6, 24, 6), 0, 2)]
    out = keyline_bean.sew_last(regs, {"Skey"})
    assert [r.shape_id for r in out] == ["Sword", "Sparen", "Skey"]
    assert [r.meta["layer"] for r in out] == [0, 1, 2]
    assert regs[1].meta["layer"] == 1                            # copies, not edits
    assert keyline_bean.sew_last(regs, set()) is regs


def test_no_fill_passes_its_keyline():
    body = _region("Sbody", FACE, 0, 0)
    key = _region("Skey", _ring(0.4), 1, 1)
    grown = FACE.buffer(0.5, join_style=2)                       # stage 5: underlap + pull
    planned = [PlannedRegion(region=body, polygon=grown, sew_index=0),
               PlannedRegion(region=key, polygon=key.polygon, sew_index=1)]
    assert keyline_bean.hold_bodies(planned, {"Skey"}) == 1
    limit = FACE.buffer(0.2, join_style=2)
    assert planned[0].polygon.equals(limit)                      # what growth fits under the line is kept
    assert planned[1].polygon is key.polygon


def test_a_body_of_the_keylines_own_thread_goes_with_it():
    """A white counter inside a white keyline, left in its own layer, loaded
    the white twice (the logo at 40 and 127 mm: 4 colour stops, 3 threads)."""
    counter = box(-2, -1, 2, 1)
    regs = [_region("Sword", FACE.difference(counter.buffer(0.4, join_style=2)), 0, 0),
            _region("Scounter", counter, 1, 1),
            _region("Sother", box(20, -6, 24, 6), 2, 2),
            _region("Skey", _ring(0.4, counter), 1, 3)]
    out = keyline_bean.sew_last(regs, {"Skey"})
    assert [r.shape_id for r in out] == ["Sword", "Sother", "Scounter", "Skey"]
    assert [r.meta["layer"] for r in out] == [0, 1, 2, 3]


def test_the_hold_keeps_one_polygon_by_bridging_only_the_neck():
    """Body and hole are vectorized apart: at a thin neck the two can miss
    each other and the cut comes back in two. The pieces are joined between
    themselves and nowhere else: the overshoot all round the body goes."""
    lobes = [box(0, 0, 4, 4), box(4.3, 0, 8.3, 4)]                 # two letters, 0.3 mm apart
    body = unary_union([*lobes, box(4, 1.9, 4.3, 2.1)]).buffer(0.3, join_style=2)
    limit = unary_union(lobes)                                     # the hole's neck missed the body's
    assert limit.geom_type == "MultiPolygon"
    assert body.intersection(limit).geom_type == "MultiPolygon"
    got = keyline_bean.held(body, limit)
    assert got.geom_type == "Polygon" and got.area < body.area
    over = got.difference(limit)
    assert box(3.99, -0.31, 4.31, 4.31).contains(over)             # only the strip between them
    assert keyline_bean.held(body, None) is body


def test_one_threads_keylines_go_together():
    """Rings either side of the gate are one drawn line: a bean, all of them,
    when the thread's outlines pooled are a hairline; none when they are not."""
    cfg = PipelineConfig()
    a, b = box(-15, -6, 15, 6), box(20, -6, 50, 6)

    def ids(wa, wb):
        regs = [_region("Sa", a, 0, 0), _region("Sb", b, 0, 0),
                _region("Ska", _ring(wa, a), 1, 1), _region("Skb", _ring(wb, b), 1, 1)]
        return keyline_bean.keyline_regions(regs, {"Ska", "Skb"}, cfg)

    assert ids(0.40, 0.40) == {"Ska", "Skb"}
    assert ids(0.40, 0.70) == {"Ska", "Skb"}        # 0.70 alone is over the gate; pooled 0.55 is under
    assert ids(0.75, 0.85) == set()
    assert ids(0.40, 2.00) == set()                 # one thick outline: not a hairline thread


def test_a_frame_in_the_logos_own_ink_is_not_a_keyline():
    """To-a-T Machine: a thin black frame and black lettering. The frame is a
    drawn part of the logo, which the pro borders in satin; as a bean it went
    to a wire, and the O of its lettering to a hollow outline."""
    cfg = PipelineConfig()
    letter = box(-8, -3, -4, 3)                                    # the same thread's lettering
    regs = [_region("Sfield", FACE.difference(letter), 0, 0),
            _region("Sletter", letter, 1, 1),
            _region("Sframe", _ring(0.4), 1, 1)]
    assert keyline_bean.keyline_regions(regs, {"Sframe"}, cfg) == set()
    # the same frame in a thread of its own is a keyline
    regs[1] = _region("Sletter", letter, 2, 1)
    assert keyline_bean.keyline_regions(regs, {"Sframe"}, cfg) == {"Sframe"}


# --- through stage 7 ----------------------------------------------------------

def test_off_a_hairline_keyline_sews_a_satin_loop():
    """Today's defect, pinned: a 0.4 mm keyline goes down as satin."""
    runs, _ = _plan(0.4)
    assert stitches.SATIN in _kinds(runs, "Souter")


def test_on_a_hairline_keyline_sews_a_bean_and_no_satin():
    runs, _ = _plan(0.4, **{FLAG: True})
    assert _kinds(runs, "Souter") == {stitches.RUN}
    (run,) = [r for r in runs if r.shape_id == "Souter" and r.kind == stitches.RUN]
    holes = {tuple(p) for p in run.points}
    for corner in [(-15.2, -6.2), (15.2, -6.2), (15.2, 6.2), (-15.2, 6.2)]:
        assert min(math.dist(corner, h) for h in holes) < 0.01


def test_on_the_body_still_sews_as_a_plain_fill():
    """The outline's body is not a satin and gets no border of its own."""
    off, _ = _plan(0.4)
    on, _ = _plan(0.4, **{FLAG: True})
    assert stitches.SATIN not in _kinds(on, "Sbody")
    assert _md5([r for r in on if r.shape_id == "Sbody"]) == \
        _md5([r for r in off if r.shape_id == "Sbody"])


@pytest.mark.parametrize("width_mm", [0.8, 1.0, 2.0])
def test_on_a_wider_outline_is_byte_identical(width_mm):
    """To-a-T's 0.8 mm frame, a 1 mm ring and Becker's 2 mm keyline keep the
    pro's loop."""
    off, _ = _plan(width_mm)
    on, _ = _plan(width_mm, **{FLAG: True})
    assert stitches.SATIN in _kinds(off, "Souter")
    assert _md5(on) == _md5(off)


def test_on_a_tier_the_user_set_is_left_alone():
    off, _ = _plan(0.4, outline_meta={"tier": "fill"})
    on, _ = _plan(0.4, outline_meta={"tier": "fill"}, **{FLAG: True})
    assert _md5(on) == _md5(off)


def test_on_without_border_from_outline_does_nothing():
    off, _ = _plan(0.4, border_from_outline=False)
    on, _ = _plan(0.4, border_from_outline=False, **{FLAG: True})
    assert _md5(on) == _md5(off)


def test_on_the_keyline_round_a_dot_sews_the_same_bean():
    """A dot's keyline is too short a loop to be an outline
    (`machine.BORDER_MIN_LOOP_MM`); beside a bean line it must not be a satin."""
    dot = box(20, -0.75, 21.5, 0.75)
    assert dot.exterior.length < machine.BORDER_MIN_LOOP_MM
    extra = (_region("Sdot", dot, 0, 0), _region("Sdotkey", _ring(0.4, dot), 1, 1))
    on, _ = _plan(0.4, extra=extra, **{FLAG: True})
    assert _kinds(on, "Sdotkey") == {stitches.RUN}
    (run,) = [r for r in on if r.shape_id == "Sdotkey" and r.kind == stitches.RUN]
    assert tuple(run.points[0]) == tuple(run.points[-1])


# --- through the whole pipeline -----------------------------------------------

def _logo_png() -> bytes:
    """A red slab with a 4 px white keyline on a putty page: Kent's keyline
    logo in one shape. At 80 mm wide the keyline is about 0.36 mm."""
    img = np.full((300, 900, 3), (223, 231, 234), np.uint8)       # BGR
    slab = np.array([[190, 60], [760, 60], [710, 240], [140, 240]], np.int32)
    cv2.fillPoly(img, [slab], (255, 255, 255))
    inner = Polygon(slab.tolist()).buffer(-4, join_style=2)
    cv2.fillPoly(img, [np.array(inner.exterior.coords, np.int32)], (53, 33, 153))
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def _white_runs(plan, result):
    white = {r.shape_id for r in result.regions
             if min(plan.blocks[[b.thread_index for b in plan.blocks].index(r.thread_index)].rgb) > 240}
    return white, [r for b in plan.blocks for r in b.runs if r.shape_id in white]


def test_end_to_end_the_keyline_is_a_bean_sewn_last_with_the_fill_behind_it():
    art = _logo_png()
    off_result, off_plan = digitize(art, PipelineConfig(target_width_mm=80.0))
    _white, off_runs = _white_runs(off_plan, off_result)
    assert any(r.kind == stitches.SATIN for r in off_runs), "the fixture must show the defect"

    result, plan = digitize(art, PipelineConfig(target_width_mm=80.0, **{FLAG: True}))
    white, runs = _white_runs(plan, result)
    assert white and {r.kind for r in runs} - {stitches.TRAVEL} == {stitches.RUN}
    # sewn last: nothing of another shape after the first keyline stitch
    order = [r.shape_id in white for b in plan.blocks for r in b.runs if r.kind != stitches.TRAVEL]
    assert order.index(True) == len(order) - sum(order)
    # the fill never passes the bean's own needle line
    loops = [Polygon(c) for sid in white
             for c in keyline_bean.centrelines(next(r.polygon for r in result.regions if r.shape_id == sid))]
    inside = unary_union(loops)
    # (this fixture's page also sews, either side of the slab: not a body)
    bodies = {r.shape_id for r in result.regions
              if r.shape_id not in white and inside.contains(r.polygon.representative_point())}
    assert bodies
    fills = [Point(p) for b in plan.blocks for r in b.runs
             if r.shape_id in bodies and r.kind == stitches.FILL for p in r.points]
    assert fills and max(inside.distance(p) for p in fills) < 1e-6
