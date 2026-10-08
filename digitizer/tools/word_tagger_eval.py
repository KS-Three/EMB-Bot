"""How well does each lettering tagger find the letters, and the lines?

L1 of `docs/lettering-architecture-rd-2026-10-07.md` replaces two taggers
with one (`digitizer_core/words.py`). This scores all of them against hand
labels on the real logos in the repo (`testdata/lettering_truth.json`),
per ROADMAP gate 4 with chance-corrected figures only:

  * DETECTION -- Cohen's kappa of "this region is a letter" against the
    labels, over every scored region of a fixture (pooled: over all of
    them). A raw agreement would read high on Fremont's 164 regions by
    calling nothing a letter; kappa reads that as 0.
  * GROUPING -- the adjusted Rand index of the tagger's groups against the
    labelled lines, over the regions both call letters. 0 is chance, 1 is
    the labelled partition.

The four taggers scored:

  text_cluster   `text_candidate`, grouped by `text_cluster_id`
  house_group    `textcluster._lettering_groups` (writes `lettering_group`)
  either         what `columns.is_lettering` reads today: a letter when
                 either says so, groups merged where they share a member
  words          `words.detect_words` (L1, `cfg.lettering_words`)

The labels are shape ids from `build_generation` at the corpus sizes
(`tools/thin_strokes.REAL_ART`, Studio's six colours) on the commit the
truth file names. Segmentation that moves renames shapes: a fixture whose
labelled ids are no longer all present is reported STALE and left out,
never scored against the wrong regions. Re-label it (the truth file says
how) rather than trusting a partial match.

    .venv/bin/python -m tools.word_tagger_eval            # all fixtures
    .venv/bin/python -m tools.word_tagger_eval becker gaulke
    .venv/bin/python -m tools.word_tagger_eval --patterns    # what the
                                                             # pattern test removes
    .venv/bin/python -m tools.word_tagger_eval --json out.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRUTH = ROOT / "testdata" / "lettering_truth.json"
TAGGERS = ("text_cluster", "house_group", "either", "words")
BOOTSTRAP = 2000


def kappa(truth: list[bool], pred: list[bool]) -> float | None:
    """Cohen's kappa for two binary labellings; None when it is undefined
    (both labellings constant and equal: expected agreement is 1)."""
    n = len(truth)
    if n == 0:
        return None
    t = np.asarray(truth, bool)
    p = np.asarray(pred, bool)
    po = float(np.mean(t == p))
    pt, pp = float(t.mean()), float(p.mean())
    pe = pt * pp + (1 - pt) * (1 - pp)
    if pe >= 1.0:
        return None
    return (po - pe) / (1 - pe)


def ari(a: list, b: list) -> float | None:
    """Adjusted Rand index (Hubert & Arabie) of two labellings of the same
    items; None under two items, or when both are one block each."""
    n = len(a)
    if n < 2:
        return None
    ka = {x: i for i, x in enumerate(sorted(set(map(str, a))))}
    kb = {x: i for i, x in enumerate(sorted(set(map(str, b))))}
    m = np.zeros((len(ka), len(kb)), np.int64)
    for x, y in zip(a, b):
        m[ka[str(x)], kb[str(y)]] += 1

    def c2(v):
        return v * (v - 1) / 2.0
    s_ij = float(c2(m).sum())
    s_a = float(c2(m.sum(axis=1)).sum())
    s_b = float(c2(m.sum(axis=0)).sum())
    exp = s_a * s_b / c2(n)
    mx = (s_a + s_b) / 2.0
    if mx == exp:
        return None
    return (s_ij - exp) / (mx - exp)


def _union_groups(regions, tc: dict, lg: dict) -> dict:
    """`either`: a letter when either tagger says so; groups merged where a
    text cluster and a house group share a member (union-find)."""
    parent: dict[str, str] = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(x, y):
        rx, ry = find(x), find(y)
        if rx != ry:
            parent[rx] = ry
    for sid in set(tc) | set(lg):
        find(sid)
    for src in (tc, lg):
        by: dict = {}
        for sid, g in src.items():
            by.setdefault(g, []).append(sid)
        for members in by.values():
            for s in members[1:]:
                union(members[0], s)
    return {sid: find(sid) for sid in parent}


def predictions(regions, chart) -> dict[str, dict[str, str]]:
    """tagger -> {shape_id: group key} over the regions it calls letters."""
    from digitizer_core.textcluster import _lettering_groups
    from digitizer_core.words import detect_words
    tc = {r.shape_id: r.meta["text_cluster_id"] for r in regions
          if r.meta.get("text_candidate") and r.meta.get("text_cluster_id")}
    lg = {r.shape_id: f"LG{i}" for i, g in enumerate(_lettering_groups(regions)) for r in g}
    wd = {r.shape_id: w.word_id for w in detect_words(regions, chart=chart) for r in w.members}
    return {"text_cluster": tc, "house_group": lg,
            "either": _union_groups(regions, tc, lg), "words": wd}


def score_fixture(regions, truth: dict, preds: dict) -> dict:
    lab = {sid: line for line, ids in truth["lines"].items() for sid in ids}
    ignore = set(truth.get("ignore", []))
    scored = [r.shape_id for r in regions if r.shape_id not in ignore]
    t = [sid in lab for sid in scored]
    out = {"regions": len(scored), "letters": sum(t)}
    for name, pred in preds.items():
        p = [sid in pred for sid in scored]
        both = [sid for sid in scored if sid in lab and sid in pred]
        out[name] = {
            "tp": sum(a and b for a, b in zip(t, p)),
            "fp": sum(b and not a for a, b in zip(t, p)),
            "fn": sum(a and not b for a, b in zip(t, p)),
            "kappa": kappa(t, p),
            "ari": ari([lab[s] for s in both], [pred[s] for s in both]),
            "grouped": len(both),
            "_t": t, "_p": p,
        }
    return out


def pooled(results: dict, name: str, rng=None) -> dict:
    t = [x for r in results.values() for x in r[name]["_t"]]
    p = [x for r in results.values() for x in r[name]["_p"]]
    out = {"kappa": kappa(t, p)}
    if rng is not None:
        keys = sorted(results)
        ks = []
        for _ in range(BOOTSTRAP):
            pick = rng.choice(keys, size=len(keys), replace=True)
            tt = [x for k in pick for x in results[k][name]["_t"]]
            pp = [x for k in pick for x in results[k][name]["_p"]]
            k = kappa(tt, pp)
            if k is not None:
                ks.append(k)
        out["kappa_ci95"] = [float(np.percentile(ks, 2.5)), float(np.percentile(ks, 97.5))]
    aris = [r[name]["ari"] for r in results.values() if r[name]["ari"] is not None]
    out["ari_mean"] = float(np.mean(aris)) if aris else None
    return out


def paired_delta(results: dict, a: str, b: str, rng) -> list[float]:
    """95% fixture-bootstrap interval of pooled kappa(b) - kappa(a)."""
    keys = sorted(results)
    ds = []
    for _ in range(BOOTSTRAP):
        pick = rng.choice(keys, size=len(keys), replace=True)
        t = [x for k in pick for x in results[k][a]["_t"]]
        pa = [x for k in pick for x in results[k][a]["_p"]]
        pb = [x for k in pick for x in results[k][b]["_p"]]
        ka, kb = kappa(t, pa), kappa(t, pb)
        if ka is not None and kb is not None:
            ds.append(kb - ka)
    return [float(np.percentile(ds, 2.5)), float(np.percentile(ds, 97.5))]


def _fmt(x):
    return "  n/a" if x is None else f"{x:5.2f}"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("fixtures", nargs="*")
    ap.add_argument("--patterns", action="store_true",
                    help="print each linked component's pattern removals against its labels")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)

    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation
    from digitizer_core.threads import chart_for
    from tools.thin_strokes import STUDIO_MAX_COLORS, corpus_cases

    truth = json.loads(TRUTH.read_text())
    results: dict = {}
    stale: list[str] = []
    for name, path, width, garment in corpus_cases():
        if name not in truth["fixtures"] or (args.fixtures and name not in args.fixtures):
            continue
        tr = truth["fixtures"][name]
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment,
                             max_colors=STUDIO_MAX_COLORS)
        regions = build_generation(str(path), cfg).regions
        have = {r.shape_id for r in regions}
        missing = [s for ids in tr["lines"].values() for s in ids if s not in have]
        if missing:
            stale.append(name)
            print(f"{name}: STALE -- {len(missing)} labelled shape ids not in this "
                  f"generation; re-label, do not score")
            continue
        chart = chart_for(cfg)
        if args.patterns:
            _print_patterns(name, regions, tr, chart)
        results[name] = score_fixture(regions, tr, predictions(regions, chart))

    if not results:
        print("nothing scored")
        return 1
    print(f"\n{'fixture':12s} {'n':>4s} {'let':>4s}   " +
          "   ".join(f"{t:>21s}" for t in TAGGERS))
    print(f"{'':12s} {'':4s} {'':4s}   " + "   ".join(f"{'kappa  ARI  tp/fp/fn':>21s}" for _ in TAGGERS))
    for name, r in results.items():
        cells = []
        for t in TAGGERS:
            x = r[t]
            cells.append(f"{_fmt(x['kappa'])} {_fmt(x['ari'])} {x['tp']:3d}/{x['fp']:3d}/{x['fn']:3d}")
        print(f"{name:12s} {r['regions']:4d} {r['letters']:4d}   " + "   ".join(f"{c:>21s}" for c in cells))
    rng = np.random.default_rng(0)
    summary = {t: pooled(results, t, rng) for t in TAGGERS}
    print("\npooled kappa [fixture-bootstrap 95%]   mean ARI")
    for t in TAGGERS:
        s = summary[t]
        lo, hi = s["kappa_ci95"]
        print(f"  {t:13s} {s['kappa']:.3f} [{lo:.3f}, {hi:.3f}]   {_fmt(s['ari_mean'])}")
    deltas = {t: paired_delta(results, t, "words", rng) for t in TAGGERS if t != "words"}
    print("\nwords minus each, pooled kappa, paired fixture bootstrap 95%:")
    for t, (lo, hi) in deltas.items():
        print(f"  vs {t:13s} [{lo:+.3f}, {hi:+.3f}]")
    if stale:
        print(f"\nSTALE (not scored): {', '.join(stale)}")
    if args.json:
        clean = {k: {t: ({kk: vv for kk, vv in v.items() if not kk.startswith('_')}
                         if isinstance(v, dict) else v) for t, v in r.items()}
                 for k, r in results.items()}
        args.json.write_text(json.dumps({"fixtures": clean, "pooled": summary,
                                         "delta_vs_words": deltas, "stale": stale}, indent=1))
    return 0


def _print_patterns(name, regions, tr, chart) -> None:
    """Every linked component `detect_words` considers: its size, how many
    members the pattern test removes, and how many of each are labelled
    letters -- the evidence for `words.PATTERN_MIN_TWINS`."""
    from digitizer_core.textcluster import LETTER_HEIGHT_RATIO, MIN_CLUSTER_MEMBERS, _cluster
    from digitizer_core.words import _candidates, _pattern_ids
    lab = {sid for ids in tr["lines"].values() for sid in ids}
    for comp in _cluster(_candidates(regions), LETTER_HEIGHT_RATIO, chart):
        if len(comp) < MIN_CLUSTER_MEMBERS:
            continue
        pat = _pattern_ids(comp)
        hit = sum(c.region.shape_id in lab for c in comp)
        lost = sum(s in lab for s in pat)
        print(f"  {name:11s} component n={len(comp):3d} letters={hit:3d} "
              f"pattern={len(pat):3d} (letters among them: {lost})")


if __name__ == "__main__":
    raise SystemExit(main())
