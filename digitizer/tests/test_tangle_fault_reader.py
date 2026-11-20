"""tools.tangle_fault_reader on synthetic stitches, and its pin rule."""
import math

import numpy as np

from tools import fault_reader_harness as h
from tools import tangle_fault_reader as t


def _st(x, y):
    return {"type": "stitch", "x": x, "y": y}


def _satin(x0, x1, y0, y1, step=4):
    """A vertical-stitch column: zig-zag between y0 and y1 (design units)."""
    out, up = [], True
    for x in range(x0, x1 + 1, step):
        out.append(_st(x, y1 if up else y0))
        up = not up
    return out


def _star(cx, cy, r=25, n=12):
    """Stitches back and forth through one point in n directions: a pile-up."""
    out = []
    for k in range(n):
        a = math.pi * k / n
        out += [_st(cx + r * math.cos(a), cy + r * math.sin(a)),
                _st(cx - r * math.cos(a), cy - r * math.sin(a)), {"type": "trim"}]
    return out


def test_one_direction_reads_one():
    hist = np.zeros((t.NBINS, 1))
    hist[3, 0] = 1.0
    assert abs(t.directions(hist)[0] - 1.0) < 1e-9
    two = np.zeros((t.NBINS, 1))
    two[0, 0] = two[9, 0] = 0.5
    assert 1.9 < t.directions(two)[0] < 2.1
    flat = np.full((t.NBINS, 1), 1.0 / t.NBINS)
    assert t.directions(flat)[0] > 3.5


def test_axial_bin_folds_direction():
    assert t.axial_bin(1, 0) == t.axial_bin(-1, 0) == 0
    assert t.axial_bin(0, 1) == t.axial_bin(0, -1) == 9


def test_segments_break_on_trim_and_skip_short():
    s = [_st(0, 0), _st(10, 0), _st(11, 0), {"type": "trim"}, _st(50, 0), _st(60, 0)]
    assert t.segments(s) == [(0.0, 0.0, 10.0, 0.0), (50.0, 0.0, 60.0, 0.0)]


def test_clean_satin_has_no_flag_and_a_pile_up_does():
    clean = {"stitches": _satin(0, 300, 0, 60)}
    res = t.read_design(clean)
    assert res["flags"] == []
    assert res["candidates"]
    piled = {"stitches": _satin(0, 300, 0, 60) + [{"type": "trim"}] + _star(150, 30)}
    res = t.read_design(piled)
    assert res["flags"], "a twelve-way pile-up must flag"
    f = max(res["flags"], key=lambda f: f["strength"])
    # design (150, 30) -> mm from the box's top-left, y down: x 15, y 3; within the star (2.5 mm)
    assert math.hypot(f["x_mm"] - 15.0, f["y_mm"] - 3.0) <= 2.5
    assert f["strength"] >= t.FLAG_D


def test_spread_keeps_strongest_apart():
    P = np.array([[0, 0], [5, 0], [30, 0]], float)
    S = np.array([1.0, 2.0, 0.5])
    assert t.spread(P, S, 10.0) == [1, 2]


def test_tangle_pin_rule():
    assert h.tangle_reason({"what": "stray", "note": "Random Cross over stitch shouldn't be here"})
    assert h.tangle_reason({"what": "pen_flow", "note": ""}) == "bare flow kind"
    assert h.tangle_reason({"what": "jagged", "note": "fanned stitch ends"}) is None   # the edge reader's
    assert h.tangle_reason({"what": "mushed", "note": "the crossbar is a lump"}) is None
    card = {"readings": {"L_x": {"faults": [{"x_mm": 1, "y_mm": 2, "what": "mushed", "severity": "noticeable",
                                             "note": "1: a tangle of fanned stitches | 2: pile-up"}],
                                 "one_reader": [{"x_mm": 5, "y_mm": 5, "what": "stray", "note": "pile"}]}}}
    pins = h.select_tangle_pins(h.grader_marks(card))
    assert [(p["item"], p["x_mm"]) for p in pins] == [("L_x", 1)]
