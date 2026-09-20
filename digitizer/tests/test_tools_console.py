"""The doc-reading tools print text they did not write, to a console that
cannot always carry it.

`tools/scope_budget.py` crashed on Kent's Windows box with

    UnicodeEncodeError: 'charmap' codec can't encode character '\u2192'

**after printing most of its output** — the per-section table went out, then
`main()` died on the capability-area table, because one area name is
`"1. Auto-digitizing quality (image \u2192 stitches)"`, read straight out of
MASTER_SCOPE.md's own heading.

Three tools in `tools/` read a Markdown doc at runtime and print strings taken
from it: `scope_budget`, `memory_budget`, `doc_claims`. Only `scope_budget`
crashes *today*, and only because of which characters happen to sit in the
text the other two print — MASTER_SCOPE.md and the `docs/scope/` files are
full of arrows, so the other two are one doc edit away from the same stack
trace. **That is why this is fixed at the stream and not by scrubbing one
heading.**

The characters are NOT interchangeable, which is what makes this easy to
misread: cp1252 HAS an em-dash (0x97) and HAS `\u00d7` (0xd7), so most of this
project's punctuation survives a legacy console and only a handful of
characters kill it. A tool can print doc text for months and look safe.
"""
from __future__ import annotations

import ast
import io
import pathlib

from tools._console import utf8_console

TOOLS = pathlib.Path(__file__).resolve().parents[1] / "tools"

#: Tools that read a Markdown doc at runtime and print strings out of it.
DOC_READERS = {"scope_budget", "memory_budget", "doc_claims"}

#: Tools that NAME a `.md` path without ever reading one — `acceptance_ab`
#: points the reader at `rembg_isolated/README.md` in a message, and
#: `sewout_walk_reach` WRITES one beside the sew-out files it exports. Neither
#: reads doc text, so neither is exposed through a doc; listing them is what
#: lets the sweep below stay exhaustive. (`sewout_walk_reach` widens its
#: stdout all the same — its own sheet prints arrows, which is the OTHER
#: exposure, swept separately below.)
NAMES_ONLY = {"acceptance_ab", "sewout_walk_reach"}


def cp1252_stream() -> tuple[io.BytesIO, io.TextIOWrapper]:
    """A stdout that behaves exactly like the one that crashed.

    `errors="strict"` is the point — it is the default for a text layer, and
    the reason the traceback was a crash rather than a smudge.
    """
    raw = io.BytesIO()
    return raw, io.TextIOWrapper(raw, encoding="cp1252",
                                 errors="strict", newline="")


def test_the_arrow_reaches_a_cp1252_stdout_instead_of_raising():
    raw, stream = cp1252_stream()
    utf8_console(stream)
    stream.write("image \u2192 stitches\n")
    stream.flush()
    assert raw.getvalue().decode("utf-8") == "image \u2192 stitches\n", (
        "the widened stream did not carry U+2192 through as UTF-8")


def test_it_leaves_a_stream_it_cannot_widen_alone():
    """pytest's own capture, a mock, a `sys.stdout` someone replaced — anything
    without `reconfigure` must be a no-op, not an AttributeError at startup."""
    class Bare:
        def write(self, s):
            return len(s)

    utf8_console(Bare())            # must not raise


def test_it_never_raises_on_a_stream_that_refuses_reconfigure():
    """A detached or already-closed stream must not turn a diagnostic tool
    into a traceback before it has printed anything at all."""
    class Hostile:
        encoding = "cp1252"

        def reconfigure(self, **kw):
            raise OSError("detached")

    utf8_console(Hostile())         # must not raise


def test_every_doc_reading_tool_widens_its_stdout():
    """The structural half. `scope_budget` is the one that crashed, but the
    fix is only worth anything if its two siblings carry it too."""
    missing = sorted(name for name in DOC_READERS
                     if not _calls_utf8_console(TOOLS / f"{name}.py"))
    assert not missing, (
        "doc-reading tools that never widen stdout, so a U+2192 in the doc "
        "they print will crash them on a cp1252 console: " + ", ".join(missing))


def _docstring_ids(tree: ast.AST) -> set[int]:
    """The `id()` of every docstring Constant in `tree`.

    Needed because most of `tools/` cites a doc by name in its own prose, and
    counting those would bury the four real hits under dozens of mentions.
    """
    holders = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
    out = set()
    for node in ast.walk(tree):
        if not isinstance(node, holders):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr):
            first = body[0].value
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                out.add(id(first))
    return out


def test_the_doc_reader_list_has_not_gone_stale():
    """`DOC_READERS` is hand-kept, and the tree can be asked directly. Ask it,
    so a doc-reading tool added later cannot quietly sit outside the fix."""
    found = set()
    for path in sorted(TOOLS.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
        prose = _docstring_ids(tree)
        if any(isinstance(n, ast.Constant) and isinstance(n.value, str)
               and n.value.endswith(".md") and id(n) not in prose
               for n in ast.walk(tree)):
            found.add(path.stem)

    assert found <= DOC_READERS | NAMES_ONLY, (
        "a tool names a Markdown doc in code and is in neither DOC_READERS "
        "nor NAMES_ONLY: " + ", ".join(sorted(found - DOC_READERS - NAMES_ONLY)))
    assert DOC_READERS <= found, (
        "DOC_READERS names a tool that no longer reads a doc: "
        + ", ".join(sorted(DOC_READERS - found)))


def _fits_cp1252(ch: str) -> bool:
    try:
        ch.encode("cp1252")
    except UnicodeEncodeError:
        return False
    return True


def _calls_utf8_console(path: pathlib.Path) -> bool:
    """Does `path` actually CALL `utf8_console`, not merely mention it?

    The text check this replaces (`"utf8_console" not in source`) is satisfied
    by the import line alone. Measured 2026-09-20: deleting the call from
    `refused_walks` and leaving its import kept the sweep green, so a tool
    could import the fix, never wire it, and still pass the test that exists
    to catch exactly that. An import is not a widened stream.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    return any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
               and n.func.id == "utf8_console" for n in ast.walk(tree))


def _printed_literals(path: pathlib.Path):
    """Every character a `print(...)` in `path` writes from a literal.

    f-strings included: `ast.walk` reaches a `JoinedStr`'s literal parts, which
    is where the headers live — `f"... worst mean→median ΔE00 |"`.

    **A printed helper counts too** (added 2026-09-20). Reading only the
    literals *inside* the `print(...)` call missed the commonest shape in
    `tools/`: build the table in a function, print what it returns. Both
    `refused_walks` and `sewout_walk_reach` were written that way and both
    print `→` — the sweep called them clean, and only the doc-name guard
    above caught one of them, by a different route. So a `print(NAME(...))`
    whose `NAME` is a function defined in the same module also yields that
    function's literals. One level, which is the shape that occurs; a helper
    that calls a second helper is still out of reach and is why this is a
    tripwire rather than a proof.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    helpers = {n.name: n for n in ast.walk(tree)
               if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            reach = [node]
            for arg in node.args:
                inner = arg.func.id if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name) else None
                if inner in helpers:
                    reach.append(helpers[inner])
            for root in reach:
                for part in ast.walk(root):
                    if isinstance(part, ast.Constant) and isinstance(part.value, str):
                        yield from part.value


def test_no_tool_prints_a_literal_its_console_cannot_take():
    """The second exposure, and it is NOT the doc-readers.

    A tool can hard-code the hazard in its own table header. Swept
    2026-09-19: `region_colour` prints `worst mean→median ΔE00` and
    `trim_exchange_sweep` prints `Δtrim` / `Δstitch` — both in the
    header line, so both died on their FIRST line of output, before any work
    was shown. Nothing else in `tools/` printed a literal outside cp1252.

    The sweep that found them crashed on its own report, printing `Δ` to
    the same cp1252 stdout. That is how ordinary this is.

    This is the tripwire, not the sweep's result: a header written months from
    now with an arrow or a sigma in it fails here instead of on Kent's box.

    Re-swept 2026-09-20 after `_printed_literals` learned to follow a printed
    helper: `refused_walks` and `sewout_walk_reach` both print `→` from a
    table built in a function, and both now widen stdout.
    """
    offenders = []
    for path in sorted(TOOLS.rglob("*.py")):
        hazard = sorted({ch for ch in _printed_literals(path)
                         if not _fits_cp1252(ch)})
        if hazard and not _calls_utf8_console(path):
            offenders.append(f"{path.name} prints {''.join(hazard)!r}")
    assert not offenders, (
        "tools that print a character cp1252 cannot encode and never widen "
        "stdout — they crash on a stock Windows console the moment that line "
        "is reached: " + "; ".join(offenders))
