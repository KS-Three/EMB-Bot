"""Score every arm of every run against its truth run, and render panels.

usage: analyze.py RUNS_DIR OUT_DIR
Arms: M  = the mask's own pixel-exact outline (vtracer mode=none) - the floor
      A0 = stage 4, plain Douglas-Peucker (subpixel off, curve refinement off)
      A  = stage 4 as shipped
      B1 = vtracer defaults on the work-grid mask
      B2 = vtracer corner_threshold 120 on the work-grid mask
      B3 = vtracer defaults on the mask brought back to the source pixel grid
"""
import json
import re
import sys
from pathlib import Path

import cv2
import numpy as np
import shapely
from scipy import ndimage, optimize
from shapely import wkt
from shapely.geometry import Polygon

MIN_AREA, RUN_AREA, RUN_LOOP = 1.5 ** 2 * 0.25, 0.16, 2.2
STEP_MM = 0.05
ARMS = ["M", "A0", "A", "B1", "B2", "B3"]
PATH_RE = re.compile(r'<path d="([^"]*)"[^>]*?transform="translate\(([-\d.e]+),([-\d.e]+)\)"')
TOK_RE = re.compile(r"[MLCZ]|-?\d*\.?\d+(?:e-?\d+)?")
T = np.linspace(0, 1, 9)[1:, None]


def svg_rings(path):
    """-> (rings in svg px, bezier/line segment count)."""
    rings, nseg = [], 0
    for d, tx, ty in PATH_RE.findall(Path(path).read_text()):
        off = np.array([float(tx), float(ty)])
        toks = TOK_RE.findall(d)
        i, cur, pts = 0, None, []
        while i < len(toks):
            c = toks[i]
            if c == "M":
                if len(pts) >= 3:
                    rings.append(np.array(pts) + off)
                cur = np.array([float(toks[i + 1]), float(toks[i + 2])]); pts = [cur]; i += 3
            elif c == "L":
                cur = np.array([float(toks[i + 1]), float(toks[i + 2])]); pts.append(cur); i += 3; nseg += 1
            elif c == "C":
                p1, p2, p3 = (np.array([float(toks[i + k]), float(toks[i + k + 1])]) for k in (1, 3, 5))
                b = ((1 - T) ** 3 * cur + 3 * (1 - T) ** 2 * T * p1 + 3 * (1 - T) * T ** 2 * p2 + T ** 3 * p3)
                pts.extend(b); cur = p3; i += 7; nseg += 1
            elif c == "Z":
                i += 1
            else:
                raise ValueError(f"unexpected token {c!r} in {path}")
        if len(pts) >= 3:
            rings.append(np.array(pts) + off)
    return rings, nseg


def fold(rings):
    """Even-odd fold of rings into one geometry."""
    g = Polygon()
    for r in sorted(rings, key=lambda r: -abs(Polygon(r).area)):
        p = Polygon(r)
        if not p.is_valid:
            p = p.buffer(0)
        g = g.symmetric_difference(p)
    return g


def parts(g):
    if g.is_empty:
        return []
    if g.geom_type == "Polygon":
        return [g]
    return [p for x in getattr(g, "geoms", []) for p in parts(x)]


def keep(p):
    return p.area >= MIN_AREA or (p.area >= RUN_AREA and p.exterior.length >= RUN_LOOP)


def kept_masks(d, meta, shipped):
    """Indices of the masks stage 4 kept: those whose pixels the shipped
    regions cover. Every vtracer arm traces exactly this set."""
    lab = np.load(d / "labels.npy")
    cov = np.zeros(lab.shape, np.uint8)
    ppm, cx, cy = meta["px_per_mm"], meta["cx"], meta["cy"]
    for p in shipped:
        ext = np.round((np.asarray(p.exterior.coords) * ppm + [cx, cy]) * 16).astype(np.int32)
        cv2.fillPoly(cov, [ext.reshape(-1, 1, 2)], 1, cv2.LINE_8, 4)
    n = lab.max() + 1
    tot = np.bincount(lab.ravel(), minlength=n).astype(float)
    hit = np.bincount(lab.ravel(), weights=cov.ravel(), minlength=n)
    return {i - 1 for i in range(1, n) if tot[i] and hit[i] / tot[i] >= 0.5}


def vt_arm(d, meta, variant, keepset):
    sub = "masks_native" if variant == "b3" else "masks"
    if variant == "b3":
        nat = json.loads((d / "native.json").read_text())
        if nat["skip"]:
            return None, 0
        items, sx, sy = nat["masks"], nat["sx"], nat["sy"]
    else:
        items, sx, sy = meta["masks"], 1.0, 1.0
    pad, cx, cy, ppm = meta["pad"], meta["cx"], meta["cy"], meta["px_per_mm"]
    polys, nseg = [], 0
    for m in items:
        f = d / sub / f"m{m['i']:04d}.{variant}.svg"
        if m["i"] not in keepset or not f.exists():
            continue
        rings, n = svg_rings(f)
        mm = []
        for r in rings:
            x = ((r[:, 0] - pad + m["x0"]) * sx - 0.5 - cx) / ppm
            y = ((r[:, 1] - pad + m["y0"]) * sy - 0.5 - cy) / ppm
            mm.append(np.column_stack([x, y]))
        kept = [p for p in parts(fold(mm)) if p.area >= 0.02]
        if kept:
            polys.extend(kept); nseg += n
    return polys, nseg


def json_arm(path):
    polys = [wkt.loads(r["wkt"]) for r in json.loads(Path(path).read_text())]
    return polys, sum(len(p.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in p.interiors) for p in polys)


def rings_of(polys):
    for p in polys:
        yield np.asarray(p.exterior.coords)
        for h in p.interiors:
            yield np.asarray(h.coords)


def sample(polys):
    out = []
    for r in rings_of(polys):
        seg = np.diff(r, axis=0)
        ln = np.hypot(seg[:, 0], seg[:, 1])
        for a, s, l in zip(r[:-1], seg, ln):
            n = max(1, int(np.ceil(l / STEP_MM)))
            out.append(a + s * (np.arange(n)[:, None] / n))
    return np.vstack(out) if out else np.zeros((0, 2))


def turning(polys):
    """Mean absolute turning, degrees per mm of boundary."""
    tot, length = 0.0, 0.0
    for r in rings_of(polys):
        seg = np.diff(r, axis=0)
        ln = np.hypot(seg[:, 0], seg[:, 1])
        ok = ln > 1e-9
        seg, ln = seg[ok], ln[ok]
        if len(seg) < 3:
            continue
        ang = np.arctan2(seg[:, 1], seg[:, 0])
        d = np.diff(np.concatenate([ang, ang[:1]]))
        d = (d + np.pi) % (2 * np.pi) - np.pi
        tot += np.abs(d).sum(); length += ln.sum()
    return np.degrees(tot) / length if length else 0.0


class Truth:
    """2x-supersampled boundary map of the truth run's label image."""

    def __init__(self, d):
        self.meta = json.loads((d / "meta.json").read_text())
        lab = np.load(d / "labels.npy")
        lab2 = np.repeat(np.repeat(lab, 2, 0), 2, 1)
        b = np.zeros(lab2.shape, bool)
        dx = lab2[:, 1:] != lab2[:, :-1]
        dy = lab2[1:, :] != lab2[:-1, :]
        b[:, 1:] |= dx; b[:, :-1] |= dx; b[1:, :] |= dy; b[:-1, :] |= dy
        self.b = b
        self.lab = lab
        self.edt = cv2.distanceTransform((~b).astype(np.uint8), cv2.DIST_L2, 5)
        self.ppm = self.meta["px_per_mm"]
        ys, xs = np.nonzero(b)
        rng = np.random.default_rng(0)
        if len(ys) > 200_000:
            sel = rng.choice(len(ys), 200_000, replace=False); ys, xs = ys[sel], xs[sel]
        self.bpts = (ys, xs)

    def to_px2(self, mm):
        """mm -> 2x-grid centre coordinates (x, y)."""
        m = self.meta
        return np.column_stack([2 * (mm[:, 0] * self.ppm + m["cx"]) + 0.5,
                                2 * (mm[:, 1] * self.ppm + m["cy"]) + 0.5])

    def dist(self, mm):
        """Distance in mm from each point to the truth boundary."""
        p = self.to_px2(mm)
        return ndimage.map_coordinates(self.edt, [p[:, 1], p[:, 0]], order=1, mode="nearest") / (2 * self.ppm)

    def recall(self, polys):
        img = np.full(self.b.shape, 255, np.uint8)
        for r in rings_of(polys):
            q = np.round(self.to_px2(r) * 16).astype(np.int32)
            cv2.polylines(img, [q.reshape(-1, 1, 2)], True, 0, 1, cv2.LINE_8, 4)
        e = cv2.distanceTransform(img, cv2.DIST_L2, 5)
        return e[self.bpts] / (2 * self.ppm)


def register(truth, pts):
    """Similarity (scale + shift) taking the test run's mm frame onto the
    truth's, fitted on the mask's own outline so no arm is favoured."""
    rng = np.random.default_rng(1)
    if len(pts) > 30_000:
        pts = pts[rng.choice(len(pts), 30_000, replace=False)]

    def cost(v):
        return float(np.minimum(truth.dist(pts * v[0] + v[1:]), 0.5).mean())

    best = min(((cost(np.array([s, dx, dy])), s, dx, dy)
                for s in (0.98, 0.99, 1.0, 1.01, 1.02)
                for dx in np.arange(-0.6, 0.61, 0.15) for dy in np.arange(-0.6, 0.61, 0.15)))
    x0 = np.array(best[1:])
    simplex = np.array([x0, x0 + [0.004, 0, 0], x0 + [0, 0.06, 0], x0 + [0, 0, 0.06]])
    r = optimize.minimize(cost, x0, method="Nelder-Mead",
                          options={"xatol": 1e-4, "fatol": 1e-7, "maxiter": 800,
                                   "initial_simplex": simplex})
    return r.x


def apply(polys, v):
    return [shapely.transform(p, lambda c: c * v[0] + v[1:]) for p in polys]


def stats(d):
    return {"med": float(np.median(d)), "p90": float(np.percentile(d, 90)),
            "in01": float((d <= 0.10).mean())}


COL = {"M": (150, 150, 150), "A0": (0, 140, 255), "A": (0, 0, 220),
       "B1": (220, 120, 0), "B2": (200, 0, 160), "B3": (0, 150, 0)}
NAMES = {"M": "mask outline (floor)", "A0": "A0 plain DP", "A": "A stage 4 shipped",
         "B1": "B1 vtracer default", "B2": "B2 vtracer smooth", "B3": "B3 vtracer source grid"}


def panels(out, name, arms, backdrop, win, scale=40):
    """backdrop(win, scale) -> BGR image of the window; arms in backdrop mm."""
    x0, y0, w, h = win
    tiles = []
    for a in ARMS:
        img = backdrop.copy()
        if arms.get(a):
            for r in rings_of(arms[a]):
                q = np.round((r - [x0, y0]) * scale * 16).astype(np.int32)
                cv2.polylines(img, [q.reshape(-1, 1, 2)], True, COL[a], 2, cv2.LINE_AA, 4)
            label = NAMES[a]
        else:
            label = NAMES[a] + " - n/a"
        cv2.rectangle(img, (0, 0), (img.shape[1], 26), (255, 255, 255), -1)
        cv2.putText(img, label, (8, 19), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 1, cv2.LINE_AA)
        tiles.append(cv2.copyMakeBorder(img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0)))
    grid = np.vstack([np.hstack(tiles[:3]), np.hstack(tiles[3:])])
    cv2.imwrite(str(out / f"{name}.png"), grid)


def densest(bmask, ppm, cx, cy, w_mm, h_mm):
    """Window (x0, y0, w, h) in mm with the most boundary in it."""
    kw, kh = int(w_mm * ppm), int(h_mm * ppm)
    kw, kh = min(kw, bmask.shape[1]), min(kh, bmask.shape[0])
    s = cv2.boxFilter(bmask.astype(np.float32), -1, (kw, kh), normalize=False,
                      borderType=cv2.BORDER_CONSTANT)
    s[:kh // 2] = 0; s[-(kh // 2):] = 0; s[:, :kw // 2] = 0; s[:, -(kw // 2):] = 0
    y, x = np.unravel_index(np.argmax(s), s.shape)
    return ((x - kw / 2 - cx) / ppm, (y - kh / 2 - cy) / ppm, kw / ppm, kh / ppm)


def label_backdrop(lab, ppm, cx, cy, win, scale):
    x0, y0, w, h = win
    W, H = int(round(w * scale)), int(round(h * scale))
    M = np.float32([[ppm / scale, 0, x0 * ppm + cx], [0, ppm / scale, y0 * ppm + cy]])
    img = cv2.warpAffine((lab > 0).astype(np.uint8) * 255, M, (W, H),
                         flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP, borderValue=0)
    g = (255 - img // 5).astype(np.uint8)
    return cv2.cvtColor(g, cv2.COLOR_GRAY2BGR)


def rgb_backdrop(d, meta, win, scale):
    x0, y0, w, h = win
    rgb = cv2.imread(str(d / "prep_rgb.png"))
    ppm = meta["px_per_mm"]
    M = np.float32([[ppm / scale, 0, x0 * ppm + meta["cx"]], [0, ppm / scale, y0 * ppm + meta["cy"]]])
    img = cv2.warpAffine(rgb, M, (int(round(w * scale)), int(round(h * scale))),
                         flags=cv2.INTER_NEAREST | cv2.WARP_INVERSE_MAP, borderValue=(255, 255, 255))
    return cv2.addWeighted(img, 0.45, np.full_like(img, 255), 0.55, 0)


def load_arms(d, meta):
    arms, nodes = {}, {}
    arms["A0"], nodes["A0"] = json_arm(d / "arm_plain.json")
    arms["A"], nodes["A"] = json_arm(d / "arm_shipped.json")
    ks = kept_masks(d, meta, arms["A"])
    for a, v in (("M", "m"), ("B1", "b1"), ("B2", "b2"), ("B3", "b3")):
        arms[a], nodes[a] = vt_arm(d, meta, v, ks)
    return arms, nodes


def main(runs, out):
    runs, out = Path(runs), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for tdir in sorted(runs.glob("*-truth")):
        truth = Truth(tdir)
        fx, lane = tdir.name.split("-")[:2]
        tm = truth.meta
        win = densest(truth.b[::2, ::2], truth.ppm, tm["cx"], tm["cy"], 14, 9)
        back = label_backdrop(truth.lab, truth.ppm, tm["cx"], tm["cy"], win, 40)
        for d in sorted(runs.glob(f"{fx}-{lane}-r*"), key=lambda p: float(p.name.split("-r")[1])):
            meta = json.loads((d / "meta.json").read_text())
            arms, nodes = load_arms(d, meta)
            v = register(truth, sample(arms["M"]))
            reg = {a: (apply(p, v) if p else p) for a, p in arms.items()}
            for a in ARMS:
                if not reg.get(a):
                    continue
                pr, rc = stats(truth.dist(sample(reg[a]))), stats(truth.recall(reg[a]))
                rows.append({"fixture": fx, "lane": lane, "rung": float(d.name.split("-r")[1]),
                             "work_ppm": meta["px_per_mm"], "arm": a, "regions": len(reg[a]),
                             "nodes": nodes[a], "turn": turning(reg[a]),
                             "p_med": pr["med"], "p_p90": pr["p90"], "p_in01": pr["in01"],
                             "r_med": rc["med"], "r_p90": rc["p90"], "r_in01": rc["in01"],
                             "reg": [float(x) for x in v]})
            panels(out, d.name, reg, back, win)
            print(d.name, "registered s=%.4f dx=%.3f dy=%.3f" % tuple(v), flush=True)
    for d in sorted(runs.glob("*-real")):
        meta = json.loads((d / "meta.json").read_text())
        arms, nodes = load_arms(d, meta)
        lab = np.load(d / "labels.npy")
        b = np.zeros(lab.shape, bool)
        b[:, 1:] |= lab[:, 1:] != lab[:, :-1]; b[1:, :] |= lab[1:, :] != lab[:-1, :]
        win = densest(b, meta["px_per_mm"], meta["cx"], meta["cy"], 14, 9)
        panels(out, d.name, arms, rgb_backdrop(d, meta, win, 40), win)
        for a in ARMS:
            if arms.get(a):
                rows.append({"fixture": d.name.split("-")[0], "lane": meta["class"], "rung": meta["input_px_per_mm"],
                             "work_ppm": meta["px_per_mm"], "arm": a, "regions": len(arms[a]),
                             "nodes": nodes[a], "turn": turning(arms[a])})
        print(d.name, "rendered", flush=True)
    (out / "results.json").write_text(json.dumps(rows, indent=1))


if __name__ == "__main__":
    main(*sys.argv[1:])
