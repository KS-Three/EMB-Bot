"""`cfg.satin_thin_arm_stop` -- a thin arm stops at a much wider node.

Built OFF 2026-11-17 (prime grader, Toat Machine's M); ON by default since
Kent's flip the same day. The script M's
hairline joins each thick stem near its top. Two junction rules treat that
arm like any other: `satin_junction_stack` runs it INTO the node by its own
half-width, and `_is_tip_end` caps it (`_extend_to_cap`), so a fan of crosses
lands across the stem's own crosses. ON, an arm whose node is at least
`_THIN_ARM_RATIO` times its own width stops at the blob's edge with neither.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from tests.conftest import own_thread_only


class _Field:
    """half_at = 0.8 along the arm (y < 6), 2.4 at the node (y >= 6)."""

    def half_at(self, pt):
        return 0.8 if pt[1] < 6.0 else 2.4


def test_flag_default_is_on():
    """ON since Kent's flip, 2026-11-17 ("Flip ON (Recommended)"); the
    pre-flip engine is `conftest.THIN_ARM_STOP_2026_11_17_OFF`."""
    from .conftest import THIN_ARM_STOP_2026_11_17_OFF
    assert PipelineConfig().satin_thin_arm_stop is True
    assert PipelineConfig(**THIN_ARM_STOP_2026_11_17_OFF).satin_thin_arm_stop is False


def test_a_thin_arm_into_a_wide_node_is_read():
    spine = [(0.0, float(y)) for y in np.arange(0.0, 6.5, 0.5)] + [(0.0, 7.0)]
    assert s6._meets_wider(spine, _Field(), at_start=False)
    assert s6._meets_wider(list(reversed(spine)), _Field(), at_start=True)


def test_an_arm_as_wide_as_its_node_is_not():
    class Even:
        def half_at(self, pt):
            return 1.0

    spine = [(0.0, float(y)) for y in np.arange(0.0, 7.0, 0.5)]
    assert not s6._meets_wider(spine, Even(), at_start=False)


def test_a_spine_too_short_to_read_is_not():
    assert not s6._meets_wider([(0.0, 0.0), (0.0, 1.0)], _Field(), at_start=False)


def test_the_flag_reaches_the_emitter():
    """Toat Machine at 89.5 mm on a hat: ON, the reading is asked and the
    plan changes; OFF it is never asked. A dropped `thin_arm_stop=` anywhere
    on the path would turn ON into OFF with the units above still green."""
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tests.conftest import TESTDATA

    calls = []
    orig = s6._meets_wider

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    gen = None
    counts = {}
    for on in (False, True):
        cfg = PipelineConfig(target_width_mm=89.5, garment_id="hat_front", max_colors=6,
                             satin_thin_arm_stop=on)
        if gen is None:
            gen = build_generation(str(TESTDATA / "art" / "logo_toat_machine.png"), cfg)
        result = finish_generation(gen.fork(), cfg)
        calls.clear()
        s6._meets_wider = own_thread_only(spy, orig)
        try:
            plan = plan_stitches(result, cfg)
        finally:
            s6._meets_wider = orig
        counts[on] = (len(calls), plan.stats.stitch_count)
    assert counts[False][0] == 0
    assert counts[True][0] > 0
    assert counts[True][1] != counts[False][1]


def _judged(monkeypatch, on_runs, off_runs, on_bare, off_bare):
    """`satin_shape_judged` with `satin_shape` and the bare-area reading
    stubbed: the sewn runs are labels, the bare areas are the numbers."""
    seen = []

    def fake(poly, shape_id, **kw):
        seen.append(kw.get("thin_arm_stop"))
        return (on_runs if kw.get("thin_arm_stop") else off_runs), {}

    monkeypatch.setattr(s6, "satin_shape", fake)
    monkeypatch.setattr(s6, "_bare_mm2", lambda poly, runs: on_bare if runs is on_runs else off_bare)
    return s6.satin_shape_judged(None, "S1", thin_arm_stop=True), seen


def test_the_judge_keeps_the_flag_where_nothing_goes_bare(monkeypatch):
    on, off = ["on"], ["off"]
    (runs, _), seen = _judged(monkeypatch, on, off, on_bare=2.8, off_bare=2.8)
    assert runs is on and seen == [True, False]
    (runs, _), _ = _judged(monkeypatch, on, off, on_bare=3.0, off_bare=2.8)    # within the slack
    assert runs is on


def test_the_judge_refuses_the_flag_where_artwork_goes_bare(monkeypatch):
    """MARINE 80 under the first build: 2.8 -> 6.8 mm2 of bare artwork."""
    on, off = ["on"], ["off"]
    (runs, _), _ = _judged(monkeypatch, on, off, on_bare=6.8, off_bare=2.8)
    assert runs is off


def test_the_judge_is_satin_shape_when_the_flag_is_off(monkeypatch):
    calls = []
    monkeypatch.setattr(s6, "satin_shape", lambda poly, sid, **kw: (calls.append(kw), ([], {}))[1])
    s6.satin_shape_judged(None, "S1", thin_arm_stop=False)
    assert len(calls) == 1


def test_the_judge_skips_the_second_sew_when_no_end_stopped(monkeypatch):
    """Becker 96 mm sewed identical thread with the flag ON at +18% plan time
    (the OFF sew was pure cost) and the plan's longest checkpoint-free stretch
    grew past `test_cancel_seams_1113`'s 10%. No end stopped -> the flag-on
    runs ARE the flag-off runs."""
    seen = []

    def fake(poly, shape_id, **kw):
        seen.append(kw.get("thin_arm_stop"))
        s6._THIN_ARM_TALLY.get()[0] += 2       # two ends asked, none stopped
        return ["on"], {}

    monkeypatch.setattr(s6, "satin_shape", fake)
    runs, _ = s6.satin_shape_judged(None, "S1", thin_arm_stop=True)
    assert runs == ["on"] and seen == [True]


def test_the_judge_runs_whole_on_a_call_that_asked_no_end(monkeypatch):
    """A memo hit runs nothing, so a zero tally proves nothing."""
    seen = []

    def fake(poly, shape_id, **kw):
        seen.append(kw.get("thin_arm_stop"))
        return ["on" if kw.get("thin_arm_stop") else "off"], {}

    monkeypatch.setattr(s6, "satin_shape", fake)
    monkeypatch.setattr(s6, "_bare_mm2", lambda poly, runs: 1.0)
    s6.satin_shape_judged(None, "S1", thin_arm_stop=True)
    assert seen == [True, False]


def test_the_judge_checks_for_cancel_between_its_steps(monkeypatch):
    from digitizer_core import deadline

    calls = []
    monkeypatch.setattr(deadline, "check", lambda stage: calls.append(stage))
    monkeypatch.setattr(s6, "satin_shape", lambda poly, sid, **kw: (["on" if kw.get("thin_arm_stop") else "off"], {}))
    monkeypatch.setattr(s6, "_bare_mm2", lambda poly, runs: 1.0)
    s6.satin_shape_judged(None, "S1", thin_arm_stop=True)
    assert calls.count("satin thin-arm judge") >= 4
