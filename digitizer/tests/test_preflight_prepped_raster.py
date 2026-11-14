"""Preflight grades thread match on the raster the pipeline matched spools to.

With the rembg cutout accepted, stage 1.5's photo prep overwrites `p.rgb`
and stages 2 and 4 pick spools against THOSE pixels. Preflight re-read the
raw artwork and graded against it, so the excess yardstick blocked
"reassign" on 9 of the 14 cutout jobs in the 2026-11-13 sweep that graded
clean on the prepped raster (`preflight._prepped_view`).

CI has no rembg venv, so the cutout seam is stubbed at the level
`test_background_removal.py` stubs it (`pipeline.remove_background_seam`):
an ellipse of subject, the rest background. On `tight_crop_pale_subject`
that grades one `block` (thread 0020, worst dE 33.1) on the raw re-read and
nothing on the prepped raster (worst 10.1) -- measured 2026-11-13.
"""
from pathlib import Path

import cv2
import numpy as np
import pytest

import digitizer_core.pipeline as pipeline_module
from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stage1_photo_prep import photo_prep

IMAGE = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "tight_crop_pale_subject.png"


def _ellipse_cutout(rgb, px_per_mm, cfg):
    h, w = rgb.shape[:2]
    m = np.ones((h, w), np.uint8)
    cv2.ellipse(m, (w // 2, h // 2), (int(w * 0.42), int(h * 0.45)), 0, 0, 360, 0, -1)
    return m.astype(bool), None          # True = background, the seam's contract


def _cfg(**kw) -> PipelineConfig:
    # photo_prep_tone=True: the tone pass is what moves the prepped raster far
    # enough from the raw one for the two grades to disagree, and it is OFF by
    # default since 2026-11-13. With the texture kill alone the raw and the
    # prepped grade agree here (no findings on either), which tests nothing.
    return PipelineConfig(target_width_mm=80.0, forced_class="photo_scene",
                          legibility_check=False, photo_prep_tone=True, **kw)


@pytest.fixture(scope="module")
def prepped_job():
    mp = pytest.MonkeyPatch()
    mp.setattr(pipeline_module, "remove_background_seam", _ellipse_cutout)
    try:
        cfg = _cfg(photo_prep=True, photo_prep_background_removal=True)
        result = run_stages(IMAGE, cfg)
        plan = plan_stitches(result, cfg)
    finally:
        mp.undo()
    return cfg, result, plan


def _thread(findings):
    return [(f["severity"], f["extra"]["thread_number"], f["extra"]["worst_shape_id"])
            for f in findings if f["code"] == pf.THREAD_MATCH_POOR]


def _views(cfg, result, plan):
    view = pf._two_tone_view(pf.prep(IMAGE, cfg, design_class=result.design_class), plan, cfg)
    return view, pf._prepped_view(view, result, cfg)


def test_prep_ran_and_the_result_carries_its_raster(prepped_job):
    cfg, result, plan = prepped_job
    assert any(w["code"] == "PHOTO_PREP_APPLIED" for w in result.warnings)
    assert result.photo_prep_rgb is not None
    view, prepped = _views(cfg, result, plan)
    assert prepped is not None and prepped.rgb is result.photo_prep_rgb
    # The fallback recompute (`_prepped_view` without the carried raster) is
    # the pipeline's raster bit for bit: same order, same mask.
    again = photo_prep(view.rgb, view.bg_mask | ~result.subject_mask,
                       view.px_per_mm, cfg).rgb
    assert np.array_equal(again, result.photo_prep_rgb)


def test_thread_match_is_graded_on_the_prepped_raster(prepped_job):
    cfg, result, plan = prepped_job
    view, prepped = _views(cfg, result, plan)
    raw_findings, raw_worst = pf._thread_match_findings(view, result, plan, cfg)
    on_prepped, prepped_worst = pf._thread_match_findings(prepped, result, plan, cfg)
    # The fixture is only a test if the two rasters disagree: the raw grade
    # is what main reported, and it blocks.
    assert _thread(raw_findings) != _thread(on_prepped)
    assert any(f["severity"] == "block" for f in raw_findings)

    report = pf.run_preflight(result, plan, cfg, image=IMAGE)
    assert _thread(report["findings"]) == _thread(on_prepped)
    m = report["metrics"]
    assert m["thread_worst_delta_e"] == round(prepped_worst, 1)
    # The gap to the raw photo is kept, and it is the raw-raster figure.
    assert m["thread_raw_worst_delta_e"] == round(raw_worst, 1)
    raw_rows = pf._region_color_errors(view, result, plan, cfg)
    assert m["thread_raw_median_delta_e"] == round(
        float(np.median([r["delta_e"] for r in raw_rows])), 1)


def test_fallback_without_the_carried_raster_grades_the_same(prepped_job):
    """A result that lost `photo_prep_rgb` (hand-built, older) recomputes."""
    from dataclasses import replace
    cfg, result, plan = prepped_job
    bare = replace(result, photo_prep_rgb=None)
    a = pf.run_preflight(result, plan, cfg, image=IMAGE)
    b = pf.run_preflight(bare, plan, cfg, image=IMAGE)
    assert a == b


def test_a_job_without_prep_grades_the_raw_re_read_and_adds_no_key():
    cfg = _cfg(photo_prep=False)
    result = run_stages(IMAGE, cfg)
    plan = plan_stitches(result, cfg)
    assert result.photo_prep_rgb is None
    view, prepped = _views(cfg, result, plan)
    assert prepped is None
    report = pf.run_preflight(result, plan, cfg, image=IMAGE)
    raw_findings, raw_worst = pf._thread_match_findings(view, result, plan, cfg)
    assert _thread(report["findings"]) == _thread(raw_findings)
    assert report["metrics"]["thread_worst_delta_e"] == round(raw_worst, 1)
    assert not {"thread_raw_worst_delta_e", "thread_raw_median_delta_e"} & set(report["metrics"])
