"""The element-level instrument must count what a digitizer chose, not flatter.

Pure-logic guards on `tools/pro_parity/blockcensus.py`: the census math
(blocks / threads / returns / cut paths), the element counting, the layering
check, and the grouping join with its gate-4 chance correction. Plus one
real-data pin against a committed pro file so the census cannot silently
drift from the numbers the region-identification plan quotes.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from tools.pro_parity.blockcensus import (
    MIN_COMP_MM2,
    _kappa,
    census_structure,
    count_components,
    grouping_join,
    layering_stats,
    paint_block_masks,
    paint_polygon_masks,
    palette_is_synthetic,
    runs_to_segs,
)
from tools.pro_parity.prep_all import GREYS, decode

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


# ------------------------------------------------------------ census math
def test_thread_returns_counted_per_block():
    """Blocks [A, B, A] = one return: the third stop reloads a used thread."""
    blocks = [[[(0, 0), (1, 0)]]] * 3
    breaks = [["start"], ["color"], ["color"]]
    threads = [(255, 0, 0), (0, 0, 255), (255, 0, 0)]
    c = census_structure(blocks, breaks, threads)
    assert c["blocks"] == 3
    assert c["threads"] == 2
    assert c["thread_returns"] == 1
    assert c["return_share"] == pytest.approx(1 / 3, abs=1e-3)
    assert c["thread_source"] == "palette"
    assert c["thread_seq"] == [0, 1, 0]   # the base->detail->base pattern


def test_one_block_per_thread_reports_zero_returns():
    """EMB-Bot's structural shape: every block a fresh thread -> 0 returns.
    The instrument must REPORT that as 0, not hide it."""
    blocks = [[[(0, 0), (1, 0)]]] * 3
    breaks = [["start"], ["color"], ["color"]]
    threads = [(255, 0, 0), (0, 0, 255), (0, 255, 0)]
    c = census_structure(blocks, breaks, threads)
    assert c["thread_returns"] == 0
    assert c["return_share"] == 0.0


def test_synthetic_palette_reports_no_thread_fields():
    """DST carries no palette; the decoder's grey ramp must not masquerade as
    thread identity — a <=6-block DST would read zero returns by construction."""
    blocks = [[[(0, 0), (1, 0)]]] * 4
    breaks = [["start"], ["color"], ["color"], ["color"]]
    threads = [GREYS[i] for i in range(4)]
    c = census_structure(blocks, breaks, threads)
    assert c["thread_source"] == "synthetic"
    assert c["threads"] is None
    assert c["thread_returns"] is None
    assert c["return_share"] is None
    assert c["thread_seq"] is None
    assert c["blocks"] == 4  # structure is still real


def test_palette_is_synthetic_detects_ramp_not_real_colours():
    assert palette_is_synthetic([GREYS[0], GREYS[1]], 2)
    assert not palette_is_synthetic([(255, 0, 0), GREYS[0]], 2)


def test_cut_paths_split_from_floats():
    """start/trim/color opened a path with cut thread; jump/hop floated it."""
    blocks = [[[(0, 0)]] * 5]
    breaks = [["start", "trim", "color", "jump", "hop"]]
    c = census_structure(blocks, breaks, [(1, 2, 3)])
    assert c["paths_total"] == 5
    assert c["paths_cut"] == 3
    assert c["paths_float"] == 2
    assert c["break_kinds"] == {
        "start": 1, "trim": 1, "color": 1, "jump": 1, "hop": 1}


def test_trims_per_1k_uses_stitch_count():
    blocks = [[[(i, 0) for i in range(500)]]]
    breaks = [["start", "trim"]]
    c = census_structure(blocks, breaks, [(1, 2, 3)])
    assert c["stitches"] == 500
    assert c["trims_per_1k"] == pytest.approx(2.0)


def test_runs_to_segs_carries_block_index_and_length():
    segs = runs_to_segs([[[(0, 0), (3, 4)]], [[(1, 1), (1, 2), (1, 3)]]])
    assert len(segs) == 3
    x0, y0, x1, y1, d, blk, trimmed = segs[0]
    assert (x0, y0, x1, y1) == (0, 0, 3, 4)
    assert d == pytest.approx(5.0)
    assert blk == 0 and trimmed is False
    assert {s[5] for s in segs} == {0, 1}


# ------------------------------------------------------- element counting
def zigzag(x0, y0, w, h, row_mm):
    """Fill-like coverage: horizontal rows `row_mm` apart, one run."""
    pts, y, flip = [], y0, False
    while y <= y0 + h + 1e-9:
        pts += [(x0 + w, y), (x0, y)] if flip else [(x0, y), (x0 + w, y)]
        y += row_mm
        flip = not flip
    return pts


def test_close_fuses_rows_but_not_separate_elements():
    """Two fills 10 mm apart are 2 elements; the close only fuses each fill's
    own 0.7 mm rows, it must not bridge the gap between elements."""
    blocks = [[zigzag(0, 0, 8, 4, 0.7), zigzag(0, 14, 8, 4, 0.7)]]
    closed, raw, areas = paint_block_masks(blocks, (0, 0, 8, 18))
    assert count_components(closed[0]) == 2
    # raw footprint area ~ stroke 0.4 mm * total path length, well under solid
    assert 0 < areas[0] < 8 * 18


def test_speck_below_floor_is_not_an_element():
    speck = [[(0.0, 0.0), (0.3, 0.0)]]         # ~0.12 mm2 of ink
    real = zigzag(5, 5, 6, 3, 0.7)
    closed, _raw, _areas = paint_block_masks([[real] + [speck[0]]], (0, 0, 12, 10))
    assert count_components(closed[0], min_mm2=MIN_COMP_MM2) == 1


def test_polygon_masks_subtract_holes():
    shapely = pytest.importorskip("shapely.geometry")
    ring = shapely.Polygon(
        [(0, 0), (10, 0), (10, 10), (0, 10)],
        holes=[[(3, 3), (7, 3), (7, 7), (3, 7)]])
    (m,) = paint_polygon_masks([ring], (0, 0, 10, 10), pxmm=5.0)
    area = m.sum() / 25.0
    assert area == pytest.approx(100 - 16, rel=0.05)


# ------------------------------------------------------------- layering
def frame_mask(h, w, sl):
    m = np.zeros((h, w), bool)
    m[sl] = True
    return m


def test_layering_smaller_later_is_background_to_foreground():
    """Big field sewn first, small detail later on top -> 1/1."""
    big = frame_mask(50, 50, np.s_[5:45, 5:45])
    small = frame_mask(50, 50, np.s_[20:30, 20:30])
    st = layering_stats([big, small], [1600.0, 100.0], pxmm=1.0,
                        min_overlap_mm2=2.0)
    assert st == {"overlapping_pairs": 1, "smaller_later": 1,
                  "smaller_later_share": 1.0}


def test_layering_foreground_first_scores_zero():
    small = frame_mask(50, 50, np.s_[20:30, 20:30])
    big = frame_mask(50, 50, np.s_[5:45, 5:45])
    st = layering_stats([small, big], [100.0, 1600.0], pxmm=1.0,
                        min_overlap_mm2=2.0)
    assert st["smaller_later"] == 0 and st["overlapping_pairs"] == 1


def test_layering_ignores_non_overlapping_and_ties():
    a = frame_mask(40, 40, np.s_[0:10, 0:10])
    b = frame_mask(40, 40, np.s_[20:30, 20:30])     # disjoint from a
    c = frame_mask(40, 40, np.s_[0:10, 5:15])       # overlaps a, same area
    st = layering_stats([a, b, c], [100.0, 100.0, 100.0], pxmm=1.0,
                        min_overlap_mm2=2.0)
    assert st["overlapping_pairs"] == 1              # only (a, c)
    assert st["smaller_later"] == 0                  # tie is not "smaller"


# --------------------------------------------------------- grouping join
def test_join_perfect_grouping_scores_kappa_one():
    """Four of our regions quarter the pro's two blocks cleanly: a grouping
    reproduces the pro exactly, kappa 1.0."""
    left = frame_mask(20, 40, np.s_[:, 0:20])
    right = frame_mask(20, 40, np.s_[:, 20:40])
    ours = [frame_mask(20, 40, np.s_[0:10, 0:20]),
            frame_mask(20, 40, np.s_[10:20, 0:20]),
            frame_mask(20, 40, np.s_[0:10, 20:40]),
            frame_mask(20, 40, np.s_[10:20, 20:40])]
    j = grouping_join([left, right], ours, pxmm=1.0)
    assert j["kappa"] == pytest.approx(1.0)
    assert j["raw_agreement"] == pytest.approx(1.0)
    assert j["regions_per_block"] == {0: 2, 1: 2}
    assert j["regions_unassigned"] == 0
    assert j["blocks_unhit"] == []


def test_join_self_identity():
    masks = [frame_mask(10, 10, np.s_[0:5, :]), frame_mask(10, 10, np.s_[5:10, :])]
    j = grouping_join(masks, masks, pxmm=1.0)
    assert j["kappa"] == pytest.approx(1.0)


def test_join_sees_region_that_straddles_pro_blocks():
    """A region crossing a pro block boundary cannot be grouped onto both
    sides — the join must lose points there even under best-case grouping."""
    left = frame_mask(20, 40, np.s_[:, 0:20])
    right = frame_mask(20, 40, np.s_[:, 20:40])
    straddler = frame_mask(20, 40, np.s_[:, 10:28])   # 10 px on left, 8 on right
    clean_l = frame_mask(20, 40, np.s_[:, 0:10])
    clean_r = frame_mask(20, 40, np.s_[:, 28:40])
    j = grouping_join([left, right], [straddler, clean_l, clean_r], pxmm=1.0)
    # straddler assigns to LEFT (larger overlap); its 8 right-side columns
    # then disagree: raw = 1 - 8*20 / 800 = 0.8
    assert j["raw_agreement"] == pytest.approx(0.8)
    assert j["kappa"] < 1.0
    assert j["regions_per_block"] == {0: 2, 1: 1}


def test_join_chance_floor_zeroes_uninformative_grouping():
    """One giant our-region over a 50/50 pro design: raw 0.5 agreement is
    exactly the chance floor, so the corrected figure must be 0 — the gate-4
    case where a raw number would flatter."""
    left = frame_mask(20, 40, np.s_[:, 0:20])
    right = frame_mask(20, 40, np.s_[:, 20:40])
    blob = frame_mask(20, 40, np.s_[:, :])
    j = grouping_join([left, right], [blob], pxmm=1.0)
    assert j["raw_agreement"] == pytest.approx(0.5)
    assert j["chance"] == pytest.approx(0.5)
    assert j["kappa"] == pytest.approx(0.0)


def test_join_assigns_by_visible_surface_not_hidden_underlayer():
    """The pro's base block runs continuous UNDER later blocks. A region
    sitting on a foreground detail also sits on the hidden base, and a
    full-mask argmax tie would dump it on the background block (measured:
    46/55 hotel_fremont regions). Assignment must follow what is VISIBLE."""
    base = frame_mask(20, 20, np.s_[:, :])            # sewn first, everywhere
    detail = frame_mask(20, 20, np.s_[5:15, 5:15])    # sewn later, on top
    on_detail = frame_mask(20, 20, np.s_[5:15, 5:15])
    on_base = frame_mask(20, 20, np.s_[0:5, :])
    j = grouping_join([base, detail], [on_detail, on_base], pxmm=1.0)
    assert j["assign"] == [1, 0]
    assert j["raw_agreement"] == pytest.approx(1.0)
    assert j["blocks_unhit"] == []


def test_join_self_test_survives_base_mostly_covered_by_later_block():
    """Identical stacking on both sides must join ~1.0 even when the later
    block covers most of the base — the machine_hat_vs_lc same-file pair
    scored kappa 0.0 before assignment was restricted to each region's OWN
    visible pixels (a mostly-hidden base voted itself onto its coverer)."""
    base = frame_mask(20, 20, np.s_[:, :])
    top = frame_mask(20, 20, np.s_[0:12, :])          # covers 60% of base
    j = grouping_join([base, top], [base, top], pxmm=1.0)
    assert j["assign"] == [0, 1]
    assert j["raw_agreement"] == pytest.approx(1.0)
    assert j["kappa"] == pytest.approx(1.0)
    assert j["blocks_unhit"] == []


def test_join_separates_pro_hidden_blocks_from_unhit():
    """A pro block fully covered by the pro's own later block (3D-puff
    underpass, buried base) has no visible surface any region could land on —
    that is the pro's layering, not our miss, and must not read as unhit."""
    bottom = frame_mask(10, 10, np.s_[0:5, :])
    top = frame_mask(10, 10, np.s_[:, :])           # sewn later, covers all
    ours = [frame_mask(10, 10, np.s_[:, :])]
    j = grouping_join([bottom, top], ours, pxmm=1.0)
    assert j["pro_blocks_hidden"] == [0]
    assert j["blocks_unhit"] == []
    assert j["assign"] == [1]


def test_join_counts_fully_covered_region_as_hidden_not_unassigned():
    full = frame_mask(10, 10, np.s_[:, :])
    j = grouping_join([full], [full.copy(), full.copy()], pxmm=1.0)
    assert j["regions_hidden"] == 1
    assert j["regions_unassigned"] == 0
    assert j["assign"] == [None, 0]
    assert j["raw_agreement"] == pytest.approx(1.0)


def test_join_flags_single_label_domain_as_degenerate():
    """One pro block visible in the joint area -> chance ~1.0: the kappa
    passthrough is NOT grouping skill and must carry the degenerate flag."""
    j = grouping_join([frame_mask(10, 10, np.s_[:, :])],
                      [frame_mask(10, 10, np.s_[:, :])], pxmm=1.0)
    assert j["degenerate"] is True
    assert j["kappa"] == pytest.approx(j["raw_agreement"])
    ok = grouping_join(
        [frame_mask(10, 10, np.s_[0:5, :]), frame_mask(10, 10, np.s_[5:10, :])],
        [frame_mask(10, 10, np.s_[0:5, :]), frame_mask(10, 10, np.s_[5:10, :])],
        pxmm=1.0)
    assert ok["degenerate"] is False


def test_join_reports_region_off_pro_ink_as_unassigned():
    pro = [frame_mask(20, 40, np.s_[:, 0:20])]
    stray = frame_mask(20, 40, np.s_[:, 30:40])
    on = frame_mask(20, 40, np.s_[:, 0:20])
    j = grouping_join(pro, [on, stray], pxmm=1.0)
    assert j["regions_unassigned"] == 1
    assert j["our_outside_pro_share"] == pytest.approx(1 / 3, abs=1e-3)
    assert j["kappa"] == pytest.approx(1.0)  # joint area still agrees


def test_kappa_is_unclamped_and_passes_degenerate_through():
    assert _kappa(0.4, 0.6) < 0                     # worse than chance shows
    assert _kappa(0.7, 0.9995) == pytest.approx(0.7)  # degenerate passthrough


# ------------------------------------------------- real-data pin (committed)
def test_becker_chest_small_census_matches_plan_doc():
    """The committed pro PES must census to the numbers the 2026-08-23
    region-identification plan quotes (4 blocks / 2 threads / 2 returns /
    9 cut paths / 7 elements). If this moves, the plan's evidence moved."""
    pes = TESTDATA / "reference" / "becker_chest_small_beckers_logo_lc_2_a.pes"
    blocks, breaks, threads, bounds, _jumps, _trims = decode(pes)
    c = census_structure(blocks, breaks, threads)
    assert c["blocks"] == 4
    assert c["threads"] == 2
    assert c["thread_returns"] == 2
    assert c["return_share"] == pytest.approx(0.5)
    assert c["paths_cut"] == 9
    closed, _raw, areas = paint_block_masks(blocks, bounds)
    assert sum(count_components(m) for m in closed) == 7
    assert sum(areas) == pytest.approx(3264.1, rel=0.02)
    x0, _y0, x1, _y1 = bounds
    assert (x1 - x0) == pytest.approx(76.5, abs=0.1)
