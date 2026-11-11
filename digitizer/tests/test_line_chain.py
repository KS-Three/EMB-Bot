"""`cfg.line_chain_one_thread` (built OFF 2026-11-11): one thread per connected
drawn line, only when the art line is one colour.

Kent on `C_low_poly` pin 2, then "Keep OFF, build fix B"
(`docs/border-colour-change-2026-11-11.md`): the art's outline is one black
line that sews in two or three threads. Pinned on a hand-built `Prep` (the real
rows are gitignored):

1. The flag defaults OFF.
2. A line cut into pieces of different threads whose core colour is one colour
   takes ONE thread, and its pieces move to that cone's layer.
3. A genuinely two-colour line (a red piece beside a blue piece) is NOT forced
   to one colour.
4. A thin sliver of the face beside a line (no contrast with its ground) is not
   part of the line and keeps its thread.
5. A chain whose pieces already share one thread is left alone, and the cone
   set never grows.
"""
from types import SimpleNamespace

import numpy as np
from shapely.geometry import box

from digitizer_core import line_chain
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for, rgb_to_lab

PX_PER_MM = 5.0
W, H = 400, 240
CX, CY = W / 2.0, H / 2.0
ROW0, ROW1 = 118, 123            # the 1 mm line: 5 px at 5 px/mm, centred on y = 0


def _chart():
    return chart_for(PipelineConfig(target_width_mm=80.0))


def _idx(chart, rgb):
    return chart.nearest_index(rgb_to_lab(np.array([rgb], dtype=np.float64))[0])


def _prep(paint):
    """White ground (235); `paint` is a list of (x0, x1, y0, y1, rgb) boxes in px."""
    rgb = np.full((H, W, 3), 235, np.uint8)
    for x0, x1, y0, y1, c in paint:
        rgb[y0:y1, x0:x1, :] = c
    return SimpleNamespace(rgb=rgb, bg_mask=np.zeros((H, W), bool),
                           px_per_mm=PX_PER_MM, art_bbox=(0, 0, W, H))


def _region(chart, sid, x0, x1, y0, y1, rgb, layer):
    t = _idx(chart, rgb)
    poly = box(x0, y0, x1, y1)
    return Region(shape_id=sid, polygon=poly, thread_index=t, thread_number=chart[t].number,
                  area_mm2=poly.area, meta={"layer": layer})


def _apply(regions, prep, chart, layers):
    return line_chain.apply(regions, prep, PipelineConfig(target_width_mm=80.0), chart, layers)


def _two_pieces(chart, colour_a, colour_b, paint_a, paint_b):
    """A 1 mm x 72 mm line in two touching pieces, painted `paint_a` | `paint_b`,
    carrying the spools nearest `colour_a` and `colour_b`."""
    prep = _prep([(20, 200, ROW0, ROW1, paint_a), (200, 380, ROW0, ROW1, paint_b)])
    a = _region(chart, "A", -36.0, 0.0, -0.5, 0.5, colour_a, layer=0)
    b = _region(chart, "B", 0.0, 36.0, -0.5, 0.5, colour_b, layer=1)
    layers = [a.thread_index, b.thread_index]
    return prep, [a, b], layers


def test_the_flag_defaults_off():
    assert PipelineConfig().line_chain_one_thread is False


def test_a_black_line_cut_into_a_black_and_a_grey_piece_takes_one_thread():
    chart = _chart()
    black, grey = (0, 0, 0), (140, 137, 132)
    prep, regions, layers = _two_pieces(chart, black, grey, black, black)
    a, b = regions
    assert a.thread_index != b.thread_index
    stats = _apply(regions, prep, chart, layers)
    assert stats["unified"] == 1 and stats["refused"] == 0
    assert a.thread_index == b.thread_index == _idx(chart, black)
    assert b.meta["layer"] == 0                      # moved to the cone's own layer
    assert b.meta["line_chain_thread"] is True
    assert "line_chain_thread" not in a.meta         # a did not change


def test_a_genuinely_two_colour_line_is_not_forced_to_one_colour():
    chart = _chart()
    red, blue = (220, 20, 20), (20, 20, 220)
    prep, regions, layers = _two_pieces(chart, red, blue, red, blue)
    a, b = regions
    before = (a.thread_index, b.thread_index)
    stats = _apply(regions, prep, chart, layers)
    assert stats["refused"] == 1 and stats["unified"] == 0
    assert (a.thread_index, b.thread_index) == before
    assert a.thread_index != b.thread_index
    assert "line_chain_thread" not in a.meta and "line_chain_thread" not in b.meta


def test_a_speck_of_another_colour_does_not_stop_the_line_and_is_left_alone():
    chart = _chart()
    black, grey, red = (0, 0, 0), (140, 137, 132), (220, 20, 20)
    prep, regions, layers = _two_pieces(chart, black, grey, black, black)
    prep.rgb[ROW0:ROW1, 372:380, :] = red            # the last 1.6 mm of B reads red
    speck = _region(chart, "C", 34.4, 36.0, -0.5, 0.5, red, layer=1)
    regions[1].polygon = box(0.0, -0.5, 34.4, 0.5)   # B stops where the speck starts
    regions.append(speck)
    layers.append(speck.thread_index)
    before = speck.thread_index
    stats = _apply(regions, prep, chart, layers)
    assert stats["unified"] == 1
    assert regions[0].thread_index == regions[1].thread_index == _idx(chart, black)
    assert speck.thread_index == before


def test_a_thin_sliver_of_the_face_beside_a_line_is_not_part_of_it():
    chart = _chart()
    black, grey = (0, 0, 0), (140, 137, 132)
    prep, regions, layers = _two_pieces(chart, black, grey, black, black)
    # a 0.8 mm sliver of pale face 0.1 mm from the line (inside LINK_MM): pixels equal to the ground
    sliver = _region(chart, "F", -36.0, 36.0, -1.4, -0.6, grey, layer=2)
    regions.append(sliver)
    layers.append(sliver.thread_index)
    before = sliver.thread_index
    stats = _apply(regions, prep, chart, layers)
    # the sliver does not veto the line (it would, as an outlier of 55% of the
    # chain's area, were it counted as a piece of it) and is not recoloured
    assert stats["unified"] == 1
    assert regions[0].thread_index == regions[1].thread_index == _idx(chart, black)
    assert sliver.thread_index == before
    assert "line_chain_thread" not in sliver.meta


def test_a_chain_already_on_one_thread_is_untouched():
    chart = _chart()
    black = (0, 0, 0)
    prep, regions, layers = _two_pieces(chart, black, black, black, black)
    stats = _apply(regions, prep, chart, layers)
    assert stats["chains"] == 0 and stats["recoloured"] == 0
    assert all("line_chain_thread" not in r.meta for r in regions)


def test_the_cone_set_never_grows():
    chart = _chart()
    black, grey = (0, 0, 0), (140, 137, 132)
    prep, regions, layers = _two_pieces(chart, black, grey, black, black)
    before = {r.thread_index for r in regions}
    _apply(regions, prep, chart, layers)
    assert {r.thread_index for r in regions} <= before
