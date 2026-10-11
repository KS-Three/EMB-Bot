"""lost_frac split for OFF and ON at ONE physical alignment and ONE artwork
scale, so the delta is the design and not the registration grid (bias 2/3).

usage: python matched.py DIR fixture[,fixture] [offarm] [onarm]
Reads DIR/<fx>-<arm>.design.json and DIR/<fx>-on.json (letters).
"""
import json
import os
import sys

sys.path.insert(0, os.getcwd())
import cv2  # noqa: E402
import numpy as np  # noqa: E402

import tools.artfidelity_self as afs  # noqa: E402
from tools.dropped_elements import (art_colour_field, sewn_colour_field,  # noqa: E402
                                    disagreement, _components, MIN_ELEMENT_MM2,
                                    RES)
from tools.thin_strokes import REAL_ART, ROOT  # noqa: E402
from digitizer_core.stitchviz import _frame  # noqa: E402

PAD_MM = 2.0
afs.SHIFT_STEP_MM, afs.SHIFT_MM = 0.1, 1.2


def frame_origin(design):
    st = design["stitches"]
    xs = [s["x"] for s in st if s.get("type") in ("stitch", "jump")]
    ys = [s["y"] for s in st if s.get("type") in ("stitch", "jump")]
    return min(xs), max(ys)


def canvas(ours, art):
    pad = int(2 * afs.SHIFT_MM * RES) + 4
    return (max(ours.shape[0], art.shape[0]) + pad,
            max(ours.shape[1], art.shape[1]) + pad)


def K_of(design, ours, art, H, W, dx, dy):
    """art px of design mm 0 (x) and of design-frame top (y): the physical
    alignment, independent of the design's own extents."""
    x0, y1 = frame_origin(design)
    oxo, oyo = (W - ours.shape[1]) // 2, (H - ours.shape[0]) // 2
    oxa, oya = (W - art.shape[1]) // 2 + dx, (H - art.shape[0]) // 2 + dy
    kx = (-x0 / 10.0 + PAD_MM) * RES + oxo - oxa
    ky = (y1 / 10.0 + PAD_MM) * RES + oyo - oya
    return kx, ky


def dxdy_for(design, ours, art, H, W, K):
    x0, y1 = frame_origin(design)
    oxo, oyo = (W - ours.shape[1]) // 2, (H - ours.shape[0]) // 2
    oxa = (-x0 / 10.0 + PAD_MM) * RES + oxo - K[0]
    oya = (y1 / 10.0 + PAD_MM) * RES + oyo - K[1]
    return (int(round(oxa - (W - art.shape[1]) // 2)),
            int(round(oya - (H - art.shape[0]) // 2)))


def label_map(design, H, W):
    st = design["stitches"]
    (h, w), to_px = _frame(st, RES, PAD_MM)
    lab = np.zeros((h, w), np.int32)
    shapes = [""]
    tw = max(2, int(round(0.4 * RES)))
    for r in design.get("runs", []):
        sid = r.get("shape") or ""
        if sid not in shapes:
            shapes.append(sid)
        k = shapes.index(sid)
        prev = None
        for i in range(r["i0"], r["i1"] + 1):
            s = st[i]
            if s.get("type") != "stitch":
                prev = None
                continue
            p = to_px(s)
            if prev is not None and prev != p:
                cv2.line(lab, prev, p, int(k), tw)
            prev = p
    c = np.zeros((H, W), np.int32)
    oy, ox = (H - h) // 2, (W - w) // 2
    c[oy:oy + h, ox:ox + w] = lab
    return c, shapes


def place(img, H, W, ddx, ddy, fill):
    c = np.full((H, W) + img.shape[2:], fill, img.dtype)
    oy = (H - img.shape[0]) // 2 + ddy
    ox = (W - img.shape[1]) // 2 + ddx
    y0, x0 = max(0, oy), max(0, ox)
    y1, x1 = min(H, oy + img.shape[0]), min(W, ox + img.shape[1])
    c[y0:y1, x0:x1] = img[y0 - oy:y1 - oy, x0 - ox:x1 - ox]
    return c


def analyse(image, design, width_mm, K=None, letters=()):
    ours = afs.stitch_coverage_field(design)
    art = afs.art_ink_field(image, width_mm)
    if K is None:
        _iou, O_f, _A, dxm, dym = afs.register(ours, art)
        H, W = O_f.shape
        dx, dy = int(round(dxm * RES)), int(round(dym * RES))
        K = K_of(design, ours, art, H, W, dx, dy)
    H, W = canvas(ours, art)
    # keep the design inside the canvas whatever shift K asks for
    H += 40
    W += 40
    dx, dy = dxdy_for(design, ours, art, H, W, K)
    O_f = afs._place(ours, H, W)
    art_rgb, art_ink = art_colour_field(image, width_mm)
    A_rgb = place(art_rgb, H, W, dx, dy, 255)
    A_ink = place(art_ink.astype(bool), H, W, dx, dy, False)
    S_rgb = place(sewn_colour_field(design), H, W, 0, 0, 255)
    A_show = np.where(A_ink[..., None], A_rgb, np.uint8(255))
    _de, wrong = disagreement(A_show, S_rgb)
    min_px = max(1, int(round(MIN_ELEMENT_MM2 * RES * RES)))
    lab_c, comps = _components(wrong, min_px)
    thread = O_f >= 0.5
    lab, shapes = label_map(design, H, W)
    _d, idx = cv2.distanceTransformWithLabels((lab == 0).astype(np.uint8),
                                              cv2.DIST_L2, 5,
                                              labelType=cv2.DIST_LABEL_PIXEL)
    ys, xs = np.nonzero(lab)
    seed = np.zeros(int(idx.max()) + 1, np.int32)
    seed[idx[ys, xs]] = lab[ys, xs]
    near = seed[idx]
    ink_mm2 = A_ink.sum() / RES ** 2
    tot = {"unsewn": 0.0, "wrong_colour": 0.0, "overshoot": 0.0}
    per = {}
    oya_ = (H - art.shape[0]) // 2 + dy
    rows = (np.arange(H) - oya_ - K[1]) / RES
    below = np.zeros((H, W), bool)
    YB = float(os.environ.get("BAND_Y", "1e9"))
    below[rows > YB, :] = True
    band = {"unsewn": 0.0, "wrong_colour": 0.0, "overshoot": 0.0}
    over_mask = np.zeros((H, W), bool)
    uns_mask = np.zeros((H, W), bool)
    for c in comps:
        sel = lab_c == c["label"]
        ink = bool(A_ink[sel].mean() > 0.5)
        cover = float(thread[sel].mean())
        kind = "overshoot" if not ink else ("wrong_colour" if cover >= 0.5 else "unsewn")
        mm2 = sel.sum() / RES ** 2
        tot[kind] += mm2
        band[kind] += (sel & below).sum() / RES ** 2
        if kind != 'overshoot':
            uns_mask |= sel
        if kind == "overshoot":
            over_mask |= sel
            # split a merged region by nearest shape, pixelwise
            v, n = np.unique(near[sel], return_counts=True)
            for k, m in zip(v, n):
                per.setdefault(shapes[int(k)], {}).setdefault(kind, 0.0)
                per[shapes[int(k)]][kind] += m / RES ** 2
        else:
            v, n = np.unique(near[sel], return_counts=True)
            sid = shapes[int(v[np.argmax(n)])]
            per.setdefault(sid, {}).setdefault(kind, 0.0)
            per[sid][kind] += mm2
    # spill depth: thread pixels outside the ink, by distance from the ink
    dist_out = cv2.distanceTransform((~A_ink).astype(np.uint8), cv2.DIST_L2, 5) / RES
    spill = thread & ~A_ink
    deep = spill & (dist_out > 0.5)
    for name, m in (("spill", spill), ("spill_gt_0.5mm", deep), ("bare", A_ink & ~thread)):
        v, n = np.unique(near[m], return_counts=True)
        for k, cnt in zip(v, n):
            per.setdefault(shapes[int(k)], {})[name] = cnt / RES ** 2
    out = {"K": K, "dx": dx, "dy": dy, "ink_mm2": round(ink_mm2, 1),
           "lost_frac": round(sum(tot.values()) / ink_mm2, 4),
           **{k + "_frac": round(v / ink_mm2, 4) for k, v in tot.items()},
           **{k + "_mm2": round(v, 1) for k, v in tot.items()},
           "spill_mm2": round(spill.sum() / RES ** 2, 1),
           "spill_gt_0.5mm_mm2": round(deep.sum() / RES ** 2, 1),
           "bare_mm2": round((A_ink & ~thread).sum() / RES ** 2, 1),
           **{"band_" + k + "_mm2": round(v, 1) for k, v in band.items()},
           "band_bare_mm2": round((A_ink & ~thread & below).sum() / RES ** 2, 1)}
    let = set(letters)
    out["letters_overshoot_mm2"] = round(sum(v.get("overshoot", 0) for k, v in per.items() if k in let), 1)
    out["letters_unsewn_mm2"] = round(sum(v.get("unsewn", 0) for k, v in per.items() if k in let), 1)
    M = 30
    oy = (H - art.shape[0]) // 2 + dy - M
    ox = (W - art.shape[1]) // 2 + dx - M
    crop = lambda z: z[oy:oy + art.shape[0] + 2 * M, ox:ox + art.shape[1] + 2 * M]
    return out, per, (crop(A_show), crop(S_rgb), crop(over_mask), crop(uns_mask), crop(A_ink), crop(thread), crop(lab), shapes, dx, dy)


def main():
    d = sys.argv[1]
    fixtures = sys.argv[2].split(",")
    off_arm = sys.argv[3] if len(sys.argv) > 3 else "off"
    on_arm = sys.argv[4] if len(sys.argv) > 4 else "on"
    allres = {}
    for fx in fixtures:
        rel, width, _g = REAL_ART[fx]
        image = ROOT / "testdata" / rel
        A = json.load(open(f"{d}/{fx}-{off_arm}.design.json"))
        B = json.load(open(f"{d}/{fx}-{on_arm}.design.json"))
        letters = list(json.load(open(f"{d}/{fx}-on.json"))["letters"])
        ra, pa, va = analyse(image, A, width, None, letters)
        rb, pb, vb = analyse(image, B, width, ra["K"], letters)
        rb_own, _pb, _vb = analyse(image, B, width, None, letters)
        print(fx, "OFF", json.dumps(ra))
        print(fx, "ON ", json.dumps(rb))
        print(fx, "ON@own", json.dumps(rb_own))
        allres[fx] = {"off": ra, "on": rb, "on_own": rb_own, "per_off": pa, "per_on": pb}
        np.savez_compressed(f"{d}/{fx}-{off_arm}-{on_arm}-masks.npz",
                            over_a=va[2], over_b=vb[2], uns_a=va[3], uns_b=vb[3], ink_a=va[4], ink_b=vb[4],
                            thr_a=va[5], thr_b=vb[5], show=va[0], sewn_a=va[1], sewn_b=vb[1])
        ks = sorted(set(pa) | set(pb), key=lambda k: -(pb.get(k, {}).get("overshoot", 0) - pa.get(k, {}).get("overshoot", 0)))
        for k in ks[:10]:
            a, b = pa.get(k, {}), pb.get(k, {})
            print(f"   {k:14s} L={k in letters!s:5s} over {a.get('overshoot',0):5.1f}->{b.get('overshoot',0):5.1f}"
                  f"  unsewn {a.get('unsewn',0):4.1f}->{b.get('unsewn',0):4.1f}"
                  f"  spill {a.get('spill',0):5.1f}->{b.get('spill',0):5.1f}"
                  f"  deep {a.get('spill_gt_0.5mm',0):5.1f}->{b.get('spill_gt_0.5mm',0):5.1f}"
                  f"  bare {a.get('bare',0):4.1f}->{b.get('bare',0):4.1f}")
    json.dump(allres, open(f"{d}/matched-{off_arm}-{on_arm}.json", "w"), indent=1)


if __name__ == "__main__":
    main()
