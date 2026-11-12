"""`cfg.enclosed_white_skip_transparent` (built OFF 2026-11-11, ON by Kent's
ruling the same day, "Flip ON (Recommended)"): with "Sew
white areas" on, an enclosed area the artwork leaves TRANSPARENT (stage 4's
`enclosed_colour_unknown`) is not sewn; an area whose colour is known, and
every opaque shape, sews as before. Kent's pins: `C_kanji_seal` "#1-#28 extra
in-fill", `C_devanagari_logo` "in-fill only in select spots";
`docs/transparent-white-infill-2026-11-11.md`.
"""
from __future__ import annotations

import hashlib

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.enclosed_white import plan_enclosed_white
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for, rgb_to_lab
from tests.conftest import TESTDATA, WHITE_2026_11_11_OFF

CHART = chart_for(PipelineConfig())
WHITEBG = TESTDATA / "logo_whitebg.png"     # opaque: white page, one white hole
NATURAL = (235, 232, 223)


def _nearest(rgb) -> int:
    return CHART.nearest_index(rgb_to_lab(np.array([rgb], dtype=np.float64))[0])


WHITE_T, BLACK_T = _nearest((255, 255, 255)), _nearest((0, 0, 0))


def _box(x0, y0, x1, y1):
    return [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]


def _reg(sid, ring, holes=(), *, thread=BLACK_T, **meta) -> Region:
    poly = Polygon(ring, list(holes))
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area, meta={"layer": 0, **meta})


def _cfg(**kw) -> PipelineConfig:
    # the OFF arm by default, spelled out: the shipped default is ON
    return PipelineConfig(sew_enclosed_white=True, **{**WHITE_2026_11_11_OFF, **kw})


# --- the plan --------------------------------------------------------------------

def test_default_is_on_and_the_snapshot_holds_it_off():
    # ON by Kent's ruling 2026-11-11; the dated snapshot keeps the engine
    # before the flip, so `frozen_cfg()` pins still run OFF
    from tests.conftest import ENGINE_2026_10_27, PRE_FLIP
    assert PipelineConfig().enclosed_white_skip_transparent is True
    assert ENGINE_2026_10_27["enclosed_white_skip_transparent"] is False
    assert PRE_FLIP["enclosed_white_skip_transparent"] is False


def _two_holes():
    """A black bar with two 8 mm holes: one the art leaves transparent, one a
    known colour (the no-alpha path's page white)."""
    ring = _reg("Sring", _box(0, 0, 30, 10), [_box(1, 1, 9, 9), _box(11, 1, 19, 9)])
    known = _reg("Sknown", _box(1, 1, 9, 9), thread=WHITE_T, enclosed_background=True)
    alpha = _reg("Salpha", _box(11, 1, 19, 9), enclosed_background=True, enclosed_colour_unknown=True)
    return [ring, known, alpha]


def test_off_sews_both_on_leaves_the_transparent_one_open():
    assert plan_enclosed_white(_two_holes(), _cfg()) == {"Sknown": "field", "Salpha": "field"}
    assert plan_enclosed_white(_two_holes(), _cfg(enclosed_white_skip_transparent=True)) \
        == {"Sknown": "field"}


def test_a_counter_inside_a_transparent_field_stays_open_with_it():
    # A badge whose field is transparent: the letter's counter sewed only
    # because the field did (`counter_in_field`); with the field open, so is it.
    badge = _reg("Sbadge", _box(0, 0, 30, 30), [_box(2, 2, 28, 28)])
    field = _reg("Sfield", _box(2, 2, 28, 28), [_box(10, 10, 20, 20)], enclosed_background=True,
                 enclosed_colour_unknown=True)
    letter = _reg("Sletter", _box(10, 10, 20, 20), [_box(13, 13, 17, 17)], text_candidate=True)
    counter = _reg("Scounter", _box(13, 13, 17, 17), enclosed_background=True,
                   enclosed_colour_unknown=True)
    regs = [badge, field, letter, counter]
    assert plan_enclosed_white(regs, _cfg()) == {"Sfield": "field", "Scounter": "counter_in_field"}
    assert plan_enclosed_white(regs, _cfg(enclosed_white_skip_transparent=True)) == {}


def test_a_transparent_hollow_letter_body_still_sews():
    # BECKER: each white body is transparent in the PNG and tagged lettering,
    # inside an untagged keyline. The pro sews it; ON keeps it.
    ring = _reg("Sring", _box(0, 0, 10, 10), [_box(2, 2, 8, 8)])
    body = _reg("Sbody", _box(2, 2, 8, 8), enclosed_background=True, enclosed_colour_unknown=True,
                text_candidate=True)
    assert plan_enclosed_white([ring, body], _cfg(enclosed_white_skip_transparent=True)) \
        == {"Sbody": "field"}


def test_without_sew_enclosed_white_the_flag_reads_nothing():
    # The plan is only called with the option on; the flag never sews more.
    regs = _two_holes()
    on = plan_enclosed_white(regs, _cfg(enclosed_white_skip_transparent=True))
    assert set(on) <= set(plan_enclosed_white(regs, _cfg()))


# --- through the pipeline ----------------------------------------------------------

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
    return PipelineConfig(target_width_mm=60.0, garment_id="left_chest", garment_rgb=NATURAL,
                          sew_enclosed_white=True, sew_enclosed_rgb=(255, 255, 255),
                          **{**WHITE_2026_11_11_OFF, **kw})


def _rgba_fixture() -> np.ndarray:
    """BGRA, transparent page. Left: a red square ring round a TRANSPARENT
    hole. Right: a red square ring round an OPAQUE white square. Both holes
    are the same size, so only the alpha tells them apart."""
    img = np.zeros((240, 480, 4), np.uint8)
    red = (30, 30, 210, 255)
    for x0 in (20, 260):
        cv2.rectangle(img, (x0, 20), (x0 + 200, 220), red, -1)
    cv2.rectangle(img, (60, 60), (180, 180), (0, 0, 0, 0), -1)            # transparent hole
    cv2.rectangle(img, (300, 60), (420, 180), (255, 255, 255, 255), -1)   # opaque white
    return img


def _white_area(result, cfg) -> float:
    white = chart_for(cfg).nearest_index(rgb_to_lab(np.array([[255, 255, 255]], dtype=np.float64))[0])
    return sum(r.polygon.area for r in result.regions
               if r.meta.get("stitched") and int(r.thread_index) == int(white))


@pytest.fixture(scope="module")
def rgba_runs():
    img = _rgba_fixture()
    return (digitize(img.copy(), _pcfg()),
            digitize(img.copy(), _pcfg(enclosed_white_skip_transparent=True)))


def test_rgba_off_sews_the_transparent_hole_white(rgba_runs):
    (r_off, _), _ = rgba_runs
    sewn = [r for r in r_off.regions if r.meta.get("sew_enclosed_white")]
    assert sewn and all(r.meta.get("enclosed_colour_unknown") for r in sewn)


def test_rgba_on_leaves_the_transparent_hole_open_and_keeps_the_opaque_white(rgba_runs):
    (r_off, p_off), (r_on, p_on) = rgba_runs
    assert not any(r.meta.get("sew_enclosed_white") for r in r_on.regions)
    holes = [r for r in r_on.regions if r.meta.get("enclosed_background")]
    assert holes and not any(r.meta.get("stitched") for r in holes)
    # the opaque white square is a shape of its own colour, on either arm
    cfg = _pcfg()
    on_white = _white_area(r_on, cfg)
    assert on_white > 0
    # off sews the transparent hole white too: about twice the white
    assert _white_area(r_off, cfg) > 1.5 * on_white
    assert _digest(p_on) != _digest(p_off)


BECKER = TESTDATA / "becker_marine_logo.png"


@pytest.mark.parametrize("width_mm,garment", [(101.9, "hat_front"), (76.5, "left_chest")])
def test_becker_five_transparent_bodies_still_sew(width_mm, garment):
    """The guard, on the real art: Becker's five white BECKER bodies are
    transparent in its PNG, tagged lettering, and the pro sews them. ON sews
    the same areas as OFF; without the guard ON left all five open (measured
    on all five pairs, `docs/transparent-white-infill-2026-11-11.md`)."""
    from digitizer_core.pipeline import build_generation, finish_generation
    base = dict(target_width_mm=width_mm, garment_id=garment, garment_rgb=NATURAL,
                sew_enclosed_white=True)
    off_cfg = PipelineConfig(**base, **WHITE_2026_11_11_OFF)
    on_cfg = PipelineConfig(**base, enclosed_white_skip_transparent=True)
    gen = build_generation(BECKER, off_cfg)
    off = finish_generation(gen.fork(), off_cfg)
    on = finish_generation(gen.fork(), on_cfg)

    def sewn(res):
        return {r.shape_id for r in res.regions if r.meta.get("sew_enclosed_white")}

    bodies = {r.shape_id for r in off.regions
              if r.meta.get("enclosed_colour_unknown") and r.meta.get("sew_enclosed_white")}
    assert len(bodies) == 5
    assert sewn(on) == sewn(off) == bodies


def test_opaque_art_is_a_no_op():
    """No alpha channel: no hole is `enclosed_colour_unknown`, so ON is OFF."""
    r_off, p_off = digitize(WHITEBG, _pcfg())
    r_on, p_on = digitize(WHITEBG, _pcfg(enclosed_white_skip_transparent=True))
    assert any(r.meta.get("sew_enclosed_white") for r in r_off.regions)   # the option did sew
    assert not any(r.meta.get("enclosed_colour_unknown") for r in r_off.regions)
    assert _digest(p_on) == _digest(p_off)


def test_rgba_with_every_pixel_opaque_is_a_no_op():
    """An RGBA file whose alpha is 255 everywhere is opaque art: the same image
    with its hole painted white sews the same either way."""
    img = _rgba_fixture()
    img[:, :, 3] = 255
    img[(img[:, :, :3] == 0).all(-1)] = (255, 255, 255, 255)
    _, p_off = digitize(img.copy(), _pcfg())
    _, p_on = digitize(img.copy(), _pcfg(enclosed_white_skip_transparent=True))
    assert _digest(p_on) == _digest(p_off)


ALPHA = TESTDATA / "logo_alpha.png"         # alpha cutout: the blue ring's hole is transparent


def test_shipped_default_leaves_logo_alpha_ring_hole_open():
    """The flip on the default path: "Sew white areas" on (the recipe default)
    and nothing else said. `logo_alpha.png`'s blue ring holds one transparent
    hole (160.7 mm2 at 80 mm); OFF sewed it white, the shipped default leaves
    it open (`test_sew_enclosed_white.test_an_alpha_hole_sews_white` pins OFF)."""
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", garment_rgb=NATURAL)
    assert cfg.sew_enclosed_white and cfg.enclosed_white_skip_transparent
    r, _ = digitize(ALPHA, cfg)
    holes = [x for x in r.regions if x.meta.get("enclosed_colour_unknown")]
    assert holes
    assert not any(x.meta.get("sew_enclosed_white") or x.meta.get("stitched") for x in holes)
