"""Log every _corner_forks decision the SHIPPED path makes, with its margins.

Optionally disable the drop entirely (FORKS_OFF=1) to isolate its effect on
bare fabric.

Usage: FORKS_OFF=0|1 forkprobe.py <dz> <corpus_out> <slug>
"""
import sys, os, json, math
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str((HERE / sys.argv[1]).resolve()))
import digitizer_core.stage6_satin as S
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from shapely.ops import unary_union

OUT, slug = sys.argv[2], sys.argv[3]
OFF = os.environ.get("FORKS_OFF") == "1"
LOG = []

_orig = S._corner_forks


def traced(edges, dt_mm, half_mm, scale):
    picked = _orig(edges, dt_mm, half_mm, scale)
    for i, e in enumerate(edges):
        if e["closed"] or e["free_start"] == e["free_end"]:
            continue
        pts = list(e["pts"]) if e["free_end"] else list(reversed(e["pts"]))
        if len(pts) < 3:
            continue
        tip = dt_mm(pts[-1]); node = dt_mm(pts[0])
        length = sum(math.dist(a, b) for a, b in zip(pts, pts[1:])) / scale
        ratio = length / node if node > 0 else float("inf")
        if i in picked or (tip <= S._FORK_TIP_FRAC * half_mm and ratio <= 3.0):
            LOG.append({"dropped": i in picked, "half_mm": round(half_mm, 2),
                        "tip_frac": round(tip / half_mm, 3) if half_mm else None,
                        "node_mm": round(node, 2), "len_mm": round(length, 2),
                        "ratio": round(ratio, 2),
                        "tip_xy": [round(pts[-1][0] / scale, 2), round(pts[-1][1] / scale, 2)]})
    return set() if OFF else picked


S._corner_forks = traced

man = json.load(open(Path(OUT) / "manifest.json"))
e = [x for x in man if x["slug"] == slug][0]
cfg = PipelineConfig(); cfg.fill_density_boost = True
cfg.target_width_mm = round(e["pro"]["width_mm"], 1)
res = run_stages(str(Path(OUT) / slug / "art.png"), cfg)
plan = plan_stitches(res, cfg)

# bare fabric, same instrument as bare.py
RES = 10.0
runs = [list(r.points) for b in plan.blocks for r in b.runs if len(r.points) > 1]
shapes = unary_union([r.polygon for r in res.regions])
x0, y0, x1, y1 = shapes.bounds
W = int((x1 - x0) * RES) + 8; H = int((y1 - y0) * RES) + 8
def px(p): return (int((p[0] - x0) * RES) + 4, int((p[1] - y0) * RES) + 4)
sh = np.zeros((H, W), np.uint8)
polys = list(shapes.geoms) if shapes.geom_type == "MultiPolygon" else [shapes]
for g in polys:
    cv2.fillPoly(sh, [np.array([px(c) for c in g.exterior.coords], np.int32)], 1)
    for r in g.interiors:
        cv2.fillPoly(sh, [np.array([px(c) for c in r.coords], np.int32)], 0)
th = np.zeros((H, W), np.uint8)
for r in runs:
    pts = [px(p) for p in r]
    for k in range(len(pts) - 1):
        cv2.line(th, pts[k], pts[k + 1], 1, max(1, int(0.40 * RES)))
bare = (sh > 0) & (th == 0)
n, lab, st, _ = cv2.connectedComponentsWithStats(bare.astype(np.uint8), 8)
top = sorted(st[1:, 4], reverse=True)[:5]
print(f"FORKS_OFF={OFF} {slug}: bare={bare.sum()/RES**2:.1f}mm2 "
      f"top5={[round(a/RES**2,2) for a in top]}")
dropped = [d for d in LOG if d["dropped"]]
print(f"  fork candidates logged={len(LOG)} dropped={len(dropped)}")
for d in sorted(dropped, key=lambda d: -d["len_mm"])[:12]:
    print(f"   DROP len={d['len_mm']:5.2f} node={d['node_mm']:4.2f} ratio={d['ratio']:4.2f} "
          f"half={d['half_mm']:4.2f} tipfrac={d['tip_frac']} at {d['tip_xy']}")
