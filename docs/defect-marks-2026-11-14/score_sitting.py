"""Score the 2026-11-14 photo subject-recall sitting EXACTLY as
`subject-recall-preregistration.md` (commit 34bc7177) says.

    cd digitizer
    python ../docs/defect-marks-2026-11-14/score_sitting.py ROWS.json

ROWS.json comes from `python -m tools.subject_detail --runs <live>/corpus_runs/subject-1114-838b28ff
--photos <live>/eye_pairs_out/defect-marks-1114-art --out ROWS.json` (copied beside this file as
`rows.json`). Marks: `marks.json` beside this file, a byte copy of the sitting's file
(sha256 4b9949de...aaef).

Pre-registered, nothing added:
  LOST   = `detail_lost` or `unrecognizable` ticked, whatever the grade
  GOOD   = Good / Great with neither tick
  MIDDLE = any other graded item; no grade and no tick = left out
  primary: Somers' D (2 AUC - 1), LOST vs GOOD, low reading = lost, 95% bootstrap
           interval, 5,000 resamples within each group, seed 0
  cut-off: c = 0.90, flagged = reading < 0.90; Cohen's kappa flagged vs LOST over the
           LOST + GOOD items, 95% bootstrap interval, 5,000 resamples of items, seed 0
  minimum: 4 LOST and 4 GOOD for ANY verdict, else "no verdict: class not filled"
One handling rule the pre-registration did not spell out (recorded in the result doc): a
bootstrap resample in which kappa is undefined (every resampled item on one side of the
cut-off AND of the label, expected agreement 1) is dropped from the kappa interval and
counted.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "digitizer"))
from tools.subject_detail import somers_d  # noqa: E402

CUT = 0.90
N_BOOT = 5000
MIN_EACH = 4
LOST_TICKS = {"detail_lost", "unrecognizable"}


def label(rec: dict) -> str | None:
    ticks = set(rec.get("whole") or [])
    if ticks & LOST_TICKS:
        return "LOST"
    if rec.get("grade") in ("Good", "Great"):
        return "GOOD"
    if rec.get("grade"):
        return "MIDDLE"
    return None


def kappa(flag: np.ndarray, lost: np.ndarray) -> float | None:
    po = float((flag == lost).mean())
    pf, pl = flag.mean(), lost.mean()
    pe = float(pf * pl + (1 - pf) * (1 - pl))
    return None if pe >= 1.0 else (po - pe) / (1.0 - pe)


def main(rows_path: str) -> dict:
    rows = json.loads(Path(rows_path).read_text(encoding="utf-8"))
    marks = json.loads((HERE / "marks.json").read_text(encoding="utf-8"))["items"]
    table = []
    for iid, rec in sorted(marks.items()):
        slug = iid[2:] if iid.startswith("P_") else iid
        r = rows.get(slug, {})
        table.append({"item": iid, "grade": rec.get("grade"), "ticks": sorted(rec.get("whole") or []),
                      "pins": len(rec.get("pins") or []), "label": label(rec),
                      "edge_recall": r.get("edge_recall")})
    lost = [t for t in table if t["label"] == "LOST" and t["edge_recall"] is not None]
    good = [t for t in table if t["label"] == "GOOD" and t["edge_recall"] is not None]
    out = {"n_lost": len(lost), "n_good": len(good), "table": table}
    if len(lost) < MIN_EACH or len(good) < MIN_EACH:
        out["verdict"] = "no verdict: class not filled"
        return out
    lv = np.array([t["edge_recall"] for t in lost]); gv = np.array([t["edge_recall"] for t in good])
    d = somers_d(lv, gv, -1)
    rng = np.random.default_rng(0)
    boots = [somers_d(rng.choice(lv, len(lv)), rng.choice(gv, len(gv)), -1) for _ in range(N_BOOT)]
    d_lo, d_hi = (float(x) for x in np.percentile(boots, [2.5, 97.5]))
    vals = np.concatenate([lv, gv]); is_lost = np.array([1] * len(lv) + [0] * len(gv))
    flag = (vals < CUT).astype(int)
    k = kappa(flag, is_lost)
    rng = np.random.default_rng(0)
    kb, undefined = [], 0
    for _ in range(N_BOOT):
        idx = rng.integers(0, len(vals), len(vals))
        kk = kappa(flag[idx], is_lost[idx])
        if kk is None:
            undefined += 1
        else:
            kb.append(kk)
    k_lo, k_hi = (float(x) for x in np.percentile(kb, [2.5, 97.5]))
    out.update({"somers_d": round(d, 3), "d_ci95": [round(d_lo, 3), round(d_hi, 3)],
                "kappa": None if k is None else round(k, 3), "kappa_ci95": [round(k_lo, 3), round(k_hi, 3)],
                "kappa_undefined_resamples": undefined,
                "good_below_cut": [t["item"] for t in good if t["edge_recall"] < CUT]})
    if d_lo <= 0 or d <= 0.20:
        out["verdict"] = "drop it"
    elif k_lo <= 0:
        out["verdict"] = "keep as a metric, no change"
    elif d >= 0.60 and not out["good_below_cut"]:
        out["verdict"] = "propose a finding, and a grade cost as an option"
    else:
        out["verdict"] = "propose a finding"
    return out


if __name__ == "__main__":
    print(json.dumps(main(sys.argv[1]), indent=1))
