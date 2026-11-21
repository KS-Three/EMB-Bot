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

from .conftest import PRE_FLIP, TESTDATA


# 2026-11-20 (bundle roll-forward): the numbers in this file were read on the engine before
# six colour switches were folded into the code (`docs/flag-history/tier-b3-colour.md`);
# `legacy_engine` patched their False paths back. They are re-read on today's engine.

# Re-pointed 2026-11-20 (bundle roll-forward): the screenshot (score 0, raw -272, -62 under the
# 2026-09-10 patch floor) is no longer floored on today's engine (score 22). Bridge is: its raw
# score is -38 in `testdata/corpus_scorecard_baseline.json` (2026-11-12, left_chest, defaults).
FLOORED = "photo/logo_bridge_bar.jpg"
CLEAN = "logo_alpha.png"                          # score 100, raw 100


@lru_cache(maxsize=None)
def _report(fixture: str):
    art = TESTDATA / fixture
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **PRE_FLIP)
    # PRE_FLIP: the colour flags Kent flipped ON on 2026-09-10 (the
    # bundle's four and `robust_region_colour`) are held OFF here because
    # this file documents a fact of the engine before those flips
    # (conftest.PRE_FLIP says why).
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
    # The screenshot read -272 on 2026-09-06 and -62 since 2026-09-10 (the pre-flip
    # engine; `THREAD_MATCH_POOR`'s patch floor, quality review item 11, took its sub-5 mm2
    # shards out of the judging) -- under water, three blocking findings deep, which is
    # exactly the move `raw_score` exists to show (the printed 0 did not). Re-pointed
    # 2026-11-20 to bridge: -38 in the scorecard baseline (defaults), -158 here under the
    # still-held `PRE_FLIP` flags (measured 2026-11-20).
    assert rep["metrics"]["raw_score"] == pytest.approx(-158, abs=30)


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
