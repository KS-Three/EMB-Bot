"""Slivers no thread can draw (`cfg.sliver_prune`, built OFF 2026-11-10).

Kent's Pooh at 54 mm (266 px source, 4.4 px/mm, enlarged x1.8 to the work
grid), automatic lane: white run stitches down the figure's right edge, and a
red satin spike running up the arm out of the shirt. Both are regions the
segmenter made out of pixels that are not a shape:

* **Page slivers.** The JPEG's pale halo between the figure and the white
  page, about one SOURCE pixel wide, kept as six regions on a near-white
  thread (0.4-1.6 mm2 each) and sewn as runs. They are the page's colour and
  they lie on the page.
* **Tendrils.** The dark crease drawn between the arm and the head, one to two
  source pixels wide, took the shirt's label (the nearest of six colours) and
  hung off the shirt as a 7 mm spike wedged between two gold shapes.

One pass over stage 3's masks, after `resolve_small_regions` and before stage
4 traces anything, so the neighbours' outlines are traced from the pixels as
they end up and no seam is cut twice.

Both tests are tied to the SOURCE pixel (`Prep.input_px_per_mm`), not to a
millimetre: a mark narrower than the artwork's own resolution cannot be told
from its anti-alias ramp at any sewn size. Neither is a stitch value.

A PAGE SLIVER is a mask that
  * averages at most `SLIVER_WIDTH_SRC_PX` source pixels wide,
  * has at least `PAGE_CONTACT_MIN` of its rim on the border-flood page and at
    least `FIGURE_CONTACT_MIN` on other masks (it hugs a silhouette; a pale
    letter standing alone on the page touches no figure and is kept),
  * and is the page's half of the edge ramp: its layer's thread is nearer the
    page colour than the thread of the figure it lies on, and within
    `SLIVER_PAGE_DE00_MAX` of the page.
It is dropped: those pixels were page.

A TENDRIL is the part of a wide mask that an opening by
`TENDRIL_WIDTH_SRC_PX` source pixels removes, when that part
  * is at least `TENDRIL_MIN_ASPECT` kernels long,
  * is wedged in the figure: at least `TENDRIL_FIGURE_CONTACT_MIN` of its
    outside rim on other masks and none to speak of on the page (a balloon's
    string, out on the page, is kept),
  * is another colour than the body it hangs off: its own pixels at least
    `TENDRIL_MIN_DE00` from the body's core (a whisker in the nose's own ink
    is kept),
  * and is not a bridge: taking it away leaves the mask in as many pieces.
Its pixels go to the mask it has the most rim on.

ONLY ON A RASTER STAGE 1 ENLARGED by `MIN_ENLARGEMENT` or more (`prune`). A
source at or near the work grid is returned untouched: its one-pixel marks are
0.1 mm, below every stitch floor already, and the pass was busy there for
nothing (the numbers are beside the constant).
Never on an alpha cut-out for the page half (no page colour to compare), and
the pipeline calls neither half on a photo class.
"""
from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000

from .stage3_segment import RegionMask
from .threads import rgb_to_lab

# The pass runs only where stage 1 enlarged the raster at least this much
# (working pixels per source pixel). Measured 2026-11-10, verdicts read with
# no gate: at 1.00 the phone screenshot gave 225 one-pixel "slivers" and
# Golden Tee a 21.6 mm hairline moved for +267 stitches (80 mm); at 1.02-1.19
# (summit, drone, Becker's large hat at 113.5 mm) 14 slivers and 15 tendrils,
# every one a one-pixel line along a shading seam, 0.2-1.1 mm2. Pooh's spike
# is there from 1.34 (40 mm) to 2.68 (80 mm). Six flat logos at 2.03-3.25 give
# nothing at all. A candidate in the 1.19-1.34 gap, not a measured edge.
MIN_ENLARGEMENT = 1.25
# A page sliver: mean width (2 x area / rim) in SOURCE pixels. Pooh's three
# masks measure 0.91-0.99; the real ear outline kept beside them 1.32.
SLIVER_WIDTH_SRC_PX = 1.5
PAGE_CONTACT_MIN = 0.4
FIGURE_CONTACT_MIN = 0.2
# The guard on "nearer the page than the figure": CIEDE2000, layer thread to
# page. Pooh's three sliver masks read 2.6, 11.9 and 11.9 (Isacord 0010 and
# 0184 on a white page); the thin mask kept beside them, a real ear outline on
# 0945, reads 41.7. A candidate in that gap, not a measured edge.
SLIVER_PAGE_DE00_MAX = 20.0
# A tendril: what an opening this many source pixels across removes.
TENDRIL_WIDTH_SRC_PX = 2.0
# ...when it is at least this many kernels long (shorter is a corner crumb the
# opening leaves on every convex corner),
TENDRIL_MIN_ASPECT = 4.0
# ...hangs off a body at least this many kernels wide,
TENDRIL_BODY_RATIO = 4.0
# ...sits in the figure,
TENDRIL_FIGURE_CONTACT_MIN = 0.75
TENDRIL_PAGE_CONTACT_MAX = 0.1
# ...and is another colour than that body (CIEDE2000, source pixels).
TENDRIL_MIN_DE00 = 10.0

_K3 = np.ones((3, 3), np.uint8)


def _src_px(p) -> float:
    """Working-grid pixels per SOURCE pixel (1.0 when stage 1 did not enlarge)."""
    ip = float(getattr(p, "input_px_per_mm", 0.0) or 0.0)
    return max(1.0, float(p.px_per_mm) / ip) if ip > 0 else 1.0


def _owner(masks: list[RegionMask], shape: tuple[int, int]) -> np.ndarray:
    owner = np.full(shape, -1, np.int32)
    for i, m in enumerate(masks):
        owner[m.frame_slice()][m.crop] = i
    return owner


def _window(m: RegionMask, pad: int) -> tuple[int, int, int, int]:
    y0, x0, y1, x1 = m.bbox
    h, w = m.frame_shape
    return max(0, y0 - pad), max(0, x0 - pad), min(h, y1 + pad), min(w, x1 + pad)


def _held(m: RegionMask) -> bool:
    """A mask another rule kept on purpose (a dot rung, a cored counter, a
    spoked mark whose tips are stored in frame pixels, a floor-rescued
    stroke) is neither dropped nor trimmed here."""
    return bool(m.dot_rung or m.cored_counter or m.floor_rescued or m.detail_spokes is not None)


def _pieces(crop: np.ndarray) -> int:
    return cv2.connectedComponents(crop.astype(np.uint8), connectivity=8)[0] - 1


def _thread_lab(chart, thread_indices, layer: int) -> np.ndarray:
    return rgb_to_lab(np.asarray(chart[thread_indices[layer]].rgb, np.float64).reshape(1, 3))[0]


def page_slivers(masks: list[RegionMask], thread_indices, p, chart,
                 owner: np.ndarray | None = None) -> list[dict]:
    """One record per mask thin enough to be asked, `sliver` = the verdict."""
    if p.bg_from_alpha or p.bg_rgb is None or not p.bg_mask.any():
        return []
    if owner is None:
        owner = _owner(masks, p.bg_mask.shape)
    limit = SLIVER_WIDTH_SRC_PX * _src_px(p)
    page_lab = rgb_to_lab(np.asarray(p.bg_rgb, np.float64).reshape(1, 3))[0]
    out: list[dict] = []
    for i, m in enumerate(masks):
        area = m.area
        if not area or _held(m):
            continue
        wy0, wx0, wy1, wx1 = _window(m, 1)
        mine = m.window(wy0, wx0, wy1, wx1)
        ring = cv2.dilate(mine.astype(np.uint8), _K3).astype(bool) & ~mine
        n = int(ring.sum())
        if not n:
            continue
        mean_w = 2.0 * area / n
        if mean_w > limit:
            continue
        own = owner[wy0:wy1, wx0:wx1]
        page = float((ring & p.bg_mask[wy0:wy1, wx0:wx1]).sum()) / n
        nb = own[ring & (own >= 0) & (own != i)]
        figure = nb.size / n
        j = int(np.bincount(nb).argmax()) if nb.size else -1
        mine_lab = _thread_lab(chart, thread_indices, m.layer)
        de_page = float(deltaE_ciede2000(mine_lab, page_lab))
        de_nb = (float(deltaE_ciede2000(mine_lab, _thread_lab(chart, thread_indices, masks[j].layer)))
                 if j >= 0 else None)
        out.append({
            "index": i, "layer": m.layer, "area_px": area,
            "mean_width_src_px": round(mean_w / _src_px(p), 3),
            "page": round(page, 3), "figure": round(figure, 3), "neighbour": j,
            "de_page": round(de_page, 2), "de_neighbour": None if de_nb is None else round(de_nb, 2),
            "sliver": bool(page >= PAGE_CONTACT_MIN and figure >= FIGURE_CONTACT_MIN
                           and de_nb is not None and de_page <= SLIVER_PAGE_DE00_MAX
                           and de_page < de_nb),
        })
    return out


def tendrils(masks: list[RegionMask], p, owner: np.ndarray | None = None) -> list[dict]:
    """One record per long thin part an opening removes from a wide mask,
    `tendril` = the verdict; `crop`/`origin` locate its pixels in the frame."""
    if owner is None:
        owner = _owner(masks, p.bg_mask.shape)
    k = int(np.ceil(TENDRIL_WIDTH_SRC_PX * _src_px(p)))
    k += 1 - (k % 2)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    min_len = TENDRIL_MIN_ASPECT * k
    out: list[dict] = []
    for i, m in enumerate(masks):
        if min(m.crop.shape) < TENDRIL_BODY_RATIO * k or _held(m):
            continue
        wy0, wx0, wy1, wx1 = _window(m, k + 2)
        mine = m.window(wy0, wx0, wy1, wx1)
        mu = mine.astype(np.uint8)
        if 2.0 * float(cv2.distanceTransform(mu, cv2.DIST_L2, 5).max()) < TENDRIL_BODY_RATIO * k:
            continue
        core = cv2.morphologyEx(mu, cv2.MORPH_OPEN, kernel).astype(bool)
        spur = (mine & ~core).astype(np.uint8)
        n, lbl, stats, _ = cv2.connectedComponentsWithStats(spur, 8)
        if n < 2:
            continue
        pieces = cv2.connectedComponents(mu, connectivity=8)[0]
        own = owner[wy0:wy1, wx0:wx1]
        bg = p.bg_mask[wy0:wy1, wx0:wx1]
        win_lab = core_lab = None           # this window's Lab, only if a candidate asks
        for c in range(1, n):
            cw, ch = int(stats[c, cv2.CC_STAT_WIDTH]), int(stats[c, cv2.CC_STAT_HEIGHT])
            if max(cw, ch) < min_len:
                continue
            comp = lbl == c
            ring = cv2.dilate(comp.astype(np.uint8), _K3).astype(bool) & ~mine
            nr = int(ring.sum())
            if not nr:
                continue
            page = float((ring & bg).sum()) / nr
            nb = own[ring & (own >= 0) & (own != i)]
            figure = nb.size / nr
            j = int(np.bincount(nb).argmax()) if nb.size else -1
            rest = mu.copy()
            rest[comp] = 0
            bridge = cv2.connectedComponents(rest, connectivity=8)[0] != pieces
            if win_lab is None:
                win = p.rgb[wy0:wy1, wx0:wx1]
                win_lab = rgb_to_lab(win.reshape(-1, 3).astype(np.float64)).reshape(*win.shape[:2], 3)
                core_lab = win_lab[core].mean(0)
            de = float(deltaE_ciede2000(win_lab[comp].mean(0), core_lab))
            cx0, cy0 = int(stats[c, cv2.CC_STAT_LEFT]), int(stats[c, cv2.CC_STAT_TOP])
            out.append({
                "index": i, "layer": m.layer, "area_px": int(stats[c, cv2.CC_STAT_AREA]),
                "length_px": max(cw, ch), "kernel_px": k,
                "page": round(page, 3), "figure": round(figure, 3), "neighbour": j,
                "de_core": round(de, 2), "bridge": bool(bridge),
                "crop": np.ascontiguousarray(comp[cy0:cy0 + ch, cx0:cx0 + cw]),
                "origin": (wy0 + cy0, wx0 + cx0),
                "tendril": bool(j >= 0 and not bridge and figure >= TENDRIL_FIGURE_CONTACT_MIN
                                and page <= TENDRIL_PAGE_CONTACT_MAX and de >= TENDRIL_MIN_DE00),
            })
    return out


def _without(m: RegionMask, crop: np.ndarray, origin: tuple[int, int]) -> RegionMask:
    """`m` minus the pixels of `crop` at `origin`, re-cropped bbox-tight."""
    y0, x0 = m.origin
    oy, ox = origin
    h, w = crop.shape
    grid = m.crop.copy()
    grid[oy - y0:oy - y0 + h, ox - x0:ox - x0 + w] &= ~crop
    ys, xs = np.nonzero(grid)
    if not ys.size:
        return replace(m, crop=np.zeros((1, 1), bool), origin=m.origin)
    return replace(m, crop=np.ascontiguousarray(grid[ys.min():ys.max() + 1, xs.min():xs.max() + 1]),
                   origin=(y0 + int(ys.min()), x0 + int(xs.min())))


def prune(masks: list[RegionMask], thread_indices, p, chart) -> tuple[list[RegionMask], dict]:
    """`cfg.sliver_prune`: tendrils handed to the neighbour they are wedged
    in, then page slivers dropped. -> (masks, {"tendrils": n, "page_slivers": n})."""
    # An ENLARGED raster only (`MIN_ENLARGEMENT`). At or near the work grid a
    # source pixel is a working pixel (0.1 mm): nothing that thin sews, and
    # acting there is all cost. Enlarged, the same one or two source pixels
    # are 0.3-0.7 mm of manufactured width, which does sew.
    if not masks or _src_px(p) < MIN_ENLARGEMENT:
        return masks, {"tendrils": 0, "page_slivers": 0}
    given = masks
    masks = list(masks)
    owner = _owner(masks, p.bg_mask.shape)
    moved = 0
    for rec in tendrils(masks, p, owner):
        if not rec["tendril"]:
            continue
        i, j = rec["index"], rec["neighbour"]
        # The bridge test was made on the mask as it came in. Two tendrils
        # that each hold a lobe on are neither a bridge alone; the second one
        # is, once the first has gone.
        trimmed = _without(masks[i], rec["crop"], rec["origin"])
        if _pieces(trimmed.crop) > _pieces(masks[i].crop):
            continue
        masks[i] = trimmed
        masks[j] = replace(masks[j], crop=masks[j].crop.copy())     # the caller's mask is not ours
        masks[j].union_from(RegionMask(crop=rec["crop"], origin=rec["origin"],
                                       frame_shape=masks[j].frame_shape, layer=masks[j].layer))
        moved += 1
    if moved:
        owner = _owner(masks, p.bg_mask.shape)
    drop = {rec["index"] for rec in page_slivers(masks, thread_indices, p, chart, owner)
            if rec["sliver"]}
    if not moved and not drop:
        return given, {"tendrils": 0, "page_slivers": 0}      # nothing found: the list as given
    kept = [m for i, m in enumerate(masks) if i not in drop and m.area]
    return kept, {"tendrils": moved, "page_slivers": len(drop)}
