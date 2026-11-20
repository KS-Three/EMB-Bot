"""The alpha edge extension — stage 1 stops reading the RGB under an alpha
cutout's transparency (built OFF 2026-09-20, Kent's pick on the census;
flipped ON the same day, gated on the resolution-floor upscale — Kent's
pick after the census's four arms; folded into the engine, the three
`alpha_edge_extend*` switches are retired).

The shape of an alpha cutout lives in alpha; the RGB under its transparency
is whatever the exporter or a browser canvas left there, and stage 1's two
filters — the bilateral denoise and the Lanczos resolution-floor upscale —
blur that colour into the edge pixels the design then sews. Measured
2026-09-20 on Becker: the file (one colour everywhere) reads flat / 18
regions / 8,334 stitches / 59 trims, the same alpha with black underneath
gradient / 151 / 15,318 / 175. Every stage reads nearest-opaque colour
under every non-opaque pixel instead — every stage, because stage 0's
gradient signal and stage 2's segmentation run kernels over the whole raster
and mask afterwards (a first cut that put the file's own colour back under
alpha < 128 after the filters left Becker-with-black-underneath at gradient
/ 146 regions) — while the two readers that want the file's own colour
there, `bg_edge_rgb` and preflight's `GROUND_SEWN` border colour, read it
from `Prep.raw_rgb`; the naive whole-image fill that gave them the extended
colour sewed Fremont's ground (scope-history 2026-09-20 §E).

Pinned: the extension runs gated on the upscale with no halo; the helper's
contract; on a synthetic cutout with a real alpha ramp, under the floor so the
upscale runs, the under-alpha colour does not reach the sewn edge (the two
exporters read the same), while the background side still reads each file's
own colour; above the floor the gate is shut and nothing runs.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage1_prep as s1


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


def test_the_under_alpha_colour_stops_reaching_the_sewn_edge():
    # 48 px at 30 mm = 1.6 px/mm: under the 4 px/mm floor, so the Lanczos
    # upscale runs, as it does on Becker — and so the shipped gate opens.
    cfg = PipelineConfig(target_width_mm=30.0)
    friendly = s1.prep(_cutout((180, 30, 30)), cfg)      # the exporter left the ink colour underneath
    hostile = s1.prep(_cutout((0, 0, 0)), cfg)           # a canvas left black
    assert friendly.bg_from_alpha and hostile.bg_from_alpha
    assert friendly.rgb.shape == hostile.rgb.shape
    diff = np.abs(friendly.rgb.astype(int) - hostile.rgb.astype(int)).max(axis=2)
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


def test_an_opaque_image_is_untouched():
    """No alpha, or an alpha with nothing non-opaque: the extension does not
    run (no raw raster is kept)."""
    rgb = np.zeros((40, 40, 3), np.uint8); rgb[10:30, 10:30] = (30, 30, 200)
    assert s1.prep(rgb, PipelineConfig(target_width_mm=20.0)).raw_rgb is None


def test_the_halo_extends_only_within_reach_of_the_edge_and_leaves_a_deeper_backdrop_alone():
    """`alpha_edge_extend_px`: within N source px of the opaque edge the fill
    is the nearest opaque colour; further under the alpha the file's own
    colour stays (drone's render backdrop, which its photo lane wants)."""
    rgb = np.zeros((20, 20, 3), np.uint8); rgb[...] = (7, 8, 9)          # the backdrop the exporter left
    alpha = np.zeros((20, 20), np.uint8); alpha[8:12, 8:12] = 255
    rgb[8:12, 8:12] = (200, 100, 50)
    out = s1.extend_opaque_colour(rgb, alpha, max_px=2)
    assert tuple(out[7, 9]) == (200, 100, 50) and tuple(out[6, 9]) == (200, 100, 50)   # 1 and 2 px out: extended
    assert tuple(out[5, 9]) == (7, 8, 9) and tuple(out[0, 0]) == (7, 8, 9)               # beyond the halo: the file's own
    assert np.array_equal(out[8:12, 8:12], rgb[8:12, 8:12])
    everywhere = s1.extend_opaque_colour(rgb, alpha, max_px=0)
    assert tuple(everywhere[0, 0]) == (200, 100, 50)
    assert PipelineConfig().alpha_edge_extend_px == 0


@pytest.mark.usefixtures("source_line_grid")
def test_gated_on_the_upscale_the_extension_runs_under_the_floor_and_not_above_it():
    """The upscale gate (Kent's pick, 2026-09-20, and the form he flipped ON):
    the extension only where stage 1 will upscale — the one place black under
    the alpha was measured to bite. Both stages decide from
    `alpha_edge.upscale_expected`, the floor test on the alpha >= 128 box."""
    from digitizer_core.alpha_edge import upscale_expected
    friendly, hostile = _cutout((180, 30, 30)), _cutout((0, 0, 0))
    a = friendly[..., 3]
    assert upscale_expected(a, 30.0, 4.0) is True        # 30 px of art at 30 mm: 1 px/mm, under the floor
    assert upscale_expected(a, 5.0, 4.0) is False        # the same art at 5 mm: 6 px/mm, above it
    assert upscale_expected(np.zeros((4, 4), np.uint8), 30.0, 4.0) is False
    # Under the floor: the gate opens and the two exporters read the same.
    lo_f, lo_h = s1.prep(friendly, PipelineConfig(target_width_mm=30.0)), s1.prep(hostile, PipelineConfig(target_width_mm=30.0))
    assert lo_f.raw_rgb is not None and np.array_equal(lo_f.rgb, lo_h.rgb)
    # Above the floor: nothing runs, and the two exporters go on reading
    # differently, as they did before.
    hi_f = s1.prep(friendly, PipelineConfig(target_width_mm=5.0))
    hi_h = s1.prep(hostile, PipelineConfig(target_width_mm=5.0))
    assert hi_f.raw_rgb is None
    assert not np.array_equal(hi_f.rgb, hi_h.rgb)


@pytest.mark.usefixtures("source_line_grid")
def test_stage_0_reads_the_whole_image_extension_above_the_floor_while_stage_1_keeps_the_gate():
    """Stage 0 reads the whole-image extension (Kent's pick 2026-09-20): above
    the resolution floor, where stage 1's gate is shut, stage 0 still
    classifies the friendly and the hostile cutout the same — while stage 1
    keeps its gate and runs no extension there."""
    from digitizer_core import stage0_classify as s0
    friendly, hostile = _cutout((180, 30, 30)), _cutout((0, 0, 0))
    # 48 px of image at 5 mm: 9.6 px/mm, above the floor — the gate is shut.
    shipped = PipelineConfig(target_width_mm=5.0)
    a, b = s0.classify(friendly, shipped), s0.classify(hostile, shipped)
    assert (a.class_, a.signals) == (b.class_, b.signals)
    # Stage 1 above the floor: the gate is shut, no extension runs.
    assert s1.prep(hostile, shipped).raw_rgb is None
