"""`STITCHES_TOO_SHORT` says WHICH shapes carry the short stitches.

The check and `LETTERING_TOO_SMALL` measure the SAME quantity at the SAME
threshold -- `MIN_COLUMN_MM is machine.MIN_STITCH_MM`, both read off the
consecutive-step distance inside a satin run, which crosses the column. Over
the 26-fixture corpus at 80 mm this one never fired without the other (10 both,
1 lettering only, **0 here alone**), so on its own it was a second 12-point
deduction for one defect.

What it genuinely sees that lettering does not is WHERE. Lettering judges a
shape on its MEDIAN column, so only 66% of the short steps sat inside a shape
it named; the rest live in normal-width columns -- corpus medians 1.1 to
3.2 mm -- that pinch in one place. `logo_bridge_bar`'s worst residual shape has
a 2.65 mm median and 205 of its 1,597 steps under the needle minimum.

So the payload now names every carrier and flags which ones the size warning
already covered, and the message no longer recommends enlarging: the lettering
docstring's own table measured that the median flagged column stays flat near
0.8 mm from 92.5 to 220 mm, and the documented root cause is per-stroke satin
routing, which is scale-invariant.

Synthetic plans only -- no pipeline, no corpus. The corpus numbers above are
the argument for the change, not something worth re-measuring in CI.
"""

import math

import pytest

from digitizer_core import machine, preflight as pf, stitches as st
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .conftest import cfg


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _column(crosses: int, width_mm: float, spacing_mm: float,
            shape_id: str) -> StitchRun:
    """A straight zigzag: rails alternate, so every consecutive pair crosses."""
    pts = []
    for i in range(crosses):
        pts.append((i * spacing_mm, 0.0))
        pts.append((i * spacing_mm, width_mm))
    return StitchRun(points=pts, kind=st.SATIN, shape_id=shape_id)


def _waisted(crosses: int, wide_mm: float, waist_mm: float, n_waist: int,
             spacing_mm: float, shape_id: str) -> StitchRun:
    """A sewable column that pinches in the middle.

    The shape LETTERING_TOO_SMALL is structurally blind to: its median column
    is `wide_mm`, comfortably over the floor, and its bbox is far past the
    4 mm lettering extent -- so it passes both of that check's tests while the
    crosses inside the waist still fall under the needle minimum.
    """
    pts = []
    lo = (crosses - n_waist) // 2
    for i in range(crosses):
        w = waist_mm if lo <= i < lo + n_waist else wide_mm
        pts.append((i * spacing_mm, 0.0))
        pts.append((i * spacing_mm, w))
    return StitchRun(points=pts, kind=st.SATIN, shape_id=shape_id)


TINY = _column(20, width_mm=0.7, spacing_mm=0.4, shape_id="Stiny")
WAIST = _waisted(30, wide_mm=2.5, waist_mm=0.5, n_waist=6, spacing_mm=0.4,
                 shape_id="Swaist")


def _hit(report: dict, code: str) -> dict | None:
    for f in report["findings"]:
        if f["code"] == code:
            return f
    return None


# --- The fixtures are the argument, so pin what they are ---------------------

def test_the_waisted_column_is_invisible_to_the_size_warning():
    """If this shape ever starts tripping LETTERING_TOO_SMALL the rest of the
    file proves nothing -- the whole point is a carrier that check cannot see.
    """
    report = pf.run_preflight(None, _plan(WAIST), cfg())
    assert _hit(report, pf.LETTERING_TOO_SMALL) is None

    # ...and it is a real carrier, not a shape with no short steps at all.
    short = sum(1 for a, b in zip(WAIST.points, WAIST.points[1:])
                if math.dist(a, b) < machine.MIN_STITCH_MM)
    assert short > 0


def test_the_tiny_column_is_named_by_the_size_warning():
    report = pf.run_preflight(None, _plan(TINY), cfg())
    hit = _hit(report, pf.LETTERING_TOO_SMALL)
    assert hit is not None
    assert [s["shape_id"] for s in hit["extra"]["shapes"]] == ["Stiny"]


def test_the_two_checks_share_one_threshold():
    """Not a style note -- it is why the finding needed the hand-off at all."""
    assert pf.MIN_COLUMN_MM is machine.MIN_STITCH_MM


# --- What the finding now reports -------------------------------------------

def test_every_carrier_is_named_worst_first():
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    hit = _hit(report, pf.STITCHES_TOO_SHORT)
    assert hit is not None
    shapes = hit["extra"]["shapes"]
    assert {s["shape_id"] for s in shapes} == {"Stiny", "Swaist"}
    assert [s["short"] for s in shapes] == sorted(
        (s["short"] for s in shapes), reverse=True)


def test_the_waisted_shape_is_flagged_as_uncovered():
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    extra = _hit(report, pf.STITCHES_TOO_SHORT)["extra"]
    by_id = {s["shape_id"]: s for s in extra["shapes"]}
    assert by_id["Stiny"]["also_too_small"] is True
    assert by_id["Swaist"]["also_too_small"] is False
    assert extra["uncovered_shapes"] == 1


def test_the_message_points_at_the_uncovered_shapes():
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    msg = _hit(report, pf.STITCHES_TOO_SHORT)["message"]
    assert "1 of the 2 shapes" in msg
    assert "the size warning does not cover them" in msg
    assert " has a normal column width" in msg   # singular, not "have"


def test_the_message_says_so_when_the_size_warning_covers_everything():
    """Three tiny columns and nothing else: this finding adds no new location,
    and saying so is more use than repeating the remedy one check over."""
    report = pf.run_preflight(None, _plan(
        TINY,
        _column(20, width_mm=0.7, spacing_mm=0.4, shape_id="Stiny2"),
        _column(20, width_mm=0.6, spacing_mm=0.4, shape_id="Stiny3"),
    ), cfg())
    extra_msg = _hit(report, pf.STITCHES_TOO_SHORT)["message"]
    assert "already flagged as too small to sew" in extra_msg
    assert _hit(report, pf.STITCHES_TOO_SHORT)["extra"]["uncovered_shapes"] == 0


def test_the_message_no_longer_recommends_enlarging():
    """Measured false where it mattered: LETTERING_TOO_SMALL's own docstring
    table shows the median flagged column flat near 0.8 mm from 92.5 to
    220 mm. Offering "enlarge" for a defect scale does not fix is the whole
    thing this change removes."""
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    msg = _hit(report, pf.STITCHES_TOO_SHORT)["message"].lower()
    assert "enlarge" not in msg
    assert "bigger" not in msg


def test_the_carrier_step_counts_add_up_to_the_denominator():
    """A guard on the guard: `steps` is filled in the same loop that counts
    `total`, so a future edit that filters one and not the other shows up here
    rather than as a payload nobody re-checks."""
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    extra = _hit(report, pf.STITCHES_TOO_SHORT)["extra"]
    assert sum(s["short"] for s in extra["shapes"]) == extra["count"]
    assert extra["count"] / extra["total"] == pytest.approx(
        extra["fraction"], abs=0.001)


def test_the_medians_are_reported_per_shape():
    report = pf.run_preflight(None, _plan(TINY, WAIST), cfg())
    by_id = {s["shape_id"]: s
             for s in _hit(report, pf.STITCHES_TOO_SHORT)["extra"]["shapes"]}
    assert by_id["Swaist"]["median_mm"] == pytest.approx(2.5, abs=0.05)
    assert by_id["Stiny"]["median_mm"] == pytest.approx(0.7, abs=0.05)


# --- The hand-off is optional, and the old call still works ------------------

def test_the_helper_still_runs_without_the_hand_off():
    """`already_small` defaults to None so a direct caller (a tool, a probe)
    keeps working; everything is then reported as uncovered, which is the
    honest answer when nothing said otherwise."""
    findings, metrics = pf._stitch_length_findings(_plan(TINY, WAIST))
    hit = [f for f in findings if f["code"] == pf.STITCHES_TOO_SHORT][0]
    assert hit["extra"]["uncovered_shapes"] == 2
    assert all(s["also_too_small"] is False for s in hit["extra"]["shapes"])
    assert metrics["satin_steps"] > 0


def test_a_healthy_plan_reports_nothing():
    healthy = _plan(_column(40, width_mm=2.5, spacing_mm=0.4, shape_id="Sok"))
    report = pf.run_preflight(None, healthy, cfg())
    assert _hit(report, pf.STITCHES_TOO_SHORT) is None


def test_the_singular_branch_of_the_covered_message_reads():
    """One carrier, and it is already flagged: "All 1 shapes" would have
    shipped. Both branches of this sentence are generated, so both are read
    here rather than only the one the corpus happens to produce."""
    report = pf.run_preflight(None, _plan(TINY), cfg())
    msg = _hit(report, pf.STITCHES_TOO_SHORT)["message"]
    assert "The one shape carrying them is already flagged" in msg
    assert "All 1 shapes" not in msg


# --- The instrument that produced the corpus numbers -------------------------

def test_the_overlap_tool_measures_satin_steps_independently():
    """`tools/short_satin_overlap.py` deliberately re-walks the geometry rather
    than importing `_stitch_length_findings`' loop — an auditor that calls the
    thing it audits proves nothing. That makes divergence possible, so pin the
    two properties the re-implementation has to keep: SATIN runs only, and one
    distance per consecutive pair."""
    from tools.short_satin_overlap import _satin_steps

    fill = StitchRun(points=[(0.0, 0.0), (5.0, 0.0)], kind=st.FILL,
                     shape_id="Sfill")
    got = _satin_steps(_plan(WAIST, fill))
    assert list(got) == ["Swaist"]
    assert len(got["Swaist"]) == len(WAIST.points) - 1

    # ...and it agrees with the finding's own denominator on the same plan.
    _f, metrics = pf._stitch_length_findings(_plan(TINY, WAIST))
    assert sum(len(v) for v in _satin_steps(_plan(TINY, WAIST)).values()) \
        == metrics["satin_steps"]
