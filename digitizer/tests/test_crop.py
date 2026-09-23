import numpy as np
import pytest

from digitizer_core.crop import MIN_CROP_PX, apply_crop, validate_crop


def _art(h=200, w=400):
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[:, :, 0] = 255
    alpha = np.full((h, w), 255, np.uint8)
    return rgb, alpha


def test_none_is_a_no_op_and_returns_the_same_objects():
    rgb, alpha = _art()
    out_rgb, out_alpha = apply_crop(rgb, alpha, None)
    assert out_rgb is rgb
    assert out_alpha is alpha


def test_crops_rgb_and_alpha_together():
    rgb, alpha = _art(200, 400)
    out_rgb, out_alpha = apply_crop(rgb, alpha, (0.25, 0.5, 0.75, 1.0))
    assert out_rgb.shape == (100, 200, 3)
    assert out_alpha.shape == (100, 200)


def test_alpha_may_be_absent():
    rgb, _ = _art()
    out_rgb, out_alpha = apply_crop(rgb, None, (0.0, 0.0, 0.5, 0.5))
    assert out_rgb.shape == (100, 200, 3)
    assert out_alpha is None


def test_fractions_outside_the_unit_square_are_clamped_not_rejected():
    rgb, alpha = _art(200, 400)
    out_rgb, _ = apply_crop(rgb, alpha, (-0.5, -0.5, 1.5, 1.5))
    assert out_rgb.shape == (200, 400, 3)


def test_inverted_rectangle_raises():
    rgb, alpha = _art()
    with pytest.raises(ValueError, match="empty after clamping"):
        apply_crop(rgb, alpha, (0.8, 0.1, 0.2, 0.9))


def test_rectangle_under_the_pixel_floor_raises_and_names_the_size():
    rgb, alpha = _art(200, 400)
    with pytest.raises(ValueError, match=r"3x2 px"):
        apply_crop(rgb, alpha, (0.0, 0.0, 0.008, 0.01))


def test_the_floor_is_the_border_readers_not_a_physical_constant():
    # `stage1_prep._border_ring` reads a 2 px ring and
    # `_modal_corner_ownership` samples 8 px corners; below MIN_CROP_PX the
    # background detector has no border to read and fails with a worse
    # message than validation gives.
    assert MIN_CROP_PX == 16


def test_validate_returns_pixel_box():
    assert validate_crop((0.0, 0.0, 0.5, 0.5), (200, 400)) == (0, 0, 200, 100)
    assert validate_crop(None, (200, 400)) is None


def test_wrong_arity_raises():
    rgb, alpha = _art()
    with pytest.raises(ValueError, match="four fractions"):
        apply_crop(rgb, alpha, (0.1, 0.2, 0.3))


def test_nan_is_rejected_not_a_cannot_convert_float_nan_to_integer_crash():
    """`clamp` returns a NaN unchanged, and `x1f <= x0f` is False for NaN
    too, so a degenerate rectangle carrying one used to sail past the
    emptiness guard and die four lines later at `int(round(...))` with
    "cannot convert float NaN to integer" -- naming neither `crop` nor the
    rectangle (finding 9, 2026-09-22 review)."""
    rgb, alpha = _art()
    with pytest.raises(ValueError, match="empty after clamping"):
        apply_crop(rgb, alpha, (float("nan"), 0.1, 0.5, 0.9))
    with pytest.raises(ValueError, match="empty after clamping"):
        apply_crop(rgb, alpha, (0.1, 0.1, 0.5, float("nan")))
