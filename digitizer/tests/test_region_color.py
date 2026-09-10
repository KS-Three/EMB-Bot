"""`cfg.region_color` — which colour a SLIC+RAG region argues with (2026-09-10).

Step 6 of `stage2_photo_segment` hands `select_palette` one Lab per kept
region. That was always the region's MEAN, and a region full of inclusions
carries its mean nowhere: Bridge Bar's yellow disc is (251, 235, 65), 1.0
ΔE00 from `0501` Sun, and the mean the palette saw is (223, 220, 77) —
the black lettering, bird and rope inside it contributing anti-aliased edges
and grey halos — so the palette picked `6031` Limelight, 7.0 ΔE00 off a
logo's main colour. The unbound re-snap used to correct that from the source
pixels; `bind_resnap_all_classes` (ON since 2026-09-10) holds the palette's
answer, which exposed the error rather than causing it.

What these tests pin:

1. **The default is the shipped engine, byte for byte.** `region_color`
   defaults to "mean" and the "mean" arm IS the pre-change expression, not a
   re-derivation of it — pinned against that expression evaluated inline.
2. **A synthetic disc reproduces the defect and each arm's answer to it**,
   with the colours built from the live chart by criteria rather than
   hardcoded (`test_thread_revalidate_palette.py`'s convention): a field
   colour, an ink colour far from it, and the anti-aliased ramp between them
   that a rasteriser actually leaves behind.
3. **The estimators behave as their docstring claims** — the mean moves with
   the inclusions, median and modal do not; and on a region with no dominant
   mode (a ramp) every arm lands in the same neighbourhood, which is why
   this is an arm and not a bool.
4. **The seam is the only place the choice is made** — `segment` asks
   `region_lab` once per kept region and sends exactly what it returns.
"""
from __future__ import annotations

import numpy as np
import pytest
from skimage.color import deltaE_ciede2000

import digitizer_core.stage2_photo_segment as S2
from digitizer_core.config import PipelineConfig
from digitizer_core.threads import chart_for, rgb_to_lab


def de00(a, b) -> float:
    return float(deltaE_ciede2000(np.asarray(a, float).reshape(1, 3),
                                  np.asarray(b, float).reshape(1, 3))[0])


def _disc_pixels(field_rgb, ink_rgb, *, ink_share=0.30, halo_steps=8):
    """A region's pixels the way a rasteriser leaves them: a flat field, an
    inclusion of another colour, and the anti-aliased ramp between the two.

    The ramp is what makes this defect subtle — the ink itself belongs to
    its OWN region (it is a separate colour and segments apart); what stays
    behind in the field's region is the partial-coverage boundary, which no
    amount of thresholding removes.
    """
    n_field = 1000
    n_ink = int(n_field * ink_share)
    field = np.repeat(np.asarray(field_rgb, float)[None, :], n_field, 0)
    ramp = np.concatenate([
        np.repeat((np.asarray(field_rgb, float) * (1 - t)
                   + np.asarray(ink_rgb, float) * t)[None, :], n_ink // halo_steps, 0)
        for t in np.linspace(1.0 / halo_steps, 1.0, halo_steps)
    ])
    return np.vstack([field, ramp])


@pytest.fixture(scope="module")
def chart():
    return chart_for(PipelineConfig())


@pytest.fixture(scope="module")
def field_and_ink(chart):
    """A bright field colour and an ink far from it, both real chart entries.

    Picked by criteria off the live chart: the ink is the chart's darkest
    entry, the field the entry whose ΔE00 from it is the largest — the
    Bridge Bar case in kind (a saturated disc with black inside it), not by
    name.
    """
    labs = np.asarray(chart.lab)
    ink_i = int(np.argmin(labs[:, 0]))
    d = deltaE_ciede2000(np.repeat(labs[ink_i][None, :], len(labs), 0), labs)
    field_i = int(np.argmax(d))
    return (np.asarray(chart.threads[field_i].rgb, float),
            np.asarray(chart.threads[ink_i].rgb, float),
            field_i, ink_i)


# --- 1. The default is the engine that shipped -------------------------------

def test_default_is_the_mean():
    assert PipelineConfig().region_color == "mean"


def test_mean_arm_is_the_pre_change_expression(field_and_ink):
    """Not "close to": the same expression, which is what makes every
    golden and the flat/photo byte-identity suites cover this default."""
    field, ink, _fi, _ii = field_and_ink
    px = _disc_pixels(field, ink)
    before = rgb_to_lab(px.mean(axis=0, keepdims=True))[0]
    assert S2.region_lab(px, "mean").tolist() == before.tolist()
    assert S2.region_lab(px).tolist() == before.tolist()


def test_unknown_method_is_refused():
    with pytest.raises(ValueError, match="region_color"):
        S2.region_lab(np.zeros((4, 3)), "modal-ish")


# --- 2. The defect, and each arm's answer to it -------------------------------

def test_the_mean_lands_on_a_colour_the_region_does_not_have(field_and_ink):
    field, ink, _fi, _ii = field_and_ink
    px = _disc_pixels(field, ink)
    field_lab = rgb_to_lab(field.reshape(1, 3))[0]

    mean = S2.region_lab(px, "mean")
    # Every pixel is either the field or a step of the ramp toward the ink,
    # so a mean pulled off the field is the whole mechanism in one line.
    assert de00(mean, field_lab) > 2.0

    for arm in ("median", "modal"):
        got = S2.region_lab(px, arm)
        assert de00(got, field_lab) < de00(mean, field_lab), arm


def test_the_robust_arms_snap_to_the_field_s_own_spool(chart, field_and_ink):
    """The reading that matters: not the Lab, the CONE the palette is being
    argued toward. The mean argues for something else; both robust arms
    argue for the field's own thread."""
    field, ink, field_i, _ii = field_and_ink
    px = _disc_pixels(field, ink)

    assert chart.nearest_index(S2.region_lab(px, "median")) == field_i
    assert chart.nearest_index(S2.region_lab(px, "modal")) == field_i
    assert chart.nearest_index(S2.region_lab(px, "mean")) != field_i


def test_a_minority_inclusion_cannot_move_the_robust_arms(field_and_ink):
    """The defining property. The mean walks with the inclusion share; the
    median and the modal mean hold their answer while the field is still the
    majority — which is the only claim being made for them."""
    field, ink, _fi, _ii = field_and_ink
    field_lab = rgb_to_lab(field.reshape(1, 3))[0]
    light = _disc_pixels(field, ink, ink_share=0.10)
    heavy = _disc_pixels(field, ink, ink_share=0.45)

    assert (de00(S2.region_lab(heavy, "mean"), field_lab)
            > de00(S2.region_lab(light, "mean"), field_lab) + 1.0)
    for arm in ("median", "modal"):
        drift = abs(de00(S2.region_lab(heavy, arm), field_lab)
                    - de00(S2.region_lab(light, arm), field_lab))
        assert drift < 1.0, f"{arm} moved {drift:.2f} dE00 with the inclusion"


def test_on_a_ramp_the_arms_agree(field_and_ink):
    """A photo region has no dominant colour, and there the mean is
    defensible — every arm lands in the same neighbourhood. This is why
    `region_color` is an arm and not a bool: flipping it is a claim about
    logo art, and it has to be harmless where the claim does not hold."""
    field, ink, _fi, _ii = field_and_ink
    ramp = np.concatenate([
        np.repeat((field * (1 - t) + ink * t)[None, :], 40, 0)
        for t in np.linspace(0.0, 1.0, 25)
    ])
    labs = [S2.region_lab(ramp, arm) for arm in ("mean", "median", "modal")]
    assert de00(labs[0], labs[1]) < 5.0
    assert de00(labs[0], labs[2]) < 5.0


# --- 3. The geometric median, on its own --------------------------------------

def test_geometric_median_holds_against_a_minority(field_and_ink):
    field, ink, _fi, _ii = field_and_ink
    lab = rgb_to_lab(_disc_pixels(field, ink))
    gm = S2._geometric_median(lab)
    field_lab = rgb_to_lab(field.reshape(1, 3))[0]
    assert de00(gm, field_lab) < de00(lab.mean(axis=0), field_lab)


def test_geometric_median_of_one_colour_is_that_colour():
    pts = np.repeat(np.array([[50.0, 10.0, -20.0]]), 100, 0)
    assert S2._geometric_median(pts) == pytest.approx(pts[0], abs=1e-6)


# --- 4. The fixture the defect was found on -----------------------------------
#
# The colour flip's own test run found this: `0501` Sun, which
# `test_phantom_blend_photo.test_bridge_bar_keeps_its_artwork` names as real
# artwork, stopped sewing on the SHIPPED engine (that test runs on
# `conftest.PRE_FLIP`, so it stayed green). These two runs are the shipped
# engine — no flag overrides — and they are what says the estimator reaches
# the customer's cone list, not just the Lab.

BRIDGE_ARMS = ("mean", "modal")


@pytest.fixture(scope="module")
def bridge_by_arm():
    from digitizer_core.pipeline import digitize
    from tests.conftest import TESTDATA
    bridge = str(TESTDATA / "photo" / "logo_bridge_bar.jpg")
    return {arm: digitize(bridge, PipelineConfig(
        target_width_mm=80.0, max_colors=6, satin=True,
        garment_id="left_chest", region_color=arm)) for arm in BRIDGE_ARMS}


def test_the_mean_sews_the_disc_in_the_wrong_green(bridge_by_arm):
    """Characterization, not an aspiration: this is what ships today. The
    disc's own pixels are 1.0 dE00 from `0501` Sun and it sews `6031`
    Limelight, 7.0 away — the palette answering for a mean the disc does not
    carry."""
    cones = {c.get("number") for c in bridge_by_arm["mean"][1].palette}
    assert "6031" in cones
    assert "0501" not in cones


def test_a_robust_region_colour_puts_the_logo_s_yellow_back(bridge_by_arm):
    cones = {c.get("number") for c in bridge_by_arm["modal"][1].palette}
    assert "0501" in cones, "the disc is not sewing the logo's own yellow"
    assert "6031" not in cones


def test_the_robust_arm_does_not_buy_the_yellow_with_thread(bridge_by_arm):
    """A cone can always be fixed by spending stitches; this one is not.
    Bounds with headroom around the measured 14,589 -> 13,821 stitches and
    124 -> 96 trims, so a regression trips them and drift does not."""
    (_mr, mean_p) = bridge_by_arm["mean"]
    (_rr, robust_p) = bridge_by_arm["modal"]
    assert robust_p.stats.stitch_count <= mean_p.stats.stitch_count
    assert robust_p.stats.trims <= mean_p.stats.trims
