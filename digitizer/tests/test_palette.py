"""Chart-restricted weighted k-medoids palette selection (photo plan row 13,
build-order step 7 — `digitizer_core/palette.py`).

Every numeric assertion here was MEASURED against the shipped Isacord chart
before being pinned (the module docstring in palette.py records the same
numbers): the 8-step brown ramp snaps to 7 scattered spools per-region and
consolidates to 5 one-family browns under k-medoids; the 300px eye region
under a k=2 cap sews 44.5 ΔE00 off its color at weight=area and 6.3 with the
eyes multiplier. The tests assert bands around those measurements, not just
"the function ran".

The flat lane's own regression (plan accept criterion "flat-lane snap
regression-unchanged") is NOT re-pinned here — `test_flat_lane_byte_identical
.py` and `test_stage2_photo_segment.py`'s golden re-run already enforce it,
and this change touches only the photo path (`stage2_photo_segment`), which
those files prove the flat/gradient lanes never enter.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digitizer_core import stage6_blend
from digitizer_core.config import PipelineConfig
from digitizer_core.palette import (
    CLASS_MULTIPLIERS,
    PALETTE_EXCESS_DELTAE,
    region_weight,
    select_palette,
)
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import segment
from digitizer_core.threads import load_chart, rgb_to_lab
from digitizer_core.warnings_codes import PHOTO_PALETTE_SELECTED

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FUR_FIXTURE = TESTDATA / "photo" / "fur_ramp.png"

CHART = load_chart()

# The fur ramp: same endpoints tools/make_palette_fixture.py renders
# (fixture rule F6 — seeded synthetic, no found photographs). Adjacent steps
# measure 5.7-8.2 ΔE00 apart, end-to-end 57.7.
_RAMP_DARK_RGB = np.array([62, 42, 26], float)
_RAMP_LIGHT_RGB = np.array([214, 186, 148], float)
_RAMP_STEPS = 8


def _ramp_labs(steps: int = _RAMP_STEPS) -> np.ndarray:
    rgb = np.array([
        _RAMP_DARK_RGB + (_RAMP_LIGHT_RGB - _RAMP_DARK_RGB) * (i / (steps - 1))
        for i in range(steps)
    ])
    return rgb_to_lab(rgb)


def _hue_deg(lab: np.ndarray) -> float:
    return float(np.degrees(np.arctan2(lab[2], lab[1])))


# --- 1. The step-7 accept criterion: bounded one-family palette --------------


def test_fur_ramp_consolidates_what_nearest_snap_scatters():
    labs = _ramp_labs()
    weights = np.full(_RAMP_STEPS, 1000.0)

    # The OLD behavior (per-region nearest snap), as the scatter baseline:
    # each ramp step independently grabs its own nearest spool. Measured: 7
    # distinct spools for 8 steps — near-duplicates, not a shade plan.
    scattered = {CHART.nearest_index(lab) for lab in labs}
    assert len(scattered) >= 6, (
        f"nearest-snap baseline collapsed to {len(scattered)} spools — the ramp "
        "no longer demonstrates the scatter problem this module exists to fix"
    )

    sel = select_palette(labs, weights, CHART, max_k=12)

    # Plan step 7's own accept band: "F4 fur ramp = 3-5 shades". Measured: 5.
    assert 3 <= len(sel.medoids) <= 5, f"got {len(sel.medoids)} medoids"
    assert len(sel.medoids) < len(scattered)

    # ONE family: every selected thread sits in the warm brown quadrant
    # (measured hues 33-80 deg; window with margin) — no grey/blue/white
    # interloper from a different family.
    for m in sel.medoids:
        hue = _hue_deg(CHART.lab[m])
        assert 15.0 <= hue <= 105.0, (
            f"#{CHART[m].number} {CHART[m].name} (hue {hue:.0f}) is outside the "
            "ramp's color family"
        )
    # ...and they are a RAMP of that family (dark through light), not five
    # near-identical mid-tones. Measured L span: 21 -> 73.
    lightness = sorted(CHART.lab[m][0] for m in sel.medoids)
    assert lightness[-1] - lightness[0] >= 30.0

    # Fidelity: nobody's assignment is worse than the excess bound BUILD
    # stopped at (measured 2.52 on this ramp — well under the 4.5 ceiling).
    assert sel.max_excess_de00 <= PALETTE_EXCESS_DELTAE


# --- 2. The class-weight seam does something real ----------------------------


def test_eye_weight_keeps_a_dedicated_dark_under_a_binding_cap():
    """Plan row 13's whole point of weighting: under a binding color cap the
    palette spends its spools where fidelity lives. Two 9000px tan patches
    plus one 300px near-black eye, cap k=2 (measured geometry, chosen away
    from the decision boundary in both directions):

      weight = area           -> both spools serve the tans; the eye sews
                                 44.5 ΔE00 off its color (a tan eye).
      weight = area * eyes(9) -> the palette keeps a dedicated dark; the
                                 eye lands 6.3 ΔE00 from its color.
    """
    rgbs = np.array([[214, 186, 148], [176, 146, 110], [28, 22, 18]], float)
    labs = rgb_to_lab(rgbs)
    areas = [9000.0, 9000.0, 300.0]

    w_none = np.array([region_weight(a, None) for a in areas])
    sel_none = select_palette(labs, w_none, CHART, max_k=2)
    eye_resid_none = _eye_residual(labs, sel_none)

    w_eyes = np.array([
        region_weight(areas[0], None),
        region_weight(areas[1], None),
        region_weight(areas[2], "eyes"),
    ])
    sel_eyes = select_palette(labs, w_eyes, CHART, max_k=2)
    eye_resid_eyes = _eye_residual(labs, sel_eyes)

    assert eye_resid_none > 20.0, (
        f"area-only weighting kept the eye at {eye_resid_none:.1f} ΔE00 — the cap "
        "isn't binding and this scenario no longer tests the weight interface"
    )
    assert eye_resid_eyes < 10.0, (
        f"eyes multiplier still lost the dark: eye at {eye_resid_eyes:.1f} ΔE00"
    )


def _eye_residual(labs: np.ndarray, sel) -> float:
    from skimage.color import deltaE_ciede2000

    spool = sel.region_spools[2]
    return float(
        deltaE_ciede2000(labs[2].reshape(1, 3), CHART.lab[spool].reshape(1, 3))[0]
    )


def test_subject_weight_keeps_a_dedicated_color_under_a_binding_cap():
    """The subject/background half of the same seam (wired 2026-08-05, via
    `stage2_photo_segment._region_classes` consuming a real rembg mask): the
    identical shape of result as the eyes test above, at the smaller
    subject(2)/background(1) multiplier gap rather than eyes(9)/skin(4.5).
    Two 9000px "background" patches (two different tans — a real rembg cutout
    around a subject rarely leaves a uniform backdrop) plus one 1200px
    "subject" patch, cap k=2 (measured geometry, chosen away from the
    decision boundary — the flip happens between area 1500 and 1600 on this
    exact chart/color triple):

      weight = area                    -> both spools serve the backgrounds;
                                           the subject patch sews 44.5 ΔE00
                                           off its color (a background tan).
      weight = area * {background(1),
                       subject(2)}      -> the subject patch keeps a
                                           dedicated color, landing 6.3 ΔE00
                                           from its own.
    """
    rgbs = np.array([[214, 186, 148], [176, 146, 110], [28, 22, 18]], float)
    labs = rgb_to_lab(rgbs)
    areas = [9000.0, 9000.0, 1200.0]

    w_none = np.array([region_weight(a, None) for a in areas])
    sel_none = select_palette(labs, w_none, CHART, max_k=2)
    subj_resid_none = _eye_residual(labs, sel_none)

    w_cls = np.array([
        region_weight(areas[0], "background"),
        region_weight(areas[1], "background"),
        region_weight(areas[2], "subject"),
    ])
    sel_cls = select_palette(labs, w_cls, CHART, max_k=2)
    subj_resid_cls = _eye_residual(labs, sel_cls)

    assert subj_resid_none > 20.0, (
        f"area-only weighting kept the subject patch at {subj_resid_none:.1f} "
        "ΔE00 — the cap isn't binding and this scenario no longer tests the "
        "weight interface"
    )
    assert subj_resid_cls < 10.0, (
        "subject/background multipliers still lost the subject patch: "
        f"{subj_resid_cls:.1f} ΔE00"
    )


def test_region_weight_carries_the_plan_multipliers():
    assert region_weight(100.0) == 100.0
    assert region_weight(100.0, None) == 100.0
    # Plan row 13's stated ranges: eyes 8-10, skin 4-5, subject 2, background 1.
    assert 8.0 <= CLASS_MULTIPLIERS["eyes"] <= 10.0
    assert 4.0 <= CLASS_MULTIPLIERS["skin"] <= 5.0
    assert CLASS_MULTIPLIERS["subject"] == 2.0
    assert CLASS_MULTIPLIERS["background"] == 1.0
    for cls, mult in CLASS_MULTIPLIERS.items():
        assert region_weight(100.0, cls) == 100.0 * mult
    with pytest.raises(KeyError):
        region_weight(100.0, "eyebrow")  # a typo must never silently weight 1.0


# --- 3. Determinism and degenerate inputs ------------------------------------


def test_selection_is_deterministic():
    labs = _ramp_labs()
    w = np.linspace(500.0, 4000.0, _RAMP_STEPS)
    a = select_palette(labs, w, CHART, max_k=12)
    b = select_palette(labs, w, CHART, max_k=12)
    assert a.medoids == b.medoids
    assert np.array_equal(a.assignment, b.assignment)
    assert a.max_excess_de00 == b.max_excess_de00


def test_single_region_is_exactly_the_old_nearest_snap():
    lab = rgb_to_lab(np.array([[20, 40, 90]], float))  # threads.py's own navy
    sel = select_palette(lab, np.array([1000.0]), CHART, max_k=12)
    assert sel.medoids == [CHART.nearest_index(lab[0])]
    assert sel.region_spools == [CHART.nearest_index(lab[0])]


def test_empty_and_invalid_inputs():
    sel = select_palette(np.empty((0, 3)), np.empty(0), CHART, max_k=12)
    assert sel.medoids == [] and len(sel.assignment) == 0
    with pytest.raises(ValueError):
        select_palette(_ramp_labs(), np.ones(3), CHART, max_k=12)  # length mismatch
    with pytest.raises(ValueError):
        select_palette(_ramp_labs(), np.zeros(_RAMP_STEPS), CHART, max_k=12)


def test_max_colors_cap_binds_across_families():
    # Three distinct families (red / green / blue) x three shades each, all
    # equal weight, capped at 3: the palette must respect the cap, and every
    # region still gets its nearest of the selected medoids.
    fams = [
        [(180, 30, 30), (210, 90, 90), (240, 150, 150)],
        [(30, 140, 30), (90, 180, 90), (150, 220, 150)],
        [(30, 30, 170), (90, 90, 210), (150, 150, 240)],
    ]
    labs = rgb_to_lab(np.array([c for fam in fams for c in fam], float))
    sel = select_palette(labs, np.full(9, 1000.0), CHART, max_k=3)
    assert len(sel.medoids) == 3
    assert len(set(sel.region_spools)) <= 3


# --- 4. Cross-pin against the blend tier's shade step ------------------------


def test_excess_threshold_is_half_the_blend_shade_step():
    """palette.PALETTE_EXCESS_DELTAE is derived from (not imported from)
    stage6_blend.SHADE_STEP_DELTAE — half a shade step, per palette.py's
    docstring. This pin is what keeps the two from drifting apart silently
    if either tier is ever retuned."""
    assert PALETTE_EXCESS_DELTAE == stage6_blend.SHADE_STEP_DELTAE / 2


# --- 5. End to end: the committed fixture through the photo segmenter --------


def test_fur_ramp_fixture_resolves_to_a_bounded_one_family_palette():
    """The step-7 accept criterion measured on the committed fixture through
    the REAL photo path (prep -> SLIC -> RAG -> floor -> k-medoids), not just
    on analytic Lab values. Measured when pinned: 8 regions -> 5 browns
    (Very Dark Brown, Espresso, Pine Park, Pecan, Taupe), max excess 2.34."""
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(FUR_FIXTURE, cfg)
    q = segment(p, cfg)

    assert 3 <= len(q.thread_indices) <= 5, (
        f"fur ramp came out as {len(q.thread_indices)} threads"
    )

    pal = [w for w in q.warnings if w["code"] == PHOTO_PALETTE_SELECTED]
    assert len(pal) == 1
    assert pal[0]["colors"] == len(q.thread_indices)
    # Consolidation actually happened: fewer spools than surviving regions.
    assert pal[0]["colors"] < pal[0]["regions"]
    assert pal[0]["max_excess_de00"] <= PALETTE_EXCESS_DELTAE

    # One family, dark through light — same assertions as the analytic test,
    # now surviving segmentation noise, region means and the min-area floor.
    for ti in q.thread_indices:
        hue = _hue_deg(CHART.lab[ti])
        assert 15.0 <= hue <= 105.0, (
            f"#{CHART[ti].number} {CHART[ti].name} (hue {hue:.0f}) is outside the "
            "fur ramp's family"
        )
    lightness = sorted(CHART.lab[ti][0] for ti in q.thread_indices)
    assert lightness[-1] - lightness[0] >= 30.0


def test_fur_ramp_fixture_segmentation_is_deterministic():
    cfg = PipelineConfig(target_width_mm=80.0)
    p = prep(FUR_FIXTURE, cfg)
    a = segment(p, cfg)
    b = segment(p, cfg)
    assert np.array_equal(a.labels, b.labels)
    assert a.thread_indices == b.thread_indices
