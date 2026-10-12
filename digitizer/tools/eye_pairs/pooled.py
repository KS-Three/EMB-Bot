"""Pooled yardstick-vs-eye analysis (ROADMAP phase 1 exit question).

    python -m tools.eye_pairs.pooled report [--inputs PATH] [--markdown]

Every labelled eye-pairs sitting, on one footing: for each pair, which side
Kent picked and which side each instrument would have picked, and the
chance-corrected agreement between the two. ROADMAP gate 4 applies
throughout: NO raw agreement figure is computed or printed -- only Cohen's
kappa, its bootstrap interval and the n it rests on.

Pure: `pooled-inputs.json` (built once from the sittings' exports, render
directories and price tables by `pooled_build.py`) goes in, plain dicts come
out. Nothing here runs the engine.

Vocabulary and the two tie words
--------------------------------
A pair's label is one of `after`, `before`, `same` ("no difference"),
`both_bad`, or null (nothing recorded). Anything else REFUSES the whole
pool: a label this module does not know is a sitting whose meaning it cannot
guess, and silently mapping it to "tie" would make the table look better.

`before` / `after` are the page's LEFT / RIGHT. For almost every arm that is
shipped / flag; for the two old-engine arms (`ref_0827`, `ref_0930am`) it is
the OLD engine / today's. Everything below speaks in `before` / `after`, never
base / arm, so those arms need no special case.

Kent's pick is three-valued: `before`, `after`, or `tie`. Both `same` and
`both_bad` land on `tie` ("he prefers neither side"); they are different
things (nothing to see vs. nothing worth keeping) and `both_bad="drop"`
leaves the second out entirely. An instrument's pick is three-valued the same
way: `tie` is exactly equal values at the precision they were stored.

Two statistics, because they answer different questions:

* DECIDED (2 x 2, unweighted kappa): pairs where Kent chose a side AND the
  instrument chose a side. This is the exit clause read directly ("when he
  has a preference, does the metric share it"). The pairs the instrument was
  silent on are COUNTED and reported, not hidden.
* THREE-WAY (3 x 3, linear-weighted kappa, order before < tie < after): every
  judged pair, ties included, so an instrument that prefers a side on a pair
  Kent called no-difference is charged for it, and one that is silent where
  he is silent is credited. Chance is the expected agreement of the table's
  own marginals, the same correction `scorecard.type_chance` uses.

Intervals are percentile bootstrap, B = 10,000, seed fixed; a resample whose
kappa is undefined (expected agreement of 1) is discarded and COUNTED. The
default resamples PAIRS; `cluster` resamples FIXTURES (all of a fixture's
pairs together) because the pairs from one logo are not independent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

INPUTS = Path(__file__).resolve().parents[3] / "docs" / "eye-pairs-2026-10-11" / "pooled-inputs.json"

# label -> Kent's three-valued pick. None (unjudged) is handled apart.
VOCABULARY = {"after": "after", "before": "before", "same": "tie", "both_bad": "tie"}
SIDES = ("before", "tie", "after")            # the order the weighted kappa uses

# Fixtures Kent ruled off the comparison page in his own words
# (pairs.EXCLUDED_FIXTURES, repeated here so this module stays import-light).
KENT_EXCLUDED = frozenset({"screenshot", "gaulke"})

# instrument -> (which way is BETTER, one-line meaning). Directions follow
# analysis.METRICS where that table has the name; the price columns have no
# direction there ("none": descriptive) and are read here as COST, lower is
# better, as an explicit hypothesis -- the table says so wherever it is used.
INSTRUMENTS: dict[str, tuple[str, str]] = {
    "lost_frac": ("lower", "dropped_elements lost_frac (unsewn + overshoot, summed)"),
    "unsewn_frac": ("lower", "lost_frac half: artwork the stitch-out never covered"),
    "overshoot_frac": ("lower", "lost_frac half: thread standing on cloth the artwork leaves bare"),
    "uncovered_ink_frac": ("lower", "colour-free uncovered ink share"),
    "uncovered_total_mm2": ("lower", "preflight uncovered area, mm^2"),
    "lost_elements": ("lower", "count of artwork elements lost"),
    "ragged_mm": ("lower", "edge_smoothness ragged_mm"),
    "hausdorff_mm": ("lower", "edge_smoothness hausdorff_mm"),
    "artfid": ("higher", "ARTFID composite (fidelity, not a quality percentage)"),
    "stitches": ("lower", "PRICE: stitch count (cost reading, hypothesis)"),
    "trims": ("lower", "PRICE: trim count (cost reading, hypothesis)"),
    "trims_per_1000": ("lower", "trims per 1000 stitches"),
    "changed_trims": ("lower", "PRICE: trims landing on the shapes the arm changed"),
    "bare_satin_pct": ("lower", "rail_edge bare-satin share (the envelope arm's own instrument)"),
    "fan_census": ("lower", "fan_census over-long radiating crosses per lettered shape"),
}
# Declared up front, with the reason, so a zero row in the report is an
# explanation and not an omission.
NOT_COMPUTED = {
    "fan_census": ("needs a live plan (text-tagged letters, pull compensation); the stored "
                   "designs of the judged pages do not carry them, and re-digitizing would "
                   "score a different engine than the one Kent looked at"),
}
B = 10_000
SEED = 20261011


class LabelVocabularyError(ValueError):
    """A sitting carries a label this module does not know how to read."""


# ---------------------------------------------------------------- kappa ----

def kappa_from_table(table, weights: str = "none") -> float | None:
    """Cohen's kappa of a k x k contingency table (rows = Kent, cols =
    instrument). `weights="linear"` is the linear-weighted kappa for ordered
    categories, w_ij = 1 - |i-j|/(k-1). None when expected agreement is 1
    (one category on both margins: nothing to correct for)."""
    t = np.asarray(table, dtype=float)
    n = t.sum()
    if n == 0:
        return None
    k = t.shape[0]
    idx = np.arange(k)
    if weights == "linear" and k > 1:
        w = 1.0 - np.abs(idx[:, None] - idx[None, :]) / (k - 1)
    else:
        w = np.eye(k)
    p = t / n
    pe_mat = np.outer(p.sum(axis=1), p.sum(axis=0))
    po, pe = float((w * p).sum()), float((w * pe_mat).sum())
    if pe >= 1.0 - 1e-12:
        return None
    return (po - pe) / (1.0 - pe)


def _table(kent: np.ndarray, inst: np.ndarray, k: int) -> np.ndarray:
    return np.bincount(kent * k + inst, minlength=k * k).reshape(k, k)


def _boot(kent, inst, fixtures, k, weights, *, cluster: bool, rng) -> tuple:
    """-> (lo, hi, n_resamples_used). Percentile interval of the kappa over
    B resamples of pairs (or of whole fixtures when `cluster`)."""
    n = len(kent)
    if n < 2:
        return (None, None, 0)
    fx = np.asarray(fixtures)
    members = None
    if cluster:
        members = [np.flatnonzero(fx == f) for f in sorted(set(fx.tolist()))]
        if len(members) < 2:
            return (None, None, 0)
    vals = []
    for _ in range(B):
        if cluster:
            pick = rng.integers(0, len(members), len(members))
            idx = np.concatenate([members[i] for i in pick])
        else:
            idx = rng.integers(0, n, n)
        v = kappa_from_table(_table(kent[idx], inst[idx], k), weights)
        if v is not None:
            vals.append(v)
    if len(vals) < B // 2:
        return (None, None, len(vals))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return (float(lo), float(hi), len(vals))


# ----------------------------------------------------------------- pool ----

def validate(inputs: dict) -> None:
    """Refuse a pool that holds a label outside `VOCABULARY` (null is fine:
    that pair is unjudged and simply not pooled)."""
    if inputs.get("schema") != 1:
        raise LabelVocabularyError(f"pooled-inputs schema {inputs.get('schema')!r} is not 1")
    for sid, sitting in inputs["sittings"].items():
        for p in sitting["pairs"]:
            lab = p.get("label")
            if lab is not None and lab not in VOCABULARY:
                raise LabelVocabularyError(
                    f"REFUSED: sitting {sid!r}, pair {p.get('id')!r}: label {lab!r} is not one of "
                    f"{sorted(VOCABULARY)} or null; mapping it to a tie would be a guess")


def pooled_pairs(inputs: dict) -> list[dict]:
    """Every JUDGED pair, flat, with its sitting id and Kent's three-valued
    pick. Validates first."""
    validate(inputs)
    out = []
    for sid, sitting in inputs["sittings"].items():
        for p in sitting["pairs"]:
            if p.get("label") is None:
                continue
            out.append({**p, "sitting": sid, "kent": VOCABULARY[p["label"]]})
    return out


def instrument_pick(metric: str, before: float, after: float, *,
                    directions: dict | None = None) -> str:
    """`directions` defaults to `INSTRUMENTS`; a caller scoring its own
    candidates (`density_flow`) passes a table that extends it."""
    direction = (directions or INSTRUMENTS)[metric][0]
    if round(after - before, 9) == 0:
        return "tie"
    better_after = after > before if direction == "higher" else after < before
    return "after" if better_after else "before"


def select(pairs: list[dict], *, scope: str = "primary", both_bad: str = "tie") -> list[dict]:
    """The rows a statistic is computed over.

    scope "primary": drop the fixtures Kent ruled off the page himself
    (screenshot, gaulke) and any pair a source marked unscorable;
    "all_fixtures" keeps those two fixtures back in (still drops unscorable).
    both_bad "tie" folds it into Kent's tie; "drop" removes those pairs."""
    if scope not in ("primary", "all_fixtures") or both_bad not in ("tie", "drop"):
        raise ValueError("scope is primary|all_fixtures, both_bad is tie|drop")
    rows = []
    for p in pairs:
        if p.get("scorable") is False:
            continue
        if scope == "primary" and p["fixture"] in KENT_EXCLUDED:
            continue
        if both_bad == "drop" and p["label"] == "both_bad":
            continue
        rows.append(p)
    return rows


def _refused(p: dict, metric: str) -> bool:
    r = p.get("refused") or {}
    return metric in (r.get("before") or []) or metric in (r.get("after") or [])


def agreement(rows: list[dict], metric: str, *, cluster: bool = False,
              include_refused: bool = False, seed: int = SEED,
              directions: dict | None = None) -> dict:
    """Chance-corrected agreement of one instrument with Kent over `rows`.
    No raw agreement is returned. A pair the instrument REFUSED on (a side
    the scorecard says is not an engine result: ink ambiguous, subject
    mismatch, ...) is not scored unless `include_refused`, the same default
    as analysis.sign_agreement; `n_refused` says how many that cost."""
    scored, n_refused = [], 0
    for p in rows:
        b, a = p["before"].get(metric), p["after"].get(metric)
        if b is None or a is None:
            continue
        if not include_refused and _refused(p, metric):
            n_refused += 1
            continue
        scored.append((p, instrument_pick(metric, float(b), float(a), directions=directions)))
    res = {"metric": metric, "n_scored": len(scored), "n_refused": n_refused,
           "n_kent_decided": sum(1 for p, _ in scored if p["kent"] != "tie"),
           "n_instrument_silent_on_decided": sum(1 for p, i in scored
                                                 if p["kent"] != "tie" and i == "tie")}
    if metric in NOT_COMPUTED:
        res["not_computed"] = NOT_COMPUTED[metric]
    rng = np.random.default_rng(seed)
    # ---- three-way, linear-weighted
    kent3 = np.array([SIDES.index(p["kent"]) for p, _ in scored], dtype=int)
    inst3 = np.array([SIDES.index(i) for _, i in scored], dtype=int)
    fx3 = [p["fixture"] for p, _ in scored]
    res["kappa_3way"] = kappa_from_table(_table(kent3, inst3, 3), "linear") if scored else None
    lo, hi, used = _boot(kent3, inst3, fx3, 3, "linear", cluster=cluster, rng=rng)
    res.update(ci3_lo=lo, ci3_hi=hi, ci3_resamples=used)
    # ---- decided, 2 x 2
    dec = [(p, i) for p, i in scored if p["kent"] != "tie" and i != "tie"]
    res["n_decided"] = len(dec)
    k2 = np.array([0 if p["kent"] == "before" else 1 for p, _ in dec], dtype=int)
    i2 = np.array([0 if i == "before" else 1 for _, i in dec], dtype=int)
    res["kappa_decided"] = kappa_from_table(_table(k2, i2, 2)) if dec else None
    lo, hi, used = _boot(k2, i2, [p["fixture"] for p, _ in dec], 2, "none",
                         cluster=cluster, rng=rng)
    res.update(ci2_lo=lo, ci2_hi=hi, ci2_resamples=used)
    return res


MIN_N_READ = 10


def reading(n: int, *intervals) -> str:
    """What the intervals license, and no more. Both the pair interval and
    the fixture-cluster interval have to clear zero (pairs from one logo are
    not independent, and neither interval alone is conservative: with a
    handful of fixtures the cluster one can come out the narrower). Under
    `MIN_N_READ` pairs nothing is read at all."""
    if n < MIN_N_READ:
        return f"n too small (<{MIN_N_READ})"
    if any(lo is None for lo, _ in intervals):
        return "interval undefined"
    if all(lo > 0 for lo, _ in intervals):
        return "above chance"
    if all(hi < 0 for _, hi in intervals):
        return "below chance"
    return "no evidence either way"


def worse_pairs(rows: list[dict], metric: str, *, directions: dict | None = None) -> list[dict]:
    """Every pair where Kent chose a side and the instrument chose the OTHER
    one: the pair, the values, and the margin by which Kent's pick scored
    WORSE (positive; in the instrument's own units). Pairs the instrument
    refused on are left out, as in `agreement`."""
    direction = (directions or INSTRUMENTS)[metric][0]
    out = []
    for p in rows:
        b, a = p["before"].get(metric), p["after"].get(metric)
        if b is None or a is None or p["kent"] == "tie" or _refused(p, metric):
            continue
        pick = instrument_pick(metric, float(b), float(a), directions=directions)
        if pick == "tie" or pick == p["kent"]:
            continue
        mine, other = (float(a), float(b)) if p["kent"] == "after" else (float(b), float(a))
        margin = (mine - other) if direction == "lower" else (other - mine)
        out.append({"pair": p["id"], "sitting": p["sitting"], "arm": p["arm"],
                    "fixture": p["fixture"], "kent": p["label"],
                    "before": float(b), "after": float(a), "margin": round(margin, 6)})
    return sorted(out, key=lambda r: -r["margin"])


def full_report(inputs: dict) -> dict:
    pairs = pooled_pairs(inputs)
    rows = select(pairs)
    out = {"n_judged_pairs": len(pairs), "n_primary": len(rows),
           "label_counts": {lab: sum(1 for p in pairs if p["label"] == lab) for lab in VOCABULARY},
           "instruments": {}, "worse": {}}
    for m in INSTRUMENTS:
        pair_boot = agreement(rows, m)
        clus = agreement(rows, m, cluster=True)
        pair_boot["ci3_cluster"] = (clus["ci3_lo"], clus["ci3_hi"])
        pair_boot["ci2_cluster"] = (clus["ci2_lo"], clus["ci2_hi"])
        pair_boot["sens_all_fixtures"] = _brief(agreement(select(pairs, scope="all_fixtures"), m))
        pair_boot["sens_both_bad_dropped"] = _brief(agreement(select(pairs, both_bad="drop"), m))
        pair_boot["sens_refusals_ignored"] = _brief(agreement(rows, m, include_refused=True))
        out["instruments"][m] = pair_boot
        out["worse"][m] = worse_pairs(rows, m)
    return out


def _brief(r: dict) -> dict:
    return {k: r[k] for k in ("n_scored", "n_decided", "kappa_3way", "ci3_lo", "ci3_hi",
                              "kappa_decided", "ci2_lo", "ci2_hi")}


# ---------------------------------------------------------------- output ---

def _f(v, nd=2):
    return "n/a" if v is None else f"{v:+.{nd}f}"


def _ci(lo, hi):
    return "n/a" if lo is None else f"[{lo:+.2f}, {hi:+.2f}]"


def kappa_table_markdown(rep: dict) -> str:
    lines = ["| instrument | n scored | refused, left out | n decided | silent on decided | kappa decided (2x2) | 95% CI, pairs | 95% CI, fixtures | reading (decided) | kappa 3-way (weighted) | 95% CI, pairs | 95% CI, fixtures | reading (3-way) |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in rep["instruments"].items():
        if r["n_scored"] == 0:
            why = NOT_COMPUTED.get(m, "no judged pair carries this instrument")
            lines.append(f"| `{m}` | 0 | {r['n_refused']} | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | not computed: {why} |")
            continue
        c3 = r["ci3_cluster"]
        c2 = r["ci2_cluster"]
        lines.append(
            f"| `{m}` | {r['n_scored']} | {r['n_refused']} | {r['n_decided']} | {r['n_instrument_silent_on_decided']} "
            f"| {_f(r['kappa_decided'])} | {_ci(r['ci2_lo'], r['ci2_hi'])} | {_ci(*c2)} "
            f"| {reading(r['n_decided'], (r['ci2_lo'], r['ci2_hi']), c2)} "
            f"| {_f(r['kappa_3way'])} | {_ci(r['ci3_lo'], r['ci3_hi'])} | {_ci(*c3)} "
            f"| {reading(r['n_scored'], (r['ci3_lo'], r['ci3_hi']), c3)} |")
    return "\n".join(lines)


def worse_markdown(rep: dict, metrics=None) -> str:
    out = []
    for m, rows in rep["worse"].items():
        if metrics and m not in metrics:
            continue
        if not rows:
            continue
        unit = INSTRUMENTS[m][1]
        out.append(f"\n#### `{m}` ({len(rows)} pairs) - {unit}\n")
        out.append("| pair | Kent | before | after | margin (Kent's pick worse by) |")
        out.append("|---|---|---|---|---|")
        for r in rows:
            out.append(f"| `{r['pair']}` | {r['kent']} | {r['before']:g} | {r['after']:g} | {r['margin']:g} |")
    return "\n".join(out)


FIDELITY = ("lost_frac", "unsewn_frac", "overshoot_frac", "uncovered_ink_frac",
            "lost_elements", "ragged_mm", "hausdorff_mm", "artfid")


def pair_tally(rep: dict, metrics=FIDELITY) -> list[dict]:
    """Pairs ranked by how many of the fidelity instruments score Kent's pick
    worse on them: the pictures to open first."""
    seen: dict[str, dict] = {}
    for m in metrics:
        for r in rep["worse"].get(m, []):
            row = seen.setdefault(r["pair"], {"pair": r["pair"], "kent": r["kent"], "instruments": []})
            row["instruments"].append(m)
    return sorted(seen.values(), key=lambda r: (-len(r["instruments"]), r["pair"]))


def inventory(inputs: dict) -> list[dict]:
    """One row per sitting: what was judged and what could be paired with it."""
    out = []
    for sid, sitting in inputs["sittings"].items():
        judged = [p for p in sitting["pairs"] if p.get("label") is not None]
        counts = {lab: sum(1 for p in judged if p["label"] == lab) for lab in VOCABULARY}
        out.append({"sitting": sid, "date": sitting["date"], "judged": len(judged),
                    "unjudged": len(sitting["pairs"]) - len(judged), **counts,
                    "arms": sorted({p["arm"] for p in judged}),
                    "with_instruments": sum(1 for p in judged if p["before"] and p["after"]),
                    "labels": sitting.get("labels", ""), "instruments": sitting.get("instruments", "")})
    return out


def inventory_markdown(inputs: dict) -> str:
    lines = ["| sitting | date | judged | after | before | same | both_bad | arms | pairs with instrument rows |",
             "|---|---|---|---|---|---|---|---|---|"]
    for r in inventory(inputs):
        arms = ", ".join(f"`{a}`" for a in r["arms"])
        lines.append(f"| `{r['sitting']}` | {r['date']} | {r['judged']} | {r['after']} | {r['before']} "
                     f"| {r['same']} | {r['both_bad']} | {arms} | {r['with_instruments']} |")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["report"])
    ap.add_argument("--inputs", type=Path, default=INPUTS)
    ap.add_argument("--markdown", action="store_true")
    ap.add_argument("--json", type=Path, help="also write the full report as JSON")
    args = ap.parse_args(argv)
    inputs = json.loads(args.inputs.read_text(encoding="utf-8"))
    rep = full_report(inputs)
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"judged pairs pooled: {rep['n_judged_pairs']}  (primary scope: {rep['n_primary']})\n")
    print(inventory_markdown(inputs))
    print()
    print(kappa_table_markdown(rep))
    if args.markdown:
        print("\n#### pairs that score Kent's pick worse on several fidelity instruments\n")
        print("| pair | Kent | instruments |\n|---|---|---|")
        for r in pair_tally(rep):
            print(f"| `{r['pair']}` | {r['kent']} | {len(r['instruments'])}: {', '.join(r['instruments'])} |")
        print(worse_markdown(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
