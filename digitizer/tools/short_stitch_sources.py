"""Which engine source emits the short and the stacked stitches?

    python -m tools.short_stitch_sources corpus [--fixtures a,b] [--json OUT]
    python -m tools.short_stitch_sources pro --root DIR [--exclude NAME ...] [--json OUT]
    python -m tools.short_stitch_sources report CORPUS_JSON PRO_JSON

The census in `stitch_difficulty_census` found that EMB-Bot's sub-1 mm stitches
are 33.8% of a design against the pro's 10.6%, and that 31% of its penetrations
land within 0.5 mm of an earlier hole against 13%. It did not say WHERE they
come from. This tool does, and it MEASURES only: nothing in `digitizer_core/`,
the service or the Studio imports it, and it changes no stitch.

Attribution is by the plan's own provenance, read from a stream that is
checked, entry for entry, against the file `export.plan_to_pattern` would write
(a mismatch raises, so the labels cannot drift from the bytes):

- `kind` / `role` -- how the run sews (underlay, fill, satin, border, bean, run,
  travel, tie) and which tier asked for it;
- **folded locks** -- `stitches.apply_ties` folds a lock into the run it
  protects, so the run's kind says nothing about those points. The tool wraps
  `apply_ties` for the length of one run and records how many points each call
  put in front of and behind each run: `tie_in` / `tie_off`;
- **run links** -- the stitch that joins two runs with no jump between them;
- **creator** -- the function that constructed the run (`stage6_satin.satin_runs`
  and so on), taken from the call stack when the run is built, so a kind that
  many tiers share can still be told apart.

A short or stacked stitch is charged to the source of its ARRIVAL point. The
rules are the census's own (short: a sewn stitch under 1 mm, in the `<0.5` and
`0.5-1` bins; stacked: `near_hole`, a penetration within 0.5 mm of one of the
3rd..20th before it), re-implemented in `classify` and checked against
`stitch_difficulty_census.census` on every stream before it is counted.

A pro file has no provenance, so the comparison is per 1000 penetrations: a
rate per design, its p50/p95 over designs, and a ratio of pooled rates with a
bootstrap 95% interval over DESIGNS (n is small, so the interval is the number
to read, not the point). Which minimum length a source deserves is a physical
constant -- ROADMAP gate 1 -- and this tool proposes none.
"""
from __future__ import annotations

import argparse
import contextlib
import json
import math
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tools import stitch_difficulty_census as sdc  # noqa: E402
from tools._console import utf8_console  # noqa: E402

SHORT_BINS = ("lt_0p5", "0p5_1")
SINK_MODULES = ("dataclasses",)
# Creators that rebuild a run from another one: they inherit its label.
INHERIT_FROM = ("stage7_sequence.", "stage6_meander._reversed_piece")


# --- provenance ----------------------------------------------------------------

def _creator(run, depth: int) -> str:
    """`module.function` of whoever constructed `run` (the label is on the run
    itself, so a copy that keeps `__dict__` keeps it)."""
    f = sys._getframe(depth)
    while f is not None:
        mod = f.f_globals.get("__name__", "")
        if mod in SINK_MODULES or (mod.endswith(".stitches") and f.f_code.co_name == "tie_run"):
            f = f.f_back
            continue
        label = f"{mod.rsplit('.', 1)[-1]}.{f.f_code.co_name}"
        if label.startswith(INHERIT_FROM):
            for v in f.f_locals.values():
                src = getattr(v, "_src", None) if v is not run else None
                if src and getattr(v, "kind", None) == run.kind:
                    return src
        return label
    return "unknown"


def _tie_split(before: list, after: list):
    """(head, tail) point counts a lock call added around `before`, or None
    when `before` is not found whole inside `after`."""
    n = len(before)
    for k in range(len(after) - n + 1):
        if after[k:k + n] == before:
            return k, len(after) - n - k
    return None


@contextlib.contextmanager
def instrumented():
    """Tag every `StitchRun` with its creator and every `apply_ties` call with
    the points it folded in. Restores everything on exit."""
    from digitizer_core import stage7_sequence, stitches

    cls = stitches.StitchRun
    orig_init = cls.__init__
    orig_apply = stitches.apply_ties
    orig_s7 = getattr(stage7_sequence, "_apply_ties", None)

    def init(self, *a, **k):
        orig_init(self, *a, **k)
        self.__dict__["_src"] = _creator(self, 2)

    def apply(runs, *a, **k):
        runs = list(runs)
        before = [list(r.points) for r in runs]
        out = orig_apply(runs, *a, **k)
        for r, b in zip(runs, before):
            if r.points == b:
                continue
            split = _tie_split(b, r.points)
            if split is None:
                r.__dict__["_tie_unmatched"] = r.__dict__.get("_tie_unmatched", 0) + 1
                continue
            r.__dict__["_tie_head"] = r.__dict__.get("_tie_head", 0) + split[0]
            r.__dict__["_tie_tail"] = r.__dict__.get("_tie_tail", 0) + split[1]
        return out

    cls.__init__ = init
    stitches.apply_ties = apply
    if orig_s7 is not None:
        stage7_sequence._apply_ties = apply
    try:
        yield
    finally:
        cls.__init__ = orig_init
        stitches.apply_ties = orig_apply
        if orig_s7 is not None:
            stage7_sequence._apply_ties = orig_s7


def attributed_commands(plan):
    """`stitches.iter_machine_commands`, with the run behind every command.

    Yields `(cmd, point, run, index_in_run)`; a copy of that generator's rule,
    held honest by `attributed_stream`'s entry-for-entry check against the
    pattern the export would write.
    """
    from digitizer_core import stitches as st

    last = None
    started = False
    for bi, block in enumerate(plan.blocks):
        if bi > 0:
            yield st.CMD_COLOR_CHANGE, None, None, 0
            last = None
        for run in block.runs:
            if not run.points:
                continue
            if run.trim:
                yield st.CMD_TRIM, None, run, 0
                last = None
            if run.jump and started:
                yield st.CMD_JUMP, run.points[0], run, 0
                last = None
            for i, pt in enumerate(run.points):
                if last is not None and math.dist(last, pt) < st.SAME_POINT_MM:
                    continue
                yield st.CMD_STITCH, pt, run, i
                last = pt
                started = True
            last = run.points[-1]


def label_for(run, idx: int, linked: bool) -> tuple[str, str]:
    """(source, creator) of one stitch point. `source` is the coarse class the
    doc's table is keyed on; `creator` is the fine one."""
    creator = getattr(run, "_src", "unknown")
    n = len(run.points)
    head = getattr(run, "_tie_head", 0)
    tail = getattr(run, "_tie_tail", 0)
    # `<=`: the lock's last leg is the stitch that ARRIVES at the run's own
    # first point, so that arrival belongs to the lock, not to the run.
    if head and idx <= head:
        return "tie_in", creator
    if idx >= n - tail:
        return "tie_off", creator
    if linked and idx == 0:
        return "run_link", creator
    kind = run.kind
    if run.role:
        kind = f"{kind}/{run.role}"
    return kind, creator


def attributed_stream(plan):
    """-> (stream, prov): the census stream of `plan_to_pattern(plan)` and, per
    entry, `(source, creator)` or None. Raises when the two disagree."""
    from digitizer_core import stitches as st
    from digitizer_core.export import plan_to_pattern

    stream, _ = sdc.stream_from_pattern(plan_to_pattern(plan))
    cmds = list(attributed_commands(plan))
    want = {st.CMD_STITCH: "stitch", st.CMD_JUMP: "jump", st.CMD_TRIM: "trim",
            st.CMD_COLOR_CHANGE: "color_change"}
    if len(stream) != len(cmds) + 1 or stream[-1][2] != "end":
        raise ValueError(f"stream/plan length mismatch: {len(stream)} vs {len(cmds)}+end")
    prov, prev_cmd = [], None
    for (_, _, name), (cmd, _, run, idx) in zip(stream, cmds):
        if name != want[cmd]:
            raise ValueError(f"command mismatch: {name} vs {want[cmd]}")
        if cmd == st.CMD_STITCH:
            prov.append(label_for(run, idx, linked=(idx == 0 and prev_cmd == st.CMD_STITCH)))
        else:
            prov.append(None)
        prev_cmd = cmd
    prov.append(None)
    return stream, prov


# --- the classification (the census's rules, per stitch) ------------------------

def classify(stream):
    """-> (lengths, near): per stream entry, the sewn length arriving at it
    (None when it is not a sewn stitch) and the stream index of the earlier
    hole it stacks on (None when it does not). Same rules as
    `stitch_difficulty_census.census`."""
    n = len(stream)
    lengths = [None] * n
    near = [None] * n
    pens: list[tuple[float, float]] = []
    pen_at: list[int] = []
    prev_cmd = prev_pt = None
    for e, (x, y, cmd) in enumerate(stream):
        if cmd == "stitch":
            pens.append((x, y))
            pen_at.append(e)
            if prev_cmd == "stitch" and prev_pt is not None:
                lengths[e] = math.hypot(x - prev_pt[0], y - prev_pt[1])
            prev_pt = (x, y)
        elif cmd in ("jump", "trim", "color_change", "needle_set", "stop"):
            prev_pt = (x, y) if cmd == "jump" else prev_pt
        prev_cmd = cmd
    r2 = sdc.NEAR_HOLE_MM ** 2
    for i, (x, y) in enumerate(pens):
        for j in range(max(0, i - sdc.NEAR_HOLE_WINDOW), i - sdc.NEAR_HOLE_SKIP):
            dx, dy = x - pens[j][0], y - pens[j][1]
            if dx * dx + dy * dy <= r2:
                near[pen_at[i]] = pen_at[j]
                break
    return lengths, near


def _bin(length: float) -> str:
    return sdc.BIN_NAMES[sum(length >= e for e in sdc.BIN_EDGES_MM)]


COUNT_KEYS = ("lt_0p5", "0p5_1", "near", "union", "zero",
              "short_iso", "short_chain", "short_edge", "near_g5", "near_g10", "near_g20")


def _blank():
    return {"pens": 0, **{k: 0 for k in COUNT_KEYS}}


def tally(stream, prov=None) -> dict:
    """One design's counts. With `prov`, also per source and per creator."""
    lengths, near = classify(stream)
    # Re-derive the census's own figures and refuse to count if they differ.
    ref = sdc.census(stream)
    pens = sum(1 for _, _, c in stream if c == "stitch")
    sewn = sum(1 for v in lengths if v is not None)
    total, by_src, by_creator, pairs = _blank(), {}, {}, Counter()
    rank, seen = {}, 0
    for e, (_, _, cmd) in enumerate(stream):
        if cmd == "stitch":
            rank[e] = seen
            seen += 1
    for e, (_, _, cmd) in enumerate(stream):
        if cmd != "stitch":
            continue
        length, j = lengths[e], near[e]
        short = length is not None and length < 1.0
        # Source-agnostic context, so the pro (which has no provenance) can be
        # split the same way: what flanks a short stitch, and how far back the
        # hole it stacks on lies (3-5 = a retrace or a lock, more = a neighbour pass).
        ctx = None
        if short:
            nb = [lengths[e - 1] if e > 0 else None, lengths[e + 1] if e + 1 < len(stream) else None]
            ctx = ("short_edge" if None in nb else
                   "short_iso" if min(nb) >= 1.0 else "short_chain")
        gap = None
        if j is not None:
            g = rank[e] - rank[j]
            gap = "near_g5" if g <= 5 else "near_g10" if g <= 10 else "near_g20"
        rows = [total]
        if prov is not None:
            src, creator = prov[e]
            rows += [by_src.setdefault(src, _blank()), by_creator.setdefault(f"{src} @ {creator}", _blank())]
        for row in rows:
            row["pens"] += 1
            if length is not None and _bin(length) in SHORT_BINS:
                row[_bin(length)] += 1
            if short and length == 0.0:
                row["zero"] += 1
            if j is not None:
                row["near"] += 1
            if short or j is not None:
                row["union"] += 1
            if ctx:
                row[ctx] += 1
            if gap:
                row[gap] += 1
        if prov is not None and j is not None:
            pairs[f"{prov[e][0]} > {prov[j][0]}"] += 1
    n_short = total["lt_0p5"] + total["0p5_1"]
    for b, key in (("lt_0p5", "lt_0p5"), ("0p5_1", "0p5_1")):
        if sewn and abs(total[key] / sewn - ref["bins"][b]) > 6e-5:
            raise ValueError(f"classify disagrees with census on {b}: {total[key] / sewn} vs {ref['bins'][b]}")
    if pens and abs(total["near"] / pens - ref["near_hole"]) > 6e-5:
        raise ValueError("classify disagrees with census on near_hole")
    out = {"penetrations": pens, "sewn": sewn, "short": n_short, **{k: total[k] for k in COUNT_KEYS}}
    if prov is not None:
        out.update(by_source=by_src, by_creator=by_creator, near_pairs=dict(pairs))
    return out


# --- the two sides -------------------------------------------------------------

def plan_record(fixture: str) -> dict:
    from digitizer_core import PipelineConfig, digitize
    from tools import corpus_scorecard as sc

    with instrumented():
        result, plan = digitize(sc.TESTDATA / fixture, PipelineConfig(**sdc.CFG))
    stream, prov = attributed_stream(plan)
    unmatched = sum(getattr(r, "_tie_unmatched", 0) for _, r in plan.iter_runs())
    return {"design": fixture, "class": result.design_class, "tie_unmatched": unmatched,
            **tally(stream, prov)}


def pro_files(root: Path, exclude: list[str]) -> list[Path]:
    return [p for p in sorted(root.rglob("*.dst"))
            if not any(x in part for part in p.relative_to(root).parts for x in exclude)]


def pro_record(label: str, cluster: str, path: Path) -> dict:
    """`cluster` is the customer a file belongs to: several pro files are
    variants of one artwork, so designs are not independent draws."""
    stream, _ = sdc.stream_from_pattern(sdc.read_file(path))
    return {"design": label, "class": "pro", "cluster": cluster, **tally(stream)}


# --- the comparison ------------------------------------------------------------

def per_1000(row: dict, key: str) -> float:
    return 1000.0 * row[key] / row["penetrations"] if row["penetrations"] else float("nan")


def quantile(xs: list[float], p: float) -> float:
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * len(s)))]


def pooled(rows: list[dict], key: str) -> float:
    pens = sum(r["penetrations"] for r in rows)
    return 1000.0 * sum(r[key] for r in rows) / pens if pens else float("nan")


def bootstrap_ratio(ours: list[tuple[int, int]], pro: list[tuple[int, int]],
                    draws: int = 10000, seed: int = 20261015,
                    pro_groups: list[str] | None = None):
    """Ratio of pooled rates, ours / pro, with a 95% percentile interval from
    resampling DESIGNS with replacement in each group. Inputs are
    (count, penetrations) per design. With `pro_groups` (one label per pro
    design) the pro side resamples whole GROUPS instead -- several pro files
    are variants of one customer's artwork, so designs are not independent."""
    import numpy as np

    rng = np.random.default_rng(seed)
    o, p = np.array(ours, dtype=float), np.array(pro, dtype=float)
    members = None
    if pro_groups is not None:
        members = [np.array([i for i, g in enumerate(pro_groups) if g == k])
                   for k in sorted(set(pro_groups))]

    def rate(a, idx):
        s = a[idx]
        return s[:, 0].sum() / s[:, 1].sum()

    def draw_pro():
        if members is None:
            return rng.integers(0, len(p), len(p))
        return np.concatenate([members[i] for i in rng.integers(0, len(members), len(members))])

    with np.errstate(all="ignore"):     # a pro rate of zero is a ratio of inf, not a crash
        point = rate(o, np.arange(len(o))) / rate(p, np.arange(len(p)))
        vals = []
        for _ in range(draws):
            pr = rate(p, draw_pro())
            vals.append(rate(o, rng.integers(0, len(o), len(o))) / pr if pr > 0 else math.inf)
        lo, hi = np.percentile(vals, [2.5, 97.5])
    return float(point), float(lo), float(hi)

def pairs_of(rows, key):
    return [(r[key], r["penetrations"]) for r in rows]


def source_pairs(rows, src_key, name, key):
    out = []
    for r in rows:
        d = r.get(src_key, {}).get(name, {})
        out.append((d.get(key, 0), r["penetrations"]))
    return out


def report(ours: list[dict], pro: list[dict]) -> str:
    L = []
    metrics = [("lt_0p5", "<0.5 mm"), ("0p5_1", "0.5-1 mm"), ("near", "stacked"), ("union", "short or stacked")]
    L.append("### Pooled rate per 1000 penetrations, with per-design spread")
    L.append("")
    groups = [r.get("cluster", r["design"]) for r in pro]
    L.append("| metric | EMB-Bot pooled | EMB-Bot p50 / p95 | pro pooled | pro p50 / p95 | ratio | 95% CI (designs) | 95% CI (pro by customer) |")
    L.append("|---|---|---|---|---|---|---|---|")
    for key, name in metrics:
        o = [per_1000(r, key) for r in ours]
        p = [per_1000(r, key) for r in pro]
        ratio, lo, hi = bootstrap_ratio(pairs_of(ours, key), pairs_of(pro, key))
        _, clo, chi = bootstrap_ratio(pairs_of(ours, key), pairs_of(pro, key), pro_groups=groups)
        L.append(f"| {name} | {pooled(ours, key):.1f} | {quantile(o, .5):.1f} / {quantile(o, .95):.1f} | "
                 f"{pooled(pro, key):.1f} | {quantile(p, .5):.1f} / {quantile(p, .95):.1f} | "
                 f"{ratio:.2f} | {lo:.2f} - {hi:.2f} | {clo:.2f} - {chi:.2f} |")
    L.append("")
    L.append(f"EMB-Bot: {len(ours)} designs, {sum(r['penetrations'] for r in ours):,} penetrations. "
             f"Pro: {len(pro)} designs, {sum(r['penetrations'] for r in pro):,} penetrations.")
    L.append("")

    L.append("### Source-agnostic split (both sides, no provenance needed)")
    L.append("")
    L.append("A short stitch is `iso` when both neighbouring stitches are >= 1 mm (a row turn or a lone "
             "connector), `chain` when a neighbour is short too (a bean or run pitch, a thin satin), "
             "`edge` when it sits at a run boundary. A stacked penetration is `g5` when the earlier hole is "
             "3-5 penetrations back (a retrace, a lock), `g10` 6-10 back, `g20` 11-20 back (a neighbouring pass).")
    L.append("")
    L.append("| class | EMB-Bot /1000 | pro /1000 | ratio | 95% CI (pro by customer) |")
    L.append("|---|---|---|---|---|")
    for key in ("short_iso", "short_chain", "short_edge", "near_g5", "near_g10", "near_g20"):
        ratio, lo, hi = bootstrap_ratio(pairs_of(ours, key), pairs_of(pro, key), draws=4000, pro_groups=groups)
        L.append(f"| {key} | {pooled(ours, key):.1f} | {pooled(pro, key):.1f} | {ratio:.2f} | {lo:.2f} - {hi:.2f} |")
    L.append("")

    sources = sorted({s for r in ours for s in r["by_source"]})
    tot_union = sum(r["union"] for r in ours)
    pro_union = pooled(pro, "union")
    L.append("### By source (EMB-Bot only; the pro has no provenance)")
    L.append("")
    L.append("`share` is the source's share of all short-or-stacked penetrations. "
             "`rate` is per 1000 of the DESIGN's penetrations, so the rates add up to the pooled total. "
             "`within` is the fraction of the source's OWN penetrations that are short or stacked. "
             "`vs pro` is the source's rate over the pro's pooled total rate, 95% CI over EMB-Bot designs and pro customers.")
    L.append("")
    L.append("| source | penetrations | <0.5 | 0.5-1 | stacked | short or stacked | share | rate /1000 | within | vs pro (CI) | worst designs |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    table = []
    for s in sources:
        agg = _blank()
        for r in ours:
            for k, v in r["by_source"].get(s, {}).items():
                agg[k] += v
        table.append((agg["union"], s, agg))
    for _, s, agg in sorted(table, key=lambda t: -t[0]):
        ratio, lo, hi = bootstrap_ratio(source_pairs(ours, "by_source", s, "union"), pairs_of(pro, "union"),
                                        draws=4000, pro_groups=groups)
        worst = sorted(ours, key=lambda r: -per_1000({"union": r["by_source"].get(s, {}).get("union", 0),
                                                       "penetrations": r["penetrations"]}, "union"))[:3]
        w = ", ".join(f"{r['design'].split('/')[-1].rsplit('.', 1)[0]} "
                      f"{per_1000({'union': r['by_source'].get(s, {}).get('union', 0), 'penetrations': r['penetrations']}, 'union'):.0f}"
                      for r in worst)
        within = agg["union"] / agg["pens"] if agg["pens"] else float("nan")
        L.append(f"| {s} | {agg['pens']:,} | {agg['lt_0p5']:,} | {agg['0p5_1']:,} | {agg['near']:,} | {agg['union']:,} | "
                 f"{100 * agg['union'] / tot_union:.1f}% | "
                 f"{1000 * agg['union'] / sum(r['penetrations'] for r in ours):.1f} | {100 * within:.0f}% | "
                 f"{ratio:.2f} ({lo:.2f}-{hi:.2f}) | {w} |")
    L.append("")
    L.append(f"Pro pooled short-or-stacked: {pro_union:.1f} per 1000.")
    L.append("")
    L.append("### Each source's short stitches by context, and its stacked penetrations by reach back")
    L.append("")
    L.append("| source | short iso | short chain | short edge | stacked g5 | stacked g10 | stacked g20 |")
    L.append("|---|---|---|---|---|---|---|")
    for _, s, agg in sorted(table, key=lambda t: -t[0]):
        L.append(f"| {s} | {agg['short_iso']:,} | {agg['short_chain']:,} | {agg['short_edge']:,} | "
                 f"{agg['near_g5']:,} | {agg['near_g10']:,} | {agg['near_g20']:,} |")
    L.append("")

    creators = Counter()
    for r in ours:
        for k, v in r["by_creator"].items():
            creators[k] += v["union"]
    L.append("### Top creators (source @ module.function) by short-or-stacked penetrations")
    L.append("")
    L.append("| source / creator | short or stacked | share | own penetrations | within |")
    L.append("|---|---|---|---|---|")
    pens_by = Counter()
    for r in ours:
        for k, v in r["by_creator"].items():
            pens_by[k] += v["pens"]
    for k, v in creators.most_common(14):
        L.append(f"| {k} | {v:,} | {100 * v / tot_union:.1f}% | {pens_by[k]:,} | {100 * v / pens_by[k]:.0f}% |")
    L.append("")

    pairs = Counter()
    for r in ours:
        pairs.update(r["near_pairs"])
    tot_near = sum(pairs.values())
    L.append("### Stacked: arrival source > the earlier hole's source")
    L.append("")
    L.append("| arrival > earlier hole | count | share of stacked |")
    L.append("|---|---|---|")
    for k, v in pairs.most_common(10):
        L.append(f"| {k} | {v:,} | {100 * v / tot_near:.1f}% |")
    L.append("")
    zero = sum(r["zero"] for r in ours)
    zero_pro = sum(r["zero"] for r in pro)
    L.append(f"Zero-length stitches (identical 0.1 mm hole twice running): EMB-Bot {zero:,}, pro {zero_pro:,}.")
    return "\n".join(L)


# --- cli -----------------------------------------------------------------------

def main(argv=None) -> int:
    utf8_console()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("corpus", help="digitize the census corpus at 80 mm and attribute each plan's stitches")
    c.add_argument("--fixtures", default=",".join(sdc.FIXTURES))
    c.add_argument("--json", type=Path)
    p = sub.add_parser("pro", help="census the pro DSTs under a folder (names are replaced by p01, p02, ...)")
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--exclude", action="append", default=[], help="skip paths containing this folder name")
    p.add_argument("--json", type=Path)
    r = sub.add_parser("report", help="markdown tables from a corpus JSON and a pro JSON")
    r.add_argument("corpus_json", type=Path)
    r.add_argument("pro_json", type=Path)
    a = ap.parse_args(argv)

    if a.cmd == "report":
        ours = json.loads(a.corpus_json.read_text(encoding="utf-8"))
        pro = json.loads(a.pro_json.read_text(encoding="utf-8"))
        print(report(ours, pro))
        return 0

    rows = []
    if a.cmd == "corpus":
        for fx in [s for s in a.fixtures.split(",") if s]:
            rows.append(plan_record(fx))
            print(f"[done] {fx}", flush=True)
    else:
        clusters: dict[str, str] = {}
        for i, path in enumerate(pro_files(a.root, a.exclude), 1):
            top = path.relative_to(a.root).parts[0]
            cid = clusters.setdefault(top, f"c{len(clusters) + 1:02d}")
            rows.append(pro_record(f"p{i:02d}", cid, path))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rows, indent=1), encoding="utf-8")
    for r in rows:
        print(f"{r['design']}: {r['penetrations']} pens, short {r['short']}, stacked {r['near']}, union {r['union']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
