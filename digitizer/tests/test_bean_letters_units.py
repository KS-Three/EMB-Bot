"""Edge cases for `beanletters` and `stage6_beanletter` that the happy-path
files (`test_bean_letter.py`, `test_bean_letters_pipeline.py`) leave open:
`tag_bean_letters` on stub regions (no image, no pipeline), the weight-line
boundary, and `bean_letter`'s ordering, thresholds and input handling."""
from __future__ import annotations

import math
from types import SimpleNamespace

import pytest

from digitizer_core import PipelineConfig, beanletters, machine, stitches
from digitizer_core.beanletters import BEAN_LETTER_KEY, tag_bean_letters, weight_groups
from digitizer_core.ink_path import MemberInk
from digitizer_core.stage6_beanletter import bean_letter

SPINE = [(0.0, 0.0), (0.0, 5.0)]


# --- weight_groups -------------------------------------------------------------

def test_a_median_exactly_on_the_line_is_not_bean():
    assert weight_groups([1.0, 1.0, 1.0], 1.0) == [False] * 3


def test_a_single_member_decides_alone():
    assert weight_groups([0.5], 1.0) == [True]
    assert weight_groups([2.0], 1.0) == [False]


def test_a_real_split_cuts_between_the_groups_not_at_the_line():
    widths = [0.5, 0.6, 0.7, 1.4, 1.5, 1.6]
    assert weight_groups(widths, 1.0) == [True] * 3 + [False] * 3
    # a thin value NOT over the line stays bean wherever it sits in the input
    assert weight_groups([1.5, 0.6, 1.4, 0.5, 1.6, 0.7], 1.0) == [False, True, False, True, False, True]


def test_two_groups_on_one_side_of_the_line_decide_by_the_whole_median():
    assert weight_groups([0.4, 0.5, 0.6, 0.8, 0.85, 0.9], 1.0) == [True] * 6
    assert weight_groups([1.2, 1.3, 1.4, 1.8, 1.9, 2.0], 1.0) == [False] * 6


# --- tag_bean_letters ----------------------------------------------------------

def _region(cid="c1", **meta):
    m = {"text_cluster_id": cid, **meta}
    return SimpleNamespace(meta=m)


def _stub_ink(monkeypatch, inks):
    seen = []

    def fake(p, members):
        seen.append(list(members))
        return [inks[id(r)] for r in members]

    monkeypatch.setattr(beanletters, "read_cluster_ink", fake)
    return seen


def _cfg(**kw):
    return PipelineConfig(bean_letter_max_stroke_mm=1.0, **kw)


def test_tag_reads_nothing_when_off_or_without_a_page(monkeypatch):
    def boom(*_a):
        raise AssertionError("ink must not be read")

    monkeypatch.setattr(beanletters, "read_cluster_ink", boom)
    r = _region()
    assert tag_bean_letters([r], object(), PipelineConfig()) == 0
    assert tag_bean_letters([r], None, _cfg()) == 0
    assert BEAN_LETTER_KEY not in r.meta and "ink_stroke_mm" not in r.meta


def test_tag_writes_spines_and_rounded_width_on_the_members_that_go(monkeypatch):
    a, b = _region(), _region()
    inks = {id(a): MemberInk(stroke_mm=0.71234, spines=[SPINE]),
            id(b): MemberInk(stroke_mm=0.6, spines=[])}
    _stub_ink(monkeypatch, inks)
    assert tag_bean_letters([a, b], object(), _cfg()) == 1
    assert a.meta[BEAN_LETTER_KEY] == [SPINE] and a.meta["ink_stroke_mm"] == 0.712
    # thin enough to go, but no spine to sew: width recorded, nothing tagged
    assert BEAN_LETTER_KEY not in b.meta and b.meta["ink_stroke_mm"] == 0.6


def test_a_heavy_cluster_records_its_width_and_tags_nothing(monkeypatch):
    a = _region()
    _stub_ink(monkeypatch, {id(a): MemberInk(stroke_mm=1.8, spines=[SPINE])})
    assert tag_bean_letters([a], object(), _cfg()) == 0
    assert BEAN_LETTER_KEY not in a.meta and a.meta["ink_stroke_mm"] == 1.8


def test_a_member_without_ink_gets_no_width(monkeypatch):
    a = _region()
    _stub_ink(monkeypatch, {id(a): MemberInk(stroke_mm=None, spines=[])})
    assert tag_bean_letters([a], object(), _cfg()) == 0
    assert "ink_stroke_mm" not in a.meta


@pytest.mark.parametrize("meta", [{"tier": "satin"}, {"tier": "run"}, {"stitched": False}])
def test_pinned_or_switched_off_members_are_left_out(monkeypatch, meta):
    skip, keep = _region(**meta), _region()
    inks = {id(keep): MemberInk(stroke_mm=0.6, spines=[SPINE])}
    seen = _stub_ink(monkeypatch, inks)
    assert tag_bean_letters([skip, keep], object(), _cfg()) == 1
    assert seen == [[keep]]
    assert BEAN_LETTER_KEY not in skip.meta and "ink_stroke_mm" not in skip.meta


def test_tier_auto_is_case_insensitive_and_the_default(monkeypatch):
    a, b = _region(tier="AUTO"), _region()
    inks = {id(a): MemberInk(stroke_mm=0.6, spines=[SPINE]),
            id(b): MemberInk(stroke_mm=0.6, spines=[SPINE])}
    _stub_ink(monkeypatch, inks)
    assert tag_bean_letters([a, b], object(), _cfg()) == 2


def test_members_with_no_cluster_are_ignored(monkeypatch):
    a = SimpleNamespace(meta={})
    seen = _stub_ink(monkeypatch, {})
    assert tag_bean_letters([a], object(), _cfg()) == 0 and seen == []


def test_each_cluster_is_decided_on_its_own(monkeypatch):
    thin, heavy = _region("t"), _region("h")
    inks = {id(thin): MemberInk(stroke_mm=0.6, spines=[SPINE]),
            id(heavy): MemberInk(stroke_mm=1.6, spines=[SPINE])}
    seen = _stub_ink(monkeypatch, inks)
    assert tag_bean_letters([thin, heavy], object(), _cfg()) == 1
    assert len(seen) == 2
    assert BEAN_LETTER_KEY in thin.meta and BEAN_LETTER_KEY not in heavy.meta


def test_lettering_words_groups_by_word_id(monkeypatch):
    a = _region("c", word_id="w1")
    b = _region("c", word_id="w2")
    inks = {id(a): MemberInk(stroke_mm=0.6, spines=[SPINE]),
            id(b): MemberInk(stroke_mm=0.6, spines=[SPINE])}
    seen = _stub_ink(monkeypatch, inks)
    assert tag_bean_letters([a, b], object(), _cfg(lettering_words=True)) == 2
    assert len(seen) == 2


# --- bean_letter ----------------------------------------------------------------

def _run(spines, entry=None, trim=3.0):
    return bean_letter(spines, "s", entry=entry, trim_at_mm=trim)


def test_with_no_entry_the_first_spine_goes_first_forward():
    far = [(10.0, 0.0), (10.0, 5.0)]
    runs, _ = _run([far, SPINE])
    assert runs[0].points[0] == (10.0, 0.0)


def test_the_nearest_spine_goes_next_not_the_listed_order():
    mid = [(0.0, 8.0), (0.0, 13.0)]
    far = [(0.0, 30.0), (0.0, 35.0)]
    runs, report = _run([far, mid, SPINE], entry=(0.0, 0.0))
    starts = [r.points[0] for r in runs]
    assert starts == [(0.0, 0.0), (0.0, 8.0), (0.0, 30.0)] and report["strokes"] == 3


def test_a_hop_under_the_tiny_stitch_floor_is_neither_jump_nor_trim():
    nxt = [(0.0, 5.0 + machine.TINY_STITCH_MM / 2), (0.0, 10.0)]
    runs, report = _run([SPINE, nxt], entry=(0.0, 0.0))
    assert report["jumps"] == 0 and not any(r.jump or r.trim for r in runs)


def test_a_hop_over_the_trim_threshold_trims_and_one_at_it_only_jumps():
    gap = 4.0
    nxt = [(0.0, 5.0 + gap), (0.0, 10.0)]
    runs, _ = _run([SPINE, nxt], entry=(0.0, 0.0), trim=gap)
    assert runs[1].jump and not runs[1].trim
    runs, _ = _run([SPINE, nxt], entry=(0.0, 0.0), trim=gap - 0.1)
    assert runs[1].jump and runs[1].trim


def test_the_first_run_never_jumps_even_far_from_the_entry():
    runs, report = _run([SPINE], entry=(50.0, 50.0))
    assert not runs[0].jump and not runs[0].trim and report["jumps"] == 0


def test_a_total_under_the_floor_sews_nothing():
    tiny = machine.RUN_MIN_LOOP_MM / 2.0 * 0.4
    a = [(0.0, 0.0), (tiny, 0.0)]
    runs, report = _run([a])
    assert runs == [] and report["empty"] and report["strokes"] == 0


def test_degenerate_spines_are_dropped():
    runs, report = _run([[(1.0, 1.0)], [], SPINE])
    assert report["strokes"] == 1 and runs


def test_inputs_are_not_mutated_and_tuples_are_accepted():
    spine = [[0.0, 0.0], [0.0, 5.0]]
    snapshot = [list(p) for p in spine]
    _run([spine], entry=(0.0, 5.0))          # forces the reversed path
    assert spine == snapshot
    runs, _ = _run([tuple(map(tuple, SPINE))])
    assert runs


def test_the_run_is_deterministic():
    spines = [SPINE, [(1.0, 5.0), (4.0, 5.0)], [(8.0, 0.0), (8.0, 4.0)]]
    a = _run(spines, entry=(0.0, 0.0))
    b = _run(spines, entry=(0.0, 0.0))
    assert [r.points for r in a[0]] == [r.points for r in b[0]] and a[1] == b[1]


def test_no_point_of_a_run_exceeds_the_split_limit():
    runs, _ = _run([[(0.0, 0.0), (40.0, 0.0)]])
    for r in runs:
        assert r.kind == stitches.RUN
        assert all(math.dist(a, b) <= machine.BEAN_STITCH_MM * 1.1 + 1e-9
                   for a, b in zip(r.points, r.points[1:]))
