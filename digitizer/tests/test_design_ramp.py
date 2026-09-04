"""`design_ramp.py` — the design-wide ramp fit and its gate (Kent's gradient
ruling, 2026-09-03: one region when the design ramp fits).

Synthetic sweeps are generated in Lab and converted to sRGB, so the fit
sees exactly the structure it models; the one real fixture here is the
ruling's own repro, `repro_gradient_white_icon.png`, read at Studio
defaults — the configuration where the plain least-squares angle fit had
quietly stopped applying (see `stage6_blend.detect_design_ramp_angle`).
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from skimage.color import lab2rgb

from digitizer_core.config import PipelineConfig
from digitizer_core.design_ramp import (
    DESIGN_RAMP_MAX_SIGMA,
    DESIGN_RAMP_MIN_INLIER_FRAC,
    DESIGN_RAMP_R2_MIN,
    fit_design_ramp,
    fit_design_ramp_pixels,
)
from digitizer_core.stage1_prep import prep
from digitizer_core.stage6_blend import detect_design_ramp_angle
from digitizer_core.threads import rgb_to_lab

PHOTO_DIR = Path(__file__).resolve().parent.parent / "testdata" / "photo"
PX_PER_MM = 5.0
SIDE = 400  # px, an 80 mm square


def _lab_to_rgb8(lab: np.ndarray) -> np.ndarray:
    return (np.clip(lab2rgb(lab), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def _diagonal_sweep(angle_deg: float = 40.0, l_lo: float = 35.0, l_hi: float = 70.0
                    ) -> tuple[np.ndarray, np.ndarray]:
    """(rgb, direction): L* sweeps l_lo -> l_hi along `angle_deg`, a* and b*
    drift a little with it so every channel carries some of the ramp."""
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    ux, uy = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    s = (xs * ux + ys * uy) / PX_PER_MM
    t = (s - s.min()) / (s.max() - s.min())
    lab = np.stack([l_lo + (l_hi - l_lo) * t, 45.0 - 10.0 * t, 10.0 + 25.0 * t], axis=-1)
    return _lab_to_rgb8(lab), (ux, uy)


def _white_icon(rgb: np.ndarray) -> np.ndarray:
    """A frame and a ring in white, the repro's own layout: ~20% of the pixels."""
    out = rgb.copy()
    cv2.rectangle(out, (30, 30), (SIDE - 30, SIDE - 30), (255, 255, 255), 18)
    cv2.circle(out, (SIDE // 2, SIDE // 2), 90, (255, 255, 255), 18)
    return out


def _line_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _samples(rgb: np.ndarray, mask: np.ndarray, n: int = 1500, seed: int = 3):
    ys, xs = np.nonzero(mask)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(xs), size=min(n, len(xs)), replace=False)
    return xs[idx] / PX_PER_MM, ys[idx] / PX_PER_MM, rgb_to_lab(rgb[ys[idx], xs[idx]])


# --- The fit -------------------------------------------------------------------

def test_fit_recovers_a_diagonal_sweep_under_a_white_icon():
    """The ruling's case: a full-bleed sweep with white linework drawn on it.
    The plain plane fit of the whole foreground is dragged off by the icon;
    the trimmed-then-consensus fit reads the sweep and leaves the icon out."""
    clean, (ux, uy) = _diagonal_sweep()
    rgb = _white_icon(clean)
    icon = np.all(rgb == 255, axis=-1)
    assert 0.15 <= icon.mean() <= 0.3, "fixture drifted: the icon should be about a fifth"

    ramp = fit_design_ramp_pixels(rgb, np.ones(rgb.shape[:2], bool), PX_PER_MM)
    assert ramp is not None
    assert ramp.channel == 0, "L* carries this sweep"
    assert ramp.r2 >= 0.9
    assert 0.7 <= ramp.inlier_frac <= 0.9, ramp.inlier_frac
    assert ramp.sigma[0] < 2.0
    assert math.hypot(ramp.direction[0] - ux, ramp.direction[1] - uy) < 0.06
    assert _line_diff_deg(ramp.row_angle_deg(), 40.0 + 90.0) <= 2.0

    # The consensus is the sweep: ramp pixels ride, icon pixels do not.
    assert ramp.rides(*_samples(rgb, ~icon))
    assert not ramp.rides(*_samples(rgb, icon))


def test_fit_reads_a_clean_sweep_whole():
    rgb, _ = _diagonal_sweep(angle_deg=-20.0)
    ramp = fit_design_ramp_pixels(rgb, np.ones(rgb.shape[:2], bool), PX_PER_MM)
    assert ramp is not None
    assert ramp.r2 >= 0.99 and ramp.inlier_frac >= 0.98
    assert ramp.span_mm == pytest.approx(80.0 * (abs(math.cos(math.radians(20))) + abs(math.sin(math.radians(20)))), rel=0.05)


def test_fit_declines_two_flat_colours_side_by_side():
    """A step is not a sweep: a plane explains most of its variance (two
    equal halves fit at r² 0.75) but the pixels scatter far from it, and
    the scatter gate refuses — the same reason `region_blobs` and Kent's
    owl are refused on the real fixtures (sigma 9.2 and 5.4 against 4.0)."""
    lab = np.zeros((SIDE, SIDE, 3))
    lab[..., 0] = 40.0
    lab[:, SIDE // 2:, 0] = 70.0
    lab[..., 1], lab[..., 2] = 30.0, 20.0
    rgb = _lab_to_rgb8(lab)
    assert fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM) is None


def test_fit_declines_a_radial_sweep():
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    r = np.hypot(xs - SIDE / 2, ys - SIDE / 2) / (SIDE / 2)
    lab = np.stack([35.0 + 40.0 * np.clip(r, 0, 1), np.full_like(r, 30.0), np.full_like(r, 20.0)], axis=-1)
    rgb = _lab_to_rgb8(lab)
    assert fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM) is None


def test_fit_declines_noise():
    rng = np.random.default_rng(7)
    rgb = rng.integers(0, 256, size=(SIDE, SIDE, 3), dtype=np.uint8)
    assert fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM) is None


def test_gate_constants_are_the_documented_values():
    """A trip-wire, not an opinion: the module docstring's fixture table was
    measured at exactly these; moving one means re-measuring that table."""
    from digitizer_core.design_ramp import DESIGN_RAMP_MIN_SPAN
    assert DESIGN_RAMP_R2_MIN == 0.4
    assert DESIGN_RAMP_MIN_INLIER_FRAC == 0.6
    assert DESIGN_RAMP_MAX_SIGMA == 4.0
    assert DESIGN_RAMP_MIN_SPAN == 9.0


def test_a_channel_that_barely_varies_cannot_win_on_its_own_noise():
    """The two-colour step again, read channel by channel: L* is refused on
    scatter, and a*/b* — constant by construction, varying only by the
    rounding the L* step drags through sRGB — fit that rounding at high r²
    and tiny sigma. The span floor is what keeps them from winning."""
    from digitizer_core.design_ramp import _consensus_plane

    lab = np.zeros((SIDE, SIDE, 3))
    lab[..., 0] = 40.0
    lab[:, SIDE // 2:, 0] = 70.0
    lab[..., 1], lab[..., 2] = 30.0, 20.0
    rgb = _lab_to_rgb8(lab)
    ys, xs = np.nonzero(np.ones((SIDE, SIDE), bool))
    rng = np.random.default_rng(0)
    idx = rng.choice(len(xs), 2500, replace=False)
    a = np.column_stack([xs[idx] / PX_PER_MM, ys[idx] / PX_PER_MM, np.ones(2500)])
    sample = rgb_to_lab(rgb[ys[idx], xs[idx]]).astype(float)
    coef, cons, r2, sigma = _consensus_plane(a, sample[:, 1])
    span = float((a[cons] @ coef).max() - (a[cons] @ coef).min())
    assert span < 2.0, "the fixture's a* should be nearly constant"
    assert fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM) is None


# --- Frames and flattening -----------------------------------------------------

def test_shifted_is_the_same_ramp_in_another_frame():
    rgb, _ = _diagonal_sweep()
    ramp = fit_design_ramp_pixels(rgb, np.ones(rgb.shape[:2], bool), PX_PER_MM)
    moved = ramp.shifted(12.5, -7.25)
    x = np.array([3.0, 40.0, 77.0])
    y = np.array([60.0, 41.0, 2.0])
    assert np.allclose(moved.predict(x - 12.5, y + 7.25), ramp.predict(x, y))
    assert np.allclose(moved.t(x - 12.5, y + 7.25), ramp.t(x, y))
    assert moved.direction == ramp.direction
    assert moved.span_mm == pytest.approx(ramp.span_mm)
    assert moved.row_angle_deg() == ramp.row_angle_deg()


def test_flatten_lab_removes_the_sweep_and_keeps_the_icon():
    clean, _ = _diagonal_sweep()
    rgb = _white_icon(clean)
    icon = np.all(rgb == 255, axis=-1)
    ramp = fit_design_ramp_pixels(rgb, np.ones(rgb.shape[:2], bool), PX_PER_MM)
    lab = rgb_to_lab(rgb.reshape(-1, 3)).reshape(SIDE, SIDE, 3)
    flat = ramp.flatten_lab(lab, PX_PER_MM)
    # The sweep is gone from the ramp pixels (a 35-unit diagonal sweep has a
    # triangular distribution over the square: std ~7)...
    assert lab[~icon, 0].std() > 6.0
    assert flat[~icon, 0].std() < 1.5
    # ...and the icon still stands off the flattened ground by its full step.
    assert flat[icon, 0].mean() - flat[~icon, 0].mean() > 25.0
    # Flattened values are real colours: the mid-ramp Lab, not zero-centred.
    assert 35.0 <= flat[~icon, 0].mean() <= 70.0


# --- The ruling's repro, at Studio defaults ------------------------------------

def test_the_repro_fits_at_studio_defaults():
    """`repro_gradient_white_icon.png` at `PipelineConfig()`: stage 1 floods
    no background (full bleed, BACKGROUND_ABSENT), the white icon is
    foreground, and the plain fit read L* at r² 0.03. The consensus fit
    reads the diagonal sweep on the non-white 78% (2026-09-03: r² 0.80,
    sigma 2.3), which is what the whole ruling hangs on."""
    p = prep(str(PHOTO_DIR / "repro_gradient_white_icon.png"), PipelineConfig())
    ramp = fit_design_ramp(p)
    assert ramp is not None
    assert ramp.r2 >= 0.7
    assert 0.7 <= ramp.inlier_frac <= 0.85
    assert ramp.sigma[ramp.channel] <= 3.0
    assert _line_diff_deg(ramp.row_angle_deg(), 135.0) <= 5.0
    # The angle detector is this fit now, so the two agree by construction.
    assert detect_design_ramp_angle(p) == pytest.approx(ramp.row_angle_deg())


@pytest.mark.parametrize("fixture", ["drone_render.png", "summit_badge.png",
                                     "region_blobs.png", "gradient_ramp_radial.png"])
def test_the_busy_and_radial_fixtures_are_refused(fixture):
    """Every other gradient-classified fixture the module docstring's table
    lists as refused. A pass here would flatten a design the gate was tuned
    to leave alone."""
    p = prep(str(PHOTO_DIR / fixture), PipelineConfig())
    assert fit_design_ramp(p) is None


# --- The angle keeps its legacy fallback; riding needs the colour too -------

def test_a_design_the_gate_refuses_keeps_the_angle_the_plain_fit_gave_it():
    """`region_blobs.png`: five hued blobs, refused by the ramp's scatter gate
    (sigma 9.2). Its shared fill-row angle came from the 2026-08-03 plain fit
    (a-plane r² 0.45, rows at -89.7°) and must survive the gate — the gate
    guards flattening and the design's bands, where a false positive costs
    colour; a shared row angle costs nothing when it is wrong. Without the
    fallback every blob fell to its own PCA angle and the patchwork was back
    (audit, 2026-09-04: jumps 4 -> 11)."""
    from digitizer_core.stage6_blend import legacy_design_ramp_angle

    p = prep(str(PHOTO_DIR / "region_blobs.png"), PipelineConfig())
    assert fit_design_ramp(p) is None
    legacy = legacy_design_ramp_angle(p)
    assert legacy is not None
    assert _line_diff_deg(legacy, -89.7) <= 2.0, legacy
    assert detect_design_ramp_angle(p) == pytest.approx(legacy)


def test_ride_max_delta_e_is_one_shade_step():
    from digitizer_core.design_ramp import DESIGN_RAMP_RIDE_MAX_DELTAE
    from digitizer_core.stage6_blend import SHADE_STEP_DELTAE
    assert DESIGN_RAMP_RIDE_MAX_DELTAE == SHADE_STEP_DELTAE


def test_a_flat_badge_of_another_hue_at_the_sweeps_lightness_does_not_ride():
    """The per-channel tolerance is loose on the channels a hue ramp does not
    fit well, so a badge whose L* matches the sweep could pass it pixel by
    pixel; the mean-colour guard is what refuses it. The badge here is green
    (a* -45) on a sweep whose a* runs 45 -> 35, at the sweep's own L*."""
    clean, _ = _diagonal_sweep()
    rgb = clean.copy()
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    badge = np.hypot(xs - 130, ys - 260) < 45
    # The badge takes the sweep's own L* at each pixel, hue flipped to green.
    lab = rgb_to_lab(rgb.reshape(-1, 3)).reshape(SIDE, SIDE, 3)
    lab[badge, 1] = -45.0
    lab[badge, 2] = 30.0
    rgb = _lab_to_rgb8(lab)
    ramp = fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    assert ramp is not None
    assert ramp.rides(*_samples(rgb, ~badge))
    assert not ramp.rides(*_samples(rgb, badge))
    # And it is the colour guard doing the refusing, not the pixel fraction:
    # with the tolerance opened wide the badge still does not ride.
    mm_x, mm_y, lab_b = _samples(rgb, badge)
    wide = ramp.__class__(**{**ramp.__dict__, "tol": np.full(3, 200.0)})
    assert not wide.rides(mm_x, mm_y, lab_b)
    assert wide.rides(mm_x, mm_y, lab_b, max_delta_e=1e9)


# --- The colour is a profile along the sweep, the gate a plane ----------------

def _hue_arc_sweep() -> tuple[np.ndarray, np.ndarray]:
    """The repro's kind of sweep: a* and b* rotate through an arc (magenta
    to orange) while L* climbs a little. Not planar in a*/b*."""
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    ux, uy = math.cos(math.radians(45.0)), math.sin(math.radians(45.0))
    s = (xs * ux + ys * uy) / PX_PER_MM
    t = (s - s.min()) / (s.max() - s.min())
    ang = np.radians(-20.0 + 100.0 * t)
    lab = np.stack([48.0 + 14.0 * t, 60.0 * np.cos(ang), 60.0 * np.sin(ang)], axis=-1)
    return _lab_to_rgb8(lab), (ux, uy)


def test_a_hue_arc_is_a_sweep_the_plane_gate_passes_and_the_profile_flattens():
    rgb, (ux, uy) = _hue_arc_sweep()
    icon_rgb = _white_icon(rgb)
    icon = np.all(icon_rgb == 255, axis=-1)
    ramp = fit_design_ramp_pixels(icon_rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    assert ramp is not None
    assert ramp.channel == 0, "L* is the planar channel; a* and b* are an arc"
    assert math.hypot(ramp.direction[0] - ux, ramp.direction[1] - uy) < 0.06
    # Around the PLANE the arc scatters; around the PROFILE it does not.
    lab = rgb_to_lab(icon_rgb.reshape(-1, 3)).reshape(SIDE, SIDE, 3)
    assert ramp.sigma[1] < 1.5 and ramp.sigma[2] < 1.5, ramp.sigma
    flat = ramp.flatten_lab(lab, PX_PER_MM)
    assert lab[~icon, 1].std() > 8.0 and lab[~icon, 2].std() > 8.0
    assert flat[~icon, 1].std() < 2.0 and flat[~icon, 2].std() < 2.0, flat[~icon].std(axis=0)
    assert flat[icon, 0].mean() - flat[~icon, 0].mean() > 25.0
    assert ramp.rides(*_samples(icon_rgb, ~icon))
    assert not ramp.rides(*_samples(icon_rgb, icon))


def test_the_ramp_range_is_the_whole_foregrounds():
    """A sample of a square misses a diagonal's far corners; the range must
    not. The synthetic sweep's projection spans the square's diagonal."""
    rgb, (ux, uy) = _diagonal_sweep()
    ramp = fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    corners = np.array([[0, 0], [SIDE - 1, 0], [0, SIDE - 1], [SIDE - 1, SIDE - 1]], float) / PX_PER_MM
    proj = corners @ np.array(ramp.direction)
    assert ramp.lo == pytest.approx(proj.min(), abs=0.05)
    assert ramp.hi == pytest.approx(proj.max(), abs=0.05)
