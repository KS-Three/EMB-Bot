"""`cfg.robust_region_colour` — the colour a SLIC+RAG region hands the
palette: the plain mean (OFF, the shipped engine) or a robust centre of its
Lab pixels (ON). Plan `docs/superpowers/plans/2026-09-10-region-colour.md`;
the loss it repairs is Bridge Bar's disc sewing Limelight for a Sun-yellow
artwork (#442's test run, DOCTRINE 2026-09-10).
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import preflight
from digitizer_core import stage2_photo_segment as s2
from digitizer_core.config import PipelineConfig
from digitizer_core.threads import rgb_to_lab


def _pixels(pure_rgb, n_pure: int, contaminant_rgb, n_cont: int) -> np.ndarray:
    """A region's Lab pixels: `n_pure` of one colour and `n_cont` of another —
    the artwork and the anti-aliased inclusion edges inside its mask."""
    rgb = np.vstack([np.tile(np.asarray(pure_rgb, float), (n_pure, 1)),
                     np.tile(np.asarray(contaminant_rgb, float), (n_cont, 1))])
    return rgb_to_lab(rgb)


YELLOW = (251, 235, 65)      # Bridge Bar's disc, measured
BLACK = (0, 0, 0)


def test_default_off_and_the_radius_is_preflights_visible_threshold():
    assert PipelineConfig().robust_region_colour is False
    assert s2.ROBUST_REGION_RADIUS_DE00 == preflight.DELTA_E_VISIBLE == 5.0
    assert s2.ROBUST_REGION_STAT in ("median", "modal_mean")


def test_off_is_the_plain_mean_byte_for_byte():
    px = _pixels(YELLOW, 900, BLACK, 100)
    got = s2._region_lab(px, PipelineConfig(robust_region_colour=False))
    assert np.array_equal(got, px.mean(axis=0))


def test_a_minority_of_edge_pixels_moves_the_mean_and_not_the_robust_centres():
    """Ten percent black edge inside a yellow region: the mean drifts past
    the visible threshold, the median and the modal mean stay on the
    yellow — the Bridge Bar mechanism in one array."""
    from skimage.color import deltaE_ciede2000
    px = _pixels(YELLOW, 900, BLACK, 100)
    yellow = rgb_to_lab(np.asarray([YELLOW], float))[0]
    c = s2.region_colour_candidates(px)
    de = {k: float(deltaE_ciede2000(v.reshape(1, 3), yellow.reshape(1, 3))[0]) for k, v in c.items()}
    assert de["mean"] > preflight.DELTA_E_VISIBLE
    assert de["median"] < 0.01
    assert de["modal_mean"] < 0.01
    on = s2._region_lab(px, PipelineConfig(robust_region_colour=True))
    assert np.array_equal(on, c[s2.ROBUST_REGION_STAT])


def test_a_gradient_region_keeps_a_smooth_centre_under_the_modal_mean():
    """A soft ramp has no single colour; the modal mean averages the pixels
    near the median instead of snapping to one of them, so it sits between
    the median and the mean, never outside the ramp."""
    ramp = np.linspace(120.0, 200.0, 401)
    rgb = np.stack([ramp, ramp * 0.9, np.full_like(ramp, 60.0)], axis=1)
    px = rgb_to_lab(rgb)
    c = s2.region_colour_candidates(px)
    lo, hi = px[:, 0].min(), px[:, 0].max()
    for v in c.values():
        assert lo <= v[0] <= hi


def test_an_empty_region_is_not_an_error():
    c = s2.region_colour_candidates(np.zeros((0, 3)))
    assert set(c) == {"mean", "median", "modal_mean"}


@pytest.mark.parametrize("n_cont", [0, 1, 499])
def test_the_median_side_wins_while_the_artwork_is_the_majority(n_cont):
    px = _pixels(YELLOW, 500, BLACK, n_cont)
    yellow = rgb_to_lab(np.asarray([YELLOW], float))[0]
    assert np.allclose(s2.region_colour_candidates(px)["median"], yellow, atol=1e-6)
