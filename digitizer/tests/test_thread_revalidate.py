"""Fix #6.3 — post-vectorization thread re-validation
(`stage4_vectorize.revalidate_threads`).

The defect, from `docs/photo-quality-root-cause-2026-08-11.md`: a thread is
chosen at stage 2 from the pixels a region occupied THEN, and simplification
here moves the outline. On `repro_gradient_white_icon.png` a ~1.95 x 11.7 mm
sliver was matched to `2560 Azalea Pink` from a genuine pinkish-white
anti-alias blend, then drifted onto the solid white icon interior — 59.5% of
its final pixels are near-white, and its per-pixel dE00 to that thread sits at
23.9 through the p10-p90 range. Nothing between stage 2 and the machine ever
re-asked the question.

The estimator is the load-bearing part and gets its own test: the same shape
scores 5.54 under a MEAN and 23.87 under the per-pixel median the fix uses.
A mean-based version of this rule reports the defect as absent.
"""
from __future__ import annotations

import numpy as np
import pytest

from digitizer_core import stage4_vectorize as V
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage1_prep import prep
from digitizer_core.threads import chart_for, rgb_to_lab
from digitizer_core.warnings_codes import THREAD_RESNAPPED_AFTER_DRIFT

from .conftest import TESTDATA, codes

REPRO = TESTDATA / "photo" / "repro_gradient_white_icon.png"
# The background-existence guards (2026-08-11, bg_border_agreement_min /
# bg_border_rival_min) now correctly refuse to flood this full-bleed fixture
# at defaults — so the Azalea-Pink drift sliver these tests were diagnosed on
# never forms. The guards are orthogonal to the resnap mechanism pinned here;
# disabling them reproduces the exact pipeline state of the diagnosis, same
# pattern as test_enclosed_background.py's repro_cfg.
CFG = dict(
    target_width_mm=80.0,
    garment_id="left_chest",
    bg_border_agreement_min=0.0,
    bg_border_rival_min=0.0,
    # And since 2026-11-06 (`stage0_scale_relative_grad` ON) the repro reads
    # flat (tonal_frac 0.063) and never reaches the gradient lane's merge.
    stage0_scale_relative_grad=False,
)


# 2026-11-20 (bundle roll-forward): the Azalea Pink sliver these tests traced was the RAG
# merge cutting the repro's sweep and leaving a drifted fragment behind. It exists only
# on the engine before the gradient ruling (`design_ramp`, 2026-09-04), `robust_region_colour`
# (2026-09-10) and `snap_region_edges` (2026-09-30), all folded into the code; the file
# used to rebuild that engine with `legacy_engine`. It runs on today's engine now.


def _footprints(result, p):
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    shape = p.rgb.shape[:2]
    for r in result.regions:
        yield r, V._region_footprint(r, shape, cx, cy, p.px_per_mm)


def _per_pixel_median_de(lab_px, thread_lab):
    from skimage.color import deltaE_ciede2000
    samples = V._sample_lab(lab_px)
    return float(np.median(deltaE_ciede2000(
        samples, np.repeat(np.asarray(thread_lab).reshape(1, 3), len(samples), axis=0)
    )))


# --- the traced defect ------------------------------------------------------


# Re-pointed 2026-11-20 (bundle roll-forward): the Azalea Pink sliver (23.87 dE00 before) does not
# exist on today's engine, so the end-to-end "a drifted shape is re-matched and the warning says
# so" claim is read on the screenshot, the fixture whose shapes the pass still re-matches by
# default: 3 shapes, worst 29.75 dE00 before, 23.51 after, at the 50-px floor.
SHOT = TESTDATA / "photo" / "screenshot_phone_ui_golke.jpg"
SHOT_CFG = dict(target_width_mm=80.0, garment_id="left_chest")


def test_a_drifted_shape_is_resnapped_and_says_so():
    result = run_stages(str(SHOT), PipelineConfig(**SHOT_CFG))
    assert THREAD_RESNAPPED_AFTER_DRIFT in codes(result)
    w = next(x for x in result.warnings
             if x["code"] == THREAD_RESNAPPED_AFTER_DRIFT)
    assert w["worst_before_de00"] == pytest.approx(29.75, abs=0.05)
    assert w["worst_after_de00"] == pytest.approx(23.51, abs=0.05)
    assert w["worst_after_de00"] < w["worst_before_de00"]
    assert w["count"] == len(w["ids"]) == 3


def test_no_shape_still_carries_a_grossly_wrong_thread_after_the_fix():
    """The invariant the fix buys: no measurable shape is left further from
    its own pixels than the improvement gate, when a better spool exists."""
    cfg = PipelineConfig(**CFG)
    p = prep(str(REPRO), cfg)
    result = run_stages(str(REPRO), cfg)
    chart = chart_for(cfg)
    h, w = p.rgb.shape[:2]
    lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(h, w, 3)

    worst = 0.0
    for r, fp in _footprints(result, p):
        if int(fp.sum()) < V.THREAD_REVALIDATE_MIN_PX:
            continue
        if r.meta.get("enclosed_background"):
            continue
        worst = max(worst, _per_pixel_median_de(lab[fp], chart.lab[r.thread_index]))
    assert worst < 23.0, f"a shape still sits {worst:.1f} dE00 from its own pixels"


# --- the estimator, which is the whole argument -----------------------------


# `test_mean_lab_hides_the_defect_that_the_per_pixel_median_finds` (the Azalea Pink sliver scores
# 5.5 dE00 by mean, 23.9 per pixel) and `test_near_white_pixels_really_are_the_majority_of_that_
# sliver` were retired 2026-11-20 (bundle roll-forward): the sliver is gone from the fixture on
# today's engine (robust colour, edge snap and the gradient ramp are folded in), and both asserted
# only about it. The estimator they argued for, the per-pixel median CIEDE2000, is the one
# `_per_pixel_median_de` and `test_no_shape_still_carries_a_grossly_wrong_thread...` above use,
# and `tests/test_resnap_mask_matches_grader.py` pins the bimodal-footprint argument on
# `S94b8296d`.


# --- the gates --------------------------------------------------------------


def test_the_improvement_gate_turns_the_rule_off_entirely():
    """`inf` improvement required == shipped behaviour, warning and all. The
    other tests in this file rely on this being a true off switch."""
    # Re-pointed 2026-11-20 to the screenshot (see `SHOT`): the repro has nothing to re-match now.
    cfg = PipelineConfig(**SHOT_CFG)
    saved = V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
    V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = float("inf")
    try:
        off = run_stages(str(SHOT), cfg)
    finally:
        V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = saved
    assert THREAD_RESNAPPED_AFTER_DRIFT not in codes(off)

    on = run_stages(str(SHOT), cfg)
    assert THREAD_RESNAPPED_AFTER_DRIFT in codes(on)
    # Same geometry either way — this rule re-matches threads, never outlines.
    # Matched BY SHAPE ID, not by position: re-matching a thread can change
    # which layer is satin-dominated, and `borders_last` (default ON since
    # 2026-09-01) then orders those layers differently. The claim under test
    # is that no OUTLINE moved, which is a per-shape claim; zipping the two
    # lists positionally was asserting a sew order this rule never promised.
    # On today's engine the screenshot reads 217 regions ON against 218 OFF (measured
    # 2026-11-20): a re-matched shape can leave the layer the fold merges, so ON holds a SUBSET
    # of OFF's shape ids rather than the same set. No surviving outline moves, which is the claim.
    by_id = {r.shape_id: r.polygon for r in off.regions}
    assert {r.shape_id for r in on.regions} <= set(by_id)
    assert len(off.regions) - len(on.regions) in (0, 1)
    for r in on.regions:
        assert r.polygon.equals(by_id[r.shape_id]),             f"{r.shape_id}'s outline moved; this rule only re-matches threads"


def test_enclosed_background_shapes_are_never_resnapped():
    """An enclosed-background shape is unstitched by default and its colour is
    the BACKGROUND's by definition; re-matching it to the bg-coloured pixels it
    covers is a category error, not a fix."""
    cfg = PipelineConfig(**CFG)
    result = run_stages(str(REPRO), cfg)
    tagged = [r for r in result.regions if r.meta.get("enclosed_background")]
    assert tagged, "fixture no longer exercises the enclosed-background path"
    for r in tagged:
        assert "thread_resnapped_de00" not in r.meta


def test_sample_cap_is_deterministic_and_bounded():
    lab = rgb_to_lab(np.arange(3 * 4000).reshape(-1, 3) % 255)
    a = V._sample_lab(lab)
    b = V._sample_lab(lab)
    assert len(a) == V.THREAD_REVALIDATE_SAMPLE_PX
    assert np.array_equal(a, b)
    small = lab[:10]
    assert np.array_equal(V._sample_lab(small), small)
