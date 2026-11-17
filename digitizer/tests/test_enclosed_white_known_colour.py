"""`cfg.enclosed_white_keeps_known_colour` (built OFF, Kent 2026-11-17 logo trial).

A logo whose thin dark frame stage 1 takes as the page makes its dark letter
bands and counters `enclosed_background` regions of a KNOWN colour. The
Studio's "Sew white areas" thread (white) used to recolour them white, where
they fused with the white letters they wrap. ON, a known colour clearly unlike
the chosen thread (farther than `enclosed_by_garment_de00`) keeps its own
thread and still sews, in its own front layer. Synthetic regions only.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.enclosed_white import apply_enclosed_white
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for, rgb_to_lab
from tests.conftest import ENGINE_2026_10_27

CHART = chart_for(PipelineConfig())


def _nearest(rgb) -> int:
    return CHART.nearest_index(rgb_to_lab(np.array([rgb], dtype=np.float64))[0])


WHITE_T, BLACK_T, RED_T = _nearest((255, 255, 255)), _nearest((0, 0, 0)), _nearest((200, 20, 20))
CREAM_T = _nearest((245, 240, 225))


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _reg(sid, ring, holes=(), *, thread, layer=0, **meta) -> Region:
    poly = Polygon(ring, list(holes))
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, **meta})


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(sew_enclosed_white=True, sew_enclosed_rgb=(255, 255, 255), **kw)


def _scene(hole_thread, **hole_meta):
    """A red field holding one 8 mm enclosed hole whose own thread is given."""
    ring = _reg("Sring", _box(0, 0, 20, 10), [_box(1, 1, 9, 9)], thread=RED_T)
    hole = _reg("Shole", _box(1, 1, 9, 9), thread=hole_thread, layer=1,
                enclosed_background=True, **hole_meta)
    return [ring, hole]


def test_default_is_off_and_the_snapshot_holds_it_off():
    assert PipelineConfig().enclosed_white_keeps_known_colour is False
    assert ENGINE_2026_10_27["enclosed_white_keeps_known_colour"] is False


def test_a_dark_known_band_goes_white_off_and_keeps_its_thread_on():
    regs = _scene(BLACK_T)
    out, n = apply_enclosed_white(regs, [RED_T, BLACK_T], _cfg(), CHART)
    assert n == 1 and regs[1].thread_index == WHITE_T          # OFF: today's recolour

    regs = _scene(BLACK_T)
    out, n = apply_enclosed_white(regs, [RED_T, BLACK_T],
                                  _cfg(enclosed_white_keeps_known_colour=True), CHART)
    assert n == 1                                               # still SEWN
    assert regs[1].thread_index == BLACK_T
    assert regs[1].meta["sew_enclosed_white"] == "field"
    assert out == [BLACK_T, RED_T, BLACK_T]                     # its own front layer
    assert regs[1].meta["layer"] == 0 and regs[0].meta["layer"] == 1


def test_a_white_page_is_unchanged_on_and_off():
    results = []
    for on in (False, True):
        regs = _scene(WHITE_T)
        out, n = apply_enclosed_white(regs, [RED_T, WHITE_T],
                                      _cfg(enclosed_white_keeps_known_colour=on), CHART)
        results.append((out, n, regs[1].thread_index, regs[1].meta["layer"]))
    assert results[0] == results[1]
    assert results[1][2] == WHITE_T


def test_a_near_white_known_page_still_takes_the_chosen_white():
    # within the garment rule's 10 dE00 of the chosen white: not "clearly different"
    regs = _scene(CREAM_T)
    assert CHART.delta_e(CREAM_T, WHITE_T) <= PipelineConfig().enclosed_by_garment_de00
    apply_enclosed_white(regs, [RED_T, CREAM_T],
                         _cfg(enclosed_white_keeps_known_colour=True), CHART)
    assert regs[1].thread_index == WHITE_T


def test_an_unknown_transparent_page_is_unchanged():
    # alpha art: the hole's colour is nobody's; ON must not read its carried thread
    for skip in (False,):
        pair = []
        for on in (False, True):
            regs = _scene(BLACK_T, enclosed_colour_unknown=True)
            out, n = apply_enclosed_white(
                regs, [RED_T, BLACK_T],
                _cfg(enclosed_white_keeps_known_colour=on, enclosed_white_skip_transparent=skip),
                CHART)
            pair.append((out, n, regs[1].thread_index))
        assert pair[0] == pair[1] and pair[1][2] == WHITE_T


def test_a_review_recolour_still_wins():
    regs = _scene(BLACK_T)
    green = _nearest((20, 160, 20))
    regs[1].thread_index = green
    apply_enclosed_white(regs, [RED_T, BLACK_T],
                         _cfg(enclosed_white_keeps_known_colour=True), CHART,
                         {"Shole": {"thread_index": green}})
    assert regs[1].thread_index == green


def test_no_chosen_thread_is_unchanged():
    # sew_enclosed_rgb None already keeps a known hole's thread: the flag adds nothing
    pair = []
    for on in (False, True):
        regs = _scene(BLACK_T)
        out, n = apply_enclosed_white(
            regs, [RED_T, BLACK_T],
            PipelineConfig(sew_enclosed_white=True, enclosed_white_keeps_known_colour=on), CHART)
        pair.append((out, n, regs[1].thread_index))
    assert pair[0] == pair[1] and pair[1][2] == BLACK_T
