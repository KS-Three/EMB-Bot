"""Arm C: skip the mask entirely on alpha-only art. Read the source's own
alpha as a coverage field and take its half-level iso-contour (alpha
interpolated up 8x, cut at one half), then Douglas-Peucker in mm.

usage: iso_arm.py RUNS_DIR OUT_DIR   (runs named *sil-flat-r*, plus *-real)
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import analyze as A

K = 8


def iso_polys(alpha, meta, interp, eps_mm, floor=True):
    h, w = alpha.shape
    big = cv2.resize(alpha.astype(np.float32), (w * K, h * K), interpolation=interp)
    m = (big >= 127.5).astype(np.uint8)
    cs, _ = cv2.findContours(m, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    sx, sy = meta["upscale"]
    ppm, cx, cy = meta["px_per_mm"], meta["cx"], meta["cy"]
    rings = []
    for c in cs:
        if len(c) < 8:
            continue
        p = c.reshape(-1, 2).astype(np.float64)
        # contour runs through centres of inside pixels of the Kx grid: push
        # it out half a Kx pixel is below anything measured here, left as is
        xn, yn = (p[:, 0] + 0.5) / K - 0.5, (p[:, 1] + 0.5) / K - 0.5
        xw, yw = (xn + 0.5) * sx - 0.5, (yn + 0.5) * sy - 0.5
        mm = np.column_stack([(xw - cx) / ppm, (yw - cy) / ppm]).astype(np.float32)
        if eps_mm:
            mm = cv2.approxPolyDP(mm.reshape(-1, 1, 2), eps_mm, True).reshape(-1, 2)
        if len(mm) >= 3:
            rings.append(mm.astype(np.float64))
    return [p for p in A.parts(A.fold(rings)) if (A.keep(p) if floor else p.area >= 0.02)]


def nodes(polys):
    return sum(len(r) - 1 for r in A.rings_of(polys))


def main(runs, out):
    runs, out = Path(runs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    A.NAMES.update({"B1": "C iso-contour linear, DP 0.2 mm", "B2": "C iso-contour cubic, DP 0.2 mm"})
    for tdir in sorted(runs.glob("*-truth")):
        truth = A.Truth(tdir)
        fx, lane = tdir.name.split("-")[:2]
        tm = truth.meta
        win = A.densest(truth.b[::2, ::2], truth.ppm, tm["cx"], tm["cy"], 14, 9)
        back = A.label_backdrop(truth.lab, truth.ppm, tm["cx"], tm["cy"], win, 40)
        for d in sorted(runs.glob(f"{fx}-{lane}-r*"), key=lambda p: float(p.name.split("-r")[1])):
            meta = json.loads((d / "meta.json").read_text())
            arms, nd = A.load_arms(d, meta)
            alpha = cv2.imread(str(d / "input.png"), cv2.IMREAD_UNCHANGED)[..., 3]
            cand = {
                "C lin raw": iso_polys(alpha, meta, cv2.INTER_LINEAR, 0.0),
                "C lin dp.05": iso_polys(alpha, meta, cv2.INTER_LINEAR, 0.05),
                "C lin dp.2": iso_polys(alpha, meta, cv2.INTER_LINEAR, 0.2),
                "C cub raw": iso_polys(alpha, meta, cv2.INTER_CUBIC, 0.0),
                "C cub dp.2": iso_polys(alpha, meta, cv2.INTER_CUBIC, 0.2),
            }
            v = A.register(truth, A.sample(arms["M"]))
            allarms = {**{k: arms[k] for k in ("M", "A0", "A", "B3")}, **cand}
            nd.update({k: nodes(p) for k, p in cand.items()})
            reg = {}
            for k, p in allarms.items():
                if not p:
                    continue
                reg[k] = A.apply(p, v)
                pr, rc = A.stats(truth.dist(A.sample(reg[k]))), A.stats(truth.recall(reg[k]))
                rows.append({"run": d.name, "arm": k, "p_med": pr["med"], "p_p90": pr["p90"],
                             "r_med": rc["med"], "r_p90": rc["p90"], "turn": A.turning(reg[k]),
                             "nodes": nd[k], "regions": len(reg[k])})
            A.panels(out, d.name + "-iso", {"M": reg["M"], "A0": reg["A0"], "A": reg["A"],
                                            "B1": reg["C lin dp.2"], "B2": reg["C cub dp.2"],
                                            "B3": reg.get("B3")}, back, win)
    for d in sorted(runs.glob("*-real")):
        meta = json.loads((d / "meta.json").read_text())
        src = cv2.imread(meta["src"], cv2.IMREAD_UNCHANGED)
        if src.ndim != 3 or src.shape[2] != 4:
            continue
        arms, nd = A.load_arms(d, meta)
        lin = iso_polys(src[..., 3], meta, cv2.INTER_LINEAR, 0.2)
        cub = iso_polys(src[..., 3], meta, cv2.INTER_CUBIC, 0.2)
        lab = np.load(d / "labels.npy")
        b = np.zeros(lab.shape, bool)
        b[:, 1:] |= lab[:, 1:] != lab[:, :-1]; b[1:, :] |= lab[1:, :] != lab[:-1, :]
        win = A.densest(b, meta["px_per_mm"], meta["cx"], meta["cy"], 14, 9)
        A.panels(out, d.name + "-iso", {"M": arms["M"], "A0": arms["A0"], "A": arms["A"],
                                        "B1": lin, "B2": cub, "B3": arms.get("B3")},
                 A.rgb_backdrop(d, meta, win, 40), win)
        for k, p in (("A0", arms["A0"]), ("A", arms["A"]), ("C lin dp.2", lin), ("C cub dp.2", cub)):
            rows.append({"run": d.name, "arm": k, "turn": A.turning(p), "nodes": nodes(p), "regions": len(p)})
    (out / "iso.json").write_text(json.dumps(rows, indent=1))
    cur = None
    for r in rows:
        if r["run"] != cur:
            cur = r["run"]
            print(f"\n{cur}\n  {'arm':12s} p_med  p_p90  r_med  r_p90   turn  nodes regions")
        if "p_med" in r:
            print(f"  {r['arm']:12s} {r['p_med']:.3f}  {r['p_p90']:.3f}  {r['r_med']:.3f}  {r['r_p90']:.3f} "
                  f"{r['turn']:6.1f} {r['nodes']:6d} {r['regions']:5d}")
        else:
            print(f"  {r['arm']:12s}     -      -      -      - {r['turn']:6.1f} {r['nodes']:6d} {r['regions']:5d}")


if __name__ == "__main__":
    main(*sys.argv[1:])
