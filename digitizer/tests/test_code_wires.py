"""Every warning/finding code the Studio switches on must still exist.

The UI-switches-on-codes-never-prose contract (`warnings_codes.py`'s own
header) has one cost nobody had priced: **the Studio names those codes as
bare string literals**, so a rename in Python is a silent feature deletion in
the browser. Nothing imports, nothing type-checks, nothing fails.

By-string is the right convention and stays. `preflight.py` states its reason
outright -- named by string "so preflight neither imports it nor breaks in a
tree where that lane has not landed" -- and the Studio has no way to import a
Python constant at all. What was missing is the tripwire, which is this file.

## The crossings, and what each one loses in silence

Measured 2026-09-07 -- **34 distinct code strings cross a module boundary as
a literal, over six sites (four of them parseable as one shape), and every one
is live**. None was guarded before this file.

| site | codes | owner | what a rename deletes |
|---|---|---|---|
| `digitizer.js` `WARNING_TEXT` | 28 | `warnings_codes` | the translation. The panel falls back to the engine's own build-status prose -- the exact thing Kent's 2026-08-30 note ("IDK what ANY of that even means") was about |
| `DigitizePanel` flat-art nudge | 4 `CLASSIFIED_*` | `warnings_codes` | the nudge never appears again |
| `DigitizePanel` `otherWarningLines` | `BACKGROUND_ENCLOSED` | `warnings_codes` | its dedicated banner duplicates into the plain list |
| `DigitizePanel` merge/split notes | 2 `*_BY_USER` | `warnings_codes` | the review-screen note vanishes |
| `DigitizePanel` `FIX_FOR` + trim panel | 4 | `preflight` | the one-press fix button stops being offered |
| `preflight.py` 4 mirrored constants | 5 | `warnings_codes` | `_tonal_fill_technique` reads "tatami" for a tonal plan, so `_density_findings` scores a BAND-intending design against a single number; the face and contour guards just go quiet |

**The contrast that makes the case is one module over.**
`stage7_sequence.py` consumes the same codes by IMPORT, and deleting one from
`warnings_codes.py` stops the whole package loading with a named ImportError
before any test runs (verified while proving these assertions can fail). The
by-string consumers are the ones that survive the same edit, keep rendering,
and quietly lose a feature.

**This is the catchable class.** The day's four documentation defects each
defeated a checker on structure (see `.claude/memory/instruments-that-
underreport-2026-09-06.md`, part two: a truthful substring, a value in a
different form, a constant named nowhere). This one is a set-membership
question with both sets machine-readable, which is why it gets a test and
those got a reader.
"""
from __future__ import annotations

import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
STUDIO = REPO / "app" / "src"
DIGITIZER_JS = STUDIO / "lib" / "digitizer.js"
PANEL = STUDIO / "ui" / "DigitizePanel.svelte"
WARNINGS_CODES = REPO / "digitizer" / "digitizer_core" / "warnings_codes.py"

# Deliberately NOT guarded by a `skipif(not PANEL.is_file())`, unlike
# `test_charts.py`'s browser-bundle check. A missing Studio means the seam
# cannot be checked, and the honest outcome is an error, not a green run --
# skipping is the other way a file like this quietly stops testing anything.
# `test_stitchviz.py` reads app/src the same way, unguarded, in a repo that
# has never shipped the digitizer without the Studio beside it.

# Every literal a shipped consumer compares a `.code` against is SHOUTY except
# one: `warnings_codes.PHOTO_AUTO_TIER` is `"photo_auto_tier"`, the sole
# lowercase wire value among 57. It is consumed as a WARNING_TEXT KEY, which
# `_map_keys` reads structurally rather than by shape, so it is covered. A
# future lowercase code consumed only through `.code === "..."` would not be --
# said here rather than papered over, because the alternative (accept any
# literal) makes `typeof t.code !== "string"` in threads.spec.js a failure.
_CODEISH = re.compile(r"^[A-Z][A-Z_0-9]{3,}$")


def _wire_values(src: str) -> set[str]:
    """`NAME = "value"` pairs. The VALUE is what crosses the wire."""
    return set(re.findall(r'^[A-Z_][A-Z_0-9]*\s*=\s*"([^"]+)"', src, re.M))


def _set_members(src: str, name: str) -> set[str]:
    """String literals of an `export const <name> = new Set([...])`.

    `SILENT_WARNINGS` (2026-09-07) is a fifth by-string crossing and the
    quietest yet: a TYPO in it does not throw, does not blank anything, and
    does not stop the page rendering — the code simply is not silenced, and
    "982 superpixels, 32 after merging" is back in the customer's panel on 20
    of 26 designs. Exactly the shape this file exists for, so it joins it.
    """
    m = re.search(rf"const {name}\s*=\s*new Set\(\[(.*?)\]\)", src, re.S)
    assert m, f"no `const {name} = new Set([...])` in the source"
    return set(re.findall(r'"([^"]+)"', m.group(1)))


def _map_keys(src: str, name: str) -> set[str]:
    """Top-level keys of a `const <name> = { ... };` object literal.

    Sliced at the closing brace that matches the declaration's OWN
    indentation -- `WARNING_TEXT` sits at module scope in digitizer.js,
    `FIX_FOR` inside DigitizePanel's `<script>`. Reading past that brace is
    the whole risk here: the next object literal down the file would donate
    its keys and this file would then assert something about the wrong map.
    """
    m = re.search(rf"^([ \t]*)const {name}\b", src, re.M)
    assert m, f"no `const {name}` in the source"
    indent, start = m.group(1), m.start()
    close = re.search(rf"^{indent}}};", src[start:], re.M)
    assert close, f"`const {name}` has no closing brace at its own indent"
    body = src[start:start + close.start()]
    return set(re.findall(rf"^{indent}  ([A-Za-z_][A-Za-z_0-9]*)\s*:", body, re.M))


def _compared_codes() -> dict[str, list[str]]:
    """SHOUTY literals compared against a `.code`, per file, across the Studio."""
    out: dict[str, list[str]] = {}
    for path in sorted(STUDIO.rglob("*")):
        if path.suffix not in (".js", ".svelte") or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        for m in re.finditer(r'(\w+)\.code\s*[=!]==?\s*"([^"]+)"', text):
            if _CODEISH.match(m.group(2)):
                out.setdefault(str(path.relative_to(REPO)), []).append(m.group(2))
    return out


def _preflight_codes() -> set[str]:
    """The codes preflight PUBLISHES — its own, never its re-reads.

    Leading-underscore names are excluded, and that is load-bearing rather
    than tidy. preflight declares its own codes bare (`THREAD_MATCH_POOR = ...`)
    and its re-reads of somebody else's private (`_CONTOUR_RING_UNREACHABLE`),
    so admitting the private ones would let a MIRROR vouch for a consumer:
    delete `CONTOUR_RING_UNREACHABLE` from warnings_codes.py and preflight's
    own stale copy would keep the Studio assertions below green. A check that
    validates a string against a second copy of that string has stopped
    checking anything.
    """
    from digitizer_core import preflight

    return {v for k, v in vars(preflight).items()
            if k.isupper() and not k.startswith("_")
            and isinstance(v, str) and _CODEISH.match(v)}


@pytest.fixture(scope="module")
def live() -> set[str]:
    """Every code either OWNER publishes: the pipeline's and preflight's."""
    return _wire_values(WARNINGS_CODES.read_text(encoding="utf-8")) | _preflight_codes()


def test_the_parsers_are_not_vacuous(live):
    """A test that cannot fail is worse than none.

    `test_stitchviz.py` learned this the expensive way: its first version
    matched a `LIGHT_DEG = 225` a merge had left behind as dead code, so it
    passed for weeks while the live canvas lit from a different corner. Every
    assertion below is a "not in" check, and a parser that finds nothing
    passes all of them. So pin the shapes first.
    """
    assert len(live) >= 68, f"only {len(live)} codes found — did the parse break?"
    assert "THREAD_MATCH_POOR" in live      # preflight's, via the module
    assert "BACKGROUND_ENCLOSED" in live    # warnings_codes', via the source

    # And a MIRROR must never be able to vouch for a consumer. Both of these
    # strings are live — but only because warnings_codes.py publishes them, and
    # `_preflight_codes` is the seam where that could quietly stop being true.
    from digitizer_core import preflight
    contributed = _preflight_codes()
    assert preflight._CONTOUR_RING_UNREACHABLE not in contributed
    assert preflight._PHOTO_FACES_DETECTED not in contributed
    assert {preflight._CONTOUR_RING_UNREACHABLE,
            preflight._PHOTO_FACES_DETECTED} <= live

    translated = _map_keys(DIGITIZER_JS.read_text(encoding="utf-8"), "WARNING_TEXT")
    assert len(translated) >= 25, f"WARNING_TEXT parsed as {sorted(translated)}"
    assert "photo_auto_tier" in translated, "the lowercase key must survive the parse"

    fixes = _map_keys(PANEL.read_text(encoding="utf-8"), "FIX_FOR")
    # The exact set, so a button added or lost is a deliberate act. Grew to
    # four on 2026-09-10 when the legibility check landed ON by default
    # (quality review item 11): `LETTERING_ILLEGIBLE` shares the size cure
    # and the panel dedupes the three into one button.
    assert fixes == {"COLOR_STOPS_HEAVY", "LETTERING_TOO_SMALL",
                     "STITCHES_TOO_SHORT", "LETTERING_ILLEGIBLE"}

    compared = _compared_codes()
    assert sum(len(v) for v in compared.values()) >= 8, compared

    silent = _set_members(DIGITIZER_JS.read_text(encoding="utf-8"),
                          "SILENT_WARNINGS")
    assert len(silent) >= 3, sorted(silent)


def test_every_translation_has_a_code_to_translate(live):
    """A WARNING_TEXT key that matches nothing is a customer-facing regression.

    Not a tidiness problem: `describeWarnings` falls back to
    `String(w.message)`, so a stranded key does not throw, does not warn, and
    does not blank the panel. It ships the engine's sentence to the customer
    and looks exactly like a code that was never translated.
    """
    keys = _map_keys(DIGITIZER_JS.read_text(encoding="utf-8"), "WARNING_TEXT")
    assert not (keys - live), (
        f"{DIGITIZER_JS.name} translates codes nothing emits: {sorted(keys - live)}")


def test_every_silenced_code_is_one_the_engine_still_emits(live):
    """A stale entry in SILENT_WARNINGS silently un-silences telemetry.

    The panel filters this set out of its rendered list, so a code that no
    longer matches is simply not filtered — and the two entries that matter
    fire on **20 of 26** corpus fixtures each, in the engine's own words. No
    error, no blank, just a build log back in front of a customer.
    """
    silent = _set_members(DIGITIZER_JS.read_text(encoding="utf-8"),
                          "SILENT_WARNINGS")
    assert not (silent - live), (
        f"SILENT_WARNINGS names codes nothing emits — they are no longer "
        f"being silenced: {sorted(silent - live)}")


def test_nothing_the_studio_switches_on_is_also_silenced(live):
    """Silencing a code the panel BRANCHES on would delete a feature.

    `warningLines` keeps every code and only the rendered list filters, so
    this cannot happen today — but the two live one import apart, and the
    failure would be a nudge or a classification readout that simply never
    appears again.
    """
    src = DIGITIZER_JS.read_text(encoding="utf-8")
    silent = _set_members(src, "SILENT_WARNINGS")
    switched = {c for cs in _compared_codes().values() for c in cs}
    switched |= _map_keys(PANEL.read_text(encoding="utf-8"), "FIX_FOR")
    assert not (silent & switched), (
        f"these codes are both silenced and branched on: "
        f"{sorted(silent & switched)}")


def test_every_studio_code_comparison_matches_a_live_code(live):
    """The behavioural switches — a stranded one deletes a FEATURE, silently.

    `FIX_FOR` misses and no button is offered; the flat-art nudge misses and
    the panel simply never suggests the correction. Both are `if` statements
    that stop being true, which produces no error anywhere.
    """
    stale = {f: sorted(set(cs) - live) for f, cs in _compared_codes().items()}
    stale = {f: cs for f, cs in stale.items() if cs}
    assert not stale, f"Studio switches on codes nothing emits: {stale}"

    fixes = _map_keys(PANEL.read_text(encoding="utf-8"), "FIX_FOR")
    assert not (fixes - live), (
        f"FIX_FOR offers a button for codes nothing emits: {sorted(fixes - live)}")


def test_preflight_mirrors_live_pipeline_codes():
    """preflight re-reads five pipeline codes by string, and owns none of them.

    The quietest of the six crossings, because it never reaches a screen.
    `_PHOTO_AUTO_TIER` going stale leaves `_tonal_fill_technique` returning
    the tatami default for a plan that sewed a tonal tier, and
    `_density_findings` then scores a design that intends a BAND against a
    single row pitch — a spurious or missing DENSITY_EXTREME, from a check
    that still runs and still looks healthy.
    """
    from digitizer_core import preflight

    published = _wire_values(WARNINGS_CODES.read_text(encoding="utf-8"))
    mirrored = {
        "_CONTOUR_RING_UNREACHABLE": (preflight._CONTOUR_RING_UNREACHABLE,),
        "_CLASSIFIED_PHOTO": tuple(preflight._CLASSIFIED_PHOTO),
        "_PHOTO_AUTO_TIER": (preflight._PHOTO_AUTO_TIER,),
        "_PHOTO_FACES_DETECTED": (preflight._PHOTO_FACES_DETECTED,),
    }
    assert sum(len(v) for v in mirrored.values()) == 5     # not vacuous

    stale = {name: [c for c in codes if c not in published]
             for name, codes in mirrored.items()}
    stale = {k: v for k, v in stale.items() if v}
    assert not stale, (
        f"preflight re-reads pipeline codes warnings_codes.py no longer "
        f"publishes: {stale}")
