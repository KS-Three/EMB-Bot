"""Preflight — the report an operator reads before the machine sews.

Two kinds of test, deliberately. The synthetic-plan tests hand the scorer a
StitchPlan built to embody exactly one defect, because each threshold is a
measured number and the test should show the measurement tripping it. The
fixture tests run the real pipeline output through the real scorer, holding
the one promise every metric here was validated against first: a clean plan
earns a clean report. A metric that flags clean work trains the operator to
ignore the report — that failure mode has already cost this project once.
"""
from __future__ import annotations

import math

import pytest

from digitizer_core import (PipelineConfig, StitchBlock, StitchPlan,
                            StitchRun, machine, run_stages)
from digitizer_core import stitches as st
from digitizer_core.preflight import (
    CONTOUR_STARVED,
    DELTA_E_CLEARLY_DIFFERENT,
    DENSITY_EXTREME,
    DENSITY_STACKED,
    LETTERING_TOO_SMALL,
    LINK_UNCOVERED,
    SAME_HOLE_HEAVY,
    STITCHES_TOO_LONG,
    STITCHES_TOO_SHORT,
    THREAD_MATCH_POOR,
    TRIM_HEAVY,
    _CONTOUR_RING_UNREACHABLE,
    _coverage_map,
    run_preflight,
)
from tests.conftest import PLAN_CFG_KW, TESTDATA, cfg

ART = TESTDATA / "logo_whitebg.png"


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _satin_column(crosses: int, width_mm: float, spacing_mm: float,
                  shape_id: str = "S1") -> StitchRun:
    """A straight zigzag column: rails alternate A, B, A, B."""
    pts = []
    for i in range(crosses):
        pts.append((i * spacing_mm, 0.0))
        pts.append((i * spacing_mm, width_mm))
    return StitchRun(points=pts, kind=st.SATIN, shape_id=shape_id)


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


# --- A clean plan earns a clean report --------------------------------------

def test_a_clean_real_plan_earns_a_clean_report(whitebg, plan):
    """The fixture logo, planned by the real pipeline, scores 100 — every
    threshold in the module was validated against this promise first."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW), image=ART)

    assert report["findings"] == []
    assert report["score"] == 100
    assert report["grade"] == "A"
    # And the instruments actually measured, rather than silently skipping.
    m = report["metrics"]
    assert m["thread_match_checked"] is True
    assert m["fill_advance_mm"] == pytest.approx(0.40, abs=0.05)
    assert m["satin_advance_mm"] == pytest.approx(0.40, abs=0.05)
    assert m["satin_short_fraction"] < 0.25
    # Law 27's region sum measured, and comfortably inside its budget.
    assert m["coverage_p50"] == pytest.approx(1.2, abs=0.15)
    assert m["coverage_over_warn_mm2"] == 0.0
    assert m["same_hole_fraction"] is not None
    # Chaining law 60 and the contour tier, both measured rather than skipped.
    # Re-measured 2026-08-02 after the fill-axis geometry fix (stage6_fill.py,
    # commit c9556ae): rows now run the shape's true long axis instead of a
    # spurious diagonal, which changes both the fill geometry chaining routes
    # around and the travel distance between shapes -- 99.4->109.0 mm needle-
    # down, and, apparently for the better on this fixture, the previously
    # 0.40 mm of bare link exposure is now fully covered (0.0). Same fix
    # already re-pinned GOLDEN_FLAG_OFF and the flat-lane golden elsewhere in
    # this suite; this is that same blast radius, not a new defect.
    assert m["link_thread_mm"] == pytest.approx(109.0, abs=1.0)
    assert m["link_uncovered_max_mm"] == pytest.approx(0.0, abs=0.05)
    assert m["fill_axis_concentration"] == pytest.approx(0.974, abs=0.02)
    assert m["contour_starved_shapes"] == 0


# --- Thread color fidelity ---------------------------------------------------

def test_madeira_fires_on_the_purple_and_isacord_does_not(whitebg):
    """The motivating case: Madeira Rayon's nearest thread to the fixture's
    purple is deltaE00 ~10.7 (12.2 by the step-8 probe) — visibly a different
    color, and silent before this module existed. Isacord matches everything
    on the same art within 4.4 and must stay silent, or the warning is noise.

    The empty plan is deliberate: only the thread check needs the artwork,
    and skipping stages 5-7 keeps the test at run_stages cost.
    """
    empty = StitchPlan(blocks=[], palette=[])

    mad_cfg = cfg(thread_brand="madeira-rayon")
    mad = run_preflight(run_stages(ART, mad_cfg), empty, mad_cfg, image=ART)
    purple = [f for f in mad["findings"]
              if f["code"] == THREAD_MATCH_POOR
              and f["extra"]["thread_number"] == "1033"]
    assert purple, "the deltaE ~12 purple substitution must be surfaced"
    assert purple[0]["severity"] == "block"
    assert purple[0]["extra"]["delta_e"] > DELTA_E_CLEARLY_DIFFERENT

    iso = run_preflight(whitebg, empty, cfg(), image=ART)
    assert THREAD_MATCH_POOR not in _codes(iso)


def test_without_the_artwork_the_thread_check_is_skipped_and_says_so(whitebg):
    """A stored plan may outlive its artwork; the report must distinguish
    'checked and clean' from 'never checked'."""
    report = run_preflight(whitebg, StitchPlan(blocks=[], palette=[]), cfg())

    assert THREAD_MATCH_POOR not in _codes(report)
    assert report["metrics"]["thread_match_checked"] is False
    assert report["metrics"]["thread_worst_delta_e"] is None


# --- Lettering size ----------------------------------------------------------

def test_satin_below_sewable_lettering_size_is_flagged():
    """House sew-out fact: stacked text below ~4 mm cap height dies at hat
    scale, and Hatch's own font ranges bottom out at 5 mm. A 3 mm shape of
    0.8 mm columns is both too small overall and too thin per stroke."""
    tiny = _plan(_satin_column(8, width_mm=0.8, spacing_mm=0.4))
    report = run_preflight(None, tiny, cfg())

    flagged = [f for f in report["findings"] if f["code"] == LETTERING_TOO_SMALL]
    assert len(flagged) == 1
    assert flagged[0]["extra"]["count"] == 1
    assert flagged[0]["extra"]["shapes"][0]["shape_id"] == "S1"


def test_a_healthy_column_is_not_lettering_too_small():
    healthy = _plan(_satin_column(30, width_mm=2.5, spacing_mm=0.4))
    assert LETTERING_TOO_SMALL not in _codes(run_preflight(None, healthy, cfg()))


# --- Stitch length -----------------------------------------------------------

def test_the_dst_ceiling_backstop_reports_a_stitch_the_planner_missed():
    """The planner splits long moves at the source, so any step past 12.1 mm
    is a regression the operator should hear about before the export quietly
    papers over it."""
    plan = _plan(StitchRun(points=[(0.0, 0.0), (15.0, 0.0)], kind=st.FILL))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == STITCHES_TOO_LONG]
    assert len(hit) == 1
    assert hit[0]["extra"]["count"] == 1
    assert hit[0]["extra"]["max_mm"] == pytest.approx(15.0, abs=0.01)


def test_a_regressed_satin_short_fraction_warns():
    """The benchmark measured 54.6% of satin stitches under the needle
    minimum before the zigzag-order fix and ~10% after; 25% is the tripwire
    halfway back to the broken world. Every cross of a 0.7 mm column is
    under the minimum, which is exactly the geometry that regression made."""
    regressed = _plan(_satin_column(40, width_mm=0.7, spacing_mm=0.4))
    report = run_preflight(None, regressed, cfg())

    hit = [f for f in report["findings"] if f["code"] == STITCHES_TOO_SHORT]
    assert len(hit) == 1
    assert hit[0]["extra"]["fraction"] > 0.25

    healthy = _plan(_satin_column(40, width_mm=2.5, spacing_mm=0.4))
    assert STITCHES_TOO_SHORT not in _codes(run_preflight(None, healthy, cfg()))


# --- Trims -------------------------------------------------------------------

def _rows(n_runs: int, pts_per_run: int, trim_from: int | None) -> list[StitchRun]:
    """n straight fill rows, 2 mm steps; runs from `trim_from` on are cut."""
    runs = []
    for r in range(n_runs):
        pts = [(2.0 * i, 3.0 * r) for i in range(pts_per_run)]
        runs.append(StitchRun(points=pts, kind=st.FILL,
                              trim=(r == 0 or (trim_from is not None and r >= trim_from)),
                              jump=True))
    return runs


def test_trim_heavy_measures_the_file_not_the_plan():
    """The plan marks the first run trimmed but the machine has no thread to
    cut yet — the corrected rate must read zero for a design that never cuts,
    and fire once real cuts pass the corpus's 4.1 per 1,000."""
    never_cuts = _plan(*_rows(4, 10, trim_from=None))
    report = run_preflight(None, never_cuts, cfg())
    assert TRIM_HEAVY not in _codes(report)
    assert report["metrics"]["trims_per_1000"] == 0.0

    scissors = _plan(*_rows(10, 10, trim_from=1))
    report = run_preflight(None, scissors, cfg())
    hit = [f for f in report["findings"] if f["code"] == TRIM_HEAVY]
    assert len(hit) == 1
    assert hit[0]["extra"]["trims"] == 9
    assert hit[0]["extra"]["per_1000"] > 4.1


# --- Density -----------------------------------------------------------------

def test_sparse_fill_rows_are_density_extreme():
    """Rows advancing 1.0 mm against the 0.40 target is 2.5x sparse — bare
    fabric grinning through the coverage."""
    pts: list[tuple[float, float]] = []
    for row in range(34):
        xs = [0.0, 2.0, 4.0, 6.0, 8.0]
        if row % 2:
            xs.reverse()
        pts.extend((x, row * 1.0) for x in xs)
    plan = _plan(StitchRun(points=pts, kind=st.FILL))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert hit[0]["extra"]["kind"] == "fill"
    assert hit[0]["extra"]["ratio"] == pytest.approx(2.5, abs=0.1)


def test_overdense_satin_is_density_extreme():
    """Same-rail advance 0.15 mm against the 0.40 spacing packs 2.7x the
    thread into the column — puckered fabric and needle heat."""
    plan = _plan(_satin_column(45, width_mm=2.0, spacing_mm=0.15))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert hit[0]["extra"]["kind"] == "satin"
    assert hit[0]["extra"]["ratio"] < 1.0


def test_a_deliberate_density_override_is_not_extreme():
    """The comparison target mirrors stage 7's own formula, so an operator
    who ASKED for 1.0 mm rows must not be warned about getting them."""
    pts: list[tuple[float, float]] = []
    for row in range(34):
        xs = [0.0, 2.0, 4.0, 6.0, 8.0]
        if row % 2:
            xs.reverse()
        pts.extend((x, row * 1.0) for x in xs)
    plan = _plan(StitchRun(points=pts, kind=st.FILL))
    report = run_preflight(None, plan, cfg(fill_row_mm=1.0))

    assert DENSITY_EXTREME not in _codes(report)


# --- Per-region coverage (law 27) --------------------------------------------

def _square_fill(side_mm: float = 14.0,
                 spacing_mm: float = machine.FILL_ROW_MM,
                 shape_id: str = "F1") -> StitchRun:
    """A boustrophedon fill of one square, rows `spacing_mm` apart.

    Rows run 2 mm per stitch, which is what stage 6 emits; the square is big
    enough (14 mm) that a stacked patch clears law 27's 5x5 mm floor.
    """
    pts: list[tuple[float, float]] = []
    row, y = 0, -side_mm / 2
    while y <= side_mm / 2:
        xs = [-side_mm / 2 + 2.0 * i for i in range(int(side_mm / 2.0) + 1)]
        if row % 2:
            xs.reverse()
        pts.extend((x, y) for x in xs)
        y += spacing_mm
        row += 1
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _stacked(layers: int) -> StitchPlan:
    """The same square filled `layers` times — one patch, N full layers."""
    return _plan(*(_square_fill(shape_id=f"F{i}") for i in range(layers)))


def test_one_full_density_fill_measures_exactly_one_covering_layer():
    """The instrument's zero point. Law 16: 40wt thread is 0.4 mm wide, so
    rows at the 0.40 mm default sit edge to edge and ARE one full covering
    layer. If this reads anything but 1.0, every threshold above is nonsense.
    """
    m = run_preflight(None, _stacked(1), cfg())["metrics"]

    assert m["coverage_p50"] == pytest.approx(1.0, abs=0.02)
    assert m["coverage_max"] == pytest.approx(1.0, abs=0.05)


def test_a_satin_column_counts_one_layer_per_same_rail_advance():
    """Law 27's unit for satin is 0.4 / SAME-RAIL advance, so a column at the
    0.40 mm default is ONE layer. A zigzag lays two legs between consecutive
    same-rail penetrations, so counting raw thread would read 2.0 here and
    would score the playbook's own 'safe classic stack' at 3.2 instead of
    2.5 — flagging the arrangement law 27 calls safe.
    """
    column = _plan(_satin_column(60, width_mm=4.0, spacing_mm=0.4))
    m = run_preflight(None, column, cfg())["metrics"]

    assert m["coverage_p50"] == pytest.approx(1.0, abs=0.1)
    assert DENSITY_STACKED not in _codes(run_preflight(None, column, cfg()))


def test_underlay_is_charged_to_the_budget_not_ignored():
    """Law 28: underlay costs ~0.1-0.2 coverage units — cheap, but not zero,
    and law 27's region sum includes it. A zigzag underlay at the 2.0 mm
    house spacing must price at 0.4 / 2.0 = 0.20, the top of law 28's band,
    derived from the stitch geometry alone rather than assumed.

    Asserted areally, over the band the underlay sweeps, because that is the
    figure law 28 quotes. A percentile would answer a different question: at
    2.0 mm the zigzag is coarser than a 1.0 mm cell, so the map resolves its
    individual legs (0.4 on a leg, less between) instead of averaging them —
    correct, and not what "0.1-0.2 units" means.
    """
    crosses = 40
    zig = _satin_column(crosses, width_mm=6.0,
                        spacing_mm=machine.UNDERLAY_ZIGZAG_MM, shape_id="U1")
    zig.kind = st.UNDERLAY
    grid, _origin = _coverage_map(_plan(zig))

    swept_mm2 = 6.0 * (crosses - 1) * machine.UNDERLAY_ZIGZAG_MM
    laid = float(grid.sum()) * machine.COVERAGE_CELL_MM ** 2
    assert laid / swept_mm2 == pytest.approx(0.20, abs=0.02)


def test_two_full_density_fills_stay_inside_the_budget():
    """Law 27 permits it in as many words — 'never more than TWO full-density
    fills stacked' — so 2.0 units must not be a finding, or the check
    condemns a legal construction."""
    report = run_preflight(None, _stacked(2), cfg())

    assert report["metrics"]["coverage_p50"] == pytest.approx(2.0, abs=0.05)
    assert DENSITY_STACKED not in _codes(report)


def test_a_third_stacked_layer_warns_though_every_object_passes_alone():
    """THE defect this check exists for. Three fills at the correct 0.40 mm
    spacing on one patch of fabric: every per-OBJECT density check passes,
    because each layer is exactly on target — DENSITY_EXTREME compares
    emitted spacing against the planner's own, and 0.40 is the planner's own.
    Only the per-REGION sum sees it. Law 27: 'a third layer means cutting a
    hole in the base'. Measured 3.00 units over 175 mm2.
    """
    report = run_preflight(None, _stacked(3), cfg())

    assert DENSITY_EXTREME not in _codes(report), \
        "the per-object check must be blind to this — that is the defect"
    hit = [f for f in report["findings"] if f["code"] == DENSITY_STACKED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["peak_units"] == pytest.approx(3.0, abs=0.1)
    assert hit[0]["extra"]["over_warn_mm2"] > 100.0
    assert hit[0]["extra"]["over_block_mm2"] == 0.0


def test_a_fourth_stacked_layer_blocks():
    """Past 3.5 units the file is not a judgement call. Embrilliance's red
    line is 6 thread layers ~ 3 lockstitch passes and we are over it."""
    hit = [f for f in run_preflight(None, _stacked(4), cfg())["findings"]
           if f["code"] == DENSITY_STACKED]

    assert len(hit) == 1
    assert hit[0]["severity"] == "block"
    assert hit[0]["extra"]["peak_units"] == pytest.approx(4.0, abs=0.1)


def test_a_stacked_speckle_too_small_to_act_on_is_not_a_finding():
    """Law 27's remedy stops at 5x5 mm ('no holes under objects < 5x5 mm'),
    and clean work does speckle over 2.5 where satin columns join or a shape
    too small for anything else is rescued with a triple run. Measured on the
    house fixtures, the biggest such speckle is 11 mm2 on the benchmark and
    6 mm2 on the fixture logo. Four stacked layers on a 3 mm square is 9 mm2
    of fabric — over the threshold, under the floor, and silent."""
    report = run_preflight(None, _plan(*(_square_fill(side_mm=3.0, shape_id=f"F{i}")
                                         for i in range(4))), cfg())

    assert report["metrics"]["coverage_max"] > machine.COVERAGE_BLOCK_UNITS
    assert DENSITY_STACKED not in _codes(report)


def test_coverage_reads_stitch_geometry_through_ties_and_splits(plan):
    """The playbook's two parity traps, which would double every satin
    number. Stage 7 splices tie bounces INTO the runs they protect and a
    bounce is a 180 deg reversal; split satin inserts mid-cross penetrations
    that make consecutive segments collinear. Either one, unstripped, moves a
    real satin column across the reversal gate and gets it charged at twice
    its density. The fixture's real plan carries both, and its satin still
    prices at one layer."""
    stitch_plan, _planned, _warnings = plan
    m = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]

    # Fill at 0.40 + underlay at law 28's 0.1-0.2: the classic stack's floor.
    assert m["coverage_p50"] == pytest.approx(1.2, abs=0.15)
    assert m["coverage_p95"] < machine.COVERAGE_WARN_UNITS


# --- Uncovered links (chaining law 60) ---------------------------------------

def _fill_rect(x0: float, y0: float, x1: float, y1: float,
               spacing: float = machine.FILL_ROW_MM,
               shape_id: str = "F") -> StitchRun:
    """A boustrophedon fill of an axis-aligned rectangle, rows `spacing` apart."""
    pts: list[tuple[float, float]] = []
    y, row = y0, 0
    cols = [x0 + 2.0 * i for i in range(int((x1 - x0) / 2.0) + 1)]
    while y <= y1 + 1e-9:
        xs = cols[::-1] if row % 2 else cols
        pts.extend((x, y) for x in xs)
        y += spacing
        row += 1
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _outline_rect(x0: float, y0: float, x1: float, y1: float,
                  shape_id: str = "R") -> StitchRun:
    """The run tier's answer to a small shape: its OUTLINE, nothing inside."""
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    pts: list[tuple[float, float]] = [corners[0]]
    for a, b in zip(corners, corners[1:]):
        n = max(1, int(math.ceil(math.dist(a, b) / machine.BEAN_STITCH_MM)))
        pts.extend((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                   for i in range(1, n + 1))
    return StitchRun(points=pts, kind=st.RUN, shape_id=shape_id)


def _link_run(a: tuple[float, float], b: tuple[float, float],
              shape_id: str = "L") -> StitchRun:
    """A needle-DOWN link between two shapes, at the chaining law's 2.0 mm."""
    n = max(1, int(math.ceil(math.dist(a, b) / 2.0)))
    return StitchRun(
        points=[(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                for i in range(n + 1)],
        kind=st.TRAVEL, shape_id=shape_id)


def _two_shapes_linked(*later_runs: StitchRun) -> StitchPlan:
    """Two filled squares 12 mm apart, joined by a needle-down link, and
    whatever sews after them in a second colour."""
    first = StitchBlock(thread_index=0, thread_number="1704", rgb=(230, 60, 60),
                        runs=[_fill_rect(-14.0, -4.0, -6.0, 4.0, shape_id="F1"),
                              _link_run((-6.0, 0.0), (6.0, 0.0)),
                              _fill_rect(6.0, -4.0, 14.0, 4.0, shape_id="F2")])
    blocks = [first]
    if later_runs:
        blocks.append(StitchBlock(thread_index=1, thread_number="3902",
                                  rgb=(60, 120, 200), runs=list(later_runs)))
    return StitchPlan(blocks=blocks, palette=[])


def test_a_link_across_bare_fabric_blocks():
    """Chaining declines a trim on the promise the thread will be buried. Here
    nothing buries it: 12 mm of needle-down thread crosses open fabric between
    two squares, which is the float the trim rule exists to cut out, now sewn
    in instead. The limit is the fabric's own trim distance — 3.0 mm on pique
    knit — because that is the number this engine already uses to decide when
    exposed thread may not be left on a garment."""
    report = run_preflight(None, _two_shapes_linked(), cfg())

    hit = [f for f in report["findings"] if f["code"] == LINK_UNCOVERED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "block"
    assert hit[0]["extra"]["limit_mm"] == 3.0
    assert hit[0]["extra"]["max_mm"] == pytest.approx(11.6, abs=0.3)
    # And it names where to look on the garment.
    assert hit[0]["extra"]["at_mm"][1] == pytest.approx(0.0, abs=0.3)


def test_a_link_buried_under_the_next_colour_is_silent():
    """Law 60's main mechanism, and the anti-noise half of the pair: the same
    link under a colour that sews after it is invisible on the finished
    garment, so it must not cost the design a thing."""
    buried = _two_shapes_linked(_fill_rect(-7.0, -3.0, 7.0, 3.0, shape_id="F3"))
    report = run_preflight(None, buried, cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["metrics"]["link_uncovered_max_mm"] == 0.0
    assert report["score"] == 100


def test_the_link_check_reads_laid_thread_not_the_shape_that_claims_to_cover_it():
    """THE defect this instrument exists for, and the known gap in stage 7's
    own test. A link is legal there when its route lies inside the covering
    geometry — POLYGONS — and the run tier sews a small shape's outline and
    nothing else, so its polygon claims cover that no thread provides. Same
    link, same covering shape, same polygon: filled it is buried, outlined it
    is a stray line across bare fabric. Only an instrument that reads the
    stitches can tell those apart, and the difference is the whole finding.
    """
    box = (-7.0, -3.0, 7.0, 3.0)
    filled = run_preflight(None, _two_shapes_linked(
        _fill_rect(*box, shape_id="F3")), cfg())
    outlined = run_preflight(None, _two_shapes_linked(
        _outline_rect(*box, shape_id="R3")), cfg())

    # The link runs straight through the middle of that shape either way.
    assert box[0] < -6.0 and box[2] > 6.0 and box[1] < 0.0 < box[3]

    assert LINK_UNCOVERED not in _codes(filled)
    assert LINK_UNCOVERED in _codes(outlined)
    assert outlined["metrics"]["link_uncovered_max_mm"] > 3.0


def test_content_thread_on_bare_fabric_is_not_a_link():
    """A fill row lying on open fabric IS the design; only thread whose job is
    to get somewhere can be a stray line. Three stacked fills therefore raise
    nothing — while the two needle-down moves BETWEEN them are still counted,
    because the machine really does sew from the end of one run to the start of
    the next. That connection belongs to no run's point list, so every
    instrument that walks a run's consecutive pairs is blind to it,
    `_coverage_map` included; here it is transport, and it is covered."""
    report = run_preflight(None, _stacked(3), cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["metrics"]["link_segments"] == 2
    assert report["metrics"]["link_uncovered_max_mm"] == 0.0


def test_the_real_fixture_leaves_no_link_on_bare_fabric(plan):
    """The promise every threshold here was validated against. Measured
    2026-08-02 over 60 configurations (5 artworks x 4 sizes x 3 garments, with
    chaining on) the longest bare stretch is 2.29 mm and the p90 is 1.07,
    against a 3.0 mm ceiling on pique knit — so real work is silent, and the
    margin comes from measurement rather than from a threshold rounded up to
    fit."""
    stitch_plan, _planned, _warnings = plan
    m = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]

    assert m["link_segments"] > 0, "the fixture does travel; measure it"
    assert m["link_uncovered_max_mm"] < 3.0
    assert m["link_uncovered_mm"] < m["link_thread_mm"] * 0.05


# --- Contour fill starvation (laws 39-44) ------------------------------------

def _starved_plan(**extra) -> StitchPlan:
    """A clean plan carrying stage 6's contour-starvation warning."""
    p = _plan(_square_fill())
    p.warnings = [dict(code=_CONTOUR_RING_UNREACHABLE,
                       message="rings too short to sew", **extra)]
    return p


def test_contour_starvation_reaches_the_operator():
    """Stage 6 knows a shape's dropped rings left more than 1% of it bare and
    says so in `plan.warnings`, which the preflight report never read — the one
    number that says a fill has a hole in it reached nobody scoring the file."""
    report = run_preflight(None, _starved_plan(count=2, rings=4), cfg())

    hit = [f for f in report["findings"] if f["code"] == CONTOUR_STARVED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["count"] == 2
    assert hit[0]["extra"]["rings"] == 4


def test_contour_starvation_names_the_shapes_when_stage_6_carries_them():
    """'Which shape' is the operator's actual question. The contour lane's
    warning carries only a count today, so the finding degrades to that; the
    moment it carries `shapes`, this says which ones with no further change."""
    report = run_preflight(None, _starved_plan(count=1, rings=2,
                                               shapes=["Sb253ebba"]), cfg())

    hit = [f for f in report["findings"] if f["code"] == CONTOUR_STARVED][0]
    assert hit["extra"]["shapes"] == ["Sb253ebba"]
    assert "Sb253ebba" in hit["message"]


def test_a_plan_with_no_starved_shape_says_nothing_about_contours(plan):
    """The silent half. A tatami fixture carries no such warning and must not
    grow one — and the metric must read 0 rather than going missing, so a
    caller can tell 'none' from 'not checked'."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert CONTOUR_STARVED not in _codes(report)
    assert report["metrics"]["contour_starved_shapes"] == 0


# --- The fill-density instrument declines what it cannot measure -------------

def _rings(outer_mm: float = 8.0, inner_mm: float = 2.0,
           spacing: float = machine.FILL_ROW_MM) -> StitchRun:
    """Concentric rings at `spacing`, sewn outer to inner — a contour fill's
    geometry, which has no dominant stitch axis by construction."""
    pts: list[tuple[float, float]] = []
    r = outer_mm
    while r >= inner_mm:
        n = max(8, int(math.ceil(2 * math.pi * r / 1.5)))
        pts.extend((r * math.cos(2 * math.pi * i / n),
                    r * math.sin(2 * math.pi * i / n)) for i in range(n + 1))
        r -= spacing
    return StitchRun(points=pts, kind=st.FILL, shape_id="C1")


def test_the_row_density_instrument_declines_on_contour_rings():
    """Warning noise, caught before it shipped. `_fill_row_advance_mm` models a
    fill as rows along one axis with short turns between them; a contour fill
    has no such axis, so the model does not degrade on it, it inverts — nearly
    every step reads as a turn and the median 'row advance' returned is really
    the ring chord. Measured on the real tier: 2.19 / 2.35 / 2.98 mm against
    the 0.40 mm target, a DENSITY_EXTREME warn on three house fixtures out of
    four whose coverage map read a healthy 1.36-1.39 units. The instrument now
    checks its own assumption and stays quiet when it does not hold."""
    report = run_preflight(None, _plan(_rings()), cfg())

    assert report["metrics"]["fill_axis_concentration"] < 0.6
    assert report["metrics"]["fill_advance_mm"] is None
    assert DENSITY_EXTREME not in _codes(report)


def test_the_gate_does_not_blind_the_instrument_to_real_rows():
    """The other half: tatami rows concentrate hard on one axis (measured
    0.913-0.991 on the house fixtures against 0.003-0.270 for contour), so the
    gate must be invisible to them and the 0.40 mm reading must survive it."""
    m = run_preflight(None, _stacked(1), cfg())["metrics"]

    assert m["fill_axis_concentration"] > 0.6
    assert m["fill_advance_mm"] == pytest.approx(0.40, abs=0.02)


# --- Same-hole strikes (law 17) ----------------------------------------------

def test_same_hole_stays_silent_on_the_practice_professionals_share(plan):
    """The field note of 2026-08-01 measured 9.455% of penetrations landing
    on points struck 2+ times across the 36-file corpus, ALL 36 files
    containing 3+ stacked points, against our benchmark's 9.8% — the same
    practice, and both charges against the engine were dismissed. A check
    that fires there is wrong, and 'the naive fix would have been damaging':
    reading law 17 strictly 'would condemn every satin column ever sewn'.
    """
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert SAME_HOLE_HEAVY not in _codes(report)
    assert report["metrics"]["same_hole_fraction"] < 0.09455


def test_same_hole_fires_only_on_a_rate_far_above_the_corpus():
    """A regression that revisits every penetration once more: 50% of
    landings are on an already-struck point, five times the corpus's 9.455%.
    INFO severity — law 17's mechanism is real but its trade phrasing is
    stricter than professional files, so this must never cost score."""
    pts: list[tuple[float, float]] = []
    for i in range(40):
        a, b = (2.0 * i, 0.0), (2.0 * i, 4.0)
        pts.extend([a, b, a, b])
    report = run_preflight(None, _plan(StitchRun(points=pts, kind=st.RUN)), cfg())

    hit = [f for f in report["findings"] if f["code"] == SAME_HOLE_HEAVY]
    assert len(hit) == 1
    assert hit[0]["severity"] == "info"
    assert hit[0]["extra"]["fraction"] > 0.25
    assert report["score"] == 100, "an info finding must not cost score"


# --- Scoring -----------------------------------------------------------------

def test_the_score_prices_severity_not_finding_count():
    """One block outweighs one warn: a wrong thread color is most of a letter
    grade, a heavy trim count is a nuisance."""
    clean = run_preflight(None, StitchPlan(blocks=[], palette=[]), cfg())
    assert (clean["score"], clean["grade"]) == (100, "A")

    warn_only = run_preflight(None, _plan(*_rows(10, 10, trim_from=1)), cfg())
    assert warn_only["score"] == 88
    assert warn_only["grade"] == "B"

    # Both thread findings ride on the madeira path (block + warn = 58, D);
    # asserted there rather than mocked here — the scorer has no seam for
    # injecting findings, deliberately.
    blocked = run_preflight(
        None, _plan(_satin_column(8, width_mm=0.8, spacing_mm=0.4)), cfg())
    assert blocked["score"] == 88   # one warn: lettering


def test_the_report_is_json_safe():
    """The service hands this straight to a JSON boundary; a stray numpy
    scalar would 500 the job endpoint."""
    import json

    plan = _plan(_satin_column(40, width_mm=0.7, spacing_mm=0.4),
                 StitchRun(points=[(0.0, 0.0), (15.0, 0.0)], kind=st.FILL))
    json.dumps(run_preflight(None, plan, cfg()))
    # The link check builds its answer out of numpy arrays; a stray numpy
    # scalar in the coordinate or the length would 500 the job endpoint.
    json.dumps(run_preflight(None, _two_shapes_linked(), cfg()))
    json.dumps(run_preflight(None, _starved_plan(count=1, rings=1,
                                                 shapes=["S1"]), cfg()))
