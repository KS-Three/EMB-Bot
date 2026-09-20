"""Why a between-stroke walk is refused, per call — the anatomy behind the
"walk-refused" bucket the lettering trim census counts (scope-history
2026-09-19; MARINE 127 read 20 of them, 9 on the file).

Between two strokes the linking pass asks `stage6_satin._graph_travel` for a
needle-down path over the UNSEWN spine web; when it gets none, the needle
lifts and that is a trim. The census counted the refusals. It could not say
WHY any of them was refused, and "relax the walk" is not one change — the
function has four distinct ways to refuse and the CALLER has a fifth:

  cursor_unsnapped  the needle sits further than `trim_at_mm` from any node
                    (it ends wherever the last run ended, often a
                    cap-extended point off the web)
  target_unsnapped  the stroke start sits further than 0.8 mm from any node
                    — the strict snap `_graph_travel` keeps on the target
                    side on purpose ("a 0.8mm miss there means the web
                    genuinely does not reach it")
  blocked_by_sewn   a path exists, but every route runs over strokes already
                    sewn; running stitches on finished satin show, so those
                    edges are forbidden. THIS one is a trade, not a wall
  disconnected      no path even ignoring what is sewn: the two strokes are
                    in different components of the web (different letters,
                    usually), and a trim is the correct answer
  too_long          a path was FOUND and the caller threw it away:
                    `plen <= max(20.0, 4.0 * direct)` at both call sites,
                    the same cap the fill path uses. Invisible to the
                    census, which only logged `path is None`

Reachability is asked of the real `_graph_travel` (the same call with `sewn`
emptied), so this tool duplicates no Dijkstra; only the two snap thresholds
are mirrored here, and `tests/test_refused_walks.py` pins them against the
real function.

    .venv/bin/python -m tools.refused_walks run --out refused.json
    .venv/bin/python -m tools.refused_walks tables refused.json

Measurement only: it changes nothing in the pipeline.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent            # digitizer/
REPO = ROOT.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from digitizer_core import stage6_satin as s6  # noqa: E402
from digitizer_core import textcluster as tc  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402

from digitizer_core.preflight import run_preflight  # noqa: E402

from tools.thin_strokes import corpus_cases  # noqa: E402
from tools.travel_cover import travel_exposure  # noqa: E402

# `_graph_travel`'s own literals, mirrored so a refusal can be attributed
# without re-running its closures. `tests/test_refused_walks.py` pins both
# against the real function, so a change there fails this tool loudly
# instead of silently re-labelling refusals.
SNAP_MM = 0.8               # the strict snap, used on the target side
# Radii tried when pricing a snap-caused refusal (`machine.TRIM_AT_MM` is 3.0).
RESCUE_LADDER_MM = (4.0, 5.0, 6.0, 8.0, 12.0)
CAP_FLOOR_MM = 20.0         # the caller's length cap: max(20, 4 x direct)
CAP_FACTOR = 4.0

REASONS = ("ok", "trivial", "too_long", "cursor_unsnapped",
           "target_unsnapped", "blocked_by_sewn", "disconnected")

RENDERS = REPO / "docs" / "renders"
FIXTURES = [
    ("marine127", RENDERS / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png", 127.4, "left_chest"),
    ("marine80", RENDERS / "lettering-route-2026-09-19" / "marine_80mm_traced_input.png", 80.2, "left_chest"),
]


def _nearest(p, nodes) -> float:
    """Distance from p to the closest node, inf when the web has none."""
    return min((math.dist(p, q) for q in nodes), default=float("inf"))


def classify(cur, target, sewn, allow, nodes, edges, adj, *, trim_at_mm,
             snap_to_open, path, orig) -> dict:
    """One walk's verdict: its reason and the geometry behind it."""
    direct = math.dist(cur, target)
    cur_miss, tgt_miss = _nearest(cur, nodes), _nearest(target, nodes)
    row = {"direct_mm": round(direct, 2), "cursor_miss_mm": round(cur_miss, 2),
           "target_miss_mm": round(tgt_miss, 2), "trim_at_mm": round(trim_at_mm, 2),
           "snap_to_open": bool(snap_to_open), "sewn": len(sewn), "nodes": len(nodes)}
    if path is not None:
        plen = sum(math.dist(a, b) for a, b in zip(path, path[1:]))
        cap = max(CAP_FLOOR_MM, CAP_FACTOR * direct)
        row["path_mm"] = round(plen, 2)
        row["cap_mm"] = round(cap, 2)
        if len(path) < 2:
            row["reason"] = "trivial"          # same node: no travel run, no trim either
        else:
            row["reason"] = "ok" if plen <= cap else "too_long"
        return row
    # Refused. Ask the real function the same question with nothing sewn:
    # a path THERE and not here means finished satin is in the way.
    free = orig(cur, target, set(), set(), nodes, edges, adj,
                trim_at_mm=trim_at_mm, snap_to_open=snap_to_open)
    if free is not None and len(free) >= 2:
        row["reason"] = "blocked_by_sewn"
        row["free_path_mm"] = round(sum(math.dist(a, b) for a, b in zip(free, free[1:])), 2)
        return row
    # No path with the whole web open either: a snap miss, or two components.
    if tgt_miss > SNAP_MM:
        row["reason"] = "target_unsnapped"
    elif cur_miss > trim_at_mm:
        row["reason"] = "cursor_unsnapped"
    else:
        row["reason"] = "disconnected"
    # What would it take to rescue this one, and what would it cost? The
    # cursor-side snap radius IS `trim_at_mm` (3.0 mm, `machine.TRIM_AT_MM`),
    # so a refusal the needle's distance caused is priced by the radius that
    # would reach the web and the leg that would then be sewn from the true
    # cursor onto it — exposed unless it happens to run under coverage.
    if row["reason"] in ("cursor_unsnapped", "target_unsnapped"):
        for radius in RESCUE_LADDER_MM:
            if radius <= trim_at_mm:
                continue
            got = orig(cur, target, sewn, allow, nodes, edges, adj,
                       trim_at_mm=radius, snap_to_open=snap_to_open)
            if got is not None and len(got) >= 2:
                plen = sum(math.dist(a, b) for a, b in zip(got, got[1:]))
                row["rescued_at_mm"] = radius
                row["rescue_path_mm"] = round(plen, 2)
                row["rescue_within_cap"] = plen <= max(CAP_FLOOR_MM, CAP_FACTOR * direct)
                # The leg the needle would sew from where it actually is onto
                # the web (the walk's own first point).
                row["rescue_leg_mm"] = round(math.dist(cur, got[0]), 2)
                break
        if "rescued_at_mm" not in row:
            # The snap was not the whole story. With the widest radius AND
            # nothing forbidden, does a path exist at all? Yes means finished
            # satin blocks it once the needle is on the web (the same trade as
            # `blocked_by_sewn`, hidden behind a snap miss); no means the two
            # strokes are in different components and a trim is correct.
            wide = orig(cur, target, set(), set(), nodes, edges, adj,
                        trim_at_mm=RESCUE_LADDER_MM[-1], snap_to_open=snap_to_open)
            row["blocked_after_snap"] = bool(wide is not None and len(wide) >= 2)
            if row["blocked_after_snap"]:
                row["free_path_mm"] = round(sum(math.dist(a, b) for a, b in zip(wide, wide[1:])), 2)
    return row


class Spy:
    """Wraps `_graph_travel` and classifies every call."""

    def __init__(self) -> None:
        self.calls: list[dict] = []
        self.orig = s6._graph_travel

    def __enter__(self) -> "Spy":
        def spy(cur, target, sewn, allow, nodes, edges, adj, *, trim_at_mm, **kw):
            path = self.orig(cur, target, sewn, allow, nodes, edges, adj,
                             trim_at_mm=trim_at_mm, **kw)
            self.calls.append(classify(cur, target, sewn, allow, nodes, edges, adj,
                                       trim_at_mm=trim_at_mm,
                                       snap_to_open=kw.get("snap_to_open", False),
                                       path=path, orig=self.orig))
            return path
        s6._graph_travel = spy
        return self

    def __exit__(self, *exc) -> None:
        s6._graph_travel = self.orig


def measure(name: str, path: Path, width_mm: float, garment: str,
            cfg_kw: dict | None = None) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment, **(cfg_kw or {}))
    gen = build_generation(str(path), cfg)
    with Spy() as spy:
        result = finish_generation(gen, cfg)
        plan = plan_stitches(result, cfg)
    letters = {r.shape_id for g in tc._lettering_groups(result.regions) for r in g}
    by = collections.Counter(c["reason"] for c in spy.calls)
    refused = [c for c in spy.calls if c["reason"] not in ("ok", "trivial")]
    return {
        "case": name, "width_mm": width_mm, "garment": garment,
        "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
        "letters": len(letters), "calls": len(spy.calls),
        "by": {r: by[r] for r in REASONS if by[r]},
        # The geometry of what was refused, so a candidate relaxation can be
        # priced before it is built.
        "refused": refused,
    }


def compare(name: str, path: Path, width_mm: float, garment: str,
            reach_mm: float) -> dict:
    """One case OFF against ON at `reach_mm`: what the rescued walks cost.

    A stage-6/7 flag, so both arms finish from one build (the fork is
    identical to a fresh build for these — checked 2026-09-20 on three)."""
    base = PipelineConfig(target_width_mm=width_mm, garment_id=garment)
    gen = build_generation(str(path), base)
    row = {"case": name, "width_mm": width_mm}
    for arm, cfg in (("off", base),
                     ("on", PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                                           satin_walk_cursor_reach_mm=reach_mm))):
        with Spy() as spy:
            result = finish_generation(gen.fork(), cfg)
            plan = plan_stitches(result, cfg)
        pf = run_preflight(result, plan, cfg, image=str(path))
        by = collections.Counter(c["reason"] for c in spy.calls)
        row[arm] = {
            "stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
            "exposed_mm": round(travel_exposure(plan)["exposed_mm"], 1),
            "grade": pf.get("grade"),
            "cursor_unsnapped": by["cursor_unsnapped"], "ok": by["ok"],
            "findings": sorted({f["code"] for f in pf["findings"]}),
        }
    return row


def run(out: Path, cases=None) -> list[dict]:
    jobs = cases if cases is not None else (
        FIXTURES + [(n, Path(p), float(w), g) for n, p, w, g in corpus_cases()])
    rows: list[dict] = []
    for name, p, w, g in jobs:
        rows.append(measure(name, Path(p), w, g))
        out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
        r = rows[-1]
        print(f"{name}: {r['calls']} calls, {r['trims']} trims, {r['by']}", file=sys.stderr)
    return rows


def tables(rows: list[dict]) -> str:
    out = ["### Every between-stroke walk, by what happened to it\n",
           "| case | calls | " + " | ".join(REASONS) + " | trims |",
           "|---|---|" + "---|" * (len(REASONS) + 1)]
    totals: collections.Counter = collections.Counter()
    for r in rows:
        by = r["by"]
        for k, v in by.items():
            totals[k] += v
        out.append(f"| {r['case']} | {r['calls']} | "
                   + " | ".join(str(by.get(k, 0)) for k in REASONS)
                   + f" | {r['trims']} |")
    out.append("| **all** | " + str(sum(r["calls"] for r in rows)) + " | "
               + " | ".join(str(totals.get(k, 0)) for k in REASONS)
               + f" | {sum(r['trims'] for r in rows)} |")

    out.append("\n### What the refusals look like, by reason\n")
    out.append("| reason | n | median direct mm | median cursor miss | median target miss | median path (free / found) | rescued by radius | median rescue leg / path | the rest |")
    out.append("|---|---|---|---|---|---|---|---|---|")
    pool: dict[str, list[dict]] = collections.defaultdict(list)
    for r in rows:
        for c in r["refused"]:
            pool[c["reason"]].append(c)
    def med(vals):
        vals = sorted(v for v in vals if v is not None and math.isfinite(v))
        return round(vals[len(vals) // 2], 2) if vals else None
    for reason in REASONS:
        rs = pool.get(reason)
        if not rs:
            continue
        resc = [c for c in rs if c.get("rescued_at_mm") and c.get("rescue_within_cap")]
        blocked_after = sum(1 for c in rs if c.get("blocked_after_snap"))
        disconn = sum(1 for c in rs if c.get("blocked_after_snap") is False)
        out.append(f"| {reason} | {len(rs)} | {med(c['direct_mm'] for c in rs)} "
                   f"| {med(c['cursor_miss_mm'] for c in rs)} | {med(c['target_miss_mm'] for c in rs)} "
                   f"| {med(c.get('free_path_mm') or c.get('path_mm') for c in rs)} "
                   f"| {len(resc)}/{len(rs)} at <= {med(c['rescued_at_mm'] for c in resc) if resc else '-'} mm "
                   f"| {med(c['rescue_leg_mm'] for c in resc)} / {med(c['rescue_path_mm'] for c in resc)} "
                   f"| {blocked_after} sewn-blocked, {disconn} disconnected |")
    return "\n".join(out)


def compare_table(rows: list[dict], reach_mm: float) -> str:
    out = [f"### `satin_walk_cursor_reach_mm` OFF vs {reach_mm:g} mm\n",
           "| case | stitches | trims | exposed travel mm | grade | cursor_unsnapped walks |",
           "|---|---|---|---|---|---|"]
    tot = {a: collections.Counter() for a in ("off", "on")}
    for r in rows:
        o, n = r["off"], r["on"]
        for a, d in (("off", o), ("on", n)):
            for k in ("stitches", "trims", "cursor_unsnapped"):
                tot[a][k] += d[k]
            tot[a]["exposed_mm"] += d["exposed_mm"]
        out.append(f"| {r['case']} | {o['stitches']:,} → {n['stitches']:,} | {o['trims']} → {n['trims']} "
                   f"| {o['exposed_mm']} → {n['exposed_mm']} | {o['grade']} → {n['grade']} "
                   f"| {o['cursor_unsnapped']} → {n['cursor_unsnapped']} |")
    out.append(f"| **all** | {tot['off']['stitches']:,} → {tot['on']['stitches']:,} "
               f"| {tot['off']['trims']} → {tot['on']['trims']} "
               f"| {round(tot['off']['exposed_mm'], 1)} → {round(tot['on']['exposed_mm'], 1)} | — "
               f"| {tot['off']['cursor_unsnapped']} → {tot['on']['cursor_unsnapped']} |")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--only", nargs="*", help="case names to run (default: fixtures + corpus)")
    c = sub.add_parser("compare")
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--reach", type=float, default=5.0)
    c.add_argument("--only", nargs="*")
    t = sub.add_parser("tables")
    t.add_argument("json", type=Path)
    a = ap.parse_args(argv)
    if a.cmd == "run":
        cases = None
        if a.only:
            allc = FIXTURES + [(n, Path(p), float(w), g) for n, p, w, g in corpus_cases()]
            cases = [c for c in allc if c[0] in set(a.only)]
        print(tables(run(a.out, cases)))
    elif a.cmd == "compare":
        allc = FIXTURES + [(n, Path(p), float(w), g) for n, p, w, g in corpus_cases()]
        jobs = [x for x in allc if not a.only or x[0] in set(a.only)]
        rows = []
        for name, p_, w, g in jobs:
            rows.append(compare(name, Path(p_), w, g, a.reach))
            a.out.write_text(json.dumps(rows, indent=1), encoding="utf-8")
            r = rows[-1]
            print(f"{name}: trims {r['off']['trims']} -> {r['on']['trims']}, "
                  f"exposed {r['off']['exposed_mm']} -> {r['on']['exposed_mm']} mm", file=sys.stderr)
        print(compare_table(rows, a.reach))
    else:
        print(tables(json.loads(a.json.read_text(encoding="utf-8"))))


if __name__ == "__main__":
    main()
