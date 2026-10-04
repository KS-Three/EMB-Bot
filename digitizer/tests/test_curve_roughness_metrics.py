"""Curve roughness reaches preflight as METRICS, and judges nothing (defect 46).

The other half of defect 46, and the one Law 37 actually names: direction
change along the stitch path. `tools/curve_fidelity.py` has read it off
`plan.iter_runs()` since 2026-08-27 -- is a curve sewn as a curve, or as a
polygon -- and nothing that scores a design could see it. Its measurement now
lives in `digitizer_core/curve_fidelity.py` and `run_preflight` reports it.

Metrics only, for the reasons `test_edge_wobble_metrics.py` gives: Law 37
forbids a cutoff, and Kent's 2026-10-02 ruling is that the tool does not warn
the customer about what it should fix. The instrument adds a third: it cannot
read intent (a logo that IS a 20-gon and a circle polygonised to one are the
same path), so its number is for comparing one design against itself across
engine changes -- which is what a scorecard diff does -- and never a grade.

**Five keys, because the instrument says to read them together.** A delta in
`curve_roughness_deg` means nothing if the population under it moved, so the
trace and vertex counts ride out beside it.

A refusal -- nothing curved to measure -- is None here, not the tool's NaN:
the service serialises with `allow_nan=False`.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest

from digitizer_core import preflight as pf
from digitizer_core import stitches
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .conftest import PLAN_CFG_KW, cfg
from .test_curve_fidelity import ngon, resample, square

KEYS = ("curve_roughness_deg", "curve_turn_gini", "curve_vertices",
        "curve_corner_vertices", "curve_traces")


def core():
    from digitizer_core import curve_fidelity
    return curve_fidelity


def outline_plan(poly: np.ndarray, step: float = 0.5, kind: str = stitches.RUN) -> StitchPlan:
    """`poly` sewn as one run, a needle every `step` mm."""
    run = StitchRun(points=[(float(x), float(y)) for x, y in resample(poly, step)],
                    kind=kind, shape_id="s")
    return StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="0000",
                                          rgb=(0, 0, 0), runs=[run])], palette=[{}])


def metrics(plan: StitchPlan) -> dict:
    return pf.run_preflight(None, plan, cfg())["metrics"]


def test_the_measurement_lives_in_the_core_and_the_tool_reads_it_from_there():
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from tools import curve_fidelity as tool

    assert tool.measure is core().measure
    assert tool.traces is core().traces
    assert tool.CORNER_DEG == core().CORNER_DEG


def test_a_polygonised_circle_reaches_preflight_at_the_instruments_own_reading():
    curve, polygon = outline_plan(ngon(None)), outline_plan(ngon(20))
    smooth, rough = metrics(curve), metrics(polygon)
    own = core().measure([p for _k, _s, p in core().traces(polygon)])

    assert smooth["curve_roughness_deg"] < 0.1          # 0.001 on the tool's own table
    assert rough["curve_roughness_deg"] == own["roughness_deg"] > 2.0
    assert rough["curve_turn_gini"] == own["turn_gini"]
    assert (rough["curve_vertices"], rough["curve_corner_vertices"], rough["curve_traces"]) == (
        own["curve_vertices"], own["corner_vertices"], own["traces"])


def test_a_refusal_is_none_and_never_nan():
    # A square: four real corners and nothing curved. The tool answers NaN and
    # says why; NaN does not survive the service's JSON.
    m = metrics(outline_plan(square()))
    assert m["curve_roughness_deg"] is None and m["curve_turn_gini"] is None
    assert m["curve_corner_vertices"] >= 3                # an open run sees three of the four
    json.dumps(m, allow_nan=False)


def test_a_plan_with_nothing_visible_reports_no_traces():
    # Tatami rows turn at every row end; that is not artwork shape.
    m = metrics(outline_plan(ngon(20), kind=stitches.FILL))
    assert m["curve_traces"] == 0 and m["curve_roughness_deg"] is None


def test_it_reads_a_bare_plan():
    # Unlike edge wobble it needs no outline: the path is the whole input.
    assert metrics(outline_plan(ngon(20)))["curve_roughness_deg"] is not None


def test_it_judges_nothing(monkeypatch):
    plan = outline_plan(ngon(12))
    read = pf.run_preflight(None, plan, cfg())
    assert read["metrics"]["curve_roughness_deg"] > 2.0     # the polygon is seen...

    monkeypatch.setattr(pf, "_curve_roughness_metrics", lambda _plan: {})
    unread = pf.run_preflight(None, plan, cfg())
    assert "curve_roughness_deg" not in unread["metrics"]
    assert read["findings"] == unread["findings"]           # ...and says nothing
    assert (read["score"], read["grade"]) == (unread["score"], unread["grade"])
    assert read["metrics"]["raw_score"] == unread["metrics"]["raw_score"]


def test_the_metrics_cross_the_json_boundary_as_plain_numbers():
    m = metrics(outline_plan(ngon(20)))
    assert type(m["curve_roughness_deg"]) is float and type(m["curve_turn_gini"]) is float
    assert all(type(m[k]) is int for k in KEYS[2:])
    json.dumps({k: m[k] for k in KEYS}, allow_nan=False)


def test_a_real_plan_is_read_the_way_the_tool_reads_it(whitebg, plan):
    stitch_plan, _planned, _warnings = plan
    m = pf.run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]
    own = core().measure([p for _k, _s, p in core().traces(stitch_plan)])

    assert own["traces"] >= 1 and own["refusal"] is None
    assert m["curve_roughness_deg"] == own["roughness_deg"]
    assert m["curve_traces"] == own["traces"]
