"""Rule-12 ring detector, on top of rule7's reader (copied here as reader.py, now returning ctx).

For every piece on a ground (reader row), look for a THIN band of thread hugging its edge:
  * another block k (sewn after the piece's host ground; k != piece block) whose RAW thread
    (not opened: a run-stitch line must survive) covers >= RING_COV of the piece's contour within
    NEAR_MM outside the footprint, while covering <= FAR_MAX of a band FAR_MM out (so it is a ring,
    not a neighbouring fill the piece sits in);
  * in the piece's own block: a satin edge ring, i.e. pairs of consecutive antiparallel stitches
    0.5-2.2 mm long whose both ends lie within 2.4 mm of the edge, running across the edge
    (|cos(stitch, edge normal)| >= 0.7), covering >= RING_COV of the contour. Only judged on pieces
    >= OWN_MIN_W wide (a narrow satin column IS such stitches all through).
Detector constants are about geometry, not contrast; reported values let a reader re-cut them.
"""
from __future__ import annotations
import math
import numpy as np
import cv2
from reader import PPM, disk

NEAR_MM = 0.7      # ring thread must lie within this of the footprint edge, outside it
FAR_IN, FAR_OUT = 1.6, 2.4
RING_COV = 0.6
FAR_MAX = 0.3
OWN_MIN_W = 4.5
OWN_LEN = (0.5, 2.2)
OWN_DEPTH = 2.4
PAD = int(3.5 * PPM)


def _win(ctx, r):
    xa, ya, xb, yb = r["bbox_px"]
    W, H = ctx["W"], ctx["H"]
    Xa, Ya, Xb, Yb = max(0, xa - PAD), max(0, ya - PAD), min(W, xb + PAD), min(H, yb + PAD)
    P = np.zeros((Yb - Ya, Xb - Xa), np.uint8)
    P[ya - Ya:yb - Ya, xa - Xa:xb - Xa] = r["_P"]
    return (Xa, Ya, Xb, Yb), P


def filled(P):
    """outer silhouette: holes (counters, a ring's middle) filled, so only the OUTER edge is judged"""
    cnts, _ = cv2.findContours(P, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    F = np.zeros_like(P)
    cv2.drawContours(F, cnts, -1, 1, -1)
    return F


def annotate(rows, ctx):
    rasters, segl = ctx["rasters"], ctx["segl"]
    gid = ctx["gid"]
    x0, y0 = ctx["x0"], ctx["y0"]
    near = disk(2 * NEAR_MM)
    for r in rows:
        (Xa, Ya, Xb, Yb), P0 = _win(ctx, r)
        P = filled(P0)
        host_block = max(gid[h]["block"] for h in r["_host_ids"])
        cont = P - cv2.erode(P, np.ones((3, 3), np.uint8))
        nC = max(1, int(cont.sum()))
        Z1 = cv2.dilate(P, near) & (1 - P)
        Z2 = cv2.dilate(P, disk(2 * FAR_OUT)) & (1 - cv2.dilate(P, disk(2 * FAR_IN)))
        nZ2 = max(1, int(Z2.sum()))
        cands = []
        for k, R in enumerate(rasters):
            if k == r["block"] or k < host_block:
                continue
            Rw = R[Ya:Yb, Xa:Xb]
            hit = Rw & Z1
            if not hit.any():
                continue
            cov = float((cv2.dilate(hit, near) & cont).sum()) / nC
            far = float((Rw & Z2).sum()) / nZ2
            # ring width outside the footprint: thread in Z1 band depth (distance from P)
            cands.append(dict(block=k, cov=round(cov, 3), far=round(far, 3),
                              sewn="after" if k > r["block"] else "before",
                              is_host=k == host_block))
        rings = [c for c in cands if c["cov"] >= RING_COV and c["far"] <= FAR_MAX and not c["is_host"]]
        r["ring_cands"] = sorted(cands, key=lambda c: -c["cov"])[:4]
        r["rings"] = rings
        # own-block satin edge ring
        own_cov = None
        if r["width_mm"] >= OWN_MIN_W:
            dt = cv2.distanceTransform(P, cv2.DIST_L2, 5) / PPM
            gy, gx = np.gradient(dt)
            sg = segl[r["block"]]
            M = np.zeros_like(P)

            def pix(x, y):
                return int(round((x - x0) * PPM)) - Xa, int(round((y - y0) * PPM)) - Ya

            def ok(s):
                if s is None or not (OWN_LEN[0] <= s[4] <= OWN_LEN[1]):
                    return None
                a, b = pix(s[0], s[1]), pix(s[2], s[3])
                for (u, v) in (a, b):
                    if not (0 <= u < P.shape[1] and 0 <= v < P.shape[0]) or P[v, u] == 0 \
                            or dt[v, u] > OWN_DEPTH:
                        return None
                mu, mv = (a[0] + b[0]) // 2, (a[1] + b[1]) // 2
                n = np.array([gx[mv, mu], gy[mv, mu]])
                nn = np.linalg.norm(n)
                if nn < 1e-6:
                    return None
                d = np.array([s[2] - s[0], s[3] - s[1]]) / s[4]
                if abs(float(d @ (n / nn))) < 0.7:
                    return None
                return a, b, d
            prev = None
            for s in sg:
                cur = ok(s)
                if cur is not None and prev is not None and float(cur[2] @ prev[2]) < -0.7:
                    cv2.line(M, prev[0], prev[1], 1, 2)
                    cv2.line(M, cur[0], cur[1], 1, 2)
                prev = cur
            own_cov = round(float((cv2.dilate(M, disk(2 * 0.6)) & cont).sum()) / nC, 3)
        r["own_satin_edge_cov"] = own_cov
        r["own_satin_edge_ring"] = bool(own_cov is not None and own_cov >= RING_COV)
    # pieces that are themselves somebody's ring
    for r in rows:
        r["is_ring_of"] = None
    for r in rows:
        if not r["rings"]:
            continue
        (Xa, Ya, Xb, Yb), P = _win(ctx, r)
        zone = cv2.dilate(P, disk(2 * FAR_IN))
        for q in rows:
            if q is r or q["block"] not in {c["block"] for c in r["rings"]}:
                continue
            (qa, qb_, qc, qd), Q = _win(ctx, q)
            # Q into r's window
            ox, oy = qa - Xa, qb_ - Ya
            Qr = np.zeros_like(P)
            ys, xs = np.nonzero(Q)
            ys2, xs2 = ys + oy, xs + ox
            ok = (ys2 >= 0) & (ys2 < P.shape[0]) & (xs2 >= 0) & (xs2 < P.shape[1])
            if ok.sum() < 0.8 * len(ys):
                continue
            Qr[ys2[ok], xs2[ok]] = 1
            if (Qr & zone).sum() >= 0.8 * Qr.sum():
                q["is_ring_of"] = (r["block"], r["bbox_px"])
    return rows
