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
#: points the reader at `rembg_isolated/README.md` in a message. They carry no
#: exposure, and listing them is what lets the sweep below stay exhaustive.
NAMES_ONLY = {"acceptance_ab"}


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
                     if "utf8_console" not in (TOOLS / f"{name}.py").read_text(
                         encoding="utf-8"))
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


def _printed_literals(path: pathlib.Path):
    """Every character a `print(...)` in `path` writes from a literal.

    f-strings included: `ast.walk` reaches a `JoinedStr`'s literal parts, which
    is where the headers live — `f"... worst mean→median ΔE00 |"`.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "print"):
            for part in ast.walk(node):
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
    """
    offenders = []
    for path in sorted(TOOLS.rglob("*.py")):
        hazard = sorted({ch for ch in _printed_literals(path)
                         if not _fits_cp1252(ch)})
        if hazard and "utf8_console" not in path.read_text(encoding="utf-8"):
            offenders.append(f"{path.name} prints {''.join(hazard)!r}")
    assert not offenders, (
        "tools that print a character cp1252 cannot encode and never widen "
        "stdout — they crash on a stock Windows console the moment that line "
        "is reached: " + "; ".join(offenders))
