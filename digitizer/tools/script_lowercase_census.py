"""Script and lowercase never reach the Column lane. Which tagger refuses each glyph, and why?

The Column lane (`cfg.lettering_columns`, ON) takes a shape when
`columns.is_lettering` says so: `text_candidate` (the text cluster) or
`lettering_group` (the house-angle group), less its three guards. Under
`cfg.lettering_words` (L1, OFF) it reads `word_id` instead. This census
answers, per fixture and per glyph, for the repo's four lettering fixtures
(becker, bridge, tires, golden_tee):

  * is the glyph tagged by the text cluster, the house group, L1, and does
    the lane take it (and, when a guard turns a tagged glyph away, which);
  * for every tagger that does NOT tag it, the rule that refused it with the
    measured value beside its threshold.

The reasons come from `tools/word_tagger_trace.py` (`admission`,
`link_failures`, `explain_missing`) run with each tagger's OWN constants:

  text_cluster   rescued door (cv 0.32, aspect 0.05-1.4, ratio 0.5, no ink),
                 then the letter door (height 1.5-60 mm, cv 0.55, aspect
                 0.05-1.4, ratio 0.8, ink 20), `_drop_nested`, >= 3 members
  house_group    aspect 0.05-1.4 and a skeleton, ratio 0.8, no ink link,
                 `_drop_nested`, >= 3 members
  words          `word_tagger_trace.base_rules()` (L1: aspect <= 2.0, cv 0.60,
                 ink 20, pattern, row split)

It mirrors the taggers and changes none of them. `parity` in the output
says, per fixture and tagger, whether the mirror's members equal the set the
shipped pass actually wrote (`text_candidate`, `lettering_group`, or the
words `words.detect_words` returns); a False there means the reasons describe
a different tagger and must not be quoted.

GLYPHS are the hand-labelled letters (`testdata/lettering_truth.json`) where
the fixture has labels and every id is still in this generation (otherwise
the fixture is reported STALE and read as unlabelled). golden_tee has no
labels (its bevel has no honest letter call): its glyphs are every region
ANY tagger tags, and the table says so. Regions tagged but not labelled are
listed as `tagged_not_letter`.

AGREEMENT is Cohen's kappa for "this region is a letter" with a 95%
percentile bootstrap over regions (resampled pooled across the labelled
fixtures, seed 0, 2000 draws), never a raw percentage. The pool is three
fixtures and a few dozen regions; read the interval, not the point.

    .venv/Scripts/python -m tools.script_lowercase_census
    .venv/Scripts/python -m tools.script_lowercase_census tires bridge
    .venv/Scripts/python -m tools.script_lowercase_census --json out.json golden_tee
    .venv/Scripts/python -m tools.script_lowercase_census --table out.txt
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools import word_tagger_trace as WT  # noqa: E402
from tools._console import utf8_console  # noqa: E402

TRUTH = ROOT / "testdata" / "lettering_truth.json"
FIXTURES = ("becker", "bridge", "tires", "golden_tee")
TAGGERS = ("text_cluster", "house_group", "words")
PREDICTORS = TAGGERS + ("lane",)
BOOTSTRAP = 2000

# What each script glyph reads as, read off the artwork by eye (2026-10-14,
# the regions drawn with their ids over `testdata/logo_script_tires.png` and
# `photo/logo_bridge_bar.jpg`), so the table can say "ires" and not a shape
# id. A fixture whose ids are not all present gets no read, never a wrong one.
# Everything not named here is read as `KIND[fixture]`.
NOTES: dict[str, dict[str, str]] = {
    "tires": {"S1f2e2d7b": "T stem", "S8edf1545": "T crossbar swash",
              "S27641282": "i dot", "Sf272c1de": "ires, joined"},
    "bridge": {"S71ddac97": "Bridge"},
}
KIND = {"becker": "caps", "bridge": "caps", "tires": "script", "golden_tee": "caps"}
SCRIPT_IDS = {"bridge": {"S71ddac97"}}     # script glyphs inside an otherwise-caps fixture


def text_cluster_rules():
    """The text cluster's LETTER door (`textcluster._letter_candidates`)."""
    return replace(WT.base_rules(), aspect_max=1.4, min_height_mm=1.5, max_height_mm=60.0, cv_max=0.55)


def rescued_rules():
    """The text cluster's RESCUED door (`textcluster._candidates`): the
    calibration on rescued blobs, ratio 0.5, no height bounds, no ink link
    (it is run with `chart=None`)."""
    return replace(WT.base_rules(), aspect_max=1.4, min_height_mm=0.0, max_height_mm=math.inf,
                   cv_max=0.32, height_ratio=0.5, ink_de=math.inf)


def house_rules():
    """`textcluster._lettering_groups`: aspect and a skeleton, ratio 0.8, no
    ink, no height or CV screen (run with `chart=None`)."""
    return replace(WT.base_rules(), aspect_max=1.4, min_height_mm=0.0, max_height_mm=math.inf,
                   cv_max=math.inf, ink_de=math.inf)


def _round(regions, rules, chart, memo, keep):
    """One door: admission, nesting drop, link, size >= min. -> (Trace, kept
    candidates after nesting, components). Fills `t.rejected` / `t.nested` /
    `t.cands` like `word_tagger_trace.trace`, without its pattern and row
    steps (the old taggers have neither)."""
    t = WT.Trace()
    raw = []
    for r in regions:
        if not keep(r):
            continue
        c, why = WT.admission(r, rules, memo)
        if c is None:
            t.rejected[r.shape_id] = why
        else:
            raw.append(c)
    kept = WT.drop_nested(raw, rules, chart)
    keep_ids = {c.region.shape_id for c in kept}
    for c in raw:
        if c.region.shape_id not in keep_ids:
            info = WT.nest_info(c, raw, chart)
            t.nested[c.region.shape_id] = info
            t.rejected[c.region.shape_id] = WT.Why(
                "nested", None, None,
                detail=f"box inside a larger candidate's box [host {info['host']}: "
                       f"h {info['host_h']:.2f} vs {info['h']:.2f} mm, aspect {info['host_aspect']:.2f}]")
    t.cands = {c.region.shape_id: c for c in kept}
    return t, kept


def _link_and_fate(t, kept, rules, chart):
    """Components of `kept` under `rules`; a component under the minimum is
    every member's `small_component` fate. -> the components >= min."""
    comps = WT._cluster(kept, chart, rules)
    big = []
    for comp in comps:
        ids = sorted(c.region.shape_id for c in comp)
        t.components.append(ids)
        if len(comp) < rules.min_members:
            for s in ids:
                t.fate[s] = WT.Why("small_component", len(comp), rules.min_members,
                                   rules.min_members / len(comp), f"(component of {len(comp)})")
        else:
            big.append(comp)
    return big


def house_group_trace(regions, memo=None):
    """`_lettering_groups`, instrumented (no chart: it has no ink link)."""
    rules = house_rules()
    t, kept = _round(regions, rules, None, memo, lambda r: True)
    for comp in _link_and_fate(t, kept, rules, None):
        t.words.append(sorted(c.region.shape_id for c in comp))
    return t


def text_cluster_trace(regions, chart, memo=None):
    """`detect_text_clusters`, instrumented: the rescued door clustered on its
    own first (no ink, ratio 0.5), then the letter door joined by whatever the
    first round left, clustered with the one-ink link and ratio 0.8. A
    rescued region its own door refuses never reaches the second."""
    rr, lr = rescued_rules(), text_cluster_rules()
    t1, kept1 = _round(regions, rr, None, memo, lambda r: bool(r.meta.get("rescued_small_shape")))
    taken: set[str] = set()
    t = WT.Trace()
    for sid, why in t1.rejected.items():
        t.rejected[sid] = WT.Why(why.rule, why.value, why.threshold, why.ratio,
                                 (why.detail + " (rescued door)").strip())
    for comp in _link_and_fate(t1, kept1, rr, None):
        ids = sorted(c.region.shape_id for c in comp)
        t.words.append(ids)
        taken.update(ids)
    # fates from round 1 that round 2 may still overturn are not carried:
    # the leftover rescued candidates re-enter the pool below
    raw = [c for c in kept1 if c.region.shape_id not in taken]
    for r in regions:
        if r.meta.get("rescued_small_shape"):
            continue
        c, why = WT.admission(r, lr, memo)
        if c is None:
            t.rejected[r.shape_id] = why
        else:
            raw.append(c)
    kept = WT.drop_nested(raw, lr, chart)
    keep_ids = {c.region.shape_id for c in kept}
    for c in raw:
        if c.region.shape_id not in keep_ids:
            info = WT.nest_info(c, raw, chart)
            t.nested[c.region.shape_id] = info
            t.rejected[c.region.shape_id] = WT.Why(
                "nested", None, None,
                detail=f"box inside a larger candidate's box [host {info['host']}: "
                       f"h {info['host_h']:.2f} vs {info['h']:.2f} mm, aspect {info['host_aspect']:.2f}]")
    t.cands = {c.region.shape_id: c for c in kept}
    t.cands.update({c.region.shape_id: c for c in kept1 if c.region.shape_id in taken})
    for comp in _link_and_fate(t, kept, lr, chart):
        t.words.append(sorted(c.region.shape_id for c in comp))
    return t


LINK_RULES = {"text_cluster": text_cluster_rules, "house_group": house_rules, "words": WT.base_rules}


def words_trace(regions, chart, memo=None):
    """L1 itself, `word_tagger_trace.trace` with the shipped rules."""
    return WT.trace(regions, chart, memo=memo)


def lane_verdict(region, cfg) -> tuple[bool, str | None]:
    """`columns.is_lettering`, with the reason a TAGGED shape is turned away:
    -> (lane takes it, guard that refused it or None). The parity test pins
    this against `is_lettering` itself."""
    from digitizer_core.columns import is_drawing_fragment, is_solid_blob
    m = region.meta or {}
    if getattr(cfg, "lettering_words", False):
        tagged = bool(m.get("word_id"))
    else:
        tagged = bool(m.get("text_candidate") or m.get("lettering_group"))
    if not tagged:
        return False, None
    if getattr(cfg, "lettering_columns_skip_blobs", False) and is_solid_blob(region.polygon):
        return False, "skip_blobs"
    if getattr(cfg, "lettering_columns_ink_link", False) and m.get("lettering_ink_stray"):
        return False, "ink_stray"
    if (getattr(cfg, "lettering_columns_icon_guard", False) and m.get("lettering_group")
            and not m.get("text_candidate") and is_drawing_fragment(region.polygon)):
        return False, "icon_guard"
    return True, None


def census_regions(name: str, regions, chart, cfg, truth_fixture: dict | None) -> dict:
    """The census of one fixture's regions (as `build_generation` returns
    them, tagged by the shipped passes). Runs `words.tag_words` on them
    afterwards to read the L1 verdict (`cfg.lettering_words` is OFF in the
    build); the old taggers' keys are read first and are not touched."""
    from digitizer_core import words as W
    from digitizer_core.columns import is_lettering
    from digitizer_core.textcluster import _skeleton_stroke_stats

    by_id = {r.shape_id: r for r in regions}
    old_tc = {r.shape_id for r in regions if r.meta.get("text_candidate")}
    old_hg = {r.shape_id for r in regions if r.meta.get("lettering_group")}
    lane = {}
    for r in regions:
        take, guard = lane_verdict(r, cfg)
        assert take == is_lettering(r, cfg), (name, r.shape_id)
        lane[r.shape_id] = (take, guard)
    detected = W.detect_words(regions, chart=chart)
    l1 = {r.shape_id for w in detected for r in w.members}
    W.tag_words(regions, chart=chart)
    wcfg = replace(cfg, lettering_words=True)
    lane_words = {r.shape_id: lane_verdict(r, wcfg) for r in regions}

    memo: dict = {}
    traces = {"text_cluster": text_cluster_trace(regions, chart, memo),
              "house_group": house_group_trace(regions, memo),
              "words": words_trace(regions, chart, memo)}
    sets = {"text_cluster": old_tc, "house_group": old_hg, "words": l1}
    mirror = {k: {s for w in traces[k].words for s in w} for k in TAGGERS}
    parity = {k: mirror[k] == sets[k] for k in TAGGERS}

    stale = False
    lines: dict[str, list[str]] = {}
    ignore: set[str] = set()
    if truth_fixture:
        ids = [s for v in truth_fixture["lines"].values() for s in v]
        stale = any(s not in by_id for s in ids)
        if not stale:
            lines = {k: list(v) for k, v in truth_fixture["lines"].items()}
            ignore = set(truth_fixture.get("ignore", []))
    labelled = bool(lines)
    line_of = {s: ln for ln, ids in lines.items() for s in ids}
    if labelled:
        glyph_ids = sorted(line_of)
    else:
        glyph_ids = sorted(old_tc | old_hg | l1)

    notes = NOTES.get(name, {})
    if any(s not in by_id for s in notes):
        notes = {}

    def kind_of(sid):
        return "script" if sid in SCRIPT_IDS.get(name, ()) else KIND.get(name, "?")

    def partners(sid):
        ln = line_of.get(sid)
        return [p for p in lines.get(ln, []) if p != sid] if ln else []

    def row(sid):
        r = by_id[sid]
        x0, y0, x1, y1 = r.polygon.bounds
        h, w = y1 - y0, x1 - x0
        st = _skeleton_stroke_stats(r)
        tags = {k: sid in sets[k] for k in TAGGERS}
        refused = {}
        for k in TAGGERS:
            if tags[k]:
                continue
            why = WT.explain_missing(sid, partners(sid), traces[k],
                                     None if k == "house_group" else chart, LINK_RULES[k]())
            refused[k] = {"rule": why.rule, "text": why.text()}
        take, guard = lane[sid]
        return {"shape": sid, "line": line_of.get(sid), "read": notes.get(sid), "kind": kind_of(sid), "h_mm": round(h, 2), "w_mm": round(w, 2),
                "aspect": round(w / h, 2) if h > 0 else None,
                "cv": None if st is None else round(st.cv, 3),
                "stroke_mm": None if st is None else round(2 * st.mean_mm, 2),
                "rescued": bool(r.meta.get("rescued_small_shape")),
                "tagged": tags, "lane": take, "lane_guard": guard,
                "lane_if_words": lane_words[sid][0], "refused": refused}

    glyphs = [row(s) for s in glyph_ids]
    gset = set(glyph_ids)
    not_letter = [row(s) for s in sorted((old_tc | old_hg | l1) - gset - ignore)] if labelled else []
    # every region not listed above: the L1 refusal tally (what the rest of the
    # design is turned away for), so the glyph table is not read in isolation
    rest: dict[str, int] = {}
    for r in regions:
        s = r.shape_id
        if s in gset or s in (old_tc | old_hg | l1) or s in ignore:
            continue
        rule = WT.explain_missing(s, [], traces["words"], chart).rule
        rest[rule] = rest.get(rule, 0) + 1
    # every region L1 refuses at the aspect ceiling: the population a wide-glyph
    # door would have to separate the script word from (see `wide_refused` in the PR)
    wide = []
    for sid, why in traces["words"].rejected.items():
        if why.rule == "aspect" and "(max)" in why.detail:
            g = row(sid)
            g["labelled_letter"] = sid in gset
            wide.append(g)
    wide.sort(key=lambda g: -g["aspect"])
    scored = [r.shape_id for r in regions if r.shape_id not in ignore]
    pred = {k: [s in sets[k] for s in scored] for k in TAGGERS}
    pred["lane"] = [lane[s][0] for s in scored]
    return {"fixture": name, "regions": len(regions), "source": "labels" if labelled else "reference",
            "stale": stale, "parity": parity,
            "admitted": {k: len(traces[k].cands) for k in TAGGERS}, "glyphs": glyphs, "tagged_not_letter": not_letter, "wide_refused": wide,
            "rest_refusals": dict(sorted(rest.items(), key=lambda kv: (-kv[1], kv[0]))),
            "scored": scored, "truth": [s in gset for s in scored] if labelled else None,
            "pred": pred}


# --- agreement: kappa with a CI, never a raw percentage -----------------------

def kappa_ci(truth: list[bool], pred: list[bool], draws: int = BOOTSTRAP, seed: int = 0):
    """Cohen's kappa and a 95% percentile bootstrap over items; the interval
    is None when fewer than 20 draws are defined."""
    import numpy as np
    from tools.word_tagger_eval import kappa
    k = kappa(truth, pred)
    t, p = np.asarray(truth, bool), np.asarray(pred, bool)
    rng = np.random.default_rng(seed)
    ks = []
    for _ in range(draws):
        i = rng.integers(0, len(t), len(t))
        v = kappa(t[i].tolist(), p[i].tolist())
        if v is not None:
            ks.append(v)
    ci = None if len(ks) < 20 else [float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))]
    return k, ci


def pooled_kappa(results: list[dict]) -> dict:
    """Per predictor, pooled over the LABELLED non-stale fixtures: kappa, CI,
    and the tp / fp / fn counts."""
    lab = [r for r in results if r["truth"] is not None]
    out = {}
    if not lab:
        return out
    t = [x for r in lab for x in r["truth"]]
    for k in PREDICTORS:
        p = [x for r in lab for x in r["pred"][k]]
        kap, ci = kappa_ci(t, p)
        out[k] = {"kappa": kap, "ci95": ci,
                  "tp": sum(a and b for a, b in zip(t, p)), "fp": sum(b and not a for a, b in zip(t, p)),
                  "fn": sum(a and not b for a, b in zip(t, p)), "n": len(t), "letters": sum(t),
                  "fixtures": [r["fixture"] for r in lab]}
    return out


# --- the build and the table --------------------------------------------------

def build(name: str):
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation
    from digitizer_core.threads import chart_for
    from tools.thin_strokes import REAL_ART, STUDIO_MAX_COLORS
    fname, width, garment = REAL_ART[name]
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=STUDIO_MAX_COLORS)
    regions = build_generation(str(ROOT / "testdata" / fname), cfg).regions
    return regions, chart_for(cfg), cfg, width


def run(names, log=print) -> list[dict]:
    truth = json.loads(TRUTH.read_text())["fixtures"]
    out = []
    for name in names:
        regions, chart, cfg, width = build(name)
        res = census_regions(name, regions, chart, cfg, truth.get(name))
        res["width_mm"] = width
        log(f"{name} {width:g} mm: {res['regions']} regions, {len(res['glyphs'])} glyphs")
        out.append(res)
    return out


def _mark(g, k):
    return "Y" if g["tagged"][k] else "."


def _short(g, k):
    r = g["refused"].get(k)
    if r is None:
        return ""
    text = r["text"]
    return text if len(text) <= 70 else text[:67] + "..."


def format_table(res: dict) -> list[str]:
    """One fixture, one row per glyph. TC text cluster, HG house group, L1
    words, LN the Column lane today (default cfg), L1+LN the lane under
    `lettering_words`. Y tagged, . not. A refused tagger's rule follows."""
    out = [f"== {res['fixture']} at {res['width_mm']:g} mm: {res['regions']} regions, glyphs from "
           f"{res['source']}{' (STALE labels)' if res['stale'] else ''}; parity "
           + " ".join(f"{k}={'ok' if v else 'DIFF'}" for k, v in res["parity"].items())
           + "; candidates admitted past admission and nesting "
           + " ".join(f"{k}={v}" for k, v in res["admitted"].items())]
    out.append(f"{'shape':10s} {'line':18s} {'read':16s} {'kind':6s} {'h':>5s} {'w':>5s} {'asp':>5s} {'cv':>5s} "
               f"TC HG L1 LN L1+LN  refusals")
    for g in res["glyphs"] + res["tagged_not_letter"]:
        mark = "" if g in res["glyphs"] else " [tagged, not a letter]"
        lane = "Y" if g["lane"] else ("." if not g["lane_guard"] else g["lane_guard"][:2])
        line = (f"{(g['line'] or '-')[:18]:18s} {(g['read'] or '-')[:16]:16s} "
                f"{g['kind'][:6]:6s}")
        out.append(f"{g['shape']:10s} {line} {g['h_mm']:5.1f} {g['w_mm']:5.1f} "
                   f"{g['aspect'] if g['aspect'] is not None else 0:5.2f} "
                   f"{g['cv'] if g['cv'] is not None else -1:5.2f} "
                   f" {_mark(g, 'text_cluster')}  {_mark(g, 'house_group')}  {_mark(g, 'words')}  "
                   f"{lane:2s}  {'Y' if g['lane_if_words'] else '.'}{mark}")
        for k, tag in (("text_cluster", "TC"), ("house_group", "HG"), ("words", "L1")):
            if k in g["refused"]:
                out.append(f"{'':10s}   {tag}: {_short(g, k)}")
    if res["wide_refused"]:
        out.append("   regions L1 refuses at the aspect ceiling (shape, h x w mm, aspect, cv, stroke mm, labelled):")
        for g in res["wide_refused"]:
            out.append(f"      {g['shape']:10s} {g['h_mm']:5.1f} x {g['w_mm']:5.1f}  asp {g['aspect']:5.2f}  "
                       f"cv {g['cv'] if g['cv'] is not None else -1:5.2f}  stroke {g['stroke_mm'] or 0:5.2f}  "
                       f"{'LETTER' if g['labelled_letter'] else '-'}")
    if res["rest_refusals"]:
        out.append("   other regions, L1 refusal tally: "
                   + ", ".join(f"{k} {v}" for k, v in res["rest_refusals"].items()))
    return out


def format_summary(results: list[dict], pooled: dict) -> list[str]:
    out = []
    lab = [r for r in results if r["source"] == "labels"]
    if lab:
        out.append("\nfirst refusing rule per tagger, labelled letters no tagger-side tag reaches:")
        for k in TAGGERS:
            tally: dict[str, int] = {}
            for r in lab:
                for g in r["glyphs"]:
                    if k in g["refused"]:
                        rule = g["refused"][k]["rule"]
                        tally[rule] = tally.get(rule, 0) + 1
            out.append(f"  {k:13s} " + (", ".join(f"{a} {b}" for a, b in
                       sorted(tally.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"))
    if pooled:
        first = next(iter(pooled.values()))
        out.append(f"\nkappa 'is a letter', pooled over {', '.join(first['fixtures'])} "
                   f"({first['n']} regions, {first['letters']} labelled letters), "
                   f"region bootstrap 95% CI:")
        for k, s in pooled.items():
            ci = "n/a" if s["ci95"] is None else f"[{s['ci95'][0]:.2f}, {s['ci95'][1]:.2f}]"
            kap = "n/a" if s["kappa"] is None else f"{s['kappa']:.2f}"
            out.append(f"  {k:13s} kappa {kap} {ci}   tp/fp/fn {s['tp']}/{s['fp']}/{s['fn']}")
    return out


def main(argv=None) -> int:
    utf8_console(sys.stdout)
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*", help=f"default: {' '.join(FIXTURES)}")
    ap.add_argument("--json", type=Path, help="write the full census as JSON")
    ap.add_argument("--table", type=Path, help="write the printed tables to a file too")
    args = ap.parse_args(argv)
    names = args.fixtures or list(FIXTURES)
    bad = [n for n in names if n not in FIXTURES]
    if bad:
        ap.error(f"unknown fixture(s) {bad}; choose from {list(FIXTURES)}")
    results = run(names)
    pooled = pooled_kappa(results)
    lines: list[str] = []
    for res in results:
        lines.append("")
        lines.extend(format_table(res))
    lines.extend(format_summary(results, pooled))
    text = "\n".join(lines)
    print(text)
    if args.table:
        args.table.write_text(text + "\n", encoding="utf-8")
    if args.json:
        slim = [{k: v for k, v in r.items() if k not in ("scored", "truth", "pred")} for r in results]
        args.json.write_text(json.dumps({"fixtures": slim, "pooled": pooled}, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
