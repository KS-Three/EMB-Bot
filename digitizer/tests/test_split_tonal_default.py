"""Spec decision 2 (2026-08-18): photo classes split tonal regions by
default; gradient and flat do not. The flag stays an explicit opt-in for
non-photo classes."""
from digitizer_core.pipeline import effective_split_tonal
from digitizer_core.config import PipelineConfig


def test_photo_classes_split_by_default():
    cfg = PipelineConfig()
    assert effective_split_tonal(cfg, "photo_subject") is True
    assert effective_split_tonal(cfg, "photo_scene") is True


def test_gradient_and_flat_do_not_split_by_default():
    cfg = PipelineConfig()
    assert effective_split_tonal(cfg, "gradient") is False
    assert effective_split_tonal(cfg, "flat") is False


def test_explicit_flag_still_wins_everywhere():
    cfg = PipelineConfig(split_tonal_regions=True)
    assert effective_split_tonal(cfg, "gradient") is True
