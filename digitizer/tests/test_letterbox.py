"""Tests for digitizer_core/letterbox.py.

Pure-array tests plus a cheap decode of the tracked fixtures — no engine run,
no service, same rule as `test_artfidelity_self.py`.

**The load-bearing test here is `test_four_sided_margin_is_not_stripped`.**
The first version of this detector had only a contrast guard (the bars must
look different from the interior), and that guard ACCEPTS `bg_uncertain.png`
— a navy block inside a white margin — cropping it 800x500 -> 601x341. That
fixture scores ARTFID 95.6 and was ranked best of fourteen by eye in
`docs/artfid-eye-agreement-2026-09-11.md`. Cropping it would have removed the
background that `stage1_prep`'s border flood needs, i.e. a repo-wide
regression shipped to fix one screenshot. The rule that saves it is semantic
rather than tuned: letterboxing is one-dimensional, so bars on BOTH axes are
a margin and are never stripped.
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.letterbox import (  # noqa: E402
    detect_letterbox,
    strip_letterbox,
)

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"

# The one tracked fixture that IS a screenshot: a phone capture of a roofing
# logo, 1284x2778, pure-black bars above and below a white logo band.
SCREENSHOT = "photo/logo_gaulke_roofing.png"


def _load_rgb(name: str) -> np.ndarray:
    raw = cv2.imread(str(TESTDATA / name), cv2.IMREAD_UNCHANGED)
    assert raw is not None, f"could not decode {name}"
    if raw.ndim == 2:
        return cv2.cvtColor(raw, cv2.COLOR_GRAY2RGB)
    if raw.shape[2] == 4:
        return cv2.cvtColor(raw[:, :, :3], cv2.COLOR_BGR2RGB)
    return cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)


def _letterbox(rgb: np.ndarray, pad: int, vertical: bool = True,
               colour: tuple[int, int, int] = (0, 0, 0)) -> np.ndarray:
    h, w = rgb.shape[:2]
    if vertical:
        bar = np.full((pad, w, 3), colour, np.uint8)
        return np.vstack([bar, rgb, bar])
    bar = np.full((h, pad, 3), colour, np.uint8)
    return np.hstack([bar, rgb, bar])


# --- the regression this module exists to prevent ---------------------------

def test_four_sided_margin_is_not_stripped():
    """A uniform border on BOTH axes is a margin, never letterboxing.

    `bg_uncertain.png` passes the contrast guard easily (white margin, navy
    interior) and must still come back untouched.
    """
    rgb = _load_rgb("bg_uncertain.png")
    assert detect_letterbox(rgb) == (0, 0, 0, 0)
    out, _ = strip_letterbox(rgb)
    assert out.shape == rgb.shape
    assert np.array_equal(out, rgb)


def test_synthetic_four_sided_frame_is_not_stripped():
    """The same rule on a hand-built case, so it does not rest on one fixture."""
    inner = np.full((200, 300, 3), 240, np.uint8)
    inner[50:150, 80:220] = (10, 20, 180)
    framed = np.full((300, 420, 3), 0, np.uint8)
    framed[50:250, 60:360] = inner
    assert detect_letterbox(framed) == (0, 0, 0, 0)


# --- the defect this module exists to fix -----------------------------------

def test_screenshot_bars_are_detected():
    rgb = _load_rgb(SCREENSHOT)
    top, bottom, left, right = detect_letterbox(rgb)
    assert top > 0 and bottom > 0, "the black bars must be found"
    assert left == 0 and right == 0, "there are no side bars in this fixture"
    out, _ = strip_letterbox(rgb)
    assert out.shape[0] < rgb.shape[0]
    assert out.shape[1] == rgb.shape[1], "width must not change"
    # What survives must be the logo band: bright, not the black bars.
    assert out.mean() > rgb.mean() + 40


@pytest.mark.parametrize("name", [
    "becker_marine_logo.png",
    "logo_whitebg.png",
    "logo_script_tires.png",
    "photo/logo_bridge_bar.jpg",
    "photo/enthusiast_logo.png",
])
@pytest.mark.parametrize("pad_frac", [0.15, 0.4, 0.8])
@pytest.mark.parametrize("vertical", [True, False])
def test_black_letterbox_round_trips_exactly(name, pad_frac, vertical):
    """strip(letterbox(x)) == x, byte for byte.

    Synthetic bars are legitimate here: a bar is a GEOMETRIC property, and
    this asserts an inverse, not a tonal judgement. ROADMAP gate 2 bars
    synthetic fixtures as substitutes for real tonal artwork in stage-0
    recalibration; nothing here recalibrates stage 0.
    """
    rgb = _load_rgb(name)
    span = rgb.shape[0] if vertical else rgb.shape[1]
    pad = max(4, int(span * pad_frac))
    out, _ = strip_letterbox(_letterbox(rgb, pad, vertical))
    assert out.shape == rgb.shape
    assert np.array_equal(out, rgb)


def test_alpha_is_cropped_with_the_image():
    rgb = np.full((100, 60, 3), 250, np.uint8)
    rgb[40:60, 20:40] = (10, 10, 10)
    alpha = np.full((100, 60), 255, np.uint8)
    lb = _letterbox(rgb, 40)
    lb_a = np.vstack([np.zeros((40, 60), np.uint8), alpha,
                      np.zeros((40, 60), np.uint8)])
    out, out_a = strip_letterbox(lb, lb_a)
    assert out.shape[:2] == out_a.shape
    assert np.array_equal(out, rgb)
    assert np.array_equal(out_a, alpha)


# --- guards against over-cropping -------------------------------------------

def test_uniform_image_is_never_stripped():
    """One flat colour has no subject to keep, so there is nothing to strip."""
    for value in (0, 128, 255):
        flat = np.full((120, 160, 3), value, np.uint8)
        assert detect_letterbox(flat) == (0, 0, 0, 0)


def test_bars_larger_than_max_frac_are_refused():
    """A dark design on a dark ground must never be cropped to nothing."""
    rgb = np.full((200, 200, 3), 8, np.uint8)
    rgb[98:102, 98:102] = 255          # a tiny bright subject, dead centre
    top, bottom, left, right = detect_letterbox(rgb)
    assert (top, bottom, left, right) == (0, 0, 0, 0)


def test_vertical_gradient_is_not_a_bar():
    """A smooth ramp matches its own neighbour at every step; only the
    per-line uniformity test keeps it from being eaten."""
    h, w = 200, 120
    ramp = np.repeat(np.linspace(0, 255, h, dtype=np.uint8)[:, None], w, axis=1)
    rgb = np.dstack([ramp] * 3)
    assert detect_letterbox(rgb) == (0, 0, 0, 0)


def test_noise_thin_edge_is_not_a_bar():
    """A run under min_frac is edge noise, not a bar."""
    rgb = np.full((400, 300, 3), 240, np.uint8)
    rgb[200:260, 100:200] = (20, 20, 20)
    rgb[:2] = 0          # 2 rows of 400 = 0.5%, under MIN_FRAC
    top, _, _, _ = detect_letterbox(rgb)
    assert top == 0


def test_strip_is_identity_when_nothing_is_found():
    """The common path must return the inputs themselves, not copies."""
    rgb = _load_rgb("logo_whitebg.png")
    alpha = np.full(rgb.shape[:2], 255, np.uint8)
    out, out_a = strip_letterbox(rgb, alpha)
    assert out is rgb
    assert out_a is alpha


def test_tracked_fixtures_are_untouched_except_the_screenshot():
    """The blast radius, pinned. Only the screenshot may crop."""
    from tools.artfidelity_self import FIXTURES
    cropped = [n for n in FIXTURES
               if any(detect_letterbox(_load_rgb(n)))]
    assert cropped == [SCREENSHOT], (
        f"letterbox detection changed its blast radius: {cropped}")
