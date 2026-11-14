"""Thin bars kept whole (`cfg.fine_bar_survive`, built OFF 2026-11-14).

Kent pinned To a T five times for its speed lines (hat: "Missing top bar",
"Gap/Jump in the line", a missing bar; beanie: "Gap in the line" twice). The
art draws each one as a straight dark line 0.3-0.35 mm thick; the pro sews
each as one straight satin bar. Traced on main 2026-11-14 (`eye_pairs_out/
thin-bars-1114/`), three things happen to them, none of them a width:

* **Split.** Stages 2-4 break a line into collinear pieces (anti-aliased
  pixels in the middle read as the page, or a piece falls under the sliver
  floor): hat right-top bar two 6 mm pieces 0.37 mm apart, beanie bottom bar
  20 + 8 mm with a 4 mm hole. Each piece sews as its own bar, so the gap shows.
* **Lost at stage 5.** A bar 0.25 mm thick sits in a hole of the white field
  sewn first. By stage 5 that field is an under-fill (`silhouette_underfill`,
  `keyline_folded`) whose polygon covers the bar's hole, so the bar, clipped
  against it, keeps nothing and is dropped (`SHAPE_NOT_STITCHED`: hat
  top-left 12.7 mm, beanie bottom 27 mm; traced line by line 2026-11-14).
* **Kinked.** A 42 mm bar sews with a Z jog part way along (Kent's
  "Gap/Jump"); its stage-4 polygon wanders no more than a healthy bar's, so
  the jog is made sewing the traced outline, not by the outline.

What this does, on logos (not photographs):

1. **Find the ink bars.** A stage-4 region whose minimum rotated rectangle is
   at most `BAR_MAX_W_MM` across, `BAR_MIN_LEN_MM` long and `BAR_MIN_ASPECT`
   times longer than wide, with no hole, not lettering, not the page's own
   colour (within `PAGE_DE` of `Prep.bg_rgb`, else the garment), and at least
   `INK_CONTRAST_L` L* off the region it sits in.
2. **Read the bar off the art.** In a band along the piece's axis
   (`BAND_MARGIN_MM` either side of it, the art's full length), a pixel is the
   bar's ink when it is nearer (CIE Lab) the bar's thread than the colour it
   sits in; the connected ink through the piece is the art's whole line.
3. **Fit it straight.** That ink, fitted as one straight bar: the
   least-squares centre line and a linearly tapering width, to the ink's two
   ends -- a quadrilateral, at the width stage 4 would trace (one pixel under
   the ink, as a contour through boundary-pixel centres is). Nothing happens
   when the ink is not a straight thin bar: a slice over `BAR_MAX_INK_W_MM`,
   a centre more than `STRAIGHT_MM` off the line, or under
   `REBUILD_MIN_ASPECT` long for its width. A thick slice at an END is
   trimmed off (a bar running into a letter's stroke), not refused.
4. **Redraw only a broken bar.** The piece takes the fitted polygon only
   when the trace broke it: another piece of its thread lies `ABSORB_FRAC`
   inside the fit (a split; that piece leaves the list), the ink runs
   `REBUILD_EXTEND_MM` past the piece (a gap or a lost end), or
   `SLIVER_MIN_MM` of thin other-colour region lies along it (its
   anti-aliased edge traced as a shape of its own, where the hat's 42 mm bar
   jogged). A whole bar keeps its outline: Fremont's "|" divider sews
   straight already, and a redraw from the anti-aliased ink only widened it.
5. **Survives stage 5.** Every such bar, redrawn or not, is tagged
   `meta[FINE_BAR_KEY]`; when the clip against the colours already down
   would leave under `KEEP_FRAC` of its own art, it sews its art over them
   instead (`stage5_overlap.resolve_overlaps`), as `cfg.small_glyph_keep`
   does for a rescued glyph. On the hat the field sewn first had become an
   under-fill (`silhouette_underfill`) whose polygon covered the bar.

Widths and pull are untouched: the existing fine-bar / satin paths size the
stitches (ours already sews these at the pro's 0.8-1.1 mm where it sews them
at all). No fabric constant: gate 1 does not apply. Off, the module is not
imported and the engine is byte for byte as before.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
from shapely.geometry import Polygon

#: meta key on a bar this pass redrew (stage 5 reads it)
FINE_BAR_KEY = "fine_bar_whole"

BAR_MAX_W_MM = 0.6          # a stage-4 piece this narrow, or under, is a bar candidate
BAR_MIN_LEN_MM = 1.0
BAR_MIN_ASPECT = 4.0
PAGE_DE = 10.0              # a thread this close (Lab) to the page colour is the page, not ink
INK_CONTRAST_L = 20.0       # L* between the bar's thread and the region it sits in
HOST_RING_MM = 0.4          # how far round the piece the host region is read
BAND_MARGIN_MM = 0.3        # band half-width past the piece's own half-width
BAR_MAX_INK_W_MM = 0.8      # the widest slice a bar's ink may have (two laid threads)
STRAIGHT_MM = 0.15          # largest centre offset from the fitted line
REBUILD_MIN_ASPECT = 6.0
END_TRIM = 1.8              # an end slice this many times the median width is not the bar's
ABSORB_FRAC = 0.8           # share of a same-thread region inside the bar that makes it a piece
ABSORB_PAD_MM = 0.15
KEEP_FRAC = 0.5             # stage 5: under this share of its art left after the clip, keep the art
REBUILD_EXTEND_MM = 1.0     # the ink this much longer than the piece: the trace broke the bar
SLIVER_MIN_MM = 3.0         # this much other-colour sliver along the bar: its edge was traced off
SLIVER_TOUCH_MM = 0.1
SLIVER_ANGLE_DEG = 10.0


def _lab(rgb) -> np.ndarray:
    a = np.asarray(rgb, np.float32).reshape(-1, 1, 3) / 255.0
    return cv2.cvtColor(a, cv2.COLOR_RGB2LAB).reshape(-1, 3)


def _rect(poly) -> tuple[float, float, float, tuple[float, float]]:
    """(short side, long side, long-side angle, centre) of the minimum rotated rectangle."""
    r = poly.minimum_rotated_rectangle
    pts = list(r.exterior.coords)
    a, b = math.dist(pts[0], pts[1]), math.dist(pts[1], pts[2])
    if a >= b:
        ang = math.atan2(pts[1][1] - pts[0][1], pts[1][0] - pts[0][0])
    else:
        ang = math.atan2(pts[2][1] - pts[1][1], pts[2][0] - pts[1][0])
    c = r.centroid
    return min(a, b), max(a, b), ang, (c.x, c.y)


def is_bar(poly) -> bool:
    if not isinstance(poly, Polygon) or poly.is_empty or poly.interiors:
        return False
    w, length, _a, _c = _rect(poly)
    return w <= BAR_MAX_W_MM and length >= BAR_MIN_LEN_MM and length >= BAR_MIN_ASPECT * max(w, 1e-6)


def fit_bar(xs: np.ndarray, ys: np.ndarray, ppm: float, cx: float, cy: float) -> Polygon | None:
    """The straight tapering bar through one ink component (pixel indices) ->
    a quadrilateral in mm (stage 4's frame), or None when the ink is not a
    straight thin bar."""
    P = np.column_stack([(xs - cx) / ppm, (ys - cy) / ppm])
    c0 = P.mean(axis=0)
    _u, _s, vt = np.linalg.svd(P - c0, full_matrices=False)
    u = vt[0]
    n = np.array([-u[1], u[0]])
    S = (P - c0) @ u
    T = (P - c0) @ n
    step = 1.0 / ppm
    bins = np.floor((S - S.min()) / step).astype(int)
    nb = int(bins.max()) + 1
    cnt = np.bincount(bins, minlength=nb).astype(float)
    tsum = np.bincount(bins, weights=T, minlength=nb)
    thick = cnt * step                         # mm across, per slice
    ok = cnt > 0
    if ok.sum() < 3:
        return None
    med = float(np.median(thick[ok]))
    # trim thick slices off the ends (a bar running into a letter's stroke)
    idx = np.nonzero(ok)[0]
    lo, hi = int(idx[0]), int(idx[-1])
    while lo < hi and thick[lo] > END_TRIM * med:
        lo += 1
    while hi > lo and thick[hi] > END_TRIM * med:
        hi -= 1
    keep = ok.copy()
    keep[:lo] = False
    keep[hi + 1:] = False
    if keep.sum() < 3 or float(thick[keep].max()) > BAR_MAX_INK_W_MM:
        return None
    sc = S.min() + (np.arange(nb) + 0.5) * step
    cen = np.where(keep, tsum / np.maximum(cnt, 1.0), 0.0)
    A = np.column_stack([np.ones(int(keep.sum())), sc[keep]])
    a = np.linalg.lstsq(A, cen[keep], rcond=None)[0]
    b = np.linalg.lstsq(A, thick[keep], rcond=None)[0]
    if float(np.max(np.abs(cen[keep] - (a[0] + a[1] * sc[keep])))) > STRAIGHT_MM:
        return None
    s0 = S.min() + lo * step
    s1 = S.min() + (hi + 1) * step
    length = s1 - s0
    mean_w = float(np.mean(thick[keep]))
    if length < REBUILD_MIN_ASPECT * max(mean_w, step):
        return None

    def corner(sv: float, side: int):
        w = max(step, b[0] + b[1] * sv - step) / 2.0     # a contour through pixel centres
        t = a[0] + a[1] * sv + side * w
        return tuple(c0 + sv * u + t * n)
    return Polygon([corner(s0, 1), corner(s1, 1), corner(s1, -1), corner(s0, -1)])


def _sliver_along(r, poly, ang: float, regions: list, gone: set) -> float:
    """mm of thin regions of OTHER threads lying along the bar, touching it
    and parallel to it: the bar's anti-aliased edge traced as its own shape
    (To a T hat: a 27 mm white sliver eating a 42 mm bar's width, where the
    satin jogged)."""
    total = 0.0
    for o in regions:
        if o is r or id(o) in gone or o.thread_index == r.thread_index or not is_bar(o.polygon):
            continue
        if o.polygon.distance(poly) > SLIVER_TOUCH_MM:
            continue
        _w, length, oang, _c = _rect(o.polygon)
        d = abs((oang - ang + math.pi / 2) % math.pi - math.pi / 2)
        if d <= math.radians(SLIVER_ANGLE_DEG):
            total += length
    return total


def apply_fine_bar_survive(regions: list, p, cfg) -> list[dict]:
    """Redraw the thin ink bars of `regions` (stage 4, mm, y down) from the
    art raster `p` (`Prep`), in place. -> one record per redrawn bar."""
    from .columns import is_lettering
    from .threads import chart_for
    chart = chart_for(cfg)
    ppm = float(p.px_per_mm)
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    H, W = p.rgb.shape[:2]
    page = getattr(p, "bg_rgb", None)
    if page is None:
        page = getattr(cfg, "garment_rgb", None)
    page_lab = None if page is None else _lab([tuple(page)[:3]])[0]
    img_lab = None
    gone: set[int] = set()
    records: list[dict] = []
    for r in list(regions):
        if id(r) in gone or (r.meta or {}).get(FINE_BAR_KEY) or not is_bar(r.polygon):
            continue
        if is_lettering(r, cfg):
            continue
        T = _lab([chart[r.thread_index].rgb])[0]
        if page_lab is not None and float(np.linalg.norm(T - page_lab)) < PAGE_DE:
            continue
        poly = r.polygon
        ring = poly.buffer(HOST_RING_MM).difference(poly.buffer(0.05))
        hosts = [o for o in regions if o is not r and id(o) not in gone
                 and o.thread_index != r.thread_index and o.polygon.intersects(ring)]
        if not hosts:
            continue
        host = max(hosts, key=lambda o: o.polygon.intersection(ring).area)
        B = _lab([chart[host.thread_index].rgb])[0]
        if abs(float(T[0] - B[0])) < INK_CONTRAST_L:
            continue
        if img_lab is None:
            img_lab = _lab(p.rgb.reshape(-1, 3)).reshape(H, W, 3)
        w, _length, ang, (mx, my) = _rect(poly)
        ux, uy = math.cos(ang), math.sin(ang)
        half = (w / 2.0 + BAND_MARGIN_MM) * ppm
        pcx, pcy = mx * ppm + cx, my * ppm + cy
        ext = float(max(H, W))
        band = np.array([[pcx - ux * ext - uy * half, pcy - uy * ext + ux * half],
                         [pcx + ux * ext - uy * half, pcy + uy * ext + ux * half],
                         [pcx + ux * ext + uy * half, pcy + uy * ext - ux * half],
                         [pcx - ux * ext + uy * half, pcy - uy * ext - ux * half]])
        bmask = np.zeros((H, W), np.uint8)
        cv2.fillPoly(bmask, [np.round(band).astype(np.int32)], 1)
        sub = img_lab
        ink = ((np.linalg.norm(sub - T, axis=2) < np.linalg.norm(sub - B, axis=2)) & (bmask > 0)).astype(np.uint8)
        _n, lbl = cv2.connectedComponents(ink, connectivity=8)
        seed = np.zeros((H, W), np.uint8)
        cv2.fillPoly(seed, [np.round(np.asarray(poly.exterior.coords) * ppm + [cx, cy]).astype(np.int32)], 1)
        hit = np.unique(lbl[(seed > 0) & (ink > 0)])
        hit = hit[hit > 0]
        if not len(hit):
            continue
        ys, xs = np.nonzero(np.isin(lbl, hit))
        bar = fit_bar(xs.astype(float), ys.astype(float), ppm, cx, cy)
        if bar is None or not bar.is_valid or bar.is_empty:
            continue
        reach = bar.buffer(ABSORB_PAD_MM)
        pieces = [o for o in regions if o is not r and id(o) not in gone
                  and o.thread_index == r.thread_index and not (o.meta or {}).get(FINE_BAR_KEY)
                  and not is_lettering(o, cfg)
                  and o.polygon.intersection(reach).area >= ABSORB_FRAC * max(o.polygon.area, 1e-9)]
        r.meta = dict(r.meta or {})
        # Redrawn only when the trace is BROKEN; a whole bar keeps its outline
        # (Fremont's "|" divider sews straight already, and redrawing it from
        # the anti-aliased ink only widened it), and is tagged for stage 5.
        extends = _rect(bar)[1] - _rect(poly)[1]
        sliver = _sliver_along(r, poly, ang, regions, gone)
        if not (pieces or extends >= REBUILD_EXTEND_MM or sliver >= SLIVER_MIN_MM):
            r.meta[FINE_BAR_KEY] = {"pieces": 1, "redrawn": False}
            continue
        new = bar
        before = poly.area + sum(o.polygon.area for o in pieces)
        r.polygon = new
        r.area_mm2 = float(new.area)
        for o in pieces:
            gone.add(id(o))
        why = ("pieces" if pieces else "extends" if extends >= REBUILD_EXTEND_MM else "sliver")
        r.meta[FINE_BAR_KEY] = {"pieces": len(pieces) + 1, "redrawn": True, "why": why,
                                "length_mm": round(_rect(new)[1], 2)}
        records.append({"thread": r.thread_number, "pieces": len(pieces) + 1, "why": why,
                        "area_before_mm2": round(before, 3), "area_after_mm2": round(new.area, 3),
                        "length_mm": round(_rect(new)[1], 2),
                        "at_mm": [round(new.centroid.x, 2), round(new.centroid.y, 2)]})
    if gone:
        regions[:] = [o for o in regions if id(o) not in gone]
    return records
