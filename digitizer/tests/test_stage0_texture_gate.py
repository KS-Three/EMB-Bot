"""Stage 0's texture route and two-ink veto (`cfg.stage0_texture_gate`).

Spec: `docs/superpowers/specs/2026-10-28-stage0-photo-texture-gate-design.md`.
Every fixture reading pinned here is an instrument reading on a real file,
not a quality claim (ROADMAP gate 4); the arrays built in-line check
arithmetic only and calibrate nothing (gate 2).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digitizer_core.config import PipelineConfig

from .conftest import ENGINE_2026_10_27

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"


def cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- Task 1: the flag ----------------------------------------------------------

def test_the_flag_defaults_on():
    assert PipelineConfig().stage0_texture_gate is True


def test_the_frozen_snapshot_holds_the_pre_flip_value():
    """A pin built on the dated engine must not ride this flip
    (`tests/test_pins_are_frozen.py`, rule 2)."""
    assert ENGINE_2026_10_27["stage0_texture_gate"] is False


# --- Task 2: the signals ------------------------------------------------------

from digitizer_core import stage0_classify as s0  # noqa: E402


def _ones(h, w):
    return np.ones((h, w), bool)


def test_texture_frac_is_zero_on_a_flat_field():
    rgb = np.full((300, 400, 3), 120, np.uint8)
    assert s0._texture_frac(rgb, _ones(300, 400)) == 0.0


def test_texture_frac_is_near_one_on_broadband_noise():
    rng = np.random.default_rng(0)
    rgb = rng.integers(100, 140, (300, 400, 3)).astype(np.uint8)
    assert s0._texture_frac(rgb, _ones(300, 400)) > 0.95


def test_texture_frac_ignores_a_hard_edge():
    rgb = np.zeros((300, 400, 3), np.uint8)
    rgb[:, 200:] = 255
    assert s0._texture_frac(rgb, _ones(300, 400)) < 0.03


def test_texture_frac_reads_the_long_edge_down_to_512():
    """A 2000-px file and its own INTER_AREA 512-px version read the same
    number: the signal is taken on the normalised raster."""
    import cv2
    rng = np.random.default_rng(1)
    big = rng.integers(60, 200, (1000, 2000, 3)).astype(np.uint8)
    big = cv2.GaussianBlur(big, (0, 0), 3)
    small = cv2.resize(big, (512, 256), interpolation=cv2.INTER_AREA)
    a = s0._texture_frac(big, _ones(1000, 2000))
    b = s0._texture_frac(small, _ones(256, 512))
    assert a == pytest.approx(b, abs=0.05)
    assert 0.2 < a < 1.0


def test_texture_frac_reads_a_small_file_as_it_is():
    """`photo/logo_bridge_bar.jpg` is 400 px wide: under the 512 norm, so the
    reading is the raw array's (no upscale)."""
    rgb, alpha = s0._load(str(PHOTO_DIR / "logo_bridge_bar.jpg"))
    fg = s0._fg_mask(rgb, alpha)
    assert rgb.shape[1] == 400
    assert s0._texture_frac(rgb, fg) == s0._texture_frac(rgb.copy(), fg.copy())
    assert s0.TEXTURE_NORM_PX == 512


def test_two_tone_mass_on_ink_and_paper():
    rgb = np.full((100, 100, 3), 250, np.uint8)
    rgb[20:40] = 10
    assert s0._two_tone_mass(rgb, _ones(100, 100)) == pytest.approx(1.0)


def test_two_tone_mass_on_a_ramp():
    ramp = np.linspace(0, 255, 256).astype(np.uint8)
    rgb = np.repeat(ramp[None, :, None], 3, axis=2).repeat(10, axis=0)
    assert s0._two_tone_mass(rgb, _ones(10, 256)) == pytest.approx(2 / 16, abs=0.01)


def test_empty_foreground_reads_zero():
    rgb = np.full((300, 400, 3), 120, np.uint8)
    none = np.zeros((300, 400), bool)
    assert s0._texture_frac(rgb, none) == 0.0
    assert s0._two_tone_mass(rgb, none) == 0.0
    tiny = np.zeros((300, 400), bool)
    tiny[0, :10] = True
    assert s0._texture_frac(rgb, tiny) == 0.0


@pytest.mark.parametrize("alpha,expected", [
    (None, False),
    (np.full((4, 4), 255, np.uint8), False),
    (np.array([[255, 0], [255, 255]], np.uint8), True),
    (np.array([[255, 127], [255, 255]], np.uint8), True),
    (np.array([[255, 128], [255, 255]], np.uint8), False),
])
def test_has_cutout(alpha, expected):
    assert s0._has_cutout(alpha) is expected


def test_an_LA_png_hands_its_alpha_to_the_cutout_test(tmp_path):
    from PIL import Image
    im = Image.new("LA", (8, 8), (200, 255))
    im.putpixel((0, 0), (200, 0))
    path = tmp_path / "la.png"
    im.save(path)
    rgb, alpha = s0._load(str(path))
    assert rgb.shape == (8, 8, 3) and alpha is not None
    assert s0._has_cutout(alpha) is True


@pytest.mark.parametrize("rel,lo,hi", [
    ("photo/owl_kent.jpg", 0.40, 0.55),
    ("logo_script_tires.png", 0.0, 0.05),
    ("logo_whitebg.png", 0.0, 0.05),
    ("photo/summit_badge.png", 0.0, 0.10),
])
def test_texture_readings_on_real_fixtures(rel, lo, hi):
    """Readings (2026-10-28): owl 0.459, tires 0.015, whitebg 0.015, summit
    0.059 — the real photograph against three designed logos."""
    rgb, alpha = s0._load(str(TESTDATA / rel))
    v = s0._texture_frac(rgb, s0._fg_mask(rgb, alpha))
    assert lo <= v <= hi, (rel, v)


@pytest.mark.parametrize("rel,lo,hi", [
    ("logo_script_tires.png", 0.95, 1.0),
    ("photo/owl_kent.jpg", 0.30, 0.45),
])
def test_two_tone_readings_on_real_fixtures(rel, lo, hi):
    """Readings (2026-10-28): tires 0.995 (two inks), owl 0.357."""
    rgb, alpha = s0._load(str(TESTDATA / rel))
    v = s0._two_tone_mass(rgb, s0._fg_mask(rgb, alpha))
    assert lo <= v <= hi, (rel, v)
