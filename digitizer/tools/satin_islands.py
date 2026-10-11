#!/usr/bin/env python
"""How many islands does each satin shape sew as — MASTER_SCOPE defect 6.

An ISLAND is a maximal needle-down chain of one satin shape's runs: the
shape's first run starts one, and every trimmed run inside the shape starts
another. A shape that sews in one pass is one island; the defect is a shape
that sews as many, each a separate tie-in, tie-off and cut.

Per design (`thin_strokes.corpus_cases`, each at its own width/garment):

  shapes    satin shapes (any run of kind SATIN)
  islands   their islands, summed
  small     islands sewing under `SMALL_MM` of thread
  in_trims  trims INSIDE a satin shape (islands - shapes, when every shape
            starts on a cut)
  trims     the design's trims, all causes

    .venv/bin/python -m tools.satin_islands [case ...] [--set KEY=VALUE ...]

Measurement only: it changes nothing in the pipeline.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, stitches  # noqa: E402
from digitizer_core.pipeline import digitize  # noqa: E402

SMALL_MM = 5.0


def islands(plan) -> dict:
    """-> {shapes, islands, small, in_trims} over the plan's satin shapes."""
    satin_ids = {r.shape_id for _b, r in plan.iter_runs()
                 if r.kind == stitches.SATIN and r.points}
    per: dict[str, list[float]] = {}
    prev_sid = None
    for _b, r in plan.iter_runs():
        if not r.points:
            continue
        sid = r.shape_id
        if sid in satin_ids:
            chain = per.setdefault(sid, [])
            if not chain or r.trim or sid != prev_sid:
                chain.append(0.0)
            chain[-1] += r.length_mm
        prev_sid = sid
    n_isl = sum(len(v) for v in per.values())
    return {
        "shapes": len(per),
        "islands": n_isl,
        "small": sum(1 for v in per.values() for x in v if x < SMALL_MM),
        "in_trims": n_isl - len(per),
    }


def main(argv: list[str]) -> int:
    from thin_strokes import corpus_cases
    sets: dict = {}
    names: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--set":
            k, v = next(it).split("=", 1)
            sets[k] = {"true": True, "false": False}.get(v.lower(), v)
        else:
            names.append(a)
    cols = ("shapes", "islands", "small", "in_trims", "trims", "stitches")
    print(f"{'case':12} " + " ".join(f"{c:>8}" for c in cols))
    tot: Counter = Counter()
    for name, path, w, g in corpus_cases():
        if names and name not in names:
            continue
        cfg = PipelineConfig(target_width_mm=w, garment_id=g)
        for k, v in sets.items():
            cur = getattr(cfg, k)
            setattr(cfg, k, v if isinstance(v, bool) else type(cur)(v))
        _res, plan = digitize(path, cfg)
        row = islands(plan)
        row["trims"] = plan.stats.trims
        row["stitches"] = plan.stats.stitch_count
        tot.update(row)
        print(f"{name:12} " + " ".join(f"{row[c]:8}" for c in cols))
        sys.stdout.flush()
    print(f"{'TOTAL':12} " + " ".join(f"{tot[c]:8}" for c in cols))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
