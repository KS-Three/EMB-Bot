"""The word-thread rule's guard (`cfg.group_consistent_thread`, held OFF by Kent
2026-11-14, "Hold it, guard first").

The rule moves a lone text-cluster letter onto its word's thread. On
drone_render (80 mm left_chest) it moved a Pumpkin 1102 shape onto Fox Fire
1305, which matches that shape's own artwork worse (7.3 -> 13.0 dE00, past
preflight's 10 "clearly different" line): Fox Fire's finding went warn -> block
and the grade D -> F. The guard reads each candidate's artwork the way
preflight grades it (`stage4_vectorize.art_thread_errors`) and refuses a move to
a worse-matching thread. Bridge's U of RESTAURANT, the case the rule was built
for, matches its word's Caribbean better than its own snap (15.3 -> 14.1) and
still moves.
"""
from __future__ import annotations

import pytest

from digitizer_core import PipelineConfig
from digitizer_core import lettering_thread as lt
from digitizer_core import pipeline as pl
from digitizer_core.pipeline import digitize
from digitizer_core.preflight import run_preflight
from digitizer_core.threads import chart_for

from .conftest import TESTDATA

from .test_group_consistency import CARIBBEAN, SWISS_IVY, _cluster

CHART = chart_for(PipelineConfig())
LONE, WORD = SWISS_IVY, CARIBBEAN     # Bridge's U of RESTAURANT and its ten siblings


def _word():
    return _cluster([WORD] * 10 + [LONE])


def _guard(old, new):
    return lambda r, ts: {LONE: old, WORD: new}


def test_the_two_threads_are_near_enough_for_the_rule_to_try():
    assert CHART.delta_e(LONE, WORD) <= lt.STRAY_MAX_DE00


def test_no_guard_moves_the_lone_letter_as_built():
    regs = _word()
    assert lt.word_thread(regs, CHART, {}) == 1
    assert regs[-1].thread_index == WORD


def test_a_worse_matching_word_thread_is_refused_and_says_so():
    regs = _word()
    assert lt.word_thread(regs, CHART, {}, art_errors=_guard(7.29, 13.04)) == 0
    assert regs[-1].thread_index == LONE
    assert regs[-1].meta["lettering_word_thread_refused"] == [7.29, 13.04]
    assert "lettering_word_thread_from" not in regs[-1].meta


@pytest.mark.parametrize("old,new", [(15.29, 14.11), (6.0, 6.0)], ids=["better", "equal"])
def test_a_word_thread_no_worse_still_moves(old, new):
    regs = _word()
    assert lt.word_thread(regs, CHART, {}, art_errors=_guard(old, new)) == 1
    assert regs[-1].thread_index == WORD


def test_no_pixels_to_read_leaves_the_move_as_built():
    regs = _word()
    assert lt.word_thread(regs, CHART, {}, art_errors=lambda r, ts: None) == 1


def test_flag_off_never_builds_the_reader(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("art_thread_errors built with the flag OFF")
    monkeypatch.setattr(pl, "art_thread_errors", boom)
    digitize(TESTDATA / "photo/logo_bridge_bar.jpg",
             PipelineConfig(target_width_mm=60.0, group_consistent_thread=False))


def _thread_findings(art, on):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", group_consistent_thread=on)
    result, plan = digitize(art, cfg)
    rep = run_preflight(result, plan, cfg, image=art)
    return result, rep, sorted((f["severity"], f["extra"]["thread_number"]) for f in rep["findings"]
                               if f["code"] == "THREAD_MATCH_POOR")


def test_drone_keeps_its_pumpkin_shape_and_its_grade():
    art = TESTDATA / "photo/drone_render.png"
    _r, rep_off, tm_off = _thread_findings(art, False)
    result, rep_on, tm_on = _thread_findings(art, True)
    refused = {r.meta["lettering_word_thread_refused"][1] > r.meta["lettering_word_thread_refused"][0]
               for r in result.regions if "lettering_word_thread_refused" in r.meta}
    assert refused == {True}
    assert not any("lettering_word_thread_from" in r.meta for r in result.regions)
    assert tm_on == tm_off
    assert (rep_on["grade"], rep_on["score"]) == (rep_off["grade"], rep_off["score"])
