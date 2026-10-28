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


# --- Task 3: the decision tree -------------------------------------------------

from digitizer_core.stage0_classify import classify, decide_photo  # noqa: E402

ALL_FIXTURES = sorted(
    [p for d in (TESTDATA, PHOTO_DIR) for p in d.iterdir()
     if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}],
)


def _old_tree(ucm: float, grad: float) -> tuple[str, float]:
    """The pre-2026-10-28 decision, restated locally from the constants."""
    photo_conf = s0._gate_confidence(ucm, s0.UCM_PHOTO_MIN, s0.UCM_MARGIN)
    if ucm >= s0.UCM_PHOTO_MIN:
        conf = min(photo_conf, s0._gate_confidence(grad, s0.GRAD_VAR_SUBJECT_MIN, s0.GRAD_VAR_SUBJECT_MARGIN))
        cls = "photo_subject" if grad >= s0.GRAD_VAR_SUBJECT_MIN else "photo_scene"
    else:
        conf = min(photo_conf, s0._gate_confidence(grad, s0.GRAD_VAR_GRADIENT_MIN, s0.GRAD_VAR_GRADIENT_MARGIN))
        cls = "gradient" if grad >= s0.GRAD_VAR_GRADIENT_MIN else "flat"
    if cls != "flat" and conf < s0.CONFIDENCE_FLOOR:
        cls = "flat"
    return cls, conf


@pytest.mark.parametrize("rel,on,off", [
    ("photo/owl_kent.jpg", "photo_scene", "gradient"),
    ("logo_script_tires.png", "gradient", "photo_scene"),
    ("photo/drone_render.png", "gradient", "gradient"),
    ("photo/enthusiast_logo.png", "flat", "flat"),
    ("photo/summit_badge.png", "gradient", "gradient"),
    ("photo/fur_ramp.png", "photo_scene", "photo_scene"),
    ("logo_whitebg.png", "flat", "flat"),
])
def test_class_under_both_arms(rel, on, off):
    p = TESTDATA / rel
    assert classify(p, cfg(stage0_texture_gate=True)).class_ == on
    assert classify(p, cfg(stage0_texture_gate=False)).class_ == off


def test_off_arm_is_byte_identical_to_the_old_tree_on_every_fixture():
    for p in ALL_FIXTURES:
        r = classify(p, cfg(stage0_texture_gate=False))
        cls, conf = _old_tree(r.signals["unique_color_mass"], r.signals["gradient_smoothness"])
        assert (r.class_, r.confidence) == (cls, conf), p.name


def test_the_signals_are_reported_under_both_arms():
    for on in (True, False):
        r = classify(PHOTO_DIR / "owl_kent.jpg", cfg(stage0_texture_gate=on))
        assert {"texture_frac", "two_tone_mass", "cutout_alpha", "photo_route"} <= set(r.signals)
        assert r.signals["cutout_alpha"] is False
    assert classify(PHOTO_DIR / "drone_render.png", cfg()).signals["cutout_alpha"] is True


def test_forced_class_reports_no_signals():
    assert classify(PHOTO_DIR / "owl_kent.jpg", cfg(), forced_class="flat").signals == {}


def test_routes_are_named():
    assert classify(PHOTO_DIR / "owl_kent.jpg", cfg()).signals["photo_route"] == "texture"
    assert classify(TESTDATA / "logo_script_tires.png", cfg()).signals["photo_route"] == "veto"
    assert classify(PHOTO_DIR / "drone_render.png", cfg()).signals["photo_route"] == "legacy"
    assert classify(PHOTO_DIR / "fur_ramp.png", cfg()).signals["photo_route"] == "grain"
    assert classify(TESTDATA / "logo_whitebg.png", cfg()).signals["photo_route"] == "none"
    assert classify(PHOTO_DIR / "owl_kent.jpg", cfg(stage0_texture_gate=False)).signals["photo_route"] == "legacy"


def test_a_photo_verdict_by_texture_carries_the_texture_gate_confidence():
    r = classify(PHOTO_DIR / "owl_kent.jpg", cfg())
    tex = r.signals["texture_frac"]
    expected = min(1.0, 0.5 + 0.5 * abs(tex - s0.TEXTURE_PHOTO_MIN) / s0.TEXTURE_MARGIN)
    sub = s0._gate_confidence(r.signals["gradient_smoothness"], s0.GRAD_VAR_SUBJECT_MIN, s0.GRAD_VAR_SUBJECT_MARGIN)
    assert r.confidence == pytest.approx(min(expected, sub))


def test_the_veto_decides_tires_confidence():
    r = classify(TESTDATA / "logo_script_tires.png", cfg())
    veto = s0._gate_confidence(r.signals["two_tone_mass"], s0.TWO_TONE_MAX, s0.TWO_TONE_MARGIN)
    grad = s0._gate_confidence(r.signals["gradient_smoothness"], s0.GRAD_VAR_GRADIENT_MIN, s0.GRAD_VAR_GRADIENT_MARGIN)
    assert r.confidence == pytest.approx(min(veto, grad))


def test_a_cutout_file_takes_the_whole_old_tree():
    on = classify(PHOTO_DIR / "drone_render.png", cfg(stage0_texture_gate=True))
    off = classify(PHOTO_DIR / "drone_render.png", cfg(stage0_texture_gate=False))
    assert (on.class_, on.confidence) == (off.class_, off.confidence)
    assert on.signals["photo_route"] == "legacy"


@pytest.mark.parametrize("ucm,tex,two,cut,on,want", [
    (0.1, 0.5, 0.3, False, True, (True, "texture")),
    (0.5, 0.01, 0.3, False, True, (True, "grain")),
    (0.5, 0.5, 0.3, False, True, (True, "grain+texture")),
    (0.5, 0.5, 0.95, False, True, (False, "veto")),
    (0.1, 0.01, 0.3, False, True, (False, "none")),
    (0.1, 0.5, 0.3, True, True, (False, "legacy")),
    (0.5, 0.5, 0.95, True, True, (True, "legacy")),
    (0.1, 0.5, 0.3, False, False, (False, "legacy")),
])
def test_decide_photo_table(ucm, tex, two, cut, on, want):
    is_photo, conf, route = decide_photo(ucm, tex, two, cut, on)
    assert (is_photo, route) == want
    assert 0.5 <= conf <= 1.0


def test_seed_sweep_warning_is_withheld_when_texture_decided(monkeypatch):
    """The sweep's crossings are about the grain gate; once the texture route
    decided, the seed cannot move the verdict. Signals still reported."""
    monkeypatch.setattr(s0, "_unique_color_mass", lambda rgb, fg, seed: 0.5 if seed % 2 else 0.1)
    r = classify(PHOTO_DIR / "owl_kent.jpg", cfg(stage0_seed_sweep=4))
    assert r.signals["unique_color_mass_gate_crossings"] == 2
    assert all(w["code"] != "CLASSIFICATION_SEED_UNSTABLE" for w in r.warnings)
    off = classify(PHOTO_DIR / "owl_kent.jpg", cfg(stage0_seed_sweep=4, stage0_texture_gate=False))
    assert any(w["code"] == "CLASSIFICATION_SEED_UNSTABLE" for w in off.warnings)


def test_debug_dump_lists_the_new_signals(tmp_path):
    classify(PHOTO_DIR / "owl_kent.jpg", cfg(debug_dir=str(tmp_path)))
    text = (tmp_path / "stage0_classification.txt").read_text(encoding="utf-8")
    assert "texture_frac:" in text and "two_tone_mass:" in text and "photo_route: 'texture'" in text
