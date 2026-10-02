"""`stage6_beanletter.bean_letter` — a letter's ink spines sewn as bean runs
(`docs/superpowers/specs/2026-10-02-bean-letters-design.md`)."""
from __future__ import annotations

import math

from digitizer_core import machine, stitches
from digitizer_core.stage6_beanletter import bean_letter

STEM = [(0.0, 0.0), (0.0, 5.0)]
FOOT = [(0.0, 5.0), (3.0, 5.0)]          # an L: the foot starts where the stem ends


def _pts(runs):
    return [p for r in runs for p in r.points]


def test_only_run_stitches_and_the_report_contract():
    runs, report = bean_letter([STEM, FOOT], "L", entry=None, trim_at_mm=3.0)
    assert runs and {r.kind for r in runs} == {stitches.RUN}
    assert all(r.shape_id == "L" for r in runs)
    assert set(report) >= {"loops", "jumps", "empty", "too_thin", "arcs", "yielded", "strokes"}
    assert report["empty"] is False and report["too_thin"] is False and report["strokes"] == 2


def test_strokes_that_meet_sew_without_a_trim_or_a_jump():
    runs, report = bean_letter([STEM, FOOT], "L", entry=(0.0, 0.0), trim_at_mm=3.0)
    assert not any(r.trim for r in runs) and report["jumps"] == 0
    assert math.dist(runs[0].points[0], (0.0, 0.0)) < 1e-6
    assert math.dist(_pts(runs)[-1], (3.0, 5.0)) < 1e-6


def test_the_letter_is_entered_at_the_end_nearest_the_needle():
    runs, _ = bean_letter([STEM, FOOT], "L", entry=(3.2, 5.1), trim_at_mm=3.0)
    assert math.dist(runs[0].points[0], (3.0, 5.0)) < 1e-6      # the foot's far end, reversed
    assert math.dist(_pts(runs)[-1], (0.0, 0.0)) < 1e-6


def test_each_spine_is_an_odd_number_of_passes_at_the_bean_stitch():
    runs, _ = bean_letter([STEM], "I", entry=(0.0, 0.0), trim_at_mm=3.0)
    pts = _pts(runs)
    per_pass = int(round(5.0 / machine.BEAN_STITCH_MM))
    assert len(pts) == machine.BEAN_PASSES * per_pass + 1
    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(steps) <= machine.BEAN_STITCH_MM * 1.1


def test_separate_strokes_jump_and_a_far_one_trims():
    dot = [(0.0, -6.0), (0.0, -4.5)]                             # an i's dot region would be its own shape; a far stroke here
    runs, report = bean_letter([STEM, dot], "x", entry=(0.0, 5.0), trim_at_mm=3.0)
    assert report["jumps"] == 1 and sum(r.trim for r in runs) == 1
    near = [(0.0, -1.5), (0.0, -0.8)]
    runs, report = bean_letter([STEM, near, [(0.0, -3.5), (0.0, -2.3)]], "x", entry=(0.0, 5.0), trim_at_mm=3.0)
    assert sum(r.trim for r in runs) == 0


def test_a_speck_is_skipped_and_nothing_sewable_reports_empty():
    speck = [(0.0, 0.0), (0.3, 0.0)]
    runs, report = bean_letter([STEM, speck], "I", entry=None, trim_at_mm=3.0)
    assert report["strokes"] == 1
    runs, report = bean_letter([speck], "s", entry=None, trim_at_mm=3.0)
    assert runs == [] and report["empty"] is True
    assert bean_letter([], "s", entry=None, trim_at_mm=3.0)[1]["empty"] is True
