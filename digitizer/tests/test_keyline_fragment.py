"""`cfg.keyline_fragment_drop`: an orphan piece of a hairline keyline goes to the page.

Kent, 2026-11-17, on the Drone render: "The P,R & C should not have the dark
stitch lines on them". Four dark slivers a few mm long sat on the bottom
edges of PRECISION's light letters and each sewed as a short dark satin bar.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, box
from skimage.color import deltaE_ciede2000

from digitizer_core.config import PipelineConfig
from digitizer_core.keyline_fragment import drop_keyline_fragments
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())


def _nearest(lab) -> int:
    return int(np.argmin(deltaE_ciede2000(np.array(CHART.lab), np.array(lab, float)[None, :])))


LIGHT, DARK, MID = _nearest([82, 0, 0]), _nearest([25, 0, 0]), _nearest([55, 0, 0])
BLACK, NEAR_LIGHT = _nearest([0, 0, 0]), _nearest([79.5, 0, 0])


def ink():
    """The design's own darkest ink, far off: the sliver below is not it."""
    return _r("ink", box(30, 0, 36, 10), BLACK)


def _r(sid: str, poly: Polygon, thread: int, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=float(poly.area), meta=dict(meta))


def letter() -> Region:
    return _r("letter", box(0, 0, 6, 10), LIGHT)                    # a 6 x 10 mm light body


def test_a_dark_sliver_on_one_edge_of_a_light_letter_is_dropped():
    regions = [letter(), ink(), _r("sliver", box(1, 10, 4, 10.4), DARK)]   # 3 mm x 0.4 mm under the foot
    assert drop_keyline_fragments(regions, CHART) == ["sliver"]
    assert [r.shape_id for r in regions] == ["letter", "ink"]


def test_a_whole_keyline_stays():
    ring = box(-0.4, -0.4, 6.4, 10.4).difference(box(0, 0, 6, 10))
    outer = Polygon(ring.exterior.coords, [ring.interiors[0].coords])
    regions = [letter(), _r("keyline", outer, DARK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_shadow_along_a_real_share_of_the_outline_stays():
    # right side and bottom: 16 of 32 mm of the letter's outline
    regions = [letter(), _r("s1", box(6, 0, 6.4, 10.4), DARK), _r("s2", box(0, 10, 6, 10.4), DARK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_line_between_two_shapes_stays():
    regions = [letter(), _r("other", box(0, 10.4, 6, 20), MID), _r("rule", box(0, 10, 6, 10.4), DARK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_light_sliver_on_a_dark_shape_is_not_this_rules_business():
    regions = [_r("body", box(0, 0, 6, 10), DARK), _r("glint", box(1, 10, 4, 10.4), LIGHT)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_thick_piece_is_not_a_band():
    regions = [letter(), _r("foot", box(1, 10, 4, 12), DARK)]       # 2 mm deep: a drawn shape
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_sliver_as_big_as_its_host_stays():
    regions = [_r("small", box(0, 0, 3, 1.2), LIGHT), _r("sliver", box(0, 1.2, 3, 1.6), DARK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_counters_and_enclosed_background_are_never_dropped():
    regions = [letter(), _r("c", box(1, 10, 4, 10.4), DARK, counter=True),
               _r("e", box(1, -0.4, 4, 0), DARK, enclosed_background=True)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_the_flag_is_on_by_default():
    assert PipelineConfig().keyline_fragment_drop is True


def test_a_thin_band_in_a_hole_of_its_host_is_drawn_art():
    # To a T's speed lines: dark bands lying INSIDE the white fill
    host = Polygon(box(0, 0, 20, 10).exterior.coords, [box(2, 4.8, 8, 5.2).exterior.coords])
    regions = [_r("fill", host, LIGHT), ink(), _r("speed", box(2, 4.8, 8, 5.2), DARK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_the_designs_darkest_ink_is_drawn_not_a_remnant():
    # Golden Tee's black shadow under the flag tip, on a light body
    regions = [letter(), _r("shadow", box(1, 10, 4, 10.4), BLACK)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_darkest_ink_piece_the_trace_rescued_is_still_a_remnant():
    regions = [letter(), _r("noise", box(1, 10, 4, 10.4), BLACK, rescued_small_shape=True)]
    assert drop_keyline_fragments(regions, CHART) == ["noise"]


def test_a_sliver_barely_darker_than_its_host_is_not_a_keyline():
    regions = [letter(), ink(), _r("sliver", box(1, 10, 4, 10.4), NEAR_LIGHT)]
    assert drop_keyline_fragments(regions, CHART) == []


def test_a_band_wider_than_a_hairline_in_the_art_is_drawn():
    # Golden Tee's black bar under the F's arm: 15 source pixels wide
    thin = lambda: [letter(), ink(), _r("bar", box(1, 10, 4, 10.4), DARK)]
    assert drop_keyline_fragments(thin(), CHART, mm_per_src_px=0.4 / 15) == []          # 15 px
    assert drop_keyline_fragments(thin(), CHART, mm_per_src_px=0.4 / 1.5) == ["bar"]    # 1.5 px
