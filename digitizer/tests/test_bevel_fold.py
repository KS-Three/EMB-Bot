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
    lo, hi = _letter()
    bevel = box(0, -0.5, 10, 0)                      # 0.5 mm dark band under the letter
    keyline = box(10, 0, 10.3, 4)                    # 0.3 mm red band up its right side
    regions = [_r(lo.union(hi), GOLD, "L"), _r(bevel, BLACK, "BEV"), _r(keyline, RED, "KEY")]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert {b["shape_id"] for b in rep["bands"]} == {"BEV", "KEY"}
    assert len(regions) == 1 and regions[0].thread_index == GOLD
    assert abs(regions[0].polygon.area - (40.0 + 5.0 + 1.2)) < 0.3


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
    cross = box(-12, -0.25, 12, 0.25)                       # a 0.5 mm line through the centre
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


def test_the_dark_wall_of_a_counter_folds_into_the_letter():
    """GOLF's O: a dark inner bevel lines the counter; the pro sews the O one
    gold with the counter open."""
    o = Point(0, 0).buffer(5, 64)
    counter = Point(0, 0).buffer(2.0, 64)
    wall = Point(0, 0).buffer(2.5, 64).difference(counter)          # 0.5 mm dark ring
    letter = o.difference(Point(0, 0).buffer(2.5, 64))
    regions = [_r(letter, GOLD, "O"), _r(wall, BLACK, "WALL"), _r(counter, WHITE, "C", counter=True)]
    rep = bf.apply_bevel_fold(regions, WHITE_PAGE, CFG, CHART)
    assert [b["shape_id"] for b in rep["bands"]] == ["WALL"]
    assert {r.shape_id for r in regions} == {"O", "C"}


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
