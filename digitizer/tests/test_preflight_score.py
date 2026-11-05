"""The preflight score (0-100) and its grade: one mapping, pinned.

NOT a new feature. `score` has been in the report since build step 9, the
Studio prints it (`app/src/ui/QualityReport.svelte` renders `{score}/100`
beside the grade) and `tests/test_raw_score_metric.py` pins `raw_score`. This
file pins what the module comment in `digitizer_core/preflight.py` ("THE
STITCH-OUT SCORE") says about the mapping, so a later edit to `_DEDUCT` or
the grade bands cannot break the grade/score agreement unnoticed:

  * grade is a monotone step function of score (every A above every B, ...);
  * the ceiling is 100, the floor 0, and `raw_score` is the unclamped value;
  * a blocking finding caps the score: k blocks score at most 100 - 30*k;
  * the committed scorecard baseline (52 design/garment rows) obeys all of it.

Pure arithmetic over the helpers plus the committed baseline JSON: no
pipeline run, so it costs nothing and is stable across machines.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from digitizer_core import preflight as pf

BASELINE = Path(__file__).resolve().parent.parent / "testdata" / "corpus_scorecard_baseline.json"
GRADES = "ABCDF"          # best to worst


def _findings(n_warn: int = 0, n_block: int = 0, n_info: int = 0) -> list[dict]:
    return ([pf.finding("W", "warn", "w")] * n_warn
            + [pf.finding("B", "block", "b")] * n_block
            + [pf.finding("I", "info", "i")] * n_info)


def _score(findings: list[dict]) -> int:
    return max(0, pf._raw_score(findings))


def _baseline_rows() -> dict[str, dict]:
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if isinstance(v, dict) and "grade" in v}


def _severities(row: dict) -> list[str]:
    # The baseline stores findings as "CODE:severity" strings.
    return [f.rsplit(":", 1)[1] for f in row["findings"]]


# --- the deduction table ---------------------------------------------------

def test_the_deduction_table_is_what_the_comment_says():
    assert pf._DEDUCT == {"info": 0, "warn": 12, "block": 30}


def test_a_clean_report_is_the_ceiling_and_nothing_adds_score():
    assert pf._raw_score([]) == 100
    assert _score([]) == 100 and pf._grade_for(100) == "A"
    # Info is free at any count; an unknown severity is free until priced.
    assert _score(_findings(n_info=50)) == 100
    assert pf._raw_score([pf.finding("X", "weird", "x")]) == 100


def test_the_floor_is_zero_and_raw_score_keeps_the_depth():
    deep = _findings(n_block=11)
    assert pf._raw_score(deep) == 100 - 330
    assert _score(deep) == 0 and pf._grade_for(0) == "F"


# --- grade is a monotone function of score ---------------------------------

def test_grade_never_improves_as_score_falls():
    ranks = [GRADES.index(pf._grade_for(s)) for s in range(100, -1, -1)]
    assert ranks == sorted(ranks)
    assert {pf._grade_for(s) for s in range(101)} == set(GRADES)


@pytest.mark.parametrize("score,grade", [
    (100, "A"), (90, "A"), (89, "B"), (75, "B"), (74, "C"), (60, "C"),
    (59, "D"), (40, "D"), (39, "F"), (0, "F"),
])
def test_the_band_edges(score, grade):
    assert pf._grade_for(score) == grade


def test_every_warn_block_combination_agrees_on_order():
    """Exhaustive over 0-12 warns x 0-8 blocks: more findings never raise the
    score, and a better grade never sits under a worse one's score."""
    seen: dict[str, list[int]] = {g: [] for g in GRADES}
    for w in range(13):
        for b in range(9):
            s = _score(_findings(n_warn=w, n_block=b))
            assert 0 <= s <= 100
            seen[pf._grade_for(s)].append(s)
            if w:
                assert s <= _score(_findings(n_warn=w - 1, n_block=b))
            if b:
                assert s <= _score(_findings(n_warn=w, n_block=b - 1))
    present = [g for g in GRADES if seen[g]]
    for better, worse in zip(present, present[1:]):
        assert min(seen[better]) > max(seen[worse]), (better, worse)


# --- a blocking finding caps the score -------------------------------------

@pytest.mark.parametrize("k,cap,worst_grade", [
    (1, 70, "C"), (2, 40, "D"), (3, 10, "F"), (4, 0, "F"),
])
def test_k_blocks_cap_the_score_and_the_grade(k, cap, worst_grade):
    for n_warn in range(0, 6):
        for n_info in (0, 3):
            s = _score(_findings(n_warn=n_warn, n_block=k, n_info=n_info))
            assert s <= cap
            assert GRADES.index(pf._grade_for(s)) >= GRADES.index(worst_grade)


def test_one_block_never_grades_above_c_even_beside_nothing_else():
    assert pf._grade_for(_score(_findings(n_block=1))) == "C"


# --- the report agrees with the helpers (real pipeline output) -------------

def test_run_preflight_uses_the_helpers_on_a_real_fixture():
    # Imported here: the pipeline import is the slow part, the rest is pure.
    from .test_raw_score_metric import CLEAN, _report
    rep = _report(CLEAN)
    assert rep["score"] == _score(rep["findings"])
    assert rep["grade"] == pf._grade_for(rep["score"])
    assert rep["metrics"]["raw_score"] == pf._raw_score(rep["findings"])


# --- the committed scorecard baseline (52 design/garment rows) -------------

def test_the_baseline_is_the_size_the_pr_table_was_cut_from():
    # A recapture that adds rows is fine; this just fails loudly if the file
    # stops parsing into rows at all.
    assert len(_baseline_rows()) >= 52


def test_baseline_rows_obey_the_mapping():
    for name, row in _baseline_rows().items():
        raw = 100 - sum(pf._DEDUCT.get(s, 0) for s in _severities(row))
        assert row["score"] == max(0, raw), name
        assert row["grade"] == pf._grade_for(row["score"]), name
        assert row["metrics"].get("raw_score", raw) == raw, name
        blocks = _severities(row).count("block")
        assert row["score"] <= 100 - 30 * blocks, name


def test_baseline_grade_bands_do_not_overlap():
    """Every A scores above every B, every B above every C, and so on."""
    by_grade: dict[str, list[int]] = {g: [] for g in GRADES}
    for row in _baseline_rows().values():
        by_grade[row["grade"]].append(row["score"])
    present = [g for g in GRADES if by_grade[g]]
    assert present, "no baseline rows"
    for better, worse in zip(present, present[1:]):
        assert min(by_grade[better]) > max(by_grade[worse]), (better, worse)
