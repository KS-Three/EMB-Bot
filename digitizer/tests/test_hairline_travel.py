"""Why `cfg.hairline` raises "thread over bare fabric" (2026-10-13): it does
not. A MEASURED NEGATIVE, pinned.

PR #888 saw golden_tee's `tests/test_chaining.py::_thread_bare_mm` (as it shipped,
now `_thread_bare_mm_untrimmed`) go from 19.9
to 75.2 mm with `cfg.hairline` ON. That instrument walks previous-run-end ->
TRAVEL run -> next-run-start for every TRAVEL run and never reads `jump` /
`trim`; a TRAVEL run that follows a TRIMMED jump (the walk-in to a column) is a
flight, not thread. `tools/hairline_travel.py` splits the two. Corrected,
golden_tee reads 0.94 mm (OFF) and 0.56 mm (ON) of thread over bare fabric; the
rise is flight (18.9 -> 74.4 mm) and the real cost is trims: hairline shapes
break into a rest piece and strand pieces that sit more than the trim distance
apart. Nothing to fix without dragging thread across cloth.
"""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from digitizer_core import PipelineConfig, stitches
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stitches import StitchRun
from tests.test_chaining import _thread_bare_mm_untrimmed
from tests.test_thread_profile import TESTDATA
from tools import hairline_travel as ht

ROWS = Path(__file__).resolve().parents[2] / "docs" / "renders" / "claude-hairline-bare-travel" / "rows.json"


def _plan(*runs):
    """A one-block plan around hand-built runs."""
    n = sum(len(r.points) for r in runs)
    return SimpleNamespace(blocks=[SimpleNamespace(runs=list(runs))],
                           stats=SimpleNamespace(stitch_count=n, trims=sum(bool(r.trim) for r in runs)))


def _row(x0, y, kind=stitches.SATIN, shape="A", jump=False, trim=False, length=10.0):
    return StitchRun(points=[(x0 + i * 1.0, y) for i in range(int(length) + 1)],
                     kind=kind, shape_id=shape, jump=jump, trim=trim)


def _flight_plan(trim: bool):
    """Satin A at the origin, a far satin B reached by a walk-in TRAVEL run."""
    a = _row(0, 0, shape="A")
    walk = StitchRun(points=[(50, 20), (51, 20)], kind=stitches.TRAVEL, shape_id="B",
                     jump=True, trim=trim)
    b = _row(50, 20, shape="B")
    return _plan(a, walk, b)


def test_a_trimmed_jump_is_a_flight_and_not_thread():
    plan = _flight_plan(trim=True)
    _links, _exposed, legacy_mm, _w = _thread_bare_mm_untrimmed(plan)
    row = ht.measure_plan(plan, with_legacy=False)
    assert legacy_mm > 20.0, "the shipped instrument counts the flight"
    assert row["thread_bare_mm"] == 0.0
    assert row["flight_bare_mm"] == pytest.approx(legacy_mm, rel=0.05)
    assert row["trims_in_shape"] == 0 and row["trims_between_shapes"] == 1
    assert row["flight_total_mm"] > 30.0


def test_an_untrimmed_jump_is_a_dragged_float_and_stays_counted():
    """The needle lifts but the thread is NOT cut: it crosses the cloth."""
    plan = _flight_plan(trim=False)
    row = ht.measure_plan(plan, with_legacy=False)
    _links, _exposed, legacy_mm, _w = _thread_bare_mm_untrimmed(plan)
    assert row["flight_bare_mm"] == 0.0
    assert row["thread_bare_mm"] == pytest.approx(legacy_mm, rel=0.05)
    assert row["thread_by_leg"]["in"] > 20.0


def test_a_chained_link_over_bare_cloth_is_counted_like_the_shipped_instrument():
    a = _row(0, 0, shape="A")
    link = StitchRun(points=[(10 + i * 2.0, 5) for i in range(5)], kind=stitches.TRAVEL, shape_id="B")
    b = _row(20, 5, shape="B")
    plan = _plan(a, link, b)
    row = ht.measure_plan(plan, with_legacy=False)
    _l, _e, legacy_mm, _w = _thread_bare_mm_untrimmed(plan)
    assert row["flight_bare_mm"] == 0.0 and row["thread_bare_mm"] > 3.0
    assert row["thread_bare_mm"] == pytest.approx(legacy_mm, rel=0.1)


def test_a_link_over_thread_is_not_bare():
    a = _row(0, 0, shape="A")
    link = StitchRun(points=[(9, 0), (10, 0)], kind=stitches.TRAVEL, shape_id="B")
    b = _row(10, 0, shape="B")
    assert ht.measure_plan(_plan(a, link, b), with_legacy=False)["thread_bare_mm"] == 0.0


def test_trim_anatomy_names_where_the_trims_are():
    a = _row(0, 0, shape="A")
    a2 = _row(30, 0, shape="A", jump=True, trim=True)        # inside shape A
    b = _row(60, 0, shape="B", jump=True, trim=True)         # between shapes
    row = ht.measure_plan(_plan(a, a2, b), with_legacy=False)
    assert (row["trims_in_shape"], row["trims_between_shapes"]) == (1, 1)
    assert row["flight_total_mm"] == pytest.approx(20.0 + 20.0)


# --- the finding, on a real fixture and on the recorded rows ---------------------

@pytest.fixture(scope="module")
def enthusiast():
    path = TESTDATA / "photo" / "enthusiast_logo.png"
    base = dict(target_width_mm=80.0, garment_id="left_chest", thread_wt=40)
    result = run_stages(path, PipelineConfig(**base))
    return {name: plan_stitches(result, PipelineConfig(**base, **kw))
            for name, kw in (("off", {}), ("on", dict(hairline=True)))}


def test_hairline_adds_no_thread_over_bare_fabric_on_a_real_logo(enthusiast):
    off = ht.measure_plan(enthusiast["off"], with_legacy=False)
    on = ht.measure_plan(enthusiast["on"], with_legacy=False)
    assert on["thread_bare_mm"] <= off["thread_bare_mm"] + 0.5


def test_the_corrected_number_and_the_shipped_one_agree_without_flights(enthusiast):
    """enthusiast_logo has flights too, so the shipped number is the corrected
    thread plus the flight, to sampling noise.

    The noise is one-sided since 2026-10-14: the shipped instrument sampled n + 1
    points that each stood for L / n, so it read every bare stretch ~0.1 mm long;
    `bare_profile` now samples cell midpoints. Measured on this fixture the
    shipped figure is 0.45 mm above the sum (5.84 vs 5.39), hence the 0.5 mm
    floor on the tolerance."""
    for plan in enthusiast.values():
        row = ht.measure_plan(plan, with_legacy=True)
        assert row["legacy"]["mm"] == pytest.approx(
            row["thread_bare_mm"] + row["flight_bare_mm"], rel=0.05, abs=0.5)


def test_recorded_golden_tee_the_rise_is_flights_and_trims():
    """`docs/renders/claude-hairline-bare-travel/rows.json`, written by
    `python -m tools.hairline_travel run`. golden_tee at 80 mm / left_chest."""
    rows = json.loads(ROWS.read_text(encoding="utf-8"))
    key = next(k for k in rows if k.startswith("photo/logo_golden_tee"))
    arms = rows[key]["arms"]
    off, on = arms["off"], arms["on"]
    assert on["thread_bare_mm"] <= off["thread_bare_mm"] + 1.0, "no extra thread over bare cloth"
    assert on["flight_bare_mm"] > 3 * off["flight_bare_mm"], "the legacy rise is flight"
    assert on["trims"] > off["trims"] and on["trims_in_shape"] > off["trims_in_shape"]
    assert on["trims_block_start"] == off["trims_block_start"]
    # the coverage guard does not touch it (the sibling PR's guard is about ink)
    assert arms["on_cov"]["thread_bare_mm"] <= off["thread_bare_mm"] + 1.0
