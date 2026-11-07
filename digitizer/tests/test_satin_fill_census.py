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


# ----------------------------------------------- gain attribution (C3, 2026-11-07)
def test_weighted_kappa_without_weights_is_kappa_of_and_weights_duplicate_cells():
    pt = np.array([1, 1, 2, 2, 2, 0, 1, 2])
    ot = np.array([1, 2, 2, 2, 1, 0, 1, 2])
    assert sfc._wkappa(pt, ot) == sfc._kappa_of(pt, ot)
    assert sfc._wkappa(pt, ot, np.ones(8, int))[0] == pytest.approx(sfc._kappa_of(pt, ot)[0])
    w = np.array([2, 0, 1, 3, 1, 1, 0, 2])
    dup_p, dup_o = np.repeat(pt, w), np.repeat(ot, w)
    k, ch = sfc._wkappa(pt, ot, w)
    assert k == pytest.approx(sfc._kappa_of(dup_p, dup_o)[0])
    assert ch == pytest.approx(sfc._kappa_of(dup_p, dup_o)[1])


def test_vector_bootstrap_kappa_matches_the_scalar_one_row_by_row():
    rng = np.random.default_rng(0)
    pt = rng.integers(0, 3, 200)
    ot = np.where(rng.random(200) < 0.7, pt, rng.integers(0, 3, 200))
    w = sfc._boot_weights(np.arange(200) // 10, 25, rng)            # 20 clusters of 10 cells
    assert w.shape == (25, 200) and (w.sum(1) == 200).all()
    for row, k in zip(w, sfc._boot_kappa(pt, ot, w)):
        assert k == pytest.approx(sfc._wkappa(pt, ot, row)[0])


def _ground_with_piece():
    """Region 0: a 36 x 36 ground (rows/cols 2-37) in a 40 x 40 grid of unowned
    cells. Region 1: one of OUR pieces, a 4 x 4 square at rows/cols 24-27."""
    owner = np.full((40, 40), -1)
    owner[2:38, 2:38] = 0
    owner[24:28, 24:28] = 1
    return owner


def test_blob_pattern_reads_keyline_halo_contained_and_edge():
    owner = _ground_with_piece()
    ring = np.zeros((40, 40), bool)
    ring[2:38, 2:38] = True
    ring[3:37, 3:37] = False                                        # the ground's outline, 1 cell wide
    assert sfc.blob_pattern(ring, owner, 0)["pattern"] == "keyline"
    halo = np.zeros((40, 40), bool)
    halo[23:29, 23:29] = True
    halo[24:28, 24:28] = False                                      # a rim round our piece
    assert sfc.blob_pattern(halo, owner, 0)["pattern"] == "halo"
    inside = np.zeros((40, 40), bool)
    inside[8:13, 8:13] = True                                       # 5 x 5, far from both edges
    assert sfc.blob_pattern(inside, owner, 0)["pattern"] == "contained"
    lobe = np.zeros((40, 40), bool)
    lobe[2:12, 28:38] = True                                        # a 10 x 10 corner of the ground
    assert sfc.blob_pattern(lobe, owner, 0)["pattern"] == "edge"


def test_blob_pattern_calls_a_strip_between_outline_and_our_piece_a_band():
    owner = np.full((12, 20), -1)
    owner[2:7, 2:18] = 0                                            # a ground 5 cells tall
    owner[7:10, 2:18] = 1                                           # our piece right under it
    strip = np.zeros((12, 20), bool)
    strip[4, 3:15] = True                                           # 2 cells from both edges
    assert sfc.blob_pattern(strip, owner, 0)["pattern"] == "band"


def test_oracle_split_parts_are_exactly_the_cells_it_cut():
    pt, ot, tboth, owner = _two_regions(3, 4)
    o = sfc.oracle_split(pt, ot, tboth, owner)
    assert len(o["parts"]) == o["blobs"] == 1
    p = o["parts"][0]
    assert (p["region"], p["type"], p["dom"]) == (0, 1, 2)
    assert int(p["mask"].sum()) == o["cells_cut"]
    rb = ot.copy(); rb[p["mask"]] = p["type"]                       # routing + blobs: here routing was right elsewhere
    assert (rb == pt).all()


def test_attribution_summary_shares_and_top3():
    def job(gain, relabel, blobs):
        d = lambda v: {"delta": v, "ci": [v, v]}                    # noqa: E731
        k = {"kappa": 0.4, "chance": 0.5, "ci": [0.3, 0.5]}
        return {m: k for m in sfc.MAPS} | {"gain": d(gain), "relabel": d(relabel), "cut": d(gain - relabel),
                                             "blobs_on_routing": d(0.0), "blobs": blobs,
                                             "regions": [{"k": 0, "id": "S0", "tier": "FILL", "lettering": False,
                                                          "ground": True, "graded_mm2": 100.0}]}
    blob = lambda v, pat: {"k": 0, "add_cut": v, "pattern": pat, "colour": "darker",   # noqa: E731
                           "add_on_routing": v / 2, "ours_right": 0.5, "cells": 10,
                           "pro_type": 1, "ground_type": 2, "half_width_cells": 0.95}
    res = {"jobs": {"a": job(0.4, 0.0, [blob(0.3, "contained"), blob(0.1, "keyline")]),
                    "b": job(0.1, 0.0, [blob(0.1, "contained")]),
                    "c": job(0.0, 0.0, []), "d": job(-0.1, -0.1, [])}}
    sm = sfc.attribution_summary(res)
    assert sm["mean_gain"] == pytest.approx(0.1)
    assert sm["top3_gain"]["jobs"] == ["a", "b", "c"]
    assert sm["top3_gain"]["share"] == pytest.approx(0.5 / 0.4)    # the fourth job pulls the mean down
    assert sm["cut_by_pattern"] == {"contained": 0.8, "keyline": 0.2}
    assert sm["cut_regions"]["n"] == 2 and sm["cut_regions"]["for_50pct"] == 1
    assert sm["on_routing_by_pattern"] == {"contained": 0.8, "keyline": 0.2}
    assert sm["blob_cells_ours_right"] == pytest.approx(0.5)
