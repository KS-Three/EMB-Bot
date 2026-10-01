"""The analysis, fixed before any pick was seen (spec section 4).

Everything here is pure: `sealed` (pair -> what was shown), `picks` (pair ->
final click) and `features` (fixture -> arm -> metric values) go in, plain
dicts come out. ROADMAP gate 4: no raw agreement is ever returned without its
n, its interval and the chance-corrected `kappa = 2a - 1`.
"""
from __future__ import annotations

import math

import numpy as np

from .pairs import BASE

# metric -> which way is BETTER. "none" is descriptive only: the spec gives
# those no direction, so they can never be scored as agreement.
METRICS: dict[str, str] = {
    "trims_per_1000": "lower",
    "preflight_raw_score": "higher",
    "preflight_blocks": "lower",
    "uncovered_total_mm2": "lower",
    "thread_worst_delta_e": "lower",
    "artfid": "higher",
    "artfid_no_colour": "higher",
    "artfid_coverage": "higher",
    "artfid_structure": "higher",
    "artfid_colour": "higher",
    "lost_elements": "lower",
    "lost_frac": "lower",
    "ragged_mm": "lower",
    "hausdorff_mm": "lower",
    "roughness_deg": "lower",
    "thin_recall": "higher",
    "legibility": "higher",
    "stitches": "none",
    "cones": "none",
    "stops": "none",
}
# Named on 2026-09-17, before any pick: fidelity plus Kent's two 08-27 themes.
EXPLORATORY = ("artfid", "lost_elements", "ragged_mm", "roughness_deg")
MIN_N_VERDICT = 10
MIN_N_FIT = 40


def wilson(k: float, n: int, z: float = 1.959964) -> tuple[float, float]:
    """`k` may be fractional: the exploratory fit's single-metric accuracy
    gives half credit to a pair the metric has no say on."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    denom = 1.0 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, centre - half), min(1.0, centre + half))


def _arm_of(s: dict) -> str:
    return s["right_arm"] if s["left_arm"] == BASE else s["left_arm"]


def _picked(s: dict, pick: dict | None) -> str | None:
    """-> the arm id Kent chose, "tie", or None when the pair has no pick."""
    if not pick:
        return None
    if pick["choice"] == "tie":
        return "tie"
    return s["left_arm"] if pick["choice"] == "L" else s["right_arm"]


def decided_rows(sealed: dict, picks: dict, *, ref: bool) -> list[dict]:
    """Decided LIVE pairs. `ref=True` selects the design-only arms (an older
    engine run out of process), `ref=False` everything else — the two are
    never pooled, because a design-only arm carries only the Design-dict
    metrics. The bucket is the STORED `design_only` flag on the sealed map,
    never the arm's name (review finding 6, 2026-09-17)."""
    rows = []
    for pid in sorted(sealed):
        s = sealed[pid]
        if s["kind"] != "live":
            continue
        arm = _arm_of(s)
        if bool(s.get("design_only", False)) != ref:
            continue
        picked = _picked(s, picks.get(pid))
        if picked in (None, "tie"):
            continue
        rows.append({"pair": pid, "fixture": s["fixture"], "arm": arm,
                     "picked_arm": picked, "picked_is_arm": picked == arm})
    return rows


def _value(features: dict, fixture: str, arm: str, metric: str) -> float | None:
    v = features.get(fixture, {}).get(arm, {}).get(metric)
    if v is None:
        return None
    v = float(v)
    return None if math.isnan(v) else v


def _refused(features: dict, fixture: str, arm: str, metric: str) -> bool:
    return metric in (features.get(fixture, {}).get(arm, {}).get("refusals") or {})


def _both(features: dict, row: dict, metric: str, *, ties: bool) -> tuple[float, float] | None:
    """-> (base value, arm value) for one decided row, or None when the
    metric cannot speak on it: missing on either arm, always; equal on both,
    unless `ties`.

    THE one place a pair's two values are fetched. `ties` has no default
    because what a tie means is the caller's decision, and the callers
    differ on purpose: a verdict (`_scored`) and a lean drop a tie — the
    metric prefers neither arm — while the exploratory fit keeps it as a
    zero delta, "no say" on that one feature of a row that still has a
    pick and three other features. Written out three times, that difference
    was invisible (review 2026-09-17)."""
    b = _value(features, row["fixture"], BASE, metric)
    a = _value(features, row["fixture"], row["arm"], metric)
    if b is None or a is None or (not ties and a == b):
        return None
    return b, a


def _prefers_arm(metric: str, base_v: float, arm_v: float) -> bool | None:
    """True/False = the metric prefers the arm/the base; None = it has no
    direction, so it never has a say."""
    direction = METRICS[metric]
    if direction == "none":
        return None
    return arm_v > base_v if direction == "higher" else arm_v < base_v


def _scored(rows, features, metric, include_refused):
    for r in rows:
        if not include_refused and (
                _refused(features, r["fixture"], BASE, metric)
                or _refused(features, r["fixture"], r["arm"], metric)):
            continue
        values = _both(features, r, metric, ties=False)
        pref = None if values is None else _prefers_arm(metric, *values)
        if pref is not None:
            yield r, *values, pref


# How far the expected-by-chance agreement may sit from 0.5 before the
# report says so. Past it, `kappa` (the pre-registered 2a-1) and
# `kappa_marginal` part company and only the second is a chance correction.
SKEW_WARN = 0.05


def sign_agreement(rows: list[dict], features: dict, metric: str,
                   include_refused: bool = False) -> dict:
    """Does the metric point the way Kent did, above chance?

    `a` is the share of scored pairs where they agree. The spec pre-registered
    `kappa = 2a - 1`, which puts chance at 0.5 — true only when Kent's picks
    and the metric's preferences are each split 50/50 between arm and base.
    Neither is balanced by construction (`build_pairs` balances LEFT/RIGHT,
    not arm/base), and the ten arms are default-OFF flags with measured
    costs, so a shared lean toward shipped is the realistic case. Under one,
    an independent metric agrees above 0.5 by arithmetic alone: both at 75%
    base gives a = 0.625, and Wilson's lower bound clears 0.5 at n = 60
    (review finding 2026-09-17, verified numerically).

    So the chance floor is taken from the observed marginals the way this
    repo's other chance corrections do (`scorecard.type_chance`):
    `pe = p_pick * p_metric + (1 - p_pick) * (1 - p_metric)`, and the verdict
    tests Wilson's interval on `a` against `pe`, not 0.5. `kappa_marginal =
    (a - pe) / (1 - pe)` is the corrected figure; `kappa` is kept beside it
    because it was pre-registered, and `skewed` says when the two disagree.
    A metric that answers the same way on every pair has `p_metric` of 0 or
    1, `pe == a`, and earns exactly nothing — which is right.
    """
    n = k = picked_arm = metric_arm = 0
    for r, _b, _a, pref in _scored(rows, features, metric, include_refused):
        n += 1
        k += pref == r["picked_is_arm"]
        picked_arm += r["picked_is_arm"]
        metric_arm += pref
    lo, hi = wilson(k, n)
    a = k / n if n else None
    p_pick = picked_arm / n if n else None
    p_metric = metric_arm / n if n else None
    pe = (p_pick * p_metric + (1 - p_pick) * (1 - p_metric)) if n else None
    kappa_marginal = None
    if pe is not None and pe < 1.0:
        kappa_marginal = (a - pe) / (1 - pe)
    if n < MIN_N_VERDICT:
        verdict = "n too small"
    elif lo > pe:
        verdict = "agrees"
    elif hi < pe:
        verdict = "anti-agrees"
    else:
        verdict = "no evidence"
    return {"metric": metric, "n": n, "k": k, "a": a,
            "kappa": None if a is None else 2 * a - 1,
            "p_pick": p_pick, "p_metric": p_metric, "pe": pe,
            "kappa_marginal": kappa_marginal,
            "skewed": (pe is not None and abs(pe - 0.5) > SKEW_WARN),
            "lo": lo, "hi": hi, "verdict": verdict}


def exit_clause(rows: list[dict], features: dict, metric: str) -> list[dict]:
    """Phase 1's second clause, read literally: every decided pair where Kent
    picked the arm this metric scores WORSE. Refused pairs are included and
    marked — this is a list of renders to open, not a statistic."""
    out = []
    for r, b, a, pref in _scored(rows, features, metric, include_refused=True):
        if pref != r["picked_is_arm"]:
            out.append({"pair": r["pair"], "fixture": r["fixture"], "arm": r["arm"],
                        "picked": r["picked_arm"], "base_value": b, "arm_value": a,
                        "refused": _refused(features, r["fixture"], BASE, metric)
                        or _refused(features, r["fixture"], r["arm"], metric)})
    return out


def per_fixture_sign(rows: list[dict], features: dict, metric: str) -> dict:
    """Pairs from one fixture are not independent; nine fixtures are the real n."""
    fixtures: dict[str, dict] = {}
    for r, _b, _a, pref in _scored(rows, features, metric, include_refused=False):
        cell = fixtures.setdefault(r["fixture"], {"n": 0, "k": 0})
        cell["n"] += 1
        cell["k"] += pref == r["picked_is_arm"]
    agree = sum(1 for c in fixtures.values() if 2 * c["k"] > c["n"])
    disagree = sum(1 for c in fixtures.values() if 2 * c["k"] < c["n"])
    return {"metric": metric, "fixtures": fixtures, "agree": agree, "disagree": disagree}


def lean(rows: list[dict], features: dict, metric: str) -> dict:
    """For a directionless metric: how often Kent picked the HIGHER value."""
    n = hi = 0
    for r in rows:
        values = _both(features, r, metric, ties=False)
        if values is None:
            continue
        b, a = values
        n += 1
        hi += (a > b) == r["picked_is_arm"]
    return {"metric": metric, "n": n, "picked_higher": hi}


def ceiling(sealed: dict, picks: dict) -> dict:
    n = k = 0
    for pid, s in sealed.items():
        if s["kind"] != "repeat":
            continue
        first = _picked(sealed[s["repeat_of"]], picks.get(s["repeat_of"]))
        again = _picked(s, picks.get(pid))
        if first is None or again is None:
            continue
        n += 1
        k += first == again
    return {"n": n, "consistent": k, "share": k / n if n else None}


def controls(sealed: dict, picks: dict) -> dict:
    ident = [picks[p]["choice"] for p, s in sealed.items()
             if s["kind"] == "identical" and p in picks]
    sided = [c for c in ident if c != "tie"]
    every = [picks[p]["choice"] for p in sealed if p in picks and picks[p]["choice"] != "tie"]
    return {
        "identical_n": len(ident),
        "identical_tie_rate": ident.count("tie") / len(ident) if ident else None,
        "identical_left_share": sided.count("L") / len(sided) if sided else None,
        "left_share_all": every.count("L") / len(every) if every else None,
    }


def flag_table(sealed: dict, picks: dict) -> dict:
    """Per arm: wins (Kent picked the arm), losses (the base), ties. Evidence
    for Kent's flag rulings — this tool flips nothing."""
    table: dict[str, dict] = {}
    for pid in sorted(sealed):
        s = sealed[pid]
        if s["kind"] != "live":
            continue
        arm = _arm_of(s)
        picked = _picked(s, picks.get(pid))
        if picked is None:
            continue
        row = table.setdefault(arm, {"wins": 0, "losses": 0, "ties": 0, "by_fixture": {}})
        outcome = "ties" if picked == "tie" else "wins" if picked == arm else "losses"
        row[outcome] += 1
        row["by_fixture"][s["fixture"]] = outcome
    return table


def ref_confound(env: dict | None, photo_class: bool) -> dict:
    """Is a ref arm's difference from today's arm partly the ENVIRONMENT's?

    -> {"confounded": True | False | None, "why": [every fact that fired]}.
    Decided from facts measured when the row was rendered
    (`refarm.ref_environment`), never from the design class alone: that
    proxy called every photo-class fixture confounded, and on a checkout
    with no rembg venv — every worktree — today's engine skips photo prep
    exactly as the old one does, so there was nothing to flag (review
    2026-09-17). None means the row predates the record: unknown, not clean.
    """
    if not env:
        return {"confounded": None,
                "why": ["environment not recorded when this arm was rendered"]}
    why = []
    if env["requirements_differ"]:
        why.append(f"requirements.txt differs between {env['ref']} and HEAD: the old "
                   "source ran under pins it was not written for")
    if photo_class and env["rembg_venv_main"] != env["rembg_venv_ref"]:
        only = "today's" if env["rembg_venv_main"] else "the old"
        why.append(f"photo-class fixture, and the rembg venv existed for {only} engine "
                   "only: one arm skipped photo prep")
    return {"confounded": bool(why), "why": why}


# ---- exploratory, and labelled so (spec section 4, SECONDARY) --------------

def _logistic(A: np.ndarray, y: np.ndarray, ridge: float) -> np.ndarray:
    """Ridge-penalised logistic regression by Newton's method. The intercept
    (column 0) is not penalised. The ridge is what keeps a perfectly
    separable sample — likely at this n — from running the weights to
    infinity."""
    w = np.zeros(A.shape[1])
    R = ridge * np.eye(A.shape[1])
    R[0, 0] = 0.0
    for _ in range(50):
        p = 1.0 / (1.0 + np.exp(-(A @ w)))
        grad = A.T @ (p - y) + R @ w
        hess = (A * (p * (1 - p))[:, None]).T @ A + R + 1e-9 * np.eye(A.shape[1])
        step = np.linalg.solve(hess, grad)
        w = w - step
        if np.abs(step).max() < 1e-8:
            break
    return w


def exploratory_fit(rows: list[dict], features: dict,
                    names: tuple[str, ...] = EXPLORATORY,
                    min_n: int = MIN_N_FIT, ridge: float = 1.0) -> dict | None:
    """Does a small combination beat the best single metric, judged on
    fixtures it never saw? None under `min_n` rows: a fit on less is the
    'weights that reproduce the table they were solved from' trap ARTFID's
    own composite already fell into. The weights are reported and shipped
    nowhere."""
    X, y, fx = [], [], []
    for r in rows:
        vals = []
        for m in names:
            # `ties=True`, deliberately: a zero delta is "no say" on ONE
            # feature of a row that still has a pick and three others.
            values = _both(features, r, m, ties=True)
            if values is None:
                break
            b, a = values
            # Oriented: positive always means "this metric prefers the arm".
            vals.append(a - b if METRICS[m] == "higher" else b - a)
        else:
            X.append(vals)
            y.append(1.0 if r["picked_is_arm"] else 0.0)
            fx.append(r["fixture"])
    if len(X) < min_n:
        return None

    X, y, fx = np.asarray(X, float), np.asarray(y, float), np.asarray(fx)
    scale = X.std(axis=0)
    scale[scale == 0] = 1.0
    Z = X / scale          # scaled, NOT centred: a zero delta stays "no say"
    A = np.hstack([np.ones((len(Z), 1)), Z])

    hits = total = scored_arm = 0
    for held in sorted(set(fx.tolist())):
        test, train = fx == held, fx != held
        if len(set(y[train].tolist())) < 2:
            continue                    # one answer to learn from: no model
        w = _logistic(A[train], y[train], ridge)
        hits += int((((A[test] @ w) > 0) == (y[test] == 1.0)).sum())
        total += int(test.sum())
        scored_arm += int((y[test] == 1.0).sum())

    singles = {}
    for j, m in enumerate(names):
        credit = np.where(Z[:, j] == 0, 0.5, ((Z[:, j] > 0) == (y == 1.0)).astype(float))
        singles[m] = float(credit.mean())
    best = max(singles, key=singles.get)

    # ROADMAP gate 4: neither accuracy is returned without its floor. Always
    # guessing Kent's commoner pick scores `baseline` knowing nothing, and the
    # arms are default-OFF flags he mostly turns down, so that floor is
    # nowhere near 0.5 (review 2026-09-17: both figures were printed raw).
    baseline = float(max(y.mean(), 1.0 - y.mean()))
    # An accuracy and its floor are taken over the SAME rows. A fold is
    # skipped when holding its fixture out leaves one answer to learn from,
    # so LOFO can score fewer rows than `n` — and if every arm-pick sits in
    # that one fixture, the rows it does score are all "shipped": 1.00 on
    # them is their floor, and against the all-row floor (59/60) it read
    # "+1.00 above baseline" for a model that learned nothing.
    lofo_baseline = (max(scored_arm, total - scored_arm) / total) if total else None

    def above(acc, floor):
        if acc is None or floor is None or floor >= 1.0:
            return None
        return (acc - floor) / (1.0 - floor)

    lofo = hits / total if total else None
    lofo_lo, lofo_hi = wilson(hits, total)
    return {"label": "EXPLORATORY", "n": int(len(y)), "features": list(names),
            "weights": [float(v) for v in _logistic(A, y, ridge)],
            "majority_baseline": baseline,
            "lofo_accuracy": lofo, "lofo_hits": hits, "lofo_n": total,
            "lofo_baseline": lofo_baseline,
            "lofo_wilson": [lofo_lo, lofo_hi],
            "lofo_above_baseline": above(lofo, lofo_baseline),
            # The same test `sign_agreement` applies to `pe`: the interval's
            # lower bound has to clear the floor, not the point estimate.
            "lofo_beats_baseline": bool(total and lofo_lo > lofo_baseline),
            "best_single": {"metric": best, "accuracy": singles[best],
                            "wilson": list(wilson(singles[best] * len(y), len(y))),
                            "above_baseline": above(singles[best], baseline)}}
