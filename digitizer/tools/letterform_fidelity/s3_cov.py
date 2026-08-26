import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union
OUT = _OUT
d = pickle.load(open(OUT + "/cap.pkl", "rb"))
THREAD_HALF = 0.2

SKIP = {"travel", "jump", "trim"}

def thread_geom(include_underlay=True):
    segs = []
    for b in d["blocks"]:
        for pts, kind in zip(b["runs"], b["run_kinds"]):
            if kind in SKIP:
                continue
            if not include_underlay and kind == "underlay":
                continue
            if len(pts) < 2:
                continue
            segs.append(LineString(pts).buffer(THREAD_HALF, cap_style=1, join_style=1))
    return unary_union(segs)

for inc in (True, False):
    th = thread_geom(inc)
    rows = []
    tot_a = tot_bare = 0.0
    for sid, poly in d["regions"]:
        bare = poly.difference(th)
        rows.append((sid, poly.area, bare.area, poly.bounds))
        tot_a += poly.area; tot_bare += bare.area
    rows.sort(key=lambda r: -r[2])
    print("=== include_underlay =", inc, " total_area %.2f total_bare %.2f (%.2f%%)" % (tot_a, tot_bare, 100*tot_bare/tot_a))
    for sid, a, bare, bb in rows[:14]:
        print("  %s area %8.3f bare %7.3f (%5.1f%%)  bbox x[%7.2f,%7.2f] y[%7.2f,%7.2f]" % (sid, a, bare, 100*bare/a, bb[0], bb[2], bb[1], bb[3]))
    print()
