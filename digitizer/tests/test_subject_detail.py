"""`tools.subject_detail`: the subject-loss readings behave on a picture whose
answer is known (2026-11-14, build walkthrough item 2). An instrument, so the
test pins direction and the design-json path, not any threshold's merit."""
from __future__ import annotations

import numpy as np

from tools.subject_detail import design_segments, readings, somers_d, thread_map

PPM = 8.0
GARMENT = (235, 232, 223)


class _P:
    """The four fields of a Prep the readings use: 40 x 30 mm of green with
    a 10 x 10 mm red square in the middle, all of it artwork."""

    def __init__(self):
        h, w = int(30 * PPM), int(40 * PPM)
        self.rgb = np.zeros((h, w, 3), np.uint8)
        self.rgb[:] = (40, 140, 40)
        self.rgb[int(10 * PPM):int(20 * PPM), int(15 * PPM):int(25 * PPM)] = (220, 30, 30)
        self.bg_mask = np.zeros((h, w), bool)
        self.art_bbox = (0, 0, w, h)
        self.px_per_mm = PPM


def _fill(rgb, x0, y0, x1, y1, step=0.3):
    """Horizontal rows over a plan-mm box (origin at the art bbox centre)."""
    return [(rgb, [(x0, y), (x1, y)]) for y in np.arange(y0, y1, step)]


def test_a_faithful_sew_keeps_the_subject_and_a_flat_one_loses_it():
    p = _P()
    green = (40, 140, 40)
    kept = _fill(green, -20, -15, 20, 15) + _fill((220, 30, 30), -5, -5, 5, 5)
    lost = _fill(green, -20, -15, 20, 15)                       # the square sewn as meadow
    a, b = readings(p, kept, GARMENT), readings(p, lost, GARMENT)
    assert a["edge_recall"] > 0.9 and b["edge_recall"] < 0.1
    assert a["blob_lost_frac"] == 0.0 and b["blob_lost_frac"] > 0.0
    assert a["salient_lost_frac"] == 0.0 and b["salient_lost_frac"] > 0.0
    assert a["edge_density"] == b["edge_density"]               # the control reads the source only


def test_design_json_runs_land_where_the_plan_put_them():
    """0.1 mm y-up units back to plan mm y-down; a jump starts a new run, a
    colour change moves to the next thread."""
    design = {"colors": [{"r": 1, "g": 2, "b": 3}, {"r": 4, "g": 5, "b": 6}],
              "stitches": [{"x": 0, "y": 0, "type": "jump"}, {"x": 50, "y": 0, "type": "stitch"},
                           {"x": 50, "y": -20, "type": "stitch"}, {"x": 50, "y": -20, "type": "trim"},
                           {"x": 50, "y": -20, "type": "color"}, {"x": -10, "y": 10, "type": "jump"},
                           {"x": -30, "y": 10, "type": "stitch"}, {"x": 0, "y": 0, "type": "end"}]}
    segs = design_segments(design)
    assert segs == [((1, 2, 3), [(0.0, 0.0), (5.0, 0.0), (5.0, 2.0)]),
                    ((4, 5, 6), [(-1.0, -1.0), (-3.0, -1.0)])]
    t = thread_map(_P(), segs, GARMENT)
    cx, cy = 20 * PPM, 15 * PPM
    assert tuple(t[int(cy), int(cx + 2.5 * PPM)]) == (1, 2, 3)


def test_somers_d_is_zero_at_chance_and_one_when_every_pair_is_ordered():
    assert somers_d(np.array([0.9, 0.8]), np.array([0.1, 0.2]), +1) == 1.0
    assert somers_d(np.array([0.5, 0.5]), np.array([0.5, 0.5]), +1) == 0.0
    assert somers_d(np.array([0.1]), np.array([0.9]), -1) == 1.0
