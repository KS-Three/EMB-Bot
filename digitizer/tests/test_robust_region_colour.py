"""The colour a SLIC+RAG region hands the palette: a robust centre of its Lab
pixels (the shipped engine since 2026-09-10 — built OFF in PR #445, flipped in
the PR after on Kent's ruling, folded into the code 2026-11-20; before that
the plain mean). Plan
`docs/superpowers/plans/2026-09-10-region-colour.md`; the loss it repairs
is Bridge Bar's disc sewing Limelight for a Sun-yellow artwork (#442's test
run, DOCTRINE 2026-09-10).
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import preflight
from digitizer_core import stage2_photo_segment as s2
from digitizer_core.config import PipelineConfig
from digitizer_core.threads import rgb_to_lab


def _pixels(pure_rgb, n_pure: int, contaminant_rgb, n_cont: int) -> np.ndarray:
    """A region's RGB pixels: `n_pure` of one colour and `n_cont` of another —
    the artwork and the anti-aliased inclusion edges inside its mask."""
    return np.vstack([np.tile(np.asarray(pure_rgb, float), (n_pure, 1)),
                      np.tile(np.asarray(contaminant_rgb, float), (n_cont, 1))])


YELLOW = (251, 235, 65)      # Bridge Bar's disc, measured
BLACK = (0, 0, 0)


def test_the_radius_is_preflights_visible_threshold():
    assert s2.ROBUST_REGION_RADIUS_DE00 == preflight.DELTA_E_VISIBLE == 5.0
    assert s2.ROBUST_REGION_STAT in ("median", "modal_mean")


def test_the_mean_candidate_is_the_pre_flip_expression_byte_for_byte():
    """The RGB mean converted once — NOT the mean of the Lab pixels, which
    is a different number (Lab is not linear in RGB). The first cut of this
    seam averaged in Lab and the photo-lane golden caught it."""
    px = _pixels(YELLOW, 900, BLACK, 100)
    old = rgb_to_lab(px.reshape(-1, 3).mean(axis=0, keepdims=True))[0]
    lab_mean = rgb_to_lab(px).mean(axis=0)
    assert not np.allclose(old, lab_mean, atol=1e-6), "the two means must differ for this test to mean anything"
    assert np.array_equal(s2.region_colour_candidates(px)["mean"], old)


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
    on = s2._region_lab(px, PipelineConfig())
    assert np.array_equal(on, c[s2.ROBUST_REGION_STAT])


def test_a_gradient_region_keeps_a_smooth_centre_under_the_modal_mean():
    """A soft ramp has no single colour; the modal mean averages the pixels
    near the median instead of snapping to one of them, so it sits between
    the median and the mean, never outside the ramp."""
    ramp = np.linspace(120.0, 200.0, 401)
    rgb = np.stack([ramp, ramp * 0.9, np.full_like(ramp, 60.0)], axis=1)
    c = s2.region_colour_candidates(rgb)
    lab = rgb_to_lab(rgb)
    lo, hi = lab[:, 0].min(), lab[:, 0].max()
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


# --- the fixture the defect was found on ---------------------------------------

from pathlib import Path

from digitizer_core.pipeline import digitize
from tests.conftest import PRE_FLIP, TESTDATA

BRIDGE = TESTDATA / "photo" / "logo_bridge_bar.jpg"
# What each statistic hands the palette for the disc, measured by
# `tools/region_colour.py` on 2026-09-10: the mean lands on 6031 Limelight
# (218, 224, 86), the median on 0713 Lemon (2.1 dE00 from the artwork's
# yellow), the modal mean on 0501 Sun (1.0).
DISC_SPOOL = {"median": "0713", "modal_mean": "0501"}


# `robust_region_colour` is a `stage2_photo_segment` statistic: the gradient
# lane's. Since the stage-0 flip + flat soft-edge cure Bridge routes flat, where
# it never runs, so this section holds the pre-flip route (PRE_FLIP) the
# premise lives on (Kent 2026-11-07, "Accept the plan (Recommended)" on #1301's bucket (c); docs/stage0-scale-relative-bucket-c-2026-11-06.md, row 9).
_PRE_FLIP_ROUTE = {k: PRE_FLIP[k] for k in (
    "stage0_scale_relative_grad", "flat_page_fringe_soft_ramp", "flat_ramp_blend_dissolve")}


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, max_colors=6, garment_id="left_chest",
                          **{**_PRE_FLIP_ROUTE, **kw})


def _disc(result):
    """Bridge Bar's yellow disc: the largest region by area."""
    return max(result.regions, key=lambda r: float(r.area_mm2 or 0.0))


def test_the_shipped_engine_sews_the_disc_in_the_artworks_yellow():
    """The loss #442 found, and its repair: the disc is 1.0 dE00 from Sun
    and sewed Limelight (`6031`) when its palette colour was the mean, a
    colour no pixel carries."""
    result, _plan = digitize(BRIDGE, _cfg())
    assert _disc(result).thread_number == DISC_SPOOL[s2.ROBUST_REGION_STAT]
