"""The pro's stitches on MFab's A counter: each needle-to-needle stitch inside the triangle,
in sew order, with angle, length, and position along the shape. argv: tree run_dir sid"""
import json
import math
import sys
from pathlib import Path

tree, run_dir, sid = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
sys.argv = [sys.argv[0], str(tree), ".", r"C:/Users/EE-LT-11030/Claude Personal/EMB-Bot/digitizer/eye_pairs_out/apex-guard-1114/tipgroups.json",
            r"C:/Users/EE-LT-~1/AppData/Local/Temp/claude/071b1732849458bd/62e56464-dd7b-488a-8302-f8c388f50168/scratchpad"]
sys.path.insert(0, str(tree))
exec(open(Path(__file__).with_name("gain_sheets.py"), encoding="utf-8").read().split("for name, sids in GAINS")[0])
from shapely.geometry import LineString, MultiPoint, Point  # noqa: E402

rs = json.load(open(run_dir / "runs.json"))
ours = [[(tuple(rgb), [(pts, kind, jump, False, s) for kind, jump, s, pts in runs])] for rgb, runs in rs]
fill_pts = [p for rgb, runs in rs for kind, jump, s, pts in runs if s == sid and kind == "fill" for p in pts]
tri = MultiPoint(fill_pts).convex_hull
print("our counter (fill hull): area", round(tri.area, 2), "bounds", [round(v, 2) for v in tri.bounds])
j = pb.JOBS["mfab_hat"]
path = pb.resolve(j[4]) if len(j) > 4 and j[4] else pb.resolve(j[3])
reg = register(path, ours)
print("registered iou", round(reg[4], 3))
pro = pro_runs(path, reg)
zone = tri.buffer(0.3)
seq = []
for rgb, pts in pro:
    for a, b in zip(pts[:-1], pts[1:]):
        if zone.contains(Point(a)) and zone.contains(Point(b)):
            L = math.dist(a, b)
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
            seq.append((a, b, L, ang, rgb))
print("pro stitches inside:", len(seq), "colours", sorted({s[4] for s in seq}))
# the triangle's long axis: from its narrow tip to the base midpoint
xs, ys = tri.exterior.xy
for i, (a, b, L, ang, rgb) in enumerate(seq):
    mid = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    if i % 3 == 0 or L < 1.0:
        print(f"{i:3d} L {L:5.2f} ang {ang:6.1f} mid ({mid[0]:6.2f},{mid[1]:6.2f})")
