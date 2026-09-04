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
    DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC,
    DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS,
    DESIGN_RAMP_RADIAL_R2_MIN,
    RADIAL_REJECT_CENTER,
    RADIAL_REJECT_KNOTS,
    RADIAL_REJECT_R2,
    fit_design_ramp,
    fit_design_ramp_pixels,
    radial_candidates,
    stitched_foreground,
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


def _radial_sweep(clamp: bool = True, l_lo: float = 35.0, l_step: float = 40.0
                  ) -> tuple[np.ndarray, np.ndarray]:
    """(rgb, disc mask): L* climbs `l_lo` -> `l_lo + l_step` from the centre
    of the square (40, 40 mm) to the inscribed circle's rim. Clamped, the
    corners beyond the rim are flat (the committed fixture's colours, a disc
    on white); unclamped, the sweep continues to the square's corners."""
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    r = np.hypot(xs - SIDE / 2, ys - SIDE / 2) / (SIDE / 2)
    disc = r <= 1.0
    if clamp:
        r = np.clip(r, 0, 1)
    lab = np.stack([l_lo + l_step * r, np.full_like(r, 30.0), np.full_like(r, 20.0)], axis=-1)
    return _lab_to_rgb8(lab), disc


def test_fit_reads_a_radial_sweep():
    """A disc that lightens toward its centre is a sweep too — rings, not a
    plane (2026-09-04). Until then the fit declined it: linear at r² 0.00,
    and the centroid-radial check refusing what the plane could not read."""
    rgb, disc = _radial_sweep()
    ramp = fit_design_ramp_pixels(rgb, disc, PX_PER_MM)
    assert ramp is not None
    assert ramp.kind == "radial" and ramp.direction is None
    assert ramp.channel == 0 and ramp.r2 >= 0.99
    assert math.hypot(ramp.center[0] - 40.0, ramp.center[1] - 40.0) < 0.5, ramp.center
    assert ramp.row_angle_deg() == 0.0
    assert ramp.lo == pytest.approx(0.0, abs=0.3) and ramp.hi == pytest.approx(40.0, abs=0.3)


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
    assert DESIGN_RAMP_RADIAL_R2_MIN == 0.6
    assert DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC == 0.5
    assert DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS == 2


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
                                     "region_blobs.png"])
def test_the_busy_fixtures_are_refused(fixture):
    """Every other gradient-classified fixture the module docstring's table
    lists as refused. A pass here would flatten a design the gate was tuned
    to leave alone."""
    p = prep(str(PHOTO_DIR / fixture), PipelineConfig())
    assert fit_design_ramp(p) is None


def test_the_radial_fixture_fits_radial():
    """`gradient_ramp_radial.png` at Studio defaults: a disc, light at the
    centre, dark at the rim. Linear reads it at r² 0.00; the radial fit
    (2026-09-04) reads L* at 0.999 with the centre on the disc's, and the
    design gets five shades — where before it declined, stage 2 cut the
    disc into a ring and a core, and the ring sewed flat in one thread."""
    from digitizer_core.stage6_blend import design_shade_scheme
    from digitizer_core.threads import chart_for

    p = prep(str(PHOTO_DIR / "gradient_ramp_radial.png"), PipelineConfig())
    ramp = fit_design_ramp(p)
    assert ramp is not None and ramp.kind == "radial"
    assert ramp.channel == 0 and ramp.r2 >= 0.95
    assert ramp.inlier_frac >= 0.95 and ramp.plane_sigma <= 1.0
    x0, y0, x1, y1 = p.art_bbox
    true_centre = ((x0 + x1) / 2.0 / p.px_per_mm, (y0 + y1) / 2.0 / p.px_per_mm)
    assert math.dist(ramp.center, true_centre) < 1.0, (ramp.center, true_centre)
    assert ramp.lo == pytest.approx(0.0, abs=0.3)
    assert ramp.hi == pytest.approx((x1 - x0) / 2.0 / p.px_per_mm, abs=0.5)
    assert ramp.row_angle_deg() == 0.0
    assert detect_design_ramp_angle(p) == 0.0
    n, threads = design_shade_scheme(ramp, chart_for(PipelineConfig()))
    assert n == 5 and len(set(threads)) == 5


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


# --- The radial ramp (2026-09-04) ---------------------------------------------

def _white_frame(rgb: np.ndarray, thickness: int = 12) -> np.ndarray:
    """The repro's frame alone, thinner than `_white_icon`'s: a ring would
    blank a knot of a radial sweep by design (see the ring test below)."""
    out = rgb.copy()
    cv2.rectangle(out, (30, 30), (SIDE - 30, SIDE - 30), (255, 255, 255), thickness)
    return out


def test_fit_recovers_a_radial_sweep_under_a_white_frame():
    """The ruling's case, radial: a full-bleed sweep about the square's
    centre with white linework on it. The trimmed-then-consensus centre
    lands on the true one, the sweep rides and the frame does not. The
    sweep is unclamped so the corners carry it (a sweep that goes flat at
    the rim has 4 of 17 knots blank on a square and is refused on knots)."""
    clean, _ = _radial_sweep(clamp=False, l_step=30.0)
    rgb = _white_frame(clean)
    icon = np.all(rgb == 255, axis=-1)
    assert 0.08 <= icon.mean() <= 0.15, "fixture drifted: the frame should be about a tenth"

    ramp = fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    assert ramp is not None and ramp.kind == "radial"
    assert ramp.channel == 0 and ramp.r2 >= 0.99
    assert 0.8 <= ramp.inlier_frac <= 0.95, ramp.inlier_frac
    assert math.hypot(ramp.center[0] - 40.0, ramp.center[1] - 40.0) < 0.5, ramp.center
    assert ramp.row_angle_deg() == 0.0
    assert ramp.hi == pytest.approx(40.0 * math.sqrt(2.0), abs=0.3), "the range is the corners'"
    assert ramp.rides(*_samples(rgb, ~icon))
    assert not ramp.rides(*_samples(rgb, icon))


def test_a_concentric_ring_icon_blanks_one_knot_and_the_sweep_still_fits():
    """A white ring drawn on the disc sits in one bin of the radius: that
    bin's consensus fraction falls under `DESIGN_RAMP_RADIAL_KNOT_MIN_FRAC`
    and it reads blank, one of the two the gate allows."""
    clean, disc = _radial_sweep()
    rgb = clean.copy()
    cv2.circle(rgb, (SIDE // 2, SIDE // 2), 90, (255, 255, 255), 12)
    icon = np.all(rgb == 255, axis=-1) & disc
    fits = radial_candidates(rgb, disc, PX_PER_MM)
    l_fit = fits[0]
    assert l_fit.blank_knots == 1 and l_fit.passes, (l_fit.blank_knots, l_fit.reason)
    ramp = fit_design_ramp_pixels(rgb, disc, PX_PER_MM)
    assert ramp is not None and ramp.kind == "radial"
    assert math.hypot(ramp.center[0] - 40.0, ramp.center[1] - 40.0) < 0.5
    assert ramp.rides(*_samples(rgb, disc & ~icon))
    assert not ramp.rides(*_samples(rgb, icon))


def test_summit_is_refused_on_knots_and_the_owl_on_r2():
    """The two busy fixtures whose radial fits clear the most: `summit_badge`'s
    L* line fits the ring around its emblem at r² 0.93 — the emblem IS the
    centre, so 10 of 17 bins hold no sweep — and Kent's owl's best channel
    reads 0.45 against the 0.6 floor. Both stay refused, each by the gate
    named here; moving either number means re-measuring the docstring's
    table."""
    summit = prep(str(PHOTO_DIR / "summit_badge.png"), PipelineConfig())
    fits = radial_candidates(summit.rgb, stitched_foreground(summit), summit.px_per_mm)
    l_fit = fits[0]
    assert l_fit.r2 >= DESIGN_RAMP_RADIAL_R2_MIN
    assert l_fit.blank_knots > DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS, l_fit.blank_knots
    assert l_fit.reason == RADIAL_REJECT_KNOTS
    assert not any(f.passes for f in fits)
    assert fit_design_ramp(summit) is None

    owl = prep(str(PHOTO_DIR / "owl_kent.jpg"), PipelineConfig())
    fits = radial_candidates(owl.rgb, stitched_foreground(owl), owl.px_per_mm)
    assert max(f.r2 for f in fits) < DESIGN_RAMP_RADIAL_R2_MIN
    assert all(f.reason == RADIAL_REJECT_R2 for f in fits)
    assert fit_design_ramp(owl) is None


def test_a_linear_sweeps_radial_centre_lands_off_the_design():
    """A plane is a radial ramp whose centre sits at infinity: Gauss-Newton
    from the centroid walks the centre away at the step cap, the foreground
    starts many sweeps' lengths from it (`lo` against `hi - lo`), and the
    scale gate refuses it — which is what keeps the radial model from ever
    claiming a linear sweep it fits by a hair. The linear fit is untouched
    by the radial one."""
    rgb, (ux, uy) = _diagonal_sweep()
    fits = radial_candidates(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    l_fit = fits[0]
    assert l_fit.r2 >= DESIGN_RAMP_RADIAL_R2_MIN, "the plane IS fitted well by a far centre"
    assert not l_fit.center_near
    assert l_fit.lo > 3.0 * (l_fit.hi - l_fit.lo), (l_fit.lo, l_fit.hi)
    assert math.hypot(l_fit.center[0] - 40.0, l_fit.center[1] - 40.0) > 200.0, l_fit.center
    assert l_fit.reason == RADIAL_REJECT_CENTER
    ramp = fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    assert ramp is not None and ramp.kind == "linear" and ramp.center is None
    assert math.hypot(ramp.direction[0] - ux, ramp.direction[1] - uy) < 0.06


def test_a_radial_sweep_that_goes_flat_at_the_rim_is_refused_on_knots():
    """The committed fixture's colours on a SQUARE foreground: the corners
    beyond the rim are flat, not on the line, and the outer bins of the
    radius read blank — the knot rule refuses, as it refuses the summit."""
    rgb, _disc = _radial_sweep(clamp=True)
    fits = radial_candidates(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM)
    assert fits[0].blank_knots > DESIGN_RAMP_RADIAL_MAX_BLANK_KNOTS
    assert fits[0].reason == RADIAL_REJECT_KNOTS
    assert fit_design_ramp_pixels(rgb, np.ones((SIDE, SIDE), bool), PX_PER_MM) is None


def test_shifted_carries_a_radial_ramps_centre():
    rgb, disc = _radial_sweep()
    ramp = fit_design_ramp_pixels(rgb, disc, PX_PER_MM)
    assert ramp.kind == "radial"
    moved = ramp.shifted(12.5, -7.25)
    assert moved.kind == "radial"
    assert moved.center == pytest.approx((ramp.center[0] - 12.5, ramp.center[1] + 7.25))
    # Radii are frame-invariant: the range and the line in `planes` stay.
    assert (moved.lo, moved.hi) == (ramp.lo, ramp.hi)
    assert np.array_equal(moved.planes, ramp.planes)
    x = np.array([3.0, 40.0, 77.0])
    y = np.array([60.0, 41.0, 2.0])
    assert np.allclose(moved.raw(x - 12.5, y + 7.25), ramp.raw(x, y))
    assert np.allclose(moved.predict(x - 12.5, y + 7.25), ramp.predict(x, y))
    assert np.allclose(moved.t(x - 12.5, y + 7.25), ramp.t(x, y))
    assert moved.row_angle_deg() == ramp.row_angle_deg() == 0.0


def test_flatten_lab_removes_the_rings_and_keeps_the_icon():
    clean, disc = _radial_sweep()
    rgb = clean.copy()
    cv2.circle(rgb, (SIDE // 2, SIDE // 2), 90, (255, 255, 255), 12)
    icon = np.all(rgb == 255, axis=-1) & disc
    sweep = disc & ~icon
    ramp = fit_design_ramp_pixels(rgb, disc, PX_PER_MM)
    assert ramp.kind == "radial"
    lab = rgb_to_lab(rgb.reshape(-1, 3)).reshape(SIDE, SIDE, 3)
    flat = ramp.flatten_lab(lab, PX_PER_MM)
    # A 40-unit sweep over a disc, uniform in area: std of the radius is
    # ~0.24 of it, so L* scatters ~9 before and nothing after.
    assert lab[sweep, 0].std() > 6.0
    assert flat[sweep, 0].std() < 1.5, flat[sweep, 0].std()
    assert flat[icon, 0].mean() - flat[sweep, 0].mean() > 25.0
    assert 35.0 <= flat[sweep, 0].mean() <= 75.0
    # The rings are gone: the centre and the rim read the same colour.
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    r_mm = np.hypot(xs - SIDE / 2, ys - SIDE / 2) / PX_PER_MM
    core, rim = sweep & (r_mm < 8.0), sweep & (r_mm > 32.0)
    assert abs(flat[core, 0].mean() - flat[rim, 0].mean()) < 1.5


# --- The centre is near on the sweep's scale, not inside a box (review, 2026-09-04)

def _partial_disc(cx_px: float, cy_px: float, radius_px: float) -> tuple[np.ndarray, np.ndarray]:
    """(rgb, fg): the part of the square within `radius_px` of (cx, cy), L*
    climbing 35 -> 75 from that centre to the rim — a sweep whose centre
    can sit on the foreground's edge, or at its corner."""
    ys, xs = np.mgrid[0:SIDE, 0:SIDE]
    r = np.hypot(xs - cx_px, ys - cy_px) / radius_px
    fg = r <= 1.0
    lab = np.stack([35.0 + 40.0 * np.clip(r, 0, 1), np.full_like(r, 30.0), np.full_like(r, 20.0)], axis=-1)
    return _lab_to_rgb8(lab), fg


def test_a_half_disc_sunrise_with_its_centre_on_the_edge_fits_radial():
    """A sunrise: a half-disc whose centre sits ON its flat edge, a common
    logo class. The fitted centre lands a hair either side of that edge —
    (39.998, 40.0004) on the review's copy — and a bounding-box test on it
    was knife-edge: the whole design refused. The rule is scale: the centre
    is far only when the foreground starts farther from it than the sweep
    is long, and a half-disc starts AT it."""
    cx, cy = SIDE / 2.0, SIDE - 1.0
    rgb, fg = _partial_disc(cx, cy, SIDE / 2.0)
    assert 0.35 <= fg.mean() <= 0.45, "a half-disc is 39% of the square"
    l_fit = radial_candidates(rgb, fg, PX_PER_MM)[0]
    assert l_fit.center_near and l_fit.lo < 1.0 and l_fit.passes, (l_fit.lo, l_fit.reason)
    ramp = fit_design_ramp_pixels(rgb, fg, PX_PER_MM)
    assert ramp is not None and ramp.kind == "radial"
    assert math.hypot(ramp.center[0] - cx / PX_PER_MM, ramp.center[1] - cy / PX_PER_MM) < 0.5, ramp.center
    assert ramp.r2 >= 0.99 and ramp.row_angle_deg() == 0.0


def test_a_corner_glow_with_its_centre_at_the_corner_fits_radial_never_linear():
    """A quarter-disc glow from the square's corner: the centre IS the
    corner, the fitted one lands a hundredth of a millimetre outside the
    foreground, and a plane fits the quarter-disc well enough to pass the
    linear gate with a diagonal direction — under the bounding-box rule the
    radial fit was refused and the design got straight diagonal bands
    (review, 2026-09-04). Radial wins outright now."""
    from digitizer_core.design_ramp import _consensus_plane

    rgb, fg = _partial_disc(0.0, 0.0, SIDE - 1.0)
    assert 0.7 <= fg.mean() <= 0.85, "a quarter-disc is 79% of the square"
    l_fit = radial_candidates(rgb, fg, PX_PER_MM)[0]
    assert l_fit.center_near and l_fit.lo < 1.0 and l_fit.passes, (l_fit.lo, l_fit.reason)
    # The plane the linear path would have taken: it clears the linear gate.
    ys, xs = np.nonzero(fg)
    rng = np.random.default_rng(0)
    idx = rng.choice(len(xs), 2500, replace=False)
    a = np.column_stack([xs[idx] / PX_PER_MM, ys[idx] / PX_PER_MM, np.ones(2500)])
    _coef, _cons, r2_plane, _sigma = _consensus_plane(a, rgb_to_lab(rgb[ys[idx], xs[idx]])[:, 0].astype(float))
    assert r2_plane >= DESIGN_RAMP_R2_MIN, r2_plane
    assert l_fit.r2 > r2_plane
    ramp = fit_design_ramp_pixels(rgb, fg, PX_PER_MM)
    assert ramp is not None and ramp.kind == "radial", "never the plane's diagonal bands"
    assert math.hypot(*ramp.center) < 0.5, ramp.center
    assert ramp.hi == pytest.approx((SIDE - 1.0) / PX_PER_MM, abs=0.3)


@pytest.mark.parametrize("fixture", ["gradient_ramp_linear.png", "repro_gradient_white_icon.png"])
def test_a_linear_designs_radial_centre_is_far(fixture):
    """The two linear designs the module's table lists: their L* radial fits
    clear the r² floor (a far centre fits a plane) and are refused because
    the foreground starts many sweeps' lengths from the centre — the linear
    fixture's `lo` 15 times its sweep, the repro's 4 times. Both fit linear,
    byte for byte what they were."""
    p = prep(str(PHOTO_DIR / fixture), PipelineConfig())
    fits = radial_candidates(p.rgb, stitched_foreground(p), p.px_per_mm)
    l_fit = fits[0]
    assert l_fit.r2 >= DESIGN_RAMP_RADIAL_R2_MIN
    assert not l_fit.center_near
    assert l_fit.lo > 3.0 * (l_fit.hi - l_fit.lo), (l_fit.lo, l_fit.hi)
    assert l_fit.reason == RADIAL_REJECT_CENTER
    assert not any(f.passes for f in fits)
    ramp = fit_design_ramp(p)
    assert ramp is not None and ramp.kind == "linear" and ramp.center is None
