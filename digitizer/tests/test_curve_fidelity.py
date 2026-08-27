"""The n-gon ladder, as a test rather than a number in a docstring.

`tools/edge_smoothness.py` records a turning-concentration measure that was
built and cut because it is not monotonic on a rasterised mask. The claim this
file defends is that the SAME measure, read off path geometry, IS monotonic —
so the table in `curve_fidelity.py`'s docstring cannot quietly stop being true.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.curve_fidelity import (  # noqa: E402
    CORNER_DEG, MIN_TOTAL_TURN_DEG, gini, measure, traces, turns,
)

R_MM = 10.0          # the 20 mm circle the rejected table used
# 3.0 mm is deliberately absent: a 20-gon this size has 3.13 mm edges, so
# sampling every 3.0 mm hides the polygon entirely. That floor is asserted on
# its own in `test_the_measure_goes_dead_when_stitch_length_meets_edge_length`.
STEPS = (0.5, 1.0, 2.0)


# ---------------------------------------------------------------- fixtures

def ngon(n: int | None, r: float = R_MM, dense: int = 2048) -> np.ndarray:
    a = np.linspace(0, 2 * math.pi, dense if n is None else n, endpoint=False)
    return np.c_[r * np.cos(a), r * np.sin(a)]


def resample(poly: np.ndarray, step: float) -> np.ndarray:
    """Lay a vertex every `step` mm along the closed polyline — straight
    chords between needle positions, which is what the machine sews."""
    P = np.vstack([poly, poly[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    out = []
    for ti in np.arange(0, s[-1], step):
        i = min(np.searchsorted(s, ti, side="right") - 1, len(seg) - 1)
        f = (ti - s[i]) / seg[i] if seg[i] > 0 else 0.0
        out.append(P[i] + f * (P[i + 1] - P[i]))
    return np.array(out)


def rounded_rect(w=24.0, h=16.0, r=4.0, dense=256) -> np.ndarray:
    """Flat sides, exact quarter-circle corners — legitimately smooth."""
    pts = []
    for cx, cy, a0 in ((w / 2 - r, h / 2 - r, 0.0),
                       (-(w / 2 - r), h / 2 - r, math.pi / 2),
                       (-(w / 2 - r), -(h / 2 - r), math.pi),
                       (w / 2 - r, -(h / 2 - r), 3 * math.pi / 2)):
        for a in np.linspace(a0, a0 + math.pi / 2, dense // 4):
            pts.append([cx + r * math.cos(a), cy + r * math.sin(a)])
    return np.array(pts)


def square(side=20.0) -> np.ndarray:
    h = side / 2
    return np.array([[-h, -h], [h, -h], [h, h], [-h, h]], float)


def stat(poly: np.ndarray, key: str) -> float:
    return measure([poly])[key]


# ---------------------------------------------------------------- the ladder

@pytest.mark.parametrize("step", STEPS)
def test_turn_gini_is_monotonic_in_polygon_coarseness(step):
    """circle <= 60-gon <= 40-gon <= 20-gon <= 12-gon, at every sampling step.

    This is the exact comparison the raster version failed — there the circle
    read MORE angular than a 40-gon at all four steps.
    """
    vals = [stat(resample(ngon(n), step), "turn_gini")
            for n in (None, 60, 40, 20, 12)]
    assert all(vals[i] <= vals[i + 1] + 1e-9 for i in range(len(vals) - 1)), \
        f"not monotonic at step {step} mm: {vals}"


@pytest.mark.parametrize("step", STEPS)
def test_a_circle_reads_as_smooth(step):
    """The single number the raster got backwards."""
    assert stat(resample(ngon(None), step), "turn_gini") < 0.05


@pytest.mark.parametrize("step,floor", [(0.5, 0.70), (1.0, 0.50)])
def test_a_coarse_polygon_reads_as_polygonal(step, floor):
    assert stat(resample(ngon(20), step), "turn_gini") > floor


def test_the_measure_goes_dead_when_stitch_length_meets_edge_length():
    """The instrument's physical floor, asserted so it cannot be quoted past.

    A 20 mm 20-gon has 3.13 mm edges. Sampled every 3.0 mm it lands about one
    vertex per edge, every vertex turns alike, and the polygon is invisible —
    the 20-gon reads BELOW the 60-gon. Nothing is wrong with the code; the
    needle is simply as coarse as the polygon. Arms must therefore be compared
    at one stitch length.
    """
    vals = {n: stat(resample(ngon(n), 3.0), "turn_gini")
            for n in (None, 60, 40, 20)}
    assert vals[20] < vals[60], "expected the ladder to collapse at 3.0 mm"
    assert all(v < 0.01 for v in vals.values()), vals
    # The 12-gon's 5.18 mm edges still clear a 3.0 mm needle, so it survives.
    assert stat(resample(ngon(12), 3.0), "turn_gini") > 0.20


# ------------------------------------------------- corners are not roughness

def test_a_square_refuses_instead_of_reading_as_rough():
    """Four 90 deg corners are intentional. Excluding them is the whole point
    of CORNER_DEG — without it a square tops the ranking. With it, a square has
    no curved vertex left, and saying so beats returning a number."""
    m = measure([resample(square(), 0.5)])
    assert m["refusal"] is not None
    assert m["roughness_deg"] != m["roughness_deg"]          # NaN, not 0.0


def test_a_square_reports_its_corners():
    """Three, not four: `turns` reads an OPEN polyline, so the vertex the
    resampler starts on has no incoming chord and cannot be a corner."""
    assert measure([resample(square(), 0.5)])["corner_vertices"] == 3


def test_roughness_separates_a_smooth_rounded_rect_from_a_polygon():
    """The false positive that rules `turn_gini` out as a lone instrument:
    a rounded rectangle reads ~0.65 gini, about what a 20-gon reads."""
    rr = resample(rounded_rect(), 0.5)
    assert stat(rr, "turn_gini") > 0.5                      # gini IS fooled
    assert stat(rr, "roughness_deg") < 1.0                  # roughness is not
    assert stat(resample(ngon(20), 0.5), "roughness_deg") > 4.0


# ------------------------------------------------------------- the refusals

def test_a_straight_line_refuses_rather_than_scoring_noise():
    line = np.c_[np.linspace(0, 40, 200), np.zeros(200)]
    m = measure([line])
    assert m["refusal"] is not None
    assert m["turn_gini"] != m["turn_gini"]                  # NaN, not 0.0

def test_too_few_vertices_refuses():
    m = measure([np.c_[np.linspace(0, 3, 4), np.zeros(4)]])
    assert m["refusal"] is not None


# ------------------------------------------------------------ the primitives

def test_turns_are_measured_on_an_open_polyline():
    """A satin rail has two free ends; wrapping it would invent a chord."""
    assert turns(resample(ngon(None), 1.0)).size == len(resample(ngon(None), 1.0)) - 2


def test_gini_of_an_even_spread_is_zero():
    assert gini(np.ones(50)) == pytest.approx(0.0, abs=1e-12)


def test_gini_of_a_single_spike_approaches_one():
    x = np.zeros(50)
    x[0] = 1.0
    assert gini(x) > 0.95


def test_gini_of_nothing_is_zero_not_a_crash():
    assert gini(np.array([])) == 0.0


# --------------------------------------------------- what the plan feeds in

def test_traces_splits_a_satin_zigzag_into_two_rails():
    """A satin run alternates across the column, so the raw sequence turns
    ~180 deg per vertex. Each rail alone traces the artwork edge."""
    from digitizer_core import stitches

    n = 40
    xs = np.repeat(np.linspace(0, 20, n), 2)
    ys = np.tile([0.0, 2.0], n)
    run = stitches.StitchRun(points=list(zip(xs, ys)), kind=stitches.SATIN)
    plan = stitches.StitchPlan(
        blocks=[stitches.StitchBlock(thread_index=0, thread_number="0",
                                     rgb=(0, 0, 0), runs=[run])],
        palette=[{}])
    got = traces(plan)
    assert len(got) == 2, "expected two rails"
    for _k, _s, p in got:
        assert np.allclose(p[:, 1], p[0, 1]), "a rail should not zigzag"


def test_fill_and_travel_are_not_measured():
    """Tatami row reversal is not artwork shape, and Kent cannot see underlay."""
    from digitizer_core import stitches

    pts = [(float(i), float(i % 2)) for i in range(40)]
    blocks = [stitches.StitchBlock(
        thread_index=0, thread_number="0", rgb=(0, 0, 0),
        runs=[stitches.StitchRun(points=pts, kind=k)
              for k in (stitches.FILL, stitches.TRAVEL,
                        stitches.UNDERLAY, stitches.TIE)])]
    assert traces(stitches.StitchPlan(blocks=blocks, palette=[{}])) == []
