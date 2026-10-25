"""The hairline tier (`cfg.hairline`, default OFF, 2026-10-12).

A stroke at or under 1.5 laid thread widths sews as ONE run along its
skeleton (`stage6_hairline`), not as today's three-pass bean on its outline.
Every number here is a property of the file, not of a sew-out (ROADMAP gate
1); docs/hairline-prototype-2026-10-12.md carries the card that would test
them on cloth.
"""
from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import plan_stitches, run_stages
from digitizer_core.stage6_border import run_outline
from digitizer_core.stage6_hairline import hairline_runs, measure, stitch_path

SYN = Path(__file__).resolve().parent.parent / "testdata" / "synthetic"
P40 = machine.thread_profile(40)
P60 = machine.thread_profile(60)


def _s_curve(n=200):
    t = np.linspace(0, 1, n)
    return LineString(np.column_stack([30 * t, 3 * np.sin(2 * math.pi * t)]))


def _sew(poly, prof=P40, entry=None):
    return hairline_runs(poly, "S1", max_width_mm=prof.hairline_max_width_mm,
                         run_width_mm=prof.hairline_run_width_mm,
                         stitch_mm=1.5, entry=entry, trim_at_mm=machine.TRIM_AT_MM)


def _steps(runs):
    return [math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:])]


def _length(runs):
    return sum(_steps(runs))


def test_a_single_strand_is_one_pass_down_its_middle():
    line = _s_curve()
    poly = line.buffer(0.15)                  # a 0.3 mm strand
    runs, rep = _sew(poly)
    assert rep["admitted"] and not rep["empty"]
    assert len(runs) == 1 and rep["strands"] == 1
    # One pass: the thread laid is the strand's own length, not two or three.
    assert _length(runs) == pytest.approx(line.length, rel=0.06)
    # Down the middle: every needle point within a thread width of the spine.
    for x, y in runs[0].points:
        assert line.distance(Point(x, y)) < P40.width_mm
    assert all(r.kind == "run" for r in runs)


def test_no_hairline_stitch_is_under_the_needle_floor():
    runs, _ = _sew(_s_curve().buffer(0.2))
    steps = _steps(runs)
    assert min(steps) >= machine.MIN_STITCH_MM - 1e-9
    assert np.median(steps) == pytest.approx(1.5, abs=0.25)


def test_a_curl_under_two_millimetres_holds_the_floor():
    a = np.linspace(0, 2.6 * math.pi, 300)
    r = 1.6 * (1 - 0.25 * np.linspace(0, 1, 300))
    curl = LineString(np.column_stack([r * np.cos(a), r * np.sin(a)]))
    runs, rep = _sew(curl.buffer(0.17))
    assert not rep["empty"]
    assert min(_steps(runs)) >= machine.MIN_STITCH_MM - 1e-9


def test_stitch_path_shortens_on_a_bend_but_never_under_the_floor():
    # A tight hairpin: the chord rule halves the 1.5 mm stitches round the
    # bend, the floor stops it at 1.0.
    a = np.linspace(0, math.pi, 100)
    pts = ([(x, 1.2) for x in np.linspace(-10, 0, 20)]
           + [(1.2 * math.sin(t), 1.2 * math.cos(t)) for t in a]
           + [(x, -1.2) for x in np.linspace(0, -10, 20)])
    out = stitch_path(pts, 1.5, 0.2)
    steps = [math.dist(p, q) for p, q in zip(out, out[1:])]
    assert min(steps) >= 1.0 - 1e-9
    assert min(steps) < 1.4            # it DID shorten somewhere


def test_a_crossing_is_followed_straight_through():
    a = LineString([(0, 0), (20, 20)])
    b = LineString([(0, 20), (20, 0)])
    runs, rep = _sew(unary_union([a.buffer(0.15), b.buffer(0.15)]))
    assert not rep["empty"]
    # Two strands, each sewn once: no edge twice, nothing left out.
    assert _length(runs) == pytest.approx(a.length + b.length, rel=0.08)
    assert rep["strands"] == 2
    for r in runs:
        # Each pass is one straight strand, not an L turned at the crossing.
        p0, p1 = r.points[0], r.points[-1]
        assert math.dist(p0, p1) == pytest.approx(a.length, rel=0.08)


def test_a_wide_stroke_is_not_a_hairline():
    runs, rep = _sew(_s_curve().buffer(0.5))          # 1.0 mm
    assert runs == [] and rep["empty"] and not rep["admitted"]


def test_the_gate_follows_the_thread_weight():
    poly = _s_curve().buffer(0.275)                   # a 0.55 mm stroke
    assert measure(poly, P40.hairline_max_width_mm)["admit"]       # <= 0.60
    assert not measure(poly, P60.hairline_max_width_mm)["admit"]   # >  0.48


def test_a_strand_under_the_loop_floor_is_dropped_and_counted():
    runs, rep = _sew(LineString([(0, 0), (1.6, 0)]).buffer(0.15))
    assert runs == [] and rep["empty"] and rep["admitted"]
    assert rep["dropped"] == 1


def test_against_todays_run_tier_on_one_strand():
    """Today a sub-floor stroke sews as a bean on its OUTLINE: three passes
    round a ring twice the strand's length, at 0.73 mm stations. The
    hairline tier lays one pass at 1.5 mm. The ratio is pinned loosely —
    the claim is "at most a third of the thread", which is the point."""
    poly = _s_curve().buffer(0.15)
    hair, _ = _sew(poly)
    bean, rep = run_outline(poly, "S1", entry=None, trim_at_mm=machine.TRIM_AT_MM)
    assert not rep["empty"]
    n_hair = sum(len(r.points) for r in hair)
    n_bean = sum(len(r.points) for r in bean)
    assert _length(hair) / _length(bean) < 1 / 3
    assert n_hair / n_bean < 1 / 3


def test_off_is_the_default_and_on_routes_the_script_through_the_tier():
    cfg = dict(target_width_mm=60.0, forced_class="flat")
    result = run_stages(SYN / "thin_script.png", PipelineConfig(**cfg))
    off = plan_stitches(result, PipelineConfig(**cfg))
    on = plan_stitches(result, PipelineConfig(**cfg, hairline=True))
    assert not any(w["code"] == "HAIRLINE_TIER_SEWN" for w in off.warnings)
    w = next(w for w in on.warnings if w["code"] == "HAIRLINE_TIER_SEWN")
    assert w["shapes"] >= 1 and w["strands"] >= w["shapes"]

    def dark_len(plan):
        return sum(math.dist(a, b) for _, r in plan.iter_runs()
                   for a, b in zip(r.points, r.points[1:]))
    # One pass where the bean laid six (three round a two-sided ring).
    assert dark_len(on) < dark_len(off) / 3
    # No hairline-tier stitch under the needle floor; the only shorter ones
    # are the existing lock rule's 0.8 mm legs at trims.
    for _, r in on.iter_runs():
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            if 0.01 < d < machine.MIN_STITCH_MM:
                assert d == pytest.approx(machine.TIE_STITCH_MM, abs=1e-6)
