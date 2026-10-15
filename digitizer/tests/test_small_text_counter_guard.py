"""The true-size switch's counter guard (`cfg.small_text_true_size_min_counter_mm`,
Kent WoK 56 option A; `config.SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM` 0.5 x
thread_wt / 40 mm, a gate-1 CANDIDATE). It replaced a 1.6 mm cap-height guard
that could not separate Fremont's Hat 81 mm date (better ON) from its 65 mm
tagline (worse ON): the tagline's cost is its A's apex counters closing, so
the guard reads the narrowest SOURCE counter of a line. A line under it takes
today's path -- not restored, not tagged bean, byte for byte the engine
before the flip; a line with no counter passes.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, beanletters, digitize, small_text
from digitizer_core.config import (SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM, counter_floor_mm,
                                   true_size_min_counter)
from digitizer_core.ink_path import MemberInk

from .conftest import own_thread_only
from .test_small_text import _glyphs, _scene, _tag, _two_lines

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def _narrow(words=("1895",)) -> float:
    """The scene's narrowest source counter, as the restore step reads it."""
    regions, p = _scene(words=words)
    _tag(regions, {r.shape_id for r in _glyphs(regions)})
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_counter_mm=1e-6)
    return next(r for r in rep if r["cluster"] == "TCtest")["min_counter_mm"]


def test_the_guard_is_read_only_while_the_switch_is_on():
    assert SMALL_TEXT_TRUE_SIZE_MIN_COUNTER_MM == 0.5
    assert PipelineConfig().small_text_true_size_min_counter_mm == 0.5
    assert true_size_min_counter(PipelineConfig()) == 0.5
    # switch OFF: explicit restore / bean values act on every line, as before
    assert true_size_min_counter(PipelineConfig(small_text_true_size=False)) is None
    assert true_size_min_counter(PipelineConfig(small_text_true_size_min_counter_mm=None)) is None


def test_the_switch_fills_keep_stray_lines_and_an_explicit_value_wins():
    assert PipelineConfig().small_text_keep_stray_lines is True
    assert PipelineConfig(small_text_keep_stray_lines=False).small_text_keep_stray_lines is False
    assert PipelineConfig(small_text_true_size=False).small_text_keep_stray_lines is None
    cfg = PipelineConfig()
    cfg.small_text_true_size = False            # the setattr OFF arm clears what it filled
    assert cfg.small_text_keep_stray_lines is None


def test_the_floor_scales_with_thread_weight():
    assert counter_floor_mm(0.5, 40) == pytest.approx(0.5)
    assert counter_floor_mm(0.5, 60) == pytest.approx(0.75)
    assert counter_floor_mm(0.5, 75) == pytest.approx(0.9375)


def test_the_scene_has_counters_and_the_measure_is_their_inscribed_width():
    narrow = _narrow()
    # Hershey "1895" at a ~2 mm cap: the 8's and 9's loops, a few tenths of a mm
    assert narrow is not None and 0.1 < narrow < 1.0, narrow
    assert _narrow(words=("1717",)) is None, "a line with no counter has none"


def test_restore_leaves_a_line_below_the_guard_untouched():
    narrow = _narrow()
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_counter_mm=narrow * 1.05)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert row["skipped"] == "below_min_counter" and row["min_counter_mm"] == narrow
    after = [(r.shape_id, r.polygon.wkb, {k: v for k, v in r.meta.items() if k != small_text.GUARD_KEY})
             for r in regions]
    assert after == before, "nothing adopted, retraced or stripped"
    assert all(r.meta.get(small_text.GUARD_KEY) for r in regions if r.meta.get("text_cluster_id"))


def test_restore_still_restores_a_line_above_the_guard():
    narrow = _narrow()
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_counter_mm=narrow * 0.95)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row and row.get("adopted") == 1, row
    assert not any(r.meta.get(small_text.GUARD_KEY) for r in regions)


def test_a_line_with_no_counter_passes_any_floor():
    regions, p = _scene(words=("1717",))
    _tag(regions, {r.shape_id for r in _glyphs(regions)})
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_counter_mm=100.0)
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert "skipped" not in row and row["min_counter_mm"] is None, row


@pytest.mark.parametrize("wt, guarded", [(40, False), (60, True)])
def test_the_line_meets_its_own_threads_floor(wt, guarded):
    narrow = _narrow()
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg2", "Sg3"})
    # base 0.8 x narrow: 40 wt floor 0.8 x narrow passes; 60 wt 1.2 x narrow does not
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, min_counter_mm=narrow * 0.8,
                                        thread_wts={7: wt})
    row = next(r for r in rep if r["cluster"] == "TCtest")
    assert (row.get("skipped") == "below_min_counter") is guarded, row


def test_a_guarded_cluster_keeps_its_stray_line():
    """65 mm Fremont: THE (no counter) shares the date's cluster, the date is
    under the guard. The whole cluster takes today's path, THE included:
    releasing THE re-routed the rest of the design, the guarded tagline with
    it. Over the guard the stray line still leaves (`keep_stray_lines`)."""
    narrow = _narrow()
    regions, p, glyphs = _two_lines()
    before = [(r.shape_id, r.polygon.wkb, dict(r.meta)) for r in regions]
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, keep_stray_lines=True,
                                        min_counter_mm=narrow * 1.05)
    assert [r["cluster"] for r in rep] == ["TCmerged"]
    assert rep[0]["skipped"] == "below_min_counter" and "stray_line" not in rep[0]
    assert all(r.meta.get(small_text.GUARD_KEY) for r in glyphs)
    after = [(r.shape_id, r.polygon.wkb, {k: v for k, v in r.meta.items() if k != small_text.GUARD_KEY})
             for r in regions]
    assert after == before
    regions, p, glyphs = _two_lines()
    rep = small_text.restore_small_text(regions, p, cap_mm=3.0, keep_stray_lines=True,
                                        min_counter_mm=narrow * 0.95)
    assert rep[0].get("stray_line") and len(rep) == 2


@pytest.mark.parametrize("scale, reads", [(1.05, False), (0.95, True)])
def test_bean_tagging_reads_no_ink_below_the_guard(monkeypatch, scale, reads):
    narrow = _narrow()
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    calls = []

    def fake(_p, members, **_kw):
        calls.append(len(members))
        return [MemberInk(stroke_mm=None, spines=[]) for _ in members]

    monkeypatch.setattr(beanletters, "read_cluster_ink", own_thread_only(fake, beanletters.read_cluster_ink))
    cfg = PipelineConfig(small_text_true_size_min_counter_mm=narrow * scale)
    assert beanletters.tag_bean_letters(regions, p, cfg) == 0
    assert bool(calls) is reads
    assert not any(beanletters.BEAN_LETTER_KEY in r.meta or "ink_stroke_mm" in r.meta for r in regions)


def test_bean_tagging_takes_the_restore_steps_verdict(monkeypatch):
    """A line the restore step guarded stays guarded for the bean tagger even
    when its own cluster (without the adopted 8) would pass."""
    regions, p = _scene()
    _tag(regions, {"Sg0", "Sg1", "Sg2", "Sg3"})
    for r in regions:
        if r.meta.get("text_cluster_id"):
            r.meta[small_text.GUARD_KEY] = True
    calls = []
    monkeypatch.setattr(beanletters, "read_cluster_ink", own_thread_only(
        lambda _p, m, **_k: calls.append(1) or [MemberInk() for _ in m], beanletters.read_cluster_ink))
    beanletters.tag_bean_letters(regions, p, PipelineConfig(small_text_true_size_min_counter_mm=1e-6))
    assert calls == []


# --- end to end: the small-print census's synthetic line ---------------------------
# md5 prefixes measured 2026-10-15 (`plan.iter_runs()` coords). "off" is the engine
# before the flip (`small_text_true_size=False`), pinned so an OFF drift is caught;
# "unguarded" is the switch with no counter guard. The synthetic line's narrowest
# source counter is 0.28 mm at a 1.55 mm cap and 0.455 at 2.5 (under 0.5: the
# default is the engine before the flip), 0.546 at 3 (over it: the default is the
# switch). At 2.5 mm the old 1.6 mm cap guard let the switch act; this one does not.
MD5 = {1.55: {"off": "dbb6380a91", "unguarded": "1644330929"},
       2.5: {"off": "1ad15a6e07", "unguarded": "a502e7908a"},
       3: {"off": "5da6cf3d84", "unguarded": "88822294f9"}}


def _md5(cap, **kw):
    from tools import small_print
    ref = json.loads((TESTDATA / "small_print_synthetic_ref.json").read_text())
    _r, plan = digitize(small_print.load("synthetic"),
                        PipelineConfig(target_width_mm=round(cap / ref["cap"], 2), **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()[:10]


@pytest.mark.parametrize("cap", [1.55, 2.5])
def test_below_the_guard_the_default_is_the_engine_before_the_flip(cap):
    off = _md5(cap, small_text_true_size=False)
    assert off == MD5[cap]["off"]
    assert _md5(cap) == off
    assert _md5(cap, small_text_true_size_min_counter_mm=None) == MD5[cap]["unguarded"]


def test_above_the_guard_the_default_is_the_switch():
    assert _md5(3, small_text_true_size=False) == MD5[3]["off"]
    assert _md5(3) == MD5[3]["unguarded"]
