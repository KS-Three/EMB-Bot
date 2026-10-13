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
from dataclasses import dataclass, field
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


def admission(region):
    """-> (candidate or None, Why or None), `words._candidates`' per-region
    tests in the same order, before the nesting drop."""
    from digitizer_core import words as W
    from digitizer_core.textcluster import (ASPECT_RATIO_MIN, _Candidate,
                                            _skeleton_stroke_stats)
    x0, y0, x1, y1 = region.polygon.bounds
    w, h = x1 - x0, y1 - y0
    if h <= 0 or w <= 0:
        return None, Why("degenerate", None, None, detail="empty box")
    asp = w / h
    if asp < ASPECT_RATIO_MIN:
        return None, Why("aspect", asp, ASPECT_RATIO_MIN, ASPECT_RATIO_MIN / asp, "(min)")
    if asp > W.WORD_ASPECT_MAX:
        return None, Why("aspect", asp, W.WORD_ASPECT_MAX, asp / W.WORD_ASPECT_MAX, "(max)")
    if h < W.WORD_MIN_HEIGHT_MM:
        return None, Why("height_min", h, W.WORD_MIN_HEIGHT_MM, W.WORD_MIN_HEIGHT_MM / h)
    if h > W.WORD_MAX_HEIGHT_MM:
        return None, Why("height_max", h, W.WORD_MAX_HEIGHT_MM, h / W.WORD_MAX_HEIGHT_MM)
    stats = _skeleton_stroke_stats(region)
    if stats is None:
        return None, Why("no_skeleton", None, None, detail="skeleton unreadable")
    if stats.cv > W.WORD_STROKE_CV_MAX:
        return None, Why("stroke_cv", stats.cv, W.WORD_STROKE_CV_MAX,
                         stats.cv / W.WORD_STROKE_CV_MAX)
    return _Candidate(region=region, height_mm=h, width_mm=w,
                      stroke_mean_mm=stats.mean_mm, stroke_cv=stats.cv,
                      cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0), None


def link_failures(a, b, chart) -> list[Why]:
    """Every `textcluster._linked` test (with `LETTER_HEIGHT_RATIO`) that the
    pair `a`, `b` fails; empty when they link. Same four tests, same
    thresholds, read off the constants."""
    from digitizer_core import textcluster as T
    out: list[Why] = []
    lo, hi = sorted((a.height_mm, b.height_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < T.LETTER_HEIGHT_RATIO:
        out.append(Why("height_ratio", r, T.LETTER_HEIGHT_RATIO, _ratio_min(r, T.LETTER_HEIGHT_RATIO)))
    if chart is not None and not T._same_ink(a.region, b.region, chart):
        try:
            de = float(chart.delta_e(a.region.thread_index, b.region.thread_index))
        except (IndexError, TypeError, ValueError):
            de = float("nan")
        out.append(Why("ink", de, T.TEXT_CLUSTER_DELTA_E_MAX, de / T.TEXT_CLUSTER_DELTA_E_MAX))
    lo, hi = sorted((a.stroke_mean_mm, b.stroke_mean_mm))
    r = lo / hi if hi > 0 else 0.0
    if r < T.SIMILARITY_RATIO:
        out.append(Why("stroke_ratio", r, T.SIMILARITY_RATIO, _ratio_min(r, T.SIMILARITY_RATIO)))
    d = math.hypot(a.cx - b.cx, a.cy - b.cy)
    reach = T.PROXIMITY_HEIGHT_MULT * max(a.height_mm, b.height_mm)
    if d > reach:
        out.append(Why("distance", d, reach, d / reach,
                       f"({d / max(a.height_mm, b.height_mm):.2f} heights, limit "
                       f"{T.PROXIMITY_HEIGHT_MULT:g})"))
    return out


@dataclass
class Trace:
    cands: dict = field(default_factory=dict)         # sid -> _Candidate (post nesting)
    rejected: dict = field(default_factory=dict)      # sid -> Why (admission)
    fate: dict = field(default_factory=dict)          # sid -> Why (admitted, in no word)
    components: list = field(default_factory=list)    # lists of sids, first link pass
    words: list = field(default_factory=list)         # lists of sids, reading-agnostic


def trace(regions, chart=None) -> Trace:
    """`words.detect_words`, instrumented. Returns the words (as sets of
    shape ids) and the fate of every region."""
    from digitizer_core import threads
    from digitizer_core import words as W
    from digitizer_core.textcluster import (LETTER_HEIGHT_RATIO, MIN_CLUSTER_MEMBERS,
                                            _cluster, _drop_nested)
    if chart is None:
        chart = threads.CHART
    t = Trace()
    raw = []
    for r in regions:
        c, why = admission(r)
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
    for comp in _cluster(kept_n, LETTER_HEIGHT_RATIO, chart):
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
        subs = _cluster(rest, LETTER_HEIGHT_RATIO, chart) if pattern else [comp]
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


def run_fixture(name: str, widths, reference_width: float | None, log=print) -> dict:
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
    for w in widths:
        regions, chart = (ref_regions, ref_chart) if float(w) == ref_w else build(w)
        mapping = carry(ref_regions, ref_w, regions, float(w)) if float(w) != ref_w else {r.shape_id: r.shape_id for r in ref_regions}
        t = trace(regions, chart)
        rows = report_size(lines, mapping, t, chart)
        out["sizes"][str(w)] = {"regions": len(regions), "candidates": len(t.cands),
                                 "words": len(t.words), "rows": rows, "tally": tally(rows)}
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


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="+")
    ap.add_argument("--widths", type=float, nargs="+", default=list(DEFAULT_WIDTHS))
    ap.add_argument("--reference-width", type=float, default=None,
                    help="unlabelled fixtures: the width whose words are 'expected' (default: widest)")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    results = []
    for name in args.fixtures:
        res = run_fixture(name, args.widths, args.reference_width, log=lambda m: print(m, flush=True))
        print_fixture(res)
        results.append(res)
    if args.json:
        args.json.write_text(json.dumps(results, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
