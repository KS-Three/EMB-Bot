import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys

from shapely.geometry import LineString, box
from shapely.ops import unary_union
OUT = _OUT
d = pickle.load(open(OUT + "/cap.pkl", "rb"))
TH = 0.2
SKIP = {"travel", "jump", "trim"}
segs = []
for b in d["blocks"]:
    for pts, kind in zip(b["runs"], b["run_kinds"]):
        if kind in SKIP or len(pts) < 2:
            continue
        segs.append(LineString(pts).buffer(TH, cap_style=1, join_style=1))
thread = unary_union(segs)

NAMED = {
    "S8438f8fc": "PRECISION N", "S3e7df60e": "THERMAL H", "S14057482": "THERMAL E",
    "Sc6ef66a0": "DRONE E", "Sa155e9ec": "DRONE N", "S37e7e27f": "AND N",
    "Sa7529943": "PRECISION O", "S60ac57f2": "PRECISION R?", "S46627035": "PRECISION P?",
    "S85b059f2": "PRECISION C?", "Sf812c421": "DRONE O", "Sc90d4b1a": "AND D",
    "Sb0a7fa0d": "THERMAL T", "S6cc4a060": "THERMAL M?", "S81d913c5": "THERMAL A?",
    "S81b4b426": "THERMAL L?", "Sbf8a37c3": "THERMAL R?",
}
regs = dict(d["regions"])
print("%-14s %-12s %8s %8s %6s %8s %6s" % ("shape", "name", "area", "bare", "bare%", "spill", "spill%"))
for sid, name in NAMED.items():
    p = regs[sid]
    bare = p.difference(thread)
    # spill: thread within 2mm of this letter that falls outside the letter polygon
    near = thread.intersection(p.buffer(1.2))
    spill = near.difference(p)
    print("%-14s %-12s %8.3f %8.3f %5.1f%% %8.3f %5.1f%%" % (sid, name, p.area, bare.area, 100*bare.area/p.area, spill.area, 100*spill.area/p.area))
    # top bare blobs
    gs = [bare] if bare.geom_type == "Polygon" else list(bare.geoms)
    gs = sorted([g for g in gs if g.area > 0.05], key=lambda g: -g.area)[:3]
    for g in gs:
        b = g.bounds
        print("      bare blob %6.3f mm2  x[%7.2f,%7.2f] y[%6.2f,%6.2f]" % (g.area, b[0], b[2], b[1], b[3]))
