import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

import pickle, sys

from PIL import Image, ImageDraw
OUT = _OUT
d = pickle.load(open(OUT + "/cap.pkl", "rb"))
regs = dict(d["regions"])
im = Image.open("/home/user/EMB-Bot/digitizer/testdata/photo/drone_render.png").convert("RGB")
PPM = 9.6125
CX, CY = 768.0, 512.0
S = 10
PAD = 1.2

def go(sid, name):
    p = regs[sid]
    x0, y0, x1, y1 = p.bounds
    a = int((x0 - PAD) * PPM + CX); b = int((x1 + PAD) * PPM + CX)
    c = int((y0 - PAD) * PPM + CY); e = int((y1 + PAD) * PPM + CY)
    sub = im.crop((a, c, b, e)).resize(((b - a) * S, (e - c) * S), Image.NEAREST)
    dr = ImageDraw.Draw(sub)
    def T(q):
        return ((q[0] * PPM + CX - a) * S, (q[1] * PPM + CY - c) * S)
    dr.line([T(q) for q in p.exterior.coords], fill=(0, 90, 255), width=3)
    for it in p.interiors:
        dr.line([T(q) for q in it.coords], fill=(0, 90, 255), width=3)
    for q in p.exterior.coords[:-1]:
        x, y = T(q)
        dr.ellipse([x-6, y-6, x+6, y+6], fill=(255, 0, 0))
    path = OUT + "/POLY_%s.png" % name
    sub.save(path)
    print(path, len(p.exterior.coords) - 1, "vertices")

for sid, n in [("S3e7df60e", "THERMAL_H"), ("S8438f8fc", "PRECISION_N"),
               ("S14057482", "THERMAL_E"), ("Sc6ef66a0", "DRONE_E")]:
    go(sid, n)
