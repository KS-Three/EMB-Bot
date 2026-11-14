"""original | ours (arms...) | pro at one spot, single stitches visible.
argv: tree slug out.png cx cy half_mm label=run_dir [label=run_dir ...]
run_dir holds runs.json + regions.json (mfab_run.py). The pro registers onto the FIRST run."""
import json
import sys
from pathlib import Path

tree, slug, outp = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
cx, cy, HALF = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
arms = [a.split("=", 1) for a in sys.argv[7:]]
sys.path.insert(0, str(tree))
import cv2  # noqa: E402
import numpy as np  # noqa: E402

sys.argv = [sys.argv[0], str(tree), ".", r"C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/eye_pairs_out/apex-guard-1114/tipgroups.json", str(outp.parent)]
exec(open(Path(__file__).with_name("gain_sheets.py"), encoding="utf-8").read().split("for name, sids in GAINS")[0])
HALF = float(__import__("os").environ.get("HALF", "4")); S = 360.0 / (2 * HALF)


def load(d):
    rs = json.load(open(Path(d) / "runs.json"))
    # -> the corpus pickle's shape: [[(rgb, [(pts, kind, jump, trim, sid)])]]
    return [[(tuple(rgb), [(pts, kind, jump, False, sid) for kind, jump, sid, pts in runs if kind != "bean"])] for rgb, runs in rs] + [[((230, 30, 30), [(pts, kind, jump, False, sid) for kind, jump, sid, pts in runs if kind == "bean"])] for rgb, runs in rs]


def panel2(runs, title):
    global S, HALF
    return panel(runs, cx, cy, title)


ours = [(lab, load(d)) for lab, d in arms]
j = pb.JOBS[slug]
path = pb.resolve(j[4]) if len(j) > 4 and j[4] else pb.resolve(j[3])
reg = register(path, ours[0][1])
pro = pro_runs(path, reg)
print("registered iou", round(reg[4], 3))
# the art: the source raster in our plan frame (the run's prep is not kept): affine from the
# art's content bbox to the design's stitch bbox is good enough to look at
regs = json.load(open(Path(arms[0][1]) / "regions.json"))
xs = [b for r in regs["regions"] for b in (r["bounds"][0], r["bounds"][2])]
ys = [b for r in regs["regions"] for b in (r["bounds"][1], r["bounds"][3])]
art = cv2.imread(str(pb.resolve(j[2])), cv2.IMREAD_UNCHANGED)
if art.ndim == 3 and art.shape[2] == 4:
    a = art[:, :, 3:4] / 255.0
    art = (art[:, :, :3] * a + 235 * (1 - a)).astype(np.uint8)
g = cv2.cvtColor(art, cv2.COLOR_BGR2GRAY).astype(int)
bgv = np.median(np.r_[g[0], g[-1], g[:, 0], g[:, -1]])
yy, xx = np.nonzero(np.abs(g - bgv) > 25)
sx = (xx.max() - xx.min()) / (max(xs) - min(xs))
sy = (yy.max() - yy.min()) / (max(ys) - min(ys))
px0, py0 = xx.min() + (cx - HALF - min(xs)) * sx, yy.min() + (cy - HALF - min(ys)) * sy
crop = art[int(py0):int(py0 + 2 * HALF * sy), int(px0):int(px0 + 2 * HALF * sx)]
crop = cv2.resize(crop, (360, 360), interpolation=cv2.INTER_NEAREST)
cv2.rectangle(crop, (0, 0), (360, 24), (255, 255, 255), -1)
cv2.putText(crop, f"original {slug}", (4, 17), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 180), 1)
row = [crop] + [panel2(flat(r), lab) for lab, r in ours] + [panel2(pro, "pro")]
cv2.imwrite(str(outp), np.hstack(row))
print("wrote", outp)
