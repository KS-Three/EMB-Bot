"""`outline_inlets_kept` and `proofread_guard_clipped` together (both built
OFF; review 2026-11-14): the guard replans the result the plan in hand was
sewn from.

`pipeline.plan_stitches` re-planned a satin that covered its own inlets as a
fill on a copy of the regions, then handed the guard a `replan` that planned
the ORIGINAL regions: whenever the guard kept its replan, the gear the inlet
rule had moved to fill sewed as a satin again, and nothing said so. Stages
5-7 are stood in for here; what is pinned is which regions each plan is
asked to sew.
"""
from __future__ import annotations

from types import SimpleNamespace

from shapely.geometry import box

from digitizer_core import PipelineConfig, outline_inlets, pipeline, proofread_guard
from digitizer_core.pipeline import BackgroundInfo, PipelineResult
from digitizer_core.regions import Region


def _result():
    gear = Region(shape_id="gear", polygon=box(0, 0, 10, 10), thread_index=1, thread_number="1",
                  area_mm2=100.0, source="test", meta={"layer": 0})
    dot = Region(shape_id="dot", polygon=box(20, 0, 22, 2), thread_index=2, thread_number="2",
                 area_mm2=4.0, source="test", meta={"layer": 0})
    return PipelineResult(regions=[gear, dot], palette=[], background=BackgroundInfo(False),
                          px_per_mm=10.0, design_size_mm=(22.0, 10.0), proof_art=object())


def _stand_ins(monkeypatch, guard_keeps_replan: bool):
    asked = []

    def fake_plan(result, cfg):
        tiers = {r.shape_id: r.meta.get("tier", "auto") for r in result.regions}
        asked.append(tiers)
        return SimpleNamespace(tiers=tiers)

    def fake_guard(result, cfg, plan, replan):
        plan2 = replan(["dot"])
        return plan2 if guard_keeps_replan else plan

    monkeypatch.setattr(pipeline, "_plan_stitches", fake_plan)
    monkeypatch.setattr(outline_inlets, "satin_over_inlets", lambda regions, plan: {"gear": 0.1})
    monkeypatch.setattr(proofread_guard, "guard_clipped", fake_guard)
    return asked


def _cfg(**kw):
    return PipelineConfig(extra={"outline_inlets_kept": True}, **kw)


def test_the_guards_replan_keeps_the_inlet_rules_fill(monkeypatch):
    asked = _stand_ins(monkeypatch, guard_keeps_replan=True)
    plan = pipeline.plan_stitches(_result(), _cfg(proofread_guard_clipped=True))
    assert [a["gear"] for a in asked] == ["auto", "fill", "fill"]   # first plan, inlet re-plan, guard replan
    assert plan.tiers["gear"] == "fill"


def test_a_refused_replan_keeps_the_inlet_plan(monkeypatch):
    _stand_ins(monkeypatch, guard_keeps_replan=False)
    plan = pipeline.plan_stitches(_result(), _cfg(proofread_guard_clipped=True))
    assert plan.tiers["gear"] == "fill"


def test_either_flag_alone_is_the_plan_as_it_was(monkeypatch):
    asked = _stand_ins(monkeypatch, guard_keeps_replan=True)
    plan = pipeline.plan_stitches(_result(), _cfg())                 # inlets alone
    assert [a["gear"] for a in asked] == ["auto", "fill"] and plan.tiers["gear"] == "fill"
    asked.clear()
    plan = pipeline.plan_stitches(_result(), PipelineConfig(proofread_guard_clipped=True))   # guard alone
    assert [a["gear"] for a in asked] == ["auto", "auto"] and plan.tiers["gear"] == "auto"
    res = _result()
    pipeline.plan_stitches(res, _cfg(proofread_guard_clipped=True))
    assert res.regions[0].meta.get("tier") is None                    # the caller's regions untouched
