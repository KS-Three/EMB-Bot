"""The vision pre-screen, computed exactly as
`docs/eye-pairs-2026-11-04/vlm-judge-100/PRESCREEN-PRE-REGISTRATION.md` fixes it.

Arithmetic over verdict and pick files already committed; no render, no model
call. Each verdict row falls in one class:

- "nothing to choose": choice == "tie" (any confidence)
- "plainly damaged":   choice L or R and confidence >= 4
- "Kent has to look":  choice L or R and confidence <= 3, or no choice

The threshold is 4 and only 4. The settled classes (the first two) are mapped
through the sealed side map and scored against Kent with `vlm_judge._kappas`.
The same function scores both data sets:

- the primary: the 11-04 judge's 54 recorded pairs;
- the replication: the 99 pairs of `vlm-judge-100`, whose judge knew this rule.

Run once and commit; a changed rule is a new dated pre-registration.

    python -m tools.eye_pairs.vlm_prescreen            # writes prescreen.json
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.eye_pairs import vlm_judge as vj

THRESHOLD = 4
NOTHING, DAMAGED, LOOK = "nothing_to_choose", "plainly_damaged", "kent_has_to_look"
SEED = 20261104

PRESCREEN_OUT = vj.PRO100_OUT
PRIMARY_MODEL = vj.SESSION_MODEL                 # claude-fable-5-1-session, 11-04
PRIMARY_EXCLUDE = frozenset({"P001", "P002", "P003"})   # 11-04 Amendment 1
REPLICATION_MODEL = "claude-opus-5-5-session"    # vlm-judge-100 Amendment 1
CONTAMINATION = ("The judge that wrote the 99 verdicts had written this rule before judging "
                 "and could, without meaning to, have pushed confidence on side picks up or down.")


def classify(row: dict | None) -> str:
    """One verdict row -> its pre-screen class."""
    if not row:
        return LOOK
    c = row.get("choice")
    if c == "tie":
        return NOTHING
    conf = row.get("confidence")
    if c in ("L", "R") and isinstance(conf, int) and conf >= THRESHOLD:
        return DAMAGED
    return LOOK


def _binary(rows: list[tuple[int, int, str]], seed: int = SEED) -> dict:
    """rows = (kent 0/1, screen 0/1, design). Unweighted 2x2 kappa with both
    percentile intervals and the repo's reading."""
    import numpy as np
    from tools.eye_pairs import pooled
    rng = np.random.default_rng(seed)
    if not rows:
        return {"n": 0, "kappa": None, "reading": "n too small (<10)"}
    k = np.array([r[0] for r in rows], dtype=int)
    j = np.array([r[1] for r in rows], dtype=int)
    d = [r[2] for r in rows]
    kappa = pooled.kappa_from_table(pooled._table(k, j, 2))
    lo, hi, _ = pooled._boot(k, j, d, 2, "none", cluster=False, rng=rng)
    clo, chi, _ = pooled._boot(k, j, d, 2, "none", cluster=True, rng=rng)
    table = [[0, 0], [0, 0]]
    for a, b, _ in rows:
        table[a][b] += 1
    return {"n": len(rows), "kappa": kappa, "ci_pairs": [lo, hi], "ci_designs": [clo, chi],
            "reading": pooled.reading(len(rows), (lo, hi), (clo, chi)),
            "table_kent_rows_screen_cols": table}


def screen(sitting: dict, rows: dict[str, dict], exclude: frozenset[str] = frozenset()) -> dict:
    """`sitting` as `vlm_judge.load_sitting` / `load_pro100` return it; `rows`
    = pair -> the judge's order-A verdict row."""
    sealed = {p: s for p, s in sitting["sealed"].items() if p not in exclude}
    picks = sitting["picks"]
    live = sorted(p for p, s in sealed.items() if s["kind"] == "live" and p in picks)
    ident = sorted(p for p, s in sealed.items() if s["kind"] == "identical")
    kent = {p: vj.to_label(picks[p], sealed[p]) for p in live}

    def design(p: str) -> str:
        return sitting["design_of"][sealed[p]["fixture"]]

    cls = {p: classify(rows.get(p)) for p in live}
    settled = [p for p in live if cls[p] != LOOK]
    primary = vj._kappas([(kent[p], vj.to_label(rows[p]["choice_frame_a"], sealed[p]), design(p))
                          for p in settled], seed=SEED)
    tie = _binary([(int(kent[p] == "tie"), int(cls[p] == NOTHING), design(p)) for p in live])
    dam_ids = [p for p in live if cls[p] == DAMAGED]
    damaged: dict = {"n": len(dam_ids)}
    if len(dam_ids) >= 10:
        damaged["sides"] = vj._kappas([(kent[p], vj.to_label(rows[p]["choice_frame_a"], sealed[p]),
                                        design(p)) for p in dam_ids], seed=SEED)
    else:
        damaged["pairs"] = [{"pair": p, "fixture": sealed[p]["fixture"], "kent": kent[p],
                             "screen": vj.to_label(rows[p]["choice_frame_a"], sealed[p]),
                             "confidence": rows[p].get("confidence"), "reason": rows[p].get("reason")}
                            for p in dam_ids]
    look = [p for p in live if cls[p] == LOOK]
    kent_sides = [p for p in live if kent[p] != "tie"]
    workload = {"n_live": len(live), "n_kent_has_to_look": len(look),
                "n_settled": len(settled),
                "n_nothing_to_choose": sum(1 for p in live if cls[p] == NOTHING),
                "n_plainly_damaged": len(dam_ids),
                "kent_side_picks": len(kent_sides),
                "kent_side_picks_in_look": sum(1 for p in kent_sides if cls[p] == LOOK),
                "kent_side_picks_in_nothing_to_choose": sum(1 for p in kent_sides if cls[p] == NOTHING),
                "kent_side_picks_in_plainly_damaged": sum(1 for p in kent_sides if cls[p] == DAMAGED)}
    identical = {"n": len(ident), "answered": sum(1 for p in ident if p in rows),
                 "not_nothing_to_choose": [p for p in ident if p in rows and classify(rows[p]) != NOTHING]}
    return {"threshold": THRESHOLD, "primary_settled": primary, "n_settled": len(settled),
            "n_live": len(live), "tie_class": tie, "damaged_class": damaged,
            "workload": workload, "identical_controls": identical}


def order_a(out: Path, model: str) -> dict[str, dict]:
    return vj.load_verdicts(out).get(model, {}).get("A", {})


def compute() -> dict:
    from tools.eye_pairs import pooled
    one = screen(vj.load_sitting(), order_a(vj.OUT, PRIMARY_MODEL), PRIMARY_EXCLUDE)
    hundred = screen(vj.load_pro100(), order_a(vj.PRO100_OUT, REPLICATION_MODEL))
    both = (one["primary_settled"]["reading_3way"] == "above chance"
            and hundred["primary_settled"]["reading_3way"] == "above chance")
    return {"rule": {"nothing_to_choose": "choice == tie",
                     "plainly_damaged": f"choice in (L, R) and confidence >= {THRESHOLD}",
                     "kent_has_to_look": f"choice in (L, R) and confidence <= {THRESHOLD - 1}, or no choice"},
            "seed": SEED, "resamples": getattr(pooled, "B", None),
            "primary": {"set": "pro-lettering-1102 (vlm-judge, 11-04)", "model": PRIMARY_MODEL,
                        "excluded": sorted(PRIMARY_EXCLUDE), **one},
            "replication": {"set": "vlm-judge-pro100 (vlm-judge-100, 11-06)", "model": REPLICATION_MODEL,
                            "contamination": CONTAMINATION, **hundred},
            "both_above_chance": both}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=str(PRESCREEN_OUT / "prescreen.json"))
    a = ap.parse_args(argv)
    rep = compute()
    Path(a.out).write_text(json.dumps(rep, indent=1) + "\n", encoding="utf-8")
    p, r = rep["primary"]["primary_settled"], rep["replication"]["primary_settled"]
    print(json.dumps({"primary": {k: p.get(k) for k in ("n_scored", "kappa_3way", "ci3_pairs", "ci3_designs", "reading_3way")},
                      "replication": {k: r.get(k) for k in ("n_scored", "kappa_3way", "ci3_pairs", "ci3_designs", "reading_3way")},
                      "both_above_chance": rep["both_above_chance"]}, indent=1))
    print(f"wrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
