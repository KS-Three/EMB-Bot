"""Where a design's stitch directions point — per shape, per design, and
against the professional's file — the instrument for item 7 of the quality
review (2026-09-08; `cfg.design_angle`).

Every fill-tier shape in the plan is read for the row direction it actually
sewed (the length-weighted mean of its fill segments in doubled-angle space),
its area, its aspect (the ratio of its principal moments, 1.0 for a disc or a
square, large for a bar), and where its angle came from: `house` (the
lettering pass wrote `satin_angle_deg`/`fill_angle_deg`), `meta` (a
review-screen override), `cfg` (`fill_angle_deg`), `axis` (the directional-
comp lane's axis) or `derived` (stage 6's own `best_fill_angle_deg`). Per
design: the number of fill shapes, the area-weighted resultant length R of
their doubled angles (1.0 = every fill on one angle, 0 = spread evenly over
the half-circle), how many distinct 11.25-degree bins they occupy, the modal
angle, and the lettering house angle if one was set. Non-lettering satin
shapes are counted with whether they were handed a cross angle at all (none
are, OFF: each stroke follows its own tangent).

With `--pro FILE` (a professionally sewn DST/PES of the same design — the
Becker files under `testdata/reference/`) the design is digitized at the
pro's own width, the pro's stitches are put in our frame (y flipped, the
scorecard's translation search for the residual), and both are read the way
`tools/pro_parity/scorecard.py` reads them: the dominant direction per 2 mm
cell over the solid area. Reported: the pro's own spread (R and bins over
its solid cells), ours, and the scorecard's chance-corrected `direction`
agreement over the shared solid cells — the 20-point component item 7 says
has the most headroom.

`--compare` digitizes OFF and ON `cfg.design_angle` and prints both.

Usage:
  python tools/design_direction.py [--widths W ...] [--flag NAME[=VALUE] ...]
                                   [--compare] [--pro FILE] [--json PATH]
                                   [--corpus] [cases ...]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Point as SPoint
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "pro_parity"))

from digitizer_core import PipelineConfig, digitize                       # noqa: E402
from digitizer_core import stage6_fill as s6f                              # noqa: E402
from digitizer_core import stage6_satin as s6                              # noqa: E402
from digitizer_core import stage7_sequence as s7                           # noqa: E402
from digitizer_core.stitches import strip_ties                             # noqa: E402
from curve_tiers import CASES                                               # noqa: E402
from thin_strokes import parse_flags                                        # noqa: E402
import scorecard as sc                                                      # noqa: E402

ROOT = HERE.parent
BIN_DEG = 11.25


def has_flag() -> bool:
    return "design_angle" in {f.name for f in dataclasses.fields(PipelineConfig)}


# ----------------------------------------------------------------- geometry
def aspect_of(poly: Polygon) -> float:
    """Ratio of the polygon's principal moments' square roots, >= 1: the
    long axis over the short one by AREA (the same moments
    `stage6_fill.principal_angle_deg` reads)."""
    area, mx, my, ixx, iyy, ixy = s6f._ring_moments(poly.exterior.coords)
    for ring in poly.interiors:
        r = s6f._ring_moments(ring.coords)
        area, mx, my = area + r[0], mx + r[1], my + r[2]
        ixx, iyy, ixy = ixx + r[3], iyy + r[4], ixy + r[5]
    if abs(area) < 1e-12:
        return 1.0
    cx, cy = mx / area, my / area
    sxx = iyy - area * cx * cx
    syy = ixx - area * cy * cy
    sxy = ixy - area * cx * cy
    if area < 0:
        sxx, syy, sxy = -sxx, -syy, -sxy
    mean = (sxx + syy) / 2.0
    half = math.hypot((sxx - syy) / 2.0, sxy)
    lo, hi = max(mean - half, 1e-12), max(mean + half, 1e-12)
    return math.sqrt(hi / lo)


def doubled_mean(angles_deg: list[float], weights: list[float]) -> tuple[float | None, float]:
    """-> (mean angle on [0, 180) or None, resultant length R on [0, 1])."""
    if not angles_deg:
        return None, 0.0
    c = s = w = 0.0
    for a, wt in zip(angles_deg, weights):
        t = math.radians(2.0 * a)
        c += wt * math.cos(t)
        s += wt * math.sin(t)
        w += wt
    if w <= 0:
        return None, 0.0
    c /= w
    s /= w
    return (math.degrees(0.5 * math.atan2(s, c))) % 180.0, math.hypot(c, s)


def bins_of(angles_deg: list[float]) -> int:
    return len({int(((a % 180.0) + BIN_DEG / 2.0) // BIN_DEG) % int(round(180.0 / BIN_DEG)) for a in angles_deg})


def run_direction(points: list) -> tuple[float | None, float]:
    """Length-weighted doubled-angle mean of a run's segments -> (deg, length)."""
    c = s = total = 0.0
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d < 0.05 or d > sc.LONG_MM:
            continue
        t = 2.0 * math.atan2(dy, dx)
        c += d * math.cos(t)
        s += d * math.sin(t)
        total += d
    if total <= 0:
        return None, 0.0
    return (math.degrees(0.5 * math.atan2(s, c))) % 180.0, total


# -------------------------------------------------------------- one design
def scan(case: str, rel: str, kw: dict, width_mm: float | None, flags: dict,
         pro: Path | None = None) -> dict:
    cfg = dict(kw)
    if width_mm is not None:
        cfg["target_width_mm"] = width_mm
    cfg.update(flags)
    pc = PipelineConfig(**cfg)

    fills: dict[str, dict] = {}
    satins: dict[str, dict] = {}
    real_fill = s7.stitch_shape
    real_satin = s7.satin_shape

    def spy_fill(poly, shape_id, **kwargs):
        fills[shape_id] = {"poly": poly, "angle_arg": kwargs.get("angle_deg")}
        return real_fill(poly, shape_id, **kwargs)

    def spy_satin(poly, shape_id, **kwargs):
        satins[shape_id] = {"poly": poly, "angle_arg": kwargs.get("angle_deg")}
        return real_satin(poly, shape_id, **kwargs)

    s7.stitch_shape = spy_fill
    s7.satin_shape = spy_satin
    try:
        result, plan = digitize(ROOT / "testdata" / rel, pc)
    finally:
        s7.stitch_shape = real_fill
        s7.satin_shape = real_satin

    meta_by_id = {r.shape_id: r.meta for r in result.regions}
    by_shape: dict[str, list] = {}
    for _b, run in plan.iter_runs():
        by_shape.setdefault(run.shape_id, []).append(run)

    rows = []
    for sid, info in fills.items():
        runs = [r for r in by_shape.get(sid, []) if r.kind == "fill"]
        pts_all = [p for r in runs for p in r.points]
        # one direction per shape: weight every fill run's own mean by length
        angs, lens = [], []
        for r in runs:
            a, ln = run_direction(list(r.points))
            if a is not None:
                angs.append(a)
                lens.append(ln)
        sewn, _r = doubled_mean(angs, lens)
        meta = meta_by_id.get(sid, {}) or {}
        if "satin_angle_deg" in meta and "fill_angle_deg" in meta:
            source = "house"
        elif meta.get("fill_angle_deg") is not None:
            source = "meta"
        elif pc.fill_angle_deg is not None:
            source = "cfg"
        elif info["angle_arg"] is not None:
            source = "axis"
        else:
            source = "derived"
        if meta.get("design_angle_deg") is not None and source in ("axis", "derived"):
            source = "design"
        poly = info["poly"]
        rows.append({
            "shape": sid, "tier": "fill", "sewn_deg": None if sewn is None else round(sewn, 1),
            "angle_arg": None if info["angle_arg"] is None else round(float(info["angle_arg"]), 1),
            "source": source, "area_mm2": round(poly.area, 1), "aspect": round(aspect_of(poly), 2),
            "stitches": len(pts_all),
        })
    n_satin_house = sum(1 for sid in satins if (meta_by_id.get(sid) or {}).get("satin_angle_deg") is not None)
    n_satin_design = sum(1 for sid in satins if (meta_by_id.get(sid) or {}).get("design_angle_deg") is not None
                         and (meta_by_id.get(sid) or {}).get("satin_angle_deg") is None)
    n_satin_arg = sum(1 for v in satins.values() if v["angle_arg"] is not None)

    with_dir = [r for r in rows if r["sewn_deg"] is not None]
    modal, R = doubled_mean([r["sewn_deg"] for r in with_dir], [r["area_mm2"] for r in with_dir])
    house = sorted({round(float(m["satin_angle_deg"]), 1) for m in meta_by_id.values()
                    if m and m.get("satin_angle_deg") is not None})
    design = sorted({round(float(m["design_angle_deg"]), 1) for m in meta_by_id.values()
                     if m and m.get("design_angle_deg") is not None})
    out = {
        "case": case, "width_mm": cfg.get("target_width_mm"), "flags": flags,
        "fills": len(rows), "fills_with_direction": len(with_dir),
        "spread_R": round(R, 3), "bins": bins_of([r["sewn_deg"] for r in with_dir]),
        "modal_deg": None if modal is None else round(modal, 1),
        "house_deg": house, "design_deg": design,
        "sources": {k: sum(1 for r in rows if r["source"] == k) for k in ("house", "meta", "cfg", "axis", "design", "derived")},
        "satin_shapes": len(satins), "satin_with_house": n_satin_house, "satin_with_design": n_satin_design,
        "satin_with_angle_arg": n_satin_arg,
        "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
        "shapes": sorted(rows, key=lambda r: -r["area_mm2"]),
    }
    if pro is not None:
        out["pro"] = against_pro(plan, pro, [(sid, info["poly"]) for sid, info in fills.items()])
    return out


# ---------------------------------------------------------------- the pro
def plan_segs(plan) -> list[tuple]:
    segs = []
    for bi, block in enumerate(plan.blocks):
        prev = None
        for run in block.runs:
            pts = strip_ties(run.points) if run.kind == "satin" else list(run.points)
            if not pts:
                continue
            if prev is not None:
                x0, y0 = prev
                x1, y1 = pts[0]
                segs.append((x0, y0, x1, y1, math.hypot(x1 - x0, y1 - y0), bi, bool(run.trim)))
            for a, b in zip(pts, pts[1:]):
                segs.append((a[0], a[1], b[0], b[1], math.hypot(b[0] - a[0], b[1] - a[1]), bi, False))
            prev = pts[-1]
    return segs


def pro_segs(path: Path, flip_y: bool) -> list[tuple]:
    import pystitch
    pat = pystitch.read(str(path))
    rows = []
    block = 0
    pending = False
    for x, y, cmd in pat.stitches:
        c = cmd & pystitch.COMMAND_MASK
        if c == pystitch.STITCH:
            rows.append((block, x / 10.0, (-y if flip_y else y) / 10.0, pending))
            pending = False
        elif c == pystitch.COLOR_CHANGE:
            block += 1
            pending = True
        elif c in (pystitch.TRIM, pystitch.STOP):
            pending = True
        elif c == pystitch.END:
            break
    return sc.to_segs(rows)


def cell_spread(angles: np.ndarray, mask: np.ndarray) -> tuple[float, int, float | None]:
    vals = angles[mask & ~np.isnan(angles)]
    if vals.size == 0:
        return 0.0, 0, None
    deg = [math.degrees(v) % 180.0 for v in vals.tolist()]
    modal, r = doubled_mean(deg, [1.0] * len(deg))
    return round(r, 3), bins_of(deg), None if modal is None else round(modal, 1)


def against_pro(plan, pro: Path, fill_polys=None) -> dict:
    ours = plan_segs(plan)
    best = None
    for flip in (True, False):
        segs = pro_segs(pro, flip)
        # centre the pro on ours before the translation search (its origin is the hoop's)
        oxs = [s[0] for s in ours] + [s[2] for s in ours]
        oys = [s[1] for s in ours] + [s[3] for s in ours]
        pxs = [s[0] for s in segs] + [s[2] for s in segs]
        pys = [s[1] for s in segs] + [s[3] for s in segs]
        dx = (min(oxs) + max(oxs)) / 2 - (min(pxs) + max(pxs)) / 2
        dy = (min(oys) + max(oys)) / 2 - (min(pys) + max(pys)) / 2
        segs = sc.shifted(segs, dx, dy)
        bb = sc.bounds(segs, ours)
        rdx, rdy, iou = sc.register(segs, ours, bb)
        if best is None or iou > best[0]:
            best = (iou, flip, segs, rdx, rdy)
    iou, flip, segs, rdx, rdy = best
    our_r = sc.shifted(ours, rdx, rdy)
    bb = sc.bounds(segs, our_r)
    pc = sc.raster(segs, bb)
    oc = sc.raster(our_r, bb)
    sp, so = sc.solid(pc), sc.solid(oc)
    pa, _pt, _ = sc.cell_stats(segs, bb)
    oa, _ot, _ = sc.cell_stats(our_r, bb)
    shared = sc.solid_cells(sp & so, bb)
    h = min(pa.shape[0], shared.shape[0])
    w = min(pa.shape[1], shared.shape[1])
    both = np.zeros(pa.shape, bool)
    both[:h, :w] = shared[:h, :w]
    both &= ~np.isnan(pa) & ~np.isnan(oa)
    out = {"file": pro.name, "flip_y": flip, "registration_iou": round(iou, 3),
           "shift_mm": [round(rdx, 2), round(rdy, 2)], "shared_cells": int(both.sum())}
    p_solid = sc.solid_cells(sp, bb)
    o_solid = sc.solid_cells(so, bb)
    pb = np.zeros(pa.shape, bool); pb[:min(pa.shape[0], p_solid.shape[0]), :min(pa.shape[1], p_solid.shape[1])] = \
        p_solid[:min(pa.shape[0], p_solid.shape[0]), :min(pa.shape[1], p_solid.shape[1])]
    ob = np.zeros(oa.shape, bool); ob[:min(oa.shape[0], o_solid.shape[0]), :min(oa.shape[1], o_solid.shape[1])] = \
        o_solid[:min(oa.shape[0], o_solid.shape[0]), :min(oa.shape[1], o_solid.shape[1])]
    out["pro_spread_R"], out["pro_bins"], out["pro_modal_deg"] = cell_spread(pa, pb)
    out["our_spread_R"], out["our_bins"], out["our_modal_deg"] = cell_spread(oa, ob)
    if both.any():
        diff = np.abs(pa[both] - oa[both])
        diff = np.minimum(diff, math.pi - diff)
        raw = float(np.mean(1 - diff / (math.pi / 2)))
        out["direction_raw"] = round(raw, 3)
        out["direction"] = round(sc.chance_correct(raw, sc.DIRECTION_CHANCE), 3)
        out["within_20deg"] = round(float(np.mean(diff <= math.radians(20))), 3)
    # The pro's direction INSIDE each of our fill shapes (cells whose centre
    # the shape covers, in the registered frame): does the pro hold one
    # angle across shapes of every aspect, or turn the elongated ones?
    out["per_shape"] = []
    x0, y0, _x1, _y1 = bb
    for sid, poly in fill_polys or []:
        moved = translate(poly, rdx, rdy)
        vals = []
        ovals = []
        for i in range(pa.shape[0]):
            for j in range(pa.shape[1]):
                if np.isnan(pa[i, j]):
                    continue
                cx = x0 + (j + 0.5) * sc.CELL
                cy = y0 + (i + 0.5) * sc.CELL
                if moved.covers(SPoint(cx, cy)):
                    vals.append(math.degrees(pa[i, j]) % 180.0)
                    if not np.isnan(oa[i, j]):
                        ovals.append(math.degrees(oa[i, j]) % 180.0)
        pm, pr = doubled_mean(vals, [1.0] * len(vals))
        om, orr = doubled_mean(ovals, [1.0] * len(ovals))
        out["per_shape"].append({
            "shape": sid, "area_mm2": round(poly.area, 1), "aspect": round(aspect_of(poly), 2),
            "pro_cells": len(vals), "pro_deg": None if pm is None else round(pm, 1), "pro_R": round(pr, 2),
            "our_deg": None if om is None else round(om, 1),
        })
    return out


# ------------------------------------------------------------------ report
def print_design(r: dict, top: int) -> None:
    flags = r["flags"] or "flags default"
    print(f"== {r['case']:12s} {r['width_mm']} mm  {flags}: fills {r['fills']} (with direction {r['fills_with_direction']})  "
          f"spread R {r['spread_R']}  bins {r['bins']}  modal {r['modal_deg']}  house {r['house_deg']}  design {r['design_deg']}  "
          f"sources {r['sources']}  satin {r['satin_shapes']} (house {r['satin_with_house']}, design {r['satin_with_design']}, angled {r['satin_with_angle_arg']})  "
          f"stitches {r['stitches']} trims {r['trims']}")
    for s in r["shapes"][:top]:
        print(f"     {s['shape']:10s} {s['area_mm2']:8.1f} mm2  aspect {s['aspect']:5.2f}  sewn {s['sewn_deg']}  arg {s['angle_arg']}  {s['source']}")
    if "pro" in r:
        p = r["pro"]
        print(f"     PRO {p['file']}: registration IoU {p['registration_iou']} shift {p['shift_mm']} flip {p['flip_y']}  "
              f"pro spread R {p['pro_spread_R']} bins {p['pro_bins']} modal {p['pro_modal_deg']}  |  ours R {p['our_spread_R']} bins {p['our_bins']} modal {p['our_modal_deg']}  "
              f"|  direction {p.get('direction')} (raw {p.get('direction_raw')}, within 20 deg {p.get('within_20deg')}) over {p['shared_cells']} shared cells")
        for q in sorted(p.get("per_shape", []), key=lambda q: -q["area_mm2"])[:top]:
            print(f"        pro in {q['shape']:10s} {q['area_mm2']:8.1f} mm2 aspect {q['aspect']:5.2f}: pro {q['pro_deg']} (R {q['pro_R']}, {q['pro_cells']} cells)  ours {q['our_deg']}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="*", default=None)
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--pro", default=None)
    ap.add_argument("--json", default=None)
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--corpus", action="store_true", help="the 26 scorecard fixtures at 80 mm")
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    pro = None
    if a.pro:
        pro = Path(a.pro) if Path(a.pro).is_absolute() else ROOT / a.pro
    cases: list[tuple[str, str, dict]] = []
    if a.corpus:
        from corpus_scorecard import FIXTURES
        for rel in FIXTURES:
            cases.append((Path(rel).stem, rel, {"target_width_mm": 80.0}))
    for c in a.cases or ([] if a.corpus else ["enthusiast", "becker", "drone", "fremont"]):
        if c in CASES:
            rel, kw = CASES[c]
            cases.append((c, rel, dict(kw)))
        elif (ROOT / "testdata" / c).exists():
            # a path under testdata/, as tools/satin_lean.py takes one
            cases.append((Path(c).stem, c, {"target_width_mm": 80.0}))
        else:
            raise SystemExit(f"unknown case {c!r}: not in curve_tiers.CASES and not a path under testdata/")
    widths = a.widths or [None]
    results = []
    for case, rel, kw in cases:
        for w in widths:
            if a.compare:
                if not has_flag():
                    print("cfg.design_angle is not built yet; --compare needs it")
                    return 2
                off = scan(case, rel, kw, w, {**flags, "design_angle": False}, pro)
                on = scan(case, rel, kw, w, {**flags, "design_angle": True}, pro)
                print_design(off, a.top)
                print_design(on, a.top)
                print(f"     OFF -> ON: spread R {off['spread_R']} -> {on['spread_R']}  bins {off['bins']} -> {on['bins']}  "
                      f"stitches {off['stitches']} -> {on['stitches']}  trims {off['trims']} -> {on['trims']}"
                      + (f"  direction {off['pro'].get('direction')} -> {on['pro'].get('direction')}" if pro else ""))
                results += [off, on]
            else:
                r = scan(case, rel, kw, w, flags, pro)
                print_design(r, a.top)
                results.append(r)
    if a.json:
        Path(a.json).write_text(json.dumps(results, indent=1))
    print("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
