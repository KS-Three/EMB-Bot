#!/usr/bin/env python
"""flag_ledger: every engine flag built OFF, one row each -- what Kent flips from.

WHAT IT IS FOR. Kent flips flags by the numbers, but the OFF flags are spread
over ~5,600 lines of `digitizer_core/config.py`. This reads that file (never
writes it) and lists every `PipelineConfig` field whose default is False or
None and whose comment says OFF, with:

  default ...... the field's default
  pr ........... the PR that built it: the first `#NNNN` the comment names,
                 else the squash subject of the first commit that added the
                 field (`git log -S`), else blank
  kind ......... LAYOUT  flippable from renders (Kent's ruling 2026-10-22)
                 FABRIC  gate 1: the comment names a sew-out, a physical
                         constant, pull, density, underlay or stitch length
                 HELD    a hold is named (`HOLD`: "held OFF", "Kent held",
                         "parked OFF", "construction hold") -- in the comment,
                         or in a memory note within HOLD_WINDOW characters of
                         the flag's name
  why .......... the words that decided the kind, so a wrong row is easy to see
  flip sheet ... whether `tools/flip_sheet_renders.FLAGS` renders it
  memory ....... its memory note: the note whose description names it, else
                 the note that names it most

The kind is read in this order, first match wins: HELD; LAYOUT by the
comment's own layout ruling (layout, judged in the preview, the 2026-10-22
ruling -- a comment that classes itself wins over a gate-1 caveat in it);
FABRIC by an explicit gate-1 phrase (gate 1, physical constant, after a
sew-out, sew-out card); FABRIC by a cloth word (pull, density, underlay,
stitch length, sew-out); else LAYOUT.

It also lists STALE comments: fields whose default is True but whose comment
still says the flag is OFF by default ("built OFF", "default OFF") without
saying it was flipped. Listed only, never fixed.

    python -m tools.flag_ledger [--md OUT] [--json OUT] [--no-git]

Markdown goes to stdout (or `--md`); nothing is committed.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))
from tools._console import utf8_console  # noqa: E402

REPO = DIGITIZER.parent
CONFIG = DIGITIZER / "digitizer_core" / "config.py"
MEMORY = REPO / ".claude" / "memory"

OFF = re.compile(r"\bOFF\b")
PR = re.compile(r"(?:PR\s*)?#(\d{3,5})\b")
#: a hold named: "held OFF", "Kent held/holds", "parked OFF", "construction
#: hold", "reversal holds" -- not any "held" ("keyline-held bodies" is no
#: hold) and not "stays OFF" (comments use it of OTHER flags and of code
#: paths: "the supplement itself stays OFF")
HOLD = re.compile(r"held OFF|holds? (?:it )?OFF|Kent(?:'s)?\s+(?:held|holds)|parked OFF|"
                  r"construction hold|reversal holds", re.I)
HOLD_COMMENT = HOLD
FABRIC_HARD = re.compile(r"gate 1|physical constant|after a sew-?out|sew-?out card", re.I)
LAYOUT_HARD = re.compile(r"\blayout\b|judged in the preview|ruling 2026-10-22|10-22 ruling", re.I)
FABRIC_SOFT = re.compile(r"\bpull\b|\bdensity\b|\bunderlay\b|stitch length|sew-?out", re.I)
#: "OFF by default" phrasing, and the phrases that say it was flipped since
OFF_CLAIM = re.compile(r"built OFF|BUILT OFF|default OFF|DEFAULT OFF|defaults? to OFF", re.I)
FLIPPED = re.compile(r"flipped|flip(?:ped)? ON|ON by default|default ON|DEFAULT ON|ON since|"
                     r"ON \(default|on by default|now ON|turned ON", re.I)
#: a memory-note line naming a hold this close to the flag's name is its hold
HOLD_WINDOW = 120


def fields(path: Path = CONFIG) -> list[dict]:
    """Every PipelineConfig field: name, default, line, its comment block (the
    comment lines straight above it, plus any inline comment)."""
    src = path.read_text(encoding="utf-8")
    lines = src.splitlines()
    tree = ast.parse(src)
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == "PipelineConfig")
    out = []
    for node in cls.body:
        if not (isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)):
            continue
        if node.value is None or not isinstance(node.value, ast.Constant):
            continue
        i = node.lineno - 1
        block = []
        j = i - 1
        while j >= 0 and lines[j].strip().startswith("#"):
            block.append(lines[j].strip().lstrip("#").strip())
            j -= 1
        block.reverse()
        inline = lines[i].split("#", 1)[1].strip() if "#" in lines[i] else ""
        comment = " ".join(block + ([inline] if inline else []))
        out.append({"name": node.target.id, "default": node.value.value,
                    "line": node.lineno, "comment": comment})
    return out


def memory_notes(root: Path = MEMORY) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {p.name: p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(root.glob("*.md")) if p.name not in ("MEMORY.md", "MEMORY-archive.md")}


def _description(text: str) -> str:
    m = re.search(r"^description:\s*(.*)$", text, re.M)
    return m.group(1) if m else ""


def note_for(name: str, notes: dict[str, str]) -> str | None:
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    by_desc = [n for n, t in notes.items() if pat.search(_description(t))]
    if by_desc:
        return by_desc[0]
    counts = {n: len(pat.findall(t)) for n, t in notes.items()}
    best = max(counts.items(), key=lambda kv: (kv[1], kv[0]), default=(None, 0))
    return best[0] if best[1] else None


def hold_in_notes(name: str, notes: dict[str, str]) -> str | None:
    """The first memory note naming a hold (HOLD) within HOLD_WINDOW characters of
    the flag's name, on the same line."""
    pat = re.compile(r"\b" + re.escape(name) + r"\b")
    for n, t in notes.items():
        for line in t.splitlines():
            for m in pat.finditer(line):
                lo, hi = max(0, m.start() - HOLD_WINDOW), m.end() + HOLD_WINDOW
                if HOLD.search(line[lo:hi]):
                    return n
    return None


def classify(comment: str, held_note: str | None) -> tuple[str, str]:
    """-> (kind, why)."""
    m = HOLD_COMMENT.search(comment)
    if m:
        return "HELD", m.group(0)
    if held_note:
        return "HELD", f"memory {held_note}"
    for kind, rx in (("LAYOUT", LAYOUT_HARD), ("FABRIC", FABRIC_HARD), ("FABRIC", FABRIC_SOFT)):
        m = rx.search(comment)
        if m:
            return kind, m.group(0)
    return "LAYOUT", "(no gate-1 or hold words)"


def pr_from_git(name: str) -> str | None:
    try:
        out = subprocess.run(["git", "log", "-S", f"{name}:", "--reverse", "--format=%s", "--",
                              str(CONFIG.relative_to(REPO))],
                             cwd=REPO, capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for subj in out.splitlines():
        m = re.search(r"\(#(\d+)\)\s*$", subj)
        if m:
            return m.group(1)
    return None


def flip_sheet_flags() -> set[str]:
    try:
        from tools import flip_sheet_renders as F
    except Exception:  # noqa: BLE001 - a broken import reads as no sheet, said in the output
        return set()
    names = set(F.FLAGS)
    for spec in F.FLAGS.values():
        names.update(spec.get("sets", {}))
    return names


def ledger(use_git: bool = True, config: Path = CONFIG, memory: Path = MEMORY) -> dict:
    notes = memory_notes(memory)
    sheet = flip_sheet_flags()
    rows, stale, quiet = [], [], []
    for f in fields(config):
        c = f["comment"]
        if f["default"] is True:
            if OFF_CLAIM.search(c) and not FLIPPED.search(c):
                stale.append({"name": f["name"], "line": f["line"],
                              "says": OFF_CLAIM.search(c).group(0)})
            continue
        if f["default"] is False and not OFF.search(c):
            quiet.append({"name": f["name"], "line": f["line"]})
            continue
        if not (f["default"] is False or f["default"] is None) or not OFF.search(c):
            continue
        held = hold_in_notes(f["name"], notes)
        kind, why = classify(c, held)
        m = PR.search(c)
        pr = m.group(1) if m else (pr_from_git(f["name"]) if use_git else None)
        rows.append({"name": f["name"], "default": f["default"], "line": f["line"],
                     "pr": pr, "kind": kind, "why": why, "flip_sheet": f["name"] in sheet,
                     "memory": note_for(f["name"], notes)})
    return {"rows": rows, "stale": stale, "quiet": quiet,
            "counts": dict(Counter(r["kind"] for r in rows))}


def markdown(led: dict) -> str:
    c = led["counts"]
    out = [f"**{len(led['rows'])} flags built OFF**: "
           + ", ".join(f"{k} {c.get(k, 0)}" for k in ("LAYOUT", "FABRIC", "HELD"))
           + f"; {sum(1 for r in led['rows'] if r['flip_sheet'])} on the flip sheet. "
           + f"{len(led['stale'])} stale comments (default True, comment still says OFF).", ""]
    for kind in ("LAYOUT", "FABRIC", "HELD"):
        rows = [r for r in led["rows"] if r["kind"] == kind]
        out += [f"### {kind} ({len(rows)})", "",
                "| flag | default | PR | why | flip sheet | memory |", "|---|---|---|---|---|---|"]
        for r in sorted(rows, key=lambda r: r["name"]):
            out.append(f"| `{r['name']}` | {r['default']} | {('#' + r['pr']) if r['pr'] else '-'} | "
                       f"{r['why']} | {'yes' if r['flip_sheet'] else '-'} | {r['memory'] or '-'} |")
        out.append("")
    out += ["### Stale comments (listed, not fixed)", "", "| flag | config.py line | says |", "|---|---|---|"]
    out += [f"| `{s['name']}` | {s['line']} | {s['says']} |" for s in led["stale"]]
    out += ["", f"### Default False, comment never says OFF ({len(led['quiet'])}; not in the ledger)", "",
            ", ".join(f"`{q['name']}`" for q in led["quiet"])]
    return "\n".join(out) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--md", type=Path, help="write the markdown here instead of stdout")
    ap.add_argument("--json", type=Path, help="also write the rows as JSON")
    ap.add_argument("--no-git", action="store_true", help="skip the `git log -S` PR lookup")
    a = ap.parse_args(argv)
    utf8_console()
    led = ledger(use_git=not a.no_git)
    md = markdown(led)
    if a.md:
        a.md.write_text(md, encoding="utf-8")
    else:
        print(md)
    if a.json:
        a.json.write_text(json.dumps(led, indent=1, default=str), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
