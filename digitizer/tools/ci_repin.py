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
tuple or dict compare from before the plugin knew them) is refused with
"re-run needed": guessing a value from 28 characters is how a wrong pin gets in.

TUPLE, LIST AND DICT PINS (W5-06a). tests/_hexrepr.py also answers a `==` between
two like containers that hold a digest (or the first 20+ hex characters of one,
which is how test_pushcomp pins `sha256[:20]`) with every changed element on its
own line, and both sides whole. This tool reads those lines and
  * if only digests changed, moves each one to its literal in the tests, exactly
    as for a plain md5 pin (one ledger row per digest);
  * if a count or other element changed too, prints it and refuses -- unless one
    tuple / list / dict literal in the tests equals the old side exactly. Then the
    WHOLE literal moves (element by element, so quotes, comments and layout stay)
    and the ledger says "whole literal".
The source decides which side is the pin, as always. The gain starts on the first
CI run of a branch that has this plugin in it: older logs hold only the cut headline.

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
one); one pin would take two values; a container whose length or keys differ;
a changed non-digest element with no single literal to move it in; two edits
that would land on the same bytes.

"Tree" below is a directory with `digitizer_core/` in it, i.e. `digitizer/`.
"""
from __future__ import annotations

import argparse
import ast
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
_CUT_HEADLINE = re.compile(r"'[0-9a-fA-F]{4,}\.\.\.(?:[0-9a-fA-F]{4,}')?")   # also a tuple's first cut element
# a pin literal in the tests: a digest, or a cut of one (test_pushcomp pins sha256[:20])
_LITERAL = re.compile(rb"(?<![0-9A-Fa-f])[0-9A-Fa-f]{20,64}(?![0-9A-Fa-f])")
# the nested block tests/_hexrepr.py writes for a tuple / list / dict compare
_NEST_HEAD = re.compile(r"^[ \t]*hash mismatch inside a (tuple|list|dict), every changed element in full:[ \t]*$", re.M)
_NEST_LEAF = re.compile(r"^[ \t]+(\[.*?\]) (left |right): (.*?)[ \t]*$", re.M)
_NEST_WHOLE = re.compile(r"^[ \t]+whole (left |right): (.*?)[ \t]*$", re.M)
_NEST_MORE = re.compile(r"^[ \t]+\.\.\. (\d+) more changed elements not shown[ \t]*$", re.M)


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


def _hex():
    """tests/_hexrepr.py: the digest test and the container diff the plugin and the tool share."""
    if str(DIGITIZER) not in sys.path:
        sys.path.insert(0, str(DIGITIZER))
    from tests import _hexrepr
    return _hexrepr


@dataclass
class Nested:
    """A tuple / list / dict compare as tests/_hexrepr.py wrote it into the log."""
    kind: str
    whole: tuple | None = None       # (left, right) when the log wrote both sides whole
    leaves: list | None = None       # [(where, left, right)] as listed; None: one is not a literal
    cut: int = 0                     # changed elements the plugin counted but did not list


def read_nested(entry: list[str]):
    """A Nested from one summary entry, or None when the entry is not a container compare."""
    text = "\n".join(entry)
    head = _NEST_HEAD.search(text)
    if head is None:
        return None
    hx = _hex()
    nested = Nested(kind=head.group(1))
    more = _NEST_MORE.search(text)
    nested.cut = int(more.group(1)) if more else 0

    def value(raw):
        return hx.MISSING if raw == repr(hx.MISSING) else ast.literal_eval(raw)

    leaves = _NEST_LEAF.findall(text)
    lefts = [(w, v) for w, side, v in leaves if side == "left "]
    rights = [(w, v) for w, side, v in leaves if side == "right"]
    try:
        if len(lefts) != len(rights) or any(a[0] != b[0] for a, b in zip(lefts, rights)):
            raise ValueError("unpaired")
        nested.leaves = [(a[0], value(a[1]), value(b[1])) for a, b in zip(lefts, rights)]
    except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
        nested.leaves = None
    sides = _NEST_WHOLE.findall(text)
    left = [v for side, v in sides if side == "left "]
    right = [v for side, v in sides if side == "right"]
    if len(left) == 1 and len(right) == 1:
        try:
            nested.whole = (ast.literal_eval(left[0]), ast.literal_eval(right[0]))
        except (ValueError, SyntaxError, TypeError, MemoryError, RecursionError):
            nested.whole = None
    return nested


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
    where: str = ""                        # the element of a tuple / list / dict this row is
    note: str = ""                         # what else the ledger must say (a whole literal moving)
    edits: list = field(default_factory=list)   # [Edit]: a whole literal moving, element by element


@dataclass(frozen=True)
class Edit:
    """Bytes [start, end) of `path` (read at plan time) become `new`."""
    path: Path
    start: int
    end: int
    old: bytes
    new: bytes

    @property
    def key(self):
        return (self.path, self.start, self.end)


class PatchConflict(Exception):
    """Two planned edits want the same bytes, or the file moved since it was planned."""


@dataclass
class Site:
    """A tuple / list / dict literal in the tests that holds a digest."""
    path: Path
    node: ast.AST
    value: object
    data: bytes
    starts: list


def literal_index(tests_dir: Path) -> dict[str, dict[Path, int]]:
    """{lower-cased 20..64-hex literal: {file: count}} over every tests/**/*.py."""
    index: dict[str, dict[Path, int]] = {}
    for path in sorted(Path(tests_dir).rglob("*.py")):
        for tok in _LITERAL.findall(path.read_bytes()):
            sites = index.setdefault(tok.decode().lower(), {})
            sites[path] = sites.get(path, 0) + 1
    return index


def container_sites(tests_dir: Path) -> list[Site]:
    """Every tuple / list / dict literal that holds a digest, over tests/**/*.py."""
    has_digest = _hex().has_digest
    out = []
    for path in sorted(Path(tests_dir).rglob("*.py")):
        data = path.read_bytes()
        if not _LITERAL.search(data):
            continue
        try:
            tree = ast.parse(data)
        except (SyntaxError, ValueError):
            continue
        starts = [0]
        for line in data.splitlines(keepends=True):
            starts.append(starts[-1] + len(line))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.Tuple, ast.List, ast.Dict)):
                continue
            try:
                value = ast.literal_eval(node)
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                continue
            if has_digest(value):
                out.append(Site(path, node, value, data, starts))
    return out


def _orient(a: str, b: str, index):
    """(old, new, why not): which of two hashes is the pin is the one that is a literal."""
    x, y = sorted((a.lower(), b.lower()))
    held = [h for h in (x, y) if h in index]
    if len(held) == 2:
        return "", "", ("both hashes are literals in the tests, so which one is the pin "
                        "cannot be told from the source")
    if not held:
        return "", "", ("neither hash is a literal in digitizer/tests/*.py: the pin is in a "
                        "data file or is computed")
    return held[0], (y if held[0] == x else x), ""


def _literal_text(site: Site, node: ast.AST, new):
    """The source text that writes `new` where `node` is: the quote style of the source kept."""
    start, end = _span(site, node)
    seg = site.data[start:end]
    inner = node.operand if isinstance(node, ast.UnaryOp) else node
    if not isinstance(inner, ast.Constant):
        return None
    if isinstance(inner.value, str):
        quote = seg[:1]
        if (isinstance(new, str) and isinstance(node, ast.Constant) and quote in (b"'", b'"')
                and seg[:3] != quote * 3 and seg[-1:] == quote
                and quote.decode() not in new and "\\" not in new and new.isprintable()):
            return start, end, seg, quote + new.encode("utf-8") + quote
        return None
    if isinstance(new, (bool, int, float)) or new is None:
        return start, end, seg, repr(new).encode()
    return None


def _span(site: Site, node: ast.AST):
    return (site.starts[node.lineno - 1] + node.col_offset,
            site.starts[node.end_lineno - 1] + node.end_col_offset)


def _leaf_edit(site: Site, path: tuple, new):
    """(Edit, "") that writes `new` at `path` inside the literal, or (None, why not)."""
    node = site.node
    for key in path:
        if isinstance(node, (ast.Tuple, ast.List)):
            node = node.elts[key]
        elif isinstance(node, ast.Dict):
            for k, v in zip(node.keys, node.values):
                if k is not None and ast.literal_eval(k) == key:
                    node = v
                    break
            else:
                return None, f"key {key!r} is not in the literal at {site.path.name}"
        else:
            return None, f"{site.path.name} holds no container at {path!r}"
    got = _literal_text(site, node, new)
    if got is None:
        return None, (f"the element in {site.path.name} is not a plain literal that "
                      f"{new!r} can be written over")
    start, end, old, text = got
    return Edit(site.path, start, end, old, text), ""


def _same(value, side) -> bool:
    return type(value) is type(side) and value == side


def _plan_nested(node, nested: Nested, index, sites, explained: str, all_occurrences: bool) -> list[Row]:
    """The rows for one tuple / list / dict compare."""
    hx = _hex()

    def refuse(why):
        return [Row(node=node, explained_by=explained, refused=why)]

    if nested.whole is not None:
        changes = [(hx.where(p), p, a, b) for p, a, b in hx.changed_leaves(*nested.whole)]
    elif nested.leaves is not None and not nested.cut:
        changes = [(w, None, a, b) for w, a, b in nested.leaves]
    else:
        return refuse("the log lists only some of the changed elements and not the whole "
                      f"{nested.kind} (too large for tests/_hexrepr.py to write out): "
                      "it cannot be re-pinned from this log")
    if not changes:
        return refuse("no changed element in the log")
    if any(a is hx.MISSING or b is hx.MISSING for _w, _p, a, b in changes):
        return refuse(f"the {nested.kind}'s shape differs (an element or key is on one side "
                      "only): a structure change, not a pin value")
    others = [c for c in changes if not (hx.is_digest_like(c[2]) and hx.is_digest_like(c[3]))]
    if not others:                                     # digests only: each to its literal
        rows = []
        for here, _p, a, b in changes:
            row = Row(node=node, explained_by=explained, where=here)
            row.old, row.new, row.refused = _orient(a, b, index)
            if not row.refused:
                row.sites = dict(index[row.old])
            rows.append(row)
        return rows

    shown = "; ".join(f"{w} {a!r} vs {b!r}" for w, _p, a, b in others)
    if nested.whole is None:
        return refuse(f"non-digest elements changed too ({shown}) and the log does not show the "
                      f"whole {nested.kind}, so no single literal can be matched")
    left, right = nested.whole
    on_left = [s for s in sites() if _same(s.value, left)]
    on_right = [s for s in sites() if _same(s.value, right)]
    if on_left and on_right:
        return refuse("both sides are literals in the tests, so which one is the pin cannot be "
                      "told from the source")
    if not on_left and not on_right:
        return refuse(f"non-digest elements changed too ({shown}); neither side is a single "
                      f"literal in digitizer/tests/*.py, so the whole {nested.kind} cannot be "
                      "moved: the pin is built from parts or lives in a data file")
    pin_on_left = bool(on_left)
    held, old, new = (on_left, left, right) if pin_on_left else (on_right, right, left)
    if len(held) > 1 and not all_occurrences:
        names = ", ".join(sorted({s.path.name for s in held}))
        return refuse(f"{len(held)} source literals equal the old {nested.kind} ({names}): "
                      "pass --all-occurrences if every one is meant to move")
    edits = []
    for site in held:
        for here, path, a, b in changes:
            edit, why = _leaf_edit(site, path, b if pin_on_left else a)
            if edit is None:
                return refuse(f"{here}: {why}")
            edits.append(edit)
    return [Row(node=node, old=repr(old), new=repr(new), explained_by=explained, edits=edits,
                note=f"whole literal moves, non-digest elements with it: {shown}")]


def plan(entries, nodes, tests_dir, explained: str, all_occurrences: bool = False) -> list[Row]:
    index = literal_index(tests_dir)
    cached: list = []

    def sites():
        if not cached:
            cached.append(container_sites(tests_dir))
        return cached[0]

    rows = []
    for node in nodes:
        entry = entries.get(node)
        if entry is None:
            rows.append(Row(node=node, explained_by=explained,
                            refused="did not fail in this run (no FAILED line for it in the logs)"))
            continue
        nested = read_nested(entry)
        if nested is not None:
            rows += _plan_nested(node, nested, index, sites, explained, all_occurrences)
            continue
        row = Row(node=node, explained_by=explained)
        rows.append(row)
        pair, why = read_pair(entry)
        if pair is None:
            row.refused = why
            continue
        a, b = sorted(pair)
        row.old, row.new, row.refused = _orient(a, b, index)
        if not row.refused:
            row.sites = dict(index[row.old])
    live = [r for r in rows if not r.refused]
    values: dict[str, set] = {}
    for r in live:
        if not r.edits:
            values.setdefault(r.old, set()).add(r.new)
    written: dict[tuple, set] = {}
    for r in live:
        for e in r.edits:
            written.setdefault(e.key, set()).add(e.new)
    for r in live:
        if r.edits:
            clash = sorted({t.decode() for e in r.edits if len(written[e.key]) > 1
                            for t in written[e.key]})
            if clash:
                r.refused = f"the same literal would take two values: {', '.join(clash)}"
        elif len(values[r.old]) > 1:
            r.refused = f"{r.old} would take two values: {', '.join(sorted(values[r.old]))}"
        elif sum(r.sites.values()) > 1 and not all_occurrences:
            names = ", ".join(sorted(p.name for p in r.sites))
            r.refused = (f"{sum(r.sites.values())} occurrences of the old hash ({names}): "
                         "pass --all-occurrences if every one is meant to move")
    return rows


def patch(rows: list[Row]) -> dict[Path, tuple[bytes, bytes]]:
    """{file: (before, after)} for the live rows: exactly the pinned literals,
    one pass per file (a new value is never rewritten again), every other byte kept.
    Raises PatchConflict if two edits want the same bytes."""
    swaps: dict[Path, dict[bytes, bytes]] = {}
    literals: dict[Path, dict[tuple, Edit]] = {}
    for r in rows:
        if r.refused:
            continue
        for path in r.sites:
            swaps.setdefault(path, {})[r.old.encode()] = r.new.encode()
        for e in r.edits:
            literals.setdefault(e.path, {})[(e.start, e.end)] = e
    edits = {}
    for path in sorted(set(swaps) | set(literals)):
        before = path.read_bytes()
        spans: dict[tuple, bytes] = {}
        swap = swaps.get(path, {})
        for m in _LITERAL.finditer(before):
            new = swap.get(m.group(0).lower())
            if new is not None:
                spans[(m.start(), m.end())] = new
        for (start, end), e in literals.get(path, {}).items():
            if before[start:end] != e.old:
                raise PatchConflict(f"{path.name} is not what it was when the plan was made "
                                    f"(byte {start})")
            if spans.setdefault((start, end), e.new) != e.new:
                raise PatchConflict(f"{path.name} byte {start}: two different new values")
        last = 0
        for start, end in sorted(spans):
            if start < last:
                raise PatchConflict(f"{path.name} byte {start}: two edits overlap "
                                    "(a digest and the whole literal that holds it)")
            last = end
        after = bytearray(before)
        for (start, end), new in sorted(spans.items(), reverse=True):
            after[start:end] = new
        if bytes(after) != before:
            edits[path] = (before, bytes(after))
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
        who = r.node + (f" {r.where}" if r.where else "")
        if r.refused:
            out.append(f"| {who} | - | - | REFUSED: {r.refused} |")
        else:
            out.append(f"| {who}{f' [{r.note}]' if r.note else ''} | {r.old} | {r.new} | {r.explained_by} |")
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
            if read_nested(entry) is not None:
                print(f"  {node}   (tuple / list / dict compare)")
            elif pair is not None or "truncated" in why:
                print(f"  {node}" + ("" if pair else "   (truncated: re-run needed)"))
        return 2

    if args.base_tree:
        label, moved = explain(args.base_tree, args.head_tree)
    else:
        from tools.default_path_diff import merge_base_tree
        with merge_base_tree(args.base_ref) as base:
            label, moved = explain(base, args.head_tree)
    rows = plan(entries, args.nodes, args.tests_dir, label, args.all_occurrences)
    print(f"run {args.run_id}: defaults moved since the merge-base: "
          + (", ".join(f"{k} {a!r} -> {b!r}" for k, (a, b) in sorted(moved.items())) or "none"))
    print(ledger(rows))
    try:
        edits = patch(rows)
    except PatchConflict as e:
        print(f"\nTwo edits collide: {e}. Nothing written.")
        return 1
    refused = [r for r in rows if r.refused]
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
