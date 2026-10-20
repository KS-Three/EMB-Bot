"""The unsewn-ground memo must show up in the clock and nowhere else.

`travel_path`'s covered routing builds the ground not yet sewn
(`cover.difference(sewn)`), hair-widens it and insets it into rings, and a
cold owl_kent digitize asked for the same ground from byte-identical inputs
in 223 of 749 ring builds (profiled 2026-10-13,
`docs/photo-cold-profile-2026-10-13.md`). `_unsewn_ground` memoizes those on
the exact bytes of (`cover`, `sewn`). Its safety is that all three values are
pure functions of those two geometries -- so the tests compare against the
unmemoized computation, not against a stored hash that a later, legitimate
output change would have to re-bless.
"""
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, machine
from digitizer_core import stage6_fill as F
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from tests.conftest import own_thread_only

OWL = Path(__file__).resolve().parent.parent / "testdata" / "photo" / "owl_kent.jpg"


@pytest.fixture(autouse=True)
def _clean_memo():
    F.clear_fill_reorder_memo()
    yield
    F.clear_fill_reorder_memo()


def _unmemoized(cover, sewn):
    """What `travel_path` computed inline before the memo existed."""
    unsewn = cover.difference(sewn)
    inset = min(machine.TRAVEL_INSET_MM, machine.FILL_ROW_MM / 2.0)
    return (unsewn, lambda: unsewn.buffer(0.01),
            lambda: tuple(F._inset_ring(unsewn, inset)))


def test_a_hit_is_the_geometry_a_miss_builds():
    cover = box(0.0, 0.0, 20.0, 10.0)
    sewn = box(0.0, 0.0, 8.0, 10.0)
    want_u, want_s, want_r = _unmemoized(cover, sewn)
    for _ in range(2):                       # miss, then hit
        u, s, r = F._unsewn_ground(cover, sewn)
        assert u.wkb == want_u.wkb
        assert s().wkb == want_s().wkb
        assert [g.wkb for g in r()] == [g.wkb for g in want_r()]
    assert len(F._UNSEWN_MEMO) == 1


def test_different_sewn_ground_does_not_collide():
    """The key must carry `sewn`, not just `cover`: one more column sewn is a
    different answer, and handing back the stale one would route travel over
    fill that is already down."""
    cover = box(0.0, 0.0, 20.0, 10.0)
    u1, _, _ = F._unsewn_ground(cover, box(0.0, 0.0, 8.0, 10.0))
    u2, _, _ = F._unsewn_ground(cover, box(0.0, 0.0, 12.0, 10.0))
    assert u1.area != pytest.approx(u2.area)
    assert len(F._UNSEWN_MEMO) == 2


def test_the_memo_is_bounded(monkeypatch):
    monkeypatch.setattr(F, "_UNSEWN_MAX", 3)
    cover = Polygon([(0, 0), (40, 0), (40, 10), (0, 10)])
    for k in range(6):
        F._unsewn_ground(cover, box(0.0, 0.0, 1.0 + k, 10.0))
    assert len(F._UNSEWN_MEMO) == 3


def test_owl_kent_cold_digitize_is_byte_identical_with_and_without_the_memo(monkeypatch):
    """The fixture the memo was profiled on, end to end: every stitch, not a
    count -- a count matches while every coordinate moves."""
    cfg = PipelineConfig(target_width_mm=80.0, max_colors=6)
    gen = build_generation(OWL, cfg)

    def plan():
        F.clear_fill_reorder_memo()
        return plan_to_design(plan_stitches(finish_generation(gen.fork(), cfg), cfg),
                              name="owl")["stitches"]

    real = F._unsewn_ground
    keys: list[bytes] = []

    def counting(cover, sewn):
        keys.append(cover.wkb + sewn.wkb)
        return real(cover, sewn)

    monkeypatch.setattr(F, "_unsewn_ground", own_thread_only(counting, real))
    memoized = plan()
    assert len(keys) > len(set(keys)), "no repeated ground; the memo was never hit"
    assert not F._UNSEWN_MEMO, "stitch_shape must let the memo's geometry go"
    monkeypatch.setattr(F, "_unsewn_ground", _unmemoized)
    assert plan() == memoized
