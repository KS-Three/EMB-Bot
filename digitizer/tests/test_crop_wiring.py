import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core import stage0_classify, stage1_prep


def _banner_art():
    """White frame, a dark bar across the top (the "chrome"), and a dark
    block in the middle (the "logo"). 400x600."""
    rgb = np.full((600, 400, 3), 255, np.uint8)
    rgb[0:60, :] = 20            # chrome band
    rgb[250:350, 100:300] = 30   # logo
    return rgb


def test_prep_crops_before_anything_reads_the_pixels():
    art = _banner_art()
    cfg = PipelineConfig(target_width_mm=80.0, crop=(0.0, 0.33, 1.0, 0.67))
    p = stage1_prep.prep(art, cfg)
    # 600 * 0.33 = 198 .. 600 * 0.67 = 402 -> 204 rows before any upscale.
    assert p.rgb.shape[1] / p.rgb.shape[0] == pytest.approx(400 / 204, rel=0.05)


def test_uncropped_prep_is_unchanged():
    art = _banner_art()
    a = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0))
    b = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0, crop=None))
    assert np.array_equal(a.rgb, b.rgb)
    assert np.array_equal(a.bg_mask, b.bg_mask)


def test_stage0_sees_the_same_picture_stage1_digitizes():
    """The strip_letterbox rule, applied to crop: if only one of them
    cropped, stage 0 would classify the chrome the crop exists to remove."""
    art = _banner_art()
    crop = (0.0, 0.33, 1.0, 0.67)
    cfg = PipelineConfig(target_width_mm=80.0, crop=crop)
    rgb0, _ = stage0_classify._load(art, cfg.strip_letterbox, cfg.crop)
    p = stage1_prep.prep(art, cfg)
    # Same crop applied, so stage 0's raster and stage 1's PRE-upscale raster
    # describe the same region: identical aspect ratio, and the chrome band
    # is absent from both.
    assert rgb0.shape[:2] == (204, 400)
    assert int(rgb0[:10].mean()) > 200      # top row is page, not chrome
    assert int(p.rgb[:10].mean()) > 200


def _signals_equal(a: dict, b: dict) -> bool:
    if set(a) != set(b):
        return False
    for k in a:
        va, vb = a[k], b[k]
        if isinstance(va, (int, float, np.floating, np.integer)) and not isinstance(va, bool):
            if va != pytest.approx(vb, rel=1e-9, abs=1e-12, nan_ok=True):
                return False
        elif va != vb:
            return False
    return True


def test_classify_threads_the_crop_from_cfg():
    """classify(art, cfg WITH crop) must read exactly the picture
    classify(art[crop], cfg WITHOUT crop) reads: every signal equal. And the
    uncropped frame must read differently, or this proves nothing."""
    art = _banner_art()
    cropped_cfg = PipelineConfig(target_width_mm=80.0, crop=(0.0, 0.33, 1.0, 0.67))
    plain_cfg = PipelineConfig(target_width_mm=80.0)
    # 600 * 0.33 = 198 .. 600 * 0.67 = 402, full width.
    via_cfg = stage0_classify.classify(art, cropped_cfg)
    by_hand = stage0_classify.classify(np.ascontiguousarray(art[198:402]), plain_cfg)
    uncropped = stage0_classify.classify(art, plain_cfg)
    assert via_cfg.class_ == by_hand.class_
    assert via_cfg.signals, "no signals computed -- nothing was compared"
    assert _signals_equal(via_cfg.signals, by_hand.signals), (
        via_cfg.signals, by_hand.signals)
    assert not _signals_equal(via_cfg.signals, uncropped.signals), (
        "the crop changed no signal -- the test cannot see whether it was applied")


def test_a_bad_crop_raises_out_of_prep():
    with pytest.raises(ValueError, match="empty after clamping"):
        stage1_prep.prep(_banner_art(),
                         PipelineConfig(target_width_mm=80.0,
                                        crop=(0.9, 0.1, 0.1, 0.9)))


def test_a_crop_onto_blank_artwork_says_widen_not_crop_tighter():
    """The likeliest wrong drag: a box landing on empty background. The
    uncropped message's advice -- "or crop tighter" -- is backwards there;
    the fix is to widen the box. A crop is the caller's own input, so its
    message stays out of `errors._KNOWN` and reaches the panel as written."""
    from digitizer_service.errors import customer_message

    blank = np.full((40, 40, 3), 255, np.uint8)
    with pytest.raises(ValueError, match="no foreground pixels"):
        stage1_prep.prep(blank, PipelineConfig(target_width_mm=80.0))

    # Rows 480:600, cols 0:80 -- below the logo, outside the chrome: all white.
    with pytest.raises(ValueError, match="crop rectangle contains no artwork") as exc:
        stage1_prep.prep(_banner_art(), PipelineConfig(
            target_width_mm=80.0, crop=(0.0, 0.8, 0.2, 1.0)))
    said = customer_message(exc.value)
    assert "crop rectangle contains no artwork" in said
    assert "crop tighter" not in said
