"""Hairline tier: does it leave bare fabric on ordinary logos? (2026-10-13)

    python -m tools.hairline_coverage run   [--fixtures a,b] [--arms off,on,...] [--force]
    python -m tools.hairline_coverage table
    python -m tools.hairline_coverage render [--fixture photo/logo_gaulke_roofing.png]

#872 priced `cfg.hairline` on the scorecard logos and found bare fabric and new
`ARTWORK_UNCOVERED` findings; #879 added the drop guard (a shape that would erase
more than 2 % of its strand length is handed back). This tool asks the next
question: which shapes lose coverage when they are converted, by how much, and
why — and does `cfg.hairline_coverage_guard` stop it.

Arms (all `matrix[0]` = 80 mm / left_chest, 40 wt, stages 0-4 once per fixture):

- `off`          `cfg.hairline` False: today.
- `on`           `cfg.hairline` True, the drop guard ON (`stage6_hairline.DROP_GUARD`).
- `on_nodrop`    `cfg.hairline` True, drop guard OFF (#872's arm).
- `on_cov`       `on` + `cfg.hairline_coverage_guard`.
- `on_cov_nodrop` `on_nodrop` + `cfg.hairline_coverage_guard`.

Per arm: stitches, trims, preflight's `ARTWORK_UNCOVERED` (total mm2, shape ids),
the bare-fabric total (`hairline_renders.bare_cells`: artwork cells with no
thread, the instrument #872 reported), and `tests/test_chaining.py`'s
`_thread_bare_mm` (thread TRAVELLING over bare fabric: links, exposed links, mm,
worst clearance). Those are two different instruments; the second is about
travel links, the first about the artwork itself, and both are recorded.

Per shape the gate admits (drop guard off, so every shape the width gate and the
ground rule let through): ink area, widths, strands laid / dropped, the plan-time
prediction `stage6_hairline.strand_bare_mm2`, and — per ON arm — the bare cells
that appear against OFF, attributed to the shape and split by cause:

- `edge_mm2`     inside the shape, within 0.5 mm of a laid run: the run is
                 narrower than the stroke it replaced (a 0.4 mm ribbon on a
                 wider stroke leaves both edges bare);
- `erased_mm2`   inside the shape, farther than 0.5 mm from any laid run: a
                 strand the walk dropped, its ink erased;
- `ground_mm2`   outside the shape but within 0.6 mm of it: a gap in the colour
                 beneath that the strand no longer closes (the ground-gap case).

Every number is a property of the FILE, not of a sew-out (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitches  # noqa: E402
from digitizer_core import stage6_hairline as s6h  # noqa: E402
from digitizer_core.pipeline import (  # noqa: E402
    _fill_inside_satin_border, plan_stitches, run_stages)
from digitizer_core.stage6_hairline import (  # noqa: E402
    hairline_candidates, hairline_runs, strand_bare_mm2)
from tools import corpus_scorecard as sc  # noqa: E402
from tools.hairline_logo_bill import _hair_matrix, measure_mode, row_key  # noqa: E402
from tools.hairline_renders import bare_cells  # noqa: E402

TESTDATA = sc.TESTDATA
OUT_DIR = ROOT.parent / "docs" / "renders" / "claude-hairline-coverage-guard"

# The logos #872 found captures on, plus two flat logos it found none on
# (the control: a guard must leave them alone).
LOGOS = ("photo/enthusiast_logo.png", "photo/screenshot_phone_ui_golke.jpg",
         "photo/logo_hotel_fremont.webp", "photo/logo_golden_tee.jpg",
         "photo/drone_render.png", "photo/logo_bridge_bar.jpg",
         "photo/logo_gaulke_roofing.png", "photo/summit_badge.png",
         "logo_alpha.png", "logo_whitebg.png")
ARMS = ("off", "on", "on_nodrop", "on_cov", "on_cov_nodrop")
NO_TRAVEL = False          # --no-travel: skip `_thread_bare_mm` (minutes per plan on a hair network)
EDGE_REACH_MM = 0.5      # a bare cell nearer than this to a laid run is a narrow-run edge
GROUND_REACH_MM = 0.6    # a bare cell this near a captured shape, outside it, is a ground gap


def arm_setup(arm: str) -> tuple[dict, bool]:
    """-> (cfg overrides, drop guard on?)"""
    kw: dict = {}
    if arm != "off":
        kw["hairline"] = True
    if arm.startswith("on_cov"):
        kw["hairline_coverage_guard"] = True
    return kw, "nodrop" not in arm


def thread_bare(plan) -> dict:
    if NO_TRAVEL:
        return {"links": 0, "exposed": 0, "mm": 0.0, "worst_mm": 0.0, "skipped": True}
    from tests.test_chaining import _thread_bare_mm
    links, exposed, mm, worst = _thread_bare_mm(plan)
    return {"links": links, "exposed": exposed, "mm": round(mm, 3), "worst_mm": round(worst, 3)}


def new_bare_cells(off, on):
    """Cells bare in `on` and not in `off` (and the reverse count), as plan-mm
    centres. Each grid is (bool bare, (x0, y0) mm origin, cell mm); the two
    origins differ because each plan's thread extent does."""
    og, (ox, oy), cell = off
    ng, (nx0, ny0), _ = on
    iy, ix = np.nonzero(ng)
    xs = nx0 + (ix + 0.5) * cell
    ys = ny0 + (iy + 0.5) * cell
    jx = np.floor((xs - ox) / cell).astype(np.int64)
    jy = np.floor((ys - oy) / cell).astype(np.int64)
    inside = (jx >= 0) & (jx < og.shape[1]) & (jy >= 0) & (jy < og.shape[0])
    off_at = np.ones(len(xs), bool)          # off the OFF grid there was no thread: bare
    off_at[inside] = og[jy[inside], jx[inside]]
    new = ~off_at
    fixed = None
    # Cells bare in OFF and covered in ON: the reverse, counted by area only.
    ngy, ngx = np.nonzero(og)
    oxs = ox + (ngx + 0.5) * cell
    oys = oy + (ngy + 0.5) * cell
    kx = np.floor((oxs - nx0) / cell).astype(np.int64)
    ky = np.floor((oys - ny0) / cell).astype(np.int64)
    inn = (kx >= 0) & (kx < ng.shape[1]) & (ky >= 0) & (ky < ng.shape[0])
    on_at = np.ones(len(oxs), bool)
    on_at[inn] = ng[ky[inn], kx[inn]]
    fixed = int((~on_at).sum())
    return xs[new], ys[new], cell, fixed


def laid_by_shape(plan) -> dict[str, list]:
    out: dict[str, list] = {}
    for _b, r in plan.iter_runs():
        if r.kind == stitches.TRAVEL or len(r.points) < 2:
            continue
        out.setdefault(r.shape_id, []).append(LineString(r.points))
    return out


def attribute(off_bare, on_bare, cands: dict, plan) -> dict:
    """New bare cells of `plan` against OFF -> per-candidate mm2 split by cause,
    plus the cells no candidate owns. `cands` = {sid: polygon}."""
    xs, ys, cell, fixed = new_bare_cells(off_bare, on_bare)
    a = cell * cell
    laid = laid_by_shape(plan)
    left = np.ones(len(xs), bool)
    per: dict[str, dict] = {}
    for sid, poly in cands.items():
        inside = left & shapely.contains_xy(poly, xs, ys)
        edge = erased = 0
        if inside.any():
            lines = laid.get(sid)
            if lines:
                d = shapely.distance(shapely.points(xs[inside], ys[inside]), unary_union(lines))
                edge = int((d <= EDGE_REACH_MM).sum())
                erased = int((d > EDGE_REACH_MM).sum())
            else:
                erased = int(inside.sum())
            left &= ~inside
        per[sid] = {"edge_mm2": edge * a, "erased_mm2": erased * a, "ground_mm2": 0.0}
    for sid, poly in cands.items():
        near = left & shapely.contains_xy(poly.buffer(GROUND_REACH_MM), xs, ys)
        per[sid]["ground_mm2"] = float(near.sum()) * a
        left &= ~near
    for v in per.values():
        for k in v:
            v[k] = round(v[k], 2)
        v["new_bare_mm2"] = round(v["edge_mm2"] + v["erased_mm2"] + v["ground_mm2"], 2)
    return {"per_shape": per, "unattributed_mm2": round(float(left.sum()) * a, 2),
            "new_bare_mm2": round(len(xs) * a, 2), "resolved_mm2": round(fixed * a, 2)}


def measure_arm(plan, result, p, cfg, off_bare=None, cands=None) -> tuple[dict, tuple]:
    row = measure_mode(plan, result, p, cfg)
    row["thread_bare"] = thread_bare(plan)
    bare = bare_cells(plan, result, p)
    if off_bare is not None:
        row["attribution"] = attribute(off_bare, bare, cands, plan)
    return row, bare


def candidate_table(result, cfg_on) -> tuple[list[dict], dict]:
    """Every shape the gate admits with the drop guard OFF -> rows + {sid: polygon}."""
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    if cfg_on.fill_inside_satin_border:
        stitched = _fill_inside_satin_border(stitched, cfg_on, result.design_class)
    keep = s6h.DROP_GUARD
    s6h.DROP_GUARD = False
    try:
        cands = hairline_candidates(stitched, cfg_on, ink=getattr(result, "ink_source", None))
    finally:
        s6h.DROP_GUARD = keep
    prof = machine.thread_profile(cfg_on.thread_wt)
    by_id = {r.shape_id: r for r in stitched}
    rows, polys = [], {}
    from shapely.strtree import STRtree
    tree = STRtree([q.polygon for q in stitched])
    half = machine.COVERAGE_THREAD_W_MM / 2.0
    for sid, m in cands.items():
        r = by_id[sid]
        runs, rep = hairline_runs(r.polygon, sid, max_width_mm=prof.hairline_max_width_mm,
                                  run_width_mm=prof.hairline_run_width_mm,
                                  stitch_mm=cfg_on.hairline_stitch_mm, entry=None,
                                  trim_at_mm=machine.TRIM_AT_MM, m=m)
        polys[sid] = r.polygon
        x0, y0, x1, y1 = r.polygon.bounds
        rows.append({
            "shape_id": sid, "area_mm2": round(r.polygon.area, 2),
            "bbox_mm": [round(v, 1) for v in (x0, y0, x1, y1)],
            "width_mm": round(m["width_mm"], 3),
            "width_source_mm": None if m["width_source_mm"] is None else round(m["width_source_mm"], 3),
            "strands": rep["strands"], "dropped": rep["dropped"],
            "dropped_mm": round(rep["dropped_mm"], 3), "sewn_mm": round(rep["sewn_mm"], 2),
            "bare_est_mm2": round(strand_bare_mm2(r.polygon, runs, m), 3),
        })
        # Calibration features: the ink of OTHER shapes within g mm of this
        # one (the ground its planned polygon's growth used to cover), and
        # the strict own-ribbon bare (no instrument slack).
        ribbons = unary_union([LineString(ru.points).buffer(half) for ru in runs
                               if len(ru.points) >= 2]) if runs else None
        near = [q.polygon for i in tree.query(r.polygon.buffer(0.45))
                if (q := stitched[int(i)]).shape_id != sid]
        other = unary_union(near) if near else None
        for g in (0.1, 0.2, 0.3, 0.4):
            ring = r.polygon.buffer(g).difference(r.polygon)
            gnd = ring.intersection(other) if other is not None else ring.difference(ring)
            if ribbons is not None:
                gnd = gnd.difference(ribbons)
            rows[-1][f"ground_est_{g}"] = round(gnd.area, 3)
        rows[-1]["own_strict_mm2"] = round(
            (r.polygon if ribbons is None else r.polygon.difference(ribbons)).area, 3)
    rows.sort(key=lambda c: -c["area_mm2"])
    return rows, polys


def run_one(fixture: str, cfg_kw: dict, wt: int, arms: tuple) -> dict:
    path = TESTDATA / fixture
    base = dict(cfg_kw, thread_wt=wt)
    t0 = time.perf_counter()
    result = run_stages(path, PipelineConfig(**base))
    p = preflight.prep(path, PipelineConfig(**base), design_class=result.design_class)
    out: dict = {"fixture": fixture, "matrix": cfg_kw, "thread_wt": wt,
                 "design_class": str(result.design_class),
                 "stage0_4_s": round(time.perf_counter() - t0, 1), "arms": {}}
    cand_rows, polys = candidate_table(result, PipelineConfig(**base, hairline=True))
    out["candidates"] = cand_rows
    off_bare = None
    for arm in arms:
        kw, drop = arm_setup(arm)
        if "hairline_coverage_guard" in kw and not hasattr(PipelineConfig(), "hairline_coverage_guard"):
            continue
        s6h.DROP_GUARD = drop
        try:
            cfg = PipelineConfig(**base, **kw)
            t0 = time.perf_counter()
            plan = plan_stitches(result, cfg)
            el = time.perf_counter() - t0
            row, bare = measure_arm(plan, result, p, cfg, off_bare, polys)
        finally:
            s6h.DROP_GUARD = True
        row["plan_s"] = round(el, 1)
        if arm == "off":
            off_bare = bare
        out["arms"][arm] = row
    return out


def _load(out: Path) -> dict:
    f = out / "rows.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_run(args) -> int:
    global NO_TRAVEL
    NO_TRAVEL = args.no_travel
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fixtures = args.fixtures.split(",") if args.fixtures else list(LOGOS)
    arms = tuple(a for a in args.arms.split(",") if a and a != "none")
    for fx in fixtures:
        cfg_kw = _hair_matrix(fx)[0] if fx.startswith("synthetic/") else sc.MATRIX[0]
        key = row_key(fx, cfg_kw)
        rows = _load(out)             # re-read: workers share the file through merge only
        if key in rows and "error" not in rows[key] and not args.force:
            print(f"{key}: cached")
            continue
        try:
            rows[key] = run_one(fx, cfg_kw, args.wt, arms)
        except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
            rows[key] = {"fixture": fx, "matrix": cfg_kw, "error": f"{type(exc).__name__}: {exc}"}
        r = rows[key]
        if "error" in r:
            print(f"{key}: ERROR {r['error']}", flush=True)
        else:
            print(f"{key}: " + " | ".join(
                f"{a} bare {v['bare_mm2']} unc {(v['artwork_uncovered'] or {}).get('total_mm2', 0)}"
                for a, v in r["arms"].items()), flush=True)
        (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


def cmd_merge(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = _load(out)
    for d in args.dirs:
        rows.update(_load(Path(d)))
    (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows")
    return 0


def _unc(a: dict) -> float:
    return (a["artwork_uncovered"] or {}).get("total_mm2", 0.0)


def markdown(rows: dict) -> str:
    ok = {k: r for k, r in rows.items() if "error" not in r}
    arms = [a for a in ARMS if any(a in r["arms"] for r in ok.values())]
    lines = ["### Per fixture: ARTWORK_UNCOVERED mm2 / bare-fabric mm2 / thread over bare fabric mm "
             "(travel links, `_thread_bare_mm`) / stitches", "",
             "| fixture | " + " | ".join(arms) + " |", "|---|" + "---|" * len(arms)]
    for k, r in sorted(ok.items()):
        cells = []
        for a in arms:
            v = r["arms"].get(a)
            cells.append("-" if v is None else
                         f"{_unc(v)} / {v['bare_mm2']} / {v['thread_bare']['mm']} / {v['stitches']:,}")
        lines.append(f"| {k.split(' @ ')[0]} | " + " | ".join(cells) + " |")
    lines += ["", "### Shapes that lose coverage under `on_nodrop`: new bare mm2 against OFF, by cause",
              "(edge = run narrower than the stroke; erased = strand dropped; ground = gap in the colour beneath;"
              " est = `strand_bare_mm2`, the plan-time prediction)", "",
              "| fixture | shape | ink mm2 | width mm (read / source) | strands / dropped | est mm2 | "
              "edge | erased | ground | new bare | in `on` | in `on_cov` |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in sorted(ok.items()):
        att = r["arms"].get("on_nodrop", {}).get("attribution")
        if not att:
            continue
        on = r["arms"].get("on", {}).get("attribution", {}).get("per_shape", {})
        cv = r["arms"].get("on_cov", {}).get("attribution", {}).get("per_shape", {})
        for c in r["candidates"]:
            a = att["per_shape"].get(c["shape_id"])
            if not a or a["new_bare_mm2"] <= 0 and c["bare_est_mm2"] <= 0.05:
                continue
            lines.append(
                f"| {k.split(' @ ')[0]} | {c['shape_id']} | {c['area_mm2']} | {c['width_mm']} / "
                f"{c['width_source_mm']} | {c['strands']} / {c['dropped']} | {c['bare_est_mm2']} | "
                f"{a['edge_mm2']} | {a['erased_mm2']} | {a['ground_mm2']} | {a['new_bare_mm2']} | "
                f"{on.get(c['shape_id'], {}).get('new_bare_mm2', '-')} | "
                f"{cv.get(c['shape_id'], {}).get('new_bare_mm2', '-')} |")
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
    """OFF | ON | ON + coverage guard on one fixture: the whole logo, plus a
    zoom (30 px/mm) on the triggering shape (the shape the guard hands back
    with the most predicted bare area, or --zoom cx,cy,hw,hh)."""
    from tools.hairline_logo_bill import _panel, _strip, _write_png, _zoom_panel
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cfg_kw = sc.MATRIX[0]
    base = dict(cfg_kw, thread_wt=args.wt)
    result = run_stages(TESTDATA / args.fixture, PipelineConfig(**base))
    labels = ("today (OFF)", "hairline ON", "hairline ON + coverage guard")
    plans = [plan_stitches(result, PipelineConfig(**base)),
             plan_stitches(result, PipelineConfig(**base, hairline=True)),
             plan_stitches(result, PipelineConfig(**base, hairline=True,
                                                  hairline_coverage_guard=True))]
    name = Path(args.fixture).stem
    _write_png(out / f"{name}_coverage_compare.png",
               _strip([_panel(pl, lb, args.wt) for pl, lb in zip(plans, labels)]))
    if args.zoom:
        cx, cy, hw, hh = (float(v) for v in args.zoom.split(","))
    else:
        rows = _load(out)
        r = next(v for k, v in rows.items() if "error" not in v and v["fixture"] == args.fixture)
        on, cov = r["arms"]["on"]["attribution"]["per_shape"], r["arms"]["on_cov"]["attribution"]["per_shape"]
        pick = max(r["candidates"], key=lambda c: on.get(c["shape_id"], {}).get("new_bare_mm2", 0)
                   - cov.get(c["shape_id"], {}).get("new_bare_mm2", 0))
        x0, y0, x1, y1 = pick["bbox_mm"]
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        hw, hh = max(5.0, (x1 - x0) / 2 + 1.5), max(4.0, (y1 - y0) / 2 + 1.5)
        print(f"zoom on {pick['shape_id']} ({pick['area_mm2']} mm2)")
    _write_png(out / f"{name}_coverage_zoom.png", _strip(
        [_zoom_panel(pl, lb, args.wt, cx, cy, hw, hh) for pl, lb in zip(plans, labels)]))
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", default="", help="comma list under testdata/; default the logo set")
    r.add_argument("--arms", default=",".join(ARMS))
    r.add_argument("--wt", type=int, default=40)
    r.add_argument("--force", action="store_true")
    r.add_argument("--no-travel", action="store_true", help="skip the travel-over-bare-fabric instrument")
    r.set_defaults(fn=cmd_run)
    m = sub.add_parser("merge")
    m.add_argument("dirs", nargs="+")
    m.set_defaults(fn=cmd_merge)
    t = sub.add_parser("table")
    t.set_defaults(fn=cmd_table)
    d = sub.add_parser("render")
    d.add_argument("--fixture", required=True)
    d.add_argument("--wt", type=int, default=40)
    d.add_argument("--zoom", default="")
    d.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
