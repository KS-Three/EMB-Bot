import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import io, sys

from PIL import Image
from digitizer_core.pipeline import digitize
from digitizer_core.config import PipelineConfig
from digitizer_core.adapter import plan_to_design
from digitizer_core import stitchviz

OUT = _OUT
PPM = 28.0
result, plan = digitize("testdata/photo/drone_render.png", PipelineConfig())
design = plan_to_design(plan, name="x")
png = stitchviz.render_png_bytes(design, px_per_mm=PPM)
im = Image.open(io.BytesIO(png)).convert("RGB")
im.save(OUT + "/VIZ_full_28.png")
print("full", im.size)

# design mm bbox -> pixel: assume render spans the design bbox with some margin.
xs = []; ys = []
for b in plan.blocks:
    for r in b.runs:
        for p in r.points:
            xs.append(p[0]); ys.append(p[1])
x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
print("stitch bbox mm", round(x0,2), round(x1,2), round(y0,2), round(y1,2))
W, H = im.size
sx = W / (x1 - x0); sy = H / (y1 - y0)
print("implied ppm x %.3f y %.3f" % (sx, sy))
mx = (W - (x1 - x0) * PPM) / 2.0
my = (H - (y1 - y0) * PPM) / 2.0
print("margins", round(mx,1), round(my,1))

def crop(bx0, bx1, by0, by1, name, pad=1.0, scale=3):
    a = int((bx0 - pad - x0) * PPM + mx); b = int((bx1 + pad - x0) * PPM + mx)
    c = int((by0 - pad - y0) * PPM + my); e = int((by1 + pad - y0) * PPM + my)
    sub = im.crop((a, c, b, e))
    sub = sub.resize((sub.width * scale, sub.height * scale), Image.LANCZOS)
    sub.save(OUT + "/VIZ_%s.png" % name)
    print(name, (a, c, b, e), sub.size)

crop(-20.23, -13.16, 22.52, 28.24, "THERMAL_H")
crop(30.33, 39.90, 13.06, 21.48, "PRECISION_N")
crop(-11.81, -5.15, 22.52, 28.24, "THERMAL_E")
crop(13.68, 22.73, 30.85, 33.76, "DRONE_NE", pad=0.6, scale=5)
crop(-18.67, 39.90, 13.06, 21.48, "row_PRECISION", pad=0.6, scale=2)
crop(-31.68, 30.85, 30.74, 33.76, "row_ANDDRONE", pad=0.6, scale=3)
