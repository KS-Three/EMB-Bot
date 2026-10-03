"""Does the sewn edge wander about the outline it was given? The measurement.

Every visible edge penetration's signed distance to its own shape's boundary,
high-passed along that boundary: a constant standoff is pull compensation and
a slow drift is a taper, and what is left is wobble. `tools/edge_wobble.py` is
this instrument's CLI and renders and carries its story — the 2026-09-19
spike, why it is neither `edge_smoothness` nor `curve_fidelity`, how the
baseline is built. That file held this code until 2026-10-03.

It lives here because `preflight` reports three of these readings as metrics
(`_edge_wobble_metrics`, MASTER_SCOPE defect 46) and `digitizer_core` cannot
import from `tools/`. Reported, never judged: nothing in this file decides
anything about a design. `OVER_MM` is what the tool's renders ring.
"""
from __future__ import annotations

import math

import numpy as np
import shapely
from scipy.ndimage import median_filter
from shapely.geometry import LineString

from . import machine, stitches

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
# Where a rail deviation sits. The first root-cause probe (2026-09-19) found
# the rate of >OVER_MM deviations at 15-26% within 0.6 mm of an outline corner
# against 2-4% mid-column, on all three real logos: most of "wobble" is rails
# ROUNDING CORNERS, then column ends, and only then a lumpy curve. One pooled
# number cannot say which, and they are three different fixes. A "corner" is
# an outline vertex turning more than CORNER_TURN_DEG — which a curve tighter
# than ~1 mm radius also is, at this engine's chord lengths, and rightly so: a
# rail rounds both the same way. "end" is the end of a measured series.
CORNER_TURN_DEG = 35.0
CORNER_MM = 0.6
END_MM = 1.5
ZONES = ("corner", "end", "mid")
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


def _corners(rings: list[LineString]) -> np.ndarray:
    out = []
    for ring in rings:
        C = np.asarray(ring.coords)[:-1]
        a, b = C - np.roll(C, 1, 0), np.roll(C, -1, 0) - C
        turn = np.abs(np.arctan2(a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0], (a * b).sum(1)))
        out.append(C[turn > math.radians(CORNER_TURN_DEG)])
    return np.vstack(out) if out else np.zeros((0, 2))


def _zones(P: np.ndarray, s: np.ndarray, corners: np.ndarray) -> np.ndarray:
    z = np.full(len(P), "mid", dtype=object)
    z[np.minimum(s - s[0], s[-1] - s) < END_MM] = "end"
    if len(corners):
        near = np.hypot(*(P[:, None, :] - corners[None, :, :]).transpose(2, 0, 1)).min(1)
        z[near < CORNER_MM] = "corner"
    return z


def _baseline(d: np.ndarray, n: int) -> np.ndarray:
    w = np.ones(n + 1)
    w[0] = w[-1] = 0.5
    med = median_filter(d, size=3, mode="nearest")
    pad = np.pad(med, n // 2, mode="edge")
    return np.convolve(pad, w / w.sum(), mode="valid")


def _nearest_ring(rings: list[LineString], tree, part: np.ndarray):
    """-> (ring index, distance) per point: `argmin` and `min` over every ring.

    Asked of an index, not computed ring by ring. The plain form is rings x
    points distances, and a ground with a block of knocked-out text in it has
    hundreds of rings. Measured 2026-10-03 on a plate with a run round every
    hole, the plain form against this one, readings identical in each:
    25 holes 0.08 s -> 0.05, 100 holes 0.77 -> 0.21, 400 holes 9.05 -> 1.36
    -- in a measurement preflight makes on every job.

    The index only NAMES the ring; the distance is then taken the way it
    always was, so a reading cannot move. `all_matches` returns every ring at
    the minimum and the lowest index is kept, which is `argmin`'s own tie
    rule -- the web between two holes is equidistant from both.
    """
    ring_of = np.zeros(len(part), dtype=np.intp)
    dist = np.full(len(part), np.nan)
    ok = np.flatnonzero(np.isfinite(part).all(axis=1))
    pts = shapely.points(part[ok])
    if len(rings) > 1:
        src, hit = tree.query_nearest(pts, all_matches=True)
        ring_of[ok] = len(rings)
        np.minimum.at(ring_of, ok[src], hit)
    dist[ok] = shapely.distance(np.asarray(rings, dtype=object)[ring_of[ok]], pts)
    return ring_of, dist


def _series(part: np.ndarray, rings: list[LineString], poly, tree=None):
    """-> [(points, signed_d)] ordered along each ring, broken at gaps.
    `tree` is an `STRtree` over `rings`, needed when there is more than one."""
    if len(part) < MIN_SERIES:
        return []
    pts = shapely.points(part)
    ring_of, dist = _nearest_ring(rings, tree, part)
    d = dist * np.where(shapely.contains(poly, pts), -1.0, 1.0)
    near = np.abs(d) <= EDGE_BAND_MM
    out = []
    for k in np.unique(ring_of[near]):          # only the rings this part reaches
        ring = rings[k]
        sel = np.where((ring_of == k) & near)[0]
        if len(sel) < MIN_SERIES:
            continue
        s = shapely.line_locate_point(ring, pts[sel])
        order = np.argsort(s, kind="stable")
        sel, s = sel[order], s[order]
        for seg in np.split(np.arange(len(sel)), np.where(np.diff(s) > GAP_MM)[0] + 1):
            if len(seg) >= MIN_SERIES:
                out.append((part[sel[seg]], d[sel[seg]], s[seg]))
    return out


def _excused(P: np.ndarray, d: np.ndarray) -> np.ndarray:
    """The guard's own condition: an inward dip on a bunched rail.

    The step is measured ALONG THE RAIL, between the dip's two neighbours —
    never along the outline the points project onto. The first cut used the
    projected step, and a projection compresses toward a convex corner: a rail
    cutting a corner at 1 mm radius steps 0.4 mm along itself and 0.28 along
    the outline, under `SATIN_SHORT_STITCH_AT_MM`, so the corner-cutting
    penetration was excused as technique and the instrument under-read the
    one zone that carries most of the defect. Caught by the zone test.
    """
    n = len(d)
    out = np.zeros(n, bool)
    if n < 3:
        return out
    chord = P[2:] - P[:-2]
    L = np.maximum(np.hypot(*chord.T), 1e-9)
    t = ((P[1:-1] - P[:-2]) * chord).sum(1) / L          # along-rail, prev -> dip
    step = np.minimum(t, L - t)
    dip = d[1:-1] < np.minimum(d[:-2], d[2:]) - SHORT_STITCH_DIP_MM
    out[1:-1] = dip & (step < SHORT_STITCH_STEP_MM)
    return out


def _unreadable_ends(d: np.ndarray) -> np.ndarray:
    """A series END that dips inward has one neighbour, so its un-retracted
    step cannot be recovered: it may be a short stitch or a defect, and the
    instrument cannot tell. It is neither excused nor counted — it is reported
    (`series_ends_unread`). Both guesses were tried: counting it read a 0.6 mm
    "defect" on a clean tight curve whose last station the guard retracted;
    a one-neighbour estimate excused a corner-cutting point wherever a ring's
    first vertex happens to be a corner."""
    out = np.zeros(len(d), bool)
    if len(d) >= 2:
        out[0] = d[0] < d[1] - SHORT_STITCH_DIP_MM
        out[-1] = d[-1] < d[-2] - SHORT_STITCH_DIP_MM
    return out


# The reverse direction. Stitches -> outline cannot flag a place with no
# stitches in it, and that is most of what Kent meant by "you missed quite a
# few" (2026-09-19): the bare crotch of Becker's M and the foot of
# Enthusiast's N are outline with NO THREAD NEAR IT. So the outline is walked
# too: a sample further than UNSEWN_GAP_MM from any visible thread — half a
# thread's width plus the pull standoff, generously — is bare, and a run of
# them at least UNSEWN_MIN_SPAN_MM long is a span worth a ring. Thread from
# ANY shape counts as cover: under seam ownership the shape beneath skips an
# edge the shape on top sews, and that edge is not bare.
UNSEWN_GAP_MM = 0.5
UNSEWN_STEP_MM = 0.25
UNSEWN_MIN_SPAN_MM = 0.75


def _unsewn(polygons: dict, plan, background: frozenset = frozenset()) -> dict:
    """`background` names shapes that are MEANT to carry no thread — stage 1's
    enclosed background (a letter's counter, a knocked-out word). On the first
    real run every threadless shape was one of those (4 / 7 / 9 on enthusiast /
    Becker / Gaulke), so an unqualified count reads as dropped elements and is
    not. They are left out of `shapes_without_thread`."""
    segs, threaded = [], set()
    for _b, run in plan.iter_runs():
        if run.kind in TIER and len(run.points) >= 2:
            P = np.asarray(run.points, float)
            segs.append(shapely.linestrings(np.stack([P[:-1], P[1:]], axis=1)))
            threaded.add(run.shape_id)
    without = sorted(sid for sid, p in polygons.items()
                     if sid not in threaded and sid not in background and not p.is_empty)
    out = dict(edge_mm=0.0, share=None, spans=[], shapes_without_thread=without)
    if not segs:
        return out
    tree = shapely.STRtree(np.concatenate(segs))
    total = 0.0
    for sid, poly in polygons.items():
        if sid not in threaded or poly.is_empty:
            continue
        for geom in getattr(poly, "geoms", [poly]):
            for ring in (geom.exterior, *geom.interiors):
                line = LineString(ring.coords)
                n = max(8, int(line.length / UNSEWN_STEP_MM))
                step = line.length / n
                total += line.length
                pts = shapely.line_interpolate_point(line, np.arange(n) * step)
                idx, dist = tree.query_nearest(pts, return_distance=True, all_matches=False)
                gap = np.zeros(n)
                gap[idx[0]] = dist
                bare = gap > UNSEWN_GAP_MM
                if not bare.any():
                    continue
                if bare.all():
                    runs = [np.arange(n)]
                else:                                    # circular runs: start on a sewn sample
                    k = int(np.argmin(bare))
                    order = np.r_[k:n, 0:k]
                    b = bare[order]
                    edges = np.flatnonzero(np.diff(np.r_[0, b.astype(int), 0]))
                    runs = [order[a:z] for a, z in zip(edges[0::2], edges[1::2])]
                for r in runs:
                    if len(r) * step < UNSEWN_MIN_SPAN_MM:
                        continue
                    xy = shapely.get_coordinates(pts[r])
                    mid = xy[len(xy) // 2]
                    out["edge_mm"] += len(r) * step
                    out["spans"].append(dict(
                        shape_id=sid, length_mm=round(len(r) * step, 2),
                        gap_mm=round(float(gap[r].max()), 3),
                        at_mm=(round(float(mid[0]), 2), round(float(mid[1]), 2)),
                        path_mm=[(round(float(x), 2), round(float(y), 2)) for x, y in xy]))
    out["edge_mm"] = round(out["edge_mm"], 2)
    out["share"] = round(out["edge_mm"] / total, 4) if total else None
    out["spans"].sort(key=lambda s: -s["length_mm"])
    return out


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


def analyse_plan(polygons: dict, plan, background=frozenset(),
                 unsewn: bool = True) -> dict:
    """`polygons` is shape_id -> shapely Polygon, in the plan's own mm frame.
    `background` is the shape ids meant to carry no thread (see `_unsewn`).
    `unsewn=False` skips that outline walk and leaves its key out -- a fifth
    to a half of the time, for a caller that reads only the wobble."""
    rings_of, trees, corners_of = {}, {}, {}
    rows = []          # (tier, shape_id, x, y, dev, d, zone)
    excused = unread = 0
    for _block, run in plan.iter_runs():
        tier, poly = TIER.get(run.kind), polygons.get(run.shape_id)
        if tier is None or poly is None or poly.is_empty:
            continue
        if run.shape_id not in rings_of:
            geoms = getattr(poly, "geoms", [poly])
            rings = rings_of[run.shape_id] = [LineString(r.coords) for g in geoms
                                              for r in (g.exterior, *g.interiors)]
            trees[run.shape_id] = shapely.STRtree(rings) if len(rings) > 1 else None
            corners_of[run.shape_id] = _corners(rings)
            shapely.prepare(poly)                # `contains`, once per run part
        for part in _edge_parts(run):
            for P, d, s in _series(part, rings_of[run.shape_id], poly,
                                   trees[run.shape_id]):
                if run.kind in RAIL_KINDS:
                    skip = _excused(P, d)
                    excused += int(skip.sum())
                    P, d, s = P[~skip], d[~skip], s[~skip]
                    skip = _unreadable_ends(d)
                    unread += int(skip.sum())
                    P, d, s = P[~skip], d[~skip], s[~skip]
                    if len(d) < MIN_SERIES:
                        continue
                step = float(np.median(np.diff(s))) or WINDOW_MM
                n = max(4, int(round(WINDOW_MM / max(step, 1e-6))) // 2 * 2)
                n = min(n, (len(d) - 1) // 2 * 2)
                dev = d - _baseline(d, n)
                zone = (_zones(P, s, corners_of[run.shape_id])
                        if run.kind in RAIL_KINDS else [None] * len(P))
                rows += [(tier, run.shape_id, x, y, v, dd, z)
                         for (x, y), v, dd, z in zip(P, dev, d, zone)]

    dev = np.array([r[4] for r in rows])
    d = np.array([r[5] for r in rows])
    tiers = np.array([r[0] for r in rows])
    zones = np.array([r[6] for r in rows], dtype=object)
    out = _summary(dev, d)
    out["short_stitches_excused"] = excused
    out["series_ends_unread"] = unread
    out["by_tier"] = {t: _summary(dev[tiers == t], d[tiers == t])
                      for t in dict.fromkeys(r[0] for r in rows)}
    out["rail_zones"] = {z: _summary(dev[zones == z], d[zones == z])
                         for z in ZONES if (zones == z).any()}
    worst = []
    for i in np.argsort(-np.abs(dev)) if len(dev) else []:
        _t, sid, x, y, v, _d, _z = rows[i]
        if all(w["shape_id"] != sid or math.dist(w["at_mm"], (x, y)) > 2.0 for w in worst):
            worst.append(dict(shape_id=sid, tier=rows[i][0], zone=rows[i][6],
                              dev_mm=round(float(v), 3),
                              at_mm=(round(float(x), 2), round(float(y), 2))))
        if len(worst) == 5:
            break
    out["worst"] = worst
    out["flagged"] = [dict(tier=r[0], zone=r[6], dev_mm=round(float(r[4]), 3),
                           at_mm=(round(float(r[2]), 2), round(float(r[3]), 2)))
                      for r in rows if abs(r[4]) > OVER_MM]
    if unsewn:
        out["unsewn"] = _unsewn(polygons, plan, frozenset(background))
    return out
