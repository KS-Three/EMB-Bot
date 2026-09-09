"""Node-to-node edges of the satin skeleton, across the corpus — the
instrument for junction clustering (quality review 2026-09-08, item 5).

A raster medial axis renders one junction as SEVERAL branch pixels a few
pixels apart whenever the stroke width is even in pixels or the arms meet
off-centre: a crossing becomes two 3-way nodes joined by a 2-3 px stub, a
5-way node a chain of them. `_merge_through_junctions` then pairs arms at
each pixel separately and the stub is dropped as junction noise afterwards,
so the crossing decomposes into three strokes instead of two bars
(`tests/test_stroke_classify.py`, the PLUS at 1.25x, 2026-09-09).

This lists every edge whose both ends are branch nodes — pixel length, the
distance transform at each end, the shape's half-width — so the clustering
threshold is read off the corpus rather than guessed: a stub that is a
fraction of the stroke width is one junction split by the raster; an edge
of a stroke width or more is a bar between two junctions.

Usage: python tools/junction_nodes.py [--flag NAME[=VALUE]] [--clustered] [--json PATH] [cases ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
from skimage.morphology import medial_axis

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize          # noqa: E402
from digitizer_core import stage6_satin as s6                # noqa: E402
from digitizer_core import stage7_sequence as s7             # noqa: E402
from curve_tiers import CASES                                 # noqa: E402
from thin_strokes import parse_flag                           # noqa: E402

ROOT = HERE.parent
EXTRA = {"becker100": ("becker_marine_logo.png", dict(target_width_mm=100.0))}
BINS = ((0.25, "<=0.25"), (0.5, "<=0.5"), (1.0, "<=1"), (2.0, "<=2"), (math.inf, ">2"))


def node_edges(poly, clustered: bool = False):
    """-> (rows, n_nodes, n_edges, half_px) for one polygon, the way
    `extract_strokes` builds its skeleton up to the junction merge."""
    mask, scale, ox, oy = s6._rasterize(poly)
    if not mask.any():
        return [], 0, 0, 0.0
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    skel = s6._collapse_pinholes(skel)
    skel_mask = skel.astype(np.uint8)
    half_px = float(dist[skel].mean()) if skel.any() else 0.0
    s6._prune_spurs(skel_mask, max(3.0, half_px * 1.6))
    edges = s6._skeleton_edges(skel_mask)
    if clustered:
        edges = s6._cluster_junctions(
            edges, max(s6._JUNCTION_CLUSTER_MIN_PX, s6._JUNCTION_CLUSTER_HALFWIDTHS * half_px),
            lambda p: float(dist[p[1], p[0]]) / scale)
    nodes = set()
    rows = []
    for e in edges:
        if e["closed"]:
            continue
        if not e["free_start"]:
            nodes.add(e["pts"][0])
        if not e["free_end"]:
            nodes.add(e["pts"][-1])
        if e["free_start"] or e["free_end"]:
            continue
        length = sum(math.dist(a, b) for a, b in zip(e["pts"], e["pts"][1:]))
        da = float(dist[e["pts"][0][1], e["pts"][0][0]])
        db = float(dist[e["pts"][-1][1], e["pts"][-1][0]])
        rows.append({"length_px": round(length, 2), "dt_a": round(da, 2), "dt_b": round(db, 2),
                     "half_px": round(half_px, 2), "scale": scale,
                     "ratio_half": round(length / half_px, 3) if half_px else None,
                     "ratio_node": round(length / max(min(da, db), 1e-6), 3),
                     "at_mm": (round(ox + (e["pts"][0][0] + 0.5) / scale, 1),
                               round(oy + (e["pts"][0][1] + 0.5) / scale, 1))})
    return rows, len(nodes), len(edges), half_px


def scan(case: str, rel: str, kw: dict, flag, clustered: bool = False) -> dict:
    seen: list[tuple[str, object]] = []
    real = s6.satin_shape

    def spy(poly, shape_id, **kwargs):
        seen.append((shape_id, poly))
        return real(poly, shape_id, **kwargs)

    s7.satin_shape = spy
    try:
        cfg = dict(kw)
        if flag is not None:
            cfg[flag[0]] = flag[1]
        result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
    finally:
        s7.satin_shape = real
    out = {"case": case, "shapes": {}, "rows": []}
    for shape_id, poly in seen:
        rows, n_nodes, n_edges, half_px = node_edges(poly, clustered)
        strokes, _h, _f = s6.extract_strokes(poly)
        out["shapes"][shape_id] = {"nodes": n_nodes, "edges": n_edges,
                                   "strokes": len(strokes), "half_px": round(half_px, 2),
                                   "node_edges": len(rows)}
        for r in rows:
            r["shape_id"] = shape_id
        out["rows"].extend(rows)
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--flag", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--clustered", action="store_true",
                    help="count what is left after _cluster_junctions, the way extract_strokes sees it")
    a = ap.parse_args(argv)
    flag = parse_flag(a.flag) if a.flag else None
    cases = {**CASES, **EXTRA}
    names = a.cases or list(cases)
    report = []
    print(f"node-to-node skeleton edges — {'default config' if flag is None else flag}"
          f"{' — after _cluster_junctions' if a.clustered else ''}")
    for name in names:
        rel, kw = cases[name]
        r = scan(name, rel, kw, flag, a.clustered)
        report.append(r)
        rows = r["rows"]
        counts = []
        lo = 0.0
        for hi, label in BINS:
            n = sum(1 for x in rows if x["ratio_half"] is not None and lo < x["ratio_half"] <= hi)
            counts.append(f"{label}:{n}")
            lo = hi
        n_shapes = len(r["shapes"])
        strokes = sum(v["strokes"] for v in r["shapes"].values())
        nodes = sum(v["nodes"] for v in r["shapes"].values())
        print(f"== {name:12} satin shapes {n_shapes:3}  strokes {strokes:4}  nodes {nodes:4}  "
              f"node-node edges {len(rows):3}  by length/half: {' '.join(counts)}")
        for x in sorted(rows, key=lambda x: x["ratio_half"] or 0)[:6]:
            print(f"     {x['shape_id']} len {x['length_px']:5.2f} px  dt {x['dt_a']:5.2f}/{x['dt_b']:5.2f}"
                  f"  half {x['half_px']:5.2f}  ratio {x['ratio_half']}  at {x['at_mm']}")
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
