"""`cfg.thread_match_excess_gradient` (built OFF 2026-10-29, ON since
2026-10-30, Kent's flip): MASTER_SCOPE defect 28 part 1, the gradient lane
scored on EXCESS over the loaded spools, as the photo route has been since
2026-08-24. It supersedes his 2026-09-10 ruling that the lane stays on raw
distance. `docs/thread-match-gradient-excess-2026-10-29.md` carries the
52-entry before/after table.

What is pinned:

* OFF is the old check: a gradient design keeps the raw yardstick.
* ON, a gradient design whose every cone is already the best one loaded goes
  quiet, and one with a free swap left on the table still blocks.
* ON never reaches the flat lane, and the one-cone guard still reports.
* It is a GRADING change: the flag has one reader, in preflight, and a real
  gradient fixture's plan is md5-identical OFF and ON.
"""
from __future__ import annotations

import hashlib
import re
from pathlib import Path
from types import SimpleNamespace

import pytest

from digitizer_core import PipelineConfig, StitchPlan
from digitizer_core.preflight import (DELTA_E_CLEARLY_DIFFERENT,
                                      THREAD_MATCH_POOR, run_preflight)
from tests.conftest import TESTDATA, cfg
from tests.test_preflight import _two_spool_photo_scene

EMPTY = StitchPlan(blocks=[], palette=[])


def _scene(design_class: str, swapped: bool):
    result, img, chart, red_i, blue_i = _two_spool_photo_scene(
        assign_swapped=swapped)
    return (SimpleNamespace(regions=result.regions, design_class=design_class),
            img, chart, red_i, blue_i)


def _tm(report):
    return [f for f in report["findings"] if f["code"] == THREAD_MATCH_POOR]


def test_default_is_on():
    assert PipelineConfig().thread_match_excess_gradient is True


@pytest.mark.usefixtures("source_line_grid")
def test_off_keeps_the_gradient_lane_on_raw_distance():
    result, img, *_ = _scene("gradient", swapped=False)
    hits = _tm(run_preflight(
        result, EMPTY, cfg(thread_match_excess_gradient=False), image=img))
    assert hits, "fixture must be non-trivial: raw fires on it"
    assert all(f["extra"]["yardstick"] == "raw" for f in hits)


@pytest.mark.usefixtures("source_line_grid")
def test_on_quiets_a_gradient_design_already_wearing_its_best_cones():
    result, img, *_ = _scene("gradient", swapped=False)
    on = run_preflight(result, EMPTY, cfg(thread_match_excess_gradient=True),
                       image=img)
    assert not _tm(on)


@pytest.mark.usefixtures("source_line_grid")
def test_on_still_blocks_a_free_swap_and_says_which_yardstick():
    result, img, chart, red_i, blue_i = _scene("gradient", swapped=True)
    hits = _tm(run_preflight(result, EMPTY,
                             cfg(thread_match_excess_gradient=True), image=img))
    assert hits and all(f["severity"] == "block" for f in hits)
    for f in hits:
        assert f["extra"]["yardstick"] == "excess"
        assert f["extra"]["excess_delta_e"] > DELTA_E_CLEARLY_DIFFERENT
        assert f["extra"]["better_spool"] in {chart[red_i].number,
                                              chart[blue_i].number}


@pytest.mark.usefixtures("source_line_grid")
@pytest.mark.parametrize("design_class", ["flat", None])
def test_on_never_reaches_a_design_that_is_not_gradient(design_class):
    result, img, *_ = _scene(design_class, swapped=False)
    off = run_preflight(result, EMPTY, cfg(thread_match_excess_gradient=False),
                        image=img)
    on = run_preflight(result, EMPTY, cfg(thread_match_excess_gradient=True),
                       image=img)
    assert on == off
    assert _tm(on) and all(f["extra"]["yardstick"] == "raw" for f in _tm(on))


@pytest.mark.usefixtures("source_line_grid")
def test_on_keeps_the_one_cone_guard():
    """With a single loaded spool every excess is 0 by construction; the
    photo route's `len(loaded) > 1` guard keeps raw scoring, and so must this."""
    result, img, chart, red_i, _b = _scene("gradient", swapped=True)
    for r in result.regions:
        r.thread_index = red_i
        r.thread_number = chart[red_i].number
    hits = _tm(run_preflight(result, EMPTY,
                             cfg(thread_match_excess_gradient=True), image=img))
    assert hits and all(f["extra"]["yardstick"] == "raw" for f in hits)


def test_the_flag_has_one_reader_and_it_is_preflight():
    """Structural half of "no stitch moves": nothing upstream of the grader
    can branch on it."""
    core = Path(__file__).resolve().parents[1] / "digitizer_core"
    readers = sorted(p.name for p in core.rglob("*.py")
                     if re.search(r"\bthread_match_excess_gradient\b",
                                  p.read_text(encoding="utf-8")))
    assert readers == ["config.py", "preflight.py"]


def _plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def test_a_real_gradient_fixture_sews_the_same_and_grades_on_excess():
    """`photo/gradient_ramp_linear.png` (left_chest, 80 mm): every cone is the
    closest one loaded, so raw distance blocks it and excess does not
    (2026-10-29 on 44ecf1cb: D 46 -> A 100, one TMP block + two warns -> none).
    Each arm is digitized on its own config, so the md5 equality is the
    whole pipeline's, not a reuse of one plan."""
    from digitizer_core.pipeline import digitize

    art = TESTDATA / "photo/gradient_ramp_linear.png"
    arms = {}
    for on in (False, True):
        c = cfg(garment_id="left_chest", thread_match_excess_gradient=on)
        result, plan = digitize(art, c)
        assert result.design_class == "gradient"
        arms[on] = (_plan_md5(plan), run_preflight(result, plan, c, image=art))
    assert arms[False][0] == arms[True][0]
    off, on = arms[False][1], arms[True][1]
    assert any(f["severity"] == "block" and f["extra"]["yardstick"] == "raw"
               for f in _tm(off))
    assert not _tm(on)
    assert on["score"] > off["score"]


def test_spool_remedy_grades_the_view_the_check_grades(monkeypatch):
    """`tools.spool_remedy` re-reads on the traced class's grid through
    `_two_tone_view`, as `run_preflight` does. Grading a plain `prep` put a
    White block on gaulke that the shipped check has not carried since
    2026-10-08."""
    from digitizer_core import preflight as pf
    from tools import spool_remedy

    seen = {}
    monkeypatch.setattr(pf, "prep", lambda art, c, design_class=None:
                        seen.setdefault("class", design_class) and "P")
    monkeypatch.setattr(pf, "_two_tone_view",
                        lambda p, plan, c: ("two-tone", p, plan))
    got = spool_remedy.graded_view("art", cfg(),
                                   SimpleNamespace(design_class="gradient"), "PLAN")
    assert seen["class"] == "gradient"
    assert got == ("two-tone", "P", "PLAN")
