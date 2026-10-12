"""`machine.thread_profile` and `cfg.thread_wt` (2026-10-12).

Kent: "Thread is extremely thin, we should be able to embroider hair!" The
profile is the one place a thread weight other than 40 is described
(docs/fine-detail-hair-research-2026-10-12.md §4,
docs/hairline-prototype-2026-10-12.md). 60 and 75 are CANDIDATES from vendor
pages — ROADMAP gate 1, no sew-out — so these tests pin what the sources say
and what 40 must stay, not that the candidates are right.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def test_forty_weight_is_every_constant_the_engine_already_used():
    p = machine.thread_profile(40)
    assert p.width_mm == machine.COVERAGE_THREAD_W_MM == 0.40
    assert p.satin_spacing_mm == machine.SATIN_SPACING_MM
    assert p.hairline_run_width_mm == p.width_mm
    assert p.hairline_max_width_mm == pytest.approx(0.6)
    assert machine.thread_profile() is not None
    assert machine.THREAD_WT_DEFAULT == 40


def test_sixty_and_seventy_five_sit_inside_the_vendor_bands():
    p60, p75 = machine.thread_profile(60), machine.thread_profile(75)
    # sqrt(dtex) scaling of 0.40 (Madeira Polyneon 84x2 / 55x2 vs 135x2).
    assert p60.width_mm == pytest.approx(0.40 * (84 / 135) ** 0.5, abs=0.005)
    assert p75.width_mm == pytest.approx(0.40 * (55 / 135) ** 0.5, abs=0.005)
    # Amann: 0.30-0.35 for 60 wt, 0.20-0.25 for 75 wt.
    assert 0.30 <= p60.satin_spacing_mm <= 0.35
    assert 0.20 <= p75.satin_spacing_mm <= 0.25
    assert p60.hairline_max_width_mm == pytest.approx(0.48)
    # Finer thread, finer everything that IS thread.
    assert p75.width_mm < p60.width_mm < machine.thread_profile(40).width_mm


def test_the_minimum_stitch_does_not_move_with_thread_weight():
    """The shortest stitch is the NEEDLE's floor (Melco "Stitches Too Small":
    a needle is 0.7-0.8 mm across; #843 §1), not the thread's. A finer thread
    does not lower it. If this goes red because someone "optimised" the
    floor for 60 wt, that is the change that is wrong."""
    for wt in machine.THREAD_WEIGHTS:
        assert machine.thread_profile(wt).min_stitch_mm == machine.MIN_STITCH_MM == 1.0


def test_cap_height_notes_and_needle_advice_carry_the_disagreements():
    p40, p60, p75 = (machine.thread_profile(w) for w in (40, 60, 75))
    assert (p40.min_cap_height_mm, p60.min_cap_height_mm, p75.min_cap_height_mm) == (6.0, 4.0, 3.0)
    assert "DISAGREE" in p60.cap_height_note
    for s in ("3 mm", "4-5 mm", "4 mm"):
        assert s in p60.cap_height_note
    # Madeira and Wilcom disagree on the 60 wt needle; both are carried.
    assert "60/8-65/9" in p60.needle_advice and "70/10-75/11" in p60.needle_advice
    assert "60/8" in p75.needle_advice


@pytest.mark.parametrize("bad", [50, 30, 100, True, "60", None])
def test_an_unknown_weight_is_refused(bad):
    with pytest.raises(ValueError):
        machine.thread_profile(bad)


def test_profile_is_read_only():
    p = machine.thread_profile(60)
    with pytest.raises(AttributeError):
        p.width_mm = 0.1


def test_config_defaults_are_today():
    cfg = PipelineConfig()
    assert cfg.thread_wt == 40
    assert cfg.hairline is False
    assert cfg.hairline_stitch_mm == 1.5


def test_shape_override_thread_wt_is_validated_and_stored():
    from digitizer_core.regions import apply_shape_edits
    from digitizer_core.threads import chart_for

    result = run_stages(TESTDATA / "ribbon_curve.png", PipelineConfig(target_width_mm=80.0))
    sid = result.regions[0].shape_id
    regions, threads, _w = apply_shape_edits(list(result.regions), list(result.thread_indices),
                                             [], {sid: {"thread_wt": 60}}, chart_for(PipelineConfig()))
    assert next(r for r in regions if r.shape_id == sid).meta["thread_wt"] == 60
    with pytest.raises(ValueError, match="thread_wt"):
        apply_shape_edits(list(result.regions), list(result.thread_indices),
                          [], {sid: {"thread_wt": 50}}, chart_for(PipelineConfig()))


def test_service_refuses_an_unknown_weight_at_submit():
    pytest.importorskip("fastapi")
    from fastapi import HTTPException

    from digitizer_service import app as svc

    svc._validate_config_dict({"thread_wt": 60}, svc._CONFIG_FIELDS)
    with pytest.raises(HTTPException):
        svc._validate_config_dict({"thread_wt": 55}, svc._CONFIG_FIELDS)
    assert "thread_wt" in svc._OVERRIDE_KEYS


# --- OFF is byte-identical -----------------------------------------------------
#
# The three flat-lane goldens CI runs (`test_flat_lane_byte_identical.py`;
# `photo/enthusiast_logo.png` is the platform red it deselects). The md5 is of
# the golden FILE's stitch stream, pinned here so the golden cannot be quietly
# re-captured to absorb this change; the snapshot is re-computed with the new
# fields set explicitly to their defaults.

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _coords_md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_thread_wt_40_and_hairline_off_is_byte_identical_to_the_golden(fixture):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            thread_wt=40, hairline=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]


# --- 60 wt moves satin spacing and nothing else -------------------------------

def _satin_pitch(plan) -> float:
    """Median same-rail step of the satin runs: two crosses per station, so
    a rail point recurs every second penetration, one spacing apart."""
    import math
    import statistics

    steps = []
    for _, r in plan.iter_runs():
        if r.kind != "satin":
            continue
        pts = r.points
        steps += [math.dist(a, b) for a, b in zip(pts, pts[2:])]
    return statistics.median(steps)


def test_sixty_weight_changes_satin_spacing_and_nothing_else():
    result = run_stages(TESTDATA / "ribbon_curve.png", PipelineConfig(target_width_mm=80.0))
    p40 = plan_stitches(result, PipelineConfig(target_width_mm=80.0, thread_wt=40))
    p60 = plan_stitches(result, PipelineConfig(target_width_mm=80.0, thread_wt=60))
    sat40 = sum(len(r.points) for _, r in p40.iter_runs() if r.kind == "satin")
    sat60 = sum(len(r.points) for _, r in p60.iter_runs() if r.kind == "satin")
    assert sat40 > 0
    # 0.40 -> 0.32: about 1.25x the crosses.
    assert sat60 / sat40 == pytest.approx(0.40 / 0.32, rel=0.08)
    assert _satin_pitch(p60) < _satin_pitch(p40)
    # Nothing else: same blocks, same threads, same warnings, and every
    # non-satin run kind sews the same number of runs.
    assert [b.thread_number for b in p40.blocks] == [b.thread_number for b in p60.blocks]
    assert sorted(w["code"] for w in p40.warnings) == sorted(w["code"] for w in p60.warnings)

    def kinds(plan):
        out = {}
        for _, r in plan.iter_runs():
            if r.kind != "satin":
                out[r.kind] = out.get(r.kind, 0) + 1
        return out
    assert kinds(p40) == kinds(p60)
