"""`tools/satin_columns.py` — the satin-as-sewn instrument, pinned.

What it answers: what share of a design's PENETRATIONS sit in a real zigzag
column, and how wide those columns are — read off the stitches, so ours and
a professional's digitizing of the same logo are measured by one instrument.
The plan-level question ("how many shapes took the satin rung") is a
different one, and this repo has twice paid for confusing the two.

The synthetic cases below are the contract; the professional file at the end
is the calibration, and the reason the constants are what they are.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from satin_columns import (  # noqa: E402
    MIN_RUN,
    MIN_WIDTH_MM,
    measure,
    passes_from_file,
    passes_from_plan,
)

REFERENCE = HERE.parent / "testdata" / "reference"


def _zigzag(width_mm: float, spacing_mm: float, length_mm: float) -> list[tuple[float, float]]:
    """A satin column: alternating rails, advancing one spacing per stitch."""
    pts = []
    n = int(length_mm / spacing_mm)
    for i in range(n):
        pts.append((i * spacing_mm, 0.0 if i % 2 == 0 else width_mm))
    return pts


def _tatami(row_mm: float, length_mm: float, rows: int) -> list[tuple[float, float]]:
    """A boustrophedon fill: long rows, right-angle turns at the ends."""
    pts = []
    for r in range(rows):
        y = r * row_mm
        xs = (0.0, length_mm) if r % 2 == 0 else (length_mm, 0.0)
        pts.extend([(xs[0], y), (xs[1], y)])
    return pts


def test_a_zigzag_column_reads_as_one_and_its_width_is_the_rail_gap():
    m = measure([_zigzag(2.5, 0.4, 40.0)])
    assert m["share"] > 0.97, m
    assert m["median_mm"] == pytest.approx(2.5, abs=0.02)
    assert m["under_0_7"] == 0.0 and m["under_1_0"] == 0.0


def test_a_tatami_fill_reads_as_no_satin_at_all():
    """The gate that matters: a fill's row turns are right angles, and
    without the reversal threshold they would read as satin crosses."""
    m = measure([_tatami(0.15, 30.0, 60)])
    assert m["crossing"] == 0, m
    assert m["share"] == 0.0
    assert m["columns"] == 0


def test_a_retrace_is_not_a_column_however_sharply_it_reverses():
    """Thread doubling back along its own line — a bean stitch, a travel sewn
    out and back — reverses by 180 deg and has NO width. Before the width
    floor these dominated: the Becker corpus logo read 2.7% crossing at a
    median column width of 0.00 mm."""
    out_and_back = [(i * 2.0, 0.0) for i in range(6)] + [(i * 2.0, 0.0) for i in range(5, -1, -1)]
    m = measure([out_and_back])
    assert m["crossing"] == 0, m
    assert m["median_mm"] is None


def test_two_reversals_are_a_corner_and_a_run_of_three_is_a_column():
    """`MIN_RUN` is what separates a stroke from a turn. Two crosses can
    happen at any sharp corner; a column is a sustained alternation."""
    short = _zigzag(2.0, 0.4, 0.4 * (MIN_RUN + 1))     # MIN_RUN-1 crosses
    assert measure([short])["crossing"] == 0, short
    just_long = _zigzag(2.0, 0.4, 0.4 * (MIN_RUN + 2))  # MIN_RUN crosses
    assert measure([just_long])["crossing"] > 0


def test_a_column_narrower_than_the_floor_still_counts_but_reads_thin():
    """A hairline column is the defect the width distribution exists to
    show, so it must be COUNTED, not filtered — only zero-width retraces are
    excluded. 0.5 mm is above `MIN_WIDTH_MM` and below both thin marks."""
    assert MIN_WIDTH_MM < 0.5 < 0.7
    m = measure([_zigzag(0.5, 0.4, 40.0)])
    assert m["share"] > 0.97
    assert m["under_0_7"] == 1.0 and m["under_1_0"] == 1.0


def test_a_lift_breaks_a_pass_so_a_column_never_spans_a_jump():
    """Two half-columns 50 mm apart are two columns, not one with a 50 mm
    leg — `MAX_LEG_MM` catches it even inside one pass, and the pass split
    is what makes that structural rather than incidental."""
    a = _zigzag(2.5, 0.4, 20.0)
    b = [(x + 50.0, y) for x, y in _zigzag(2.5, 0.4, 20.0)]
    two = measure([a, b])
    one = measure([a + b])
    assert two["crossing"] == one["crossing"] + 0, (two, one)


def test_our_own_plan_reads_through_the_plan_reader():
    """The plan path and the file path must answer the same question. A
    ribbon fixture sews mostly satin, which is the control that the
    instrument is not simply reporting low numbers."""
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import plan_stitches, run_stages
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(str(HERE.parent / "testdata" / "logo_script_tires.png"), cfg)
    plan = plan_stitches(result, cfg)
    m = measure(passes_from_plan(plan))
    assert m["penetrations"] > 1000
    assert m["share"] > 0.4, m
    assert m["median_mm"] is not None and m["median_mm"] > 1.0


@pytest.mark.skipif(not (REFERENCE / "becker_hat_polo_large_beckers_logolc.dst").exists(),
                    reason="professional reference file not present")
@pytest.mark.parametrize("name,penetrations,share,median", [
    ("becker_hat_polo_large_beckers_logolc.dst", 11274, 0.443, 2.52),
    ("becker_chest_small_beckers_logo_lc_2_a.dst", 8694, 0.486, 2.09),
])
def test_the_professional_files_calibrate_the_constants(name, penetrations, share, median):
    """THE calibration, and the reason this instrument is trusted: the
    professional's own production files for a logo we also digitize read
    44.3% and 48.6% of their penetrations in columns, at 2.52 and 2.09 mm
    medians. An independent audit of the larger file, with its own
    implementation, read 42.8% and 2.52 — the median to the digit, the share
    1.5 points under because its 120 deg reversal gate could not see columns
    narrower than about 0.69 mm.

    If a constant here moves, this is the test that says the instrument
    stopped measuring what it measured on 2026-09-04.

    Ours on the same logo at 100 mm reads 2.2% at a 0.29 mm median with 84%
    of its columns under 0.7 mm — pinned in `docs/superpowers/plans/
    2026-09-04-per-stroke-satin-routing.md`, not here, because that number
    is the DEFECT and is expected to move.
    """
    m = measure(passes_from_file(REFERENCE / name))
    assert m["penetrations"] == penetrations
    assert m["share"] == pytest.approx(share, abs=0.01)
    assert m["median_mm"] == pytest.approx(median, abs=0.05)
    # The professional's columns are sewable: almost none sit under the
    # needle floor, against 84% of ours on the same logo.
    assert m["under_1_0"] < 0.12
