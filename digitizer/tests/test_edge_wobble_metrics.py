"""Edge wobble reaches preflight as METRICS, and judges nothing (defect 46).

`tools/edge_wobble.py` has measured how far the sewn edge wanders about its
outline since 2026-09-19, and nothing that scores a design could see it:
preflight graded `logo_whitebg` and a logo Kent calls jagged without either
number moving on the edge. The measurement now lives in
`digitizer_core/edge_wobble.py`, and `run_preflight` reports three of its
readings.

**Metrics only, on purpose.** No finding, no sentence, no score: Law 37 says
to score smoothness monotonically and invent no cutoff, and Kent's 2026-10-02
ruling is that the tool is not to warn the customer about what it should fix.
So this file pins the two halves separately: the number is the instrument's
own and rises with the defect, and the report around it does not change.

Synthetic plans on a synthetic ring, so the right answer is known before the
instrument runs; one engine-backed case for the real result object.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from digitizer_core import preflight as pf

from .conftest import PLAN_CFG_KW, cfg
from .test_edge_wobble import plan_of, ring, ring_satin

KEYS = ("edge_wobble_p95_mm", "edge_wobble_std_mm", "edge_wobble_max_mm")


def core():
    from digitizer_core import edge_wobble
    return edge_wobble


def result_of(poly=None):
    """What preflight reads of a `PipelineResult` here: the regions' ids and
    polygons (`tests/test_preflight.py` stubs it the same way)."""
    return SimpleNamespace(regions=[
        SimpleNamespace(shape_id="s", polygon=poly or ring(), meta={})])


def sawtooth(amp_mm: float):
    return plan_of(ring_satin(outer=lambda i: amp_mm if i % 2 else -amp_mm))


def metrics(plan, result="ring"):
    report = pf.run_preflight(result_of() if result == "ring" else result, plan, cfg())
    return report["metrics"]


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
    row = core().analyse_plan({"s": ring()}, plan)

    assert m["edge_wobble_p95_mm"] == row["wobble_p95_mm"] == pytest.approx(0.2, abs=0.03)
    assert m["edge_wobble_std_mm"] == row["wobble_std_mm"]
    assert m["edge_wobble_max_mm"] == row["wobble_max_mm"]


def test_the_reading_rises_with_the_sawtooth_and_there_is_no_cutoff_in_it():
    rows = [metrics(sawtooth(a)) for a in (0.0, 0.05, 0.1, 0.2, 0.4)]
    for k in KEYS:
        values = [r[k] for r in rows]
        assert values == sorted(values) and len(set(values)) == len(values), (k, values)
    # Below `OVER_MM` the tool's "visible" line would read nothing at all; the
    # metric still separates 0.05 from clean.
    assert rows[1]["edge_wobble_p95_mm"] > rows[0]["edge_wobble_p95_mm"]


def test_it_judges_nothing():
    # ONE rough plan, scored with its outline and without. A clean plan beside
    # a rough one is the wrong pair: the checks that were already here react
    # to the rail itself (`DENSITY_EXTREME` fires on this sawtooth), and that
    # is theirs to do. What must not move is the report when the wobble is
    # read against when it is not.
    plan = sawtooth(0.4)
    read = pf.run_preflight(result_of(), plan, cfg())
    unread = pf.run_preflight(None, plan, cfg())

    assert read["metrics"]["edge_wobble_p95_mm"] > 0.3      # the defect is seen...
    assert unread["metrics"]["edge_wobble_p95_mm"] is None
    assert read["findings"] == unread["findings"]           # ...and says nothing
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


def test_the_metrics_cross_the_json_boundary_as_plain_floats():
    m = metrics(sawtooth(0.2))
    assert all(type(m[k]) is float for k in KEYS)
    json.dumps(m)


def test_a_real_result_is_read_the_way_the_tool_reads_it(whitebg, plan):
    stitch_plan, _planned, _warnings = plan
    m = pf.run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]
    row = core().analyse_plan({r.shape_id: r.polygon for r in whitebg.regions}, stitch_plan)

    assert row["points"] > 100
    assert m["edge_wobble_p95_mm"] == row["wobble_p95_mm"]
    assert m["edge_wobble_std_mm"] == row["wobble_std_mm"]
    assert m["edge_wobble_max_mm"] == row["wobble_max_mm"]
