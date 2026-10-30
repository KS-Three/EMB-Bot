#!/usr/bin/env python
"""edge_cap_remeasure: MASTER_SCOPE defect 19 re-measured -- the design's own
edge, what already sews along it, and what the edge cap bills across size.

    .venv/Scripts/python tools/edge_cap_remeasure.py attrib OUT.jsonl [--workers 4]
    .venv/Scripts/python tools/edge_cap_remeasure.py sweep  OUT.jsonl [--workers 4]
    .venv/Scripts/python tools/edge_cap_remeasure.py table  OUT.jsonl [OUT2.jsonl ...]

`attrib` digitizes the six `fill_exposure.SHORT` fixtures at 80 mm with the cap
off, bean and satin, and once per edge flag turned OFF (cap off), so each
flag's share of the covered silhouette shows as the bare share it leaves when
it is gone. `sweep` digitizes the satin cap and the pre-10-27 bean cap
(`bean_only_lines` OFF, since ON turns the bean style into no cap) across
60-120 mm, with Becker on the widths of docs/edge-cap-cliff-2026-09-12.md.
`table` prints both. Each job is one line of JSON; a rerun skips the jobs
already in OUT.jsonl.

The silhouette and the cover are `tools/pro_silhouette.py --ours`'s rule
exactly: the outer boundary of the union of the sewn regions, and every
satin / border / bean / run polyline at one thread width, read within
`BORDER_HOST_MARGIN_MM`. `art_bare_pct` leaves the cap's own runs out (the
design as if the cap were off), `all_bare_pct` puts them in. `cap_pts` is
the needle points on runs stamped `__edge_cap__`, ties included.
docs/edge-cap-remeasure-2026-10-29.md has the tables this wrote.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for p in (str(ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

FIXTURES = ["fremont", "becker", "enthusiast", "drone", "whitebg", "gaulke"]
#: The edge work landed since the 2026-09-11 measurement, all ON on main.
EDGE_FLAGS = ["border_by_size", "border_by_size_fabric_edges", "border_from_outline",
              "silhouette_underfill", "silhouette_underfill_rim", "outline_loop_mitre"]
SATIN = ("satin", {"edge_cap": "satin"})
BEAN_LEGACY = ("bean-legacy", {"edge_cap": "bean", "bean_only_lines": False})
BECKER_WIDTHS = [60, 70, 80, 86, 88, 90, 91, 92, 95, 95.7, 96, 100, 110, 120]


def attrib_jobs() -> list[dict]:
    arms = [("none", {"edge_cap": "none"}), ("bean", {"edge_cap": "bean"}), SATIN]
    arms += [(f"none-{f}", {"edge_cap": "none", f: False}) for f in EDGE_FLAGS]
    return [{"name": n, "width": 80.0, "tag": t, "over": o} for n in FIXTURES for t, o in arms]


def sweep_jobs() -> list[dict]:
    arms = [SATIN, BEAN_LEGACY]
    jobs = [{"name": "becker", "width": float(w), "tag": t, "over": o}
            for w in BECKER_WIDTHS for t, o in arms]
    for n in ("enthusiast", "whitebg", "gaulke", "drone"):
        jobs += [{"name": n, "width": float(w), "tag": t, "over": o}
                 for w in (60, 70, 90, 100, 120) for t, o in arms]
    jobs += [{"name": "fremont", "width": float(w), "tag": t, "over": o}
             for w in (60, 120) for t, o in arms]
    return jobs


def one(job: dict) -> dict:
    from shapely.geometry import LineString
    from shapely.ops import unary_union

    from digitizer_core import PipelineConfig, digitize, machine
    from digitizer_core.stage7_sequence import _LINEAR_KINDS
    from fill_exposure import SHORT

    name, width, over = job["name"], job["width"], job.get("over", {})
    rel, kw = SHORT.get(name, (name, {}))
    t0 = time.time()
    try:
        result, plan = digitize(ROOT / "testdata" / rel,
                                PipelineConfig(target_width_mm=width, **{**kw, **over}))
    except Exception as e:  # noqa: BLE001 -- a failed cell is a row, not a dead sweep
        return {**job, "error": repr(e)}
    polys = [r.polygon for r in result.regions if r.meta.get("stitched", True)]
    union = unary_union(polys)
    parts = [g for g in getattr(union, "geoms", [union]) if g.geom_type == "Polygon"]
    outer = unary_union([LineString(p.exterior.coords) for p in parts])
    total = float(outer.length)
    tol = machine.BORDER_HOST_MARGIN_MM
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    by_kind: dict[str, list] = {}
    art, cap = [], []
    for b in plan.blocks:
        for r in b.runs:
            if r.kind in _LINEAR_KINDS and len(r.points) > 1:
                ribbon = LineString(r.points).buffer(half)
                if r.shape_id == "__edge_cap__":
                    cap.append(ribbon)
                else:
                    art.append(ribbon)
                    by_kind.setdefault(r.kind, []).append(ribbon)

    def covered(ribbons) -> float:
        if not ribbons:
            return 0.0
        return float(outer.intersection(unary_union(ribbons).buffer(tol)).length)

    def bare(mm: float) -> float | None:
        return round(100 * (1 - mm / total), 1) if total else None

    return {
        **job,
        "parts": len(parts),
        "sil_mm": round(total, 1),
        "art_bare_pct": bare(covered(art)),
        "all_bare_pct": bare(covered(art + cap)),
        "kinds_cover_pct": ({k: round(100 * covered(v) / total, 1) for k, v in by_kind.items()}
                            if total else {}),
        "stitches": plan.stats.stitch_count,
        "trims": plan.stats.trims,
        "cap_pts": sum(len(r.points) for b in plan.blocks for r in b.runs
                       if r.shape_id == "__edge_cap__"),
        "secs": round(time.time() - t0, 1),
    }


def _key(d: dict) -> str:
    return json.dumps([d["name"], d["width"], d.get("tag")])


def run(out: Path, jobs: list[dict], workers: int) -> None:
    from multiprocessing import Pool

    done = set()
    if out.exists():
        done = {_key(d) for d in map(json.loads, out.read_text().splitlines())
                if "error" not in d}
    jobs = [j for j in jobs if _key(j) not in done]
    print(f"{len(jobs)} jobs", flush=True)
    with Pool(workers, maxtasksperchild=4) as pool, out.open("a") as fh:
        for r in pool.imap_unordered(one, jobs):
            fh.write(json.dumps(r) + "\n")
            fh.flush()
            print(r["name"], r["width"], r["tag"], r.get("all_bare_pct"), r.get("secs"),
                  r.get("error", ""), flush=True)


def table(paths: list[Path]) -> None:
    rows = [json.loads(line) for p in paths for line in p.read_text().splitlines()]
    rows = [r for r in rows if "error" not in r]
    attrib = [r for r in rows if r["width"] == 80.0 and r["tag"].startswith("none")]
    if attrib:
        print("80 mm, cap off: bare % of the sewn silhouette, all ON | each flag OFF")
        print(f"{'fixture':11s} {'all ON':>7s} " + " ".join(f"{f[:14]:>14s}" for f in EDGE_FLAGS))
        for n in FIXTURES:
            got = {r["tag"]: r for r in attrib if r["name"] == n}
            if "none" not in got:
                continue
            cells = [f"{got[f'none-{f}']['art_bare_pct']:14.1f}" if f"none-{f}" in got
                     else f"{'-':>14s}" for f in EDGE_FLAGS]
            print(f"{n:11s} {got['none']['art_bare_pct']:7.1f} " + " ".join(cells))
    by: dict = {}
    for r in rows:
        if r["tag"] in ("satin", "bean-legacy", "none"):
            by.setdefault(r["name"], {}).setdefault(r["width"], {})[r["tag"]] = r

    def cell(x) -> str:
        if not x:
            return f"{'-':>22s}"
        art = x["stitches"] - x["cap_pts"]
        return f"{x['cap_pts']:5d} (+{100 * x['cap_pts'] / art:4.1f}%) {x['all_bare_pct']:5.1f}%"

    print("\nwidth | bare, no cap | satin cap: pts (+% art) bare | bean (legacy): pts (+% art) bare")
    for n, ws in by.items():
        print(n)
        for w in sorted(ws):
            a = ws[w]
            ref = a.get("satin") or a.get("none") or a.get("bean-legacy")
            print(f"  {w:6.1f} | {ref['art_bare_pct']:5.1f}% | {cell(a.get('satin'))} | "
                  f"{cell(a.get('bean-legacy'))}")


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("attrib", "sweep", "table"):
        print(__doc__)
        return 1
    workers = int(argv[argv.index("--workers") + 1]) if "--workers" in argv else 4
    paths = [Path(a) for a in argv[1:] if not a.startswith("--") and not a.isdigit()]
    if argv[0] == "table":
        table(paths)
        return 0
    os.environ.setdefault("OPENCV_IPP", "avx2")
    run(paths[0], attrib_jobs() if argv[0] == "attrib" else sweep_jobs(), workers)
    return 0


if __name__ == "__main__":
    if {"-h", "--help"} & set(sys.argv[1:]):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        print(__doc__ or "No usage text; see the source.")
        raise SystemExit(0)
    raise SystemExit(main(sys.argv[1:]))
