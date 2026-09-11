"""The per-bridge exposure census, pinned against the total it must explain.

Quality review 2026-09-08 item 12. `tools/fill_bridges.py` exists to answer
"why was this bridge laid over finished fill", and its whole value rests on
reading the same plan the same way `tools/fill_exposure.py` does — a census
that disagrees with the total is a census explaining something else.

It found the answer by DISAGREEING with the review, which is why these
assertions are about the instrument's own honesty rather than about today's
numbers: the review's three remedies reach 2%, a no-op, and 8 bridges, and
88% of the exposed millimetres have no unsewn corridor at all. If a later
change moves those figures that is fine and the instrument will say so; what
must not drift is the census agreeing with the total, every row carrying the
facts a cause needs, and every row getting exactly one cause.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parent.parent / "tools"
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from tests.conftest import TESTDATA                          # noqa: E402

import fill_bridges                                          # noqa: E402
import fill_exposure                                         # noqa: E402

ART = TESTDATA / "becker_marine_logo.png"
CAUSES = {"buried", "budget", "probes", "both", "router", "no-corridor"}


@pytest.fixture(scope="module")
def run():
    cfg = PipelineConfig(target_width_mm=80.0)
    result, plan = digitize(ART, cfg)
    return result, plan, cfg


def test_the_census_explains_exactly_the_total_it_is_a_census_of(run):
    """Same plan, same tolerance, same footprint rule — so the same answer.

    `fill_exposure` sums; this one itemises. They read `plan.iter_runs()`
    with the same half-row-simplified full-row buffer and the same
    `_EXPOSED_TOLERANCE_MM`, and if they ever stop agreeing the itemised
    version is explaining bridges the total does not contain.
    """
    result, plan, cfg = run
    total = fill_exposure.exposure(plan)
    rows = fill_bridges.bridges(result, plan, cfg)
    assert len(rows) == total["exposed_runs"]
    assert sum(r["exposed_mm"] for r in rows) == pytest.approx(total["exposed_mm"])
    assert total["exposed_runs"] > 0, "a vacuous fixture proves nothing here"


def test_every_row_carries_what_a_cause_needs(run):
    result, plan, cfg = run
    for r in fill_bridges.bridges(result, plan, cfg):
        assert r["exposed_mm"] > 0
        assert r["len_mm"] >= r["exposed_mm"] - 1e-6
        assert r["gap_mm"] >= 0
        assert r["covered_mm"] >= 0
        assert r["unsewn_mm2"] >= 0
        assert isinstance(r["corridor"], bool)
        assert isinstance(r["jumpable"], bool)


def test_every_row_gets_exactly_one_named_cause(run):
    """`_cause` is a chain of ifs; an unnamed outcome would read as a bug in
    whatever consumes it, silently."""
    result, plan, cfg = run
    rows = fill_bridges.bridges(result, plan, cfg)
    assert rows, "a vacuous census passes every assertion below"
    for r in rows:
        assert fill_bridges._cause(r) in CAUSES


def test_a_clean_route_is_measured_WITH_its_start_point(run):
    """The trap that produced a fix that does not exist (2026-09-11).

    `travel_path` returns its route with the start EXCLUDED (`_densify` is
    a-exclusive), and that first step is exactly the part lying inside the
    column just finished. Measuring exposure without it made every short
    bridge read clean, which reported a detour-budget fix for 26 bridges —
    and the engine change built on that reading was a perfect no-op on all
    nine fixtures. The tell was a detour ratio of 0.5x, impossible for a
    route between the same two points.
    """
    result, plan, cfg = run
    for r in fill_bridges.bridges(result, plan, cfg):
        if r.get("clean_mm"):
            assert r["clean_mm"] >= r["gap_mm"] - 1e-6, (
                "a route from a to b cannot be shorter than the straight line "
                "between them — the start point is being dropped again")
