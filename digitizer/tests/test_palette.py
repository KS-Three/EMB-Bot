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
    PALETTE_MAX_SWAP_SWEEPS,
    PALETTE_OVERFLOW_K,
    _strictly_better,
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
    # equal weight, capped at 3: every region's own floor is well above the
    # excess_deltae/2 rescue threshold (measured: 2.79-6.62, nothing close to
    # the 2.25 cutoff), so the floor-gated overflow never fires and BUILD
    # stops at the soft cap -- same 3-medoid result the cap always gave, now
    # because nothing here actually qualifies for rescue rather than growth
    # being disallowed outright. Every region still gets its nearest of the
    # selected medoids.
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


# --- 6. Fix #6.1: floor-aware overflow past max_colors -----------------------
# docs/photo-quality-root-cause-2026-08-11.md's drone_render.png finding:
# select_palette's max_colors cap can bind before every region satisfies
# PALETTE_EXCESS_DELTAE, even when the region being force-merged has an
# excellent chart match sitting unused (that fixture's real case: two
# regions with floor 1.98/1.51 force-merged onto "Armour" at ΔE 9.10-9.18).
# These three pin the fix: select_palette may grow past max_k, bounded by
# PALETTE_OVERFLOW_K, but only to rescue a region whose own floor is
# <= excess_deltae/2 -- never to pad the palette for a region no thread is
# actually close to. All floor/ΔE numbers below were measured against the
# real Isacord chart (load_chart()) on 2026-08-11.

_FILLERS_RGB = [(200, 30, 30), (30, 160, 40), (30, 60, 200)]  # 3 mutually
# distant families, each with a decent (not exact) chart match: measured
# floors 4.057 (-> #163 Poinsettia), 1.788 (-> #364 Emerald), 3.362
# (-> #275 Imperial Blue) -- all individually under PALETTE_EXCESS_DELTAE
# (4.5), so once each has its own medoid its own residual satisfies the
# excess bound on its own.


def _overflow_scenario(outlier_rgbs, outlier_area, max_k):
    """3 big, distant, decently-served filler regions (area 9000, so BUILD's
    weighted-cost greedy always picks them before any small-area outlier)
    plus N small (area=outlier_area) outlier regions. Returns (selection,
    labs) so callers can measure a specific outlier's residual."""
    rgbs = np.array(_FILLERS_RGB + list(outlier_rgbs), float)
    labs = rgb_to_lab(rgbs)
    weights = np.array(
        [9000.0] * len(_FILLERS_RGB) + [float(outlier_area)] * len(outlier_rgbs)
    )
    return select_palette(labs, weights, CHART, max_k=max_k), labs


def test_overflow_does_not_fire_for_a_genuinely_hard_to_match_region():
    """A cyan outlier with NO good chart match nearby (measured floor=7.611
    -> #317 Turquoise, well over the excess_deltae/2=2.25 rescue threshold)
    must NOT trigger overflow -- more medoids wouldn't help it, so the
    palette stays at max_k and the outlier keeps riding an existing filler
    medoid. Measured against this scenario: 3 medoids, max_excess_de00
    =29.960 -- the fix must not move either number here, since nothing
    about this region is actually rescuable."""
    sel, labs = _overflow_scenario([(0, 255, 255)], 300.0, max_k=3)
    assert len(sel.medoids) == 3, (
        f"got {len(sel.medoids)} medoids -- overflow fired for a high-floor "
        "region it shouldn't have rescued"
    )
    assert sel.max_excess_de00 == pytest.approx(29.960, abs=0.01)


def test_overflow_rescues_a_genuinely_low_floor_region():
    """A grey outlier that IS an exact chart match (measured floor=0.0 ->
    #308 Silver) -- the same shape as drone_render.png's real defect
    (root-cause doc: 'e.g. Isacord Silver (204,204,204)'). Without the fix
    this force-merges onto a filler medoid at ΔE 33.067 (measured). With
    the fix it must get its own medoid: every region's own floor (fillers
    4.057/1.788/3.362, outlier 0.0) is individually under
    PALETTE_EXCESS_DELTAE, so once the outlier has a medoid the excess
    condition is fully satisfiable -- BUILD stays inside the hard cap and
    the outlier ends up fully rescued, not force-merged (see the inline
    comment below for the actual medoid count and why it isn't the 4 this
    might suggest)."""
    sel, labs = _overflow_scenario([(204, 204, 204)], 300.0, max_k=3)
    # NOT asserting an exact medoid count: pure-greedy BUILD's very first
    # pick (before any medoid exists, res=inf for every region) minimizes
    # total weighted cost across ALL regions at once, not "closest to the
    # biggest region" -- for this scenario that first pick is #209
    # (Titanium), a compromise thread that later becomes redundant once
    # each filler gets its own dedicated match. SWAP only refines at FIXED
    # k (module docstring) and can never prune a now-stranded early pick,
    # so the real, correct-per-design result here is 5 medoids, not a
    # hypothetical minimum of 4 -- still comfortably inside the hard cap.
    # What the design actually promises, and what matters here: bounded
    # growth and a fully rescued outlier.
    assert len(sel.medoids) <= 3 + PALETTE_OVERFLOW_K, (
        f"got {len(sel.medoids)} medoids -- exceeds the hard overflow cap"
    )
    assert sel.max_excess_de00 <= PALETTE_EXCESS_DELTAE, (
        f"max_excess_de00={sel.max_excess_de00:.3f} still over the bound "
        "after the rescue medoid was added"
    )
    from skimage.color import deltaE_ciede2000

    outlier_lab = labs[len(_FILLERS_RGB)]
    outlier_resid = float(
        deltaE_ciede2000(
            outlier_lab.reshape(1, 3),
            CHART.lab[sel.region_spools[len(_FILLERS_RGB)]].reshape(1, 3),
        )[0]
    )
    assert outlier_resid <= PALETTE_EXCESS_DELTAE, (
        f"outlier still {outlier_resid:.3f} ΔE00 from its assigned spool"
    )


def test_overflow_is_bounded_by_palette_overflow_k():
    """Four low-floor outliers (Silver/Black/White/Citrus-yellow -- measured
    floors all 0.0, mutually far apart in Lab, all far from the filler
    hues) but only PALETTE_OVERFLOW_K=3 overflow slots: one must stay
    unresolved. Pins the hard ceiling itself -- len(medoids) never exceeds
    max_k + PALETTE_OVERFLOW_K even when a 4th region would also benefit
    from further growth. Measured against today's code (no overflow at
    all): 3 medoids, max_excess_de00=40.243."""
    outliers = [(204, 204, 204), (0, 0, 0), (255, 255, 255), (255, 255, 0)]
    sel, labs = _overflow_scenario(outliers, 300.0, max_k=3)
    assert len(sel.medoids) == 3 + PALETTE_OVERFLOW_K, (
        "expected the cap to actually bind (4 low-floor outliers competing "
        f"for 3 overflow slots) -- got {len(sel.medoids)}, cap wasn't reached"
    )
    assert sel.max_excess_de00 > PALETTE_EXCESS_DELTAE, (
        "expected at least one region to remain unresolved past the hard "
        f"cap, but max_excess_de00={sel.max_excess_de00:.3f} is within "
        "bound -- the cap didn't actually bind anything in this scenario"
    )


# --- SWAP termination (2026-08-23) -----------------------------------------
# A 2 MP selfie hung the digitizer service for 25+ minutes inside SWAP, with
# the single worker blocked behind it. Cause: "strictly lowers cost" was an
# ABSOLUTE 1e-9, but the two sides of that comparison come from different
# numpy reductions and disagree by ~1 ulp -- 1.9e-9 at the portrait's 9.8e6
# cost, i.e. LARGER than the epsilon. SWAP therefore "improved" forever by
# alternating between two chart spools with bit-identical Lab.


def test_strictly_better_rejects_the_measured_ulp_phantom():
    """The exact cost pair captured from the hung selfie job (N=58, C=398).

    The two values differ by 3.7e-9 -- pure reduction-order noise on a swap
    whose true gain is zero, which the old absolute 1e-9 accepted. This is
    the whole bug in one comparison, which is why it is pinned by value.
    """
    current = 9779152.0087797325
    candidate = 9779152.0087797288
    assert candidate < current, "sanity: the phantom does look like a gain"
    assert candidate < current - 1e-9, (
        "sanity: the gap is ~3.7e-9, wider than the old absolute epsilon, "
        "which is exactly why the old rule accepted this swap forever"
    )
    assert not _strictly_better(candidate, current), (
        "a sub-ulp difference at 9.8e6 scale is noise, not an improvement"
    )


def test_strictly_better_still_accepts_a_real_improvement_at_that_scale():
    """The guard must not be so wide it stops SWAP doing its job: a gain
    that is genuinely perceptible (1e-2 of a ΔE00·px cost) still passes at
    the same 9.8e6 magnitude where the phantom is rejected."""
    current = 9779152.0087797325
    assert _strictly_better(current - 1e-2, current)
    assert _strictly_better(current * 0.999, current)


def test_strictly_better_is_scale_free():
    """Same relative gain, six decades apart, decided the same way -- the
    property the old absolute epsilon lacked."""
    for scale in (1.0, 1e3, 1e6, 1e9):
        assert _strictly_better(scale * (1 - 1e-6), scale), f"scale={scale}"
        assert not _strictly_better(scale * (1 - 1e-15), scale), f"scale={scale}"


def test_select_palette_terminates_on_duplicate_chart_colors():
    """End-to-end regression: a chart holding two bit-identical spools plus
    weights heavy enough to put total cost past ~4.5e6 (where one ulp
    exceeds the old 1e-9) is exactly the selfie's shape. Before the fix this
    call did not return; the sweep cap alone now bounds it, and the relative
    tolerance means it settles on the first sweep.

    Uses the real shipped chart so the duplicate is the one that actually
    bit us, not a synthetic stand-in.
    """
    chart = load_chart()
    dupes = [
        (i, j)
        for i in range(len(chart.lab))
        for j in range(i + 1, min(i + 12, len(chart.lab)))
        if np.array_equal(chart.lab[i], chart.lab[j])
    ]
    assert dupes, (
        "the shipped chart no longer contains bit-identical Lab entries -- "
        "this regression's trigger is gone, so re-derive the fixture rather "
        "than deleting the guard (the tolerance bug is chart-independent)"
    )
    i, j = dupes[0]

    rng = np.random.default_rng(0)
    picks = rng.choice(len(chart.lab), size=58, replace=False)
    labs = chart.lab[picks].astype(np.float64)
    labs[0] = chart.lab[i]
    labs[1] = chart.lab[j]
    weights = np.full(58, 32_000.0)  # ~1.85e6 total, the selfie's weight sum

    sel = select_palette(labs, weights, chart, max_k=12)

    assert 1 <= len(sel.medoids) <= 12 + PALETTE_OVERFLOW_K
    assert len(set(sel.medoids)) == len(sel.medoids), "medoids must be distinct"
    assert len(sel.assignment) == 58


def test_swap_sweep_cap_is_a_backstop_not_a_working_limit():
    """Worst observed need across twelve measured calls is THREE sweeps (on
    a real photo; the committed fixtures all settle on the first). The cap
    must stay far above that -- if it ever has to be raised to make a real
    design work, the tolerance is wrong, not the cap."""
    assert PALETTE_MAX_SWAP_SWEEPS >= 100
