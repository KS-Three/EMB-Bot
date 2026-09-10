"""A professionally sewn reference file in OUR frame: coverage layers and
thread inside our own shapes and junction blobs, ours beside the pro's —
the calibration item 5's PR 3 rested on (2026-09-09).

Every read of "this junction looks over-sewn" is a layer count, and a layer
count means nothing until the pro's file has been read at the same spot.
This aligns the reference's stitches to our plan by the two designs' whole
stitch bounding boxes (the same artwork at the same aspect; the pro's
Becker is 95.7 x 58.3 mm against our 99.9 x 62.6), rasterizes both through
`preflight._coverage_map` at a quarter millimetre, and reports layers
(p50 / p95 / p99 / max) for the whole design, for each of our satin shapes,
and — with `--blobs` — inside each junction blob `tools/junction_blobs.py`
builds, plus penetrations and thread length inside a horizontal band.

The alignment is a similarity from box to box; a 1-2 mm residual is normal
(the pro's outline is not ours), so read the per-shape and band figures as
the finding and the per-blob ones as indicative.

Usage:
  python tools/pro_layers.py --ref testdata/reference/becker_hat_polo_large_beckers_logolc.dst \\
                             becker [--width 100] [--flag NAME[=VALUE] ...] [--blobs] [--band y0 y1]
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig, digitize                 # noqa: E402
from digitizer_core import stage6_satin as s6                      # noqa: E402
from digitizer_core import stage7_sequence as s7                   # noqa: E402
from digitizer_core.preflight import _coverage_map                 # noqa: E402
from digitizer_core.stitches import StitchRun, strip_ties          # noqa: E402
from curve_tiers import CASES                                       # noqa: E402
from satin_columns import passes_from_file                          # noqa: E402
from thin_strokes import parse_flags                                # noqa: E402
import junction_blobs as jb                                         # noqa: E402

ROOT = HERE.parent
CELL_MM = 0.25


def _stats(grid) -> str:
    a = grid[grid > 0]
    if not len(a):
        return "no thread"
    return (f"p50 {np.percentile(a, 50):.2f}  p95 {np.percentile(a, 95):.2f}  "
            f"p99 {np.percentile(a, 99):.2f}  max {a.max():.2f}")


def _inside(poly, grid, origin) -> str:
    c = jb.coverage_in(poly, grid, origin, CELL_MM)
    return f"mean {c['mean']:.2f}  p95 {c['p95']:.2f}  max {c['max']:.2f}  bare {c['bare']:.2f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("case")
    ap.add_argument("--ref", required=True, help="the reference stitch file (DST/PES)")
    ap.add_argument("--width", type=float, default=None)
    ap.add_argument("--flag", action="append", default=[])
    ap.add_argument("--blobs", action="store_true", help="also read inside each junction blob")
    ap.add_argument("--band", type=float, nargs=2, default=None,
                    help="a horizontal band of OUR plan (y0 y1, mm) to count penetrations and thread in")
    a = ap.parse_args(argv)
    rel, kw = CASES[a.case]
    cfg = {k: v for k, v in kw.items() if not (a.width is not None and k == "target_width_mm")}
    if a.width is not None:
        cfg["target_width_mm"] = a.width
    cfg.update(parse_flags(a.flag))

    seen: list[tuple[str, object]] = []
    real = s6.satin_shape

    def spy(poly, shape_id, **kwargs):
        seen.append((shape_id, poly))
        return real(poly, shape_id, **kwargs)

    s7.satin_shape = spy
    try:
        _result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
    finally:
        s7.satin_shape = real
    ours = [r for _b, r in plan.iter_runs()]
    op = np.array([q for r in ours for q in strip_ties(r.points)])
    ox0, ox1, oy0, oy1 = op[:, 0].min(), op[:, 0].max(), op[:, 1].min(), op[:, 1].max()

    ref = Path(a.ref) if Path(a.ref).is_absolute() else ROOT / a.ref
    passes = passes_from_file(ref)
    pp = np.array([q for ps in passes for q in ps])
    px0, px1, py0, py1 = pp[:, 0].min(), pp[:, 0].max(), pp[:, 1].min(), pp[:, 1].max()
    sx, sy = (ox1 - ox0) / (px1 - px0), (oy1 - oy0) / (py1 - py0)

    def to_ours(q):                       # the reference is y-up, the plan y-down
        return (ox0 + (q[0] - px0) * sx, oy1 - (q[1] - py0) * sy)

    pro = [StitchRun(points=[to_ours(q) for q in ps], kind="satin", shape_id="ref")
           for ps in passes if len(ps) >= 2]
    g_our = _coverage_map(jb._Runs(ours), cell_mm=CELL_MM)
    g_pro = _coverage_map(jb._Runs(pro), cell_mm=CELL_MM)
    print(f"{a.case} @ {cfg.get('target_width_mm')} mm {parse_flags(a.flag) or ''}: ours {ox1 - ox0:.1f} x {oy1 - oy0:.1f} mm, "
          f"{ref.name} {px1 - px0:.1f} x {py1 - py0:.1f}; scale x {sx:.3f} y {sy:.3f}")
    print(f"whole design layers   ours: {_stats(g_our[0])}\n                      pro:  {_stats(g_pro[0])}")
    for sid, poly in sorted(seen, key=lambda kv: kv[1].bounds[0]):
        print(f"  {sid} x {poly.bounds[0]:.1f}..{poly.bounds[2]:.1f}:  ours {_inside(poly, *g_our)}  |  pro {_inside(poly, *g_pro)}")
        if not a.blobs:
            continue
        g = jb.skeleton_graph(poly)
        if g is None:
            continue
        edges, half_mm, field, scale, to_mm, dt_mm, _skel, _dist = g
        decisions, _merged = jb.merge_decisions(edges, dt_mm, half_mm, scale)
        for node, arms in decisions.items():
            blob, _exits, _halves = jb.blob_of(node, [(i, s) for i, s, _d in arms], edges, field,
                                               half_mm, to_mm, dt_mm, poly)
            if blob.is_empty:
                continue
            print(f"      blob at {tuple(round(v, 1) for v in to_mm(node))} arms {len(arms)} area {blob.area:.0f}:  "
                  f"ours {_inside(blob, *g_our)}  |  pro {_inside(blob, *g_pro)}")
    if a.band:
        y0, y1 = a.band
        o_runs = [strip_ties(r.points) for r in ours
                  if r.points and y0 - 0.3 <= np.mean([q[1] for q in r.points]) <= y1 + 0.3]
        p_runs = [[q for q in r.points if y0 - 0.5 <= q[1] <= y1 + 0.5] for r in pro]
        p_runs = [r for r in p_runs if len(r) >= 2]
        o_pts = sum(len(r) for r in o_runs)
        o_len = sum(sum(math.dist(p, q) for p, q in zip(r, r[1:])) for r in o_runs)
        p_pts = sum(len(r) for r in p_runs)
        p_len = sum(sum(math.dist(p, q) for p, q in zip(r, r[1:])) for r in p_runs)
        print(f"band y {y0}..{y1}:  ours {o_pts} penetrations, {o_len:.0f} mm thread  |  pro {p_pts}, {p_len:.0f} mm (in our frame)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
