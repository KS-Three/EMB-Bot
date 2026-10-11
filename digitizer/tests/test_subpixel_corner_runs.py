"""`cfg.subpixel_corner_runs`: the native edge read's corner placement
repaired where the Becker outline reversals start, built 2026-10-11,
default OFF.

The contracts. OFF is today's pipeline byte for byte. ON, Becker at its own
1.8 px/mm loses its reversals (vertices turning back past 120 degrees)
WITHOUT the 0.68 mm source-pixel staircase coming back (right-angle turns
must not rise) — the reversal count alone is blind to a stair, which turns
90. A clean rectangle keeps the squared corners the side-line fit gives it.
And each of the three repairs does what it says on a ring small enough to
check by hand. Evidence: `docs/native-read-corners-2026-10-11.md`.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core.pipeline import build_generation
from digitizer_core.subpixel import _fit_corner_runs, _inherit_offsets, drop_folds

BECKER = Path(__file__).resolve().parents[1] / "testdata" / "becker_marine_logo.png"


def _turns(polys, lo_deg: float, hi_deg: float) -> float:
    """Vertices turning by more than `lo_deg` and at most `hi_deg`, per
    100 mm of outline (the head-to-head harness's `spikes` for 120-180,
    the gate's `right_angles` for 60-120)."""
    n, length = 0, 0.0
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            r = np.asarray(ring.coords)
            seg = np.diff(r, axis=0)
            ln = np.hypot(seg[:, 0], seg[:, 1])
            seg, ln = seg[ln > 1e-9], ln[ln > 1e-9]
            if len(seg) < 3:
                continue
            ang = np.arctan2(seg[:, 1], seg[:, 0])
            d = np.abs((np.diff(np.concatenate([ang, ang[:1]])) + np.pi) % (2 * np.pi) - np.pi)
            n += int(((d > np.radians(lo_deg)) & (d <= np.radians(hi_deg))).sum())
            length += ln.sum()
    return 100.0 * n / length if length else 0.0


def _becker(monkeypatch, **kw):
    """-> (Prep, stage 4's own polygons, every region's polygon) for Becker
    at 80 mm, its own 1.8 px/mm. Stage 4's output is what the measurements
    in the evidence doc read (bare `vectorize()`, before stage 5)."""
    bare = {}
    orig = pipeline.vectorize

    def wrap(masks, ti, p, c):
        out = orig(masks, ti, p, c)
        bare["polys"] = [r.polygon for r in out[0]]
        return out

    monkeypatch.setattr(pipeline, "vectorize", wrap)
    gen = build_generation(str(BECKER), PipelineConfig(target_width_mm=80.0, **kw))
    return gen.p, bare["polys"], [r.polygon for r in gen.regions]


def test_the_default_is_off():
    assert PipelineConfig().subpixel_corner_runs is False


def test_off_is_todays_polygon_byte_for_byte(monkeypatch):
    _p, bare, default = _becker(monkeypatch)
    _p, bare_x, explicit = _becker(monkeypatch, subpixel_corner_runs=False)
    assert [g.wkt for g in bare] == [g.wkt for g in bare_x]
    assert [g.wkt for g in default] == [g.wkt for g in explicit]


def test_becker_reversals_go_and_the_staircase_stays_gone(monkeypatch):
    p, today, _ = _becker(monkeypatch)
    assert p.upscale[0] > 1.0 and p.input_px_per_mm == pytest.approx(1.81, abs=0.01)
    _p, fixed, _ = _becker(monkeypatch, subpixel_corner_runs=True)
    rev_today, rev_fixed = _turns(today, 120, 180), _turns(fixed, 120, 180)
    assert rev_today >= 5.0                      # the defect is there to fix (7.1 measured)
    assert rev_fixed < 1.0                       # 0.92 measured
    assert _turns(fixed, 60, 120) <= _turns(today, 60, 120)     # 26.5 -> 20.1 measured


def _rect_cutout(tmp_path: Path) -> Path:
    """One ink, a 60 x 36 px rectangle in alpha whose edges sit mid-pixel."""
    s, w = 16, 100
    canvas = np.zeros((w * s, w * s), np.uint8)
    canvas[int(20.5 * s):int(56.5 * s), int(20.5 * s):int(80.5 * s)] = 255
    img = np.zeros((w, w, 4), np.uint8)
    img[..., 3] = cv2.resize(canvas, (w, w), interpolation=cv2.INTER_AREA)
    path = tmp_path / "rect.png"
    cv2.imwrite(str(path), img)
    return path


@pytest.mark.parametrize("ppm", [1.8, 5.0])
def test_a_clean_rectangle_comes_out_a_clean_quadrilateral(tmp_path, ppm):
    """Square corners, no hook at any of them, the same size as today's.
    (Today's at 1.8 px/mm carries a fold at every corner, 16 vertices;
    measured 2026-10-11.)"""
    art = _rect_cutout(tmp_path)
    width = float(np.floor(60.0 / ppm * 10.0) / 10.0)
    on = build_generation(str(art), PipelineConfig(target_width_mm=width))
    fixed = build_generation(str(art), PipelineConfig(target_width_mm=width, subpixel_corner_runs=True))
    assert on.p.upscale[0] > 1.0
    a = [r.polygon for r in on.regions if not r.meta.get("enclosed_background")]
    b = [r.polygon for r in fixed.regions if not r.meta.get("enclosed_background")]
    assert len(a) == len(b) == 1
    assert len(b[0].exterior.coords) - 1 <= 5
    assert _turns(b, 120, 180) == 0.0
    assert b[0].area == pytest.approx(a[0].area, rel=0.02)


def _square_ring(side: int = 12, step: float = 0.25) -> np.ndarray:
    """A closed square of pixel centres, `step` apart, clockwise in image
    coordinates (y down)."""
    t = np.arange(0.0, side, step)
    top = np.stack([t, np.zeros_like(t)], 1)
    right = np.stack([np.full_like(t, side), t], 1)
    bottom = np.stack([side - t, np.full_like(t, side)], 1)
    left = np.stack([np.zeros_like(t), side - t], 1)
    return np.vstack([top, right, bottom, left])


def test_one_meet_per_corner_run():
    """Every vertex of a run lands on ONE meet, the side lines' corner."""
    raw = _square_ring()
    n = len(raw)
    pts = raw.copy()
    # the read put every side vertex half a pixel out: top up, right right...
    side = np.repeat(np.arange(4), n // 4)
    out = np.array([[0, -1], [1, 0], [0, 1], [-1, 0]], float)[side]
    pts = pts + 0.5 * out
    corner = np.zeros(n, bool)
    k = n // 4
    for c in range(4):                      # five flagged vertices round each corner
        corner[[(c * k + d) % n for d in range(-2, 3)]] = True
    accepted = ~corner
    protect = corner.copy()
    _fit_corner_runs(raw, pts, accepted, protect, corner, steps=8)
    run = [(k + d) % n for d in range(-2, 3)]             # the top-right corner
    assert np.allclose(pts[run], [12.5, -0.5])
    assert accepted[corner].all() and not protect.any()


def test_a_meet_behind_its_side_is_refused():
    """A run whose two fitted sides meet BEHIND the nearest side point (it
    would fold the ring) keeps what the profile gave it."""
    raw = _square_ring()
    n = len(raw)
    k = n // 4
    pts = raw.copy()
    corner = np.zeros(n, bool)
    run = [(k + d) % n for d in range(-12, 13)]          # a run 3 px either side
    corner[run] = True
    # pull the next side's read vertices back so the meet sits behind it
    nxt = [(k + d) % n for d in range(13, 40)]
    pts[nxt, 0] -= 4.0
    before = pts[run].copy()
    accepted = ~corner
    protect = corner.copy()
    _fit_corner_runs(raw, pts, accepted, protect, corner, steps=8)
    assert np.array_equal(pts[run], before)
    assert protect[run].all()


def test_an_unread_vertex_takes_its_read_neighbours_offset():
    raw = np.stack([np.arange(40.0), np.zeros(40)], 1)
    normal = np.tile([0.0, -1.0], (40, 1))
    pts = raw + 0.5 * normal
    accepted = np.ones(40, bool)
    accepted[20] = False
    pts[20] = raw[20]                                     # left at its pixel centre
    ok = np.ones(40, bool)
    _inherit_offsets(raw, pts, accepted, accepted.copy(), normal, ok, reach=6)
    assert np.allclose(pts[20], [20.0, -0.5])
    assert not accepted[20]


def test_an_unread_vertex_with_a_read_on_one_side_only_stays():
    raw = np.stack([np.arange(40.0), np.zeros(40)], 1)
    normal = np.tile([0.0, -1.0], (40, 1))
    pts = raw + 0.5 * normal
    accepted = np.ones(40, bool)
    accepted[10:35] = False                               # a long unreadable stretch
    pts[10:35] = raw[10:35]
    ok = np.ones(40, bool)
    _inherit_offsets(raw, pts, accepted, accepted.copy(), normal, ok, reach=6)
    assert np.array_equal(pts[20], raw[20])               # 10 steps from either read


def test_a_vertex_that_lands_behind_its_predecessor_is_dropped():
    raw = _square_ring()
    pts = raw.copy()
    pts[10, 0] -= 1.0                                     # read back past vertices 7-9
    accepted = np.ones(len(raw), bool)
    protect = np.zeros(len(raw), bool)
    p2, a2, c2 = drop_folds(pts, accepted, protect, raw, steps=2)
    assert np.array_equal(p2, np.delete(pts, 10, axis=0))
    assert len(a2) == len(c2) == len(p2)
    assert Polygon(p2).is_valid
    p3, _a3, _c3 = drop_folds(raw.copy(), accepted, protect, raw, steps=2)
    assert np.array_equal(p3, raw)                        # nothing folds, nothing goes
