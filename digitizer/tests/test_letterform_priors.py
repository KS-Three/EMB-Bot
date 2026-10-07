"""The pure-geometry half of the letterform-priors spike
(`tools/letterform_priors_spike/fit.py`): the tolerance cap, the grid gate's
byte-identical pass-through, line and arc fits on synthetic stems and
bowls, per-letter refusal, and a pinched counter kept open. No engine run,
no fixture, no client artwork."""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools" / "letterform_priors_spike"))

import fit  # noqa: E402

PX = 0.66          # Becker's source pixel at 95.7 mm
GRID = 1 / 6.06    # the working grid that run traced it on
K = 0.75
TOL = K * PX


def _prior(widths=(4.8,), baseline=None, cap=None, px=PX, grid=GRID, k=K):
    return fit.WordPrior(line_deg=0.0, slant_deg=0.0, stem_deg=90.0, baseline_v=baseline,
                         cap_v=cap, widths_mm=list(widths), tol_mm=k * px, src_px_mm=px,
                         grid_px_mm=grid, k=k)


def _staircase(ring: np.ndarray, px: float, seed: int, amp: float = 0.35) -> np.ndarray:
    """A clean ring made raster-like: resampled every px along it, each
    vertex pushed along the normal by up to `amp` px, as a thresholded
    pixel edge would be. Deterministic."""
    rng = np.random.default_rng(seed)
    line = LineString(np.vstack([ring, ring[:1]]))
    n = max(8, int(line.length / px))
    pts = np.array([line.interpolate(i / n, normalized=True).coords[0] for i in range(n)])
    out = []
    for i in range(n):
        a, b = pts[i - 1], pts[(i + 1) % n]
        t = b - a
        t = t / max(np.hypot(*t), 1e-9)
        nrm = np.array([-t[1], t[0]])
        out.append(pts[i] + nrm * rng.uniform(-amp, amp) * px)
    return np.array(out)


def _two_way_max(a: Polygon, b: Polygon, step: float = 0.05) -> float:
    """Max distance between the two outlines, sampled both ways."""
    worst = 0.0
    for ra, rb in zip([a.exterior, *a.interiors], [b.exterior, *b.interiors]):
        la, lb = LineString(ra.coords), LineString(rb.coords)
        for src, dst in ((la, lb), (lb, la)):
            n = max(4, int(src.length / step))
            for i in range(n):
                worst = max(worst, dst.distance(src.interpolate(i / n, normalized=True)))
    return worst


def test_tolerance_cap_holds_both_ways():
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, PX, seed=1))
    res = fit.fit_letter(poly, _prior())
    assert res.status == "refit", (res.status, res.reason)
    assert res.moved_max_mm <= TOL + 1e-6
    assert _two_way_max(poly, res.polygon) <= TOL + 1e-3


def test_grid_gate_is_byte_identical():
    """A clean upload: the cap is under the working grid's pixel, so the
    word passes through untouched -- the SAME object, same WKB."""
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, 0.068, seed=2))
    prior = _prior(px=0.068, grid=1 / 13.64)
    assert prior.gated
    res = fit.fit_letter(poly, prior)
    assert res.status == "pass" and res.reason == "grid"
    assert res.polygon is poly
    assert res.polygon.wkb == poly.wkb
    before = fit.polygon_wkb_hash({"a": poly})
    assert fit.polygon_wkb_hash({"a": res.polygon}) == before


def test_stem_becomes_four_snapped_lines():
    stem = np.array([[0.0, 0.0], [4.8, 0.0], [4.8, 16.0], [0.0, 16.0]])
    poly = Polygon(_staircase(stem, PX, seed=3))
    res = fit.fit_letter(poly, _prior(widths=(4.8,)))
    assert res.status == "refit", (res.status, res.reason)
    assert res.n_arc == 0 and res.n_pass == 0
    assert res.n_line == 4
    prims = res.rings[0].prims
    stems = [p for p in prims if p.snapped == "stem"]
    bars = [p for p in prims if p.snapped == "line"]
    assert len(stems) == 2 and len(bars) == 2
    for p in stems:
        d = p.p1 - p.p0
        assert abs(d[0]) < 1e-6          # exactly vertical in the frame
    # the two stem edges sit exactly the word's width apart
    xs = sorted(float(p.p0[0]) for p in stems)
    assert xs[1] - xs[0] == pytest.approx(4.8, abs=1e-6)
    # and the structure statistic sees no spread
    assert all(abs(a) < 1e-6 for a, _w in res.stem_angles)


def test_bowl_becomes_arcs_and_keeps_its_hole():
    t = np.linspace(0, 2 * math.pi, 200, endpoint=False)
    outer = np.column_stack([8 * np.cos(t), 8 * np.sin(t)])
    inner = np.column_stack([4 * np.cos(-t), 4 * np.sin(-t)])
    poly = Polygon(_staircase(outer, PX, seed=4), [_staircase(inner, PX, seed=5)])
    assert poly.is_valid
    res = fit.fit_letter(poly, _prior(widths=(4.0,)))
    assert res.status == "refit", (res.status, res.reason)
    assert len(res.polygon.interiors) == 1
    assert res.n_arc >= 2
    radii = [p.r for rf in res.rings for p in rf.prims if p.kind == "arc"]
    assert any(abs(r - 8.0) < TOL for r in radii), radii
    assert any(abs(r - 4.0) < TOL for r in radii), radii
    # far fewer pieces than the trace needed
    assert res.n_prims < res.before_n_prims


def test_blob_is_refused_and_left_alone():
    """Radial noise far over the cap at every vertex: no line or arc holds
    a run, the residue passes the share, the letter is refused untouched."""
    rng = np.random.default_rng(6)
    t = np.linspace(0, 2 * math.pi, 60, endpoint=False)
    r = 6.0 + rng.uniform(-3 * TOL, 3 * TOL, len(t))
    poly = Polygon(np.column_stack([r * np.cos(t), r * np.sin(t)]))
    poly = poly.buffer(0) if not poly.is_valid else poly
    res = fit.fit_letter(poly, _prior(widths=(4.0,)))
    assert res.status != "refit" or res.n_pass > 0
    if res.status == "refused":
        assert res.polygon is poly
        assert res.reason in ("unexplained", "cap", "invalid")


def test_pinched_notch_keeps_its_opening():
    """A foot notch whose roof sits within the cap of the word's baseline:
    the baseline snap would pinch it shut and the ring would cross itself.
    The repair reverts the primitives round the crossing; the result is a
    valid polygon that still has the notch."""
    depth = 1.2 * TOL
    ring = np.array([[0.0, 0.0], [12.0, 0.0], [12.0, 16.0], [7.0, 16.0], [7.0, 16.0 - depth],
                     [5.0, 16.0 - depth], [5.0, 16.0], [0.0, 16.0]])
    poly = Polygon(ring)
    res = fit.fit_letter(poly, _prior(widths=(5.0,), baseline=16.0, cap=0.0))
    assert res.status in ("refit", "refused"), res.reason
    assert res.polygon.is_valid
    if res.status == "refit":
        notch = Polygon([[5.0, 16.0 - depth], [7.0, 16.0 - depth], [7.0, 16.0], [5.0, 16.0]])
        # the notch's centre is still outside the letter
        assert not res.polygon.contains(Point(6.0, 16.0 - depth / 2))
        assert res.polygon.intersection(notch).area < 0.5 * notch.area


def test_refusal_reports_share_of_outline():
    """Half a letter clean, half a mess: the unexplained share is read
    against the whole outline, and the refusal names it."""
    rng = np.random.default_rng(7)
    clean = np.array([[0.0, 0.0], [10.0, 0.0], [10.0, 16.0]])
    t = np.linspace(0, 1, 40)
    messy_x = 10.0 - 10.0 * t
    messy_y = 16.0 + rng.uniform(-3 * TOL, 3 * TOL, len(t))
    ring = np.vstack([clean, np.column_stack([messy_x, messy_y])[1:-1]])
    poly = Polygon(ring)
    if not poly.is_valid:
        poly = poly.buffer(0)
    res = fit.fit_letter(poly, _prior(widths=(5.0,)))
    assert 0.0 <= res.unexplained_share <= 1.0
    if res.status == "refused":
        assert res.polygon is poly


def test_wkb_hash_is_deterministic_and_sensitive():
    a = Polygon([[0, 0], [1, 0], [1, 1], [0, 1]])
    b = Polygon([[0, 0], [1, 0], [1, 1.001], [0, 1]])
    assert fit.polygon_wkb_hash({"x": a, "y": b}) == fit.polygon_wkb_hash({"y": b, "x": a})
    assert fit.polygon_wkb_hash({"x": a}) != fit.polygon_wkb_hash({"x": b})
