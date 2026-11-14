"""Score `tools.subject_detail` readings against Kent's grades of the same renders.

Labels come from the defect-marks sittings that graded corpus rows on the
tree the captures were made on (950855bf): `docs/defect-marks-2026-11-10`
(the 4 corpus photos) and `docs/defect-marks-2026-11-11` (the 21 Commons
logos). LOST = he ticked `detail_lost` or `unrecognizable`; GOOD = graded
Good or Great with neither tick; every other graded row is MIDDLE and
sits out of the contrast.

The figure is chance-corrected: Somers' D = 2 x AUC - 1 for "the reading
puts a LOST row on the lost side of a GOOD row" (0 = chance, 1 = every pair
ordered), with a 95% bootstrap interval resampled within each group.

`python -m tools.subject_detail_score ROWS.json` prints ASCII only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

DOCS = Path(__file__).resolve().parents[2] / "docs"
SITTINGS = ("defect-marks-2026-11-10", "defect-marks-2026-11-11")
LOST_TICKS = {"detail_lost", "unrecognizable"}

#: reading -> +1 when HIGH means lost, -1 when LOW means lost
READINGS = {"edge_recall": -1, "blob_lost_frac": +1, "salient_lost_frac": +1,
            "element_dropped_frac": +1, "edge_density": +1}


def labels() -> dict[str, dict]:
    out = {}
    for s in SITTINGS:
        marks = json.loads((DOCS / s / "marks.json").read_text(encoding="utf-8"))["items"]
        for item, v in marks.items():
            if not item.startswith(("P_", "C_")):
                continue            # pro-paired logos: not corpus rows
            ticks = set(v.get("whole") or [])
            grade = v.get("grade")
            if ticks & LOST_TICKS:
                lab = "LOST"
            elif grade in ("Good", "Great"):
                lab = "GOOD"
            else:
                lab = "MIDDLE"
            out[item[2:]] = {"grade": grade, "ticks": sorted(ticks), "label": lab}
    return out


def somers_d(lost: np.ndarray, good: np.ndarray, sign: int) -> float:
    a, b = sign * lost[:, None], sign * good[None, :]
    auc = float(((a > b).sum() + 0.5 * (a == b).sum()) / (len(lost) * len(good)))
    return 2.0 * auc - 1.0


def score(rows: dict, n_boot: int = 5000, seed: int = 0) -> dict:
    lab = labels()
    rng = np.random.default_rng(seed)
    out = {}
    for key, sign in READINGS.items():
        lost = np.array([rows[s][key] for s, v in lab.items()
                         if v["label"] == "LOST" and rows.get(s, {}).get(key) is not None], float)
        good = np.array([rows[s][key] for s, v in lab.items()
                         if v["label"] == "GOOD" and rows.get(s, {}).get(key) is not None], float)
        if not len(lost) or not len(good):
            out[key] = None
            continue
        d = somers_d(lost, good, sign)
        boots = [somers_d(rng.choice(lost, len(lost)), rng.choice(good, len(good)), sign)
                 for _ in range(n_boot)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        out[key] = {"somers_d": round(d, 3), "ci95": [round(float(lo), 3), round(float(hi), 3)],
                    "n_lost": len(lost), "n_good": len(good)}
    return out


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    rows = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    print(json.dumps({"labels": labels(), "scores": score(rows)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
