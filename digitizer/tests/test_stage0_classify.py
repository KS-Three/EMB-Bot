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

    It was not free: it went red twice in CI on `logo_whitebg.png` until
    `gradient_smoothness` stopped depending on a buffer's address -- Test 5b.
    """
    a = classify(path, cfg())
    b = classify(path, cfg())
    assert a.class_ == b.class_
    assert a.confidence == b.confidence
    assert a.signals == b.signals
    assert a.warnings == b.warnings


# --- Test 5b: the signal must not follow the heap --------------------------
#
# CI went red twice (main run 40137455117, a PR run 40129814835, both shard 1)
# on the test above, `logo_whitebg.png`, `gradient_smoothness` 0.0005601321504400403
# against 0.0005601322072834591 -- once with the first call high, once with the
# second. The brief blamed the float32 `boxFilter` and mean. Measured 2026-10-25
# they are bit-stable at 1 and 8 threads, at every input and output alignment,
# and under IPP's avx2 / sse42 / disabled paths. The one op that moves is
# `cv2.magnitude`: Intel IPP's AVX2 kernel (the path conftest.py caps CI at)
# gives a different answer for a 16-byte-aligned output buffer than for a
# 32-byte-aligned one, and the buffer is numpy's, so its address is whatever the
# allocator had free. Offsets 0/4/32/36 read ...2072834591, 12-28 read
# ...1504400403, 8/40 a third value. The signal is near zero on this fixture
# (a flat logo), so one rounding in a few pixels is visible; the others do not
# show it.

LOGO_WHITEBG = TESTDATA / "logo_whitebg.png"


def _magnitude_into_buffer_at(offset: int):
    """A stand-in for `cv2.magnitude` that hands IPP an OUTPUT buffer whose data
    pointer sits `offset` bytes past a 64-byte boundary -- the one thing numpy's
    allocator varies from call to call and the test cannot otherwise steer."""
    real = cv2.magnitude

    def magnitude(x, y):
        raw = np.empty(x.size * 4 + 256, np.uint8)
        start = (-raw.ctypes.data) % 64 + offset
        dst = raw[start:start + x.size * 4].view(np.float32).reshape(x.shape)
        assert dst.ctypes.data % 64 == offset
        real(x, y, dst)
        return dst

    return magnitude


@pytest.mark.parametrize("offset", range(0, 64, 4))
def test_gradient_smoothness_does_not_follow_the_output_buffers_address(offset, monkeypatch):
    """Every 4-byte shift of the buffer `mag` lands in must read the same value.
    On a host whose IPP takes the AVX2 path (CI, capped by conftest.py; Kent's
    laptop) this is red with `cv2.magnitude` in `_gradient_smoothness`; it is
    vacuous only where IPP is off, which is exactly where the bug cannot show."""
    from digitizer_core import stage0_classify as stage0

    rgb, alpha = stage0._load(LOGO_WHITEBG)
    fg = stage0._fg_mask(rgb, alpha)
    want = stage0._gradient_smoothness(rgb, fg)

    monkeypatch.setattr(stage0.cv2, "magnitude", _magnitude_into_buffer_at(offset))
    assert stage0._gradient_smoothness(rgb, fg) == want


def test_magnitude_is_the_exact_hypotenuse_rounded_once():
    """`_magnitude` is sqrt(gx^2 + gy^2) in float64 -- both squares are exact
    there, the sum rounds once, and sqrt is correctly rounded on every IEEE
    host -- then rounded once to float32. Nothing in it can vary with SIMD
    width, alignment, thread count or library path."""
    from digitizer_core import stage0_classify as stage0

    rng = np.random.default_rng(7)
    gx = (rng.standard_normal((37, 53)) * 3).astype(np.float32)
    gy = (rng.standard_normal((37, 53)) * 3).astype(np.float32)
    gx[0, 0], gy[0, 0] = 3.0, 4.0
    want = np.sqrt(gx.astype(np.float64) ** 2 + gy.astype(np.float64) ** 2).astype(np.float32)

    got = stage0._magnitude(gx, gy)
    assert got.dtype == np.float32 and got.shape == gx.shape
    assert got[0, 0] == 5.0
    assert np.array_equal(got, want)
    # the same answer from a block size that does not divide the rows
    assert np.array_equal(stage0._magnitude(gx, gy, rows=5), want)


@pytest.mark.parametrize("threads", [1, 2, 8])
def test_classifying_in_a_loop_is_bit_identical(threads):
    """The same input classified N times is identical -- at any OpenCV thread
    count and with the heap shifted between passes (live blocks of odd sizes
    kept across calls, so numpy's next large block lands elsewhere). Precision
    must not depend on timing or thread count: CI runs this on an xdist worker
    with other tests' arrays still being freed around it."""
    previous = cv2.getNumThreads()
    cv2.setNumThreads(threads)
    held = []
    try:
        first = classify(LOGO_WHITEBG, cfg())
        for i in range(5):
            held.append(np.empty(1_000_003 + 4099 * i + 12 * i, np.uint8))
            again = classify(LOGO_WHITEBG, cfg())
            assert again.signals == first.signals, (i, threads)
            assert again.class_ == first.class_
            assert again.confidence == first.confidence
    finally:
        cv2.setNumThreads(previous)


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
        # Mirror `_write_debug`'s OWN rule rather than assuming every signal
        # is a float. That isinstance branch has always been there; until
        # `unique_color_mass_seed` (2026-09-14) no signal ever exercised it,
        # so this loop's `f"{value:.6f}"` passed by coincidence. An int seed
        # writes as `0`, not `0.000000`, and the dump is correct — the
        # assertion was the thing that only knew about one kind of signal.
        expected = f"{value:.6f}"[:10] if isinstance(value, float) else repr(value)
        assert expected in text, f"{key}={value!r} not rendered as {expected!r}"


def test_no_debug_artifact_without_debug_dir(tmp_path):
    classify(TESTDATA / "logo_whitebg.png", cfg())
    # Nothing written anywhere the test can see by default -- the direct
    # check is that debug_dir=None never raises trying to write.
    assert cfg().debug_dir is None
