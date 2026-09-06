"""`SAME_HOLE_HEAVY` reports how DEEP the stacking goes, and where.

`fraction` counts points struck 2+ times over all penetrations. That number
cannot tell **thousands of doubles** — which every professional file in the
36-file corpus contains, and which the check's own docstring defends — from
**one spot the needle hits twelve times**, which is a hole in the fabric. The
check's argument for its own threshold is made on depth ("ALL 36 files contain
3+ stacked points") and its payload could not answer on depth.

`max_strikes`, `points_3plus` and `worst_at_mm` close that. `worst_at_mm` is
also the "where" the message asks for — *"expect the odd thread break WHERE
the stitching doubles back"* — on the same 0.1 mm DST grid the rate is
computed on, and in the plan's own mm like `LINK_UNCOVERED`'s `at_mm`.

Severity does not move: this is `info`, worth 0 points, and a test below pins
that so the extra detail never becomes a deduction by accident.
"""

import pytest

from digitizer_core import preflight as pf
from digitizer_core import stitches as st
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .conftest import cfg


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _shallow(n: int = 40) -> StitchRun:
    """Every point struck exactly twice — the professional pattern, deep 0."""
    pts: list[tuple[float, float]] = []
    for i in range(n):
        a, b = (2.0 * i, 0.0), (2.0 * i, 4.0)
        pts.extend([a, b, a, b])
    return StitchRun(points=pts, kind=st.RUN)


def _with_a_pit(n: int = 40, strikes: int = 13, k: int = 5) -> StitchRun:
    """The same field, but at column `k` the needle bounces `strikes` times.

    Two constraints made this harder than it looks, and both are worth
    keeping:

      * **the pit cannot be appended somewhere else.** A spot off in the
        corner needs a hop to reach, and a 38 mm hop trips
        `STITCHES_TOO_LONG` — a `warn` — so the plan would stop scoring 100
        for a reason that has nothing to do with this check. Bouncing between
        two points of the field keeps every step at 4 mm.
      * **the pit cannot be CONSECUTIVE duplicates.** `iter_machine_commands`
        skips a point within `SAME_POINT_MM` of the last, so a run of
        identical points is one machine penetration, not twelve. It would
        still count twelve here (this check walks `run.points`, not the
        command stream) and the fixture would be measuring a hole the machine
        never makes.

    Both ends of the bounce end up deep, which is why `points_3plus` is 2.
    `strikes` is ODD on purpose: an even bounce leaves the two rails TIED, and
    which one gets reported then rests on `max`'s tie-break (count, then key)
    rather than on anything about the design. An odd count gives the starting
    rail one extra strike and a unique answer.
    """
    pts: list[tuple[float, float]] = []
    for i in range(n):
        a, b = (2.0 * i, 0.0), (2.0 * i, 4.0)
        if i == k:
            for j in range(strikes):
                pts.append(a if j % 2 == 0 else b)
        else:
            pts.extend([a, b, a, b])
    return StitchRun(points=pts, kind=st.RUN)


def _hit(report: dict) -> dict | None:
    for f in report["findings"]:
        if f["code"] == pf.SAME_HOLE_HEAVY:
            return f
    return None


def test_a_field_of_doubles_reports_depth_two_and_no_deep_spots():
    e = _hit(pf.run_preflight(None, _plan(_shallow()), cfg()))["extra"]
    assert e["max_strikes"] == 2
    assert e["points_3plus"] == 0


def test_one_deep_pit_is_visible_even_though_the_rate_barely_moves():
    """THE case the fraction cannot see. Both plans are ~50% repeat points;
    only one has a spot struck twelve times."""
    flat = _hit(pf.run_preflight(None, _plan(_shallow()), cfg()))["extra"]
    pit = _hit(pf.run_preflight(None, _plan(_with_a_pit()), cfg()))["extra"]

    assert abs(pit["fraction"] - flat["fraction"]) < 0.05, \
        "the rate is nearly unchanged — that is the point"
    assert flat["max_strikes"] == 2 and pit["max_strikes"] == 7
    assert flat["points_3plus"] == 0 and pit["points_3plus"] == 2


def test_the_deepest_spot_reports_its_own_place():
    """Column 5 of the field is x = 10 mm, and the bounce starts on the y = 0
    rail, so that rail takes the extra strike and is the one named."""
    hit = _hit(pf.run_preflight(None, _plan(_with_a_pit(k=5)), cfg()))
    assert hit["extra"]["worst_at_mm"] == [10.0, 0.0]
    assert "near (10, 0) mm" in hit["message"]
    assert "takes 7 strikes" in hit["message"]


def test_the_place_is_on_the_same_grid_the_rate_is_computed_on():
    """The rate quantises to `_SAME_HOLE_QUANTUM_MM` (the 0.1 mm DST grid), so
    the reported point has to come back OFF that grid — not a raw float naming
    a spot the counter never counted. Off-grid coordinates in, grid out."""
    q = pf._SAME_HOLE_QUANTUM_MM
    run = _with_a_pit(k=5)
    run.points = [(x + 0.043, y - 0.027) for x, y in run.points]
    hit = _hit(pf.run_preflight(None, _plan(run), cfg()))
    x, y = hit["extra"]["worst_at_mm"]
    assert x == pytest.approx(round(10.043 / q) * q, abs=1e-6)
    assert y == pytest.approx(round(-0.027 / q) * q, abs=1e-6)


def test_the_deep_count_only_counts_three_or_more():
    """`points_3plus` is the figure the docstring's corpus claim is about, so
    it must not quietly become "2 or more" and duplicate `repeat_points`."""
    e = _hit(pf.run_preflight(None, _plan(_with_a_pit()), cfg()))["extra"]
    assert e["points_3plus"] == 2
    assert e["repeat_points"] > e["points_3plus"]


def test_it_still_costs_nothing():
    """Law 17's trade phrasing is stricter than professional files, so this
    stays INFO. Extra payload must never turn it into a deduction."""
    report = pf.run_preflight(None, _plan(_with_a_pit()), cfg())
    assert _hit(report)["severity"] == "info"
    assert report["score"] == 100


# --- Why depth, and not just a bigger rate -----------------------------------

def _diluted(base: StitchRun, n: int) -> StitchRun:
    """`base` plus `n` landings on FRESH fabric — what a denser fill adds.

    0.5 mm apart so none coincides on the 0.1 mm grid and none is a long
    stitch; started at x = 200 so they cannot collide with the field.
    """
    out = StitchRun(points=list(base.points), kind=st.RUN)
    out.points.extend((200.0 + 0.5 * i, 0.0) for i in range(n))
    return out


def test_depth_survives_a_density_change_and_the_rate_does_not():
    """The reason `max_strikes` earns its place, pinned without the pipeline.

    The rate is (2+-struck points) / (penetrations). Landings on FRESH fabric —
    exactly what a denser fill adds — grow the denominator and touch nothing
    else, so the rate falls while the fabric is struck in precisely the same
    places, precisely as often.

    Measured on the real thing 2026-09-06 across `FILL_ROW_MM` 0.40 -> 0.15:
    penetrations x1.17-2.30, repeat points x0.98-1.15 (28 against 28 on
    `logo_whitebg`), rate x0.43-0.83, and `max_strikes` IDENTICAL on all four
    fixtures. This is that, synthetically and instantly.
    """
    base = _with_a_pit()
    thin = _hit(pf.run_preflight(None, _plan(base), cfg()))["extra"]
    fat = _hit(pf.run_preflight(None, _plan(_diluted(base, 100)), cfg()))["extra"]

    assert fat["penetrations"] > thin["penetrations"]
    assert fat["fraction"] < thin["fraction"], "the rate is diluted"
    # ...and every physical fact about the stacking is untouched.
    assert fat["repeat_points"] == thin["repeat_points"]
    assert fat["points_3plus"] == thin["points_3plus"]
    assert fat["max_strikes"] == thin["max_strikes"]
    assert fat["worst_at_mm"] == thin["worst_at_mm"]


def test_enough_dilution_silences_the_finding_outright():
    """The same effect taken far enough, which is what happened to the corpus.

    `SAME_HOLE_RATE_MAX` was set as "far above" a benchmark of 9.8% recorded
    before the row moved; the corpus now runs 0.001-0.103 and NOTHING fires
    (0 of 26, 2026-09-06). Here the fabric is struck in exactly the same
    places and the finding disappears anyway — so its silence is not evidence
    that anything improved."""
    base = _with_a_pit()
    loud = pf.run_preflight(None, _plan(base), cfg())
    quiet = pf.run_preflight(None, _plan(_diluted(base, 400)), cfg())

    assert _hit(loud) is not None
    assert _hit(quiet) is None
    # The METRIC still reports, which is how a caller sees the dilution.
    assert quiet["metrics"]["same_hole_fraction"] < \
        loud["metrics"]["same_hole_fraction"]
