"""`TRIM_HEAVY` splits its cuts by whether merging shapes could remove them.

The message said *"consider merging or removing the smallest shapes"* since it
was written. On `becker_marine_logo` — the design the finding was investigated
on — that is the wrong end of the design: **19 of 28 PEN-UPS stay inside ONE
shape**, `Sead76620`, a 638.8 mm² 27-stroke region. `satin_shape` may travel
over UNSEWN strokes only, and the 2026-09-06 instrumented run showed the walk
succeeding up to 40% sewn and never again after, so a big multi-stroke shape
spends nearly all its life unable to reach anywhere. Five other remedies were
measured and refuted there.

(That 19/28 counts pen-ups — trims AND floats. What this file pins is the
TRIM split, which is the number the finding is scored on, and it is not the
same quantity.)

So the useful split is IN-SHAPE against BETWEEN-SHAPE, and the plan already
knows it: a trimmed run whose `shape_id` matches the previous run's is the
needle lifting inside one shape. Merging shapes cannot touch those.
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


def _row(r: int, shape_id: str, trim: bool, n: int = 10) -> StitchRun:
    return StitchRun(points=[(2.0 * i, 3.0 * r) for i in range(n)],
                     kind=st.FILL, trim=trim, jump=True, shape_id=shape_id)


def _hit(report: dict) -> dict | None:
    for f in report["findings"]:
        if f["code"] == pf.TRIM_HEAVY:
            return f
    return None


ONE_SHAPE = _plan(*[_row(r, "Sbig", trim=True) for r in range(10)])
MANY_SHAPES = _plan(*[_row(r, f"S{r}", trim=True) for r in range(10)])


def test_every_cut_lands_in_exactly_one_bucket():
    """The invariant the whole payload rests on. Attribution walks the runs in
    the same order and with the same empty-run skip as
    `iter_machine_commands`, so a trim can never be counted twice or lost."""
    for plan in (ONE_SHAPE, MANY_SHAPES):
        extra = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
        assert extra["in_shape"] + extra["between_shapes"] == extra["trims"]


def test_cuts_inside_one_shape_say_merging_will_not_help():
    extra = _hit(pf.run_preflight(None, ONE_SHAPE, cfg()))["extra"]
    assert extra["in_shape"] == extra["trims"] == 9
    assert extra["between_shapes"] == 0
    assert extra["worst_shape_id"] == "Sbig"
    msg = _hit(pf.run_preflight(None, ONE_SHAPE, cfg()))["message"]
    assert "merging or removing shapes cannot remove those" in msg


def test_cuts_between_shapes_keep_the_old_advice():
    """The old message was not wrong everywhere — it was wrong on the design it
    was investigated on. Where the cuts really are moves between shapes, the
    remedy it named is still the cheapest thing to try, and it is still said."""
    hit = _hit(pf.run_preflight(None, MANY_SHAPES, cfg()))
    assert hit["extra"]["between_shapes"] == hit["extra"]["trims"] == 9
    assert hit["extra"]["in_shape"] == 0
    assert "the cheapest thing to try" in hit["message"]


def test_the_carriers_are_listed_worst_first():
    plan = _plan(_row(0, "Sa", trim=True), _row(1, "Sb", trim=True),
                 _row(2, "Sb", trim=True), _row(3, "Sb", trim=True),
                 _row(4, "Sc", trim=True), _row(5, "Sc", trim=True),
                 *[_row(r, "Sd", trim=True) for r in range(6, 12)])
    extra = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
    assert [c["shape_id"] for c in extra["shapes"]] == ["Sd", "Sb", "Sc"]
    assert extra["worst_shape_id"] == "Sd"
    assert sum(c["trims"] for c in extra["shapes"]) == extra["trims"]


def test_a_run_with_no_shape_id_is_never_called_in_shape():
    """`StitchRun.shape_id` defaults to "", so an unattributed run would
    otherwise match its unattributed neighbour and claim a shape's worth of
    cuts that merging "cannot remove". Conservative by construction: only a
    NON-EMPTY id that matches counts as in-shape."""
    plan = _plan(*[_row(r, "", trim=True) for r in range(10)])
    extra = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
    assert extra["in_shape"] == 0
    assert extra["between_shapes"] == extra["trims"] == 9
    assert extra["shapes"] == []
    assert extra["worst_shape_id"] is None


def test_an_empty_leading_run_does_not_eat_a_real_cut():
    """`iter_machine_commands` SKIPS a run with no points entirely, its trim
    included, so `stats.trims` never counted it — but the correction used to
    read `blocks[0].runs[0]` regardless and subtract for it anyway. With an
    empty first run that is one real cut silently unreported."""
    plan = _plan(StitchRun(points=[], kind=st.FILL, trim=True, shape_id="Sx"),
                 *[_row(r, "Sa", trim=True) for r in range(10)])
    extra = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
    assert extra["trims"] == 9                    # 10 emitted, less the first
    assert extra["in_shape"] + extra["between_shapes"] == 9


def test_the_rate_and_the_denominator_are_unchanged():
    """This change is prose and payload — the number that earns the finding
    must be the one that always earned it."""
    hit = _hit(pf.run_preflight(None, ONE_SHAPE, cfg()))
    assert hit["extra"]["per_1000"] > 4.1
    assert hit["extra"]["stitches"] == ONE_SHAPE.stats.stitch_count
    assert hit["extra"]["per_1000"] == pytest.approx(
        1000.0 * 9 / ONE_SHAPE.stats.stitch_count, abs=0.05)


# --- The instrument that produced the corpus numbers -------------------------

def test_the_locality_tool_agrees_with_the_shipped_check():
    """`tools/trim_locality.py` re-walks the plan rather than importing
    `_trim_findings` — an auditor that calls the thing it audits proves
    nothing. Pin the agreement on plans where the two could diverge: one
    all-in-shape, one all-between, and one with an empty leading run."""
    from tools.trim_locality import split

    empty_lead = _plan(
        StitchRun(points=[], kind=st.FILL, trim=True, shape_id="Sx"),
        *[_row(r, "Sa", trim=True) for r in range(10)])
    for plan in (ONE_SHAPE, MANY_SHAPES, empty_lead):
        d = split(plan)
        extra = _hit(pf.run_preflight(None, plan, cfg()))["extra"]
        assert (d["trims"], d["in_shape"], d["between"]) == (
            extra["trims"], extra["in_shape"], extra["between_shapes"])
        assert d["in_shape"] + d["between"] == d["trims"]


def test_the_tool_reports_an_empty_leading_run_rather_than_hiding_it():
    """Its docstring claims no corpus plan has one, which is only a useful
    claim if the tool would say so when a plan does."""
    from tools.trim_locality import split

    assert split(ONE_SHAPE)["empty_lead"] is False
    assert split(_plan(
        StitchRun(points=[], kind=st.FILL, trim=True, shape_id="Sx"),
        *[_row(r, "Sa", trim=True) for r in range(10)]))["empty_lead"] is True
