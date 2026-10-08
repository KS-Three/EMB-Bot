"""`two_tone` (defect 58): the per-IMAGE gate that snaps a black-and-white
logo's anti-alias grey to its two inks.

The detector's constants were set on the real-art fixtures
(`tools/two_tone_probe.py --detect`, 2026-10-08); these tests pin that
reading on the files the cases were decided on, plus the snap's contract.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import two_tone
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import build_generation
from digitizer_core.stage0_classify import classify
from digitizer_core.stage1_prep import prep
from tests.conftest import TESTDATA


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6, **kw)


def _stage1(rel: str):
    cfg = _cfg()
    c = classify(TESTDATA / rel, cfg)
    p = prep(TESTDATA / rel, cfg, design_class=c.class_)
    return p.rgb, ~p.bg_mask


@pytest.mark.parametrize("rel", [
    "art/logo_golke_roofing.png",
    "art/logo_mfab_lc.png",
    "art/logo_toat_beanie.png",
    # the closest pass on the sweep (plateau 1.92)
    "photo/logo_gaulke_roofing.png",
])
def test_black_and_white_logos_fire(rel):
    tt = two_tone.detect(*_stage1(rel))
    assert tt is not None
    assert max(tt.dark) < 60 and min(tt.light) > 230


@pytest.mark.parametrize("rel", [
    # colour art whose ringing the per-region stroke rule repainted
    "photo/logo_bridge_bar.jpg",
    # achromatic, but its rope is a drawn grey: the plateau gate (14.3)
    "photo/logo_hotel_fremont.webp",
    # the closest refusal on the sweep (plateau 2.34)
    "art/logo_hotel_fremont_patch.png",
    "photo/drone_render.png",
])
def test_everything_else_refuses(rel):
    assert two_tone.detect(*_stage1(rel)) is None


def test_a_grey_plateau_refuses():
    """A drawn grey ink stacks in one bin; anti-alias grey spreads evenly."""
    img = np.full((100, 100, 3), 255, np.uint8)
    img[:40] = 0
    img[40:60, :] = np.linspace(30, 225, 100).astype(np.uint8)[None, :, None]
    assert two_tone.detect(img) is not None
    img[60:70, :20] = 128          # a block of one drawn grey on top of the ramp
    assert two_tone.detect(img) is None


def test_one_ink_refuses():
    """A white logo on transparency arrives with no dark half at all."""
    img = np.full((60, 60, 3), 250, np.uint8)
    img[20:40, 20:40] = 200
    assert two_tone.detect(img) is None


def test_snap_leaves_only_the_two_inks():
    # an even anti-alias ramp between the inks, one grey per column
    img = np.full((200, 200, 3), 250, np.uint8)
    img[:, :20] = 10
    img[:, 20:40] = np.linspace(22, 238, 20).astype(np.uint8)[None, :, None]
    tt = two_tone.detect(img)
    assert tt is not None
    out = two_tone.snap(img, tt)
    assert {tuple(v) for v in out.reshape(-1, 3)} == {tt.dark, tt.light}
    assert tuple(out[0, 25]) == tt.dark and tuple(out[0, 34]) == tt.light


def test_fold_fringe_hands_the_outer_halo_to_the_background():
    """Background-coloured ink touching the background joins it; the same
    ink enclosed by the other ink does not."""
    tt = two_tone.TwoTone(dark=(0, 0, 0), light=(255, 255, 255), dark_grey=0,
                          light_grey=255, mid_frac=0.0, plateau=1.0)
    snapped = np.full((40, 40, 3), 255, np.uint8)
    snapped[10:30, 10:30] = 0
    snapped[18:22, 18:22] = 255    # an enclosed counter
    bg = np.zeros((40, 40), bool)
    bg[:8], bg[32:], bg[:, :8], bg[:, 32:] = True, True, True, True
    out = two_tone.fold_fringe(snapped, tt, bg, (255, 255, 255))
    assert out[9, 9] and out[9, 20]           # the fringe ring at 8..9 joined
    assert not out[20, 20]                    # the counter did not
    assert not out[15, 15]                    # nor the ink
    # unknown background colour (alpha cutout): nothing moves
    assert (two_tone.fold_fringe(snapped, tt, bg, None) == bg).all()


def test_white_logo_on_transparency_runs_with_the_flag_on():
    """The reviewer's crash (2026-10-08): `alpha_edge_extend` paints the
    transparent area with the nearest ink, so a white logo on alpha is an
    all-light raster and the dark mode came from an empty half."""
    rgba = np.zeros((120, 240, 4), np.uint8)
    rgba[..., :3] = 255
    rgba[30:90, 30:210, 3] = 255
    gen = build_generation(rgba, _cfg(two_tone_snap=True))
    assert gen is not None


def test_flag_on_by_default():
    """Kent's flip 2026-10-08, after `keep_lines` cured golke's roof lines."""
    assert PipelineConfig().two_tone_snap is True


def _snapped_stage1(rel: str):
    cfg = _cfg()
    c = classify(TESTDATA / rel, cfg)
    p = prep(TESTDATA / rel, cfg, design_class=c.class_)
    tt = two_tone.detect(p.rgb, ~p.bg_mask)
    assert tt is not None
    snapped = two_tone.snap(p.rgb, tt)
    bg = two_tone.fold_fringe(snapped, tt, p.bg_mask, p.bg_rgb)
    return p, bg


def test_golke_roof_lines_are_kept_as_lines():
    """The roof chevron, the window cross and the zigzag under the sun are
    white lines drawn between black shapes. Snapped, the flood and the fold
    took them, and they sewed as one black mass (2026-10-08). `keep_lines`
    hands them back; the lettering's gaps stay background."""
    import cv2

    p, bg = _snapped_stage1("art/logo_golke_roofing.png")
    lines = two_tone.keep_lines(bg, p.px_per_mm)
    n, lab, st, _ = cv2.connectedComponentsWithStats(lines.astype(np.uint8), connectivity=8)
    spans = sorted((st[i, cv2.CC_STAT_WIDTH] / p.px_per_mm for i in range(1, n)), reverse=True)
    # the chevron runs ~40 mm across; the window cross and two zigzag halves follow
    assert spans and spans[0] > 35.0
    assert len(spans) >= 4
    # nothing in the lettering (the two text rows sit below the roof's base)
    ys = np.nonzero(lines)[0]
    text_top = int(0.71 * lines.shape[0])
    assert ys.max() < text_top


@pytest.mark.parametrize("rel", [
    "art/logo_mfab_lc.png",
    "art/logo_mfab_hat.png",
    "art/logo_toat_machine.png",
    "art/logo_toat_beanie.png",
])
def test_no_line_where_the_art_draws_none(rel):
    p, bg = _snapped_stage1(rel)
    assert not two_tone.keep_lines(bg, p.px_per_mm).any()


def test_keep_lines_takes_a_long_channel_not_a_short_gap():
    """Synthetic, at 8 px/mm: a 0.25 mm channel 20 mm long between two
    black slabs is a line; a 0.5 mm gap 4 mm tall between two letters is not."""
    ppmm = 8.0
    bg = np.ones((200, 400), bool)
    bg[40:80, 40:360] = False      # upper slab
    bg[82:122, 40:360] = False     # lower slab; rows 80-81 are the channel
    bg[150:182, 40:100] = False    # letter one
    bg[150:182, 104:160] = False   # letter two; columns 100-103 are the gap
    lines = two_tone.keep_lines(bg, ppmm)
    assert lines[80, 200] and lines[81, 200]
    assert not lines[166, 101]
    # widened to the satin floor along its centre line, into the slabs
    from digitizer_core.machine import SATIN_MIN_CROSS_MM
    assert lines[:, 200].sum() >= SATIN_MIN_CROSS_MM * ppmm


def test_golke_roof_sews_white_with_the_flag_on():
    """End to end: the roof lines reach the stitch plan in the light ink.
    The fold alone left 117 white stitches (2026-10-08), the roof as a mass."""
    from tools.eye_pairs.features import base_cfg, digitize_once
    from tools.stroke_colour_probe import _blocks

    *_, design = digitize_once(TESTDATA / "art/logo_golke_roofing.png",
                               base_cfg(80.0, "left_chest", two_tone_snap=True))
    white = sum(n for c, n in _blocks(design) if c.lower() == "#ffffff")
    assert white > 400
