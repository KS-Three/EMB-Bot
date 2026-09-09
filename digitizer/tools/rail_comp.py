"""What pull compensation does to a satin shape BEFORE it is decomposed, and
what rail-side compensation changes — the instrument for item 6 (quality
review 2026-09-08; `cfg.satin_rail_comp`).

Stage 5 grows every shape by the fabric's pull with a round join and the
satin tier then skeletonises the GROWN polygon. Per satin-tier shape this
reads, at the design's own fabric pull:

  vertices   artwork -> grown: the arc vertices the round join adds to
             every convex corner
  extra      mm2 the polygon the satin tier actually received lies outside
             the artwork: the growth band OFF, only the underlap tongue ON
  sealed     exterior concavities narrower than 2 x pull — the E's arm
             slots, the N's crotch — as the closing (grow then shrink)
             minus the artwork: count and mm2. The grown polygon has no
             slot where these were, and its skeleton welds across them.
  graph      the stroke decomposition on the artwork against the grown
             polygon: strokes after the merge, junction nodes, welds
  iou_target thread (the `COVERAGE_THREAD_W_MM` ribbon on every needle-down
             run) against the artwork grown by the pull — what a
             compensated column is aiming at in the FILE
  iou_art    the same thread against the artwork itself — the 2026-08-26
             letterform-fidelity number, kept for continuity (it penalises
             correct compensation, so read it beside `iou_target`)

`--compare` digitizes OFF and ON `cfg.satin_rail_comp` and prints both
sets, plus stitches, trims and preflight's coverage_max / uncovered.

Usage:
  python tools/rail_comp.py [--widths W ...] [--flag NAME[=VALUE] ...]
                            [--compare] [--json PATH] [--top N] [cases ...]
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from pathlib import Path

from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize, machine                 # noqa: E402
from digitizer_core import stage6_satin as s6                               # noqa: E402
from digitizer_core import stage7_sequence as s7                            # noqa: E402
from digitizer_core.pipeline import fabric_for                              # noqa: E402
from digitizer_core.preflight import run_preflight                          # noqa: E402
from digitizer_core.stitches import strip_ties                              # noqa: E402
from curve_tiers import CASES                                                # noqa: E402
from thin_strokes import parse_flags                                        # noqa: E402
import junction_blobs as jb                                                 # noqa: E402

ROOT = HERE.parent
THREAD_HALF_MM = machine.COVERAGE_THREAD_W_MM / 2.0
NEEDLE_DOWN = {"satin", "underlay", "run", "fill", "travel"}
# The drone wordmark's letters, named the way the 2026-08-26 study named them.
NAMED = {"S46627035": "PRECISION P", "S60ac57f2": "PRECISION R", "S85b059f2": "PRECISION C",
         "Sa7529943": "PRECISION O", "S8438f8fc": "PRECISION N", "Sb0a7fa0d": "THERMAL T",
         "S3e7df60e": "THERMAL H", "S14057482": "THERMAL E", "Sbf8a37c3": "THERMAL R",
         "S6cc4a060": "THERMAL M", "S81d913c5": "THERMAL A", "S81b4b426": "THERMAL L",
         "S37e7e27f": "AND N", "Sc90d4b1a": "AND D", "S3f60d519": "DRONE R",
         "S420b5535": "DRONE O", "Sa155e9ec": "DRONE N", "Sc6ef66a0": "DRONE E"}


def has_flag() -> bool:
    return "satin_rail_comp" in {f.name for f in dataclasses.fields(PipelineConfig)}


def sealed_slots(art: Polygon, pull: float) -> tuple[int, float]:
    """Exterior concavities the growth closes: the closing minus the artwork."""
    if pull <= 0:
        return 0, 0.0
    closing = art.buffer(pull).buffer(-pull)
    gap = closing.difference(art)
    parts = [g for g in getattr(gap, "geoms", [gap]) if g.geom_type == "Polygon" and g.area >= 0.05]
    return len(parts), round(sum(g.area for g in parts), 2)


def graph_stats(poly: Polygon) -> dict:
    g = jb.skeleton_graph(poly)
    if g is None:
        return {"strokes": 0, "nodes": 0, "welds": 0}
    edges, half_mm, field, scale, to_mm, dt_mm, _skel, _dist = g
    decisions, merged = jb.merge_decisions(edges, dt_mm, half_mm, scale)
    welds = sum(1 for arms in decisions.values() for _i, _s, d in arms if d == "weld")
    strokes, _h, _f = s6.extract_strokes(poly)
    return {"strokes": len(strokes), "nodes": len(decisions), "welds": welds}


def thread_of(runs) -> Polygon:
    segs = []
    for r in runs:
        if r.kind not in NEEDLE_DOWN:
            continue
        pts = strip_ties(r.points) if r.kind == "satin" else list(r.points)
        if len(pts) >= 2:
            segs.append(LineString(pts).buffer(THREAD_HALF_MM, cap_style=1, join_style=1))
    return unary_union(segs) if segs else Polygon()


def iou(a, b) -> float:
    if a.is_empty or b.is_empty:
        return 0.0
    u = a.union(b).area
    return round(a.intersection(b).area / u, 3) if u > 0 else 0.0


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
    pull = max(0.0, fabric_for(pc).pull_comp_mm)
    s7.satin_shape = spy
    try:
        result, plan = digitize(ROOT / "testdata" / rel, pc)
    finally:
        s7.satin_shape = real
    rep = run_preflight(result, plan, pc, image=ROOT / "testdata" / rel)
    art_by_id = {r.shape_id: r.polygon for r in result.regions}
    by_shape: dict[str, list] = {}
    for _b, run in plan.iter_runs():
        by_shape.setdefault(run.shape_id, []).append(run)
    rows = []
    for shape_id, sewn_poly in seen:
        art = art_by_id.get(shape_id)
        if art is None or art.is_empty:
            continue
        grown = art.buffer(pull) if pull > 0 else art
        n_sealed, a_sealed = sealed_slots(art, pull)
        thread = thread_of(by_shape.get(shape_id, []))
        rows.append({
            "shape_id": shape_id, "name": NAMED.get(shape_id, ""),
            "area_mm2": round(art.area, 1), "pull_mm": pull,
            "vertices_art": len(art.exterior.coords) - 1,
            "vertices_grown": len(grown.exterior.coords) - 1,
            "extra_mm2": round(sewn_poly.difference(art).area, 2),
            "sealed_n": n_sealed, "sealed_mm2": a_sealed,
            "graph_art": graph_stats(art), "graph_grown": graph_stats(grown),
            "iou_target": iou(thread, grown), "iou_art": iou(thread, art),
            "stitches": sum(len(r.points) for r in by_shape.get(shape_id, [])),
        })
    m = rep["metrics"]
    return {"case": case, "width_mm": cfg.get("target_width_mm"), "flags": flags, "pull_mm": pull,
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
            "score": rep["score"], "coverage_max": m.get("coverage_max"),
            "unc_total": m.get("uncovered_total_mm2"), "unc_worst": m.get("uncovered_worst_mm2"),
            "rows": rows}


def summarize(r: dict, top: int) -> str:
    rows = r["rows"]
    n = len(rows)
    if not n:
        return f"== {r['case']:12} {r['width_mm'] or 'default':>7} mm: no satin shapes"
    mean = lambda k: sum(x[k] for x in rows) / n  # noqa: E731
    sealed = [x for x in rows if x["sealed_n"]]
    welded = [x for x in rows if x["graph_grown"]["strokes"] < x["graph_art"]["strokes"]]
    lines = [f"== {r['case']:12} {r['width_mm'] or 'default':>7} mm  pull {r['pull_mm']} mm  satin shapes {n}  "
             f"sewn outside the artwork: {sum(x['extra_mm2'] for x in rows):.1f} mm2  "
             f"stitches {r['stitches']}  trims {r['trims']}  score {r['score']}  coverage_max {r['coverage_max']}  "
             f"uncovered {r['unc_total']} / worst {r['unc_worst']}",
             f"     vertices artwork -> grown: {sum(x['vertices_art'] for x in rows)} -> {sum(x['vertices_grown'] for x in rows)}  "
             f"shapes with sealed slots: {len(sealed)} ({sum(x['sealed_mm2'] for x in rows):.1f} mm2)  "
             f"shapes whose grown skeleton has FEWER strokes than the artwork's: {len(welded)}  "
             f"IoU vs target mean {mean('iou_target'):.3f}  vs artwork {mean('iou_art'):.3f}"]
    named = [x for x in rows if x["name"]] or sorted(rows, key=lambda x: -x["sealed_mm2"])[:top]
    for x in sorted(named, key=lambda x: (x["name"], -x["area_mm2"]))[:max(top, 18)]:
        ga, gg = x["graph_art"], x["graph_grown"]
        lines.append(f"     {x['shape_id']} {x['name']:12} {x['area_mm2']:6.1f} mm2  vertices {x['vertices_art']:3} -> {x['vertices_grown']:3}  "
                     f"sealed {x['sealed_n']} ({x['sealed_mm2']:.2f} mm2)  strokes art {ga['strokes']} (nodes {ga['nodes']}, welds {ga['welds']}) "
                     f"-> grown {gg['strokes']} ({gg['nodes']}, {gg['welds']})  IoU target {x['iou_target']:.3f} art {x['iou_art']:.3f}")
    return "\n".join(lines)


def compare_line(off: dict, on: dict) -> str:
    o = {x["shape_id"]: x for x in off["rows"]}
    n = {x["shape_id"]: x for x in on["rows"]}
    both = [s for s in o if s in n]
    if not both:
        return "     OFF -> ON: no shape in both"
    mt = lambda d, k: sum(d[s][k] for s in both) / len(both)  # noqa: E731
    lines = [f"     OFF -> ON: stitches {off['stitches']} -> {on['stitches']}  trims {off['trims']} -> {on['trims']}  "
             f"score {off['score']} -> {on['score']}  coverage_max {off['coverage_max']} -> {on['coverage_max']}  "
             f"uncovered {off['unc_total']} -> {on['unc_total']} (worst {off['unc_worst']} -> {on['unc_worst']})  "
             f"IoU vs target {mt(o, 'iou_target'):.3f} -> {mt(n, 'iou_target'):.3f}  vs artwork {mt(o, 'iou_art'):.3f} -> {mt(n, 'iou_art'):.3f}  "
             f"sewn outside the artwork {sum(o[s]['extra_mm2'] for s in both):.1f} -> {sum(n[s]['extra_mm2'] for s in both):.1f} mm2"]
    for s in sorted(both, key=lambda s: (o[s]["name"] == "", o[s]["name"], -o[s]["area_mm2"]))[:18]:
        a, b = o[s], n[s]
        if a["name"] or a["iou_target"] != b["iou_target"] or a["stitches"] != b["stitches"]:
            lines.append(f"        {s} {a['name']:12} IoU target {a['iou_target']:.3f} -> {b['iou_target']:.3f}  art {a['iou_art']:.3f} -> {b['iou_art']:.3f}  "
                         f"stitches {a['stitches']} -> {b['stitches']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--widths", type=float, nargs="*", default=None)
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--json", default=None)
    ap.add_argument("--top", type=int, default=8)
    a = ap.parse_args(argv)
    flags = parse_flags(a.flag)
    names = a.cases or list(CASES)
    if a.compare and not has_flag():
        print("--compare needs cfg.satin_rail_comp, which this tree does not have")
        return 2
    print(f"pull compensation and the satin tier — flags {flags or 'default'}")
    report = []
    for name in names:
        rel, kw = CASES[name]
        for w in (a.widths or [None]):
            kw2 = {k: v for k, v in kw.items() if not (w is not None and k == "target_width_mm")}
            off = scan(name, rel, kw2, w, {**flags, **({"satin_rail_comp": False} if a.compare else {})})
            print(summarize(off, a.top), flush=True)
            report.append(off)
            if a.compare:
                on = scan(name, rel, kw2, w, {**flags, "satin_rail_comp": True})
                print(compare_line(off, on), flush=True)
                report.append(on)
    if a.json:
        Path(a.json).write_text(json.dumps(report, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
