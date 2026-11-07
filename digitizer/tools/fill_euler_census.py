"""fill_euler_census: would ONE walk over a fill's sections sew it without a cut?

    python -m tools.fill_euler_census [--slugs a,b] [--out DIR] [--jobs N] [--table OUT.md]

Built 2026-11-07 for lagging area 3 (trims / fragmentation). The class the
professional never has is the cut between two sections of ONE fill: 32 over
the 17 paired jobs on 2026-10-29, 0 on his side; `fill_one_pass_sections`
took it to 31 and `fill_seam_aware_sections` to 26 (both OFF, defect 6 stopped
there on Kent's ruling). This is the CENSUS the next step asked for, before
any routing change: for every fill stage 7 sews in more than one section with
a cut between sections, the cheapest single walk over all its sections, and
what that walk would cost.

**How a walk is found** (the "Euler tour" of the lagging-area note, with
networkx 3.6.1 as pinned):

- Each section is a REQUIRED edge between its two ends; two sections are
  ADJACENT when their sewn footprints (`stage6_fill._footprint`) meet. A hop
  between two ends is a candidate edge weighted by its route inside the shape
  (straight when the chord lies in the shape, else
  `fill_section_travel.hidden_route` over the whole shape within
  `travel_path`'s own budget; no route, a large weight). Adjacent sections
  get geodesic weights; non-adjacent pairs the chord, so the graph stays
  connected without a raster call per pair.
- Every end has degree 1 in the required graph, so every end is odd:
  `networkx.min_weight_matching` pairs them (never `eulerize`, which would
  duplicate sections). Required edges plus the matching is a set of
  alternating cycles; they are spliced into one by the cheapest 2-opt
  exchange of two hops, the dearest hop (net of the hop in from the needle)
  is dropped, and `networkx.eulerian_path` from the open end nearest the
  needle is the walk.

**How a walk is priced**: the engine's own rule, not a proxy. `walk_cost`
steps the order exactly as `stage6_fill._order_cost_walk` does -- `travel_path`
with the fill laid so far, `_hide_bridge` for a route under rows still to come
(the one-pass rule, finished fill out of bounds), `_cut_is_cheaper` where the
plan cuts a bridge that shows, `_footprint` accumulated in `_Sewn` -- and
reads each hop's length and its exposed length with `stage6_fill._exposed_mm`
(thread over fill already laid, net of `_EXPOSED_TOLERANCE_MM` per hop, as
the scorer bills it). Nothing about exposure is re-implemented here. The walk
does NOT pin the shape's last path, so its exit may move where the planners'
would not; a census figure, not a plan.

**What it reads**: the committed tripwire jobs (`tools.tripwire.committed_jobs`,
pro files from the zip), stages 0-4 pickled under `--out`, then
`plan_stitches` replayed per arm (`main`, `one_pass`, `seam_aware`) with
`stage7_sequence.stitch_shape` wrapped to capture each fill's inputs and the
sections it sewed. The fills counted are those `tools.inpiece_cuts.classify_plan`
reads a `fill_section` cut in on the main arm's plan -- stage 7's own answer,
buried hops included. Reads; judges nothing; changes no default.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import math
import os
import pickle
import sys
import time
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE.parent) not in sys.path:
    sys.path.insert(0, str(HERE.parent))
os.environ.setdefault("OPENCV_IPP", "avx2")

DEFAULT_OUT = HERE.parent / "debug_out" / "fill_euler_census"
#: A hop no route was found for, as a matching weight: dearer than any shape.
NO_ROUTE_MM = 1.0e6
#: A work cap, not a quality knob: past this many sections the census skips the fill.
MAX_SECTIONS = 160
ARMS = {"main": {}, "one_pass": {"fill_one_pass_sections": True},
        "seam_aware": {"fill_seam_aware_sections": True}}


# ------------------------------------------------------------------ capture --

@dataclasses.dataclass
class Capture:
    """One fill as `stitch_shape` sewed it: the inputs the pricer needs and the
    FILL sections in sew order."""
    shape_id: str
    poly: object
    angle: float
    row_mm: float
    trim_at_mm: float
    cut_bridges: bool
    two_pass: bool
    entry: tuple | None
    sections: list
    stage6_cuts: int

    def ring_slack(self):
        from digitizer_core import machine, stage6_fill as s6
        return s6._inset_ring(self.poly, machine.TRAVEL_INSET_MM), self.poly.buffer(0.01)


def capture_plan(result, cfg) -> tuple[object, dict[str, Capture]]:
    """`plan_stitches(result, cfg)` with every fill's sections recorded."""
    from digitizer_core import stage6_fill as s6, stage7_sequence as s7, stitches
    from digitizer_core.pipeline import plan_stitches
    seen: dict[str, Capture] = {}
    real = s7.stitch_shape

    def wrapped(poly, shape_id, **kw):
        runs, report = real(poly, shape_id, **kw)
        fills = [r for r in runs if r.kind == stitches.FILL]
        under = [r for r in runs if r.kind == stitches.UNDERLAY]
        technique = kw.get("technique", "tatami")
        two_pass = technique == "crosshatch" or (
            technique == "tatami" and kw.get("density_boost", False) and s6.is_solid_fill(poly))
        under_cover = kw.get("under_cover", False)
        angle = kw.get("angle_deg")
        if angle is None:
            angle = s6.best_fill_angle_deg(poly, kw["row_mm"])
        seen[shape_id] = Capture(
            shape_id=shape_id, poly=poly, angle=angle, row_mm=kw["row_mm"],
            trim_at_mm=kw["trim_at_mm"],
            cut_bridges=bool(kw.get("cut_bridges", False) and under_cover and not two_pass),
            two_pass=two_pass,
            entry=tuple(under[-1].points[-1]) if under else kw.get("start_near"),
            sections=[list(map(tuple, r.points)) for r in fills],
            stage6_cuts=sum(1 for r in fills if r.trim))
        return runs, report

    s7.stitch_shape = wrapped
    try:
        plan = plan_stitches(result, cfg)
    finally:
        s7.stitch_shape = real
    return plan, seen


def fill_section_cuts(plan) -> dict[str, list[float]]:
    """shape id -> the gap (mm) of each `fill_section` cut stage 7 left in the file."""
    from tools import inpiece_cuts as ic
    out: dict[str, list[float]] = {}
    for r in ic.classify_plan(plan):
        if r["cause"] == "fill_section":
            out.setdefault(r["shape"], []).append(r["gap_mm"])
    return out


# -------------------------------------------------------------------- price --

def walk_cost(order, cap: Capture, hidden: bool) -> dict:
    """What this section ORDER costs, by `fill_region`'s rule: cuts (and how
    many past `LINK_MAX_GAP_MM`), travel mm and stitches, exposed mm (over
    fill already laid, net of `_EXPOSED_TOLERANCE_MM` per hop) and raw.
    `hidden`: routes under rows still to come where `travel_path` lifts or
    shows, finished fill out of bounds (the one-pass rule)."""
    from shapely.geometry import LineString
    from digitizer_core import machine, stage6_fill as s6, stitches
    ring, slack = cap.ring_slack()
    cuts = long_cuts = travel_st = 0
    travel_mm = exposed_mm = raw_mm = 0.0
    sewn, cache, cur = None, {}, cap.entry
    hops = []
    with s6.one_pass_scope(hidden):
        for i, path in enumerate(order):
            if len(path) < 2:
                continue
            if cur is not None:
                bridge = s6.travel_path(cap.poly, ring, cur, path[0], slack, sewn, cache)
                if hidden:
                    bridge = s6._hide_bridge(bridge, cap.poly, slack, cur, path[0], stitches.FILL,
                                             order[i:], cap.row_mm, sewn)
                if cap.cut_bridges and bridge and s6._cut_is_cheaper(cur, bridge, sewn, cap.trim_at_mm):
                    bridge = None
                d = math.dist(cur, path[0])
                if bridge is None:
                    if d > cap.trim_at_mm:
                        cuts += 1
                        long_cuts += d > machine.LINK_MAX_GAP_MM
                    hops.append({"cut": d > cap.trim_at_mm, "gap_mm": round(d, 2)})
                else:
                    route = [cur] + list(bridge)
                    length = LineString(route).length if len(route) > 1 else 0.0
                    raw = s6._exposed_mm(route, sewn) if sewn is not None else 0.0
                    travel_st += max(0, len(bridge) - 1)
                    travel_mm += length
                    raw_mm += raw
                    exposed_mm += max(0.0, raw - s6._EXPOSED_TOLERANCE_MM)
                    hops.append({"cut": False, "gap_mm": round(d, 2), "route_mm": round(length, 2),
                                 "exposed_mm": round(max(0.0, raw - s6._EXPOSED_TOLERANCE_MM), 2)})
            sewn = s6._sewn_add(sewn, s6._footprint(path, cap.row_mm))
            cur = path[-1]
    return {"cuts": cuts, "long_cuts": long_cuts, "travel_mm": round(travel_mm, 1),
            "travel_stitches": travel_st, "exposed_mm": round(exposed_mm, 1),
            "raw_exposed_mm": round(raw_mm, 1), "hops": hops}


# -------------------------------------------------------------------- graph --

def adjacency(sections, row_mm: float) -> set[tuple[int, int]]:
    """Pairs (i, j), i < j, whose sewn footprints meet."""
    from digitizer_core import stage6_fill as s6
    feet = [s6._footprint(p, row_mm) for p in sections]
    boxes = [f.bounds for f in feet]
    out = set()
    for i in range(len(sections)):
        for j in range(i + 1, len(sections)):
            bi, bj = boxes[i], boxes[j]
            if bi[0] > bj[2] or bj[0] > bi[2] or bi[1] > bj[3] or bj[1] > bi[3]:
                continue
            if feet[i].intersects(feet[j]):
                out.add((i, j))
    return out


class _Hops:
    """Hop weights between section ends, memoized: the chord when it lies in
    the shape, else `fill_section_travel.hidden_route` over the whole shape.
    Geometry only: which fill is already laid when a hop is made depends on
    the walk, so the weight cannot know whether the hop will show (a penalty
    for crossing a third section's footprint was tried on the Becker beanie
    and took its walk from 4 cuts to 10: a crossing of a section sewn LATER
    is the hidden route the walk wants)."""

    def __init__(self, sections, slack):
        self.sections, self.slack, self.memo = sections, slack, {}

    def end(self, node):
        i, e = node
        return self.sections[i][-1 if e else 0]

    def weight(self, u, v, geodesic: bool) -> float:
        from shapely.geometry import LineString
        from digitizer_core import fill_section_travel as fst
        key = (u, v) if u <= v else (v, u)
        if key in self.memo:
            return self.memo[key]
        a, b = self.end(u), self.end(v)
        d = math.dist(a, b)
        if d < 1e-9 or self.slack.covers(LineString([a, b])):
            w = d
        elif geodesic:
            pts = fst.hidden_route(self.slack, self.slack, a, b, fst._budget(a, b))
            w = LineString(pts).length if pts and len(pts) > 1 else NO_ROUTE_MM + d
        else:
            w = NO_ROUTE_MM + d
        self.memo[key] = w
        return w


def euler_walk(sections, slack, entry, adjacent: set[tuple[int, int]]) -> dict:
    """One walk over every section: {order (oriented sections), hops [(from
    node, to node, weight)], components (cycles before splicing), matching_mm}."""
    import networkx as nx
    n = len(sections)
    if n < 2:
        return {"order": list(sections), "hops": [], "components": 1, "matching_mm": 0.0}
    hops = _Hops(sections, slack)
    nodes = [(i, e) for i in range(n) for e in (0, 1)]
    adj = {frozenset(p) for p in adjacent}
    g = nx.Graph()
    g.add_nodes_from(nodes)
    for a in range(len(nodes)):
        for b in range(a + 1, len(nodes)):
            u, v = nodes[a], nodes[b]
            if u[0] == v[0]:
                continue
            g.add_edge(u, v, weight=hops.weight(u, v, frozenset((u[0], v[0])) in adj))
    matched = {tuple(sorted(e)) for e in nx.min_weight_matching(g)}
    assert len(matched) == n, "a perfect matching over the section ends"
    w = lambda e: g.edges[e]["weight"]

    def components(hop_set):
        m = nx.Graph()
        m.add_edges_from(((i, 0), (i, 1)) for i in range(n))
        m.add_edges_from(hop_set)
        return [set(c) for c in nx.connected_components(m)]

    comps = components(matched)
    n_comps = len(comps)
    # Splice the cycles into one: the cheapest exchange of one hop from each
    # of two cycles for the two hops that join them (either pairing).
    while len(comps) > 1:
        best = None
        by_comp = [[e for e in matched if e[0] in c] for c in comps]
        for x in range(len(comps)):
            for y in range(x + 1, len(comps)):
                for (a1, a2) in by_comp[x]:
                    for (b1, b2) in by_comp[y]:
                        for p, q in (((a1, b1), (a2, b2)), ((a1, b2), (a2, b1))):
                            delta = w(p) + w(q) - w((a1, a2)) - w((b1, b2))
                            if best is None or delta < best[0]:
                                best = (delta, (a1, a2), (b1, b2), tuple(sorted(p)), tuple(sorted(q)))
        _d, old_a, old_b, new_p, new_q = best
        matched -= {old_a, old_b}
        matched |= {new_p, new_q}
        comps = components(matched)
    # One alternating cycle. Drop the hop that saves most, net of the hop in
    # from the needle to the end that becomes the start.
    def drop_cost(e):
        u, v = e
        if entry is None:
            return -w(e), u
        du, dv = math.dist(entry, hops.end(u)), math.dist(entry, hops.end(v))
        return (du - w(e), u) if du <= dv else (dv - w(e), v)
    dropped = min(matched, key=lambda e: drop_cost(e)[0])
    start = drop_cost(dropped)[1]
    m = nx.MultiGraph()
    for i in range(n):
        m.add_edge((i, 0), (i, 1), key=("sec", i))
    for e in matched:
        if e != dropped:
            m.add_edge(*e, key=("hop", e), weight=w(e))
    order, walk_hops = [], []
    for u, v, key in nx.eulerian_path(m, source=start, keys=True):
        if key[0] == "sec":
            i = key[1]
            order.append(sections[i] if u == (i, 0) else sections[i][::-1])
        else:
            walk_hops.append((u, v, round(w(key[1]), 2)))
    assert len(order) == n and sum(1 for h in walk_hops) == n - 1
    return {"order": order, "hops": walk_hops, "components": n_comps,
            "matching_mm": round(sum(w(e) for e in matched), 1),
            "dropped_mm": round(w(dropped), 1)}


def census_shape(cap: Capture, dst_cuts: list[float]) -> dict:
    """One fill's row: the sewn order priced as it sews, the Euler walk priced
    with hidden routes, and the comparison figures."""
    from digitizer_core import stage6_fill as s6
    sections = [p for p in cap.sections if len(p) >= 2]
    row = {"shape": cap.shape_id, "sections": len(sections), "dst_cuts": len(dst_cuts),
           "dst_gaps_mm": dst_cuts, "stage6_cuts": cap.stage6_cuts, "two_pass": cap.two_pass}
    if cap.two_pass or len(sections) < 2 or len(sections) > MAX_SECTIONS:
        row["skipped"] = "two-pass fill" if cap.two_pass else f"{len(sections)} sections"
        return row
    with s6.cut_exposed_scope(True):
        base = walk_cost(sections, cap, hidden=False)
        adjacent = adjacency(sections, cap.row_mm)
        _ring, slack = cap.ring_slack()
        t = time.process_time()
        walk = euler_walk(sections, slack, cap.entry, adjacent)
        euler = walk_cost(walk["order"], cap, hidden=True)
    for h in euler["hops"]:
        h.pop("cut", None)
    row.update({
        "adjacent_pairs": len(adjacent),
        "components_before_splice": walk["components"],
        "sewn": {k: base[k] for k in ("cuts", "long_cuts", "travel_mm", "exposed_mm", "raw_exposed_mm")},
        "euler": {k: euler[k] for k in ("cuts", "long_cuts", "travel_mm", "exposed_mm", "raw_exposed_mm")},
        "euler_hops": euler["hops"],
        "one_walk": euler["cuts"] == 0,
        "added_travel_mm": round(euler["travel_mm"] - base["travel_mm"], 1),
        "walk_cpu_s": round(time.process_time() - t, 2),
    })
    return row


# ---------------------------------------------------------------------- jobs --

def digitized(slug: str, cache: Path):
    """(result, cfg): stages 0-4 at the pro's width and garment, from the pickle
    when one exists (`tools.pro_baseline.JOBS`, the Studio's request)."""
    pk = cache / f"{slug}.pkl"
    if pk.exists():
        d = pickle.loads(pk.read_bytes())
        return d["result"], d["cfg"]
    from tools import pro_baseline as pb
    from tools.pro_pair import request
    from digitizer_core import PipelineConfig
    from digitizer_core.pipeline import build_generation, finish_generation
    from digitizer_service.app import _decode, _parse_config
    garment, width, art, *_ = pb.JOBS[slug]
    data = Path(pb.resolve(art)).read_bytes()
    cfg = PipelineConfig(**_parse_config(json.dumps(request(width, garment, {}))))
    gen = build_generation(_decode(data), cfg, exif_source=data)
    result = finish_generation(gen.fork(), cfg)
    pk.write_bytes(pickle.dumps({"result": result, "cfg": cfg}))
    return result, cfg


def census_job(slug: str, cache: Path) -> dict:
    result, cfg = digitized(slug, cache)
    arms = {}
    captures = {}
    for name, sets in ARMS.items():
        c = dataclasses.replace(cfg, **sets)
        t = time.process_time()
        plan, seen = capture_plan(result, c)
        cpu = time.process_time() - t
        by_shape = fill_section_cuts(plan)
        arms[name] = {"cuts": int(plan.stats.trims), "plan_cpu_s": round(cpu, 1),
                      "fill_section": sum(len(v) for v in by_shape.values()),
                      "by_shape": {k: len(v) for k, v in by_shape.items()},
                      "stage6_cuts_by_shape": {k: v.stage6_cuts for k, v in seen.items()}}
        captures[name] = (seen, by_shape)
    seen, by_shape = captures["main"]
    shapes = []
    for sid, gaps in sorted(by_shape.items()):
        if sid not in seen:
            shapes.append({"shape": sid, "dst_cuts": len(gaps), "skipped": "not a stitch_shape fill"})
            continue
        row = census_shape(seen[sid], gaps)
        for name in ("one_pass", "seam_aware"):
            s, b = captures[name]
            row[name] = {"dst_cuts": len(b.get(sid, [])),
                         "stage6_cuts": s[sid].stage6_cuts if sid in s else None}
        shapes.append(row)
    return {"slug": slug, "arms": arms, "shapes": shapes}


def _worker(args):
    slug, cache = args
    try:
        return census_job(slug, cache)
    except Exception as e:                       # noqa: BLE001 -- one job's failure is a row
        return {"slug": slug, "error": f"{type(e).__name__}: {e}"}


# --------------------------------------------------------------------- table --

def table(report: dict) -> str:
    rows = ["| job | fill | sections | DST cuts main / one_pass / seam_aware "
            "| sewn: stage-6 cuts (past 40 mm), exposed mm "
            "| Euler: cuts (past 40 mm), +travel mm, exposed mm | one walk, 0 mm |",
            "|---|---|---|---|---|---|---|"]
    tot = Counter()
    for slug, job in sorted(report.items()):
        if "error" in job:
            rows.append(f"| {slug} | error | | {job['error']} | | | |")
            continue
        for s in job["shapes"]:
            tot["dst_cuts"] += s["dst_cuts"]
            if "skipped" in s:
                rows.append(f"| {slug} | {s['shape']} | {s.get('sections', '')} | {s['dst_cuts']} | "
                            f"skipped: {s['skipped']} | | |")
                continue
            clean = s["one_walk"] and s["euler"]["exposed_mm"] == 0.0
            tot["one_walk"] += s["dst_cuts"] if s["one_walk"] else 0
            tot["clean"] += s["dst_cuts"] if clean else 0
            tot["fills"] += 1
            tot["fills_clean"] += clean
            op, sa = s["one_pass"]["dst_cuts"], s["seam_aware"]["dst_cuts"]
            rows.append(
                f"| {slug} | {s['shape']} | {s['sections']} | {s['dst_cuts']} / {op} / {sa} "
                f"| {s['sewn']['cuts']} ({s['sewn']['long_cuts']}), {s['sewn']['exposed_mm']} "
                f"| {s['euler']['cuts']} ({s['euler']['long_cuts']}), {s['added_travel_mm']:+.1f}, "
                f"{s['euler']['exposed_mm']} "
                f"| {'YES' if clean else ('walk, shows' if s['one_walk'] else 'no')} |")
    rows.append(f"| **total** | {tot['fills']} fills | | **{tot['dst_cuts']}** | | "
                f"| **{tot['clean']}** of {tot['dst_cuts']} cuts one walk at 0 mm "
                f"({tot['one_walk']} one walk at any exposure) |")
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m tools.fill_euler_census",
                                 description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--slugs", default="", help="comma list; default every committed tripwire job")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--jobs", type=int, default=1, help="worker processes")
    ap.add_argument("--table", type=Path, help="write the markdown table here too")
    a = ap.parse_args(argv)
    from tools import tripwire
    slugs = a.slugs.split(",") if a.slugs else tripwire.committed_jobs()
    a.out.mkdir(parents=True, exist_ok=True)
    tripwire.materialise(a.out / "_kent", slugs)
    report_path = a.out / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    todo = [(s, a.out) for s in slugs if s not in report]
    if a.jobs > 1 and len(todo) > 1:
        import multiprocessing as mp
        with mp.get_context("fork").Pool(a.jobs, maxtasksperchild=1) as pool:
            results = pool.imap_unordered(_worker, todo)
            for job in results:
                report[job["slug"]] = job
                print(job["slug"], json.dumps({k: v for k, v in job.items() if k != "shapes"}), flush=True)
                report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    else:
        for item in todo:
            job = _worker(item)
            report[job["slug"]] = job
            print(job["slug"], json.dumps({k: v for k, v in job.items() if k != "shapes"}), flush=True)
            report_path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    md = table(report)
    print(md)
    if a.table:
        a.table.write_text(md + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
