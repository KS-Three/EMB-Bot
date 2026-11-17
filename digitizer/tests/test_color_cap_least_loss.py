"""`cfg.color_cap_least_loss`: which threads the colour cap KEEPS.

The cap kept the N threads with the most sewn area. On Precision Drone
(2026-11-17, the prime grader's first scorecard: "no blue thread anywhere")
that is black, orange and four greys; the 34 mm2 of blue water sewed in the
nearest grey. ON, the kept set is the one with the least total sewn area x
CIEDE2000 squared from each dropped thread to the thread it lands on.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon
from skimage.color import deltaE_ciede2000

from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import _least_loss_keep, enforce_color_cap
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())


def _nearest(lab) -> int:
    d = deltaE_ciede2000(np.array(CHART.lab), np.array(lab, float)[None, :])
    return int(np.argmin(d))


BLACK, WHITE = _nearest([0, 0, 0]), _nearest([100, 0, 0])
GREYS = [_nearest([L, 0, 0]) for L in (45, 52, 59)]
BLUE = _nearest([30, 20, -55])


def _region(sid: str, thread: int, area: float) -> Region:
    s = max(area, 0.01) ** 0.5
    return Region(shape_id=sid, polygon=Polygon([(0, 0), (s, 0), (s, s), (0, s)]),
                  thread_index=thread, thread_number=CHART[thread].number, area_mm2=area, meta={})


def _design() -> list[Region]:
    """Black, white, three near greys, and a blue smaller than any of them."""
    assert len({BLACK, WHITE, BLUE, *GREYS}) == 6
    return ([_region("k", BLACK, 800), _region("w", WHITE, 300)]
            + [_region(f"g{i}", t, 120 - 10 * i) for i, t in enumerate(GREYS)]
            + [_region("b", BLUE, 35)])


def test_off_is_the_area_ranking():
    regions = _design()
    enforce_color_cap(regions, CHART, 5)
    assert BLUE not in {r.thread_index for r in regions}        # the smallest goes


def test_on_keeps_the_lone_colour_and_folds_a_near_duplicate():
    regions = _design()
    (w,) = enforce_color_cap(regions, CHART, 5, least_loss=True)
    kept = {r.thread_index for r in regions}
    assert BLUE in kept and BLACK in kept and WHITE in kept
    assert len(kept) == 5 and w["after"] == 5
    assert len(kept & set(GREYS)) == 2                          # one grey folded into its neighbour
    moved = next(r for r in regions if "color_cap_merged_from" in r.meta)
    assert moved.thread_index in GREYS


def test_on_changes_nothing_under_the_cap():
    regions = _design()
    assert enforce_color_cap(regions, CHART, 6, least_loss=True) == []
    assert [r.thread_index for r in regions] == [r.thread_index for r in _design()]


def test_a_speck_of_colour_does_not_evict_a_real_shade():
    regions = _design()
    regions[-1] = _region("b", BLUE, 0.5)                       # half a square mm of blue
    enforce_color_cap(regions, CHART, 5, least_loss=True)
    assert BLUE not in {r.thread_index for r in regions}


def test_protected_threads_stay_pinned():
    regions = _design()
    enforce_color_cap(regions, CHART, 5, least_loss=True, protected=set(GREYS))
    kept = {r.thread_index for r in regions}
    assert set(GREYS) <= kept and len(kept) == 5


def test_the_answer_does_not_depend_on_region_order():
    a, b = _design(), list(reversed(_design()))
    enforce_color_cap(a, CHART, 4, least_loss=True)
    enforce_color_cap(b, CHART, 4, least_loss=True)
    assert {r.thread_index for r in a} == {r.thread_index for r in b}


def test_least_loss_keep_returns_n_in_ranked_order():
    ranked = [BLACK, WHITE, *GREYS, BLUE]
    area = dict(zip(ranked, (800, 300, 120, 110, 100, 35)))
    kept = _least_loss_keep(ranked, 5, [], area, CHART)
    assert len(kept) == 5 and kept == [t for t in ranked if t in kept]


def test_a_grey_never_evicts_a_colour():
    """Summit badge, the first sweep: a grey took the lavender lettering's slot."""
    lav, purple, orange = _nearest([60, 12, -28]), _nearest([45, 45, -40]), _nearest([65, 35, 65])
    grey = _nearest([72, 0, 0])
    assert len({BLACK, lav, purple, orange, grey}) == 5
    regions = [_region("k", BLACK, 900), _region("p", purple, 300), _region("o", orange, 200),
               _region("l", lav, 60), _region("g", grey, 55)]
    off = [r.thread_index for r in regions]
    enforce_color_cap(regions, CHART, 4, least_loss=True)
    kept = {r.thread_index for r in regions}
    assert lav in kept and grey not in kept
    regions2 = [_region("k", BLACK, 900), _region("p", purple, 300), _region("o", orange, 200),
                _region("l", lav, 60), _region("g", grey, 55)]
    enforce_color_cap(regions2, CHART, 4)
    assert [r.thread_index for r in regions] == [r.thread_index for r in regions2] != off


def test_a_second_shade_of_a_kept_hue_buys_no_slot():
    o1, o2 = _nearest([65, 35, 65]), _nearest([75, 22, 75])
    assert o1 != o2
    regions = [_region("k", BLACK, 900), _region("w", WHITE, 300), _region("o", o1, 200),
               _region("g0", GREYS[0], 90), _region("g1", GREYS[2], 80), _region("o2", o2, 40)]
    enforce_color_cap(regions, CHART, 5, least_loss=True)
    assert o2 not in {r.thread_index for r in regions}


def test_the_flag_is_off_by_default():
    assert PipelineConfig().color_cap_least_loss is False
