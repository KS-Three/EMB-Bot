"""tools/wordmark_ticks.py: the pure helpers behind the per-tick census (no digitize)."""
from types import SimpleNamespace

import pytest
from shapely.geometry import box

from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from tools import wordmark_ticks as wt


def test_frac_to_mm_is_the_triage_transform():
    # 100 x 200 raster, art box the whole raster, 10 px/mm: the centre is 0, 0
    assert wt.frac_to_mm((100, 200), (0, 0, 200, 100), 10.0, (0.5, 0.5)) == (0.0, 0.0)
    assert wt.frac_to_mm((100, 200), (0, 0, 200, 100), 10.0, (1.0, 0.0)) == (10.0, -5.0)


def test_index_groups():
    assert wt.index_groups([5, 3, 4, 9, 10, 12]) == [[3, 5], [9, 10], [12, 12]]
    assert wt.index_groups([]) == []


def test_block_record_span_reads_between_colour_changes():
    st = [{"type": "stitch"}] * 3 + [{"type": "color"}] + [{"type": "stitch"}] * 2 + \
         [{"type": "color"}] + [{"type": "stitch"}, {"type": "end"}]
    assert wt.block_record_span(st, 0) == (0, 3)
    assert wt.block_record_span(st, 1) == (4, 6)
    assert wt.block_record_span(st, 2) == (7, 9)


def _plan(runs, rgb=(0, 0, 0)):
    return StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="0020", rgb=rgb,
                                          runs=runs)], palette=[])


def test_laid_segments_link_runs_but_not_across_a_jump():
    a = StitchRun([(0, 0), (1, 0)], kind="satin", shape_id="A")
    b = StitchRun([(1, 1), (2, 1)], kind="travel", shape_id="A")          # needle-down link
    c = StitchRun([(5, 5), (6, 5)], kind="satin", shape_id="B", jump=True, trim=True)
    segs = wt.laid_segments(_plan([a, b, c]), [0])
    assert ((1, 0), (1, 1)) in segs
    assert ((2, 1), (5, 5)) not in segs
    assert len(segs) == 4


def test_excess_bare_reads_thread_past_the_pull_and_uncovered_ink():
    ink = box(-1, -1, 1, 1)
    inside = [((-0.8, y / 10), (0.8, y / 10)) for y in range(-9, 10, 2)]
    ex, bare = wt.excess_bare(ink, inside, (0, 0), 2.0)
    assert ex == 0.0
    assert bare < 0.15                       # rows 0.2 mm apart, 0.4 mm thread
    # a 1 mm leg 1.5 mm outside the ink: all of it is past 0.3 + 0.2
    ex, bare = wt.excess_bare(ink, inside + [((-0.5, 2.5), (0.5, 2.5))], (0, 0), 3.0)
    # a 1 mm x 0.4 mm filament with round caps: 0.4 + pi * 0.2**2
    assert ex == pytest.approx(0.4 + 3.1416 * 0.04, abs=0.06)
    # no thread: every mm2 of ink is bare
    ex, bare = wt.excess_bare(ink, [], (0, 0), 2.0)
    # (fillPoly paints its boundary pixels: a 2 x 2 mm square reads ~4.1 at 40 px/mm)
    assert (ex, bare) == (0.0, pytest.approx(4.0, abs=0.15))


def test_tick_census_names_runs_records_and_the_furthest_point():
    leg = StitchRun([(0.0, 0.0), (0.0, 0.5), (0.0, 1.4)], kind="satin", shape_id="R")
    hop = StitchRun([(0.6, 0.0), (0.6, 0.4)], kind="travel", shape_id="R", jump=True, trim=True)
    far = StitchRun([(9.0, 9.0), (9.0, 9.5)], kind="satin", shape_id="R")
    plan = _plan([leg, hop, far])
    regions = [SimpleNamespace(shape_id="R", polygon=box(-0.5, -0.5, 0.5, 1.5))]
    rec = [{"type": "stitch", "x": 0, "y": 0}, {"type": "stitch", "x": 0, "y": -5},
           {"type": "stitch", "x": 0, "y": -14}, {"type": "trim", "x": 0, "y": -14},
           {"type": "jump", "x": 6, "y": 0}, {"type": "stitch", "x": 6, "y": 0},
           {"type": "stitch", "x": 6, "y": -4}, {"type": "stitch", "x": 90, "y": -90},
           {"type": "end", "x": 90, "y": -90}]
    t = wt.tick_census(plan, regions, {"stitches": rec}, (0.0, 0.5), 1.0)
    assert [(r["run"], r["kind"], r["jump"], r["trim"]) for r in t["runs"]] == \
        [(0, "satin", False, False), (1, "travel", True, True)]
    assert t["runs"][0]["first_mm"] == 0.5 and t["runs"][0]["last_mm"] == 0.9
    assert t["records"] == [[0, 6]]
    assert t["jumps"] == [4] and t["trims"] == [3]
    assert t["longest_step_mm"] == 0.9
    assert t["max_out_mm"] == 0.1             # (0.6, *) is 0.1 mm past x = 0.5


def test_ticks_and_arms_are_what_the_pr_reports():
    assert list(wt.TICKS) == ["e_top", "r_foot", "m_v", "n_foot"]
    assert wt.ARMS["main"] == {}
    assert wt.ARMS["ends_off"] == {"lettering_columns_square_ends": False,
                                   "lettering_columns_inside_connectors": False}
