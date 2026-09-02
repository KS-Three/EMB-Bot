"""Calibration for tools/fill_pitch.py — the row-pitch instrument.

The whole reason this instrument exists is that two readings of one sewn file
disagreed by a factor of two and NEITHER had a committed instrument behind it.
So the calibration is an executable test, not a number remembered in a
docstring — the same discipline test_curve_fidelity.py applies to its own
table.

The load-bearing test is `recovers_several_different_row_spacings`. Recovering
ONE value proves nothing: a stopped clock reports 0.40 correctly. Recovering
four different configured values, each to its own answer, is what separates an
instrument from an echo.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from tools.fill_pitch import (
    MIN_POINTS,
    pass_pitch_mm,
    passes_from_plan,
    measure_image,
)

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
ART = TESTDATA / "logo_whitebg.png"


def _synthetic_rows(pitch_mm, n_rows=40, length_mm=20.0, step_mm=0.4, angle_deg=0.0):
    """A boustrophedon tatami pass with a known row pitch, in mm.

    Direction reverses every row, exactly like a real fill — which is the case
    that breaks a naive angle average and the reason the estimator takes an
    axial mean.
    """
    th = math.radians(angle_deg)
    along = np.array([math.cos(th), math.sin(th)])
    across = np.array([-math.sin(th), math.cos(th)])
    pts = []
    for r in range(n_rows):
        n = max(2, int(length_mm / step_mm))
        ts = np.linspace(0, length_mm, n)
        if r % 2:
            ts = ts[::-1]
        for t in ts:
            p = along * t + across * (r * pitch_mm)
            pts.append((float(p[0]), float(p[1])))
    return pts


@pytest.mark.parametrize("pitch", [0.18, 0.20, 0.40, 0.55, 0.80])
def test_synthetic_pitch_is_recovered(pitch):
    """Ground truth with no engine in the way."""
    got = pass_pitch_mm(_synthetic_rows(pitch))
    assert got is not None, f"{pitch} mm rows should be readable"
    assert got["pitch_mm"] == pytest.approx(pitch, abs=0.02)


@pytest.mark.parametrize("angle", [0.0, 23.0, 45.0, 90.0, 137.0])
def test_recovery_does_not_depend_on_row_ANGLE(angle):
    """A fill sewn at 137 degrees is the same fill.

    The estimator finds its own axis, so nothing here may assume rows run
    along x — and the axial mean is what makes the reversing direction of a
    boustrophedon pass average to the row direction instead of to zero.
    """
    got = pass_pitch_mm(_synthetic_rows(0.40, angle_deg=angle))
    assert got is not None
    assert got["pitch_mm"] == pytest.approx(0.40, abs=0.02)


def test_the_instrument_recovers_several_different_row_spacings():
    """THE calibration. Four configured spacings, four different answers.

    Run through the real engine rather than synthetics, so the path measured is
    one the planner actually emitted — staggered starts, unequal row lengths,
    underlay and all.
    """
    seen = {}
    for row_mm in (0.25, 0.40, 0.60, 0.80):
        rep = measure_image(ART, 80.0, row_mm)
        assert rep["passes_read"] > 0, f"no pass was readable at {row_mm} mm"
        seen[row_mm] = rep["pitch_mm_median"]
        assert rep["pitch_mm_median"] == pytest.approx(row_mm, abs=0.03), (
            f"told {row_mm} mm, read {rep['pitch_mm_median']} mm")
    # And they are genuinely four ANSWERS, not one constant reported four
    # times — the failure mode a single-value calibration cannot see.
    assert len(set(seen.values())) == 4, seen


def test_it_reports_how_much_of_the_design_it_could_actually_read():
    """The honesty ratio, not a nicety.

    The lost estimator's own stated limit was that 16 of ~1,700 passes were
    wide enough to read, so it spoke for the substantial fills only. A median
    over three passes is a different claim from a median over three hundred,
    and a report that hides which one it is invites the next factor-of-two
    argument.
    """
    rep = measure_image(ART, 80.0, 0.40)
    assert rep["passes_total"] >= rep["passes_read"] > 0
    assert len(rep["per_pass"]) == rep["passes_read"]
    for p in rep["per_pass"]:
        assert p["span_mm"] > 0 and p["points"] >= MIN_POINTS


def test_a_pass_too_narrow_to_hold_rows_is_refused_not_guessed():
    """Two rows do not make a period.

    Returning None here is the point: a satin column or a short run must not
    be reported as a fill pitch, because that is precisely how a 0.19 mm
    satin-crossing artifact gets quoted as a tatami row spacing — the
    confusion machine.FILL_ROW_MM's own comment records in the corpus.
    """
    assert pass_pitch_mm(_synthetic_rows(0.40, n_rows=2)) is None
    # A dense straight run: many points, no cross-row structure at all.
    line = [(x * 0.05, 0.0) for x in range(400)]
    assert pass_pitch_mm(line) is None
    # Too few penetrations to profile, however wide the pass is. 10 rows of 2
    # points is 20, under MIN_POINTS — note 30 such rows (60 points) IS read
    # correctly at 0.40, so this guard is about sample size and nothing else.
    sparse = _synthetic_rows(0.40, n_rows=10, length_mm=1.0, step_mm=0.9)
    assert len(sparse) < MIN_POINTS
    assert pass_pitch_mm(sparse) is None


def test_pass_splitting_matches_the_needle_down_definition():
    """Passes are maximal needle-down streaks, the same unit sequence_census
    counts — so the two tools can be quoted about the same file without
    silently meaning different things by "pass"."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import digitize

    _res, plan = digitize(ART, PipelineConfig(target_width_mm=80.0))
    passes = passes_from_plan(plan)
    assert passes and all(len(p) > 0 for p in passes)
    # Every penetration lands in exactly one pass.
    assert sum(len(p) for p in passes) == sum(len(r.points) for _b, r in plan.iter_runs())
