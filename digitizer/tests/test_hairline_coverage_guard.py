"""`cfg.hairline_coverage_guard` (2026-10-13, default OFF): a shape whose
hairline runs would leave bare artwork keeps its pre-hairline construction.

PR #872 priced `cfg.hairline` on ordinary logos and found bare fabric and new
`ARTWORK_UNCOVERED`; #879's drop guard removed the erased-strand half. This
guard takes the rest: a 0.4 mm ribbon along a 0.5 mm stroke leaves its edges
bare. `tools/hairline_coverage.py` measured it (docs/renders/
claude-hairline-coverage-guard/). Every number is a property of the file
(ROADMAP gate 1); the cut is a candidate.
"""
from __future__ import annotations

import json

import pytest
from shapely.geometry import LineString

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_hairline as s6h
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_hairline import hairline_candidates, hairline_runs, measure
from tests.test_hairline_drop_guard import _region
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

P40 = machine.thread_profile(40)


def _stroke(width, length=30.0):
    return LineString([(0, 0), (length, 0)]).buffer(width / 2, cap_style=2)


def _bare(poly):
    m = measure(poly, P40.hairline_max_width_mm)
    assert m is not None and m["admit"]
    runs, _rep = hairline_runs(poly, "S1", max_width_mm=P40.hairline_max_width_mm,
                               run_width_mm=P40.hairline_run_width_mm, stitch_mm=1.5,
                               entry=None, trim_at_mm=machine.TRIM_AT_MM, m=m)
    return s6h.strand_bare_mm2(poly, runs, m)


# --- 1. default and the predictor ---------------------------------------------------

def test_the_guard_is_off_by_default():
    assert PipelineConfig().hairline_coverage_guard is False


def test_a_hair_wide_stroke_is_covered_by_its_ribbon():
    """0.3 mm of ink under a 0.4 mm ribbon: nothing bare but the end caps."""
    assert _bare(_stroke(0.30)) < s6h.COVERAGE_GUARD_MM2


def test_a_stroke_wider_than_the_ribbon_leaves_its_edges_bare():
    """0.58 mm is under the 0.6 mm width gate (admitted) and over the ribbon's
    reach (0.4 + the instrument's slack): both edges of 30 mm are bare."""
    assert _bare(_stroke(0.58)) > 3 * s6h.COVERAGE_GUARD_MM2


# --- 2. the guard on the candidate set ----------------------------------------------

def test_a_wide_stroke_is_handed_back_when_the_guard_is_on():
    wide = _region("Swide", _stroke(0.58))
    got = hairline_candidates([wide], PipelineConfig(hairline=True, hairline_coverage_guard=True))
    assert "Swide" not in got and got.guarded_coverage["Swide"] > s6h.COVERAGE_GUARD_MM2
    assert not got.guarded


def test_a_wide_stroke_keeps_the_tier_when_the_guard_is_off():
    wide = _region("Swide", _stroke(0.58))
    got = hairline_candidates([wide], PipelineConfig(hairline=True))
    assert "Swide" in got and not got.guarded_coverage


def test_a_thin_stroke_keeps_the_tier_with_the_guard_on():
    """The tier's own use case is untouched."""
    thin = _region("Sthin", _stroke(0.30))
    got = hairline_candidates([thin], PipelineConfig(hairline=True, hairline_coverage_guard=True))
    assert "Sthin" in got and not got.guarded_coverage


# --- 3. through the pipeline, on a logo that triggers it ----------------------------

@pytest.fixture(scope="module")
def enthusiast():
    from tools.hairline_renders import bare_cells
    from digitizer_core import preflight
    path = TESTDATA / "photo" / "enthusiast_logo.png"
    base = dict(target_width_mm=80.0, garment_id="left_chest", thread_wt=40)
    result = run_stages(path, PipelineConfig(**base))
    p = preflight.prep(path, PipelineConfig(**base), design_class=result.design_class)
    out = {}
    for name, kw in (("off", {}), ("on", dict(hairline=True)),
                     ("cov", dict(hairline=True, hairline_coverage_guard=True))):
        plan = plan_stitches(result, PipelineConfig(**base, **kw))
        grid, _o, cell = bare_cells(plan, result, p)
        out[name] = {"plan": plan, "bare_mm2": float(grid.sum()) * cell * cell}
    return out


def test_the_guard_takes_bare_fabric_back_toward_off_on_the_enthusiast_logo(enthusiast):
    """The done-test. Measured at the time of writing: bare 2.62 mm2 OFF, 4.75
    ON, and the guard returns most of the difference. The assertion is the
    ordering, not the digits."""
    off, on, cov = (enthusiast[k]["bare_mm2"] for k in ("off", "on", "cov"))
    assert on > off, "hairline ON no longer adds bare fabric here: the test has no teeth"
    assert cov < on
    assert cov - off < 0.5 * (on - off)


def test_the_guard_keeps_some_of_the_tier_on_the_enthusiast_logo(enthusiast):
    """It is a guard, not an off switch: the plan with it is smaller than OFF's."""
    def n(plan):
        return sum(len(r.points) for _, r in plan.iter_runs())
    assert n(enthusiast["cov"]["plan"]) < n(enthusiast["off"]["plan"])


# --- 4. OFF is byte-identical -------------------------------------------------------

@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical_with_the_guard_flag_set(fixture):
    """`hairline_coverage_guard` is only read under `cfg.hairline`: with the
    tier off the stream is the golden file's md5 whatever the flag says."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", thread_wt=40,
                                            hairline=False, hairline_coverage_guard=True))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]
