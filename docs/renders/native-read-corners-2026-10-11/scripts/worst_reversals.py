"""Diagnose Becker reversal vertices: which read point, flags, displacement."""
import dataclasses
import pickle
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

WT = Path(__file__).resolve().parents[4]
sys.path[:0] = [str(WT / "digitizer")]
from digitizer_core import stage4_vectorize as S4  # noqa: E402
from digitizer_core import subpixel as SP  # noqa: E402

S = Path(sys.argv[1])
w = sys.argv[2]
kw = eval(sys.argv[3]) if len(sys.argv) > 3 else {}
for kv in (sys.argv[4].split(",") if len(sys.argv) > 4 else []):
    k, v = kv.split("=")
    setattr(SP, k, float(v))
cap = pickle.loads((S / f"becker_{w}.pkl").read_bytes())
p = cap["p"]

rings = []
hold = {}
orig_fit = SP._fit_corners; orig_runs = SP._fit_corner_runs
orig_ns = S4._native_subpixel


def mkfit(fn):
    def fit(raw, pts, accepted, protect, corner, steps):
        hold.update(pre_pts=pts.copy(), pre_acc=accepted.copy(), corner=corner.copy(), protect_pre=protect.copy())
        fn(raw, pts, accepted, protect, corner, steps)
        hold.update(post_pts=pts.copy())
    return fit


def ns(raw_int, lab, mask, origin, pp, de, **kw2):
    hold.clear()
    up, acc, prot = orig_ns(raw_int, lab, mask, origin, pp, de, **kw2)
    sx, sy = pp.upscale
    rings.append(dict(raw=raw_int.astype(float), up=up, acc=acc, prot=prot,
                      corner=hold.get("corner", np.zeros(len(up), bool)),
                      fitted=np.any(hold["pre_pts"] != hold["post_pts"], axis=1) if "post_pts" in hold else np.zeros(len(up), bool),
                      pre_up=np.stack([(hold["pre_pts"][:, 0] + .5) * sx - .5, (hold["pre_pts"][:, 1] + .5) * sy - .5], 1) if "pre_pts" in hold else up))
    return up, acc, prot


SP._fit_corners = mkfit(orig_fit); SP._fit_corner_runs = mkfit(orig_runs)
S4._native_subpixel = ns
try:
    regs = S4.vectorize(cap["masks"], cap["ti"], p, dataclasses.replace(cap["cfg"], **kw))[0]
finally:
    SP._fit_corners = orig_fit; SP._fit_corner_runs = orig_runs
    S4._native_subpixel = orig_ns

x0, y0, x1, y1 = p.art_bbox
cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
ppm = p.px_per_mm
sx, sy = p.upscale

allpts = np.vstack([r["up"] for r in rings])
owner = np.concatenate([[(k, i) for i in range(len(r["up"]))] for k, r in enumerate(rings)])
tree = cKDTree(allpts)

revs = []
for ri, reg in enumerate(regs):
    for ring in [reg.polygon.exterior, *reg.polygon.interiors]:
        r = np.asarray(ring.coords)[:-1]
        px = np.stack([r[:, 0] * ppm + cx, r[:, 1] * ppm + cy], 1)
        n = len(px)
        for j in range(n):
            a, b, c = px[j - 1], px[j], px[(j + 1) % n]
            u, v = b - a, c - b
            if np.hypot(*u) < 1e-9 or np.hypot(*v) < 1e-9:
                continue
            ang = np.degrees(np.arccos(np.clip(u @ v / np.hypot(*u) / np.hypot(*v), -1, 1)))
            if ang > 120:
                revs.append(dict(reg=ri, j=j, ang=ang, prev=a, at=b, nxt=c,
                                 len_in=np.hypot(*u) / sx, len_out=np.hypot(*v) / sx, ring=px))
print(f"{len(revs)} reversal vertices on {len(regs)} regions")
out = []
for rv in sorted(revs, key=lambda d: -d["ang"]):
    rec = {}
    for key in ("prev", "at", "nxt"):
        d, k = tree.query(rv[key])
        rk, ii = owner[k]
        R = rings[rk]
        rec[key] = dict(d=d, ring=int(rk), i=int(ii), acc=bool(R["acc"][ii]), corner=bool(R["corner"][ii]),
                        fitted=bool(R["fitted"][ii]),
                        move_src=float(np.hypot(*(R["up"][ii] - R["raw"][ii])) / sx),
                        fit_move_src=float(np.hypot(*(R["up"][ii] - R["pre_up"][ii])) / sx))
    rv["rec"] = rec
    out.append(rv)
    at = rec["at"]
    print(f"ang {rv['ang']:6.1f} at ({rv['at'][0]/sx:7.1f},{rv['at'][1]/sy:7.1f})src  in {rv['len_in']:.2f} out {rv['len_out']:.2f} srcpx | "
          + " | ".join(f"{k}: d{v['d']:.2g} acc{int(v['acc'])} cor{int(v['corner'])} fit{int(v['fitted'])} mv{v['move_src']:.2f} fitmv{v['fit_move_src']:.2f}"
                       for k, v in rec.items()))
pickle.dump(dict(revs=out, rings=rings, regs=[r.polygon for r in regs]), open(S / f"diag_{w}.pkl", "wb"))
