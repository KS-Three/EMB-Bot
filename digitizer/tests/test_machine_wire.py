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
        "dst.js 121 vs exp.js 127 — each format's real per-axis RECORD limit, so the "
        "name is a collision and reconciling the record limits would corrupt an "
        "encoder — EXP genuinely jumps at 127 and DST genuinely cannot. The separate "
        "question, which of them gets used as the SEWN split, was settled 2026-09-13: "
        "see test_the_three_encoders_agree_on_the_sewability_ceiling below, where all "
        "three now read 121."
    ),
    "UNDERLAY_INSET_MM": (
        "satinfont.js 0.4 vs machine.py 1.0 — a NAME COLLISION, not drift, and the two "
        "sides say so themselves. The browser value is a satin column's contour-underlay "
        "inset PER SIDE (its own comment: 'Ink/Stitch contour default, per side'); the "
        "Python value is a region's edge-walk inset ('edge walk sits inside the finished "
        "edge'). Different lanes, different geometry, one name. Invisible to this file "
        "until 2026-09-14, when the comment-tolerant patterns above first let it be seen. "
        "NOT to be reconciled by picking a number: docs/trade-knowledge-2026-09-13.md §3 "
        "measured that Wilcom publishes NO underlay inset at all — two extraction passes, "
        "explicit negatives — so neither value has vendor backing and merging them would "
        "be inventing a physical constant, which is ROADMAP gate 1's business. Renaming "
        "one side would be the honest fix and is a separate change."
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
#
# BOTH patterns tolerate a TRAILING INLINE COMMENT, and that is not cosmetic —
# without it this file had a blind spot exactly the shape of the "first
# declaration wins" bug its own docstring describes. Measured 2026-09-14: the
# Python pattern anchored `\s*$` immediately after the number, so **36 of
# machine.py's constants were invisible to it** for carrying the trailing
# comment that is this codebase's house style — `TIE_STITCH_MM = 0.8   # one leg
# of a lock stitch` and the entire APPLIQUE_* block among them. A JS/Python pair
# could therefore be added, drift, and never be seen. Found when the 2026-09-14
# tie port added `TIE_STITCH_MM`/`TIE_STITCHES` to `src/digitize.js`, asserted
# they were now guarded, and a mutation test walked straight through — the same
# way the first cut of this file was caught.
#
# Fixing it took the shared count from 18 to 21 and surfaced one real
# divergence nobody could see: `UNDERLAY_INSET_MM`, pinned below.
_JS_CONST = re.compile(r"\b(?:const|let|var)\s+([A-Z][A-Z0-9_]{3,})\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:[;,\n]|//)")
# Module-level `NAME = 1.23` or `NAME: float = 1.23`. Anchored to column 0 so a
# local inside a function never counts.
_PY_CONST = re.compile(r"^([A-Z][A-Z0-9_]{3,})\s*(?::[^=\n]+)?=\s*(-?\d+(?:\.\d+)?)\s*(?:#.*)?$", re.M)


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
    # 302 with the comment-tolerant pattern (2026-09-14); 266 before it.
    assert len(py) >= 290, f"only {len(py)} Python constants found — the Python scanner broke"
    shared = _shared()
    assert len(shared) >= 21, (
        f"only {len(shared)} constants are declared in more than one file (measured 21 on "
        f"2026-09-14, up from 19 on 2026-09-13 when the patterns could not see a constant "
        f"with a trailing comment) — a scanner broke, or a shared constant was renamed on "
        f"one side only, which is itself the drift this file exists to catch"
    )
    # The named pairs this was built on must still be among them.
    for expected in ("SATIN_SPACING_MM", "FILL_ROW_MM", "BEAN_STITCH_MM", "SATIN_MAX_WIDTH_MM",
                     "MAX_DELTA", "TIE_STITCH_MM", "TIE_STITCHES", "UNDERLAY_INSET_MM"):
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


# --------------------------------------------------------------------------
# The SEWABILITY ceiling: a different question from the record limit, and the
# one the browser encoders have answered three different ways.
#
# A format's record limit is how far one record can reach. The sewability
# ceiling is how far the MACHINE can pull in one stitch — `machine.MAX_STITCH_MM`
# = 12.1, i.e. 121 units. They are not the same number and only coincide for DST.
#
# Measured 2026-09-13 — one design, a 6-step sewn chain of 12.5 mm axis moves,
# encoded by all three browser encoders and decoded with pystitch:
#
#     dst  12 sewn, worst axis 12.1 mm   splits at its record's own 121
#     pes  12 sewn, worst axis 12.1 mm   splits at PEC_MAX_SEWN_DELTA = 121
#     exp   6 sewn, worst axis 12.5 mm   splits at MAX_DELTA = 127  <- over
#
# So one design still produces three sew-outs and only EXP's carries a move
# past the ceiling — which is the same sentence `pes.js`'s own comment records
# about PES before #465 fixed it on 2026-09-12. That fix's comment even names
# the outlier: *"121 rather than EXP's 127 so that a PES file never carries a
# sewn move DST would have split."*
#
# NOT FIXED HERE ON PURPOSE. Kent ruled the PES split on 2026-09-12; the EXP
# one is the same kind of call and changes every .exp a customer exports, so it
# is his. `test/crossval-stitch-formats.test.js` pins today's behaviour
# ("crossval: EXP splits it the same way, at its own 127") and flipping it is
# a one-line change plus that pin, exactly as the PES flip was.
SEWABILITY_CEILING_UNITS = 121  # machine.MAX_STITCH_MM 12.1 * 10

ENCODER_SEWN_SPLIT = {
    "src/dst.js": ("MAX_DELTA", 121),
    "src/pes.js": ("PEC_MAX_SEWN_DELTA", 121),
    "src/exp.js": ("EXP_MAX_SEWN_DELTA", 121),  # brought into line 2026-09-13 (Kent)
}

# Empty, and that is the finished state: all three browser encoders now split a
# SEWN move at the same ceiling. EXP was the last one out — it used its record
# limit (127) as its sewn split until Kent's 2026-09-13 ruling, the same call he
# made for PES the day before. An entry reappearing here means an encoder drifted
# back out, and the test below will say which.
SEWN_SPLIT_DIVERGENCE: dict[str, str] = {}


def test_machine_max_stitch_mm_is_the_ceiling_these_units_encode():
    """The units in ENCODER_SEWN_SPLIT are machine.MAX_STITCH_MM, not a new number."""
    machine = (PY_DIR / "machine.py").read_text(encoding="utf-8")
    match = re.search(r"^MAX_STITCH_MM\s*=\s*([\d.]+)\s*$", machine, re.M)
    assert match, "machine.py no longer declares MAX_STITCH_MM at module level"
    assert abs(float(match.group(1)) * 10 - SEWABILITY_CEILING_UNITS) < 1e-9, (
        f"machine.MAX_STITCH_MM is {match.group(1)} mm, but this file encodes the "
        f"ceiling as {SEWABILITY_CEILING_UNITS} units. Move both or neither."
    )


def test_the_three_encoders_agree_on_the_sewability_ceiling():
    """Each encoder still splits sewn moves where this file records it does.

    This reads the declared constant rather than re-encoding a design: the
    behavioural proof lives in `test/crossval-stitch-formats.test.js`, and this
    is the census half — it exists so a fourth encoder, or a changed constant,
    cannot join the set unnoticed.
    """
    wrong = []
    for rel, (name, expected) in ENCODER_SEWN_SPLIT.items():
        text = (REPO / rel).read_text(encoding="utf-8")
        match = re.search(rf"const {name} = (\d+)", text)
        assert match, f"{rel} no longer declares {name} — the encoder was restructured"
        actual = int(match.group(1))
        if actual != expected:
            wrong.append(f"{rel} {name}: recorded {expected}, found {actual}")
    assert not wrong, (
        "an encoder's sewn-split constant moved without this census moving with it:\n  "
        + "\n  ".join(wrong)
    )

    agreeing = {rel for rel, (_, v) in ENCODER_SEWN_SPLIT.items() if v == SEWABILITY_CEILING_UNITS}
    diverging = set(ENCODER_SEWN_SPLIT) - agreeing
    assert diverging == set(SEWN_SPLIT_DIVERGENCE), (
        f"the set of encoders splitting sewn moves somewhere other than the "
        f"{SEWABILITY_CEILING_UNITS}-unit ceiling is {sorted(diverging)}, but "
        f"SEWN_SPLIT_DIVERGENCE records {sorted(SEWN_SPLIT_DIVERGENCE)}.\n\n"
        f"If an encoder was brought into line, delete its entry. If one drifted OUT "
        f"of line, that is the defect this test exists for."
    )
