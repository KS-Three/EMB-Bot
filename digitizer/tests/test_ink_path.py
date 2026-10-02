"""`ink_path.read_cluster_ink` — a letter's strokes read from the SOURCE INK.

Bridge's "RESTAURANT" (2026-10-02): 0.7 mm strokes in a 3.5 px/mm file. The
region mask closes every counter before a polygon exists, so the traced shape
is a blob and its skeleton is a squiggle. The ink itself still carries the
letter: projected onto the ground-to-ink colour axis and thresholded, its
skeleton reads as strokes (`docs/superpowers/specs/2026-10-02-bean-letters-
design.md`, "What the spikes found").
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.ink_path import MemberInk, read_cluster_ink
from digitizer_core.legibility import _plan_frame
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import prep

SRC_PX_PER_MM = 3.5
SS = 10                                   # supersampling of the drawing
MARGIN_MM = 4.0


def _draw(rects_mm: list[tuple[float, float, float, float]], *, cutout: bool = False):
    """Dark rectangles (x0, y0, x1, y1 in mm) on white, drawn supersampled and
    reduced by area to SRC_PX_PER_MM so every edge is an anti-alias ramp.
    -> (image, artwork width in mm, artwork centre in mm)."""
    xs = [v for r in rects_mm for v in (r[0], r[2])]
    ys = [v for r in rects_mm for v in (r[1], r[3])]
    w_mm, h_mm = max(xs) - min(xs), max(ys) - min(ys)
    s = SRC_PX_PER_MM * SS
    W, H = int(round((w_mm + 2 * MARGIN_MM) * s)), int(round((h_mm + 2 * MARGIN_MM) * s))
    ink = np.zeros((H, W), np.uint8)
    for x0, y0, x1, y1 in rects_mm:
        cv2.rectangle(ink, (int(round((x0 - min(xs) + MARGIN_MM) * s)), int(round((y0 - min(ys) + MARGIN_MM) * s))),
                      (int(round((x1 - min(xs) + MARGIN_MM) * s)) - 1, int(round((y1 - min(ys) + MARGIN_MM) * s)) - 1), 255, -1)
    small = cv2.resize(ink, (W // SS, H // SS), interpolation=cv2.INTER_AREA)
    if cutout:
        img = np.zeros(small.shape + (4,), np.uint8)
        img[..., :3] = 30
        img[..., 3] = small
    else:
        v = (255 - small.astype(np.float32) * (225 / 255.0)).astype(np.uint8)
        img = np.dstack([v, v, v])
    return img, w_mm, ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2)


# Two far-apart marks that make the artwork 33 mm wide, so the one pixel the
# edge ramp adds to the art box is 1% of the scale and not 15%.
ANCHORS = [(-15.0, 1.0, -14.0, 2.0), (17.0, 1.0, 18.0, 2.0)]


def _read(rects_mm, member_boxes_mm, **kw) -> tuple[list[MemberInk], object]:
    img, w_mm, (cx, cy) = _draw(list(rects_mm) + ANCHORS, **kw)
    cfg = PipelineConfig(target_width_mm=w_mm, garment_id="left_chest")
    p = prep(img, cfg)
    assert p.input_px_per_mm == pytest.approx(SRC_PX_PER_MM, abs=0.2)
    members = []
    for i, (x0, y0, x1, y1) in enumerate(member_boxes_mm):
        poly = box(x0 - cx, y0 - cy, x1 - cx, y1 - cy)       # stage 4's frame: centred on the artwork
        members.append(Region(shape_id=f"S{i}", polygon=poly, thread_index=0, thread_number="0020",
                              area_mm2=poly.area, meta={}))
    return read_cluster_ink(p, members), (cx, cy)


# An E, 2.5 x 3.1 mm: 0.7 mm strokes, 0.5 mm counters — closed in any mask a
# 3.5 px/mm file can give, open in the ink.
E = [(0.0, 0.0, 0.7, 3.1), (0.0, 0.0, 2.5, 0.7), (0.0, 1.2, 2.5, 1.9), (0.0, 2.4, 2.5, 3.1)]
E_BOX = [(0.0, 0.0, 2.5, 3.1)]


def _arm_rows(ink: MemberInk, cx: float, cy: float) -> set[int]:
    """Which of the E's three arm rows (0, 1, 2) and two counter rows (10, 11)
    the path reaches at the letter's right-hand end."""
    hit = set()
    for spine in ink.spines:
        for x, y in spine:
            if x + cx < 1.6:               # well right of the stem (the E is 2.5 wide)
                continue
            yy = y + cy
            for row, (lo, hi) in {0: (0.0, 0.7), 10: (0.8, 1.1), 1: (1.2, 1.9), 11: (2.0, 2.3), 2: (2.4, 3.1)}.items():
                if lo <= yy <= hi:
                    hit.add(row)
    return hit


def test_the_ink_keeps_the_counters_a_blob_does_not():
    (ink,), (cx, cy) = _read(E, E_BOX)
    assert ink.spines, "the E must give a path"
    assert _arm_rows(ink, cx, cy) == {0, 1, 2}
    assert ink.stroke_mm == pytest.approx(0.7, abs=0.25)


def test_a_short_arm_reaches_the_end_of_its_ink():
    """A skeleton stops half a stroke short of every free end, which left
    bridge's E with a 0.47 mm middle arm that two length floors then dropped
    (it sewed as a C). Free ends are carried out to the ink's edge."""
    (ink,), (cx, cy) = _read(E, E_BOX)
    middle = [x + cx for s in ink.spines for x, y in s if 1.2 <= y + cy <= 1.9]
    assert middle and max(middle) >= 2.1
    stem = [y + cy for s in ink.spines for x, y in s if x + cx <= 0.7]
    assert min(stem) <= 0.45 and max(stem) >= 2.65


def test_a_cutout_reads_its_ink_from_alpha_and_agrees_with_the_white_ground():
    (white,), _ = _read(E, E_BOX)
    (cut,), (cx, cy) = _read(E, E_BOX, cutout=True)
    assert _arm_rows(cut, cx, cy) == {0, 1, 2}
    assert cut.stroke_mm == pytest.approx(white.stroke_mm, abs=0.15)


def test_a_bold_letter_measures_bold():
    """The trigger's other side: a 1.6 mm stem is not small lettering."""
    (ink,), _ = _read([(0.0, 0.0, 1.6, 5.0)], [(0.0, 0.0, 1.6, 5.0)])
    assert ink.stroke_mm == pytest.approx(1.6, abs=0.3)


def test_ink_belongs_to_the_nearest_member():
    """Two stems 0.4 mm apart — one blur away from one shape. Each member
    gets its own stem and neither path strays into the other's box."""
    bars = [(0.0, 0.0, 0.7, 4.0), (1.1, 0.0, 1.8, 4.0)]
    inks, (cx, _cy) = _read(bars, bars)
    assert len(inks) == 2 and all(i.spines for i in inks)
    left = [x + cx for s in inks[0].spines for x, _y in s]
    right = [x + cx for s in inks[1].spines for x, _y in s]
    assert max(left) < 0.9 and min(right) > 0.9


def test_nothing_to_read_is_an_empty_answer_not_an_error():
    (ink,), _ = _read(E, [(40.0, 40.0, 42.0, 42.0)])       # a member box over bare ground
    assert ink.spines == [] and ink.stroke_mm is None
    assert read_cluster_ink(None, []) == []
