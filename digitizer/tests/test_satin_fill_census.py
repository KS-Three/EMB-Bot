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


# ----------------------------------------------------- oracle-split (C3, 2026-11-06)
def _two_regions(blob_rows, blob_cols):
    """Region 0 (cols 0-19): ours and the pro's majority are FILL (2), and the pro
    sews a SATIN (1) blob of blob_rows x blob_cols in it. Region 1 (cols 20-29):
    satin on both sides, a clean region. All cells graded."""
    pt = np.full((12, 30), 2)
    ot = np.full((12, 30), 2)
    owner = np.zeros((12, 30), int)
    owner[:, 20:] = 1
    pt[:, 20:] = 1
    ot[:, 20:] = 1
    pt[2:2 + blob_rows, 3:3 + blob_cols] = 1
    return pt, ot, np.ones((12, 30), bool), owner


def test_oracle_split_cuts_a_ground_along_a_12_cell_blob_and_scores_one():
    pt, ot, tboth, owner = _two_regions(3, 4)                      # 12 cells
    o = sfc.oracle_split(pt, ot, tboth, owner)
    assert o["grounds_cut"] == 1 and o["blobs"] == 1 and o["cells_cut"] == 12
    assert (o["split"] == pt).all()
    assert sfc._kappa_of(pt[tboth], o["split"][tboth])[0] == pytest.approx(1.0)
    # the per-region oracle the same call carries cannot see the blob
    assert sfc._kappa_of(pt[tboth], o["plain"][tboth])[0] < 1.0


def test_oracle_split_leaves_a_9_cell_blob_alone():
    pt, ot, tboth, owner = _two_regions(3, 3)                      # 9 cells
    o = sfc.oracle_split(pt, ot, tboth, owner)
    assert o["grounds_cut"] == 0 and o["blobs"] == 0
    assert (o["split"] == o["plain"]).all()
    assert sfc._kappa_of(pt[tboth], o["split"][tboth])[0] < 1.0


def test_oracle_split_blob_is_per_type_four_connected():
    # two diagonal-touching 6-cell blobs are NOT one 12-cell blob (4-connectivity)
    pt, ot, tboth, owner = _two_regions(0, 0)
    pt[2:4, 3:6] = 1                                               # 6 cells
    pt[4:6, 6:9] = 1                                               # 6 cells, touches at a corner
    o = sfc.oracle_split(pt, ot, tboth, owner)
    assert o["blobs"] == 0
    assert sfc.oracle_split(pt, ot, tboth, owner, floor=6)["blobs"] == 2


def test_oracle_split_cells_outside_any_region_keep_our_type():
    pt, ot, tboth, owner = _two_regions(3, 4)
    owner[:, 20:] = -1
    ot[:, 20:] = 2                                                 # ours disagrees out there
    o = sfc.oracle_split(pt, ot, tboth, owner)
    assert (o["split"][:, 20:] == 2).all()


def test_oracle_split_tie_goes_to_the_type_met_first_like_cell_census():
    pt = np.array([[2, 1], [1, 2]])                                # 2 and 1 tie; 2 is met first
    ot = np.array([[1, 1], [1, 1]])
    o = sfc.oracle_split(pt, ot, np.ones((2, 2), bool), np.zeros((2, 2), int), floor=10)
    assert (o["plain"] == 2).all()


def test_oracle_split_verdict_follows_the_decision_rule():
    assert "worth designing" in sfc.split_verdict(0.55)
    assert "closes" in sfc.split_verdict(0.45)
    assert "no verdict" in sfc.split_verdict(0.50)
