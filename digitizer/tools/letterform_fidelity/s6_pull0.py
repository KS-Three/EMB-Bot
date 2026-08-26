import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

"""CONTROL: re-run the pipeline with pull compensation set to zero.

Prototype only — monkeypatches the in-memory fabric table, edits no repo file.
"""
import dataclasses, pickle, sys, os

from digitizer_core import fabrics as F

for i, fab in enumerate(F.FABRICS):
    F.FABRICS[i] = dataclasses.replace(fab, pull_comp_mm=0.0)
if hasattr(F, "_BY_ID"):
    F._BY_ID = {f.id: f for f in F.FABRICS}
for name in dir(F):
    obj = getattr(F, name)
    if isinstance(obj, dict) and obj and all(isinstance(v, F.Fabric) for v in obj.values()):
        setattr(F, name, {k: dataclasses.replace(v, pull_comp_mm=0.0) for k, v in obj.items()})

from digitizer_core.pipeline import digitize
from digitizer_core.config import PipelineConfig

result, plan = digitize("testdata/photo/drone_render.png", PipelineConfig())
print("regions", len(result.regions))
data = {"regions": [(r.shape_id, r.polygon) for r in result.regions], "blocks": []}
for b in plan.blocks:
    data["blocks"].append({"runs": [list(r.points) for r in b.runs],
                           "run_kinds": [getattr(r, "kind", None) for r in b.runs]})
OUT = _OUT
pickle.dump(data, open(os.path.join(OUT, "cap_pull0.pkl"), "wb"))
print("ok")
