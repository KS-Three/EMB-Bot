"""`cfg.extra["counter_fan_satin"]` (2026-11-14, built OFF): a small three-sided
counter sews as ONE fanned satin, the pro's way (`stage6_counter_fan`).

Kent's MFab pin "random stitch in the middle", and "I want it exactly like the
pros". The pro's file sews the A's white counter as an underlay zigzag plus a
run into the tip, then one satin base to tip whose crosses turn 3 -> 40 ->
80-90 deg, 5.73 mm down to 1.5 mm. Ours sewed it as a fill. The fan is a
lagging-pivot sweep, held to `machine.SATIN_MAX_WIDTH_MM` (gate 1): at
MFab's own 104.9 mm the base cross is 5.37 mm and it refuses.
"""
from __future__ import annotations

import inspect
import math

import numpy as np
from shapely.geometry import Point, Polygon, box

from digitizer_core import machine, stitches
from digitizer_core import stage7_sequence as s7
from digitizer_core.stage6_counter_fan import counter_fan_runs, fan_crosses, wedge

#: an MFab-like counter: base 4.5 mm, a narrow arm up the right side to the tip
WEDGE = Polygon([(0, 0), (4.5, 0), (4.5, 6.5)])


def _deg(p, q):
    d = q - p
    return math.degrees(math.atan2(abs(d[1]), abs(d[0])))


def test_wedge_reads_tip_and_rails():
    tip, outer, inner, base_o, base_i = wedge(WEDGE)
    assert tip == (4.5, 6.5)                                # the sharpest corner
    assert {base_o, base_i} == {(0.0, 0.0), (4.5, 0.0)}
    assert outer.length > inner.length                      # outer = the longer side


def test_crosses_turn_base_to_tip_and_shorten():
    cr = fan_crosses(WEDGE, machine.SATIN_SPACING_MM, machine.SATIN_MAX_WIDTH_MM)
    ang = [_deg(p, q) for p, q in cr]
    lens = [float(np.linalg.norm(q - p)) for p, q in cr]
    assert ang[0] < 3.0 and ang[-1] > 80.0                  # the base edge -> along the arm
    assert all(b >= a - 1e-6 for a, b in zip(ang, ang[1:]))  # they TURN, one way
    assert lens[0] == max(lens) and lens[-1] < 2.0          # long at the base, short at the tip
    assert max(lens) <= machine.SATIN_MAX_WIDTH_MM


def test_rails_walk_the_real_ring_not_the_simplified_one():
    """A traced edge bowing out under the corner read's simplify tolerance:
    rails on the simplified ring left that bulge bare and the coverage guard
    refused (MFab's counter at 90 mm, 0.86 covered); on the real ring the
    sweep reaches it."""
    a, b = np.array([0.0, 0.0]), np.array([4.5, 6.5])
    nrm = np.array([-6.5, 4.5]) / math.hypot(6.5, 4.5)        # outward of the hypotenuse
    bow = [tuple(b + (a - b) * t + nrm * 0.35 * 4 * t * (1 - t)) for t in np.linspace(0, 1, 25)[1:-1]]
    bowed = Polygon([(0, 0), (4.5, 0), (4.5, 6.5)] + bow)
    assert bowed.area > WEDGE.area * 1.1
    runs, rep = counter_fan_runs(bowed, "S1")
    assert rep["counter_fan_longest_mm"] <= machine.SATIN_MAX_WIDTH_MM


def test_runs_are_underlay_then_one_satin():
    runs, rep = counter_fan_runs(WEDGE, "S1", pull_mm=0.3)
    assert [r.kind for r in runs] == [stitches.UNDERLAY, stitches.SATIN]
    assert all(r.shape_id == "S1" for r in runs)
    assert rep["counter_fan"] == 1 and rep["jumps"] == 0
    # satin alternates ends, so its stitch count is two per cross
    assert len(runs[1].points) == 2 * rep["counter_fan_crosses"]
    # pull pushes each end out along its cross by exactly pull_mm
    a, b = np.array(runs[1].points[0]), np.array(runs[1].points[1])
    assert abs(float(np.linalg.norm(b - a)) - (4.5 + 0.6)) < 1e-6


def test_the_ceiling_is_the_machine_constant(monkeypatch):
    """The ceiling is a parameter that READS `machine.SATIN_MAX_WIDTH_MM`;
    the constant itself is gate 1 and is not touched here."""
    big = Polygon([(0, 0), (6, 0), (6, 8)])                 # a 6 mm base: over 5.0
    assert counter_fan_runs(big, "S1") is None
    assert counter_fan_runs(big, "S1", max_cross_mm=6.5) is not None
    monkeypatch.setattr(machine, "SATIN_MAX_WIDTH_MM", 6.5)
    assert counter_fan_runs(big, "S1") is not None          # read at call time


def test_refuses_what_is_not_a_three_sided_counter():
    for g in (box(0, 0, 4, 4),                                   # four corners
              Point(0, 0).buffer(2.5),                           # none
              box(0, 0, 4, 4).difference(box(1, 1, 4, 3)),       # a C: not solid
              Polygon([(0, 0), (0.5, 0), (0.5, 0.8)])):          # a speck under the fill floor
        assert counter_fan_runs(g, "S1") is None


def test_hook_is_behind_the_flag_and_auto_only():
    src = inspect.getsource(s7)
    assert 'get("counter_fan_satin")' in src
    assert src.count("counter_fan_runs(") == 1
    # the shape's own tier, not the white-field rung's forced "fill"
    assert 'if (counter_fan and own_tier == "auto" and p.region.meta.get("enclosed_background")' in src
