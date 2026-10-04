"""Is a curve sewn as a curve, or as a polygon? The measurement.

Turn angles read off `plan.iter_runs()` -- the vertices the machine sews --
and two statistics over them: `roughness_deg`, the mean change in turn from
one vertex to the next, and `turn_gini`, how concentrated the turning is.
`tools/curve_fidelity.py` is this instrument's CLI and carries its story: why
it cannot come from a raster, why there are two numbers, what it cannot do,
and the tables behind each. That file held this code until 2026-10-03.

It lives here because `preflight` reports these readings as metrics
(`_curve_roughness_metrics`, MASTER_SCOPE defect 46 -- Law 37's
direction-change score) and `digitizer_core` cannot import from `tools/`.
Reported, never judged: the instrument cannot read intent, so its number
compares a design with itself across engine changes and is never a grade.
"""
from __future__ import annotations

import math

import numpy as np

from . import stitches


# A turn at or above this is an intentional corner — a letterform's stem, a
# badge's point — not a curve rendered coarsely. Excluding it is what stops a
# square from topping the ranking: with its four corners gone a square has no
# curved vertex left at all, so it REFUSES rather than scoring. Chosen at 60 deg because a
# 12-gon (30 deg/vertex) is still visibly a polygon and must stay measured,
# while a square's 90 deg must not. Its cost is the star above.
CORNER_DEG = 60.0

# A trace with fewer interior vertices than this cannot support a distribution
# statistic; a 3-point run would hand back a gini of 0 or 1 on noise.
MIN_TURNS = 8

# Only what Kent can SEE. Underlay is hidden under its satin, fill is tatami
# rows whose turning is row reversal rather than artwork shape, and
# travel/tie are structural moves the artwork never asked for.
VISIBLE_KINDS = (stitches.SATIN, stitches.BORDER, stitches.BEAN, stitches.RUN)

# Below this total turning a trace is a straight line, and the concentration
# of near-zero float noise is not a measurement.
MIN_TOTAL_TURN_DEG = 30.0


def _rails(points: list[tuple[float, float]]) -> list[np.ndarray]:
    """Split an alternating satin zigzag into its two rails.

    A satin run's points alternate across the column (`stage6_satin.py`'s
    "alternating zigzag"), so the raw sequence turns ~180 deg at every vertex
    and reads as pure noise. Each rail on its own traces the artwork edge —
    verified on `logo_whitebg`, where the raw chords run 2.66-2.69 mm and the
    rails step a clean 0.406 mm.
    """
    P = np.asarray(points, float)
    return [P[0::2], P[1::2]]


def traces(plan) -> list[tuple[str, str, np.ndarray]]:
    """-> [(kind, shape_id, polyline)] for every visible outline in the plan."""
    out = []
    for _block, run in plan.iter_runs():
        if run.kind not in VISIBLE_KINDS or len(run.points) < 4:
            continue
        parts = (_rails(run.points)
                 if run.kind in (stitches.SATIN, stitches.BORDER)
                 else [np.asarray(run.points, float)])
        for p in parts:
            if len(p) >= MIN_TURNS + 2:
                out.append((run.kind, run.shape_id, p))
    return out


def turns(poly: np.ndarray) -> np.ndarray:
    """Turn angle in radians at each INTERIOR vertex of an open polyline.

    Open, not wrapped: a satin rail is a column with two free ends, and
    closing it would invent a chord across the shape. A closed ring loses one
    vertex of its several hundred, which no statistic here can feel.
    """
    P = np.asarray(poly, float)
    a, b = P[1:-1] - P[:-2], P[2:] - P[1:-1]
    la, lb = np.linalg.norm(a, axis=1), np.linalg.norm(b, axis=1)
    ok = (la > 1e-9) & (lb > 1e-9)
    cross = a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]
    return np.abs(np.arctan2(cross, (a * b).sum(axis=1)))[ok]


def gini(x: np.ndarray) -> float:
    """Concentration of a non-negative sample: 0 spread evenly, 1 all in one."""
    x = np.sort(np.asarray(x, float))
    if x.size == 0 or x.sum() <= 0:
        return 0.0
    n = x.size
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def measure(polys: list[np.ndarray]) -> dict:
    """Pool the curve statistics over a design's traces.

    Turn CHANGES are differenced within a trace and only then pooled — a diff
    across a trace boundary would compare one shape's edge to another's.
    """
    kept, diffs, n_corner, n_kept = [], [], 0, 0
    for p in polys:
        th = turns(p)
        corner = th >= math.radians(CORNER_DEG)
        n_corner += int(corner.sum())
        t = th[~corner]
        if t.size < MIN_TURNS:
            continue
        n_kept += int(t.size)
        kept.append(t)
        diffs.append(np.abs(np.diff(t)))

    if not kept:
        return {"turn_gini": float("nan"), "roughness_deg": float("nan"),
                "curve_vertices": 0, "corner_vertices": n_corner,
                "traces": 0, "refusal": "no measurable curve in the visible tiers"}

    allt = np.concatenate(kept)
    total_deg = float(np.degrees(allt.sum()))
    if total_deg < MIN_TOTAL_TURN_DEG:
        return {"turn_gini": float("nan"), "roughness_deg": float("nan"),
                "curve_vertices": n_kept, "corner_vertices": n_corner,
                "traces": len(kept),
                "refusal": f"outline is straight ({total_deg:.0f} deg of turn)"}

    return {
        "turn_gini": round(gini(allt), 4),
        "roughness_deg": round(float(np.degrees(np.concatenate(diffs).mean())), 4),
        "curve_vertices": n_kept,
        "corner_vertices": n_corner,
        "traces": len(kept),
        "refusal": None,
    }
