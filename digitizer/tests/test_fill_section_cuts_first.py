"""`cfg.extra["fill_section_cuts_first"]` (built OFF 2026-10-29, defects 4/6):
`fill_section_travel` on, and its section planner's orders priced with the
travel under rows still to come free.

Re-measured on main 44ecf1cb (`docs/trim-defects-4-6-2026-10-29.md`): the pro
cuts between two sections of one fill 0 times over 17 paired jobs, we cut 32,
and on Becker's and MFab's fields the planner already finds an order with
fewer cuts and no more exposed travel -- `_score` refused it for the hidden
travel stitches alone. The gate is `fill_section_travel`'s, unchanged: a plan
that cuts more or lays more thread on finished fill is never kept.

Same shapely fixture as `tests/test_fill_section_travel.py`.
"""
from __future__ import annotations

import sys

import pytest

from digitizer_core import PipelineConfig, fill_section_travel, stage6_fill
from tests.test_fill_section_travel import OFF_MD5, _md5, _sew_now


def _sew(on: bool, cuts_first: bool, underlay: str = "none"):
    tok = fill_section_travel._CUTS_FIRST.set(cuts_first)
    try:
        return _sew_now(on, underlay)
    finally:
        fill_section_travel._CUTS_FIRST.reset(tok)


def test_the_switch_is_off_by_default():
    assert not PipelineConfig().extra.get(fill_section_travel.KEY_CUTS_FIRST)
    assert not fill_section_travel.cuts_first()


def test_it_turns_fill_section_travel_on_and_restores():
    cfg = PipelineConfig(extra={fill_section_travel.KEY_CUTS_FIRST: True})
    with fill_section_travel.enabled(cfg):
        assert fill_section_travel.active() and fill_section_travel.cuts_first()
        with fill_section_travel.enabled(PipelineConfig(extra={fill_section_travel.KEY: True})):
            assert fill_section_travel.active() and not fill_section_travel.cuts_first()
        assert fill_section_travel.cuts_first()
    assert not fill_section_travel.active() and not fill_section_travel.cuts_first()


def test_plan_stitches_reads_it_from_cfg_extra(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: seen.append(
        (fill_section_travel.active(), fill_section_travel.cuts_first())))
    pipeline.plan_stitches(None, PipelineConfig())
    pipeline.plan_stitches(None, PipelineConfig(extra={fill_section_travel.KEY_CUTS_FIRST: True}))
    assert seen == [(False, False), (True, True)]


def test_the_hidden_free_price():
    """Cuts at the trim rate; exposed stitches pay as travel AND as exposure,
    exactly as in `_score`; hidden travel pays nothing."""
    assert stage6_fill._score_hidden_free((2, 100.0, 5.0)) == stage6_fill._score((2, 5.0, 5.0))
    assert stage6_fill._score_hidden_free((0, 500.0, 0.0)) == 0.0


@pytest.mark.parametrize("underlay", ["none", "edge_lattice"])
def test_off_is_byte_identical_to_base(underlay):
    """The flags-off fixture is the pin `test_fill_section_travel.py` captured on
    c531c7b8; the switch never reaches a sewing without `fill_section_travel`."""
    got = _md5(_sew(False, False, underlay))
    if sys.platform == "win32":
        assert got == OFF_MD5[underlay]


def test_off_leaves_fill_section_travel_as_it_was():
    """`fill_section_travel` alone prices with `_score`, as before the switch."""
    assert _md5(_sew(True, False)) == _md5(_sew_now(True, "none"))


class _Planned(list):
    pass


def _priced(monkeypatch, planned_cost):
    """The planner proposes the incoming order reversed (last path pinned); the
    scorer prices every other order honestly and the proposal at
    `planned_cost(before)`, `before` being the incoming order `_plan_sections`
    priced just ahead of it."""
    real = stage6_fill._order_cost
    seen = {}

    def scorer(order, *a, **k):
        if isinstance(order, _Planned):
            seen["before"] = seen["last"]
            return planned_cost(seen["last"])
        seen["last"] = real(order, *a, **k)
        return seen["last"]
    monkeypatch.setattr(fill_section_travel, "plan",
                        lambda paths, *_a, **_k: _Planned([*reversed(paths[:-1]), paths[-1]]))
    monkeypatch.setattr(stage6_fill, "_order_cost", scorer)
    return seen


def test_a_fewer_cut_order_refused_for_hidden_travel_is_taken(monkeypatch):
    """One cut fewer, same exposure, 500 more hidden travel stitches: `_score`
    refuses it, the switch keeps it."""
    seen = _priced(monkeypatch, lambda b: (b[0] - 1, b[1] + 500.0, b[2]))
    incoming = _md5(_sew(True, False))
    assert seen["before"][0] >= 1, "the fixture must cut in its fill"
    assert _md5(_sew(True, True)) != incoming


@pytest.mark.parametrize("worse", ["more_cuts", "more_exposure"])
def test_the_gate_still_holds(monkeypatch, worse):
    """A plan that cuts more, or lays more thread on finished fill, is refused
    however little it travels."""
    bump = {"more_cuts": lambda b: (b[0] + 1, 0.0, 0.0),
            "more_exposure": lambda b: (max(0, b[0] - 1), 0.0, b[2] + 1.0)}[worse]
    _priced(monkeypatch, bump)
    assert _md5(_sew(True, True)) == _md5(_sew(True, False))
