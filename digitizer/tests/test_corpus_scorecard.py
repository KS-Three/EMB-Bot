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

from tools.corpus_scorecard import _finding_changes


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
