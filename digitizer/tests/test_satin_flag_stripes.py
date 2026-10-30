"""A flag's stripes: equal art sews equal, and a square end sews square (2026-10-30).

Kent's Flag.webp at 96 mm: seven red and six white stripes, 4.05 mm each in the
art. Three faults, each a stripe-shaped case of something general:

* `cfg.satin_seam_hold`. The pull lands on satin rails in stage 6, after stage
  5's clip, so the last colour sewn kept all of it and laid it over the colour
  already down: white 4.53 mm, red's visible share 3.57 mm.
* `cfg.satin_cap_skew_inset`. A cap the raster traced 0.03 mm off true lost half
  its end cross, and with it one corner of every stripe.
* Stage 5's underlap counted the pull a second time on one stripe, whose tongue
  also left a slit in it, so that stripe split and sewed on a slant.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.prepared import prep

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import _push_rails, satin_shape

# The flag's fourth white stripe as stage 4 traced it, leaning 0.03 mm.
LEANING = Polygon([(-50.0, 2.02), (-49.97, 6.06), (49.97, 6.05), (49.95, 2.01)])
SQUARE = box(-50.0, 2.0, 50.0, 6.0)


def _end_crosses(poly, **kw):
    runs, _ = satin_shape(poly, "S", underlay_style="center_run", trim_at_mm=3.0,
                          end_cutback_mm=0.0, rail_comp_floor_mm=0.5, **kw)
    satin = next(r for r in runs if r.kind == "satin")
    return satin.points[:2], satin.points[-2:]


def _span(cross):
    return abs(cross[0][1] - cross[1][1])


def test_defaults_pin_both_flags():
    cfg = PipelineConfig()
    assert cfg.satin_seam_hold is False
    assert cfg.satin_cap_skew_inset is False


def test_a_leaning_cap_loses_half_its_end_cross_without_the_inset():
    first, last = _end_crosses(LEANING)
    assert min(_span(first), _span(last)) < 2.5


def test_a_leaning_cap_keeps_its_whole_end_cross_with_the_inset():
    first, last = _end_crosses(LEANING, cap_skew_inset=True)
    assert _span(first) > 3.8
    assert _span(last) > 3.8


def test_the_full_end_cross_takes_the_pull_too():
    first, last = _end_crosses(LEANING, cap_skew_inset=True, rail_comp_mm=0.3)
    assert _span(first) > 4.3
    assert _span(last) > 4.3


def test_the_inset_leaves_a_true_cap_where_it_was():
    plain = _end_crosses(SQUARE)
    inset = _end_crosses(SQUARE, cap_skew_inset=True)
    assert inset[0][0][0] == pytest.approx(plain[0][0][0], abs=0.031)
    assert inset[1][0][0] == pytest.approx(plain[1][0][0], abs=0.031)


def test_a_slanted_end_the_art_drew_is_not_a_lean():
    # 1 mm across the cap is a cut, not raster rounding: past `_CAP_SKEW_MAX_MM`.
    slant = Polygon([(-50.0, 2.0), (-49.0, 6.0), (50.0, 6.0), (49.0, 2.0)])
    assert _end_crosses(slant, cap_skew_inset=True) == _end_crosses(slant)


def _held(ground):
    return prep(ground.buffer(0.1)), ground


def test_a_rail_stops_at_the_colour_already_down():
    # a 4 mm cross with a red stripe below y=2: the far rail keeps its pull.
    poly = box(0, 2, 10, 6)
    a, b = _push_rails([(5.0, 6.0)], [(5.0, 2.0)], poly, 0.3, 0.5, held=_held(box(0, -2, 10, 2)))
    assert a[0][1] == pytest.approx(6.3)
    assert b[0][1] == pytest.approx(2.0)


def test_a_rail_short_of_the_seam_still_closes_the_gap():
    poly = box(0, 2, 10, 6)
    _, b = _push_rails([(5.0, 6.0)], [(5.0, 2.12)], poly, 0.3, 0.5, held=_held(box(0, -2, 10, 2)))
    assert b[0][1] == pytest.approx(2.0)


def test_a_thin_column_keeps_its_pull_at_a_seam():
    poly = box(0, 2, 10, 4)
    _, b = _push_rails([(5.0, 4.0)], [(5.0, 2.0)], poly, 0.3, 0.5, held=_held(box(0, -2, 10, 2)))
    assert b[0][1] == pytest.approx(1.7)


def test_nothing_held_pushes_both_rails():
    poly = box(0, 2, 10, 6)
    a, b = _push_rails([(5.0, 6.0)], [(5.0, 2.0)], poly, 0.3, 0.5)
    assert (a[0][1], b[0][1]) == (pytest.approx(6.3), pytest.approx(1.7))


# --- the whole pipeline, on stripes alone ------------------------------------

RED = (66, 25, 179)     # BGR, as an array reaches stage 0
GOLD = (40, 190, 240)
NAVY = (88, 40, 10)
STRIPES = 7
ROW_PX = 48  # 4 mm at 100 mm wide: satin, as the flag's 4.05 mm stripes are


@pytest.fixture(scope="module")
def stripes():
    """Opaque BGRA, as Flag.webp is, with its canton. Gold stands in for white:
    white on this fabric reads as bare garment, and the seam is the subject."""
    art = np.full((ROW_PX * STRIPES, 1200, 4), 255, np.uint8)
    for i in range(STRIPES):
        art[i * ROW_PX:(i + 1) * ROW_PX, :, :3] = RED if i % 2 == 0 else GOLD
    art[:ROW_PX * 4, :480, :3] = NAVY
    return art


def _sew(art, **flags):
    cfg = PipelineConfig(target_width_mm=100, forced_class="flat", edge_cap="none",
                         garment_id="left_chest", garment_rgb=(235, 232, 223), **flags)
    return digitize(art.copy(), cfg)[1]


def _last_colour_height(plan) -> float:
    """The last satin colour's sewn band, read on its rails: the median stripe
    between its 5th and 95th percentile needle, so one end stitch cannot set it."""
    block = [b for b in plan.blocks if any(r.kind == "satin" for r in b.runs)][-1]
    shapes: dict[str, list] = {}
    for run in block.runs:
        if run.kind == "satin":
            shapes.setdefault(run.shape_id, []).extend(p[1] for p in run.points)
    return float(np.median([np.percentile(v, 95) - np.percentile(v, 5)
                            for v in shapes.values()]))


def test_equal_stripes_sew_equal(stripes):
    """Off, the last colour sews a pull wider on each seam. On, it sews its art."""
    art_mm = 100.0 * ROW_PX / 1200
    assert _last_colour_height(_sew(stripes)) > art_mm + 0.35
    held = _sew(stripes, satin_seam_hold=True, satin_cap_skew_inset=True)
    assert _last_colour_height(held) == pytest.approx(art_mm, abs=0.1)
