"""`sew_enclosed_white` OFF never enters the white path, on the art it acts on.

`enclosed_white_keyline` and `sew_enclosed_white_fields_fill` (#1076) are
read only under `sew_enclosed_white`, so with it OFF the engine is the engine
as it was. (`sew_enclosed_white` is ON by default since Kent's flip
2026-10-26, so the OFF arm here pins it False.) That is only worth asserting on art that HAS the white the options
act on: Becker, whose five white BECKER faces are why the fields-fill option
exists (with them sewn as Column-lane letters, Becker at 100 mm took 8.4x the
time). And it is only a measurement if the tripwires can fire: the control
runs the same patches with `sew_enclosed_white` ON and sees both reached, so
an OFF run that never reaches them is not a test that cannot fail.

Numbers for the flip (timing, the census, the faces beside the pro's) are
`tools/enclosed_pro_census.py`'s, in the PR that added this file.
"""
from __future__ import annotations

import hashlib
import json

from digitizer_core import pipeline, stage7_sequence as s7
from digitizer_core.config import PipelineConfig
from tests.conftest import TESTDATA, own_thread_only

BECKER = TESTDATA / "becker_marine_logo.png"
WIDTH_MM = 50.0
#: the two options that ride on `sew_enclosed_white`
RIDERS = {"enclosed_white_keyline": True, "sew_enclosed_white_fields_fill": True}


class Tripped(AssertionError):
    """The white path was entered."""


def _apply_watch(monkeypatch, trip: bool) -> list[int]:
    """`apply_enclosed_white` (the only writer of `meta["sew_enclosed_white"]`,
    which every rider reads), watched where the pipeline calls it: `trip`
    raises on the call, else each call is counted and runs for real."""
    real = pipeline.apply_enclosed_white
    calls: list[int] = []

    def watch(*a, **k):
        if trip:
            raise Tripped("apply_enclosed_white was called")
        calls.append(1)
        return real(*a, **k)
    monkeypatch.setattr(pipeline, "apply_enclosed_white", own_thread_only(watch, real))
    return calls


def _field_fill_spy(monkeypatch) -> list[str]:
    """Every region `stage7_sequence._white_field_fill` sends to the fill tier."""
    real = s7._white_field_fill
    routed: list[str] = []

    def spy(region, cfg, *a, **k):
        got = real(region, cfg, *a, **k)
        if got:
            routed.append(region.shape_id)
        return got
    monkeypatch.setattr(s7, "_white_field_fill", own_thread_only(spy, real))
    return routed


def _md5(plan) -> str:
    c = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
         for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(c).encode()).hexdigest()


def test_off_the_riders_never_reach_the_white_path_on_becker(monkeypatch):
    _apply_watch(monkeypatch, trip=True)
    routed = _field_fill_spy(monkeypatch)
    result, plan = pipeline.digitize(
        BECKER, PipelineConfig(target_width_mm=WIDTH_MM, sew_enclosed_white=False, **RIDERS))
    assert routed == []
    assert not any((r.meta or {}).get("sew_enclosed_white") for r in result.regions)
    # not vacuous: the art carries the white letter faces the riders act on
    faces = [r for r in result.regions
             if r.meta.get("enclosed_background") and r.meta.get("text_candidate")]
    assert len(faces) >= 5, [r.shape_id for r in faces]
    # and the riders change nothing while `sew_enclosed_white` is OFF
    _r, plain = pipeline.digitize(BECKER, PipelineConfig(target_width_mm=WIDTH_MM,
                                                         sew_enclosed_white=False))
    assert _md5(plan) == _md5(plain)


def test_control_on_both_watches_are_reached_and_the_faces_leave_the_lane(monkeypatch):
    calls = _apply_watch(monkeypatch, trip=False)
    routed = _field_fill_spy(monkeypatch)
    result, _plan = pipeline.digitize(
        BECKER, PipelineConfig(target_width_mm=WIDTH_MM, sew_enclosed_white=True, **RIDERS))
    assert calls == [1]
    faces = {r.shape_id for r in result.regions
             if r.meta.get("enclosed_background") and r.meta.get("text_candidate")}
    assert len(faces) >= 5
    assert faces <= set(routed), sorted(faces - set(routed))
