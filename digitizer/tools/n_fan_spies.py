#!/usr/bin/env python
"""The spies that found defect 59's mechanism, committed (the repo's rule:
commit the probe, even an ugly one). One letter of one logo, priors OFF and
ON, three readings taken from INSIDE `plan_stitches` by monkeypatching one
`stage6_satin` function at a time:

  --runs   every satin run of the letter: crosses, over-long crosses (> 1.6 x
           (W + 2 x 0.3 mm pull), W = 2 area / perimeter), the first and last
           cross midpoints and the angle rotation -- which run carries the fan;
  --tips   `_is_tip_end` at every junction end inside the letter: the end's
           tangent, the reach (1.6 sewn half-widths) and where the ray hits
           the boundary -- which ends are called tapered tips;
  --ends   `_corner_forks` (which skeleton edges are forks) and `_extend_to_cap`
           (which ends run out to the edge, from where, how far).

Becker's N at 100 mm, 2026-10-07: the trace's five junction ends read as
meetings; the refit's read 3 tips at 4.56 / 4.79 / 4.81 mm against a 4.84 mm
reach, and those three are the three 4.6-4.8 mm extensions through the
neighbouring stroke whose crosses fan. `docs/n-fan-2026-10-07.md`.

    .venv/Scripts/python tools/n_fan_spies.py [--case becker] [--width 100] [--letter 4]
                                              [--runs] [--tips] [--ends] [--arms off,on]

`--letter` is the index of the letter by x among the text-tagged shapes
14-19 mm tall at that width (Becker's MARINE: M A R I N E -> the N is 4).
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                      # noqa: E402
from digitizer_core import stage6_satin as s6                  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from digitizer_core.stage6_satin import strip_splits           # noqa: E402
from digitizer_core.stitches import strip_ties                 # noqa: E402
from tools.thin_strokes import corpus_cases                    # noqa: E402

PULL = 0.3
FAN_LEN = 1.6
ARMS = {"off": {"letterform_priors_k": None}, "on": {}}


def pick_letter(res, index: int, lo: float = 14.0, hi: float = 19.0):
    letters = sorted([r for r in res.regions if r.meta.get("text_candidate")
                      and lo < (r.polygon.bounds[3] - r.polygon.bounds[1]) < hi],
                     key=lambda r: r.polygon.centroid.x)
    if index >= len(letters):
        raise SystemExit(f"only {len(letters)} tagged letters {lo}-{hi} mm tall; --letter {index} is out of range")
    return letters[index]


def runs_report(plan, region) -> None:
    W = 2 * region.polygon.area / region.polygon.length
    bar = FAN_LEN * (W + 2 * PULL)
    tot = long = 0
    print(f"  W {W:.2f} mm, over-long bar {bar:.2f} mm, verts {len(region.polygon.exterior.coords) - 1}")
    for _b, run in plan.iter_runs():
        if run.shape_id != region.shape_id or run.kind != "satin":
            continue
        pts = np.asarray(strip_splits(strip_ties(list(run.points))), float)
        cr = [(pts[j], pts[j + 1]) for j in range(0, len(pts) - 1, 2)]
        if len(cr) < 2:
            continue
        L = np.array([math.dist(a, b) for a, b in cr])
        ang = np.array([math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180 for a, b in cr])
        mids = np.array([(a + b) / 2 for a, b in cr])
        longi = np.where(L > bar)[0]
        tot += len(cr)
        long += len(longi)
        where = (f" | over-long at x {mids[longi, 0].min():.1f}-{mids[longi, 0].max():.1f} "
                 f"y {mids[longi, 1].min():.1f}-{mids[longi, 1].max():.1f}, angles "
                 f"{ang[longi].min():.0f}-{ang[longi].max():.0f}" if len(longi) else "")
        print(f"  run: crosses {len(cr):3} over-long {len(longi):3} max {L.max() / W:.2f} W "
              f"from ({mids[0][0]:.1f}, {mids[0][1]:.1f}) to ({mids[-1][0]:.1f}, {mids[-1][1]:.1f}) "
              f"angles {ang[0]:.0f}/{ang[-1]:.0f}{where}")
    print(f"  total crosses {tot}, over-long {long} ({long / max(tot, 1):.0%})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--case", default="becker")
    ap.add_argument("--width", type=float, default=None, help="mm; default the corpus's")
    ap.add_argument("--letter", type=int, default=4)
    ap.add_argument("--arms", default="off,on")
    ap.add_argument("--runs", action="store_true")
    ap.add_argument("--tips", action="store_true")
    ap.add_argument("--ends", action="store_true")
    a = ap.parse_args(argv)
    if not (a.runs or a.tips or a.ends):
        a.runs = a.tips = a.ends = True
    case = {c[0]: c for c in corpus_cases()}[a.case]
    width = a.width or case[2]
    for arm in a.arms.split(","):
        cfg = PipelineConfig(target_width_mm=width, garment_id=case[3], max_colors=6, **ARMS[arm])
        res = run_stages(case[1], cfg)
        letter = pick_letter(res, a.letter)
        box = letter.polygon.bounds
        inside = lambda p: box[0] - 1 <= p[0] <= box[2] + 1 and box[1] - 1 <= p[1] <= box[3] + 1  # noqa: E731
        log: list[str] = []
        patched = {}
        if a.tips:
            orig_tip = s6._is_tip_end

            def tip_spy(spine, poly, half_sewn, at_start):
                r = orig_tip(spine, poly, half_sewn, at_start)
                pts = list(reversed(spine)) if at_start else list(spine)
                tip, prev = pts[-1], pts[-2]
                if inside(tip):
                    d = math.dist(prev, tip)
                    ux, uy = (tip[0] - prev[0]) / d, (tip[1] - prev[1]) / d
                    reach = half_sewn * s6._TIP_REACH_HALVES
                    hit = LineString([tip, (tip[0] + ux * reach, tip[1] + uy * reach)]).intersection(poly.boundary)
                    hd = None if hit.is_empty else Point(tip).distance(hit)
                    log.append(f"  tip? end ({tip[0]:.1f}, {tip[1]:.1f}) tangent {math.degrees(math.atan2(uy, ux)):.0f} deg "
                               f"reach {reach:.2f} boundary at {'none' if hd is None else f'{hd:.2f}'} -> "
                               f"{'TIP' if r else 'meeting'}")
                return r
            patched["_is_tip_end"] = tip_spy
        if a.ends:
            orig_forks, orig_ext = s6._corner_forks, s6._extend_to_cap

            def forks_spy(edges, dt_mm, half_mm, scale):
                out = orig_forks(edges, dt_mm, half_mm, scale)
                for i, e in enumerate(edges):
                    pts = list(e["pts"])
                    if len(pts) < 2:
                        continue
                    length = sum(math.dist(p, q) for p, q in zip(pts, pts[1:])) / scale
                    log.append(f"  skeleton edge {i}/{len(edges)}: {length:.2f} mm, dt {dt_mm(pts[0]):.2f}->{dt_mm(pts[-1]):.2f}, "
                               f"free {e['free_start']}/{e['free_end']}{' FORK' if i in out else ''}")
                return out

            def ext_spy(spine, poly, half_mm, at_start, corner=False):
                res_ = orig_ext(spine, poly, half_mm, at_start, corner)
                tip = spine[0] if at_start else spine[-1]
                new = res_[0] if at_start else res_[-1]
                if inside(tip) and math.dist(tip, new) > 0.05:
                    log.append(f"  extend ({tip[0]:.1f}, {tip[1]:.1f}) -> ({new[0]:.1f}, {new[1]:.1f}) {math.dist(tip, new):.2f} mm"
                               f"{' (corner)' if corner else ''}")
                return res_
            patched["_corner_forks"] = forks_spy
            patched["_extend_to_cap"] = ext_spy
        saved = {k: getattr(s6, k) for k in patched}
        for k, v in patched.items():
            setattr(s6, k, v)
        try:
            if a.ends:
                res.regions = [letter]          # the fork log is the letter's alone
            plan = plan_stitches(res, cfg)
        finally:
            for k, v in saved.items():
                setattr(s6, k, v)
        print(f"=== {a.case} {width:g} mm, priors {arm}: letter {letter.shape_id} "
              f"({letter.meta.get('ocr_char')}) {letter.meta.get('letterform_prior', '-')}")
        for line in log:
            print(line)
        if a.runs:
            runs_report(plan, letter)
    return 0


if __name__ == "__main__":
    sys.exit(main())
