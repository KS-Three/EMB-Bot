"""`cfg.stroke_bridge_keep` (built OFF 2026-11-14): a thin stroke of a shape's
own ink, broken into crumbs, that bridges two shapes of that ink on the page
is kept whole (`stage3_segment._stroke_bridges`).

Kent's arabic calligraphy at 80 mm (2 pins, "missing line"): each stem between
two leaves reached stage 3 as crumbs of the leaves' gold and their darker edge
gold (11.9 dE76 apart, 65 from the page), about 120 px together at 11.5 px/mm,
under the chain rescue's 297 px; each was absorbed into a leaf. ON, the six
stems of the two wreaths are kept as strokes.

Synthetic frame, 8 px/mm: the run floors are 10.24 px of area and a 17.6 px
perimeter proxy.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage3_segment import (BRIDGE_GROUND_MIN, BRIDGE_HOST_CONTACT_MAX,
                                           RegionMask, _stroke_bridges)

GOLD, DARK_GOLD, NAVY = [64.4, 1.1, 55.3], [58.6, 9.4, 49.2], [30.0, 5.0, -30.0]
LAB = np.asarray([GOLD, DARK_GOLD, NAVY], np.float64)
PPM = 8.0
H, W = 40, 64


def _mask(*rects):
    m = np.zeros((H, W), bool)
    for y0, x0, y1, x1 in rects:
        m[y0:y1, x0:x1] = True
    return m


def _run(masks_layers):
    regs = [RegionMask.from_full(m, layer) for m, layer in masks_layers]
    areas = [r.area for r in regs]
    boxes = [r.bbox for r in regs]
    floor = (1.5 * PPM) ** 2
    small = [i for i, a in enumerate(areas) if a < floor]
    keep = [i for i, a in enumerate(areas) if a >= floor]
    left, kept = _stroke_bridges(regs, areas, boxes, small, keep, LAB,
                                 machine.RUN_MIN_AREA_MM2 * PPM ** 2,
                                 machine.RUN_MIN_LOOP_MM * PPM)
    return regs, small, left, kept


LEAVES = [(_mask((10, 0, 30, 20)), 0), (_mask((10, 40, 30, 60)), 0)]
#: a 2 px stem from leaf to leaf, in four crumbs alternating the two golds
STEM = [(_mask((19, 20, 21, 25)), 1), (_mask((19, 25, 21, 28)), 0),
        (_mask((19, 28, 21, 35)), 1), (_mask((19, 35, 21, 40)), 0)]


def test_default_is_on():
    # Kent 2026-11-15, review pack (review-1115): ticked ON
    assert PipelineConfig().stroke_bridge_keep is True
    assert BRIDGE_HOST_CONTACT_MAX < BRIDGE_GROUND_MIN


def test_a_crumbled_stem_between_two_leaves_is_kept_as_one_stroke():
    regs, small, left, kept = _run(LEAVES + STEM)
    assert left == [] and len(kept) == 1
    stroke = regs[kept[0]]
    assert stroke.area == 40 and stroke.layer == 1      # the layer holding most of it (24 of 40)


def test_a_halo_along_two_close_shapes_is_not_a_bridge():
    """Crumbs filling a 2 px gap between two leaves touch them along their
    whole length: a seam, not a stroke (it would weld them)."""
    leaves = [(_mask((10, 0, 30, 20)), 0), (_mask((10, 22, 30, 42)), 0)]
    gap = [(_mask((10, 20, 20, 22)), 1), (_mask((20, 20, 30, 22)), 0)]
    regs, small, left, kept = _run(leaves + gap)
    assert kept == [] and sorted(left) == sorted(small)


def test_crumbs_of_another_ink_are_not_the_hosts_stroke():
    stem = [(m, 2) for m, _l in STEM]
    regs, small, left, kept = _run(LEAVES + stem)
    assert kept == []


def test_a_spur_off_one_shape_is_not_a_bridge():
    stem = [(_mask((19, 20, 21, 25)), 1), (_mask((19, 25, 21, 30)), 0)]
    regs, small, left, kept = _run(LEAVES[:1] + stem)
    assert kept == []
