"""Guards for the two cap-order diagnostics' hand-rolled maths.

`tools/cap_order_pro.py` computes its own Spearman rank correlation rather
than taking a scipy dependency, and that number is the whole output — a
reader quotes it as "the pro sews this way". An unguarded diagnostic that
produces a plausible wrong number is a failure mode this repo has already
paid for (DOCTRINE: a crossval script that told its reader to UN-FIX the DST
axis), so the maths is pinned here even though neither tool runs in CI.

Only the pure functions are tested. The rest of both tools needs either a
digitize or the gitignored Drive corpus, and neither belongs in a unit test.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from cap_order_pro import spearman  # noqa: E402


def test_a_perfectly_monotonic_pair_is_plus_one():
    a = np.arange(10, dtype=float)
    assert spearman(a, a * 3.0 + 1.0) == pytest.approx(1.0)


def test_a_perfectly_reversed_pair_is_minus_one():
    a = np.arange(10, dtype=float)
    assert spearman(a, -a) == pytest.approx(-1.0)


def test_it_reads_RANK_not_value():
    """The whole reason for a rank correlation: one wild outlier must not
    drag the coefficient the way it would drag a Pearson r."""
    a = np.arange(10, dtype=float)
    b = a.copy()
    b[-1] = 10_000.0          # still the largest, so the RANKING is unchanged
    assert spearman(a, b) == pytest.approx(1.0)


def test_a_constant_column_is_nan_not_zero():
    """A flat column has no ordering. Zero would read as 'measured, no
    relationship'; nan is the honest answer and is what the caller skips on.
    """
    a = np.arange(10, dtype=float)
    assert np.isnan(spearman(a, np.full(10, 4.0)))


def test_too_few_points_is_nan():
    assert np.isnan(spearman(np.arange(2, dtype=float), np.arange(2, dtype=float)))


def test_ties_are_averaged_not_broken_by_input_order():
    """Two runs at the same position must not get different ranks according
    to which one the decoder happened to emit first — that would let file
    order fake a trend."""
    a = np.arange(6, dtype=float)
    tied = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    shuffled_but_same_ranks = np.array([1.0, 1.0, 2.0, 2.0, 3.0, 3.0])
    assert spearman(a, tied) == pytest.approx(
        spearman(a, shuffled_but_same_ranks))
    # And the averaged-tie value, worked by hand so the constant is checkable
    # rather than copied from the code it guards:
    #   ry = [0.5, 0.5, 2.5, 2.5, 4.5, 4.5]  (each tied pair takes its mean rank)
    #   cov = (5 + 3 + 0 + 0 + 3 + 5) / 6 = 16/6
    #   sx  = sqrt(17.5/6) = 1.707825, sy = sqrt(16/6) = 1.632993
    #   rho = (16/6) / (1.707825 * 1.632993) = 0.956183
    assert spearman(a, tied) == pytest.approx(0.956183, abs=1e-6)


def test_it_agrees_with_a_worked_example():
    """A hand-checkable case, so a refactor cannot quietly change the scale.

    x = 0..4 against y = [0, 2, 1, 4, 3]: two adjacent swaps out of five
    points, d^2 = 0+1+1+1+1 = 4, rho = 1 - 6*4/(5*24) = 0.8.
    """
    x = np.arange(5, dtype=float)
    y = np.array([0.0, 2.0, 1.0, 4.0, 3.0])
    assert spearman(x, y) == pytest.approx(0.8)
