"""Arm D: the coverage read, generalised to multi-colour art.

For each source pixel, estimate how much of it each palette colour covers
(two-colour unmix along the line between the two colours that are
confidently present nearby), then take each colour's half-level iso-contour
exactly as arm C does for alpha. The palette is the pipeline's own: the mean
source colour of each stage-2 layer, plus the background.

usage: unmix_arm.py RUNS_DIR OUT_DIR   (scores *-flat-r1.8, r3, r5)
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np

import analyze as A
from digitizer_core.threads import rgb_to_lab

K = 8
CONF_DE = 10.0
WIN = 5


def lab_of(rgb_u8):
    return rgb_to_lab(rgb_u8.reshape(-1, 3)).reshape(*rgb_u8.shape[:2], 3).astype(np.float32)


def palette(d, meta):
    """Lab palette: index 0 background, 1.. the layers."""
    lab = np.load(d / "labels.npy")
    prep = cv2.cvtColor(cv2.imread(str(d / "prep_rgb.png")), cv2.COLOR_BGR2RGB)
    layer_of = np.full(lab.max() + 1, -1, np.int32)
    for m in meta["masks"]:
        layer_of[m["i"] + 1] = m["layer"]
    lay = layer_of[lab]
    pl = lab_of(prep)
    k3 = np.ones((3, 3), np.uint8)
    out = []
    for L in [-1] + sorted(int(x) for x in np.unique(lay) if x >= 0):
        m = (lay == L).astype(np.uint8)
        core = cv2.erode(m, k3, iterations=2).astype(bool)
        sel = core if core.sum() >= 20 else m.astype(bool)
        out.append(np.median(pl[sel], axis=0))
    return np.array(out, np.float32)


def memberships(src, pal):
    """(n, h, w) coverage fields from the source image (BGR or BGRA)."""
    if src.ndim == 3 and src.shape[2] == 4:
        a = src[..., 3:4].astype(np.float32) / 255.0
        rgb = (src[..., 2::-1].astype(np.float32) * a + 255.0 * (1 - a)).round().astype(np.uint8)
    else:
        rgb = np.ascontiguousarray(src[..., 2::-1])
    L = lab_of(rgb)
    h, w = L.shape[:2]
    n = len(pal)
    d = np.linalg.norm(L[:, :, None, :] - pal[None, None], axis=-1)        # h, w, n
    near = d.argmin(-1)
    conf = d.min(-1) < CONF_DE
    # how many confident pixels of each colour sit in the window round each pixel
    cnt = np.stack([cv2.boxFilter(((near == k) & conf).astype(np.float32), -1, (WIN, WIN),
                                  normalize=False, borderType=cv2.BORDER_REPLICATE)
                    for k in range(n)], -1)
    order = np.argsort(-cnt, -1)
    a_idx, b_idx = order[..., 0], order[..., 1]
    has_b = np.take_along_axis(cnt, b_idx[..., None], -1)[..., 0] > 0
    has_a = np.take_along_axis(cnt, a_idx[..., None], -1)[..., 0] > 0
    ca, cb = pal[a_idx], pal[b_idx]
    ab = cb - ca
    t = ((L - ca) * ab).sum(-1) / np.maximum((ab * ab).sum(-1), 1e-6)
    t = np.where(has_b, np.clip(t, 0, 1), 0.0)
    S = np.zeros((n, h, w), np.float32)
    yy, xx = np.mgrid[:h, :w]
    S[a_idx, yy, xx] += 1 - t
    S[b_idx, yy, xx] += t
    # nothing confident nearby: fall back to the hard nearest colour
    lone = ~has_a
    S[:, lone] = 0
    S[near[lone], yy[lone], xx[lone]] = 1
    return S


def polys_from(S, meta, eps_mm):
    sx, sy = meta["upscale"]
    ppm, cx, cy = meta["px_per_mm"], meta["cx"], meta["cy"]
    h, w = S.shape[1:]
    out = []
    for k in range(1, len(S)):
        big = cv2.resize(S[k], (w * K, h * K), interpolation=cv2.INTER_LINEAR)
        cs, _ = cv2.findContours((big >= 0.5).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
        rings = []
        for c in cs:
            if len(c) < 8:
                continue
            p = c.reshape(-1, 2).astype(np.float64)
            xn, yn = (p[:, 0] + 0.5) / K - 0.5, (p[:, 1] + 0.5) / K - 0.5
            xw, yw = (xn + 0.5) * sx - 0.5, (yn + 0.5) * sy - 0.5
            mm = np.column_stack([(xw - cx) / ppm, (yw - cy) / ppm]).astype(np.float32)
            mm = cv2.approxPolyDP(mm.reshape(-1, 1, 2), eps_mm, True).reshape(-1, 2)
            if len(mm) >= 3:
                rings.append(mm.astype(np.float64))
        out.extend(p for p in A.parts(A.fold(rings)) if A.keep(p))
    return out


def main(runs, out):
    runs, out = Path(runs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    A.NAMES.update({"B1": "D unmix iso-contour, DP 0.2 mm", "B2": "D unmix iso-contour, DP 0.05 mm"})
    rows = []
    for tdir in sorted(runs.glob("*-flat-truth")):
        truth = A.Truth(tdir)
        fx = tdir.name.split("-")[0]
        tm = truth.meta
        win = A.densest(truth.b[::2, ::2], truth.ppm, tm["cx"], tm["cy"], 14, 9)
        back = A.label_backdrop(truth.lab, truth.ppm, tm["cx"], tm["cy"], win, 40)
        for rung in ("1.8", "3", "5"):
            d = runs / f"{fx}-flat-r{rung}"
            if not d.exists():
                continue
            meta = json.loads((d / "meta.json").read_text())
            arms, nd = A.load_arms(d, meta)
            pal = palette(d, meta)
            S = memberships(cv2.imread(str(d / "input.png"), cv2.IMREAD_UNCHANGED), pal)
            cand = {"D dp.2": polys_from(S, meta, 0.2), "D dp.05": polys_from(S, meta, 0.05)}
            v = A.register(truth, A.sample(arms["M"]))
            reg = {}
            for k, p in {**{a: arms[a] for a in ("M", "A0", "A", "B1")}, **cand}.items():
                reg[k] = A.apply(p, v)
                pr, rc = A.stats(truth.dist(A.sample(reg[k]))), A.stats(truth.recall(reg[k]))
                rows.append({"run": d.name, "arm": k, "p_med": pr["med"], "p_p90": pr["p90"],
                             "r_med": rc["med"], "r_p90": rc["p90"], "turn": A.turning(reg[k]),
                             "nodes": sum(len(r) - 1 for r in A.rings_of(reg[k])), "regions": len(reg[k]),
                             "palette": len(pal)})
            A.panels(out, d.name + "-unmix", {"M": reg["M"], "A0": reg["A0"], "A": reg["A"],
                                              "B1": reg["D dp.2"], "B2": reg["D dp.05"], "B3": None}, back, win)
    (out / "unmix.json").write_text(json.dumps(rows, indent=1))
    cur = None
    for r in rows:
        if r["run"] != cur:
            cur = r["run"]
            print(f"\n{cur}  (palette {r['palette']})\n  {'arm':10s} p_med  p_p90  r_med  r_p90   turn  nodes regions")
        print(f"  {r['arm']:10s} {r['p_med']:.3f}  {r['p_p90']:.3f}  {r['r_med']:.3f}  {r['r_p90']:.3f} "
              f"{r['turn']:6.1f} {r['nodes']:6d} {r['regions']:5d}")


if __name__ == "__main__":
    main(*sys.argv[1:])
