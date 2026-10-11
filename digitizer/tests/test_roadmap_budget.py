"""ROADMAP.md states its own budget: *"Budget: 60 lines. Over it, cut or move
-- never grow."* This enforces it.

Nothing did. The file was 60 lines when the rule was written and 80 on
2026-10-03, and every line past the budget was history a gate had collected:
how the DST axis left gate 1, when tonal splitting left gate 3, what the
Studio's class override did one evening -- all of it already in DOCTRINE.md.
The file's other rule is *"no numbers, no dates, no status, ever"*, so the
overflow broke both at once.

It matters more here than a long doc usually does: a SessionStart hook
(`.claude/hooks/roadmap-gates.js`) lifts two of this file's sections into
every session, so a line under "Hard gates" is paid for at every start.

The budget is read from the file's own sentence, so the rule and the check
cannot drift apart: change the number there and this follows it.
MASTER_SCOPE's budget has had the same kind of check since 2026-09-07
(`test_scope_budget.py`) -- a budget nothing checks is a preference.
"""
from __future__ import annotations

import re

from tools.scope_budget import SCOPE, line_count

ROADMAP = SCOPE.parent / "ROADMAP.md"
BUDGET_SENTENCE = re.compile(r"Budget: (\d+) lines")


def _text() -> str:
    return ROADMAP.read_text(encoding="utf-8")


def test_the_roadmap_still_states_its_line_budget():
    assert BUDGET_SENTENCE.search(_text()), (
        "ROADMAP.md no longer says 'Budget: N lines'. The check below reads its "
        "number from that sentence; restore it or re-point this test.")


def test_the_roadmap_is_within_its_own_budget():
    text = _text()
    budget = int(BUDGET_SENTENCE.search(text).group(1))
    n = line_count(text)
    assert n <= budget, (
        f"ROADMAP.md is {n} lines against its own budget of {budget}. Its rule "
        "is 'cut or move -- never grow': dates, numbers and how a gate was "
        "settled belong in DOCTRINE.md or docs/scope-history.md, and a gate "
        "keeps the refusal and its blocker.")


def test_the_sections_the_session_hook_lifts_are_still_there():
    """`roadmap-gates.js` finds these by heading and a rename fails SILENT:
    the session simply starts without its gates."""
    text = _text()
    for heading in ("## Where we are", "## Hard gates"):
        assert re.search(rf"^{re.escape(heading)}", text, re.M), heading
