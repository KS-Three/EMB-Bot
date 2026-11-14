"""`cfg.extra["lettering_columns_apex_guard"]` (2026-11-14, built OFF; read
only while `cfg.lettering_columns_apex_cut` is on): the merged tips behind
apex_cut's losses on the 43-design corpus table
(`docs/apex-cut-corpus-2026-11-14.md`) are refused, so the letter cuts as it
does with apex_cut OFF (`outline_cut._apex_guard_refuses`, comment at
`_APEX_GUARD`):

- a stroke under one satin cross (`machine.SATIN_MIN_CROSS_MM`): the hairline
  rings outline_lineart_logo's tagger took for letters;
- a cross found only by sliding below the crotch until it reached
  `APEX_GUARD_SHARE` of the walk's limit (k_line, Drone's N, mfab_lc's W and
  N, duotone's "2", and_pizza's Z joints).

A tip cut through its crotch (Becker MARINE's M) is kept, as apex_cut sews it.
"""
from __future__ import annotations

from dataclasses import replace

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from tests.test_column_apex_cut import LANE, _letters, _v


def _cut(poly, apex: bool, guard: bool):
    with oc.apex_cut_scope(apex), oc.apex_guard_scope(guard):
        return oc.letter_columns(poly, 0.4, **LANE)


def _same(a, b) -> bool:
    return a.cuts == b.cuts and [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._APEX_GUARD.get() is False
    with oc.apex_guard_scope(True):
        assert oc._APEX_GUARD.get() is True
    assert oc._APEX_GUARD.get() is False
    with oc.apex_guard_scope(False):
        assert oc._APEX_GUARD.get() is False


def test_plan_stitches_sets_it_from_the_extra_key_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._APEX_GUARD.get())
    on = replace(PipelineConfig(), extra={"lettering_columns_apex_guard": True})
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._APEX_GUARD.get() is False


def test_without_apex_cut_the_guard_changes_nothing():
    for poly in (_v(35.0, 1.2, 6.0), _v(20.0, 0.3, 3.0), _letters()["marine76_M"][0]):
        assert _same(_cut(poly, False, True), _cut(poly, False, False))


def test_a_tip_cut_through_its_crotch_is_kept():
    # MARINE's M at 76.5 mm (Becker hat small, a gain) and a narrow V
    for poly in (_letters()["marine76_M"][0], _v(20.0, 1.2, 8.0)):
        on, guarded = _cut(poly, True, False), _cut(poly, True, True)
        assert "apex" in [c[2] for c in on.cuts]
        assert _same(guarded, on)


def test_a_cross_found_by_sliding_to_the_limit_cuts_as_off():
    poly = _v(35.0, 1.2, 6.0)
    on, off, guarded = _cut(poly, True, False), _cut(poly, False, False), _cut(poly, True, True)
    stub = [c for c in on.cuts if c[2] == "apex_stub"]
    assert stub, "the fixture's cut slides below its crotch"
    lim = min(oc.APEX_CROSS_W * on.W, oc.APEX_CROSS_MM)
    cross = sum(c[3] for c in on.cuts if c[2] == "apex")
    assert cross >= oc.APEX_GUARD_SHARE * lim
    assert _same(guarded, off)
    assert "guard_slid_to_limit" in oc._APEX_WHY


def test_a_hairline_stroke_cuts_as_off():
    poly = _v(20.0, 0.4, 3.0)
    on, off, guarded = _cut(poly, True, False), _cut(poly, False, False), _cut(poly, True, True)
    assert on.W < 0.5 and "apex" in [c[2] for c in on.cuts]
    assert _same(guarded, off)
    assert "guard_hairline" in oc._APEX_WHY


def test_a_refused_crotch_tries_no_other_tip():
    """Refused, the crotch keeps the junction rules' own cut: no apex record
    of any kind is left from it."""
    guarded = _cut(_v(35.0, 1.2, 6.0), True, True)
    assert not [c for c in guarded.cuts if c[2].startswith("apex")]
