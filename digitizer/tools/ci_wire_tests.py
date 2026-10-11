"""List the digitizer test files that read something OUTSIDE digitizer/.

CI's `digitizer` check runs the whole suite whenever a PR touches
`digitizer/` or `.github/`, and on every push to main. A PR that touches
neither cannot change what the pipeline tests exercise -- their code, pins
and fixtures all live under digitizer/ -- so for those PRs CI runs only the
files printed here: the "wire" tests that read the Studio's JS, the engine's
`src/`, the fonts, `docs/` or the root docs, which such a PR CAN break.

THE RULE (static, so a new test is classified the moment it lands):
a test file is a wire test when its own source, or the source of a
`tools.*` module it imports, reaches above digitizer/ -- `parents[2]` from
a file one level down, `ROOT.parent`, or a `REPO`/`REPO_ROOT` name. That
catches every repo-root reader in the suite as of 2026-10-08 (20 files,
~3.6 of 166 test-minutes on CI). `digitizer_core` and `digitizer_service`
are not scanned: library code reads nothing outside digitizer/ (its two
regex hits, `pipeline.py` and `calibration/card.py`, are a comment and a
path to digitizer/ itself).

A miss costs a red main, not a wrong merge going unseen: main still runs
the full suite on every merge. Fails closed -- no output means the caller
must run everything.

    python -m tools.ci_wire_tests            # one path per line, from digitizer/
"""

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # digitizer/
_REACHES_UP = re.compile(r"parents\[2\]|ROOT\.parent|\bREPO\b|\bREPO_ROOT\b")
_IMPORT_DOTTED = re.compile(r"^\s*(?:from|import)\s+(tools(?:\.\w+)+)", re.M)
_IMPORT_FROM = re.compile(r"^\s*from\s+tools\s+import\s+\(?([\w,\s]+)\)?", re.M)


def _tool_modules():
    out = {}
    for p in (ROOT / "tools").rglob("*.py"):
        name = ".".join(p.relative_to(ROOT).with_suffix("").parts)
        out[name] = bool(_REACHES_UP.search(p.read_text(encoding="utf-8")))
    return out


def wire_files():
    tools = _tool_modules()
    found = []
    for t in sorted((ROOT / "tests").glob("test_*.py")):
        src = t.read_text(encoding="utf-8")
        hit = bool(_REACHES_UP.search(src))
        hit = hit or any(tools.get(m) for m in _IMPORT_DOTTED.findall(src))
        for names in _IMPORT_FROM.findall(src):
            hit = hit or any(tools.get(f"tools.{n}") for n in re.findall(r"\w+", names))
        if hit:
            found.append(t.relative_to(ROOT).as_posix())
    return found


def main():
    files = wire_files()
    if not files:
        print("no wire tests found; run the full suite", file=sys.stderr)
        return 1
    print("\n".join(files))
    return 0


if __name__ == "__main__":
    sys.exit(main())
