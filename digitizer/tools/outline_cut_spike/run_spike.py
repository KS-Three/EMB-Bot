"""usage: run_spike.py <design> <shape_id,...|text> <out.png>
Draws the cut plan (outline, corners, cuts, pieces, rails) and the thread render."""
import sys, pickle
from pathlib import Path
import numpy as np, cv2
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

sys.path.insert(0, str(HERE.parents[1]))          # digitizer/, for digitizer_core
from digitizer_core import stitchviz
import oc

name, sel, out = sys.argv[1], sys.argv[2], sys.argv[3]
d = pickle.load(open(HERE / f"{name}.pkl", "rb"))
regs = [r for r in d["regions"] if (sel == "text" and r["meta"].get("text_candidate")) or r["shape_id"] in sel.split(",")]
regs.sort(key=lambda r: r["polygon"].bounds[0])
PPM = 40
res = [oc.letter_columns(r["polygon"]) for r in regs]
x0 = min(r["poly"].bounds[0] for r in res) - 1
x1 = max(r["poly"].bounds[2] for r in res) + 1
y0 = min(r["poly"].bounds[1] for r in res) - 1
y1 = max(r["poly"].bounds[3] for r in res) + 1
H, Wd = int((y1 - y0) * PPM), int((x1 - x0) * PPM)
px = lambda p: (int((p[0] - x0) * PPM), int((p[1] - y0) * PPM))
img = np.full((H, Wd, 3), 245, np.uint8)
rng = np.random.default_rng(3)
for r in res:
    for c in r["cols"]:
        col = tuple(int(v) for v in rng.integers(150, 235, 3))
        cv2.fillPoly(img, [np.array([px(p) for p in c["piece"].exterior.coords], np.int32)], col)
        for h in c["piece"].interiors:
            cv2.fillPoly(img, [np.array([px(p) for p in h.coords], np.int32)], (245, 245, 245))
    rings = [r["poly"].exterior] + list(r["poly"].interiors)
    for ring in rings:
        cv2.polylines(img, [np.array([px(p) for p in ring.coords], np.int32)], True, (60, 60, 60), 2)
    for c in r["cols"]:
        if c["rails"]:
            for rail, colr in zip(c["rails"], ((0, 140, 0), (160, 0, 160))):
                cv2.polylines(img, [np.array([px(p) for p in rail], np.int32)], False, colr, 5)
        elif c["axis"]:
            cp = c["piece"].centroid.coords[0]; u = c["axis"]
            cv2.arrowedLine(img, px((cp[0] - u[0], cp[1] - u[1])), px((cp[0] + u[0], cp[1] + u[1])), (0, 90, 200), 3)
        else:
            cp = c["piece"].representative_point().coords[0]
            cv2.putText(img, "X", px(cp), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 0, 255), 3)
    for a, b, kind, _ in r["cuts"]:
        cv2.line(img, px(a), px(b), (0, 0, 255), 3)
        cv2.putText(img, kind, px(((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 160), 1)
    for q in r["reflex"]:
        cv2.circle(img, px(q["p"]), 9, (0, 0, 255), -1)
    for q in r["convex"]:
        cv2.circle(img, px(q["p"]), 6, (255, 120, 0), -1)
    print(f"W={r['W']:.2f} reflex={len(r['reflex'])} convex={len(r['convex'])} cuts={[(k, round(L, 1)) for _, _, k, L in r['cuts']]} "
          f"pieces={len(r['cols'])} sewn={sum(1 for c in r['cols'] if c['stitches'])} straight={sum(1 for c in r['cols'] if c['axis'])}")

# thread render
st = []
for r in res:
    for c in r["cols"]:
        if not c["stitches"]:
            continue
        p = c["stitches"]
        st.append(dict(x=p[0][0] * 10, y=-p[0][1] * 10, type="jump"))
        st.extend(dict(x=q[0] * 10, y=-q[1] * 10, type="stitch") for q in p)
        st.append(dict(x=p[-1][0] * 10, y=-p[-1][1] * 10, type="trim"))
design = dict(stitches=st, colors=[dict(r=96, g=100, b=112)])
th = stitchviz.render_design(design, px_per_mm=PPM, pad_mm=1.0)
if th.shape[0] != H:
    th = th[::1]
Wm = max(img.shape[1], th.shape[1])
pad = lambda im: cv2.copyMakeBorder(im, 0, 8, 0, Wm - im.shape[1], cv2.BORDER_CONSTANT, value=(90, 90, 90))
cv2.imwrite(out, np.vstack([pad(img), pad(th)]))
print("wrote", out, "stitches", sum(1 for s in st if s["type"] == "stitch"))
