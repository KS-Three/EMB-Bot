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
from digitizer_core.stage0_classify import classify
from digitizer_core.stage1_prep import prep
from tests.conftest import TESTDATA


def _stage1(rel: str) -> np.ndarray:
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6)
    c = classify(TESTDATA / rel, cfg)
    return prep(TESTDATA / rel, cfg, design_class=c.class_).rgb


@pytest.mark.parametrize("rel", [
    "art/logo_golke_roofing.png",
    "art/logo_mfab_lc.png",
    "art/logo_toat_beanie.png",
    "photo/logo_gaulke_roofing.png",
])
def test_black_and_white_logos_fire(rel):
    tt = two_tone.detect(_stage1(rel))
    assert tt is not None
    assert max(tt.dark) < 60 and min(tt.light) > 230


@pytest.mark.parametrize("rel", [
    # colour art whose ringing the per-region stroke rule repainted
    "photo/logo_bridge_bar.jpg",
    # achromatic, but its rope is a drawn grey: the plateau gate
    "photo/logo_hotel_fremont.webp",
    # the nearest refusal on the sweep (max mid bin 0.0109)
    "art/logo_hotel_fremont_patch.png",
    "photo/drone_render.png",
])
def test_everything_else_refuses(rel):
    assert two_tone.detect(_stage1(rel)) is None


def test_a_grey_plateau_refuses():
    """A drawn grey ink stacks in one bin; anti-alias grey does not."""
    img = np.full((100, 100, 3), 255, np.uint8)
    img[:40] = 0
    img[40:60, :20] = 128          # 4% of the pixels on one grey
    assert two_tone.detect(img) is None
    img[40:60, :20] = 255
    assert two_tone.detect(img) is not None


def test_snap_leaves_only_the_two_inks():
    # each anti-alias column is 0.5% of the pixels, under the plateau gate
    img = np.full((200, 200, 3), 250, np.uint8)
    img[:, :20] = 10
    img[:, 20] = 100               # anti-alias column, nearer dark
    img[:, 21] = 180               # nearer light
    tt = two_tone.detect(img)
    assert tt is not None
    out = two_tone.snap(img, tt)
    assert {tuple(v) for v in out.reshape(-1, 3)} == {tt.dark, tt.light}
    assert tuple(out[0, 20]) == tt.dark and tuple(out[0, 21]) == tt.light


def test_flag_off_by_default():
    assert PipelineConfig().two_tone_snap is False
