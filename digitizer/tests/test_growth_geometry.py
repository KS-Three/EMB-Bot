"""Stage 5's growth GEOMETRY, two flags built OFF 2026-11-13 in `cfg.extra`
(the Director's fat-ink brief; ledger `tools/width_ledger.py`).

- `pull_comp_along_stitch_only`: a fill grows only along its stitch axis,
  square at its convex corners, not a round `buffer(pull)` every way.
- `growth_keeps_gaps`: growth keeps out of the bare fabric the art keeps
  between shapes (at least `GAP_SEWABLE_MM` apart, or apart at all on one
  thread) and inside its counters of that width.

The pull itself (`Fabric.pull_comp_mm`) is gate 1 and untouched: every test
reads WHERE growth goes, never how much. Absent keys are the engine as it was.
"""
from __future__ import annotations

import hashlib

from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import GAP_SEWABLE_MM, resolve_overlaps

PIQUE = get_fabric("pique_knit")          # 0.30 mm pull
PULL = PIQUE.pull_comp_mm


def _r(poly, sid, thread=0, layer=0, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(1000 + thread),
                  area_mm2=float(poly.area), meta={"layer": layer, **meta})


def _plan(regions, **extra):
    c = PipelineConfig(overlap_mm=0.25, extra=dict(extra))
    planned, _w = resolve_overlaps(regions, PIQUE, c)
    return {p.region.shape_id: p.polygon for p in planned}


def _md5(planned) -> str:
    h = hashlib.md5()
    for sid in sorted(planned):
        h.update(sid.encode())
        h.update(planned[sid].wkb)
    return h.hexdigest()


def _fill(poly, sid="F", angle=0.0, **kw):
    # a fill told its angle (the review's per-shape key): rows along x
    return _r(poly, sid, fill_angle_deg=angle, tier="fill", **kw)


def test_absent_and_false_keys_are_the_engine_as_it_was():
    def scene():
        return [_fill(box(0, 0, 12, 8), "A"), _fill(box(13, 0, 20, 8), "B", layer=1),
                _fill(box(0, 9, 20, 15).difference(box(5, 11, 6, 13)), "C", thread=1, layer=2)]
    base = _md5(_plan(scene()))
    assert _md5(_plan(scene(), pull_comp_along_stitch_only=False, growth_keeps_gaps=False)) == base


def test_a_fill_grows_along_its_rows_only_and_keeps_square_corners():
    art = box(0, 0, 12, 8)
    off = _plan([_fill(art)])["F"]
    on = _plan([_fill(art)], pull_comp_along_stitch_only=True)["F"]
    # OFF: every way, round corners -- the area of a rounded rectangle
    x0, y0, x1, y1 = off.bounds
    assert abs((x1 - x0) - (12 + 2 * PULL)) < 0.02 and abs((y1 - y0) - (8 + 2 * PULL)) < 0.02
    assert off.area < (12 + 2 * PULL) * (8 + 2 * PULL) - 0.05, "OFF corners are round"
    # ON: along the rows (x) only, a rectangle -- square corners
    x0, y0, x1, y1 = on.bounds
    assert abs((x1 - x0) - (12 + 2 * PULL)) < 0.02, (x0, x1)
    assert abs((y1 - y0) - 8) < 0.02, (y0, y1)
    assert abs(on.area - (12 + 2 * PULL) * 8) < 0.02, "a rectangle: corners square"


def test_a_turned_fill_grows_along_its_own_axis():
    from shapely import affinity
    art = affinity.rotate(box(-6, -4, 6, 4), 30, origin=(0, 0))
    on = _plan([_fill(art, angle=30.0)], pull_comp_along_stitch_only=True)["F"]
    back = affinity.rotate(on, -30, origin=(0, 0))
    x0, y0, x1, y1 = back.bounds
    assert abs((x1 - x0) - (12 + 2 * PULL)) < 0.03 and abs((y1 - y0) - 8) < 0.03, back.bounds


def test_a_gap_the_art_keeps_is_kept_between_two_colours():
    gap = 1.0
    def scene():
        return [_fill(box(0, 0, 10, 8), "A", thread=0, layer=0),
                _fill(box(10 + gap, 0, 20, 8), "B", thread=1, layer=1)]
    off = _plan(scene())
    on = _plan(scene(), growth_keeps_gaps=True)
    assert off["A"].distance(off["B"]) < gap - 2 * PULL + 0.05, "OFF: both grow into it"
    assert on["A"].distance(on["B"]) >= gap - 1e-6, on["A"].distance(on["B"])
    # the far edges, facing nothing, still take the pull
    assert on["A"].bounds[0] <= -PULL + 0.02 and on["B"].bounds[2] >= 20 + PULL - 0.02


def test_a_seam_between_two_colours_narrower_than_sewable_is_as_before():
    gap = 0.3
    assert gap < GAP_SEWABLE_MM
    def scene():
        return [_fill(box(0, 0, 10, 8), "A", thread=0, layer=0),
                _fill(box(10 + gap, 0, 20, 8), "B", thread=1, layer=1)]
    assert _md5(_plan(scene(), growth_keeps_gaps=True)) == _md5(_plan(scene()))


def test_two_shapes_of_one_thread_in_two_layers_are_never_welded():
    gap = 0.4                       # under 2 x pull: OFF the two grow into one
    def scene():
        return [_fill(box(0, 0, 10, 8), "A", thread=0, layer=0),
                _fill(box(10 + gap, 0, 20, 8), "B", thread=0, layer=1)]
    off = _plan(scene())
    on = _plan(scene(), growth_keeps_gaps=True)
    assert off["A"].distance(off["B"]) < 1e-6, "OFF: welded across the gap"
    assert on["A"].distance(on["B"]) >= gap - 1e-6


def test_a_counter_the_art_keeps_is_held_at_its_size():
    hole = box(5, 2, 6.8, 5)                        # 1.8 x 3.0: inscribed 1.8 mm, shrunk 2.9 mm2 >= the 2.25 floor
    art = box(0, 0, 11, 8).difference(hole)
    off = _plan([_fill(art)])["F"]
    on = _plan([_fill(art)], growth_keeps_gaps=True)["F"]
    def hole_area(p):
        return sum(Polygon(r).area for r in p.interiors)
    assert hole_area(off) < hole.area - 0.3, "OFF: the counter shrinks by the pull"
    assert abs(hole_area(on) - hole.area) < 0.02, hole_area(on)


def _off_angle(regions, sid):
    """The row angle stage 6 picks for `sid` on the shape stage 5 plans
    with neither flag."""
    from digitizer_core.machine import FILL_ROW_MM
    from digitizer_core.stage6_fill import best_fill_angle_deg
    planned, _w = resolve_overlaps(regions, PIQUE, PipelineConfig(overlap_mm=0.25))
    poly = next(p.polygon for p in planned if p.region.shape_id == sid)
    return best_fill_angle_deg(poly, FILL_ROW_MM * max(0.1, PIQUE.density_adjust))


def _same_angle(a, b):
    return abs(((a - b + 90) % 180) - 90) < 1e-6


def test_a_fill_with_no_angle_of_its_own_keeps_the_angle_it_sewed_at():
    """Bridge's round field: grown along its art's principal axis, or along
    a guess of the old shape's pick, its rows turned 12, 12 and 56 degrees
    across three builds. Either flag ON, a fill with no angle of its own is
    handed (and, along its rows, grown along) the angle stage 6 picked for it
    on the shape stage 5 plans with neither flag."""
    from shapely import affinity
    from shapely.geometry import Point
    shapes = {"E": affinity.rotate(box(-10, -3, 10, 3), 20, origin=(0, 0)).difference(box(-2, -1, 3, 1)),
              "D": Point(30, 0).buffer(9.0, 64).difference(box(27, -2, 34, 3))}
    for flags in ({"pull_comp_along_stitch_only": True}, {"growth_keeps_gaps": True},
                  {"pull_comp_along_stitch_only": True, "growth_keeps_gaps": True}):
        def scene():
            return [_r(g, sid, tier="fill") for sid, g in shapes.items()]
        planned, _w = resolve_overlaps(scene(), PIQUE, PipelineConfig(overlap_mm=0.25, extra=dict(flags)))
        for p in planned:
            want = _off_angle(scene(), p.region.shape_id)
            assert p.stitch_angle_deg is not None and _same_angle(p.stitch_angle_deg, want), (flags, p.region.shape_id)


def test_off_hands_stage_7_no_angle_for_a_free_fill():
    planned, _w = resolve_overlaps([_r(box(0, 0, 20, 6), "F", tier="fill")], PIQUE, PipelineConfig(overlap_mm=0.25))
    assert planned[0].stitch_angle_deg is None
