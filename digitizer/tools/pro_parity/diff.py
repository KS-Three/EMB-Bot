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

import cv2
import numpy as np
import shapely
from PIL import Image
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
from digitizer_core.adapter import UNITS_PER_MM                         # noqa: E402
from digitizer_core.machine import FILL_ROW_MM                          # noqa: E402
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


# --------------------------------------------------------------- shape rows
def _art_ink(pair: pf.Pair):
    """The art's ink mask (`real_art.prepare`'s own rule: alpha > 16 where
    the image carries alpha, else RGB sum < 720) and its tight pixel bbox,
    (x0, y0, x1, y1) exclusive on the high end."""
    im = Image.open(pair.art).convert("RGBA")
    a = np.asarray(im)
    alpha = a[..., 3]
    if alpha.min() < 255:
        ink = alpha > 16
    else:
        ink = a[..., :3].astype(np.int32).sum(axis=2) < 720
    ys, xs = np.nonzero(ink)
    if not len(xs):
        return ink, (0, 0, ink.shape[1], ink.shape[0])
    return ink, (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)


def _art_meta_scale_origin(pair: pf.Pair):
    """`(px_per_mm, origin_mm)` from a synthetic fixture's `art_meta.json`
    sidecar, or `None` when there is no such file or it does not carry
    those two keys.

    R2 (controller ruling): `proloop_synth.make_prep_dir` writes this exact
    sidecar, in OURS mm (the frame `art_ink_boxes_mm` was drawn in), so
    reading it is exact -- no bbox-matching approximation needed. A REAL
    prep dir has no sidecar at all (`prep_all.run_ours` never writes one);
    `prep_all.main()`'s own corpus-reconstruction pipeline writes a
    DIFFERENTLY SHAPED `art_meta.json` (scale/palette/per-block
    measurements, no `px_per_mm`/`origin_mm`) for a different purpose, so
    checking for the two keys -- not just the file's existence -- is what
    keeps this branch from misreading that file."""
    p = pair.art.parent / "art_meta.json"
    if not p.exists():
        return None
    try:
        meta = json.loads(p.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    if "px_per_mm" not in meta or "origin_mm" not in meta:
        return None
    ox, oy = meta["origin_mm"]
    return float(meta["px_per_mm"]), (float(ox), float(oy))


def _our_regions_bbox_mm(pair: pf.Pair):
    """Union bbox of our OWN region polygons, in OURS mm (pre-`reg`) --
    `None` when there are no regions to bound."""
    if not pair.regions:
        return None
    bounds = [shapely.wkt.loads(r["wkt"]).bounds for r in pair.regions]
    return (min(b[0] for b in bounds), min(b[1] for b in bounds),
            max(b[2] for b in bounds), max(b[3] for b in bounds))


def _art_to_ours_affine(pair: pf.Pair, ink_bbox_px) -> np.ndarray:
    """Art-pixel -> OURS-mm 2x3 affine.

    R2 (controller ruling): the brief's original approach stretched the
    art's ink bbox onto OUR STITCH EXTENTS, per axis -- wrong whenever the
    two differ, which is exactly when there is something to find (an
    ours-only bar sewn outside the art grows our stitch extent without
    moving the ink at all, so that mapping silently rescales the ink to
    fit around our own defect). Mapped here instead:

      1. A synthetic fixture's own `art_meta.json` (px_per_mm + origin_mm)
         is exact -- used directly, no approximation.
      2. A real prep dir has no such sidecar. One uniform scale (not
         per-axis) is derived from OUR REGIONS' union bbox against the
         ink's pixel bbox, centred on each other. Regions are themselves
         derived from the artwork (`write_regions`'s `res.regions`), so
         they track the ink even where we drop or add an element; our
         stitch extents do not.
    """
    ix0, iy0, ix1, iy1 = ink_bbox_px
    meta = _art_meta_scale_origin(pair)
    if meta is not None:
        ppm, (ox, oy) = meta
        s = 1.0 / ppm
        return np.array([[s, 0.0, ox], [0.0, s, oy]])
    bbox = _our_regions_bbox_mm(pair)
    if bbox is None:
        raise ValueError(f"{pair.slug}: no art_meta.json sidecar and no regions to place the art by")
    rx0, ry0, rx1, ry1 = bbox
    icx, icy = (ix0 + ix1) / 2.0, (iy0 + iy1) / 2.0
    rcx, rcy = (rx0 + rx1) / 2.0, (ry0 + ry1) / 2.0
    s = (rx1 - rx0) / max(ix1 - ix0, 1)
    return np.array([[s, 0.0, rcx - icx * s], [0.0, s, rcy - icy * s]])


def _compose(*mats):
    """2x3 affines, applied left to right, composed into one 2x3."""
    M = np.eye(3)
    for m in mats:
        m3 = np.vstack([np.asarray(m, dtype=np.float64), [0, 0, 1]])
        M = m3 @ M
    return M[:2]


def ink_mask_in_frame(pair: pf.Pair, reg: pf.Reg, frame: pf.Frame) -> np.ndarray:
    """The art's ink, warped into the overlay `frame`: art px -> ours mm
    (`_art_to_ours_affine`, R2) -> pro mm (`reg.matrix()`) -> frame px
    (`frame.mm_to_px_affine()`), composed into one affine for a single
    `cv2.warpAffine` (nearest, so the mask stays boolean)."""
    ink, ink_bbox_px = _art_ink(pair)
    art_to_ours = _art_to_ours_affine(pair, ink_bbox_px)
    a, b, d, e, xoff, yoff = reg.matrix()
    ours_to_pro = np.array([[a, b, xoff], [d, e, yoff]])
    M = _compose(art_to_ours, ours_to_pro, frame.mm_to_px_affine())
    W, H = frame.size
    warped = cv2.warpAffine(ink.astype(np.uint8), M, (W, H), flags=cv2.INTER_NEAREST, borderValue=0)
    return warped > 0


def _components(mask: np.ndarray, frame: pf.Frame, dust_mm2: float):
    """Connected components of `mask` (8-connectivity) in frame pixels,
    split into `big` (each `{area_mm2, centre_mm, bbox_mm}`) and everything
    under `dust_mm2` summed into `(dust_area_mm2, dust_count)`."""
    n, _lab, stats, cents = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    px_area = 1.0 / (frame.ppm ** 2)
    big, dust_area, dust_n = [], 0.0, 0
    for k in range(1, n):
        area = stats[k, cv2.CC_STAT_AREA] * px_area
        if area < dust_mm2:
            dust_area += area
            dust_n += 1
            continue
        cx, cy = cents[k]
        X = cx / frame.ppm + frame.x0_units / UNITS_PER_MM - frame.pad_mm
        Y = cy / frame.ppm - frame.y1_units / UNITS_PER_MM - frame.pad_mm
        x, y, w, h = (stats[k, cv2.CC_STAT_LEFT], stats[k, cv2.CC_STAT_TOP],
                      stats[k, cv2.CC_STAT_WIDTH], stats[k, cv2.CC_STAT_HEIGHT])
        bx0 = x / frame.ppm + frame.x0_units / UNITS_PER_MM - frame.pad_mm
        by0 = y / frame.ppm - frame.y1_units / UNITS_PER_MM - frame.pad_mm
        # float(...) before round(): cv2's stats/centroids are numpy float64,
        # and numpy >= 2's repr renders that as "np.float64(35.9)" inside a
        # list -- exactly the value `write_catalogue`'s shape tables print.
        # Plain Python floats keep the catalogue's "centre" column readable.
        big.append({"area_mm2": round(float(area), 1), "centre_mm": [round(float(X), 1), round(float(Y), 1)],
                    "bbox_mm": [round(float(bx0), 1), round(float(by0), 1),
                                round(float(bx0 + w / frame.ppm), 1), round(float(by0 + h / frame.ppm), 1)]})
    return big, dust_area, dust_n


def shape_rows(pair: pf.Pair, reg: pf.Reg, r: dict, dust_mm2: float = 2.0) -> list:
    """The shape half of the catalogue (Task 11): components of the
    overlay's `pro_only`/`ours_only` masks, tagged by Kent's ruling --

      pro_only & ink   -> dropped     (our defect: we left art unsewn)
      pro_only & ~ink  -> redesign    (the pro added thread the art lacks)
      ours_only & ~ink -> background  (our defect: we sewed ground)
      ours_only & ink  -> redesign    (the pro left art unsewn, or merged it)

    Every row also carries `sewn_by`, `"pro"` or `"ours"` -- the side whose
    thread the row IS (R18, controller ruling, fix round 1: `redesign`
    covers two opposite situations -- the pro adding thread, or the pro
    leaving/merging art we sewed -- and Kent needs to tell them apart
    without the tags themselves splitting).

    Each big row is `{tag, sewn_by, area_mm2, centre_mm, nearest_region,
    crop}`; components under `dust_mm2` are summed into ONE dust row PER
    TAG (fix round 1, finding 1: `redesign` is TWO buckets below --
    `pro_only & ~ink` and `ours_only & ink` -- and dust from both must
    land in the same row, not one each), `{tag, dust: True, area_mm2,
    count, sewn_by}` where `sewn_by` is `"pro"`/`"ours"` when only that
    tag's dust came from one side, else `"mixed"`. Sorted biggest-first,
    dust rows last."""
    frame = r["frame"]
    ink = ink_mask_in_frame(pair, reg, frame)
    polys = region_polys(pair, reg)
    buckets = [("dropped", "pro", r["pro_only"] & ink),
               ("redesign", "pro", r["pro_only"] & ~ink),
               ("background", "ours", r["ours_only"] & ~ink),
               ("redesign", "ours", r["ours_only"] & ink)]
    rows = []
    dust: dict = {}    # tag -> {"area_mm2", "count", "sides"} -- accumulated across buckets
    for tag, sewn_by, mask in buckets:
        big, dust_area, dust_n = _components(mask, frame, dust_mm2)
        for c in big:
            pt = Point(c["centre_mm"])
            nearest = min(polys, key=lambda sp: sp[1].distance(pt))[0] if polys else None
            x0, y0, x1, y1 = c["bbox_mm"]
            m = 1.0
            rows.append({"tag": tag, "sewn_by": sewn_by, **c, "nearest_region": nearest,
                         "crop": f"--crop {x0 - m:.1f} {y0 - m:.1f} {x1 + m:.1f} {y1 + m:.1f}"})
        if dust_n:
            acc = dust.setdefault(tag, {"area_mm2": 0.0, "count": 0, "sides": set()})
            acc["area_mm2"] += dust_area
            acc["count"] += dust_n
            acc["sides"].add(sewn_by)
    for tag, acc in dust.items():
        sewn_by = next(iter(acc["sides"])) if len(acc["sides"]) == 1 else "mixed"
        rows.append({"tag": tag, "dust": True, "area_mm2": round(acc["area_mm2"], 1),
                     "count": acc["count"], "sewn_by": sewn_by})
    rows.sort(key=lambda x: (x.get("dust", False), -x["area_mm2"]))
    return rows


# --------------------------------------------------------------------- flags
def _ang_dist(a, b):
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def flag_row(row: dict) -> list:
    """The columns on which pro and ours differ past a DISPLAY threshold
    (Spec §5; controller ruling: no score, no ranking anywhere — these
    thresholds decide sort order only, nothing is summed or weighted).

    `density` is never checked here: row/fill pitch is a RULED CONSTANT
    (`machine.FILL_ROW_MM`), not a target either side is being graded
    against, so a density difference is reported in the table and never
    flagged."""
    p, o = row["pro"], row["ours"]
    flags = []
    if p["tier"] != o["tier"] and "none" not in (p["tier"], o["tier"]):
        flags.append("tier")
    if p.get("width_p50") is not None and o.get("width_p50") is not None:
        d = abs(p["width_p50"] - o["width_p50"])
        # Spec §5: "differs by more than a stated tolerance (width ±0.3 mm
        # or 25%)" -- an OR of an absolute floor and a relative one, so a
        # coarse 2.0mm-vs-2.6mm column (0.6mm, over the floor alone) still
        # flags even though it is under 25% of the pro's 2.6mm width.
        if d > TOL_WIDTH_MM or d > TOL_WIDTH_FRAC * p["width_p50"]:
            flags.append("width")
    if (p.get("direction_deg") is not None and o.get("direction_deg") is not None
            and p.get("direction_R", 0) >= 0.5 and o.get("direction_R", 0) >= 0.5
            and _ang_dist(p["direction_deg"], o["direction_deg"]) > TOL_DIRECTION_DEG):
        flags.append("direction")
    if p.get("pitch_mm") is not None and o.get("pitch_mm") is not None:
        if abs(p["pitch_mm"] - o["pitch_mm"]) > TOL_PITCH_FRAC * p["pitch_mm"]:
            flags.append("pitch")
    if abs(p.get("layers_p50", 0) - o.get("layers_p50", 0)) > TOL_LAYERS:
        flags.append("layers")
    return flags


def _blocks_of(path: Path, transform=None):
    """Passes per colour block of a machine file, same split rule as passes_of."""
    import pystitch
    pat = pystitch.read(str(path))
    blocks, cur, bi = {}, [], 0
    rgb = [(t.get_red(), t.get_green(), t.get_blue()) for t in pat.threadlist]
    for x, y, c in pat.stitches:
        cmd = c & pystitch.COMMAND_MASK
        if cmd == pystitch.STITCH:
            p = (x / 10.0, y / 10.0)
            cur.append(transform(*p) if transform else p)
            continue
        if len(cur) >= 3:
            blocks.setdefault(bi, []).append(cur)
        cur = []
        if cmd in (pystitch.COLOR_CHANGE, pystitch.STOP):
            bi += 1
    if len(cur) >= 3:
        blocks.setdefault(bi, []).append(cur)
    return blocks, rgb


def _extent_of(passes) -> list:
    """[width, height] mm spanned by a side's own stitch points, in whatever
    frame `passes` is already in. `design_rows` calls this AFTER each side's
    own transform (`reg.apply_xy` for ours, none for pro), so both numbers
    land in the one registered frame (R12, controller ruling)."""
    xs = [x for p in passes for x, _y in p]
    ys = [y for p in passes for _x, y in p]
    if not xs:
        return [0.0, 0.0]
    return [round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)]


def design_rows(pair: pf.Pair, reg: pf.Reg) -> dict:
    """Design-level counts per side: stitches, trims (= passes), blocks,
    cones (distinct rgb), the sew order, and each side's own stitch
    `extent_mm` (R12, controller ruling) — width/height in the registered
    frame. The first real overlay showed our Becker about 3% taller than
    the pro's at the same width; an aspect mismatch is a finding the craft
    rows (all per-region) cannot show on their own."""
    polys = region_polys(pair, reg)
    out = {}
    for side, path, tr, rgbs in (("pro", pair.pro_path, None, pair.pro_rgb),
                                 ("ours", pair.ours_path, reg.apply_xy, pair.ours_rgb)):
        blocks, file_rgb = _blocks_of(path, tr)
        rgb = rgbs or file_rgb
        order = []
        for bi in sorted(blocks):
            per, _res, _lifts = assign_passes(blocks[bi], polys)
            top = max(per.items(), key=lambda kv: length_mm(kv[1]), default=(None, []))
            order.append({"block": bi, "rgb": list(rgb[bi]) if bi < len(rgb) else None,
                          "mm": round(length_mm(blocks[bi]), 1), "mostly": top[0]})
        passes = [p for b in blocks.values() for p in b]
        out[side] = {"stitches": sum(len(p) for p in passes), "trims": len(passes),
                     "blocks": len(blocks), "cones": len({tuple(r) for r in rgb[:max(len(blocks), 1)]}),
                     "sew_order": order, "extent_mm": _extent_of(passes)}
    return out


def _fmt(v):
    if v is None:
        return "—"
    if isinstance(v, float):
        return f"{v:.2f}"
    return str(v)


def _row_line(row, flags):
    p, o = row["pro"], row["ours"]
    cells = [row["shape_id"], _fmt(row["area_mm2"]), ",".join(flags) or "",
             f"{o['tier']} / {p['tier']}" + (f" (planned {row['tier_planned']})" if row.get("tier_planned") else ""),
             f"{_fmt(o['width_p50'])} / {_fmt(p['width_p50'])}",
             f"{_fmt(o['direction_deg'])} / {_fmt(p['direction_deg'])}",
             f"{_fmt(o['pitch_mm'])} / {_fmt(p['pitch_mm'])}",
             f"{_fmt(o['layers_p50'])} / {_fmt(p['layers_p50'])}",
             f"{_fmt(o['density'])} / {_fmt(p['density'])}",
             f"{o['trims']} / {p['trims']}",
             f"`{o['recipe'][:40]}` / `{p['recipe'][:40]}`"]
    return "| " + " | ".join(cells) + " |"


_HEAD = ("| region | mm² | flags | tier ours / pro | width p50 | direction | pitch | layers | "
         "density (reported, not flagged) | trims (distinct passes, not lifts) | recipe |\n"
         "|---|---:|---|---|---|---|---|---|---|---|---|")

# Controller ruling: density and trims get their caveat said in the catalogue
# text itself, beside the table they head — not only in a source comment.
_CRAFT_NOTE = (
    "`density` is reported here and never flagged: row/fill pitch is a ruled constant "
    f"(`machine.FILL_ROW_MM` = {FILL_ROW_MM} mm), not a target either side is graded against. "
    "`trims` counts distinct SOURCE PASSES that contributed thread to a region (a lift count), "
    "not the region's own chunk count — chunking a long pro pass at a region boundary can hand "
    "one region several chunks from a single lift.")


def write_catalogue(pair, reg, rows, residual, design, shapes, out_dir):
    out_dir = Path(out_dir)
    flagged = [(r, flag_row(r)) for r in rows]
    flagged = [(r, f) for r, f in flagged if f]
    flagged.sort(key=lambda rf: (-len(rf[1]), -rf[0]["area_mm2"]))
    lines = [f"# {pair.slug} — ours vs pro, {pair.width_mm:.1f} mm",
             f"registration iou {reg.iou:.3f}, scale {reg.scale:.3f}, flip_y {reg.flip_y}, "
             f"shift ({reg.dx:.1f}, {reg.dy:.1f}) mm. Tolerances are display thresholds, not a score.", ""]
    if reg.iou < 0.5:
        lines += ["**Registration is unreliable (iou < 0.5): read the shape rows as indicative only.**", ""]
    # Craft table (Spec §5): one row per region, never truncated (controller ruling —
    # only the shape tables below get a per-tag display cap).
    lines += ["## Flagged", "", _CRAFT_NOTE, "", _HEAD] + [_row_line(r, f) for r, f in flagged] + [""]
    lines += ["## All regions", "", _CRAFT_NOTE, "", _HEAD] + [_row_line(r, flag_row(r)) for r in rows] + [""]
    lines += ["## Design", "", "| | ours | pro |", "|---|---:|---:|"]
    for k in ("stitches", "trims", "blocks", "cones"):
        lines.append(f"| {k} | {design['ours'][k]} | {design['pro'][k]} |")
    ow, oh = design["ours"]["extent_mm"]
    pw, ph = design["pro"]["extent_mm"]
    lines.append(f"| width mm | {ow:.1f} | {pw:.1f} |")
    lines.append(f"| height mm | {oh:.1f} | {ph:.1f} |")
    lines.append(f"| aspect h/w | {(oh / ow if ow else 0.0):.3f} | {(ph / pw if pw else 0.0):.3f} |")
    lines += ["", "sew order ours: " + " → ".join(f"{b['block']}({b['mostly']})" for b in design["ours"]["sew_order"]),
              "sew order pro: " + " → ".join(f"{b['block']}({b['mostly']})" for b in design["pro"]["sew_order"]), ""]
    lines += ["## Residual (passes assigned to no region)", "",
              f"pro {residual['pro_passes']} passes / {residual['pro_mm']} mm; "
              f"ours {residual['ours_passes']} passes / {residual['ours_mm']} mm", ""]
    kent = [s for s in shapes if s["tag"] == "redesign"]
    ours_rows = [s for s in shapes if s["tag"] in ("dropped", "background")]

    def shape_table(items, limit=15):
        """15 largest (by area) rows per TAG, most-severe first (R19,
        controller ruling: Becker alone produces 373 shape rows over the
        dust floor — unreadable in full). Every row still reaches
        `diff.json` through the caller's own `shapes` list; only this
        markdown table is capped. A tag with more than `limit` big rows
        gets one trailing line reading `and N more, X mm² total`."""
        order, groups = [], {}
        for s in items:
            g = groups.setdefault(s["tag"], {"big": [], "dust": None})
            if s["tag"] not in order:
                order.append(s["tag"])
            if s.get("dust"):
                g["dust"] = s
            else:
                g["big"].append(s)
        t = ["| tag | sewn_by | mm² | centre | nearest region | crop |", "|---|---|---:|---|---|---|"]
        notes = []
        for tag in order:
            g = groups[tag]
            big = sorted(g["big"], key=lambda s: -s["area_mm2"])
            shown, rest = big[:limit], big[limit:]
            for s in shown:
                t.append(f"| {s['tag']} | {s['sewn_by']} | {s['area_mm2']} | {s['centre_mm']} | "
                        f"{s['nearest_region']} | `{s['crop']}` |")
            if rest:
                notes.append(f"*{tag}: and {len(rest)} more, "
                             f"{round(sum(r['area_mm2'] for r in rest), 1)} mm² total*")
            if g["dust"] is not None:
                d = g["dust"]
                t.append(f"| {d['tag']} (dust) | {d['sewn_by']} | {d['area_mm2']} | {d['count']} pieces | | |")
        return t, notes

    kent_t, kent_notes = shape_table(kent)
    ours_t, ours_notes = shape_table(ours_rows)
    lines += ["## Shape rows — Kent's call (the pro departed from the artwork)", ""] + kent_t + kent_notes + [""]
    lines += ["## Shape rows — ours (dropped elements, sewn background)", ""] + ours_t + ours_notes + [""]
    md = out_dir / "catalogue.md"
    md.write_text("\n".join(lines), encoding="utf-8")
    js = out_dir / "diff.json"
    js.write_text(json.dumps({"slug": pair.slug, "width_mm": pair.width_mm, "registration": reg.as_dict(),
                              "flagged": [dict(r, flags=f) for r, f in flagged], "regions": rows,
                              "residual": residual, "design": design, "shapes": shapes}, indent=1, default=str))
    return md, js


def main(argv=None) -> int:
    import overlay
    from thin_strokes import parse_flags
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--dir")
    ap.add_argument("--slug")
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--ppm", type=float, default=overlay.DEFAULT_PPM)
    a = ap.parse_args(argv)
    pair = pf.load_pair(overlay._resolve_dir(a))
    flags = parse_flags(a.flag)
    if flags:
        pair = pf.load_pair(pf.redigitize(pair, flags))
    reg = pf.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = region_rows(pair, reg)
    r = overlay.render_pair(pair, reg, ppm=a.ppm)
    shapes = shape_rows(pair, reg, r)
    md, js = write_catalogue(pair, reg, rows, residual, design_rows(pair, reg), shapes, pair.dir)
    print(f"{pair.slug}  iou {reg.iou:.2f}  scale {reg.scale:.3f}  → {md}")
    for row in rows:
        f = flag_row(row)
        if f:
            p, o = row["pro"], row["ours"]
            bits = []
            if "tier" in f: bits.append(f"tier: ours {o['tier']} / pro {p['tier']}")
            if "width" in f: bits.append(f"width: {_fmt(o['width_p50'])} / {_fmt(p['width_p50'])}")
            if "direction" in f: bits.append(f"direction: {_fmt(o['direction_deg'])} / {_fmt(p['direction_deg'])}")
            if "pitch" in f: bits.append(f"pitch: {_fmt(o['pitch_mm'])} / {_fmt(p['pitch_mm'])}")
            if "layers" in f: bits.append(f"layers: {_fmt(o['layers_p50'])} / {_fmt(p['layers_p50'])}")
            print(f"  {row['shape_id']:>12}  " + "   ".join(bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
