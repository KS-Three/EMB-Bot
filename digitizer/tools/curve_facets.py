"""Curve facets: where a clean curve becomes chords, and what the pro sews there.

Built 2026-11-14 for Kent's 18 facet pins (`docs/curve-facets-2026-11-14.md`,
the (b) row of `docs/jag-source-2026-11-13.md`).

    # stage 4 ring by ring: raw trace -> Douglas-Peucker -> curve refinement ->
    # curve densify (`cfg.curve_chord_mm`), vertices / deviation / turn per stage
    python -m tools.curve_facets stages NAME ART WIDTH_MM GARMENT [KEY=JSON ...]
    # per pin, from `tools.jag_strips capture` pickles: the polygon's chords and
    # turns against the art's own curve, our edge needle points, the pro's
    python -m tools.curve_facets pins SPOTS.json CAPDIR [CAPDIR_ON] > out.json
    # art | OFF | ON | pro strips, the measured turn printed on each panel
    python -m tools.curve_facets sheets SPOTS.json CAP_OFF CAP_ON PINS.json OUTDIR

Instrument readings, not quality claims (ROADMAP gate 4). "Turn" is the
direction change at one vertex (polygon) or one needle point (stitches) in
degrees; a smooth arc of radius R sewn at end spacing s turns s/R at every
end, a faceted one turns 0, 0, 0, then the whole chord's angle at once.
"""
from __future__ import annotations

import json
import math
import os
import sys
import time
from pathlib import Path

import cv2
import numpy as np

DIGITIZER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(DIGITIZER))

CORNER_DEG = 45.0     # a turn past this is a corner, not a facet (stage4's own line)


def turns_deg(pts: np.ndarray, closed: bool) -> np.ndarray:
    """Signed turn at each vertex, degrees (open: interior vertices only)."""
    P = np.asarray(pts, dtype=np.float64)
    if closed:
        d = np.roll(P, -1, axis=0) - P
        a = np.arctan2(d[:, 1], d[:, 0])
        t = a - np.roll(a, 1)
    else:
        d = np.diff(P, axis=0)
        a = np.arctan2(d[:, 1], d[:, 0])
        t = np.diff(a)
    return np.degrees((t + np.pi) % (2 * np.pi) - np.pi)


# ------------------------------------------------------------------ stages
def ring_stats(raw: np.ndarray, ring: np.ndarray, px_mm: float, corner: float = CORNER_DEG) -> dict:
    import shapely
    from shapely.geometry import LinearRing
    lr = LinearRing(np.asarray(ring, dtype=np.float64))
    dev = shapely.distance(shapely.points(np.asarray(raw, dtype=np.float64)), lr)
    t = np.abs(turns_deg(ring, closed=True))
    curve = t[(t >= 2.0) & (t <= corner)]
    return {"n": int(len(ring)), "dev_mm": float(dev.max()) / px_mm,
            "facets": int(((t >= 5.0) & (t <= corner)).sum()),
            "turn_p95": float(np.percentile(curve, 95)) if len(curve) else 0.0,
            "turn_max": float(curve.max()) if len(curve) else 0.0}


def stages(name: str, art: str, width: float, garment: str, extra: dict) -> dict:
    """Stage 4 traced ring by ring: what Douglas-Peucker, the refinement and
    the densify each hand on (vertices, max deviation from the raw trace,
    facet vertices = turns of 5-45 deg, p95 turn on curves)."""
    from digitizer_core import PipelineConfig, stage4_vectorize as s4
    from digitizer_core.pipeline import build_generation, finish_generation
    from digitizer_service.app import _decode, _parse_config
    from tools import pro_pair

    req = pro_pair.request(width, garment, extra)
    cfg = PipelineConfig(**_parse_config(json.dumps(req)))
    rec: list = []
    ref0, den0 = s4._refine_curves, s4.densify_curves

    def ref(raw, simplified, *a, **k):
        out = ref0(raw, simplified, *a, **k)
        rec.append(["refine", np.array(raw), np.array(simplified), np.array(out)])
        return out

    def den(ring, raw, *a, **k):
        out = den0(ring, raw, *a, **k)
        rec.append(["densify", np.array(raw), np.array(ring), np.array(out)])
        return out

    s4._refine_curves, s4.densify_curves = ref, den
    try:
        data = open(art, "rb").read()
        t0 = time.time()
        gen = build_generation(_decode(data), cfg, exif_source=data)
        res = finish_generation(gen.fork(), cfg)
        el = time.time() - t0
    finally:
        s4._refine_curves, s4.densify_curves = ref0, den0
    ppm = gen.p.px_per_mm
    agg: dict = {}
    for kind, raw, a, b in rec:
        pairs = [(f"{kind}_in", a), (f"{kind}_out", b)]
        if kind == "refine":
            pairs.insert(0, ("raw", raw))
        for tag, ring in pairs:
            s = ring_stats(raw, ring, ppm)
            g = agg.setdefault(tag, {"rings": 0, "n": 0, "dev_mm": 0.0, "facets": 0, "turn_p95": []})
            g["rings"] += 1
            g["n"] += s["n"]
            g["dev_mm"] = max(g["dev_mm"], s["dev_mm"])
            g["facets"] += s["facets"]
            g["turn_p95"].append(s["turn_p95"])
    # the Column lane, letter by letter: its own simplify at max(0.12, W/16)
    # (`outline_cut._letter_columns`), then the densify `curve_chord_mm`
    # gives its pieces (here on the whole simplified letter, same rule)
    from digitizer_core import outline_cut as oc
    from digitizer_core.curve_densify import densify_polygon
    chord = float(extra.get("curve_chord_mm") or 0.4)
    for r in res.regions:
        if not r.meta.get("text_candidate") or r.polygon.geom_type != "Polygon":
            continue
        W = oc.stroke_width(r.polygon)
        tol = max(oc.SIMPLIFY_MM, W / 16.0)
        simp = r.polygon.simplify(tol, preserve_topology=True)
        if simp.is_empty or simp.geom_type != "Polygon":
            continue
        den = densify_polygon(simp, r.polygon.boundary, chord,
                              min(oc.CURVE_GUARD_SHARE * tol, oc.CURVE_GUARD_MAX_MM), oc.CURVE_CORNER_DEG)
        for tag, g in (("lane_in", r.polygon), ("lane_simplified", simp), ("lane_densified", den)):
            for ring in [g.exterior] + list(g.interiors):
                # deviation: the stage-4 ring this one came from, read both ways
                src = min([r.polygon.exterior] + list(r.polygon.interiors), key=lambda q: q.hausdorff_distance(ring))
                s = ring_stats(np.asarray(src.coords)[:-1], np.asarray(ring.coords)[:-1], 1.0,
                               corner=oc.CURVE_CORNER_DEG)
                s["dev_mm"] = max(s["dev_mm"], float(src.hausdorff_distance(ring)))
                a = agg.setdefault(tag, {"rings": 0, "n": 0, "dev_mm": 0.0, "facets": 0, "turn_p95": []})
                a["rings"] += 1
                a["n"] += s["n"]
                a["dev_mm"] = max(a["dev_mm"], s["dev_mm"])
                a["facets"] += s["facets"]
                a["turn_p95"].append(s["turn_p95"])
    for g in agg.values():
        g["turn_p95"] = float(np.median(g["turn_p95"])) if g["turn_p95"] else 0.0
    verts = sum(len(r.polygon.exterior.coords) + sum(len(h.coords) for h in r.polygon.interiors)
                for r in res.regions if r.polygon.geom_type == "Polygon")
    return {"name": name, "px_per_mm": ppm, "extra": extra, "elapsed_s": round(el, 1),
            "regions": len(res.regions), "region_vertices": int(verts), "stages": agg}


# -------------------------------------------------------------------- pins
def _art_curve_mm(ctx, x0, y0, w):
    """The art's own edge in the window: iso-contours of the source's ink
    (alpha if it has one, else luminance) at half way, in plan mm."""
    from skimage.measure import find_contours
    cap = ctx.cap
    if cap["native_rgb"] is not None:
        src, to, (sx, sy) = cap["native_rgb"], ctx.to_native, cap["upscale"]
    else:
        src, to, (sx, sy) = cap["rgb"], ctx.to_work, (1.0, 1.0)
    field = cv2.cvtColor(src, cv2.COLOR_RGB2GRAY).astype(np.float64)
    alpha = cap.get("native_alpha") if cap["native_rgb"] is not None else None
    if alpha is not None and float(alpha.min()) < 128.0:
        # ink on transparency: composite on the opposite of the ink's tone
        a = alpha.astype(np.float64) / 255.0
        bg = 255.0 if float(np.median(field[alpha >= 128])) < 128.0 else 0.0
        field = field * a + bg * (1.0 - a)
    ax0, ay0 = to(x0, y0)
    ax1, ay1 = to(x0 + w, y0 + w)
    c0, r0 = max(0, int(ax0) - 2), max(0, int(ay0) - 2)
    c1, r1 = min(field.shape[1], int(ax1) + 3), min(field.shape[0], int(ay1) + 3)
    sub = field[r0:r1, c0:c1]
    if (sub.size == 0 or sub.max() - sub.min() < 40) and cap["native_rgb"] is None:
        # one ink on transparency: the work raster is the ink's colour
        # everywhere and the shape lives in the background mask
        field = np.where(cap["bg_mask"], 255.0, 0.0)
        sub = field[r0:r1, c0:c1]
    if sub.size == 0 or sub.max() - sub.min() < 40:
        return []
    lvl = (float(sub.max()) + float(sub.min())) / 2.0
    out = []
    for c in find_contours(sub, lvl):
        nx, ny = c[:, 1] + c0, c[:, 0] + r0
        wx, wy = (nx + 0.5) * sx - 0.5, (ny + 0.5) * sy - 0.5
        out.append(np.column_stack([(wx - ctx.cx) / ctx.ppm, (wy - ctx.cy) / ctx.ppm]))
    return out


def _near_ring(regions, at, half):
    """The ring vertex run nearest `at`, within +/- `half` mm along the ring."""
    from shapely.geometry import LinearRing, Point
    from tools.jag_strips import rings
    best = None
    for poly, *_ in regions:
        for r in rings(poly):
            lr = LinearRing(r)
            d = lr.distance(Point(at))
            if best is None or d < best[0]:
                best = (d, np.array(r[:-1] if r[0] == r[-1] else r, dtype=np.float64), lr)
    if best is None:
        return None, None
    d, R, lr = best
    s0 = lr.project(Point(at))
    seg = np.r_[0.0, np.cumsum(np.hypot(*np.diff(np.vstack([R, R[:1]]), axis=0).T))]
    L = seg[-1]
    pos = seg[:-1]
    rel = (pos - s0 + L / 2) % L - L / 2
    keep = np.abs(rel) <= half
    order = np.argsort(rel[keep])
    return R[keep][order], d


def edge_points(paths, at, half, curve_pts=None):
    """Needle points of the thread colour nearest `at` that sit on its
    coverage EDGE inside the window, ordered along that edge (mm)."""
    win = []
    for rgb, pts in paths:
        a = np.asarray(pts, dtype=np.float64)
        m = (np.abs(a[:, 0] - at[0]) <= half + 0.5) & (np.abs(a[:, 1] - at[1]) <= half + 0.5)
        if m.any():
            win.append((rgb, a, m))
    if not win:
        return np.zeros((0, 2))
    # the colour whose needle points come nearest the pin
    best = min(win, key=lambda t: np.hypot(*(t[1][t[2]] - at).T).min())
    col = best[0]
    S = 40.0                                   # raster px per mm
    W = int(2 * (half + 1.0) * S)
    ox, oy = at[0] - half - 1.0, at[1] - half - 1.0
    img = np.zeros((W, W), np.uint8)
    pts_all = []
    for rgb, a, m in win:
        if rgb != col:
            continue
        q = np.round((a - [ox, oy]) * S * 4).astype(np.int32)
        for i in range(1, len(q)):
            cv2.line(img, tuple(q[i - 1]), tuple(q[i]), 255, max(1, int(0.4 * S)), cv2.LINE_8, shift=2)
        pts_all.append(a[m])
    P = np.vstack(pts_all)
    cs, _h = cv2.findContours(img, cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    if not cs:
        return np.zeros((0, 2))
    # the contour passing nearest the pin
    ctr = min(cs, key=lambda c: np.hypot(*(c.reshape(-1, 2) / S + [ox, oy] - at).T).min())
    C = ctr.reshape(-1, 2).astype(np.float64) / S + [ox, oy]
    from scipy.spatial import cKDTree
    tree = cKDTree(C)
    dist, idx = tree.query(P)
    on = (dist <= 0.30) & (np.abs(P[:, 0] - at[0]) <= half) & (np.abs(P[:, 1] - at[1]) <= half)
    if not on.any():
        return np.zeros((0, 2))
    E, k = P[on], idx[on]
    # order along the contour, unwrapped about the pin's own place on it
    k0 = tree.query(np.asarray(at))[1]
    n = len(C)
    rel = (k - k0 + n // 2) % n - n // 2
    E = E[np.argsort(rel)]
    # one point per place (a satin's two passes, underlay rows)
    keep = [0]
    for i in range(1, len(E)):
        if np.hypot(*(E[i] - E[keep[-1]])) >= 0.12:
            keep.append(i)
    return E[keep]


def curve_read(E: np.ndarray) -> dict:
    """Turn per point and spacing along an ordered edge; circle-fit radius and
    the RMS of the points off that circle (does the edge land ON a curve)."""
    if len(E) < 4:
        return {"n": int(len(E))}
    t = np.abs(turns_deg(E, closed=False))
    seg = np.hypot(*np.diff(E, axis=0).T)
    A = np.column_stack([2 * E[:, 0], 2 * E[:, 1], np.ones(len(E))])
    b = (E ** 2).sum(1)
    try:
        (cx, cy, c), *_ = np.linalg.lstsq(A, b, rcond=None)
        R = math.sqrt(max(c + cx * cx + cy * cy, 0.0))
        res = np.hypot(E[:, 0] - cx, E[:, 1] - cy) - R
        rms = float(np.sqrt((res ** 2).mean()))
    except np.linalg.LinAlgError:
        R, rms = float("nan"), float("nan")
    tc = t[t <= CORNER_DEG]
    sp = float(np.median(seg))
    return {"n": int(len(E)), "spacing_mm": sp, "radius_mm": float(R),
            "turn_fit": math.degrees(sp / R) if R and R == R and R > 0 else float("nan"),
            "turn_mean": float(tc.mean()) if len(tc) else 0.0,
            "turn_max": float(tc.max()) if len(tc) else 0.0,
            "turn_std": float(tc.std()) if len(tc) else 0.0, "off_circle_mm": rms}


def pin_read(spot: dict, capdir: str) -> dict:
    from shapely.geometry import LineString, Point
    from tools.jag_strips import _Ctx, design_runs_mm
    ctx = _Ctx(os.path.join(capdir, spot["cap"] + ".pkl"))
    pmx, pmy, pxy, it, pin, imgdir = ctx.plan_mm(spot)
    if spot.get("at_plan"):
        pmx, pmy = spot["at_plan"]
    half = 1.5
    at = (pmx, pmy)
    out = {"id": spot["id"], "at_plan": [pmx, pmy]}
    V, d = _near_ring(ctx.cap["regions"], at, 2 * half)
    if V is not None and len(V) >= 3:
        t = np.abs(turns_deg(V, closed=False))
        seg = np.hypot(*np.diff(V, axis=0).T)
        art = _art_curve_mm(ctx, pmx - half - 0.5, pmy - half - 0.5, 2 * half + 1.0)
        dev = None
        if art:
            lines = [LineString(a) for a in art if len(a) >= 2]
            samples = []
            for i in range(len(V) - 1):
                for f in np.linspace(0, 1, 8):
                    samples.append(V[i] * (1 - f) + V[i + 1] * f)
            dev = float(max(min(ln.distance(Point(p)) for ln in lines) for p in samples))
        tc = t[t <= CORNER_DEG]
        out["polygon"] = {"vertices": int(len(V)), "chord_mm": float(np.median(seg)),
                          "chord_max_mm": float(seg.max()),
                          "turn_max": float(tc.max()) if len(tc) else 0.0,
                          "turn_mean": float(tc.mean()) if len(tc) else 0.0,
                          "dev_from_art_mm": dev, "pin_to_ring_mm": float(d)}
    # ours from the PLAN's runs (float mm): the design file is quantized to
    # 0.1 mm, which at 0.4 mm spacing alone reads as 14-18 degree turns
    plan_paths = [(rgb, [tuple(p) for p in pts]) for blk in ctx.cap["runs"] for rgb, runs in blk
                  for pts, _kind, jump, _trim, _sid in runs if not jump and len(pts) >= 2]
    out["ours"] = curve_read(edge_points(plan_paths, at, half))
    if spot.get("pro"):
        from tools import pro_baseline as pb
        from tools.eye_pairs.filearm import design_from_file
        from tools.jag_strips import bbox_units, kit_offset
        key = ("pro", spot["pro"])
        if key not in _Ctx._cache:
            prod = design_from_file(pb.resolve(spot["pro"]))
            _Ctx._cache[key] = (prod, kit_offset(imgdir / it["pro"], prod) if it.get("pro") else (0, 0, 0))
        prod, (pox, poy, _r) = _Ctx._cache[key]
        qx0, _qx1, _qy0, qy1 = bbox_units(prod)
        qat = (pxy[0] + pox + qx0 / 10.0, pxy[1] + poy - qy1 / 10.0)
        out["pro"] = curve_read(edge_points(design_runs_mm(prod), qat, half))
    return out


def sheet(spot: dict, cap_off: str, cap_on: str, row_off: dict, row_on: dict) -> np.ndarray:
    """art | OFF | ON | pro at one pin, stage-4 polygon over each arm's
    thread, the measured turns printed on each panel."""
    from tools.jag_strips import (_Ctx, _hstack, design_runs_mm, draw_poly, label,
                                  panel_from_raster, pro_panel, rings, thread_panel)
    a = _Ctx(os.path.join(cap_off, spot["cap"] + ".pkl"))
    b = _Ctx(os.path.join(cap_on, spot["cap"] + ".pkl"))
    pmx, pmy, pxy, it, pin, imgdir = a.plan_mm(spot)
    half = spot.get("half_mm") or 3.0
    x0, y0, w = pmx - half, pmy - half, 2 * half
    art = label(panel_from_raster(a.work_bgr(), a.to_work, x0, y0, w, w), "art (work raster)")

    def arm(ctx, row, name):
        img = thread_panel(design_runs_mm(ctx.cap["design"]), x0, y0, w, w)
        for poly, *_ in ctx.cap["regions"]:
            bb = poly.bounds
            if bb[2] < x0 or bb[0] > x0 + w or bb[3] < y0 or bb[1] > y0 + w:
                continue
            for r in rings(poly):
                draw_poly(img, r, x0, y0, (255, 0, 255), 1, dots=True)
        p, o = row.get("polygon") or {}, row.get("ours") or {}
        txt = (f"{name}: poly turn {p.get('turn_max', float('nan')):.1f} deg chord "
               f"{p.get('chord_mm', float('nan')):.2f}mm | st turn max {o.get('turn_max', float('nan')):.1f}")
        return label(img, txt)

    panels = [art, arm(a, row_off, "OFF"), arm(b, row_on, "ON")]
    if spot.get("pro"):
        pp = pro_panel(spot, it, imgdir, pxy, half)
        q = row_off.get("pro") or {}
        panels.append(label(pp, f"pro: {q.get('spacing_mm', float('nan')):.2f}mm/end r "
                                f"{q.get('radius_mm', float('nan')):.1f} = {q.get('turn_fit', float('nan')):.1f} deg/end"))
    return _hstack(panels, f"{spot['id']}  pin@({pxy[0]:.2f},{pxy[1]:.2f})  win {w:.1f} mm  "
                           f"(magenta: stage-4 polygon and vertices)", pin.get("note") or "")


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd = argv.pop(0)
    if cmd == "stages":
        name, art, width, garment, *kv = argv
        extra = {k: json.loads(v) for k, v in (s.split("=", 1) for s in kv)}
        print(json.dumps(stages(name, art, float(width), garment, extra), indent=1))
        return 0
    if cmd == "pins":
        spots = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        rows = []
        for sp in spots:
            if not all(os.path.exists(os.path.join(d, sp["cap"] + ".pkl")) for d in argv[1:]):
                continue
            row = {"off": pin_read(sp, argv[1])}
            if len(argv) > 2:
                row["on"] = pin_read(sp, argv[2])
            rows.append(row)
        print(json.dumps(rows, indent=1))
        return 0
    if cmd == "sheets":
        spots = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
        rows = {r["off"]["id"]: r for r in json.loads(Path(argv[3]).read_text(encoding="utf-8"))}
        out = Path(argv[4])
        out.mkdir(parents=True, exist_ok=True)
        for sp in spots:
            r = rows.get(sp["id"])
            if r is None:
                continue
            cv2.imwrite(str(out / f"{sp['id']}.png"), sheet(sp, argv[1], argv[2], r["off"], r["on"]))
        return 0
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    raise SystemExit(main())
