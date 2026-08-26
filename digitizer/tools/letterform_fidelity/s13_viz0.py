import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

"""stitchviz render of the pull-comp = 0 CONTROL (prototype monkeypatch, no repo edit)."""
import dataclasses, io, sys

from digitizer_core import fabrics as F
for i, fab in enumerate(F.FABRICS):
    F.FABRICS[i] = dataclasses.replace(fab, pull_comp_mm=0.0)
for name in dir(F):
    obj = getattr(F, name)
    if isinstance(obj, dict) and obj and all(isinstance(v, F.Fabric) for v in obj.values()):
        setattr(F, name, {k: dataclasses.replace(v, pull_comp_mm=0.0) for k, v in obj.items()})

from PIL import Image
from digitizer_core.pipeline import digitize
from digitizer_core.config import PipelineConfig
from digitizer_core.adapter import plan_to_design
from digitizer_core import stitchviz

OUT = _OUT
PPM = 28.0
result, plan = digitize("testdata/photo/drone_render.png", PipelineConfig())
design = plan_to_design(plan, name="x")
im = Image.open(io.BytesIO(stitchviz.render_png_bytes(design, px_per_mm=PPM))).convert("RGB")
xs = [p[0] for b in plan.blocks for r in b.runs for p in r.points]
ys = [p[1] for b in plan.blocks for r in b.runs for p in r.points]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
W, H = im.size
mx = (W - (x1 - x0) * PPM) / 2.0
my = (H - (y1 - y0) * PPM) / 2.0

def crop(bx0, bx1, by0, by1, name, pad=1.0, scale=3):
    a = int((bx0 - pad - x0) * PPM + mx); b = int((bx1 + pad - x0) * PPM + mx)
    c = int((by0 - pad - y0) * PPM + my); e = int((by1 + pad - y0) * PPM + my)
    s = im.crop((a, c, b, e))
    s = s.resize((s.width * scale, s.height * scale), Image.LANCZOS)
    s.save(OUT + "/VIZ0_%s.png" % name)
    print(name, s.size)

crop(-20.23, -13.16, 22.52, 28.24, "THERMAL_H")
crop(30.33, 39.90, 13.06, 21.48, "PRECISION_N")
crop(-31.68, 30.85, 30.74, 33.76, "row_ANDDRONE", pad=0.6, scale=3)
crop(-18.67, 39.90, 13.06, 21.48, "row_PRECISION", pad=0.6, scale=2)
