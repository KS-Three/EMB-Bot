"""Letterform priors: refit a traced letter outline to straight segments and
circular arcs under parameters the whole word shares, moving no vertex more
than a fraction of the SOURCE pixel.

Built as a spike (2026-10-06, `docs/superpowers/specs/2026-10-06-letterform-
priors-design.md`, write-up `docs/letterform-priors-2026-10-06.md`) and
wired the same day behind `PipelineConfig.letterform_priors_k`, DEFAULT None
(off): `pipeline.build_generation` imports this module only inside the
flag's branch, so off, nothing here runs and the output is byte-identical.
The spike's tools (`tools/letterform_priors_spike/`) import the geometry
from here -- one copy of the code.

`apply_letterform_priors(regions, ...)` is the engine's entry: it groups the
lettering the way the house pass does, builds the word prior, refits every
text-tagged member in place (same `shape_id`, same `meta`, plus
`meta["letterform_prior"]` naming the outcome) and leaves a refused letter
untouched. Everything below it is pure geometry: a polygon in, a polygon
out, or the same polygon back with a reason.

## The rule that keeps the customer's font

Every move is capped at `k * src_px_mm` (the source image's pixel at the
design size). The fit may not invent what the raster could not have carried,
so a clean upload is left alone and a low-resolution one is redrawn only
inside its own pixel. Two mechanisms make a clean upload byte-identical:

1. the GRID gate: when the cap is under the engine's own working-grid pixel
   (`1 / result.px_per_mm`) the traced polygon already carries the edge to
   finer than the fit may move it, so the word passes through untouched;
2. per-letter REFUSAL: a letter whose outline the primitives do not explain
   within the cap on more than `UNEXPLAINED_MAX` of its length is left alone.

## Pipeline, per letter (one ring at a time)

densify -> Douglas-Peucker at the cap (chords within cap by construction)
-> drop short chamfers whose neighbours' corner explains them (sharp corners)
-> merge chord runs into circular arcs where one circle explains them
-> snap line angles to the word's stem / line direction (rotation about the
   chord midpoint, only when the endpoints move under the cap)
-> snap opposite stem/bar edges to the word's stroke-width mode(s)
-> snap bars sitting at the word's baseline / cap line onto them
-> rebuild the ring: line-line corners by intersection, line-arc joins on
   the circle, arcs sampled finely, unexplained pieces passed through verbatim
-> validate (simple, same hole count), check the cap both ways, refuse or accept.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely.geometry import LinearRing, LineString, Point, Polygon

# --- knobs (every one is listed in the write-up with what it was set on) ----
K_DEFAULT = 0.75          # cap = K * source pixel (the brief's starting point)
SNAP_DEG = 12.0           # a line this close to the stem/line direction is one
STEM_FAMILY_DEG = SNAP_DEG  # the "stem angle spread" statistic counts the same family
MIN_ARC_SWEEP_DEG = 40.0  # less bend than this is a line (or two), not an arc
MAX_ARC_SWEEP_DEG = 300.0
MIN_ARC_CHORDS = 3        # an arc explains a RUN of chords; two chords are a corner
MAX_ARC_TURN_DEG = 55.0   # one turn this sharp inside a run is a corner, not a bowl
UNEXPLAINED_MAX = 0.10    # share of outline left as pass-through before refusing
MIN_CORNER_DEG = 8.0      # two lines meeting flatter than this are not intersected
ARC_CHORD_MM = 0.02       # sampling error when an arc is written back as a polyline
ARC_MAX_STEP_MM = 0.25
WIDTH_CLUSTER_MIN = 2     # separations needed before a width mode exists


# --------------------------------------------------------------- data types
@dataclass
class WordPrior:
    line_deg: float             # direction of the line of text, [0, 180)
    slant_deg: float            # stems' lean off the normal to that line
    stem_deg: float             # stem direction, [0, 180)
    baseline_v: float | None    # along the line normal (frame v), the word's bottom
    cap_v: float | None         # ... and its top
    widths_mm: list[float]      # stroke width modes, full width
    tol_mm: float               # the cap
    src_px_mm: float
    grid_px_mm: float
    k: float

    @property
    def gated(self) -> bool:
        """True when the cap is under the working grid's pixel: pass through."""
        return self.tol_mm < self.grid_px_mm


@dataclass
class Prim:
    kind: str                   # "line" | "arc" | "pass"
    i0: int                     # sample index range [i0, i1] (inclusive, circular)
    i1: int
    p0: np.ndarray | None = None   # line endpoints (frame coords)
    p1: np.ndarray | None = None
    c: np.ndarray | None = None    # arc centre, radius, start/end angle, sweep sign
    r: float = 0.0
    a0: float = 0.0
    a1: float = 0.0
    ccw: bool = True
    snapped: str | None = None     # "stem" | "line" | None
    length: float = 0.0


@dataclass
class RingFit:
    prims: list[Prim]
    coords: np.ndarray          # the rebuilt ring, frame coords, closed
    unexplained_mm: float
    length_mm: float
    S: np.ndarray | None = None      # the source samples the primitives index
    own: np.ndarray | None = None    # which primitive wrote each rebuilt vertex

    def revert_near(self, pt: np.ndarray, radius: float, tol: float) -> bool:
        """Put every primitive that wrote a vertex within `radius` of `pt`
        back to the trace verbatim and rebuild. True when something moved."""
        if self.S is None or self.own is None:
            return False
        near = np.hypot(*(self.coords[:-1] - pt).T) <= radius
        hit = {int(k) for k in self.own[near] if self.prims[int(k)].kind != "pass"}
        if not hit:
            return False
        for k in hit:
            p = self.prims[k]
            p.kind = "pass"
            p.snapped = None
            self.unexplained_mm += float(LineString(_samples_of(self.S, p.i0, p.i1)).length)
        self.coords, self.own = _rebuild(self.S, self.prims, tol)
        return True


@dataclass
class FitResult:
    status: str                 # "refit" | "pass" | "refused"
    reason: str                 # "", "grid", "unexplained", "cap", "invalid", "holes", "empty"
    polygon: Polygon            # the output (== input when not "refit")
    moved_max_mm: float = 0.0
    moved_p95_mm: float = 0.0
    unexplained_share: float = 0.0
    n_line: int = 0
    n_arc: int = 0
    n_pass: int = 0
    stem_angles: list[tuple[float, float]] = field(default_factory=list)   # (deg off stem, length)
    rings: list[RingFit] = field(default_factory=list)
    before_n_prims: int = 0
    before_stem_angles: list[tuple[float, float]] = field(default_factory=list)

    @property
    def n_prims(self) -> int:
        return self.n_line + self.n_arc + self.n_pass


# ------------------------------------------------------------------ frames
def frame_axes(line_deg: float) -> tuple[np.ndarray, np.ndarray]:
    """Unit u along the line of text, v = u rotated +90 deg (y-down: v points
    'down' the page for a horizontal line, so the baseline is max v)."""
    t = math.radians(line_deg)
    u = np.array([math.cos(t), math.sin(t)])
    v = np.array([-u[1], u[0]])
    return u, v


def to_frame(xy: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    xy = np.asarray(xy, float)
    return np.stack([xy @ u, xy @ v], axis=1)


def from_frame(uv: np.ndarray, u: np.ndarray, v: np.ndarray) -> np.ndarray:
    uv = np.asarray(uv, float)
    return np.outer(uv[:, 0], u) + np.outer(uv[:, 1], v)


# --------------------------------------------------------------- sampling
def densify_ring(coords: np.ndarray, step: float) -> np.ndarray:
    """Closed ring (first == last) -> samples along it at most `step` apart,
    every original vertex kept, last point NOT repeated."""
    P = np.asarray(coords, float)
    if len(P) > 1 and np.allclose(P[0], P[-1]):
        P = P[:-1]
    out = []
    n = len(P)
    for i in range(n):
        a, b = P[i], P[(i + 1) % n]
        d = float(np.hypot(*(b - a)))
        m = max(1, int(math.ceil(d / step))) if step > 0 else 1
        for j in range(m):
            out.append(a + (b - a) * (j / m))
    return np.array(out)


def _dp_open(P: np.ndarray, eps: float, i0: int, i1: int, keep: list[int]) -> None:
    """Douglas-Peucker on P[i0..i1] (inclusive); appends interior keeps."""
    if i1 - i0 < 2:
        return
    a, b = P[i0], P[i1]
    ab = b - a
    L = float(np.hypot(*ab))
    seg = P[i0 + 1:i1]
    if L < 1e-12:
        d = np.hypot(*(seg - a).T)
    else:
        d = np.abs((seg - a)[:, 0] * ab[1] - (seg - a)[:, 1] * ab[0]) / L
    j = int(np.argmax(d))
    if d[j] > eps:
        k = i0 + 1 + j
        _dp_open(P, eps, i0, k, keep)
        keep.append(k)
        _dp_open(P, eps, k, i1, keep)


def dp_closed(P: np.ndarray, eps: float) -> list[int]:
    """Douglas-Peucker breakpoints of a closed sample ring, as sorted sample
    indices. Split at the two mutually farthest points so neither half wraps."""
    n = len(P)
    if n < 4:
        return list(range(n))
    c = P.mean(axis=0)
    s = int(np.argmax(np.hypot(*(P - c).T)))
    Q = np.roll(P, -s, axis=0)
    t = int(np.argmax(np.hypot(*(Q - Q[0]).T)))
    keep = [0]
    _dp_open(Q, eps, 0, t, keep)
    keep.append(t)
    Qw = np.vstack([Q, Q[:1]])
    _dp_open(Qw, eps, t, n, keep)
    idx = sorted({(k + s) % n for k in keep})
    return idx


# ------------------------------------------------------------- circle fit
def fit_circle(P: np.ndarray) -> tuple[np.ndarray, float] | None:
    """Kasa linear fit refined by a few Gauss-Newton steps on the geometric
    residual. None when the points are collinear or too few."""
    P = np.asarray(P, float)
    if len(P) < 3:
        return None
    m = P.mean(axis=0)
    Q = P - m
    A = np.column_stack([2 * Q[:, 0], 2 * Q[:, 1], np.ones(len(Q))])
    b = (Q ** 2).sum(axis=1)
    try:
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
    except np.linalg.LinAlgError:
        return None
    cx, cy, cc = sol
    r2 = cc + cx * cx + cy * cy
    if not np.isfinite(r2) or r2 <= 0:
        return None
    c = np.array([cx, cy])
    r = math.sqrt(r2)
    for _ in range(12):
        d = Q - c
        rho = np.hypot(*d.T)
        if (rho < 1e-9).any():
            break
        res = rho - r
        J = np.column_stack([-d[:, 0] / rho, -d[:, 1] / rho, -np.ones(len(rho))])
        try:
            step, *_ = np.linalg.lstsq(J, -res, rcond=None)
        except np.linalg.LinAlgError:
            break
        c = c + step[:2]
        r = r + step[2]
        if r <= 0 or not np.isfinite(r):
            return None
        if np.abs(step).max() < 1e-9:
            break
    return c + m, r


def arc_params(P: np.ndarray, c: np.ndarray, r: float) -> tuple[float, float, bool, float] | None:
    """(a0, a1, ccw, sweep_deg) if the samples wind monotonically about c."""
    ang = np.unwrap(np.arctan2(P[:, 1] - c[1], P[:, 0] - c[0]))
    d = np.diff(ang)
    if len(d) == 0:
        return None
    if (d > 0).all():
        ccw = True
    elif (d < 0).all():
        ccw = False
    else:
        # allow tiny backward jitter from sampling noise only
        s = np.sign(d[np.abs(d) > 1e-9])
        if len(s) == 0 or not (s == s[0]).all():
            return None
        ccw = s[0] > 0
    sweep = abs(ang[-1] - ang[0])
    return float(ang[0]), float(ang[-1]), bool(ccw), math.degrees(sweep)


def arc_points(c: np.ndarray, r: float, a0: float, a1: float, ccw: bool) -> np.ndarray:
    """Arc as a polyline from angle a0 to a1 (radians) including both ends."""
    sweep = (a1 - a0)
    if ccw and sweep < 0:
        sweep += 2 * math.pi
    if not ccw and sweep > 0:
        sweep -= 2 * math.pi
    if r <= ARC_CHORD_MM:
        n = 2
    else:
        step = 2 * math.acos(max(-1.0, min(1.0, 1 - ARC_CHORD_MM / r)))
        step = min(step, ARC_MAX_STEP_MM / r)
        n = max(2, int(math.ceil(abs(sweep) / max(step, 1e-6))) + 1)
    t = a0 + sweep * np.linspace(0, 1, n)
    return np.column_stack([c[0] + r * np.cos(t), c[1] + r * np.sin(t)])


# -------------------------------------------------------------- line utils
def seg_dist(P: np.ndarray, a: np.ndarray, b: np.ndarray) -> np.ndarray:
    ab = b - a
    L2 = float(ab @ ab)
    if L2 < 1e-18:
        return np.hypot(*(P - a).T)
    t = np.clip(((P - a) @ ab) / L2, 0.0, 1.0)
    foot = a + np.outer(t, ab)
    return np.hypot(*(P - foot).T)


def line_intersect(a0, a1, b0, b1) -> np.ndarray | None:
    d1, d2 = a1 - a0, b1 - b0
    den = d1[0] * d2[1] - d1[1] * d2[0]
    if abs(den) < 1e-12:
        return None
    t = ((b0[0] - a0[0]) * d2[1] - (b0[1] - a0[1]) * d2[0]) / den
    return a0 + t * d1


def line_circle_nearest(p0, p1, c, r, near) -> np.ndarray | None:
    """Intersection of the infinite line p0-p1 with circle (c, r) nearest to
    `near`, or None if they miss."""
    d = p1 - p0
    L = float(np.hypot(*d))
    if L < 1e-12:
        return None
    d = d / L
    f = p0 - c
    bq = 2 * float(f @ d)
    cq = float(f @ f) - r * r
    disc = bq * bq - 4 * cq
    if disc < 0:
        return None
    s = math.sqrt(disc)
    cands = [p0 + d * ((-bq + s) / 2), p0 + d * ((-bq - s) / 2)]
    return min(cands, key=lambda q: float(np.hypot(*(q - near))))


def angle_diff_axial(a_deg: float, b_deg: float) -> float:
    """Signed smallest difference between two undirected directions, (-90, 90]."""
    return (a_deg - b_deg + 90.0) % 180.0 - 90.0


# ------------------------------------------------------------ ring fitting
def _samples_of(S: np.ndarray, i0: int, i1: int) -> np.ndarray:
    n = len(S)
    if i1 >= i0:
        return S[i0:i1 + 1]
    return np.vstack([S[i0:], S[:i1 + 1]])


def _initial_lines(S: np.ndarray, breaks: list[int]) -> list[Prim]:
    prims = []
    for k in range(len(breaks)):
        i0, i1 = breaks[k], breaks[(k + 1) % len(breaks)]
        p0, p1 = S[i0].copy(), S[i1].copy()
        prims.append(Prim("line", i0, i1, p0=p0, p1=p1, length=float(np.hypot(*(p1 - p0)))))
    return prims


def _drop_chamfers(S: np.ndarray, prims: list[Prim], tol: float, lmin: float) -> list[Prim]:
    """A line shorter than `lmin` between two longer lines is dropped when
    the corner its neighbours make explains its samples within `tol`."""
    changed = True
    while changed and len(prims) > 3:
        changed = False
        for k, p in enumerate(prims):
            if p.kind != "line" or p.length >= lmin:
                continue
            a, b = prims[(k - 1) % len(prims)], prims[(k + 1) % len(prims)]
            if a.kind != "line" or b.kind != "line" or a is b:
                continue
            if a.length < lmin or b.length < lmin:
                continue
            x = line_intersect(a.p0, a.p1, b.p0, b.p1)
            if x is None:
                continue
            # the corner must sit near the dropped piece, not off in the distance
            if seg_dist(x[None, :], p.p0, p.p1)[0] > tol:
                continue
            pts = _samples_of(S, p.i0, p.i1)
            d = np.minimum(seg_dist(pts, a.p0, x), seg_dist(pts, x, b.p1))
            if d.max() <= tol:
                a.p1 = x
                a.i1 = p.i1
                a.length = float(np.hypot(*(a.p1 - a.p0)))
                b.p0 = x
                b.length = float(np.hypot(*(b.p1 - b.p0)))
                del prims[k]
                changed = True
                break
    return prims


def _try_line(S: np.ndarray, i0: int, i1: int, tol: float) -> Prim | None:
    """A total-least-squares line through the run's samples, when it holds
    every one of them within tol. The endpoints are the extreme samples'
    feet on that line."""
    pts = _samples_of(S, i0, i1)
    if len(pts) < 2:
        return None
    m = pts.mean(axis=0)
    _u, _s, vt = np.linalg.svd(pts - m, full_matrices=False)
    d = vt[0]
    dev = np.abs((pts - m)[:, 0] * d[1] - (pts - m)[:, 1] * d[0])
    if dev.max() > tol:
        return None
    t = (pts - m) @ d
    p0, p1 = m + d * t[0], m + d * t[-1]
    return Prim("line", i0, i1, p0=p0, p1=p1, length=float(np.hypot(*(p1 - p0))))


def _try_arc(S: np.ndarray, i0: int, i1: int, tol: float, rmin: float,
             rmax: float = math.inf) -> Prim | None:
    pts = _samples_of(S, i0, i1)
    if len(pts) < 4:
        return None
    fit = fit_circle(pts)
    if fit is None:
        return None
    c, r = fit
    if r < rmin or r > rmax or not np.isfinite(r):
        return None
    if np.abs(np.hypot(*(pts - c).T) - r).max() > tol:
        return None
    ap = arc_params(pts, c, r)
    if ap is None:
        return None
    a0, a1, ccw, sweep = ap
    if sweep < MIN_ARC_SWEEP_DEG or sweep > MAX_ARC_SWEEP_DEG:
        return None
    return Prim("arc", i0, i1, c=c, r=r, a0=a0, a1=a1, ccw=ccw, length=math.radians(sweep) * r)


def _turn_deg(a: Prim, b: Prim) -> float:
    """Signed turn from chord a's direction to chord b's, in degrees."""
    da, db = a.p1 - a.p0, b.p1 - b.p0
    return math.degrees(math.atan2(da[0] * db[1] - da[1] * db[0], float(da @ db)))


def _chords_of(S: np.ndarray, i0: int, i1: int, tol: float) -> list[Prim]:
    """The DP chords of the open sample run [i0, i1] -- what an arc or a
    merged line is softened back to when the rebuilt ring breaks the cap."""
    pts = _samples_of(S, i0, i1)
    keep: list[int] = [0]
    _dp_open(pts, tol, 0, len(pts) - 1, keep)
    keep.append(len(pts) - 1)
    n = len(S)
    out = []
    for a, b in zip(keep, keep[1:]):
        ia, ib = (i0 + a) % n, (i0 + b) % n
        out.append(Prim("line", ia, ib, p0=S[ia].copy(), p1=S[ib].copy(),
                        length=float(np.hypot(*(S[ib] - S[ia])))))
    return out


def _merge_arcs(S: np.ndarray, prims: list[Prim], tol: float, rmin: float,
                rmax: float = math.inf) -> list[Prim]:
    """Greedy: from each line, extend a run over following lines while ONE
    primitive explains all their samples within tol -- a line first (the
    typographic prior: stems, bars and arms are straight, and at a coarse
    source pixel a slow arc and a straight edge both fit the staircase), a
    circle only where no line holds the run. Keeps the longest run."""
    n = len(prims)
    if n < 3:
        return prims
    out: list[Prim] = []
    used = [False] * n
    # Start from a primitive that will NOT be absorbed by a run wrapping
    # around the end: pick the longest line as the anchor.
    start_k = max(range(n), key=lambda i: prims[i].length)
    order = [(start_k + i) % n for i in range(n)]
    pos = 0
    while pos < n:
        k = order[pos]
        if used[k]:
            pos += 1
            continue
        p = prims[k]
        if p.kind != "line":
            out.append(p)
            used[k] = True
            pos += 1
            continue
        best = None
        best_len = 1
        run_i1 = p.i1
        turns: list[float] = []
        prev = p
        for extra in range(1, n - 1):
            q = order[(pos + extra) % n]
            if used[q] or prims[q].kind != "line" or q == k:
                break
            cur = prims[q]
            run_i1 = cur.i1
            turns.append(_turn_deg(prev, cur))
            prev = cur
            same_sign = all(t > 0 for t in turns) or all(t < 0 for t in turns)
            if not same_sign or max(abs(t) for t in turns) > MAX_ARC_TURN_DEG:
                break                                   # a corner, or a wiggle
            cand = _try_line(S, p.i0, run_i1, tol)
            if cand is None and len(turns) + 1 >= MIN_ARC_CHORDS:
                cand = _try_arc(S, p.i0, run_i1, tol, rmin, rmax)
                if cand is None:
                    break                               # no one circle holds the run
            if cand is not None:
                best, best_len = cand, extra + 1
            # else: too few chords for an arc yet; keep extending
        if best is not None:
            out.append(best)
            for extra in range(best_len):
                used[order[(pos + extra) % n]] = True
            pos += best_len
        else:
            out.append(p)
            used[k] = True
            pos += 1
    return out


def _line_residual(S: np.ndarray, p: Prim) -> float:
    """Max distance of the primitive's own source samples to its infinite
    line -- the cap is measured against the SOURCE, never against the
    previous fit, so two moves of tol cannot stack to 2 tol."""
    pts = _samples_of(S, p.i0, p.i1)
    d = p.p1 - p.p0
    L = float(np.hypot(*d))
    if L < 1e-12:
        return float(np.hypot(*(pts - p.p0).T).max())
    return float(np.abs((pts - p.p0)[:, 0] * d[1] - (pts - p.p0)[:, 1] * d[0]).max() / L)


def _snap_angles(S: np.ndarray, prims: list[Prim], prior: WordPrior, tol: float) -> None:
    """Rotate each line about its midpoint onto the stem or line direction
    when it is within SNAP_DEG and its source samples stay under the cap."""
    for p in prims:
        if p.kind != "line":
            continue
        d = p.p1 - p.p0
        L = float(np.hypot(*d))
        if L < 1e-9:
            continue
        ang = math.degrees(math.atan2(d[1], d[0]))
        for fam, target in (("stem", prior.stem_deg), ("line", prior.line_deg)):
            off = angle_diff_axial(ang, target)
            if abs(off) > SNAP_DEG:
                continue
            t = math.radians(ang - off)
            u = np.array([math.cos(t), math.sin(t)])
            m = (p.p0 + p.p1) / 2
            old = (p.p0.copy(), p.p1.copy())
            p.p0, p.p1 = m - u * (L / 2), m + u * (L / 2)
            if _line_residual(S, p) > tol:
                p.p0, p.p1 = old
                continue
            p.snapped = fam
            break


def _edge_normal(p: Prim, ring_ccw: bool) -> np.ndarray:
    d = p.p1 - p.p0
    L = float(np.hypot(*d))
    if L < 1e-12:
        return np.zeros(2)
    d = d / L
    # left normal for a CCW ring points inward; outward = right normal
    nrm = np.array([d[1], -d[0]]) if ring_ccw else np.array([-d[1], d[0]])
    return nrm


def pair_separations(prims: list[Prim], ring_ccw: bool, fam: str,
                     ink: Polygon | None) -> list[tuple[int, int, float]]:
    """(i, j, separation) for pairs of snapped lines in family `fam` facing
    each other ACROSS INK (the midpoint between them is inside `ink`, so a
    counter or the gap between two stems is not a stroke) with overlapping
    extents."""
    idx = [i for i, p in enumerate(prims) if p.kind == "line" and p.snapped == fam]
    pairs = []
    for a in range(len(idx)):
        i = idx[a]
        pi = prims[i]
        ni = _edge_normal(pi, ring_ccw)
        di = pi.p1 - pi.p0
        Li = float(np.hypot(*di))
        if Li < 1e-9:
            continue
        di = di / Li
        for b in range(a + 1, len(idx)):
            j = idx[b]
            pj = prims[j]
            nj = _edge_normal(pj, ring_ccw)
            if float(ni @ nj) > -0.99:          # must face opposite ways
                continue
            # overlap along the stroke axis
            s0 = sorted([0.0, Li])
            s1 = sorted([float((pj.p0 - pi.p0) @ di), float((pj.p1 - pi.p0) @ di)])
            ov = min(s0[1], s1[1]) - max(s0[0], s1[0])
            if ov <= 0.5 * min(Li, s1[1] - s1[0]):
                continue
            sep = float(((pj.p0 + pj.p1) / 2 - (pi.p0 + pi.p1) / 2) @ (-ni))
            if sep <= 0:
                continue
            if ink is not None:
                # the midpoint of the overlap, halfway across
                lo, hi = max(s0[0], s1[0]), min(s0[1], s1[1])
                mid_i = pi.p0 + di * ((lo + hi) / 2)
                mid = mid_i - ni * (sep / 2)
                if not ink.contains(Point(mid)):
                    continue
            pairs.append((i, j, sep))
    return pairs


def _snap_widths(S: np.ndarray, prims: list[Prim], ring_ccw: bool, prior: WordPrior,
                 tol: float, ink: Polygon | None) -> None:
    """Move facing edges of a stroke symmetrically to the nearest word width
    mode when both edges' source samples stay under the cap. Each edge is
    moved at most once."""
    if not prior.widths_mm:
        return
    moved: set[int] = set()
    for fam in ("stem", "line"):
        pairs = pair_separations(prims, ring_ccw, fam, ink)
        pairs.sort(key=lambda t: t[2])
        for i, j, sep in pairs:
            if i in moved or j in moved:
                continue
            w = min(prior.widths_mm, key=lambda m: abs(m - sep))
            shift = (w - sep) / 2
            if abs(shift) > tol or abs(shift) < 1e-9:
                continue
            ni = _edge_normal(prims[i], ring_ccw)
            nj = _edge_normal(prims[j], ring_ccw)
            old = (prims[i].p0.copy(), prims[i].p1.copy(), prims[j].p0.copy(), prims[j].p1.copy())
            prims[i].p0 = prims[i].p0 + ni * shift
            prims[i].p1 = prims[i].p1 + ni * shift
            prims[j].p0 = prims[j].p0 + nj * shift
            prims[j].p1 = prims[j].p1 + nj * shift
            if _line_residual(S, prims[i]) > tol or _line_residual(S, prims[j]) > tol:
                prims[i].p0, prims[i].p1, prims[j].p0, prims[j].p1 = old
                continue
            moved.update((i, j))


def _snap_baseline(S: np.ndarray, prims: list[Prim], prior: WordPrior, tol: float,
                   u: np.ndarray, v: np.ndarray) -> None:
    """A line-direction edge sitting within the cap of the word's baseline or
    cap line is put exactly on it (translation along v), source samples
    permitting."""
    for p in prims:
        if p.kind != "line" or p.snapped != "line":
            continue
        vmid = float(((p.p0 + p.p1) / 2) @ v)
        for target in (prior.baseline_v, prior.cap_v):
            if target is None:
                continue
            dv = target - vmid
            if abs(dv) <= tol and abs(dv) > 1e-9:
                old = (p.p0.copy(), p.p1.copy())
                p.p0 = p.p0 + v * dv
                p.p1 = p.p1 + v * dv
                if _line_residual(S, p) > tol:
                    p.p0, p.p1 = old
                    continue
                break


def _rebuild(S: np.ndarray, prims: list[Prim], tol: float) -> np.ndarray:
    """Walk the primitives and write the ring back as a closed polyline.
    Every junction vertex is checked against the SOURCE ring (`src`), not
    against the primitives' own endpoints, so a sharpened corner cannot
    land further from the trace than the cap."""
    n = len(prims)
    src = LineString(np.vstack([S, S[:1]]))
    pieces: list[np.ndarray] = []

    def near_src(x) -> bool:
        return src.distance(Point(x)) <= tol

    for k in range(n):
        p, q = prims[k], prims[(k + 1) % n]
        # junction between p and q
        if p.kind == "line" and q.kind == "line":
            x = line_intersect(p.p0, p.p1, q.p0, q.p1)
            d1, d2 = p.p1 - p.p0, q.p1 - q.p0
            cosang = abs(float(d1 @ d2)) / max(float(np.hypot(*d1) * np.hypot(*d2)), 1e-12)
            if (x is not None and cosang < math.cos(math.radians(MIN_CORNER_DEG))
                    and near_src(x)):
                j = x
            else:
                j = (p.p1 + q.p0) / 2
            p.p1 = j
            q.p0 = j
        elif p.kind == "line" and q.kind == "arc":
            near = q.c + q.r * np.array([math.cos(q.a0), math.sin(q.a0)])
            x = line_circle_nearest(p.p0, p.p1, q.c, q.r, near)
            if x is not None and near_src(x):
                p.p1 = x
                q.a0 = math.atan2(x[1] - q.c[1], x[0] - q.c[0])
            else:
                p.p1 = near
        elif p.kind == "arc" and q.kind == "line":
            near = p.c + p.r * np.array([math.cos(p.a1), math.sin(p.a1)])
            x = line_circle_nearest(q.p0, q.p1, p.c, p.r, near)
            if x is not None and near_src(x):
                q.p0 = x
                p.a1 = math.atan2(x[1] - p.c[1], x[0] - p.c[0])
            else:
                q.p0 = near
        elif p.kind == "arc" and q.kind == "arc":
            e1 = p.c + p.r * np.array([math.cos(p.a1), math.sin(p.a1)])
            e2 = q.c + q.r * np.array([math.cos(q.a0), math.sin(q.a0)])
            m = (e1 + e2) / 2
            p.a1 = math.atan2(m[1] - p.c[1], m[0] - p.c[0])
            q.a0 = math.atan2(m[1] - q.c[1], m[0] - q.c[0])
        else:
            # a pass-through piece keeps its own endpoints; the neighbour meets it there
            if p.kind == "pass":
                end = S[p.i1]
                if q.kind == "line":
                    q.p0 = end.copy()
                elif q.kind == "arc":
                    q.a0 = math.atan2(end[1] - q.c[1], end[0] - q.c[0])
            if q.kind == "pass":
                start = S[q.i0]
                if p.kind == "line":
                    p.p1 = start.copy()
                elif p.kind == "arc":
                    p.a1 = math.atan2(start[1] - p.c[1], start[0] - p.c[0])
    owner: list[int] = []
    for k, p in enumerate(prims):
        if p.kind == "line":
            pieces.append(np.array([p.p0]))
        elif p.kind == "arc":
            pieces.append(arc_points(p.c, p.r, p.a0, p.a1, p.ccw)[:-1])
        else:
            pieces.append(_samples_of(S, p.i0, p.i1)[:-1])
        owner += [k] * len(pieces[-1])
    R = np.vstack(pieces)
    own = np.array(owner)
    # drop consecutive duplicates
    keep = np.ones(len(R), bool)
    keep[1:] = np.hypot(*(R[1:] - R[:-1]).T) > 1e-9
    R, own = R[keep], own[keep]
    if len(R) > 1 and np.hypot(*(R[0] - R[-1])) <= 1e-9:
        R, own = R[:-1], own[:-1]
    return np.vstack([R, R[:1]]), own


def _offenders(S: np.ndarray, prims: list[Prim], R: np.ndarray, own: np.ndarray,
               tol: float) -> set[int]:
    """Primitives whose source samples sit further than tol from the rebuilt
    ring, or whose rebuilt vertices sit further than tol from the source."""
    bad: set[int] = set()
    ring = LineString(R)
    src = LineString(np.vstack([S, S[:1]]))
    n = len(S)
    for k, p in enumerate(prims):
        if p.kind == "pass":
            continue
        idx = list(range(p.i0, p.i1 + 1)) if p.i1 >= p.i0 else list(range(p.i0, n)) + list(range(0, p.i1 + 1))
        if any(ring.distance(Point(S[i])) > tol for i in idx):
            bad.add(k)
    for q, k in zip(R[:-1], own):
        if k not in bad and prims[k].kind != "pass" and src.distance(Point(q)) > tol:
            bad.add(int(k))
    return bad


def sample_step(tol: float) -> float:
    return max(min(tol / 4.0, 0.1), 0.02)


def primitives_of(S: np.ndarray, tol: float) -> list[Prim]:
    """Lines and arcs explaining the sample ring `S` within `tol`, snapping
    aside: DP chords -> chamfers dropped -> chord runs merged into one line
    or one arc. An arc's radius is bounded below by 2 tol (a tighter bend is
    a corner the raster could not show) and above by the ring's own extent
    (a letterform's arcs are its bowls, not a horizon)."""
    prims = _initial_lines(S, dp_closed(S, tol))
    prims = _drop_chamfers(S, prims, tol, 2.0 * tol)
    extent = float(np.hypot(*(S.max(axis=0) - S.min(axis=0))))
    return _merge_arcs(S, prims, tol, rmin=2.0 * tol, rmax=extent)


def fit_ring(coords: np.ndarray, prior: WordPrior, u: np.ndarray, v: np.ndarray,
             tol: float, ink: Polygon | None) -> RingFit:
    """One ring in frame coordinates -> its rebuilt ring and primitives.
    `ink` is the whole letter in the same frame (for the across-ink test)."""
    S = densify_ring(coords, sample_step(tol))
    ring_ccw = LinearRing(np.vstack([S, S[:1]])).is_ccw
    length = float(LineString(np.vstack([S, S[:1]])).length)
    prims = primitives_of(S, tol)
    lmin = 2.0 * tol
    # short lines that survived the chamfer pass are unexplained residue
    unexplained = 0.0
    for p in prims:
        if p.kind == "line" and p.length < lmin:
            p.kind = "pass"
            unexplained += p.length
    _snap_angles(S, prims, prior, tol)
    _snap_widths(S, prims, ring_ccw, prior, tol, ink)
    _snap_baseline(S, prims, prior, tol, u, v)
    R, own = _rebuild(S, prims, tol)
    # Repair, two rounds. A primitive the rebuilt ring leaves over the cap
    # (a junction trim, an arc's extrapolated end, a midpoint fallback) is
    # first SOFTENED -- an arc or a merged line back to its DP chords, a
    # snapped line back to its own chord -- and the ring rebuilt. What still
    # breaks the cap then goes back to the trace verbatim ("pass") and counts
    # as unexplained.
    bad = _offenders(S, prims, R, own, tol)
    if bad:
        soft: list[Prim] = []
        for k, p in enumerate(prims):
            if k in bad and p.kind in ("line", "arc"):
                soft += _chords_of(S, p.i0, p.i1, tol)
            else:
                soft.append(p)
        prims = soft
        R, own = _rebuild(S, prims, tol)
        bad = _offenders(S, prims, R, own, tol)
        for k in bad:
            p = prims[k]
            p.kind = "pass"
            p.snapped = None
            unexplained += float(LineString(_samples_of(S, p.i0, p.i1)).length)
        if bad:
            R, own = _rebuild(S, prims, tol)
    return RingFit(prims=prims, coords=R, unexplained_mm=unexplained, length_mm=length, S=S, own=own)


def letter_lean_deg(coords: np.ndarray, stem_deg: float, tol: float,
                    window_deg: float = 15.0) -> float | None:
    """How far this letter's own stems lean off `stem_deg`: the length-
    weighted MEDIAN offset of its DP chords within `window_deg` of that
    direction, or None when it has no such chord. The median, not the
    mean: a slanted terminal (Becker's E arms are cut at an angle) is a
    short chord inside the window and a mean read that E as leaning 8.7
    deg on a straight word. Resolution-independent where the engine's
    skeleton instrument is not: chords are millimetres long, skeleton
    steps are pixels."""
    S = densify_ring(coords, sample_step(tol))
    lines = _initial_lines(S, dp_closed(S, tol))
    votes: list[tuple[float, float]] = []
    for p in lines:
        d = p.p1 - p.p0
        L = float(np.hypot(*d))
        if L < 1e-9:
            continue
        off = angle_diff_axial(math.degrees(math.atan2(d[1], d[0])), stem_deg)
        if abs(off) <= window_deg:
            votes.append((off, L))
    if not votes:
        return None
    votes.sort()
    half = sum(w for _o, w in votes) / 2.0
    acc = 0.0
    for off, w in votes:
        acc += w
        if acc >= half:
            return off
    return votes[-1][0]


def _stem_angles(prims: list[Prim], stem_deg: float) -> list[tuple[float, float]]:
    out = []
    for p in prims:
        if p.kind != "line":
            continue
        d = p.p1 - p.p0
        L = float(np.hypot(*d))
        if L < 1e-9:
            continue
        off = angle_diff_axial(math.degrees(math.atan2(d[1], d[0])), stem_deg)
        if abs(off) <= STEM_FAMILY_DEG:
            out.append((off, L))
    return out


def _cap_check(src_rings: list[np.ndarray], out_rings: list[np.ndarray], tol: float,
               step: float) -> tuple[float, float]:
    """Max and p95 of the two-way distance between the source rings and the
    rebuilt rings, sampled every `step` mm (plus every vertex)."""
    ds = []
    for A, B in zip(src_rings, out_rings):
        la, lb = LineString(A), LineString(B)
        Sa = densify_ring(A, step)
        Sb = densify_ring(B, step)
        ds.append(np.array([lb.distance(Point(p)) for p in Sa]))
        ds.append(np.array([la.distance(Point(p)) for p in Sb]))
    d = np.concatenate(ds) if ds else np.zeros(1)
    return float(d.max()), float(np.percentile(d, 95))


def _invalid_point(poly) -> np.ndarray | None:
    """Where shapely says a polygon is invalid, as (x, y), or None."""
    import re
    from shapely.validation import explain_validity
    m = re.search(r"\[(-?[\d.eE+-]+) (-?[\d.eE+-]+)\]", explain_validity(poly) or "")
    return np.array([float(m.group(1)), float(m.group(2))]) if m else None


def fit_letter(poly: Polygon, prior: WordPrior) -> FitResult:
    """Refit one letter polygon under the word's prior. Never raises; the
    input polygon comes back with a reason when the fit is refused."""
    if poly.is_empty or not poly.is_valid:
        return FitResult("refused", "invalid-input", poly)
    tol = prior.tol_mm
    u, v = frame_axes(prior.line_deg)
    src_rings_xy = [np.asarray(poly.exterior.coords, float)] + [np.asarray(h.coords, float)
                                                                 for h in poly.interiors]
    # "before" structure: what the trace needs at this cap, snapping aside
    before_n = 0
    before_stems: list[tuple[float, float]] = []
    for ring in src_rings_xy:
        F = to_frame(ring, u, v)
        S = densify_ring(F, max(min(tol / 4.0, 0.1), 0.02))
        br = dp_closed(S, tol)
        lines = _initial_lines(S, br)
        before_n += len(lines)
        before_stems += _stem_angles(lines, prior.stem_deg - prior.line_deg)
    if prior.gated:
        return FitResult("pass", "grid", poly, before_n_prims=before_n,
                         before_stem_angles=before_stems)
    fits: list[RingFit] = []
    out_rings_xy: list[np.ndarray] = []
    # the prior's directions, expressed in the frame (line = 0 deg)
    fprior = WordPrior(line_deg=0.0, slant_deg=prior.slant_deg,
                       stem_deg=(prior.stem_deg - prior.line_deg) % 180.0,
                       baseline_v=prior.baseline_v, cap_v=prior.cap_v,
                       widths_mm=prior.widths_mm, tol_mm=tol, src_px_mm=prior.src_px_mm,
                       grid_px_mm=prior.grid_px_mm, k=prior.k)
    fu, fv = np.array([1.0, 0.0]), np.array([0.0, 1.0])
    try:
        ink = Polygon(to_frame(src_rings_xy[0], u, v), [to_frame(h, u, v) for h in src_rings_xy[1:]])
        if not ink.is_valid:
            ink = None
        for ring in src_rings_xy:
            F = to_frame(ring, u, v)
            rf = fit_ring(F, fprior, fu, fv, tol, ink)
            fits.append(rf)
            out_rings_xy.append(from_frame(rf.coords, u, v))
    except Exception as e:                                   # noqa: BLE001
        return FitResult("refused", f"error:{type(e).__name__}", poly,
                         before_n_prims=before_n, before_stem_angles=before_stems)
    total_len = sum(f.length_mm for f in fits) or 1.0
    base: dict = dict(before_n_prims=before_n, before_stem_angles=before_stems, rings=fits)

    def assemble():
        rings = [from_frame(f.coords, u, v) for f in fits]
        try:
            return rings, Polygon(rings[0], rings[1:])
        except Exception:                                    # noqa: BLE001
            return rings, None

    out_rings_xy, new = assemble()
    # A ring that crosses itself (a notch or counter the snaps pinched shut:
    # "counters keep their opening") is repaired where it crosses: the
    # primitives that wrote the vertices round the crossing go back to the
    # trace, that ring is rebuilt, and the polygon is tried again.
    for _round in range(2):
        if new is not None and new.is_valid and not new.is_empty and new.geom_type == "Polygon":
            break
        pt = _invalid_point(new) if new is not None else None
        if pt is None:
            break
        fpt = to_frame(np.array([pt]), u, v)[0]
        if not any(f.revert_near(fpt, 2.0 * tol, tol) for f in fits):
            break
        out_rings_xy, new = assemble()
    unexplained = sum(f.unexplained_mm for f in fits) / total_len
    n_line = sum(1 for f in fits for p in f.prims if p.kind == "line")
    n_arc = sum(1 for f in fits for p in f.prims if p.kind == "arc")
    n_pass = sum(1 for f in fits for p in f.prims if p.kind == "pass")
    stems = [a for f in fits for a in _stem_angles(f.prims, fprior.stem_deg)]
    base.update(unexplained_share=unexplained, n_line=n_line, n_arc=n_arc, n_pass=n_pass,
                stem_angles=stems)
    if unexplained > UNEXPLAINED_MAX:
        return FitResult("refused", "unexplained", poly, **base)
    if new is None or new.is_empty or not new.is_valid or new.geom_type != "Polygon":
        return FitResult("refused", "invalid", poly, **base)
    if len(new.interiors) != len(poly.interiors):
        return FitResult("refused", "holes", poly, **base)
    mx, p95 = _cap_check(src_rings_xy, out_rings_xy, tol, max(min(tol / 4.0, 0.1), 0.02))
    base.update(moved_max_mm=mx, moved_p95_mm=p95)
    if mx > tol * (1.0 + 1e-6):
        return FitResult("refused", "cap", poly, **base)
    return FitResult("refit", "", new, **base)


# ------------------------------------------------------------ word prior
def cluster_1d(values: list[float], gap: float, min_members: int) -> list[float]:
    """Medians of runs of sorted values whose neighbours sit closer than `gap`."""
    if not values:
        return []
    vs = sorted(values)
    runs: list[list[float]] = [[vs[0]]]
    for x in vs[1:]:
        if x - runs[-1][-1] <= gap:
            runs[-1].append(x)
        else:
            runs.append([x])
    return [float(np.median(r)) for r in runs if len(r) >= min_members]


def letter_prior(prior: WordPrior, line_deg: float) -> WordPrior:
    """The word's prior re-expressed for one letter whose local line of text
    is `line_deg` (an arched word: each letter sits upright on its own piece
    of the arc). Baseline and cap lines are dropped: along an arc they are
    not lines."""
    import dataclasses
    return dataclasses.replace(prior, line_deg=line_deg,
                               stem_deg=(line_deg + 90.0 + prior.slant_deg) % 180.0,
                               baseline_v=None, cap_v=None)


def word_prior(polys: list[Polygon], line_deg: float, slant_deg: float | None,
               src_px_mm: float, grid_px_mm: float, k: float = K_DEFAULT,
               line_degs: list[float] | None = None,
               width_hint_mm: float | None = None) -> WordPrior:
    """Shared parameters for one line of lettering. `line_deg` and
    `slant_deg` come from `textcluster._line_of_text_deg` / `_stem_slant_deg`
    (the engine's own house reading); this derives the rest from the
    member polygons at the cap.

    `line_degs` (one per polygon) is the arched case: each letter's own local
    line, so the width modes are measured in each letter's upright frame
    and no baseline / cap line is set. `width_hint_mm` is the word's stroke
    width from the engine's skeleton instrument (`_skeleton_stroke_stats`,
    2 x the mean half-width): a facing pair further apart than twice it is
    a letter's height or width, not a stroke, and is not a width vote."""
    tol = k * src_px_mm
    slant = float(slant_deg or 0.0)
    stem_deg = (line_deg + 90.0 + slant) % 180.0
    arched = line_degs is not None
    u, v = frame_axes(line_deg)
    bottoms, tops = [], []
    for p in polys:
        F = to_frame(np.asarray(p.exterior.coords, float), u, v)
        bottoms.append(float(F[:, 1].max()))
        tops.append(float(F[:, 1].min()))
    baseline = float(np.median(bottoms)) if bottoms and not arched else None
    cap = float(np.median(tops)) if tops and not arched else None
    prior = WordPrior(line_deg=line_deg, slant_deg=slant, stem_deg=stem_deg,
                      baseline_v=baseline, cap_v=cap, widths_mm=[], tol_mm=tol,
                      src_px_mm=src_px_mm, grid_px_mm=grid_px_mm, k=k)
    if prior.gated:
        return prior
    # width modes: separations of facing stem / bar edges over the word,
    # measured on the angle-snapped (not width-snapped) primitives
    fprior = WordPrior(line_deg=0.0, slant_deg=slant, stem_deg=(90.0 + slant) % 180.0,
                       baseline_v=None, cap_v=None, widths_mm=[], tol_mm=tol,
                       src_px_mm=src_px_mm, grid_px_mm=grid_px_mm, k=k)
    seps: list[float] = []
    for li, p in enumerate(polys):
        lu, lv = frame_axes(line_degs[li]) if arched else (u, v)
        ink = Polygon(to_frame(np.asarray(p.exterior.coords, float), lu, lv),
                      [to_frame(np.asarray(h.coords, float), lu, lv) for h in p.interiors])
        if not ink.is_valid:
            ink = None
        for ring in [p.exterior, *p.interiors]:
            F = to_frame(np.asarray(ring.coords, float), lu, lv)
            S = densify_ring(F, sample_step(tol))
            ring_ccw = LinearRing(np.vstack([S, S[:1]])).is_ccw
            prims = primitives_of(S, tol)
            _snap_angles(S, prims, fprior, tol)
            for fam in ("stem", "line"):
                seps += [s for _i, _j, s in pair_separations(prims, ring_ccw, fam, ink)]
    if width_hint_mm:
        seps = [s for s in seps if s <= 2.0 * width_hint_mm]
    prior.widths_mm = cluster_1d(seps, gap=2.0 * tol, min_members=WIDTH_CLUSTER_MIN)
    return prior


def polygon_wkb_hash(polys: dict[str, Polygon]) -> str:
    import hashlib
    h = hashlib.sha256()
    for sid in sorted(polys):
        h.update(sid.encode())
        h.update(polys[sid].wkb)
    return h.hexdigest()[:16]


# ------------------------------------------------------- the engine's entry
# A word whose letters' stem leans (each read by `letter_lean_deg` on that
# letter alone) spread more than this -- over the middle 60% of the leans,
# so an A's legs or an E's slanted terminals cannot call a straight word
# arched -- is arched: each letter then gets its own line of text. Set on
# Becker's two words (MARINE's core leans agree within 1 deg; the arched
# BECKER band reads 4.7 and is NOT called arched -- its lean is under the
# snap window and self-limiting) and on bridge; gaulke was held out.
ARCH_LEAN_SPREAD_DEG = 6.0
# The engine's `_stem_slant_deg` reads its slant off 4-px skeleton chords and
# gave 0 on Fremont's italic word where the DP chords read 12.8 deg; past
# this disagreement the chord reading is the word's slant.
SLANT_DISAGREE_DEG = 3.0


@dataclass
class LetterOutcome:
    """One text-tagged member's fit, before anything is written back."""
    word: int
    shape_id: str
    char: str | None
    traced: Polygon
    fit: FitResult
    prior: WordPrior
    note: dict = field(default_factory=dict)     # the word's slant source, arch verdict, leans

    @property
    def refit(self) -> Polygon:
        return self.fit.polygon

    @property
    def outcome(self) -> str:
        """`refit` | `pass:<why>` | `refused:<why>` -- the meta value."""
        return self.fit.status + (":" + self.fit.reason if self.fit.reason else "")


def lettering_words(regions, words: bool = False) -> list[list]:
    """The lines of lettering to refit: `textcluster._lettering_groups` (the
    house pass's groups), plus -- for text-tagged letters that pass leaves
    out -- the tagger's own `text_cluster_id`. Bridge's 8 tagged blobs form
    no `_lettering_groups` group at all (its size/aspect links are stricter
    than the tagger's) and reach the fit only through the cluster id.

    `words` (`cfg.lettering_words`): the one tagger's words are the lines
    (`words.tag_words` ran first), every member a letter, and nothing
    else is read -- no words, nothing to refit."""
    if words:
        from .words import word_groups
        return word_groups(regions)
    from .textcluster import _lettering_groups
    groups = _lettering_groups(regions)
    seen = {r.shape_id for g in groups for r in g}
    by_cluster: dict[str, list] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid and r.meta.get("text_candidate") and r.shape_id not in seen:
            by_cluster.setdefault(cid, []).append(r)
    return groups + [g for g in by_cluster.values() if len(g) >= 2]


def plan_letterform_priors(regions, src_px_mm: float, grid_px_mm: float,
                           k: float = K_DEFAULT, words: bool = False) -> list[LetterOutcome]:
    """Every text-tagged member of every word, fitted; nothing written back.
    `src_px_mm` is the source image's pixel at the design size
    (`1 / Prep.input_px_per_mm`), `grid_px_mm` the working grid's
    (`1 / Prep.px_per_mm`); the fit touches a word only when `k * src_px_mm`
    is over the grid pixel, i.e. only an upload stage 1 upscaled."""
    from .textcluster import (_house_chains, _line_of_text_deg, _skeleton_stroke_stats,
                              _stem_slant_deg)
    out: list[LetterOutcome] = []
    for wi, members in enumerate(lettering_words(regions, words)):
        letters = members if words else [r for r in members if r.meta.get("text_candidate")]
        if not letters:
            continue
        line = _line_of_text_deg(members)
        if line is None:
            line = 0.0
        slant = _stem_slant_deg(_house_chains(members), line)
        # the word's stroke width from the engine's own instrument
        halfs = [s.mean_mm for s in (_skeleton_stroke_stats(r) for r in members) if s is not None]
        width_hint = 2.0 * float(np.median(halfs)) if halfs else None
        tol = k * src_px_mm
        # Leans are read against the line's normal (slant 0), so the word's
        # slant and each letter's lean come from one reading.
        normal = (line + 90.0) % 180.0
        leans = [letter_lean_deg(np.asarray(r.polygon.exterior.coords, float), normal, tol)
                 for r in letters]
        known = [x for x in leans if x is not None]
        slant_chords = float(np.median(known)) if known else None
        slant_source = "engine"
        if slant_chords is not None and (slant is None or abs(slant - slant_chords) > SLANT_DISAGREE_DEG):
            slant, slant_source = slant_chords, "chords"
        slant = slant or 0.0
        line_degs = None
        arched = False
        if len(known) >= 4:
            core = sorted(known)
            trim = max(1, int(len(core) * 0.2))
            core = core[trim:-trim]
            if core and (core[-1] - core[0]) > ARCH_LEAN_SPREAD_DEG:
                arched = True
        if arched:
            # an arch's lean is linear in position along the line; a robust
            # line through (position, lean) gives each letter its lean with a
            # diagonal-letter misread (an A's legs) voted down
            u = np.array([math.cos(math.radians(line)), math.sin(math.radians(line))])
            pos = np.array([float(np.array([r.polygon.centroid.x, r.polygon.centroid.y]) @ u)
                            for r in letters])
            pts = [(p, x) for p, x in zip(pos, leans) if x is not None]
            slopes = [(x2 - x1) / (p2 - p1) for i, (p1, x1) in enumerate(pts)
                      for (p2, x2) in pts[i + 1:] if abs(p2 - p1) > 1e-6]
            b = float(np.median(slopes)) if slopes else 0.0
            a = float(np.median([x - b * p for p, x in pts]))
            line_degs = [(line + (a + b * p) - slant) % 180.0 for p in pos]
        prior = word_prior([r.polygon for r in letters], line, slant, src_px_mm, grid_px_mm, k,
                           line_degs=line_degs, width_hint_mm=width_hint)
        note = dict(slant_source=slant_source, slant_chords=slant_chords, arched=arched, leans=leans)
        for li, r in enumerate(letters):
            lp = letter_prior(prior, line_degs[li]) if line_degs is not None else prior
            res = fit_letter(r.polygon, lp)
            out.append(LetterOutcome(wi, r.shape_id, r.meta.get("ocr_char"), r.polygon, res, lp,
                                     dict(note)))
    return out


def apply_letterform_priors(regions, src_px_mm: float, grid_px_mm: float,
                            k: float = K_DEFAULT, words: bool = False) -> list[LetterOutcome]:
    """The pipeline's call: fit, then write every accepted refit into its
    region (same `shape_id`, same `meta` plus `letterform_prior`), leaving a
    passed or refused letter's polygon exactly as it was. Returns the
    outcomes for whoever wants the detail (the spike's sheets, a test)."""
    outcomes = plan_letterform_priors(regions, src_px_mm, grid_px_mm, k, words)
    by_id = {o.shape_id: o for o in outcomes}
    for r in regions:
        o = by_id.get(r.shape_id)
        if o is None:
            continue
        r.meta["letterform_prior"] = o.outcome
        if o.fit.status == "refit":
            r.polygon = o.fit.polygon
            r.area_mm2 = o.fit.polygon.area
    return outcomes
