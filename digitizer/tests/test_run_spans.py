"""`design["runs"]` — the run-span index, and the role that makes a border
tellable from a fill.

Why an identity and not a spot check. A span index is a second description of
something the record stream already holds, and the failure mode of a second
description is that it drifts from the first quietly: `plan_to_design` emits
`jump`/`trim`/`color` records between runs, so every span's indices depend on
rules that live somewhere else in that function, and a check that only looked
at a few spans would keep passing while the rest slid by one. The assertions
below are therefore a PARTITION — every `stitch` record is claimed by exactly
one span, each span holds nothing but that run's own stitches, and the points
match coordinate for coordinate — which cannot be satisfied by an index that
is off anywhere.

On real fixtures, not synthetic ones, for the same reason: the interleaving
only gets interesting where there are trims, colour changes, empty runs and
travel between tiers, and a hand-built two-run plan has none of those.
"""
from __future__ import annotations

from collections import Counter

import pytest

from digitizer_core import PipelineConfig, plan_stitches, run_stages
from digitizer_core.adapter import _u, plan_to_design
from digitizer_core import stitches as st

from .conftest import TESTDATA


def _design(plan, name):
    return plan_to_design(plan, name)


@pytest.fixture(scope="module")
def becker():
    """Becker's marine logo at 80 mm, WITH the border tier on.

    Real customer artwork, and the border switch is what makes it the right
    second fixture: `cfg.border` defaults to "off" for a flat-class design, so
    with stock config no `role="border"` run exists anywhere in the corpus and
    the field this module exists to pin would go untested. `edge_cap="satin"`
    for the same reason on the other role — it routes the design cap through
    `border_runs`, the emitter whose own default role is ROLE_BORDER, which is
    exactly the collision the cap has to survive.
    """
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         border="auto", edge_cap="satin")
    result = run_stages(TESTDATA / "becker_marine_logo.png", cfg)
    plan = plan_stitches(result, cfg)
    return plan, _design(plan, "Becker")


@pytest.fixture(scope="module")
def enthusiast(enthusiast_logo_93mm):
    """The repo's primary real-art benchmark, stock config, off the session
    fixture so this module adds no pipeline run for it."""
    cfg = PipelineConfig(target_width_mm=93.0)
    plan = plan_stitches(enthusiast_logo_93mm, cfg)
    return plan, _design(plan, "Enthusiast")


@pytest.fixture(params=["becker", "enthusiast"])
def fixture(request):
    return request.getfixturevalue(request.param)


# --- The identity ---------------------------------------------------------

def test_every_span_holds_only_its_own_runs_stitches(fixture):
    """`stitches[i0..i1]` is that run's penetrations, in order, and nothing
    else — no jump, no trim, no colour record ever falls inside a span."""
    plan, design = fixture
    recs = design["stitches"]
    sewn = [run for _b, run in plan.iter_runs() if run.points]
    spans = design["runs"]
    assert len(spans) == len(sewn), "one span per run that emitted stitches"

    for span, run in zip(spans, sewn):
        assert span["i0"] <= span["i1"], span
        window = recs[span["i0"]:span["i1"] + 1]
        assert len(window) == len(run.points)
        assert {r["type"] for r in window} == {"stitch"}
        # Coordinate for coordinate, through the adapter's one y-flip. This is
        # what makes the span an index into THIS run rather than into a run
        # with the same length somewhere else in the stream.
        assert [(r["x"], r["y"]) for r in window] == [_u(*p) for p in run.points]


def test_the_spans_partition_every_stitch_record_exactly_once(fixture):
    """Coverage and disjointness in one pass: no stitch is left out of the
    index, and none is claimed twice."""
    _plan, design = fixture
    recs = design["stitches"]
    stitch_idx = {i for i, r in enumerate(recs) if r["type"] == "stitch"}

    claimed: list[int] = []
    for span in design["runs"]:
        claimed.extend(range(span["i0"], span["i1"] + 1))

    assert len(claimed) == len(set(claimed)), "a stitch record is in two spans"
    assert set(claimed) == stitch_idx
    assert len(claimed) == design["stitchCount"]


def test_span_kinds_and_shapes_match_the_plan(fixture):
    """The census the browser will draw from equals the plan's own."""
    plan, design = fixture
    sewn = [run for _b, run in plan.iter_runs() if run.points]
    assert (Counter(s["kind"] for s in design["runs"])
            == Counter(r.kind for r in sewn))
    assert (Counter(s["shape"] for s in design["runs"])
            == Counter(r.shape_id for r in sewn))
    assert (Counter(s["role"] for s in design["runs"])
            == Counter(r.role for r in sewn))


def test_block_index_points_at_the_colour_that_sews_the_run(fixture):
    """`block` indexes `design["colors"]` — the plan's own block index, since
    the adapter writes one colour entry per block in sew order."""
    plan, design = fixture
    expected = [bi for bi, block in enumerate(plan.blocks)
                for run in block.runs if run.points]
    assert [s["block"] for s in design["runs"]] == expected
    assert all(0 <= s["block"] < len(design["colors"]) for s in design["runs"])

    # And the colour records in the stream agree. This is a COROLLARY, not the
    # contract: the adapter writes a `color` record only when the previous
    # block actually sewed something, so a design whose first block is empty
    # would break the correspondence while `block` stayed right. Asserted
    # under its own precondition rather than unconditionally, so a future
    # fixture with an empty leading block fails where the problem is.
    recs = design["stitches"]
    changes = [i for i, r in enumerate(recs) if r["type"] == "color"]
    if len(changes) == len(design["colors"]) - 1:
        for span in design["runs"]:
            assert sum(1 for c in changes if c < span["i0"]) == span["block"]


def test_spans_are_in_sew_order_and_do_not_overlap(fixture):
    """Consecutive spans advance. A reader can binary-search the index and a
    scrubber can map a stitch number onto a run without sorting first."""
    _plan, design = fixture
    spans = design["runs"]
    for a, b in zip(spans, spans[1:]):
        assert b["i0"] > a["i1"]


# --- The role -------------------------------------------------------------

def test_a_generated_border_is_marked_and_a_rescued_outline_is_not(becker):
    """The whole point of `role`, on artwork that has all three at once.

    Becker with `border="auto"` sews per-shape border columns, a satin design
    cap, and run-tier outlines. All three carry `kind` values a client would
    otherwise have to guess at — and the two that are NOT a shape's border
    must not read as one.
    """
    _plan, design = becker
    by_role: dict[str, Counter] = {}
    for s in design["runs"]:
        by_role.setdefault(s["role"], Counter())[s["kind"]] += 1

    assert st.ROLE_BORDER in by_role, "border='auto' generated no marked border"
    assert st.ROLE_EDGE_CAP in by_role, "edge_cap='satin' generated no marked cap"

    # A per-shape border belongs to a real shape; the cap belongs to none.
    border_shapes = {s["shape"] for s in design["runs"]
                     if s["role"] == st.ROLE_BORDER}
    assert border_shapes and "__edge_cap__" not in border_shapes
    assert {s["shape"] for s in design["runs"]
            if s["role"] == st.ROLE_EDGE_CAP} == {"__edge_cap__"}

    # The run tier sews the ARTWORK itself. Marking its outlines "border"
    # would tell the Studio an edging exists on a design that has none — the
    # reason `run_outline`'s role defaults to "" while `border_runs`' defaults
    # to ROLE_BORDER.
    assert all(s["role"] == "" for s in design["runs"]
               if s["kind"] == st.RUN and s["shape"] != "__edge_cap__")


def test_the_design_cap_keeps_its_own_role_through_the_border_emitter(becker):
    """`silhouette_cap(style="satin")` calls `border_runs`, whose default role
    is ROLE_BORDER. If the override were ever dropped, the cap would arrive at
    the browser as a per-shape border on a shape id no review screen knows."""
    _plan, design = becker
    cap = [s for s in design["runs"] if s["shape"] == "__edge_cap__"]
    assert cap, "this fixture is supposed to sew a cap"
    assert {s["role"] for s in cap} == {st.ROLE_EDGE_CAP}
    # It really did come through the satin emitter, so the collision was live.
    assert any(s["kind"] == st.BORDER for s in cap)


def test_stock_config_marks_no_border_at_all(enthusiast):
    """`cfg.border` is default-off, and the index must say so rather than
    inventing one. This is the negative half of the Studio's question."""
    _plan, design = enthusiast
    assert all(s["role"] != st.ROLE_BORDER for s in design["runs"])


# --- Additivity -----------------------------------------------------------

def test_the_index_moves_no_stitch(fixture):
    """The records and the totals are what they would be with no index at all
    — proved by rebuilding them from the plan by the adapter's own rule rather
    than by trusting the same function twice."""
    plan, design = fixture
    rebuilt = [_u(*p) for _b, run in plan.iter_runs() for p in run.points]
    assert [(r["x"], r["y"]) for r in design["stitches"]
            if r["type"] == "stitch"] == rebuilt
    assert design["stitchCount"] == len(rebuilt)
    assert design["stitches"][-1]["type"] == "end"


def test_an_imported_pattern_carries_no_index_rather_than_an_empty_one():
    """`pattern_to_design` has no runs to describe, and ABSENT is the honest
    answer — `[]` would read as "this design contains no runs" and a renderer
    keying off the index would draw nothing over a design full of stitches."""
    from digitizer_core.adapter import design_to_pattern, pattern_to_design

    plan_design = plan_to_design(_tiny_plan(), "Tiny")
    assert "runs" in plan_design
    back = pattern_to_design(design_to_pattern(plan_design), "Imported")
    assert "runs" not in back


def test_a_run_with_no_points_emits_no_span():
    """The guard that keeps an inverted `i1 = i0 - 1` out of the contract.
    Empty runs are real — `tests/test_trim_locality.py` builds them, and the
    planner carries a trim flag on one."""
    plan = _tiny_plan(with_empty=True)
    design = plan_to_design(plan, "Tiny")
    sewn = [r for _b, r in plan.iter_runs() if r.points]
    assert len(design["runs"]) == len(sewn) < sum(1 for _ in plan.iter_runs())


def _tiny_plan(with_empty: bool = False):
    runs = [st.StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=st.FILL,
                         shape_id="S1")]
    if with_empty:
        runs.append(st.StitchRun(points=[], kind=st.FILL, shape_id="S2"))
    runs.append(st.StitchRun(points=[(5.0, 5.0), (6.0, 5.0)], kind=st.SATIN,
                             shape_id="S3", jump=True, trim=True,
                             role=st.ROLE_BORDER))
    return st.StitchPlan(
        blocks=[st.StitchBlock(thread_index=0, thread_number="1234",
                               rgb=(10, 20, 30), runs=runs)],
        palette=[{"number": "1234", "name": "Test Thread"}],
    )
