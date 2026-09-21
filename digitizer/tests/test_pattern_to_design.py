"""`adapter.pattern_to_design` is the inverse of `design_to_pattern`.

The overlay loop renders a professional's machine file through the same
`stitchviz` model the Studio draws, so the file has to become a `Design`
dict exactly the way our own plans do — same record types, same y-up units,
same colour list — or the two sides of an overlay are drawn by two rules.
"""
from __future__ import annotations

import pystitch
import pytest

from digitizer_core.adapter import (design_to_pattern, pattern_to_design,
                                    plan_to_design)
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun


def _plan() -> StitchPlan:
    a = StitchBlock(thread_index=0, thread_number="0010", rgb=(200, 20, 20), runs=[
        StitchRun(points=[(0.0, 0.0), (2.0, 0.0), (2.0, 1.5)], kind="satin"),
        StitchRun(points=[(5.0, 5.0), (7.0, 5.0)], kind="fill", jump=True, trim=True),
    ])
    b = StitchBlock(thread_index=1, thread_number="0020", rgb=(20, 20, 200), runs=[
        StitchRun(points=[(1.0, 8.0), (1.0, 9.0), (3.0, 9.0)], kind="run"),
    ])
    return StitchPlan(blocks=[a, b], palette=[])


def test_round_trip_records_and_colours():
    design = plan_to_design(_plan())
    back = pattern_to_design(design_to_pattern(design))
    want = [(s["x"], s["y"], s["type"]) for s in design["stitches"]]
    got = [(s["x"], s["y"], s["type"]) for s in back["stitches"]]
    assert got == want
    assert [(c["r"], c["g"], c["b"]) for c in back["colors"]] == [(200, 20, 20), (20, 20, 200)]
    assert back["stitchCount"] == design["stitchCount"]


def test_transform_is_applied_in_the_file_frame_before_the_flip():
    design = plan_to_design(_plan())
    pat = design_to_pattern(design)
    moved = pattern_to_design(pat, transform_mm=lambda x, y: (x + 10.0, y * 2.0))
    first = next(s for s in moved["stitches"] if s["type"] == "stitch")
    # plan point (0,0) mm -> file (0,0) -> transform (10, 0) -> units (100, -0)
    assert (first["x"], first["y"]) == (100, 0)
    last_sewn = [s for s in moved["stitches"] if s["type"] == "stitch"][-1]
    # plan point (3,9) mm y-down -> file (3,9) -> (13, 18) -> units (130, -180)
    assert (last_sewn["x"], last_sewn["y"]) == (130, -180)


def test_black_dst_threads_take_the_fallback_cycle():
    pat = pystitch.EmbPattern()
    for _ in range(2):
        t = pystitch.EmbThread()
        t.set_color(0, 0, 0)
        pat.add_thread(t)
    pat.add_stitch_absolute(pystitch.STITCH, 0, 0)
    pat.add_stitch_absolute(pystitch.STITCH, 10, 0)
    pat.add_stitch_absolute(pystitch.COLOR_CHANGE, 10, 0)
    pat.add_stitch_absolute(pystitch.STITCH, 10, 10)
    pat.add_stitch_absolute(pystitch.STITCH, 20, 10)
    pat.end()
    d = pattern_to_design(pat, fallback_colors=[(40, 40, 40), (150, 150, 150)])
    assert [(c["r"], c["g"], c["b"]) for c in d["colors"]] == [(40, 40, 40), (150, 150, 150)]
    assert [s["type"] for s in d["stitches"]] == ["stitch", "stitch", "color", "stitch", "stitch", "end"]
