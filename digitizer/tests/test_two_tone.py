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


def test_flag_off_by_default():
    assert PipelineConfig().two_tone_snap is False
