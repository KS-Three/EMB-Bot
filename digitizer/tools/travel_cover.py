#!/usr/bin/env python
"""Is every travel leg under thread sewn LATER? The instrument for the
Euler-walk stroke order (lettering construction plan step 2, 2026-09-19)
and for DOCTRINE gate 3's letter: a green suite has hidden needle-down thread
on bare fabric here before, and preflight's two instruments cannot see this
feature's thread -- `ARTWORK_UNCOVERED` measures artwork with no thread,
`LINK_UNCOVERED` classifies a shape's own TRAVEL run as internal routing.

For each TRAVEL run in a plan, in sew order, the runs sewn AFTER it are
rasterised with `preflight._coverage_map`'s own ribbon rule (same thread
width, same cell, same sampling; ties stripped) and the leg is sampled every
half millimetre against that map. A sample under `MIN_UNITS` of later thread
is EXPOSED: the needle went down there and nothing sewn afterwards covers
it. Reported per fixture and mode: travel legs, travel mm, exposed mm (and
the share), the worst leg's exposed mm, plus preflight's `uncovered_total_mm2`
and `link_uncovered_mm` so the two instruments read side by side.

    .venv/bin/python tools/travel_cover.py [case ...] [--width MM] [--order nearest|euler|both]

Cases default to the nine `REAL_ART` logos (`tools.thin_strokes.corpus_cases`)
at 80 mm; `--width corpus` uses each case's corpus width. A path under
`testdata/` or an absolute path is a case too.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

import numpy as np  # noqa: E402

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches  # noqa: E402
from digitizer_core.preflight import _column_weight, run_preflight  # noqa: E402

# One full ribbon layer of a run is 0.40 units over a 1.0 mm cell
# (`_coverage_map`'s docstring); half of that is "some thread lies here".
MIN_UNITS = 0.2
SAMPLE_MM = 0.5


def _grid_frame(runs):
    xs, ys = [], []
    for run in runs:
        pts = stitches.strip_ties(run.points)
        for x, y in pts:
            xs.append(x)
            ys.append(y)
    if not xs:
        return None
    w = machine.COVERAGE_THREAD_W_MM
    cell = machine.COVERAGE_CELL_MM
    x0, y0 = min(xs) - w, min(ys) - w
    nx = int(math.ceil((max(xs) + w - x0) / cell)) + 1
    ny = int(math.ceil((max(ys) + w - y0) / cell)) + 1
    return x0, y0, nx, ny, cell


def _add_ribbon(grid, frame, pts):
    """`_coverage_map`'s sampling of one run's ribbon, added into `grid`."""
    x0, y0, nx, ny, cell = frame
    a = np.asarray(pts, np.float64)
    if len(a) < 2:
        return
    seg = np.stack([a[:-1], a[1:]], axis=1)
    d = seg[:, 1] - seg[:, 0]
    ln = np.hypot(d[:, 0], d[:, 1])
    keep = ln > 1e-9
    seg, d, ln = seg[keep], d[keep], ln[keep]
    if not len(seg):
        return
    wt = _column_weight(pts)
    thread_w = machine.COVERAGE_THREAD_W_MM
    n = np.maximum(1, np.ceil(ln / machine.COVERAGE_SUBSAMPLE_MM).astype(np.int64))
    idx = np.repeat(np.arange(len(seg)), n)
    starts = np.concatenate([[0], np.cumsum(n)[:-1]])
    t = (np.arange(int(n.sum())) - np.repeat(starts, n) + 0.5) / n[idx]
    px = seg[idx, 0, 0] + d[idx, 0] * t
    py = seg[idx, 0, 1] + d[idx, 1] * t
    ux, uy = -d[idx, 1] / ln[idx], d[idx, 0] / ln[idx]
    across = max(1, int(machine.COVERAGE_ACROSS_SAMPLES))
    area = (ln[idx] / n[idx]) * thread_w * wt / across
    flat = grid.reshape(-1)
    for k in range(across):
        off = ((k + 0.5) / across - 0.5) * thread_w
        cx = ((px + ux * off - x0) / cell).astype(np.int64)
        cy = ((py + uy * off - y0) / cell).astype(np.int64)
        np.clip(cx, 0, nx - 1, out=cx)
        np.clip(cy, 0, ny - 1, out=cy)
        flat += np.bincount(cy * nx + cx, weights=area, minlength=ny * nx) / (cell * cell)


def _samples(pts):
    out = []
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        L = math.hypot(xb - xa, yb - ya)
        n = max(1, int(math.ceil(L / SAMPLE_MM)))
        for i in range(n):
            t = (i + 0.5) / n
            out.append((xa + (xb - xa) * t, ya + (yb - ya) * t, L / n))
    return out


def travel_exposure(plan) -> dict:
    """-> {legs, travel_mm, exposed_mm, worst_leg_mm} over the plan's TRAVEL
    runs, each read against the thread sewn after it."""
    runs = [run for _b, run in plan.iter_runs()]
    frame = _grid_frame(runs)
    if frame is None:
        return dict(legs=0, travel_mm=0.0, exposed_mm=0.0, worst_leg_mm=0.0)
    x0, y0, nx, ny, cell = frame
    after = np.zeros((ny, nx), np.float64)
    legs = 0
    travel_mm = exposed_mm = worst = 0.0
    for run in reversed(runs):
        pts = stitches.strip_ties(run.points)
        if run.kind == stitches.TRAVEL and len(pts) >= 2:
            legs += 1
            leg_exposed = 0.0
            for x, y, L in _samples(pts):
                cx = min(nx - 1, max(0, int((x - x0) / cell)))
                cy = min(ny - 1, max(0, int((y - y0) / cell)))
                travel_mm += L
                if after[cy, cx] < MIN_UNITS:
                    leg_exposed += L
            exposed_mm += leg_exposed
            worst = max(worst, leg_exposed)
        _add_ribbon(after, frame, pts)
    return dict(legs=legs, travel_mm=travel_mm, exposed_mm=exposed_mm, worst_leg_mm=worst)


def measure(path: Path, width_mm: float, garment: str, order: str) -> dict:
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id=garment,
                         max_colors=6, satin_stroke_order=order)
    gen = build_generation(str(path), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    pf = run_preflight(result, plan, cfg, image=str(path))
    out = travel_exposure(plan)
    out.update(stitches=plan.stats.stitch_count, trims=plan.stats.trims,
               uncovered_mm2=pf["metrics"].get("uncovered_total_mm2"),
               link_uncovered_mm=pf["metrics"].get("link_uncovered_mm"),
               findings=sorted({f["code"] for f in pf["findings"]}))
    return out


def main(argv: list[str]) -> None:
    from thin_strokes import corpus_cases  # noqa: E402  (tools/ on sys.path)
    width_arg = None
    orders = ["nearest", "euler"]
    names: list[str] = []
    it = iter(argv)
    for a in it:
        if a == "--width":
            width_arg = next(it)
        elif a == "--order":
            o = next(it)
            orders = ["nearest", "euler"] if o == "both" else [o]
        else:
            names.append(a)
    cases = []
    for name, path, width, garment in corpus_cases():
        if not names or name in names:
            cases.append((name, Path(path), width, garment))
    for n in names:
        if not any(c[0] == n for c in cases):
            p = Path(n) if Path(n).is_absolute() else ROOT / "testdata" / n
            cases.append((Path(n).stem, p, 80.0, "left_chest"))
    for name, path, cw, garment in cases:
        width = cw if width_arg == "corpus" else float(width_arg or 80.0)
        rows = {o: measure(path, width, garment, o) for o in orders}
        line = f"## {name} @ {width:g} mm"
        for o, r in rows.items():
            share = (r["exposed_mm"] / r["travel_mm"] * 100.0) if r["travel_mm"] else 0.0
            line += (f"\n  {o:8s} st={r['stitches']:6d} trims={r['trims']:4d} legs={r['legs']:4d} "
                     f"travel={r['travel_mm']:7.1f} mm exposed={r['exposed_mm']:6.1f} mm ({share:4.1f}%) "
                     f"worst leg={r['worst_leg_mm']:5.1f} mm | uncovered={r['uncovered_mm2']} "
                     f"link_uncovered={r['link_uncovered_mm']} findings={r['findings']}")
        print(line, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:])
