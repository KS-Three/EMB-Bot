import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys

from shapely.geometry import LineString
from shapely.ops import unary_union
OUT = _OUT
TH = 0.2
SKIP = {"travel", "jump", "trim"}

def load(fn):
    d = pickle.load(open(OUT + "/" + fn, "rb"))
    segs = []
    for b in d["blocks"]:
        for pts, kind in zip(b["runs"], b["run_kinds"]):
            if kind in SKIP or len(pts) < 2:
                continue
            segs.append(LineString(pts).buffer(TH, cap_style=1, join_style=1))
    return dict(d["regions"]), unary_union(segs)

r0, t0 = load("cap.pkl")
r1, t1 = load("cap_pull0.pkl")

NAMED = [("S46627035","PRECISION P"),("S60ac57f2","PRECISION R"),("S85b059f2","PRECISION C"),
         ("Sa7529943","PRECISION O"),("S8438f8fc","PRECISION N"),
         ("Sb0a7fa0d","THERMAL T"),("S3e7df60e","THERMAL H"),("S14057482","THERMAL E"),
         ("Sbf8a37c3","THERMAL R"),("S6cc4a060","THERMAL M"),("S81d913c5","THERMAL A"),
         ("S81b4b426","THERMAL L"),
         ("S5f511ee1","AND A"),("S37e7e27f","AND N"),("Sc90d4b1a","AND D"),
         ("S3f60d519","DRONE R"),("S420b5535","DRONE O"),("Sf812c421","DRONE O2"),
         ("Sa155e9ec","DRONE N"),("Sc6ef66a0","DRONE E")]

def iou(p, th):
    near = th.intersection(p.buffer(1.5))
    inter = near.intersection(p).area
    union = near.union(p).area
    return inter / union

print("%-13s %8s %7s %7s" % ("letter", "area", "IoU@0.3", "IoU@0.0"))
tot0 = tot1 = 0.0
for sid, name in NAMED:
    a = iou(r0[sid], t0); b = iou(r1[sid], t1)
    tot0 += a; tot1 += b
    print("%-13s %8.2f %7.3f %7.3f" % (name, r0[sid].area, a, b))
print("%-13s %8s %7.3f %7.3f" % ("MEAN", "", tot0/len(NAMED), tot1/len(NAMED)))
