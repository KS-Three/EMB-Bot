"""The pro-pair figures against Kent's eye, pooled: the 10-11 method on the
readings that actually drive the flips.

    python -m tools.eye_pairs.pro_pooled report [--inputs PATH] [--markdown] [--json PATH]

`docs/yardstick-vs-kents-eye-2026-10-11.md` found no fidelity instrument that
clears chance against Kent's before | after picks. The instruments the flips
are judged by are different ones: one reader on OUR machine file and on the
PRO'S for the same job (`tools/pro_baseline.py`, `lettering_board.py`,
`word_legibility.py`): cuts, needle-up moves and mm, the stitch-type kappa,
the word-legibility cc, the Column-lane column count. This pools those over
the same labelled pairs, exactly as `pooled.py` pooled the fidelity ones.
ROADMAP gate 4 holds: no raw agreement figure is computed or printed.

Pure: `pro-pair-inputs.json` (built by `pro_pooled_build.py`: both arms of
every pair re-digitized on the sitting's tree at the pro's width and garment,
read beside the pro's DST) goes in, plain dicts come out.

Each instrument is read as a DISTANCE to the pro
------------------------------------------------
* a count or a length (`cuts`, `hops`, `needle_up_mm`, `columns`):
  |ours - pro|;
* the stitch-type kappa: 1 - kappa (the pro against his own file is 1);
* the word-legibility cc: |cc_ours - cc_pro| over the words both files read.

Lower is closer. The instrument "says after is closer to the pro" when
after's distance is the smaller; exactly equal distances are a tie. The pro's
board figures (columns, cc) are read in a frame registered to OUR file, so
each side carries the pro reading taken beside it (`pro_side`); the DST-level
figures (cuts, hops, mm) are the pro's file alone.

The statistics are `pooled.py`'s, unchanged: the decided 2 x 2 kappa, the
3-way linear-weighted kappa with ties in, percentile bootstrap over pairs and
over fixtures, nothing read under 10 pairs, `both_bad` folded into the tie or
dropped. One sensitivity is new: `signed` reads every figure as a plain cost
with no pro in it (fewer cuts / hops / mm / columns better, higher kappa / cc
better) -- the 10-11 doc's own reading of trims -- so the table shows what the
pro reference adds over "less is better". `no_tires` drops the one fixture
whose pro file is 3D puff (`tires_hat_3d`), a construction ours never sews.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import pooled
from .pooled import (B, SEED, VOCABULARY, LabelVocabularyError, agreement, inventory_markdown,  # noqa: F401
                     reading, select, worse_pairs)

INPUTS = Path(__file__).resolve().parents[3] / "docs" / "eye-pairs-2026-11-01" / "pro-pair-inputs.json"

#: instrument -> (kind, one-line meaning). `kind` decides the distance.
INSTRUMENTS: dict[str, tuple[str, str]] = {
    "cuts": ("count", "cuts: TRIM records, pystitch on both DSTs (pro_pair.pro_counts)"),
    "hops": ("count", "needle-up moves: gaps the needle flies with the thread up (pro_baseline.needle_up)"),
    "needle_up_mm": ("length", "needle-up travel, mm, summed over those gaps"),
    "sttype_kappa": ("kappa", "stitch-type kappa over the shared solid area, both DSTs decoded alike (pro_parity.scorecard)"),
    "word_cc": ("cc", "word-legibility cc, letter-weighted over the pinned words both files read (word_legibility)"),
    "columns": ("count", "satin columns over the pinned lines of lettering (column_harness.census via lettering_board)"),
}
#: the pooled.py direction table for the transformed rows: every distance is lower-is-closer
DISTANCE_DIRECTIONS = {m: ("lower", f"distance to the pro: {why}") for m, (_k, why) in INSTRUMENTS.items()}
#: ... and for the pro-free cost reading (sensitivity): lower cost is better, a kappa or cc is negated
COST_DIRECTIONS = {m: ("lower", f"plain cost, no pro: {why}") for m, (_k, why) in INSTRUMENTS.items()}
MODES = ("distance", "signed")
PUFF_FIXTURES = frozenset({"tires"})


def validate(inputs: dict) -> None:
    """`pooled.validate`'s vocabulary rule, plus: a pair with readings has a `pro`."""
    pooled.validate(inputs)
    for sid, s in inputs["sittings"].items():
        for p in s["pairs"]:
            if (p.get("before") or p.get("after")) and "pro" not in p:
                raise LabelVocabularyError(f"REFUSED: sitting {sid!r}, pair {p.get('id')!r} has readings but no `pro`")


def pro_value(pair: dict, side: str, metric: str):
    """The pro's reading to measure `side` against: the one taken beside that
    side when there is one (board figures), else the pro file's own."""
    v = ((pair.get("pro_side") or {}).get(side) or {}).get(metric)
    if v is None:
        v = (pair.get("pro") or {}).get(metric)
    return v


def distance(metric: str, ours, pro):
    """How far `ours` is from the pro on `metric`; None when either is missing."""
    kind = INSTRUMENTS[metric][0]
    if ours is None:
        return None
    if kind == "kappa":
        return round(1.0 - float(ours), 6)
    if pro is None:
        return None
    return round(abs(float(ours) - float(pro)), 6)


def cost(metric: str, ours):
    """The pro-free reading: a count or length as it is, a kappa or cc negated
    (so lower is better everywhere, as `instrument_pick` expects)."""
    if ours is None:
        return None
    kind = INSTRUMENTS[metric][0]
    return round(-float(ours), 6) if kind in ("kappa", "cc") else float(ours)


def transformed_pairs(inputs: dict, mode: str = "distance") -> list[dict]:
    """Every judged pair with `before` / `after` replaced by the instruments'
    distances to the pro (or costs). Pairs without both designs keep empty
    dicts and are counted, not scored."""
    if mode not in MODES:
        raise ValueError(f"mode is one of {MODES}")
    validate(inputs)
    out = []
    for p in pooled.pooled_pairs(inputs):
        q = {k: v for k, v in p.items() if k not in ("before", "after")}
        for side in ("before", "after"):
            vals = {}
            for m in INSTRUMENTS:
                ours = (p.get(side) or {}).get(m)
                v = distance(m, ours, pro_value(p, side, m)) if mode == "distance" else cost(m, ours)
                if v is not None:
                    vals[m] = v
            q[side] = vals
        out.append(q)
    return out


def _directions(mode: str) -> dict:
    return DISTANCE_DIRECTIONS if mode == "distance" else COST_DIRECTIONS


def drop_fixtures(rows: list[dict], fixtures) -> list[dict]:
    return [r for r in rows if r["fixture"] not in fixtures]


def full_report(inputs: dict) -> dict:
    pairs = transformed_pairs(inputs, "distance")
    rows = select(pairs)
    both = [p for p in rows if p["before"] and p["after"]]
    signed = select(transformed_pairs(inputs, "signed"))
    out = {"n_judged_pairs": len(pairs), "n_primary": len(rows), "n_with_both_designs": len(both),
           "n_decided_with_both_designs": sum(1 for p in both if p["kent"] != "tie"),
           "label_counts": {lab: sum(1 for p in pairs if p["label"] == lab) for lab in VOCABULARY},
           "unscored": [{"pair": p["id"], "why": p.get("unscored_why", "a design is missing")}
                        for p in rows if not (p["before"] and p["after"])],
           "instruments": {}, "worse": {}}
    d = DISTANCE_DIRECTIONS
    for m in INSTRUMENTS:
        r = agreement(rows, m, directions=d)
        c = agreement(rows, m, cluster=True, directions=d)
        r["ci3_cluster"] = (c["ci3_lo"], c["ci3_hi"])
        r["ci2_cluster"] = (c["ci2_lo"], c["ci2_hi"])
        r["sens_both_bad_dropped"] = _brief(agreement(select(pairs, both_bad="drop"), m, directions=d))
        r["sens_no_tires"] = _brief(agreement(drop_fixtures(rows, PUFF_FIXTURES), m, directions=d))
        r["sens_signed_cost"] = _brief(agreement(signed, m, directions=COST_DIRECTIONS))
        out["instruments"][m] = r
        out["worse"][m] = worse_pairs(rows, m, directions=d)
    out["worse_signed"] = {m: worse_pairs(signed, m, directions=COST_DIRECTIONS) for m in INSTRUMENTS}
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
    lines = ["| instrument (distance to the pro) | n scored | n Kent chose a side | instrument silent there | n decided | kappa, sides only (2x2) | 95% CI pairs | 95% CI fixtures | kappa, ties in (3-way, weighted) | 95% CI pairs | 95% CI fixtures | pairs scoring Kent's pick farther from the pro | reading |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for m, r in rep["instruments"].items():
        if r["n_scored"] == 0:
            lines.append(f"| `{m}` | 0 | 0 | 0 | 0 | n/a | n/a | n/a | n/a | n/a | n/a | 0 | not computed: no pair carries this instrument |")
            continue
        c3, c2 = r["ci3_cluster"], r["ci2_cluster"]
        lines.append(
            f"| `{m}` | {r['n_scored']} | {r['n_kent_decided']} | {r['n_instrument_silent_on_decided']} | {r['n_decided']} "
            f"| {_f(r['kappa_decided'])} | {_ci(r['ci2_lo'], r['ci2_hi'])} | {_ci(*c2)} "
            f"| {_f(r['kappa_3way'])} | {_ci(r['ci3_lo'], r['ci3_hi'])} | {_ci(*c3)} "
            f"| {len(rep['worse'][m])} "
            f"| sides: {reading(r['n_decided'], (r['ci2_lo'], r['ci2_hi']), c2)}; "
            f"with ties: {reading(r['n_scored'], (r['ci3_lo'], r['ci3_hi']), c3)} |")
    return "\n".join(lines)


def sensitivity_markdown(rep: dict) -> str:
    lines = ["| variant | instrument | n scored | n decided | kappa, sides only | kappa, ties in (3-way) | pairs scoring Kent's pick worse |",
             "|---|---|---|---|---|---|---|"]
    for key, label, worse_key in (("sens_both_bad_dropped", "`both_bad` pairs dropped, not folded into the tie", None),
                                  ("sens_no_tires", "tires (3D puff pro file) left out", None),
                                  ("sens_signed_cost", "plain cost, no pro reference (the 10-11 reading)", "worse_signed")):
        for m, r in rep["instruments"].items():
            s = r.get(key)
            if not s or s["n_scored"] == 0:
                continue
            w = len(rep[worse_key][m]) if worse_key else "-"
            lines.append(f"| {label} | `{m}` | {s['n_scored']} | {s['n_decided']} "
                         f"| {_f(s['kappa_decided'])} {_ci(s['ci2_lo'], s['ci2_hi'])} "
                         f"| {_f(s['kappa_3way'])} {_ci(s['ci3_lo'], s['ci3_hi'])} | {w} |")
    return "\n".join(lines)


def worse_markdown(rep: dict, key: str = "worse") -> str:
    out = []
    for m, rows in rep[key].items():
        if not rows:
            continue
        out.append(f"\n#### `{m}` ({len(rows)} pairs) - {INSTRUMENTS[m][1]}\n")
        out.append("| pair | Kent | before (distance) | after (distance) | margin (Kent's pick farther by) |")
        out.append("|---|---|---|---|---|")
        for r in rows:
            out.append(f"| `{r['pair']}` | {r['kent']} | {r['before']:g} | {r['after']:g} | {r['margin']:g} |")
    return "\n".join(out)


def pair_tally(rep: dict) -> list[dict]:
    seen: dict[str, dict] = {}
    for m in INSTRUMENTS:
        for r in rep["worse"].get(m, []):
            row = seen.setdefault(r["pair"], {"pair": r["pair"], "kent": r["kent"], "instruments": []})
            row["instruments"].append(m)
    return sorted(seen.values(), key=lambda r: (-len(r["instruments"]), r["pair"]))


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
    print(f"judged pairs with a pro file: {rep['n_judged_pairs']}  (primary scope: {rep['n_primary']}; "
          f"both designs: {rep['n_with_both_designs']}, Kent chose a side on {rep['n_decided_with_both_designs']})\n")
    print(inventory_markdown(inputs))
    print()
    print(kappa_table_markdown(rep))
    print()
    print(sensitivity_markdown(rep))
    if args.markdown:
        print("\n#### pairs that score Kent's pick farther from the pro on several instruments\n")
        print("| pair | Kent | instruments |\n|---|---|---|")
        for r in pair_tally(rep):
            print(f"| `{r['pair']}` | {r['kent']} | {len(r['instruments'])}: {', '.join(r['instruments'])} |")
        print(worse_markdown(rep))
        if rep["unscored"]:
            print("\n#### pairs without both designs\n")
            for u in rep["unscored"]:
                print(f"- `{u['pair']}`: {u['why']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
