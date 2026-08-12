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
)


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


def test_the_drifted_sliver_is_resnapped_and_says_so():
    result = run_stages(str(REPRO), PipelineConfig(**CFG))
    assert THREAD_RESNAPPED_AFTER_DRIFT in codes(result)
    w = next(x for x in result.warnings
             if x["code"] == THREAD_RESNAPPED_AFTER_DRIFT)
    # The root-cause doc's own measured number, to two decimals.
    assert w["worst_before_de00"] == pytest.approx(23.87, abs=0.05)
    assert w["worst_after_de00"] < w["worst_before_de00"]
    assert w["count"] == len(w["ids"]) >= 1


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


def test_mean_lab_hides_the_defect_that_the_per_pixel_median_finds():
    """Pins WHY this rule scores per pixel. The traced sliver is bimodal —
    majority near-white, minority pink — so a mean lands on a colour almost no
    pixel carries and reports a 23.9 dE00 error as 5.5."""
    cfg = PipelineConfig(**CFG)
    p = prep(str(REPRO), cfg)
    # Score against the SHIPPED (pre-resnap) assignment by disabling the gate.
    saved = V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
    V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = float("inf")
    try:
        result = run_stages(str(REPRO), cfg)
    finally:
        V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = saved

    chart = chart_for(cfg)
    h, w = p.rgb.shape[:2]
    lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(h, w, 3)

    target = None
    for r, fp in _footprints(result, p):
        if r.thread_number == "2560" and int(fp.sum()) >= V.THREAD_REVALIDATE_MIN_PX:
            target = (r, fp)
            break
    assert target is not None, "the traced Azalea Pink sliver is gone from the fixture"
    r, fp = target

    from skimage.color import deltaE_ciede2000
    px = lab[fp]
    thread_lab = chart.lab[r.thread_index].reshape(1, 3)
    by_mean = float(deltaE_ciede2000(px.mean(axis=0).reshape(1, 3), thread_lab)[0])
    by_pixel = _per_pixel_median_de(px, chart.lab[r.thread_index])

    assert by_mean < 10.0, f"mean-based error unexpectedly large ({by_mean:.2f})"
    assert by_pixel > 20.0, f"per-pixel error unexpectedly small ({by_pixel:.2f})"
    assert by_pixel - by_mean > 15.0


def test_near_white_pixels_really_are_the_majority_of_that_sliver():
    """The physical claim underneath the estimator choice, measured directly
    rather than inferred from the dE00 numbers above."""
    cfg = PipelineConfig(**CFG)
    p = prep(str(REPRO), cfg)
    saved = V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
    V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = float("inf")
    try:
        result = run_stages(str(REPRO), cfg)
    finally:
        V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = saved

    for r, fp in _footprints(result, p):
        if r.thread_number != "2560" or int(fp.sum()) < V.THREAD_REVALIDATE_MIN_PX:
            continue
        rgb = p.rgb[fp].astype(np.int32)
        near_white = int((rgb.min(axis=1) >= 235).sum())
        assert near_white / len(rgb) > 0.5
        return
    pytest.fail("the traced Azalea Pink sliver is gone from the fixture")


# --- the gates --------------------------------------------------------------


def test_the_improvement_gate_turns_the_rule_off_entirely():
    """`inf` improvement required == shipped behaviour, warning and all. The
    other tests in this file rely on this being a true off switch."""
    cfg = PipelineConfig(**CFG)
    saved = V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00
    V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = float("inf")
    try:
        off = run_stages(str(REPRO), cfg)
    finally:
        V.THREAD_REVALIDATE_MIN_IMPROVEMENT_DE00 = saved
    assert THREAD_RESNAPPED_AFTER_DRIFT not in codes(off)

    on = run_stages(str(REPRO), cfg)
    assert THREAD_RESNAPPED_AFTER_DRIFT in codes(on)
    # Same geometry either way — this rule re-matches threads, never outlines.
    assert len(on.regions) == len(off.regions)
    for a, b in zip(on.regions, off.regions):
        assert a.polygon.equals(b.polygon)


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
