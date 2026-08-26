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
print("blocks", len(d["blocks"]))
for i, b in enumerate(d["blocks"][:5]):
    print(i, b["shape_id"], b["kind"], len(b["runs"]), b["run_kinds"][:4])
print("---regions---")
for sid, poly in d["regions"][:5]:
    print(sid, round(poly.area, 3), poly.bounds)
