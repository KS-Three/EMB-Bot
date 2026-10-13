"""The hairline DROP GUARD (2026-10-12): a shape whose strands the tier would
drop is sewn whole by the ladder instead.

PR #872's logo bill found `cfg.hairline` ON erases ink on logos: a path under
`machine.RUN_MIN_LOOP_MM` is dropped, not re-routed, so the arms of a 1.6 mm
capital E vanish ("ENTERPRISES INC" read "CNTPPPISES ING" on enthusiast_logo).
The guard lives in `stage6_hairline.hairline_candidates` (no `cfg` flag: the
tier is unflipped), so stage 5 and stage 7 both see a guarded shape as an
ordinary one. Every number here is a property of the file (ROADMAP gate 1).
"""
from __future__ import annotations

import json
import math

import pytest
from shapely.geometry import LineString
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_hairline as s6h
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.regions import Region
from digitizer_core.stage6_hairline import hairline_candidates, hairline_runs, measure
from digitizer_core.threads import chart_for
from digitizer_core.warnings_codes import HAIRLINE_TIER_SEWN
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

P40 = machine.thread_profile(40)
CHART = chart_for(PipelineConfig())
DARK = int(CHART.lab[:, 0].argmin())


def _small_e(h=2.0, w=1.0, sw=0.3):
    """A capital E of cap height `h` mm drawn as four butt-capped strokes: the
    stem sews as one path, an arm hangs off it under the loop floor."""
    segs = [[(0, 0), (0, h)], [(0, 0), (w, 0)], [(0, h / 2), (w * 0.85, h / 2)], [(0, h), (w, h)]]
    return unary_union([LineString(s).buffer(sw / 2, cap_style=2, join_style=2) for s in segs])


def _region(sid, poly):
    return Region(shape_id=sid, polygon=poly, thread_index=DARK,
                  thread_number=CHART[DARK].number, area_mm2=poly.area,
                  meta={"layer": 0, "stitched": True})


def _walk(poly):
    m = measure(poly, P40.hairline_max_width_mm)
    assert m is not None and m["admit"]
    return m, hairline_runs(poly, "S1", max_width_mm=P40.hairline_max_width_mm,
                            run_width_mm=P40.hairline_run_width_mm, stitch_mm=1.5,
                            entry=None, trim_at_mm=machine.TRIM_AT_MM, m=m)


# --- 1. the loss the guard exists for ---------------------------------------------

def test_the_unguarded_walk_drops_an_arm_of_a_small_e():
    """The premise, pinned: one path sewn, one dropped (ink erased)."""
    _m, (runs, rep) = _walk(_small_e())
    assert rep["strands"] == 1 and rep["dropped"] == 1
    assert len(runs) == 1


def test_a_small_e_is_handed_back_whole():
    e = _small_e()
    region = _region("Se", e)
    got = hairline_candidates([region], PipelineConfig(hairline=True))
    assert "Se" not in got and got.guarded == {"Se": 1}
    assert not got.fragments


def test_without_the_guard_the_small_e_is_a_candidate(monkeypatch):
    monkeypatch.setattr(s6h, "DROP_GUARD", False)
    got = hairline_candidates([_region("Se", _small_e())], PipelineConfig(hairline=True))
    assert "Se" in got and not got.guarded


def test_a_shape_that_drops_nothing_keeps_the_tier():
    """The guard costs a clean strand nothing: a 30 mm stroke sews as before."""
    line = LineString([(0, 0), (30, 0), (45, 6)]).buffer(0.15)
    got = hairline_candidates([_region("Sline", line)], PipelineConfig(hairline=True))
    assert "Sline" in got and not got.guarded


def test_a_stub_off_a_long_strand_does_not_cost_the_shape_its_tier():
    """The hair case. A 120 mm strand with a 1.5 mm stub drops the stub (a path
    under the loop floor) and 1.2 % of its length: the guard leaves the tier
    on, or every hair network would go to the ladder for its crossings'
    leftovers (hair_strands: 2 stubs of 51 paths, -5,485 stitches forfeited
    when the guard fired on ANY drop)."""
    poly = unary_union([LineString([(0, 0), (120, 0)]).buffer(0.15),
                        LineString([(60, 0), (60, 1.5)]).buffer(0.15)])
    n, share = s6h.strand_drops(poly, "Sstub", measure(poly, P40.hairline_max_width_mm),
                                PipelineConfig(hairline=True), 40)
    assert n == 1 and 0.0 < share < s6h.DROP_GUARD_SHARE
    got = hairline_candidates([_region("Sstub", poly)], PipelineConfig(hairline=True))
    assert "Sstub" in got and not got.guarded


def test_a_large_e_loses_no_strand_so_it_is_not_guarded():
    got = hairline_candidates([_region("Sbig", _small_e(h=6.0, w=3.6))],
                              PipelineConfig(hairline=True))
    assert "Sbig" in got and not got.guarded


# --- 2. through the whole pipeline ------------------------------------------------

def _plan_dropped(plan) -> int:
    w = next((w for w in plan.warnings if w["code"] == HAIRLINE_TIER_SEWN), None)
    return 0 if w is None else w["dropped"]


def _sig(plan):
    return _coords_md5([[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
                        for _, r in plan.iter_runs() for x, y in r.points])


@pytest.fixture(scope="module")
def enthusiast():
    """The enthusiast logo, stages 0-4 once, and the plan three ways: OFF,
    hairline ON (guard), hairline ON with the guard off (#872's bill)."""
    path = TESTDATA / "photo" / "enthusiast_logo.png"
    base = dict(target_width_mm=80.0, garment_id="left_chest", thread_wt=40)
    result = run_stages(path, PipelineConfig(**base))
    plans = {"off": plan_stitches(result, PipelineConfig(**base))}
    plans["on"] = plan_stitches(result, PipelineConfig(**base, hairline=True))
    old = s6h.DROP_GUARD
    s6h.DROP_GUARD = False
    try:
        plans["unguarded"] = plan_stitches(result, PipelineConfig(**base, hairline=True))
    finally:
        s6h.DROP_GUARD = old
    return plans


def test_the_enthusiast_tagline_loses_no_strand_with_hairline_on(enthusiast):
    """The done-test. The tagline's capitals ("ENTERPRISES INC") lose arms
    without the guard and nothing with it: not one dropped path in the plan."""
    assert _plan_dropped(enthusiast["unguarded"]) > 0     # the test has teeth
    assert _plan_dropped(enthusiast["on"]) == 0


def test_the_guard_keeps_the_ink_the_unguarded_tier_drops(enthusiast):
    """Fewer shapes are re-sewn, none lose a strand, and the plan still sews
    at least as much thread as the unguarded one did on its dropped paths."""
    def mm(plan):
        return sum(math.dist(a, b) for _, r in plan.iter_runs()
                   for a, b in zip(r.points, r.points[1:]))
    assert _sig(enthusiast["on"]) != _sig(enthusiast["unguarded"])
    assert mm(enthusiast["on"]) > mm(enthusiast["unguarded"])


# --- 3. OFF is byte-identical -----------------------------------------------------

@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_hairline_off_is_byte_identical_to_the_golden(fixture):
    """The guard rides `cfg.hairline`: with it off (the default) nothing it
    added is reached, and the stream is the golden file's md5."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    assert not PipelineConfig().hairline
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            thread_wt=40, hairline=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]
