"""Rule-7 reader: does a later colour block sit ON an earlier tatami ground, or in a hole?

Input: a list of (x_mm, y_mm, kind) with kind in {"S","J","T","C"} (stitch, jump,
trim, colour change/stop). Conventions (pro-digitizer-rules 2026-10-21): needle-down
STITCH->STITCH segments of 6 mm or less, drawn 0.4 mm wide at 20 px/mm, each file in
its own frame; pieces opened by 0.55 mm so travel runs fall away.
"""
from __future__ import annotations
import math
import numpy as np
import cv2

PPM = 20.0
LINE_MM = 0.4
MAX_SEG = 6.0
OPEN_MM = 0.55
CORE_MM = 0.5          # erosion for the "core" under-cover (0.25 tongue + 0.2 half thread + margin)
BAND_MM = 0.5
GROUND_MIN_MM2 = 25.0
GROUND_TATAMI = 0.5
INSIDE_FRAC = 0.9
MIN_PIECE_MM2 = 0.5


def blocks_of(points):
    blocks, cur = [], []
    for p in points:
        if p[2] == "C":
            if cur:
                blocks.append(cur)
            cur = []
        else:
            cur.append(p)
    if cur:
        blocks.append(cur)
    return [b for b in blocks if sum(1 for q in b if q[2] == "S") > 0]


def segments(block):
    segs = []
    for a, b in zip(block, block[1:]):
        if a[2] == "S" and b[2] == "S":
            L = math.hypot(b[0] - a[0], b[1] - a[1])
            if L <= MAX_SEG:
                segs.append((a[0], a[1], b[0], b[1], L))
            else:
                segs.append(None)
        else:
            segs.append(None)
    return segs


def disk(mm):
    k = max(1, int(round(mm * PPM)))
    return cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))


def read(points, label=""):
    xs = [p[0] for p in points if p[2] == "S"]
    ys = [p[1] for p in points if p[2] == "S"]
    x0, y0 = min(xs) - 2, min(ys) - 2
    W = int((max(xs) - x0 + 2) * PPM) + 1
    H = int((max(ys) - y0 + 2) * PPM) + 1
    tw = max(1, int(round(LINE_MM * PPM)))

    def px(x, y):
        return int(round((x - x0) * PPM)), int(round((y - y0) * PPM))

    blocks = blocks_of(points)
    rasters, segl, stitch_pts = [], [], []
    for b in blocks:
        m = np.zeros((H, W), np.uint8)
        sg = segments(b)
        for s in sg:
            if s is None:
                continue
            cv2.line(m, px(s[0], s[1]), px(s[2], s[3]), 1, tw)
        rasters.append(m)
        segl.append(sg)
        stitch_pts.append(np.array([px(q[0], q[1]) for q in b if q[2] == "S"]))
    allthread = np.zeros((H, W), np.uint8)
    for m in rasters:
        allthread |= m
    opener = disk(OPEN_MM)

    # ---- grounds: opened components of a block whose segments are mostly tatami rows
    grounds = []  # (block index, comp mask, filled mask, thread-in-filled mask, density, tatami score)
    for bi, (m, sg) in enumerate(zip(rasters, segl)):
        op = cv2.morphologyEx(m, cv2.MORPH_OPEN, opener)
        n, lab, st, _ = cv2.connectedComponentsWithStats(op, 8)
        # segment midpoints -> component labels
        segs = []
        for k, s in enumerate(sg):
            if s is None:
                continue
            mx, my = px((s[0] + s[2]) / 2, (s[1] + s[3]) / 2)
            if 0 <= mx < W and 0 <= my < H:
                segs.append((k, s, lab[my, mx]))
        for c in range(1, n):
            area = st[c, 4] / PPM ** 2
            if area < GROUND_MIN_MM2:
                continue
            mine = [(k, s) for k, s, l in segs if l == c]
            byk = {k: s for k, s in mine}
            long_ = [(k, s) for k, s in mine if s[4] >= 1.0]
            if not long_:
                continue
            ang = np.array([math.atan2(s[3] - s[1], s[2] - s[0]) % math.pi for _, s in long_])
            wts = np.array([s[4] for _, s in long_])
            hist, edges = np.histogram(ang, bins=36, range=(0, math.pi), weights=wts)
            dom = (edges[np.argmax(hist)] + edges[np.argmax(hist) + 1]) / 2
            tat = 0.0
            for (k, s), a in zip(long_, ang):
                d = abs((a - dom + math.pi / 2) % math.pi - math.pi / 2)
                if d > math.radians(15):
                    continue
                cont = False
                for nb in (k - 1, k + 1):
                    t = byk.get(nb)
                    if t is None or t[4] < 1.0:
                        continue
                    cs = ((s[2] - s[0]) * (t[2] - t[0]) + (s[3] - s[1]) * (t[3] - t[1])) / (s[4] * t[4])
                    if cs > 0.9:
                        cont = True
                if cont:
                    tat += s[4]
            score = tat / wts.sum()
            comp = (lab == c).astype(np.uint8)
            cnts, _ = cv2.findContours(comp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
            filled = np.zeros_like(comp)
            cv2.drawContours(filled, cnts, -1, 1, -1)
            thr = m & filled
            npts = 0
            if len(stitch_pts[bi]):
                p = stitch_pts[bi]
                ok = (p[:, 0] >= 0) & (p[:, 0] < W) & (p[:, 1] >= 0) & (p[:, 1] < H)
                p = p[ok]
                npts = int(filled[p[:, 1], p[:, 0]].sum())
            dens = npts / max(1e-9, thr.sum() / PPM ** 2)
            grounds.append(dict(block=bi, comp=comp, filled=filled, thread=thr, density=dens,
                                tatami=score, area=area, is_ground=score >= GROUND_TATAMI))
    G = [g for g in grounds if g["is_ground"]]

    # ---- later pieces inside a ground's filled outline
    rows = []
    hole_masks = {}
    core_k = disk(2 * CORE_MM)
    band_k = disk(2 * BAND_MM)
    earlier = np.zeros((H, W), np.uint8)
    earliers = []
    for m in rasters:
        earliers.append(earlier.copy())
        earlier |= m
    for bi, m in enumerate(rasters):
        under = [g for g in G if g["block"] < bi]
        E = earliers[bi]
        if not under:
            continue
        op = cv2.morphologyEx(m, cv2.MORPH_OPEN, opener)
        n, lab, st, _ = cv2.connectedComponentsWithStats(op, 8)
        for c in range(1, n):
            a_px = st[c, 4]
            if a_px / PPM ** 2 < MIN_PIECE_MM2:
                continue
            x, y, w, h = st[c, 0], st[c, 1], st[c, 2], st[c, 3]
            pad = int(2 * PPM)
            ya, yb, xa, xb = max(0, y - pad), min(H, y + h + pad), max(0, x - pad), min(W, x + w + pad)
            P = (lab[ya:yb, xa:xb] == c).astype(np.uint8)
            hosts = [g for g in under if (g["filled"][ya:yb, xa:xb] & P).sum() >= INSIDE_FRAC * a_px]
            if not hosts:
                continue
            under_thr = np.zeros_like(P)
            for g in hosts:
                under_thr |= g["thread"][ya:yb, xa:xb]
            uc = float((under_thr & P).sum()) / a_px
            core = cv2.erode(P, core_k)
            core_uc = float((under_thr & core).sum()) / core.sum() if core.sum() else None
            Ew = E[ya:yb, xa:xb]
            uc_any = float((Ew & P).sum()) / a_px
            core_uc_any = float((Ew & core).sum()) / core.sum() if core.sum() else None
            # thread-width-free check: host needle penetrations in the core per mm2 / host density
            pen = None
            if core.sum():
                hp = 0
                for g in hosts:
                    p = stitch_pts[g["block"]]
                    ok = (p[:, 0] >= xa) & (p[:, 0] < xb) & (p[:, 1] >= ya) & (p[:, 1] < yb)
                    q = p[ok]
                    if len(q):
                        hp += int((core[q[:, 1] - ya, q[:, 0] - xa] & g["filled"][q[:, 1], q[:, 0]]).sum())
                dens = max(g["density"] for g in hosts)
                pen = hp / (core.sum() / PPM ** 2) / dens
            dt = cv2.distanceTransform(P, cv2.DIST_L2, 5)
            width = 2 * float(dt.max()) / PPM
            depth = dt / PPM
            prof = []
            for lo, hi in ((0, 0.5), (0.5, 1.0), (1.0, 2.0), (2.0, 1e9)):
                ring = (P > 0) & (depth > lo) & (depth <= hi)
                prof.append(None if ring.sum() < 4 else round(float((Ew[ring] > 0).mean()), 3))
            band = cv2.dilate(P, band_k) & (1 - cv2.erode(P, band_k))
            bare = band & (1 - allthread[ya:yb, xa:xb])
            band_bare = float(bare.sum()) / max(1, band.sum())
            band_out = cv2.dilate(P, band_k) & (1 - P)
            out_bare = float((band_out & (1 - allthread[ya:yb, xa:xb])).sum()) / max(1, band_out.sum())
            host = max(hosts, key=lambda g: g["block"])
            rows.append(dict(job=label, block=bi, host_block=host["block"], area_mm2=round(a_px / PPM ** 2, 3),
                             width_mm=round(width, 3), under_cover=round(uc, 4),
                             core_under_cover=None if core_uc is None else round(core_uc, 4),
                             under_cover_any=round(uc_any, 4),
                             core_under_cover_any=None if core_uc_any is None else round(core_uc_any, 4),
                             cover_by_depth_mm={"0-0.5": prof[0], "0.5-1": prof[1], "1-2": prof[2], ">2": prof[3]},
                             core_pen_ratio=None if pen is None else round(pen, 3),
                             band_bare=round(band_bare, 4), band_bare_outside=round(out_bare, 4),
                             bbox=(xa, ya, xb, yb), _hosts=[id(g) for g in hosts], _P=P))
    # ---- holes in each ground under knocked-out pieces -> cost of a solid ground
    gid = {id(g): g for g in G}
    cost = 0.0
    hole_area = 0.0
    seen = {}
    counted = np.zeros((H, W), np.uint8)   # each hole pixel priced once per job
    for r in rows:
        ko = (r["core_under_cover_any"] if r["core_under_cover_any"] is not None else r["under_cover_any"]) < 0.5
        r["knocked_out"] = bool(ko)
        if not ko:
            continue
        g = max((gid[h] for h in r["_hosts"]), key=lambda g: g["block"])   # the innermost (latest) ground
        key = (id(g), r["block"])
        if key not in seen:
            holes = (g["filled"] & (1 - earliers[r["block"]])).astype(np.uint8)
            seen[key] = cv2.connectedComponents(holes, connectivity=8)[1]
        lab = seen[key]
        xa, ya, xb, yb = r["bbox"]
        sub = lab[ya:yb, xa:xb][r["_P"] > 0]
        for hl in set(int(v) for v in np.unique(sub) if v):
            hm = (lab == hl) & (counted == 0)
            ar = hm.sum() / PPM ** 2
            counted[hm] = 1
            hole_area += ar
            cost += ar * g["density"]
    ctx = dict(rasters=rasters, segl=segl, x0=x0, y0=y0, W=W, H=H, G=G, gid=gid)
    for r in rows:
        r["_host_ids"] = r.pop("_hosts")
        r["bbox_px"] = [int(v) for v in r.pop("bbox")]
    nst = sum(1 for p in points if p[2] == "S")
    summary = dict(job=label, stitches=nst, blocks=len(blocks),
                   grounds=[dict(block=g["block"], area_mm2=round(g["area"], 1), tatami=round(g["tatami"], 2),
                                 density_st_per_mm2=round(g["density"], 2)) for g in G],
                   candidates_rejected=[dict(block=g["block"], area_mm2=round(g["area"], 1),
                                             tatami=round(g["tatami"], 2)) for g in grounds if not g["is_ground"]],
                   solid_cost_stitches=round(cost), solid_cost_pct=round(100 * cost / nst, 2),
                   hole_area_mm2=round(hole_area, 2))
    return rows, summary, ctx


def points_of(path):
    import pystitch
    pat = pystitch.read(str(path))
    m = pystitch.COMMAND_MASK
    pts = []
    for x, y, c in pat.stitches:
        c &= m
        k = {pystitch.STITCH: "S", pystitch.JUMP: "J", pystitch.TRIM: "T",
             pystitch.COLOR_CHANGE: "C", pystitch.STOP: "C"}.get(c)
        if k is None:
            continue
        pts.append((x / 10.0, y / 10.0, k))
    return pts


def read_file(path, label=""):
    import pystitch
    pat = pystitch.read(str(path))
    m = pystitch.COMMAND_MASK
    pts = []
    for x, y, c in pat.stitches:
        c &= m
        k = {pystitch.STITCH: "S", pystitch.JUMP: "J", pystitch.TRIM: "T",
             pystitch.COLOR_CHANGE: "C", pystitch.STOP: "C"}.get(c)
        if k is None:
            continue
        pts.append((x / 10.0, y / 10.0, k))
    return read(pts, label)
