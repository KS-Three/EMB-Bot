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
    n = 0
    for b in d["blocks"]:
        for pts, kind in zip(b["runs"], b["run_kinds"]):
            if kind in SKIP or len(pts) < 2:
                continue
            n += len(pts)
            segs.append(LineString(pts).buffer(TH, cap_style=1, join_style=1))
    return dict(d["regions"]), unary_union(segs), n

r0, t0, n0 = load("cap.pkl")
r1, t1, n1 = load("cap_pull0.pkl")
print("stitch points  shipped %d   pull0 %d" % (n0, n1))

NAMED = {
    "S8438f8fc": "PRECISION N", "S3e7df60e": "THERMAL H", "S14057482": "THERMAL E",
    "Sc6ef66a0": "DRONE E", "Sa155e9ec": "DRONE N", "S37e7e27f": "AND N",
    "Sa7529943": "PRECISION O", "Sf812c421": "DRONE O", "Sc90d4b1a": "AND D",
    "S5f511ee1": "AND A", "S3f60d519": "DRONE R", "S420b5535": "DRONE O2",
    "Sb0a7fa0d": "THERMAL T", "S6cc4a060": "THERMAL M", "S81b4b426": "THERMAL L",
}
print("%-13s | %-28s | %-28s" % ("", "SHIPPED (pull 0.3)", "CONTROL (pull 0.0)"))
print("%-13s | %7s %7s %7s | %7s %7s %7s" % ("letter", "area", "bare%", "spill%", "area", "bare%", "spill%"))
for sid, name in NAMED.items():
    a = r0[sid]; b = r1[sid]
    def m(p, th):
        bare = p.difference(th).area
        spill = th.intersection(p.buffer(1.2)).difference(p).area
        return 100*bare/p.area, 100*spill/p.area
    ba, sa = m(a, t0); bb, sb = m(b, t1)
    print("%-13s | %7.2f %6.1f%% %6.1f%% | %7.2f %6.1f%% %6.1f%%" % (name, a.area, ba, sa, b.area, bb, sb))
    # sanity: artwork polygons identical between runs?
    if abs(a.area - b.area) > 1e-6:
        print("      NOTE artwork polygon differs between runs by %.4f mm2" % (a.area - b.area))
