"""corpus_scorecard's diff — the count-aware findings comparison.

The failure mode this pins (found 2026-08-11, pinned at the code in commit
76af7a6): the old comparison was a set difference over "{code}:{severity}"
strings, so duplicates collapsed and a COUNT change on a code present in
both runs was invisible — fix #6.1 took photo/drone_render.png from 5
THREAD_MATCH_POOR findings to 6 and `diff` answered "no finding drift".
Worse than a missing feature, because the tool reads as a clean result.

These tests exercise the comparison helper directly with synthetic finding
lists, the same "{code}:{severity}" strings the baseline stores. Digitizing
the real corpus is `capture`'s job — minutes of pipeline work no unit test
should spend.
"""
from __future__ import annotations

from tools.corpus_scorecard import _finding_changes, _grade_fell, _GRADE_ORDER


def test_a_count_change_on_a_code_present_in_both_runs_is_drift():
    """The exact shape of the #6.1 miss: same code, same severity, one more
    of it. The set diff answered nothing; this must answer 5 -> 6."""
    old = ["THREAD_MATCH_POOR:warn"] * 5
    new = ["THREAD_MATCH_POOR:warn"] * 6

    appeared, resolved, counts, new_block = _finding_changes(old, new)

    assert appeared == []
    assert resolved == []
    assert counts == ["THREAD_MATCH_POOR:warn: x5 -> x6"]
    assert new_block is False


def test_codes_present_in_only_one_run_still_read_as_appeared_and_resolved():
    """The half the set diff already got right keeps its exact shape, so
    `diff`'s output stays backward compatible for set-level changes."""
    old = ["TRIM_HEAVY:warn", "DENSITY_EXTREME:warn"]
    new = ["TRIM_HEAVY:warn", "LETTERING_TOO_SMALL:warn"]

    appeared, resolved, counts, new_block = _finding_changes(old, new)

    assert appeared == ["LETTERING_TOO_SMALL:warn"]
    assert resolved == ["DENSITY_EXTREME:warn"]
    assert counts == []
    assert new_block is False


def test_one_more_instance_of_an_existing_block_code_hard_fails():
    """The hard-fail contract is "a block finding that was not there
    before", and the SECOND instance of a block code was not there before —
    exempting it would be the same blind spot at the exit-code level."""
    old = ["LINK_UNCOVERED:block"]
    new = ["LINK_UNCOVERED:block"] * 2

    appeared, _resolved, counts, new_block = _finding_changes(old, new)

    assert appeared == []
    assert counts == ["LINK_UNCOVERED:block: x1 -> x2"]
    assert new_block is True


def test_a_brand_new_block_code_hard_fails():
    """The original contract, unchanged by the count-aware fix."""
    appeared, _resolved, _counts, new_block = _finding_changes(
        [], ["DENSITY_STACKED:block"])

    assert appeared == ["DENSITY_STACKED:block"]
    assert new_block is True


def test_fewer_block_instances_is_not_a_hard_fail():
    """Losing a block instance is an improvement — reported as a count
    change, never as a regression."""
    _appeared, _resolved, counts, new_block = _finding_changes(
        ["DENSITY_STACKED:block"] * 2, ["DENSITY_STACKED:block"])

    assert counts == ["DENSITY_STACKED:block: x2 -> x1"]
    assert new_block is False


def test_identical_findings_report_nothing():
    result = _finding_changes(["THREAD_MATCH_POOR:warn"] * 3,
                              ["THREAD_MATCH_POOR:warn"] * 3)

    assert result == ([], [], [], False)


# --- the grade band that fell and exited 0 -----------------------------------
# Second silent-accept in the same tool, found by the 2026-09-12 gap audit
# (§4.1) and fixed 2026-09-14. `diff` has always PRINTED "grade: A -> B" and
# then returned 0, so the strongest single-number regression signal the
# scorecard produces could not fail anything. Measured instance: the
# 2026-09-11 edge-cap flip took `logo_script_tires` A 100 -> B 88 with corpus
# thread +9.10%, and every check stayed green.
#
# Same discipline as the count-aware tests above: the helper, synthetic
# grades, no pipeline.


def test_the_measured_regression_reads_as_a_fall():
    """The exact move that went unflagged: logo_script_tires, A -> B."""
    assert _grade_fell("A", "B") is True


def test_every_downward_band_step_reads_as_a_fall():
    """Not just A -> B — every adjacent step, plus a two-band skip, so a
    fall further down the scale cannot pass while the top of it fails."""
    for i, better in enumerate(_GRADE_ORDER):
        for worse in _GRADE_ORDER[i + 1:]:
            assert _grade_fell(better, worse) is True, f"{better} -> {worse}"


def test_an_improvement_and_an_unchanged_grade_are_not_failures():
    """The tool must not punish a change that made the corpus better, or
    fail on a row that did not move at all."""
    for i, worse in enumerate(_GRADE_ORDER):
        for better in _GRADE_ORDER[:i]:
            assert _grade_fell(worse, better) is False, f"{worse} -> {better}"
    for g in _GRADE_ORDER:
        assert _grade_fell(g, g) is False


def test_a_missing_grade_is_no_verdict_rather_than_the_worst_band():
    """`diff` rewrites a baseline row captured as an error to grade None
    before comparing. Treating None as an F would make RECOVERING from a
    captured error read as a regression, and treating a recovery as a fall
    is how a guard gets switched off."""
    assert _grade_fell(None, "F") is False
    assert _grade_fell("A", None) is False
    assert _grade_fell(None, None) is False
    assert _grade_fell("A", "Z") is False


# --- and the exit code itself, not just the helper ---------------------------
# The helper tests above would ALL still pass if someone deleted the
# `hard_fail = True` that acts on them, which is the same shape of hole this
# file was originally written about. These drive the real `diff()` and assert
# the process exit code, with `_score_one` stubbed so no pipeline runs.

import json as _json

from tools import corpus_scorecard as _cs


def _diff_with(monkeypatch, tmp_path, baseline_row, fresh_row):
    """Run the real diff() over exactly one fixture/config, both sides given."""
    fixture, cfg = "logo_script_tires.png", {"target_width_mm": 80.0,
                                             "garment_id": "left_chest"}
    key = _cs._run_key(fixture, cfg)
    baseline = tmp_path / "baseline.json"
    baseline.write_text(_json.dumps({key: baseline_row}), encoding="utf-8")

    monkeypatch.setattr(_cs, "OUT", baseline)
    monkeypatch.setattr(_cs, "FIXTURES", [fixture])
    monkeypatch.setattr(_cs, "MATRIX", [cfg])
    monkeypatch.setattr(_cs, "_score_one", lambda f, c: fresh_row)
    return _cs.diff()


def _row(score, grade):
    return {"score": score, "grade": grade, "findings": [], "metrics": {}}


def test_diff_exits_non_zero_when_a_grade_band_falls(monkeypatch, tmp_path):
    """The regression that shipped green: A 100 -> B 88 on logo_script_tires,
    printed by this very tool and then followed by exit 0."""
    assert _diff_with(monkeypatch, tmp_path, _row(100, "A"), _row(88, "B")) == 1


def test_diff_still_exits_zero_when_the_grade_improves(monkeypatch, tmp_path):
    """A guard that fails on good news gets turned off. It must not."""
    assert _diff_with(monkeypatch, tmp_path, _row(88, "B"), _row(100, "A")) == 0


def test_diff_exits_zero_on_a_score_move_inside_one_band(monkeypatch, tmp_path):
    """Still a REPORTING tool for everything below a band change -- a 100 -> 91
    drop prints and does not fail, exactly as before this guard existed."""
    assert _diff_with(monkeypatch, tmp_path, _row(100, "A"), _row(91, "A")) == 0
