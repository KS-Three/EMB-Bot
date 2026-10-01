"""`cfg.alpha_edge_extend` — stage 1 stops reading the RGB under an alpha
cutout's transparency (built OFF 2026-09-20, Kent's pick on the census;
flipped ON the same day, gated on the resolution-floor upscale — Kent's
pick after the census's four arms).

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

Pinned: the default is ON in the gated form (`alpha_edge_extend_upscaled_only`)
with no halo, and OFF is the pre-flip engine; the helper's contract; on a
synthetic cutout with a real alpha ramp, under the floor so the upscale runs,
OFF leaks the under-alpha colour into the sewn edge (the two exporters read
differently) and ON does not (they read the same), while the background side
still reads each file's own colour; above the floor the gate is shut and the
shipped engine is byte-identical to OFF.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage1_prep as s1


def test_the_default_is_on_gated_on_the_upscale_with_no_halo():
    # Kent's flip 2026-09-20, after the census: the whole-image form cost the
    # friendly files (ENTHUSIAST +5 trims, drone +33, Fremont +78 mm of
    # exposed travel); the gated form was measured byte-identical to OFF
    # everywhere the upscale does not run and the cure where it does.
    cfg = PipelineConfig()
    assert cfg.alpha_edge_extend is True
    assert cfg.alpha_edge_extend_upscaled_only is True
    assert cfg.alpha_edge_extend_px == 0


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
    # upscale runs, as it does on Becker — and so the shipped gate opens.
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
        # The pre-flip engine: black under the alpha darkens the sewn edge.
        assert diff[sewn].max() > 20, int(diff[sewn].max())


def test_an_opaque_image_is_untouched_on():
    """No alpha, or an alpha with nothing non-opaque: ON changes nothing —
    the shipped engine and the pre-flip one read an opaque file the same."""
    rgb = np.zeros((40, 40, 3), np.uint8); rgb[10:30, 10:30] = (30, 30, 200)
    a = s1.prep(rgb, PipelineConfig(target_width_mm=20.0, alpha_edge_extend=False)).rgb
    b = s1.prep(rgb, PipelineConfig(target_width_mm=20.0)).rgb
    c = s1.prep(rgb, PipelineConfig(target_width_mm=20.0, alpha_edge_extend=True, alpha_edge_extend_upscaled_only=False)).rgb
    assert np.array_equal(a, b) and np.array_equal(a, c)


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


def test_gated_on_the_upscale_the_extension_runs_under_the_floor_and_not_above_it():
    """`alpha_edge_extend_upscaled_only` (Kent's pick, 2026-09-20, and the
    form he flipped ON): the extension only where stage 1 will upscale — the
    one place black under the alpha was measured to bite. Both stages decide
    from `alpha_edge.upscale_expected`, the floor test on the alpha >= 128
    box. The shipped defaults are this gate, so `PipelineConfig()` alone is
    the gated arm."""
    from digitizer_core.alpha_edge import upscale_expected
    assert PipelineConfig().alpha_edge_extend_upscaled_only is True
    friendly, hostile = _cutout((180, 30, 30)), _cutout((0, 0, 0))
    a = friendly[..., 3]
    assert upscale_expected(a, 30.0, 4.0) is True        # 30 px of art at 30 mm: 1 px/mm, under the floor
    assert upscale_expected(a, 5.0, 4.0) is False        # the same art at 5 mm: 6 px/mm, above it
    assert upscale_expected(np.zeros((4, 4), np.uint8), 30.0, 4.0) is False
    gated = dict(alpha_edge_extend=True, alpha_edge_extend_upscaled_only=True)
    # Under the floor: the gate opens and the two exporters read the same —
    # from the explicit gated arm and from the bare defaults alike.
    lo_f, lo_h = s1.prep(friendly, PipelineConfig(target_width_mm=30.0, **gated)), s1.prep(hostile, PipelineConfig(target_width_mm=30.0, **gated))
    assert lo_f.raw_rgb is not None and np.array_equal(lo_f.rgb, lo_h.rgb)
    assert np.array_equal(s1.prep(hostile, PipelineConfig(target_width_mm=30.0)).rgb, lo_f.rgb)
    # Above the floor: nothing runs — byte-identical to the pre-flip engine,
    # and the two exporters go on reading differently, as they did before.
    off_f = s1.prep(friendly, PipelineConfig(target_width_mm=5.0, alpha_edge_extend=False))
    hi_f = s1.prep(friendly, PipelineConfig(target_width_mm=5.0, **gated))
    hi_h = s1.prep(hostile, PipelineConfig(target_width_mm=5.0, **gated))
    assert hi_f.raw_rgb is None and np.array_equal(hi_f.rgb, off_f.rgb)
    assert not np.array_equal(hi_f.rgb, hi_h.rgb)


def test_stage_0_reads_the_whole_image_extension_above_the_floor_while_stage_1_keeps_the_gate():
    """`alpha_edge_extend_stage0_whole` (Kent's pick 2026-09-20, ON): above the
    resolution floor, where stage 1's gate is shut, stage 0 still classifies
    the friendly and the hostile cutout the same, and stops doing so with the
    flag off — while stage 1's raster stays byte-identical to the pre-flip
    engine there, whatever the flag says."""
    from digitizer_core import stage0_classify as s0
    assert PipelineConfig().alpha_edge_extend_stage0_whole is True
    friendly, hostile = _cutout((180, 30, 30)), _cutout((0, 0, 0))
    # 48 px of image at 5 mm: 9.6 px/mm, above the floor — the gate is shut.
    shipped = PipelineConfig(target_width_mm=5.0)
    a, b = s0.classify(friendly, shipped), s0.classify(hostile, shipped)
    assert (a.class_, a.signals) == (b.class_, b.signals)
    stage1_only = PipelineConfig(target_width_mm=5.0, alpha_edge_extend_stage0_whole=False)
    c, d = s0.classify(friendly, stage1_only), s0.classify(hostile, stage1_only)
    assert c.signals != d.signals
    # And the pre-flip engine reads the friendly file as the gated one does.
    off = PipelineConfig(target_width_mm=5.0, alpha_edge_extend=False)
    assert s0.classify(friendly, off).signals == c.signals
    # Stage 1 above the floor: byte-identical to OFF under both settings.
    p_off = s1.prep(hostile, off)
    for cfg in (shipped, stage1_only):
        p = s1.prep(hostile, cfg)
        assert p.raw_rgb is None and np.array_equal(p.rgb, p_off.rgb)
