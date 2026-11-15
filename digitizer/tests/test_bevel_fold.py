"""`cfg.bevel_ring_fold` (built OFF 2026-11-13): shading the pro flattens sews as the shape it shades.

Kent on Golden Tee: "The bean stitching makes 'golf' look to bust" (20 pins);
the pro sews GOLF as one flat gold where we traced a gold ramp in two
threads, a dark bevel, a red keyline and a grey drop shadow. Drone pin 3: the
frame ring "changes colour too much". These fixtures are those layers drawn
by hand, plus what must survive: a keyline all round, a line drawn across a
shape, the edge of a white shape on a white page.
"""
from __future__ import annotations

from types import SimpleNamespace

from shapely.geometry import Point, Polygon, box

from digitizer_core import bevel_fold as bf
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.threads import CHART

CFG = PipelineConfig()
WHITE_PAGE = SimpleNamespace(input_px_per_mm=20.0, px_per_mm=20.0, bg_rgb=(255, 255, 255),
                             bg_from_alpha=False)


def _t(rgb):
    """The chart thread nearest `rgb`."""
    import numpy as np
    return CHART.nearest_index(bf._lab(rgb))


GOLD, GOLD_LIGHT = _t((255, 170, 51)), _t((255, 204, 0))
BLACK, RED, GREY, WHITE = _t((0, 0, 0)), _t((155, 48, 28)), _t((204, 204, 185)), _t((255, 255, 255))
SILVER = _t((204, 204, 204))


def _r(poly, thread, sid, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=poly.area, meta=dict(meta))


def _letter():
    """A bar letter 10 x 4 mm at the origin, its top half the light gold."""
    return box(0, 0, 10, 2), box(0, 2, 10, 4)


def test_fixture_threads_are_distinct():
    assert len({GOLD, GOLD_LIGHT, BLACK, RED, GREY, WHITE}) == 6


def test_a_ramp_split_in_two_becomes_one_thread_and_one_shape():
    lo, hi = _letter()
    regions = [_r(hi, GOLD_LIGHT, "HI"), _r(lo, GOLD, "LO")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["tones"] and len(regions) == 1
    assert regions[0].polygon.equals_exact(box(0, 0, 10, 4).normalize(), 0.05) or \
        abs(regions[0].polygon.area - 40.0) < 0.2


def test_a_bevel_band_along_one_side_folds_into_the_letter():
    """The red keyline folds. A black band in its own ink, the design's
    darkest, is DRAWN (2026-11-14, the pro's Golden Tee: he sews the tee's
    black shadow): it stays."""
    lo, hi = _letter()
    bevel = box(0, -0.5, 10, 0)                      # 0.5 mm dark band under the letter
    keyline = box(10, 0, 10.3, 4)                    # 0.3 mm red band up its right side
    regions = [_r(lo.union(hi), GOLD, "L"), _r(bevel, BLACK, "BEV"), _r(keyline, RED, "KEY")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert {b["shape_id"] for b in rep["bands"]} == {"KEY"}
    assert sorted(r.shape_id for r in regions) == ["BEV", "L"]
    letter = next(r for r in regions if r.shape_id == "L")
    assert letter.thread_index == GOLD and abs(letter.polygon.area - (40.0 + 1.2)) < 0.3


def test_shading_in_an_ink_without_a_spool_goes_to_the_page():
    """GOLF's dark teal extrusion: the colour cap sewed it in black
    (`color_cap_merged_from`); the pro leaves it out, the garment shows."""
    lo, hi = _letter()
    bevel = box(0, -0.5, 10, 0)
    regions = [_r(lo.union(hi), GOLD, "L"), _r(bevel, BLACK, "BEV", color_cap_merged_from="3344")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert [c["shape_id"] for c in rep["cap_shading"]] == ["BEV"]
    assert [r.shape_id for r in regions] == ["L"] and abs(regions[0].polygon.area - 40.0) < 0.01


def test_substituted_shading_inset_in_art_is_kept():
    """Precision Drone: cap-merged grey slivers inset in the black badge face
    no page; dropped they would open a garment-coloured hole, so they stay."""
    badge = box(0, 0, 20, 10)
    inset = box(5, 5, 15, 5.4)
    regions = [_r(badge.difference(inset), GOLD, "B"), _r(inset, GREY, "IN", color_cap_merged_from="0108")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["cap_shading"] == []


def test_a_bevel_ring_between_a_white_face_and_its_outline_is_one_band():
    """GT: white face, then a gold bevel, a cream highlight and a red keyline,
    then the black outline. The pro sews the ring as ONE band in the gold
    that sews the design's letters; the face stays white, the outline black."""
    face = box(0, 0, 10, 6)
    gold_b = box(-0.6, 0, 0, 6)                      # left side: gold extrusion
    cream = box(0, 6, 10, 6.5)                       # top: cream highlight
    red = box(10, 0, 10.4, 6)                        # right: red keyline
    outline = box(-1.1, -0.5, 10.9, 7.0).difference(box(-0.6, 0, 10.4, 6.5))
    letter = box(20, 0, 30, 4)                       # a gold letter elsewhere (GOLF)
    regions = [_r(face, WHITE, "F", enclosed_background=True), _r(gold_b, GOLD, "GB"),
               _r(cream, GREY, "CR"), _r(red, RED, "RED"), _r(outline, BLACK, "OUT"),
               _r(letter, GOLD, "GOLF")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["rings"] and rep["rings"][0]["ink"] == CHART[GOLD].number
    threads = {r.shape_id: r.thread_index for r in regions}
    assert threads["F"] == WHITE and threads["OUT"] == BLACK and threads["GOLF"] == GOLD
    ring = [r for r in regions if r.meta.get(bf.RING_KEY)]
    assert ring and all(r.thread_index == GOLD for r in ring)
    assert abs(sum(r.polygon.area for r in ring) - (3.6 + 5.0 + 2.4)) < 0.2


def test_a_ramp_sews_its_deeper_end_and_a_patch_its_body():
    """The pro's Golden Tee gold (Madeira 1172, his worksheet) is the art's
    ORANGE end (1.5 dE00), not the larger yellow half. Two tones each a
    substantial share of the merged shape are a ramp: the deeper one sews.
    A small patch on a large body (the crest's navy, 4%) is shading: the
    body's tone stays."""
    top, bottom = box(0, 0, 10, 2.2), box(0, 2.2, 10, 4)       # yellow 55%, orange 45%
    regions = [_r(top, GOLD_LIGHT, "Y"), _r(bottom, GOLD, "O")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["tones"][0]["ramp"] and {r.thread_index for r in regions} == {GOLD}
    body, patch = box(0, 0, 10, 9.6), box(0, 9.6, 10, 10)       # orange body, 4% yellow edge patch
    regions = [_r(body, GOLD, "B"), _r(patch, GOLD_LIGHT, "P")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert not rep["tones"][0]["ramp"] and {r.thread_index for r in regions} == {GOLD}
    regions = [_r(body, GOLD_LIGHT, "B"), _r(patch, GOLD, "P")]  # the deeper tone as the patch
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert not rep["tones"][0]["ramp"] and {r.thread_index for r in regions} == {GOLD_LIGHT}


def _gt_with_golf():
    """A white face, a gold bevel band on its left, the black outline round
    both, and a gold letter (GOLF) below with a red keyline along it that
    touches the bevel."""
    face = box(0, 0, 10, 6)
    bevel = box(-0.6, 0, 0, 6)
    outline = box(-1.1, -0.5, 10.5, 6.5).difference(box(-0.6, 0, 10, 6))
    golf = box(-3, 7.0, 4, 11)
    key = box(-3, 6.6, 4, 7.0)                                   # 0.4 mm red along GOLF's top
    return face, bevel, outline, golf, key


def test_the_ring_stops_at_a_coloured_letter():
    """His GT ring stops at the GT's outline; GOLF's own keyline is GOLF's
    (the band fold gives it to the gold letter), not a piece of the ring."""
    face, bevel, outline, golf, key = _gt_with_golf()
    regions = [_r(face, WHITE, "F", enclosed_background=True), _r(bevel, GOLD, "BEV"),
               _r(outline, BLACK, "OUT"), _r(golf, GOLD, "GOLF"), _r(key, RED, "KEY")]
    bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert not any(r.meta.get(bf.RING_KEY) == "F" and r.shape_id == "KEY" for r in regions)
    assert "KEY" not in {r.shape_id for r in regions}            # folded into GOLF


def test_a_ring_band_out_on_the_page_joins_the_outline_where_it_runs_along_it():
    """GT's G keyline runs down past the outline onto the page between
    GOLF's O and L: he sews the outline's black where it runs along the
    outline, garment beyond it."""
    face = box(0, 0, 10, 6)
    bevel = box(10, 0, 10.5, 6)                                  # gold bevel up the right side
    # the outline round it all, open where the keyline runs out past its bottom
    outline = (box(-0.5, -0.5, 11.4, 6.5).difference(box(0, 0, 10.9, 6))
               .difference(box(10.5, 6, 10.9, 6.5)))
    # a 0.4 mm keyline between the bevel and the outline, running 5.5 mm on past it
    key = box(10.5, 1.0, 10.9, 12.0)
    letter = box(20, 0, 30, 4)                                   # a gold body elsewhere
    regions = [_r(face, WHITE, "F", enclosed_background=True), _r(bevel, GOLD, "BEV"),
               _r(outline, BLACK, "OUT"), _r(key, RED, "KEY"), _r(letter, GOLD, "L")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    edges = [x for x in rep["rings"] if "outline_edge" in x]
    assert [e["outline_edge"] for e in edges] == ["KEY"] and edges[0]["ink"] == CHART[BLACK].number
    assert RED not in {r.thread_index for r in regions}
    black = [r for r in regions if r.thread_index == BLACK]
    assert black and max(r.polygon.bounds[3] for r in black) < 12.0 - 2.0   # clipped short of the far end


def test_a_ring_with_no_body_ink_is_left_alone():
    """Only a red keyline between the face and the outline, and no red body
    anywhere: nothing says which thread the ring would be, so the ring rule
    stays out (the band fold then treats the keyline as it always did: a
    keyline stacked on the outline it is dwarfed by)."""
    face = box(0, 0, 10, 6)
    red = box(10, 0, 10.4, 6)
    outline = box(-0.5, -0.5, 10.9, 6.5).difference(box(0, 0, 10.4, 6))
    regions = [_r(face, WHITE, "F", enclosed_background=True), _r(red, RED, "RED"),
               _r(outline, BLACK, "OUT")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["rings"] == []
    assert not any(r.meta.get(bf.RING_KEY) for r in regions)


def test_a_shade_in_a_counter_goes_to_the_page():
    """GOLF's O: the drop shadow seen through the counter is a light grey
    lying against the counter's dark wall and its white; the pro's counter
    is open (garment)."""
    o = Point(0, 0).buffer(5, 64)
    hole = Point(0, 0).buffer(2.5, 64)
    wall = hole.difference(Point(0, 0).buffer(2.0, 64))
    shade = Point(0, 0).buffer(2.0, 64).intersection(box(-3, -3, 3, 0))
    white = Point(0, 0).buffer(2.0, 64).difference(shade)
    regions = [_r(o.difference(hole), GOLD, "O"), _r(wall, BLACK, "WALL"),
               _r(shade, GREY, "SH"), _r(white, WHITE, "C", enclosed_background=True)]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert [c["shape_id"] for c in rep["counter_shades"]] == ["SH"]
    assert "SH" not in {r.shape_id for r in regions}


def test_a_light_window_in_a_body_is_not_a_counter_shade():
    """A grey window drawn in a gold shape touches the body itself: art."""
    body = box(0, 0, 10, 6)
    win = box(4, 2, 6, 4)
    regions = [_r(body.difference(win), GOLD, "B"), _r(win, GREY, "W")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["counter_shades"] == [] and len(regions) == 2


def test_a_cream_highlight_on_a_coloured_letter_folds():
    """GOLF's cream bevel slivers (14.3 dE00 from the white page) are a
    highlight ON the gold, not the page showing through: they fold."""
    letter = box(0, 0, 10, 4.3)
    hl = box(1, 3.6, 9, 3.9)                          # 0.3 mm cream sliver just inside the top edge
    regions = [_r(letter.difference(hl), GOLD, "L"), _r(hl, GREY, "HL")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert [b["shape_id"] for b in rep["bands"]] == ["HL"]
    assert [r.shape_id for r in regions] == ["L"]


def test_a_drop_shadow_on_the_page_goes_to_the_page():
    lo, hi = _letter()
    shadow = Polygon([(0.8, -1.2), (10.8, -1.2), (10.8, 3.2), (10, 3.2), (10, 0), (0.8, 0)])  # under + right
    regions = [_r(lo.union(hi), GOLD, "L"), _r(shadow, GREY, "SH")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert [s["shape_id"] for s in rep["shadows"]] == ["SH"]
    assert [r.shape_id for r in regions] == ["L"]


def test_a_keyline_all_round_is_kept():
    """Becker's and MFab's keylines: a band wrapping its letter is a border."""
    lo, hi = _letter()
    letter = lo.union(hi)
    keyline = letter.buffer(0.4, join_style=2).difference(letter)
    regions = [_r(letter, GOLD, "L"), _r(keyline, BLACK, "K")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["bands"] == [] and len(regions) == 2


def test_a_line_across_a_shape_stays_but_a_ring_arc_folds():
    """Drone: silver arcs just inside the black ring's edge fold; the
    crosshair across the middle stays."""
    disc = Point(0, 0).buffer(20, 128)
    arc = Point(0, 0).buffer(19.6, 128).difference(Point(0, 0).buffer(19.0, 128)) \
        .intersection(box(-30, 5, 30, 30))                  # 0.6 mm silver bevel arc near the edge
    cross = box(-19.7, -0.25, 19.7, 0.25)                   # a 0.5 mm line through the centre,
    #                                                         reaching the edge at both ends
    black = disc.difference(arc).difference(cross)
    regions = [_r(black, BLACK, "RING"), _r(arc, SILVER, "ARC"), _r(cross, SILVER, "X")]
    # Drone's art floods no page colour: the garment (the Studio's cream) stands in
    no_page = SimpleNamespace(input_px_per_mm=12.0, px_per_mm=12.0, bg_rgb=None, bg_from_alpha=False)
    rep = bf.apply_bevel_fold(regions, no_page, PipelineConfig(garment_rgb=(235, 232, 223)), CHART)
    assert {b["shape_id"] for b in rep["bands"]} == {"ARC"}
    assert {r.shape_id for r in regions} == {"RING", "X"}


def test_the_edge_of_a_white_shape_on_a_white_page_is_kept():
    """Golden Tee's ball arc: white with a black band on one side. On a white
    page the band is what shows the shape; the pro keeps it."""
    white = box(0, 0, 20, 3)
    band = box(0, -0.6, 20, 0)
    regions = [_r(white, WHITE, "W"), _r(band, BLACK, "B")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["bands"] == [] and rep["shadows"] == [] and len(regions) == 2


def test_distinct_colours_and_wide_shapes_are_left_alone():
    """Two flat colours side by side (no ramp) and a wide second colour
    beside a letter: nothing folds."""
    a = box(0, 0, 10, 4)
    b = box(10, 0, 20, 4)
    regions = [_r(a, GOLD, "A"), _r(b, BLACK, "B")]
    before = [(r.shape_id, r.thread_index, r.polygon.wkb) for r in regions]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep == {**rep, "shadows": [], "tones": [], "bands": []}
    assert [(r.shape_id, r.thread_index, r.polygon.wkb) for r in regions] == before


def test_a_line_splitting_a_shape_in_two_stays():
    """Drone's crosshair runs edge to edge: it is not a hole in the black but
    a line between two black halves."""
    left, right = box(-10, -10, -0.25, 10), box(0.25, -10, 10, 10)
    line = box(-0.25, -10, 0.25, 10)
    regions = [_r(left, BLACK, "L"), _r(right, BLACK, "R"), _r(line, SILVER, "LINE")]
    no_page = SimpleNamespace(input_px_per_mm=12.0, px_per_mm=12.0, bg_rgb=None, bg_from_alpha=False)
    rep = bf.apply_bevel_fold(regions, no_page, PipelineConfig(garment_rgb=(235, 232, 223)), CHART)
    assert rep["bands"] == [] and len(regions) == 3


def test_the_dark_wall_of_a_counter_stays():
    """A dark inner wall in the design's darkest ink, its own art ink, is
    drawn and stays (2026-11-14). GOLF's O wall was teal the cap sewed black:
    that one goes to the page (`test_shading_in_an_ink_without_a_spool...`)."""
    o = Point(0, 0).buffer(5, 64)
    counter = Point(0, 0).buffer(2.0, 64)
    wall = Point(0, 0).buffer(2.5, 64).difference(counter)          # 0.5 mm dark ring
    letter = o.difference(Point(0, 0).buffer(2.5, 64))
    regions = [_r(letter, GOLD, "O"), _r(wall, BLACK, "WALL"), _r(counter, WHITE, "C", counter=True)]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["bands"] == []
    assert {r.shape_id for r in regions} == {"O", "WALL", "C"}


def test_the_page_showing_through_is_never_folded():
    """To a T: white slivers between black brush strokes are the page."""
    stroke = box(0, 0, 10, 4).difference(box(3, 1.8, 7, 2.0))
    gap = box(3, 1.8, 7, 2.0)
    regions = [_r(stroke, BLACK, "S"), _r(gap, WHITE, "GAP", rescued_small_shape=True)]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["bands"] == [] and len(regions) == 2


def test_a_detail_kept_inside_a_shape_is_never_folded():
    """Hotel Fremont: no page colour of its own; the white insides of its small
    tan letters are rescued details lying inside the letter -- counters."""
    letter = box(0, 0, 3, 4)
    inner = box(1.2, 1.0, 1.5, 3.0)
    regions = [_r(letter.difference(inner), GOLD, "L"), _r(inner, WHITE, "IN", rescued_small_shape=True)]
    no_page = SimpleNamespace(input_px_per_mm=12.0, px_per_mm=12.0, bg_rgb=None, bg_from_alpha=False)
    rep = bf.apply_bevel_fold(regions, no_page, PipelineConfig(garment_rgb=(235, 232, 223)), CHART)
    assert rep["bands"] == [] and len(regions) == 2


def test_an_anti_alias_fringe_is_not_a_shadow():
    """ProSeal: a light sliver narrower than two source pixels on the page
    is the JPEG's fringe, not a drop shadow."""
    lo, hi = _letter()
    fringe = box(0, -0.06, 10, 0)                    # 0.06 mm < 2 px at 20 px/mm
    regions = [_r(lo.union(hi), BLACK, "L"), _r(fringe, GREY, "F")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["shadows"] == []


def test_counters_and_dark_ink_are_never_folded():
    lo, hi = _letter()
    regions = [_r(lo.union(hi), GOLD, "L"), _r(box(0, -0.5, 10, 0), BLACK, "INK", dark_ink=True)]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert rep["bands"] == [] and len(regions) == 2


def test_flag_is_off_by_default():
    assert PipelineConfig().bevel_ring_fold is False
