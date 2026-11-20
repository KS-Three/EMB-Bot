"""Border from the art's outline (built OFF 2026-10-24, ON by Kent's flip the same
day, folded into the engine: the `border_from_outline` switch is retired).

The pro's border choice is not a stroke threshold: he borders a shape when
the ART draws an outline round it (BECKER's white faces in their black
keyline, MFab's M-FAB in its white one) and satins the same stroke when it
does not (MARINE). `tools/outline_census.py` over ten paired files: kappa
0.76 (raw 0.980, n 586). An outline -- a region whose hole holds a body
at least as wide as the outline is thick, a letter's counters excluded --
sews as one satin loop per hole at his width (the art outline's own
thickness, 1.5-2.5), rail on the body's edge; its bodies sew as plain fills,
never satin, and never a ring of their own (`border_by_size` included).
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from tests.conftest import FLIP_2026_10_23  # the OFF md5 predates the 2026-10-23 flips
from tests.conftest import FRAME_GUARD_2026_11_15_OFF  # priced before the frame guard
from tests.conftest import FLAG_ENDS_SEAM_2026_11_17_OFF  # the OFF md5 predates the flag ends/seam trio
from digitizer_core.art_outline import find_art_outlines, outline_width_mm
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

#: a 30 x 12 mm white face (BECKER's E, roughly) in a 2 mm black keyline
FACE = box(-15, -6, 15, 6)
KEY = Polygon(FACE.buffer(2.0, join_style=2).exterior, [FACE.exterior])
#: the same face in a keyline drawn 3.2 mm thick (the art's drop shadow) --
#: past the loop only its mitred corners fill -- and 4 mm, whose strip fills
THICK = Polygon(FACE.buffer(3.2, join_style=2).exterior, [FACE.exterior])
FAT = Polygon(FACE.buffer(4.0, join_style=2).exterior, [FACE.exterior])
#: MARINE's A, roughly: a solid 5 mm stroke ring with a background counter
LETTER = Polygon(box(40, -8, 56, 8).exterior, [box(45, -3, 51, 3).exterior])
COUNTER = box(45, -3, 51, 3)


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _plan(outline, body, *, body_sewn=True, body_meta=None, outline_meta=None, **cfg_kw):
    """The body (white, layer 0) then its outline (black, layer 1)."""
    b = _region("Sbody", body, 0, 0, **(body_meta or {}))
    o = _region("Souter", outline, 1, 1, **(outline_meta or {}))
    planned = [PlannedRegion(region=o, polygon=outline, sew_index=1)]
    if body_sewn:
        planned.insert(0, PlannedRegion(region=b, polygon=body, sew_index=0))
    cfg = PipelineConfig(underlay=False, **{**FLIP_2026_10_23, **FLAG_ENDS_SEAM_2026_11_17_OFF, **cfg_kw})
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg,
                         art_outlines=_art_outlines([b, o], cfg))
    return [r for blk in blocks for r in blk.runs]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _crosses(runs, sid):
    out = []
    for r in runs:
        if r.shape_id == sid and r.kind == stitches.SATIN:
            out += [(a, b) for a, b in zip(r.points, r.points[1:])]
    return out


def test_the_widths_are_the_pros():
    assert machine.OUTLINE_WIDTH_MM == (1.5, 2.5)
    assert machine.OUTLINE_BODY_RATIO == 1.0


def test_a_keyline_round_a_wide_body_is_an_outline():
    b, o = _region("Sbody", FACE, 0, 0), _region("Souter", KEY, 1, 1)
    found = find_art_outlines([b, o])
    assert list(found) == ["Souter"] and [bid for bid, _h in found["Souter"]] == ["Sbody"]
    # one width per outline: the art keyline's own thickness round its body
    # (184 mm2 of keyline over an 84 mm edge, 2.19), clamped to 1.5-2.5
    hole = found["Souter"][0][1]
    assert abs(outline_width_mm(o, [(b, hole)]) - 2.19) < 0.01
    thin = Polygon(FACE.buffer(0.5, join_style=2).exterior, [FACE.exterior])
    assert outline_width_mm(_region("St", thin, 1, 1), [(b, hole)]) == 1.5
    assert outline_width_mm(_region("St", THICK, 1, 1), [(b, hole)]) == 2.5


def test_a_solid_letter_with_a_counter_is_not_an_outline():
    # the counter is the gap inside a letter, not a body
    letter = _region("Sletter", LETTER, 1, 1, text_candidate=True)
    counter = _region("Scounter", COUNTER, 0, 0, enclosed_background=True)
    assert find_art_outlines([letter, counter]) == {}
    # and tagged as one by stage 3, whoever holds it
    plain = _region("Sletter", LETTER, 1, 1)
    tagged = _region("Scounter", COUNTER, 0, 0, enclosed_background=True, counter=True)
    assert find_art_outlines([plain, tagged]) == {}
    # and SEWN: Hotel Fremont's O holds white the field sews -- still the
    # letter's counter (looped, it sewed a spiked sun where he sews the O)
    ring = Polygon(box(40, -4, 48, 4).exterior, [box(41, -3, 47, 3).exterior])
    o_letter = _region("So", ring, 1, 1, text_candidate=True)
    inside = _region("Sinside", box(41, -3, 47, 3), 0, 0)
    assert find_art_outlines([o_letter, inside]) == {}
    assert find_art_outlines([_region("So", ring, 1, 1), inside])     # untagged: an outline


def test_a_ring_with_spokes_is_a_drawing_not_an_outline():
    # Bridge's wheel: the ring round the disc is a fraction of the region
    disc = Polygon(Point(0, 0).buffer(10).exterior)
    wheel = Point(0, 0).buffer(12).difference(disc)
    for a in range(0, 360, 45):
        dx, dy = math.cos(math.radians(a)), math.sin(math.radians(a))
        wheel = wheel.union(LineString([(11 * dx, 11 * dy), (22 * dx, 22 * dy)]).buffer(1.5))
    regions = [_region("Sdisc", disc, 0, 0), _region("Swheel", wheel, 1, 1)]
    assert find_art_outlines(regions) == {}
    ring = Point(0, 0).buffer(12).difference(disc)
    assert find_art_outlines([regions[0], _region("Sring", ring, 1, 1)])     # the ring alone is one


def test_a_field_round_thin_letters_is_not_their_outline():
    # Fremont: thin letters in a wide white ground read stroke / band < 1
    thin = box(-10, -0.6, 10, 0.6)
    ground = Polygon(box(-14, -5, 14, 5).exterior, [thin.exterior])
    assert find_art_outlines([_region("Sground", ground, 0, 0),
                              _region("Sthin", thin, 1, 1)]) == {}


def test_a_counter_inside_the_face_is_not_a_body_of_its_keyline():
    face = Polygon(FACE.exterior, [box(-5, -2, 5, 2).exterior])
    blob = _region("Sblob", box(-5, -2, 5, 2), 1, 1)
    found = find_art_outlines([_region("Sbody", face, 0, 0), _region("Souter", KEY, 1, 1), blob])
    assert [bid for bid, _h in found["Souter"]] == ["Sbody"]


def test_two_touching_bodies_in_one_hole_are_both_bodies():
    # MFab's F and hyphen share one keyline hole
    left, right = box(-15, -6, 0, 6), box(0, -6, 15, 6)
    found = find_art_outlines([_region("Sleft", left, 0, 0), _region("Sright", right, 0, 0),
                               _region("Souter", KEY, 1, 1)])
    assert sorted(bid for bid, _h in found["Souter"]) == ["Sleft", "Sright"]


def test_on_the_outline_is_one_satin_loop_on_the_bodys_edge():
    on = _plan(KEY, FACE)
    loops = [r for r in on if r.shape_id == "Souter" and r.kind == stitches.SATIN]
    assert len(loops) == 1
    assert min(FACE.exterior.distance(Point(p)) for p in loops[0].points[0::2]) < 1e-6
    # one width all round: the keyline's own 2.19 (its corners count), out
    # past the 2 mm sides onto the garment, never into the body
    widths = sorted(math.dist(a, b) for a, b in _crosses(on, "Souter"))
    assert abs(widths[len(widths) // 2] - 2.19) < 0.05
    inner = FACE.buffer(-0.01)
    assert not any(inner.intersects(LineString([a, b])) for a, b in _crosses(on, "Souter"))


def test_on_a_thin_ring_is_widened_to_the_pros_width_but_not_into_a_neighbour():
    # a thin keyline sews at the pro's width; two faces 1 mm apart in one keyline
    left, right = box(-15, -6, -0.5, 6), box(0.5, -6, 15, 6)
    ring = Polygon(box(-16, -7, 16, 7).exterior, [left.exterior, right.exterior])
    b1, b2 = _region("Sleft", left, 0, 0), _region("Sright", right, 0, 0)
    o = _region("Souter", ring, 1, 1)
    cfg = PipelineConfig(underlay=False)
    planned = [PlannedRegion(region=b1, polygon=left, sew_index=0),
               PlannedRegion(region=b2, polygon=right, sew_index=0),
               PlannedRegion(region=o, polygon=ring, sew_index=1)]
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg,
                         art_outlines=_art_outlines([b1, b2, o], cfg))
    runs = [r for blk in blocks for r in blk.runs]
    loops = [r for r in runs if r.shape_id == "Souter" and r.kind == stitches.SATIN]
    assert len(loops) == 2
    faces = unary_union([left, right]).buffer(-0.01)
    crosses = _crosses(runs, "Souter")
    assert not any(faces.intersects(LineString([a, b])) for a, b in crosses)
    assert sorted(math.dist(a, b) for a, b in crosses)[len(crosses) // 2] > 1.0


def test_on_the_body_is_a_fill_with_no_ring_of_its_own():
    on = _plan(KEY, FACE)
    body = [r for r in on if r.shape_id == "Sbody"]
    assert body and {r.kind for r in body} <= {stitches.FILL, stitches.UNDERLAY, stitches.TRAVEL}
    # border_by_size would ring a 12 mm non-lettering fill in its own colour
    both = _plan(KEY, FACE, border_by_size=True)
    assert not [r for r in both if r.shape_id == "Sbody" and r.kind == stitches.BORDER]
    assert _md5([r for r in both if r.shape_id == "Sbody"]) == _md5(body)


def test_on_a_thicker_outline_keeps_the_pros_width_and_fills_the_rest_under():
    # his border is one width all round, 2.5 at most; the art's thicker
    # keyline (BECKER's drop shadow) is filled under the loop, not spanned.
    # Priced before `outline_frame_guard` (ON 2026-11-15): FAT (400 mm2 of
    # keyline round a 360 mm2 face, 1.11) reads as a field under it, so the
    # arm keeps the guard off, as every flip's OFF dict is spread.
    for ring in (THICK, FAT):
        on = _plan(ring, FACE, **FRAME_GUARD_2026_11_15_OFF)
        widths = sorted(math.dist(a, b) for a, b in _crosses(on, "Souter"))
        assert abs(widths[len(widths) // 2] - 2.5) < 0.05
        assert max(widths) < 2.5 * 1.1          # one width (a zigzag diagonal), no fringe
        kinds = [r.kind for r in on if r.shape_id == "Souter" and r.kind != stitches.TRAVEL]
        first_loop = kinds.index(stitches.SATIN)
        assert stitches.FILL in kinds[:first_loop]      # the mitred corners, FAT's strip
        assert stitches.FILL not in kinds[first_loop:]


def test_on_with_the_body_left_unsewn_the_outline_still_loops():
    # BECKER's faces with `sew_enclosed_white` off: the face is a region, unsewn
    on = _plan(KEY, FACE, body_sewn=False)
    assert len([r for r in on if r.shape_id == "Souter" and r.kind == stitches.SATIN]) == 1


def test_on_an_outline_that_does_not_sew_leaves_its_body_alone():
    b = _region("Sbody", FACE, 0, 0)
    o = _region("Souter", KEY, 1, 1)
    cfg_on = PipelineConfig(underlay=False)
    found = _art_outlines([b, o], cfg_on)
    planned = [PlannedRegion(region=b, polygon=FACE, sew_index=0)]
    on, _ = sequence(planned, fabric_for_garment("hat_front"), cfg_on, art_outlines=found)
    alone, _ = sequence(planned, fabric_for_garment("hat_front"), cfg_on, art_outlines=None)
    assert _md5([r for x in on for r in x.runs]) == _md5([r for x in alone for r in x.runs])


def test_on_a_per_shape_tier_still_wins():
    on = _plan(KEY, FACE, outline_meta={"tier": "fill"}, body_meta={"tier": "satin"})
    assert not [r for r in on if r.shape_id == "Souter" and r.kind == stitches.SATIN]
