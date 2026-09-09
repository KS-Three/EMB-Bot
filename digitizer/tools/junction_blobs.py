"""Every junction of the satin skeleton as a BLOB, with what the merge did
there and what the thread did to it — the instrument for item 5, PR 3
(quality review 2026-09-08; the pro's A apex: the blob sewn as one column,
the arms ending on it).

A junction node's medial ball is bigger than its arms' — that is what a
junction IS to the distance transform — and the arms' columns, each sized by
a ray that reads its own arm, meet inside it. What happens there today is
one of four things `_merge_through_junctions` decides: two arms WELD straight
through, an arm takes the CORNER (a capped free end, extended across the
blob), an arm TUCKS under a named owner, or an arm ENDS at a junction of
three or more and clears the blob by `_junction_entry_mm`. The render shows
the cost at the A's apex and the R's join (the corner cap's 5-6 mm crosses
sweep the square the butting member also covers) and at the K's crotch
(nobody covers it). This reads all of it as numbers:

  per blob    the node's radius against its arms' half-widths, the arm
              count, the merge's decision at each arm, the blob's area, the
              thread inside it as coverage LAYERS (`preflight._coverage_map`'s
              own units: mean, p95, max), its bare fraction, the seam
              crossing pairs seated in it
  per shape   the DT p90 over the ARMS alone (skeleton pixels outside every
              blob) against the full skeleton's, and the classifier's verdict
              at the shipped ceiling and the wide one

The blob is the union of the medial balls on the skeleton between the node
and each arm's EXIT — the first pixel along the arm whose ball is no bigger
than the arm's own (its median radius past one half-width from the node,
with `BLOB_TOL` of slack) — clipped to the artwork. A clean T has no blob
beyond the node's own ball: its node reads the bar's half-width. A bold
letter's apex reads a ball half again the legs', and the blob is exactly
the region those bigger balls cover. (`_junction_entry_mm`'s "stops
narrowing" walk was tried first and swallowed 80-98% of MARINE's skeleton
at 100 mm: on a bold letter the corridor never plateaus within its reach.)

Usage:
  python tools/junction_blobs.py [--widths 80 100] [--flag NAME[=VALUE] ...]
                                 [--json PATH] [--render DIR] [--top N] [cases ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

import numpy as np
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize, machine                 # noqa: E402
from digitizer_core import stage6_satin as s6                               # noqa: E402
from digitizer_core import stage7_sequence as s7                            # noqa: E402
from digitizer_core.preflight import _coverage_map, _COVERAGE_FLOOR_UNITS   # noqa: E402
from digitizer_core.stitches import StitchRun, strip_ties                   # noqa: E402
from curve_tiers import CASES                                                # noqa: E402
from letterforms import crossing_seats                                       # noqa: E402
from thin_strokes import parse_flags                                         # noqa: E402

ROOT = HERE.parent
RATIO_BINS = ((1.15, "<=1.15"), (1.4, "<=1.4"), (1.8, "<=1.8"), (math.inf, ">1.8"))
COVER_CELL_MM = 0.25
# A ball this fraction bigger than the arm's own is still the arm.
BLOB_TOL = 0.15


class _Runs:
    """The one method `_coverage_map` reads off a plan, over one shape's runs."""

    def __init__(self, runs):
        self._runs = runs

    def iter_runs(self):
        for r in self._runs:
            yield None, r


def skeleton_graph(poly: Polygon):
    """-> (edges after clustering, half_mm, field, scale, to_mm, dt_mm) built
    exactly as `extract_strokes` builds them, so the nodes here are the nodes
    the merge sees."""
    mask, scale, ox, oy = s6._rasterize(poly)
    if not mask.any():
        return None
    from skimage.morphology import medial_axis
    skel, dist = medial_axis(mask > 0, return_distance=True, rng=0)
    skel = s6._collapse_pinholes(skel)
    skel_mask = skel.astype(np.uint8)
    half_px = float(dist[skel].mean()) if skel.any() else 0.0
    field = s6._WidthField(dist=dist, scale=scale, ox=ox, oy=oy)
    s6._prune_spurs(skel_mask, max(3.0, half_px * 1.6))
    if not skel_mask.any():
        return None

    def to_mm(p):
        return (ox + (p[0] + 0.5) / scale, oy + (p[1] + 0.5) / scale)

    def dt_mm(p):
        return float(dist[p[1], p[0]]) / scale

    edges = s6._cluster_junctions(
        s6._skeleton_edges(skel_mask),
        max(s6._JUNCTION_CLUSTER_MIN_PX, s6._JUNCTION_CLUSTER_HALFWIDTHS * half_px),
        dt_mm)
    return edges, half_px / scale, field, scale, to_mm, dt_mm, skel_mask, dist


def merge_decisions(edges, dt_mm, half_mm, scale):
    """What `_merge_through_junctions` did at every node: node -> list of
    (edge index, at_start, decision) with decision in weld / corner / tuck /
    end / dropped (a corner fork removed outright)."""
    merged = s6._merge_through_junctions(edges, dt_mm, half_mm, scale)
    nodes: dict[tuple, list] = {}
    for i, e in enumerate(edges):
        if e["closed"]:
            continue
        for at_start, free in ((True, e["free_start"]), (False, e["free_end"])):
            if free:
                continue
            node = e["pts"][0] if at_start else e["pts"][-1]
            nodes.setdefault(node, []).append((i, at_start))
    # the merged chains, indexed by every pixel they contain (an X crossing
    # puts two chains through one node)
    interior: dict[tuple, list] = {}
    ends: dict[tuple, list] = {}
    for ci, c in enumerate(merged):
        pts = c["pts"]
        for p in pts[1:-1]:
            interior.setdefault(p, []).append(ci)
        for at_start in (True, False):
            p = pts[0] if at_start else pts[-1]
            ends.setdefault(p, []).append((ci, at_start, c))
    out = {}
    for node, arms in nodes.items():
        rows = []
        for i, at_start in arms:
            e = edges[i]
            decision = "dropped"
            nxt = e["pts"][1] if at_start else e["pts"][-2]
            for ci in interior.get(node, []):
                # an arm whose pixels continue through the node in one chain
                if nxt in merged[ci]["pts"]:
                    decision = "weld"
                    break
            if decision == "dropped":
                for ci, cs, c in ends.get(node, []):
                    nxt = e["pts"][1] if at_start else e["pts"][-2]
                    seq = c["pts"][:3] if cs else c["pts"][-3:]
                    if nxt in seq:
                        if c.get("capped_start" if cs else "capped_end"):
                            decision = "corner"
                        elif c.get("tuck_under_start" if cs else "tuck_under_end") is not None:
                            decision = "tuck"
                        else:
                            decision = "end"
                        break
            rows.append((i, at_start, decision))
        out[node] = rows
    return out, merged


def blob_of(node, arms, edges, field, half_mm, to_mm, dt_mm, poly):
    """The union of the medial balls between the node and each arm's exit,
    clipped to the artwork -> (polygon, exits_mm, arm_halves_mm)."""
    r0 = dt_mm(node)
    balls = [Point(to_mm(node)).buffer(max(r0, 0.05))]
    exits = []
    halves = []
    for i, at_start in arms:
        e = edges[i]
        pts = e["pts"] if at_start else list(reversed(e["pts"]))
        radii = [dt_mm(p) for p in pts]
        cum = [0.0]
        for a, b in zip(pts, pts[1:]):
            cum.append(cum[-1] + math.dist(to_mm(a), to_mm(b)))
        # the arm's own half-width: the median ball past one half-width from
        # the node (the whole far half of a short arm)
        far = [r for r, s in zip(radii, cum) if s >= min(half_mm, cum[-1] / 2.0)]
        arm_half = sorted(far)[len(far) // 2] if far else radii[-1]
        halves.append(arm_half)
        limit = arm_half * (1.0 + BLOB_TOL)
        exit_mm = 0.0
        for k in range(1, len(pts)):
            if radii[k] <= limit or cum[k] > 3.0 * r0:
                break
            balls.append(Point(to_mm(pts[k])).buffer(max(radii[k], 0.05)))
            exit_mm = cum[k]
        exits.append(exit_mm)
    blob = unary_union(balls).intersection(poly)
    if blob.geom_type != "Polygon":
        parts = [g for g in getattr(blob, "geoms", []) if g.geom_type == "Polygon"]
        blob = max(parts, key=lambda g: g.area) if parts else Polygon()
    return blob, exits, halves


def coverage_in(blob: Polygon, grid, origin, cell_mm: float) -> dict:
    """Coverage layers of the cells whose centres fall inside the blob."""
    if blob.is_empty or grid is None:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0, "bare": 1.0, "cells": 0}
    x0, y0 = origin
    bx0, by0, bx1, by1 = blob.bounds
    i0, i1 = int((bx0 - x0) / cell_mm), int((bx1 - x0) / cell_mm) + 1
    j0, j1 = int((by0 - y0) / cell_mm), int((by1 - y0) / cell_mm) + 1
    vals = []
    prepared = blob.buffer(1e-6)
    for j in range(max(0, j0), min(grid.shape[0], j1 + 1)):
        for i in range(max(0, i0), min(grid.shape[1], i1 + 1)):
            cx, cy = x0 + (i + 0.5) * cell_mm, y0 + (j + 0.5) * cell_mm
            if prepared.covers(Point(cx, cy)):
                vals.append(float(grid[j, i]))
    if not vals:
        return {"mean": 0.0, "p95": 0.0, "max": 0.0, "bare": 1.0, "cells": 0}
    a = np.asarray(vals)
    return {"mean": round(float(a.mean()), 2), "p95": round(float(np.percentile(a, 95)), 2),
            "max": round(float(a.max()), 2),
            "bare": round(float((a < _COVERAGE_FLOOR_UNITS).mean()), 3), "cells": len(vals)}


def shape_census(shape_id: str, poly: Polygon, runs: list[StitchRun], max_width_mm: float,
                 wide_mm: float) -> tuple[list[dict], dict | None]:
    g = skeleton_graph(poly)
    if g is None:
        return [], None
    edges, half_mm, field, scale, to_mm, dt_mm, skel_mask, dist = g
    decisions, merged = merge_decisions(edges, dt_mm, half_mm, scale)
    cov = _coverage_map(_Runs(runs), cell_mm=COVER_CELL_MM) if runs else None
    grid, origin = cov if cov is not None else (None, (0.0, 0.0))
    seats = []
    for r in runs:
        if r.kind == "satin":
            seats.extend(c for c, _ang in crossing_seats(s6.strip_splits(strip_ties(r.points))))
    blobs = []
    blob_polys = []
    for node, arms in decisions.items():
        blob, exits, halves = blob_of(node, [(i, s) for i, s, _d in arms], edges, field,
                                      half_mm, to_mm, dt_mm, poly)
        blob_polys.append(blob)
        r0 = dt_mm(node)
        arm_half = float(np.mean(halves)) if halves else half_mm
        c = coverage_in(blob, grid, origin, COVER_CELL_MM)
        inside = blob.buffer(1e-6)
        n_seats = sum(1 for s in seats if inside.covers(Point(s)))
        kinds = Counter(d for _i, _s, d in arms)
        blobs.append({"shape_id": shape_id, "node_mm": tuple(round(v, 2) for v in to_mm(node)),
                      "arms": len(arms), "decisions": dict(kinds),
                      "node_r_mm": round(r0, 2), "arm_half_mm": round(arm_half, 2),
                      "ratio": round(r0 / arm_half, 2) if arm_half > 0 else None,
                      "exits_mm": [round(e, 2) for e in exits],
                      "area_mm2": round(blob.area, 2), "coverage": c, "seam_pairs": n_seats,
                      "half_mm": round(half_mm, 2)})
    # the arm-only width statistic: skeleton pixels outside every blob
    ys, xs = np.nonzero(skel_mask)
    union = unary_union([b for b in blob_polys if not b.is_empty]) if blob_polys else Polygon()
    r_all = np.asarray([dt_mm((x, y)) for x, y in zip(xs, ys)])
    if not union.is_empty:
        keep = np.asarray([not union.covers(Point(to_mm((x, y)))) for x, y in zip(xs, ys)])
    else:
        keep = np.ones(len(xs), bool)
    r_arms = r_all[keep] if keep.any() else r_all
    v_ship = s6.classify_ribbon(poly, max_width_mm, full_metrics=True)
    v_wide = s6.classify_ribbon(poly, wide_mm, full_metrics=True)
    shape = {"shape_id": shape_id, "half_mm": round(half_mm, 2), "blobs": len(blobs),
             "p90_full_mm": round(2.0 * float(np.percentile(r_all, 90)), 2) if len(r_all) else None,
             "p90_arms_mm": round(2.0 * float(np.percentile(r_arms, 90)), 2) if len(r_arms) else None,
             "classifier_p90_mm": round(v_ship.metrics.get("dt_p90_mm", 0.0), 2),
             "verdict_ship": v_ship.reason, "verdict_wide": v_wide.reason,
             "blob_frac": round(1.0 - float(keep.mean()), 3) if len(keep) else 0.0}
    return blobs, shape


def scan(case: str, rel: str, kw: dict, width_mm: float | None, flags: dict) -> dict:
    seen: list[tuple[str, object]] = []
    real = s6.satin_shape

    def spy(poly, shape_id, **kwargs):
        seen.append((shape_id, poly))
        return real(poly, shape_id, **kwargs)

    cfg = dict(kw)
    if width_mm is not None:
        cfg["target_width_mm"] = width_mm
    cfg.update(flags)
    pc = PipelineConfig(**cfg)
    s7.satin_shape = spy
    try:
        _result, plan = digitize(ROOT / "testdata" / rel, pc)
    finally:
        s7.satin_shape = real
    by_shape: dict[str, list[StitchRun]] = {}
    for _b, run in plan.iter_runs():
        by_shape.setdefault(run.shape_id, []).append(run)
    ceiling = machine.satin_ceiling_mm(pc)
    out = {"case": case, "width_mm": cfg.get("target_width_mm"), "flags": flags,
           "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
           "blobs": [], "shapes": [], "polys": {}}
    for shape_id, poly in seen:
        blobs, shape = shape_census(shape_id, poly, by_shape.get(shape_id, []),
                                    ceiling, machine.SATIN_WIDE_COLUMN_MAX_MM)
        out["blobs"].extend(blobs)
        if shape is not None:
            out["shapes"].append(shape)
        out["polys"][shape_id] = poly
    return out


def _bin(v, bins):
    if v is None:
        return "n/a"
    for hi, lab in bins:
        if v <= hi:
            return lab
    return bins[-1][1]


def summarize(r: dict, top: int) -> str:
    blobs = r["blobs"]
    by_arms = Counter(b["arms"] for b in blobs)
    dec = Counter()
    for b in blobs:
        dec.update(b["decisions"])
    ratio = Counter(_bin(b["ratio"], RATIO_BINS) for b in blobs)
    hot = [b for b in blobs if b["coverage"]["p95"] >= machine.COVERAGE_WARN_UNITS / 2]
    bare = [b for b in blobs if b["coverage"]["bare"] >= 0.25 and b["area_mm2"] >= 2.0]
    lines = [f"== {r['case']:12} {r['width_mm'] or 'default':>7} mm  shapes {len(r['shapes']):3}  "
             f"junction blobs {len(blobs):3} (arms: {', '.join(f'{k}:{v}' for k, v in sorted(by_arms.items()))})  "
             f"arm decisions: {', '.join(f'{k} {v}' for k, v in sorted(dec.items()))}  "
             f"stitches {r['stitches']}  trims {r['trims']}",
             f"     node radius / arm half: {'  '.join(f'{lab}: {ratio[lab]}' for _h, lab in RATIO_BINS)}"
             f"   blobs with coverage p95 >= {machine.COVERAGE_WARN_UNITS / 2:.2f} layers: {len(hot)}"
             f"   blobs >= 25% bare (area >= 2 mm2): {len(bare)}"]
    for b in sorted(blobs, key=lambda b: -b["coverage"]["p95"])[:top]:
        c = b["coverage"]
        lines.append(f"     {b['shape_id']} at {b['node_mm']} arms {b['arms']} {b['decisions']}  "
                     f"r {b['node_r_mm']} / arm {b['arm_half_mm']} = {b['ratio']}  area {b['area_mm2']} mm2  "
                     f"layers mean {c['mean']} p95 {c['p95']} max {c['max']}  bare {c['bare']}  seams {b['seam_pairs']}")
    flips = [s for s in r["shapes"] if s["p90_arms_mm"] is not None and s["classifier_p90_mm"]
             and (s["p90_arms_mm"] <= machine.SATIN_MAX_WIDTH_MM < s["classifier_p90_mm"]
                  or s["p90_arms_mm"] <= machine.SATIN_WIDE_COLUMN_MAX_MM < s["classifier_p90_mm"])]
    for s in r["shapes"]:
        lines.append(f"     width {s['shape_id']}: classifier p90 {s['classifier_p90_mm']}  "
                     f"pruned skeleton p90 {s['p90_full_mm']}  arms only {s['p90_arms_mm']}  "
                     f"(blob pixels {s['blob_frac']:.0%})  verdict {s['verdict_ship']} / wide {s['verdict_wide']}"
                     + ("  <- arms-only p90 clears a cap the classifier's does not" if s in flips else ""))
    return "\n".join(lines)


def render(r: dict, out_dir: Path) -> None:
    from PIL import Image, ImageDraw
    out_dir.mkdir(parents=True, exist_ok=True)
    by_shape: dict[str, list] = {}
    for b in r["blobs"]:
        by_shape.setdefault(b["shape_id"], []).append(b)
    for shape_id, poly in r["polys"].items():
        x0, y0, x1, y1 = poly.bounds
        Z = max(8.0, min(50.0, 900.0 / max(x1 - x0, y1 - y0, 1e-6)))
        W, H = int((x1 - x0) * Z) + 20, int((y1 - y0) * Z) + 40
        im = Image.new("RGB", (W, H), "white")
        d = ImageDraw.Draw(im)
        mm = lambda p: ((p[0] - x0) * Z + 10, (p[1] - y0) * Z + 30)  # noqa: E731
        d.polygon([mm(c) for c in poly.exterior.coords], fill=(235, 235, 235), outline=(90, 90, 90))
        for ring in poly.interiors:
            d.polygon([mm(c) for c in ring.coords], fill="white", outline=(90, 90, 90))
        g = skeleton_graph(poly)
        if g is not None:
            edges, half_mm, field, scale, to_mm, dt_mm, skel_mask, dist = g
            decisions, merged = merge_decisions(edges, dt_mm, half_mm, scale)
            for node, arms in decisions.items():
                blob, _e, _h = blob_of(node, [(i, s) for i, s, _d in arms], edges, field,
                                       half_mm, to_mm, dt_mm, poly)
                if not blob.is_empty:
                    d.polygon([mm(c) for c in blob.exterior.coords], outline=(220, 0, 0), width=2)
                q = mm(to_mm(node))
                d.ellipse([q[0] - 4, q[1] - 4, q[0] + 4, q[1] + 4], fill=(0, 0, 0))
            for c in merged:
                pts = [mm(to_mm(p)) for p in c["pts"]]
                if len(pts) > 1:
                    d.line(pts, fill=(40, 80, 220), width=2)
        d.text((6, 6), f"{r['case']} {shape_id} @ {r['width_mm']} mm: junction blobs (red) on the merged strokes (blue)",
               fill="black")
        im.save(out_dir / f"{r['case']}_{shape_id}_{int(r['width_mm'] or 0)}mm_blobs.png")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="*", default=None)
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--json", default=None)
    ap.add_argument("--render", default=None)
    ap.add_argument("--top", type=int, default=6)
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    names = a.cases or list(CASES)
    print(f"junction blobs — flags {flags or 'default'}")
    report = []
    for name in names:
        rel, kw = CASES[name]
        for w in (a.widths or [None]):
            kw2 = {k: v for k, v in kw.items() if not (w is not None and k == "target_width_mm")}
            r = scan(name, rel, kw2, w, flags)
            print(summarize(r, a.top), flush=True)
            if a.render:
                render(r, Path(a.render))
            r.pop("polys")
            report.append(r)
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
