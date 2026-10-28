"""ARTWORK_NOT_SEWN: preflight asks whether the artwork made it into the design.

The 2026-10-27 census (`docs/photo-style-census-2026-10-27.md` items 1-2,
`docs/logo-style-census-2026-10-27.md` items 3-4) sent a 0-stitch design out
at A 100 and a 211-stitch sketch at B 88, because every check read only what
the design sews. `_artwork_reach_findings` reads the ARTWORK instead: stage 1
re-run by preflight, which a rembg cutout never touched.
"""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np

from digitizer_core.pipeline import plan_stitches
from digitizer_core.preflight import (
    _ARTWORK_REACHED_FLOOR,
    ARTWORK_NOT_SEWN,
    _artwork_reach_findings,
    run_preflight,
)
from digitizer_core.stage1_prep import prep

from .conftest import cfg

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
WHITEBG = TESTDATA / "logo_whitebg.png"


class _NoThread:
    """A plan that sews nothing: the census's blank hoop."""

    def iter_runs(self):
        return iter(())


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


def test_a_healthy_design_reaches_its_artwork_and_says_nothing(whitebg):
    plan = plan_stitches(whitebg, cfg())
    report = run_preflight(whitebg, plan, cfg(), image=WHITEBG)
    m = report["metrics"]
    assert m["artwork_checked"] is True
    assert m["artwork_reached_frac"] >= 0.95
    assert ARTWORK_NOT_SEWN not in _codes(report)


def test_a_design_that_sews_nothing_is_blocked(whitebg):
    p = prep(WHITEBG, cfg(), design_class=whitebg.design_class)
    findings, metrics = _artwork_reach_findings(p, whitebg, _NoThread())
    assert metrics["artwork_reached_frac"] == 0.0
    assert [f["code"] for f in findings] == [ARTWORK_NOT_SEWN]
    assert findings[0]["severity"] == "block"
    assert findings[0]["extra"]["artwork_mm2"] > 0


def test_an_accepted_cutout_narrows_the_artwork_it_is_judged_on(whitebg):
    """A background the pipeline removed ON PURPOSE is not missing artwork:
    with a subject mask that keeps nothing there is nothing left to judge."""
    p = prep(WHITEBG, cfg(), design_class=whitebg.design_class)
    result = copy.copy(whitebg)
    result.subject_mask = np.zeros(p.bg_mask.shape, bool)
    findings, metrics = _artwork_reach_findings(p, result, _NoThread())
    assert findings == [] and metrics["artwork_checked"] is False


def test_no_artwork_means_no_check(whitebg):
    p = copy.copy(prep(WHITEBG, cfg(), design_class=whitebg.design_class))
    p.bg_mask = np.ones(p.bg_mask.shape, bool)
    findings, metrics = _artwork_reach_findings(p, whitebg, _NoThread())
    assert findings == [] and metrics["artwork_reached_frac"] is None


def test_the_floor_is_the_measured_one():
    assert _ARTWORK_REACHED_FLOOR == 0.90
