"""Outline-cut: a letter polygon -> stroke pieces whose rails are the outline.

The construction every commercial letter builder uses (Wilcom's turning
satin, Ink/Stitch's fill-to-satin, the expired Viking US6934599 and Soft
Sight US6804573 families; survey in
`docs/lettering-architecture-rd-2026-10-07.md` §4): the letter's outline is
cut into stroke pieces at its concave corners, and each piece's two rails
are stretches of the OUTLINE itself. The skeleton is consulted only to find
a piece's ends and to say whether it bends; it never positions a rail.
That is the opposite of `stage6_satin`, whose rails are normals cast from a
smoothed skeleton, and it is why one letter sews there as several slabs at
unrelated angles (the "patchwork" of the R&D report §2) and here as one
column per stroke.

Ported from the spike `digitizer/tools/outline_cut_spike/oc.py` (lane
`claude/outline-cut-columns`, 2026-10-05/06, 18 passes plus the second
look), with ONE change of output: a piece is returned as a `Column` of
STATIONS (rail-to-rail crosses, `columns.Column`) rather than as stitches,
so the construction engine (`columns.column_runs`) owns pull compensation,
split satin, underlay and order -- the rules a typed glyph already gets.
The cut rules, thresholds and pairing are the spike's, unchanged; every
threshold was set on Becker MAR and Gaulke INDUSTRIES and is named where
it is used. The second-look refinement (`_refine`) is kept.

Nothing here reads a config; `cfg.lettering_columns` (stage 7) decides
whether a text-tagged shape comes this way at all.
"""
from __future__ import annotations

import math
from collections import deque

import cv2
import numpy as np
from shapely.geometry import LinearRing, LineString, Point, Polygon
from shapely.ops import nearest_points, polygonize, unary_union
from skimage.morphology import medial_axis

from .columns import Column

SIMPLIFY_MM = 0.12       # lumps under this (or W/16) are the trace, not the letter
REFLEX_DEG = 55.0        # concave turn that counts as a junction corner
CONVEX_DEG = 35.0        # convex turn that counts as a real corner
PX = 12                  # px/mm for the per-piece skeleton
_RAIL_STEP_MM = 0.08     # densification of an outline arc before pairing
_DTW_STEP_MM = 0.1       # resampling step of the two rails for the matching
REFINE_TRIGGER = 0.12    # share of thread in over-long crosses that says "two strokes"
REFINE_GAIN = 0.6        # a second-look cut must take that share to this fraction
REFINE_REFLEX_DEG = 30.0 # the second look reads softer concave corners than the junction rules


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 0.0)


def stroke_width(poly: Polygon) -> float:
    """2A/P: the mean stroke width of a ribbon-like shape."""
    return 2.0 * poly.area / max(poly.length, 1e-9)


def _run_len(c, i, step):
    """Length of the straight run leaving vertex i in ring direction `step`."""
    n = len(c)
    p, q = c[i], c[(i + step) % n]
    d0 = _unit((q[0] - p[0], q[1] - p[1]))
    L, k = 0.0, i
    for _ in range(n):
        p, q = c[k], c[(k + step) % n]
        dd = _unit((q[0] - p[0], q[1] - p[1]))
        if dd[0] * d0[0] + dd[1] * d0[1] < math.cos(math.radians(14)):
            break
        L += math.hypot(q[0] - p[0], q[1] - p[1])
        k = (k + step) % n
    return L


def corners(poly: Polygon, W: float, reflex_deg: float = REFLEX_DEG):
    """-> (reflex, convex) corner records: p, d_in, d_out, bis, turn, len_in,
    len_out. A corner is turn gathered over W/8 of outline, so a chamfered or
    two-vertex corner counts once and a curve's vertices do not."""
    reflex, convex = [], []
    half = 0.125 * W
    for ring in [poly.exterior] + list(poly.interiors):
        c = list(ring.coords)[:-1]
        n = len(c)
        if n < 3:
            continue
        seg = [_unit((c[(i + 1) % n][0] - c[i][0], c[(i + 1) % n][1] - c[i][1])) for i in range(n)]
        elen = [math.hypot(c[(i + 1) % n][0] - c[i][0], c[(i + 1) % n][1] - c[i][1]) for i in range(n)]
        turn = []
        for i in range(n):
            u, v = seg[i - 1], seg[i]
            turn.append(math.degrees(math.atan2(u[0] * v[1] - u[1] * v[0], u[0] * v[0] + u[1] * v[1])))
        for i in range(n):
            if abs(turn[i]) < 8:
                continue
            sg = 1 if turn[i] > 0 else -1
            lo, d = i, 0.0
            while d + elen[(lo - 1) % n] <= half and turn[(lo - 1) % n] * sg > 0 and (lo - 1) % n != i:
                d += elen[(lo - 1) % n]
                lo = (lo - 1) % n
            hi, d = i, 0.0
            while d + elen[hi] <= half and turn[(hi + 1) % n] * sg > 0 and (hi + 1) % n != i:
                d += elen[hi]
                hi = (hi + 1) % n
            idx, k = [lo], lo
            while k != hi:
                k = (k + 1) % n
                idx.append(k)
            tot = abs(sum(turn[j] for j in idx))
            if tot < min(reflex_deg, CONVEX_DEG):
                continue
            if max(idx, key=lambda j: (abs(turn[j]), -j)) != i:   # one corner per stretch: its sharpest vertex
                continue
            u, v = seg[(lo - 1) % n], seg[hi]
            wedge = _unit((v[0] - u[0], v[1] - u[1]))
            p = c[i]
            solid_in_wedge = poly.contains(Point(p[0] + wedge[0] * 0.05, p[1] + wedge[1] * 0.05))
            bis = wedge if solid_in_wedge else (-wedge[0], -wedge[1])
            rec = dict(p=p, d_in=u, d_out=v, bis=bis, turn=tot,
                       len_in=_run_len(c, lo, -1), len_out=_run_len(c, hi, 1))
            if solid_in_wedge:
                if tot >= CONVEX_DEG:
                    convex.append(rec)
            elif tot >= reflex_deg:
                reflex.append(rec)
    return reflex, convex


def _cluster(cs, r):
    """Corners closer than r are one corner: keep the sharpest."""
    out = []
    for c in sorted(cs, key=lambda c: -c["turn"]):
        if all(math.hypot(c["p"][0] - o["p"][0], c["p"][1] - o["p"][1]) > r for o in out):
            out.append(c)
    return out


def _inside(poly, a, b):
    seg = LineString([a, b])
    if seg.length < 1e-6:
        return False
    core = LineString([seg.interpolate(0.02, normalized=True).coords[0],
                       seg.interpolate(0.98, normalized=True).coords[0]])
    return poly.buffer(1e-6).contains(core)


def _ray_hit(poly, p, d, far, bis=None):
    """First boundary hit from p along d, past the start. An edge extension
    leaves a corner ALONG the outline, so the start is nudged into the solid."""
    q = (p[0] + d[0] * far, p[1] + d[1] * far)
    start = (p[0] + d[0] * 0.03, p[1] + d[1] * 0.03)
    if not poly.contains(Point(start)) and bis is not None:
        start = (start[0] + bis[0] * 0.04, start[1] + bis[1] * 0.04)
    if not poly.contains(Point(start)):
        return None
    hit = LineString([start, q]).intersection(poly.boundary)
    if hit.is_empty:
        return None
    pts = []
    for g in getattr(hit, "geoms", [hit]):
        pts.extend(g.coords)
    return min(pts, key=lambda t: math.hypot(t[0] - p[0], t[1] - p[1]))


def _snap(poly, q, r):
    best, bd = q, r
    for ring in [poly.exterior] + list(poly.interiors):
        for v in ring.coords:
            dd = math.hypot(v[0] - q[0], v[1] - q[1])
            if dd < bd:
                best, bd = v, dd
    return best


def find_cuts(poly: Polygon, W: float):
    """-> (cuts, reflex, convex). A cut is (p, q, rule, length) with rule in
    "through" (two concave corners joined along an edge at both ends: a
    stroke butting a through-stroke), "mitre" (a lone concave corner to the
    convex apex across it) or "ext" (the longer edge run on through)."""
    reflex, convex = corners(poly, W)
    reflex = _cluster(reflex, 0.25 * W)
    reflex = [r for r in reflex if max(r["len_in"], r["len_out"]) >= 0.25 * W]   # a dent is not a junction

    def dot(a, b):
        return a[0] * b[0] + a[1] * b[1]

    def neg(a):
        return (-a[0], -a[1])

    def ext(r):
        return [(r["d_in"], r["len_in"]), (neg(r["d_out"]), r["len_out"])]   # edge continued into the body

    cuts, used = [], set()
    pairs = []
    for i, r in enumerate(reflex):
        for j in range(i + 1, len(reflex)):
            o = reflex[j]
            p, q = r["p"], o["p"]
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L > 3.0 * W or L < 1e-6:
                continue
            d = _unit((q[0] - p[0], q[1] - p[1]))
            a1 = max(dot(d, e) for e, _ in ext(r))
            a2 = max(dot(neg(d), e) for e, _ in ext(o))
            if min(a1, a2) > 0.94 and _inside(poly, p, q):
                pairs.append((L, i, j))
    for L, i, j in sorted(pairs):
        if i in used or j in used:
            continue
        used |= {i, j}
        cuts.append((reflex[i]["p"], reflex[j]["p"], "through", L, 0))
    for i, r in enumerate(reflex):
        if i in used:
            continue
        p = r["p"]
        la, lb = r["len_in"], r["len_out"]
        mitres, elbow = [], False
        for o in convex:
            if o["turn"] < 45:      # the far side of an elbow is a real corner, not a vertex on a curve
                continue
            q = o["p"]
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L < 0.6 * W or L > 2.6 * W:
                continue
            al = dot(_unit((q[0] - p[0], q[1] - p[1])), r["bis"])
            if al > 0.6 and _inside(poly, p, q):
                elbow = True
                if al > 0.9 and L <= 1.8 * W:
                    mitres.append((L, q))
        mitres.sort()
        if not elbow:
            continue        # smooth on the far side: the stroke is bending here, not meeting another
        if mitres and max(la, lb) < 1.6 * min(la, lb):
            cuts.append((p, mitres[0][1], "mitre", mitres[0][0], 1))
            continue
        done = False
        for e, le in sorted(ext(r), key=lambda t: -t[1]):
            q = _ray_hit(poly, p, e, 3.2 * W, r["bis"])
            if q is None:
                continue
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L < 0.25 * W:
                continue        # ran straight into a whisker of the trace
            if L <= 1.5 * le:
                q = _snap(poly, q, 0.15 * W)
                cuts.append((p, q, "ext", math.hypot(q[0] - p[0], q[1] - p[1]), 1))
                done = True
                break
        if done:
            continue
        if mitres:
            cuts.append((p, mitres[0][1], "mitre", mitres[0][0], 1))
    cuts.sort(key=lambda t: (t[4], t[3]))
    kept = []
    for cu in cuts:
        seg = LineString([cu[0], cu[1]])
        if seg.length < 0.25 * W and cu[2] != "through":
            continue
        if any(seg.crosses(LineString([k[0], k[1]])) or seg.buffer(0.05).contains(LineString([k[0], k[1]]))
               or LineString([k[0], k[1]]).buffer(0.05).contains(seg) for k in kept):
            continue
        kept.append(cu)
    return [k[:4] for k in kept], reflex, convex


def split(poly: Polygon, cuts) -> list[Polygon]:
    """The polygon cut along `cuts` -> its pieces (scraps under 0.05 mm² dropped)."""
    verts = {(round(x, 6), round(y, 6)) for ring in [poly.exterior] + list(poly.interiors) for x, y in ring.coords}
    lines = [poly.exterior] + list(poly.interiors)
    for a, b, _, _ in cuts:
        d = _unit((b[0] - a[0], b[1] - a[1]))
        # an end on a vertex is already a node; an end from a ray hit needs a hair of overshoot to cross the ring
        ea = 0.0 if (round(a[0], 6), round(a[1], 6)) in verts else 0.01
        eb = 0.0 if (round(b[0], 6), round(b[1], 6)) in verts else 0.01
        lines.append(LineString([(a[0] - d[0] * ea, a[1] - d[1] * ea), (b[0] + d[0] * eb, b[1] + d[1] * eb)]))
    pieces = [g for g in polygonize(unary_union(lines)) if poly.buffer(1e-6).contains(g.representative_point())]
    return [g for g in pieces if g.area > 0.05]


def _spine_ends(piece: Polygon):
    """Longest skeleton path of the piece -> points (mm), or None."""
    x0, y0, x1, y1 = piece.bounds
    w, h = int((x1 - x0) * PX) + 5, int((y1 - y0) * PX) + 5
    m = np.zeros((h, w), np.uint8)

    def to_px(cs):
        return np.round([((x - x0) * PX + 2, (y - y0) * PX + 2) for x, y in cs]).astype(np.int32)

    cv2.fillPoly(m, [to_px(piece.exterior.coords)], 1)
    for r in piece.interiors:
        cv2.fillPoly(m, [to_px(r.coords)], 0)
    sk, dist = medial_axis(m.astype(bool), return_distance=True)
    ys, xs = np.nonzero(sk)
    if len(xs) < 2:
        return None
    S = set(zip(xs.tolist(), ys.tolist()))

    def bfs(s):
        seen = {s: None}
        dq = deque([s])
        last = s
        while dq:
            c = dq.popleft()
            last = c
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nb = (c[0] + dx, c[1] + dy)
                    if nb in S and nb not in seen:
                        seen[nb] = c
                        dq.append(nb)
        return last, seen

    a, _ = bfs(next(iter(S)))
    b, par = bfs(a)
    path = []
    c = b
    while c is not None:
        path.append(c)
        c = par[c]
    dv = np.array([dist[y, x] for x, y in path])
    keep = dv >= 0.75 * np.median(dv)
    idx = np.flatnonzero(keep)
    if len(idx) < 2:
        return None
    path = path[idx[0]:idx[-1] + 1]
    return [((x - 2) / PX + x0, (y - 2) / PX + y0) for x, y in path]


def _arc(ring_pts, i, j):
    n = len(ring_pts)
    out = [ring_pts[i]]
    k = i
    while k != j:
        k = (k + 1) % n
        out.append(ring_pts[k])
    return out


def ring_rails(piece: Polygon):
    """A piece that still wraps a counter (an O, an uncut bowl): outer ring
    against the counter's ring, both started at the thinnest place and walked
    the same way round."""
    hole = max(piece.interiors, key=lambda h: Polygon(h).area)
    ext = piece.exterior
    pe, ph = nearest_points(ext, hole)

    def walk(ring, start):
        ring = LinearRing(ring.coords)
        if not ring.is_ccw:
            ring = LinearRing(list(ring.coords)[::-1])
        t0 = ring.project(start)
        L = ring.length
        return [ring.interpolate((t0 + t) % L).coords[0] for t in np.arange(0, L, _RAIL_STEP_MM)]

    return walk(ext, pe), walk(hole, ph)


def rails(piece: Polygon, cut_lines, W: float):
    """-> (rail_a, rail_b) as dense point lists running the same way, or None.
    The piece's ends are where its spine leaves it; the two outline arcs
    between those exits are the rails, each trimmed of the cap it runs across
    and squared where the end is a free cap rather than a cut."""
    if len(piece.interiors) > 0:
        return ring_rails(piece)
    sp = _spine_ends(piece)
    if sp is None or len(sp) < 4:
        return None
    k = max(2, min(len(sp) // 3, int(PX * W * 0.5)))
    d0 = _unit((sp[0][0] - sp[k][0], sp[0][1] - sp[k][1]))
    d1 = _unit((sp[-1][0] - sp[-1 - k][0], sp[-1][1] - sp[-1 - k][1]))
    ring = piece.exterior
    dense = [ring.interpolate(t).coords[0] for t in np.arange(0, ring.length, _RAIL_STEP_MM)]

    def exit_idx(p, d):
        q = LineString([p, (p[0] + d[0] * 50, p[1] + d[1] * 50)]).intersection(ring)
        if q.is_empty:
            return None
        pts = []
        for g in getattr(q, "geoms", [q]):
            pts.extend(g.coords)
        e = min(pts, key=lambda t: math.hypot(t[0] - p[0], t[1] - p[1]))
        return int(np.argmin([math.hypot(x - e[0], y - e[1]) for x, y in dense])), e

    r0, r1 = exit_idx(sp[0], d0), exit_idx(sp[-1], d1)
    if r0 is None or r1 is None or r0[0] == r1[0]:
        return None
    (i0, e0), (i1, e1) = r0, r1
    A = _arc(dense, i0, i1)            # e0 -> e1
    B = _arc(dense, i1, i0)[::-1]      # e0 -> e1 the other way round

    def end_cut(e):
        for ln in cut_lines:
            if ln.distance(Point(e)) < 0.06:
                return ln
        return None

    c0, c1 = end_cut(e0), end_cut(e1)

    def trim(arc, d_start, cut, from_start):
        pts = arc if from_start else arc[::-1]
        i = 0
        lim = int(1.6 * W / _RAIL_STEP_MM)
        while i < len(pts) - 3 and i < lim:
            p, q = pts[i], pts[i + 1]
            if cut is not None:
                if cut.distance(Point(q)) < 0.04:
                    i += 1
                    continue
                break
            t = _unit((q[0] - p[0], q[1] - p[1]))
            if abs(t[0] * d_start[0] + t[1] * d_start[1]) < 0.6:   # still running across the end: a cap
                i += 1
                continue
            break
        pts = pts[i:]
        return pts if from_start else pts[::-1]

    A = trim(trim(A, d0, c0, True), d1, c1, False)
    B = trim(trim(B, d0, c0, True), d1, c1, False)

    def square(A, B, dvec, is_cut, from_start):
        if is_cut is not None:
            return A, B
        a = A if from_start else A[::-1]
        b = B if from_start else B[::-1]
        if len(a) < 3 or len(b) < 3:
            return A, B
        # dvec points out of the piece at this end; keep the rail that reaches less far, cut the other back to it

        def reach(p):
            return p[0] * dvec[0] + p[1] * dvec[1]

        lim = min(reach(a[0]), reach(b[0]))

        def back(r):
            i = 0
            while i < len(r) - 3 and reach(r[i]) > lim + 0.04:
                i += 1
            return r[i:]

        a, b = back(a), back(b)
        return (a, b) if from_start else (a[::-1], b[::-1])

    A, B = square(A, B, d0, c0, True)
    A, B = square(A, B, d1, c1, False)
    if len(A) < 3 or len(B) < 3:
        return None
    return A, B


def pair_rails(A, B, pitch_mm: float) -> list[tuple[tuple, tuple]]:
    """Rail to rail: the two outline arcs paired by the monotone matching that
    keeps every cross as short as it can be (dynamic time warping), so crosses
    stay square to the stroke, fan round a bend, and close into a mitred end,
    without any spine deciding the angle. A station is taken every `pitch_mm`
    of progress along whichever rail is moving -- round a bend that is the
    OUTER rail, so the outside stays covered and the inside takes the short
    crosses. -> [(pa, pb), ...]."""
    la, lb = LineString(A), LineString(B)
    step = _DTW_STEP_MM
    a = np.array([la.interpolate(t).coords[0] for t in np.arange(0, la.length + step, step)])
    b = np.array([lb.interpolate(t).coords[0] for t in np.arange(0, lb.length + step, step)])
    n, m = len(a), len(b)
    D = np.hypot(a[:, None, 0] - b[None, :, 0], a[:, None, 1] - b[None, :, 1])
    C = np.full((n, m), np.inf)
    C[0, 0] = D[0, 0]
    for j in range(1, m):
        C[0, j] = C[0, j - 1] + D[0, j]
    for i in range(1, n):
        C[i, 0] = C[i - 1, 0] + D[i, 0]
        row, prev = C[i], C[i - 1]
        for j in range(1, m):
            row[j] = D[i, j] + min(prev[j], prev[j - 1], row[j - 1])
    i, j, path = n - 1, m - 1, [(n - 1, m - 1)]
    while i > 0 or j > 0:
        if i == 0:
            j -= 1
        elif j == 0:
            i -= 1
        else:
            k = int(np.argmin((C[i - 1, j - 1], C[i - 1, j], C[i, j - 1])))
            if k == 0:
                i, j = i - 1, j - 1
            elif k == 1:
                i -= 1
            else:
                j -= 1
        path.append((i, j))
    path.reverse()
    out, since = [], pitch_mm
    for (i, j) in path:
        if since >= pitch_mm - 1e-9:
            out.append((tuple(a[i]), tuple(b[j])))
            since = 0.0
        since += step
    return out


def straight_axis(piece: Polygon, W: float, cut_lines=()):
    """Unit axis of a straight stroke piece, or None if it bends. The axis is
    the direction the piece's OWN outline runs (cut edges excluded), so a
    mitred diagonal reads along its sides, not along its cuts."""
    cs = list(piece.exterior.coords)
    C = S = tot = 0.0
    for p, q in zip(cs[:-1], cs[1:]):
        L = math.hypot(q[0] - p[0], q[1] - p[1])
        if L < 1e-6:
            continue
        mid = Point((p[0] + q[0]) / 2, (p[1] + q[1]) / 2)
        if any(ln.distance(mid) < 0.03 for ln in cut_lines):
            continue
        th = 2 * math.atan2(q[1] - p[1], q[0] - p[0])
        C += L * math.cos(th)
        S += L * math.sin(th)
        tot += L
    u = None
    if tot > 1e-6 and math.hypot(C, S) / tot >= 0.55:
        th = math.atan2(S, C) / 2
        u = np.array([math.cos(th), math.sin(th)])
    else:
        # caps and a serif can outweigh a short stem's sides: fall back to the spine's chord
        sp = _spine_ends(piece)
        if sp is None or len(sp) < 4:
            return None
        Q = np.array(sp)
        chord = Q[-1] - Q[0]
        Lc = float(np.hypot(*chord))
        if Lc < 1e-6:
            return None
        u = chord / Lc
        if np.abs((Q - Q[0]) @ np.array([-u[1], u[0]])).max() > max(0.12 * Lc, 0.2 * W):
            return None
    # along that axis the piece must be a stroke, not a slab: longer than it is wide
    P = np.array(cs)
    ext_u = np.ptp(P @ u)
    ext_n = np.ptp(P @ np.array([-u[1], u[0]]))
    if ext_u < 0.8 * ext_n:
        return None
    for snap in ((1.0, 0.0), (0.0, 1.0)):                # a stem that is nearly upright is upright
        if abs(u[0] * snap[0] + u[1] * snap[1]) > math.cos(math.radians(7)):
            u = np.array(snap)
    return (float(u[0]), float(u[1]))


def scan_stations(piece: Polygon, u, pitch_mm: float) -> list[tuple[tuple, tuple]] | None:
    """Crosses square to axis u, each end ON the piece's outline, one every
    `pitch_mm` along the axis. -> [(pa, pb), ...] or None."""
    n = (-u[1], u[0])
    cs = np.array(piece.exterior.coords)
    t = cs @ np.array(u)
    out = []
    for tt in np.arange(t.min() + pitch_mm / 2, t.max(), pitch_mm):
        o = (u[0] * tt, u[1] * tt)
        hit = LineString([(o[0] - n[0] * 200, o[1] - n[1] * 200),
                          (o[0] + n[0] * 200, o[1] + n[1] * 200)]).intersection(piece)
        segs = [g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "LineString" and g.length > 0.05]
        if not segs:
            continue
        g = max(segs, key=lambda g: g.length)
        p, q = g.coords[0], g.coords[-1]
        if (p[0] * n[0] + p[1] * n[1]) > (q[0] * n[0] + q[1] * n[1]):
            p, q = q, p
        out.append((tuple(p), tuple(q)))
    return out if len(out) >= 3 else None


def _straight_rails(piece: Polygon, u):
    """The two outline sides of a straight piece, split at its extreme points
    along u, both running +u. Kept on the Column so a consumer that wants
    the rails (the sewn-width preview, a later per-rail rule) has them."""
    cs = list(piece.exterior.coords)[:-1]
    t = [p[0] * u[0] + p[1] * u[1] for p in cs]
    i0, i1 = int(np.argmin(t)), int(np.argmax(t))
    if i0 == i1:
        return None
    a = _arc(cs, i0, i1)
    b = _arc(cs, i1, i0)[::-1]
    n = (-u[1], u[0])

    def side(r):
        return sum(p[0] * n[0] + p[1] * n[1] for p in r) / len(r)

    return (a, b) if side(a) <= side(b) else (b, a)


def build_column(piece: Polygon, cut_lines, W: float, pitch_mm: float) -> Column | None:
    """One piece -> its Column, or None when neither construction fits it."""
    if not piece.interiors:
        u = straight_axis(piece, W, cut_lines)
        if u is not None:
            st = scan_stations(piece, u, pitch_mm)
            if st:
                rr = _straight_rails(piece, u)
                return Column(stations=st, piece=piece, kind="straight", axis=u,
                              width_mm=W, rail_a=rr[0] if rr else [], rail_b=rr[1] if rr else [])
    r = rails(piece, cut_lines, W)
    if r is None:
        return None
    st = pair_rails(r[0], r[1], pitch_mm)
    if len(st) < 3:
        return None
    return Column(stations=st, piece=piece, kind="ring" if piece.interiors else "curved",
                  axis=None, width_mm=W, rail_a=list(r[0]), rail_b=list(r[1]))


def _overlong(col: Column | None, W: float):
    """-> (cross length in crosses far longer than the stroke is wide, total).
    A piece that is one stroke has none; a piece that is still two strokes
    sews across both, and that is how it shows."""
    if col is None or not col.stations:
        return 0.0, 0.0
    thr = 1.6 * W
    L = np.array([math.dist(a, b) for a, b in col.stations])
    return float(L[L > thr].sum()), float(L.sum())


def _refine(pc: Polygon, cut_lines, W: float, pitch_mm: float, depth: int):
    """Yield (piece, cut lines, new cuts). The junction rules missed a cut
    wherever a piece still sews over-long; look again at that piece's own
    concave corners and keep the one cut that most reduces it."""
    long0, tot0 = _overlong(build_column(pc, cut_lines, W, pitch_mm), W)
    if depth >= 3 or tot0 <= 0 or long0 / tot0 < REFINE_TRIGGER:
        yield pc, cut_lines, []
        return
    # Softer corners than the junction rules read (REFLEX_DEG): a low-res
    # E's slots round off under 55 deg and the body sewed as one fan (Becker
    # at 146 px: one corner at 55, four at 35). The piece has already
    # proven itself over-long, so a soft corner here is a junction, not a
    # bend -- and the cut still has to earn REFINE_GAIN.
    rf, _ = corners(pc, W, reflex_deg=REFINE_REFLEX_DEG)
    best = None
    for r in _cluster(rf, 0.25 * W):
        p = r["p"]
        for dvec in (r["d_in"], (-r["d_out"][0], -r["d_out"][1]), r["bis"]):
            q = _ray_hit(pc, p, dvec, 2.4 * W, r["bis"])
            if q is None:
                continue
            L = math.hypot(q[0] - p[0], q[1] - p[1])
            if L < 0.25 * W:
                continue
            cut = (p, q, "again", L)
            subs = split(pc, [cut])
            if len(subs) < 2 or min(g.area for g in subs) < 0.4 * W * W:
                continue
            lines = cut_lines + [LineString([p, q])]
            score = sum(_overlong(build_column(g, lines, W, pitch_mm), W)[0] for g in subs)
            if best is None or score < best[0]:
                best = (score, cut, subs, lines)
    if best is None or best[0] > REFINE_GAIN * long0:
        yield pc, cut_lines, []
        return
    first = True
    for g in best[2]:
        for sub, lines, extra in _refine(g, best[3], W, pitch_mm, depth + 1):
            yield sub, lines, ([best[1]] if first else []) + extra
            first = False


class LetterCut:
    """What `letter_columns` returns: the cleaned polygon, its stroke width,
    the cuts taken, and the Columns (one per piece the construction could
    sew; `unsewn` holds the pieces it could not)."""

    def __init__(self, poly, W, cuts, columns, unsewn):
        self.poly = poly
        self.W = W
        self.cuts = cuts
        self.columns = columns
        self.unsewn = unsewn


def letter_columns(poly: Polygon, pitch_mm: float = 0.2) -> LetterCut:
    """A letter polygon -> its stroke Columns. `pitch_mm` is the progress
    between consecutive stations along the moving rail -- the satin spacing
    itself (`machine.SATIN_SPACING_MM`): a station is one cross, and the
    crosses sit `pitch_mm` apart whichever rail each starts from."""
    W = stroke_width(poly)
    # a pinhole is the trace, not a counter
    poly = Polygon(poly.exterior, [h for h in poly.interiors if Polygon(h).area > 0.05 * W * W])
    # lumps under a sixteenth of the stroke are the trace, not the letter
    poly = poly.simplify(max(SIMPLIFY_MM, W / 16.0), preserve_topology=True)
    if poly.is_empty or poly.geom_type != "Polygon":
        return LetterCut(poly, W, [], [], [])
    W = stroke_width(poly)
    cuts, _reflex, _convex = find_cuts(poly, W)
    pieces = split(poly, cuts)
    # a cut that only shaves off a scrap is not a junction: take it back out
    while cuts:
        small = [g for g in pieces if g.area < 0.4 * W * W]
        if not small:
            break
        pc = min(small, key=lambda g: g.area)
        near = [k for k in cuts if LineString([k[0], k[1]]).intersection(pc.buffer(0.02)).length > 0.5 * k[3]]
        if not near:
            break
        cuts.remove(max(near, key=lambda k: k[3]))
        pieces = split(poly, cuts)
    cut_lines = [LineString([a, b]) for a, b, _, _ in cuts]
    columns, unsewn = [], []
    for pc in pieces:
        for sub, lines, extra in _refine(pc, cut_lines, W, pitch_mm, 0):
            cuts = cuts + extra
            col = build_column(sub, lines, W, pitch_mm)
            if col is None:
                unsewn.append(sub)
            else:
                columns.append(col)
    return LetterCut(poly, W, cuts, columns, unsewn)
