"""`cfg.extra["satin_junction_block"]` (built OFF 2026-11-20; MFab top line, faults 1, 3, 4, 5, 8
of `docs/mfab-top-line-faults-2026-11-19.md`, census in `docs/mfab-ladder-junction-2026-11-20.md`).

Where strokes of one shape meet, the satin ladder sews two walks side by side: the F's
arm and stem each lay a ~1.9 mm bar over the same ~3 mm block, 0.5-1.5 mm apart across the stitch,
and the two bars fan into each other at both ends. The professional's file sews that block as ONE
column, as wide as the two bars together (3.8 mm, one run of ~40 stitches), and fans only at its ends.

`junction_block`: a satin stitch of a LATER run of the shape that has a partner among an EARLIER
satin run's stitches (same station along the stroke, a nearly equal cross direction, extents that
overlap but are not the same) is stretched across the union of the two. A stretch of at least
`MIN_STITCHES` such stitches is sewn as one wide column in the later run (its two ends ramp in over
`JUNCTION_RAMP` stitches, so the block does not step), and the earlier run's stitches under it become a
running path through their midpoints (`column_overlap`'s construction), so the needle path stays
unbroken and nothing the earlier bar covered is bare: the wide column spans both bars.
No satin floor, pull or cover figure is read or changed.
"""
from __future__ import annotations

import dataclasses
import math

import numpy as np
from shapely.geometry import Point

from . import deadline, stitches

MIN_STITCHES = 8        # ~3 mm of 0.4 mm pitch: a short lap stays as it was
MAX_UNION_MM = 4.4      # the wide column's longest stitch (the satin ceiling is 5.0)
MAX_ANGLE_DEG = 30.0    # cross directions that may count as one block
STATION_MM = 0.3        # |offset along the stroke| of two stitches at one station
MIN_SHIFT_MM = 0.3      # nearer than this the two are one bar (`column_overlap`'s case)
MIN_LAP_MM = 0.2        # the two stitches' extents overlap at least this much, or they only butt
MIN_GAIN_MM = 0.3       # the union is at least this much longer than the longer stitch
JUNCTION_RAMP = 16      # stitches over which each end of a block grows to full width
MISS_MM = 0.35          # a partner may go where its widened stitch falls at most this short of the union
CLIP_MM = 0.35         # a widened end may sit this far past the shape's polygon (pull slack)
JUNCTION_STEP_MM = 2.0  # `column_overlap.OVERLAP_RUN_STEP_MM`


def _mid_dir(P: np.ndarray):
    a, b = P[:-1], P[1:]
    v = b - a
    ln = np.hypot(v[:, 0], v[:, 1])
    ok = ln > 1e-9
    u = np.zeros_like(v)
    u[ok] = v[ok] / ln[ok, None]
    return (a + b) / 2.0, u, ln


def _thin(mids: list, step: float) -> list:
    out = [mids[0]]
    for q in mids[1:]:
        if math.dist(q, out[-1]) >= step:
            out.append(q)
    if math.dist(mids[-1], out[-1]) > 1e-6:
        out.append(mids[-1])
    return out


def _partners(PB: np.ndarray, PA: np.ndarray):
    """-> {B stitch index: (A stitch index, tmin, tmax)}: tmin/tmax are the union's ends along
    B's travel direction, measured from B's midpoint."""
    mB, uB, lB = _mid_dir(PB)
    mA, uA, lA = _mid_dir(PA)
    cos_min = math.cos(math.radians(MAX_ANGLE_DEG))
    found: dict[int, tuple] = {}
    for j in range(len(uB)):
        if lB[j] < 0.5:
            continue
        d = mA - mB[j]
        near = np.hypot(d[:, 0], d[:, 1]) <= MAX_UNION_MM
        if not near.any():
            continue
        u = uB[j]
        n = np.array([-u[1], u[0]])
        along = d @ u
        lat = d @ n
        par = np.abs(uA @ u) >= cos_min
        sel = near & par & (np.abs(lat) <= STATION_MM) & (lA >= 0.5) & (np.abs(along) >= MIN_SHIFT_MM)
        for i in np.flatnonzero(sel):
            half_a = lA[i] / 2.0
            lo_a, hi_a = along[i] - half_a, along[i] + half_a
            lo_b, hi_b = -lB[j] / 2.0, lB[j] / 2.0
            lap = min(hi_a, hi_b) - max(lo_a, lo_b)
            lo, hi = min(lo_a, lo_b), max(hi_a, hi_b)
            if lap < MIN_LAP_MM or hi - lo - max(lA[i], lB[j]) < MIN_GAIN_MM or hi - lo > MAX_UNION_MM:
                continue
            prev = found.get(j)
            if prev is None or abs(lat[i]) < prev[3]:
                found[j] = (int(i), lo, hi, abs(lat[i]))
    return {j: v[:3] for j, v in found.items()}


def _stretches(js: list[int], gap: int = 1) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    s = p = None
    for j in sorted(js):
        if s is None:
            s = p = j
        elif j - p <= gap + 1:
            p = j
        else:
            out.append((s, p))
            s = p = j
    if s is not None:
        out.append((s, p))
    return out


def junction_block(runs: list, poly=None, short_ramp: bool = False) -> tuple[list, int]:
    """`runs` with each later satin stretch that stacks on an earlier one sewn as one wide
    column. -> (runs, stitches merged). A run with no stretch is the same object."""
    out = list(runs)
    n_merged = 0
    reach = None if poly is None else poly.buffer(CLIP_MM)
    satin = [i for i, r in enumerate(runs) if r.kind == stitches.SATIN and len(r.points) >= 3]
    for bi in satin:
        deadline.check("stage 7 junction block")
        rb = out[bi]
        PB = np.asarray(rb.points, float)
        new_pts = None
        for ai in satin:
            if ai >= bi or out[ai].shape_id != rb.shape_id:
                continue
            PA = np.asarray(out[ai].points, float)
            found = _partners(PB, PA)
            # a partner counts only where the earlier bar's stitches can come out (a lap of 3
            # or more consecutive ones): a widened stitch over a kept one would pile thread
            ids_all = sorted({v[0] for v in found.values()})
            runs_ok: set[int] = set()
            g: list[int] = []
            for i in ids_all + [None]:
                if g and (i is None or i - g[-1] > 1):
                    if len(g) >= 3:
                        runs_ok.update(g)
                    g = []
                if i is not None:
                    g.append(i)
            found = {j: v for j, v in found.items() if v[0] in runs_ok}
            if len(found) < MIN_STITCHES:
                continue
            a_hits: list[int] = []
            moved = False
            for (j0, j1) in _stretches(list(found)):
                if j1 - j0 + 1 < MIN_STITCHES:
                    continue
                if new_pts is None:
                    new_pts = PB.copy()
                _, uB, _ = _mid_dir(PB)
                # `short_ramp` (`cfg.extra["satin_junction_block"] == "short"`): a short stretch ramps
                # over a third of its length, so MFab's F4 block (about 20 stitches) merges. It
                # piles 3-deep thread +0.08 at F4 (0.51 against OFF 0.43), so it is not the default.
                ramp = min(JUNCTION_RAMP, max(2, (j1 - j0 + 1) // 3)) if short_ramp else JUNCTION_RAMP
                full_pts: set[int] = set()
                for k in range(j0, j1 + 2):
                    j = min(k, j1)
                    if j not in found:
                        continue
                    _, lo, hi = found[j]
                    u = uB[j]
                    mid_b = (PB[j] + PB[j + 1]) / 2.0
                    t_k = float((PB[k] - mid_b) @ u)
                    target = lo if k == j else hi
                    w = min(1.0, (k - j0 + 1) / ramp, (j1 + 2 - k) / ramp)
                    cand = PB[k] + u * (target - t_k) * w
                    if reach is not None and not reach.covers(Point(float(cand[0]), float(cand[1]))):
                        continue            # past the artwork's edge: the stitch stays as it was
                    new_pts[k] = cand
                    if abs(target - t_k) * (1.0 - w) <= MISS_MM:
                        full_pts.add(k)
                # only the earlier bar's partners of stitches that reach (nearly) the whole union
                # go: a partner removed under a half-widened stitch would leave the thread bare
                ids = sorted({found[j][0] for j in range(j0, j1 + 1)
                              if j in found and j in full_pts and j + 1 in full_pts})
                if not ids:
                    new_pts[j0:j1 + 2] = PB[j0:j1 + 2]
                    continue
                g0 = prev = ids[0]
                for i in ids[1:] + [None]:
                    if i is None or i - prev > 1:
                        a_hits.append((g0, prev))
                        g0 = i
                    prev = i
                moved = True
                n_merged += j1 - j0 + 1
            if moved:
                # earlier bar's stretch -> running path through its midpoints
                P = list(map(tuple, PA))
                cut = sorted(a_hits, reverse=True)
                for (i0, i1) in cut:
                    if i1 - i0 + 1 < 3:
                        continue
                    mids = [((P[m][0] + P[m + 1][0]) / 2.0, (P[m][1] + P[m + 1][1]) / 2.0)
                            for m in range(i0, i1 + 1)]
                    P = P[:i0 + 1] + _thin(mids, JUNCTION_STEP_MM) + P[i1 + 1:]
                out[ai] = dataclasses.replace(out[ai], points=P)
        if new_pts is not None:
            out[bi] = dataclasses.replace(rb, points=[tuple(map(float, q)) for q in new_pts])
    return out, n_merged
