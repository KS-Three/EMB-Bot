"""`tools/satin_fill_census.py` -- the defect 5 re-measure's two kappas.

The instrument's numbers are only as good as these: the cell kappa must be
scorecard's own corrected sttype (so a figure here reads against a figure the
baseline reports), and the shape kappa must leave out what the tier reader
cannot decide (BAR, NONE) rather than score it.
"""
import numpy as np
import pytest

from tools import satin_fill_census as sfc
from tools.pro_parity import scorecard


def test_cell_kappa_is_scorecards_corrected_sttype():
    pt = np.array([1, 1, 2, 2, 2, 0, 1, 2])
    ot = np.array([1, 2, 2, 2, 1, 0, 1, 2])
    k, ch = sfc._kappa_of(pt, ot)
    raw = float((pt == ot).mean())
    assert ch == pytest.approx(scorecard.type_chance(pt, ot))
    assert k == pytest.approx(scorecard.chance_correct(raw, ch))


def test_cell_kappa_of_a_perfect_copy_is_one_and_of_nothing_is_zero():
    pt = np.array([1, 2, 2, 0, 1])
    assert sfc._kappa_of(pt, pt.copy())[0] == pytest.approx(1.0)
    assert sfc._kappa_of(np.array([], int), np.array([], int)) == (0.0, 0.0)


def _row(ours, pro, area=1.0):
    return {"ours": ours, "pro": pro, "area": area, "lettering": False}


def test_shape_kappa_pools_split_with_satin_and_drops_undecidable_tiers():
    rows = [_row("SPLIT", "SATIN"), _row("FILL", "FILL"), _row("SATIN", "FILL"),
            _row("BAR", "SATIN"), _row("FILL", "NONE")]
    k, n = sfc._shape_kappa(rows)
    assert n == 3, "BAR and NONE say nothing about satin vs fill"
    # 2 of 3 agree; marginals ours satin 2/3 fill 1/3, pro satin 1/3 fill 2/3
    pe = (2 / 3) * (1 / 3) + (1 / 3) * (2 / 3)
    assert k == pytest.approx(round((2 / 3 - pe) / (1 - pe), 3))


def test_area_weighting_lets_one_big_shape_outweigh_many_small():
    rows = [_row("FILL", "FILL", 1000.0), _row("SATIN", "SATIN", 900.0)] + \
           [_row("SATIN", "FILL", 1.0)] * 10
    by_count, _ = sfc._shape_kappa(rows)
    by_area, _ = sfc._shape_kappa(rows, weight=True)
    assert by_area > 0.9 > by_count
