"""A calibrated vision judge, phase A: the split, the calibration kit, the page.

Kent, 2026-11-07: "why don't we develop a new yard stick that develops you
into reviewing these like a human? Maybe a side by side camparison of
ambiguous photos that can point you in the right direction."

The protocol is `docs/eye-pairs-2026-11-04/calibrated-judge/PRE-REGISTRATION.md`
(committed before any picture was opened). This module does three things and
judges nothing:

    python -m tools.eye_pairs.judge_calibration split   [--check]
    python -m tools.eye_pairs.judge_calibration kit     --out DIR [--runs DIR] [--trees DIR]
    python -m tools.eye_pairs.judge_calibration serve   --kit DIR [--port 8733]

* `split` pools every Kent-labelled pair the two session judges read (54 on
  11-04, 99 on 11-06), de-duplicated by (sitting, fixture, arm), and splits it
  ONCE under `SEED` into CALIBRATION (~40%) and HELD-OUT (~60%), stratified by
  design and by Kent's pick class. The manifest is two files of pair ids and
  nothing else (no label, no arm, no side): `split-calibration.json` and
  `split-held-out.json`. `--check` recomputes and compares.
* `kit` reads `split-calibration.json` ONLY (`_kit_read` refuses any other
  manifest file), picks up to `KIT_MAX` pairs where the old judge and Kent
  disagreed, from the verdict files already committed, and writes a review
  kit: both renders at one scale, a 3x crop of the region that differs most,
  Kent's original pick, the old judge's verdict and reason, and a box for
  Kent's one-line reason. 11-04 pictures are copied from the surviving
  `eye_pairs_out/pro-lettering-1102/img/`; the 11-06 kit's pictures are gone,
  so its calibration pairs' designs (and no others) are re-drawn on their
  sittings' trees exactly as `pro_pooled_build render --sitting-size` drew them.
* `serve` serves that page on localhost and saves every reason to
  `<kit>/reasons.json`, which phase B reads. Opened from disk instead, the page
  keeps reasons in the browser and offers the same JSON as a download.

The held-out list is read by `split --check`, by tests, and by phase B's
scoring, never by anything that builds or shows a picture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
DIGITIZER = HERE.parents[2]
REPO = DIGITIZER.parent
if str(DIGITIZER) not in sys.path:
    sys.path.insert(0, str(DIGITIZER))

from tools.eye_pairs import vlm_judge as vj  # noqa: E402

OUT = REPO / "docs" / "eye-pairs-2026-11-04" / "calibrated-judge"
CALIBRATION_FILE = "split-calibration.json"
HELD_OUT_FILE = "split-held-out.json"
SEED = 20261107
CAL_FRACTION = 0.40
KIT_MAX = 25

#: The two judged sets, by the directory their verdicts live in. A pool id is
#: `<set>:<kit pair id>`: the id the judge saw, so the manifest unseals nothing.
SET_1104 = "vlm-judge"
SET_1106 = "vlm-judge-100"
VERDICTS = {SET_1104: vj.OUT / f"verdicts-{vj.SESSION_MODEL}.jsonl",
            SET_1106: vj.PRO100_OUT / "verdicts-claude-opus-5-5-session.jsonl"}
#: 11-04: the pairs whose pick was seen while that kit was built (Amendment 1).
EXCLUDED_1104 = frozenset({"P001", "P002", "P003"})
SITTING_1102 = "pro-size-lettering-1102"

#: Disagreement classes (old judge vs Kent, ties in).
CLASS_JUDGE_TIE = "judge_tie_kent_side"
CLASS_KENT_TIE = "judge_side_kent_tie"
CLASS_OPPOSITE = "opposite_sides"
CLASSES = (CLASS_JUDGE_TIE, CLASS_KENT_TIE, CLASS_OPPOSITE)

#: The pass bar (PRE-REGISTRATION.md): both must hold, on HELD-OUT only.
PASS_KAPPA = 0.55
PASS_CI_LOWER = 0.34


# ------------------------------------------------------------------ the pool ----

def _arm_of(s: dict) -> str:
    return s["left_arm"] if s["left_arm"] != "base" else s["right_arm"]


def sealed_1104() -> dict:
    """11-04's sitting: sealed key per kit pair, with Kent's label, design and
    dedup key. Live pairs only, Amendment 1's exclusions out."""
    st = vj.load_sitting()
    out = {}
    for pid, s in sorted(st["sealed"].items()):
        if s["kind"] != "live" or pid in EXCLUDED_1104 or pid not in st["picks"]:
            continue
        out[pid] = {**s, "kent": vj.to_label(st["picks"][pid], s),
                    "design": st["design_of"][s["fixture"]],
                    "key": (SITTING_1102, s["fixture"], _arm_of(s))}
    return out


def sealed_1106() -> dict:
    """11-06's kit rebuilt (`vlm_judge.pro100_sealed`): live pairs only."""
    out = {}
    for pid, s in vj.pro100_sealed().items():
        if s["kind"] != "live":
            continue
        out[pid] = {**s, "design": s["fixture"], "key": (s["sitting"], s["fixture"], s["arm"])}
    return out


def pool(sets: dict[str, dict] | None = None) -> list[dict]:
    """Every Kent-labelled pair, de-duplicated by (sitting, fixture, arm): the
    first set listed keeps a pair both hold. -> rows {id, set, pair, design, kent}."""
    sets = sets if sets is not None else {SET_1104: sealed_1104(), SET_1106: sealed_1106()}
    seen, rows = set(), []
    for name, sealed in sets.items():
        for pid, s in sorted(sealed.items()):
            key = tuple(s["key"])
            if key in seen:
                continue
            seen.add(key)
            rows.append({"id": f"{name}:{pid}", "set": name, "pair": pid,
                         "design": s["design"], "kent": s["kent"]})
    return rows


def stratum(row: dict) -> tuple[str, str]:
    return (row["design"], row["kent"])


def split(rows: list[dict], *, seed: int = SEED, fraction: float = CAL_FRACTION) -> dict:
    """Seeded, stratified, systematic: strata (design, Kent's class) in sorted
    order, each one's ids shuffled, then every position i of the concatenation
    goes to CALIBRATION when floor(f*(i+1)+u) > floor(f*i+u), u drawn once from
    the seed. Each stratum gets its share to within one pair; the whole gets
    round(f*n) to within one."""
    rng = random.Random(seed)
    by: dict[tuple, list[str]] = {}
    for r in rows:
        by.setdefault(stratum(r), []).append(r["id"])
    order: list[str] = []
    for key in sorted(by):
        ids = sorted(by[key])
        rng.shuffle(ids)
        order += ids
    u = rng.random()
    cal, held = [], []
    for i, pid in enumerate(order):
        (cal if math.floor(fraction * (i + 1) + u) > math.floor(fraction * i + u) else held).append(pid)
    return {"calibration": sorted(cal), "held_out": sorted(held)}


def pool_sha(rows: list[dict]) -> str:
    """Hash of the pool's ids and strata: a changed input moves it, so a stale
    manifest is caught by `--check` and by the test."""
    blob = json.dumps(sorted([r["id"], *stratum(r)] for r in rows), separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def manifest_payloads(rows: list[dict]) -> dict[str, dict]:
    sp = split(rows)
    common = {"seed": SEED, "fraction": CAL_FRACTION, "n_pool": len(rows), "pool_sha256": pool_sha(rows),
              "rule": "PRE-REGISTRATION.md, 'The split'"}
    return {CALIBRATION_FILE: {**common, "part": "calibration", "ids": sp["calibration"]},
            HELD_OUT_FILE: {**common, "part": "held_out", "ids": sp["held_out"]}}


def do_split(a) -> int:
    rows = pool()
    payloads = manifest_payloads(rows)
    out = Path(a.out)
    if a.check:
        bad = [n for n, p in payloads.items()
               if json.loads((out / n).read_text(encoding="utf-8")) != p]
        print(json.dumps({"n_pool": len(rows), "stale": bad}))
        return 1 if bad else 0
    out.mkdir(parents=True, exist_ok=True)
    for name, payload in payloads.items():
        path = out / name
        text = json.dumps(payload, indent=1) + "\n"
        if path.exists() and path.read_text(encoding="utf-8") != text:
            raise SystemExit(f"REFUSED: {path} exists and differs; the split is made once.")
        path.write_text(text, encoding="utf-8")
    cal = payloads[CALIBRATION_FILE]["ids"]
    print(json.dumps({"n_pool": len(rows), "calibration": len(cal),
                      "held_out": len(payloads[HELD_OUT_FILE]["ids"])}))
    return 0


# ------------------------------------------------------------- phase B's read ----

def primary(rows: list[tuple[str, str, str]]) -> dict:
    """The pre-registered primary on HELD-OUT: `rows` = (kent, judge, design)
    labels in before / tie / after. The repo's own `vlm_judge._kappas` (3-way
    linear-weighted kappa, ties in; percentile bootstrap over pairs and over
    designs; `pooled.reading`), plus the pass bar."""
    res = vj._kappas(rows)
    k, ci = res.get("kappa_3way"), res.get("ci3_pairs")
    res["passes"] = bool(k is not None and ci and ci[0] is not None
                         and k >= PASS_KAPPA and ci[0] > PASS_CI_LOWER)
    res["bar"] = {"kappa_at_least": PASS_KAPPA, "ci_pairs_lower_above": PASS_CI_LOWER}
    return res


# ------------------------------------------------------------------- main ----

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sp = sub.add_parser("split", help="write (or --check) the calibration / held-out manifest")
    sp.add_argument("--out", default=str(OUT))
    sp.add_argument("--check", action="store_true")
    sp.set_defaults(fn=do_split)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
