"""`DENSITY_STACKED` says WHERE the thread piles up.

Its own message ends *"cut the bottom layer back WHERE the top one covers
it"*, and the check computed that and threw it away: `_coverage_map` returns
`(grid, origin)` and `_coverage_findings` bound the origin to `_origin`, while
`patch_area_mm2` collapsed `connectedComponentsWithStats` — bounding boxes,
centroids and all — to one summed area.

A sum also cannot tell 40 mm2 in one blob from 40 mm2 speckled over twenty,
which are different defects with different fixes. `patches` and
`worst_patch_mm2` separate them; `worst_patch_at_mm` is the plan-mm centre of
the largest, matching `LINK_UNCOVERED`'s `at_mm`.

**This file is not a nice-to-have.** Swept 2026-09-06, the finding fires on
**0 of the 52 corpus design/garment combos** — six fixtures carry a peak over
the warn level and every one yields 0.0 mm2 of qualifying patch, because the
`_COVERAGE_MIN_PATCH_MM2` filter is doing all the work. So synthetic plans are
the ONLY exercise a `block`-severity check gets, here and in
`test_preflight.py`'s `_stacked(n)` cases.
"""

import math

import pytest

from digitizer_core import machine, preflight as pf
from digitizer_core import stitches as st
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .conftest import cfg


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _square_fill(side_mm: float, cx: float, cy: float, shape_id: str,
                 spacing_mm: float = machine.FILL_ROW_MM) -> StitchRun:
    """A boustrophedon fill of one square centred on (cx, cy)."""
    pts: list[tuple[float, float]] = []
    row, y = 0, cy - side_mm / 2
    while y <= cy + side_mm / 2:
        xs = [cx - side_mm / 2 + 2.0 * i for i in range(int(side_mm / 2.0) + 1)]
        if row % 2:
            xs.reverse()
        pts.extend((x, y) for x in xs)
        row += 1
        y += spacing_mm
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _stack_at(cx: float, cy: float, layers: int, side_mm: float = 14.0,
              tag: str = "") -> list[StitchRun]:
    return [_square_fill(side_mm, cx, cy, f"F{tag}{i}") for i in range(layers)]


def _hit(report: dict) -> dict | None:
    for f in report["findings"]:
        if f["code"] == pf.DENSITY_STACKED:
            return f
    return None


def test_one_stack_reports_its_own_centre():
    report = pf.run_preflight(None, _plan(*_stack_at(30.0, -20.0, 4)), cfg())
    hit = _hit(report)
    assert hit is not None and hit["severity"] == "block"
    x, y = hit["extra"]["worst_patch_at_mm"]
    assert math.hypot(x - 30.0, y - -20.0) < 1.5, (x, y)
    assert hit["extra"]["patches"] == 1
    assert "It is one patch, centred near" in hit["message"]


def test_the_worst_of_several_is_the_one_named():
    """Two stacks, one clearly bigger. The sum cannot tell them apart; the
    worst patch and its centre can, and the big one has to win."""
    plan = _plan(*_stack_at(-40.0, 0.0, 4, side_mm=8.0, tag="small"),
                 *_stack_at(40.0, 0.0, 4, side_mm=20.0, tag="big"))
    hit = _hit(pf.run_preflight(None, plan, cfg()))
    assert hit is not None
    assert hit["extra"]["patches"] == 2
    x, _y = hit["extra"]["worst_patch_at_mm"]
    assert x > 0, "the 20 mm stack is on the right and is the larger"
    assert hit["extra"]["worst_patch_mm2"] > 200.0
    assert f"The worst of 2" in hit["message"]


def test_the_worst_patch_never_exceeds_the_total():
    """The sum and the largest part are computed in one pass, so a future
    edit that filters one and not the other shows up here."""
    plan = _plan(*_stack_at(-40.0, 0.0, 4, side_mm=8.0, tag="a"),
                 *_stack_at(40.0, 0.0, 4, side_mm=20.0, tag="b"))
    e = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
    total = e["over_block_mm2"]
    assert 0.0 < e["worst_patch_mm2"] <= total
    assert e["patches"] >= 1


def test_the_centre_is_in_plan_mm_not_grid_cells():
    """The whole value of the field is that the review screen can point at it.
    A stack 100 mm from the origin must report ~100, not a cell index."""
    hit = _hit(pf.run_preflight(None, _plan(*_stack_at(100.0, 60.0, 4)), cfg()))
    x, y = hit["extra"]["worst_patch_at_mm"]
    assert x == pytest.approx(100.0, abs=1.5)
    assert y == pytest.approx(60.0, abs=1.5)


def test_a_warn_level_stack_reports_its_place_too():
    """Three layers is a warn, not a block, and it takes the same branch —
    the location must not be block-only."""
    hit = _hit(pf.run_preflight(None, _plan(*_stack_at(-15.0, 25.0, 3)), cfg()))
    assert hit is not None and hit["severity"] == "warn"
    x, y = hit["extra"]["worst_patch_at_mm"]
    assert math.hypot(x - -15.0, y - 25.0) < 1.5, (x, y)


def test_the_thresholds_are_fill_layer_multiples_not_bare_numbers():
    """The docstring said "2.5 and 3.5" for these two constants until
    2026-09-06 while they evaluated to 6.67 and 9.33 — which made every corpus
    peak look like a gross overshoot. Pin the relationship rather than either
    number, so a future re-base moves both together or fails here."""
    assert machine.COVERAGE_WARN_UNITS == pytest.approx(
        2.5 * machine.COVERAGE_FILL_LAYER_UNITS)
    assert machine.COVERAGE_BLOCK_UNITS == pytest.approx(
        3.5 * machine.COVERAGE_FILL_LAYER_UNITS)
    assert machine.COVERAGE_FILL_LAYER_UNITS == pytest.approx(
        machine.COVERAGE_THREAD_W_MM / machine.FILL_ROW_MM)
    # ...and the corpus's highest measured peak (7.97 on photo_dof_meadow,
    # 2026-09-06) sits UNDER the block ceiling, which is why nothing fires.
    assert 7.97 < machine.COVERAGE_BLOCK_UNITS
