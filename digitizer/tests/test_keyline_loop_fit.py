"""`cfg.extra["keyline_loop_fit"]` (built OFF 2026-11-15, Kent: "Fix MFab
white loops").

A keyline over the hairline gate (0.6 mm at 40 wt) sews as a satin loop, never
under `machine.OUTLINE_WIDTH_MM`'s 1.5 mm. On MFab's hat with
`photo_enclosed_rim` ON the keyline reads 0.60 to 0.95 mm at 38 to 60 mm wide
and the loop 1.62 to 2.01 mm, round letters whose strokes are 1.90 to 2.95 mm:
the faces sew as slivers and the hyphen is lost. ON, a thread whose loops do
not fit the bodies they ring (`keyline_bean.loop_fits`) sews its keylines as
the bean. Layout, judged in the preview; unsewn.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, keyline_bean, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.pipeline import _art_outlines
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence

KEY = keyline_bean.LOOP_FIT_KEY
ON = {KEY: True}

#: a letter stroke: 30 x 2 mm, 2 x area / perimeter 1.875 mm
BAR = box(-15, -1, 15, 1)
#: a face: 30 x 12 mm, 8.57 mm
FACE = box(-15, -6, 15, 6)


def _ring(width_mm: float, body):
    return body.buffer(width_mm, join_style=2).difference(body)


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _regions(width_mm: float, body, extra=()):
    return [_region("Sbody", body, 0, 0), _region("Souter", _ring(width_mm, body), 1, 1), *extra]


def _taken(width_mm: float, body, *, extra=(), cfg_extra=None, with_bodies: bool = True):
    regions = _regions(width_mm, body, extra)
    cfg = PipelineConfig(extra=dict(cfg_extra or {}))
    outlines = _art_outlines(regions, cfg)
    assert outlines and "Souter" in outlines, "the fixture must read as an art outline"
    return keyline_bean.keyline_regions(regions, set(outlines), cfg,
                                        bodies=outlines if with_bodies else None)


def _kinds(width_mm: float, body, cfg_extra=None) -> set[str]:
    regions = _regions(width_mm, body)
    planned = [PlannedRegion(region=r, polygon=r.polygon, sew_index=r.meta["layer"]) for r in regions]
    cfg = PipelineConfig(underlay=False, extra=dict(cfg_extra or {}))
    outlines = _art_outlines(regions, cfg)
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"), cfg, art_outlines=outlines)
    return {r.kind for blk in blocks for r in blk.runs if r.shape_id == "Souter"} - {stitches.TRAVEL}


# --- the rule -----------------------------------------------------------------

def test_off_by_default():
    assert not (PipelineConfig().extra or {}).get(KEY)


@pytest.mark.parametrize("width_mm, stroke, keyline, loop, fits", [
    # MFab hat, `photo_enclosed_rim` ON, no cutout (probe, 2026-11-15)
    (38.0, 1.90, 0.604, 1.624, False),
    (45.0, 2.25, 0.719, 1.703, False),
    (50.0, 2.50, 0.815, 1.722, False),
    (60.0, 2.95, 0.945, 2.011, False),
    (70.0, 3.43, 1.075, 2.058, True),
    (100.8, 4.93, 1.423, 2.116, True),     # the pro borders this size in satin
    # ... and rim OFF, where the loop is what sews today
    (55.0, 2.50, 0.657, 1.500, True),
    (60.0, 2.73, 0.703, 1.500, True),
])
def test_the_mfab_ladder(width_mm, stroke, keyline, loop, fits):
    assert keyline_bean.loop_fits([stroke], keyline, loop) is fits


def test_the_median_body_decides_and_no_body_fits():
    assert keyline_bean.loop_fits([], 0.8, 1.5)
    # two wide faces and one thin one: the loop fits the outline
    assert keyline_bean.loop_fits([6.0, 6.0, 1.0], 0.8, 1.5)
    assert not keyline_bean.loop_fits([6.0, 1.0, 1.0], 0.8, 1.5)


def test_a_face_exactly_as_wide_as_its_loop_fits():
    lo = machine.OUTLINE_WIDTH_MM[0]
    assert keyline_bean.loop_fits([2 * lo - 0.8], 0.8, lo)
    assert not keyline_bean.loop_fits([2 * lo - 0.8 - 1e-6], 0.8, lo)


# --- which keylines are taken -------------------------------------------------

def test_off_a_wide_keyline_round_a_thin_body_is_a_loop():
    """Today: 0.8 mm is over the hairline gate, so the outline is not a bean."""
    assert _taken(0.8, BAR) == set()


def test_on_a_loop_wider_than_the_face_it_leaves_is_a_bean():
    """1.875 mm stroke, 0.8 mm keyline, 1.5 mm loop: 1.175 mm of face left."""
    assert _taken(0.8, BAR, cfg_extra=ON) == {"Souter"}


def test_on_a_loop_that_fits_is_left_a_loop():
    """The same keyline round a 12 mm face: the loop is a border, not the art."""
    assert _taken(0.8, FACE, cfg_extra=ON) == set()


@pytest.mark.parametrize("width_mm", [0.3, 0.4, 0.55])
@pytest.mark.parametrize("body", [BAR, FACE])
def test_on_a_hairline_keyline_is_taken_as_before(width_mm, body):
    assert _taken(width_mm, body) == _taken(width_mm, body, cfg_extra=ON) == {"Souter"}


def test_on_a_band_as_wide_as_the_narrowest_loop_is_never_a_bean():
    """A 1.6 mm band round the 1.875 mm bar: its loop (1.76 mm) leaves 1.71 mm
    of face, 0.05 short of fitting, but a band the pro's narrowest border
    width or wider is a border, not a line."""
    assert 1.6 >= machine.OUTLINE_WIDTH_MM[0]
    assert _taken(1.6, BAR, cfg_extra=ON) == set()


def test_on_a_one_millimetre_keyline_round_a_thin_body_is_a_bean():
    """1.0 mm keyline, 1.5 mm loop, 1.875 mm stroke: 1.375 mm of face left."""
    assert _taken(1.0, BAR, cfg_extra=ON) == {"Souter"}


def test_on_a_keyline_near_the_loops_width_fits_and_stays_a_loop():
    """1.4 mm keyline, 1.52 mm loop: the loop adds 0.12 mm and leaves 1.75."""
    assert _taken(1.4, BAR, cfg_extra=ON) == set()


def test_on_a_frame_in_the_logos_own_ink_is_still_not_a_keyline():
    """The thread must still draw nearly nothing but keyline (To-a-T's frame)."""
    letter = _region("Sletter", box(-8, 6, 8, 16), 1, 1)
    assert _taken(0.8, BAR, extra=[letter], cfg_extra=ON) == set()


def test_on_without_the_outline_map_nothing_is_read():
    assert _taken(0.8, BAR, cfg_extra=ON, with_bodies=False) == set()


# --- through stage 7 ------------------------------------------------------------

def test_off_the_outline_sews_a_satin_loop():
    assert stitches.SATIN in _kinds(0.8, BAR)


def test_on_the_outline_sews_a_bean_and_no_satin():
    assert _kinds(0.8, BAR, ON) == {stitches.RUN}


def test_on_an_outline_whose_loop_fits_still_sews_satin():
    assert stitches.SATIN in _kinds(0.8, FACE, ON)
