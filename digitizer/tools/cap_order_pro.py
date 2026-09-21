#!/usr/bin/env python
"""Does the professional actually sew a CAP centre-out and bottom-up?

`cfg.cap_center_out` is built and parked OFF. The craft rule behind it comes
from the machine-physics playbook's Law 34 — [P] Melco (two docs), [T] ASI —
and from the browser lane, which has ordered caps this way for months. Neither
source owns the files this project is benchmarked against. This tool asks the
one professional whose work we DO have.

**Why this corpus can answer it at all.** Kent's pro digitized the SAME
artwork twice for several clients — once for a structured cap front and once
for a left chest — and `tools/pro_parity/prep_both.py` already records which
file is which, from the pro's own filename convention. So the artwork is held
constant and the garment is the only thing that moves. Any ordering bias that
comes from the design itself (lettering runs left to right, a border chases
its fill) appears in BOTH files of a pair and cancels in the difference. What
survives the difference is the garment.

**What is measured.** Each file is decoded to needle-down runs in sew order
(`study_pro.load_runs`, the same loader the corpus study uses). Per colour
block, two Spearman rank correlations against sew position:

  `centre_out`  rho(order, |x - cx|)   positive => sews outward from the seam
  `bottom_up`   rho(order, y)          NEGATIVE => sews toward the crown

`cx` is the design's own bbox centre and y runs DOWN, the same frame stage 4
and the DST writer use, so "bottom of the garment" is the LARGER y. Blocks
with fewer than `--min-runs` runs are skipped: a three-run block has no
ordering to speak of and its rho is noise at full weight. A file's figure is
the run-count-weighted mean over its surviving blocks.

**The honest limit, stated before the numbers.** A pro's RUN is not our
SHAPE. His files interleave underlay, travel and border passes that our
sequencer treats as companions to a shape rather than as orderable units, and
a stitch file carries no shape ids to group them back. So this measures the
ORDER THREAD GOES DOWN, which is the thing the craft rule is actually about,
but it is not a like-for-like test of our pick loop. Read it as evidence about
the RULE, not as a parity score.

**AND ON THIS CORPUS THAT LIMIT MOSTLY BITES — measured 2026-09-19, first
run.** A run ends at a lift, and this pro barely lifts: that is the same
behaviour MASTER_SCOPE defect 4 records from the other side (we trim 3.1x
what he does). Seven of the eight files decode to **9 to 13 runs across 4-5
colour blocks** — one to six runs per block — so there is no ordering in them
to correlate, and the honest output is a skip, not a number. The exception is
`gaulke`, whose cap and left-chest files are **42 runs in a single block
each**, and which is therefore the only pair in the corpus this instrument
can actually read.

**What that one pair says, and it is a split verdict:**

  `bottom_up`   cap -0.856  vs  flat +0.827   (d = -1.683)  rule CONFIRMED
  `centre_out`  cap -0.314  vs  flat +0.475   (d = -0.789)  rule CONTRADICTED

i.e. on the one design that can be read, the pro's cap file does work from
the bill toward the crown — strongly, and in the opposite direction from his
own left-chest file of the same artwork — while sewing INWARD toward the
seam rather than outward from it. **n = 1 pair. That is an observation, not a
finding, and nothing should be flipped on it.**

Getting a real answer needs runs assigned to REGIONS before they are ordered,
which is what `tools/pro_parity/diff` on the `claude/pro-overlay-diff` lane
already does (pushed 2026-09-18, no PR yet). Use that rather than rebuilding
region assignment here.

Usage (needs the Drive corpus; `PRO_PARITY_ROOT` overrides the default path):

    .venv/Scripts/python tools/cap_order_pro.py
    .venv/Scripts/python tools/cap_order_pro.py --min-runs 8 --json out.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from study_pro import load_runs  # noqa: E402

ROOT = Path(os.environ.get("PRO_PARITY_ROOT",
                           r"G:/My Drive/EMB-Bot/Embroidery Files"))

# (pair label, garment, pro stitch file) — the garment column is the pro's own
# filename convention as Kent read it (prep_both.py's header): `hat` is a
# Richardson 112 structured cap front, `beanie` a knit winter hat, `LC` a left
# chest. Only artwork that exists in BOTH a cap and a flat garment is listed:
# an unpaired file cannot separate the garment from the design.
PAIRS = [
    ("becker_large",  "cap",  "Becker Marine/Becker Hat & Polo Large/beckers logo hat.PES"),
    ("becker_large",  "flat", "Becker Marine/Becker Hat & Polo Large/beckers logolc.PES"),
    ("becker_small",  "cap",  "Becker Marine/Becker Hat & Polo Small/Becker Hat Small/beckers logo hat 2 A.PES"),
    ("becker_small",  "flat", "Becker Marine/Becker Hat & Polo Small/Becker Chest Small/beckers logo LC 2 A.PES"),
    ("gaulke",        "cap",  "Gaulke Roofing/c golke logo hat.DST"),
    ("gaulke",        "flat", "Gaulke Roofing/c golke logo LC.DST"),
    ("mfab",          "cap",  "MFAB/Mfab Hat & Polo/mf4b logo hat.PES"),
    ("mfab",          "flat", "MFAB/Mfab Hat & Polo/mf4b logo lc.PES"),
]


def spearman(a: np.ndarray, b: np.ndarray) -> float:
    """Rank correlation, ties averaged. numpy only — no scipy dependency."""
    if len(a) < 3:
        return float("nan")
    ra, rb = _rank(a), _rank(b)
    sa, sb = ra.std(), rb.std()
    if sa == 0 or sb == 0:
        return float("nan")
    return float(((ra - ra.mean()) * (rb - rb.mean())).mean() / (sa * sb))


def _rank(v: np.ndarray) -> np.ndarray:
    order = v.argsort(kind="stable")
    out = np.empty(len(v), float)
    out[order] = np.arange(len(v), dtype=float)
    # average tied ranks, so a column of identical values cannot fake a trend
    _, start, count = np.unique(v[order], return_index=True, return_counts=True)
    for s, c in zip(start, count):
        if c > 1:
            out[order[s:s + c]] = out[order[s:s + c]].mean()
    return out


def read_file(path: Path, min_runs: int) -> dict:
    runs, _n_trim, _n_jump = load_runs(path)
    if not runs:
        raise SystemExit(f"no runs decoded: {path}")
    pts = np.array([p for r in runs for p in r["pts"]], float)
    cx = (pts[:, 0].min() + pts[:, 0].max()) / 2.0

    cent = np.array([np.mean(r["pts"], axis=0) for r in runs], float)
    blocks = np.array([r["block"] for r in runs], int)

    rows, weights, co, bu = [], [], [], []
    for b in sorted(set(blocks.tolist())):
        sel = blocks == b
        n = int(sel.sum())
        if n < min_runs:
            continue
        order = np.arange(n, dtype=float)
        r_co = spearman(order, np.abs(cent[sel, 0] - cx))
        r_bu = spearman(order, cent[sel, 1])
        if np.isnan(r_co) or np.isnan(r_bu):
            continue
        rows.append({"block": b, "runs": n, "centre_out": r_co, "bottom_up": r_bu})
        weights.append(n)
        co.append(r_co)
        bu.append(r_bu)

    w = np.array(weights, float)
    return {
        "path": str(path),
        "runs": len(runs),
        "blocks_total": len(set(blocks.tolist())),
        "blocks_scored": len(rows),
        "runs_scored": int(w.sum()) if len(w) else 0,
        "centre_out": float(np.average(co, weights=w)) if len(w) else float("nan"),
        "bottom_up": float(np.average(bu, weights=w)) if len(w) else float("nan"),
        "per_block": rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-runs", type=int, default=6,
                    help="skip a colour block with fewer runs than this (default 6)")
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args()

    if not ROOT.exists():
        print(f"corpus not found at {ROOT} — set PRO_PARITY_ROOT", file=sys.stderr)
        return 2

    out = {}
    for label, garment, rel in PAIRS:
        path = ROOT / rel
        if not path.exists():
            print(f"  MISSING {label}/{garment}: {rel}", file=sys.stderr)
            continue
        out.setdefault(label, {})[garment] = read_file(path, args.min_runs)

    # `runs` and `blocks` are the file's TOTALS; `scored` is what survived
    # --min-runs. A file whose scored count is 0 is not a missing file and not
    # a null result — this pro barely lifts the needle, so there are too few
    # runs in a block to hold an order at all. Printing both columns is what
    # keeps that visible instead of reading as `nan`.
    print(f"{'pair':<14} {'garment':<6} {'runs':>5} {'blk':>4} "
          f"{'scored':>7} {'centre_out':>11} {'bottom_up':>10}")
    print("-" * 62)
    for label in out:
        for garment in ("cap", "flat"):
            r = out[label].get(garment)
            if r is None:
                continue
            scored = f"{r['blocks_scored']}/{r['blocks_total']}"
            if r["blocks_scored"] == 0:
                print(f"{label:<14} {garment:<6} {r['runs']:>5} "
                      f"{r['blocks_total']:>4} {scored:>7} "
                      f"{'too few runs per block':>22}")
                continue
            print(f"{label:<14} {garment:<6} {r['runs']:>5} "
                  f"{r['blocks_total']:>4} {scored:>7} "
                  f"{r['centre_out']:>11.3f} {r['bottom_up']:>10.3f}")

    print()
    print("PAIRED DIFFERENCE (cap - flat) — the artwork cancels, the garment does not")
    print(f"{'pair':<14} {'d centre_out':>13} {'d bottom_up':>12}")
    print("-" * 42)
    d_co, d_bu = [], []
    for label, arms in out.items():
        if "cap" not in arms or "flat" not in arms:
            continue
        a, b = arms["cap"], arms["flat"]
        dc = a["centre_out"] - b["centre_out"]
        db = a["bottom_up"] - b["bottom_up"]
        d_co.append(dc)
        d_bu.append(db)
        print(f"{label:<14} {dc:>13.3f} {db:>12.3f}")
    if d_co:
        print("-" * 42)
        print(f"{'mean':<14} {np.mean(d_co):>13.3f} {np.mean(d_bu):>12.3f}")
        print()
        print("Reading it: the rule predicts POSITIVE d centre_out (the cap file")
        print("sews outward from the seam more than the flat one does) and")
        print("NEGATIVE d bottom_up (the cap file works toward the crown).")
        print(f"n = {len(d_co)} pairs — too few for a p-value, and it is not offered.")

    if args.json:
        args.json.write_text(json.dumps(out, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
