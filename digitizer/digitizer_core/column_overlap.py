"""`cfg.extra["satin_overlap_run"]` (built OFF 2026-11-19, MFab top line).

The Column lane sews a letter's columns one walk (component) at a time, and two
walks can cover the SAME stretch of one stroke: MFab's F diagonal is sewn by the
walk of the arm (run `S1a1cc475` 252 points) and again, 6.5 mm of it, by the walk of
the stem that follows (35 satin stitches inside the first walk's thread, 2026-11-19
prime-grader card `L_mfab_hat`, "doubled stitch blocks", pile 15 layers against 5 on
a clean stem). A satin stitch that lies wholly inside thread already laid adds
height and no cover.

`overlap_run`: in a satin run, a stretch of at least `MIN_STITCHES` consecutive
stitches each lying wholly inside the cover (half a laid thread, `HALF_MM`, the figure
`columns.satin_cover` already reads) of the lane's earlier SATIN runs is replaced by a
running path through the stretch's midpoints, `columns._UNDERPATH_STEP_MM` apart, the
same thread on the same finished satin. Nothing is bare that was covered; the
stretch's two end points stay, so the needle path is unbroken. No satin floor, pull
or cover tolerance is read or changed.
"""
from __future__ import annotations

import dataclasses
import math

from shapely.geometry import LineString
from shapely.ops import unary_union

from . import stitches

HALF_MM = 0.2          # half a 0.4 mm laid thread (columns.satin_cover's default)
MIN_STITCHES = 8       # ~3 mm of a 0.4 mm pitch: a junction's short lap stays
STEP_MM = 2.0          # columns._UNDERPATH_STEP_MM


def _thin(mids: list[tuple[float, float]], step: float) -> list[tuple[float, float]]:
    out = [mids[0]]
    for q in mids[1:]:
        if math.dist(q, out[-1]) >= step:
            out.append(q)
    if out[-1] != mids[-1] and math.dist(mids[-1], out[-1]) > 1e-6:
        out.append(mids[-1])
    return out


def overlap_run(runs: list, min_stitches: int = MIN_STITCHES) -> tuple[list, int]:
    """`runs` with the satin stretches that LATER satin of the list covers turned
    to running stitch. -> (runs, points removed). The list is walked last run
    first and only satin that is still sewn counts as cover, so two stretches
    that lie on each other cannot both go; a run with no such stretch is the same
    object, a run with one is a copy."""
    pieces: list = []
    cover = None
    out = list(runs)
    for ri in range(len(runs) - 1, -1, -1):
        run = runs[ri]
        if run.kind != stitches.SATIN or len(run.points) < 2:
            continue
        P = run.points
        segs = [LineString([P[j], P[j + 1]]) for j in range(len(P) - 1)]
        if pieces:
            if cover is None:
                cover = unary_union(pieces).buffer(0)
            inside = [bool(cover.contains(s)) for s in segs]
        else:
            inside = [False] * len(segs)
        new: list = []
        kept = [True] * len(segs)
        j = 0
        while j < len(P):
            if j < len(segs) and inside[j]:
                k = j
                while k < len(segs) and inside[k]:
                    k += 1
                # stitches j..k-1 lie under later satin; their points are P[j]..P[k]
                if k - j >= min_stitches:
                    mids = [((P[m][0] + P[m + 1][0]) / 2.0, (P[m][1] + P[m + 1][1]) / 2.0)
                            for m in range(j, k)]
                    new.append(P[j])
                    new.extend(_thin(mids, STEP_MM))
                    new.append(P[k])
                    for m in range(j, k):
                        kept[m] = False
                    j = k + 1
                    continue
            new.append(P[j])
            j += 1
        if len(new) != len(P) or any(not k_ for k_ in kept):
            out[ri] = dataclasses.replace(run, points=new)
        pieces += [s_.buffer(HALF_MM) for s_, k_ in zip(segs, kept) if k_]
        cover = None
    return out, sum(len(a.points) - len(b.points) for a, b in zip(runs, out))
