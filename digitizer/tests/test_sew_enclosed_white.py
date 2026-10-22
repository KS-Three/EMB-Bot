"""`cfg.sew_enclosed_white` (2026-10-21, built OFF): the customer's option to
sew the white or hollow areas inside a design instead of leaving fabric.

The pro does it on 5 of 11 jobs (rule R11,
`docs/pro-digitizer-rules-2026-10-21.md`): badge fields, hollow letters,
white letters and keylines. A letter's counter stays open unless the
customer asks (`sew_enclosed_counters`) or it sits inside a field that sews.
See `digitizer_core/enclosed_white.py` for the rule.
"""
from __future__ import annotations

import hashlib

import pytest
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.enclosed_white import apply_enclosed_white, plan_enclosed_white
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for, rgb_to_lab
from tests.conftest import TESTDATA

import numpy as np

CHART = chart_for(PipelineConfig())
WHITEBG = TESTDATA / "logo_whitebg.png"     # white bg, one white hole
ALPHA = TESTDATA / "logo_alpha.png"         # alpha cutout: hole colour unknown
NATURAL = (235, 232, 223)                   # the Studio's default garment


def _nearest(rgb) -> int:
    return CHART.nearest_index(rgb_to_lab(np.array([rgb], dtype=np.float64))[0])


WHITE_T = _nearest((255, 255, 255))
BLACK_T = _nearest((0, 0, 0))


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _reg(sid, ring, holes=(), *, thread=BLACK_T, layer=0, **meta) -> Region:
    poly = Polygon(ring, [h for h in holes])
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, **meta})


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(sew_enclosed_white=True, **kw)


# --- which enclosed areas sew ---------------------------------------------------

def _ring_and_hole(outer_tags=None, inner_tags=None):
    """A 10 mm black ring with a 6 mm white hole, and the white area in it."""
    ring = _reg("Sring", _box(0, 0, 10, 10), [_box(2, 2, 8, 8)], **(outer_tags or {}))
    hole = _reg("Shole", _box(2, 2, 8, 8), thread=WHITE_T, enclosed_background=True,
                **(inner_tags or {}))
    return [ring, hole]


def test_a_field_inside_an_untagged_ring_sews():
    assert plan_enclosed_white(_ring_and_hole(), _cfg()) == {"Shole": "field"}


def test_a_counter_inside_a_letter_stays_open_unless_asked():
    regs = _ring_and_hole(outer_tags={"text_candidate": True})
    assert plan_enclosed_white(regs, _cfg()) == {}
    assert plan_enclosed_white(regs, _cfg(sew_enclosed_counters=True)) == {"Shole": "counter"}


def test_a_hollow_letter_body_is_not_a_counter():
    # BECKER: the white body is itself tagged lettering, inside an untagged keyline.
    regs = _ring_and_hole(inner_tags={"text_candidate": True})
    assert plan_enclosed_white(regs, _cfg()) == {"Shole": "field"}


def test_a_house_group_only_ring_is_not_a_letter():
    # Golden Tee's ball-arc outline carries `lettering_group` alone; the pro
    # sews the crescent inside it.
    regs = _ring_and_hole(outer_tags={"lettering_group": 1})
    assert plan_enclosed_white(regs, _cfg()) == {"Shole": "field"}


def test_a_kept_counter_is_a_counter():
    regs = _ring_and_hole(inner_tags={"counter": True})
    assert plan_enclosed_white(regs, _cfg()) == {}


def test_a_counter_inside_a_sewn_field_sews_with_it():
    # A badge: outline ring, white field, a letter on the field, its counter.
    badge = _reg("Sbadge", _box(0, 0, 30, 30), [_box(2, 2, 28, 28)])
    field = _reg("Sfield", _box(2, 2, 28, 28), [_box(10, 10, 20, 20)], thread=WHITE_T,
                 enclosed_background=True)
    letter = _reg("Sletter", _box(10, 10, 20, 20), [_box(13, 13, 17, 17)], text_candidate=True)
    counter = _reg("Scounter", _box(13, 13, 17, 17), thread=WHITE_T, enclosed_background=True)
    plan = plan_enclosed_white([badge, field, letter, counter], _cfg())
    assert plan == {"Sfield": "field", "Scounter": "counter_in_field"}


def test_lettering_words_reads_the_word_tag_instead():
    regs = _ring_and_hole(outer_tags={"text_candidate": True})
    assert plan_enclosed_white(regs, _cfg(lettering_words=True)) == {"Shole": "field"}
    regs = _ring_and_hole(outer_tags={"word_id": "w1"})
    assert plan_enclosed_white(regs, _cfg(lettering_words=True)) == {}


# --- thread and layer -------------------------------------------------------------

def test_a_known_hole_keeps_its_colour_and_an_alpha_hole_sews_white():
    cream = _nearest((240, 230, 200))
    ring = _reg("Sring", _box(0, 0, 30, 10), [_box(1, 1, 9, 9), _box(11, 1, 19, 9)], layer=0)
    known = _reg("Sknown", _box(1, 1, 9, 9), thread=cream, layer=1, enclosed_background=True)
    alpha = _reg("Salpha", _box(11, 1, 19, 9), thread=BLACK_T, layer=0,
                 enclosed_background=True, enclosed_colour_unknown=True)
    regs = [ring, known, alpha]
    out, n = apply_enclosed_white(regs, [BLACK_T, cream], _cfg(), CHART)
    assert n == 2
    assert known.thread_index == cream and alpha.thread_index == WHITE_T
    # Two front layers, one per thread, in region order; the rest shift by two.
    assert out == [cream, WHITE_T, BLACK_T, cream]
    assert (known.meta["layer"], alpha.meta["layer"], ring.meta["layer"]) == (0, 1, 2)
    assert known.meta["sew_enclosed_white"] == "field"


def test_a_chosen_colour_sews_every_area_and_a_review_recolour_still_wins():
    regs = _ring_and_hole()
    red = _nearest((200, 20, 20))
    out, n = apply_enclosed_white(regs, [BLACK_T, WHITE_T], _cfg(sew_enclosed_rgb=(200, 20, 20)), CHART)
    assert n == 1 and regs[1].thread_index == red and out[0] == red
    regs = _ring_and_hole()
    green = _nearest((20, 160, 20))
    regs[1].thread_index = green          # apply_shape_edits already recoloured it
    apply_enclosed_white(regs, [BLACK_T, WHITE_T], _cfg(sew_enclosed_rgb=(200, 20, 20)), CHART,
                         {"Shole": {"thread_index": green}})
    assert regs[1].thread_index == green


def test_a_review_off_switch_is_left_alone():
    regs = _ring_and_hole()
    out, n = apply_enclosed_white(regs, [BLACK_T], _cfg(), CHART, {"Shole": {"stitched": False}})
    assert n == 0 and out == [BLACK_T] and "sew_enclosed_white" not in regs[1].meta


# --- through the pipeline ------------------------------------------------------------

def _digest(plan) -> str:
    h = hashlib.sha1()
    for b in plan.blocks:
        h.update(str(b.thread_number).encode())
        for run in b.runs:
            h.update(str(len(run.points)).encode())
            for x, y in run.points:
                h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _pcfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", garment_rgb=NATURAL, **kw)


@pytest.fixture(scope="module")
def whitebg_default():
    return digitize(WHITEBG, _pcfg())


def test_off_is_the_default_engine(whitebg_default):
    r, plan = digitize(WHITEBG, _pcfg(sew_enclosed_white=False, sew_enclosed_counters=True,
                                      sew_enclosed_rgb=(255, 0, 0)))
    assert _digest(plan) == _digest(whitebg_default[1])
    assert not any("sew_enclosed_white" in x.meta for x in r.regions)


def test_whitebg_hole_sews_first_on_the_natural_garment(whitebg_default):
    r0, plan0 = whitebg_default
    hole0 = [x for x in r0.regions if x.meta.get("enclosed_background")]
    assert len(hole0) == 1 and hole0[0].meta["stitched"] is False   # the garment rule declines
    r, plan = digitize(WHITEBG, _pcfg(sew_enclosed_white=True))
    hole = [x for x in r.regions if x.meta.get("enclosed_background")]
    assert len(hole) == 1 and hole[0].meta["stitched"] is True
    assert hole[0].meta["sew_enclosed_white"] == "field"
    assert plan.blocks[0].thread_number == hole[0].thread_number   # sewn first
    assert _digest(plan) != _digest(plan0)
    w = [x for x in r.warnings if x["code"] == "BACKGROUND_ENCLOSED"]
    assert len(w) == 1 and w[0]["sewn_by_option"] == 1 and "SEW" in w[0]["message"]


def test_a_review_off_switch_beats_the_option():
    r0, _ = digitize(WHITEBG, _pcfg(sew_enclosed_white=True))
    sid = next(x.shape_id for x in r0.regions if x.meta.get("enclosed_background"))
    r, _ = digitize(WHITEBG, _pcfg(sew_enclosed_white=True,
                                   shape_overrides={sid: {"stitched": False}}))
    hole = next(x for x in r.regions if x.shape_id == sid)
    assert hole.meta["stitched"] is False


def test_an_alpha_hole_sews_white():
    r, _ = digitize(ALPHA, _pcfg(sew_enclosed_white=True))
    holes = [x for x in r.regions if x.meta.get("sew_enclosed_white")]
    assert holes and all(x.meta.get("enclosed_colour_unknown") for x in holes)
    assert all(x.thread_index == WHITE_T and x.meta["stitched"] for x in holes)
