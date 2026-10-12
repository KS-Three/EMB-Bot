"""Density / flow candidates for Kent's eye, read from a stored design's stitches.

    python -m tools.eye_pairs.density_flow report [--inputs PATH] [--markdown] [--json PATH]

PR #842 pooled 115 judged before | after pairs and found that no fidelity
instrument clears chance against Kent's eye; only the trim counts do. His
own notes talk about stitch DENSITY, FLOW and TRIMS, which nothing measured.
This module codes that vocabulary into candidates, each defined in one
sentence and computed from the STORED design's stitch stream only (no
re-digitize: that would score today's engine, not the one he looked at),
and re-scores the pairs with `pooled.py`'s kappa machinery. ROADMAP gate 4
holds: no raw agreement figure is computed or printed, only Cohen's kappa,
its bootstrap interval and n.

The candidates (`CANDIDATES` carries each one's direction, a HYPOTHESIS
written down from his notes before the table was computed):

* `thread_density`: needle-down thread length (mm) per mm^2 of sewn footprint
  (the union of every stitch drawn as a 0.4 mm thread), on the shapes the arm
  changed. Higher = denser. His notes: "the before stitch density is better"
  (the side sewn at 0.40 against 0.80), "trying to fill a void".
* `thread_density_whole`: the same over the whole design.
* `density_pro_gap`: |whole-design `thread_density` - the professional's own
  file's|, where Kent owns a pro file of that logo. Lower = closer to the pro.
* `flow_circvar`: thread-weighted mean, over fill and satin shapes, of the
  circular variance of stitch direction (axial, doubled angle) of stitches
  >= 1 mm in that shape. Lower = one direction per stroke ("one direction per
  stroke", "structured pattern").
* `turns_per_100mm`: within each fill/satin run, consecutive stitches >= 1 mm
  whose axial direction changes by more than 30 degrees, per 100 mm of that
  thread. Lower = smoother flow ("the lettering does not flow").
* `stitch_median_mm`, `short_share` (share of stitches under 1 mm),
  `long_share` (share over 4 mm): the stitch-length distribution on the
  changed shapes. His pro note: "each stitch crosses the whole stroke in one
  go", read as longer is better and short dust is worse.
* `jumps_per_1000` (needle-up moves per 1000 stitches) and `longest_jump_mm`
  (the longest one): the travel he names beside trims. Lower = better.
* `runs_per_shape`: sewn (fill, satin, run) runs per changed shape: how many
  pieces a shape is sewn in. Lower = flows ("on off on off", "lettering does
  not flow").
* `back_share_thread`, `top_support`: REUSED from `tools/underlay_cover.py`
  (back stitching as a share of thread; share of the top thread laid on
  thread), whole design. Higher = his "back stitching supports the top
  threading" note on the pro's Becker.

"Both bad" is a separate question (`both_bad_table`): does the LEVEL of an
instrument (the mean of the two sides) flag the pairs he called both bad?
It reuses the bare-fabric instruments already in `pooled-inputs.json`
(`unsewn_frac`, `uncovered_ink_frac`, `uncovered_total_mm2`, `lost_frac`)
rather than rebuilding them, beside two of the new candidates; the split is
the pooled median of the level, fixed before looking at the labels.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

from tools.eye_pairs import pooled

UNITS_PER_MM = 10.0            # Design coordinates are 0.1 mm
THREAD_MM = 0.4                # a 40-wt thread laid flat (underlay_cover.THREAD_MM)
FLOW_MIN_MM = 1.0              # shorter stitches are ties, row turns and dust
TURN_DEG = 30.0
SHORT_MM, LONG_MM = 1.0, 4.0
FLOW_KINDS = frozenset({"fill", "satin"})
SEWN_KINDS = frozenset({"fill", "satin", "run"})

DOCS = Path(__file__).resolve().parents[3] / "docs"
INPUTS = DOCS / "eye-pairs-2026-10-12" / "density-flow-inputs.json"

# metric -> (direction, one-line meaning). Directions are the hypotheses read
# from Kent's notes BEFORE any kappa was computed; the sign of the kappa says
# whether he agrees, and a negative one is reported as such, never flipped.
CANDIDATES: dict[str, tuple[str, str]] = {
    "thread_density": ("higher", "thread mm per mm^2 of sewn footprint, changed shapes"),
    "thread_density_whole": ("higher", "thread mm per mm^2 of sewn footprint, whole design"),
    "density_pro_gap": ("lower", "|whole-design density - the pro file's|, pro logos only"),
    "flow_circvar": ("lower", "circular variance of stitch direction within fill/satin shapes"),
    "turns_per_100mm": ("lower", ">30 deg direction changes per 100 mm of fill/satin thread"),
    "stitch_median_mm": ("higher", "median stitch length, changed shapes"),
    "short_share": ("lower", "share of stitches under 1 mm, changed shapes"),
    "long_share": ("higher", "share of stitches over 4 mm, changed shapes"),
    "jumps_per_1000": ("lower", "needle-up moves per 1000 stitches"),
    "longest_jump_mm": ("lower", "longest needle-up move, mm"),
    "runs_per_shape": ("lower", "sewn runs per changed shape (pieces a shape is sewn in)"),
    "back_share_thread": ("higher", "underlay_cover: back stitching, share of thread (reused)"),
    "top_support": ("higher", "underlay_cover: top thread laid on thread (reused)"),
    "trims_per_1000": ("lower", "trims per 1000 stitches (recomputed here; the #842 control)"),
}
GROUPS = (
    ("density", ("thread_density", "thread_density_whole", "density_pro_gap")),
    ("flow", ("flow_circvar", "turns_per_100mm", "runs_per_shape")),
    ("stitch length", ("stitch_median_mm", "short_share", "long_share")),
    ("travel", ("jumps_per_1000", "longest_jump_mm", "trims_per_1000")),
    ("back stitching (reused)", ("back_share_thread", "top_support")),
)
# Level instruments for the both-bad question: (metric, direction, source).
BOTH_BAD = (
    ("unsewn_frac", "lower", "pooled"), ("uncovered_ink_frac", "lower", "pooled"),
    ("uncovered_total_mm2", "lower", "pooled"), ("lost_frac", "lower", "pooled"),
    ("thread_density_whole", "higher", "candidate"), ("flow_circvar", "lower", "candidate"),
)


# ------------------------------------------------------------ the stream ---

def segments(design: dict) -> list[dict]:
    """Every needle-down segment in sew order: consecutive `stitch` records
    with nothing between them, as {x0, y0, x1, y1 (mm), len, run} where `run`
    is the index of the run holding the segment's END record (None when the
    design carries no runs, e.g. a professional's machine file)."""
    st = design.get("stitches") or []
    run_of = None
    runs = design.get("runs")
    if runs:
        run_of = np.full(len(st), -1, dtype=int)
        for ri, r in enumerate(runs):
            run_of[r["i0"]:r["i1"] + 1] = ri
    out = []
    for i in range(1, len(st)):
        a, b = st[i - 1], st[i]
        if a["type"] != "stitch" or b["type"] != "stitch":
            continue
        x0, y0 = a["x"] / UNITS_PER_MM, a["y"] / UNITS_PER_MM
        x1, y1 = b["x"] / UNITS_PER_MM, b["y"] / UNITS_PER_MM
        ln = math.hypot(x1 - x0, y1 - y0)
        if ln == 0.0:
            continue
        ri = None if run_of is None else int(run_of[i])
        out.append({"x0": x0, "y0": y0, "x1": x1, "y1": y1, "len": ln,
                    "run": None if ri is None or ri < 0 else ri})
    return out


def _footprint_mm2(segs: list[dict], thread_mm: float = THREAD_MM) -> float:
    """Area of the union of every segment drawn as a round-capped thread of
    width `thread_mm`. Exact geometry (shapely), no raster."""
    import shapely

    if not segs:
        return 0.0
    lines = shapely.linestrings([[(s["x0"], s["y0"]), (s["x1"], s["y1"])] for s in segs])
    return float(shapely.union_all(shapely.buffer(lines, thread_mm / 2.0, quad_segs=8)).area)


def thread_density(segs: list[dict]) -> float | None:
    area = _footprint_mm2(segs)
    if area <= 0:
        return None
    return sum(s["len"] for s in segs) / area


def _axial(s: dict) -> float:
    return math.atan2(s["y1"] - s["y0"], s["x1"] - s["x0"]) % math.pi


def circular_variance(segs: list[dict]) -> float | None:
    """1 - |length-weighted mean of exp(2i*theta)|: 0 when every stitch lies
    on one axis (either way along it), 1 when directions are spread evenly."""
    if not segs:
        return None
    w = np.array([s["len"] for s in segs])
    th = np.array([_axial(s) for s in segs])
    z = (w * np.exp(2j * th)).sum() / w.sum()
    return float(1.0 - abs(z))


def _axial_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % math.pi
    return math.degrees(min(d, math.pi - d))


def _groups(design: dict, segs: list[dict], key: str) -> dict:
    """Segments grouped by run index (`key="run"`) or by shape id
    (`key="shape"`), fill/satin runs only; one group when the design has no
    runs."""
    runs = design.get("runs")
    if not runs:
        return {None: [s for s in segs]}
    g: dict = {}
    for s in segs:
        if s["run"] is None:
            continue
        r = runs[s["run"]]
        if r["kind"] not in FLOW_KINDS:
            continue
        g.setdefault(s["run"] if key == "run" else r["shape"], []).append(s)
    return g


def flow_circvar(design: dict, segs: list[dict]) -> float | None:
    vals, wts = [], []
    for grp in _groups(design, segs, "shape").values():
        long_ = [s for s in grp if s["len"] >= FLOW_MIN_MM]
        cv = circular_variance(long_)
        if cv is None:
            continue
        vals.append(cv)
        wts.append(sum(s["len"] for s in long_))
    if not vals:
        return None
    return float(np.average(vals, weights=wts))


def turns_per_100mm(design: dict, segs: list[dict]) -> float | None:
    turns, thread = 0, 0.0
    for grp in _groups(design, segs, "run").values():
        long_ = [s for s in grp if s["len"] >= FLOW_MIN_MM]
        thread += sum(s["len"] for s in long_)
        th = [_axial(s) for s in long_]
        turns += sum(1 for a, b in zip(th, th[1:]) if _axial_diff_deg(a, b) > TURN_DEG)
    if thread <= 0:
        return None
    return 100.0 * turns / thread


def length_stats(segs: list[dict]) -> dict:
    if not segs:
        return {"stitch_median_mm": None, "short_share": None, "long_share": None}
    L = np.array([s["len"] for s in segs])
    return {"stitch_median_mm": float(np.median(L)),
            "short_share": float((L < SHORT_MM).mean()),
            "long_share": float((L > LONG_MM).mean())}


def travel(design: dict) -> dict:
    """Needle-up moves: a maximal stretch of jump/trim/colour records between
    two needle-down stitches that contains at least one jump, its length the
    distance between those two stitches."""
    st = design.get("stitches") or []
    n = design.get("stitchCount")
    if n is None:
        n = sum(1 for s in st if s["type"] == "stitch")
    moves, trims, longest = 0, sum(1 for s in st if s["type"] == "trim"), 0.0
    last = None
    jumped = False
    for s in st:
        t = s["type"]
        if t == "stitch":
            if jumped and last is not None:
                d = math.hypot(s["x"] - last[0], s["y"] - last[1]) / UNITS_PER_MM
                if d > 0:
                    moves += 1
                    longest = max(longest, d)
            last, jumped = (s["x"], s["y"]), False
        elif t == "jump":
            jumped = True
    per = 1000.0 / n if n else 0.0
    return {"jumps_per_1000": moves * per, "longest_jump_mm": longest,
            "trims_per_1000": trims * per}


def runs_per_shape(design: dict, shapes: set[str] | None) -> float | None:
    runs = [r for r in design.get("runs") or [] if r["kind"] in SEWN_KINDS
            and (shapes is None or r["shape"] in shapes)]
    if not runs:
        return None
    return len(runs) / len({r["shape"] for r in runs})


def _scope(design: dict, segs: list[dict], shapes: set[str] | None) -> list[dict]:
    if shapes is None or not design.get("runs"):
        return segs
    runs = design["runs"]
    return [s for s in segs if s["run"] is not None and runs[s["run"]]["shape"] in shapes]


def measure(design: dict, shapes: set[str] | None = None, *, support: bool = True) -> dict:
    """Every candidate for one design. `shapes` scopes the changed-shape
    candidates (None = the whole design); travel, `thread_density_whole` and
    the reused back-stitching pair are always whole-design."""
    segs = segments(design)
    sc = _scope(design, segs, shapes)
    dens = thread_density(sc)
    out = {"thread_density": dens,
           "thread_density_whole": dens if sc is segs else thread_density(segs),
           "flow_circvar": flow_circvar(design, sc),
           "turns_per_100mm": turns_per_100mm(design, sc),
           **length_stats(sc), **travel(design),
           "runs_per_shape": runs_per_shape(design, shapes)}
    if support:
        from tools.underlay_cover import measure as uc_measure, runs_from_design

        w = uc_measure(runs_from_design(design))["whole"]
        out["back_share_thread"] = w["back_share_thread"]
        out["top_support"] = w["top_support"]
    return out


# -------------------------------------------------------------- analysis ---

def load(path: Path = INPUTS) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def directions() -> dict[str, tuple[str, str]]:
    return {**pooled.INSTRUMENTS, **CANDIDATES}


def both_bad_agreement(rows: list[dict], metric: str, direction: str, *,
                       cluster: bool = False, seed: int = pooled.SEED) -> dict:
    """Kappa of `both_bad` (Kent) against `the level is on the bad side of the
    pooled median` (instrument), level = mean of the two sides. Every judged
    pair carrying the metric on both sides and refused on neither (the
    scorecard's refusal says the value is not an engine result)."""
    lv, kb, fx = [], [], []
    for p in rows:
        b, a = p["before"].get(metric), p["after"].get(metric)
        if b is None or a is None or pooled._refused(p, metric):
            continue
        lv.append((float(b) + float(a)) / 2.0)
        kb.append(1 if p["label"] == "both_bad" else 0)
        fx.append(p["fixture"])
    res = {"metric": metric, "direction": direction, "n": len(lv), "n_both_bad": sum(kb)}
    if len(lv) < 2:
        return {**res, "kappa": None, "ci_lo": None, "ci_hi": None, "threshold": None}
    thr = float(np.median(lv))
    L = np.array(lv)
    inst = (L > thr) if direction == "lower" else (L < thr)
    k = np.array(kb, dtype=int)
    i = inst.astype(int)
    rng = np.random.default_rng(seed)
    lo, hi, _ = pooled._boot(k, i, fx, 2, "none", cluster=cluster, rng=rng)
    return {**res, "threshold": thr, "n_flagged": int(i.sum()),
            "kappa": pooled.kappa_from_table(pooled._table(k, i, 2)), "ci_lo": lo, "ci_hi": hi}


def instrument_vs_instrument(rows: list[dict], m1: str, m2: str) -> dict:
    """Kappa between two instruments' picks on the pairs where both chose a
    side: does candidate m1 restate m2? (Not Kent; no label involved.)"""
    dirs = directions()
    a, b = [], []
    for p in rows:
        v = [p["before"].get(m1), p["after"].get(m1), p["before"].get(m2), p["after"].get(m2)]
        if None in v:
            continue
        p1 = pooled.instrument_pick(m1, float(v[0]), float(v[1]), directions=dirs)
        p2 = pooled.instrument_pick(m2, float(v[2]), float(v[3]), directions=dirs)
        if "tie" in (p1, p2):
            continue
        a.append(0 if p1 == "before" else 1)
        b.append(0 if p2 == "before" else 1)
    if not a:
        return {"n": 0, "kappa": None}
    return {"n": len(a), "kappa": pooled.kappa_from_table(pooled._table(np.array(a), np.array(b), 2))}


# Splits that ask whether a reading is one sitting's or one arm's: the 09-18..09-28
# flags sitting is 46 of the 76 measured pairs, and its two old-engine pairs
# per logo (`ref_0827`) compare whole engines, not one flag.
SPLITS = (
    ("no_old_engine_arms", lambda p: p["arm"] not in ("ref_0827", "ref_0930am")),
    ("flags_sitting_only", lambda p: p["sitting"] == "flags-0918-0928"),
    ("later_sittings_only", lambda p: p["sitting"] != "flags-0918-0928"),
)


def full_report(inputs: dict) -> dict:
    dirs = directions()
    pairs = pooled.pooled_pairs(inputs)          # validates the label vocabulary
    rows = pooled.select(pairs)
    out = {"n_judged_pairs": len(pairs), "n_primary": len(rows),
           "n_with_designs": sum(1 for p in rows if p.get("designs")),
           "instruments": {}, "worse": {}, "both_bad": {}, "restates_trims": {}}
    for m in CANDIDATES:
        r = pooled.agreement(rows, m, directions=dirs)
        c = pooled.agreement(rows, m, cluster=True, directions=dirs)
        r["ci3_cluster"] = (c["ci3_lo"], c["ci3_hi"])
        r["ci2_cluster"] = (c["ci2_lo"], c["ci2_hi"])
        r["sens_both_bad_dropped"] = pooled._brief(
            pooled.agreement(pooled.select(pairs, both_bad="drop"), m, directions=dirs))
        for name, keep in SPLITS:
            sub = [p for p in rows if keep(p)]
            s = pooled._brief(pooled.agreement(sub, m, directions=dirs))
            cs = pooled.agreement(sub, m, cluster=True, directions=dirs)
            s["ci2_cluster"], s["ci3_cluster"] = (cs["ci2_lo"], cs["ci2_hi"]), (cs["ci3_lo"], cs["ci3_hi"])
            r[f"split_{name}"] = s
        out["instruments"][m] = r
        out["worse"][m] = pooled.worse_pairs(rows, m, directions=dirs)
        out["restates_trims"][m] = instrument_vs_instrument(rows, m, "trims_per_1000")
    for m, d, _src in BOTH_BAD:
        r = both_bad_agreement(rows, m, d)
        c = both_bad_agreement(rows, m, d, cluster=True)
        r["ci_cluster"] = (c["ci_lo"], c["ci_hi"])
        out["both_bad"][m] = r
    return out


def direction_matches(r: dict) -> str:
    """Does the sign of the point estimate match the hypothesis written down
    from his notes? Read only where the pair count licenses a reading."""
    k = r.get("kappa_3way")
    if k is None or r["n_scored"] < pooled.MIN_N_READ:
        return "n/a"
    if k > 0:
        return "yes (sign)"
    if k < 0:
        return "no, reversed (sign)"
    return "no lean"


# ---------------------------------------------------------------- output ---

def kappa_table_markdown(rep: dict) -> str:
    f, ci = pooled._f, pooled._ci
    lines = ["| candidate | better is | n scored | n Kent chose a side | silent there | kappa, sides only (2x2) "
             "| 95% CI pairs | 95% CI fixtures | kappa, ties in (3-way, weighted) | 95% CI pairs "
             "| 95% CI fixtures | reading | sign matches his notes | Kent's pick worse on | "
             "kappa vs `trims_per_1000` picks (n) |",
             "|" + "---|" * 15]
    for gname, ms in GROUPS:
        lines.append(f"| **{gname}** |" + " |" * 14)
        for m in ms:
            r = rep["instruments"][m]
            rt = rep["restates_trims"][m]
            rt_s = "-" if m == "trims_per_1000" else (
                f"{f(rt['kappa'])} ({rt['n']})" if rt["n"] else "n/a (0)")
            if r["n_scored"] == 0:
                lines.append(f"| `{m}` | {CANDIDATES[m][0]} | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a "
                             f"| not computed (no pair carries it) | n/a | 0 | {rt_s} |")
                continue
            c2, c3 = r["ci2_cluster"], r["ci3_cluster"]
            rd2 = pooled.reading(r["n_decided"], (r["ci2_lo"], r["ci2_hi"]), c2)
            rd3 = pooled.reading(r["n_scored"], (r["ci3_lo"], r["ci3_hi"]), c3)
            lines.append(
                f"| `{m}` | {CANDIDATES[m][0]} | {r['n_scored']} | {r['n_kent_decided']} "
                f"| {r['n_instrument_silent_on_decided']} | {f(r['kappa_decided'])} "
                f"| {ci(r['ci2_lo'], r['ci2_hi'])} | {ci(*c2)} | {f(r['kappa_3way'])} "
                f"| {ci(r['ci3_lo'], r['ci3_hi'])} | {ci(*c3)} | sides: {rd2}; ties in: {rd3} "
                f"| {direction_matches(r)} | {len(rep['worse'][m])} | {rt_s} |")
    return "\n".join(lines)


def splits_markdown(rep: dict) -> str:
    f, ci = pooled._f, pooled._ci
    lines = ["| candidate | split | n scored | n decided | kappa, sides only | 95% CI pairs | 95% CI fixtures "
             "| kappa, ties in | 95% CI pairs | 95% CI fixtures |", "|" + "---|" * 10]
    for m in CANDIDATES:
        r = rep["instruments"][m]
        for name, _ in SPLITS:
            s = r[f"split_{name}"]
            lines.append(f"| `{m}` | {name.replace('_', ' ')} | {s['n_scored']} | {s['n_decided']} "
                         f"| {f(s['kappa_decided'])} | {ci(s['ci2_lo'], s['ci2_hi'])} | {ci(*s['ci2_cluster'])} "
                         f"| {f(s['kappa_3way'])} | {ci(s['ci3_lo'], s['ci3_hi'])} | {ci(*s['ci3_cluster'])} |")
        s = r["sens_both_bad_dropped"]
        lines.append(f"| `{m}` | both_bad dropped | {s['n_scored']} | {s['n_decided']} "
                     f"| {f(s['kappa_decided'])} | {ci(s['ci2_lo'], s['ci2_hi'])} | - "
                     f"| {f(s['kappa_3way'])} | {ci(s['ci3_lo'], s['ci3_hi'])} | - |")
    return "\n".join(lines)


def both_bad_markdown(rep: dict) -> str:
    f, ci = pooled._f, pooled._ci
    lines = ["| level instrument | source | bad side | n | n both bad | split (pooled median) | n flagged "
             "| kappa (2x2) | 95% CI pairs | 95% CI fixtures | reading |", "|" + "---|" * 11]
    for m, d, src in BOTH_BAD:
        r = rep["both_bad"][m]
        thr = "n/a" if r.get("threshold") is None else f"{r['threshold']:.4g}"
        lines.append(f"| `{m}` | {src} | {'above' if d == 'lower' else 'below'} | {r['n']} | {r['n_both_bad']} "
                     f"| {thr} | {r.get('n_flagged', 0)} | {f(r['kappa'])} | {ci(r['ci_lo'], r['ci_hi'])} "
                     f"| {ci(*r['ci_cluster'])} | "
                     f"{pooled.reading(r['n'], (r['ci_lo'], r['ci_hi']), r['ci_cluster'])} |")
    return "\n".join(lines)


def worse_markdown(rep: dict) -> str:
    out = []
    for m, rows in rep["worse"].items():
        if not rows:
            continue
        out.append(f"\n#### `{m}` ({len(rows)} pairs) - {CANDIDATES[m][1]}\n")
        out.append("| pair | Kent | before | after | margin (Kent's pick worse by) |")
        out.append("|---|---|---|---|---|")
        for r in rows:
            out.append(f"| `{r['pair']}` | {r['kent']} | {r['before']:.4g} | {r['after']:.4g} | {r['margin']:.3g} |")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cmd", choices=["report"])
    ap.add_argument("--inputs", type=Path, default=INPUTS)
    ap.add_argument("--markdown", action="store_true", help="also print the worse-pair lists")
    ap.add_argument("--json", type=Path, help="also write the full report as JSON")
    args = ap.parse_args(argv)
    rep = full_report(load(args.inputs))
    if args.json:
        args.json.write_text(json.dumps(rep, indent=1), encoding="utf-8")
    print(f"judged pairs: {rep['n_judged_pairs']}  primary scope: {rep['n_primary']}  "
          f"with stored designs: {rep['n_with_designs']}\n")
    print(kappa_table_markdown(rep))
    print()
    print(both_bad_markdown(rep))
    if args.markdown:
        print()
        print(splits_markdown(rep))
        print(worse_markdown(rep))
    return 0


if __name__ == "__main__":
    sys.exit(main())
