"""Spike: outline-cut columns. Cut a letter polygon at its concave corners,
take each piece's rails from the outline itself, sew rail to rail.
Self-contained on purpose: nothing here is wired into the pipeline."""
import math
from collections import deque
import numpy as np, cv2
from shapely.geometry import LineString, Polygon, Point, MultiPolygon
from shapely.ops import polygonize, unary_union
from skimage.morphology import medial_axis

SIMPLIFY_MM = 0.12
REFLEX_DEG = 55.0       # concave turn that counts as a corner
CONVEX_DEG = 35.0
CUT_MAX_W = 1.45         # cut no longer than this many stroke widths
PITCH_MM = 0.20
PX = 12                 # px/mm for the per-piece skeleton


def _unit(v):
    n = math.hypot(*v)
    return (v[0] / n, v[1] / n) if n > 1e-9 else (0.0, 0.0)


def stroke_width(poly):
    return 2.0 * poly.area / max(poly.length, 1e-9)


def _run_len(c, i, step):
    """length of the straight run leaving vertex i in ring direction `step`."""
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


def corners(poly, W):
    """-> (reflex, convex): dict(p, d_in, d_out, bis, turn, len_in, len_out).
    A corner is turn gathered over a short stretch of outline, so a chamfered
    or two-vertex corner counts as one and a curve's vertices do not."""
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
                d += elen[(lo - 1) % n]; lo = (lo - 1) % n
            hi, d = i, 0.0
            while d + elen[hi] <= half and turn[(hi + 1) % n] * sg > 0 and (hi + 1) % n != i:
                d += elen[hi]; hi = (hi + 1) % n
            idx, k = [lo], lo
            while k != hi:
                k = (k + 1) % n; idx.append(k)
            tot = abs(sum(turn[j] for j in idx))
            if tot < min(REFLEX_DEG, CONVEX_DEG):
                continue
            if max(idx, key=lambda j: (abs(turn[j]), -j)) != i:      # one corner per stretch: its sharpest vertex
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
            elif tot >= REFLEX_DEG:
                reflex.append(rec)
    return reflex, convex


def _cluster(cs, r):
    """corners closer than r are one corner: keep the sharpest."""
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
    """first boundary hit from p along d, past the start. An edge extension
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


def find_cuts(poly, W):
    reflex, convex = corners(poly, W)
    reflex = _cluster(reflex, 0.25 * W)
    reflex = [r for r in reflex if max(r["len_in"], r["len_out"]) >= 0.25 * W]   # a dent is not a junction
    dot = lambda a, b: a[0] * b[0] + a[1] * b[1]
    neg = lambda a: (-a[0], -a[1])
    ext = lambda r: [(r["d_in"], r["len_in"]), (neg(r["d_out"]), r["len_out"])]   # edge continued into the body
    cuts, used = [], set()
    # 1. two concave corners joined along an edge at BOTH ends: a stroke butting a through-stroke
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
    # 2. the rest: mitre a symmetric apex, else run the longer edge on through
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


def split(poly, cuts):
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


def _spine_ends(piece):
    """longest skeleton path of the piece -> (points mm) or None."""
    x0, y0, x1, y1 = piece.bounds
    w, h = int((x1 - x0) * PX) + 5, int((y1 - y0) * PX) + 5
    m = np.zeros((h, w), np.uint8)
    to_px = lambda cs: np.round([((x - x0) * PX + 2, (y - y0) * PX + 2) for x, y in cs]).astype(np.int32)
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
    pts = [((x - 2) / PX + x0, (y - 2) / PX + y0) for x, y in path]
    return pts


def _arc(ring_pts, i, j):
    n = len(ring_pts)
    out = [ring_pts[i]]
    k = i
    while k != j:
        k = (k + 1) % n
        out.append(ring_pts[k])
    return out


def ring_rails(piece):
    """a piece that still wraps a counter (an O, an uncut bowl): outer ring
    against the counter's ring, both started at the thinnest place and walked
    the same way round."""
    from shapely.ops import nearest_points
    from shapely.geometry import LinearRing
    hole = max(piece.interiors, key=lambda h: Polygon(h).area)
    ext = piece.exterior
    pe, ph = nearest_points(ext, hole)
    def walk(ring, start):
        ring = LinearRing(ring.coords)
        if not ring.is_ccw:
            ring = LinearRing(list(ring.coords)[::-1])
        t0 = ring.project(start)
        L = ring.length
        return [ring.interpolate((t0 + t) % L).coords[0] for t in np.arange(0, L, 0.08)]
    return walk(ext, pe), walk(hole, ph)


def rails(piece, cut_lines, W):
    """-> (rail_a, rail_b) as dense point lists running the same way, or None."""
    if len(piece.interiors) > 0:
        return ring_rails(piece)
    sp = _spine_ends(piece)
    if sp is None or len(sp) < 4:
        return None
    k = max(2, min(len(sp) // 3, int(PX * W * 0.5)))
    d0 = _unit((sp[0][0] - sp[k][0], sp[0][1] - sp[k][1]))
    d1 = _unit((sp[-1][0] - sp[-1 - k][0], sp[-1][1] - sp[-1 - k][1]))
    ring = piece.exterior
    dense = [ring.interpolate(t).coords[0] for t in np.arange(0, ring.length, 0.08)]
    n = len(dense)

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
        lim = int(1.6 * W / 0.08)
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
        reach = lambda p: p[0] * dvec[0] + p[1] * dvec[1]
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


def _resample(pts, n):
    ln = LineString(pts)
    return [ln.interpolate(t, normalized=True).coords[0] for t in np.linspace(0, 1, n)]


def zigzag(A, B):
    """sew rail to rail. The two outline arcs are paired by the monotone
    matching that keeps every stitch as short as it can be (dynamic time
    warping), so stitches stay square to the stroke, fan round a bend, and
    close into a mitred end, without any spine deciding the angle."""
    la, lb = LineString(A), LineString(B)
    step = 0.1
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
    # pitch is kept on whichever rail is moving: round a bend that is the OUTER
    # rail, so the outside stays covered and the inside takes the short stitches
    out, since, k = [], PITCH_MM, 0
    for (i, j) in path:
        if since >= PITCH_MM - 1e-9:
            out.append(tuple(a[i]) if k % 2 == 0 else tuple(b[j]))
            since = 0.0
            k += 1
        since += step
    return out


def straight_axis(piece, W, cut_lines=()):
    """unit axis of a straight stroke piece, or None if it bends. The axis is
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
        C += L * math.cos(th); S += L * math.sin(th); tot += L
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


def scan_column(piece, u):
    """stitches square to axis u, each end ON the piece's outline."""
    n = (-u[1], u[0])
    cs = np.array(piece.exterior.coords)
    t = cs @ np.array(u)
    out, k = [], 0
    for tt in np.arange(t.min() + PITCH_MM / 2, t.max(), PITCH_MM):
        o = (u[0] * tt, u[1] * tt)
        hit = LineString([(o[0] - n[0] * 200, o[1] - n[1] * 200), (o[0] + n[0] * 200, o[1] + n[1] * 200)]).intersection(piece)
        segs = [g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "LineString" and g.length > 0.05]
        if not segs:
            continue
        g = max(segs, key=lambda g: g.length)
        p, q = g.coords[0], g.coords[-1]
        if (p[0] * n[0] + p[1] * n[1]) > (q[0] * n[0] + q[1] * n[1]):
            p, q = q, p
        out.append(p if k % 2 == 0 else q)
        k += 1
    return out if len(out) >= 3 else None


def spine_column(piece, W):
    """a bending stroke: stations along its smoothed spine, each stitch square
    to the spine there, each end ON the piece's outline."""
    sp = _spine_ends(piece)
    if sp is None or len(sp) < 6:
        return None
    ln = LineString(sp)
    if ln.length < 0.8 * W:
        return None
    P = np.array([ln.interpolate(t).coords[0] for t in np.arange(0, ln.length, 0.1)])
    k = max(3, int(W / 0.1) | 1)                       # smooth over about a stroke width
    if len(P) > k + 2:
        pad = np.vstack([np.repeat(P[:1], k // 2, 0), P, np.repeat(P[-1:], k // 2, 0)])
        ker = np.ones(k) / k
        P = np.column_stack([np.convolve(pad[:, 0], ker, "valid"), np.convolve(pad[:, 1], ker, "valid")])
    m = min(len(P) - 1, max(2, int(0.5 * W / 0.1)))
    d0 = P[0] - P[m]; d0 /= max(np.hypot(*d0), 1e-9)
    d1 = P[-1] - P[-1 - m]; d1 /= max(np.hypot(*d1), 1e-9)
    ext = np.arange(0.1, 2.0 * W, 0.1)[:, None]
    P = np.vstack([(P[0] + ext * d0)[::-1], P, P[-1] + ext * d1])
    core = LineString(P)
    out, k2 = [], 0
    for t in np.arange(0, core.length, PITCH_MM):
        c = np.array(core.interpolate(t).coords[0])
        a = np.array(core.interpolate(max(t - 0.4, 0)).coords[0])
        b = np.array(core.interpolate(min(t + 0.4, core.length)).coords[0])
        tg = b - a
        L = np.hypot(*tg)
        if L < 1e-9 or not piece.buffer(0.02).contains(Point(c)):
            continue
        n = np.array([-tg[1], tg[0]]) / L
        hit = LineString([c - n * 4 * W, c + n * 4 * W]).intersection(piece)
        segs = [g for g in getattr(hit, "geoms", [hit]) if g.geom_type == "LineString" and g.length > 0.05]
        if not segs:
            continue
        g = min(segs, key=lambda g: g.distance(Point(c)))
        p, q = np.array(g.coords[0]), np.array(g.coords[-1])
        if (p - c) @ n > (q - c) @ n:
            p, q = q, p
        out.append(tuple(p) if k2 % 2 == 0 else tuple(q))
        k2 += 1
    return out if len(out) >= 3 else None


def _sew(pc, cut_lines, W):
    """-> (stitches, rails, axis) for one piece."""
    u = straight_axis(pc, W, cut_lines) if not pc.interiors else None
    st = scan_column(pc, u) if u else None
    r = None
    if st is None:
        r = rails(pc, cut_lines, W)
        st = zigzag(*r) if r else None
    return st, r, u


def _overlong(st, pc, W):
    """-> (length in stitches far longer than the stroke is wide, total length).
    A piece that is one stroke has none; a piece that is still two strokes
    sews across both, and that is how it shows."""
    if not st:
        return 0.0, 0.0
    thr = 1.6 * W
    P = np.array(st)
    L = np.hypot(*(P[1:] - P[:-1]).T)
    return float(L[L > thr].sum()), float(L.sum())


REFINE_TRIGGER = 0.12      # share of thread in over-long stitches that says "this is not one stroke"
REFINE_GAIN = 0.6          # a second-look cut must take that share down to this fraction of itself


def _refine(pc, cut_lines, W, depth):
    """yield (piece, cut lines, new cuts). The junction rules missed a cut
    wherever a piece still sews over-long; look again at that piece's own
    concave corners and keep the one cut that most reduces it."""
    st, _, _ = _sew(pc, cut_lines, W)
    long0, tot0 = _overlong(st, pc, W)
    if depth >= 3 or tot0 <= 0 or long0 / tot0 < REFINE_TRIGGER:
        yield pc, cut_lines, []
        return
    rf, _ = corners(pc, W)
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
            score = sum(_overlong(_sew(g, lines, W)[0], g, W)[0] for g in subs)
            if best is None or score < best[0]:
                best = (score, cut, subs, lines)
    if best is None or best[0] > REFINE_GAIN * long0:
        yield pc, cut_lines, []
        return
    first = True
    for g in best[2]:
        for sub, lines, extra in _refine(g, best[3], W, depth + 1):
            yield sub, lines, ([best[1]] if first else []) + extra
            first = False


def letter_columns(poly):
    W = stroke_width(poly)
    # a pinhole is the trace, not a counter
    poly = Polygon(poly.exterior, [h for h in poly.interiors if Polygon(h).area > 0.05 * W * W])
    # lumps under a sixteenth of the stroke are the trace, not the letter
    poly = poly.simplify(max(SIMPLIFY_MM, W / 16.0), preserve_topology=True)
    W = stroke_width(poly)
    cuts, reflex, convex = find_cuts(poly, W)
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
    cols = []
    for pc in pieces:
        for sub, lines, extra in _refine(pc, cut_lines, W, 0):
            cuts = cuts + extra
            st, r, u = _sew(sub, lines, W)
            cols.append(dict(piece=sub, rails=r, stitches=st, axis=u))
    return dict(poly=poly, W=W, cuts=cuts, reflex=reflex, convex=convex, cols=cols)
