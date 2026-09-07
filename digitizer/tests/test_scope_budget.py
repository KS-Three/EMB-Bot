"""MASTER_SCOPE.md states an 800-line budget. Nothing enforced it.

The rule is the document's own, in its own words — *"Current state ONLY,
under an 800-line budget"* — with per-area detail in `docs/scope/` and dated
snapshots in `docs/scope-history.md` as the two places overflow is supposed
to go. On 2026-09-07 the file reached **799**, one line of headroom, and the
only reason anybody noticed is that the next entry did not fit.

**A budget nothing checks is a preference.** This is the check, and its
failure message names where the reclaim is, because a test that says "too
long" and stops just gets the next line squeezed in somewhere else.

The reclaim is NOT a defect. Measured (`tools/scope_budget.py`): live defects
are 138 lines of 799 — 17%, over 30 numbered entries — while the capability
areas take 255 and area 1 alone takes 107 against a `docs/scope/` detail file
of 3,871. And retiring a numbered defect reclaims nothing anyway: the Closed
section keeps every number *"because ten other docs cite them by number"*, so
moving Live → Closed swaps a line for a line.
"""
from __future__ import annotations

import re

import pytest

from tools.scope_budget import (BUDGET, SCOPE, areas, line_count,
                                live_and_closed, sections)


@pytest.fixture(scope="module")
def text() -> str:
    return SCOPE.read_text(encoding="utf-8")


def test_the_counter_agrees_with_wc_l(text):
    """`wc -l` is what the budget has always meant.

    `split("\\n")` on a trailing-newline file returns one extra empty element,
    and the first cut of `scope_budget.py` reported 800 for a file `wc -l`
    calls 799 — an instrument off by one against the number it exists to
    enforce, which would have failed the budget below a line early.
    """
    assert line_count("a\nb\n") == 2
    assert line_count("a\nb") == 2
    assert line_count("") == 0
    assert line_count(text) == text.count("\n") + (0 if text.endswith("\n") else 1)


def test_master_scope_is_within_its_own_budget(text):
    n = line_count(text)
    if n <= BUDGET:
        return
    biggest = sorted(sections(text), key=lambda r: -r[1])[:3]
    worst = max(areas(text), key=lambda r: r[1], default=("", 0, 0))
    pytest.fail(
        f"MASTER_SCOPE.md is {n} lines against its own {BUDGET}-line budget.\n"
        f"Biggest sections: "
        + ", ".join(f"{name} {ln}" for name, ln in biggest) + ".\n"
        f"The reclaim is capability area '{worst[0]}' — {worst[1]} lines here "
        f"against {worst[2]} in its own docs/scope/ detail file, which is the "
        f"offload mechanism this document already documents.\n"
        f"Retiring a numbered defect reclaims NOTHING: the Closed section "
        f"keeps every number, so Live -> Closed swaps a line for a line.")


def test_the_section_parser_is_not_vacuous(text):
    """The budget test above passes trivially if the file cannot be read, and
    its failure message is only useful if the parsers work. Pin both."""
    names = {n for n, _ in sections(text)}
    assert len(names) >= 6, sorted(names)
    assert any(n.startswith("Live defects") for n in names), sorted(names)
    assert any(n.startswith("Capability areas") for n in names), sorted(names)

    rows = areas(text)
    assert len(rows) == 5, [r[0] for r in rows]
    # Every area must resolve to a real detail file, or the "reclaim" column
    # silently reads 0 and the failure message points nowhere.
    assert all(detail > 0 for _n, _h, detail in rows), rows
    assert sum(h for _n, h, _d in rows) < line_count(text)


def test_every_live_defect_carries_a_dated_pointer(text):
    """CLAUDE.md's rule for this file, in its own words: *"Every claim carries
    a `(verb date — source)` pointer; one without a pointer is unverified."*

    Nothing checked it. An entry can enter the dashboard sourceless and read
    exactly like a measured one — which is the whole failure the rule exists
    to prevent, and it is silent.

    Measured clean at the time of writing: **18 of 18**.
    """
    live, _closed = live_and_closed(text)
    bad = [f"defect {n} (line {i + 1})" for n, i, body in live
           if not re.search(r"\*\([^)]*\d{4}-\d{2}-\d{2}[^)]*\)\*", body)]
    assert not bad, (
        "live defect entries with no `*(verb date — source)*` pointer, which "
        "CLAUDE.md calls unverified: " + ", ".join(bad))


def test_closed_pointers_still_say_when(text):
    """The closed entries are pointers by design and take a date INLINE
    ("RESOLVED 2026-08-19") rather than the italic tail. Different rule, same
    purpose — and asserting the right one per section is the point of the
    split, see below."""
    _live, closed = live_and_closed(text)
    bad = [f"{n} (line {i + 1})" for n, i, body in closed
           if not re.search(r"\d{4}-\d{2}-\d{2}", body)]
    assert not bad, "closed pointers with no date at all: " + ", ".join(bad)


def test_the_entry_split_is_the_load_bearing_part(text):
    """`### Closed` is an H3 INSIDE the Live defects H2.

    A first cut of this sliced on the H2 alone and reported **twelve**
    pointer-rule violations — every one a closed pointer behaving exactly as
    documented. Read the matches, not the count. Pinning both counts keeps a
    future refactor of the parser from quietly merging the two populations
    and re-introducing that.
    """
    live, closed = live_and_closed(text)
    assert len(live) >= 15, [n for n, _i, _b in live]
    assert len(closed) >= 10, [n for n, _i, _b in closed]
    assert not ({n for n, _i, _b in live} & {n for n, _i, _b in closed})
