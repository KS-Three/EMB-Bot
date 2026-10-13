"""Why does `cfg.hairline` raise "thread over bare fabric"? (2026-10-13)

    python -m tools.hairline_travel run   [--fixtures a,b] [--arms off,on,...] [--force]
    python -m tools.hairline_travel table
    python -m tools.hairline_travel render [--fixture photo/logo_golden_tee.jpg]

PR #888 found a side effect: on golden_tee the travel-over-bare-fabric number
of `tests/test_chaining.py::_thread_bare_mm` rises from 19.9 to 75.2 mm when
`cfg.hairline` is ON. This tool takes that number apart.

`_thread_bare_mm` walks, for every `TRAVEL` run, the path
`previous run's last point -> the TRAVEL run's own points -> next run's first
point` and counts the length further than half a thread width from ANY laid
stitch. It was written for chaining links (`jump=False`: the needle stays down,
the thread is dragged), and it never reads `run.jump` / `run.trim`. But a
`TRAVEL` run can also be the walk-in that follows a TRIMMED jump (a lock
stitch, then a few stitches along the next column's centreline): the needle
lifts, the thread is cut, the machine flies to the walk's first point, and
there is no thread at all on the flight. The instrument counts that flight as
thread on bare fabric.

So each `TRAVEL` run's path is split into three legs and each is named:

- `in`    previous run's last point -> the run's first point. Thread iff the run
          is not a jump, or is a jump that is NOT trimmed (a dragged float).
          A trimmed jump is a FLIGHT: no thread, counted on its own line.
- `body`  the run's own stitches. Always thread.
- `out`   the run's last point -> the next run's first point. Thread iff the
          next run is not a trimmed jump.

and reported per arm: `legacy` (the instrument as shipped), `thread` (bare mm
on the legs that really are thread: the corrected number), `flight` (mm of
trimmed-jump flight on bare fabric, which the legacy number included), and the
trims / stitches beside them. Every number is a property of the FILE, not a
sew-out (ROADMAP gate 1).

Arms (`matrix[0]` = 80 mm / left_chest, 40 wt, stages 0-4 once per fixture):
`off`, `on` (hairline, drop guard ON), `on_nodrop`, `on_cov` (+ coverage guard),
`on_cov_nodrop`.

What it found (docs/renders/claude-hairline-bare-travel/table.md): the rise is
flights, not thread. Corrected, thread over bare fabric does NOT rise with
`cfg.hairline`; what rises is the number of trims (hairline shapes break into a
rest piece plus strand pieces that sit more than the trim distance apart) and
the length the needle flies. A flight is a cut jump, which is what a pro does;
the only way to remove it is to drag thread across the cloth, which is the
thing the instrument exists to forbid. No fix was built: see the PR.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core import stage6_hairline as s6h  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools import corpus_scorecard as sc  # noqa: E402
from tools.hairline_logo_bill import row_key  # noqa: E402

TESTDATA = sc.TESTDATA
OUT_DIR = ROOT.parent / "docs" / "renders" / "claude-hairline-bare-travel"
LOGOS = ("photo/enthusiast_logo.png", "photo/screenshot_phone_ui_golke.jpg",
         "photo/logo_hotel_fremont.webp", "photo/logo_golden_tee.jpg",
         "photo/drone_render.png", "photo/logo_bridge_bar.jpg",
         "photo/logo_gaulke_roofing.png", "photo/summit_badge.png",
         "logo_alpha.png", "logo_whitebg.png")
ARMS = ("off", "on", "on_nodrop", "on_cov", "on_cov_nodrop")
STEP_MM = 0.1


def arm_setup(arm: str) -> tuple[dict, bool]:
    """-> (cfg overrides, drop guard on?)"""
    kw: dict = {}
    if arm != "off":
        kw["hairline"] = True
    if "cov" in arm:
        kw["hairline_coverage_guard"] = True
    return kw, "nodrop" not in arm


def _is_flight(run) -> bool:
    """A trimmed jump: the needle lifts and the thread is cut."""
    return bool(run.jump and run.trim)


def legs(plan) -> list[dict]:
    """Every leg of every TRAVEL run's path, with what it is and who owns it."""
    runs = [r for b in plan.blocks for r in b.runs]
    out = []
    for i, run in enumerate(runs):
        if run.kind != stitches.TRAVEL or not run.points:
            continue
        prev = runs[i - 1] if i and runs[i - 1].points else None
        nxt = runs[i + 1] if i + 1 < len(runs) and runs[i + 1].points else None
        if prev is not None:
            out.append({"i": i, "leg": "in", "pts": [prev.points[-1], run.points[0]],
                        "flight": _is_flight(run), "own": run.shape_id,
                        "from": (prev.kind, prev.shape_id), "to": (run.kind, run.shape_id)})
        if len(run.points) >= 2:
            out.append({"i": i, "leg": "body", "pts": list(run.points), "flight": False,
                        "own": run.shape_id, "from": (run.kind, run.shape_id),
                        "to": (run.kind, run.shape_id)})
        if nxt is not None:
            out.append({"i": i, "leg": "out", "pts": [run.points[-1], nxt.points[0]],
                        "flight": _is_flight(nxt), "own": run.shape_id,
                        "from": (run.kind, run.shape_id), "to": (nxt.kind, nxt.shape_id)})
    return out


def _thread_zone(plan):
    """An STRtree over every laid run's centreline (buffering the whole union
    to a polygon runs out of memory on a dense plan)."""
    laid = [LineString(r.points) for b in plan.blocks for r in b.runs
            if r.kind != stitches.TRAVEL and len(r.points) >= 2]
    return shapely.STRtree(laid) if laid else None


def bare_mm(zone, pts) -> float:
    """Length of the polyline `pts` further than half a thread width from any
    laid stitch (sampled every STEP_MM, like the shipped instrument)."""
    if zone is None or len(pts) < 2:
        return 0.0
    path = LineString(pts)
    n = max(2, int(path.length / STEP_MM))
    pp = shapely.line_interpolate_point(path, np.linspace(0.0, 1.0, n + 1), normalized=True)
    hit = zone.query(pp, predicate="dwithin", distance=machine.COVERAGE_THREAD_W_MM / 2.0)
    covered = np.zeros(len(pp), bool)
    covered[hit[0]] = True
    return float((~covered).sum()) * path.length / n


def trim_anatomy(plan) -> dict:
    """Every trimmed jump in the plan (not only the ones a TRAVEL run follows):
    how many open a block (a colour change, unavoidable), how many sit INSIDE
    one shape (the shape's own pieces: rest + strands), how many go between
    shapes, and the length the needle flies on all of them."""
    block_start = in_shape = between = 0
    fly = 0.0
    for b in plan.blocks:
        prev = None
        for r in b.runs:
            if r.trim and r.points:
                if prev is None:
                    block_start += 1
                else:
                    d = math.dist(prev.points[-1], r.points[0])
                    fly += d
                    if prev.shape_id == r.shape_id:
                        in_shape += 1
                    else:
                        between += 1
            if r.points:
                prev = r
    return {"trims_block_start": block_start, "trims_in_shape": in_shape,
            "trims_between_shapes": between, "flight_total_mm": round(fly, 2)}


def measure_plan(plan, with_legacy: bool = True) -> dict:
    zone = _thread_zone(plan)
    thread = flight = 0.0
    thread_links = flight_links = 0
    by_leg = {"in": 0.0, "body": 0.0, "out": 0.0}
    worst: list[dict] = []
    for lg in legs(plan):
        b = bare_mm(zone, lg["pts"])
        if lg["flight"]:
            flight += b
            flight_links += b > 0
            continue
        thread += b
        by_leg[lg["leg"]] += b
        if b > 0:
            thread_links += 1
            worst.append({"i": lg["i"], "leg": lg["leg"], "bare_mm": round(b, 2),
                          "from": list(lg["from"]), "to": list(lg["to"])})
    worst.sort(key=lambda w: -w["bare_mm"])
    row = {"stitches": plan.stats.stitch_count, "trims": plan.stats.trims,
           "thread_bare_mm": round(thread, 2), "thread_exposed_legs": int(thread_links),
           "thread_by_leg": {k: round(v, 2) for k, v in by_leg.items()},
           "flight_bare_mm": round(flight, 2), "flight_legs": int(flight_links),
           **trim_anatomy(plan),
           "worst": worst[:6]}
    if with_legacy:
        from tests.test_chaining import _thread_bare_mm
        links, exposed, mm, _w = _thread_bare_mm(plan)
        row["legacy"] = {"links": links, "exposed": exposed, "mm": round(mm, 2)}
    return row


def run_one(fixture: str, wt: int, arms: tuple, with_legacy: bool) -> dict:
    cfg_kw = sc.MATRIX[0]
    base = dict(cfg_kw, thread_wt=wt)
    t0 = time.perf_counter()
    result = run_stages(TESTDATA / fixture, PipelineConfig(**base))
    out = {"fixture": fixture, "matrix": cfg_kw, "thread_wt": wt,
           "stage0_4_s": round(time.perf_counter() - t0, 1), "arms": {}}
    for arm in arms:
        kw, drop = arm_setup(arm)
        if any(k not in PipelineConfig.__dataclass_fields__ for k in kw):
            continue
        s6h.DROP_GUARD = drop
        try:
            plan = plan_stitches(result, PipelineConfig(**base, **kw))
        finally:
            s6h.DROP_GUARD = True
        out["arms"][arm] = measure_plan(plan, with_legacy)
    return out


def _load(out: Path) -> dict:
    f = out / "rows.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fixtures = args.fixtures.split(",") if args.fixtures else list(LOGOS)
    arms = tuple(a for a in args.arms.split(",") if a)
    for fx in fixtures:
        key = row_key(fx, sc.MATRIX[0])
        rows = _load(out)
        if key in rows and "error" not in rows[key] and not args.force:
            print(f"{key}: cached")
            continue
        try:
            rows[key] = run_one(fx, args.wt, arms, not args.no_legacy)
        except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
            rows[key] = {"fixture": fx, "error": f"{type(exc).__name__}: {exc}"}
        r = rows[key]
        print(f"{key}: ERROR {r['error']}" if "error" in r else f"{key}: " + " | ".join(
            f"{a} thread {v['thread_bare_mm']} flight {v['flight_bare_mm']} trims {v['trims']}"
            for a, v in r["arms"].items()), flush=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


def markdown(rows: dict) -> str:
    ok = {k: r for k, r in rows.items() if "error" not in r}
    arms = [a for a in ARMS
            if any(a in r["arms"] for r in ok.values())]
    lines = ["### legacy `_thread_bare_mm` mm / corrected thread-over-bare mm / trimmed-flight-over-bare mm "
             "/ trims (of which inside one shape) / stitches", "",
             "| fixture | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for k, r in sorted(ok.items()):
        cells = []
        for a in arms:
            v = r["arms"].get(a)
            cells.append("-" if v is None else
                         f"{v.get('legacy', {}).get('mm', '-')} / **{v['thread_bare_mm']}** / "
                         f"{v['flight_bare_mm']} / {v['trims']} ({v['trims_in_shape']}) / {v['stitches']:,}")
        lines.append(f"| {k.split(' @ ')[0]} | " + " | ".join(cells) + " |")
    lines += ["", "### What is still thread over bare fabric, worst legs per arm", ""]
    for k, r in sorted(ok.items()):
        for a, v in r["arms"].items():
            if v["worst"] and v["thread_bare_mm"] > 0:
                lines.append(f"- {k.split(' @ ')[0]} `{a}`: " + "; ".join(
                    f"{w['leg']} {w['bare_mm']} mm {w['from'][0]} {w['from'][1]} -> {w['to'][0]} {w['to'][1]}"
                    for w in v["worst"][:3]))
    bad = {k: r["error"] for k, r in rows.items() if "error" in r}
    if bad:
        lines += ["", "### Errors", ""] + [f"- {k}: {e}" for k, e in bad.items()]
    return "\n".join(lines) + "\n"


def cmd_table(args) -> int:
    out = Path(args.out)
    (out / "table.md").write_text(markdown(_load(out)), encoding="utf-8")
    print(markdown(_load(out)))
    return 0


def cmd_render(args) -> int:
    """OFF | ON on one fixture, the travel legs drawn over the stitches: a
    trimmed flight in blue (the needle is up, no thread), thread over bare
    fabric in red, a link or walk over thread in green. Whole design, then a
    zoom (30 px/mm) on the shapes whose in-shape trims rose."""
    import cv2
    from tools.hairline_logo_bill import (RENDER_PX_PER_MM, ZOOM_PX_PER_MM, _write_png)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    base = dict(sc.MATRIX[0], thread_wt=args.wt)
    result = run_stages(TESTDATA / args.fixture, PipelineConfig(**base))
    labels = ("today (OFF)", "hairline ON")
    plans = [plan_stitches(result, PipelineConfig(**base)),
             plan_stitches(result, PipelineConfig(**base, hairline=True))]
    if args.zoom:
        box = tuple(float(v) for v in args.zoom.split(","))
    else:
        box = _rose_box(plans[0], plans[1])
    name = Path(args.fixture).stem
    whole = [_travel_panel(pl, lb, args.wt, RENDER_PX_PER_MM) for pl, lb in zip(plans, labels)]
    _write_png(out / f"{name}_travel_compare.png", _hstack(whole))
    zoom = [_travel_panel(pl, lb, args.wt, ZOOM_PX_PER_MM, box) for pl, lb in zip(plans, labels)]
    _write_png(out / f"{name}_travel_zoom.png", _hstack(zoom))
    return 0


def _hstack(panels):
    import cv2
    h = max(p.shape[0] for p in panels)
    panels = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, 0, cv2.BORDER_CONSTANT,
                                 value=(255, 255, 255)) for p in panels]
    sep = np.full((h, 4, 3), 200, np.uint8)
    out = panels[0]
    for p in panels[1:]:
        out = np.hstack([out, sep, p])
    return out


def _in_shape_ids(plan) -> dict:
    cnt: dict = {}
    for b in plan.blocks:
        prev = None
        for r in b.runs:
            if r.trim and prev is not None and prev.shape_id == r.shape_id:
                cnt[r.shape_id] = cnt.get(r.shape_id, 0) + 1
            if r.points:
                prev = r
    return cnt


def _rose_box(off, on) -> tuple[float, float, float, float]:
    """(cx, cy, hw, hh) mm around every shape whose in-shape trims rose."""
    a, b = _in_shape_ids(off), _in_shape_ids(on)
    ids = {s for s, n in b.items() if n > a.get(s, 0)}
    xs, ys = [], []
    for blk in on.blocks:
        for r in blk.runs:
            if r.shape_id in ids:
                xs += [p[0] for p in r.points]
                ys += [p[1] for p in r.points]
    if not xs:
        return 0.0, 0.0, 10.0, 8.0
    return ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2,
            (max(xs) - min(xs)) / 2 + 2.0, (max(ys) - min(ys)) / 2 + 2.0)


def _travel_panel(plan, label, wt, px_per_mm, box=None):
    """The stitch render with the travel legs drawn over it. `box` = (cx, cy,
    hw, hh) in plan mm crops to a window."""
    import cv2
    from digitizer_core.adapter import plan_to_design
    from digitizer_core import stitchviz
    design = plan_to_design(plan, name=label)
    img = stitchviz.render_design(design, px_per_mm=px_per_mm,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], px_per_mm, 2.0)
    u = stitchviz.UNITS_PER_MM
    zone = _thread_zone(plan)

    def px(p):
        a, b = to_px({"x": p[0] * u, "y": -p[1] * u})
        return int(a), int(b)
    scale = max(1, int(round(px_per_mm / 6.0)))
    for lg in legs(plan):
        pts = lg["pts"]
        if len(pts) < 2:
            continue
        if lg["flight"]:
            col, th = (230, 120, 20), 1                 # blue (BGR): needle up, no thread
        elif bare_mm(zone, pts) > 0:
            col, th = (30, 30, 230), max(2, scale)      # red: thread over bare fabric
        else:
            col, th = (60, 170, 60), 1                  # green: over thread
        for p, q in zip(pts, pts[1:]):
            cv2.line(img, px(p), px(q), col, th, cv2.LINE_AA)
    if box is not None:
        cx, cy, hw, hh = box
        ax, ay = px((cx - hw, cy - hh))
        bx, by = px((cx + hw, cy + hh))
        top, bot = sorted((ay, by))
        lft, rgt = sorted((ax, bx))
        crop = img[max(top, 0):max(bot, 1), max(lft, 0):max(rgt, 1)]
        canvas = np.full((int(2 * hh * px_per_mm), int(2 * hw * px_per_mm), 3), 255, np.uint8)
        canvas[:crop.shape[0], :crop.shape[1]] = crop[:canvas.shape[0], :canvas.shape[1]]
        img = canvas
    band = np.full((30, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", default="")
    r.add_argument("--arms", default=",".join(ARMS))
    r.add_argument("--wt", type=int, default=40)
    r.add_argument("--force", action="store_true")
    r.add_argument("--no-legacy", action="store_true", help="skip the shipped (slow) instrument")
    r.set_defaults(fn=cmd_run)
    t = sub.add_parser("table")
    t.set_defaults(fn=cmd_table)
    d = sub.add_parser("render")
    d.add_argument("--fixture", default="photo/logo_golden_tee.jpg")
    d.add_argument("--wt", type=int, default=40)
    d.add_argument("--zoom", default="", help="cx,cy,hw,hh in plan mm; default the shapes whose in-shape trims rose")
    d.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
