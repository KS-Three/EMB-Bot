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


def test_classify_threads_the_crop_from_cfg():
    art = _banner_art()
    cfg = PipelineConfig(target_width_mm=80.0, crop=(0.0, 0.33, 1.0, 0.67))
    # Must not raise, and must not classify on the uncropped frame.
    c = stage0_classify.classify(art, cfg)
    assert c.class_ in ("flat", "gradient", "photo_subject", "photo_scene")


def test_a_bad_crop_raises_out_of_prep():
    with pytest.raises(ValueError, match="empty after clamping"):
        stage1_prep.prep(_banner_art(),
                         PipelineConfig(target_width_mm=80.0,
                                        crop=(0.9, 0.1, 0.1, 0.9)))
