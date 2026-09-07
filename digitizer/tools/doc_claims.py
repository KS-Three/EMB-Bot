#!/usr/bin/env python
"""Check MASTER_SCOPE's and DOCTRINE's factual claims against the code.

MASTER_SCOPE's own rule is that every claim carries a `(verb date — source)`
pointer, but nothing checks the claims themselves, and a doc claim can outlive
its fix silently. Two did, found by accident on 2026-09-06:

  * defect 20 said *"No off switch for photo classes (`effective_split_tonal`
    ORs flag with class)"* — the switch had landed the day before (PR #316),
    and the function's own docstring already named defect 20 as its reason.
    The claim being false is what made the tier's benefit look unmeasurable.
  * defect 28's cause-3 mechanism was wrong in a way only a measurement caught.

This checks the two kinds of claim a script can settle:

  DEFAULTS   every `cfg.<flag>` the docs name, with "DEFAULT ON" or "DEFAULT
             OFF" on the SAME LINE, against `PipelineConfig`'s real default.
             Same line, not a character window: MASTER_SCOPE's entries are one
             long line each, and a window bleeds into the neighbouring entry
             (it paired `border` with both ON and OFF that way).
  CONSTANTS  every `NAME = <number>` assertion against the module that defines
             NAME. Handles scientific notation — a first pass read
             `SPLIT_TOLERANCE_MM = 1e-6` as 1 and reported a mismatch that was
             the regex, not the doc.

    python -m tools.doc_claims        # from digitizer/, seconds

It cannot check a measurement (a stitch count, a grade) — those need the
corpus, and the instrument for each lives beside it in tools/. What it covers
is the class where the doc and the code can be compared directly, which is
exactly where drift is silent.

Exit code 1 only when a CURRENT-STATE doc disagrees, so it can be wired
into a check later without the advisory snapshots making it permanently red.
"""
from __future__ import annotations

import dataclasses
import importlib
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]

# Current-state docs: a disagreement here is a DEFECT and fails the run.
# MASTER_SCOPE says "Current state ONLY"; DOCTRINE only accumulates rulings.
STRICT = ["MASTER_SCOPE.md", "DOCTRINE.md"]

# Supporting records: a disagreement is usually a dated SNAPSHOT, which their
# own header licenses ("Test counts, stitch counts and corpus grades written
# here were snapshots when written -- do not quote one as a current
# baseline"). Reported as advisory, because the useful action is a pointer to
# the current state, not a rewrite -- and because a checker that cries wolf
# on legitimate narrative is a checker nobody runs.
#
# EXPECT THE ADVISORY COUNT TO STAY NON-ZERO, and do not "fix" it to zero. A
# corrected snapshot still QUOTES the superseded number beside its pointer --
# that is what makes the correction readable -- so it keeps matching. The
# advisory list is a reading list, not a defect list; the number that must
# stay at zero is the current-state one below.
# Every area doc, discovered rather than listed, so a new one is covered the
# day it lands. Swept 2026-09-06: areas 2-5 and the research backlog are clean;
# every hit was in area 1.
ADVISORY = sorted(
    p.relative_to(ROOT).as_posix()
    for p in (ROOT / "docs" / "scope").glob("*.md")) if (
        ROOT / "docs" / "scope").is_dir() else []

# Modules whose module-level constants the docs quote. Adding one is free.
MODULES = [
    "machine", "preflight", "stage2_photo_segment", "stage4_vectorize",
    "stage6_blend", "stage6_fill", "stage6_satin", "stage6_streamline",
    "stage7_sequence", "stitches", "config",
]

_FLAG = re.compile(r"`(?:cfg|PipelineConfig)\.([a-z_0-9]+)`")
# A documented test count, in the two shapes the docs actually use:
#   `tests/test_x.py` (13)      `tests/test_x.py` (7 tests, 35s)
#   (`tests/test_x.py`, 13)     `digitizer/tests/test_x.py` (11)
# The number must sit in PARENS and be followed by `tests`, `)` or `,` — an
# unanchored "first number within N characters" also matches "at 80 mm" and
# a 4-digit date, which is how the first cut of this found phantom claims.
_TESTS = re.compile(
    r"`(?:digitizer/)?(tests/test_[a-z0-9_]+\.py)`[^`\n]{0,24}?"
    r"\((\d{1,3})(?:\s+tests?)?[),]"
    r"|\(`(?:digitizer/)?(tests/test_[a-z0-9_]+\.py)`,\s*(\d{1,3})\)")
# `NAME = 0.4`, `NAME = 1e-6`, `NAME is 200` — the shapes the docs actually use.
_CONST = re.compile(
    r"`?\b([A-Z][A-Z0-9_]{4,})\b`?\s*(?:=|is)\s*\*{0,2}"
    r"([0-9]+(?:\.[0-9]+)?(?:[eE][-+]?[0-9]+)?)\*{0,2}")


def _modules() -> dict:
    out = {}
    for name in MODULES:
        try:
            out[name] = importlib.import_module(f"digitizer_core.{name}")
        except Exception as exc:                       # pragma: no cover
            print(f"  (skipped digitizer_core.{name}: {exc})")
    return out


def check_defaults(text: str, doc: str
                   ) -> tuple[list[str], int, list[str], set[str]]:
    """Returns (disagreements, agreements, could-NOT-settle, flags touched).

    The third value is the point. A checker that reports only what it found
    cannot be told apart from one that examined nothing — the same trap as a
    green `node --test` that silently SKIPPED its six format cross-validation
    tests because the venv was built on 3.11 and holds no pystitch (CLAUDE.md,
    the quiet-venv failure). Four things make a default claim
    unverifiable, and every one of them used to be a bare `continue`, so the
    flag came out of a clean run looking checked.
    """
    from digitizer_core.config import PipelineConfig

    fields = {f.name: f for f in dataclasses.fields(PipelineConfig)}
    problems: list[str] = []
    unverifiable: list[str] = []
    seen: set[str] = set()
    verified = 0
    for line in text.splitlines():
        upper = line.upper()
        says_on = "DEFAULT ON" in upper
        says_off = "DEFAULT OFF" in upper or "DEFAULT-OFF" in upper
        if not (says_on or says_off):
            continue
        for flag in sorted(set(_FLAG.findall(line))):
            seen.add(flag)
            field = fields.get(flag)
            if field is None:
                # Not a defect on its own: a doc may name a flag that has not
                # landed, or one since renamed. Both are worth a reader's eye,
                # neither should fail the run. (Swept 2026-09-06: all 33 flag
                # mentions across the eight docs resolve, so this is
                # insurance, not a haul.)
                unverifiable.append(
                    f"{doc}: cfg.{flag} names no PipelineConfig field")
                continue
            if field.default is dataclasses.MISSING:
                unverifiable.append(
                    f"{doc}: cfg.{flag} has no plain default to compare "
                    f"against (default_factory or required)")
                continue
            real = field.default
            if not isinstance(real, bool):
                unverifiable.append(
                    f"{doc}: cfg.{flag} default is {real!r}, not a bool — "
                    f"'DEFAULT ON/OFF' does not describe a tri-state")
                continue
            if says_on and says_off:
                # The line states both, so which one is about THIS flag is
                # not decidable from the line. Deliberately NOT resolved by
                # pairing each flag with the nearer phrase: English puts the
                # phrase on either side ("`a` is DEFAULT ON while `b` is
                # DEFAULT OFF" vs "DEFAULT OFF for `b`"), and a wrong pairing
                # would report a disagreement that is the heuristic, not the
                # doc — the same failure the +/-400-character window produced
                # before this checker moved to line scope.
                unverifiable.append(
                    f"{doc}: cfg.{flag} sits on a line stating both DEFAULT "
                    f"ON and DEFAULT OFF — split the line to check it")
                continue
            claimed = says_on
            if real is not claimed:
                problems.append(
                    f"{doc}: cfg.{flag} documented DEFAULT "
                    f"{'ON' if claimed else 'OFF'}, code default is {real}")
            else:
                verified += 1
    return problems, verified, unverifiable, seen


def test_counts() -> dict[str, int]:
    """One `pytest --collect-only` for the whole suite -> {relpath: count}.

    ONE collection, not one per file: the docs name a dozen files and a
    per-file subprocess each would turn a seconds-long checker into a
    half-minute one, which is how a checker stops being run.

    Returns {} when collection fails (a missing venv, an import error). The
    caller reports that as unverifiable rather than as agreement — a checker
    that goes quiet when its input is broken is the failure this whole tool
    exists to stop.
    """
    try:
        out = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--collect-only"],
            capture_output=True, text=True, cwd=ROOT / "digitizer", timeout=300)
    except Exception:                                   # pragma: no cover
        return {}
    counts: dict[str, int] = {}
    for line in out.stdout.splitlines():
        if line.startswith("tests/") and "::" in line:
            counts[line.split("::", 1)[0]] = counts.get(
                line.split("::", 1)[0], 0) + 1
    return counts


def check_test_counts(text: str, doc: str, counts: dict[str, int]
                      ) -> tuple[list[str], int, list[str]]:
    """Documented per-file test counts against a real collection.

    These DRIFT, which is what makes them worth checking and is the whole
    difference from file paths: a path the docs name is usually either right
    or deliberately historical (`tools/bundle.mjs`, `src/app.js` — both cited
    in sentences saying they were deleted), while a count goes stale every
    time someone adds a test.

    **WHY THE PATTERN IS NARROW, which is the load-bearing decision here.**
    A first cut matched "the first number within 40 characters of the
    filename" and reported SIX drifts in `docs/scope/1`, the worst
    `test_satin.py` documented 43 against 99 collected. Every one was a false
    positive, because none of those is a claim about the file's current size:

        `tests/test_satin.py` **43/43**             pass/total at the time
        `tests/test_textcluster.py` gains 6         a DELTA
        `tests/test_pushcomp.py` together **46/46** combined across TWO files
        `tests/test_border.py` (17 -> 22 tests)     a before/after from a PR

    So this matches only the unambiguous total forms — a number in parens,
    followed by `tests`, `)` or `,` — and deliberately ignores prose. Swept
    2026-09-06 that way: **all three real count claims, every one of them in
    the current-state docs, are correct.** A checker that flagged the other
    six would have been noise, and noise is how a checker stops being run.
    """
    problems: list[str] = []
    unverifiable: list[str] = []
    agreed = 0
    for a, b, c, d in _TESTS.findall(text):
        rel, claimed = (a, b) if a else (c, d)
        if not counts:
            unverifiable.append(
                f"{doc}: {rel} claims {claimed} tests — collection "
                f"unavailable, so nothing was checked")
            continue
        real = counts.get(rel)
        if real is None:
            unverifiable.append(
                f"{doc}: {rel} claims {claimed} tests but collects nothing "
                f"(renamed, moved, or not collected here)")
        elif real != int(claimed):
            problems.append(
                f"{doc}: {rel} documented as {claimed} tests, collects {real}")
        else:
            agreed += 1
    return problems, agreed, unverifiable


def check_constants(text: str, doc: str, mods: dict
                    ) -> tuple[list[str], int, set[str]]:
    """Returns (disagreements, agreements, distinct constant names touched).

    One documented name can produce SEVERAL checks: `FILL_ROW_MM` and
    `SATIN_MAX_WIDTH_MM` are each defined in TWO modules, and the same name
    quoted in three docs is three claims. So the agreement count is checks,
    not constants — 18 against 11 distinct names on 2026-09-06 — and main()
    prints both rather than letting the larger number stand in for the
    smaller. Publishing the larger one as "constants" is the mistake the
    2026-09-06 entry made.
    """
    problems, agreed, seen = [], 0, set()
    for name, claimed in set(_CONST.findall(text)):
        for mod_name, mod in mods.items():
            if not hasattr(mod, name):
                continue
            real = getattr(mod, name)
            if isinstance(real, bool) or not isinstance(real, (int, float)):
                continue
            seen.add(name)
            if abs(float(real) - float(claimed)) > 1e-12:
                problems.append(
                    f"{doc}: {name} documented as {claimed}, "
                    f"digitizer_core.{mod_name} has {real}")
            else:
                agreed += 1
    return problems, agreed, seen


def main() -> int:
    mods = _modules()
    counts = test_counts()
    if not counts:
        print("  (test collection unavailable — no count was checked)")
    hard: list[str] = []
    soft: list[str] = []
    unchecked: list[str] = []
    agreed = 0
    flags_ok = 0
    tests_ok = 0
    flag_names: set[str] = set()
    const_names: set[str] = set()
    for doc in STRICT + ADVISORY:
        path = ROOT / doc
        if not path.is_file():
            print(f"  (no {doc})")
            continue
        text = path.read_text(encoding="utf-8")
        found, n_flags, cannot, flags = check_defaults(text, doc)
        const_problems, n, consts = check_constants(text, doc, mods)
        test_problems, n_tests, test_cannot = check_test_counts(
            text, doc, counts)
        found += const_problems + test_problems
        cannot += test_cannot
        tests_ok += n_tests
        agreed += n
        flags_ok += n_flags
        unchecked += cannot
        flag_names |= flags
        const_names |= consts
        (hard if doc in STRICT else soft).extend(found)

    # Say what was EXAMINED, not only what was found. A clean run that checked
    # nothing reads identically otherwise — the same trap as a green
    # `node --test` that silently SKIPPED six cross-validation tests.
    #
    # And the count is CHECKS, over that many DISTINCT names — one name can
    # be quoted in several docs and defined in several modules, so the two
    # numbers differ (18 checks over 11 names on 2026-09-06) and reporting
    # only the larger one overstates the coverage. The 2026-09-06 entry
    # announcing this checker published "11 flag defaults and 16 constants";
    # neither reproduces, because both came from a side probe rather than
    # from this output. Quote these lines, not a probe.
    print(f"\n{flags_ok} flag-default check(s) agree, over "
          f"{len(flag_names)} distinct flag(s)")
    print(f"{agreed} constant check(s) agree, over "
          f"{len(const_names)} distinct name(s)")
    print(f"{tests_ok} documented test count(s) match a real collection")
    if unchecked:
        print(f"\n{len(unchecked)} claim(s) this checker CANNOT settle "
              f"(not a defect — it just did not check them):")
        for u in unchecked:
            print(f"  {u}")
    if soft:
        print(f"\n{len(soft)} advisory (dated snapshot, or a pointer is "
              f"missing — read it before editing):")
        for s in soft:
            print(f"  {s}")
    if hard:
        print(f"\n{len(hard)} DISAGREEMENT(S) in a current-state doc:")
        for h in hard:
            print(f"  {h}")
        return 1
    print("no current-state doc disagrees with the code")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
