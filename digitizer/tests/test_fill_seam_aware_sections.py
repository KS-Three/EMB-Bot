"""`cfg.fill_seam_aware_sections` (built OFF 2026-11-06, defect 6): seam order's
sections planned with lookahead, for the short hops.

On the 17 pairs, 31 fill-section cuts survive `fill_one_pass_sections`, and on
Drone and ProSeal hat every one is a hop of 3-15 mm that stage 7 finds no later
thread to bury. That switch never re-plans them: its gate wants a hop past
`machine.LINK_MAX_GAP_MM`. This one re-plans any field whose seam order cuts,
within the seams: `fill_section_travel.plan`'s step rule (reached hidden, one
step of lookahead, the articulation rule on the seam graph, nearest), with the
plain reach-first order priced beside it, and keeps the result only if it lays
no worse, cuts fewer, has no more long hops and lays no more on finished fill
(`stage6_fill._seam_aware_sections`).

Shapely fixtures, as `tests/test_fill_one_pass_sections.py`: a body with lobes
SHORT enough that the hop between them is under the bury limit.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, fill_section_travel, machine, stage6_fill, stitches
from digitizer_core.stage6_fill import (_SEAM_AWARE, _order_for_seams, _seam_aware_chooser,
                                        cut_exposed_scope, one_pass_scope, seam_aware_scope,
                                        seam_order_scope, seam_priced_scope, stitch_shape)
from tests.test_fill_one_pass_sections import FORK, _cuts, _md5, _seam_faults
from tests.test_fill_seam_order import _rows_of

ROW = 0.4
# Two lobes 14 mm long under a body: the hop between them is far under
# `LINK_MAX_GAP_MM`, so `fill_one_pass_sections` leaves it to the cut.
SHORT_FORK = unary_union([box(0, 0, 40, 10), box(0, 10, 14, 24), box(26, 10, 40, 24)])
# Three lobes: nearest-first walls two of them in.
THREE = unary_union([box(0, 0, 50, 8), box(0, 8, 10, 22), box(20, 8, 30, 22), box(40, 8, 50, 22)])


def _sew(on: bool, shape=SHORT_FORK, one_pass: bool = False):
    with seam_order_scope(True), seam_priced_scope(True), cut_exposed_scope(True), \
            one_pass_scope(one_pass), seam_aware_scope(on):
        runs, _report = stitch_shape(shape, "F", angle_deg=0.0, row_mm=ROW, stitch_mm=3.0,
                                     underlay_style="none", trim_at_mm=3.0, start_near=(0.0, 0.0),
                                     under_cover=True, cut_bridges=True)
    return runs


def test_the_switch_is_off_by_default():
    assert PipelineConfig().fill_seam_aware_sections is False
    assert not _SEAM_AWARE.get()


def test_plan_stitches_reads_the_flag(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: seen.append(_SEAM_AWARE.get()))
    pipeline.plan_stitches(None, PipelineConfig())
    pipeline.plan_stitches(None, PipelineConfig(fill_seam_aware_sections=True))
    assert seen == [False, True]
    assert not _SEAM_AWARE.get()


def test_shape_memo_keys_on_it():
    from digitizer_core import shape_memo
    assert ("stage6_fill", "_SEAM_AWARE") in shape_memo._AMBIENT


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("fill_seam_aware_sections reached with the switch off")
    monkeypatch.setattr(stage6_fill, "_seam_aware_sections", boom)
    monkeypatch.setattr(fill_section_travel, "bridge", boom)
    _sew(False)
    _sew(False, THREE)


def test_one_pass_leaves_the_short_fork_to_its_cut():
    """The case the switch is for: `fill_one_pass_sections` alone does nothing here."""
    assert _cuts(_sew(False)) >= 1
    assert _md5(_sew(False, one_pass=True)) == _md5(_sew(False))


@pytest.mark.parametrize("shape", [SHORT_FORK, THREE], ids=["short_fork", "three_lobes"])
def test_on_sews_the_field_in_one_pass_and_lays_no_worse(shape):
    off, on = _sew(False, shape), _sew(True, shape)
    assert _cuts(off) >= 1
    assert _cuts(on) < _cuts(off)
    assert _cuts(on) == 0
    assert sum(_seam_faults(on)) <= sum(_seam_faults(off))
    # what replaced the cut is travel inside the shape, sewn needle-down
    assert any(r.kind == stitches.TRAVEL for r in on)


def test_a_long_fork_is_still_one_pass_s_and_not_made_worse():
    """Past the bury limit both switches agree, and together they cut no more."""
    assert _cuts(_sew(True, FORK)) <= _cuts(_sew(False, FORK, one_pass=True))
    assert _cuts(_sew(True, FORK, one_pass=True)) <= _cuts(_sew(False, FORK))


def test_nothing_to_buy_is_left_alone():
    """A plain plate cuts nowhere: the re-plan is never priced and the order stands."""
    plate = box(0, 0, 30, 20)
    assert _cuts(_sew(False, plate)) == 0
    assert _md5(_sew(True, plate)) == _md5(_sew(False, plate))


# ---------------------------------------------------------------- the chooser

TOP, LEFT, MID, RIGHT = (_rows_of(0.0, 4.0, 0.0, 50.0), _rows_of(4.0, 8.0, 0.0, 10.0),
                         _rows_of(4.0, 8.0, 20.0, 30.0), _rows_of(4.0, 8.0, 40.0, 50.0))


def _choose_with(reached):
    """The chooser over a stub reach: `reached(cur, head)` -> bool."""
    return _seam_aware_chooser(lambda cur, head, sewn, todo: reached(cur, head), ROW)


def test_the_chooser_keeps_the_seams():
    """Whatever it prefers, a section never goes before its upstream neighbour."""
    order = _order_for_seams([TOP, LEFT, MID, RIGHT], 0.0, (0.0, 0.0), ROW, None,
                             choose=_choose_with(lambda cur, head: head[0] > 15.0))
    assert order[0][0][1] == 0.0                 # the body, which every lobe shares a seam with
    assert len(order) == 4


def test_the_chooser_prefers_a_hidden_reach_over_the_nearest():
    """From the body's end, LEFT is nearest; only RIGHT is reached hidden."""
    order = _order_for_seams([TOP, LEFT, MID, RIGHT], 0.0, (0.0, 0.0), ROW, None,
                             choose=_choose_with(lambda cur, head: head[0] >= 40.0))
    nearest = _order_for_seams([TOP, LEFT, MID, RIGHT], 0.0, (0.0, 0.0), ROW, None)
    assert order != nearest
    assert min(p[0] for p in order[1]) >= 40.0


def test_the_lookahead_avoids_a_dead_end():
    """Two free sections, both reached hidden; from one's tail nothing else is
    reached hidden, from the other's it is: the other goes first."""
    def reached(cur, head):
        if cur[0] <= 10.5 and cur[1] > 4.0:      # leaving LEFT's tail: walled in
            return False
        return True
    choose = _choose_with(reached)
    order = _order_for_seams([TOP, LEFT, MID, RIGHT], 0.0, (0.0, 0.0), ROW, None, choose=choose)
    assert min(p[0] for p in order[-1]) == 0.0, "LEFT, the dead end, goes last"


def test_gate_constants_are_read_not_new():
    assert machine.LINK_MAX_GAP_MM > 0
    assert stage6_fill._ROUTABLE_PROBE_LIMIT > 0 and fill_section_travel._LOOKAHEAD > 0
