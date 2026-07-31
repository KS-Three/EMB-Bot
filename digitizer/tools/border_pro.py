#!/usr/bin/env python
"""Border forensics v3: how professionals sew outlines. MEASURED, not inferred.

WHAT WAS WRONG WITH v1 (all four are instrument bugs, not facts about thread):

  B1  over-fill never fired: it looked for an earlier run that
      study_pro.classify() labelled "fill". classify() tests `run` BEFORE
      `fill`, and `run` accepts rev_frac <= 0.25. A tatami with long rows
      reverses only at row ends, so its rev_frac is low and the `run` branch
      steals it. Hotel Fremont's badge fill: 7,067 stitches, rev_frac 0.104
      -> "run". Large fills — exactly the ones borders get sewn around — are
      systematically invisible to classify(). (study_pro.py:85-88)

  B2  it also required the fill to be in the SAME colour block as the border.
      A border over a fill is normally a CONTRASTING colour, i.e. a different
      block by construction. Measured: 0 of the edge borders found here share
      a block with the fill they cover.

  B3  "18/18 borders are closed loops" was a tautology: a satin was only
      RECORDED as a border if it was closed or over-fill, and over-fill never
      fired. Worse, the closure test (first point within 1.5 mm of last) mostly
      catches round LETTERS — the two "borders" v1 found in Fremont are the O
      of HOTEL and the O of FREMONT.

  B4  it measured width and density over a WHOLE RUN. Corpus runs chain
      `R.Z.S.R.Z.S...` with the needle down (playbook law 1), so whole-run
      metrics average column spans together with travel stitches.

v3 fixes all four. The unit of analysis is a COLUMN — one contiguous satin
phase inside a run, recovered with census_pro._phases — not a run. Area fills
are found from penetration geometry with classify() never consulted: rasterise
the run's short segments (travel dropped), morphologically close, and require
a max inscribed radius wider than any satin column can be. The region boundary
comes from cv2.findContours, so concave badges and counters survive.

OFFSET SIGN CONVENTION: INWARD POSITIVE. +0.50 mm means the border centreline
sits 0.50 mm INSIDE the fill edge, so the column body overlaps the fill.
Negative means the centreline sits outside the fill, over bare fabric.

Instrument accuracy, from tools/_validate_border.py on synthetic ground truth:
exact (err 0.00 mm) for fill row spacing <= 0.6 mm; -0.15 mm bias at 0.9-1.2 mm
row spacing. Corpus fills are 0.18-0.65 mm, i.e. inside the exact band.

Usage:
  python tools/border_pro.py <file.dst> [...] [--json out.json] [--render]
  python tools/border_pro.py --summary a.json [b.json ...]
"""
from __future__ import annotations

import json
import math
import sys
from collections import Counter
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from census_pro import _phases  # noqa: E402
from study_pro import classify, load_runs  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT_BASE = ROOT / "debug_out" / "border"

RES = 0.20              # mm per mask pixel
PAD = 3.0               # mm margin around a run's extent
CLOSE_MM = 0.8          # closing radius; bridges fill row gaps up to 1.6 mm
TRAVEL_MM = 6.0         # longer segments are travel, not area stitches
MIN_INSCRIBED_MM = 2.6  # half-thickness floor: wider than SATIN_MAX_WIDTH/2
MIN_FILL_AREA_MM2 = 60.0
MIN_COL_SEGS = 24       # a column shorter than this is not an outline
EDGE_NEAR_MM = 2.5      # a spine sample "tracks" the boundary within this
EDGE_FRAC = 0.60        # ... and this fraction of samples must track it
OBLIP = 40              # merge S.O.S into one column when the O gap is smaller


# ---------------------------------------------------------------- raster ---
def _frame(pts, res=RES, pad=PAD):
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    x0, y0 = min(xs) - pad, min(ys) - pad
    return x0, y0, int((max(xs) + pad - x0) / res) + 2, int((max(ys) + pad - y0) / res) + 2


def _mask(pts, frame, res=RES, close_mm=CLOSE_MM, travel_mm=TRAVEL_MM):
    x0, y0, w, h = frame
    img = np.zeros((h, w), np.uint8)
    for a, b in zip(pts, pts[1:]):
        if math.dist(a, b) <= travel_mm:
            cv2.line(img,
                     (int(round((a[0] - x0) / res)), int(round((a[1] - y0) / res))),
                     (int(round((b[0] - x0) / res)), int(round((b[1] - y0) / res))),
                     255, 1, cv2.LINE_8)
    k = max(1, int(round(close_mm / res)))
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * k + 1, 2 * k + 1))
    return cv2.morphologyEx(img, cv2.MORPH_CLOSE, ker)


def _polys(mask, frame, res=RES):
    from shapely.geometry import Polygon
    x0, y0, _w, _h = frame
    cnts, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return []
    hier = hier[0]
    rings = [[(float(p[0][0]) * res + x0, float(p[0][1]) * res + y0) for p in c]
             for c in cnts]
    out = []
    for i, (_nx, _pv, child, parent) in enumerate(hier):
        if parent != -1 or len(rings[i]) < 4:
            continue
        holes, j = [], child
        while j != -1:
            if len(rings[j]) >= 4:
                holes.append(rings[j])
            j = hier[j][0]
        try:
            p = Polygon(rings[i], holes)
            if not p.is_valid:
                p = p.buffer(0)
            if not p.is_empty and p.area > 1.0:
                out.append(p)
        except Exception:                                    # noqa: BLE001
            continue
    return out


def area_fills(runs):
    """Runs that lay down a 2-D area, from geometry alone. classify() unused."""
    out = []
    for i, r in enumerate(runs):
        pts = r["pts"]
        if len(pts) < 120:
            continue
        fr = _frame(pts)
        if fr[2] * fr[3] > 40_000_000:
            continue
        m = _mask(pts, fr)
        rad = float(cv2.distanceTransform(m, cv2.DIST_L2, 5).max()) * RES if m.any() else 0.0
        if rad < MIN_INSCRIBED_MM:
            continue
        area = float(m.sum()) / 255.0 * RES * RES
        if area < MIN_FILL_AREA_MM2:
            continue
        ps = sorted(_polys(m, fr), key=lambda p: -p.area)
        if ps:
            out.append({"idx": i, "block": r["block"], "polys": ps, "inscribed": rad,
                        "area": area, "n": len(pts), "cls": classify(pts)})
    return out


# --------------------------------------------------------------- columns ---
def columns(pts):
    """Contiguous satin phases inside one run -> [(start, end)] point indices.

    A run chains center walk, zigzag underlay and column with the needle down,
    so the column is a PHASE, not a run. `O` is census_pro's ambiguous label and
    is what a satin corner degrades into (the outer rail's advance grows and the
    reversal geometry stops looking like a zigzag), so a short O gap flanked by
    S on both sides is absorbed rather than treated as a column break.
    """
    ph = _phases(pts)
    toks = [t for t, _c, _m in ph]
    cnts = [c for _t, c, _m in ph]
    for i in range(1, len(toks) - 1):
        if toks[i] == "O" and toks[i - 1] == "S" and toks[i + 1] == "S" and cnts[i] <= OBLIP:
            toks[i] = "S"
    out, pos, start = [], 0, None
    for t, c in zip(toks, cnts):
        if t == "S":
            if start is None:
                start = pos
        else:
            if start is not None and pos - start >= MIN_COL_SEGS:
                out.append((start, pos))
            start = None
        pos += c
    if start is not None and pos - start >= MIN_COL_SEGS:
        out.append((start, pos))
    return out, toks, cnts


def preceding_phases(toks, cnts, seg_start):
    """Phase tokens laid down in this run immediately before a column starts."""
    pos, before = 0, []
    for t, c in zip(toks, cnts):
        if pos >= seg_start:
            break
        before.append(t)
        pos += c
    tail = []
    for t in reversed(before):
        if t == "S":
            break
        tail.append(t)
    return ".".join(reversed(tail)) or "-"


def run_phases(pts):
    ph = _phases(pts)
    out = []
    for t, _c, _m in ph:
        if not out or out[-1] != t:
            out.append(t)
    return ".".join(out)


# ------------------------------------------------------------- geometry ---
def spine_of(pts):
    return [((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0) for a, b in zip(pts, pts[1:])]


def rail_metrics(pts):
    """Parity-safe column metrics — never slice a satin at fixed parity.

    width[i] = |p_i p_i+1| : every consecutive pair spans the column.
    adv[i]   = |p_i p_i+2| : two apart always lands on the SAME rail.
    At spine index i the two rails advance adv[i] and adv[i+1].
    """
    n = len(pts)
    return ([math.dist(pts[i], pts[i + 1]) for i in range(n - 1)],
            [math.dist(pts[i], pts[i + 2]) for i in range(n - 2)])


def true_width(w_consec, dens):
    """|p_i p_i+1| is the hypotenuse of (column width, half a rail advance)."""
    return math.sqrt(max(w_consec * w_consec - (dens / 2.0) ** 2, 0.0))


def loop_span(spine, tol=1.5):
    """Closed circuit, tolerating lead-in / lead-out tails."""
    n = len(spine)
    if n < MIN_COL_SEGS:
        return None
    best = None
    hs, he = 0, max(1, int(n * 0.20))
    ts, te = int(n * 0.80), n
    for i in range(hs, he):
        for j in range(ts, te):
            if math.dist(spine[i], spine[j]) <= tol and (best is None or (j - i) > best[1] - best[0]):
                best = (i, j)
    return best


def corner_indices(spine, width_mm, turn_deg=30.0):
    n = len(spine)
    if n < 8:
        return []
    seg = [math.dist(a, b) for a, b in zip(spine, spine[1:])]
    sp = sorted(seg)[len(seg) // 2] if seg else 0.0
    if sp <= 1e-9:
        return []
    k = max(1, round(max(width_mm, 0.5) / sp))
    if n <= 2 * k + 2:
        return []
    out = []
    for i in range(k, n - k):
        a, b, c = spine[i - k], spine[i], spine[i + k]
        t = abs(math.degrees((math.atan2(c[1] - b[1], c[0] - b[0])
                              - math.atan2(b[1] - a[1], b[0] - a[0])
                              + math.pi) % (2 * math.pi) - math.pi))
        if t >= turn_deg and (not out or i - out[-1][0] > 2 * k):
            out.append((i, t))
    return out, k


def signed_offsets(spine, poly, cap=240):
    """Signed distance, spine sample -> fill boundary. INWARD POSITIVE."""
    from shapely.geometry import Point
    from shapely.prepared import prep
    b, pre = poly.boundary, prep(poly)
    step = max(1, len(spine) // cap)
    out = []
    for p in spine[::step]:
        pt = Point(p)
        d = pt.distance(b)
        out.append(d if pre.covers(pt) else -d)
    return out


def med(a):
    if not a:
        return None
    s = sorted(a)
    return s[len(s) // 2]


def pct(a, q):
    if not a:
        return None
    s = sorted(a)
    return s[min(len(s) - 1, max(0, int(len(s) * q)))]


# ------------------------------------------------------------ bean/triple ---
def bean_stats(pts):
    if len(pts) < 12:
        return None
    grid = Counter((round(p[0] / 0.25), round(p[1] / 0.25)) for p in pts)
    if sum(1 for c in grid.values() if c >= 3) / max(len(grid), 1) < 0.25:
        return None
    lens = sorted(x for x in (math.dist(a, b) for a, b in zip(pts, pts[1:])) if x > 0.05)
    if not lens:
        return None
    return {"passes": round(len(pts) / max(len(grid), 1), 2),
            "stitch_med": lens[len(lens) // 2], "n": len(pts)}


# ---------------------------------------------------------------- render ---
def render(path, runs, fills, cols):
    allp = [p for r in runs for p in r["pts"]]
    if not allp:
        return None
    S = 8.0
    xs, ys = [p[0] for p in allp], [p[1] for p in allp]
    x0, y0 = min(xs) - 4, min(ys) - 4
    img = np.full((int((max(ys) + 4 - y0) * S) + 10, int((max(xs) + 4 - x0) * S) + 10, 3),
                  252, np.uint8)

    def px(p):
        return (int((p[0] - x0) * S) + 5, int((p[1] - y0) * S) + 5)

    for r in runs:
        cv2.polylines(img, [np.array([px(p) for p in r["pts"]], np.int32)], False,
                      (222, 222, 222), 1, cv2.LINE_AA)
    for f in fills:
        for poly in f["polys"]:
            for ring in [poly.exterior] + list(poly.interiors):
                cv2.polylines(img, [np.array([px(p) for p in ring.coords], np.int32)],
                              True, (210, 110, 40), 2, cv2.LINE_AA)
    for c in cols:
        sp = c["_spine"]
        col = ((40, 40, 225) if c.get("fill_edge") else
               (40, 150, 40) if c.get("closed") else (150, 150, 150))
        cv2.polylines(img, [np.array([px(p) for p in sp], np.int32)], False, col, 2,
                      cv2.LINE_AA)
        if c.get("fill_edge") or c.get("closed"):
            q = px(sp[len(sp) // 2])
            cv2.putText(img, f"{c['col_id']}", (q[0] + 4, q[1] - 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    out = OUT_BASE / path.stem.replace(" ", "_")
    out.mkdir(parents=True, exist_ok=True)
    dst = out / "borders.png"
    cv2.imwrite(str(dst), img)
    return dst


# ------------------------------------------------------------------ study ---
def study(path, do_render=False):
    runs, n_trim, _j = load_runs(path)
    fills = area_fills(runs)
    recs, cols_for_render = [], []

    for i, r in enumerate(runs):
        pts = r["pts"]
        cols, toks, cnts = columns(pts)

        # bean / triple run: whole runs with no column, plus long R phases
        if not cols:
            bn = bean_stats(pts)
            if bn:
                recs.append({"file": path.name, "kind": "bean", "src": "run",
                             "idx": i, "block": r["block"], **bn})
        pos = 0
        for t, c in zip(toks, cnts):
            if t == "R" and c >= 40:
                bn = bean_stats(pts[pos:pos + c + 1])
                if bn:
                    recs.append({"file": path.name, "kind": "bean", "src": "phase",
                                 "idx": i, "block": r["block"], **bn})
            pos += c

        for ci, (s0, s1) in enumerate(cols):
            cpts = pts[s0:s1 + 1]
            if len(cpts) < MIN_COL_SEGS:
                continue
            width, adv = rail_metrics(cpts)
            if not width or len(adv) < 4:
                continue
            spine = spine_of(cpts)
            wm = med(width)
            dm = med(adv)
            outer = [max(adv[k], adv[k + 1]) for k in range(len(adv) - 1)]
            inner = [min(adv[k], adv[k + 1]) for k in range(len(adv) - 1)]
            cr = corner_indices(spine, wm)
            cors, kwin = (cr if isinstance(cr, tuple) else ([], 1))
            span = loop_span(spine)

            rec = {"file": path.name, "kind": "col", "col_id": f"{i}.{ci}",
                   "idx": i, "block": r["block"], "n": len(cpts),
                   "width_med": wm, "width_true": true_width(wm, dm),
                   "width_p10": pct(width, 0.10), "width_p90": pct(width, 0.90),
                   "dens_med": dm, "dens_outer": med(outer), "dens_inner": med(inner),
                   "path_mm": sum(math.dist(a, b) for a, b in zip(spine, spine[1:])),
                   "closed": span is not None, "n_corners": len(cors),
                   "underlay": preceding_phases(toks, cnts, s0),
                   "run_recipe": run_phases(pts),
                   "over_fill": False, "fill_edge": False, "offset_med": None}
            rec["width_range"] = (rec["width_p90"] or 0) - (rec["width_p10"] or 0)
            rec["width_cv"] = rec["width_range"] / max(wm, 1e-6)

            # corner behaviour: corner window vs straight window, same column
            if cors and len(spine) > 40:
                k = max(2, min(kwin, 10))
                cset, far = set(), set()
                for cidx, _t in cors:
                    cset.update(range(max(0, cidx - k), min(len(spine), cidx + k + 1)))
                    far.update(range(max(0, cidx - 4 * k), min(len(spine), cidx + 4 * k + 1)))
                straight = [j for j in range(len(spine)) if j not in far]
                pick = lambda arr, ix: [arr[j] for j in ix if j < len(arr)]  # noqa: E731
                cw, sw = pick(width, sorted(cset)), pick(width, straight)
                co, so = pick(outer, sorted(cset)), pick(outer, straight)
                cin, sin_ = pick(inner, sorted(cset)), pick(inner, straight)
                if len(cw) > 4 and len(sw) > 10:
                    rec.update({
                        "corner_width_mm": med(cw), "straight_width_mm": med(sw),
                        "corner_outer_mm": med(co), "straight_outer_mm": med(so),
                        "corner_inner_mm": med(cin), "straight_inner_mm": med(sin_),
                        "corner_width_ratio": med(cw) / max(med(sw), 1e-6),
                        "corner_outer_ratio": med(co) / max(med(so), 1e-6),
                        "corner_inner_ratio": med(cin) / max(med(sin_), 1e-6),
                        "corner_turn_med": med([t for _c, t in cors])})

            # loop start relative to the nearest corner
            if span and cors:
                i0, j0 = span
                loop = spine[i0:j0 + 1]
                seg = [math.dist(a, b) for a, b in zip(loop, loop[1:])]
                per = sum(seg)
                cs = [c for c, _t in cors if i0 <= c <= j0]
                if cs and per > 1e-6 and len(loop) > 20:
                    cum = [0.0]
                    for s in seg:
                        cum.append(cum[-1] + s)
                    ds = []
                    for c in cs:
                        dc = cum[min(c - i0, len(cum) - 1)]
                        ds.append(min(dc, per - dc))
                    rec["start_to_corner_mm"] = min(ds)
                    rec["loop_perimeter_mm"] = per
                    rec["start_to_corner_norm"] = min(ds) / max(per / len(cs), 1e-6)
                    from shapely.geometry import Polygon as _P
                    try:
                        pg = _P(loop)
                        pg = pg if pg.is_valid else pg.buffer(0)
                        rec["loop_area_mm2"] = abs(pg.area)
                    except Exception:                          # noqa: BLE001
                        pass

            # a separate EARLIER RUN tracking this spine (underlay as its own run)
            rec["underlay_run"] = _tracking_run(runs, i, spine)

            # over a fill?
            best = None
            for f in fills:
                if f["idx"] >= i:
                    continue
                for poly in f["polys"][:3]:
                    ds = signed_offsets(spine, poly)
                    if len(ds) < 8:
                        continue
                    near = sum(1 for d in ds if abs(d) <= EDGE_NEAR_MM) / len(ds)
                    cand = {"fill_idx": f["idx"], "fill_block": f["block"],
                            "fill_area": f["area"], "fill_cls": f["cls"],
                            "near": near,
                            "inside": sum(1 for d in ds if d > 0) / len(ds),
                            "offset_med": med(ds), "offset_p10": pct(ds, 0.10),
                            "offset_p90": pct(ds, 0.90),
                            "offset_iqr": (pct(ds, 0.75) or 0) - (pct(ds, 0.25) or 0)}
                    if best is None or cand["near"] > best["near"]:
                        best = cand
            if best:
                rec["near_fill"] = best["near"]
                if best["near"] >= EDGE_FRAC:
                    rec.update({"over_fill": True, "fill_edge": True,
                                "same_block_as_fill": best["fill_block"] == r["block"]})
                    rec.update({k: best[k] for k in
                                ("fill_idx", "fill_area", "fill_cls", "inside",
                                 "offset_med", "offset_p10", "offset_p90", "offset_iqr")})
                elif best["inside"] >= 0.85:
                    rec["over_fill"] = True          # sits on the fill but not its edge
                    rec["inside"] = best["inside"]
            rec["_spine"] = spine
            recs.append(rec)
            cols_for_render.append(rec)

    dst = render(path, runs, fills, cols_for_render) if do_render else None
    return recs, fills, n_trim, dst


def _tracking_run(runs, i, spine, tol=1.0):
    if len(spine) < 20:
        return False
    samp = spine[::max(1, len(spine) // 40)]
    for j in range(max(0, i - 4), i):
        q = runs[j]["pts"]
        if len(q) < 8 or len(q) > 2 * len(spine):
            continue
        grid = {(round(p[0] / tol), round(p[1] / tol)) for p in q}
        hit = sum(1 for p in samp
                  if any((round(p[0] / tol) + dx, round(p[1] / tol) + dy) in grid
                         for dx in (-1, 0, 1) for dy in (-1, 0, 1)))
        if hit / len(samp) >= 0.8:
            return True
    return False


# --------------------------------------------------------------- summary ---
def _stat(name, arr, unit="mm", sign="+"):
    if not arr:
        print(f"  {name:<38} n=0")
        return
    a = sorted(arr)
    n = len(a)
    f = f"{{:{sign}.2f}}"
    print(f"  {name:<38} n={n:<4} med={f.format(a[n // 2])} "
          f"p10={f.format(a[int(n * .10)])} p90={f.format(a[min(n - 1, int(n * .90))])} {unit}")


def summary(recs, label):
    files = sorted({r["file"] for r in recs})
    print(f"\n{'=' * 78}\n== {label}   files={len(files)}\n{'=' * 78}")
    cols = [r for r in recs if r["kind"] == "col"]
    bean = [r for r in recs if r["kind"] == "bean"]
    edge = [r for r in cols if r.get("fill_edge")]
    closed = [r for r in cols if r["closed"]]
    # a border = closed loop OR tracks a fill edge
    border = [r for r in cols if r["closed"] or r.get("fill_edge")]
    plain = [r for r in cols if not (r["closed"] or r.get("fill_edge"))]
    print(f"columns={len(cols)}  closed-loop={len(closed)}  fill-edge={len(edge)}  "
          f"border(either)={len(border)}  non-border columns={len(plain)}")

    print("\n-- [Q2] SEAM-COVERAGE OFFSET  (centreline vs fill edge, INWARD POSITIVE)")
    _stat("offset", [r["offset_med"] for r in edge if r.get("offset_med") is not None])
    _stat("within-border spread p90-p10",
          [r["offset_p90"] - r["offset_p10"] for r in edge if r.get("offset_p90") is not None], "mm", "")
    _stat("within-border IQR", [r["offset_iqr"] for r in edge if r.get("offset_iqr") is not None], "mm", "")
    _stat("offset / half-width", [r["offset_med"] / max(r["width_true"] / 2, 1e-6)
                                  for r in edge if r.get("offset_med") is not None], "x")
    _stat("fraction of column inside the fill", [r["inside"] for r in edge if "inside" in r], "", "")
    if edge:
        sb = sum(1 for r in edge if r.get("same_block_as_fill"))
        print(f"  {'same colour block as its fill':<38} {sb}/{len(edge)}")
        print(f"  {'files contributing':<38} {len(sorted({r['file'] for r in edge}))}")

    print("\n-- [Q4 law 11] BORDER WIDTH vs OTHER COLUMNS")
    _stat("border width (raw |p_i p_i+1|)", [r["width_med"] for r in border], "mm", "")
    _stat("border width (TRUE, hypotenuse removed)", [r["width_true"] for r in border], "mm", "")
    _stat("  ... closed-loop subset", [r["width_true"] for r in closed], "mm", "")
    _stat("  ... fill-edge subset", [r["width_true"] for r in edge], "mm", "")
    _stat("non-border column width (TRUE)", [r["width_true"] for r in plain], "mm", "")
    _stat("ALL column width (TRUE)", [r["width_true"] for r in cols], "mm", "")

    print("\n-- [Q4 law 12] BORDER DENSITY vs OTHER COLUMNS")
    _stat("border density (rail advance)", [r["dens_med"] for r in border], "mm", "")
    _stat("  ... outer rail", [r["dens_outer"] for r in border], "mm", "")
    _stat("  ... inner rail", [r["dens_inner"] for r in border], "mm", "")
    _stat("non-border column density", [r["dens_med"] for r in plain], "mm", "")
    _stat("ALL column density", [r["dens_med"] for r in cols], "mm", "")

    print("\n-- [Q4 law 13] IS A BORDER A CLOSED LOOP?")
    if cols:
        print(f"  closed loops as a share of all columns : {len(closed)}/{len(cols)} "
              f"= {100 * len(closed) / len(cols):.0f}%")
    if edge:
        ce = sum(1 for r in edge if r["closed"])
        print(f"  fill-edge borders that are closed loops: {ce}/{len(edge)} "
              f"= {100 * ce / len(edge):.0f}%")
    _stat("closed-loop perimeter", [r["loop_perimeter_mm"] for r in closed
                                    if "loop_perimeter_mm" in r], "mm", "")

    print("\n-- [Q3a] CORNER BEHAVIOUR  (corner window vs straight window, same column)")
    for nm, arr in (("borders", border), ("all columns", cols)):
        cw = [r for r in arr if "corner_width_ratio" in r]
        if not cw:
            continue
        print(f"  [{nm}]")
        _stat("   width  corner/straight", [r["corner_width_ratio"] for r in cw], "x", "")
        _stat("   OUTER rail corner/straight", [r["corner_outer_ratio"] for r in cw], "x", "")
        _stat("   INNER rail corner/straight", [r["corner_inner_ratio"] for r in cw], "x", "")
        _stat("   corner width", [r["corner_width_mm"] for r in cw], "mm", "")
        _stat("   straight width", [r["straight_width_mm"] for r in cw], "mm", "")
        _stat("   corner OUTER advance", [r["corner_outer_mm"] for r in cw], "mm", "")
        _stat("   straight OUTER advance", [r["straight_outer_mm"] for r in cw], "mm", "")
        _stat("   corner INNER advance", [r["corner_inner_mm"] for r in cw], "mm", "")
        _stat("   straight INNER advance", [r["straight_inner_mm"] for r in cw], "mm", "")

    print("\n-- [Q3b] WHERE A CLOSED LOOP STARTS, RELATIVE TO CORNERS")
    sc = [r for r in closed if "start_to_corner_norm" in r]
    _stat("start -> nearest corner", [r["start_to_corner_mm"] for r in sc], "mm", "")
    _stat("  ... / mean corner spacing", [r["start_to_corner_norm"] for r in sc], "x", "")
    print("     uniform-random starts average 0.25x; 0.00 = starts AT a corner")

    print("\n-- [Q3c] DOES A BORDER CARRY ITS OWN UNDERLAY?")
    for nm, arr in (("fill-edge borders", edge), ("closed loops", closed),
                    ("non-border columns", plain)):
        if not arr:
            continue
        u = Counter(r["underlay"] for r in arr)
        sep = sum(1 for r in arr if r.get("underlay_run"))
        anyu = sum(1 for r in arr if r["underlay"] not in ("-", "L", "O"))
        z = sum(1 for r in arr if "Z" in r["underlay"])
        print(f"  {nm:<20} in-run underlay {anyu}/{len(arr)}  with Z {z}/{len(arr)}  "
              f"separate underlay run {sep}/{len(arr)}")
        print(f"  {'':<20} phases before the column: {dict(u.most_common(6))}")

    print("\n-- [Q3d] IS BORDER WIDTH CONSTANT AROUND A LOOP?")
    _stat("width p90-p10 within one border", [r["width_range"] for r in border], "mm", "")
    _stat("  ... as a fraction of width", [r["width_cv"] for r in border], "x", "")
    _stat("non-border p90-p10", [r["width_range"] for r in plain], "mm", "")

    print("\n-- [Q3e] BORDER WIDTH vs SIZE OF THE SHAPE IT BOUNDS")
    pairs = [(math.sqrt(r["loop_area_mm2"]), r["width_true"]) for r in closed
             if r.get("loop_area_mm2", 0) > 4]
    if len(pairs) >= 5:
        xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        num = sum((a - mx) * (b - my) for a, b in pairs)
        den = math.sqrt(sum((a - mx) ** 2 for a in xs) * sum((b - my) ** 2 for b in ys))
        print(f"  n={len(pairs)}  corr(sqrt(enclosed area), true width) = "
              f"{num / den if den else 0:+.2f}")
        pairs.sort()
        t = max(1, len(pairs) // 4)
        for nm, sl in (("Q1 small", pairs[:t]), ("Q2", pairs[t:2 * t]),
                       ("Q3", pairs[2 * t:3 * t]), ("Q4 large", pairs[3 * t:])):
            if sl:
                print(f"    {nm:<9} sqrt(area) med={med([a for a, _ in sl]):6.1f} mm   "
                      f"width med={med([b for _, b in sl]):.2f} mm   n={len(sl)}")
    else:
        print(f"  too few closed loops with an enclosed area ({len(pairs)})")

    print("\n-- [Q4 law 14] BEAN / TRIPLE RUN")
    _stat("passes", [r["passes"] for r in bean], "x", "")
    _stat("stitch length", [r["stitch_med"] for r in bean], "mm", "")
    if bean:
        print(f"  whole-run beans {sum(1 for r in bean if r['src'] == 'run')}, "
              f"in-run R-phase beans {sum(1 for r in bean if r['src'] == 'phase')}")


def main():
    args = sys.argv[1:]
    if args and args[0] == "--summary":
        recs = []
        for a in args[1:]:
            recs.extend(json.loads(Path(a).read_text()))
        summary(recs, "POOLED")
        return
    do_render = "--render" in args
    quiet = "--quiet" in args
    args = [a for a in args if a not in ("--render", "--quiet")]
    out_json = None
    if "--json" in args:
        k = args.index("--json")
        out_json = Path(args[k + 1])
        args = args[:k] + args[k + 2:]

    allrecs = []
    for a in args:
        p = Path(a)
        try:
            recs, fills, n_trim, dst = study(p, do_render)
        except Exception as exc:                              # noqa: BLE001
            print(f"{p.name}: FAILED {type(exc).__name__}: {exc}")
            continue
        cols = [r for r in recs if r["kind"] == "col"]
        edge = [r for r in cols if r.get("fill_edge")]
        if not quiet:
            print(f"\n=== {p.name} ===  area-fills={len(fills)} columns={len(cols)} "
                  f"fill-edge-borders={len(edge)} trims={n_trim}")
            for f in fills:
                print(f"  FILL run#{f['idx']} blk{f['block']} classify()={f['cls']:<5} "
                      f"area={f['area']:7.1f}mm2 inscribed_r={f['inscribed']:5.1f}mm n={f['n']}")
            for r in cols:
                tag = ""
                if r.get("fill_edge"):
                    tag = (f"  <<EDGE over fill#{r['fill_idx']} offset={r['offset_med']:+.2f} "
                           f"[p10 {r['offset_p10']:+.2f} p90 {r['offset_p90']:+.2f}] "
                           f"inside={r['inside']:.2f}")
                elif r.get("over_fill"):
                    tag = f"  (on fill, not its edge)"
                print(f"  COL {r['col_id']:<7} blk{r['block']} n={r['n']:<5} "
                      f"w={r['width_true']:.2f} d={r['dens_med']:.2f} "
                      f"len={r['path_mm']:6.1f}mm {'LOOP' if r['closed'] else 'open'} "
                      f"cor={r['n_corners']:<3} under={r['underlay']:<7}{tag}")
            if dst:
                print(f"  render -> {dst}")
        for r in recs:
            r.pop("_spine", None)
        allrecs.extend(recs)

    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(allrecs))
        print(f"\nwrote {len(allrecs)} records -> {out_json}")
    summary(allrecs, "POOLED")


if __name__ == "__main__":
    main()
