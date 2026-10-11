"""Score vtracer 1.0.0a4 run on the source grid of the alpha-only cases
(coverage as grey: black ink on white), watershed and bw clustering, cutout.

usage: vt1_arm.py RUNS_DIR OUT_DIR
"""
import json
import re
import sys
from pathlib import Path

import numpy as np
from shapely.ops import unary_union

import analyze as A

P_RE = re.compile(r'<path d="([^"]*)"\s+fill="#([0-9A-Fa-f]{6})"')
T = A.T


def ink_polys(svg, meta):
    sx, sy = meta["upscale"]
    ppm, cx, cy = meta["px_per_mm"], meta["cx"], meta["cy"]
    geoms, nseg = [], 0
    for d, fill in P_RE.findall(Path(svg).read_text()):
        lum = 0.299 * int(fill[0:2], 16) + 0.587 * int(fill[2:4], 16) + 0.114 * int(fill[4:6], 16)
        if lum >= 128:
            continue
        toks = A.TOK_RE.findall(d)
        i, cur, pts, rings = 0, None, [], []
        while i < len(toks):
            c = toks[i]
            if c == "M":
                if len(pts) >= 3:
                    rings.append(np.array(pts))
                cur = np.array([float(toks[i + 1]), float(toks[i + 2])]); pts = [cur]; i += 3
            elif c == "L":
                cur = np.array([float(toks[i + 1]), float(toks[i + 2])]); pts.append(cur); i += 3; nseg += 1
            elif c == "C":
                p1, p2, p3 = (np.array([float(toks[i + k]), float(toks[i + k + 1])]) for k in (1, 3, 5))
                pts.extend((1 - T) ** 3 * cur + 3 * (1 - T) ** 2 * T * p1 + 3 * (1 - T) * T ** 2 * p2 + T ** 3 * p3)
                cur = p3; i += 7; nseg += 1
            else:
                i += 1
        if len(pts) >= 3:
            rings.append(np.array(pts))
        mm = [np.column_stack([(r[:, 0] * sx - 0.5 - cx) / ppm, (r[:, 1] * sy - 0.5 - cy) / ppm]) for r in rings]
        geoms.append(A.fold(mm))
    u = unary_union(geoms) if geoms else None
    return ([p for p in A.parts(u) if A.keep(p)] if u is not None else []), nseg


def main(runs, out):
    runs, out = Path(runs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    A.NAMES.update({"B1": "vtracer 1.0a4 watershed, source grid", "B2": "vtracer 1.0a4 bw, source grid",
                    "B3": "vtracer 0.6.15, source grid"})
    for tdir in sorted(runs.glob("*-truth")):
        truth = A.Truth(tdir)
        fx, lane = tdir.name.split("-")[:2]
        tm = truth.meta
        win = A.densest(truth.b[::2, ::2], truth.ppm, tm["cx"], tm["cy"], 14, 9)
        back = A.label_backdrop(truth.lab, truth.ppm, tm["cx"], tm["cy"], win, 40)
        for d in sorted(runs.glob(f"{fx}-{lane}-r*"), key=lambda p: float(p.name.split("-r")[1])):
            meta = json.loads((d / "meta.json").read_text())
            arms, _ = A.load_arms(d, meta)
            v = A.register(truth, A.sample(arms["M"]))
            print(f"\n{d.name}\n  {'arm':22s} p_med  p_p90  r_med  r_p90   turn  nodes regions")
            reg = {}
            for name, f in (("1.0a4 watershed", "vt1.wc.svg"), ("1.0a4 watershed stk", "vt1.w.svg"),
                            ("1.0a4 bw", "vt1.bw.svg")):
                if not (d / f).exists():
                    continue
                polys, n = ink_polys(d / f, meta)
                if not polys:
                    print(f"  {name:22s} no ink paths"); continue
                q = reg[name] = A.apply(polys, v)
                pr, rc = A.stats(truth.dist(A.sample(q))), A.stats(truth.recall(q))
                print(f"  {name:22s} {pr['med']:.3f}  {pr['p90']:.3f}  {rc['med']:.3f}  {rc['r_p90'] if 'r_p90' in rc else rc['p90']:.3f} "
                      f"{A.turning(q):6.1f} {n:6d} {len(q):5d}")
            A.panels(out, d.name + "-vt1", {"M": A.apply(arms["M"], v), "A0": A.apply(arms["A0"], v),
                                            "A": A.apply(arms["A"], v), "B1": reg.get("1.0a4 watershed"),
                                            "B2": reg.get("1.0a4 bw"),
                                            "B3": A.apply(arms["B3"], v) if arms.get("B3") else None}, back, win)


if __name__ == "__main__":
    main(*sys.argv[1:])
