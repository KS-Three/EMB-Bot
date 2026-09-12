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


def assign_passes(passes, polys: list[tuple[str, Polygon]], buffer_mm: float = ASSIGN_BUFFER_MM):
    """Chunk each pass into the region it actually lies in (R14, amended R16).

    A professional file travels with the needle down between elements — on
    the Becker corpus file, 15 passes run to 33,330 mm total, median
    1,405 mm, longest 7,394 mm — so a single needle-down PASS routinely
    visits several of our regions, or none. Giving the WHOLE pass to
    whichever region holds the biggest share of it (the old rule) throws
    away most of a long pass's thread: measured 54% of the pro's thread
    landing in any region, the rest becoming residual.

    R16: label SEGMENTS by their midpoint, not points. Labelling points (R14)
    left the segment BETWEEN the last point of one chunk and the first point
    of the next belonging to no chunk at all — its length vanished from both
    `per_region` and `residual` — and on a heavily-fragmented file (our own
    thread, grown past the artwork polygon by pull compensation, shreds into
    thousands of short runs near every edge) that was most of the file:
    measured 18.6 m of the pro's 33.3 m and 12.1 m of ours' 33.6 m went
    unaccounted before this fix.

    Each SEGMENT (a pass's consecutive point pair) is labelled with the
    first buffered region polygon — in the order `polys` is given — whose
    buffer contains that segment's MIDPOINT, or left unlabelled if none does
    (`shapely.contains_xy`, vectorised over all of a pass's segment
    midpoints at once, same style `direction_in`'s grid lookup and the old
    point-labelling used). The pass is then cut into maximal runs of
    consecutive same-label segments; a run's chunk is that run's endpoints
    in order (so a chunk of `k` segments has `k + 1` points — still
    consecutive needle-down points, which is what `satin_columns.measure`
    and `union_pitch` need) and goes to that region's chunk list, or to
    residual when the run's label is no region. Every segment lands in
    exactly one chunk, so `length_mm` over `per_region`'s chunks plus
    `length_mm` over `residual` now equals `length_mm` over `passes` (up to
    float rounding) — nothing vanishes at a chunk boundary any more.

    -> (per_region: dict[shape_id, list[chunk]], residual: list[chunk],
        lifts: dict[shape_id, int]) — `lifts[sid]` is the number of
        DISTINCT SOURCE PASSES that contributed any chunk to that region
        (how many times the machine arrived there after a lift), which is
        NOT the same as the region's chunk count: one long pro pass can
        hand one region several chunks without the machine ever having
        lifted the needle over it more than once.
    """
    buffered = [(sid, poly.buffer(buffer_mm)) for sid, poly in polys]
    per: dict = {sid: [] for sid, _ in polys}
    lift_sources: dict = {sid: set() for sid, _ in polys}
    residual = []
    for pi, pts in enumerate(passes):
        m = len(pts) - 1     # number of segments
        if m < 1:
            continue
        p0 = np.array(pts[:-1]); p1 = np.array(pts[1:])
        mx = (p0[:, 0] + p1[:, 0]) / 2.0
        my = (p0[:, 1] + p1[:, 1]) / 2.0
        labels: list = [None] * m
        claimed = np.zeros(m, bool)
        for sid, poly in buffered:
            idx = np.flatnonzero(~claimed)
            if not len(idx):
                break
            inside = shapely.contains_xy(poly, mx[idx], my[idx])
            for k in idx[inside]:
                labels[k] = sid
            claimed[idx[inside]] = True
        i = 0
        while i < m:
            j = i + 1
            while j < m and labels[j] == labels[i]:
                j += 1
            chunk = pts[i:j + 1]    # the run's j-i segments' endpoints, in order
            sid = labels[i]
            if sid is not None:
                per[sid].append(chunk)
                lift_sources[sid].add(pi)
            else:
                residual.append(chunk)
            i = j
    lifts = {sid: len(sources) for sid, sources in lift_sources.items()}
    return per, residual, lifts


# ----------------------------------------------------------------- readers
def _measurable(passes):
    """Chunks of at least 3 points — the floor `satin_columns._crosses` needs
    before it can report any crossings at all (R17).

    A shorter chunk carries no crossing information in EITHER direction:
    `satin_columns.measure` still adds its penetrations to `total` while its
    own `crossing` can only ever read 0, so a 2-point fragment can only push
    `share` DOWN, never up — it cannot vote "satin", only dilute toward
    "not satin". Dropping the old point-level 3-point floor was required for
    `assign_passes`'s millimetre accounting to close (R16), but that let
    these un-evaluable fragments into the tier ratio: on the Becker pro
    file, 1,136 of 2,541 chunks are under 3 points, and the design's
    largest region — the BECKER outline, sewn as a satin keyline — read
    share 0.444 ("fill") with every chunk voting and 0.520 ("satin", the
    correct read) with only measurable chunks voting.

    Used by `tier_of` and `width_of` only. Density, stitches, trims,
    length, layers, direction and pitch all keep reading every chunk
    (unfiltered), so the millimetre accounting `assign_passes` closes to
    (Fix round 2) is untouched by this filter."""
    return [c for c in passes if len(c) >= 3]


def tier_of(passes) -> str:
    passes = _measurable(passes)
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
    passes = _measurable(passes)
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


def trims_in(lifts: int) -> int:
    """The number of distinct source passes (lifts) that landed a chunk in
    this region — how many times the machine arrived here after a lift.

    Not the region's own chunk count (R14): chunking a long professional
    pass at region boundaries can hand one region several chunks from a
    single pass, and counting those as separate trims would overstate how
    often the machine actually cut here. `assign_passes` computes the real
    count; this reader just names it."""
    return lifts


def side_stats(passes, poly: Polygon, ang_map, bb, cov, lifts: int):
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
        "trims": trims_in(lifts),
    }


def region_rows(pair: pf.Pair, reg: pf.Reg):
    pro = passes_of(pair.pro_path)
    ours = passes_of(pair.ours_path, reg.apply_xy)
    polys = region_polys(pair, reg)
    pro_by, pro_res, pro_lifts = assign_passes(pro, polys)
    our_by, our_res, our_lifts = assign_passes(ours, polys)
    allsegs = [(a[0], a[1], b[0], b[1], math.dist(a, b), 0, False) for a, b in segments(pro + ours)]
    bb = sc.bounds(allsegs)
    pro_ang = direction_map(pro, bb)
    our_ang = direction_map(ours, bb)
    pro_cov = coverage_grid(pro)
    our_cov = coverage_grid(ours)
    planned = {r["shape_id"]: r.get("tier") for r in pair.regions}
    rows = []
    for sid, poly in polys:
        pp = pro_by[sid]
        op = our_by[sid]
        rows.append({
            "shape_id": sid, "area_mm2": round(poly.area, 1), "tier_planned": planned.get(sid),
            "pro": side_stats(pp, poly, pro_ang, bb, pro_cov, pro_lifts[sid]),
            "ours": side_stats(op, poly, our_ang, bb, our_cov, our_lifts[sid]),
        })
    residual = {"pro_passes": len(pro_res), "pro_mm": round(length_mm(pro_res), 1),
                "ours_passes": len(our_res), "ours_mm": round(length_mm(our_res), 1)}
    return rows, residual
