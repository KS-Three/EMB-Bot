"""`cfg.rescue_needs_drawn_edge` (built OFF 2026-11-19): the contrast rescue
(`keep_thin_strokes`) also asks that the ARTWORK step across the region's
boundary. Doc: `docs/stage0-grain-needs-texture-2026-11-19.md` §7.

The arrays here check arithmetic only and calibrate nothing (ROADMAP gate 2):
the tolerance is `merge_delta_e`, the one the layer colours are compared on.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.threads import rgb_to_lab

from .conftest import ENGINE_2026_10_27

PX_PER_MM = 10.0
FRAME = (120, 120)
# Layer colours: a tan disc and a dark-brown blob, two different threads.
LAYER_RGB = np.array([(140, 110, 70), (102, 89, 76)], float)
BLOB = (slice(54, 66), slice(54, 66))   # 144 px: under the 225 px floor, over the run floors


def _masks() -> list[RegionMask]:
    disc = np.zeros(FRAME, bool)
    disc[10:110, 10:110] = True
    disc[BLOB] = False
    blob = np.zeros(FRAME, bool)
    blob[BLOB] = True
    return [RegionMask.from_full(disc, 0), RegionMask.from_full(blob, 1)]


def _drawn() -> np.ndarray:
    """The blob is DRAWN: its pixels are the dark thread, the disc's tan."""
    rgb = np.zeros(FRAME + (3,), np.uint8)
    rgb[:] = LAYER_RGB[0]
    rgb[BLOB] = LAYER_RGB[1]
    return rgb


def _shade() -> np.ndarray:
    """The blob is a SHADE: a smooth radial darkening, one or two levels a
    pixel, that the quantiser happened to cut at its darkest centre."""
    yy, xx = np.mgrid[0:FRAME[0], 0:FRAME[1]]
    r = np.hypot(yy - 59.5, xx - 59.5)
    rgb = LAYER_RGB[0] - np.clip(14.0 - r, 0, None)[..., None] * 1.0
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _kept(cfg, src) -> int:
    kept, _ = resolve_small_regions(_masks(), cfg, PX_PER_MM, None,
                                    layer_lab=rgb_to_lab(LAYER_RGB), src_rgb=src)
    return len(kept)


def test_the_flag_defaults_off():
    assert PipelineConfig().rescue_needs_drawn_edge is False


def test_the_frozen_snapshot_holds_the_off_value():
    assert ENGINE_2026_10_27["rescue_needs_drawn_edge"] is False


def test_the_layers_contrast_so_today_keeps_both():
    cfg = PipelineConfig()
    lab = rgb_to_lab(LAYER_RGB)
    assert np.linalg.norm(lab[1] - lab[0]) > cfg.merge_delta_e
    assert _kept(cfg, None) == 2


def test_a_drawn_blob_is_kept():
    assert _kept(PipelineConfig(rescue_needs_drawn_edge=True), _drawn()) == 2


def test_a_shaded_centre_goes_to_its_host():
    assert _kept(PipelineConfig(rescue_needs_drawn_edge=True), _shade()) == 1


def test_without_the_source_nothing_changes():
    """`src_rgb=None` is the OFF arm, byte-identical."""
    assert _kept(PipelineConfig(rescue_needs_drawn_edge=True), None) == 2
