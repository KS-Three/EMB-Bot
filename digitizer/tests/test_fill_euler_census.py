"""`tools/fill_euler_census.py` (2026-11-07, lagging area 3): one walk over a
fill's sections, found with networkx (`min_weight_matching`, `eulerian_path`)
and priced by the engine's own rule.

Fixture: a body with two lobes hanging from it (`tests/test_fill_one_pass_sections.FORK`
in miniature), laid as three hand-made sections so the test owns the ends.
Nearest-first from the needle at the body's corner sews body, near lobe, then
hops across bare cloth to the far lobe -- the cut the census is about. The
Euler walk sews lobe, body, lobe.
"""
from __future__ import annotations

import networkx as nx
import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import stage6_fill as s6
from tests.test_fill_seam_order import ROW, _rows_of
from tools import fill_euler_census as fec

# body 10 mm tall (25 rows: the snake ends on the far side), lobes 44 mm
FORK = unary_union([box(0, 0, 40, 10), box(0, 10, 14, 54), box(26, 10, 40, 54)])
BODY, LEFT, RIGHT = (_rows_of(0.2, 10.0, 0.0, 40.0), _rows_of(10.2, 54.0, 0.0, 14.0),
                     _rows_of(10.2, 54.0, 26.0, 40.0))


def _capture(sections, entry=(0.0, 0.2)):
    return fec.Capture(shape_id="F", poly=FORK, angle=0.0, row_mm=ROW, trim_at_mm=3.0,
                       cut_bridges=True, two_pass=False, entry=entry, sections=sections, stage6_cuts=0)


def test_adjacency_reads_the_seams_not_the_gap():
    adj = fec.adjacency([BODY, LEFT, RIGHT], ROW)
    assert adj == {(0, 1), (0, 2)}, "each lobe meets the body; the lobes do not meet"


def test_the_walk_covers_every_section_once_and_hops_n_minus_1_times():
    cap = _capture([BODY, LEFT, RIGHT])
    walk = fec.euler_walk(cap.sections, cap.ring_slack()[1], cap.entry, fec.adjacency(cap.sections, ROW))
    assert len(walk["order"]) == 3 and len(walk["hops"]) == 2
    assert sorted(len(p) for p in walk["order"]) == sorted(len(p) for p in cap.sections)
    assert {tuple(sorted(map(tuple, p))) for p in walk["order"]} == \
        {tuple(sorted(map(tuple, p))) for p in cap.sections}, "each section once, either way round"
    # the body is the middle of the walk: lobe, body, lobe
    assert len(walk["order"][1]) == len(BODY)


def test_the_walk_sews_the_fork_in_one_pass_where_nearest_first_cuts():
    cap = _capture([BODY, LEFT, RIGHT])
    with s6.cut_exposed_scope(True):
        sewn = fec.walk_cost([BODY, LEFT, RIGHT], cap, hidden=False)
        walk = fec.euler_walk(cap.sections, cap.ring_slack()[1], cap.entry,
                              fec.adjacency(cap.sections, ROW))
        euler = fec.walk_cost(walk["order"], cap, hidden=True)
    assert sewn["cuts"] >= 1 and sewn["long_cuts"] >= 1, "the hop between the lobes' bottoms is a cut past 40 mm"
    assert euler["cuts"] == 0 and euler["long_cuts"] == 0 and euler["exposed_mm"] == 0.0
    assert len(euler["hops"]) == 3 and all("route_mm" in h for h in euler["hops"]), \
        "the hop in and both hops between sections are sewn, none lifted"


def test_the_price_is_the_engines_own():
    """`walk_cost`'s cuts and travel stitches are `_order_cost`'s, on the same order."""
    cap = _capture([BODY, LEFT, RIGHT])
    ring, slack = cap.ring_slack()
    with s6.cut_exposed_scope(True):
        got = fec.walk_cost([BODY, LEFT, RIGHT], cap, hidden=False)
        cuts, travel, exposed = s6._order_cost([BODY, LEFT, RIGHT], FORK, ring, slack, cap.entry,
                                               3.0, ROW, True)
    assert got["cuts"] == cuts and got["travel_stitches"] == travel
    assert got["exposed_mm"] == pytest.approx(exposed * s6.machine.TRAVEL_STITCH_MM, abs=0.1)


def test_odd_ends_are_paired_by_matching_not_eulerize(monkeypatch):
    calls = []
    real = nx.min_weight_matching
    monkeypatch.setattr(nx, "min_weight_matching", lambda g, **kw: calls.append(len(g)) or real(g, **kw))
    monkeypatch.setattr(nx, "eulerize", lambda *a, **k: pytest.fail("eulerize duplicates sections"))
    cap = _capture([BODY, LEFT, RIGHT])
    fec.euler_walk(cap.sections, cap.ring_slack()[1], cap.entry, fec.adjacency(cap.sections, ROW))
    assert calls == [6], "one matching over the six section ends"


def test_a_single_section_is_its_own_walk():
    cap = _capture([BODY])
    walk = fec.euler_walk(cap.sections, cap.ring_slack()[1], cap.entry, set())
    assert walk["order"] == [BODY] and walk["hops"] == []


def test_the_table_counts_cuts_that_become_one_clean_walk():
    report = {"j": {"slug": "j", "arms": {}, "shapes": [
        {"shape": "A", "sections": 3, "dst_cuts": 2, "sewn": {"cuts": 2, "long_cuts": 1, "exposed_mm": 0.0},
         "euler": {"cuts": 0, "long_cuts": 0, "exposed_mm": 0.0}, "one_walk": True, "added_travel_mm": 1.0,
         "one_pass": {"dst_cuts": 2}, "seam_aware": {"dst_cuts": 1}},
        {"shape": "B", "sections": 4, "dst_cuts": 1, "sewn": {"cuts": 1, "long_cuts": 0, "exposed_mm": 0.0},
         "euler": {"cuts": 0, "long_cuts": 0, "exposed_mm": 3.0}, "one_walk": True, "added_travel_mm": 9.0,
         "one_pass": {"dst_cuts": 1}, "seam_aware": {"dst_cuts": 1}},
        {"shape": "C", "dst_cuts": 1, "skipped": "two-pass fill"}]}}
    md = fec.table(report)
    assert "**2** of 4 cuts one walk at 0 mm (3 one walk at any exposure)" in md
    assert "| j | A | 3 | 2 / 2 / 1 | 2 (1), 0.0 | 0 (0), +1.0, 0.0 | YES |" in md
    assert "walk, shows" in md and "skipped: two-pass fill" in md
