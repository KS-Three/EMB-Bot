#!/usr/bin/env python
"""Per-transition dump: every needle-up move and why it is or is not linkable."""
from __future__ import annotations

import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import fabric_for, run_stages  # noqa: E402
from digitizer_core.stage5_overlap import resolve_overlaps  # noqa: E402
from digitizer_core.stage7_sequence import sequence  # noqa: E402

TOL = 0.2


def dump(name, path, garment, width):
    cfg = PipelineConfig(target_width_mm=width, garment_id=garment)
    result = run_stages(path, cfg)
    fabric = fabric_for(cfg)
    planned, _ = resolve_overlaps(result.regions, fabric, cfg)
    blocks, _ = sequence(planned, fabric, cfg)
    by_id = {p.shape_id: p for p in planned}
    layers = sorted({p.layer for p in planned})
    geom = {L: unary_union([p.region.polygon for p in planned if p.layer == L])
            for L in layers}
    later = {}
    running = None
    for L in reversed(layers):
        later[L] = running
        running = geom[L] if running is None else running.union(geom[L])

    print(f"=== {name} trim_at={fabric.trim_at_mm} pull={fabric.pull_comp_mm} "
          f"layers={layers}")
    for p in sorted(planned, key=lambda p: (p.sew_index, p.shape_id)):
        print(f"    shape {p.shape_id:<10} sew={p.sew_index} layer={p.layer} "
              f"area={p.polygon.area:7.2f} laterNone={later[p.layer] is None}")
    covers = {}
    for si in sorted({p.sew_index for p in planned}):
        group = [p for p in planned if p.sew_index == si]
        parts = [p.polygon for p in group]
        L = group[0].layer
        if later[L] is not None:
            parts.append(later[L])
        covers[si] = unary_union(parts).buffer(TOL)

    for bi, b in enumerate(blocks):
        si = None
        for p in planned:
            if b.runs and p.shape_id == b.runs[0].shape_id:
                si = p.sew_index
        cover = covers.get(si)
        comps = ([cover] if cover.geom_type == "Polygon" else list(cover.geoms))
        print(f"  -- block {bi} sew_index={si} rgb={b.rgb} "
              f"cover_components={len(comps)}")
        prev = None
        prev_shape = None
        for run in b.runs:
            if run.jump and prev is not None:
                d = math.dist(prev, run.points[0])
                seg = LineString([prev, run.points[0]])
                straight = cover.covers(seg)
                a, bp = Point(prev), Point(run.points[0])
                conn = any(c.covers(a) and c.covers(bp) for c in comps)
                tag = "TRIM" if run.trim else "jump"
                scope = "in " if run.shape_id == prev_shape else "X  "
                print(f"     {tag} {scope} {prev_shape:>9}->{run.shape_id:<9} "
                      f"{run.kind:<9} d={d:6.2f} straight={int(straight)} "
                      f"connected={int(conn)}")
            prev = run.points[-1]
            prev_shape = run.shape_id


if __name__ == "__main__":
    dump("benchmark",
         Path(r"C:\Users\EE-LT-11030\Downloads\enthusiast enterprises logo.png"),
         "left_chest", 90.0)
