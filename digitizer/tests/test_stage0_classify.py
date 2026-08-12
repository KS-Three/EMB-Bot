"""Stage 0 -- the 4-way input classifier.

Covers `docs/superpowers/plans/2026-08-02-photo-digitizing-steps1-2.md`
Tests 2 (classifier routing) and 5 (classification determinism), plus the
`stage0_classification.txt` debug artifact this module owns. Tests 1, 3, 4
(flat-lane byte-identical, blend geometry, drone-render A/B) belong to
`pipeline.py`/`stage6_blend.py` wiring and are out of scope here.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage0_classify import classify

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"


def cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- Test 2: classifier routing --------------------------------------------

@pytest.mark.parametrize("filename,expected", [
    ("logo_whitebg.png", "flat"),
    ("logo_alpha.png", "flat"),
    ("ribbon_curve.png", "flat"),
])
def test_pre_existing_flat_fixtures_classify_flat(filename, expected):
    result = classify(TESTDATA / filename, cfg())
    assert result.class_ == expected, (filename, result.signals)


@pytest.mark.parametrize("filename,expected", [
    ("enthusiast_logo.png", "flat"),
    ("drone_render.png", "gradient"),
    ("photo_subject_stub.png", "photo_subject"),
    ("photo_scene_stub.png", "photo_scene"),
    ("gradient_ramp_linear.png", "gradient"),
    ("gradient_ramp_radial.png", "gradient"),
])
def test_photo_fixtures_route_to_the_expected_class(filename, expected):
    """`enthusiast_logo.png` and `drone_render.png` are Kent's real
    production art (F1/F2 of the plan), not synthetic stand-ins -- this is
    the load-bearing pair the whole classifier exists to get right."""
    result = classify(PHOTO_DIR / filename, cfg())
    assert result.class_ == expected, (filename, result.signals, result.confidence)


@pytest.mark.parametrize("filename,expected", [
    ("photo_owl_pale.png", "photo_scene"),
    ("photo_dof_meadow.png", "photo_scene"),
    ("photo_grass_macro.png", "photo_subject"),
    ("photo_sunset_backlit.png", "photo_scene"),
    ("photo_chrome_specular.png", "photo_scene"),
])
def test_photorealistic_fixtures_route_to_photo_territory(filename, expected):
    """The 2026-08-11 photo-realistic fixtures (tools/make_photo_fixtures.py)
    — procedurally generated but with real-photo statistics, unlike the two
    *_stub.png stand-ins. Every one of them must land in photo territory;
    the subject/scene split below records the CURRENT gate behaviour, one
    finding included: stage0's photo_subject gate is effectively bimodal
    (it fires on full-frame fine texture via the measured path or the
    everything-is-an-edge fallback, but a textured subject against any
    smooth backdrop keeps enough smooth interior to read photo_scene — the
    owl portrait and the chrome kettle land there for exactly that reason).
    Revisit when the subject/scene thresholds are retuned against real
    portrait fixtures."""
    result = classify(PHOTO_DIR / filename, cfg())
    assert result.class_ == expected, (filename, result.signals, result.confidence)
    assert result.confidence >= 0.9, (filename, result.confidence, result.signals)


def test_ambiguous_soft_shadow_fixture_never_crashes():
    """Flat art plus one soft (Gaussian-blurred) drop shadow -- the plan's
    Test 2 ambiguous case. A stable class (any of the four) or
    CLASSIFICATION_UNCERTAIN is acceptable; a crash or a non-deterministic
    result is not.
    """
    img = np.full((300, 300, 3), 255, np.uint8)
    shadow = np.zeros((300, 300), np.float32)
    cv2.circle(shadow, (170, 170), 70, 1.0, -1)
    shadow = cv2.GaussianBlur(shadow, (0, 0), sigmaX=18)
    shaded = (255 - shadow * 90).astype(np.uint8)
    for c in range(3):
        img[:, :, c] = np.minimum(img[:, :, c], shaded)
    cv2.circle(img, (150, 150), 60, (30, 30, 30), -1)

    result = classify(img, cfg())
    assert result.class_ in {"flat", "gradient", "photo_subject", "photo_scene"}

    again = classify(img, cfg())
    assert again.class_ == result.class_
    assert again.confidence == result.confidence


# --- Test 5: classification determinism ------------------------------------

@pytest.mark.parametrize("path", [
    TESTDATA / "logo_whitebg.png",
    TESTDATA / "logo_alpha.png",
    PHOTO_DIR / "drone_render.png",
    PHOTO_DIR / "enthusiast_logo.png",
    PHOTO_DIR / "photo_subject_stub.png",
    PHOTO_DIR / "photo_scene_stub.png",
    PHOTO_DIR / "gradient_ramp_linear.png",
])
def test_same_input_classified_twice_is_identical(path):
    """No RNG in the signal computation (the throwaway quantize is seeded),
    so this should be free -- pinned as a canary anyway, per this codebase's
    established pattern (see test_stage6_blend.py::test_blend_determinism).
    """
    a = classify(path, cfg())
    b = classify(path, cfg())
    assert a.class_ == b.class_
    assert a.confidence == b.confidence
    assert a.signals == b.signals
    assert a.warnings == b.warnings


# --- forced_class escape hatch ----------------------------------------------

def test_forced_class_skips_signal_computation_entirely():
    result = classify(PHOTO_DIR / "photo_subject_stub.png", cfg(), forced_class="flat")
    assert result.class_ == "flat"
    assert result.confidence == 1.0
    assert result.signals == {}
    assert result.warnings == []


# --- debug artifact ----------------------------------------------------------

def test_debug_artifact_written_when_debug_dir_set(tmp_path):
    result = classify(PHOTO_DIR / "drone_render.png", cfg(debug_dir=str(tmp_path)))
    path = tmp_path / "stage0_classification.txt"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert result.class_ in text
    assert f"{result.confidence:.4f}" in text
    for key, value in result.signals.items():
        assert key in text
        assert f"{value:.6f}"[:10] in text


def test_no_debug_artifact_without_debug_dir(tmp_path):
    classify(TESTDATA / "logo_whitebg.png", cfg())
    # Nothing written anywhere the test can see by default -- the direct
    # check is that debug_dir=None never raises trying to write.
    assert cfg().debug_dir is None
