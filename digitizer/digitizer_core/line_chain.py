"""One thread per connected drawn line (`cfg.line_chain_one_thread`, built OFF 2026-11-11).

Kent on `C_low_poly` pin 2 (docs/border-colour-change-2026-11-11.md): the
art's outline is ONE black line, and it sews in two or three colours because
stage 2 and the thread re-check read each piece of it from its own anti-aliased
pixels. The flag that only stops the re-check lightening a hairline
(`resnap_hairline_never_lightens`) moved other things: the inner lines went
blue-grey and a whole slab changed colour through the colour cap. This works
on the LINE, not on each piece:

1. **Candidates.** A region no wider than a drawn line (`bean_rule.LINE_MAX_MM`,
   1.2 mm: geometry, not cloth, so gate 1 does not apply) that is not an
   enclosed-background hole or a specialty step.
2. **Core colour and ink test.** For each candidate, the colour of the pixels of
   its footprint that stand farthest from the ground beside it (the ring of
   pixels just outside every candidate; pixels shared with another candidate are
   not read): a black
   line reads black, not the grey of its halo. The farthest `CORE_FRAC` of the
   footprint, averaged in CIELAB. A candidate whose core is within
   `INK_CONTRAST_DE00` of its ground is a thin sliver of the FACE beside it,
   not a drawn line, and takes no part.
3. **Chains.** Ink candidates whose polygons lie within `LINK_MM` of each other
   are one drawn line (the pieces an outline is cut into by colour, and the
   mesh lines that cross it).
4. **Uniformity test.** A chain is ONE colour only when the pieces whose core
   sits within `UNIFORM_DE00` (CIEDE2000) of the chain's median core colour
   hold at least `MAJORITY_AREA_FRAC` of its area. A line that really changes
   colour (a red piece beside a blue piece) holds half at most, fails this and
   is left exactly as it was: a chain is never forced. A speck outside the
   band does not stop the line and is left as it is.
5. **The thread.** The loaded spool nearest the median core colour of the
   pieces inside the band; among spools within `TIE_DE00` of the nearest, the
   most used (so one near-black line is not split between Black and Blackberry).
   "Loaded" = the thread of every region that is not a candidate, plus the
   chain's own current threads: the cone set never grows, so the colour cap
   that runs after this has the same palette to work from (the slab-colour
   swing of the hairline flag came from changing which cones exist).
6. Every piece of the chain takes it, and moves to the earliest layer that
   declares that cone, as `stage4_vectorize.rehome_resnapped_regions` does, so
   one spool sews at one position and no layer sandwiches another.

Chains whose pieces already share one thread are untouched. Off, never called.
"""
from __future__ import annotations

import cv2
import numpy as np
from shapely.strtree import STRtree

from . import bean_rule
from .threads import rgb_to_lab

#: Pieces of one drawn line touch or overlap; a gap this wide (mm) still joins
#: them (each side of a seam is its own simplified contour of one pixel edge,
#: `_BORDER_SEAM_EPS_MM`'s argument).
LINK_MM = 0.3
#: Share of a candidate's footprint read as its core (the pixels farthest from
#: the ground), floor `MIN_CORE_PX`.
CORE_FRAC = 0.2
MIN_CORE_PX = 4
#: A footprint below this many pixels is not read (it neither votes nor
#: blocks).
MIN_FOOTPRINT_PX = 6
#: The pixels outside a footprint that make its ground ring, in working-grid px.
RING_PX = 3
#: A candidate's core must stand this far (CIEDE2000) from its ground to be a
#: drawn line rather than a thin sliver of a face. A raster measure.
INK_CONTRAST_DE00 = 25.0
#: Every readable piece's core within this CIEDE2000 distance of the chain's
#: median core is one colour. A raster measure of how far a drawn line's own
#: colour wanders along it, not a stitch value.
UNIFORM_DE00 = 12.0
#: ... and the pieces inside that band must hold this share of the chain's
#: area (a speck or two outside it is left alone; a line cut half red, half
#: blue holds 0.5 and is refused).
MAJORITY_AREA_FRAC = 0.9
#: Spools within this CIEDE2000 of the nearest to a chain's core colour are
#: equally good matches; the most used of them wins (Black 0020 and Blackberry
#: 1776 are 12.2 apart: one near-black line must not be split between them).
TIE_DE00 = 15.0


def _de00(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    try:
        from skimage.color import deltaE_ciede2000
    except ImportError:  # pragma: no cover
        from skimage.color.delta_e import deltaE_ciede2000
    return deltaE_ciede2000(a, b)


def _candidates(regions) -> list:
    out = []
    for r in regions:
        if r.meta.get("enclosed_background") or r.meta.get("step_key"):
            continue
        poly = r.polygon
        if poly is None or poly.is_empty or poly.geom_type != "Polygon":
            continue
        if bean_rule.min_dim_mm(poly) <= bean_rule.LINE_MAX_MM:
            out.append(r)
    return out


def _chains(items: list) -> list[list]:
    """Connected components (size >= 2) of `items` by polygon distance <= LINK_MM."""
    if len(items) < 2:
        return []
    geoms = [c.polygon for c in items]
    tree = STRtree(geoms)
    parent = list(range(len(items)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, g in enumerate(geoms):
        for j in tree.query(g.buffer(LINK_MM)):
            j = int(j)
            if j > i and g.distance(geoms[j]) <= LINK_MM:
                a, b = find(i), find(j)
                if a != b:
                    parent[max(a, b)] = min(a, b)
    comps: dict[int, list] = {}
    for i, c in enumerate(items):
        comps.setdefault(find(i), []).append(c)
    return [sorted(v, key=lambda r: r.shape_id) for _k, v in sorted(comps.items())
            if len(v) >= 2]


def core_colour(region, p, lab_img: np.ndarray, cover: np.ndarray, cx: float,
                cy: float):
    """-> (CIELAB core colour, CIEDE2000 distance of it from the ground), or
    None when the footprint or its ground ring is too small to read."""
    from .stage4_vectorize import _region_footprint
    shape = p.rgb.shape[:2]
    fp = _region_footprint(region, shape, cx, cy, p.px_per_mm)
    fp = fp & (~p.bg_mask) & (cover == 1)     # pixels of this candidate alone
    if int(fp.sum()) < MIN_FOOTPRINT_PX:
        return None
    k = np.ones((2 * RING_PX + 1, 2 * RING_PX + 1), np.uint8)
    wide = cv2.dilate(fp.astype(np.uint8), k) > 0
    ring = wide & (cover == 0)               # outside every candidate
    if int(ring.sum()) < MIN_FOOTPRINT_PX:
        return None
    ground = np.median(lab_img[ring], axis=0)
    px = lab_img[fp]
    dist = np.linalg.norm(px - ground, axis=1)
    n = max(MIN_CORE_PX, int(round(CORE_FRAC * len(px))))
    idx = np.argsort(-dist)[:n]
    core = px[idx].mean(axis=0)
    contrast = float(_de00(core.reshape(1, 3), ground.reshape(1, 3))[0])
    return core, contrast


def apply(regions, p, cfg, chart, layer_threads) -> dict:
    """Unify the thread of every uniform drawn-line chain. -> a stats dict
    (`candidates`, `ink`, `chains`, `unified`, `refused`, `recoloured`, `moved`,
    `detail`); regions edited in place."""
    stats = {"candidates": 0, "ink": 0, "chains": 0, "unified": 0, "refused": 0,
             "recoloured": 0, "moved": 0, "detail": []}
    cands = _candidates(regions)
    stats["candidates"] = len(cands)
    if len(cands) < 2:
        return stats

    from .stage4_vectorize import _region_footprint
    shape = p.rgb.shape[:2]
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    lab_img = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(*shape, 3)
    cover = np.zeros(shape, np.int16)
    for r in cands:
        cover += _region_footprint(r, shape, cx, cy, p.px_per_mm)

    core: dict[int, np.ndarray] = {}
    for r in cands:
        got = core_colour(r, p, lab_img, cover, cx, cy)
        if got is not None and got[1] >= INK_CONTRAST_DE00:
            core[id(r)] = got[0]
    ink = [r for r in cands if id(r) in core]
    stats["ink"] = len(ink)
    chains = [ch for ch in _chains(ink) if len({r.thread_index for r in ch}) > 1]
    stats["chains"] = len(chains)
    if not chains:
        return stats

    cand_ids = {id(r) for r in cands}
    base_loaded = {r.thread_index for r in regions
                   if id(r) not in cand_ids and not r.meta.get("enclosed_background")}
    usage: dict[int, float] = {}
    for r in regions:
        if not r.meta.get("enclosed_background"):
            usage[r.thread_index] = usage.get(r.thread_index, 0.0) + r.polygon.area
    home: dict[int, int] = {}
    for layer, thread in enumerate(layer_threads):
        home.setdefault(thread, layer)

    for ch in chains:
        arr = np.array([core[id(r)] for r in ch])
        area = np.array([r.polygon.area for r in ch])
        med = np.median(arr, axis=0)
        spread = _de00(arr, np.repeat(med.reshape(1, 3), len(arr), axis=0))
        inl = spread <= UNIFORM_DE00
        share = float(area[inl].sum() / max(area.sum(), 1e-9))
        det = {"n": len(ch), "threads": sorted({r.thread_number for r in ch}),
               "inlier_area_share": round(share, 3), "outliers": int((~inl).sum()),
               "median_lab": [round(float(v), 1) for v in med]}
        stats["detail"].append(det)
        if share < MAJORITY_AREA_FRAC:
            stats["refused"] += 1
            det["outcome"] = "not_uniform"
            continue
        # the pieces inside the band are the line; a speck outside it is left as it is
        ch = [r for r, ok in zip(ch, inl) if ok]
        med = np.median(arr[inl], axis=0)
        if len({r.thread_index for r in ch}) < 2:
            det["outcome"] = "already_one_thread"
            continue
        loaded = sorted(base_loaded | {r.thread_index for r in ch})
        per = _de00(np.repeat(med.reshape(1, 3), len(loaded), axis=0),
                    np.array([chart.lab[t] for t in loaded]))
        # among the spools about as near as the nearest, the most used one: two
        # chains of one near-black line must not pick Black and Blackberry
        near = [t for t, d in zip(loaded, per) if d <= float(per.min()) + TIE_DE00]
        best = max(near, key=lambda t: (usage.get(t, 0.0), -t))
        det["outcome"] = "unified"
        det["thread"] = chart[best].number
        changed = False
        for r in ch:
            if r.thread_index != best:
                r.thread_index = best
                r.thread_number = chart[best].number
                r.meta["line_chain_thread"] = True
                stats["recoloured"] += 1
                changed = True
                target = home.get(best)
                if target is not None and r.meta.get("layer") != target:
                    r.meta["layer"] = target
                    stats["moved"] += 1
        if changed:
            stats["unified"] += 1
    return stats
