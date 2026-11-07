#!/usr/bin/env python
"""Which flags do the scope docs cite, do they exist, and is the default right?

A READ-ONLY, ADVISORY report for a scope-refresh session. It reads
MASTER_SCOPE.md, ROADMAP.md, DOCTRINE.md and every docs/scope/*.md, and never
writes any of them. It exits 0 whatever the docs say: a doc-content finding
must never block a PR, because the PRs that would trip it are exactly the
scope refreshes that exist to fix it.

What counts as a flag citation (three shapes, all in backticks):

  `cfg.<name>`               any PipelineConfig attribute the docs name
  `cfg.extra["<name>"]`      a cfg.extra key
  `<snake_case>` + ON/OFF    a bare snake_case name with an upper-case ON or
                             OFF (or "default `True`/`False`") right beside it

Each cited name is looked up in three places:

  field   a `PipelineConfig` dataclass field (digitizer_core/config.py)
  extra   a `cfg.extra` READER in digitizer_core/ or digitizer_service/ —
          found by AST, so `extra.get(KEY)` with `KEY = "..."` resolves too
  js      a JS engine option read as `o.<camelCase>` / `opts.` / `options.`
          in src/*.js, under the camelCase spelling of the snake_case name

and the report gives three lists:

  CITED       every distinct flag, where it lives, its real default, and
              every doc:line that cites it with the ON/OFF claimed there
  ORPHANS     cited but in none of the three. Split in two: ABSENT (the name
              is nowhere in the code — renamed or deleted) and NOT-A-FLAG
              (the name is in the code, but as a function, fixture, constant
              or comment — usually the doc citing something that is not a
              switch, which needs a reader, not an edit)
  MISMATCHES  the doc's ON/OFF against the real default. Split CURRENT
              ("is ON", "default OFF", "stays OFF") from HISTORICAL ("built
              OFF", "was ON", or struck through with ~~) and from
              CONDITIONAL ("with it ON", "switches X ON", "an OFF arm"): a
              historical or conditional claim that disagrees is usually a
              flip the doc narrates, or an experiment arm, correctly — a
              reading list, not a defect list

plus UNSETTLED: claims the tool found but could not compare (a tri-state or
non-bool default, a default_factory, a span stating both ON and OFF). Every
one of those is printed, never silently dropped — a skipped claim and a
passing claim look the same otherwise (the lesson `tools/doc_claims.py`
records).

How this differs from `tools/doc_claims.py`: that checker compares `cfg.X`
with "DEFAULT ON/OFF" on the same line against PipelineConfig and FAILS on a
current-state disagreement. This one covers the two shapes it does not —
`cfg.extra[...]` keys and bare backticked names — reports ORPHANS, also reads
ROADMAP.md, and never fails.

    python -m tools.scope_flag_lint            # from digitizer/, ~2 s
    python -m tools.scope_flag_lint --json     # same report as JSON

What it cannot know: an `effective_*` helper that turns a default-OFF field
on for some classes reads as OFF here; a JS option's default is inferred from
how it is read (`!== false` / `?? true` mean ON, anything else unset-means-
OFF), not from what the Studio passes.
"""
from __future__ import annotations

import ast
import dataclasses
import json
import pathlib
import re
import sys
from dataclasses import dataclass, field

ROOT = pathlib.Path(__file__).resolve().parents[2]
DIGITIZER = ROOT / "digitizer"

# `python tools/scope_flag_lint.py` puts tools/ on sys.path, not digitizer/.
sys.path.insert(0, str(DIGITIZER))

DOCS = ["MASTER_SCOPE.md", "ROADMAP.md", "DOCTRINE.md"]

# Where flag READERS live. tools/ and tests/ SET cfg.extra keys; they do not
# define what the pipeline reads, so they are not searched for readers — but
# they are searched for the NOT-A-FLAG / ABSENT split, since a fixture name
# that only a test mentions is "in the code" for that purpose.
READER_DIRS = ["digitizer/digitizer_core", "digitizer/digitizer_service"]
TEXT_DIRS = READER_DIRS + ["digitizer/tools", "digitizer/tests", "src",
                           "app/src", "tools", "test"]
JS_DIR = "src"


def scope_docs(root: pathlib.Path = ROOT) -> list[str]:
    """The docs this reads, discovered, so a new area doc is covered the day
    it lands."""
    area = sorted(p.relative_to(root).as_posix()
                  for p in (root / "docs" / "scope").glob("*.md"))
    return [d for d in DOCS if (root / d).is_file()] + area


# --------------------------------------------------------------------------
# Extraction
# --------------------------------------------------------------------------

_SPAN = re.compile(r"`([^`\n]+)`")
_CFG = re.compile(r"^(?:cfg|PipelineConfig)\.([a-z_][a-z0-9_]*)")
_EXTRA = re.compile(r"""cfg\.extra\[\s*["']([a-z_][a-z0-9_]*)["']\s*\]""")
_SNAKE = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")
_TOKEN = re.compile(r"\b(ON|OFF)\b|\bdefault\s*[:=]?\s*(True|False)\b")
_ARROW = re.compile(r"→|->")
# Where a span's neighbourhood ends: a sentence, a clause, a table cell, a
# paragraph. Without these a following "ON" two clauses on belongs to the
# wrong name.
_STOP = re.compile(r"\.\s|;|\||\n\s*\n|:\s")
_HISTORICAL = re.compile(
    r"\b(built|was|were|landed|originally|used to|before|previously)\b",
    re.IGNORECASE)
# An A/B arm or a switch being SET, not a statement of the default:
# "`x` ON now leaves 8.3 mm2", "switches `x` ON", "with it ON", "an OFF arm",
# "which you hold OFF". First pass on the real docs 2026-11-07: every one of
# these read as a current-state mismatch until it had its own bucket.
_CONDITIONAL = re.compile(
    r"\b(arms?|switch(?:es|ed)?|sets?|turns?|turned|with|when|if|under|"
    r"forced?|holds?|holding|leaves)\b",
    re.IGNORECASE)
# A claim BEFORE the name is read only in the "DEFAULT OFF for `x`" shape. A
# bare ON before a name is prose far more often than a claim: "ON can change
# `px_per_mm`" was the first-pass example.
_BEFORE = re.compile(r"\b(?i:default)[- ]?(ON|OFF)\b[^`]{0,16}$")
FOLLOW_CHARS = 40
PRECEDE_CHARS = 30


@dataclass
class Citation:
    doc: str
    line: int
    name: str
    kind: str                     # "cfg" | "extra" | "bare"
    claim: str | None = None      # "ON" | "OFF" | None
    historical: bool = False
    conditional: bool = False     # an A/B arm or a switch being set
    ambiguous: bool = False       # span states both ON and OFF
    snippet: str = ""


def _read_claim(seg: str, take_last: bool) -> tuple[str | None, bool]:
    """(claim, ambiguous) from one neighbourhood string."""
    toks = []
    for m in _TOKEN.finditer(seg):
        if m.group(1):
            toks.append((m.start(), m.group(1)))
        else:
            toks.append((m.start(), "ON" if m.group(2) == "True" else "OFF"))
    if not toks:
        return None, False
    kinds = {t for _, t in toks}
    if len(kinds) == 1:
        return toks[-1 if take_last else 0][1], False
    # "OFF -> ON" names a flip; the state after the arrow is the claim.
    if _ARROW.search(seg):
        return toks[-1][1], False
    return None, True


def _before(text: str, spans: list, i: int) -> str:
    """The clause before span i, back to the previous span or a stop."""
    prv = spans[i - 1] if i > 0 else None
    seg = text[prv.end() if prv else 0: spans[i].start()]
    stops = list(_STOP.finditer(seg))
    return seg[stops[-1].end() if stops else 0:][-PRECEDE_CHARS:]


def extract(text: str, doc: str) -> list[Citation]:
    """Every flag citation in `text`, with the ON/OFF claimed beside it.

    The claim is read from the text BETWEEN backtick spans: first the text
    after the name (up to the next span or clause stop, 40 chars), then — only
    if that has nothing, and only for a token no earlier name already took —
    the text before it (30 chars). The consumption rule is what keeps
    "`a` (ON) and `b`" from giving `b` the ON that belongs to `a`.
    """
    spans = list(_SPAN.finditer(text))
    line_at = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            line_at.append(i + 1)

    def lineno(pos: int) -> int:
        lo, hi = 0, len(line_at)
        while lo + 1 < hi:
            mid = (lo + hi) // 2
            if line_at[mid] <= pos:
                lo = mid
            else:
                hi = mid
        return lo + 1

    out: list[Citation] = []
    consumed: set[int] = set()    # gap index whose token a name already took
    pending: list[tuple[int, Citation, bool]] = []
    for i, m in enumerate(spans):
        body = m.group(1).strip()
        cits: list[Citation] = []
        for key in _EXTRA.findall(body):
            cits.append(Citation(doc, lineno(m.start()), key, "extra"))
        if not cits:
            cm = _CFG.match(body)
            if cm and cm.group(1) != "extra":
                cits.append(Citation(doc, lineno(m.start()), cm.group(1),
                                     "cfg"))
            elif _SNAKE.match(body):
                cits.append(Citation(doc, lineno(m.start()), body, "bare"))
        if not cits:
            continue

        # Text after this span: gap i (between span i and i+1).
        nxt = spans[i + 1] if i + 1 < len(spans) else None
        after = text[m.end(): nxt.start() if nxt else len(text)]
        if nxt and nxt.group(1).strip() in ("True", "False"):
            after = after + nxt.group(1).strip()
        stop = _STOP.search(after)
        after = after[: stop.start() if stop else len(after)][:FOLLOW_CHARS]
        before = _before(text, spans, i)

        struck = (text[max(0, m.start() - 2): m.start()] == "~~"
                  or text[m.end(): m.end() + 2] == "~~")
        claim, amb = _read_claim(after, take_last=False)
        look_before = claim is None and not amb
        if not look_before:
            consumed.add(i)            # gap i's token belongs to this name
        for c in cits:
            c.snippet = text[max(0, m.start() - PRECEDE_CHARS):
                             m.end() + FOLLOW_CHARS].replace("\n", " ")
            c.claim, c.ambiguous = claim, amb
            if look_before:
                pending.append((i, c, struck))
            else:
                # The verb can sit on either side: "built `x` OFF".
                near = before[-20:] + " " + after
                c.historical = struck or bool(_HISTORICAL.search(near))
                c.conditional = bool(_CONDITIONAL.search(near))
            out.append(c)

    # Second pass: the "before" text, for names with nothing after them, and
    # only where the previous name did not already claim that token.
    for i, c, struck in pending:
        if (i - 1) in consumed:
            c.historical = struck
            continue
        before = _before(text, spans, i)
        bm = _BEFORE.search(before)
        c.claim = bm.group(1) if bm else None
        c.historical = struck or bool(_HISTORICAL.search(before))

    # A bare name with no ON/OFF beside it is not a flag citation — it is
    # every other identifier the docs mention. `cfg.` and `cfg.extra[...]`
    # are citations on their own.
    return [c for c in out if c.kind != "bare" or c.claim or c.ambiguous]


# --------------------------------------------------------------------------
# The code side
# --------------------------------------------------------------------------

@dataclass
class CodeIndex:
    fields: dict = field(default_factory=dict)   # name -> default | MISSING
    extra: dict = field(default_factory=dict)    # name -> default | None
    js: dict = field(default_factory=dict)       # camelName -> bool default
    text_names: set = field(default_factory=set)  # every identifier in code
    sources: dict = field(default_factory=dict)  # name -> "file:line" (extra)


_MISSING = dataclasses.MISSING


def _module_str_consts(tree: ast.Module) -> dict[str, str]:
    out = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and isinstance(node.value, ast.Constant)
                and isinstance(node.value.value, str)):
            out[node.targets[0].id] = node.value.value
    return out


def _is_cfg_extra(expr: str) -> bool:
    return "extra" in expr and ("cfg" in expr or "config" in expr)


def extra_readers(paths) -> tuple[dict, dict]:
    """{key: default} for every `cfg.extra` key read in `paths`, and
    {key: "file:line"} for the first reader of each.

    A read is `.get(K[, d])` or `[K]` on an expression that names cfg/config
    AND extra, or on a local Name bound in the same function from such an
    expression (`extra = getattr(cfg, "extra", None) or {}` — the shape
    stage7 and fill_section_travel use). K may be a literal or a module-level
    string constant (`KEY = "absorb_fragments"`). The default is the `.get`
    literal, `None` for no default or `[K]`, or the source text when it is
    not a literal (fragment_absorb falls back to the FIELD of the same name).
    The warning dicts preflight also calls `extra` are not bound from cfg, so
    they do not count.
    """
    found: dict = {}
    where: dict = {}
    for path in paths:
        try:
            src = path.read_text(encoding="utf-8")
            tree = ast.parse(src)
        except (OSError, SyntaxError, UnicodeDecodeError):
            continue
        consts = _module_str_consts(tree)
        scopes = [n for n in ast.walk(tree)
                  if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
        bound: dict[int, set] = {}
        for fn in scopes:
            names = set()
            for n in ast.walk(fn):
                if (isinstance(n, ast.Assign)
                        and _is_cfg_extra(ast.unparse(n.value))):
                    names |= {t.id for t in n.targets
                              if isinstance(t, ast.Name)}
            for n in ast.walk(fn):
                bound.setdefault(id(n), set()).update(names)

        def key_of(node):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                return node.value
            if isinstance(node, ast.Name):
                return consts.get(node.id)
            return None

        def is_reader(recv) -> bool:
            if _is_cfg_extra(ast.unparse(recv)):
                return True
            return (isinstance(recv, ast.Name)
                    and recv.id in bound.get(id(recv), ()))

        for n in ast.walk(tree):
            key = recv = None
            default = None
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr == "get" and n.args):
                recv, key = n.func.value, key_of(n.args[0])
                if len(n.args) > 1:
                    d = n.args[1]
                    default = (d.value if isinstance(d, ast.Constant)
                               else ast.unparse(d))
            elif (isinstance(n, ast.Subscript)
                  and isinstance(n.ctx, ast.Load)):
                recv, key = n.value, key_of(n.slice)
            if key is None or recv is None or not is_reader(recv):
                continue
            # Several readers: a literal default wins over "no default".
            if key not in found or (found[key] is None and default is not None):
                found[key] = default
            where.setdefault(
                key, f"{path.relative_to(ROOT).as_posix()}:{n.lineno}"
                if path.is_relative_to(ROOT) else f"{path}:{n.lineno}")
    return found, where


_JS_RECV = r"\b(?:o|opts|options)\."
_JS_READ = re.compile(_JS_RECV + r"([a-zA-Z_][a-zA-Z0-9_]*)")
_JS_ON = re.compile(_JS_RECV + r"([a-zA-Z_]\w*)\s*(?:!==\s*false|\?\?\s*true)\b")
# A truthiness read: `if (o.X)`, `!o.X`, `o.X &&`, `o.X ? a : b`, `?? false`.
_JS_BOOL = re.compile(
    r"(?:(?:if\s*\(|!|&&|\|\|)\s*" + _JS_RECV + r"([a-zA-Z_]\w*)\b(?!\s*[.(\[=])"
    r"|" + _JS_RECV + r"([a-zA-Z_]\w*)\s*(?:&&|\?(?![?.])|\?\?\s*false\b|===\s*true\b))")


def js_options(paths) -> dict[str, bool | None]:
    """{option: default} for options read as `o.X` / `opts.X` / `options.X`.

    ON when any read is `!== false` or `?? true` (unset means on); OFF when
    it is read for truthiness (unset is `undefined`); None otherwise — a
    number like `o.pxPerMm` has no ON/OFF, and the first pass on the real
    docs reported it as a default mismatch until this distinguished them.
    """
    seen: set[str] = set()
    on: set[str] = set()
    boolish: set[str] = set()
    for path in paths:
        try:
            src = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        seen.update(_JS_READ.findall(src))
        on.update(_JS_ON.findall(src))
        for a, b in _JS_BOOL.findall(src):
            boolish.add(a or b)
    return {n: True if n in on else False if n in boolish else None
            for n in seen}


_IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


def build_index(root: pathlib.Path = ROOT) -> CodeIndex:
    from digitizer_core.config import PipelineConfig

    idx = CodeIndex()
    for f in dataclasses.fields(PipelineConfig):
        idx.fields[f.name] = f.default
    py = [p for d in READER_DIRS for p in (root / d).rglob("*.py")]
    idx.extra, idx.sources = extra_readers(py)
    idx.js = js_options(sorted((root / JS_DIR).glob("*.js")))
    for d in TEXT_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if p.suffix not in (".py", ".js", ".mjs", ".svelte", ".ts"):
                continue
            if "node_modules" in p.parts:
                continue
            try:
                idx.text_names.update(
                    _IDENT.findall(p.read_text(encoding="utf-8")))
            except (OSError, UnicodeDecodeError):
                continue
    return idx


def camel(name: str) -> str:
    head, *rest = name.split("_")
    return head + "".join(w[:1].upper() + w[1:] for w in rest)


# --------------------------------------------------------------------------
# Lint
# --------------------------------------------------------------------------

def _as_onoff(value) -> str | None:
    """'ON'/'OFF' for a bool default, None for anything a two-state claim
    cannot describe. A `cfg.extra` key with no default reads as None and is
    OFF in every reader that does `bool(...)` / `if extra.get(K)`."""
    if isinstance(value, bool):
        return "ON" if value else "OFF"
    return None


def resolve(c: Citation, idx: CodeIndex) -> list[tuple[str, object]]:
    """[(where, default)] for every place `c.name` is a flag. A key that is
    both a field and an extra key (absorb_fragments) gives both."""
    hits = []
    if c.kind == "extra":
        if c.name in idx.extra:
            d = idx.extra[c.name]
            hits.append(("extra", False if d is None else d))
        return hits
    if c.name in idx.fields:
        hits.append(("field", idx.fields[c.name]))
    if c.kind == "bare":
        if c.name in idx.extra:
            d = idx.extra[c.name]
            hits.append(("extra", False if d is None else d))
        if camel(c.name) in idx.js:
            hits.append(("js", idx.js[camel(c.name)]))
    return hits


@dataclass
class Report:
    docs: list
    citations: list
    cited: dict            # name -> {"where": [...], "default": ..., "cites"}
    orphans_absent: list
    orphans_not_flag: list
    mismatches_current: list
    mismatches_historical: list
    mismatches_conditional: list
    unsettled: list


def lint(citations: list[Citation], idx: CodeIndex,
         docs: list[str] | None = None) -> Report:
    cited: dict = {}
    absent: dict = {}
    not_flag: dict = {}
    cur, hist, cond, unsettled = [], [], [], []
    for c in citations:
        at = f"{c.doc}:{c.line}"
        hits = resolve(c, idx)
        label = (f'cfg.extra["{c.name}"]' if c.kind == "extra"
                 else f"cfg.{c.name}" if c.kind == "cfg" else c.name)
        if not hits:
            spelled = c.name in idx.text_names or camel(c.name) in idx.text_names
            (not_flag if spelled else absent).setdefault(label, []).append(at)
            continue
        entry = cited.setdefault(c.name, {
            "where": [w for w, _ in hits],
            "default": {w: (repr(d) if d is not _MISSING else "<factory>")
                        for w, d in hits},
            "cites": []})
        entry["cites"].append(f"{at} ({c.claim or '-'})")
        if c.ambiguous:
            unsettled.append(f"{at}: {label} sits beside both ON and OFF — "
                             f"split the claim to check it")
            continue
        if c.claim is None:
            continue
        for where, default in hits:
            real = _as_onoff(default)
            if real is None:
                why = ("default_factory, no plain default"
                       if default is _MISSING else f"default {default!r}")
                unsettled.append(f"{at}: {label} [{where}] doc says "
                                 f"{c.claim}, but {why} is not ON/OFF")
                continue
            if real != c.claim:
                line = (f"{at}: {label} [{where}] doc says {c.claim}, "
                        f"code default {real}")
                (hist if c.historical else cond if c.conditional
                 else cur).append(line)
    def fmt(d: dict) -> list[str]:
        # dict.fromkeys: two citations on one line are one place to edit.
        return [f"{k} — {', '.join(dict.fromkeys(v))}"
                for k, v in sorted(d.items())]

    return Report(docs or [], citations, dict(sorted(cited.items())),
                  fmt(absent), fmt(not_flag), cur, hist, cond, unsettled)


def run(root: pathlib.Path = ROOT, idx: CodeIndex | None = None) -> Report:
    docs = scope_docs(root)
    cits: list[Citation] = []
    for d in docs:
        cits += extract((root / d).read_text(encoding="utf-8"), d)
    return lint(cits, idx or build_index(root), docs)


def render(r: Report) -> str:
    out = [f"scope_flag_lint — advisory, read-only; {len(r.docs)} docs read: "
           + ", ".join(r.docs), ""]
    n_claims = sum(1 for c in r.citations if c.claim)
    out.append(f"CITED FLAGS: {len(r.cited)} distinct, from "
               f"{len(r.citations)} citations ({n_claims} with an ON/OFF)")
    for name, e in r.cited.items():
        dflt = ", ".join(f"{w}={v}" for w, v in e["default"].items())
        out.append(f"  {name}  [{dflt}]  {len(e['cites'])} cite(s)")
    sections = [
        ("ORPHANS — ABSENT (cited as a flag, name is nowhere in the code)",
         r.orphans_absent),
        ("ORPHANS — NOT A FLAG (name is in the code, but not as a config "
         "field, cfg.extra reader or JS option)", r.orphans_not_flag),
        ("DEFAULT MISMATCHES — CURRENT-STATE wording", r.mismatches_current),
        ("DEFAULT MISMATCHES — HISTORICAL wording (built/was/struck; usually "
         "a flip the doc narrates — read before editing)",
         r.mismatches_historical),
        ("DEFAULT MISMATCHES — CONDITIONAL wording (an A/B arm or a switch "
         "being set: 'with it ON', 'switches X ON'; rarely a default claim)",
         r.mismatches_conditional),
        ("UNSETTLED (found, not comparable — not a defect)", r.unsettled),
    ]
    for title, items in sections:
        out += ["", f"{title}: {len(items)}"] + [f"  {i}" for i in items]
    out += ["", "Advisory only: exit code is 0 whatever the docs say."]
    return "\n".join(out)


def to_json(r: Report) -> str:
    return json.dumps({
        "docs": r.docs,
        "cited": r.cited,
        "orphans_absent": r.orphans_absent,
        "orphans_not_flag": r.orphans_not_flag,
        "mismatches_current": r.mismatches_current,
        "mismatches_historical": r.mismatches_historical,
        "mismatches_conditional": r.mismatches_conditional,
        "unsettled": r.unsettled,
    }, indent=2)


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if {"-h", "--help"} & set(argv):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__)
        return 0
    from tools._console import utf8_console
    utf8_console()
    r = run()
    print(to_json(r) if "--json" in argv else render(r))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
