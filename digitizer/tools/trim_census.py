#!/usr/bin/env python
"""Every trim in a design, sorted into what could have avoided it.

    .venv/bin/python -m tools.trim_census [case ...] [--set KEY=VALUE ...]

Cases are `thin_strokes.REAL_ART` (deduplicated), at each case's width and
garment, `max_colors` left at the default. Each trim (the design's first
thread-in excluded) lands in exactly one bucket:

  colour     the first run of a block: a thread change, which cuts anyway.
  same_cone  the first run of a block whose cone equals the previous block's
             (a colour stop that changes nothing).
  in_shape   the previous sewn run is the same shape.
  entry      between shapes, and the next shape has a sewn point within
             `trim_at` of where the needle stopped — the cut is the chosen
             ENTRY point's, not the gap's.
  order      between shapes, entry cannot help, but a shape sewn LATER in the
             same block had a point within `trim_at` — the cut is the pick
             order's.
  gap        between shapes and nothing in the block was in reach.

`entry` and `order` read the SEWN points, so they bound what a different
start point or pick could save; they do not claim the alternative sews.
"""
from __future__ import annotations

import math
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import digitize, fabric_for  # noqa: E402


def _min_dist(p, pts) -> float:
    return min((math.dist(p, q) for q in pts), default=math.inf)


def census(plan, trim_at: float) -> Counter:
    c: Counter = Counter()
    first = True
    prev_thread = None
    for bi, b in enumerate(plan.blocks):
        runs = [r for r in b.runs if r.points]
        if not runs:
            continue
        # shape -> all of its sewn points in this block, and its first index
        pts: dict[str, list] = {}
        first_at: dict[str, int] = {}
        for i, r in enumerate(runs):
            pts.setdefault(r.shape_id, []).extend(r.points)
            first_at.setdefault(r.shape_id, i)
        cursor = None
        prev_sid = None
        for i, r in enumerate(runs):
            if r.trim:
                if first:
                    pass
                elif i == 0:
                    c["same_cone" if b.thread_index == prev_thread else "colour"] += 1
                elif r.shape_id and r.shape_id == prev_sid:
                    c["in_shape"] += 1
                elif _min_dist(cursor, pts.get(r.shape_id, [])) <= trim_at:
                    c["entry"] += 1
                elif any(first_at[s] > i and _min_dist(cursor, p) <= trim_at
                         for s, p in pts.items() if s != r.shape_id):
                    c["order"] += 1
                else:
                    c["gap"] += 1
            first = False
            cursor = r.points[-1]
            prev_sid = r.shape_id
        prev_thread = b.thread_index
    return c


BUCKETS = ("colour", "same_cone", "in_shape", "entry", "order", "gap")


def main(argv: list[str]) -> int:
    from thin_strokes import corpus_cases
    sets = {}
    names = []
    it = iter(argv)
    for a in it:
        if a == "--set":
            k, v = next(it).split("=", 1)
            sets[k] = {"true": True, "false": False}.get(v.lower(), v)
        else:
            names.append(a)
    print(f"{'case':12} {'stitches':>8} {'trims':>6} " + " ".join(f"{b:>9}" for b in BUCKETS))
    tot: Counter = Counter()
    for name, path, w, g in corpus_cases():
        if names and name not in names:
            continue
        cfg = PipelineConfig(target_width_mm=w, garment_id=g)
        for k, v in sets.items():
            cur = getattr(cfg, k)
            setattr(cfg, k, type(cur)(v) if cur is not None and not isinstance(v, bool) else v)
        _res, plan = digitize(path, cfg)
        trim_at = fabric_for(cfg).trim_at_mm
        c = census(plan, trim_at)
        st = plan.stats
        tot["stitches"] += st.stitch_count
        tot["trims"] += st.trims
        tot.update(c)
        print(f"{name:12} {st.stitch_count:8} {st.trims:6} " + " ".join(f"{c[b]:9}" for b in BUCKETS))
        sys.stdout.flush()
    print(f"{'TOTAL':12} {tot['stitches']:8} {tot['trims']:6} " + " ".join(f"{tot[b]:9}" for b in BUCKETS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
