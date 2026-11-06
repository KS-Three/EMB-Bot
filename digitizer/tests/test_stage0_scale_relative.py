"""Stage 0's scale-relative flat/gradient read (`cfg.stage0_scale_relative_grad`,
built OFF 2026-11-06). Doc: `docs/stage0-scale-relative-grad-2026-11-06.md`.

Arrays built in-line check arithmetic only and calibrate nothing (ROADMAP
gate 2); readings on committed files are instrument readings, not quality
claims (gate 4). The scale property itself is asserted in
`tests/test_classifier_scale_invariance.py`, ON arm.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest

from digitizer_core import stage0_classify as s0
from digitizer_core.config import PipelineConfig
from tools import stage0_scale_relative as tool

from .conftest import ENGINE_2026_10_27, TESTDATA


def test_the_flag_defaults_on_and_the_frozen_snapshot_holds_off():
    """Flipped ON 2026-11-06 (Kent, "Flip ON (Recommended)"); the dated snapshot
    and `PRE_FLIP` keep the engine the older pins were taken on."""
    from .conftest import PRE_FLIP
    assert PipelineConfig().stage0_scale_relative_grad is True
    assert ENGINE_2026_10_27["stage0_scale_relative_grad"] is False
    assert PRE_FLIP["stage0_scale_relative_grad"] is False


# --- the statistic ----------------------------------------------------------------

def _ones(h, w):
    return np.ones((h, w), bool)


def test_tonal_frac_is_zero_on_a_flat_field():
    assert s0._tonal_frac(np.full((300, 400, 3), 120, np.uint8), _ones(300, 400)) == 0.0


def test_tonal_frac_is_zero_on_an_anti_aliased_two_colour_disc_at_any_size():
    """Fills and edges only: the AA rim is a hard edge, excluded, whatever the size."""
    for side in (120, 400, 1600):
        img = np.full((side, side, 3), 240, np.uint8)
        cv2.circle(img, (side // 2, side // 2), side // 3, (20, 40, 160), -1, lineType=cv2.LINE_AA)
        assert s0._tonal_frac(img, _ones(side, side)) < 0.01, side


def test_tonal_frac_reads_a_gentle_ramp_that_texture_frac_calls_flat():
    """A 0-255 ramp across 512 px is ~0.5 levels/px: under the texture band
    (5x5 std ~0.7) but over the ramp slope floor."""
    ramp = np.tile(np.linspace(0, 255, 512, dtype=np.float32), (300, 1)).astype(np.uint8)
    rgb = np.dstack([ramp] * 3)
    assert s0._texture_frac(rgb, _ones(300, 512)) < 0.05
    assert s0._tonal_frac(rgb, _ones(300, 512)) > 0.9


def test_the_foreground_rim_is_excluded():
    """A cut-out whose rim pixels sit a few levels off the ink (PIL's
    premultiplied resample does this) reads nothing tonal there."""
    img = np.full((400, 400, 3), 60, np.uint8)
    fg = np.zeros((400, 400), bool)
    cv2.circle(fg.view(np.uint8), (200, 200), 150, 1, -1)
    rim = fg & ~cv2.erode(fg.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
    img[rim] = 63
    assert s0._tonal_frac(img, fg) == 0.0


def test_tonal_frac_is_zero_under_the_foreground_floor():
    fg = np.zeros((100, 100), bool)
    fg[:4, :4] = True
    assert s0._tonal_frac(np.zeros((100, 100, 3), np.uint8), fg) == 0.0


# --- the decision ----------------------------------------------------------------

def test_decide_flat_gradient_off_is_the_shipped_gate():
    for gv in (0.0, s0.GRAD_VAR_GRADIENT_MIN - 1e-6, s0.GRAD_VAR_GRADIENT_MIN, 0.5):
        assert s0.decide_flat_gradient(gv, 0.99, False) == (
            gv >= s0.GRAD_VAR_GRADIENT_MIN,
            s0._gate_confidence(gv, s0.GRAD_VAR_GRADIENT_MIN, s0.GRAD_VAR_GRADIENT_MARGIN))


def test_decide_flat_gradient_on_reads_tonal_frac_only():
    assert s0.decide_flat_gradient(99.0, 0.0, True)[0] is False
    assert s0.decide_flat_gradient(0.0, s0.TONAL_GRADIENT_MIN, True) == (True, 0.5)


@pytest.mark.parametrize("rel", ["logo_whitebg.png", "photo/drone_render.png", "photo/owl_kent.jpg"])
def test_both_arms_report_the_same_signals_and_off_ignores_tonal_frac(rel):
    off = s0.classify(str(TESTDATA / rel), PipelineConfig(stage0_scale_relative_grad=False))
    on = s0.classify(str(TESTDATA / rel), PipelineConfig())
    assert off.signals == on.signals
    assert "tonal_frac" in off.signals
    assert tool.derive(off.signals, False) == off.class_
    assert tool.derive(on.signals, True) == on.class_


def test_off_class_does_not_move_when_tonal_frac_would_flip_it(monkeypatch):
    """OFF never reads the new statistic: forcing it to either extreme leaves
    the shipped class and confidence exactly as they were."""
    path = str(TESTDATA / "photo" / "enthusiast_logo.png")
    off = PipelineConfig(stage0_scale_relative_grad=False)
    base = s0.classify(path, off)
    for forced in (0.0, 1.0):
        monkeypatch.setattr(s0, "_tonal_frac", lambda rgb, fg, v=forced: v)
        r = s0.classify(path, off)
        assert (r.class_, r.confidence) == (base.class_, base.confidence)


# --- the instrument -----------------------------------------------------------------

def test_kappa_arithmetic():
    assert tool.kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert tool.kappa([True, True, False, False], [True, False, True, False]) == 0.0
    assert tool.kappa([True, True], [True, True]) is None


def test_the_rungs_are_downscales_and_the_studio_cap(tmp_path):
    from PIL import Image
    p = tmp_path / "wide.png"
    Image.new("RGB", (1300, 300), (200, 30, 30)).save(p)
    rungs = [(r, w) for r, w, _ in tool.rasters(p)]
    assert rungs[0] == ("native", 1300)
    assert all(w < 1300 for r, w in rungs[1:])
    assert {r for r, _ in rungs if r.startswith("studio_")} == {f"studio_{i}" for i in tool.STUDIO_INTERPS}
    assert {w for r, w in rungs if r.startswith("studio_")} == {1200}
