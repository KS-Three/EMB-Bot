"""`tools/between_walks.py` -- piece-to-piece moves and what a walk lies under,
pinned on hand-built DSTs and plans.

Every file here is written by hand (`tests/proloop_synth.write_pattern`), so
the test knows each step's class and what covers it. Two ink letters 6 mm
apart, joined needle-down along y = 3.1 mm, with a ground fill sewn after,
before, or not at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import between_walks as bw  # noqa: E402

from .proloop_synth import fill_passes, write_pattern  # noqa: E402

GROUND = (40, 40, 40)
INK = (200, 30, 30)
WALK_Y = 3.1


def _box(x0, y0=0.0, w=4.0, h=6.0):
    """One letter-sized fill box as ONE needle-down pass (rows joined)."""
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _a():
    """Letter A (x 0-4), leaving from its right edge at y 3.1."""
    return _box(0.0) + [(4.0, WALK_Y)]


def _b():
    """Letter B (x 10-14), entered at its left edge at y 3.1."""
    return [(10.0, WALK_Y)] + _box(10.0)


def _walked_pair():
    """A, a needle-down walk at y 3.1 from x 4 to 10, B: one pass, no trim."""
    return _a() + [(7.0, WALK_Y)] + _b()


def _ground():
    """Tatami under the gap, rows 0.4 mm apart from y 1.0: the walk's centre
    and both thread edges sit within 0.1 mm of a row."""
    return _box(3.0, 1.0, 8.0, 4.0)


def _steps(tmp_path, blocks, name):
    r = bw.read_steps(write_pattern(tmp_path / name, blocks))
    return [s for s in r["steps"] if s["block"] == 0]


def test_a_walk_under_a_later_colour_is_buried(tmp_path):
    (s,) = _steps(tmp_path, [(INK, [_walked_pair()]), (GROUND, [_ground()])], "later.dst")
    assert s["cls"] == "walked" and s["trims"] == 0
    assert s["walked_mm"] == pytest.approx(6.0, abs=0.3)
    assert s["buried"] == pytest.approx(s["walked_mm"], abs=0.1)
    assert s["later"] == pytest.approx(s["buried"], abs=0.9)   # the end allowance reads as `same`
    assert s["bare"] == pytest.approx(0.0, abs=0.05) and s["on_work"] == pytest.approx(0.0, abs=0.05)
    assert s["zigzag"] == pytest.approx(0.0, abs=0.05)         # tatami rows are straight


def test_a_walk_on_an_earlier_colour_is_on_work_not_buried(tmp_path):
    steps = bw.read_steps(write_pattern(tmp_path / "earlier.dst",
                                        [(GROUND, [_ground()]), (INK, [_walked_pair()])]))["steps"]
    (s,) = [s for s in steps if s["block"] == 1]
    assert s["cls"] == "walked"
    # only the end allowances (a thread width at each end) read as buried
    assert s["buried"] < 1.0
    assert s["on_work"] == pytest.approx(s["walked_mm"] - s["buried"], abs=0.1)
    assert s["on_own"] == pytest.approx(0.0, abs=0.05)
    assert s["bare"] == pytest.approx(0.0, abs=0.05)


def test_a_walk_on_bare_fabric_is_bare(tmp_path):
    (s,) = _steps(tmp_path, [(INK, [_walked_pair()])], "bare.dst")
    assert s["cls"] == "walked"
    assert s["bare"] == pytest.approx(s["walked_mm"] - s["buried"], abs=0.1)
    assert s["bare"] > 4.5


def test_a_cut_reads_its_straight_hop_against_later_thread(tmp_path):
    (s,) = _steps(tmp_path, [(INK, [_a(), _b()]), (GROUND, [_ground()])], "cut.dst")
    assert s["cls"] == "cut" and s["trims"] == 1 and s["walked_mm"] == 0.0
    # the straight hop A -> B lies wholly under the ground sewn after
    assert s["hop_mm"] == pytest.approx(6.0, abs=0.05)
    assert s["hop_buried"] == pytest.approx(6.0, abs=0.1)
    assert s["hop_bare"] == pytest.approx(0.0, abs=0.05)
    summ = bw.summary(bw.read_steps(tmp_path / "cut.dst"))
    assert summ["cut"] == 1 and summ["walked"] == 0 and summ["cut_trims"] == 1


def test_summary_counts_a_clean_walk(tmp_path):
    write_pattern(tmp_path / "s.dst", [(INK, [_walked_pair()]), (GROUND, [_ground()])])
    summ = bw.summary(bw.read_steps(tmp_path / "s.dst"))
    assert summ["walked"] == 1 and summ["cut"] == 0
    assert summ["clean_walks"] == 1
    assert summ["clean_walk_mm"] == pytest.approx(6.0, abs=0.3)


# --------------------------------------------------------------- our plans
def _plan(ground_first: bool | None):
    """Two ink shapes cut apart (A then B), and a ground fill under the gap
    sewn after (False), before (True), or not at all (None)."""
    from digitizer_core import stitches
    from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
    ink = StitchBlock(thread_index=1, thread_number="1", rgb=INK, runs=[
        StitchRun(points=_a(), kind=stitches.FILL, shape_id="A", jump=True, trim=True),
        StitchRun(points=_b(), kind=stitches.FILL, shape_id="B", jump=True, trim=True)])
    ground = StitchBlock(thread_index=0, thread_number="0", rgb=GROUND, runs=[
        StitchRun(points=_box(3.0, 1.0, 8.0, 4.0), kind=stitches.FILL, shape_id="G", jump=True, trim=True)])
    blocks = [ink] if ground_first is None else ([ground, ink] if ground_first else [ink, ground])
    return StitchPlan(blocks=blocks, palette=[{} for _ in blocks])


def test_diagnose_a_hop_later_thread_covers_is_one_stage_7_takes():
    (row,) = bw.diagnose_plan(_plan(ground_first=False))
    assert row["between"] and row["cls"] == "takes_now"


def test_diagnose_a_hop_over_an_earlier_colour_is_a_colour_order_cut():
    (row,) = [r for r in bw.diagnose_plan(_plan(ground_first=True)) if r["pair"].startswith("A:")]
    assert row["cls"] == "no_route"
    assert row["off_on_earlier_mm"] > 3.0
    assert row["off_bare_mm"] < 0.5 and row["off_on_own_mm"] < 0.5


def test_diagnose_a_bare_hop_is_bare():
    (row,) = bw.diagnose_plan(_plan(ground_first=None))
    assert row["cls"] == "no_route"
    assert row["off_bare_mm"] > 3.0 and row["off_on_earlier_mm"] < 0.5
