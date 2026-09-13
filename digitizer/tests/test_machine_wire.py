"""Physical constants that exist in BOTH engines must hold the same number.

`test_fabric_wire.py` is the sibling of this file and states the lesson:
corpus law 26 landed in Python and never in `src/fabrics.js`, so for a month
the browser ran an extra crosshatch pass under every knit fill on three of the
ten garments. The table was a by-hand port across a language boundary and
nothing checked it.

The same shape exists one level down, in the individual machine constants.
`digitizer_core/machine.py` and `src/satinfont.js` / `digitize.js` /
`satinplay.js` / `render.js` each declare their own copy of the satin spacing,
the bean pitch, the fill row, the split segment and the rest. Measured
2026-09-13: **19 constant names are declared in more than one file**, 17 agree
and 2 differ on purpose. Nothing tested any of it — the agreement was held by
hand and by comment.

The scan counts EVERY declaration, not one per language, because the first cut
of this file took "first declaration wins" and a mutation test walked straight
through it: `FILL_ROW_MM` is declared THREE times (`src/digitize.js`,
`src/satinfont.js`, `machine.py`), so drifting the `satinfont.js` copy changed
nothing the test could see. Duplication here is not only across the language
boundary — it is inside `src/` too.

This file does not decide any number. Gate 1 owns those: a value here moves
when fabric says so, and this test only asserts that when it moves, it moves in
both places. That is the same scope `test_fabric_wire.py` set for itself.

## The deliberate divergence, and why it is pinned rather than fixed

`SATIN_MAX_WIDTH_MM` is 3.0 in the browser and 5.0 in Python, and BOTH sides
say so in their own comments. `machine.py`: *"the browser engine still
classifies at 3.0 (satinMaxWidthMm) — divergence is deliberate, corpus-driven,
and Python-side only until its own sew-out."* `satinfont.js` cites that back
and adds *"this lane keeps 3.0 and the sew-out owns the merge."*

So it is pinned in `DELIBERATE_DIVERGENCE` below, which records a decision
rather than granting an exemption: the test asserts the pair is STILL
divergent, so when the sew-out merges them the entry goes stale loudly instead
of quietly protecting a stale number. Same rule the Reserved-Font-Name guard in
`test/font-license.test.js` uses, and the same rule as `test_fabric_wire.py`'s
non-vacuity checks.
"""

from __future__ import annotations

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
JS_DIR = REPO / "src"
PY_DIR = REPO / "digitizer" / "digitizer_core"

# name -> why the two engines hold different numbers on purpose. An entry is a
# RECORD of a decision, not a licence to drift: the test below fails if the
# pair stops diverging, which is the signal to delete the entry.
DELIBERATE_DIVERGENCE = {
    "MAX_DELTA": (
        "dst.js 121 vs exp.js 127. NOT drift and not the same quantity: these are "
        "two formats' real per-axis record limits (DST carries +/-121 units, EXP "
        "+/-127). A name collision between file-format constants, which is why it is "
        "recorded here rather than reconciled — reconciling them would corrupt one "
        "encoder."
    ),
    "SATIN_MAX_WIDTH_MM": (
        "browser 3.0 vs Python 5.0. machine.py: 'divergence is deliberate, "
        "corpus-driven, and Python-side only until its own sew-out'; "
        "satinfont.js: 'this lane keeps 3.0 and the sew-out owns the merge'. "
        "Gate 1 owns the merge. DOCTRINE also warns separately against raising "
        "the Python side to 7.0 (both coherent routes break)."
    ),
}

# `const NAME = 1.23;` / `const NAME = 3,` at any indent. Numeric literals only:
# a string or an object is not a physical constant and its own module owns it.
_JS_CONST = re.compile(r"\b(?:const|let|var)\s+([A-Z][A-Z0-9_]{3,})\s*=\s*(-?\d+(?:\.\d+)?)\s*[;,\n]")
# Module-level `NAME = 1.23` or `NAME: float = 1.23`. Anchored to column 0 so a
# local inside a function never counts.
_PY_CONST = re.compile(r"^([A-Z][A-Z0-9_]{3,})\s*(?::[^=\n]+)?=\s*(-?\d+(?:\.\d+)?)\s*$", re.M)


def _scan(directory: pathlib.Path, suffixes: tuple[str, ...], pattern: re.Pattern) -> dict[str, list[tuple[float, str]]]:
    """EVERY declaration, one entry per (name, file).

    Not "first wins": that is what let a drifted third copy of FILL_ROW_MM pass.
    Deduped per file so a module that redeclares its own constant does not look
    like two engines disagreeing with each other.
    """
    out: dict[str, list[tuple[float, str]]] = {}
    for path in sorted(directory.rglob("*")):
        if path.suffix not in suffixes or not path.is_file():
            continue
        rel = str(path.relative_to(REPO))
        seen_here: set[str] = set()
        text = path.read_text(encoding="utf-8", errors="replace")
        for match in pattern.finditer(text):
            name, raw = match.group(1), match.group(2)
            if name in seen_here:
                continue
            seen_here.add(name)
            out.setdefault(name, []).append((float(raw), rel))
    return out


def _all_declarations() -> dict[str, list[tuple[float, str]]]:
    merged = _scan(JS_DIR, (".js", ".mjs"), _JS_CONST)
    for name, entries in _scan(PY_DIR, (".py",), _PY_CONST).items():
        merged.setdefault(name, []).extend(entries)
    return merged


def _shared() -> dict[str, list[tuple[float, str]]]:
    """Only names that exist in more than one FILE — one copy cannot drift."""
    return {n: v for n, v in sorted(_all_declarations().items()) if len(v) > 1}


def test_the_scanners_are_not_vacuous():
    """Every assertion below walks a dict. An empty dict passes them all.

    Measured 2026-09-13: 19 names with more than one declaration, from a JS side
    of ~40 and a Python side of ~200. A collapse to zero means a regex broke or a
    file moved, not that the copies came into perfect agreement.
    """
    js = _scan(JS_DIR, (".js", ".mjs"), _JS_CONST)
    py = _scan(PY_DIR, (".py",), _PY_CONST)
    assert len(js) >= 20, f"only {len(js)} JS constants found — the JS scanner broke"
    assert len(py) >= 50, f"only {len(py)} Python constants found — the Python scanner broke"
    shared = _shared()
    assert len(shared) >= 18, (
        f"only {len(shared)} constants are declared in more than one file (measured 19 on "
        f"2026-09-13) — a scanner broke, or a shared constant was renamed on one side "
        f"only, which is itself the drift this file exists to catch"
    )
    # The named pairs this was built on must still be among them.
    for expected in ("SATIN_SPACING_MM", "FILL_ROW_MM", "BEAN_STITCH_MM", "SATIN_MAX_WIDTH_MM", "MAX_DELTA"):
        assert expected in shared, f"{expected} is no longer seen in more than one file — renamed, or the scanner missed it"
    # FILL_ROW_MM is the one that caught the first cut of this test out. If it
    # ever reads as fewer than three copies, the scan has narrowed again.
    assert len(shared["FILL_ROW_MM"]) >= 3, (
        f"FILL_ROW_MM reads {len(shared['FILL_ROW_MM'])} copies (measured 3 on 2026-09-13: "
        f"digitize.js, satinfont.js, machine.py) — the scan is missing declarations again"
    )


def test_every_shared_constant_holds_the_same_number_in_both_engines():
    """The whole point. A value moves in both places or it does not move."""
    mismatches = []
    for name, entries in _shared().items():
        if name in DELIBERATE_DIVERGENCE:
            continue
        values = {v for v, _ in entries}
        if len(values) > 1:
            where = ", ".join(f"{v} in {f}" for v, f in entries)
            mismatches.append(f"{name}: {where}")
    assert not mismatches, (
        "these constants are declared in more than one place and disagree, so the copies "
        "sew the same design differently:\n  " + "\n  ".join(mismatches) +
        "\n\nMove the number in BOTH places, or — if the divergence is intended and a "
        "sew-out owns the merge — add it to DELIBERATE_DIVERGENCE with the reason, the "
        "way SATIN_MAX_WIDTH_MM is."
    )


def test_each_recorded_divergence_is_still_divergent():
    """A pin that has silently come true is worse than no pin.

    When the sew-out merges SATIN_MAX_WIDTH_MM, this fails and tells you to
    delete the entry, rather than sitting there exempting a constant that no
    longer needs exempting.
    """
    shared = _shared()
    for name, why in DELIBERATE_DIVERGENCE.items():
        assert name in shared, (
            f"{name} is recorded as a deliberate divergence but is no longer declared in "
            f"more than one file — if it was removed or renamed, delete its entry."
        )
        entries = shared[name]
        where = ", ".join(f"{v} in {f}" for v, f in entries)
        assert len({v for v, _ in entries}) > 1, (
            f"{name} now agrees everywhere ({where}), but DELIBERATE_DIVERGENCE still "
            f"records it as split: {why}\n\nIf the sew-out settled it, delete the entry — "
            f"the constant is then covered by the agreement test like every other."
        )
