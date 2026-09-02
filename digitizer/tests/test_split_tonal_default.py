"""Spec decision 2 (2026-08-18): photo classes split tonal regions by
default; gradient and flat do not.

`split_tonal_regions` is TRI-STATE — None lets the class decide, True splits
everything, False splits nothing. It was `bool = False` until 2026-09-02, and
the resolver read `bool(flag) or class_ in PHOTO_CLASSES`, which could only
ever turn the tier ON: for a photo class the OR was already True, so an
explicit False was byte-identical to leaving it unset.

`test_explicit_flag_still_wins_everywhere` below is why that survived. It
asserted only the True direction, under a name claiming both — so a green
suite said the override worked while half of it did not exist. The tier
therefore could not be measured against its own absence, and defect 20 records
what it costs with no denominator for what it buys."""
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


def test_an_explicit_FALSE_turns_it_off_for_photo_classes_too():
    """The half that did not exist, and the reason the tier had no off switch.

    A photo class is exactly where an override matters — it is the only class
    that splits by default — and it was the one place the old resolver ignored
    the caller. Without this, nothing can digitize a photograph WITHOUT tonal
    splitting, so the tier's cost (defect 20: coverage_max 7.18 against a
    3.5-layer ceiling) can be measured but never divided by what it buys.
    """
    cfg = PipelineConfig(split_tonal_regions=False)
    assert effective_split_tonal(cfg, "photo_subject") is False
    assert effective_split_tonal(cfg, "photo_scene") is False
    assert effective_split_tonal(cfg, "gradient") is False


def test_None_is_the_default_and_means_let_the_class_decide():
    """The sentinel that makes "unset" and "the caller said no" distinguishable
    — the same pattern `cfg.border` spells out at length, for the same reason.
    Shipped behaviour must not move: None has to answer exactly as the old
    `False` default did."""
    assert PipelineConfig().split_tonal_regions is None
    cfg = PipelineConfig(split_tonal_regions=None)
    assert effective_split_tonal(cfg, "photo_scene") is True
    assert effective_split_tonal(cfg, "flat") is False
