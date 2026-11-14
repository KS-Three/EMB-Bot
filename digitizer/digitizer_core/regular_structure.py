"""Regular structure: what the art repeats is sewn as ONE shape repeated (2026-11-13).

A person digitizing Bridge's ship's wheel draws one handle and repeats it eight
times round the hub. The pipeline traces the pixels of a 400 px JPEG instead,
so its eight handles are eight different lumpy shapes; Kent pinned it: "All of
the wheel handles look different from eachother, this would be better if they
all looked the same." The same family: equal flag stripes, a grid of squares,
a mirrored pair of feet.

This module reads the stage-4 regions (polygons in mm, y down) and finds two
kinds of repetition, both measured against the size of one SOURCE pixel
(`1 / p.input_px_per_mm`), the noise the trace carries:

* **Congruent groups**: separate regions of one thread that are the same shape
  under translation, rotation or mirror. Each group is fitted to the
  arrangement it sits in -- N-fold rotation about a centre, a row or grid at
  equal pitch (a lattice), a mirrored pair -- or none ("loose").
* **Self-symmetry**: ONE region that repeats itself round its centre. Bridge's
  wheel is a single region (rim + eight handles in one black), so no grouping
  of regions can see its handles.

`find_groups` and `find_self_symmetry` only read (the census tool prints
them). `apply_regular_structure` (`cfg.regular_structure`, built OFF) replaces
each confirmed member by the group's mean shape -- the aligned average of the
members' signed distance fields, which also averages the pixel noise out --
placed at its own fitted position on the fitted arrangement, and tags
`meta["congruent_group"]` (`id`, `kind`, `n`, `index`, `angle_deg`, `mirror`,
`moved`) so later stages can decide tier and angle once per group. A
self-symmetric region becomes the average of its own N rotations (and
mirrors, when it is mirror-symmetric too).

Guards (when in doubt, do nothing):

* lettering is out of scope: text-cluster / word / small-text members are
  never candidates;
* a group needs three members on an arrangement (a mirrored pair two); a
  "loose" set of look-alikes is reported, never moved;
* every member within `MATCH_PX` source pixels (mean boundary distance),
  `DIL_PX` (uniform dilation: a deliberate SIZE step is refused) and
  `HAUS_PX` (worst point: a deliberate SHAPE difference) of the mean shape;
* no outline moves further than `MOVE_PX` source pixels, and nothing is
  redrawn when no member would move more than `FLOOR_MM` (the Design unit)
  and `POS_PX` source pixels;
* a SEAM with a region of another colour is held where it was traced (a
  region lying under the member is a layer, not a seam);
* a self-repeat must have parts that stick out (`SELF_SOLIDITY_MAX`).

What the census found (2026-11-13, eleven designs): only Bridge's wheel is a
stage-4 geometry fault. The rest of the family Kent pinned is later: the
flag's stripes already agree to 0.015 mm (their widths come from pull), its
stars and toat's rule lines are congruent but sew at different satin angles,
the mascot's feet and the emoji's legs are not congruent at all (the same
thread lit at different fill angles), and Jakarta's dot grid is claimed by
the text tagger. The tag is the table those stages read.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from shapely import affinity
from shapely.geometry import Polygon
from shapely.ops import unary_union

# Mean boundary distance between a member and the group's mean shape, in
# source pixels: the trace noise a member may carry and still be the group's
# shape. Bridge's wheel (a 400 px JPEG, 4.4 px/mm) has its worst handle 1.15
# px off the mean of the eight while their uniform dilations stay within
# -0.17..+0.07 px: noise, not a different handle. A different SHAPE is the
# worst-point gate's job, a different SIZE the dilation gate's.
MATCH_PX = 1.5
# Uniform dilation of a member against the mean shape (area difference over
# perimeter), in source pixels. Noise wanders in and out along an outline and
# nets out; a deliberate size step moves the whole outline one way. Half a
# pixel admits the first and refuses a one-pixel step.
DIL_PX = 0.5
# The worst point of a member against the mean shape, in source pixels.
HAUS_PX = 4.0
# The furthest any member's outline may move (Hausdorff old -> new).
MOVE_PX = 3.0
# Nothing is redrawn unless it would move by more than this, mm: the Design
# contract's own unit (0.1 mm integers, `adapter`). Kent's flag shows why:
# its stripes and stars already agree to 0.05-0.09 mm, and redrawing them
# that little re-planned the long red satin (500 -> 1,399 stitches, the
# columns tilted 5 deg) for no change anyone could see. Such a group keeps
# its traced outlines and still carries its tag. The floor is also never
# below the arrangement's own tolerance (`POS_PX`): Kent's QR has its three
# finder rings within 0.03 mm, and putting one 0.11 mm onto the fitted
# lattice let a sliver of it out from under the white layer that hides them.
FLOOR_MM = 0.1
# A member smaller than this many square source pixels is trace noise.
MIN_AREA_PX2 = 12.0
# Pair alignments one design may spend finding groups (each ~150 outline
# comparisons); past it the design has too many look-alikes to be a logo's
# few repeats, and nothing is done. The census's busiest design, Kent's flag
# (50 stars), spent 128 alignments in all (17 s on a loaded laptop); the
# drone's 117 regions 101.
MAX_ALIGNS = 2000
# Arrangement fit: a centroid may sit this many source pixels off the fit.
POS_PX = 1.5
# Self-symmetry folds tried, largest first, and how many that pass the
# screen are built and measured before giving up on a region.
FOLDS = (12, 10, 9, 8, 7, 6, 5, 4, 3)
MAX_FOLD_TRIES = 2
# A region is a self-repeat only when its outline is this far from convex
# (exterior area over its convex hull's): it has parts that stick out.
SELF_SOLIDITY_MAX = 0.9
# Lettering is out of scope: a region carrying a key with any of these
# prefixes was tagged by a text reader (text clusters, words, small text,
# letterform priors) and is never a member. NOT the house-angle group
# (`lettering_group`): that grouper takes any small repeated shape, and on
# Kent's flag it holds all fifty stars.
TEXT_PREFIXES = ("text_", "word_", "small_text", "letterform")
META_KEY = "congruent_group"


# --------------------------------------------------------------------------
# geometry helpers


def _largest(g):
    if g is None or g.is_empty:
        return None
    if isinstance(g, Polygon):
        return g
    polys = [p for p in getattr(g, "geoms", []) if isinstance(p, Polygon) and not p.is_empty]
    return max(polys, key=lambda p: p.area) if polys else None


def mean_dev(a, b) -> float:
    """Mean boundary distance between two outlines, mm: symmetric-difference
    area over the mean perimeter (exact for a uniform offset)."""
    per = 0.5 * (a.length + b.length)
    if per <= 0:
        return math.inf
    return a.symmetric_difference(b).area / per


def _haus(a, b) -> float:
    return a.boundary.hausdorff_distance(b.boundary)


def _place(template, cx, cy, ang, mirror):
    """Template (canonical frame, centroid at origin) -> member frame."""
    g = template
    if mirror:
        g = affinity.scale(g, 1.0, -1.0, origin=(0.0, 0.0))
    if ang:
        g = affinity.rotate(g, ang, origin=(0.0, 0.0), use_radians=True)
    return affinity.translate(g, cx, cy)


def _canon(poly, cx, cy, ang, mirror):
    """Member frame -> canonical frame (inverse of `_place`)."""
    g = affinity.translate(poly, -cx, -cy)
    if ang:
        g = affinity.rotate(g, -ang, origin=(0.0, 0.0), use_radians=True)
    if mirror:
        g = affinity.scale(g, 1.0, -1.0, origin=(0.0, 0.0))
    return g


def _moments(poly):
    """sqrt of the two principal second moments (mm), rotation invariant."""
    from shapely.geometry.polygon import orient
    poly = orient(poly, 1.0)   # exterior CCW, holes CW: the hole terms subtract
    c = poly.centroid
    sxx = syy = sxy = 0.0
    for ring in [poly.exterior, *poly.interiors]:
        r = np.asarray(ring.coords) - (c.x, c.y)
        x0, y0, x1, y1 = r[:-1, 0], r[:-1, 1], r[1:, 0], r[1:, 1]
        cr = x0 * y1 - x1 * y0
        syy += np.sum(cr * (y0 * y0 + y0 * y1 + y1 * y1)) / 12.0
        sxx += np.sum(cr * (x0 * x0 + x0 * x1 + x1 * x1)) / 12.0
        sxy += np.sum(cr * (x0 * y1 + 2 * x0 * y0 + 2 * x1 * y1 + x1 * y0)) / 24.0
    a = abs(poly.area) or 1.0
    m = np.array([[sxx, sxy], [sxy, syy]]) / a
    w = np.linalg.eigvalsh(m)
    return float(math.sqrt(max(w[1], 0.0))), float(math.sqrt(max(w[0], 0.0)))


@dataclass
class _Shape:
    idx: int
    poly: Polygon
    cx: float
    cy: float
    area: float
    perim: float
    m1: float
    m2: float
    holes: int


def _shape(idx, poly) -> _Shape:
    c = poly.centroid
    m1, m2 = _moments(poly)
    return _Shape(idx, poly, c.x, c.y, poly.area, poly.length, m1, m2, len(poly.interiors))


def _similar(a: _Shape, b: _Shape, tol: float) -> bool:
    """Cheap first pass: congruent shapes agree on area, perimeter and the
    two principal moments to within what `tol` (mm of boundary) moves."""
    if a.holes != b.holes:
        return False
    per = 0.5 * (a.perim + b.perim)
    if abs(a.area - b.area) > 2.5 * tol * per + 1e-9:
        return False
    if abs(a.perim - b.perim) > 0.25 * per + 8 * tol:
        return False
    return abs(a.m1 - b.m1) <= 3 * tol and abs(a.m2 - b.m2) <= 3 * tol


def _align(ref_canon, s: _Shape, mirror_ok=True, margin=0.0):
    """(dev, ang, mirror) of the best rigid fit of `s` onto `ref_canon`. A
    mirror is chosen only when it fits better by `margin` mm and by 40%: a
    shape that is its own mirror image (a square, a disc) stays unmirrored,
    so one group does not split on noise into mirrored and unmirrored
    members."""
    fits = []
    for m in ((False, True) if mirror_ok else (False,)):
        best = (math.inf, 0.0, m)
        coarse = []
        for k in range(24):
            ang = k * math.pi / 12
            d = mean_dev(ref_canon, _canon(s.poly, s.cx, s.cy, ang, m))
            coarse.append((d, ang))
        coarse.sort()
        for d0, a0 in coarse[:2]:
            cur = (d0, a0)
            for step in (math.radians(3.0), math.radians(0.6), math.radians(0.12)):
                for k in range(-4, 5):
                    ang = cur[1] + k * step
                    d = mean_dev(ref_canon, _canon(s.poly, s.cx, s.cy, ang, m))
                    if d < cur[0]:
                        cur = (d, ang)
            if cur[0] < best[0]:
                best = (cur[0], cur[1] % (2 * math.pi), m)
        fits.append(best)
    if len(fits) == 2 and fits[1][0] < fits[0][0] - margin and fits[1][0] < 0.6 * fits[0][0]:
        return fits[1]
    return fits[0]


def _symmetry_order(tmpl, tol) -> int:
    """How many times the template repeats itself in a turn (8 stands for
    "round": any angle fits)."""
    if _roundness(tmpl) > 0.97:
        return 8
    c = tmpl.centroid
    for k in (8, 6, 4, 3, 2):
        if mean_dev(tmpl, affinity.rotate(tmpl, 360.0 / k, origin=c)) <= tol:
            return k
    return 1


# --------------------------------------------------------------------------
# signed-distance mean shape


_SHIFT = 4   # cv2.fillPoly sub-pixel bits


def _rasterize(poly, x0, y0, res, shape):
    """Pixel-centre fill of `poly` on the grid (row = y, col = x)."""
    import cv2
    mask = np.zeros(shape, dtype=np.uint8)
    k = float(1 << _SHIFT)

    def pts(ring):
        a = np.asarray(ring.coords)
        return np.rint(np.column_stack([(a[:, 0] - x0) / res, (a[:, 1] - y0) / res]) * k
                       ).astype(np.int32).reshape(-1, 1, 2)

    cv2.fillPoly(mask, [pts(poly.exterior)], 1, lineType=cv2.LINE_8, shift=_SHIFT)
    if poly.interiors:
        cv2.fillPoly(mask, [pts(h) for h in poly.interiors], 0, lineType=cv2.LINE_8, shift=_SHIFT)
    return mask.astype(bool)


def _sdf(mask, res):
    """Signed distance in mm, negative inside."""
    import cv2
    m = mask.astype(np.uint8)
    inside = cv2.distanceTransform(m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    outside = cv2.distanceTransform(1 - m, cv2.DIST_L2, cv2.DIST_MASK_PRECISE)
    return (outside - inside).astype(np.float64) * res


def _contour_polygon(field_, x0, y0, res):
    """Zero level set of a signed field (negative inside) -> one Polygon."""
    from skimage.measure import find_contours
    rings = []
    for c in find_contours(-field_, 0.0):
        if len(c) < 4:
            continue
        xy = np.column_stack([x0 + c[:, 1] * res, y0 + c[:, 0] * res])
        p = Polygon(xy)
        if not p.is_valid:
            p = _largest(p.buffer(0))
        if p is not None and p.area > res * res:
            rings.append(p)
    if not rings:
        return None
    rings.sort(key=lambda p: -p.area)
    shells: list[list] = []
    for r in rings:
        host = None
        for sh in shells:
            if sh[0].contains(r.representative_point()):
                inside_hole = any(h.contains(r.representative_point()) for h in sh[1])
                if not inside_hole:
                    host = sh
                    break
        if host is None:
            shells.append([r, []])
        else:
            host[1].append(r)
    polys = [Polygon(sh[0].exterior.coords, [h.exterior.coords for h in sh[1]]) for sh in shells]
    g = unary_union([p.buffer(0) for p in polys])
    return _largest(g.simplify(res * 0.4, preserve_topology=True))


def _mean_shape(canon_polys, res):
    """Aligned average of `canon_polys` (signed distance mean, zero set)."""
    b = np.array([p.bounds for p in canon_polys])
    pad = 4 * res
    x0, y0 = b[:, 0].min() - pad, b[:, 1].min() - pad
    x1, y1 = b[:, 2].max() + pad, b[:, 3].max() + pad
    shape = (int(math.ceil((y1 - y0) / res)) + 1, int(math.ceil((x1 - x0) / res)) + 1)
    acc = np.zeros(shape)
    for p in canon_polys:
        acc += _sdf(_rasterize(p, x0, y0, res, shape), res)
    acc /= len(canon_polys)
    return _contour_polygon(acc, x0, y0, res)


# --------------------------------------------------------------------------
# arrangements


def _circ_mean(angles):
    return math.atan2(sum(math.sin(a) for a in angles), sum(math.cos(a) for a in angles))


def _wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def _fit_rotation(cs, angs, pos_tol, ang_tol=math.radians(4.0)):
    """N-fold rotation about a fitted centre. -> (params, fitted [(x, y, ang)]) or None."""
    n = len(cs)
    if n < 3:
        return None
    x, y = cs[:, 0], cs[:, 1]
    A = np.column_stack([x, y, np.ones(n)])
    rhs = -(x * x + y * y)
    try:
        sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
    except np.linalg.LinAlgError:
        return None
    cx, cy = -sol[0] / 2, -sol[1] / 2
    rad = np.hypot(x - cx, y - cy)
    r = float(rad.mean())
    if r < 4 * pos_tol or np.abs(rad - r).max() > pos_tol:
        return None
    phi = np.arctan2(y - cy, x - cx)
    order = np.argsort(phi)
    step = 2 * math.pi / n
    k = np.empty(n, dtype=int)
    k[order] = np.arange(n)
    phi0 = _circ_mean([phi[i] - k[i] * step for i in range(n)])
    fit_phi = [phi0 + k[i] * step for i in range(n)]
    if max(abs(_wrap(phi[i] - fit_phi[i])) for i in range(n)) * r > pos_tol:
        return None
    beta = _circ_mean([angs[i] - phi[i] for i in range(n)])
    if max(abs(_wrap(angs[i] - phi[i] - beta)) for i in range(n)) > ang_tol:
        return None
    fitted = [(cx + r * math.cos(fit_phi[i]), cy + r * math.sin(fit_phi[i]), fit_phi[i] + beta)
              for i in range(n)]
    return {"kind": "rotation", "fold": n, "centre": [round(cx, 4), round(cy, 4)],
            "radius": round(r, 4)}, fitted


def _fit_lattice(cs, angs, pos_tol, ang_tol=math.radians(3.0)):
    """Row or grid at equal pitch (some sites may be empty). Members must
    all face one way. -> (params, fitted) or None."""
    n = len(cs)
    if n < 3:
        return None
    a0 = _circ_mean(angs)
    if max(abs(_wrap(a - a0)) for a in angs) > ang_tol:
        return None
    d = cs[None, :, :] - cs[:, None, :]
    vecs = d.reshape(-1, 2)
    L = np.hypot(vecs[:, 0], vecs[:, 1])
    ok = L > 4 * pos_tol
    if not ok.any():
        return None
    vecs, L = vecs[ok], L[ok]
    v1 = vecs[np.argmin(L)]
    if v1[0] < 0 or (v1[0] == 0 and v1[1] < 0):
        v1 = -v1
    u1 = v1 / np.linalg.norm(v1)
    perp = np.abs(vecs @ np.array([-u1[1], u1[0]]))
    off = perp > 4 * pos_tol
    v2 = None
    if off.any():
        cand = vecs[off]
        cl = np.hypot(cand[:, 0], cand[:, 1])
        v2 = cand[np.argmin(cl)]
    basis = [v1] if v2 is None else [v1, v2]
    B = np.column_stack(basis)
    rel = cs - cs[0]
    coef, *_ = np.linalg.lstsq(B, rel.T, rcond=None)
    ij = np.rint(coef.T).astype(int)
    # refit origin + basis by least squares on the integer sites
    M = np.column_stack([np.ones(n), ij])
    sol, *_ = np.linalg.lstsq(M, cs, rcond=None)
    fit = M @ sol
    resid = np.hypot(*(fit - cs).T)
    if resid.max() > pos_tol:
        return None
    if len({tuple(r) for r in ij}) != n:
        return None
    kind = "row" if v2 is None or len(set(ij[:, 1])) == 1 else "grid"
    pitch = [round(float(np.hypot(*sol[1 + i])), 4) for i in range(len(basis))]
    fitted = [(float(fit[i, 0]), float(fit[i, 1]), a0) for i in range(n)]
    return {"kind": kind, "pitch_mm": pitch}, fitted


def _fit_mirror_pair(cs, angs, pos_tol, ang_tol=math.radians(4.0)):
    if len(cs) != 2:
        return None
    (x1, y1), (x2, y2) = cs
    a1, a2 = angs
    psi_o = 0.5 * (a1 + a2)
    psi_c = math.atan2(y2 - y1, x2 - x1) + math.pi / 2
    # axis directions are mod pi
    dd = _wrap(2 * (psi_o - psi_c)) / 2
    if abs(dd) > ang_tol:
        return None
    psi = psi_c + dd / 2
    mx, my = 0.5 * (x1 + x2), 0.5 * (y1 + y2)
    nx, ny = math.cos(psi + math.pi / 2), math.sin(psi + math.pi / 2)
    h = 0.5 * ((x2 - x1) * nx + (y2 - y1) * ny)
    # move nothing along the axis beyond the midpoint split
    e = _wrap(2 * psi - a1 - a2) / 2
    fitted = [(mx - h * nx, my - h * ny, a1 + e), (mx + h * nx, my + h * ny, a2 + e)]
    if max(math.hypot(fitted[i][0] - cs[i][0], fitted[i][1] - cs[i][1]) for i in range(2)) > pos_tol:
        return None
    return {"kind": "mirror_pair", "axis_deg": round(math.degrees(psi) % 180.0, 3),
            "midpoint": [round(mx, 4), round(my, 4)]}, fitted




# --------------------------------------------------------------------------
# detection


@dataclass
class Member:
    idx: int
    shape_id: str
    ang: float
    mirror: bool
    dev_mm: float = 0.0
    haus_mm: float = 0.0
    dil_mm: float = 0.0
    fitted: tuple | None = None
    why: str = ""            # "" = within every gate


@dataclass
class Group:
    gid: str
    thread_index: int
    members: list[Member]
    template: Polygon | None = None
    arrangement: dict = field(default_factory=dict)
    confirmed: bool = False
    reason: str = ""

    @property
    def ok(self) -> list[Member]:
        return [m for m in self.members if not m.why]


@dataclass
class SelfSym:
    idx: int
    shape_id: str
    thread_index: int
    fold: int
    mirror: bool
    axis: float | None
    devs: dict = field(default_factory=dict)
    sym: Polygon | None = None
    wedge_devs: list = field(default_factory=list)
    wedge_haus: list = field(default_factory=list)
    wedge_dils: list = field(default_factory=list)
    confirmed: bool = False
    reason: str = ""


def _candidate(r, min_area) -> bool:
    if any(str(k).startswith(TEXT_PREFIXES) for k in r.meta):
        return False
    if r.meta.get("enclosed_background") or r.meta.get("counter"):
        return False
    g = r.polygon
    return isinstance(g, Polygon) and g.is_valid and not g.is_empty and g.area >= min_area


def src_px_mm(p) -> float:
    """One source pixel in mm: the noise a trace of the upload carries."""
    ipm = float(getattr(p, "input_px_per_mm", 0.0) or 0.0)
    if ipm > 0:
        return 1.0 / ipm
    ppm = float(getattr(p, "px_per_mm", 0.0) or 0.0)
    return 1.0 / ppm if ppm > 0 else 0.1


def _gate(dev, haus, dil, src, match_px) -> str:
    """Why a member is NOT the group's shape, or "" when it is."""
    if dev > match_px * src:
        return "mean distance"
    if abs(dil) > DIL_PX * src:
        return "size step"
    if haus > HAUS_PX * src:
        return "worst point"
    return ""


def _fit_member(tmpl, s: _Shape, src_px):
    d, a, m = _align(tmpl, s, margin=0.25 * src_px)
    placed = _place(tmpl, s.cx, s.cy, a, m)
    dil = (s.area - tmpl.area) / max(0.5 * (s.perim + tmpl.length), 1e-9)
    return d, a, m, _haus(placed, s.poly), dil


def _res(src_px):
    return max(0.02, min(0.08, src_px / 4.0))


def find_groups(regions, src_px, *, match_px=MATCH_PX, any_colour=False,
                pos_px=POS_PX) -> list[Group]:
    """Congruent groups among `regions` (read only). Every group with two or
    more look-alikes is returned with its numbers; `confirmed` says whether
    `apply_regular_structure` may act on it."""
    tol = match_px * src_px
    res = _res(src_px)
    min_area = MIN_AREA_PX2 * src_px * src_px
    shapes = [_shape(i, r.polygon) for i, r in enumerate(regions) if _candidate(r, min_area)]
    shapes.sort(key=lambda s: (-s.area, regions[s.idx].shape_id))
    seeds: list[tuple[_Shape, Polygon, list]] = []
    aligns = 0
    for s in shapes:
        placed = False
        for rep, rep_c, mem in seeds:
            if not any_colour and regions[rep.idx].thread_index != regions[s.idx].thread_index:
                continue
            if not _similar(rep, s, tol):
                continue
            aligns += 1
            if aligns > MAX_ALIGNS:
                return []    # too many look-alikes to compare: do nothing
            # two noisy traces differ by up to twice what one differs from the mean
            d, ang, m = _align(rep_c, s, margin=0.25 * src_px)
            if d <= 2 * tol:
                mem.append((s, ang, m))
                placed = True
                break
        if not placed:
            seeds.append((s, _canon(s.poly, s.cx, s.cy, 0.0, False), [(s, 0.0, False)]))
    groups = []
    for rep, _rep_c, mem in seeds:
        if len(mem) < 2:
            continue
        g = _confirm_group(regions, mem, tol, src_px, match_px, res, pos_px)
        if g is not None:
            groups.append(g)
    groups.sort(key=lambda g: (g.thread_index, -len(g.members), g.members[0].shape_id))
    for k, g in enumerate(groups):
        g.gid = f"G{k + 1}"
    return groups


def _confirm_group(regions, mem, tol, src_px, match_px, res, pos_px) -> Group | None:
    """Mean shape, members measured against it, outliers set aside (twice at
    most), angles brought to one sense, arrangement fitted."""
    live = list(mem)
    dropped: dict[int, tuple] = {}
    tmpl = None
    fits: dict[int, tuple] = {}
    for _round in range(3):
        canon = [_canon(s.poly, s.cx, s.cy, a, m) for s, a, m in live]
        tmpl = _mean_shape(canon, res)
        if tmpl is None:
            return None
        c = tmpl.centroid
        tmpl = affinity.translate(tmpl, -c.x, -c.y)
        fits = {s.idx: _fit_member(tmpl, s, src_px) for s, _, _ in live}
        bad = [s for s, _, _ in live
               if _gate(fits[s.idx][0], fits[s.idx][3], fits[s.idx][4], src_px, match_px)]
        if not bad or len(live) - len(bad) < 2:
            break
        for s in bad:
            dropped[s.idx] = fits[s.idx]
        live = [(s, fits[s.idx][1], fits[s.idx][2]) for s, _, _ in live if s not in bad]
    members = []
    for s, _, _ in live:
        d, a, m, h, dil = fits[s.idx]
        members.append(Member(s.idx, regions[s.idx].shape_id, a, m, d, h, dil,
                              why=_gate(d, h, dil, src_px, match_px)))
    for idx, (d, a, m, h, dil) in dropped.items():
        members.append(Member(idx, regions[idx].shape_id, a, m, d, h, dil,
                              why=_gate(d, h, dil, src_px, match_px) or "set aside"))
    members.sort(key=lambda mm: mm.shape_id)
    ok = [mm for mm in members if not mm.why]
    if ok:
        # A template that repeats itself k times in a turn (a square: 4) fits
        # each member at k angles; bring every member to the one nearest the
        # first's, so a grid of squares reads as facing one way.
        order = _symmetry_order(tmpl, 0.5 * tol)
        a_ref, m_ref = ok[0].ang, ok[0].mirror
        for mm in ok:
            if order >= 8:
                if mm.mirror == m_ref:
                    mm.ang = a_ref
            elif order > 1:
                per = 2 * math.pi / order
                mm.ang = a_ref + ((mm.ang - a_ref + per / 2) % per) - per / 2
    g = Group("", regions[members[0].idx].thread_index, members, tmpl)
    g.arrangement = (_arrangement(ok, regions, pos_px * src_px, _ang_tol(tmpl, pos_px * src_px))
                     if len(ok) >= 2 else {"kind": "none"})
    kind = g.arrangement["kind"]
    if len(ok) < 2:
        g.reason = "members not alike"
    elif kind in ("rotation", "row", "grid") and len(ok) >= 3:
        g.confirmed = True
    elif kind == "mirror_pair":
        g.confirmed = True
    else:
        # A "loose" set of look-alikes (small blobs are all alike at a few
        # source pixels) is reported, never acted on.
        g.reason = "no arrangement"
    return g


def _ang_tol(tmpl, pos_tol) -> float:
    """How far members' orientations may scatter round the arrangement's:
    3 degrees, or as much as moves the member's furthest point no more than
    the position tolerance (a lump tilts a 3 mm square's best fit by more
    than 3 degrees while moving nothing past a pixel)."""
    rad = max(math.hypot(x, y) for x, y in tmpl.exterior.coords)
    return max(math.radians(3.0), pos_tol / max(rad, 1e-6))


def _arrangement(ok: list[Member], regions, pos_tol, ang_tol=math.radians(3.0)) -> dict:
    cs = np.array([[regions[m.idx].polygon.centroid.x, regions[m.idx].polygon.centroid.y]
                   for m in ok])
    angs = [m.ang for m in ok]
    mirrors = {m.mirror for m in ok}
    fit = None
    if len(ok) == 2:
        if mirrors == {False, True}:
            order = sorted(range(2), key=lambda i: ok[i].mirror)   # unmirrored first
            fit = _fit_mirror_pair(cs[order], [angs[i] for i in order], pos_tol, ang_tol)
            if fit is not None:
                params, fitted = fit
                back = [None, None]
                for j, i in enumerate(order):
                    back[i] = fitted[j]
                fit = (params, back)
    elif len(mirrors) == 1:
        fit = _fit_rotation(cs, angs, pos_tol, ang_tol) or _fit_lattice(cs, angs, pos_tol, ang_tol)
    if fit is None:
        for m in ok:
            c = regions[m.idx].polygon.centroid
            m.fitted = (c.x, c.y, m.ang)
        return {"kind": "loose" if len(ok) >= 3 else "pair"}
    params, fitted = fit
    for m, f in zip(ok, fitted):
        m.fitted = f
    return params


def find_self_symmetry(regions, src_px, *, match_px=MATCH_PX, folds=FOLDS,
                       res=None, skip=()) -> list[SelfSym]:
    """Single regions that repeat themselves N times round their centroid.

    Screened like a group: one copy against the next may differ by twice the
    tolerance (two noisy traces), and must fit at least twice as well as the
    copy turned HALF a step (a shape that repeats N times fits at 360/N and
    not between; a roundish blob fits about as well everywhere and is not a
    repeat). Then the symmetrized mean is built and EVERY repeat (one wedge
    of 360/N degrees) must pass the member gates against it. Folds that pass
    the screen are tried largest first, at most `MAX_FOLD_TRIES`. Every
    screened region is returned; `confirmed` says whether it may be acted on."""
    tol = match_px * src_px
    res = res or _res(src_px)
    min_area = MIN_AREA_PX2 * src_px * src_px * 8
    out = []
    for i, r in enumerate(regions):
        if i in skip or not _candidate(r, min_area):
            continue
        g = r.polygon
        # a disc (or a ring) is symmetric at every fold and repeats nothing;
        # nor does a convex blob: something must stick out to be repeated
        # (Bridge's handles, a star's points, a gear's teeth). The precision
        # drone's 2 mm2 grey blob read as a rounded triangle without this.
        ext = Polygon(g.exterior.coords)
        if _roundness(g) > 0.95 or ext.area > SELF_SOLIDITY_MAX * ext.convex_hull.area:
            continue
        c = g.centroid
        devs, hits = {}, []
        for n in folds:
            d = mean_dev(g, affinity.rotate(g, 360.0 / n, origin=c))
            devs[n] = round(d, 4)
            if d > 2 * tol:
                continue
            if mean_dev(g, affinity.rotate(g, 180.0 / n, origin=c)) < 2 * d:
                continue
            if all(mean_dev(g, affinity.rotate(g, 360.0 * k / n, origin=c)) <= 2 * tol
                   for k in range(2, n // 2 + 1)):
                hits.append(n)
        first = None
        for n in hits[:MAX_FOLD_TRIES]:
            s = _try_fold(i, r, g, c, n, devs, tol, src_px, match_px, res)
            first = first or s
            if s.confirmed:
                first = s
                break
        if first is not None:
            out.append(first)
    return out


def _try_fold(i, r, g, c, n, devs, tol, src_px, match_px, res) -> SelfSym:
    axis = _mirror_axis(g, c, n, 2 * tol)
    s = SelfSym(i, r.shape_id, r.thread_index, n, axis is not None, axis, devs)
    s.sym = symmetrize(g, c, n, axis, res)
    if s.sym is None:
        s.reason = "no mean shape"
        return s
    # Two wedge phases, centred on the furthest point and half a step
    # round: a rectangle read as 4-fold splits each side between two
    # corner-centred wedges and its long and short sides net out there, but
    # not in side-centred ones.
    whys = []
    for phase in (0.0, 0.5):
        wd, wh, wl = _wedge_devs(g, s.sym, c, n, phase)
        if phase == 0.0:
            s.wedge_devs, s.wedge_haus, s.wedge_dils = wd, wh, wl
        whys += [_gate(d, h, l, src_px, match_px) for d, h, l in zip(wd, wh, wl)]
    s.reason = next((w for w in whys if w), "")
    s.confirmed = not s.reason
    return s


def _wedge_devs(g, sym, c, n, phase=0.0):
    """Per repeat: mean boundary distance, worst point and uniform dilation
    of `g` against `sym`, inside each of n wedges centred on `g`'s furthest
    point (turned `phase` of a wedge further round)."""
    ext = np.asarray(g.exterior.coords)
    rad = np.hypot(ext[:, 0] - c.x, ext[:, 1] - c.y)
    far = int(np.argmax(rad))
    a0 = math.atan2(ext[far, 1] - c.y, ext[far, 0] - c.x) - math.pi / n + phase * 2 * math.pi / n
    R = 4.0 * max(float(rad.max()), 1.0)
    diff = g.symmetric_difference(sym)
    devs, haus, dils = [], [], []
    for k in range(n):
        t0 = a0 + 2 * math.pi * k / n
        steps = [t0 + (2 * math.pi / n) * j / 8 for j in range(9)]
        wedge = Polygon([(c.x, c.y)] + [(c.x + R * math.cos(t), c.y + R * math.sin(t)) for t in steps])
        gb = g.boundary.intersection(wedge)
        per = gb.length
        devs.append(diff.intersection(wedge).area / per if per > 0 else 0.0)
        dils.append((g.intersection(wedge).area - sym.intersection(wedge).area) / per if per > 0 else 0.0)
        sb = sym.boundary.intersection(wedge.buffer(1e-6))
        haus.append(gb.hausdorff_distance(sb) if not gb.is_empty and not sb.is_empty else 0.0)
    return devs, haus, dils


def _roundness(g) -> float:
    """Exterior area over the area of a disc of the same perimeter."""
    ext = Polygon(g.exterior.coords)
    return 4 * math.pi * ext.area / max(ext.length ** 2, 1e-12)


def _mirror_axis(g, c, n, tol):
    """An axis through c the region is mirror-symmetric about, or None."""
    # the mirror axes of an n-fold shape repeat every 180/n degrees
    span = 180.0 / n
    best = None
    for k in range(int(math.ceil(span))):
        ang = math.radians(float(k))
        d = mean_dev(g, _reflect(g, c, ang))
        if best is None or d < best[0]:
            best = (d, ang)
    for step in (math.radians(0.25), math.radians(0.05)):
        for k in range(-4, 5):
            ang = best[1] + k * step
            d = mean_dev(g, _reflect(g, c, ang))
            if d < best[0]:
                best = (d, ang)
    if best is None or best[0] > tol:
        return None
    return best[1]


def _reflect(g, c, ang):
    """`g` mirrored across the line through c at `ang` radians."""
    t = affinity.translate(g, -c.x, -c.y)
    t = affinity.rotate(t, -ang, origin=(0, 0), use_radians=True)
    t = affinity.scale(t, 1.0, -1.0, origin=(0, 0))
    t = affinity.rotate(t, ang, origin=(0, 0), use_radians=True)
    return affinity.translate(t, c.x, c.y)


def symmetrize(g, c, n, mirror_axis, res):
    """The mean of `g`'s n rotations about c (and their mirrors)."""
    copies = [affinity.rotate(g, 360.0 * k / n, origin=c) for k in range(n)]
    if mirror_axis is not None:
        m = _reflect(g, c, mirror_axis)
        copies += [affinity.rotate(m, 360.0 * k / n, origin=c) for k in range(n)]
    return _mean_shape(copies, res)


# --------------------------------------------------------------------------
# apply


def _hold_seams(new, old, others, band):
    """`new` with every seam against `others` (other colours) held where
    `old` traced it: clipped off them, and refilled from `old` within `band`
    of them."""
    if others is None or others.is_empty:
        return _own_holes(new, old)
    near = others.buffer(band)
    out = new.difference(others).union(old.intersection(near).difference(others))
    return _own_holes(_largest(out.buffer(0)), old)


def _own_holes(new, old):
    """`new` keeping only the holes that answer one of `old`'s: where the
    mean outline pulls back from a seam it held, the gap between the two is
    a sliver, not a hole the art has."""
    if new is None or not new.interiors:
        return new
    old_holes = [Polygon(h) for h in old.interiors]
    keep = []
    for h in new.interiors:
        hp = Polygon(h)
        if any(hp.intersection(oh).area > 0.5 * min(hp.area, oh.area) for oh in old_holes):
            keep.append(h)
    if len(keep) == len(new.interiors):
        return new
    return Polygon(new.exterior, keep)


def _neighbours(regions, i, band):
    """Regions of another thread that share a SEAM with region i. One lying
    under (or over) most of it is a layer, not a seam -- stage-4 regions
    stack (a QR finder's black core sits on a white square) -- and is left
    out, or holding against it would erase the member."""
    r = regions[i]
    env = r.polygon.buffer(band)
    others = [o.polygon for j, o in enumerate(regions)
              if j != i and o.thread_index != r.thread_index and o.polygon.intersects(env)
              and o.polygon.intersection(r.polygon).area <= 0.5 * r.polygon.area]
    return unary_union(others) if others else None


def _replace(regions, i, new, band, cap):
    """Put `new` in for region i under the guards -> (moved, why, move_mm)."""
    r = regions[i]
    new = _hold_seams(new, r.polygon, _neighbours(regions, i, band), band)
    if new is None or not new.is_valid or len(new.interiors) != len(r.polygon.interiors):
        return False, "seam hold broke the shape", None
    move = _haus(new, r.polygon)
    if move > cap:
        return False, "move past cap", move
    r.polygon = new
    r.area_mm2 = float(new.area)
    return True, "", move


def apply_regular_structure(regions, p, cfg=None, *, match_px=MATCH_PX, move_px=MOVE_PX) -> dict:
    """Replace confirmed members by their group's mean shape (module note).
    Mutates `regions`; returns a report (also what the census prints)."""
    src = src_px_mm(p)
    res = _res(src)
    cap = move_px * src
    band = src
    floor = max(FLOOR_MM, POS_PX * src)
    report = {"src_px_mm": round(src, 4), "groups": [], "self": []}

    for g in find_groups(regions, src, match_px=match_px):
        kind = g.arrangement.get("kind")
        entry = {"id": g.gid, "thread_index": g.thread_index, "n": len(g.members),
                 "confirmed": g.confirmed, "reason": g.reason, **g.arrangement, "members": []}
        report["groups"].append(entry)
        ok = g.ok
        placed = {}
        if g.confirmed:
            placed = {m.idx: _place(g.template, *m.fitted, m.mirror) for m in ok}
        # the group is redrawn only when some member would move past the floor
        redraw = any(_haus(placed[m.idx], regions[m.idx].polygon) > floor for m in ok) \
            if placed else False
        for m in g.members:
            rec = {"shape_id": m.shape_id, "dev_mm": round(m.dev_mm, 4),
                   "haus_mm": round(m.haus_mm, 4), "dil_mm": round(m.dil_mm, 4), "moved": False}
            entry["members"].append(rec)
            if m.why:
                rec["held"] = m.why
                continue
            if not g.confirmed:
                rec["held"] = g.reason
                continue
            fa = m.fitted[2]
            moved = False
            if redraw:
                moved, why, move = _replace(regions, m.idx, placed[m.idx], band, cap)
                rec["moved"] = moved
                if move is not None:
                    rec["move_mm"] = round(move, 4)
                if why:
                    rec["held"] = why
            else:
                rec["held"] = "already regular"
            regions[m.idx].meta[META_KEY] = {
                "id": g.gid, "kind": kind, "n": len(ok), "index": ok.index(m),
                "angle_deg": round(math.degrees(fa) % 360.0, 3), "mirror": bool(m.mirror),
                "moved": bool(moved)}

    # A group member already took its group's shape; it is not re-traced.
    grouped = {i for i, r in enumerate(regions) if META_KEY in r.meta}
    for s in find_self_symmetry(regions, src, match_px=match_px, res=res, skip=grouped):
        r = regions[s.idx]
        c = r.polygon.centroid
        rec = {"shape_id": s.shape_id, "fold": s.fold, "mirror": s.mirror,
               "confirmed": s.confirmed, "reason": s.reason,
               "wedge_dev_mm": [round(v, 4) for v in s.wedge_devs],
               "wedge_dil_mm": [round(v, 4) for v in s.wedge_dils],
               "wedge_haus_mm": [round(v, 4) for v in s.wedge_haus], "moved": False}
        report["self"].append(rec)
        if not s.confirmed:
            continue
        if _haus(s.sym, r.polygon) <= floor:
            # Already regular below the Design unit: re-tracing it through
            # the raster would only round its corners.
            rec["held"] = "already regular"
            continue
        moved, why, move = _replace(regions, s.idx, s.sym, band, cap)
        rec["moved"] = moved
        if move is not None:
            rec["move_mm"] = round(move, 4)
        if why:
            rec["held"] = why
            continue
        r.meta[META_KEY] = {"id": f"R{s.shape_id}", "kind": "self_rotation", "fold": s.fold,
                            "mirror": bool(s.mirror), "centre": [round(c.x, 4), round(c.y, 4)],
                            "moved": True}
    return report
