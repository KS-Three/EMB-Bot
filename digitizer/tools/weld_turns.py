"""Every WELD the satin merge makes, by the turn it asks the column to take
-- the instrument behind `docs/superpowers/plans/2026-09-19-junction-construction.md`.

`_merge_through_junctions` welds the two arms at a node whose directions
are most nearly opposite, reading each direction over `arm_px` = two
half-widths (`_WELD_MAX_DOT` -0.5 admits anything under a 60 deg turn by
that baseline). The R of the lettering plan's fixture folds over itself
through one such weld (311 self-crossing pairs, 294 seated in that one
blob) at a 44 deg turn by the baseline -- and across the nine logos 88%
of the seam pairs the blob census reads sit in the 30-60 deg welds. So
this reads every weld the way the fold guard would price it: the turn
between the welded arms over SEVERAL windows (the merge's own baseline,
and fixed lengths in mm), the node's medial radius against the arms',
the blob, and what the thread did inside it -- seam pairs, layers, bare
-- so the window at which a fold rule separates the folding welds from
the clean ones can be read off the corpus rather than derived.

Per weld:
  turn_base_deg   the turn by the merge's baseline (two half-widths)
  turn_<w>mm_deg  the turn with each arm's direction read over w mm
  node_r_mm       the node's medial radius; arm_half_mm the arms' own
  R_<w>mm         the bend radius the fold guard would read at that
                  window: 2w / turn (rad); fold_<w> = FOLD_FRAC * R
                  against node_r -- under 1.0 the column cannot keep the
                  node's width through the bend
  seam_pairs      crossing seats the census finds inside the blob
  layers_max, bare  the blob's coverage, preflight's own units

Usage:
  python tools/weld_turns.py [cases ...] [--widths W ...] [--flag NAME[=VALUE] ...]
                             [--image PATH --width W] [--windows 1 2 3]
                             [--json PATH] [--top N]
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Point

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                                   # noqa: E402
from digitizer_core import stage6_satin as s6                               # noqa: E402
from digitizer_core import stage7_sequence as s7                            # noqa: E402
from digitizer_core.pipeline import (build_generation, finish_generation,   # noqa: E402
                                     plan_stitches)
from digitizer_core.preflight import _coverage_map                          # noqa: E402
from digitizer_core.stitches import strip_ties                              # noqa: E402
import junction_blobs as jb                                                 # noqa: E402
from thin_strokes import corpus_cases, parse_flags                          # noqa: E402
from wide_columns import crossing_pairs                                     # noqa: E402

DEFAULT_WINDOWS_MM = (1.0, 2.0, 3.0)


def _arm_dir_px(pts, at_start: bool, reach_px: int):
    p = pts if at_start else list(reversed(pts))
    far = p[min(reach_px, len(p) - 1)]
    dx, dy = far[0] - p[0][0], far[1] - p[0][1]
    d = math.hypot(dx, dy) or 1.0
    return dx / d, dy / d


def _turn_deg(d1, d2) -> float:
    """0 = the arms continue straight through each other; 90 = a right angle."""
    dot = d1[0] * d2[0] + d1[1] * d2[1]
    return 180.0 - math.degrees(math.acos(max(-1.0, min(1.0, dot))))


def probe(art: str, width: float, garment: str, flags: dict,
          windows_mm=DEFAULT_WINDOWS_MM, tag: str = "") -> tuple[list[dict], dict]:
    """-> (one row per weld, the plan's totals)."""
    seen: list = []
    real = s7.satin_shape

    def spy(poly, shape_id, **kw):
        seen.append((shape_id, poly))
        return real(poly, shape_id, **kw)

    cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6, **flags)
    s7.satin_shape = spy
    try:
        gen = build_generation(art, cfg)
        result = finish_generation(gen.fork(), cfg)
        plan = plan_stitches(result, cfg)
    finally:
        s7.satin_shape = real
    by: dict = collections.defaultdict(list)
    for _b, run in plan.iter_runs():
        by[run.shape_id].append(run)
    text = {x.shape_id for x in result.regions if x.meta.get("text_candidate")}
    rows: list[dict] = []
    for sid, poly in seen:
        g = jb.skeleton_graph(poly)
        if g is None:
            continue
        edges, half_mm, field, scale, to_mm, dt_mm, _skel, _dist = g
        decisions, _merged = jb.merge_decisions(edges, dt_mm, half_mm, scale)
        arm_px = max(5, int(round(2.0 * half_mm * scale)))
        runs = by.get(sid, [])
        sat = [x for x in runs if x.kind == "satin"]
        cov = _coverage_map(jb._Runs(runs), cell_mm=jb.COVER_CELL_MM) if runs else None
        grid, origin = cov if cov is not None else (None, (0.0, 0.0))
        seats = []
        for x in sat:
            seats.extend(c for c, _a in jb.crossing_seats(s6.strip_splits(strip_ties(x.points))))
        shape_cross = sum(crossing_pairs(s6.strip_splits(strip_ties(x.points))) for x in sat)
        for node, arms in decisions.items():
            welded = [(i, s) for i, s, d in arms if d == "weld"]
            if len(welded) != 2:
                continue
            (i1, s1), (i2, s2) = welded
            row = {"case": tag, "shape": sid, "text": sid in text,
                   "node_mm": tuple(round(v, 2) for v in to_mm(node)),
                   "arms": len(arms), "half_mm": round(half_mm, 2),
                   "turn_base_deg": round(_turn_deg(_arm_dir_px(edges[i1]["pts"], s1, arm_px),
                                                    _arm_dir_px(edges[i2]["pts"], s2, arm_px)), 1)}
            node_r = dt_mm(node)
            for w in windows_mm:
                px = max(2, int(round(w * scale)))
                t = _turn_deg(_arm_dir_px(edges[i1]["pts"], s1, px),
                              _arm_dir_px(edges[i2]["pts"], s2, px))
                rad = math.radians(t)
                R = math.inf if rad < 1e-9 else (2.0 * w) / rad
                row[f"turn_{w:g}mm_deg"] = round(t, 1)
                row[f"R_{w:g}mm"] = None if math.isinf(R) else round(R, 2)
                row[f"fold_{w:g}mm"] = None if math.isinf(R) or node_r <= 0 else round(s6._FOLD_FRAC * R / node_r, 2)
            blob, _exits, halves = jb.blob_of(node, [(i, s) for i, s, _d in arms], edges, field,
                                              half_mm, to_mm, dt_mm, poly)
            c = jb.coverage_in(blob, grid, origin, jb.COVER_CELL_MM) if grid is not None else {}
            inside = blob.buffer(1e-6)
            row.update({"node_r_mm": round(node_r, 2),
                        "arm_half_mm": round(float(np.mean(halves)) if halves else half_mm, 2),
                        "blob_area_mm2": round(blob.area, 1),
                        "seam_pairs": sum(1 for s_ in seats if inside.covers(Point(s_))),
                        "layers_max": c.get("max"), "bare": c.get("bare"),
                        "shape_cross": shape_cross})
            rows.append(row)
    totals = {"stitches": plan.stats.stitch_count, "trims": plan.stats.trims}
    return rows, totals


def summarize(tag: str, rows: list[dict], totals: dict, top: int) -> str:
    bins = collections.Counter()
    seams = collections.Counter()
    for r in rows:
        t = r["turn_base_deg"]
        b = "0-30" if t < 30 else "30-60" if t < 60 else "60+"
        bins[b] += 1
        seams[b] += r["seam_pairs"]
    out = [f"=== {tag}: stitches {totals['stitches']} trims {totals['trims']}; welds {len(rows)} "
           f"by baseline turn {dict(bins)}; seam pairs by turn {dict(seams)}"]
    for r in sorted(rows, key=lambda d: -d["seam_pairs"])[:top]:
        folds = ", ".join(f"{k[5:]}={v}" for k, v in r.items() if k.startswith("fold_"))
        out.append(f"    {r['shape'][:9]} at {r['node_mm']} arms {r['arms']} turn base {r['turn_base_deg']} "
                   f"| node_r {r['node_r_mm']} arm_half {r['arm_half_mm']} | fold {folds} "
                   f"| seams {r['seam_pairs']} layers_max {r['layers_max']} bare {r['bare']}")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*", help="corpus case names (default: all nine)")
    ap.add_argument("--widths", type=float, nargs="*", default=None)
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--image", default=None, help="an image outside the corpus")
    ap.add_argument("--width", type=float, default=None, help="its width in mm")
    ap.add_argument("--windows", type=float, nargs="*", default=list(DEFAULT_WINDOWS_MM))
    ap.add_argument("--json", default=None)
    ap.add_argument("--top", type=int, default=4)
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    jobs: list[tuple[str, str, float, str]] = []
    if a.image:
        if a.width is None:
            ap.error("--image needs --width")
        jobs.append((Path(a.image).stem, a.image, a.width, "left_chest"))
    else:
        wanted = set(a.cases)
        for name, path, width, garment in corpus_cases():
            if wanted and name not in wanted:
                continue
            for w in (a.widths or [width]):
                jobs.append((f"{name}@{w:g}", str(path), w, garment))
    allrows: list[dict] = []
    for tag, art, width, garment in jobs:
        rows, totals = probe(art, width, garment, flags, tuple(a.windows), tag=tag)
        allrows.extend(rows)
        print(summarize(tag, rows, totals, a.top), flush=True)
    if a.json:
        Path(a.json).write_text(json.dumps(allrows, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
