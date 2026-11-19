"""`cfg.keyline_under_face` (2026-11-19, built OFF): a dark thin-band layer sews under the faces it borders.

Golden Tee: `borders_last` sews the burnt-orange keyline layer last, over the gold and pumpkin
faces it fences. Order only; no satin floor, pull or cover value moves (ROADMAP gate 1).
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.keyline_under_face import keylines_under_face
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())


def _idx(number):
    return next(i for i, t in enumerate(CHART) if t.number == number)


BLACK, RED, GOLD, WHITE = _idx("0020"), _idx("1312"), _idx("0811"), _idx("0015")


def _r(sid, thread, layer, poly):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area, meta={"layer": layer})


def _design():
    # layer order: white 0, black 1, gold 2, red 3 (red last, as borders_last leaves it)
    white = _r("w", WHITE, 0, box(0, 0, 10, 10))
    black = _r("k", BLACK, 1, box(0, 11, 10, 11.4))
    gold = _r("g", GOLD, 2, box(10, 0, 20, 10))
    red = _r("r", RED, 3, box(9.8, 0, 10.2, 10))      # 0.4 mm band between white and gold
    return [white, black, gold, red], [WHITE, BLACK, GOLD, RED]


def test_the_keyline_layer_moves_before_the_earliest_face_it_touches():
    regions, threads = _design()
    out = keylines_under_face(regions, threads, CHART)
    assert out == [RED, WHITE, BLACK, GOLD]
    assert {r.shape_id: r.meta["layer"] for r in regions} == {"r": 0, "w": 1, "k": 2, "g": 3}


def test_the_darkest_ink_is_never_moved():
    regions, threads = _design()
    keylines_under_face(regions, threads, CHART)
    black = next(r for r in regions if r.shape_id == "k")
    white = next(r for r in regions if r.shape_id == "w")
    assert black.meta["layer"] > white.meta["layer"]      # black still sews after white


def test_no_keyline_layer_no_change():
    regions, threads = _design()
    regions = [r for r in regions if r.shape_id != "r"]
    out = keylines_under_face(regions, [WHITE, BLACK, GOLD], CHART)
    assert out == [WHITE, BLACK, GOLD]


def test_a_keyline_far_from_every_face_stays():
    regions, threads = _design()
    next(r for r in regions if r.shape_id == "r").polygon = box(50, 0, 50.4, 10)
    assert keylines_under_face(regions, threads, CHART) == threads


def test_a_face_that_already_sews_after_it_is_left_alone():
    white = _r("w", WHITE, 1, box(0, 0, 10, 10))
    red = _r("r", RED, 0, box(9.8, 0, 10.2, 10))
    black = _r("k", BLACK, 2, box(0, 11, 10, 11.4))
    assert keylines_under_face([red, white, black], [RED, WHITE, BLACK], CHART) == [RED, WHITE, BLACK]


def test_the_flag_is_a_typed_field_default_off_and_the_snapshot_pins_it_off():
    from tests.conftest import ENGINE_2026_10_27
    assert PipelineConfig().keyline_under_face is False
    assert ENGINE_2026_10_27["keyline_under_face"] is False
