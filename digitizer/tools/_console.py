#!/usr/bin/env python
r"""Let a tool print the characters the docs it reads are written in.

`tools/scope_budget.py` reads MASTER_SCOPE.md and prints its headings back.
One of them is *"1. Auto-digitizing quality (image -> stitches)"* with a real
U+2192 RIGHT ARROW, and on Kent's Windows box the tool printed its per-section
table and then died::

    UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'

**Where that cp1252 comes from is the whole design of this module**, and it is
not the console. Measured on Kent's machine 2026-09-19:

- `PYTHONLEGACYWINDOWSSTDIO`, `PYTHONUTF8` and `PYTHONIOENCODING` are unset in
  both the User and Machine environments.
- The system ANSI code page (`HKLM\...\Nls\CodePage\ACP`) is **1252**.

Without `PYTHONLEGACYWINDOWSSTDIO`, Python has written console output as UTF-8
through `WriteConsoleW` since 3.6 (PEP 528) — so a tool typed at a real console
never hit this. The locale encoding only applies when stdout is **redirected**:
a pipe, a file, or a harness capturing the output, which is how these tools are
usually run here. That is also why the em-dashes in the same report arrive as
mojibake in a captured run today: cp1252 *has* an em-dash (0x97) and the
capturing side decodes as UTF-8, so every one of them is already wrong and only
the arrow is loud enough to crash.

So the fix is to emit UTF-8: a no-op at a real console, correct down a pipe,
and it repairs the em-dashes on the way past. `errors="replace"` is the belt —
a stream that cannot be widened at all degrades to `?` rather than taking a
diagnostic tool down before it has printed anything.

**Do not solve this by scrubbing the heading.** Three tools here print text
they did not write (`scope_budget`, `memory_budget`, `doc_claims`); the docs
they read are full of arrows; and the next non-cp1252 character to arrive in
MASTER_SCOPE.md would start this over. Fix the stream, once.

Not every character is a hazard, which is what makes this easy to misread:
cp1252 carries em-dash, `\u00d7`, `\u00b0` and the curly quotes this project
is full of. Arrows, `\u2265`, `\u2248` and the check marks do not fit.
"""
from __future__ import annotations

import sys
from typing import Any

#: Raised by a stream that has no `reconfigure`, has been detached, or refuses
#: the call. None of them is worth a traceback in a diagnostic tool.
_REFUSED = (AttributeError, OSError, ValueError)


def utf8_console(*streams: Any) -> None:
    """Widen `streams` to UTF-8 in place; stdout and stderr by default.

    Call it first thing in `main()`, not at import: these tools import each
    other, and a module that rewires the interpreter's streams on import would
    reach whoever imported it.
    """
    for stream in streams or (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except _REFUSED:
            try:                          # cannot change the codec; at least
                stream.reconfigure(errors="replace")   # stop it from raising
            except _REFUSED:
                pass
