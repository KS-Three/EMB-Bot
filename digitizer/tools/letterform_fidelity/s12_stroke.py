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
regs = dict(d["regions"])
NAMED = [("S46627035","PRECISION P"),("S8438f8fc","PRECISION N"),("Sa7529943","PRECISION O"),
         ("S3e7df60e","THERMAL H"),("S14057482","THERMAL E"),("Sb0a7fa0d","THERMAL T"),
         ("S5f511ee1","AND A"),("S37e7e27f","AND N"),("Sa155e9ec","DRONE N"),
         ("Sc6ef66a0","DRONE E"),("Sf812c421","DRONE O2")]
print("%-13s %7s %7s %7s %8s" % ("letter", "cap_h", "area", "perim", "mean_w"))
for sid, name in NAMED:
    p = regs[sid]
    b = p.bounds
    per = p.exterior.length + sum(i.length for i in p.interiors)
    w = p.area / (per / 2.0)
    print("%-13s %7.2f %7.2f %7.2f %8.3f" % (name, b[3]-b[1], p.area, per, w))
