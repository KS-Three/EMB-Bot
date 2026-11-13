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

import cv2
import numpy as np

from digitizer_core import run_stages
from digitizer_core.pipeline import plan_stitches
from digitizer_core.preflight import (
    _ARTWORK_REACHED_FLOOR,
    ARTWORK_NOT_SEWN,
    _artwork_reach_findings,
    _held_out_enclosed,
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


# --- Enclosed background the design leaves unsewn on purpose (2026-11-13) ----
#
# `bg_mask` is only the border flood, so a letter's counter and, with "Sew
# white areas" off, every enclosed white area read as artwork nobody sewed.
# Before the fix: "OBOD" at 100 mm read 0.836 and BLOCKED; the ring below with
# `sew_enclosed_white=False` read 0.599 and BLOCKED.

def _wordmark(path: Path) -> Path:
    img = np.full((300, 900, 3), 255, np.uint8)
    cv2.putText(img, "OBOD", (20, 250), cv2.FONT_HERSHEY_SIMPLEX, 9,
                (20, 20, 20), 40, cv2.LINE_AA)
    cv2.imwrite(str(path), img)
    return path


def _ring(path: Path) -> Path:
    img = np.full((400, 400, 3), 255, np.uint8)
    cv2.circle(img, (200, 200), 180, (30, 30, 200), -1)
    cv2.circle(img, (200, 200), 120, (255, 255, 255), -1)
    cv2.imwrite(str(path), img)
    return path


class _LeftHalf:
    """The real plan with every run right of the design's centre dropped:
    half the artwork genuinely left out."""

    def __init__(self, plan):
        self._plan = plan

    def iter_runs(self):
        for b, run in self._plan.iter_runs():
            if run.points and np.mean([pt[0] for pt in run.points]) < 0:
                yield b, run


def _reach(image: Path, c, plan_wrap=None):
    """-> (result, preflight's prep, (findings, metrics))."""
    r = run_stages(image, c)
    plan = plan_stitches(r, c)
    if plan_wrap is not None:
        plan = plan_wrap(plan)
    p = prep(image, c, design_class=r.design_class)
    return r, p, _artwork_reach_findings(p, r, plan)


def _held(p, r) -> np.ndarray:
    x0, y0, x1, y1 = p.art_bbox
    return _held_out_enclosed(p, r, (x0 + x1) / 2.0, (y0 + y1) / 2.0)


def test_letter_counters_left_open_are_not_missing_artwork(tmp_path):
    img = _wordmark(tmp_path / "obod.png")
    c = cfg(target_width_mm=100.0)
    r = run_stages(img, c)
    report = run_preflight(r, plan_stitches(r, c), c, image=img)
    assert report["metrics"]["artwork_reached_frac"] >= _ARTWORK_REACHED_FLOOR
    assert ARTWORK_NOT_SEWN not in _codes(report)


def test_a_counter_set_to_sew_still_counts_as_artwork(tmp_path):
    img = _wordmark(tmp_path / "obod.png")
    r_open, p_open, (_f, open_m) = _reach(img, cfg(target_width_mm=100.0))
    r, p, (findings, sewn_m) = _reach(
        img, cfg(target_width_mm=100.0, sew_enclosed_counters=True))
    assert _held(p_open, r_open).any()
    assert not _held(p, r).any()
    assert sewn_m["artwork_mm2"] > open_m["artwork_mm2"]
    assert findings == []


def test_white_areas_off_leaves_the_ring_hole_out_of_the_artwork(tmp_path):
    img = _ring(tmp_path / "ring.png")
    c = cfg(sew_enclosed_white=False)
    r = run_stages(img, c)
    report = run_preflight(r, plan_stitches(r, c), c, image=img)
    assert report["metrics"]["artwork_reached_frac"] >= _ARTWORK_REACHED_FLOOR
    assert ARTWORK_NOT_SEWN not in _codes(report)


def test_white_areas_on_still_counts_the_ring_hole(tmp_path):
    img = _ring(tmp_path / "ring.png")
    _r, _p, (_f, off_m) = _reach(img, cfg(sew_enclosed_white=False))
    r, p, (findings, on_m) = _reach(img, cfg(sew_enclosed_white=True))
    assert not _held(p, r).any()
    # The hole (radius 120 of 180) is 44% of the disc; sewn, it is artwork.
    assert on_m["artwork_mm2"] > 1.5 * off_m["artwork_mm2"]
    assert findings == []


def test_dropped_artwork_still_blocks_with_the_holes_held_out(tmp_path):
    """Holding the holes out must not neuter the check: half the ring and
    half the word left unsewn still block."""
    ring = _ring(tmp_path / "ring.png")
    _r, _p, (findings, m) = _reach(ring, cfg(sew_enclosed_white=False), _LeftHalf)
    assert m["artwork_reached_frac"] < _ARTWORK_REACHED_FLOOR
    assert [f["code"] for f in findings] == [ARTWORK_NOT_SEWN]
    word = _wordmark(tmp_path / "obod.png")
    _r, _p, (findings, m) = _reach(word, cfg(target_width_mm=100.0), _LeftHalf)
    assert m["artwork_reached_frac"] < _ARTWORK_REACHED_FLOOR
    assert [f["code"] for f in findings] == [ARTWORK_NOT_SEWN]


def test_a_blank_hoop_on_the_wordmark_still_blocks(tmp_path):
    """The letters themselves are never held out, only their counters."""
    img = _wordmark(tmp_path / "obod.png")
    c = cfg(target_width_mm=100.0)
    r = run_stages(img, c)
    p = prep(img, c, design_class=r.design_class)
    findings, m = _artwork_reach_findings(p, r, _NoThread())
    assert m["artwork_reached_frac"] == 0.0 and m["artwork_mm2"] > 0
    assert [f["code"] for f in findings] == [ARTWORK_NOT_SEWN]
