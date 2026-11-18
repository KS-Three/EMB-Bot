"""`cfg.light_thin_stroke_keep`: a thin light highlight on a dark shape is not a sliver of it.

Precision Drone (2026-11-18): the lower-left propeller's silver highlight is its own
stage-2 region (8 mm long, ~0.2 mm wide, L 66) and the photo lane's area floor absorbed it
into the black beside it, so highlight and dark edges sewed as one black slab. ON, a
sub-floor region that clears the run floors, is long and thin, and is much lighter than
the region it would join, is kept for the run tier. Photo lane only (no layer colours).
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions

PX_PER_MM = 12.0
FRAME = (300, 300)
BLACK_LAB, SILVER_LAB, DARKGREY_LAB = (8.0, 0.0, 0.0), (66.0, 0.0, 0.0), (28.0, 0.0, 0.0)


def _scene(bar_lab, bar_rows=slice(100, 103), bar_cols=slice(60, 160)):
    """A 200 x 200 px black panel with a 3 x 100 px bar cut into it (300 px: under the
    detail floor, over the run floors) and a Lab image that paints the bar `bar_lab`."""
    bar = np.zeros(FRAME, bool); bar[bar_rows, bar_cols] = True
    panel = np.zeros(FRAME, bool); panel[50:250, 50:250] = True; panel &= ~bar
    lab = np.zeros(FRAME + (3,)); lab[:] = BLACK_LAB; lab[bar] = bar_lab
    return [RegionMask.from_full(panel, 0), RegionMask.from_full(bar, 0)], lab


def _run(regions, lab, **flags):
    cfg = PipelineConfig(**flags)
    return resolve_small_regions(regions, cfg, PX_PER_MM, chain_rescue=False, lab_img=lab)[0]


def test_default_is_off():
    assert PipelineConfig().light_thin_stroke_keep is False


def test_off_the_highlight_is_absorbed_into_the_black():
    regions, lab = _scene(SILVER_LAB)
    assert len(_run(regions, lab)) == 1


def test_on_a_long_thin_light_bar_is_kept_as_its_own_region():
    regions, lab = _scene(SILVER_LAB)
    kept = _run(regions, lab, light_thin_stroke_keep=True)
    assert sorted(r.area for r in kept) == [300, 200 * 200 - 300]


def test_on_a_dark_grey_bar_is_not_kept():
    regions, lab = _scene(DARKGREY_LAB)          # 20 L lighter: under the 30 gate
    assert len(_run(regions, lab, light_thin_stroke_keep=True)) == 1


def test_on_a_fat_light_patch_is_not_kept():
    regions, lab = _scene(SILVER_LAB, bar_rows=slice(100, 120), bar_cols=slice(60, 75))   # 15 x 20, round
    assert len(_run(regions, lab, light_thin_stroke_keep=True)) == 1


def test_on_a_light_speck_under_the_run_floors_is_not_kept():
    regions, lab = _scene(SILVER_LAB, bar_rows=slice(100, 101), bar_cols=slice(60, 64))
    assert len(_run(regions, lab, light_thin_stroke_keep=True)) == 1


def test_on_without_raster_colours_it_is_inert():
    regions, _lab = _scene(SILVER_LAB)
    cfg = PipelineConfig(light_thin_stroke_keep=True)
    assert len(resolve_small_regions(regions, cfg, PX_PER_MM, chain_rescue=False)[0]) == 1
