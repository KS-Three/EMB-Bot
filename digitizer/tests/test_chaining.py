"""Stage 7 chaining — the needle-down link, and the coverage test that makes it safe.

Chaining laws 59-62 (docs/chaining-laws-2026-08-01.md), measured over 434
inter-element transitions in the 36-file professional corpus. Two of them only
work together, and that is what most of this file is about: law 59 says gap
distance is not what decides a link, and law 60 says the reason professionals
can link a 27 mm gap is that they route the link under something. Ship 59 alone
and every trim it removes comes back as a float on bare fabric.

So the load-bearing test here is not "did trims fall" — it is
`test_no_link_is_left_uncovered`, which re-measures every needle-down link the
planner emitted against the geometry that is supposed to bury it.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import (
    PipelineConfig,
    fabric_for_garment,
    machine,
    plan_stitches,
    stitches,
)
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence

from .conftest import PLAN_CFG_KW, cfg

FABRIC = fabric_for_garment(PLAN_CFG_KW["garment_id"])   # pique knit, trims at 3.0 mm

# Chaining ships OFF (see `PipelineConfig.chain_links` for the measurement that
# turned it off). Every test in this file is a test OF chaining, so each one
# turns it on for itself rather than inheriting a default — which also means
# this file keeps telling the truth whichever way that default settles.
CHAIN_ON = {**PLAN_CFG_KW, "chain_links": True}


# --- Instruments -----------------------------------------------------------

def _cover(planned, sew_index):
    """What a link in this colour block is allowed to hide under.

    Rebuilt here from stage 5's `covered_by` instead of being taken from stage
    7, because the question this file asks is whether stage 7's routes really
    are covered — not whether stage 7 believes they are.
    """
    group = [p for p in planned if p.sew_index == sew_index]
    parts = [p.polygon for p in group]
    seen: list[object] = []
    for p in group:
        c = p.covered_by
        if c is not None and not c.is_empty and not any(c is s for s in seen):
            seen.append(c)
    parts.extend(seen)
    return unary_union(parts).buffer(machine.LINK_COVER_TOL_MM)


def _uncovered_links(planned, blocks) -> list[str]:
    """Shape ids of every needle-down travel run that is NOT buried."""
    index = {p.shape_id: p.sew_index for p in planned}
    bad: list[str] = []
    for block in blocks:
        sew_index = next((index[r.shape_id] for r in block.runs
                          if r.shape_id in index), None)
        if sew_index is None:
            continue
        cover = _cover(planned, sew_index)
        for run in block.runs:
            if run.kind != stitches.TRAVEL or len(run.points) < 2:
                continue
            if not cover.covers(LineString(run.points)):
                bad.append(run.shape_id)
    return bad


def _needle_up(blocks):
    """Every needle-up move as (run, gap mm), in sew order within its block."""
    for block in blocks:
        prev = None
        for run in block.runs:
            if run.jump and prev is not None:
                yield run, math.dist(prev, run.points[0])
            prev = run.points[-1]


# --- Synthetic geometry ----------------------------------------------------

def _region(poly: Polygon, layer: int, name: str, thread: int) -> Region:
    # Forced to "fill": these bars are meant to isolate the between/within-
    # block LINKING decision (laws 59-62), not the satin-vs-fill classifier.
    # Left on "auto", `is_satin_candidate` takes a plain 10x10 square as satin
    # and `satin_shape` returns it as several disjoint underlay/satin/travel
    # groups — which is a real, separate stage-6 behaviour, but it plants
    # additional in-shape jumps these fixtures never meant to test and now
    # that cover is real thread (not the whole polygon), those extra jumps
    # sometimes cannot be bridged, which reads as this file's own tests
    # failing. Fill sews a bar as one continuous run with no internal jump.
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=f"{1000 + thread}", area_mm2=poly.area,
                  meta={"layer": layer, "tier": "fill"})


def _bar(x0: float, x1: float) -> Polygon:
    return Polygon([(x0, 0), (x1, 0), (x1, 10), (x0, 10)])


# A partial-height covering band for the two "bend into cover" tests below.
# RE-TUNED 2026-08-05 for corpus laws 23/26 landing: the "already laid" half
# of a link's cover comes from the EARLIER shape's own emitted thread
# (`_link_cover`'s stitch-centreline half, not `covered_by`'s polygon half —
# `Sbridge` here is the LATER colour and unaffected), and law 26 (pique_knit
# `fill_underlay` `edge_lattice` -> `edge_run`) removes the crosshatch pass
# that used to widen how far `Sleft`'s own thread reached toward this gap.
# The old band (y 5-9, near the bars' tops) landed exactly on the resulting
# knife-edge — this budget/coverage search is discrete enough (candidate
# waypoints, a hard stitch-length budget) that band placement doesn't move
# the pass/fail line monotonically with height or position, confirmed by a
# sweep across dozens of placements post-landing. y 0-6 (near the bars'
# BOTTOMS instead of their tops — still off-centre, same "not the middle"
# point the original geometry made) was checked robust to +-0.4 mm on both
# edges (47/49 perturbations still route as a bend, not a cut) rather than
# picked to a single passing value.
_BEND_BAND = Polygon([(10, 0), (16, 0), (16, 6), (10, 6)])


def _two_bars(bridge: Polygon | None):
    """Two same-colour bars 6 mm apart, optionally with a later colour between.

    6 mm is deliberately double the fabric's 3.0 mm trim distance: under the
    old distance rule this transition is always cut, so whatever the planner
    does with it is chaining's doing and nothing else's.
    """
    regions = [_region(_bar(0, 10), 0, "Sleft", 0),
               _region(_bar(16, 26), 0, "Sright", 0)]
    if bridge is not None:
        regions.append(_region(bridge, 1, "Sbridge", 1))
    conf = PipelineConfig(**CHAIN_ON)
    planned, _ = resolve_overlaps(regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    return planned, blocks


def _crossing(blocks):
    """How the plan gets from the left bar to the right one.

    The run the sequence reaches Sright by: a TRAVEL run when the transition
    was chained, and the trimmed first run of Sright when it was not. Stage 6
    also emits travel runs INSIDE each bar, which is why this looks at the
    shape boundary rather than at travel runs generally — an in-shape bridge
    says nothing about whether the gap between the bars was linked.
    """
    runs = blocks[0].runs
    for i, run in enumerate(runs):
        if i and run.shape_id == "Sright" and runs[i - 1].shape_id == "Sleft":
            return run
    raise AssertionError("the plan never got from one bar to the other")


def _bridged(right_x0: float, *, chain: bool = True):
    """Two same-colour bars with a later colour bridging the whole gap.

    Coverage is deliberately never in question here — the bridge covers every
    straight line between the bars — so distance is the only thing left that
    can decide the transition, which is what makes these fixtures a test of
    the knee rather than of law 60 again.
    """
    regions = [_region(_bar(0, 10), 0, "Sleft", 0),
               _region(_bar(right_x0, right_x0 + 10), 0, "Sright", 0),
               _region(Polygon([(10, 0), (right_x0, 0),
                                (right_x0, 10), (10, 10)]), 1, "Sbridge", 1)]
    conf = PipelineConfig(**{**PLAN_CFG_KW, "chain_links": chain})
    planned, _ = resolve_overlaps(regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    return planned, blocks


def _transition(blocks):
    """(where the needle was, the run it reaches Sright by).

    `_crossing` without discarding the near side, because the length of a
    transition is a property of the pair and not of either run.
    """
    runs = blocks[0].runs
    for i, run in enumerate(runs):
        if i and run.shape_id == "Sright" and runs[i - 1].shape_id == "Sleft":
            return runs[i - 1].points[-1], run
    raise AssertionError("the plan never got from one bar to the other")


# --- Law 60: a link is legal only where it will be buried -------------------

def test_a_gap_a_later_colour_covers_is_sewn_not_cut():
    """The whole of law 59, gated on the whole of law 60. The bars sit 6 mm
    apart — twice the trim distance — and the only thing that makes the link
    legal is that another colour lands on top of it afterwards."""
    planned, blocks = _two_bars(Polygon([(10, 0), (16, 0), (16, 10), (10, 10)]))
    link = _crossing(blocks)

    assert link.kind == stitches.TRAVEL, "the covered gap should have been sewn"
    assert not link.trim and not link.jump
    assert not any(r.trim for r in blocks[0].runs[1:]), "nothing here needs cutting"
    assert not _uncovered_links(planned, blocks)


def test_a_link_bends_into_the_cover_rather_than_giving_up():
    """Law 60's actual mechanism: the covering colour reaches across only a
    6 mm band, so the straight line between the bars is NOT covered and a
    planner that only knows how to go straight would cut here. Professionals
    route where the thread will be buried, which is the whole reason they can
    link at 27 mm without showing a float.

    The band is `_BEND_BAND` (y 0-6, not centred in the bars' height) — see
    its own comment for the 2026-08-05 re-tuning after corpus laws 23/26.
    Within budget reach, the bend still happens and is still required (the
    straight line stays uncovered)."""
    planned, blocks = _two_bars(_BEND_BAND)
    link = _crossing(blocks)

    assert link.kind == stitches.TRAVEL, "a route through the band exists"
    assert not _uncovered_links(planned, blocks)

    # It really did detour rather than going straight. The measurement has to
    # be made against the geometry that is actually sewn, not against the
    # artwork: stage 5 pull-compensates each bar outward and grows it under the
    # later colour, so the bars occupy x <= 10.55 and x >= 15.45 by the time
    # anything travels between them. A route point at x = 15.7 is standing on
    # the right bar's own thread, not on bare fabric, and an earlier version of
    # this test read exactly that point as a float because it took the artwork
    # gap (10..16) for the exposed one.
    #
    # So: subtract the block's own sewing polygons from the link, and whatever
    # is left is the part that lies on fabric this colour did not lay. ALL of
    # it must be under the band, which is the only cover in the gap.
    own = unary_union([p.polygon for p in planned if p.sew_index == 0])
    exposed = LineString(link.points).difference(own)
    assert not exposed.is_empty, \
        "the link never left its own colour's work — it crossed no gap at all"
    assert _BEND_BAND.buffer(machine.LINK_COVER_TOL_MM).covers(exposed), \
        "the link crossed bare fabric instead of bending under the band"


def test_a_sliver_of_a_future_colour_no_longer_counts_as_cover():
    """The covered_by inset (LINK_COVER_INSET_MM), pinned at its own edge.

    `covered_by` is a future colour's ARTWORK polygon, and no tier stitches
    its whole polygon — measured on both committed fixtures (2026-08-04), the
    real emitted thread stops up to 0.301 mm inside a satin boundary (thread
    edge; 0.501 mm to the nearest centreline) and a run-tier shape never
    covers its interior at all (honest only once eroded away at its inradius,
    0.527/0.539 mm on the fixtures). So `_link_cover` now erodes every
    future-colour polygon by LINK_COVER_INSET_MM before it may bury a link.

    Everything here is 1.2 mm tall — thinner than twice the inset — so the
    bridging colour's eroded cover is EMPTY: geometry that thin cannot
    promise a buried link anywhere in it, whatever its outline claims (were
    it a run-tier sliver it would sew as a bare outline; even sewn as fill,
    its real rows stop short of the edge a link would ride). Before the
    inset this exact fixture sewed the transition as a needle-down link
    routed under the sliver; verified 2026-08-04 on the pre-inset engine.
    Now it must fall back to the distance rule: 6 mm on a 3.0 mm-trim fabric
    is a cut — the cheap direction to be wrong in (a needle-up move, not a
    float).

    The bars are 1.2 mm tall too, and that is fixture engineering, not the
    point under test: a transition's endpoints are emergent (they move with
    the fill), and thin bars force the whole transition to happen within the
    sliver's reach — so the ONLY thing deciding link-vs-cut is whether the
    sliver still counts as cover. The 4 mm band in
    `test_a_link_bends_into_the_cover_rather_than_giving_up` is this test's
    control: it survives the same erosion (4.0 - 1.5 = 2.5 mm of honest
    middle) and still links.
    """
    def thin_bar(x0: float, x1: float) -> Polygon:
        return Polygon([(x0, 0), (x1, 0), (x1, 1.2), (x0, 1.2)])

    sliver = thin_bar(10, 16)
    assert sliver.buffer(-machine.LINK_COVER_INSET_MM).is_empty, \
        "the fixture no longer measures what it claims: this band should erode away"
    regions = [_region(thin_bar(0, 10), 0, "Sleft", 0),
               _region(thin_bar(16, 26), 0, "Sright", 0),
               _region(sliver, 1, "Sbridge", 1)]
    conf = PipelineConfig(**CHAIN_ON)
    planned, _ = resolve_overlaps(regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    cut = _crossing(blocks)
    assert cut.kind != stitches.TRAVEL, \
        "a 1.2 mm sliver of a future colour must not bury a 6 mm link"
    assert cut.jump and cut.trim, "the thread must be cut"
    assert not _uncovered_links(planned, blocks)


def test_a_gap_nothing_will_cover_is_still_cut():
    """The failure this whole design exists to prevent. Same two bars, same
    6 mm, no covering colour — so the needle must lift. A link here is a
    float lying on bare fabric between two elements, which is strictly worse
    than the trim it replaced."""
    planned, blocks = _two_bars(None)
    cut = _crossing(blocks)
    assert cut.kind != stitches.TRAVEL, "nothing covers this gap"
    assert cut.jump and cut.trim, "the thread must be cut"
    assert not _uncovered_links(planned, blocks)


def test_a_link_is_sewn_at_the_professional_running_pitch():
    """Law 61 [M]: median 1.96 mm, p90 2.48 — so a link runs at 2.0. Stage 6's
    in-shape bridges keep their own 2.5 mm pitch and their own sew-out, which
    is why this measures a link the test built rather than travel at large."""
    link = _crossing(_two_bars(_BEND_BAND)[1])
    assert link.kind == stitches.TRAVEL, "must measure a real link, not a cut"
    assert len(link.points) >= 2
    for a, b in zip(link.points, link.points[1:]):
        assert math.dist(a, b) <= machine.RUN_STITCH_MM + 1e-6


def test_a_gap_past_the_knee_is_cut_even_though_it_is_covered():
    """Where law 59's flat curve stops being flat. The bars are 60 mm apart and
    a later colour bridges the whole way, so coverage says yes and the stitch
    budget says yes too — 36 stitches at 2.0 mm is 72 mm of allowance. Only
    LINK_MAX_GAP_MM refuses this, and it refuses it because past 40 mm the
    corpus itself flips: 33 transitions out there, 70% of them trimmed.

    Note what this test is NOT. It is not "60 mm never happens" — the longest
    linked gap in the corpus is 61.7 mm, so professionals do sometimes sew
    exactly this. It is that we cannot tell from geometry which 30% those are,
    and the two mistakes cost differently: a needless trim is two seconds, a
    needless 60 mm link is a float.
    """
    planned, blocks = _bridged(70.0)
    cut = _crossing(blocks)
    assert cut.kind != stitches.TRAVEL, \
        "a gap this wide is past law 59's knee and must not be linked"
    assert cut.trim
    for block in blocks:
        for run in block.runs:
            if run.kind == stitches.TRAVEL:
                assert len(run.points) <= machine.LINK_MAX_STITCHES


def test_the_knee_is_read_off_the_move_the_needle_actually_makes():
    """Which distance the cap measures, pinned on both sides of it.

    Law 59 bucketed TRANSITIONS, and a transition runs from where the thread
    stopped to where it starts again — not from one shape's edge to the next
    one's, or from the artwork gap. A cap read off the artwork gap instead
    could let through a lift the fill tier's own exit point makes longer or
    shorter than the gap implies.

    Both fixtures are bridged end to end, so coverage cannot be what separates
    them; the only difference is length. Each one's lift is measured with
    chaining OFF, which is the honest way to ask how far the needle would have
    travelled — with chaining on, the move has already been replaced by the
    thing under test.
    """
    for right_x0, expect_link in ((26.0, True), (60.0, False)):
        _, plain = _bridged(right_x0, chain=False)
        was, reached = _transition(plain)
        lift_mm = math.dist(was, reached.points[0])
        assert reached.jump, "with chaining off this transition is a lift"
        assert (lift_mm <= machine.LINK_MAX_GAP_MM) is expect_link, (
            f"bars at x={right_x0} lift {lift_mm:.2f} mm, which is on the "
            f"wrong side of the {machine.LINK_MAX_GAP_MM} mm knee for this "
            f"case — the fixture no longer measures what it claims to")

        planned, blocks = _bridged(right_x0)
        _, got = _transition(blocks)
        assert (got.kind == stitches.TRAVEL) is expect_link, \
            f"a {lift_mm:.2f} mm lift under full cover: link={expect_link}"
        assert not _uncovered_links(planned, blocks)
        if not expect_link:
            assert got.jump and got.trim


def test_no_link_is_left_uncovered(plan, alpha):
    """The acceptance property, on real artwork: zero uncovered links, by
    construction rather than by luck. Every segment of every route was tested
    against the cover before it was sewn; this asks the finished stitches."""
    stitch_plan, planned, _ = plan
    assert not _uncovered_links(planned, stitch_plan.blocks)

    conf = cfg(**CHAIN_ON)
    a_planned, _ = resolve_overlaps(alpha.regions, FABRIC, conf)
    a_blocks, _ = sequence(a_planned, FABRIC, conf)
    assert not _uncovered_links(a_planned, a_blocks)


# --- Laws 61 and 62: what a link costs -------------------------------------

# --- The rest of the plan must survive it ----------------------------------

def test_chaining_removes_trims_without_removing_locks(alpha):
    """`_apply_ties` locks the thread wherever it is cut, so fewer trims is
    fewer ties by construction — and the risk is that a chained sequence loses
    the lock it still needs. Every block must still open and close with one,
    and every surviving cut must still be locked on both sides."""
    conf = cfg(**CHAIN_ON)
    planned, _ = resolve_overlaps(alpha.regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)

    def locked_head(run) -> bool:
        return min(math.dist(run.points[0], p) for p in run.points[1:4]) \
            <= machine.TIE_STITCH_MM + 1e-6

    def locked_tail(run) -> bool:
        return min(math.dist(run.points[-1], p) for p in run.points[-4:-1]) \
            <= machine.TIE_STITCH_MM + 1e-6

    for block in blocks:
        assert block.runs[0].trim, "a colour change always cuts"
        assert locked_head(block.runs[0]), "a chained block lost its start lock"
        assert locked_tail(block.runs[-1]), "a chained block lost its end lock"
        for i, run in enumerate(block.runs):
            if run.trim and i > 0:
                assert locked_head(run), "the thread restarts here unlocked"
                assert locked_tail(block.runs[i - 1]), "cut without tying off"


def test_a_link_is_never_sewn_across_a_colour_change(alpha):
    """It would be sewn in the wrong thread. The first run of every block
    stays a cut, whatever the geometry says."""
    conf = cfg(**CHAIN_ON)
    planned, _ = resolve_overlaps(alpha.regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    for block in blocks:
        assert block.runs[0].jump and block.runs[0].trim
        assert block.runs[0].kind != stitches.TRAVEL


def test_an_uncovered_needle_up_move_still_obeys_the_trim_distance(alpha):
    """Law 59 retires distance as the LINK decision, not as the trim decision.
    Whatever cannot be buried is still governed by the fabric preset: a float
    long enough to catch a finger is still cut."""
    conf = cfg(**CHAIN_ON)
    planned, _ = resolve_overlaps(alpha.regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    for run, gap in _needle_up(blocks):
        if not run.trim:
            assert gap <= FABRIC.trim_at_mm + 1e-6


def test_chaining_off_restores_the_pure_distance_rule(alpha):
    """The escape hatch the pre-chaining goldens are pinned to."""
    conf = cfg(**PLAN_CFG_KW, chain_links=False)
    planned, _ = resolve_overlaps(alpha.regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    for block in blocks:
        prev = None
        for i, run in enumerate(block.runs):
            if run.jump and prev is not None and i > 0:
                gap = math.dist(prev, run.points[0])
                assert run.trim == (gap > FABRIC.trim_at_mm)
            prev = run.points[-1]


def test_chaining_cuts_the_benchmark_fixtures_trim_rate(enthusiast_logo_82mm):
    """The measured reason this exists: 8.4 trims per 1,000 stitches against a
    professional corpus that runs 0.1-4.1. Pinned on a committed fixture so the
    gain cannot silently regress.

    Moved from `logo_alpha.png` to `enthusiast_logo.png` @ 82mm (2026-08-06)
    -- see `enthusiast_logo_82mm`'s own fixture docstring in conftest.py for
    why: the satin/fill classifier's flat-lane fix correctly reclassified two
    of logo_alpha's shapes from satin to fill, which eliminated the specific
    gap chaining used to bridge on that fixture. This is a stronger
    demonstration than logo_alpha ever gave: on the new fixture chaining cuts
    trims 21 -> 9 (vs. the old 13 -> 9) at a comfortable 3.4/1k, not hugging
    the 4.1 ceiling."""
    off = plan_stitches(enthusiast_logo_82mm, cfg(target_width_mm=82.0, garment_id="left_chest", chain_links=False))
    on = plan_stitches(enthusiast_logo_82mm, cfg(target_width_mm=82.0, garment_id="left_chest", chain_links=True))
    assert on.stats.trims < off.stats.trims, "chaining removed no trims at all"
    rate = 1000.0 * (on.stats.trims - 1) / on.stats.stitch_count
    assert rate <= 4.1, f"{rate:.1f} trims/1k is still outside the corpus band"
    # Links are cheap and ties are not: each cut costs a lock at both ends, so
    # replacing cuts with 2 mm running stitches pays for itself.
    assert on.stats.stitch_count <= off.stats.stitch_count


# --- The instrument that was missing ---------------------------------------

def _thread_bare_mm(plan, step_mm: float = 0.1):
    """(links, exposed links, mm on bare fabric, worst clearance) for one plan.

    THE THIRD INSTRUMENT, and the only honest one. `_uncovered_links` above and
    `tools/chain_probe.py` both rebuild the cover from the same polygons the
    router already trusted, so neither can report the router wrong about them.
    This one never looks at a polygon. It asks where thread physically lands.

    It also fixes two structural blind spots those two share, each of which
    hides real stitches:

    - **One-point links are not skipped.** Both shipped instruments `continue`
      on `len(run.points) < 2`, and a one-point link is 37% of the benchmark's.
      They are real: export emits a plain STITCH record for a run with
      `jump=False`, so the machine sews straight through the point, needle
      down. The guard cannot simply be deleted — `LineString` of one point
      raises — which is why the path has to be rebuilt from the neighbours.
    - **The real sewn path is measured, not the stored one.** `_link_stitches`
      returns only the route's INTERIOR, so the first and last segments the
      needle actually sews — up to RUN_STITCH_MM each — appear in no run's
      points and are examined by nothing. The path here runs from the previous
      run's last penetration, through the link, to the next run's first.

    Bare means further than half a thread width from ANY emitted non-travel
    stitch, of any colour, at any point in the sew order. That is generous to
    the engine on purpose: it credits cover from threads laid long before and
    long after, and it still finds exposure.
    """
    runs = [r for b in plan.blocks for r in b.runs]
    laid = [LineString(r.points) for r in runs
            if r.kind != stitches.TRAVEL and len(r.points) >= 2]
    if not laid:
        return 0, 0, 0.0, 0.0
    thread = unary_union(laid)
    half = machine.COVERAGE_THREAD_W_MM / 2.0

    links = exposed = 0
    bare_mm = worst = 0.0
    for i, run in enumerate(runs):
        if run.kind != stitches.TRAVEL:
            continue
        links += 1
        pts = list(run.points)
        if i and runs[i - 1].points:
            pts.insert(0, runs[i - 1].points[-1])
        if i + 1 < len(runs) and runs[i + 1].points:
            pts.append(runs[i + 1].points[0])
        if len(pts) < 2:
            continue
        path = LineString(pts)
        n = max(2, int(path.length / step_mm))
        bad = 0.0
        for k in range(n + 1):
            d = thread.distance(path.interpolate(k / n, normalized=True))
            if d > half:
                bad += path.length / n
                worst = max(worst, d)
        if bad:
            exposed += 1
        bare_mm += bad
    return links, exposed, bare_mm, worst


def test_chaining_adds_no_bare_fabric_exposure_on_the_committed_fixture(enthusiast_logo_82mm):
    """The fix, measured. Replaces `test_chaining_currently_puts_thread_on_bare
    _fabric`, deleted in the same commit as its own docstring asked for.

    That test pinned a KNOWN DEFECT: `_link_cover` decided cover against
    `p.polygon` — the whole sewing polygon of every shape the block had
    stitched — but no tier stitches its whole polygon, so the router was told
    it could travel over ground its own colour never reached.

    `_link_cover` now builds the already-laid half of the cover from `runs`
    directly — the block's real emitted stitch centrelines, buffered to their
    real thread width — instead of from `p.polygon`.

    **Fixture moved from `logo_alpha.png` to `enthusiast_logo.png` @ 82mm
    (2026-08-06)** — see `enthusiast_logo_82mm`'s own fixture docstring in
    conftest.py. The satin/fill classifier's flat-lane fix correctly
    reclassified two of logo_alpha's shapes from satin to fill, which
    eliminated the specific gap chaining used to bridge on that fixture
    (measured directly: chain_links on vs. off became byte-identical output
    there — 6 links either way, 0 exposure either way). Every
    synthetic-geometry chaining test elsewhere in this file is unaffected;
    this is that one fixture's geometry changing, not a chaining regression.

    On the new fixture, chaining's 15 extra links (2 -> 17) add ZERO bare
    exposure: `exp1 == exp0 == 0` and `bare1 == bare0 == 0.0` exactly — a
    cleaner result than logo_alpha's old 0.3011mm/0.2057mm floor, not a
    weaker one. Trims fall 21 -> 9 and total stitch count falls
    correspondingly — the win law 59 measured is real and it still doesn't
    cost a float to get.

    `covered_by` (a later colour's own sewing polygon, standing in for thread
    that has not been planned yet) is unchanged and is not what this test
    covers — see `config.py`'s `chain_links` docstring for what is still
    outstanding before the default flips.
    """
    off = plan_stitches(enthusiast_logo_82mm, cfg(target_width_mm=82.0, garment_id="left_chest", chain_links=False))
    on = plan_stitches(enthusiast_logo_82mm, cfg(target_width_mm=82.0, garment_id="left_chest", chain_links=True))

    l0, exp0, bare0, worst0 = _thread_bare_mm(off)
    l1, exp1, bare1, worst1 = _thread_bare_mm(on)

    assert l1 > l0, "chaining added no links at all — this fixture no longer exercises it"
    assert on.stats.trims < off.stats.trims, "chaining removed no trims"
    assert exp1 <= exp0, f"chaining exposed {exp1} runs against a floor of {exp0}"
    assert bare1 <= bare0 + 1e-6, f"chaining's bare exposure GREW to {bare1:.4f} mm"
    assert worst1 <= worst0 + 1e-6, f"worst clearance GREW to {worst1:.4f} mm"


def test_with_chaining_off_no_link_is_worse_than_stage_6_already_was(alpha):
    """The guarantee the shipped default actually makes. Chaining off, the only
    needle-down travel in a plan is stage 6's own in-shape bridging, and that
    is the engine this repo has been sewing from all along."""
    off = plan_stitches(alpha, cfg(**{**PLAN_CFG_KW, "chain_links": False}))
    _links, _exposed, _bare, worst = _thread_bare_mm(off)
    assert worst <= machine.COVERAGE_THREAD_W_MM, \
        "stage 6 travel is now further from thread than one thread width"
