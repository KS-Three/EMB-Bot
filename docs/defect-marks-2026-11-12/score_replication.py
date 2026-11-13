"""Score the letter-reader replication by its pre-registration's pass line
(`letter-reader-replication-preregistration.md` beside this file). Written
before any pin on these items exists; run only after Kent's marks are final.

    cd digitizer
    python -m tools.letter_fault_reader run --corpus-run corpus_runs/lettering-1112-<sha8> \
        --photos eye_pairs_out/defect-marks-1112-art --out eye_pairs_out/defect-marks-1112-flags \
        --only C_lt_<slug> ...                      # every item the rule gives a pin
    python ../docs/defect-marks-2026-11-12/score_replication.py \
        --marks eye_pairs_out/defect-marks-1112/marks.json --flags eye_pairs_out/defect-marks-1112-flags \
        --json ../docs/defect-marks-2026-11-12/letter-reader-replication-score.json

Verdict: "no verdict" under MIN_ITEMS items with selected pins; else "shown"
when the pooled (hit - chance_area) at 3 mm has its item-bootstrap lower bound
above 0 both with all selected pins (2a) and with rule-4 pins removed (2b);
"not shown" otherwise. A "shown" is "fragile" when dropping any one item puts
2a's lower bound at or below 0.
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "digitizer"))

from tools import fault_reader_harness as h  # noqa: E402

PREFIX = "C_lt_"
MIN_ITEMS = 5
NULL = "chance_area"


def drop_inherited(marks: dict) -> dict:
    """`marks` with every bare pin (no note, no kind) removed: rule 4 then
    admits nothing, and each written note counts once."""
    out = copy.deepcopy(marks)
    for item in (out.get("items") or {}).values():
        item["pins"] = [p for p in item.get("pins") or [] if p.get("note") or p.get("what")]
    return out


def verdict(rows_all: dict, rows_noted: dict, radius_mm: float = h.RADIUS_MM) -> dict:
    """The pass line on two `score_rows` results (all pins; rule-4 pins dropped)."""
    a = h.pool(rows_all, radius_mm, NULL)
    b = h.pool(rows_noted, radius_mm, NULL)
    with_pins = [k for k, r in rows_all.items() if r["pins"]]
    loo = {k: h.pool({j: r for j, r in rows_all.items() if j != k}, radius_mm, NULL).get("ci95")
           for k in with_pins}
    out = {"items_with_pins": len(with_pins), "all_pins": a, "rule4_dropped": b, "leave_one_out_ci95": loo}
    if len(with_pins) < MIN_ITEMS:
        out["verdict"] = "no verdict"
    elif a["ci95"][0] > 0 and b.get("ci95") and b["ci95"][0] > 0:
        fragile = any(ci is None or ci[0] <= 0 for ci in loo.values())
        out["verdict"] = "shown, fragile" if fragile else "shown, robust"
    else:
        out["verdict"] = "not shown"
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--marks", type=Path, required=True)
    ap.add_argument("--flags", type=Path, required=True)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    marks = json.loads(a.marks.read_text(encoding="utf-8"))
    rows_all = h.score_rows(marks, a.flags, PREFIX, "letters")
    rows_noted = h.score_rows(drop_inherited(marks), a.flags, PREFIX, "letters")
    res = {"radius_mm": h.RADIUS_MM, "null": NULL, "items": rows_all, **verdict(rows_all, rows_noted),
           "sensitivity": {str(r): h.pool(rows_all, r, NULL) for r in h.SENSITIVITY_MM}}
    if a.json:
        a.json.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    for iid, row in rows_all.items():
        b = row["by_radius"][str(h.RADIUS_MM)]
        print(f"{iid:22s} pins {row['pins']:2d} flags {row['flags']:4d} hit {b['hit']}/{row['pins']}"
              f" chance {b[NULL]}")
    print("2a", res["all_pins"], "\n2b", res["rule4_dropped"], "\nLOO", res["leave_one_out_ci95"])
    print("VERDICT:", res["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
