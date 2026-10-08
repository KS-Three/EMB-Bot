#!/usr/bin/env python
"""Tip-corner census: for every junction end `_is_tip_end` calls a TIP, the
interior angle of the outline where its ray lands -- the reading
`cfg.satin_tip_corner_gate` gates on (MASTER_SCOPE defect 59, 2026-10-08).

Under 180 deg the outline closes round the end (a taper's apex: the drone's
71-148); 180 is a straight wall -- the far edge of a stroke the ray drove
through (Becker's N, all three of its tips); over 180 a concave notch between
two strokes (the M, 278-297). Each row also carries whether the gate would
keep it as a tip (angle <= `_TIP_CORNER_MAX_DEG`).

    .venv/Scripts/python tools/tip_corner_census.py [case ...] [--priors-off]

Read from inside `plan_stitches` by monkeypatching `stage6_satin._is_tip_end`,
the way `tools/n_fan_spies.py` reads the tip verdicts. Write-up:
`docs/n-fan-cure-2026-10-08.md`.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

from shapely.geometry import LineString, Point

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))

from digitizer_core import PipelineConfig                      # noqa: E402
from digitizer_core import stage6_satin as s6                  # noqa: E402
from digitizer_core.pipeline import plan_stitches, run_stages  # noqa: E402
from tools.thin_strokes import corpus_cases                    # noqa: E402

DEFAULT = ["becker", "enthusiast", "drone", "fremont", "gaulke"]


def angle_at_hit(spine, poly, half_sewn: float, at_start: bool) -> float | None:
    """The outline's interior angle (ink side) at the ray's nearest hit, over
    one sewn half-width of arc either side -- `_tip_lands_on_corner`'s reading,
    returned instead of compared."""
    pts = list(reversed(spine)) if at_start else list(spine)
    tip, prev = pts[-1], pts[-2]
    d = math.dist(prev, tip)
    if d < 1e-9:
        return None
    ux, uy = (tip[0] - prev[0]) / d, (tip[1] - prev[1]) / d
    reach = half_sewn * s6._TIP_REACH_HALVES
    ray = LineString([tip, (tip[0] + ux * reach, tip[1] + uy * reach)])
    best = None
    for ring in [poly.exterior, *poly.interiors]:
        hit = ray.intersection(ring)
        for g in ([] if hit.is_empty else getattr(hit, "geoms", [hit])):
            for c in g.coords:
                dist = Point(tip).distance(Point(c))
                if best is None or dist < best[0]:
                    best = (dist, ring, Point(c))
    if best is None:
        return None
    _d, ring, h = best
    at, L = ring.project(h), ring.length
    a, b, hp = ring.interpolate((at - half_sewn) % L), ring.interpolate((at + half_sewn) % L), ring.interpolate(at)
    v1, v2 = (a.x - hp.x, a.y - hp.y), (b.x - hp.x, b.y - hp.y)
    n1, n2 = math.hypot(*v1), math.hypot(*v2)
    if n1 < 1e-9 or n2 < 1e-9:
        return None
    ang = math.degrees(math.acos(max(-1.0, min(1.0, (v1[0] * v2[0] + v1[1] * v2[1]) / (n1 * n2)))))
    return ang if poly.covers(Point((a.x + b.x) / 2, (a.y + b.y) / 2)) else 360.0 - ang


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("cases", nargs="*")
    ap.add_argument("--priors-off", action="store_true", help="letterform_priors_k=None")
    a = ap.parse_args(argv)
    cases = {c[0]: c for c in corpus_cases()}
    extra = {"letterform_priors_k": None} if a.priors_off else {}
    orig = s6._is_tip_end
    for name in a.cases or DEFAULT:
        _n, path, width, garment = cases[name]
        cfg = PipelineConfig(target_width_mm=width, garment_id=garment, max_colors=6, **extra)
        res = run_stages(path, cfg)
        rows = []

        def spy(spine, poly, half_sewn, at_start):
            r = orig(spine, poly, half_sewn, at_start)
            if r:
                end = spine[0] if at_start else spine[-1]
                rows.append((angle_at_hit(spine, poly, half_sewn, at_start), end))
            return r
        s6._is_tip_end = spy
        try:
            plan_stitches(res, cfg)
        finally:
            s6._is_tip_end = orig
        kept = sum(1 for ang, _e in rows if ang is not None and ang <= s6._TIP_CORNER_MAX_DEG)
        print(f"=== {name} {width:g} mm{' priors off' if a.priors_off else ''}: "
              f"{len(rows)} tips, {kept} on a convex corner (<= {s6._TIP_CORNER_MAX_DEG:g} deg)")
        for ang, e in sorted(rows, key=lambda r: (r[0] is None, r[0])):
            print(f"  {'-' if ang is None else f'{ang:5.0f}'} deg  end ({e[0]:6.1f}, {e[1]:6.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
