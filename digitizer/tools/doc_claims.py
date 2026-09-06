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


def check_defaults(text: str, doc: str) -> list[str]:
    from digitizer_core.config import PipelineConfig

    fields = {f.name: f for f in dataclasses.fields(PipelineConfig)}
    problems = []
    for line in text.splitlines():
        upper = line.upper()
        says_on = "DEFAULT ON" in upper
        says_off = "DEFAULT OFF" in upper or "DEFAULT-OFF" in upper
        if not (says_on or says_off):
            continue
        for flag in set(_FLAG.findall(line)):
            field = fields.get(flag)
            if field is None or field.default is dataclasses.MISSING:
                continue
            real = field.default
            if not isinstance(real, bool):
                continue                                # tri-state, e.g. edge_cap
            if says_on and says_off:
                continue                                # the line states both
            claimed = says_on
            if real is not claimed:
                problems.append(
                    f"{doc}: cfg.{flag} documented DEFAULT "
                    f"{'ON' if claimed else 'OFF'}, code default is {real}")
    return problems


def check_constants(text: str, doc: str, mods: dict) -> tuple[list[str], int]:
    problems, agreed = [], 0
    for name, claimed in set(_CONST.findall(text)):
        for mod_name, mod in mods.items():
            if not hasattr(mod, name):
                continue
            real = getattr(mod, name)
            if isinstance(real, bool) or not isinstance(real, (int, float)):
                continue
            if abs(float(real) - float(claimed)) > 1e-12:
                problems.append(
                    f"{doc}: {name} documented as {claimed}, "
                    f"digitizer_core.{mod_name} has {real}")
            else:
                agreed += 1
    return problems, agreed


def main() -> int:
    mods = _modules()
    hard: list[str] = []
    soft: list[str] = []
    agreed = 0
    for doc in STRICT + ADVISORY:
        path = ROOT / doc
        if not path.is_file():
            print(f"  (no {doc})")
            continue
        text = path.read_text(encoding="utf-8")
        found = check_defaults(text, doc)
        const_problems, n = check_constants(text, doc, mods)
        found += const_problems
        agreed += n
        (hard if doc in STRICT else soft).extend(found)

    print(f"\n{agreed} documented constant(s) agree with the code")
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
