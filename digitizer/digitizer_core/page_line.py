"""`cfg.page_line_front` (built OFF 2026-11-17): sew the art's thin white
lines BEFORE the ink either side of them.

The fault (prime grader, `docs/prime-grader/scorecard-2026-11-17.md`,
`gaulke_roofing_hat`): under the house mark's inner roof the art has a
hairline white gap with a thin black line beneath it. Stage 1.3
(`two_tone.keep_lines`, 2026-10-08) hands such a channel back as light ink
and widens it to the satin floor INTO the ink either side, because the fills
beside a bare-fabric channel that thin close it under pull. That white then
sews as a layer AFTER the black, on top of it: a satin bar wider than the
art's gap, laid over the black line below it, which is left as a ragged
fringe.

The cure is the order, not the width: these lines go in a front layer, one
per thread, so the black lays over their edges and the line beneath stays
whole. The visible white is then the white the ink leaves, never wider than
the channel was.

The lines are read off `Prep.page_lines` (the pixels `keep_lines` handed
back, recorded by `two_tone.apply`); a region is one when at least
`PAGE_LINE_SHARE` of its footprint lies on them. Nothing here reads a
fabric number.
"""
from __future__ import annotations

import numpy as np

#: share of a region's own footprint that must lie on the kept-line pixels.
PAGE_LINE_SHARE = 0.6


def plan_page_lines(regions, p) -> list:
    """The regions that ARE a kept page line. Pure: writes nothing."""
    lines = getattr(p, "page_lines", None)
    if lines is None or not lines.any():
        return []
    from .stage4_vectorize import _region_footprint_window

    h, w = lines.shape
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    out = []
    for r in regions:
        win = _region_footprint_window(r, (h, w), cx, cy, p.px_per_mm)
        if win is None:
            continue
        wy0, wx0, fp = win
        area = int(fp.sum())
        if area == 0:
            continue
        on = int(np.count_nonzero(fp & lines[wy0:wy0 + fp.shape[0], wx0:wx0 + fp.shape[1]]))
        if on >= PAGE_LINE_SHARE * area:
            out.append(r)
    return out


def apply_page_lines(regions, thread_indices: list[int], p) -> tuple[list[int], int]:
    """Re-layer the page lines to the front, one layer per thread in the
    order each first appears. -> (thread indices with the new front layers,
    how many regions moved). Runs before `compact_layers`, which drops any
    layer this empties."""
    moved = plan_page_lines(regions, p)
    if not moved:
        return list(thread_indices), 0
    front: list[int] = []
    for r in moved:
        if r.thread_index not in front:
            front.append(r.thread_index)
    ids = {r.shape_id for r in moved}
    for r in regions:
        if r.shape_id in ids:
            r.meta["page_line"] = True
            r.meta["layer"] = front.index(r.thread_index)
        else:
            r.meta["layer"] = int(r.meta["layer"]) + len(front)
    return front + [int(t) for t in thread_indices], len(moved)
