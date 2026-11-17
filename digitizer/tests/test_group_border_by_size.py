"""The size ring decided once per line of like shapes (`cfg.group_consistent_border_by_size`, ON since 2026-11-16).

`border_by_size` reads each shape's smallest dimension against 6.0 mm, so
like shapes that straddle it sew unlike. On the NASA worm logotype (Commons
PNG, 100 mm) three shapes of one 5.4 mm stroke read 6.19, 6.26 and 5.92: two
sewed as a fill under a satin ring and the third as a bare fill.

ON, a line of shapes the rule could read takes its group's side and the
undecided members on the other side follow.

Synthetic shapes: the logotype is not in the repo.
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core import PipelineConfig, machine
from digitizer_core.regions import Region
from digitizer_core.stage7_sequence import (BORDER_GROUP_KEY, _border_by_size_width, _min_dim_mm,
                                            tag_border_by_size_groups)

FLOOR = machine.BORDER_BY_SIZE_MIN_DIM_MM
OFF = PipelineConfig(group_consistent_border_by_size=False)
ON = PipelineConfig(group_consistent_border_by_size=True)


def _reg(sid, poly, thread=0, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def row(*widths, thread=0, **meta):
    """Upright bars 20 mm tall on one line, 4 mm apart: a bar's smallest
    dimension is its width."""
    out, x = [], 0.0
    for i, w in enumerate(widths):
        out.append(_reg(f"S{i}", box(x, 0, x + w, 20), thread, **meta))
        x += w + 4.0
    return out


def _widths(regs, cfg):
    return [_border_by_size_width(r, cfg) for r in regs]


def test_flag_default_is_on():
    # ON since 2026-11-16 (Kent, from the ten-logo sheets: "Flip both ON")
    assert PipelineConfig().group_consistent_border_by_size is True


def test_the_fixture_straddles_the_floor():
    regs = row(6.2, 6.3, 5.9)
    dims = [round(_min_dim_mm(r.polygon), 2) for r in regs]
    assert dims[0] >= FLOOR and dims[1] >= FLOOR and dims[2] < FLOOR


def test_the_defect_like_shapes_sew_unlike():
    assert _widths(row(6.2, 6.3, 5.9), OFF) == [2.1, 2.1, None]


def test_on_the_odd_one_follows_its_line_onto_the_ring():
    regs = row(6.2, 6.3, 5.9)
    assert tag_border_by_size_groups(regs, ON) == 1
    assert regs[2].meta[BORDER_GROUP_KEY] is True
    assert BORDER_GROUP_KEY not in regs[0].meta and BORDER_GROUP_KEY not in regs[1].meta
    assert _widths(regs, ON) == [2.1, 2.1, 2.1]


def test_on_the_odd_one_follows_its_line_off_the_ring():
    regs = row(5.8, 5.9, 6.1)
    assert tag_border_by_size_groups(regs, ON) == 1
    assert regs[2].meta[BORDER_GROUP_KEY] is False
    assert _widths(regs, ON) == [None, None, None]


def test_the_stamp_is_read_only_with_the_flag():
    regs = row(6.2, 6.3, 5.9)
    tag_border_by_size_groups(regs, ON)
    assert _widths(regs, OFF) == [2.1, 2.1, None]


def test_decided_members_that_disagree_leave_the_line_alone():
    """12 mm and 3 mm bars are both evidence (over `MARGIN` off the floor),
    on opposite sides: a mixed line, and the one near the floor keeps its
    own call."""
    regs = row(12.0, 3.0, 6.1)
    assert tag_border_by_size_groups(regs, ON) == 0
    assert _widths(regs, ON) == _widths(regs, OFF)


def test_a_decided_member_is_never_moved():
    """Two 12 mm bars decide the line; the 5.9 follows, and a 3 mm bar is not
    in question (a bar a third the height is no line-mate's like anyway)."""
    regs = row(12.0, 12.0, 5.9)
    assert tag_border_by_size_groups(regs, ON) == 1
    assert _widths(regs, ON)[2] == 2.1


def test_two_shapes_are_not_a_line():
    regs = row(6.2, 5.9)
    assert tag_border_by_size_groups(regs, ON) == 0


def test_other_threads_and_lettering_are_not_read():
    mixed = row(6.2, 6.3) + [_reg("Sx", box(21, 0, 26.9, 20), thread=1)]
    assert tag_border_by_size_groups(mixed, ON) == 0
    letters = row(6.2, 6.3, 5.9, text_candidate=True, text_cluster_id="TC1")
    assert tag_border_by_size_groups(letters, ON) == 0
    pinned = row(6.2, 6.3, 5.9)
    pinned[2].meta["tier"] = "fill"
    assert tag_border_by_size_groups(pinned, ON) == 0


def test_a_stale_stamp_is_cleared_on_the_next_read():
    regs = row(6.2, 6.3, 5.9)
    tag_border_by_size_groups(regs, ON)
    regs[2] = _reg("S2", box(regs[2].polygon.bounds[0], 0, regs[2].polygon.bounds[0] + 12.0, 20),
                   **{BORDER_GROUP_KEY: False})
    assert tag_border_by_size_groups(regs, ON) == 0
    assert BORDER_GROUP_KEY not in regs[2].meta
