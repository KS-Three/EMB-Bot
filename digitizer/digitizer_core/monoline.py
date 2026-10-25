"""A monoline script stroke sews satin, never fill (`cfg.monoline_script_satin`,
built OFF 2026-10-24, L7).

THE PRO'S RULE. A script word written with one pen width -- Tires' joined
"ires", 919 mm², ribbon width 4.5 mm -- is satin columns end to end, even
where its joins and ball terminals widen past the 5 mm satin ceiling: 8.9 %
of his crosses there run over 5 mm (p90 4.93, max 6.79, `TIRES HAT 3D.DST`
read by `tools/script_census.py`). The classifier refuses that word on
`dt_p90_cap` alone (doubled-DT p90 5.37-5.43 mm against 5.0) and it sews a
45-degree tatami instead: 2,515 stitches under 1 mm where he has 43, and no
cross square to the stroke where 85 % of his are.

WHAT A MONOLINE IS. A shape the satin classifier refused ONLY at its p90
width -- ribbon width under the ceiling, the radii regular, aspect passed --
whose width is near-constant (`dt_cv` <= MONOLINE_CV_MAX) along a long stroke
(`elongation` >= MONOLINE_ELONGATION_MIN). Across the 21 pro-paired jobs
(L9's cache, 2026-10-24) the shapes refused on `dt_p90_cap` that are not
already text read: Tires' "ires" dt_cv 0.149 / elongation 42.4 (pro SATIN);
Golden Tee's two 0.40-0.43 / 12-21 and MFab's two 0.39-0.41 / 4.2 (pro FILL
all four). Every text member refused there reads 0.29-0.47 -- the lettering
split already takes those. One supporting row and four contradicting rows
the threshold leaves alone; read it as that, not as a rate.

WHAT IT DOES. `stage7_sequence._satin_ceiling_for` gives such a shape the
lettering split's own answer -- no width ceiling, the per-stroke rung and
the fold guard on -- so it reaches the satin tier and sews split where a
cross runs over the ceiling, exactly as a text-cluster member does under
`satin_lettering_split`. Nothing else moves.
"""
from __future__ import annotations

from functools import lru_cache

MONOLINE_CV_MAX = 0.25
MONOLINE_ELONGATION_MIN = 20.0


@lru_cache(maxsize=4096)
def _verdict(wkb: bytes, satin_max_mm: float, area_weighted: bool) -> bool:
    from shapely import wkb as _wkb
    from .stage6_satin import classify_ribbon
    v = classify_ribbon(_wkb.loads(wkb), satin_max_mm, area_weighted=area_weighted)
    m = v.metrics
    return (v.reason == "dt_p90_cap"
            and m["dt_cv"] <= MONOLINE_CV_MAX
            and m["elongation"] >= MONOLINE_ELONGATION_MIN)


def monoline_stroke(region, cfg, satin_max_mm: float) -> bool:
    """Is `region` a monoline script stroke the width ceiling alone refuses?"""
    return _verdict(region.polygon.wkb, float(satin_max_mm),
                    bool(getattr(cfg, "classify_area_weighted", False)))


# --------------------------------------------------------------- the travel
#: raster pitch the hidden route is found on, px per mm
BURY_PX_PER_MM = 10.0
#: one satin cross's footprint on that raster: the thread, plus the pitch
#: gap to its neighbour, so a column reads as one solid band
BURY_THREAD_MM = 0.5
#: how much of a route may sit outside the thread still to come -- the lead
#: out of the column just finished and into the next, never more
BURY_EXPOSED_MAX_MM = 1.0


class _SatinRaster:
    """Where this word's satin lies, by sewing order: per pixel the FIRST and
    LAST satin run covering it (indices into `runs`; none: 10**9 / -1)."""

    def __init__(self, runs: list):
        import numpy as np
        from skimage.draw import line as _line
        from skimage.morphology import dilation, disk

        from . import stitches

        pts = np.array([p for r in runs for p in r.points], float)
        self.x0, self.y0 = pts.min(0) - 2.0
        x1, y1 = pts.max(0) + 2.0
        R = BURY_PX_PER_MM
        self.W, self.H = int((x1 - self.x0) * R) + 1, int((y1 - self.y0) * R) + 1
        self.first = np.full((self.H, self.W), 10 ** 9, np.int64)
        self.last = np.full((self.H, self.W), -1, np.int64)
        foot = disk(max(1, int(round(BURY_THREAD_MM * R / 2))))
        for k, r in enumerate(runs):
            if r.kind != stitches.SATIN or len(r.points) < 2:
                continue
            m = np.zeros((self.H, self.W), bool)
            for a, b in zip(r.points, r.points[1:]):
                rr, cc = _line(*self.ij(a), *self.ij(b))
                m[rr, cc] = True
            m = dilation(m, foot)
            self.first[m] = np.minimum(self.first[m], k)
            self.last[m] = k

    def ij(self, p) -> tuple[int, int]:
        R = BURY_PX_PER_MM
        return (min(self.H - 1, max(0, int(round((p[1] - self.y0) * R)))),
                min(self.W - 1, max(0, int(round((p[0] - self.x0) * R)))))

    def xy(self, u) -> tuple[float, float]:
        return (self.x0 + u[1] / BURY_PX_PER_MM, self.y0 + u[0] / BURY_PX_PER_MM)

    def on_finished(self, a, b, k: int) -> bool:
        """Does the stitch a -> b of run `k` lie on satin already sewn, under
        none still to come (two of its three quarter points)?"""
        hits = 0
        for f in (0.25, 0.5, 0.75):
            u = self.ij((a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f))
            hits += bool(self.first[u] < k and self.last[u] < k)
        return hits >= 2


def clear_finished_underlay(runs: list, trim_at_mm: float) -> int:
    """Cut a monoline word's underlay back off the satin it already sewed;
    -> how many stitches went.

    The satin tier starts a stroke's underlay at its junction end, and in a
    joined script word that end lies inside the column sewn just before:
    Tires' "ires" laid 56 mm of underlay ON TOP of finished satin, at the
    i/r, r/e and e/s joins and the e's crown (the stray stitch at the e).
    It supports nothing there and it shows. Every stitch at the HEAD or TAIL
    of an underlay run that lies on finished satin and under none still to
    come goes; a run left with no stitch goes whole. Where a run's start
    moved, its link is re-decided as the linking pass decides one -- sewn
    needle-down within `trim_at_mm`, a cut past it -- for `bury_hops` to
    hide or keep.
    """
    import math

    from . import stitches

    if not any(r.kind == stitches.SATIN for r in runs):
        return 0
    ras = _SatinRaster(runs)
    gone = 0
    moved: set[int] = set()
    for k, r in enumerate(runs):
        if r.kind != stitches.UNDERLAY or len(r.points) < 2:
            continue
        pts = list(r.points)
        n0 = len(pts)
        while len(pts) >= 2 and ras.on_finished(pts[0], pts[1], k):
            pts.pop(0)
        if len(pts) != n0:
            moved.add(k)
        while len(pts) >= 2 and ras.on_finished(pts[-2], pts[-1], k):
            pts.pop()
        gone += n0 - len(pts)
        r.points = pts if len(pts) >= 2 else []
    if not gone:
        return 0
    keep = []
    for k, r in enumerate(runs):
        if not r.points:
            moved.add(k + 1)         # the run after an emptied one starts a new link
            continue
        if k in moved and keep:
            d = math.dist(keep[-1].points[-1], r.points[0])
            r.jump = r.trim = d > trim_at_mm      # under it, sewn as one stitch
        keep.append(r)
    runs[:] = keep
    return gone


def bury_hops(runs: list, trim_at_mm: float) -> int:
    """THE PRO'S TRAVEL. Sew a monoline script word's cuts as travel hidden
    under its own columns still to come; -> how many cuts it took.

    Tires' joined "ires" (`TIRES HAT 3D.DST`, read 2026-10-24): his word is 5
    needle-down runs with 3 cuts, and every millimetre of the travel inside
    it -- 490 mm, stitches under 3 mm between short neighbours -- lies under
    thread he sews later (100 %). The satin tier sewed the same word as 21
    runs and 20 cuts: its walk between strokes refuses a sewn spine and its
    hops from an underlay to its column read past `trim_at`, so every move
    the skeleton did not hand it whole became a cut.

    For each run marked `jump`, route from where the needle is to where the
    run starts THROUGH the footprint of this word's satin columns still to
    be sewn (that run's and every later one's, rasterised at BURY_PX_PER_MM,
    each cross BURY_THREAD_MM wide), shortest path. Take it when no more
    than BURY_EXPOSED_MAX_MM of it lies outside that footprint and it is no
    longer than the satin walk's own cap (`max(20, 4 x direct)` mm); sew it
    as a TRAVEL run and clear the jump. Otherwise the cut stays: a route on
    top of finished satin shows, and one across bare cloth is a float.
    """
    import math

    import numpy as np
    from shapely.geometry import LineString
    from skimage.graph import route_through_array

    from . import machine, stitches
    from .stage6_satin import _resample

    cuts = [i for i, r in enumerate(runs) if i > 0 and r.jump and r.points
            and runs[i - 1].points]
    if not cuts or not any(r.kind == stitches.SATIN for r in runs):
        return 0
    ras = _SatinRaster(runs)
    took = 0
    for i0 in cuts:
        i = i0 + took               # each travel taken shifted the runs after it
        a, b = runs[i - 1].points[-1], runs[i].points[0]
        direct = math.dist(a, b)
        if direct < machine.TINY_STITCH_MM:
            continue
        later = ras.last >= i
        if not later.any():
            continue
        path, _c = route_through_array(np.where(later, 1.0, 1000.0), ras.ij(a), ras.ij(b),
                                       fully_connected=True, geometric=True)
        route = [ras.xy(u) for u in path]
        route[0], route[-1] = tuple(a), tuple(b)
        exposed = sum(math.dist(p, q) for (p, q), (u, v) in
                      zip(zip(route, route[1:]), zip(path, path[1:]))
                      if not (later[u] and later[v]))
        plen = sum(math.dist(p, q) for p, q in zip(route, route[1:]))
        if exposed > BURY_EXPOSED_MAX_MM or plen > max(20.0, 4.0 * direct):
            continue
        coarse = list(LineString(route).simplify(1.0 / BURY_PX_PER_MM).coords)
        n = max(2, int(math.ceil(plen / machine.TRAVEL_STITCH_MM)) + 1)
        runs.insert(i, stitches.StitchRun(points=_resample(coarse, n), kind=stitches.TRAVEL,
                                          shape_id=runs[i].shape_id))
        runs[i + 1].jump = runs[i + 1].trim = False
        ras.last[ras.last >= i] += 1        # the raster names runs by index
        ras.first[(ras.first >= i) & (ras.first < 10 ** 9)] += 1
        took += 1
    return took
