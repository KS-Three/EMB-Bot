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
                            StitchRun, run_stages)
from digitizer_core import stitches as st
from digitizer_core.preflight import (
    DELTA_E_CLEARLY_DIFFERENT,
    DENSITY_EXTREME,
    LETTERING_TOO_SMALL,
    STITCHES_TOO_LONG,
    STITCHES_TOO_SHORT,
    THREAD_MATCH_POOR,
    TRIM_HEAVY,
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
