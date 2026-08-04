"""`tools/classify_lens.py` — the lens's OWN correctness, nothing else.

The lens re-derives stage 0's decision tree so it can sweep thresholds
without touching the engine; these tests pin that the re-derivation agrees
with the engine exactly (the lens's load-bearing self-check), that the
distance-to-flip analysis reports real flips, and that the sweep's range
grouping cannot merge non-contiguous flip regions. Zero engine behavior is
asserted here beyond "the lens mirrors it" — the engine's own routing tests
live in `test_stage0_classify.py`.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"

_spec = importlib.util.spec_from_file_location(
    "classify_lens", HERE.parent / "tools" / "classify_lens.py")
lens = importlib.util.module_from_spec(_spec)
sys.modules["classify_lens"] = lens  # dataclasses resolve their own module
_spec.loader.exec_module(lens)

from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.stage0_classify import classify  # noqa: E402


NOMINAL = lens.Thresholds.nominal()


# --- decide() mirrors the engine --------------------------------------------

@pytest.mark.parametrize("path,expected", [
    (PHOTO_DIR / "enthusiast_logo.png", "flat"),
    (PHOTO_DIR / "drone_render.png", "gradient"),
    (PHOTO_DIR / "photo_subject_stub.png", "photo_subject"),
    (PHOTO_DIR / "photo_scene_stub.png", "photo_scene"),
])
def test_decide_reproduces_engine_verdict_on_all_four_branches(path, expected):
    """One fixture per reachable class. The engine computes the signals; the
    lens's re-derived tree must land on the same class at the same
    confidence, or every number the lens prints is untrustworthy."""
    res = classify(path, PipelineConfig(target_width_mm=80.0))
    assert res.class_ == expected  # routing itself is test_stage0_classify's job
    d = lens.decide(res.signals["unique_color_mass"],
                    res.signals["gradient_smoothness"], NOMINAL)
    assert d.class_ == res.class_
    assert d.confidence == pytest.approx(res.confidence, abs=1e-12)


def test_perturbed_thresholds_actually_change_the_decision():
    """The sweep is only meaningful if `decide()` really responds to a
    perturbed Thresholds — pin that lowering the photo gate under
    drone_render's measured ucm moves it off `gradient`."""
    res = classify(PHOTO_DIR / "drone_render.png",
                   PipelineConfig(target_width_mm=80.0))
    ucm = res.signals["unique_color_mass"]
    grad = res.signals["gradient_smoothness"]
    import dataclasses
    lowered = dataclasses.replace(NOMINAL, ucm_photo_min=ucm * 0.5)
    assert lens.decide(ucm, grad, lowered).class_ != res.class_


def test_decide_is_pure_and_deterministic():
    for args in [(0.05, 0.0001), (0.16, 4.46), (0.43, 0.66), (0.75, 184.0),
                 (0.28, 0.0015), (0.281, 7.99)]:
        a = lens.decide(*args, NOMINAL)
        b = lens.decide(*args, NOMINAL)
        assert a == b


def test_demotion_band_collapses_low_confidence_nonflat_to_flat():
    """A ucm sitting closer to the photo threshold than the demotion band's
    half-width must come back `flat` + demoted, matching the engine's
    CONFIDENCE_FLOOR behavior for a would-be non-flat class."""
    band = lens._demotion_halfwidth(NOMINAL, NOMINAL.ucm_margin)
    assert band > 0
    inside = lens.decide(NOMINAL.ucm_photo_min + band / 2, 0.5, NOMINAL)
    assert inside.demoted and inside.class_ == "flat"
    assert inside.raw_class == "photo_scene"
    clear = lens.decide(NOMINAL.ucm_photo_min + band * 2, 0.5, NOMINAL)
    assert not clear.demoted and clear.class_ == "photo_scene"


# --- distance-to-flip -------------------------------------------------------

@pytest.mark.parametrize("ucm,grad", [
    (0.0030, 0.0011),   # bg_uncertain's measured signals — nearest live margin
    (0.1592, 4.4635),   # drone_render's — the documented hard case
    (0.4256, 0.6613),   # photo_scene_stub's
    (0.0002, 0.0118),   # repro_gradient_white_icon's
])
def test_reported_flip_actually_flips_and_near_side_does_not(ucm, grad):
    cur = lens.decide(ucm, grad, NOMINAL).class_
    for f in (lens.nearest_flip("unique_color_mass", ucm, grad, NOMINAL),
              lens.nearest_flip("gradient_smoothness", ucm, grad, NOMINAL)):
        if f is None:
            continue
        eps = max(abs(f.at), 1.0) * 1e-7
        side = eps if f.delta > 0 else -eps
        if f.signal == "unique_color_mass":
            far = lens.decide(f.at + side, grad, NOMINAL).class_
            near = lens.decide(f.at - side, grad, NOMINAL).class_
        else:
            far = lens.decide(ucm, f.at + side, NOMINAL).class_
            near = lens.decide(ucm, f.at - side, NOMINAL).class_
        assert far == f.to and far != cur
        assert near == cur


# --- sweep range grouping ---------------------------------------------------

def test_ranges_do_not_merge_across_gaps_or_class_changes():
    step = 0.05
    hits = [(0.50, "gradient"), (0.55, "gradient"),   # contiguous pair
            (0.90, "gradient"),                        # gap -> new range
            (0.95, "flat")]                            # class change -> new range
    got = lens._ranges(hits, step)
    assert got == [(0.50, 0.55, "gradient"),
                   (0.90, 0.90, "gradient"),
                   (0.95, 0.95, "flat")]
