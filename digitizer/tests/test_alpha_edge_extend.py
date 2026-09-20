"""`cfg.alpha_edge_extend` — stage 1 stops reading the RGB under an alpha
cutout's transparency (built OFF 2026-09-20, Kent's pick on the census).

The shape of an alpha cutout lives in alpha; the RGB under its transparency
is whatever the exporter or a browser canvas left there, and stage 1's two
filters — the bilateral denoise and the Lanczos resolution-floor upscale —
blur that colour into the edge pixels the design then sews. Measured
2026-09-20 on Becker: the file (one colour everywhere) reads flat / 18
regions / 8,334 stitches / 59 trims, the same alpha with black underneath
gradient / 151 / 15,318 / 175. ON, every stage reads nearest-opaque colour
under every non-opaque pixel instead — every stage, because stage 0's
gradient signal and stage 2's segmentation run kernels over the whole raster
and mask afterwards (a first cut that put the file's own colour back under
alpha < 128 after the filters left Becker-with-black-underneath at gradient
/ 146 regions) — while the two readers that want the file's own colour
there, `bg_edge_rgb` and preflight's `GROUND_SEWN` border colour, read it
from `Prep.raw_rgb`; the naive whole-image fill that gave them the extended
colour sewed Fremont's ground (scope-history 2026-09-20 §E).

Pinned: the default is OFF and OFF is the shipped path; the helper's
contract; on a synthetic cutout with a real alpha ramp, under the floor so
the upscale runs, OFF leaks the under-alpha colour into the sewn edge (the
two exporters read differently) and ON does not (they read the same), while
the background side still reads each file's own colour.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage1_prep as s1


def test_the_default_is_off():
    assert PipelineConfig().alpha_edge_extend is False


def test_the_helper_extends_nearest_opaque_colour_and_touches_nothing_else():
    rgb = np.zeros((4, 6, 3), np.uint8)
    rgb[:, :3] = (10, 20, 30)
    rgb[:, 3:] = (200, 210, 220)
    alpha = np.full((4, 6), 255, np.uint8)
    alpha[0, :] = 0                      # a transparent row the exporter left black
    rgb[0, :] = 0
    alpha[1, 2] = 128                    # one noisy semi-transparent pixel
    rgb[1, 2] = (99, 99, 99)
    out = s1.extend_opaque_colour(rgb, alpha)
    assert out is not rgb and np.array_equal(rgb[1, 2], (99, 99, 99))          # input untouched
    assert tuple(out[0, 0]) == (10, 20, 30) and tuple(out[0, 5]) == (200, 210, 220)
    assert tuple(out[1, 2]) == (10, 20, 30)
    opaque = alpha == 255
    assert np.array_equal(out[opaque], rgb[opaque])
    # Nothing to extend from, or nothing to extend into: the input itself.
    assert s1.extend_opaque_colour(rgb, np.full((4, 6), 255, np.uint8)) is rgb
    assert s1.extend_opaque_colour(rgb, np.zeros((4, 6), np.uint8)) is rgb


def _cutout(under_rgb, size=48, ramp=3):
    """An RGBA square with an alpha ramp at its edge; the RGB under the
    non-opaque pixels is `under_rgb` — the exporter's choice."""
    a = np.zeros((size, size), np.uint8)
    lo, hi = size // 4, size - size // 4
    a[lo:hi, lo:hi] = 255
    for i in range(1, ramp + 1):
        a[lo - i:hi + i, lo - i:hi + i] = np.maximum(a[lo - i:hi + i, lo - i:hi + i], int(255 * (ramp + 1 - i) / (ramp + 1)))
    a[lo:hi, lo:hi] = 255
    rgb = np.empty((size, size, 3), np.uint8)
    rgb[...] = under_rgb
    rgb[a == 255] = (180, 30, 30)
    return np.dstack([cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR), a])


@pytest.mark.parametrize("extend", [False, True])
def test_on_the_under_alpha_colour_stops_reaching_the_sewn_edge_and_off_it_still_does(extend):
    # 48 px at 30 mm = 1.6 px/mm: under the 4 px/mm floor, so the Lanczos
    # upscale runs, as it does on Becker.
    cfg = PipelineConfig(target_width_mm=30.0, alpha_edge_extend=extend)
    friendly = s1.prep(_cutout((180, 30, 30)), cfg)      # the exporter left the ink colour underneath
    hostile = s1.prep(_cutout((0, 0, 0)), cfg)           # a canvas left black
    assert friendly.bg_from_alpha and hostile.bg_from_alpha
    assert friendly.rgb.shape == hostile.rgb.shape
    sewn = ~friendly.bg_mask
    diff = np.abs(friendly.rgb.astype(int) - hostile.rgb.astype(int)).max(axis=2)
    if extend:
        # Every pixel any stage reads is the same whatever sat under the
        # alpha — the sewn ones and the extended background alike...
        assert diff.max() == 0, int(diff.max())
        # ...while the two readers that want the file's own colour under the
        # transparency still get it: the anti-alias endpoint and the raw
        # raster preflight reads its border colour from.
        assert tuple(np.round(friendly.bg_edge_rgb).astype(int)) != tuple(np.round(hostile.bg_edge_rgb).astype(int))
        assert friendly.raw_rgb is not None and hostile.raw_rgb is not None
        raw_diff = np.abs(friendly.raw_rgb.astype(int) - hostile.raw_rgb.astype(int)).max(axis=2)
        assert raw_diff[friendly.bg_mask].max() > 20
    else:
        assert friendly.raw_rgb is None and hostile.raw_rgb is None
        # The shipped path: black under the alpha darkens the sewn edge.
        assert diff[sewn].max() > 20, int(diff[sewn].max())


def test_off_is_the_shipped_path_and_an_opaque_image_is_untouched_on():
    """No alpha, or an alpha with nothing non-opaque: ON changes nothing."""
    rgb = np.zeros((40, 40, 3), np.uint8); rgb[10:30, 10:30] = (30, 30, 200)
    a = s1.prep(rgb, PipelineConfig(target_width_mm=20.0)).rgb
    b = s1.prep(rgb, PipelineConfig(target_width_mm=20.0, alpha_edge_extend=True)).rgb
    assert np.array_equal(a, b)
