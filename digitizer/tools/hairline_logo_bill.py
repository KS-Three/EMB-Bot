"""Hairline tier: the LOGO BILL — what `cfg.hairline` costs on ordinary art (2026-10-12).

    python -m tools.hairline_logo_bill run    [--fixtures a.png,b.png] [--matrix 0|1|all] [--wt 40]
    python -m tools.hairline_logo_bill table
    python -m tools.hairline_logo_bill render [--top 3]

The hair fixtures (`tools/hairline_renders.py`) are measured. This answers the
question a flip has to answer: on the corpus fixtures that are NOT hair, which
shapes does the hairline tier capture, and what does it do to stitches, trims,
thread and coverage?

`run` takes the fixtures and the config matrix of `tools/corpus_scorecard.py`
(its `FIXTURES` and `MATRIX`, imported, never copied), digitizes stages 0-4
ONCE per (fixture, matrix row) and plans stages 5-7 three times — the three
modes, which differ ONLY in stage 5-7 config, as `hairline_renders` relies on:

- `off`    today: `cfg.hairline` False (the OFF row is the plain pipeline's
           `run_stages` + `plan_stitches`; the test pins its counts)
- `on`     `cfg.hairline` True
- `on_gnd` `cfg.hairline` and `cfg.hairline_over_ground`

Per mode it records stitches, trims, jumps, colour changes, thread length (m),
plan seconds, `CLIP_DROPPED_SLIVER` (count, mm2), preflight's
`ARTWORK_UNCOVERED` (shapes, total mm2), the bare-fabric total (every bare
cell, `hairline_renders.bare_cells`) and whole-design thread coverage. For the
two ON modes it adds the shapes `hairline_candidates` admits (id, ink area,
the width read three ways, run vs ladder branches), which of them stage 7
actually re-sewed (their runs differ from OFF's), and the plan's own
`HAIRLINE_TIER_SEWN` shape / strand / dropped counts.

Every row is merged into `rows.json` keyed by fixture + matrix row, so a long
corpus is run in chunks under any wall-clock limit. Every number is a property
of the FILE, not of a sew-out (ROADMAP gate 1).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, machine, preflight, stitchviz  # noqa: E402
from digitizer_core.adapter import plan_to_design  # noqa: E402
from digitizer_core.pipeline import (  # noqa: E402
    _fill_inside_satin_border, plan_stitches, run_stages)
from digitizer_core.stage6_hairline import hairline_candidates, hairline_runs  # noqa: E402
from digitizer_core.threads import chart_for  # noqa: E402
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER, HAIRLINE_TIER_SEWN  # noqa: E402
from tools import corpus_scorecard as sc  # noqa: E402
from tools.hairline_renders import bare_cells  # noqa: E402

TESTDATA = sc.TESTDATA
OUT_DIR = ROOT.parent / "docs" / "renders" / "claude-hairline-logo-bill"
MODES = {"off": (False, False), "on": (True, False), "on_gnd": (True, True)}
RENDER_PX_PER_MM = 6.0
ZOOM_PX_PER_MM = 30.0


def row_key(fixture: str, cfg_kw: dict) -> str:
    return sc._run_key(fixture, cfg_kw)


def plan_counts(plan) -> dict:
    """Stitch / trim / jump / colour-change counts and thread length of a plan.

    Stitches = needle-down points over every run (`hairline_renders.measure`'s
    definition); thread (m) = their consecutive distances."""
    stitches = trims = jumps = 0
    mm = 0.0
    live = 0
    for b in plan.blocks:
        n = 0
        for r in b.runs:
            pts = r.points
            n += len(pts)
            stitches += len(pts)
            trims += bool(r.trim)
            jumps += bool(r.jump and not r.trim)
            mm += sum(math.dist(a, c) for a, c in zip(pts, pts[1:]))
        live += n > 0
    return {"stitches": stitches, "trims": trims, "jumps": jumps,
            "colour_changes": max(live - 1, 0), "thread_m": round(mm / 1000.0, 3)}


def shape_digests(plan) -> dict[str, str]:
    """md5 of every shape's runs (points + flags): what stage 7 laid for it."""
    h: dict[str, "hashlib._Hash"] = {}
    for b in plan.blocks:
        for r in b.runs:
            m = h.setdefault(r.shape_id, hashlib.md5())
            m.update(json.dumps([[round(x, 4), round(y, 4)] for x, y in r.points]
                                + [r.kind, bool(r.jump), bool(r.trim)]).encode())
    return {k: v.hexdigest() for k, v in h.items()}


def warning_extra(plan, code: str) -> dict | None:
    return next((w for w in plan.warnings if w["code"] == code), None)


def measure_mode(plan, result, p, cfg) -> dict:
    row = plan_counts(plan)
    # Stage 5's clip raises one; under `cfg.hairline` stage 7 may raise a
    # second (`source: hairline_rest`). Sum them, keep the split.
    slivers = [w for w in plan.warnings if w["code"] == CLIP_DROPPED_SLIVER]
    row["clip_dropped_sliver"] = ({
        "count": sum(w.get("count") or 0 for w in slivers),
        "total_mm2": round(sum(w.get("total_mm2") or 0.0 for w in slivers), 3),
        "from_hairline_rest": sum(w.get("count") or 0 for w in slivers
                                  if w.get("source") == "hairline_rest"),
    } if slivers else None)
    findings, _metrics = preflight._uncovered_findings(p, result, plan)
    unc = next((f for f in findings if f["code"] == preflight.ARTWORK_UNCOVERED), None)
    ux = unc["extra"] if unc else {}
    row["artwork_uncovered"] = ({"shapes": ux["count"], "total_mm2": ux["total_mm2"],
                                 "worst_mm2": ux["worst_mm2"],
                                 "ids": [s["shape_id"] for s in ux["shapes"]]} if unc else None)
    bare = bare_cells(plan, result, p)
    row["bare_mm2"] = round(float(bare[0].sum()) * bare[2] ** 2, 2)
    row["coverage"] = round(stitchviz.coverage(plan_to_design(plan, name="bill")), 4)
    w = warning_extra(plan, HAIRLINE_TIER_SEWN)
    row["hairline_sewn"] = ({k: w[k] for k in ("shapes", "strands", "dropped")} if w
                            else {"shapes": 0, "strands": 0, "dropped": 0})
    return row


def candidate_rows(result, cfg, off_digests, on_digests, plan) -> list[dict]:
    """The shapes the gate admits, with the width read three ways. `resewn` is
    True when stage 7 laid different runs for the shape than OFF did."""
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    if cfg.fill_inside_satin_border:
        stitched = _fill_inside_satin_border(stitched, cfg, result.design_class)
    cands = hairline_candidates(stitched, cfg, ink=getattr(result, "ink_source", None))
    chart = chart_for(cfg)
    prof = machine.thread_profile(cfg.thread_wt)
    by_id = {r.shape_id: r for r in stitched}
    out = []
    for sid, m in cands.items():
        r = by_id[sid]
        x0, y0, x1, y1 = r.polygon.bounds
        hair = m.get("hair_edges") or []
        rest = m.get("rest")
        # What the tier does with the shape: strands laid, strands dropped
        # (under the loop floor: ink erased, not re-routed), thread laid.
        runs, rep = hairline_runs(r.polygon, sid, max_width_mm=prof.hairline_max_width_mm,
                                  run_width_mm=prof.hairline_run_width_mm,
                                  stitch_mm=cfg.hairline_stitch_mm, entry=None,
                                  trim_at_mm=3.0, m=m)
        out.append({
            "strands": rep.get("strands", 0),
            "dropped": rep.get("dropped", 0),
            "strand_mm": round(sum(math.dist(a, c) for ru in runs
                                   for a, c in zip(ru.points, ru.points[1:])), 2),
            "shape_id": sid,
            "thread": chart.threads[r.thread_index].name,
            "area_mm2": round(r.polygon.area, 2),
            "bbox_mm": [round(v, 1) for v in (x0, y0, x1, y1)],
            "width_mm": round(m["width_mm"], 3),
            "width_traced_mm": round(m["width_traced_mm"], 3),
            "width_source_mm": (None if m["width_source_mm"] is None
                                else round(m["width_source_mm"], 3)),
            "hair_branches": len(hair),
            "thick_branches": len(m.get("thick_edges") or []),
            "widest_run_branch_mm": round(max((e["w"] for e in hair), default=0.0), 3) or None,
            "rest_mm2": 0.0 if rest is None else round(rest.area, 2),
            "resewn": off_digests.get(sid) != on_digests.get(sid),
        })
    out.sort(key=lambda c: -c["area_mm2"])
    return out


def run_one(fixture: str, cfg_kw: dict, wt: int) -> dict:
    path = TESTDATA / fixture
    base = dict(cfg_kw, thread_wt=wt)
    t0 = time.perf_counter()
    result = run_stages(path, PipelineConfig(**base))
    stage04_s = time.perf_counter() - t0
    p = preflight.prep(path, PipelineConfig(**base), design_class=result.design_class)
    rows: dict = {"fixture": fixture, "matrix": cfg_kw, "thread_wt": wt,
                  "design_class": str(result.design_class), "stage0_4_s": round(stage04_s, 1)}
    off_digests = None
    for mode, (on, gnd) in MODES.items():
        cfg = PipelineConfig(**base, hairline=on, hairline_over_ground=gnd)
        t0 = time.perf_counter()
        plan = plan_stitches(result, cfg)
        elapsed = time.perf_counter() - t0
        row = measure_mode(plan, result, p, cfg)
        row["plan_s"] = round(elapsed, 2)
        digests = shape_digests(plan)
        if mode == "off":
            off_digests = digests
        else:
            row["candidates"] = candidate_rows(result, cfg, off_digests, digests, plan)
            row["candidate_count"] = len(row["candidates"])
            row["candidate_area_mm2"] = round(sum(c["area_mm2"] for c in row["candidates"]), 2)
            row["resewn_count"] = sum(c["resewn"] for c in row["candidates"])
            row["resewn_area_mm2"] = round(sum(c["area_mm2"] for c in row["candidates"]
                                               if c["resewn"]), 2)
        rows[mode] = row
    return rows


def _load(out: Path) -> dict:
    f = out / "rows.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}


def cmd_merge(args) -> int:
    """Fold the `rows.json` of several worker directories into --out's."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = _load(out)
    for d in args.dirs:
        rows.update(_load(Path(d)))
    (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    print(f"{len(rows)} rows")
    return 0


def _matrix(sel: str) -> list[dict]:
    return sc.MATRIX if sel == "all" else [sc.MATRIX[int(sel)]]


def cmd_run(args) -> int:
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    fixtures = args.fixtures.split(",") if args.fixtures else list(sc.FIXTURES)
    rows = _load(out)
    for fx in fixtures:
        for cfg_kw in _matrix(args.matrix):
            key = row_key(fx, cfg_kw)
            if key in rows and "error" not in rows[key] and not args.force:
                print(f"{key}: cached")
                continue
            try:
                rows[key] = run_one(fx, cfg_kw, args.wt)
            except Exception as exc:  # noqa: BLE001 -- one bad fixture must not sink the run
                rows[key] = {"fixture": fx, "matrix": cfg_kw, "error": f"{type(exc).__name__}: {exc}"}
            r = rows[key]
            if "error" in r:
                print(f"{key}: ERROR {r['error']}")
            else:
                print(f"{key}: off {r['off']['stitches']} st | on cand {r['on']['candidate_count']} "
                      f"resewn {r['on']['resewn_count']} dSt {r['on']['stitches'] - r['off']['stitches']:+d} "
                      f"| gnd dSt {r['on_gnd']['stitches'] - r['off']['stitches']:+d}", flush=True)
            (out / "rows.json").write_text(json.dumps(rows, indent=1) + "\n", encoding="utf-8")
    return 0


def _d(a, b, fmt="{:+d}"):
    return fmt.format(b - a)


def change_score(r: dict) -> float:
    """How much hairline moved a fixture: the larger of the stitch and the
    thread change, relative to OFF, over the two ON modes."""
    off = r["off"]
    best = 0.0
    for m in ("on", "on_gnd"):
        o = r[m]
        best = max(best, abs(o["stitches"] - off["stitches"]) / max(off["stitches"], 1),
                   abs(o["thread_m"] - off["thread_m"]) / max(off["thread_m"], 1e-9))
    return best


def markdown(rows: dict) -> str:
    ok = {k: r for k, r in rows.items() if "error" not in r}
    lines = ["### Per fixture x matrix row (deltas vs OFF)", "",
             "| fixture @ matrix | class | OFF st / trims / m | cand: shapes (mm2) / resewn (mm2) | "
             "sewn shapes / strands / dropped | ON dSt / dTrim / dColour / dm | "
             "ON+gnd dSt / dTrim / dm | CLIP_DROPPED_SLIVER off>on>gnd | ARTWORK_UNCOVERED mm2 off>on>gnd | "
             "bare mm2 off>on>gnd | plan s off/on/gnd |",
             "|---|---|---|---|---|---|---|---|---|---|---|"]

    def unc(m):
        return "-" if m["artwork_uncovered"] is None else m["artwork_uncovered"]["total_mm2"]

    def sl(m):
        return "-" if m["clip_dropped_sliver"] is None else m["clip_dropped_sliver"]["count"]
    for k, r in sorted(ok.items(), key=lambda kv: -change_score(kv[1])):
        o, n, g = r["off"], r["on"], r["on_gnd"]
        lines.append(
            f"| {k} | {r['design_class'].split('.')[-1]} | {o['stitches']:,} / {o['trims']} / {o['thread_m']} | "
            f"{n['candidate_count']} ({n['candidate_area_mm2']}) / {n['resewn_count']} ({n['resewn_area_mm2']}) | "
            f"{n['hairline_sewn']['shapes']} / {n['hairline_sewn']['strands']} / {n['hairline_sewn']['dropped']} | "
            f"{_d(o['stitches'], n['stitches'])} / {_d(o['trims'], n['trims'])} / "
            f"{_d(o['colour_changes'], n['colour_changes'])} / {_d(o['thread_m'], n['thread_m'], '{:+.3f}')} | "
            f"{_d(o['stitches'], g['stitches'])} / {_d(o['trims'], g['trims'])} / "
            f"{_d(o['thread_m'], g['thread_m'], '{:+.3f}')} | "
            f"{sl(o)}>{sl(n)}>{sl(g)} | {unc(o)}>{unc(n)}>{unc(g)} | "
            f"{o['bare_mm2']}>{n['bare_mm2']}>{g['bare_mm2']} | {o['plan_s']}/{n['plan_s']}/{g['plan_s']} |")
    lines += ["", "### Shapes the gate admits (ON mode), widest first", "",
              "| fixture @ matrix | shape | thread | ink mm2 | width mm (read / traced / source) | "
              "run/ladder branches | rest mm2 | strands / dropped | re-sewn | where (bbox mm) |",
              "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in sorted(ok.items()):
        for c in sorted(r["on"]["candidates"], key=lambda c: -c["width_mm"]):
            lines.append(
                f"| {k} | {c['shape_id']} | {c['thread']} | {c['area_mm2']} | {c['width_mm']} / "
                f"{c['width_traced_mm']} / {c['width_source_mm']} | "
                f"{c['hair_branches']}/{c['thick_branches']} | {c['rest_mm2']} | "
                f"{c.get('strands', '-')} / {c.get('dropped', '-')} | "
                f"{'yes' if c['resewn'] else 'no'} | {c['bbox_mm']} |")
    bad = {k: r["error"] for k, r in rows.items() if "error" in r}
    if bad:
        lines += ["", "### Errors", ""] + [f"- {k}: {e}" for k, e in bad.items()]
    return "\n".join(lines) + "\n"


def cmd_table(args) -> int:
    out = Path(args.out)
    rows = _load(out)
    (out / "table.md").write_text(markdown(rows), encoding="utf-8")
    print(markdown(rows))
    return 0


def _panel(plan, label: str, wt: int) -> np.ndarray:
    from digitizer_core import machine
    img = stitchviz.render_design(plan_to_design(plan, name=label), px_per_mm=RENDER_PX_PER_MM,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    band = np.full((30, img.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([band, img])


def cmd_render(args) -> int:
    out = Path(args.out)
    rows = {k: r for k, r in _load(out).items() if "error" not in r and r["matrix"] == sc.MATRIX[0]}
    top = sorted(rows.items(), key=lambda kv: -change_score(kv[1]))[:args.top]
    for key, r in top:
        cfg_kw, wt = r["matrix"], r["thread_wt"]
        base = dict(cfg_kw, thread_wt=wt)
        result = run_stages(TESTDATA / r["fixture"], PipelineConfig(**base))
        panels, plans = [], []
        for mode, label in zip(MODES, LABELS):
            on, gnd = MODES[mode]
            plan = plan_stitches(result, PipelineConfig(**base, hairline=on, hairline_over_ground=gnd))
            panels.append(_panel(plan, label, wt))
            plans.append(plan)
        name = Path(r["fixture"]).stem
        _write_png(out / f"{name}_compare.png", _strip(panels))
        # Zoom: the widest-area re-sewn candidate, where the detail is under
        # 1 mm. Same fixture, same scale, the three arms side by side.
        pick = [c for c in r["on"]["candidates"] if c["resewn"]]
        if pick:
            c = max(pick, key=lambda c: c["area_mm2"])
            x0, y0, x1, y1 = c["bbox_mm"]
            cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
            hw = max(5.0, (x1 - x0) / 2 + 1.5)
            hh = max(4.0, (y1 - y0) / 2 + 1.5)
            crops = []
            for plan, label in zip(plans, LABELS):
                crops.append(_zoom_panel(plan, label, wt, cx, cy, hw, hh))
            _write_png(out / f"{name}_zoom.png", _strip(crops))
            print(f"zoom on {c['shape_id']} ({c['area_mm2']} mm2, width {c['width_mm']} mm)")
    return 0


LABELS = ("today (OFF)", "hairline ON", "hairline ON + over_ground")


def _strip(panels: list) -> np.ndarray:
    h = max(p.shape[0] for p in panels)
    w = max(p.shape[1] for p in panels)
    panels = [cv2.copyMakeBorder(p, 0, h - p.shape[0], 0, w - p.shape[1], cv2.BORDER_CONSTANT,
                                 value=(255, 255, 255)) for p in panels]
    sep = np.full((h, 4, 3), 200, np.uint8)
    return np.hstack([panels[0], sep, panels[1], sep, panels[2]])


def _write_png(dest: Path, img: np.ndarray, limit: int = 290_000) -> None:
    """PNG under `limit` bytes: shrink by 15 % steps until it fits."""
    while True:
        ok, buf = cv2.imencode(".png", img, [cv2.IMWRITE_PNG_COMPRESSION, 9])
        if len(buf) < limit or min(img.shape[:2]) < 120:
            break
        img = cv2.resize(img, None, fx=0.85, fy=0.85, interpolation=cv2.INTER_AREA)
    dest.write_bytes(buf.tobytes())
    print(f"{dest} {len(buf) / 1024:.0f} KB {img.shape[1]}x{img.shape[0]}")


def _zoom_panel(plan, label: str, wt: int, cx: float, cy: float, hw: float, hh: float) -> np.ndarray:
    """The design rendered at `ZOOM_PX_PER_MM`, cropped to a mm box around
    (cx, cy) in plan mm (the adapter's frame: design unit = mm x 10, y up)."""
    from digitizer_core import machine
    design = plan_to_design(plan, name=label)
    img = stitchviz.render_design(design, px_per_mm=ZOOM_PX_PER_MM,
                                  thread_mm=machine.thread_profile(wt).width_mm)
    (_h, _w), to_px = stitchviz._frame(design["stitches"], ZOOM_PX_PER_MM, 2.0)
    u = stitchviz.UNITS_PER_MM
    ax, ay = to_px({"x": (cx - hw) * u, "y": -(cy - hh) * u})   # left, bottom of the box
    bx, by = to_px({"x": (cx + hw) * u, "y": -(cy + hh) * u})   # right, top
    top, bot = sorted((ay, by))
    crop = img[max(top, 0):max(bot, 1), max(ax, 0):max(bx, 1)]
    out = np.full((int(2 * hh * ZOOM_PX_PER_MM), int(2 * hw * ZOOM_PX_PER_MM), 3), 255, np.uint8)
    out[:crop.shape[0], :crop.shape[1]] = crop[:out.shape[0], :out.shape[1]]
    band = np.full((30, out.shape[1], 3), 255, np.uint8)
    cv2.putText(band, label, (6, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (30, 30, 30), 1, cv2.LINE_AA)
    return np.vstack([band, out])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", default=str(OUT_DIR))
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--fixtures", default="", help="comma list of scorecard fixture names; default all")
    r.add_argument("--matrix", default="0", help="0 | 1 | all (scorecard MATRIX rows)")
    r.add_argument("--wt", type=int, default=40)
    r.add_argument("--force", action="store_true")
    r.set_defaults(fn=cmd_run)
    m = sub.add_parser("merge")
    m.add_argument("dirs", nargs="+")
    m.set_defaults(fn=cmd_merge)
    t = sub.add_parser("table")
    t.set_defaults(fn=cmd_table)
    d = sub.add_parser("render")
    d.add_argument("--top", type=int, default=3)
    d.set_defaults(fn=cmd_render)
    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
