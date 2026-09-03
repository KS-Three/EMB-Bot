#!/usr/bin/env python
"""Where satin rails sit against the artwork edge, and how smooth they are.

The instrument behind defect 23 (2026-09-03, `docs/rail-dents-2026-09-03.md`).
Two readings over every satin penetration of a design (ties and split
penetrations stripped first):

- **rail-to-edge** -- the signed distance from each penetration to its
  shape's boundary, positive inside the artwork. A rail that stops short
  reads positive; pull compensation reads negative (`max_out` is the comp).
  `>0.1mm in` is the share sitting more than a tenth of a millimetre inside
  the art -- on lettering fixtures 8-24% of them, from the symmetric-offset
  rail model (smoothed width below the local edge on the wider side), the
  short-stitch guard on bends and junction caps, NOT from `place`'s ladder.
- **rail smoothness** -- each rail point's distance from the chord of its
  two neighbours (`jitter`; a rail alternating between the full width and
  0.85x reads ~0.05 here, a rail on the edge ~0.005) and the same-rail
  intervals over 2 x SATIN_SPACING (`holes`, the starburst test's metric).

- **bare area** (`--bare`) -- the share of each satin shape's artwork that
  lies outside a thread's width of every sewn cross, unioned per shape.
  This is coverage; the rail-to-edge reading is not (an oblique edge or a
  corner reads "inside" even when the rail is on the edge along its own
  normal, and the short-stitch guard's retractions on bends dominate it by
  design). Behind `PipelineConfig.satin_rails_follow_edge` (2026-09-03):
  Becker 8.6 -> 5.8%, ENTHUSIAST 5.7 -> 4.4%, drone 6.1 -> 4.6%.

`--ladders` adds the census that found the real mechanism: every containment
miss inside `_rail_points`, bucketed by how far outside the art the rail at
the smoothed width sat on its FIRST miss, and how many misses it took to fit
(1 = the old 0.85x step). On the pre-change tree 70-90% of the overshoots
were under 50 um -- a pixel or less -- and three quarters took the 15% step;
on the fixed tree a body station never ladders (it goes onto the edge).

    .venv/bin/python tools/rail_edge.py [case ...] [--ladders] [--bare] [--follow-edge]

Cases: fremont, enthusiast (93 mm, left_chest), drone, becker, ribbon, alpha,
whitebg, gaulke, or a path under `testdata/`.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from shapely.geometry import LineString, Point  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from digitizer_core import PipelineConfig, digitize, machine  # noqa: E402
from digitizer_core import stage6_satin  # noqa: E402
from digitizer_core.stage6_satin import strip_splits  # noqa: E402
from digitizer_core.stitches import strip_ties  # noqa: E402

CASES = {
    "fremont": ("photo/logo_hotel_fremont.webp",
                dict(target_width_mm=80.0, max_colors=3, forced_class="flat", border="off")),
    "enthusiast": ("photo/enthusiast_logo.png",
                   dict(target_width_mm=93.0, garment_id="left_chest")),
    "drone": ("photo/drone_render.png", dict(target_width_mm=80.0)),
    "becker": ("becker_marine_logo.png", dict(target_width_mm=80.0)),
    "ribbon": ("ribbon_curve.png", dict(target_width_mm=80.0)),
    "alpha": ("logo_alpha.png", dict(target_width_mm=80.0)),
    "whitebg": ("logo_whitebg.png", dict(target_width_mm=80.0)),
    "gaulke": ("photo/logo_gaulke_roofing.png", dict(target_width_mm=80.0)),
}
EDGES = [1e-6, 1e-2, 0.05, 0.1, 0.25, 1e9]
LABELS = ["<1um", "<10um", "<50um", "<100um", "<250um", ">=250um"]


class _Census:
    """Wraps the polygon `_rail_points` sees: geometry untouched, `covers` counted."""

    def __init__(self, poly):
        self._p = poly
        self.seq: list[tuple[bool, float]] = []

    def covers(self, g):
        r = self._p.covers(g)
        self.seq.append((r, 0.0 if r else self._p.boundary.distance(g)))
        return r

    def __getattr__(self, name):
        return getattr(self._p, name)


def _ladder_census(proxies) -> tuple[list[int], dict[int, int]]:
    first = [0] * len(EDGES)
    steps: dict[int, int] = {}
    for p in proxies:
        seq, i = p.seq, 0
        while i < len(seq):
            if seq[i][0]:
                i += 1
                continue
            j = i
            while j < len(seq) and not seq[j][0]:
                j += 1
            first[next(b for b, e in enumerate(EDGES) if seq[i][1] < e)] += 1
            steps[j - i] = steps.get(j - i, 0) + 1
            i = j + 1
    return first, steps


def bare_area(polys: dict, plan) -> tuple[float, float]:
    """-> (bare mm2, satin art mm2): per shape, the artwork outside a
    thread's width of the union of its sewn crosses."""
    thread = getattr(machine, "COVERAGE_THREAD_W_MM", 0.4)
    by_shape: dict[str, list] = {}
    for _b, run in plan.iter_runs():
        if run.kind == "satin" and run.shape_id in polys:
            by_shape.setdefault(run.shape_id, []).extend(strip_splits(strip_ties(list(run.points))))
    num = den = 0.0
    for sid, pts in by_shape.items():
        crosses = [LineString([pts[i], pts[i + 1]]) for i in range(0, len(pts) - 1, 2)
                   if math.dist(pts[i], pts[i + 1]) > 1e-6]
        if not crosses:
            continue
        sewn = unary_union([c.buffer(thread / 2.0, cap_style=2) for c in crosses])
        den += polys[sid].area
        num += polys[sid].difference(sewn).area
    return num, den


def main(argv: list[str]) -> None:
    ladders = "--ladders" in argv
    bare = "--bare" in argv
    follow = "--follow-edge" in argv
    names = [a for a in argv if not a.startswith("--")] or list(CASES)
    proxies: list[_Census] = []
    if ladders:
        orig = stage6_satin._rail_points

        def spy(poly, *a, **k):
            p = _Census(poly)
            proxies.append(p)
            return orig(p, *a, **k)

        stage6_satin._rail_points = spy
    for name in names:
        rel, kw = CASES.get(name, (name, dict(target_width_mm=80.0)))
        proxies.clear()
        cfg = dict(kw)
        if follow:
            cfg["satin_rails_follow_edge"] = True
        result, plan = digitize(ROOT / "testdata" / rel, PipelineConfig(**cfg))
        polys = {r.shape_id: r.polygon for r in result.regions}
        gaps, steps, jitter, crosses, holes = [], [], [], [], 0
        for _b, run in plan.iter_runs():
            if run.kind != "satin" or run.shape_id not in polys:
                continue
            poly = polys[run.shape_id]
            bnd = poly.boundary
            pts = np.asarray(strip_splits(strip_ties(list(run.points))), dtype=float)
            for p in pts:
                q = Point(p)
                gaps.append(bnd.distance(q) * (1.0 if poly.covers(q) else -1.0))
            if len(pts) < 8:
                continue
            for rail in (pts[0::2], pts[1::2]):
                d = np.hypot(*(rail[1:] - rail[:-1]).T)
                steps.extend(d.tolist())
                holes += int(np.sum(d > 2 * machine.SATIN_SPACING_MM))
                a, b, c = rail[:-2], rail[1:-1], rail[2:]
                ac = c - a
                length = np.hypot(*ac.T)
                length[length == 0] = 1e-9
                jitter.extend((np.abs(ac[:, 0] * (b - a)[:, 1] - ac[:, 1] * (b - a)[:, 0]) / length).tolist())
            crosses.extend(np.hypot(*(pts[1::2] - pts[0::2]).T).tolist())
        print(f"## {name} st={plan.stats.stitch_count} trims={plan.stats.trims} "
              f"satin_pen={len(gaps)} crosses={len(crosses)}")
        if not gaps:
            continue
        g, j, c = np.asarray(gaps), np.asarray(jitter), np.asarray(crosses)
        print(f"  rail-to-edge  p50={np.median(g):+.3f} p90={np.percentile(g, 90):+.3f} "
              f">0.1mm in={np.mean(g > 0.1) * 100:.1f}%  max_out={-g.min():.3f}")
        if len(j):
            print(f"  smoothness    jitter p50={np.median(j):.4f} p90={np.percentile(j, 90):.4f}  "
                  f"same-rail p50={np.median(steps):.3f} holes(>{2 * machine.SATIN_SPACING_MM:.1f}mm)={holes}  "
                  f"med_cross={np.median(c):.3f} thread={c.sum():.0f}mm")
        if bare:
            num, den = bare_area(polys, plan)
            print(f"  bare area     {100 * num / max(den, 1e-9):.2f}% of {den:.0f} mm2 satin art (thread width {getattr(machine, 'COVERAGE_THREAD_W_MM', 0.4)} mm)")
        if ladders:
            first, taken = _ladder_census(proxies)
            tot = sum(first) or 1
            print("  ladders       " + f"{tot} first-miss overshoot: "
                  + "  ".join(f"{LABELS[b]}={first[b] * 100 / tot:.0f}%" for b in range(len(EDGES)))
                  + "  | misses before a fit: "
                  + "  ".join(f"{k}:{v * 100 / tot:.0f}%" for k, v in sorted(taken.items())[:4]))


if __name__ == "__main__":
    main(sys.argv[1:])
