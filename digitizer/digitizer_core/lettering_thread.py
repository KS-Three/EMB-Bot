"""Lettering's thread, after the regions are final (2026-11-01, both OFF).

Precision Drone on the 2026-10-31 lettering board read cc +0.05 (PRECISION)
and 0.00 (AND DRONE) against the pro's +0.82 and +1.00. Recolouring our own
file and re-reading it, every stitch untouched, closed both, so neither gap
is construction:

* `cfg.lettering_stray_word_thread`: `small_text` drops a letter that does not
  sit on its line from the cluster (`small_text_stray`). AND's A was one, and
  kept the darker thread it had snapped to: 18.2 dE00 off its own word. Here a
  stray that sits on a cluster's line takes the cluster's thread.
* `cfg.lettering_contrast_floor`: PRECISION's thread follows the art, silver
  on a dark panel, and sits 7.7 dE00 from a light hat. Here a text cluster
  within `cfg.lettering_contrast_floor_de00` of `cfg.garment_rgb` moves to a
  thread that clears it. No garment colour known: nothing moves. Letters
  sewn ON other thread are off the fabric, whatever their colour: MFab's white
  letters sit on its black badge, covered 1.00 against PRECISION's 0.05, and
  moving them cost a cone and took AND WELDING to 0.00.

A customer's stated colour (a review recolour) is never moved. The thread
travels on the region alone, as `enforce_color_cap` does, so both run before
the colour cap's second pass and the cap still has the last word.
"""
from __future__ import annotations

import numpy as np

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .regions import Region
from .threads import rgb_to_lab

#: A stray joins a word only in a near thread: 18.2 is AND's A, and a mark
#: further off than this is a colour of its own, not a snap that went astray.
STRAY_MAX_DE00 = 25.0
#: The gap to the nearest letter, in letter heights.
STRAY_MAX_GAP_H = 1.0
#: Its height against that letter's, and how much of the shorter one the two
#: share vertically.
STRAY_HEIGHT_RATIO = 0.75
STRAY_MIN_OVERLAP = 0.6
#: The floor prefers a thread the design already sews (no new cone) within this
#: of the old one; past it the nearest chart thread that clears is the honest
#: answer. A white word must not go orange because orange is on the design.
FLOOR_MAX_MOVE_DE00 = 35.0
#: Letters this much on other thread's outlines (padded by `ON_GROUND_PAD_MM`,
#: the seam between a letter and what it sits on) read against that, not the
#: fabric.
ON_GROUND_SHARE = 0.5
ON_GROUND_PAD_MM = 0.3


def _set_thread(region: Region, chart, thread: int, stamp: str) -> None:
    region.meta[stamp] = region.thread_number
    region.thread_index = int(thread)
    region.thread_number = chart[int(thread)].number


def _pinned(region: Region, shape_overrides: dict) -> bool:
    return (shape_overrides.get(region.shape_id) or {}).get("thread_index") is not None


def _clusters(regions: list[Region]) -> dict[str, list[Region]]:
    out: dict[str, list[Region]] = {}
    for r in regions:
        cid = r.meta.get("text_cluster_id")
        if cid and r.meta.get("stitched", True):
            out.setdefault(cid, []).append(r)
    return out


def _on_its_line(stray: Region, letter: Region) -> bool:
    x0, y0, x1, y1 = stray.polygon.bounds
    lx0, ly0, lx1, ly1 = letter.polygon.bounds
    h, lh = y1 - y0, ly1 - ly0
    if h <= 0 or lh <= 0 or min(h, lh) / max(h, lh) < STRAY_HEIGHT_RATIO:
        return False
    if min(y1, ly1) - max(y0, ly0) < STRAY_MIN_OVERLAP * min(h, lh):
        return False
    return stray.polygon.distance(letter.polygon) <= STRAY_MAX_GAP_H * lh


def stray_word_thread(regions: list[Region], chart, shape_overrides: dict) -> int:
    """Each `small_text_stray` on a single-thread cluster's line takes that
    thread, when it is within `STRAY_MAX_DE00`. -> how many moved."""
    clusters = _clusters(regions)
    moved = 0
    for r in regions:
        if not r.meta.get("small_text_stray") or not r.meta.get("stitched", True):
            continue
        if _pinned(r, shape_overrides):
            continue
        hits = [m for members in clusters.values()
                if len({x.thread_index for x in members}) == 1
                for m in members if _on_its_line(r, m)]
        if not hits:
            continue
        nearest = min(hits, key=lambda m: r.polygon.distance(m.polygon))
        t = nearest.thread_index
        if t != r.thread_index and chart.delta_e(r.thread_index, t) <= STRAY_MAX_DE00:
            _set_thread(r, chart, t, "lettering_word_thread_from")
            moved += 1
    return moved


#: `cfg.group_consistent_thread`: a thread held by under this share of a
#: word's letters is a lone letter's snap, and the word's thread is the one
#: held by over half of them (Bridge's RESTAURANT: 1 of 11 against 10).
WORD_THREAD_LONE_SHARE = 0.25


def word_thread(regions: list[Region], chart, shape_overrides: dict) -> int:
    """`cfg.group_consistent_thread` (built OFF 2026-11-13): a text-cluster
    letter on a thread under `WORD_THREAD_LONE_SHARE` of its word takes the
    thread over half the word sews, when within `STRAY_MAX_DE00` of it -- the
    stray rule's own limit, for a letter that stayed IN its cluster. Bridge's
    U of RESTAURANT is blue art on yellow, read green at its thin strokes,
    and snapped to 5422 Swiss Ivy 18.4 dE00 off its ten Caribbean siblings;
    sewn on its own it came out the one thin letter. -> how many moved.

    The U came from the dark-ink lightness read, so its own (wrong) colour
    against the yellow also made it a dark-ink bean (`thin_ink.bean_dark_ink`)
    -- the thin stitching Kent pinned. A letter moved here drops a dark-ink
    bean none of its word-mates carries, as a review-pinned tier drops it
    (`thin_ink.settle_dark_ink_bean`), and takes the ladder with them."""
    from .beanletters import BEAN_LETTER_KEY
    from .thin_ink import DARK_INK_GROUND_KEY

    moved = 0
    for members in _clusters(regions).values():
        counts: dict[int, int] = {}
        for r in members:
            counts[r.thread_index] = counts.get(r.thread_index, 0) + 1
        if len(counts) < 2:
            continue
        word_t, n = max(counts.items(), key=lambda kv: (kv[1], -kv[0]))
        if 2 * n <= len(members):
            continue
        for r in members:
            t = r.thread_index
            if t == word_t or counts[t] >= WORD_THREAD_LONE_SHARE * len(members):
                continue
            if _pinned(r, shape_overrides) or chart.delta_e(t, word_t) > STRAY_MAX_DE00:
                continue
            _set_thread(r, chart, word_t, "lettering_word_thread_from")
            if (r.meta.get(BEAN_LETTER_KEY) and r.meta.get(DARK_INK_GROUND_KEY)
                    and not any(m.meta.get(BEAN_LETTER_KEY) for m in members if m is not r)):
                del r.meta[BEAN_LETTER_KEY]
                r.meta["lettering_word_unbeaned"] = True
            moved += 1
    return moved


def _floor_target(thread: int, sewn: set[int], chart, ok: np.ndarray) -> int | None:
    """The thread a cluster in `thread` moves to: the nearest one on the design
    that clears (`ok`, per chart index) within `FLOOR_MAX_MOVE_DE00`, else the
    nearest in the chart that clears; None when the chart has none."""
    def nearest(pool):
        return min(pool, key=lambda t: (chart.delta_e(thread, t), t), default=None)
    on_design = [t for t in sewn if t != thread and ok[t]
                 and chart.delta_e(thread, t) <= FLOOR_MAX_MOVE_DE00]
    return nearest(on_design) if on_design else nearest(
        [t for t in range(len(chart)) if ok[t]])


def contrast_floor(regions: list[Region], chart, garment_rgb, floor_de00: float,
                   shape_overrides: dict) -> int:
    """Move each text cluster's thread off the garment when it sits within
    `floor_de00`, unless it sews on other thread. -> how many regions moved. A pinned member keeps its thread;
    the rest of its cluster still moves."""
    garment = rgb_to_lab(np.array([list(garment_rgb)[:3]], dtype=np.float64))
    from skimage.color import deltaE_ciede2000
    ok = deltaE_ciede2000(np.broadcast_to(garment, chart.lab.shape), chart.lab) >= floor_de00
    sewn = {r.thread_index for r in regions if r.meta.get("stitched", True)}
    moved = 0
    for members in _clusters(regions).values():
        if _on_sewn_ground(members, regions):
            continue
        for thread in sorted({r.thread_index for r in members if not ok[r.thread_index]}):
            target = _floor_target(thread, sewn, chart, ok)
            if target is None:
                continue
            for r in members:
                if r.thread_index == thread and not _pinned(r, shape_overrides):
                    _set_thread(r, chart, target, "lettering_contrast_from")
                    moved += 1
    return moved


def _on_sewn_ground(members: list[Region], regions: list[Region]) -> bool:
    threads = {r.thread_index for r in members}
    ids = {id(r) for r in members}
    grounds = []
    for r in regions:
        if id(r) in ids or r.thread_index in threads or not r.meta.get("stitched", True):
            continue
        polys = [r.polygon] if isinstance(r.polygon, Polygon) else list(r.polygon.geoms)
        grounds.extend(Polygon(p.exterior) for p in polys)
    if not grounds:
        return False
    word = unary_union([r.polygon for r in members])
    covered = unary_union(grounds).buffer(ON_GROUND_PAD_MM).intersection(word).area
    return covered >= ON_GROUND_SHARE * word.area


def apply_lettering_thread(regions: list[Region], chart, cfg, shape_overrides: dict) -> None:
    """Both rules, in `finish_generation`, with `stitched` resolved. The floor
    first: a stray then takes the thread its word finally sews in."""
    if getattr(cfg, "group_consistent_thread", False):
        # first: the floor then moves the word on the one thread it sews
        word_thread(regions, chart, shape_overrides)
    if cfg.lettering_contrast_floor and cfg.garment_rgb is not None:
        contrast_floor(regions, chart, cfg.garment_rgb,
                       cfg.lettering_contrast_floor_de00, shape_overrides)
    if cfg.lettering_stray_word_thread:
        stray_word_thread(regions, chart, shape_overrides)
