"""The axis goldens.

This file exists because of a specific, measured hazard: EMB-Bot's DST codec
and pystitch disagree about which nibble carries x, so any coordinate
convention that crosses between the Python engine and the browser has to be
pinned rather than assumed. The plan for build step 8 calls these day-one
goldens, and they are the reason `adapter.py` is allowed to be the only place a
y-flip happens.
"""
from __future__ import annotations

import io

import pystitch
import pytest

from digitizer_core.adapter import (
    UNITS_PER_MM,
    design_bbox_units,
    design_size_mm,
    design_to_pattern,
    design_to_points_mm,
    plan_bbox_mm,
    plan_to_design,
)
from digitizer_core.stitches import FILL, StitchBlock, StitchPlan, StitchRun


def _plan(points, rgb=(10, 20, 30), number="1234") -> StitchPlan:
    return StitchPlan(
        blocks=[
            StitchBlock(
                thread_index=0,
                thread_number=number,
                rgb=rgb,
                runs=[StitchRun(points=list(points), kind=FILL)],
            )
        ],
        palette=[{"number": number, "name": "Test Thread", "rgb": list(rgb)}],
        design_size_mm=(10.0, 10.0),
    )


def test_y_axis_is_inverted_and_x_is_not():
    """The whole contract in one assertion: plan y-DOWN, design y-UP."""
    plan = _plan([(0.0, 0.0), (5.0, 3.0), (-2.0, -7.0)])
    design = plan_to_design(plan)
    sewn = [(s["x"], s["y"]) for s in design["stitches"] if s["type"] == "stitch"]

    assert sewn == [(0, 0), (50, -30), (-20, 70)]


def test_round_trip_returns_the_original_geometry():
    pts = [(0.0, 0.0), (12.3, -4.5), (-7.7, 9.1), (3.0, 3.0)]
    design = plan_to_design(_plan(pts))
    back = design_to_points_mm(design)

    assert len(back) == len(pts)
    for (ax, ay), (bx, by) in zip(pts, back):
        # 0.1 mm units means half a unit of quantization error, at most.
        assert abs(ax - bx) <= 0.5 / UNITS_PER_MM
        assert abs(ay - by) <= 0.5 / UNITS_PER_MM


def test_landscape_stays_landscape():
    """A transposition bug is invisible on square art. This is not square."""
    plan = _plan([(-40.0, -8.0), (40.0, -8.0), (40.0, 8.0), (-40.0, 8.0)])
    pw, ph = 80.0, 16.0
    dw, dh = design_size_mm(plan_to_design(plan))

    assert dw == pytest.approx(pw, abs=0.1)
    assert dh == pytest.approx(ph, abs=0.1)
    assert dw > dh


def test_plan_bbox_and_design_bbox_agree_after_the_flip():
    pts = [(-3.0, -11.0), (9.0, 2.0), (1.0, 6.0)]
    plan = _plan(pts)
    px0, py0, px1, py1 = plan_bbox_mm(plan)
    dx0, dy0, dx1, dy1 = design_bbox_units(plan_to_design(plan))

    assert dx0 / UNITS_PER_MM == pytest.approx(px0, abs=0.05)
    assert dx1 / UNITS_PER_MM == pytest.approx(px1, abs=0.05)
    # y ends swap: the plan's lowest y is the design's highest.
    assert dy0 / UNITS_PER_MM == pytest.approx(-py1, abs=0.05)
    assert dy1 / UNITS_PER_MM == pytest.approx(-py0, abs=0.05)


def test_export_round_trip_through_pystitch_preserves_orientation():
    """Design -> DST -> read back. Wider than tall, the whole way."""
    plan = _plan([(-30.0, -5.0), (30.0, -5.0), (30.0, 5.0), (-30.0, 5.0)])
    design = plan_to_design(plan)

    data = io.BytesIO()
    pystitch.write_dst(design_to_pattern(design), data)
    pattern = pystitch.read_dst(io.BytesIO(data.getvalue()))

    sewn = [(s[0], s[1]) for s in pattern.stitches if s[2] == pystitch.STITCH]
    assert sewn, "no stitches survived the round trip"
    w = (max(x for x, _ in sewn) - min(x for x, _ in sewn)) / UNITS_PER_MM
    h = (max(y for _, y in sewn) - min(y for _, y in sewn)) / UNITS_PER_MM

    assert w == pytest.approx(60.0, abs=0.2)
    assert h == pytest.approx(10.0, abs=0.2)


def test_export_flips_back_to_pystitch_s_y_down():
    """The design's y-up must become y-down again on the way to a file, or
    every exported design sews mirrored."""
    plan = _plan([(0.0, 0.0), (0.0, 10.0)])   # plan: straight DOWN in y
    design = plan_to_design(plan)
    sewn_design_y = [s["y"] for s in design["stitches"] if s["type"] == "stitch"]
    assert sewn_design_y == [0, -100]          # design: y-up, so negative

    pattern = design_to_pattern(design)
    pat_y = [s[1] for s in pattern.stitches if s[2] == pystitch.STITCH]
    assert pat_y == [0, 100]                   # pystitch: y-down again


def test_read_back_relabels_long_jump_runs_as_a_trim_and_nothing_else():
    """Pins the one behavioral wrinkle of the pystitch swap (eval doc §4.2,
    `docs/pystitch-evaluation-2026-08-11.md`).

    DST has no TRIM opcode, so `read_dst` post-processes with
    `interpolate_trims(count_max=3, clipping=True)`: an untrimmed run of 3+
    JUMP records gets a synthesized TRIM inserted in front of it, and a
    zero-displacement jump run is clipped out. pyembroidery 1.5.1's reader did
    exactly the same (verified against both installed sources during the
    2026-08-11 swap), so this pinned no migration change — it exists so a
    future library bump that alters those defaults gets caught, and it proves
    STITCH records are never touched by the relabeling.
    """
    plan = StitchPlan(
        blocks=[
            StitchBlock(0, "1", (0, 0, 0), [
                StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=FILL),
                # 39 mm of untrimmed travel -> 3+ JUMP records on disk (the
                # DST writer chunks a move into <=12.1 mm records).
                StitchRun(points=[(40.0, 0.0), (41.0, 0.0)], kind=FILL, jump=True),
            ]),
        ],
        palette=[{"number": "1", "name": "A", "rgb": [0, 0, 0]}],
    )
    data = io.BytesIO()
    pystitch.write_dst(design_to_pattern(plan_to_design(plan)), data)
    pattern = pystitch.read_dst(io.BytesIO(data.getvalue()))

    cmds = [s[2] & pystitch.COMMAND_MASK for s in pattern.stitches]
    sewn = [(s[0], s[1]) for s in pattern.stitches
            if s[2] & pystitch.COMMAND_MASK == pystitch.STITCH]

    # Every penetration survives, exactly where it was written.
    assert sewn == [(0, 0), (10, 0), (400, 0), (410, 0)]
    # The untrimmed 3+ jump run comes back with exactly one synthesized TRIM,
    # sitting in front of the run it labels.
    assert cmds.count(pystitch.TRIM) == 1
    assert cmds.count(pystitch.JUMP) >= 3
    assert cmds.index(pystitch.TRIM) < cmds.index(pystitch.JUMP)


def test_design_reports_the_size_of_its_own_stitches():
    plan = _plan([(-25.0, -2.5), (25.0, 2.5)])
    design = plan_to_design(plan)

    assert design["widthMM"] == pytest.approx(50.0, abs=0.05)
    assert design["heightMM"] == pytest.approx(5.0, abs=0.05)
    assert design["stitchCount"] == 2


def test_travel_and_trim_records_are_not_counted_as_sewn_size():
    """A jump to the far corner must not inflate the reported design size."""
    plan = StitchPlan(
        blocks=[
            StitchBlock(
                thread_index=0,
                thread_number="1",
                rgb=(0, 0, 0),
                runs=[
                    StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=FILL),
                    StitchRun(points=[(2.0, 0.0), (3.0, 0.0)], kind=FILL, jump=True),
                ],
            )
        ],
        palette=[{"number": "1", "name": "T", "rgb": [0, 0, 0]}],
    )
    design = plan_to_design(plan)
    assert design["widthMM"] == pytest.approx(3.0, abs=0.05)
    assert design["heightMM"] == pytest.approx(0.0, abs=0.05)


def test_color_change_cuts_the_thread_exactly_once():
    """Two cuts stacked in one place is a real defect the JS engine avoids with
    its justChangedColor flag; the adapter has to avoid it too."""
    plan = StitchPlan(
        blocks=[
            StitchBlock(0, "1", (255, 0, 0),
                        [StitchRun(points=[(0.0, 0.0), (1.0, 1.0)], kind=FILL)]),
            StitchBlock(1, "2", (0, 0, 255),
                        [StitchRun(points=[(5.0, 5.0), (6.0, 6.0)], kind=FILL,
                                   jump=True, trim=True)]),
        ],
        palette=[{"number": "1", "name": "A", "rgb": [255, 0, 0]},
                 {"number": "2", "name": "B", "rgb": [0, 0, 255]}],
    )
    kinds = [s["type"] for s in plan_to_design(plan)["stitches"]]

    assert kinds.count("color") == 1
    assert kinds.count("trim") == 1, "the color change already cut the thread"
    # And the cut has to come before the change, never after.
    assert kinds.index("trim") < kinds.index("color")


def test_first_run_jumps_before_it_sews():
    """The machine starts at the origin; it has to travel before the first
    penetration or the encoder invents that move out of an oversized delta."""
    design = plan_to_design(_plan([(-30.0, -30.0), (-29.0, -30.0)]))
    assert design["stitches"][0]["type"] == "jump"
    assert design["stitches"][1]["type"] == "stitch"
    assert (design["stitches"][0]["x"], design["stitches"][0]["y"]) == \
           (design["stitches"][1]["x"], design["stitches"][1]["y"])


def test_every_trim_is_followed_by_a_jump_or_a_color_change():
    """A trim that isn't going anywhere is a cut for no reason."""
    plan = StitchPlan(
        blocks=[
            StitchBlock(0, "1", (0, 0, 0), [
                StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=FILL),
                StitchRun(points=[(20.0, 20.0), (21.0, 20.0)], kind=FILL, jump=True, trim=True),
            ]),
        ],
        palette=[{"number": "1", "name": "A", "rgb": [0, 0, 0]}],
    )
    recs = plan_to_design(plan)["stitches"]
    for i, r in enumerate(recs[:-1]):
        if r["type"] == "trim":
            assert recs[i + 1]["type"] in ("jump", "color")


def test_empty_plan_is_a_valid_empty_design():
    design = plan_to_design(StitchPlan(blocks=[], palette=[]))
    assert design["stitchCount"] == 0
    assert design["colorCount"] == 0
    assert design["widthMM"] == 0
    assert design["stitches"][-1]["type"] == "end"


def test_design_ends_with_an_end_record():
    design = plan_to_design(_plan([(0.0, 0.0), (1.0, 1.0)]))
    assert design["stitches"][-1] == {"x": 0, "y": 0, "type": "end"}
    assert [s["type"] for s in design["stitches"]].count("end") == 1
