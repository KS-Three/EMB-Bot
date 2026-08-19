"""Spec decision 3 (2026-08-18): the automatic tier map for photo classes.
photo_subject -> streamline (+ detail layer with faces); photo_scene ->
tatami+split; explicit caller choice always wins."""
import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import auto_photo_tier, run_stages
from digitizer_core.warnings_codes import PHOTO_AUTO_TIER


def test_photo_subject_defaults_to_streamline():
    assert auto_photo_tier(PipelineConfig(), "photo_subject", faces_present=False) == "streamline"


def test_photo_scene_defaults_to_tatami():
    # None = leave fill_technique alone; scene tone comes from split regions.
    assert auto_photo_tier(PipelineConfig(), "photo_scene", faces_present=False) is None


def test_explicit_caller_choice_wins():
    cfg = PipelineConfig(fill_technique="meander_tonal")
    assert auto_photo_tier(cfg, "photo_subject", faces_present=False) is None


def test_gradient_and_flat_untouched():
    assert auto_photo_tier(PipelineConfig(), "gradient", faces_present=False) is None
    assert auto_photo_tier(PipelineConfig(), "flat", faces_present=False) is None


# --- Wiring: run_stages' source_pixels gate + the PHOTO_AUTO_TIER warning ---
#
# The four tests above pin the pure decision function only; none of them
# call `run_stages`. `auto_photo_tier`'s return value is inert until
# something reads it — these pin the one reader (the source_pixels gate
# block pipeline.py:456-490 used to comment "automatic photo routing is a
# later slice" — this is that slice), measured from what a real caller
# actually gets back: `PipelineResult.source_pixels` and `.warnings`, never
# a re-read of `auto_photo_tier`'s own return value.

def _two_square_image() -> np.ndarray:
    """Same fixture shape as test_photo_sequencing.py's own helper: two flat
    squares on a transparent field. `forced_class` decides which lane runs,
    not real photo content, so this is enough to exercise the gate without
    a real photo fixture."""
    img = np.zeros((300, 300, 4), np.uint8)
    img[20:200, 20:200] = (245, 240, 235, 255)
    img[230:290, 230:290] = (30, 30, 35, 255)
    return img


def _warning(result, code: str) -> dict | None:
    return next((w for w in result.warnings if w["code"] == code), None)


def test_default_photo_subject_gets_source_pixels_and_the_warning():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject")
    result = run_stages(_two_square_image(), cfg)
    assert result.source_pixels is not None
    w = _warning(result, PHOTO_AUTO_TIER)
    assert w is not None, "auto-route decided streamline but never said so"
    assert w["tier"] == "streamline"
    # photo_prep defaults False (v1): no face detector ran, so there are no
    # faces to report and no auto-on detail layer either.
    assert w["detail_layer"] is False


def test_explicit_fill_technique_suppresses_the_warning_in_the_real_pipeline():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         fill_technique="meander_tonal")
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None, (
        "an explicit caller fill_technique must win inside run_stages, not "
        "just in auto_photo_tier's own return value")


def test_explicit_detail_layer_suppresses_the_warning_in_the_real_pipeline():
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         detail_layer=True)
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None


def test_photo_scene_gets_no_warning_and_no_source_pixels_by_default():
    # Spec decision 3: photo_scene stays tatami in v1 (tone arrives via
    # Task 2's split_tonal_regions, not a source-reading fill tier) — the
    # brief's own "leave scenes off want_tonal for v1" instruction, pinned
    # here from the PipelineResult a caller actually sees, not just from
    # auto_photo_tier returning None.
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_scene")
    result = run_stages(_two_square_image(), cfg)
    assert _warning(result, PHOTO_AUTO_TIER) is None
    assert result.source_pixels is None


def test_flat_and_gradient_get_no_auto_tier_warning():
    for class_ in ("flat", "gradient"):
        cfg = PipelineConfig(target_width_mm=80.0, forced_class=class_)
        result = run_stages(_two_square_image(), cfg)
        assert _warning(result, PHOTO_AUTO_TIER) is None, class_


def _astronaut(size: int = 256):
    """The rights-safe real-face fixture test_face_priors.py's own module
    docstring documents: `skimage.data.astronaut()`, public-domain, shipped
    inside the scikit-image wheel this venv already pins — a real face
    YuNet actually detects, above its measured 160px detection floor.
    Reimplemented locally (4 lines) rather than importing a private helper
    across test modules, matching every other fixture helper in this suite."""
    import cv2
    from skimage import data
    return cv2.resize(data.astronaut(), (size, size), interpolation=cv2.INTER_AREA)


def test_faces_present_turns_the_detail_layer_on_in_the_real_pipeline():
    # The one part of the wiring the pure-function tests structurally cannot
    # reach: `auto_photo_tier` accepts `faces_present` but never reads it
    # (the tier name does not change) — it is `run_stages` that turns the
    # detail layer on when the auto-route fires AND stage 1.5 actually found
    # a face. Proven on a real detector run, not a stubbed face list.
    cfg = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                         photo_prep=True)
    result = run_stages(_astronaut(), cfg)
    w = _warning(result, PHOTO_AUTO_TIER)
    assert w is not None
    assert w["tier"] == "streamline"
    assert w["detail_layer"] is True, (
        "a real detected face must turn the auto-route's detail layer on")
