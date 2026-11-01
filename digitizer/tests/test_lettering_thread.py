"""`cfg.lettering_stray_word_thread` + `cfg.lettering_contrast_floor` (built OFF
2026-11-01): Precision Drone's lettering gap was thread, not construction.

Pinned, load-bearing first: OFF moves nothing; no garment colour moves nothing;
a stated colour is never moved; a stray joins only a near thread on its own
line; the floor prefers a cone already on the design and will not take a far
one just because it is there.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.lettering_thread import apply_lettering_thread, contrast_floor, stray_word_thread
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())
NATURAL = (235, 232, 223)


def spool(l):
    return CHART.nearest_index(np.array([float(l), 0.0, 0.0]))


def region(sid, x, thread, y=0.0, h=4.0, **meta):
    r = Region(polygon=box(x, y, x + 3.0, y + h), thread_index=thread,
               thread_number=CHART[thread].number, shape_id=sid, area_mm2=3.0 * h,
               meta=dict(stitched=True, **meta))
    return r


def word(thread):
    return [region(f"L{i}", 4.0 * i, thread, text_cluster_id="TC1") for i in range(1, 4)]


def near_pair():
    """Two greys a stray could plausibly have snapped between."""
    return spool(58), spool(42)


def cfg(**kw):
    return PipelineConfig(garment_rgb=NATURAL, **kw)


def test_off_moves_nothing():
    pale, mid = spool(85), spool(58)
    regions = word(pale) + [region("A", 0.0, mid, small_text_stray=True)]
    before = [r.thread_index for r in regions]
    assert PipelineConfig().lettering_stray_word_thread is False
    assert PipelineConfig().lettering_contrast_floor is False
    apply_lettering_thread(regions, CHART, cfg(), {})
    assert [r.thread_index for r in regions] == before


def test_no_garment_colour_moves_nothing():
    regions = word(spool(90))
    before = [r.thread_index for r in regions]
    apply_lettering_thread(regions, CHART, PipelineConfig(lettering_contrast_floor=True), {})
    assert [r.thread_index for r in regions] == before


def test_stray_takes_its_words_thread():
    letters, dark = near_pair()
    regions = word(letters) + [region("A", 0.0, dark, small_text_stray=True)]
    assert stray_word_thread(regions, CHART, {}) == 1
    assert regions[-1].thread_index == letters
    assert regions[-1].thread_number == CHART[letters].number


def test_stray_off_the_line_or_far_in_colour_stays():
    letters, dark = near_pair()
    below = region("A", 0.0, dark, y=20.0, small_text_stray=True)
    tall = region("B", 0.0, dark, h=12.0, small_text_stray=True)
    far = region("C", 0.0, spool(5), small_text_stray=True)
    for odd in (below, tall):
        assert stray_word_thread(word(letters) + [odd], CHART, {}) == 0
    assert stray_word_thread(word(spool(95)) + [far], CHART, {}) == 0


def test_a_stated_colour_is_never_moved():
    letters, dark = near_pair()
    stray = region("A", 0.0, dark, small_text_stray=True)
    assert stray_word_thread(word(letters) + [stray], CHART, {"A": {"thread_index": dark}}) == 0
    pale = spool(92)
    regions = word(pale)
    contrast_floor(regions, CHART, NATURAL, 15.0, {"L1": {"thread_index": pale}})
    assert regions[0].thread_index == pale
    assert regions[1].thread_index != pale


def test_floor_prefers_a_cone_on_the_design():
    pale, mid = spool(85), spool(62)
    regions = word(pale) + [region("X", 40.0, mid)]
    assert contrast_floor(regions, CHART, NATURAL, 15.0, {}) == 3
    assert {r.thread_index for r in regions} == {mid}


def test_floor_ignores_a_far_cone_and_clears_from_the_chart():
    pale = spool(92)
    black = spool(0)
    regions = word(pale) + [region("X", 40.0, black)]
    contrast_floor(regions, CHART, NATURAL, 15.0, {})
    got = regions[0].thread_index
    assert got not in (pale, black)
    assert CHART.delta_e(pale, got) < 35.0


def test_floor_leaves_a_clear_thread_alone():
    regions = word(spool(30))
    assert contrast_floor(regions, CHART, NATURAL, 15.0, {}) == 0


def test_floor_leaves_letters_sewn_on_other_thread():
    badge = region("G", 0.0, spool(0), h=4.0)
    badge.polygon = box(-2.0, -2.0, 30.0, 8.0)
    regions = word(spool(92)) + [badge]
    assert contrast_floor(regions, CHART, NATURAL, 15.0, {}) == 0
