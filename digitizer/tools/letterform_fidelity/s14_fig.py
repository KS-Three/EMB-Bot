import os as _os, pathlib as _pl, sys as _sys
# Portable since 2026-08-26; these ran in-session against absolute scratchpad
# paths. Repo root is resolved from this file, and outputs go to $LF_OUT
# (default: ./out beside these scripts). Run with cwd = digitizer/.
_DIGITIZER = str(_pl.Path(__file__).resolve().parents[2])
_sys.path.insert(0, _DIGITIZER)
_OUT = _os.environ.get("LF_OUT", str(_pl.Path(__file__).resolve().parent / "out"))
_pl.Path(_OUT).mkdir(parents=True, exist_ok=True)

from PIL import Image, ImageDraw
OUT = _OUT

strips = [
    ("VIZ_row_PRECISION.png",  "SHIPPED  -  'PRECISION'  (7.6 mm caps, 1.7-2.0 mm strokes)"),
    ("VIZ0_row_PRECISION.png", "CONTROL, pull comp 0.0 mm  -  same code, same artwork"),
    ("VIZ_row_ANDDRONE.png",   "SHIPPED  -  'AND DRONE'  (2.9 mm caps, 0.55-0.70 mm strokes)  ->  reads A-N(rev)-D  D-R-O-N(rev)-X"),
    ("VIZ0_row_ANDDRONE.png",  "CONTROL, pull comp 0.0 mm  ->  N's correct, E still sews as an L"),
]
ims = []
TARGET = 1900
for fn, cap in strips:
    im = Image.open(OUT + "/" + fn).convert("RGB")
    s = TARGET / im.width
    im = im.resize((TARGET, max(1, int(im.height * s))), Image.LANCZOS)
    ims.append((im, cap))

pad = 14
lab = 22
W = TARGET + 2 * pad
H = sum(im.height + lab + pad for im, _ in ims) + pad
out = Image.new("RGB", (W, H), (255, 255, 255))
d = ImageDraw.Draw(out)
y = pad
for im, cap in ims:
    d.text((pad, y), cap, fill=(10, 10, 10))
    y += lab
    out.paste(im, (pad, y))
    y += im.height + pad
p = OUT + "/FIG_letterform_before_after.png"
out.save(p)
print(p, out.size)
