"""`cfg.bean_letter_max_stroke_mm` end to end — the decision, the tag, the
ground under the letter and the stitches
(`docs/superpowers/specs/2026-10-02-bean-letters-design.md`).

Bridge is the fixture the rule was built on: a 400 px JPEG, 3.5 px/mm at
80 mm, whose teal "BAR & RESTAURANT" has 0.6-0.8 mm strokes and sewed as one
satin blob per letter.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import Point

from digitizer_core import PipelineConfig, stitches
from digitizer_core.beanletters import BEAN_LETTER_KEY, MIN_GROUP_MEMBERS, weight_groups
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import LETTERING_TOO_SMALL, run_preflight
from digitizer_core.warnings_codes import SMALL_LETTERING_AS_BEAN

BRIDGE = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "logo_bridge_bar.jpg"
LINE = 1.0


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6, **kw)


# --- the decision ------------------------------------------------------------

def test_it_is_built_off():
    assert PipelineConfig().bean_letter_max_stroke_mm is None


def test_one_weight_decides_by_its_median_and_carries_its_fused_pairs():
    """Bridge's eight: six letters at 0.6-0.8 and two fused pairs over the
    line. Two is not a second weight, so the median speaks for all eight."""
    widths = [0.78, 0.75, 0.63, 1.08, 1.17, 0.76, 0.67, 0.60]
    assert weight_groups(widths, LINE) == [True] * 8
    assert weight_groups([1.5, 1.75, 1.92, 1.67], LINE) == [False] * 4


def test_two_real_weights_in_one_cluster_decide_separately():
    """Golke: a bold line and a thin line tagged as one cluster."""
    bold, thin = [1.25, 1.32, 1.45, 1.40], [0.62, 0.67, 0.60, 0.58]
    assert weight_groups(bold + thin, LINE) == [False] * 4 + [True] * 4
    assert MIN_GROUP_MEMBERS == 3
    assert weight_groups([1.25, 1.32, 0.62, 0.67, 0.60, 0.58], LINE) == [True] * 6   # two bold: carried


def test_a_member_with_no_ink_never_goes():
    assert weight_groups([0.7, None, 0.6], LINE) == [True, False, True]
    assert weight_groups([None, None], LINE) == [False, False]
    assert weight_groups([], LINE) == []


# --- bridge ------------------------------------------------------------------

@pytest.fixture(scope="module")
def bridge():
    gen = build_generation(str(BRIDGE), _cfg())

    def run(**kw):
        cfg = _cfg(**kw)
        result = finish_generation(gen.fork(), cfg)
        return cfg, result, plan_stitches(result, cfg)

    return {"off": run(), "on": run(bean_letter_max_stroke_mm=LINE), "run": run, "gen": gen}


def _kinds(plan, shape_id: str) -> set[str]:
    return {r.kind for _b, r in plan.iter_runs() if r.shape_id == shape_id}


def test_off_tags_nothing_and_says_nothing(bridge):
    _cfg_, result, plan = bridge["off"]
    assert not any(BEAN_LETTER_KEY in r.meta or "ink_stroke_mm" in r.meta for r in result.regions)
    assert SMALL_LETTERING_AS_BEAN not in {w["code"] for w in plan.warnings}


def test_bridges_words_are_tagged_and_sew_as_runs_along_their_ink(bridge):
    _cfg_, result, plan = bridge["on"]
    members = [r for r in result.regions if r.meta.get("text_cluster_id")]
    tagged = [r for r in members if r.meta.get(BEAN_LETTER_KEY)]
    assert len(members) >= 6 and len(tagged) == len(members)
    for r in tagged:
        assert r.meta["ink_stroke_mm"] < 1.3
        assert _kinds(plan, r.shape_id) == {stitches.RUN}
        near = r.polygon.buffer(0.6)                         # the ink may stand a little off the traced blob
        pts = [p for _b, run in plan.iter_runs() if run.shape_id == r.shape_id for p in run.points]
        assert pts and all(near.contains(Point(p)) for p in pts)


def test_the_engine_says_what_it_did_and_asks_for_nothing(bridge):
    cfg, result, plan = bridge["on"]
    tagged = {r.shape_id for r in result.regions if r.meta.get(BEAN_LETTER_KEY)}
    w = next(w for w in plan.warnings if w["code"] == SMALL_LETTERING_AS_BEAN)
    assert w["count"] == len(tagged) and w["words"] == 1
    report = run_preflight(result, plan, cfg, image=str(BRIDGE))
    for f in report["findings"]:
        if f["code"] == LETTERING_TOO_SMALL:
            assert not tagged & {s["shape_id"] for s in f["extra"]["shapes"]}


def test_the_ground_sews_through_under_a_bean_letter(bridge):
    """A 0.4 mm line of thread does not cover the hole the traced letter left
    in its ground, so the ground fills it: every bean letter lies inside the
    stitched footprint of an earlier colour."""
    from digitizer_core.pipeline import fabric_for
    from digitizer_core.stage5_overlap import resolve_overlaps
    cfg, result, _plan = bridge["on"]
    planned, _warnings = resolve_overlaps([r for r in result.regions if r.meta.get("stitched", True)],
                                          fabric_for(cfg), cfg, design_class=result.design_class)
    by_id = {p.region.shape_id: p for p in planned}
    for r in result.regions:
        if not r.meta.get(BEAN_LETTER_KEY):
            continue
        earlier = [p.polygon for p in planned if p.sew_index < by_id[r.shape_id].sew_index]
        covered = max((r.polygon.intersection(g).area for g in earlier), default=0.0)
        assert covered >= 0.9 * r.polygon.area, r.shape_id


def test_a_tier_the_user_set_is_an_instruction(bridge):
    _cfg_, on, _plan = bridge["on"]
    pinned = next(r.shape_id for r in on.regions if r.meta.get(BEAN_LETTER_KEY))
    _c, result, plan = bridge["run"](bean_letter_max_stroke_mm=LINE,
                                     shape_overrides={pinned: {"tier": "satin"}})
    region = next(r for r in result.regions if r.shape_id == pinned)
    assert BEAN_LETTER_KEY not in region.meta
    assert stitches.SATIN in _kinds(plan, pinned)


def test_a_letter_with_nothing_sewable_falls_through_to_the_ladder(bridge):
    cfg, on, _plan = bridge["on"]
    result = finish_generation(bridge["gen"].fork(), cfg)
    victim = next(r for r in result.regions if r.meta.get(BEAN_LETTER_KEY))
    victim.meta[BEAN_LETTER_KEY] = [[(0.0, 0.0), (0.2, 0.0)]]            # a speck: under the run floor
    plan = plan_stitches(result, cfg)
    assert _kinds(plan, victim.shape_id), "the letter must still sew"
