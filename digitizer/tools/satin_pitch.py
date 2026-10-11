#!/usr/bin/env python
"""Satin pitch as SEWN, per rail, on the text-tagged letters of the corpus.

Built 2026-10-07 after Kent's Columns sitting came back "needs work": *"the
comparison could be skewed because of the varying stitch density."* The
sitting's `lettering_columns` side had been drawn on a tree that put ONE end
of each station down (rails alternating), so every rail took a needle each
0.80 mm where the satin tier lays one each 0.40. A pair whose two sides sew at
different pitch cannot be judged on construction; this is the number a
sitting's caption quotes to say they match.

A satin run after `strip_ties` / `strip_splits` is rail penetrations in the
flat zigzag A1, B1, A2, B2, ...: even points one rail, odd points the other.
Per station the two rails each step some distance to the next station; the
**outer step** is the larger of the two (round a bend the outside rail, which
is the one the pitch is held on; the inside is short-stitched and pulled
back). Reported per logo and arm over every satin run of every text-tagged
shape: stations, the outer step's p10 / median / p90, the share of outer
steps over 1.5x the spacing asked for, and penetrations per millimetre of
rail (2 / median at a flat zigzag).

    .venv/Scripts/python tools/satin_pitch.py [case ...] [--arms shipped,columns] [--json PATH]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, machine              # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages   # noqa: E402
from digitizer_core.stage6_satin import strip_splits            # noqa: E402
from digitizer_core.stitches import strip_ties                  # noqa: E402

ARMS: dict[str, dict] = {"shipped": {}, "columns": {"lettering_columns": True}}
ORDER = ["becker", "bridge", "gaulke", "drone", "enthusiast", "fremont", "golden_tee"]
WIDE = 1.5


def rail_steps(points) -> tuple[list[float], list[float]]:
    """One satin run's points -> (outer step, inner step) per station pair."""
    pts = strip_splits(strip_ties(list(points)))
    a, b = pts[0::2], pts[1::2]
    outer, inner = [], []
    for k in range(min(len(a), len(b)) - 1):
        sa, sb = math.dist(a[k], a[k + 1]), math.dist(b[k], b[k + 1])
        outer.append(max(sa, sb))
        inner.append(min(sa, sb))
    return outer, inner


def pitch_of(plan, shape_ids, spacing_mm: float = machine.SATIN_SPACING_MM) -> dict:
    """Per-rail pitch over the satin runs of `shape_ids` in `plan`."""
    outer: list[float] = []
    inner: list[float] = []
    runs = 0
    for _b, run in plan.iter_runs():
        if run.kind != "satin" or run.shape_id not in shape_ids or len(run.points) < 6:
            continue
        o, i = rail_steps(run.points)
        if o:
            runs += 1
            outer += o
            inner += i
    if not outer:
        return {"runs": 0, "stations": 0}
    q = np.percentile(outer, [10, 50, 90])
    return {"runs": runs, "stations": len(outer),
            "outer_p10": round(float(q[0]), 3), "outer_p50": round(float(q[1]), 3),
            "outer_p90": round(float(q[2]), 3),
            "inner_p50": round(float(np.median(inner)), 3),
            "wide_share": round(float(np.mean(np.asarray(outer) > WIDE * spacing_mm)), 4)}


def measure(name: str, path, width: float, garment: str, arm: dict) -> dict:
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6, **arm)
    res = run_stages(path, cfg)
    plan = plan_stitches(res, cfg)
    from tools.fan_census import crosses_of, fan_stats
    polys = {r.shape_id: r.polygon for r in res.regions if r.meta.get("text_candidate")}
    text = set(polys)
    row = pitch_of(plan, text)
    letter_runs = [run for _b, run in plan.iter_runs() if run.shape_id in text]
    over_long = 0
    for sid, poly in polys.items():
        width = 2 * poly.area / max(poly.length, 1e-9)
        over_long += fan_stats(crosses_of(plan, sid)[0], width)["long_crosses"]
    row.update(text_shapes=len(text), stitches=plan.stats.stitch_count, trims=plan.stats.trims,
               letter_stitches=sum(len(r.points) for r in letter_runs),
               letter_trims=sum(int(bool(r.trim)) for r in letter_runs), over_long=over_long)
    return row


def main(argv=None) -> int:
    from tools.thin_strokes import corpus_cases
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--arms", default="shipped,columns")
    ap.add_argument("--json", type=Path)
    args = ap.parse_args(argv)
    cases = {c[0]: c for c in corpus_cases()}
    names = args.cases or [n for n in ORDER if n in cases]
    out: dict = {}
    for name in names:
        _n, path, width, garment = cases[name]
        for arm in args.arms.split(","):
            row = measure(name, path, width, garment, ARMS[arm])
            out.setdefault(name, {})[arm] = row
            print(f"{name:11s} {arm:8s} {row}", flush=True)
            if args.json:
                args.json.write_text(json.dumps(out, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
