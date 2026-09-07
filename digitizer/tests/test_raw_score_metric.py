"""The unclamped score rides out as a metric, so a floored design can move.

`run_preflight` prints `max(0, 100 - 30*blocks - 12*warns)`. The clamp is
right for an operator — a negative grade means nothing — but it makes the
metric SATURATE. Measured 2026-09-06 (`tools/floor_depth.py`): **12 of the
corpus's 52 design/garment combos sit on exactly 0, with true scores from
-272 to -38** — a 234-point spread behind one printed value.
`screenshot_phone_ui_golke` must clear about ELEVEN blocking findings before
`score` moves at all, so a fix clearing ten of them reads as doing nothing.

`raw_score` changes no grade and re-bases nothing (that would be a product
call). It makes the magnitude visible: `corpus_scorecard.diff` compares
`report["metrics"]` and reports any move past 5%.
"""

from functools import lru_cache

import pytest

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

from .conftest import TESTDATA

FLOORED = "photo/screenshot_phone_ui_golke.jpg"   # score 0, raw -272
CLEAN = "logo_alpha.png"                          # score 100, raw 100


@lru_cache(maxsize=None)
def _report(fixture: str):
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    return pf.run_preflight(result, plan, cfg, image=art)


@pytest.mark.parametrize("fixture", [FLOORED, CLEAN])
def test_raw_score_is_present_and_numeric(fixture):
    assert isinstance(_report(fixture)["metrics"]["raw_score"], int)


def test_an_unfloored_design_reports_the_same_number_twice():
    """Above the floor the clamp does nothing, so the two must agree — which
    is what makes `raw_score` safe to read as a drop-in for `score`."""
    rep = _report(CLEAN)
    assert rep["metrics"]["raw_score"] == rep["score"]


def test_a_floored_design_reports_its_real_depth():
    """The point of the metric. `score` says 0 for every floored design;
    `raw_score` says how far under water this one is."""
    rep = _report(FLOORED)
    assert rep["score"] == 0
    assert rep["metrics"]["raw_score"] < 0
    assert rep["metrics"]["raw_score"] == pytest.approx(-272, abs=30)


@pytest.mark.parametrize("fixture", [FLOORED, CLEAN])
def test_raw_score_is_derivable_from_the_findings(fixture):
    """Re-derived from the findings rather than trusting the field, so the
    check and its test do not share an implementation."""
    rep = _report(fixture)
    want = 100 - sum(pf._DEDUCT.get(f["severity"], 0) for f in rep["findings"])
    assert rep["metrics"]["raw_score"] == want


@pytest.mark.parametrize("fixture", [FLOORED, CLEAN])
def test_the_clamped_score_and_grade_are_untouched(fixture):
    """This is a metric, not a scoring change. `score` stays clamped and the
    grade bands are unmoved — un-clamping either would re-base every grade in
    the scorecard, which is a product call nobody has taken."""
    rep = _report(fixture)
    assert rep["score"] == max(0, rep["metrics"]["raw_score"])
    assert rep["grade"] == ("A" if rep["score"] >= 90 else
                            "B" if rep["score"] >= 75 else
                            "C" if rep["score"] >= 60 else
                            "D" if rep["score"] >= 40 else "F")
