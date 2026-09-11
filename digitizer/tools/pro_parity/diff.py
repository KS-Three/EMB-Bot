"""The catalogue: what differs between our stitches and the pro's, per element.

One set of readers pointed at two machine files — `ours.dst` (written from
the plan by prep) and the pro's — in the frame `pairframe` registered. Per
our region: tier, column width, direction, row pitch, underlay recipe,
coverage layers, density, stitches, trims, each side beside the other. Then
design-level counts, then the SHAPE rows (Task 11), tagged so a dropped
element (ours), a pro's redesign (Kent's call) and sewn background (ours)
never share a bucket. No score anywhere: tolerances below are DISPLAY
thresholds that decide which rows sort first, and say so. Spec §5.

Tier is the same scale-free rule on both sides — `satin_columns`' crossing
share, then `row_pitch_union`'s rows — because `study_pro.classify` cannot
see a column under 0.7 mm and would call our hairline satin "other". Our
engine's INTENDED tier is `tier_planned`, from `ours_regions.json`.

    python tools/pro_parity/diff.py --dir <out>/real/<slug> [--flag NAME[=VALUE] ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.affinity import affine_transform
from shapely.geometry import Point, Polygon
import shapely.wkt

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import pairframe as pf                                                  # noqa: E402
import scorecard as sc                                                  # noqa: E402
from census_pro import _phases                                          # noqa: E402
from design_direction import doubled_mean                               # noqa: E402
from junction_blobs import _Runs, coverage_in                           # noqa: E402
from row_pitch_union import union_pitch                                 # noqa: E402
from satin_columns import measure as satin_measure, passes_from_file    # noqa: E402
from digitizer_core.preflight import _coverage_map                      # noqa: E402
from digitizer_core.stitches import StitchRun                           # noqa: E402

ASSIGN_SHARE = 0.6      # a pass belongs to the region holding this share of its points
ASSIGN_BUFFER_MM = 0.3  # pull comp + half a thread
LAYER_CELL_MM = 0.25
# Display thresholds — NOT a score. A row whose two sides differ by more than
# these sorts first in the catalogue; nothing is summed or weighted.
TOL_WIDTH_MM, TOL_WIDTH_FRAC = 0.3, 0.25
TOL_DIRECTION_DEG = 15.0
TOL_PITCH_FRAC = 0.25
TOL_LAYERS = 1.0


# ------------------------------------------------------------------ passes
def passes_of(path: Path, transform=None):
    passes = passes_from_file(Path(path))
    if transform is None:
        return passes
    return [[transform(x, y) for x, y in p] for p in passes]


def segments(passes):
    return [(p[i], p[i + 1]) for p in passes for i in range(len(p) - 1)]


def length_mm(passes) -> float:
    return sum(math.dist(p[i], p[i + 1]) for p in passes for i in range(len(p) - 1))


def region_polys(pair: pf.Pair, reg: pf.Reg) -> list[tuple[str, Polygon]]:
    """Our region polygons in the PRO frame (mm y-down)."""
    out = []
    for r in pair.regions:
        poly = shapely.wkt.loads(r["wkt"])
        out.append((r["shape_id"], affine_transform(poly, reg.matrix())))
    return out


def assign_passes(passes, polys: list[tuple[str, Polygon]],
                  share: float = ASSIGN_SHARE, buffer_mm: float = ASSIGN_BUFFER_MM):
    buffered = [(sid, poly.buffer(buffer_mm)) for sid, poly in polys]
    per = {sid: [] for sid, _ in polys}
    residual = []
    for i, pts in enumerate(passes):
        if not pts:
            continue
        xs = np.array([p[0] for p in pts]); ys = np.array([p[1] for p in pts])
        best, best_share = None, 0.0
        for sid, poly in buffered:
            bx0, by0, bx1, by1 = poly.bounds
            if xs.max() < bx0 or xs.min() > bx1 or ys.max() < by0 or ys.min() > by1:
                continue
            inside = shapely.contains_xy(poly, xs, ys).mean()
            if inside > best_share:
                best, best_share = sid, float(inside)
        if best is not None and best_share >= share:
            per[best].append(i)
        else:
            residual.append(i)
    return per, residual


# ----------------------------------------------------------------- readers
def tier_of(passes) -> str:
    if not passes:
        return "none"
    m = satin_measure(passes)
    if m["share"] >= 0.5:
        return "satin"
    p = union_pitch(segments(passes))
    if p is not None and p["rows"] >= 3:
        return "fill"
    return "run"


def width_of(passes):
    m = satin_measure(passes) if passes else {"median_mm": None, "p90_mm": None}
    return m["median_mm"], m["p90_mm"]


def pitch_of(passes):
    p = union_pitch(segments(passes)) if passes else None
    return None if p is None else p["pitch_mm"]


def recipe_of(passes, cap: int = 6) -> str:
    toks = []
    for pts in passes[:cap]:
        toks.append(".".join(t for t, _n, _l in _phases(pts)))
    if len(passes) > cap:
        toks.append("…")
    return " | ".join(toks)


def direction_map(passes, bb):
    segs = [(a[0], a[1], b[0], b[1], math.dist(a, b), 0, False) for a, b in segments(passes)]
    ang, _typ, _tot = sc.cell_stats(segs, bb)
    return ang


def direction_in(ang_map, bb, poly: Polygon):
    x0, y0, _x1, _y1 = bb
    vals = []
    H, W = ang_map.shape
    for i in range(H):
        for j in range(W):
            if np.isnan(ang_map[i, j]):
                continue
            cx, cy = x0 + (j + 0.5) * sc.CELL, y0 + (i + 0.5) * sc.CELL
            if poly.covers(Point(cx, cy)):
                vals.append(math.degrees(ang_map[i, j]) % 180.0)
    if not vals:
        return None, 0.0
    modal, r = doubled_mean(vals, [1.0] * len(vals))
    return (None if modal is None else round(modal, 1)), round(r, 3)


def coverage_grid(passes):
    runs = [StitchRun(points=list(p), kind="satin", shape_id="x") for p in passes if len(p) >= 2]
    return _coverage_map(_Runs(runs), cell_mm=LAYER_CELL_MM) if runs else None


def layers_in(grid_origin, poly: Polygon):
    if grid_origin is None:
        return 0.0, 0.0
    grid, origin = grid_origin
    c = coverage_in(poly, grid, origin, LAYER_CELL_MM)
    return round(c["mean"], 2), round(c["p95"], 2)


def density_of(passes, area_mm2: float) -> float:
    area = max(area_mm2, 1e-9)
    return round(length_mm(passes) / area, 2)


def trims_in(passes) -> int:
    """Number of passes = number of lifts (jump/trim) landing inside the region."""
    return len(passes)


def side_stats(passes, poly: Polygon, ang_map, bb, cov):
    p50, p90 = width_of(passes)
    deg, r = direction_in(ang_map, bb, poly)
    l50, l95 = layers_in(cov, poly)
    return {
        "tier": tier_of(passes),
        "width_p50": None if p50 is None else round(p50, 2),
        "width_p90": None if p90 is None else round(p90, 2),
        "direction_deg": deg, "direction_R": r,
        "pitch_mm": (None if pitch_of(passes) is None else round(pitch_of(passes), 3)),
        "recipe": recipe_of(passes),
        "layers_p50": l50, "layers_p95": l95,
        "density": density_of(passes, poly.area),
        "stitches": sum(len(p) for p in passes),
        "trims": trims_in(passes),
    }


def region_rows(pair: pf.Pair, reg: pf.Reg):
    pro = passes_of(pair.pro_path)
    ours = passes_of(pair.ours_path, reg.apply_xy)
    polys = region_polys(pair, reg)
    pro_by, pro_res = assign_passes(pro, polys)
    our_by, our_res = assign_passes(ours, polys)
    allsegs = [(a[0], a[1], b[0], b[1], math.dist(a, b), 0, False) for a, b in segments(pro + ours)]
    bb = sc.bounds(allsegs)
    pro_ang = direction_map(pro, bb)
    our_ang = direction_map(ours, bb)
    pro_cov = coverage_grid(pro)
    our_cov = coverage_grid(ours)
    planned = {r["shape_id"]: r.get("tier") for r in pair.regions}
    rows = []
    for sid, poly in polys:
        pp = [pro[i] for i in pro_by[sid]]
        op = [ours[i] for i in our_by[sid]]
        rows.append({
            "shape_id": sid, "area_mm2": round(poly.area, 1), "tier_planned": planned.get(sid),
            "pro": side_stats(pp, poly, pro_ang, bb, pro_cov),
            "ours": side_stats(op, poly, our_ang, bb, our_cov),
        })
    residual = {"pro_passes": len(pro_res), "pro_mm": round(length_mm([pro[i] for i in pro_res]), 1),
                "ours_passes": len(our_res), "ours_mm": round(length_mm([ours[i] for i in our_res]), 1)}
    return rows, residual
