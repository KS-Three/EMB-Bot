"""Bevel and ring fold: shading the pro flattens sews as the shape it shades (2026-11-13).

Kent on Golden Tee (20 pins, one complaint): "The bean stitching makes 'golf'
look to bust". The art's GOLF is a gold ramp with a dark bevel, a red keyline
and a grey drop shadow; the pro sews ONE flat gold (3 threads in all: white,
gold, black). Ours traced every layer: six threads, each GOLF letter a mosaic
of four or five, the thin bevel bands sewn as runs and beans. Precision
Drone's frame ring is the same story (pin 3, "border changes colour too
much"): the art's silver bevel became light-grey arcs lying in the black
ring, where the pro sews one ring.

No step before this knew a bevel: the only flattening was the colour COUNT
(`enforce_color_cap`) and the 6.0 CIE76 same-colour merge. This module reads
the stage-4 regions just before the cap and folds what the pro folds, by ROLE
(how a shape sits against its neighbours), in three passes:

1. **Shadow.** A band of a colour near the art's own page colour, lying
   mostly ON the page, that hugs one side of the art: a drop shadow cast on
   the page. The region is removed (it becomes page).
2. **Tone merge.** Two shapes of different threads within `TONE_DE00` that
   share a long seam are one shape shaded (a ramp the palette split in two):
   the smaller-area thread joins the larger and the touching pieces union.
3. **Bevel band.** A band no wider than `BAND_MAX_MM` (what we sew as runs
   and beans) that runs along a BODY (a shape wider than a band) folds into
   it: its outline is unioned in and its thread goes. Of the bodies it runs
   along, the nearest in colour is the parent (a bevel is a tone of what it
   shades). Repeated, so a band stacked on a band folds once the first has.

Guards (when in doubt, do nothing):

* A band covering `ALL_ROUND` of its parent's outer outline or more wraps it:
  a keyline or an art outline, which the pro BORDERS (Becker's and MFab's
  keylines). Never folded.
* A band inside its parent (in a hole of it) folds only when it lies within
  a band's width of the parent's OUTER edge (Drone's ring arcs); a line drawn
  across the inside (Drone's crosshair) stays.
* A body near the page colour is never a parent: a white shape on a white
  page is SEEN by its edge, so that edge stays (Golden Tee's ball arc and its
  GT faces keep their outlines and bevels, as the pro's do).
* Counters, enclosed background and dark-ink lines are never folded. A
  rescued small detail is: one that runs along a body is bevel noise, and
  a free-standing one (the dot of an i) has no body to fold into.

Every threshold is in mm at the sewn size or in CIEDE2000, named below with
where it comes from.
"""
from __future__ import annotations

import numpy as np
from shapely import STRtree
from shapely.geometry import Polygon
from shapely.ops import unary_union

from .machine import thread_profile
from .threads import rgb_to_lab

# A band is a region whose mean width (2 x area / perimeter, exact for a long
# strip) is at most two laid threads of the default 40 wt (0.8 mm): the
# width DRAWings switches a single run to a double pass at, the basis of
# `machine.HAIRLINE_MAX_WIDTHS`. That is what our tiers sew as a run or a
# bean -- the "bean stitching" Kent called busy. Golden Tee's bevel and
# keyline bands measure 0.12-0.75 mm; its gold letter bodies 1.15-1.5 mm.
BAND_MAX_MM = 2.0 * thread_profile().width_mm
# A band runs ALONG its parent: at least this share of the band's own
# outline lies against the parent. A strip along one side of a shape shares
# about half (one long side); 0.3 allows its ends and a ragged trace.
HUG_FRAC = 0.3
# A band on the page's edge of a body (an extrusion or a dark under-edge)
# has the page on one side: it needs this share of its outline on bodies
# and half of what is not on the page.
EDGE_HUG_FRAC = 0.15
# A band covering this share of its parent's outer outline or more wraps it:
# a keyline or an art outline (ADAPTATIONS.md item 1's 60%). Never folded.
ALL_ROUND = 0.6
# Two shapes this close in CIEDE2000, sharing a seam, are one shape shaded.
# Golden Tee's gold ramp splits at 13.9 (Candlelight / Pumpkin); 15 is the
# figure ADAPTATIONS.md proposed. Distinct colours on the census sit > 20.
TONE_DE00 = 15.0
# The seam that makes two shapes one: at least this share of the smaller
# one's outline.
TONE_SEAM_FRAC = 0.2
# A shadow is no wider than a fill can hold twice (`MIN_FILL_WIDTH_MM` x 2:
# a drop shadow is an offset of a millimetre or two), lies on the page along
# at least SHADOW_PAGE_FRAC of its outline, hugs the art along at least
# HUG_FRAC, and is within PAGE_DE00 of the page's colour (Golden Tee's grey
# shadow sits 14.3 from its white page).
SHADOW_MAX_MM = 2.4
SHADOW_PAGE_FRAC = 0.4
PAGE_DE00 = 20.0
# Passes of the band fold (a band stacked on a band folds on the next one).
MAX_PASSES = 4
# Adjacency is read at the trace's own precision: 1.5 source pixels.
TOUCH_SRC_PX = 1.5

PROTECT_KEYS = ("counter", "enclosed_background", "dark_ink", "bean_letter_spines")


def _de00(lab_a, lab_b) -> float:
    from skimage.color import deltaE_ciede2000
    return float(deltaE_ciede2000(np.asarray(lab_a, dtype=np.float64).reshape(1, 3),
                                  np.asarray(lab_b, dtype=np.float64).reshape(1, 3))[0])


def _lab(rgb) -> np.ndarray:
    return rgb_to_lab(np.asarray(rgb, dtype=np.uint8).reshape(1, 1, 3)).reshape(3)


def _width(g) -> float:
    return 2.0 * g.area / g.length if g.length > 0 else 0.0


def _protected(r) -> bool:
    return any(r.meta.get(k) for k in PROTECT_KEYS)


def _poly(r) -> bool:
    return r.polygon.geom_type == "Polygon" and r.polygon.is_valid and not r.polygon.is_empty


def _union(polys, eps):
    """One polygon from touching pieces, seams closed at `eps`; None if not."""
    g = unary_union([q.buffer(eps, join_style=2) for q in polys]).buffer(-eps, join_style=2)
    if g.geom_type != "Polygon" or not g.is_valid or g.is_empty:
        return None
    return g


class _Graph:
    """Who touches whom, and along how much outline (mm)."""

    def __init__(self, regions, touch):
        self.touch = touch
        self.polys = [r.polygon for r in regions]
        self.tree = STRtree(self.polys)

    def contacts(self, i) -> dict:
        """{j: length of i's outline lying against region j}."""
        g = self.polys[i]
        out = {}
        for j in self.tree.query(g.buffer(self.touch)):
            j = int(j)
            if j == i or g.distance(self.polys[j]) > self.touch:
                continue
            shared = g.boundary.intersection(self.polys[j].buffer(self.touch)).length
            if shared > 0:
                out[j] = shared
        return out

    def page_contact(self, i) -> float:
        """Length of i's outline that touches no other region."""
        g = self.polys[i]
        near = [self.polys[int(j)] for j in self.tree.query(g.buffer(self.touch)) if int(j) != i]
        if not near:
            return g.length
        return g.boundary.difference(unary_union(near).buffer(self.touch)).length


def apply_bevel_fold(regions, p, cfg, chart, layer_threads=None) -> dict:
    """Fold shadows, tone splits and bevel bands (module note). Mutates
    `regions` (removes folded regions, grows their parents); -> a report.
    `layer_threads`: the quantize-time layer -> cone list, so a re-threaded
    region moves to the layer that sews its new cone."""
    ipm = float(getattr(p, "input_px_per_mm", 0.0) or 0.0) or float(p.px_per_mm)
    touch = max(0.02, TOUCH_SRC_PX / ipm)
    eps = touch / 2.0
    report = {"touch_mm": round(touch, 4), "shadows": [], "tones": [], "bands": [], "unions": 0}
    page = getattr(p, "bg_rgb", None)
    page_lab = None if (page is None or getattr(p, "bg_from_alpha", False)) else _lab(page)

    def lab(r):
        return chart.lab[r.thread_index]

    def near_page(r) -> bool:
        return page_lab is not None and _de00(lab(r), page_lab) <= PAGE_DE00

    # ---- 1. shadows -------------------------------------------------------
    if page_lab is not None:
        graph = _Graph(regions, touch)
        drop = []
        for i, r in enumerate(regions):
            g = r.polygon
            if _protected(r) or not _poly(r) or _width(g) > SHADOW_MAX_MM or not near_page(r):
                continue
            per = g.length
            if graph.page_contact(i) < SHADOW_PAGE_FRAC * per:
                continue
            cont = {j: v for j, v in graph.contacts(i).items()
                    if regions[j].thread_index != r.thread_index}
            art = sum(cont.values())
            if art < HUG_FRAC * per:
                continue
            touched = unary_union([regions[j].polygon for j in cont])
            parts = [touched] if touched.geom_type == "Polygon" else list(getattr(touched, "geoms", []))
            outline = sum(q.exterior.length for q in parts if q.geom_type == "Polygon")
            if outline > 0 and art >= ALL_ROUND * outline:
                continue                  # wraps the art: a halo, which the pro borders
            drop.append(i)
            report["shadows"].append({"shape_id": r.shape_id, "thread": r.thread_number,
                                      "area_mm2": round(r.area_mm2, 2), "width_mm": round(_width(g), 3)})
        for i in sorted(drop, reverse=True):
            del regions[i]

    # ---- 2. tone merge ----------------------------------------------------
    graph = _Graph(regions, touch)
    area: dict[int, float] = {}
    for r in regions:
        area[r.thread_index] = area.get(r.thread_index, 0.0) + r.area_mm2
    pairs: dict[tuple, float] = {}
    for i, r in enumerate(regions):
        if _protected(r) or not _poly(r):
            continue
        for j, v in graph.contacts(i).items():
            o = regions[j]
            if j < i or o.thread_index == r.thread_index or _protected(o) or not _poly(o):
                continue
            if v < TONE_SEAM_FRAC * min(r.polygon.length, o.polygon.length):
                continue
            de = _de00(lab(r), lab(o))
            if de <= TONE_DE00:
                key = tuple(sorted((r.thread_index, o.thread_index)))
                pairs[key] = min(pairs.get(key, 99.0), de)
    to: dict[int, int] = {}
    for (a, b), de in sorted(pairs.items(), key=lambda kv: (kv[1], kv[0])):
        a, b = to.get(a, a), to.get(b, b)
        if a == b:
            continue
        small, big = (a, b) if (area.get(a, 0), a) < (area.get(b, 0), b) else (b, a)
        to[small] = big
        for k, v in list(to.items()):
            if v == small:
                to[k] = big
        area[big] = area.get(big, 0.0) + area.pop(small, 0.0)
        report["tones"].append({"from": chart[small].number, "to": chart[big].number, "de00": round(de, 2)})
    if to:
        # One spool sews at one position (`stage4_vectorize.
        # rehome_resnapped_regions`' rule): a re-threaded region joins the
        # earliest layer declaring its new cone, else the layer its new
        # thread's other regions sew in.
        home = {}
        for li, t in enumerate(layer_threads or []):
            home.setdefault(t, li)
        for r in regions:
            if r.thread_index not in to and "layer" in r.meta:
                home.setdefault(r.thread_index, r.meta["layer"])
        changed = set()
        for i, r in enumerate(regions):
            if r.thread_index in to and not _protected(r):
                big = to[r.thread_index]
                r.meta["tone_merged_from"] = r.thread_number
                r.thread_index = big
                r.thread_number = chart[big].number
                if big in home and "layer" in r.meta:
                    r.meta["layer"] = home[big]
                changed.add(i)
        report["unions"] += _union_touching(regions, changed, touch, eps)

    # ---- 3. bevel bands ---------------------------------------------------
    for _pass in range(MAX_PASSES):
        graph = _Graph(regions, touch)
        folds: dict[int, int] = {}
        for i, r in enumerate(regions):
            g = r.polygon
            if _protected(r) or not _poly(r) or _width(g) > BAND_MAX_MM:
                continue
            per = g.length
            cands = []
            for j, v in graph.contacts(i).items():
                o = regions[j]
                if (o.thread_index == r.thread_index or not _poly(o) or o.meta.get("counter")
                        or o.polygon.area < g.area or _width(o.polygon) <= BAND_MAX_MM
                        or near_page(o)):
                    continue
                cands.append((_de00(lab(r), lab(o)), -v, j, v))
            if not cands:
                continue
            # It runs ALONG the bodies: HUG_FRAC of its outline against them,
            # or -- a band lying on the page, which has only one other side
            # (GOLF's extrusion: 72% on the page, nearly all the rest on the
            # gold) -- half its off-page outline and EDGE_HUG_FRAC overall.
            on_bodies = sum(c[3] for c in cands)
            off_page = per - graph.page_contact(i)
            if not (on_bodies >= HUG_FRAC * per
                    or (on_bodies >= EDGE_HUG_FRAC * per and on_bodies >= 0.5 * off_page)):
                continue
            _de, _neg, j, shared = min(cands)
            P = regions[j].polygon
            inside = Polygon(P.exterior).contains(g.representative_point())
            # how far it runs along the parent: a band inside it touches it on
            # both long sides, so half its contact
            along = shared / 2.0 if inside else shared
            if along >= ALL_ROUND * P.exterior.length:
                continue                  # wraps its parent: a keyline, a full inner ring
            if inside and g.distance(P.exterior) > BAND_MAX_MM:
                continue                  # drawn across the inside: a line, not a bevel
            folds[i] = j
        if not folds:
            break
        removed, grown = [], set()
        for i, j in sorted(folds.items(), key=lambda ij: (-regions[ij[1]].polygon.area, ij[0])):
            if j in folds or j in grown and False:
                continue
            band, parent = regions[i], regions[j]
            new = _union([parent.polygon, band.polygon], eps)
            report["bands"].append({"shape_id": band.shape_id, "thread": band.thread_number,
                                    "into": parent.shape_id, "into_thread": parent.thread_number,
                                    "width_mm": round(_width(band.polygon), 3),
                                    "area_mm2": round(band.area_mm2, 2), "pass": _pass + 1})
            if new is None:
                band.meta["bevel_fold_into"] = parent.shape_id
                band.thread_index = parent.thread_index
                band.thread_number = parent.thread_number
                if "layer" in parent.meta:
                    band.meta["layer"] = parent.meta["layer"]
                continue
            parent.polygon = new
            parent.area_mm2 = float(new.area)
            parent.meta.setdefault("bevel_fold", []).append(band.shape_id)
            removed.append(i)
            grown.add(j)
        if not removed:
            break
        for i in sorted(removed, reverse=True):
            del regions[i]
    return report


def _union_touching(regions, seeds, touch, eps) -> int:
    """Union every same-thread region touching a re-threaded one, so a shape
    traced as two tones sews as one. -> regions removed."""
    graph = _Graph(regions, touch)
    parent = list(range(len(regions)))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in sorted(seeds):
        for j in graph.contacts(i):
            if regions[j].thread_index == regions[i].thread_index and not _protected(regions[j]) \
                    and _poly(regions[j]):
                parent[find(i)] = find(j)
    groups: dict[int, list[int]] = {}
    for i in range(len(regions)):
        groups.setdefault(find(i), []).append(i)
    removed = []
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda k: (-regions[k].polygon.area, regions[k].shape_id))
        g = _union([regions[k].polygon for k in members], eps)
        if g is None:
            continue
        keep = regions[members[0]]
        keep.polygon = g
        keep.area_mm2 = float(g.area)
        keep.meta.setdefault("bevel_fold", []).extend(regions[k].shape_id for k in members[1:])
        removed.extend(members[1:])
    for k in sorted(removed, reverse=True):
        del regions[k]
    return len(removed)
