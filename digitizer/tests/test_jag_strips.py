"""`tools/jag_strips.py`: the frame arithmetic a pin crosses to land on a
stage's picture, and the bare-inside-art count. Synthetic, nothing digitizes."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import jag_strips as js  # noqa: E402


def test_a_pin_stored_as_fractions_lands_in_design_mm():
    it = {"img_w": 1200, "img_h": 600, "px_per_mm": 12.0, "pad_mm": 2.0}
    assert js.pin_mm(it, {"x_mm": 3.5, "y_mm": 1.0}) == (3.5, 1.0)
    x, y = js.pin_mm(it, {"x": 0.5, "y": 0.5})
    assert (round(x, 6), round(y, 6)) == (48.0, 23.0)


def test_design_runs_split_at_jumps_and_advance_colour_at_a_change():
    design = {"colors": [{"r": 1, "g": 2, "b": 3}, {"r": 4, "g": 5, "b": 6}],
              "stitches": [{"type": "stitch", "x": 0, "y": 0}, {"type": "stitch", "x": 10, "y": -10},
                           {"type": "jump", "x": 20, "y": 0}, {"type": "stitch", "x": 20, "y": 0},
                           {"type": "color", "x": 20, "y": 0}, {"type": "stitch", "x": 30, "y": 0}]}
    runs = js.design_runs_mm(design)
    assert [len(p) for _rgb, p in runs] == [2, 1, 1]
    assert runs[0][1][1] == (1.0, 1.0)          # 0.1 mm units, y flipped to the plan's y-down
    assert runs[2][0] == (4, 5, 6)


def test_bare_inside_art_counts_an_unsewn_hole_and_not_a_covered_one():
    square = Polygon([(0, 0), (6, 0), (6, 6), (0, 6)])
    rows = [[(x, 0.0), (x, 6.0)] for x in np.arange(0.0, 6.01, 0.3)]
    cap = {"regions": [(square, 0, "S1", {})],
           "runs": [[((0, 0, 0), [(pts, "fill", False, False, "S1") for pts in rows])]]}
    assert js.bare_inside_art(cap, cap)[0] == 0.0
    gap = {"regions": cap["regions"],
           "runs": [[((0, 0, 0), [(pts, "fill", False, False, "S1") for pts in rows
                                  if not 2.0 < pts[0][0] < 4.0])]]}
    mm2, patches = js.bare_inside_art(cap, gap)
    assert mm2 > 3.0 and patches == 1


def test_travel_under_other_stitching_is_not_exposed_and_travel_off_it_is():
    rows =[[(0.0, y), (6.0, y)] for y in np.arange(0, 6.01, 0.3)]
    under = [(1.0, 1.0), (5.0, 5.0)]               # inside the fill's footprint
    over_bare = [(6.0, 6.0), (16.0, 6.0)]          # 10 mm past it
    cap = {"runs": [[((0, 0, 0), [(r, "fill", False, False, "S") for r in rows]
                      + [(under, "travel", False, False, "S"), (over_bare, "travel", False, False, "S")])]]}
    got = js.exposed_travel(cap)
    assert 9.0 < got < 10.0, got                    # the 0.3 mm grace off the fill's last point


def test_long_joins_count_needle_down_stitches_between_runs_only():
    st = [{"type": "stitch", "x": 0, "y": 0}, {"type": "stitch", "x": 30, "y": 0},      # run 0, 3 mm
          {"type": "stitch", "x": 130, "y": 0},                                            # run 1 starts 10 mm on
          {"type": "stitch", "x": 230, "y": 0},                                            # run 1, a 10 mm stitch
          {"type": "jump", "x": 330, "y": 0}, {"type": "stitch", "x": 330, "y": 0}]        # run 2 after a jump
    design = {"stitches": st, "runs": [{"i0": 0, "i1": 1}, {"i0": 2, "i1": 3}, {"i0": 5, "i1": 5}]}
    assert js.long_joins({"design": design}) == (1, 10.0)
