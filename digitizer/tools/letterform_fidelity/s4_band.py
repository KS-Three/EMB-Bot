import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys

OUT = _OUT
d = pickle.load(open(OUT + "/cap.pkl", "rb"))
bands = {"PRECISION": (12.0, 22.0), "THERMAL": (22.0, 29.5), "AND DRONE": (30.0, 34.5)}
for name, (y0, y1) in bands.items():
    rows = []
    for sid, poly in d["regions"]:
        cy = poly.centroid.y
        if y0 <= cy <= y1:
            rows.append((poly.bounds[0], sid, poly))
    rows.sort()
    print("=== %s : %d regions" % (name, len(rows)))
    for x0, sid, p in rows:
        b = p.bounds
        print("   %s  x[%7.2f,%7.2f] y[%6.2f,%6.2f]  w %5.2f h %5.2f  area %7.3f  interiors %d" %
              (sid, b[0], b[2], b[1], b[3], b[2]-b[0], b[3]-b[1], p.area, len(p.interiors)))
