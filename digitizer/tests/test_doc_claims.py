"""`tools/doc_claims.py` — the checker that reads the docs, checked itself.

It shipped 2026-09-06 with no tests, and the entry announcing it published two
numbers (*"11 flag defaults and 16 constants"*) that its own output does not
produce — they came from a side probe. So the two things pinned here are:

  1. every claim it CANNOT settle is reported, never silently skipped, because
     a flag that was skipped and a flag that passed look identical otherwise;
  2. the counts it prints are the counts it means — checks, and the distinct
     names those checks covered, which are different numbers.

Cheap by construction: the checker reads text and a dataclass, so nothing here
digitizes anything.
"""

import dataclasses

import pytest

from digitizer_core.config import PipelineConfig
from tools import doc_claims


def _bool_flag(want: bool) -> str:
    """A real `PipelineConfig` field whose default is `want`, so the tests
    below assert against the shipped dataclass rather than a name that could
    be renamed out from under them."""
    for f in dataclasses.fields(PipelineConfig):
        if isinstance(f.default, bool) and f.default is want:
            return f.name
    pytest.skip(f"no bool field defaults to {want}")


def test_an_agreement_counts_as_one_check():
    off = _bool_flag(False)
    problems, agreed, cannot, seen = doc_claims.check_defaults(
        f"- `cfg.{off}` — DEFAULT OFF, measured.", "T.md")
    assert (problems, agreed, cannot) == ([], 1, [])
    assert seen == {off}


def test_a_disagreement_is_reported():
    on = _bool_flag(True)
    problems, agreed, cannot, _ = doc_claims.check_defaults(
        f"- `cfg.{on}` — DEFAULT OFF.", "T.md")
    assert agreed == 0 and cannot == []
    assert len(problems) == 1 and on in problems[0]


def _factory_field() -> str:
    """A real field with `default_factory` and no plain default. Five exist
    (`deleted_shape_ids`, `shape_overrides`, `merge_shape_ids`,
    `split_shapes`, `extra`); picked from the dataclass so the test does not
    pin a name that may be renamed."""
    for f in dataclasses.fields(PipelineConfig):
        if f.default is dataclasses.MISSING:
            return f.name
    pytest.skip("no default_factory field to exercise")


# The FOUR ways a default claim can fail to be checkable — all four, because
# each was a bare `continue` before 2026-09-06 and the flag came out of a
# clean run looking verified.
@pytest.mark.parametrize("kind,needle", [
    ("missing", "names no PipelineConfig field"),
    ("factory", "no plain default"),
    ("tristate", "not a bool"),
    ("both", "stating both"),
])
def test_every_unsettleable_claim_is_reported(kind, needle):
    line = {
        "missing": "- `cfg.no_such_flag_anywhere` — DEFAULT ON.",
        "factory": f"- `cfg.{_factory_field()}` — DEFAULT ON.",
        "tristate": "- `cfg.edge_cap` — DEFAULT ON.",
        "both": f"- `cfg.{_bool_flag(False)}` — DEFAULT ON and DEFAULT OFF.",
    }[kind]
    problems, agreed, cannot, seen = doc_claims.check_defaults(line, "T.md")
    assert problems == [] and agreed == 0
    assert len(cannot) == 1 and needle in cannot[0], cannot
    assert seen, "the flag must still count as TOUCHED, not vanish"


def test_a_line_with_no_default_phrase_is_not_a_claim():
    """Only lines that actually assert a default are claims — a flag merely
    mentioned must not be counted as checked, or the coverage number inflates
    with every prose reference."""
    off = _bool_flag(False)
    problems, agreed, cannot, seen = doc_claims.check_defaults(
        f"`cfg.{off}` is discussed at length here.", "T.md")
    assert (problems, agreed, cannot, seen) == ([], 0, [], set())


def test_the_tri_state_flag_is_named_in_its_own_report():
    """`edge_cap` is the live instance: MASTER_SCOPE puts it on a DEFAULT line
    and its default is the string 'none'. The report must say which flag it
    could not settle, not just that something was skipped."""
    _p, _a, cannot, _s = doc_claims.check_defaults(
        "- `cfg.edge_cap` — DEFAULT ON.", "T.md")
    assert cannot and "cfg.edge_cap" in cannot[0]


def test_constant_checks_and_distinct_names_are_different_numbers():
    """`FILL_ROW_MM` is defined in TWO modules, so one documented claim is two
    checks. Reporting only the larger number as "constants" is what made the
    published 16 unreproducible."""
    mods = doc_claims._modules()
    problems, agreed, seen = doc_claims.check_constants(
        "`FILL_ROW_MM = 0.15` shipped.", "T.md", mods)
    assert problems == []
    assert seen == {"FILL_ROW_MM"}
    assert agreed == 2, f"expected one claim to be two checks, got {agreed}"


def test_scientific_notation_is_read_as_a_number():
    """A first pass read `SPLIT_TOLERANCE_MM = 1e-6` as 1 and reported a
    mismatch that was the regex, not the doc."""
    mods = doc_claims._modules()
    hits = doc_claims._CONST.findall("`SPLIT_TOLERANCE_MM = 1e-6`")
    assert hits == [("SPLIT_TOLERANCE_MM", "1e-6")]
    problems, _agreed, _seen = doc_claims.check_constants(
        "`SPLIT_TOLERANCE_MM = 1e-6`", "T.md", mods)
    assert problems == [], problems


def test_the_shipped_current_state_docs_still_agree():
    """The regression guard that makes the tool protective rather than
    decorative: MASTER_SCOPE and DOCTRINE must not disagree with the code.
    `docs/scope/*` is deliberately NOT included — a dated snapshot there is
    legitimate under that file's own header."""
    mods = doc_claims._modules()
    problems = []
    for doc in doc_claims.STRICT:
        path = doc_claims.ROOT / doc
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        problems += doc_claims.check_defaults(text, doc)[0]
        problems += doc_claims.check_constants(text, doc, mods)[0]
    assert problems == [], problems
