"""Render a BEFORE/AFTER crop around a bare-fabric blob, at thread width.

Usage: holecrop.py <dz_before> <dz_after> <corpus_out> <slug> <px_x> <px_y> <tag>
Emits hole_<tag>.png — shape fill in grey, stitches in white, the blob in red.
"""
import sys, json, subprocess
from pathlib import Path
import numpy as np, cv2

RES = 10.0
PAD = 90          # px of context around the blob
ZOOM = 6

dz_b, dz_a, OUT, slug, cx, cy, tag = sys.argv[1:8]
cx, cy = int(cx), int(cy)

HERE = Path(__file__).resolve().parent

RUNNER = r'''
import sys, json
from pathlib import Path
import numpy as np, cv2
sys.path.insert(0, sys.argv[1])
from digitizer_core.pipeline import run_stages, plan_stitches
from digitizer_core.config import PipelineConfig
from shapely.ops import unary_union
OUT, slug, dest = sys.argv[2], sys.argv[3], sys.argv[4]
RES = 10.0
man = json.load(open(Path(OUT) / "manifest.json"))
e = [x for x in man if x["slug"] == slug][0]
cfg = PipelineConfig(); cfg.fill_density_boost = True
cfg.target_width_mm = round(e["pro"]["width_mm"], 1)
res = run_stages(str(Path(OUT) / slug / "art.png"), cfg); plan = plan_stitches(res, cfg)
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
tw = max(1, int(0.40 * RES))
for r in runs:
    pts = [px(p) for p in r]
    for k in range(len(pts) - 1):
        cv2.line(th, pts[k], pts[k + 1], 1, tw)
np.savez(dest, sh=sh, th=th, bounds=np.array([x0, y0, x1, y1]))
'''
rp = HERE / "_holerun.py"
rp.write_text(RUNNER)
PY = "/home/user/EMB-Bot/digitizer/.venv/bin/python"
for dz, nm in ((dz_b, "b"), (dz_a, "a")):
    subprocess.run([PY, str(rp), str((HERE / dz).resolve()), OUT, slug,
                    str(HERE / f"_hole_{nm}.npz")], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

B = np.load(HERE / "_hole_b.npz"); A = np.load(HERE / "_hole_a.npz")
x0, y0, x1, y1 = B["bounds"]
mm = ((cx - 4) / RES + x0, (cy - 4) / RES + y0)

panels = []
for D, name in ((B, "BEFORE  3a1f673"), (A, "AFTER  +laneB")):
    sh, th = D["sh"], D["th"]
    img = np.zeros((*sh.shape, 3), np.uint8)
    img[sh > 0] = (70, 70, 70)                       # fabric inside the shape
    img[th > 0] = (245, 245, 245)                    # thread
    bare = (sh > 0) & (th == 0)
    img[bare] = (40, 40, 190)                        # bare fabric, BGR red
    y_lo, y_hi = max(0, cy - PAD), min(sh.shape[0], cy + PAD)
    x_lo, x_hi = max(0, cx - PAD), min(sh.shape[1], cx + PAD)
    crop = img[y_lo:y_hi, x_lo:x_hi]
    crop = cv2.resize(crop, None, fx=ZOOM, fy=ZOOM, interpolation=cv2.INTER_NEAREST)
    cv2.putText(crop, name, (8, 26), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
    panels.append(crop)

h = max(p.shape[0] for p in panels)
panels = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 8, cv2.BORDER_CONSTANT, value=(0, 0, 0))
          for p in panels]
out = np.hstack(panels)
cv2.putText(out, f"{slug}  design mm ({mm[0]:.2f}, {mm[1]:.2f})  red = bare fabric",
            (8, out.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
dest = HERE / f"hole_{tag}.png"
cv2.imwrite(str(dest), out)
print(f"{slug} blob at design mm ({mm[0]:.2f}, {mm[1]:.2f}) -> {dest}")
