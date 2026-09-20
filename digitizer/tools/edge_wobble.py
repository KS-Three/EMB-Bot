#!/usr/bin/env python
"""Does the sewn edge wander about the outline it was given?

Kent, 2026-09-19: *"Right shapes, bad edges … wobbly / lumpy curves bothers me
most … it needs to be perfect."* The same sentence as 2026-08-27's *"shapes are
accurate but smoothness is not"* (`edge_smoothness.py`), and this time a spike
located it. Offset removed, same unit on both sides:

                 outline vs artwork      sewn rails vs outline
    enthusiast   std 0.011  p95 0.023    std 0.071  p95 0.185   (0.068 mm source px)
    becker       std 0.074  p95 0.154    std 0.082  p95 0.195   (0.552 mm source px)
    whitebg      std 0.049  p95 0.039    std 0.029  p95 0.058   (synthetic control)

On decent artwork stage 4's polygon tracks the art to a hundredth of a
millimetre and the STITCHING adds six times that about a clean outline. On a
low-resolution upload both sides wobble. The synthetic control sews clean,
which is why no suite ever saw this. `satin_rails_follow_edge` ON moved the
rail figure about 10% (0.071 -> 0.064, 0.082 -> 0.074) — Kent's eye had
already called that flag invisible. (The spike ran on `da6606e4`, BEFORE
2026-09-19's satin flips; this tool's own satin row was re-measured after
them and barely moved. Its live numbers are in DOCTRINE 2026-09-19 — quote
those, not this table.)

## Why this is not `edge_smoothness` or `curve_fidelity`

`edge_smoothness.ragged_mm` compares a rendered thread raster with the
artwork's ink mask: it needs registration, it sees outline error and stitch
error summed, and its floor is the raster's pixel. `curve_fidelity` reads turn
angles off the stitch path and answers "is this curve a polygon", with no
outline to compare against. Neither can say WHICH STAGE a wobble was born in.

This reads the two things the engine already holds in one frame —
`result.regions[].polygon` and `plan.iter_runs()` — so there is no raster, no
registration, and nothing about the artwork in it at all. It is the
stitch-side half of the table above, and only that half.

## The measurement

Every visible edge penetration — satin and border rail points, fill row ends,
bean/run outline points — gets a SIGNED distance to its own shape's boundary
(+ outside, - inside). Penetrations are ordered along the boundary ring they
sit nearest, per run and per rail, and the series is high-passed over
`WINDOW_MM`: a constant standoff is pull compensation and a slow drift is a
taper, and neither is what Kent is looking at. What is left is wobble.

The baseline is a 3-point median (so one dent cannot drag it) followed by a
trapezoid-weighted mean (whose alternating sum is exactly zero, so a sawtooth
reads at its own amplitude instead of double or nil — a plain rolling median
INVERTS an alternation and reads it 2x).

`stage6_satin._short_stitch_guard` retracts alternate penetrations where a
rail bunches under `SATIN_SHORT_STITCH_AT_MM`. That is technique, not defect,
and it is excused by the guard's OWN condition — an inward dip whose
along-boundary step is under that threshold — never by size alone: the same
dip on a rail stepping a full 0.4 mm is a sawtooth and is counted.

    .venv/Scripts/python tools/edge_wobble.py [fixture ...] [--json]
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import shapely
from scipy.ndimage import median_filter
from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from digitizer_core import PipelineConfig, digitize, machine, stitches  # noqa: E402

# The high-pass window along the edge. Long enough to hold several stitches at
# satin spacing, short enough that a letter's own curvature of offset (a taper
# into a serif) stays in the baseline.
WINDOW_MM = 3.0
# A penetration further than this from its shape's boundary is not an edge
# penetration (a split-satin mid-column stitch, a fill's interior). The
# largest legitimate standoff is a short-stitch retraction, capped at
# `SATIN_SHORT_STITCH_PULL_MAX_MM` = 0.6, on top of the pull.
EDGE_BAND_MM = 1.2
# A series breaks where consecutive penetrations sit further apart than this
# along the boundary: the far side of a column, another run's territory.
GAP_MM = 1.5
MIN_SERIES = 8
# "Visible" — a third of a 0.4 mm thread. The spike's table is quoted at it.
OVER_MM = 0.15
SHORT_STITCH_DIP_MM = 0.1
SHORT_STITCH_STEP_MM = machine.SATIN_SHORT_STITCH_AT_MM * 1.15

RAIL_KINDS = (stitches.SATIN, stitches.BORDER)
LINE_KINDS = (stitches.BEAN, stitches.RUN)
TIER = {stitches.SATIN: "satin", stitches.BORDER: "border", stitches.FILL: "fill",
        stitches.BEAN: "line", stitches.RUN: "line"}


def _row_ends(P: np.ndarray) -> np.ndarray:
    """Both vertices of every row-to-row link of a boustrophedon fill.

    NOT a turn-angle test. That was the first cut, and it is biased exactly
    where it matters: a row end that sits 0.3 mm shy of its neighbour turns
    53 deg into the link instead of 90, so a threshold on the turn drops the
    wobbling ends and keeps the clean ones (measured on this file's own bar
    fixture: 12 of 24 right-hand ends found, every one of them at d = 0.00).
    The path REVERSES along the row axis once per link whatever the jog, and
    the link is whichever segment at that vertex runs across the rows.
    """
    if len(P) < 4:
        return P[:0]
    seg = np.diff(P, axis=0)
    ang = np.arctan2(seg[:, 1], seg[:, 0])
    w = (seg ** 2).sum(1)                       # long stitches set the axis
    axis = 0.5 * math.atan2((w * np.sin(2 * ang)).sum(), (w * np.cos(2 * ang)).sum())
    u = seg @ np.array([math.cos(axis), math.sin(axis)])
    v = np.abs(seg @ np.array([-math.sin(axis), math.cos(axis)]))
    sign = np.sign(np.where(np.abs(u) < 1e-9, 0.0, u))
    for i in range(1, len(sign)):               # a square link carries the row's sign
        if sign[i] == 0:
            sign[i] = sign[i - 1]
    ends = set()
    for i in np.where(sign[1:] * sign[:-1] < 0)[0] + 1:   # vertex i: seg i-1 | seg i
        ends.add(int(i))
        ends.add(int(i - 1 if v[i - 1] >= v[i] else i + 1))
    return P[sorted(ends)]


def _edge_parts(run) -> list[np.ndarray]:
    P = np.asarray(run.points, float)
    if run.kind in RAIL_KINDS:
        return [P[0::2], P[1::2]]
    if run.kind == stitches.FILL:
        return [_row_ends(P)]
    return [P]


def _baseline(d: np.ndarray, n: int) -> np.ndarray:
    w = np.ones(n + 1)
    w[0] = w[-1] = 0.5
    med = median_filter(d, size=3, mode="nearest")
    pad = np.pad(med, n // 2, mode="edge")
    return np.convolve(pad, w / w.sum(), mode="valid")


def _series(part: np.ndarray, rings: list[LineString], poly):
    """-> [(points, signed_d)] ordered along each ring, broken at gaps."""
    if len(part) < MIN_SERIES:
        return []
    pts = shapely.points(part)
    dist = np.stack([shapely.distance(r, pts) for r in rings])
    ring_of = dist.argmin(0)
    d = dist.min(0) * np.where(shapely.contains(poly, pts), -1.0, 1.0)
    out = []
    for k, ring in enumerate(rings):
        sel = np.where((ring_of == k) & (np.abs(d) <= EDGE_BAND_MM))[0]
        if len(sel) < MIN_SERIES:
            continue
        s = shapely.line_locate_point(ring, pts[sel])
        order = np.argsort(s, kind="stable")
        sel, s = sel[order], s[order]
        for seg in np.split(np.arange(len(sel)), np.where(np.diff(s) > GAP_MM)[0] + 1):
            if len(seg) >= MIN_SERIES:
                out.append((part[sel[seg]], d[sel[seg]], s[seg]))
    return out


def _excused(d: np.ndarray, s: np.ndarray) -> np.ndarray:
    """The guard's own condition: an inward dip on a bunched rail."""
    lo = np.r_[np.inf, d[:-1]]
    hi = np.r_[d[1:], np.inf]
    step = np.minimum(np.r_[np.inf, np.diff(s)], np.r_[np.diff(s), np.inf])
    return (d < np.minimum(lo, hi) - SHORT_STITCH_DIP_MM) & (step < SHORT_STITCH_STEP_MM)


def _summary(dev: np.ndarray, d: np.ndarray) -> dict:
    if not len(dev):
        return dict(points=0, wobble_std_mm=None, wobble_p95_mm=None,
                    wobble_max_mm=None, share_over=None, offset_mm=None)
    a = np.abs(dev)
    return dict(points=int(len(dev)),
                wobble_std_mm=round(float(dev.std()), 4),
                wobble_p95_mm=round(float(np.percentile(a, 95)), 4),
                wobble_max_mm=round(float(a.max()), 4),
                share_over=round(float((a > OVER_MM).mean()), 4),
                offset_mm=round(float(np.median(d)), 4))


def analyse_plan(polygons: dict, plan) -> dict:
    """`polygons` is shape_id -> shapely Polygon, in the plan's own mm frame."""
    rings_of = {}
    rows = []          # (tier, shape_id, x, y, dev, d)
    excused = 0
    for _block, run in plan.iter_runs():
        tier, poly = TIER.get(run.kind), polygons.get(run.shape_id)
        if tier is None or poly is None or poly.is_empty:
            continue
        if run.shape_id not in rings_of:
            geoms = getattr(poly, "geoms", [poly])
            rings_of[run.shape_id] = [LineString(r.coords) for g in geoms
                                      for r in (g.exterior, *g.interiors)]
        for part in _edge_parts(run):
            for P, d, s in _series(part, rings_of[run.shape_id], poly):
                if run.kind in RAIL_KINDS:
                    skip = _excused(d, s)
                    excused += int(skip.sum())
                    P, d, s = P[~skip], d[~skip], s[~skip]
                    if len(d) < MIN_SERIES:
                        continue
                step = float(np.median(np.diff(s))) or WINDOW_MM
                n = max(4, int(round(WINDOW_MM / max(step, 1e-6))) // 2 * 2)
                n = min(n, (len(d) - 1) // 2 * 2)
                dev = d - _baseline(d, n)
                rows += [(tier, run.shape_id, x, y, v, dd)
                         for (x, y), v, dd in zip(P, dev, d)]

    dev = np.array([r[4] for r in rows])
    d = np.array([r[5] for r in rows])
    tiers = np.array([r[0] for r in rows])
    out = _summary(dev, d)
    out["short_stitches_excused"] = excused
    out["by_tier"] = {t: _summary(dev[tiers == t], d[tiers == t])
                      for t in dict.fromkeys(r[0] for r in rows)}
    worst = []
    for i in np.argsort(-np.abs(dev)) if len(dev) else []:
        _t, sid, x, y, v, _d = rows[i]
        if all(w["shape_id"] != sid or math.dist(w["at_mm"], (x, y)) > 2.0 for w in worst):
            worst.append(dict(shape_id=sid, tier=rows[i][0], dev_mm=round(float(v), 3),
                              at_mm=(round(float(x), 2), round(float(y), 2))))
        if len(worst) == 5:
            break
    out["worst"] = worst
    return out


def analyse(image_path: str | Path, cfg: PipelineConfig | None = None) -> dict:
    image_path = Path(image_path)
    result, plan = digitize(image_path, cfg or PipelineConfig())
    row = analyse_plan({r.shape_id: r.polygon for r in result.regions}, plan)
    return {"fixture": image_path.name, "route": result.design_class, **row}


def _resolve(names: list[str]) -> list[Path]:
    out = []
    for n in names:
        p = Path(n)
        out.append(p if p.exists() else ROOT / "testdata" / n)
    return out


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    rows = [analyse(p) for p in _resolve([a for a in argv if not a.startswith("--")])]
    if as_json:
        print(json.dumps(rows, indent=1))
        return 0
    for r in rows:
        print(f"{r['fixture']}  ({r['route']})  {r['points']} edge penetrations, "
              f"{r['short_stitches_excused']} short stitches excused")
        for t, s in r["by_tier"].items():
            print(f"  {t:7s} n={s['points']:6d}  std {s['wobble_std_mm']:.3f}  "
                  f"p95 {s['wobble_p95_mm']:.3f}  max {s['wobble_max_mm']:.2f} mm  "
                  f">{OVER_MM} mm {s['share_over']:.1%}  offset {s['offset_mm']:+.2f}")
        for w in r["worst"]:
            print(f"    worst {w['dev_mm']:+.2f} mm  {w['tier']:6s} {w['shape_id']}  at {w['at_mm']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
