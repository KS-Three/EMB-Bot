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

A SPECK (`cfg.speck_prune`, its own flag, built OFF 2026-11-14; `prune_specks`,
called on its own) is a mask that
  * is under stage 3's detail floor yet clears the run tier's floors (stage
    3's own proxy): one of the small regions its rescue KEPT to sew
    (`resolve_small_regions`, a contrasting sliver), not a dot rung, cored
    counter, floor-rescued stroke or spoked mark,
  * averages under `SPECK_WIDTH_SRC_PX` source pixels wide (2 x area / rim)
    AND is narrower, inscribed, than the thread that would sew it
    (`machine.thread_profile(...).width_mm`, the weight `RUN_MIN_AREA_MM2`
    already squares): the run tier lays a loop of thread round it, and a loop
    round a mark narrower than one thread is a dot of thread wider and darker
    than the mark,
  * is wedged in the figure, as a tendril is (rim on other masks, none to
    speak of on the page),
  * and is another colour than the mask it lies in (CIEDE2000 of the threads),
  * and is not a SLIT: a mark at least `SPECK_SLIT_MIN_DL` lighter (CIELAB L)
    than its host, lying in that host alone (every other mask on its rim is a
    speck itself or under the run tier's floors, scraps that leave anyway).
    That is a highlight the art cut into a body, and it stays (2026-11-15:
    with no such exemption the heraldic crest lost three of the left wing's
    five white feather quills and four of the right's, which main sews),
  * and is a FRAGMENT: the art's ink of the speck's own kind (darker than its
    host for a dark speck, lighter for a light one) runs on out of it by at
    least `SPECK_FRAGMENT_MIN_ARMS` arms that the masks sew in ANOTHER colour.
    The speck is then a piece of a longer line the rest of which is lost, a
    dot where the art has a line: low_poly's crossings and edge pieces.
    A WHOLE mark (no ink leaves it: the period in "LLC.", a speed line drawn
    as one bar) and a piece whose line is sewn on in its own colour (To a T's
    speed-line pieces, which `fine_bar_survive` redraws at stage 4) stay
    (2026-11-16: with no such test To a T lost five of its six speed lines and
    the period).
    NOT ENOUGH TO FLIP (2026-11-16 scoped check): the heraldic crest's crown
    is drawn with keylines too, and its pieces between the yellow band and
    the yellow pearls are fragments like low_poly's. Handed on, the pearls
    touch the band, the band's hole joins the crown (four holes to three at
    stage 4), and the crown's column satin then runs over the navy gaps
    between its scrolls, which it still holds as holes. No test on the speck
    alone tells those pieces from low_poly's: low_poly's crossings separate
    same-thread facets of the same sizes (54-93 px against 1,000-2,500).
Its pixels go to the mask it has the most rim on. Kent's `low_poly` at 80 mm
(sitting 2026-11-11, "Random Black Spot", 7 pins): the art's polygon edges
are one-pixel black lines; quantisation labels only their crossings black,
and each crossing kept as a 0.13-0.30 mm2 black run loop. This half runs at
ANY enlargement: `low_poly` is at the work grid (x1.01), where the page and
tendril halves never run, and the thread-width test is what keeps a coarse
source's real detail (Becker's one source pixel is 0.7 mm) out of it.
"""
from __future__ import annotations

from dataclasses import replace

import cv2
import numpy as np
from skimage.color import deltaE_ciede2000

from . import machine
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
# A speck (`cfg.speck_prune`): mean width (2 x area / rim, the page sliver's
# measure) in SOURCE pixels, the tendril's "one to two source pixels".
# low_poly's seven pinned specks read 0.44-1.58 on their traced polygons; the
# design's other kept slivers of the facet threads run 0.9-4.7.
SPECK_WIDTH_SRC_PX = TENDRIL_WIDTH_SRC_PX
SPECK_FIGURE_CONTACT_MIN = TENDRIL_FIGURE_CONTACT_MIN
SPECK_PAGE_CONTACT_MAX = TENDRIL_PAGE_CONTACT_MAX
SPECK_MIN_DE00 = TENDRIL_MIN_DE00
# A SLIT, not a speck: at least this much lighter than its host (CIELAB L of
# the threads, 0-100) and in that host alone. Measured 2026-11-15, 80 mm left
# chest: the heraldic crest's white quills read L 100 on the navy wing's 34.0
# (66). low_poly's grey specks the rule is there to take read 11.9-19.2 over
# their facets and 26.1 (dark grey on black); three light marks on black or
# dark grey that lie in one host stay (112 specks -> 109 pruned), as main
# sews them. A candidate in the 26-45 gap, not a measured edge.
SPECK_SLIT_MIN_DL = 40.0
# A FRAGMENT (module note). The art's ink: a top-hat on CIELAB L (closing
# minus L for a dark speck, L minus opening for a light one) this many SOURCE
# pixels across, at least `SPECK_INK_MIN_DL` -- a thin line darker (lighter)
# than what is round it, wider facets and bodies read no ink. Its arms are the
# pieces of that ink, joined to the speck, on a ring from one source pixel out
# to `SPECK_ARM_REACH_SRC_PX`; an arm is LOST when at least
# `SPECK_ARM_LOST_MIN` of it lies on masks sewn at least `SPECK_MIN_DE00` from
# the speck's thread (or on no mask). Measured 2026-11-16, 80 mm left chest:
# low_poly 81 of its 110 specks are fragments, every one of Kent's seven
# "Random Black Spot" pins among them and 42 of its 43 dark ones (the 43rd has
# one arm); To a T hat, beanie and machine beanie give 0, 1 and 1 of 95, 79
# and 79, none a dark mark main sews; Golden Tee 1 of 6. Before the lightness
# bound below, the top-hat at 8-20 L and rings of 3-6 source pixels gave the
# same To a T verdicts and 92-103 on low_poly, and at a lost share of 0.5,
# 537 render px of low_poly's dots came back. Candidates read off those, not
# measured edges.
SPECK_INK_KERNEL_SRC_PX = 5.0
SPECK_INK_MIN_DL = 12.0
SPECK_ARM_REACH_SRC_PX = 4.0
SPECK_ARM_LOST_MIN = 0.3
SPECK_FRAGMENT_MIN_ARMS = 2

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


def _scrap_test(p):
    """Stage 3's own proxy for the run tier's floors
    (`resolve_small_regions.clears_run_floors`): True for a mask stage 4 drops."""
    run_area_px = machine.RUN_MIN_AREA_MM2 * float(p.px_per_mm) ** 2
    run_loop_px = machine.RUN_MIN_LOOP_MM * float(p.px_per_mm)
    return lambda m: m.area < run_area_px or 2 * max(m.crop.shape) < run_loop_px


def _arms(m: RegionMask, i: int, p, owner: np.ndarray, l_me: float, l_host: float,
          de_to) -> tuple[int, int]:
    """(arms, lost arms) of the art's ink leaving speck `i` (module note,
    FRAGMENT); `l_me`/`l_host` are the CIELAB L of its thread and its
    host's, `de_to(k)` CIEDE2000 from its thread to mask k's."""
    dark = l_me < l_host
    s = _src_px(p)
    k = int(np.ceil(SPECK_INK_KERNEL_SRC_PX * s))
    k += 1 - (k % 2)
    r1, r2 = max(1.5, s), SPECK_ARM_REACH_SRC_PX * s
    wy0, wx0, wy1, wx1 = _window(m, int(np.ceil(r2)) + k + 2)
    mine = m.window(wy0, wx0, wy1, wx1)
    win = p.rgb[wy0:wy1, wx0:wx1]
    L = rgb_to_lab(win.reshape(-1, 3)).reshape(win.shape[:2] + (3,))[..., 0].astype(np.float32)
    ker = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    hat = (cv2.morphologyEx(L, cv2.MORPH_CLOSE, ker) - L) if dark else (L - cv2.morphologyEx(L, cv2.MORPH_OPEN, ker))
    d = cv2.distanceTransform((~mine).astype(np.uint8), cv2.DIST_L2, 5)
    # Ink of the speck's OWN kind: also no further from its lightness than
    # its host is. A light body's convex corners read in a light top-hat too;
    # Golden Tee's dark-teal ramp along the T's top (L 21 on black, beside
    # the white fill) read two arms there and went, and the T sewed a cream run.
    ink = (hat >= SPECK_INK_MIN_DL) & (np.abs(L - l_me) <= abs(l_me - l_host))
    reach = ((ink | mine) & (d <= r2)).astype(np.uint8)
    _, lbl = cv2.connectedComponents(reach, connectivity=8)
    ring = (np.isin(lbl, np.unique(lbl[mine])) & (d > r1) & (d <= r2)).astype(np.uint8)
    na, arm, stats, _ = cv2.connectedComponentsWithStats(ring, connectivity=8)
    own = owner[wy0:wy1, wx0:wx1]
    n = lost = 0
    for a in range(1, na):
        if stats[a, cv2.CC_STAT_AREA] < 2:
            continue
        n += 1
        under = own[arm == a]
        under = under[under != i]
        if under.size and np.mean([o < 0 or de_to(int(o)) >= SPECK_MIN_DE00
                                   for o in under]) >= SPECK_ARM_LOST_MIN:
            lost += 1
    return n, lost


def specks(masks: list[RegionMask], thread_indices, p, chart, floor_px: float, thread_px: float,
           owner: np.ndarray | None = None) -> list[dict]:
    """`cfg.speck_prune`: one record per kept sub-floor mask thin enough to be
    asked (see the module docstring), `speck` = the verdict. `floor_px` is
    stage 3's detail floor in working pixels of AREA, `thread_px` the sewing
    thread's width in working pixels."""
    if owner is None:
        owner = _owner(masks, p.bg_mask.shape)
    limit = SPECK_WIDTH_SRC_PX * _src_px(p)
    # Only what stage 4 would SEW. Smaller masks are dropped there anyway;
    # handing their pixels on would only move the outlines of the shapes
    # round them (low_poly: 3,400 such masks).
    _scrap = _scrap_test(p)

    out: list[dict] = []
    others: list[set[int]] = []
    for i, m in enumerate(masks):
        area = m.area
        if not area or area >= floor_px or _held(m) or m.source == "counter":
            continue
        if _scrap(m):
            continue
        wy0, wx0, wy1, wx1 = _window(m, 1)
        mine = m.window(wy0, wx0, wy1, wx1)
        ring = cv2.dilate(mine.astype(np.uint8), _K3).astype(bool) & ~mine
        n = int(ring.sum())
        if not n:
            continue
        mean_w = 2.0 * area / n
        if mean_w >= limit:
            continue
        # The thread test reads the INSCRIBED width (2 x the deepest pixel's
        # distance to the rim, less the pixel itself): the mean above
        # under-reads a short stroke by its end caps, and on a coarse source
        # one source pixel is already 0.6 mm of real stroke.
        inscribed = 2.0 * float(cv2.distanceTransform(
            np.pad(m.crop, 1).astype(np.uint8), cv2.DIST_L2, 5).max()) - 1.0
        if inscribed >= thread_px:
            continue
        own = owner[wy0:wy1, wx0:wx1]
        page = float((ring & p.bg_mask[wy0:wy1, wx0:wx1]).sum()) / n
        nb = own[ring & (own >= 0) & (own != i)]
        figure = nb.size / n
        j = int(np.bincount(nb).argmax()) if nb.size else -1
        lab = _thread_lab(chart, thread_indices, m.layer)
        host = _thread_lab(chart, thread_indices, masks[j].layer) if j >= 0 else None
        de = float(deltaE_ciede2000(lab, host)) if j >= 0 else None
        others.append({int(k) for k in np.unique(nb)} - {j})
        out.append({
            "index": i, "layer": m.layer, "area_px": area,
            "mean_width_src_px": round(mean_w / _src_px(p), 3),
            "mean_width_px": round(mean_w, 3), "inscribed_px": round(inscribed, 3),
            "page": round(page, 3), "figure": round(figure, 3), "neighbour": j,
            "de_neighbour": None if de is None else round(de, 2),
            "l": round(float(lab[0]), 2), "l_neighbour": None if host is None else round(float(host[0]), 2),
            "dl_neighbour": None if host is None else round(float(lab[0] - host[0]), 2),
            "speck": bool(j >= 0 and figure >= SPECK_FIGURE_CONTACT_MIN
                          and page <= SPECK_PAGE_CONTACT_MAX and de >= SPECK_MIN_DE00),
        })
    # A slit (module note) is read against the first verdicts: what else is on
    # its rim must be a speck leaving or a scrap stage 4 drops.
    first = {rec["index"] for rec in out if rec["speck"]}
    de_cache: dict[tuple[int, int], float] = {}

    def _de(a: int, b: int) -> float:
        if (a, b) not in de_cache:
            de_cache[(a, b)] = float(deltaE_ciede2000(_thread_lab(chart, thread_indices, a),
                                                      _thread_lab(chart, thread_indices, b)))
        return de_cache[(a, b)]

    for rec, rest in zip(out, others):
        rec["slit"] = bool(rec["speck"] and rec["dl_neighbour"] >= SPECK_SLIT_MIN_DL
                           and all(k in first or _scrap(masks[k]) for k in rest))
        rec["arms"] = rec["arms_lost"] = None
        if rec["speck"] and not rec["slit"]:
            me = masks[rec["index"]].layer
            rec["arms"], rec["arms_lost"] = _arms(masks[rec["index"]], rec["index"], p, owner,
                                                  rec["l"], rec["l_neighbour"],
                                                  lambda k: _de(me, masks[k].layer))
        rec["fragment"] = bool(rec["arms_lost"] is not None
                               and rec["arms_lost"] >= SPECK_FRAGMENT_MIN_ARMS)
        rec["speck"] = bool(rec["speck"] and not rec["slit"] and rec["fragment"])
    return out


def prune_specks(masks: list[RegionMask], thread_indices, p, chart, floor_px: float,
                 thread_px: float) -> tuple[list[RegionMask], dict]:
    """`cfg.speck_prune`: each speck's pixels given to the mask it lies in.
    -> (masks, {"specks": n}); the list as given when there is none."""
    if not masks:
        return masks, {"specks": 0}
    found = [rec for rec in specks(masks, thread_indices, p, chart, floor_px, thread_px)
             if rec["speck"]]
    if not found:
        return masks, {"specks": 0}
    masks = list(masks)
    gone: set[int] = set()
    for rec in found:
        i, j = rec["index"], rec["neighbour"]
        # A speck whose host was itself a speck, handed on already: the host's
        # pixels now live in ITS host, so follow them there. Two specks that
        # host each other lead back here: this one stays as it was.
        seen = {i}
        while j in gone and j not in seen:
            seen.add(j)
            j = next(r["neighbour"] for r in found if r["index"] == j)
        if j in seen:
            continue
        masks[j] = replace(masks[j], crop=masks[j].crop.copy())     # the caller's mask is not ours
        masks[j].union_from(RegionMask(crop=masks[i].crop, origin=masks[i].origin,
                                       frame_shape=masks[j].frame_shape, layer=masks[j].layer))
        gone.add(i)
    kept = [m for i, m in enumerate(masks) if i not in gone]
    return kept, {"specks": len(gone)}


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
