"""`cfg.tiny_detail_keep` (built OFF 2026-11-14): a detail a few pixels
across survives stage 2's anti-alias filter and stage 3's floors.

Kent's heraldic crest at 80 mm, "Missing the eye" (2 pins). Each eagle eye is
about 12 x 6 source pixels: two white specks either side of a black pupil in a
navy head. Stage 1 keeps it; stage 2's majority filter repaints every edge
pixel to the dominant interior label round it, and a feature 2-3 px across
has no interior pixel of its own, so two passes wipe it. Kept through stage 2,
stage 3 would still drop each colour piece under the run floors. ON: the
filter leaves a pixel that IS its colour, and touching sub-floor pieces in one
host that together clear the run floors are kept as one detail.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage2_quantize import FAR_PIXEL_DE, PURE_PIXEL_DE, _majority_filter
from digitizer_core.stage3_segment import RegionMask, _compound_details
from digitizer_core.threads import rgb_to_lab

NAVY, WHITE, BLACK = (60, 76, 110), (255, 255, 255), (0, 0, 0)
LAB = rgb_to_lab(np.asarray([NAVY, WHITE, BLACK], np.float64))
PPM = 8.0


def _scene():
    """A 40 x 40 navy field; an eye two rows tall: white 2x3, black 2x4, white 2x3."""
    labels = np.zeros((40, 40), np.int32)
    labels[18:20, 15:18] = 1
    labels[18:20, 18:22] = 2
    labels[18:20, 22:25] = 1
    rgb = np.array([NAVY, WHITE, BLACK], np.float64)[labels]
    lab = rgb_to_lab(rgb.reshape(-1, 3)).reshape(40, 40, 3)
    return labels, lab


def test_default_is_off():
    assert PipelineConfig().tiny_detail_keep is False
    assert PURE_PIXEL_DE < FAR_PIXEL_DE


def test_the_filter_eats_an_eye_and_keep_pure_holds_it():
    """OFF, the eye's ends go to the navy (their 3x3 reaches interior navy);
    on the crest, where the pieces are 1-2 px, 49 off-head pixels in the eye
    window fall to 14 (measured 2026-11-14). ON, every pixel keeps its label."""
    labels, lab = _scene()
    valid = np.ones_like(labels, bool)
    off = _majority_filter(labels, valid, 3, 2)
    assert (off[18:20, 15:25] == 0).sum() >= 4
    on = _majority_filter(labels, valid, 3, 2, keep_pure=(lab, LAB))
    assert (on == labels).all()


def test_a_blend_pixel_is_still_cleaned():
    """A halo pixel half way between navy and white, labelled white alone in
    the navy: near both centres, so it is repainted as before."""
    labels, lab = _scene()
    labels[:] = 0
    labels[5, 5] = 1
    lab = lab.copy()
    lab[:] = LAB[0]
    lab[5, 5] = (LAB[0] + LAB[1]) / 2.0
    on = _majority_filter(labels, np.ones_like(labels, bool), 3, 2, keep_pure=(lab, LAB))
    assert on[5, 5] == 0


def _regions(labels):
    out = [RegionMask.from_full(labels == 0, 0)]
    for layer in (1, 2):
        from scipy import ndimage
        cc, n = ndimage.label(labels == layer)
        out += [RegionMask.from_full(cc == c, layer) for c in range(1, n + 1)]
    return out


def _run(labels):
    regs = _regions(labels)
    areas = [r.area for r in regs]
    boxes = [r.bbox for r in regs]
    small = [i for i in range(1, len(regs))]
    return regs, _compound_details(regs, areas, boxes, small, [0], LAB,
                                   machine.RUN_MIN_AREA_MM2 * PPM ** 2,
                                   machine.DOT_RUNG_MIN_LOOP_MM * PPM, 6.0)


def test_an_eye_of_three_pieces_is_kept_as_one_white_detail():
    labels, _lab = _scene()
    regs, (left, kept) = _run(labels)
    assert left == [] and len(kept) == 1
    eye = regs[kept[0]]
    assert eye.layer == 1                      # white: the colour farthest from the navy
    assert eye.area == 6 + 8 + 6 and eye.dot_rung


def test_a_single_piece_is_left_to_the_rescue():
    labels = np.zeros((40, 40), np.int32)
    labels[18:21, 15:25] = 1
    regs, (left, kept) = _run(labels)
    assert kept == [] and left == [1]


def test_pieces_under_the_run_floors_together_stay_small():
    labels = np.zeros((40, 40), np.int32)
    labels[18:20, 18:20] = 1
    labels[18:20, 20:22] = 2                   # 8 px, 4 px long: under both floors
    regs, (left, kept) = _run(labels)
    assert kept == [] and sorted(left) == [1, 2]
