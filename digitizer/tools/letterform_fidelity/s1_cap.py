import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys, os

from digitizer_core.pipeline import digitize
from digitizer_core.config import PipelineConfig

OUT = _OUT

result, plan = digitize("testdata/photo/drone_render.png", PipelineConfig())
print("design_class", getattr(result, "design_class", None))
print("regions", len(result.regions))
print("blocks", len(plan.blocks))

data = {
    "regions": [(r.shape_id, r.polygon) for r in result.regions],
    "blocks": [],
}
for b in plan.blocks:
    data["blocks"].append({
        "shape_id": getattr(b, "shape_id", None),
        "kind": getattr(b, "kind", None),
        "runs": [list(run.points) for run in b.runs],
        "run_kinds": [getattr(run, "kind", None) for run in b.runs],
    })
with open(os.path.join(OUT, "cap.pkl"), "wb") as f:
    pickle.dump(data, f)
print("ok")
