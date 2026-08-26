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
SKIP = {"travel", "jump", "trim"}
PPM = 40.0
PAD = 1.5

def load(fn):
    d = pickle.load(open(OUT + "/" + fn, "rb"))
    return dict(d["regions"]), d["blocks"]

def crop(regs, blocks, sid, title):
    poly = regs[sid]
    x0, y0, x1, y1 = poly.bounds
    x0 -= PAD; y0 -= PAD; x1 += PAD; y1 += PAD
    W = int((x1 - x0) * PPM); H = int((y1 - y0) * PPM)
    img = Image.new("RGB", (W, H), (238, 236, 232))
    dr = ImageDraw.Draw(img)
    def T(p):
        return ((p[0] - x0) * PPM, (p[1] - y0) * PPM)
    for b in blocks:
        for pts, kind in zip(b["runs"], b["run_kinds"]):
            if kind in SKIP or len(pts) < 2:
                continue
            col = (120, 150, 200) if kind == "underlay" else (250, 250, 250)
            w = max(1, int(round(0.4 * PPM)))
            xy = [T(p) for p in pts]
            dr.line(xy, fill=col, width=w, joint="curve")
            for p in xy:
                dr.ellipse([p[0]-w/2, p[1]-w/2, p[0]+w/2, p[1]+w/2], fill=col)
    ring = [T(p) for p in poly.exterior.coords]
    dr.line(ring, fill=(220, 20, 20), width=3)
    for it in poly.interiors:
        dr.line([T(p) for p in it.coords], fill=(220, 20, 20), width=3)
    return img, title

def pair(sid, name):
    r0, b0 = load("cap.pkl"); r1, b1 = load("cap_pull0.pkl")
    a, _ = crop(r0, b0, sid, "shipped")
    b, _ = crop(r1, b1, sid, "pull0")
    W = a.width + b.width + 24; H = max(a.height, b.height) + 30
    out = Image.new("RGB", (W, H), (255, 255, 255))
    out.paste(a, (0, 30)); out.paste(b, (a.width + 24, 30))
    d = ImageDraw.Draw(out)
    d.text((6, 8), "SHIPPED  (pull comp 0.3 mm)", fill=(0, 0, 0))
    d.text((a.width + 30, 8), "CONTROL  (pull comp 0.0 mm)", fill=(0, 0, 0))
    p = OUT + "/CMP_%s.png" % name
    out.save(p)
    print(p, out.size)

for sid, name in [("S14057482", "THERMAL_E"), ("S3e7df60e", "THERMAL_H"),
                  ("S8438f8fc", "PRECISION_N"), ("Sc6ef66a0", "DRONE_E")]:
    pair(sid, name)
