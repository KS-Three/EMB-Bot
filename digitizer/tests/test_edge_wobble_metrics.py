"""Edge wobble reaches preflight as METRICS, and judges nothing (defect 46).

`tools/edge_wobble.py` has measured how far the sewn edge wanders about its
outline since 2026-09-19, and nothing that scores a design could see it:
preflight graded `logo_whitebg` and a logo Kent calls jagged without either
number moving on the edge. The measurement now lives in
`digitizer_core/edge_wobble.py`, and `run_preflight` reports its readings.

**Metrics only, on purpose.** No finding, no sentence, no score: Law 37 says
to score smoothness monotonically and invent no cutoff, and Kent's 2026-10-02
ruling is that the tool is not to warn the customer about what it should fix.
So this file pins the two halves separately: the number is the instrument's
own and rises with the defect, and the report around it does not change.

**Per tier, never pooled.** The engine's run tier sews a shape's own outline
vertices and reads exactly 0, so a pooled figure moves when shapes change tier
and no rail has moved (enthusiast: satin p95 0.247 mm, pooled 0.186). Each
tier the instrument reads -- satin, border, fill, line -- reports its own
three numbers.

Synthetic plans on a synthetic ring, so the right answer is known before the
instrument runs; one engine-backed case for the real result object.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import shapely
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import preflight as pf
from digitizer_core import stitches
from digitizer_core.stitches import StitchRun

from .conftest import PLAN_CFG_KW, cfg
from .test_edge_wobble import R_OUT, plan_of, plan_with, ring, ring_satin

TIERS = ("satin", "border", "fill", "line")
STATS = ("p95_mm", "std_mm", "max_mm")
KEYS = tuple(f"edge_wobble_{t}_{s}" for t in TIERS for s in STATS)
SATIN = tuple(f"edge_wobble_satin_{s}" for s in STATS)


def core():
    from digitizer_core import edge_wobble
    return edge_wobble


def result_of(*extra):
    """What preflight reads of a `PipelineResult` here: the regions' ids and
    polygons (`tests/test_preflight.py` stubs it the same way)."""
    return SimpleNamespace(regions=[
        SimpleNamespace(shape_id="s", polygon=ring(), meta={}), *extra])


def sawtooth_run(amp_mm: float) -> StitchRun:
    return StitchRun(points=ring_satin(outer=lambda i: amp_mm if i % 2 else -amp_mm),
                     kind=stitches.SATIN, shape_id="s")


def sawtooth(amp_mm: float):
    return plan_with([sawtooth_run(amp_mm)])


def outline_run() -> StitchRun:
    """A run sewn exactly on the ring's outer edge, a stitch every 0.5 mm."""
    n = int(2 * math.pi * R_OUT / 0.5)
    return StitchRun(points=[(R_OUT * math.cos(2 * math.pi * i / n),
                              R_OUT * math.sin(2 * math.pi * i / n)) for i in range(n)],
                     kind=stitches.RUN, shape_id="s")


def metrics(plan, result=None):
    return pf.run_preflight(result or result_of(), plan, cfg())["metrics"]


def test_the_measurement_lives_in_the_core_and_the_tool_reads_it_from_there():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    import edge_wobble as tool

    # One implementation: a tool carrying its own copy would let the number
    # preflight reports and the number the docs quote drift apart.
    assert tool.analyse_plan is core().analyse_plan
    assert tool.OVER_MM == core().OVER_MM


def test_a_sawtoothed_rail_reaches_preflight_at_the_instruments_own_reading():
    plan = sawtooth(0.2)
    m = metrics(plan)
    satin = core().analyse_plan({"s": ring()}, plan)["by_tier"]["satin"]

    assert m["edge_wobble_satin_p95_mm"] == satin["wobble_p95_mm"] == pytest.approx(0.2, abs=0.03)
    assert m["edge_wobble_satin_std_mm"] == satin["wobble_std_mm"]
    assert m["edge_wobble_satin_max_mm"] == satin["wobble_max_mm"]
    # A tier the design does not sew has no reading -- not a clean one.
    assert [m[k] for k in KEYS if k not in SATIN] == [None] * 9


def test_the_reading_rises_with_the_sawtooth_and_there_is_no_cutoff_in_it():
    # 0.05 mm is a third of the tool's "visible" line (`OVER_MM`), where its
    # flagged count reads nothing at all; the metric still separates it.
    rows = [metrics(sawtooth(a)) for a in (0.0, 0.05, 0.1, 0.2, 0.4)]
    for k in SATIN:
        values = [r[k] for r in rows]
        assert values == sorted(values) and len(set(values)) == len(values), (k, values)


def test_stitches_that_trace_the_outline_do_not_dilute_the_rails():
    # The reason the tiers are not pooled. A run sewn on the outline reads 0;
    # pooled with the rails it would pull their figure down, and a shape
    # changing tier would read as an edge getting smoother.
    alone = metrics(sawtooth(0.2))
    beside_a_run = metrics(plan_with([sawtooth_run(0.2), outline_run()]))
    assert [beside_a_run[k] for k in SATIN] == [alone[k] for k in SATIN]

    pooled = core().analyse_plan({"s": ring()}, plan_with([sawtooth_run(0.2), outline_run()]))
    assert pooled["wobble_std_mm"] < 0.9 * alone["edge_wobble_satin_std_mm"]   # what was refused


def test_a_run_on_the_outline_reads_clean_in_its_own_tier():
    m = metrics(plan_with([outline_run()]))
    assert m["edge_wobble_line_p95_mm"] < 0.001 and m["edge_wobble_line_max_mm"] < 0.001
    assert [m[k] for k in SATIN] == [None] * 3          # measured clean is not unmeasured


def test_it_judges_nothing():
    # ONE rough plan, scored with its outline and without. A clean plan beside
    # a rough one is the wrong pair: the checks that were already here react
    # to the rail itself (`DENSITY_EXTREME` fires on this sawtooth), and that
    # is theirs to do. What must not move is the report when the wobble is
    # read against when it is not.
    plan = sawtooth(0.4)
    read = pf.run_preflight(result_of(), plan, cfg())
    unread = pf.run_preflight(None, plan, cfg())

    assert read["metrics"]["edge_wobble_satin_p95_mm"] > 0.3   # the defect is seen...
    assert unread["metrics"]["edge_wobble_satin_p95_mm"] is None
    assert read["findings"] == unread["findings"]              # ...and says nothing
    assert (read["score"], read["grade"]) == (unread["score"], unread["grade"])
    assert read["metrics"]["raw_score"] == unread["metrics"]["raw_score"]


def test_a_bare_plan_reports_none_rather_than_a_clean_zero():
    # No regions, no outline to measure against. 0.0 would read as "perfect".
    m = pf.run_preflight(None, sawtooth(0.4), cfg())["metrics"]
    assert {k: m[k] for k in KEYS} == dict.fromkeys(KEYS)


def test_a_design_with_no_measurable_edge_reports_none():
    # Seven penetrations a rail: under the instrument's `MIN_SERIES`.
    m = metrics(plan_of(ring_satin()[:14]))
    assert {k: m[k] for k in KEYS} == dict.fromkeys(KEYS)


def test_a_region_without_a_polygon_is_skipped_not_fatal():
    # Nothing produces one today. A number that judges nothing must not be
    # the reason a finished design fails to reach the customer.
    ghost = SimpleNamespace(shape_id="ghost", polygon=None, meta={})
    m = metrics(sawtooth(0.2), result_of(ghost))
    assert m["edge_wobble_satin_p95_mm"] == pytest.approx(0.2, abs=0.03)


def test_the_metrics_cross_the_json_boundary_as_plain_floats():
    m = metrics(sawtooth(0.2))
    assert all(type(m[k]) is float for k in SATIN)
    json.dumps(m, allow_nan=False)             # the service's own setting


def test_preflight_does_not_pay_for_the_unsewn_outline_walk(monkeypatch):
    # `analyse_plan` also walks every outline looking for bare spans -- a
    # fifth to a half of its time, for a result preflight never reads.
    def walked(*_a, **_k):
        raise AssertionError("preflight walked the unsewn outline")

    monkeypatch.setattr(core(), "_unsewn", walked)
    assert metrics(sawtooth(0.2))["edge_wobble_satin_p95_mm"] is not None

    monkeypatch.undo()
    plan = sawtooth(0.2)
    full = core().analyse_plan({"s": ring()}, plan)
    lean = core().analyse_plan({"s": ring()}, plan, unsewn=False)
    assert "unsewn" in full and "unsewn" not in lean
    assert {k: v for k, v in full.items() if k != "unsewn"} == lean


def test_the_nearest_ring_is_the_brute_force_answer_ties_included():
    # A shape with many holes used to cost rings x points distances. The index
    # must give `argmin`'s answer exactly, and `argmin` breaks a tie toward
    # the LOWEST ring -- the web between two holes is equidistant from both.
    n = 5
    holes = [box(3 * i + 1, 3 * j + 1, 3 * i + 3, 3 * j + 3) for i in range(n) for j in range(n)]
    plate = box(0, 0, 3 * n + 1, 3 * n + 1).difference(unary_union(holes))
    rings = [LineString(r.coords) for r in (plate.exterior, *plate.interiors)]
    rng = np.random.default_rng(3)
    scattered = rng.uniform(-1, 3 * n + 2, size=(400, 2))
    webs = np.array([(3 * i + 0.5, y) for i in range(1, n) for y in np.arange(1.2, 3 * n, 0.3)])
    part = np.vstack([scattered, webs])
    pts = shapely.points(part)

    brute = np.stack([shapely.distance(r, pts) for r in rings])
    ring_of, dist = core()._nearest_ring(rings, shapely.STRtree(rings), part)

    tied = (np.isclose(brute, brute.min(0)).sum(0) > 1).sum()
    assert tied >= len(webs)                                    # the ties are really in it
    assert np.array_equal(ring_of, brute.argmin(0))
    assert np.array_equal(dist, brute.min(0))


def test_a_real_result_is_read_per_tier(whitebg, plan):
    stitch_plan, _planned, _warnings = plan
    m = pf.run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]
    row = core().analyse_plan({r.shape_id: r.polygon for r in whitebg.regions}, stitch_plan)

    for tier in ("satin", "fill"):                              # whitebg sews both
        assert row["by_tier"][tier]["points"] > 100
        for stat in STATS:
            assert m[f"edge_wobble_{tier}_{stat}"] == row["by_tier"][tier][f"wobble_{stat}"]
            assert m[f"edge_wobble_{tier}_{stat}"] is not None
