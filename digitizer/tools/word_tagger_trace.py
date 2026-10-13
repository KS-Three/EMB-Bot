"""Why does the word tagger miss a glyph? Per word, per size, per rule.

`digitizer_core/words.py` (`cfg.lettering_words`) loses words at small print
sizes. This tool replays `words.detect_words` step by step on the same
regions and names, for every glyph a word should have and does not, the rule
that turned it away with the measured value beside the threshold:

  admission   aspect, height_min, height_max, stroke_cv, no_skeleton, nested
  link        height_ratio, stroke_ratio, ink, distance  (against the
              nearest-to-linking partner; one link to ANY member joins)
  after link  pattern (twins), row_split, small_component (< 3 members)
  mapping     no_region (the size's segmentation has no region there)

It mirrors `detect_words` and does not change it; `trace` returns the same
words (`tests/test_word_tagger_trace.py` pins the parity).

EXPECTED glyphs come from one of two places:

  labels      `testdata/lettering_truth.json` (shape ids at the corpus
              width), carried to another width by position: regions'
              coordinates are millimetres and scale with the target width.
  reference   unlabelled fixtures (golden_tee: its bevel has no honest letter
              call): the words the tagger finds at `--reference-width`
              (default 100), carried the same way. "Expected" then means
              "what the tagger itself reads at the reference size" and the
              table says so.

    .venv/Scripts/python -m tools.word_tagger_trace golden_tee
    .venv/Scripts/python -m tools.word_tagger_trace golden_tee --widths 50 65 80 100
    .venv/Scripts/python -m tools.word_tagger_trace --json out.json becker
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRUTH = ROOT / "testdata" / "lettering_truth.json"
DEFAULT_WIDTHS = (50, 65, 80, 100)


@dataclass
class Why:
    """One rule that refused a glyph: `value` against `threshold`, and
    `ratio` = how far over the line (>1 fails; larger is further)."""
    rule: str
    value: float | None
    threshold: float | None
    ratio: float = float("inf")
    detail: str = ""

    def text(self) -> str:
        if self.value is None:
            return f"{self.rule} {self.detail}".strip()
        return f"{self.rule} {self.value:.3f} vs {self.threshold:.3f} {self.detail}".strip()


def _ratio_min(value: float, floor: float) -> float:
    """How far under a floor: floor / value (>1 fails)."""
    return float("inf") if value <= 0 else floor / value


@dataclass(frozen=True)
class Rules:
    """Every number the tagger tests a glyph or a pair against. The defaults
    are read off the shipped constants (`base_rules`); a census variant
    overrides one of them. NOTHING here changes the shipped tagger."""
    aspect_max: float
    min_height_mm: float
    max_height_mm: float
    cv_max: float
    height_ratio: float
    stroke_ratio: float
    ink_de: float
    prox_mult: float
    min_members: int


def base_rules() -> Rules:
    from digitizer_core import textcluster as T
    from digitizer_core import words as W
    return Rules(aspect_max=W.WORD_ASPECT_MAX, min_height_mm=W.WORD_MIN_HEIGHT_MM,
                 max_height_mm=W.WORD_MAX_HEIGHT_MM, cv_max=W.WORD_STROKE_CV_MAX,
                 height_ratio=T.LETTER_HEIGHT_RATIO, stroke_ratio=T.SIMILARITY_RATIO,
                 ink_de=T.TEXT_CLUSTER_DELTA_E_MAX, prox_mult=T.PROXIMITY_HEIGHT_MULT,
                 min_members=T.MIN_CLUSTER_MEMBERS)


def admission(region, rules: Rules | None = None, memo: dict | None = None):
    """-> (candidate or None, Why or None), `words._candidates`' per-region
    tests in the same order, before the nesting drop. `memo` caches the
    skeleton read per shape id across census variants."""
    from digitizer_core.textcluster import (ASPECT_RATIO_MIN, _Candidate,
                                            _skeleton_stroke_stats)
    rules = rules or base_rules()
    x0, y0, x1, y1 = region.polygon.bounds
    w, h = x1 - x0, y1 - y0
    if h <= 0 or w <= 0:
        return None, Why("degenerate", None, None, detail="empty box")
    asp = w / h
    if asp < ASPECT_RATIO_MIN:
        return None, Why("aspect", asp, ASPECT_RATIO_MIN, ASPECT_RATIO_MIN / asp, "(min)")
    if asp > rules.aspect_max:
        return None, Why("aspect", asp, rules.aspect_max, asp / rules.aspect_max, "(max)")
    if h < rules.min_height_mm:
        return None, Why("height_min", h, rules.min_height_mm, rules.min_height_mm / h)
    if h > rules.max_height_mm:
        return None, Why("height_max", h, rules.max_height_mm, h / rules.max_height_mm)
    if memo is not None and region.shape_id in memo:
        stats = memo[region.shape_id]
    else:
        stats = _skeleton_stroke_stats(region)
        if memo is not None:
            memo[region.shape_id] = stats
    if stats is None:
        return None, Why("no_skeleton", None, None, detail="skeleton unreadable")
    if stats.cv > rules.cv_max:
        return None, Why("stroke_cv", stats.cv, rules.cv_max, stats.cv / rules.cv_max)
    return _Candidate(region=region, height_mm=h, width_mm=w,
                      stroke_mean_mm=stats.mean_mm, stroke_cv=stats.cv,
                      cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0), None


def _same_ink(a, b, chart, ink_de: float) -> bool:
    """`textcluster._same_ink` with the delta-E ceiling a parameter."""
    if a.thread_index == b.thread_index:
        return True
    try:
        return float(chart.delta_e(a.thread_index, b.thread_index)) <= ink_de
    except (IndexError, TypeError, ValueError):
        return True


def link_failures(a, b, chart, rules: Rules | None = None) -> list[Why]:
    """Every `textcluster._linked` test (with `LETTER_HEIGHT_RATIO`) that the
    pair `a`, `b` fails; empty when they link. Same four tests, same
    thresholds, read off `rules` (the shipped constants by default)."""
    rules = rules or base_rules()
    out: list[Why] = []
    lo, hi = sorted((a.height_mm, b.height_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < rules.height_ratio:
        out.append(Why("height_ratio", r, rules.height_ratio, _ratio_min(r, rules.height_ratio)))
    if chart is not None and not _same_ink(a.region, b.region, chart, rules.ink_de):
        try:
            de = float(chart.delta_e(a.region.thread_index, b.region.thread_index))
        except (IndexError, TypeError, ValueError):
            de = float("nan")
        out.append(Why("ink", de, rules.ink_de, de / rules.ink_de))
    lo, hi = sorted((a.stroke_mean_mm, b.stroke_mean_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < rules.stroke_ratio:
        out.append(Why("stroke_ratio", r, rules.stroke_ratio, _ratio_min(r, rules.stroke_ratio)))
    d = math.hypot(a.cx - b.cx, a.cy - b.cy)
    reach = rules.prox_mult * max(a.height_mm, b.height_mm)
    if d > reach:
        out.append(Why("distance", d, reach, d / reach,
                       f"({d / max(a.height_mm, b.height_mm):.2f} heights, limit "
                       f"{rules.prox_mult:g})"))
    return out


def _cluster(cands, chart, rules: Rules):
    """`textcluster._cluster` with `link_failures` as the link test: the same
    order-free union-find, so with the shipped rules it returns the same
    components (the parity test pins it)."""
    parent = {c.region.shape_id: c.region.shape_id for c in cands}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(cands)):
        for j in range(i + 1, len(cands)):
            if not link_failures(cands[i], cands[j], chart, rules):
                ri, rj = find(cands[i].region.shape_id), find(cands[j].region.shape_id)
                if ri != rj:
                    parent[ri] = rj
    groups: dict[str, list] = {}
    for c in cands:
        groups.setdefault(find(c.region.shape_id), []).append(c)
    return list(groups.values())


@dataclass
class Trace:
    cands: dict = field(default_factory=dict)         # sid -> _Candidate (post nesting)
    rejected: dict = field(default_factory=dict)      # sid -> Why (admission)
    fate: dict = field(default_factory=dict)          # sid -> Why (admitted, in no word)
    components: list = field(default_factory=list)    # lists of sids, first link pass
    words: list = field(default_factory=list)         # lists of sids, reading-agnostic


def trace(regions, chart=None, rules: Rules | None = None, memo: dict | None = None) -> Trace:
    """`words.detect_words`, instrumented. Returns the words (as sets of
    shape ids) and the fate of every region. `rules` (default: the shipped
    constants) lets the census replay the same pipeline with one number
    moved; `memo` shares skeleton reads across those replays."""
    from digitizer_core import threads
    from digitizer_core import words as W
    from digitizer_core.textcluster import _drop_nested
    if chart is None:
        chart = threads.CHART
    rules = rules or base_rules()
    MIN_CLUSTER_MEMBERS = rules.min_members

    def _cluster_(cands, ch):
        return _cluster(cands, ch, rules)
    t = Trace()
    raw = []
    for r in regions:
        c, why = admission(r, rules, memo)
        if c is None:
            t.rejected[r.shape_id] = why
        else:
            raw.append(c)
    kept_n = _drop_nested(raw)
    keep_ids = {c.region.shape_id for c in kept_n}
    for c in raw:
        if c.region.shape_id not in keep_ids:
            t.rejected[c.region.shape_id] = Why("nested", None, None, detail="box inside a larger candidate's box")
    t.cands = {c.region.shape_id: c for c in kept_n}
    in_word: set[str] = set()
    for comp in _cluster_(kept_n, chart):
        ids = sorted(c.region.shape_id for c in comp)
        t.components.append(ids)
        if len(comp) < MIN_CLUSTER_MEMBERS:
            for s in ids:
                t.fate[s] = Why("small_component", len(comp), MIN_CLUSTER_MEMBERS,
                                MIN_CLUSTER_MEMBERS / len(comp), f"(component of {len(comp)})")
            continue
        pattern = W._pattern_ids(comp)
        for s in pattern:
            t.fate[s] = Why("pattern", None, W.PATTERN_MIN_TWINS, detail="congruent twins >= limit")
        rest = [c for c in comp if c.region.shape_id not in pattern]
        subs = _cluster_(rest, chart) if pattern else [comp]
        for sub in subs:
            for row in W._split_lines(sub):
                if len(row) < MIN_CLUSTER_MEMBERS:
                    for c in row:
                        t.fate[c.region.shape_id] = Why(
                            "row_split" if len(sub) >= 2 * MIN_CLUSTER_MEMBERS else "small_component",
                            len(row), MIN_CLUSTER_MEMBERS, MIN_CLUSTER_MEMBERS / max(len(row), 1),
                            f"(row of {len(row)})")
                    continue
                ids2 = sorted(c.region.shape_id for c in row)
                t.words.append(ids2)
                in_word.update(ids2)
    for s in in_word:
        t.fate.pop(s, None)
    return t


def explain_missing(sid: str, partners: list[str], t: Trace, chart) -> Why:
    """Why glyph `sid` is in no word. Rejected at admission, or lost after
    linking: that fate. Otherwise (admitted, linked to too few): the
    nearest-to-linking partner among `partners` (the other members the word
    should have, admitted ones first), reported with the pair's failing
    link rules; the dominant one is the one furthest over its line."""
    if sid in t.rejected:
        return t.rejected[sid]
    me = t.cands[sid]
    pool = [p for p in partners if p in t.cands and p != sid] or [p for p in t.cands if p != sid]
    best = None
    for p in pool:
        fails = link_failures(me, t.cands[p], chart)
        key = (len(fails), max((f.ratio for f in fails), default=0.0))
        if best is None or key < best[0]:
            best = (key, p, fails)
    if best is not None and best[2]:
        dom = max(best[2], key=lambda f: f.ratio)
        extra = [f.rule for f in best[2] if f is not dom]
        dom = Why(dom.rule, dom.value, dom.threshold, dom.ratio,
                  (dom.detail + f" [partner {best[1]}" + (f"; also {','.join(extra)}" if extra else "") + "]").strip())
        return dom
    if sid in t.fate:
        return t.fate[sid]
    if best is not None:
        return Why("link_ok", None, None, 0.0, f"links to {best[1]} but the component is under the word minimum")
    return Why("no_partner", None, None, detail="no other candidate in the design")


# --- expected glyphs and their carry across sizes ----------------------------

def carry(ref_regions, ref_width: float, regions, width: float) -> dict[str, str | None]:
    """ref shape id -> shape id at `width` whose centre is nearest the
    reference centre scaled by width / ref_width (coordinates are mm and
    scale with the target width), one-to-one, greedy by distance; None when
    nothing sits within half a scaled height of it, or the size is off by
    more than 2x."""
    k = width / ref_width
    cs = [(r.shape_id, r.polygon.bounds) for r in regions]
    pairs = []
    for rr in ref_regions:
        x0, y0, x1, y1 = rr.polygon.bounds
        rcx, rcy, rh = (x0 + x1) / 2 * k, (y0 + y1) / 2 * k, (y1 - y0) * k
        for sid, (a0, b0, a1, b1) in cs:
            h = b1 - b0
            d = math.hypot((a0 + a1) / 2 - rcx, (b0 + b1) / 2 - rcy)
            if d <= 0.5 * max(rh, h) and 0.5 <= h / max(rh, 1e-9) <= 2.0:
                pairs.append((d, rr.shape_id, sid))
    out: dict[str, str | None] = {rr.shape_id: None for rr in ref_regions}
    used: set[str] = set()
    for d, a, b in sorted(pairs):
        if out[a] is None and b not in used:
            out[a] = b
            used.add(b)
    return out


def expected_lines(name: str, ref_regions, chart) -> tuple[dict[str, list[str]], str]:
    """-> ({line name: [ref shape ids]}, source). Labels where the truth file
    has the fixture and every id is in this generation; otherwise the words
    the tagger finds on `ref_regions`."""
    truth = json.loads(TRUTH.read_text())["fixtures"].get(name)
    have = {r.shape_id for r in ref_regions}
    if truth and all(s in have for ids in truth["lines"].values() for s in ids):
        return {k: list(v) for k, v in truth["lines"].items()}, "labels"
    t = trace(ref_regions, chart)
    return {f"word{i}": ids for i, ids in enumerate(t.words)}, "reference"


def report_size(lines: dict[str, list[str]], mapping: dict[str, str | None], t: Trace, chart) -> list[dict]:
    """One row per expected line at one size."""
    rows = []
    word_of = {s: i for i, ids in enumerate(t.words) for s in ids}
    for line, ref_ids in lines.items():
        now = [mapping.get(s) for s in ref_ids]
        present = [s for s in now if s]
        votes: dict[int, int] = {}
        for s in present:
            if s in word_of:
                votes[word_of[s]] = votes.get(word_of[s], 0) + 1
        best = max(votes, key=lambda k: (votes[k], -k)) if votes else None
        found = votes[best] if best is not None else 0
        in_best = set(t.words[best]) if best is not None else set()
        missing = []
        for ref_id, s in zip(ref_ids, now):
            if s is None:
                missing.append({"ref": ref_id, "shape": None, "why": Why("no_region", None, None, detail="no region at this size").text(), "rule": "no_region"})
            elif s not in in_best:
                w = explain_missing(s, [p for p in present if p != s], t, chart)
                missing.append({"ref": ref_id, "shape": s, "why": w.text(), "rule": w.rule})
        rows.append({"line": line, "expected": len(ref_ids), "found": found,
                     "members": len(in_best), "missing": missing})
    return rows


def tally(rows: list[dict]) -> dict[str, int]:
    c: dict[str, int] = {}
    for r in rows:
        for m in r["missing"]:
            c[m["rule"]] = c.get(m["rule"], 0) + 1
    return dict(sorted(c.items(), key=lambda kv: (-kv[1], kv[0])))


# --- the census: one number moved at a time, scored against the truth carry --

# name -> overrides on `Rules`. Single-number relaxations first (the smallest
# change that could join a third glyph is one of these); `--variant` adds more.
VARIANTS: dict[str, dict] = {
    "aspect_max=2.3": {"aspect_max": 2.3},
    "aspect_max=2.6": {"aspect_max": 2.6},
    "aspect_max=3.0": {"aspect_max": 3.0},
    "height_ratio=0.7": {"height_ratio": 0.7},
    "height_ratio=0.6": {"height_ratio": 0.6},
    "height_ratio=0.5": {"height_ratio": 0.5},
    "stroke_ratio=0.4": {"stroke_ratio": 0.4},
    "stroke_ratio=0.3": {"stroke_ratio": 0.3},
    "ink_de=30": {"ink_de": 30.0},
    "ink_de=45": {"ink_de": 45.0},
    "ink_de=80": {"ink_de": 80.0},
    "prox_mult=3.5": {"prox_mult": 3.5},
    "prox_mult=4": {"prox_mult": 4.0},
    "prox_mult=5": {"prox_mult": 5.0},
    "cv_max=0.65": {"cv_max": 0.65},
    "cv_max=0.7": {"cv_max": 0.7},
    "cv_max=0.8": {"cv_max": 0.8},
    "min_height_mm=0.8": {"min_height_mm": 0.8},
    "min_height_mm=0.6": {"min_height_mm": 0.6},
    "min_members=2": {"min_members": 2},
}


def parse_variant(spec: str) -> tuple[str, dict]:
    """`key=val,key=val` -> (spec, overrides)."""
    ov = {}
    for part in spec.split(","):
        k, v = part.split("=")
        ov[k.strip()] = int(v) if k.strip() == "min_members" else float(v)
    return spec, ov


def _truth_roles(lines: dict[str, list[str]], mapping: dict[str, str | None],
                 ignore_ref: set[str] | None = None) -> tuple[dict[str, str], set[str]]:
    """-> ({size shape id: line name} for the expected glyphs, {size ids
    scored neither way}); both carried to this size by `mapping`."""
    line_of = {}
    for line, ids in lines.items():
        for s in ids:
            m = mapping.get(s)
            if m:
                line_of[m] = line
    ign = {mapping[s] for s in (ignore_ref or ()) if mapping.get(s)}
    return line_of, ign


def score_words(words, base_words, line_of, ignore, lines_total: dict[str, int]) -> dict:
    """A variant's words against the truth carry and against the shipped
    tagger's own words on the same regions.

      gained     expected glyphs in a variant word that no shipped word held
      lost       the reverse (a rule change that un-joins something)
      stray      NEW non-letters in a word (not in line_of, not ignored, not
                 in a shipped word): a false join
      crossline  NEW words whose letters come from two or more expected lines
      complete   expected lines whose every glyph sits in ONE word
    """
    inw = {s for w in words for s in w}
    inb = {s for w in base_words for s in w}
    base_sets = {tuple(w) for w in base_words}
    gained = sorted(s for s in inw - inb if s in line_of)
    lost = sorted(s for s in inb - inw if s in line_of)
    stray = sorted(s for s in inw - inb if s not in line_of and s not in ignore)
    cross = 0
    for w in words:
        if tuple(w) in base_sets:
            continue
        if len({line_of[s] for s in w if s in line_of}) > 1:
            cross += 1
    complete = 0
    for line, n in lines_total.items():
        members = {s for s, ln in line_of.items() if ln == line}
        if len(members) == n and any(members <= set(w) for w in words):
            complete += 1
    return {"words": len(words), "gained": gained, "lost": lost, "stray": stray,
            "crossline": cross, "complete": complete}


def run_fixture(name: str, widths, reference_width: float | None, log=print,
                variants: dict | None = None) -> dict:
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation
    from digitizer_core.threads import chart_for
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    fname, corpus_w, garment = REAL_ART[name]
    path = ROOT / "testdata" / fname

    def build(w):
        cfg = PipelineConfig(target_width_mm=w, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
        return build_generation(str(path), cfg).regions, chart_for(cfg)

    has_labels = name in json.loads(TRUTH.read_text())["fixtures"]
    ref_w = float(corpus_w) if has_labels else float(reference_width or max(widths))
    ref_regions, ref_chart = build(ref_w)
    lines, source = expected_lines(name, ref_regions, ref_chart)
    if source == "reference":
        ref_w = float(reference_width or max(widths))
    out = {"fixture": name, "source": source, "reference_width": ref_w, "sizes": {}}
    ignore_ref = set(json.loads(TRUTH.read_text())["fixtures"].get(name, {}).get("ignore", []))
    lines_total = {k: len(v) for k, v in lines.items()}
    base = base_rules()
    for w in widths:
        regions, chart = (ref_regions, ref_chart) if float(w) == ref_w else build(w)
        mapping = carry(ref_regions, ref_w, regions, float(w)) if float(w) != ref_w else {r.shape_id: r.shape_id for r in ref_regions}
        memo: dict = {}
        t = trace(regions, chart, memo=memo)
        rows = report_size(lines, mapping, t, chart)
        entry = {"regions": len(regions), "candidates": len(t.cands),
                 "words": len(t.words), "rows": rows, "tally": tally(rows),
                 "word_ids": t.words}
        if variants:
            line_of, ign = _truth_roles(lines, mapping, ignore_ref)
            entry["line_of"] = line_of
            entry["base_score"] = score_words(t.words, t.words, line_of, ign, lines_total)
            entry["variants"] = {}
            for vname, ov in variants.items():
                tv = trace(regions, chart, rules=replace(base, **ov), memo=memo)
                sc = score_words(tv.words, t.words, line_of, ign, lines_total)
                sc["word_ids"] = tv.words
                entry["variants"][vname] = sc
        out["sizes"][str(w)] = entry
        log(f"{name} {w:g} mm: {len(regions)} regions, {len(t.cands)} candidates, {len(t.words)} words")
    return out


def print_fixture(res: dict) -> None:
    print(f"\n== {res['fixture']}  (expected glyphs from {res['source']}"
          + (f" at {res['reference_width']:g} mm" if res["source"] == "reference" else "") + ")")
    for w, s in res["sizes"].items():
        print(f"-- {w} mm: {s['regions']} regions, {s['candidates']} candidates, {s['words']} words; "
              f"refusals: {s['tally'] or 'none'}")
        for r in s["rows"]:
            tag = "ok" if not r["missing"] else f"MISSING {len(r['missing'])}"
            print(f"   {r['line']:18s} expected {r['expected']:2d}  found {r['found']:2d}  "
                  f"word {r['members']:2d}  {tag}")
            for m in r["missing"]:
                print(f"       {m['ref']} -> {m['shape'] or '-':10s} {m['why']}")


def refusal_table(results: list[dict]) -> str:
    """Per-size refusal tally pooled over fixtures: rule -> count of expected
    glyphs it kept out of a word, one column per width."""
    widths = sorted({float(w) for r in results for w in r["sizes"]})
    rules = sorted({k for r in results for s in r["sizes"].values() for k in s["tally"]})
    tot = {w: sum(len(row["missing"]) for r in results for ww, s in r["sizes"].items()
                  if float(ww) == w for row in s["rows"]) for w in widths}
    exp = {w: sum(row["expected"] for r in results for ww, s in r["sizes"].items()
                  if float(ww) == w for row in s["rows"]) for w in widths}
    head = "| rule | " + " | ".join(f"{w:g} mm" for w in widths) + " |"
    lines = [head, "|---|" + "---|" * len(widths)]
    for k in sorted(rules, key=lambda k: -sum(s["tally"].get(k, 0) for r in results
                                              for s in r["sizes"].values())):
        cells = [str(sum(s["tally"].get(k, 0) for r in results for ww, s in r["sizes"].items()
                         if float(ww) == w)) for w in widths]
        lines.append(f"| {k} | " + " | ".join(cells) + " |")
    lines.append("| **glyphs missing / expected** | " + " | ".join(f"{tot[w]} / {exp[w]}" for w in widths) + " |")
    return "\n".join(lines)


def census_table(results: list[dict]) -> str:
    """Per variant, pooled over every fixture and size: expected glyphs
    gained / lost against the shipped tagger, NEW stray non-letters in words
    (false joins), NEW cross-line words, and the change in complete lines."""
    names = []
    for r in results:
        for s in r["sizes"].values():
            for v in s.get("variants", {}):
                if v not in names:
                    names.append(v)
    rows = ["| variant | gained | lost | new stray | new cross-line | lines completed (delta) | zero false joins |",
            "|---|---|---|---|---|---|---|"]
    for v in names:
        g = lo = st = cr = dc = 0
        for r in results:
            for s in r["sizes"].values():
                sc = s.get("variants", {}).get(v)
                if sc is None:
                    continue
                g += len(sc["gained"])
                lo += len(sc["lost"])
                st += len(sc["stray"])
                cr += sc["crossline"]
                dc += sc["complete"] - s["base_score"]["complete"]
        rows.append(f"| {v} | {g} | {lo} | {st} | {cr} | {dc:+d} | {'yes' if st == 0 and cr == 0 else 'NO'} |")
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*")
    ap.add_argument("--widths", type=float, nargs="+", default=list(DEFAULT_WIDTHS))
    ap.add_argument("--reference-width", type=float, default=None,
                    help="unlabelled fixtures: the width whose words are 'expected' (default: widest)")
    ap.add_argument("--json", type=Path)
    ap.add_argument("--census", action="store_true",
                    help="also replay the tagger with each VARIANTS rule relaxed and score the "
                         "false joins against the truth carry")
    ap.add_argument("--variant", action="append", default=[], metavar="k=v[,k=v]",
                    help="add a census variant (keys: aspect_max min_height_mm cv_max height_ratio "
                         "stroke_ratio ink_de prox_mult min_members); implies --census")
    ap.add_argument("--summarize", type=Path, nargs="+", metavar="JSON",
                    help="pool --json outputs and print the refusal and census tables")
    args = ap.parse_args(argv)
    if args.summarize:
        results = [r for p in args.summarize for r in json.loads(p.read_text())]
        print(refusal_table(results))
        if any(s.get("variants") for r in results for s in r["sizes"].values()):
            print()
            print(census_table(results))
        return 0
    variants = None
    if args.census or args.variant:
        variants = dict(VARIANTS) if args.census else {}
        variants.update(parse_variant(v) for v in args.variant)
    results = []
    for name in args.fixtures:
        res = run_fixture(name, args.widths, args.reference_width,
                          log=lambda m: print(m, flush=True), variants=variants)
        print_fixture(res)
        results.append(res)
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
