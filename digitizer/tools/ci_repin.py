"""ci_repin: move the md5 pins a CI run says are stale, from that run's own log.

WHY. Most red PR runs are not regressions but pins captured on another machine
(Windows against Linux, AVX2 against AVX-512) or gone stale behind a default
that moved. 77 test files pin hashes, so the fix -- copy the hash CI computed
into the test -- is the same edit by hand, many times over: #1036 took 28
commits for one OFF flag. This tool does that edit from the log, and says
what it could not do.

    python -m tools.ci_repin RUN_ID NODE_ID [NODE_ID ...] [--apply]
    python -m tools.ci_repin RUN_ID                  # lists the failed hash mismatches
    python -m tools.ci_repin 0 NODE_ID --log shard4.log     # a saved log, no gh

For each NODE_ID it reads the pair of hashes out of the failed shard's "short
test summary info" in the run's logs, finds which one is a string literal in
digitizer/tests/*.py (that is the pin: the OLD value; the other is what CI
computed: the NEW one -- the log's left/right order is not trusted, the source
decides), and prints a ledger of (node id, old, new, explained_by) plus the
patch. It WRITES NOTHING unless --apply is given, and then all rows or none.

WHAT IT READS. A pytest that cuts a failed `assert md5 == PIN` to
'bc28d37bc555...9cca8aed4db69' still prints both values whole in its `-`/`+`
diff block, and since tests/_hexrepr.py (W3-05) in `left :` / `right:` lines;
both are accepted. A failure with ONLY the truncated headline in its log (a
tuple or dict compare, say) is refused with "re-run needed": the value is not
in that log, and guessing it from 28 characters is how a wrong pin gets in.

explained_by. `flip` only when `dataclasses.asdict(PipelineConfig())` differs
between the merge-base and this tree on a default that exists in both (or a
new field whose default is on): a default moved, so a pin that follows it is
plausibly the flip's. Otherwise `UNEXPLAINED: a regression until shown
otherwise` (COOKBOOK triage). `flip` is a reason to LOOK at the pin, never a
verdict: this tool does not decide that a moved pin is fine. A new OFF flag
adds a key to asdict() and moves nothing, so it does not count.

REFUSED rows (exit 1, nothing written): the node did not fail in the run; no
whole hash pair in its log; neither hash (or both) is a literal in the tests;
the old pin is held in more than one place (--all-occurrences moves every
one); one pin would take two values.

"Tree" below is a directory with `digitizer_core/` in it, i.e. `digitizer/`.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

DIGITIZER = Path(__file__).resolve().parent.parent
REPO = "KS-Three/EMB-Bot"
EXPLAINED_FLIP = "flip"
EXPLAINED_NOT = "UNEXPLAINED: a regression until shown otherwise"

_HEX = r"(?:[0-9a-fA-F]{32}|[0-9a-fA-F]{64})"
_ANSI = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?Z ?")
_ENTRY = re.compile(r"^(?:FAILED|ERROR) (.*)$")
_LEFT = re.compile(rf"^\s*left : ({_HEX})\s*$", re.M)
_RIGHT = re.compile(rf"^\s*right: ({_HEX})\s*$", re.M)
_MINUS = re.compile(rf"^\s*- ({_HEX})\s*$", re.M)
_PLUS = re.compile(rf"^\s*\+ ({_HEX})\s*$", re.M)
_WHOLE_HEADLINE = re.compile(rf"assert '({_HEX})' == '({_HEX})'")
_CUT_HEADLINE = re.compile(r"'[0-9a-fA-F]{4,}\.\.\.[0-9a-fA-F]{4,}'")
_LITERAL = re.compile(rb"(?<![0-9A-Fa-f])" + _HEX.encode() + rb"(?![0-9A-Fa-f])")


# ------------------------------------------------------------------ the log
def clean_log(text: str) -> list[str]:
    """GitHub's job log as plain lines: no timestamp, no colour codes."""
    return [_STAMP.sub("", _ANSI.sub("", ln.rstrip("\r"))) for ln in text.split("\n")]


def summary_entries(lines: list[str]) -> dict[str, list[str]]:
    """{node id: [first message line, indented continuation lines...]} from the
    last "short test summary info" block. A node id with ' - ' in it would be
    cut there; none in the suite has one."""
    start = None
    for i, ln in enumerate(lines):
        if ln.startswith("=") and "short test summary info" in ln:
            start = i
    if start is None:
        return {}
    entries: dict[str, list[str]] = {}
    cur = None
    for ln in lines[start + 1:]:
        m = _ENTRY.match(ln)
        if m:
            node, _, msg = m.group(1).partition(" - ")
            cur = entries.setdefault(node, [])
            cur.append(msg)
        elif not ln.strip():
            continue                       # pytest's blank line inside a diff block
        elif ln[:1] in (" ", "\t") and cur is not None:
            cur.append(ln)
        else:
            cur = None
    return entries


def read_pair(entry: list[str]):
    """({hash, hash}, "") from one summary entry, or (None, why it cannot be)."""
    text = "\n".join(entry)
    left, right = _LEFT.findall(text), _RIGHT.findall(text)
    if len(left) == 1 and len(right) == 1:
        return {left[0].lower(), right[0].lower()}, ""
    minus, plus = _MINUS.findall(text), _PLUS.findall(text)
    if len(minus) == 1 and len(plus) == 1:
        return {minus[0].lower(), plus[0].lower()}, ""
    whole = _WHOLE_HEADLINE.search(text)
    if whole:
        return {whole.group(1).lower(), whole.group(2).lower()}, ""
    if len(minus) + len(plus) > 2 or len(left) + len(right) > 2:
        return None, "several hash pairs in one failure: not a single pin"
    if _CUT_HEADLINE.search(text):
        return None, ("only the truncated headline is in the log (no whole hash pair): "
                      "a re-run on a branch with tests/_hexrepr.py is needed")
    return None, "not a hash mismatch (no md5 / sha256 pair in the failure)"


def fetch_logs(run_id, repo: str = REPO, run=subprocess.run) -> list[str]:
    """The log text of every FAILED job of the run (`gh`, signed in)."""
    view = run(["gh", "run", "view", str(run_id), "--repo", repo, "--json", "jobs"],
               capture_output=True, text=True, encoding="utf-8", check=True)
    jobs = [j for j in json.loads(view.stdout)["jobs"] if j.get("conclusion") == "failure"]
    logs = []
    for job in jobs:
        got = run(["gh", "api", "--allow-escape-sequences",
                   f"repos/{repo}/actions/jobs/{job['databaseId']}/logs"],
                  capture_output=True, text=True, encoding="utf-8", check=True)
        logs.append(got.stdout)
    return logs


# ------------------------------------------------------------------ the pins
@dataclass
class Row:
    node: str
    old: str = ""
    new: str = ""
    explained_by: str = ""
    refused: str = ""                      # why this node is NOT being re-pinned
    sites: dict = field(default_factory=dict)   # Path -> occurrences of `old`


def literal_index(tests_dir: Path) -> dict[str, dict[Path, int]]:
    """{lower-cased 32/64-hex literal: {file: count}} over every tests/**/*.py."""
    index: dict[str, dict[Path, int]] = {}
    for path in sorted(Path(tests_dir).rglob("*.py")):
        for tok in _LITERAL.findall(path.read_bytes()):
            sites = index.setdefault(tok.decode().lower(), {})
            sites[path] = sites.get(path, 0) + 1
    return index


def plan(entries, nodes, tests_dir, explained: str, all_occurrences: bool = False) -> list[Row]:
    index = literal_index(tests_dir)
    rows = []
    for node in nodes:
        row = Row(node=node, explained_by=explained)
        rows.append(row)
        entry = entries.get(node)
        if entry is None:
            row.refused = "did not fail in this run (no FAILED line for it in the logs)"
            continue
        pair, why = read_pair(entry)
        if pair is None:
            row.refused = why
            continue
        a, b = sorted(pair)
        held = [h for h in (a, b) if h in index]
        if len(held) == 2:
            row.refused = ("both hashes are literals in the tests, so which one is the pin "
                           "cannot be told from the source")
        elif not held:
            row.refused = ("neither hash is a literal in digitizer/tests/*.py: the pin is in a "
                           "data file or is computed")
        else:
            row.old, row.new = held[0], (b if held[0] == a else a)
            row.sites = dict(index[row.old])
    live = [r for r in rows if not r.refused]
    values: dict[str, set] = {}
    for r in live:
        values.setdefault(r.old, set()).add(r.new)
    for r in live:
        if len(values[r.old]) > 1:
            r.refused = f"{r.old} would take two values: {', '.join(sorted(values[r.old]))}"
        elif sum(r.sites.values()) > 1 and not all_occurrences:
            names = ", ".join(sorted(p.name for p in r.sites))
            r.refused = (f"{sum(r.sites.values())} occurrences of the old hash ({names}): "
                         "pass --all-occurrences if every one is meant to move")
    return rows


def patch(rows: list[Row]) -> dict[Path, tuple[bytes, bytes]]:
    """{file: (before, after)} for the live rows: exactly the pinned literals,
    one pass per file (a new value is never rewritten again), every other byte kept."""
    todo: dict[Path, dict[bytes, bytes]] = {}
    for r in rows:
        if r.refused:
            continue
        for path in r.sites:
            todo.setdefault(path, {})[r.old.encode()] = r.new.encode()
    edits = {}
    for path, swap in todo.items():
        before = path.read_bytes()

        def sub(m, swap=swap):
            return swap.get(m.group(0).lower(), m.group(0))
        after = _LITERAL.sub(sub, before)
        if after != before:
            edits[path] = (before, after)
    return edits


# ----------------------------------------------------------- explained_by
def config_defaults(tree: Path) -> dict:
    """`asdict(PipelineConfig())` of the checkout whose `digitizer_core/` is in `tree`."""
    code = ("import dataclasses, json; from digitizer_core import PipelineConfig; "
            "print(json.dumps(dataclasses.asdict(PipelineConfig()), sort_keys=True, default=repr))")
    done = subprocess.run([sys.executable, "-c", code], cwd=str(tree), capture_output=True,
                          text=True, encoding="utf-8")
    if done.returncode != 0:
        raise RuntimeError(f"PipelineConfig() would not import in {tree}: "
                           f"{(done.stderr.strip().splitlines() or ['?'])[-1]}")
    return json.loads(done.stdout.strip().splitlines()[-1])


def explain(base_tree: Path, head_tree: Path):
    """(explained_by, {key: (base, head)}): `flip` only if a default moved."""
    try:
        base, head = config_defaults(base_tree), config_defaults(head_tree)
    except RuntimeError as e:
        return f"{EXPLAINED_NOT} (default config unreadable: {e})", {}
    moved = {k: (base[k], head[k]) for k in base if k in head and base[k] != head[k]}
    # a field that did not exist before only moves the default path if it starts ON
    moved.update({k: (None, head[k]) for k in head if k not in base and head[k]})
    return (EXPLAINED_FLIP if moved else EXPLAINED_NOT), moved


# ------------------------------------------------------------------ output
def ledger(rows: list[Row]) -> str:
    out = ["| node id | old | new | explained_by |", "|---|---|---|---|"]
    for r in rows:
        if r.refused:
            out.append(f"| {r.node} | - | - | REFUSED: {r.refused} |")
        else:
            out.append(f"| {r.node} | {r.old} | {r.new} | {r.explained_by} |")
    return "\n".join(out)


def unified(edits, root: Path) -> str:
    chunks = []
    for path, (before, after) in sorted(edits.items()):
        try:
            name = path.relative_to(root).as_posix()
        except ValueError:
            name = path.as_posix()
        chunks.append("".join(difflib.unified_diff(
            before.decode("utf-8", "replace").splitlines(keepends=True),
            after.decode("utf-8", "replace").splitlines(keepends=True),
            f"a/{name}", f"b/{name}")))
    return "".join(chunks)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(
        prog="python -m tools.ci_repin", description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_id", help="the Actions run id (any number with --log)")
    ap.add_argument("nodes", nargs="*", help="pytest node ids to re-pin; none: list candidates")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--log", action="append", default=[], metavar="FILE",
                    help="a saved job log instead of fetching the run's (repeatable)")
    ap.add_argument("--tests-dir", type=Path, default=DIGITIZER / "tests")
    ap.add_argument("--base-ref", default="origin/main",
                    help="the merge-base is taken against this ref (default origin/main)")
    ap.add_argument("--base-tree", type=Path, help="digitizer/ of the merge-base (default: git archive)")
    ap.add_argument("--head-tree", type=Path, default=DIGITIZER, help="digitizer/ to compare (default: this one)")
    ap.add_argument("--apply", action="store_true", help="write the patch (default: print it)")
    ap.add_argument("--all-occurrences", action="store_true",
                    help="move an old pin held in several places, all of them")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    if str(DIGITIZER) not in sys.path:
        sys.path.insert(0, str(DIGITIZER))
    from tools._console import utf8_console
    utf8_console()
    args = parse_args(argv)
    texts = [Path(p).read_text(encoding="utf-8", errors="replace") for p in args.log] \
        or fetch_logs(args.run_id, args.repo)
    entries: dict[str, list[str]] = {}
    for text in texts:
        entries.update(summary_entries(clean_log(text)))
    if not entries:
        print("no 'short test summary info' in the logs: the run has no failed pytest job")
        return 1
    if not args.nodes:
        print("failed hash mismatches in this run; name the ones to re-pin:")
        for node, entry in sorted(entries.items()):
            pair, why = read_pair(entry)
            if pair is not None or "truncated" in why:
                print(f"  {node}" + ("" if pair else "   (truncated: re-run needed)"))
        return 2

    if args.base_tree:
        label, moved = explain(args.base_tree, args.head_tree)
    else:
        from tools.default_path_diff import merge_base_tree
        with merge_base_tree(args.base_ref) as base:
            label, moved = explain(base, args.head_tree)
    rows = plan(entries, args.nodes, args.tests_dir, label, args.all_occurrences)
    edits = patch(rows)
    refused = [r for r in rows if r.refused]

    print(f"run {args.run_id}: defaults moved since the merge-base: "
          + (", ".join(f"{k} {a!r} -> {b!r}" for k, (a, b) in sorted(moved.items())) or "none"))
    print(ledger(rows))
    diff = unified(edits, args.tests_dir.parent)
    if diff:
        print("\n" + diff)
    print("\nThis tool moves pins; it does not judge that they should move. "
          "`flip` means a default changed, not that this pin is right.")
    if refused:
        print(f"{len(refused)} of {len(rows)} refused: nothing written.")
        return 1
    if args.apply:
        for path, (_before, after) in edits.items():
            path.write_bytes(after)
        print(f"wrote {len(edits)} file(s).")
    else:
        print("dry run: nothing written (--apply writes the patch above).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
