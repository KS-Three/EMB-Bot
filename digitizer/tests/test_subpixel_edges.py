"""`cfg.subpixel_edges` — sub-pixel, anti-alias-aware contour vertices
(`digitizer_core/subpixel.py`, plan `2026-09-08-subpixel-edges.md` §3, PR 2)
and the curve refinement keyed to their acceptance (`stage4_vectorize.
_refine_curves`, §3 step 5, PR 3).

The contracts. On an anti-aliased disc the moved vertices sit on the
circle to a fraction of a pixel where the pixel-centre trace carried the
staircase and the half-pixel inward bias; on a hard edge the vertex lands
on the pixel boundary; a two-pixel stroke (no plateau) and a ringing edge
(no monotonic profile) keep every pixel centre; OFF, the step never runs
(the goldens pin the bytes); ON, the near-floor lettering exemption holds
per ring; and on the ladder's 400 px rung the circle and ring sharpen and
lose their inward bias — the plan's §5 criterion for PR 2 alone, which
predicts the 200/400 rungs move and the ribbon does not.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig, digitize
from digitizer_core import stage4_vectorize as s4
from digitizer_core.subpixel import ACCEPT_WINDOW_PX, drop_isolated_rejects, subpixel_contour
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

import edge_truth_ladder as el  # noqa: E402

S = 4                      # the fixture generator's supersample
FG = (30, 30, 200)         # BGR
BG = (255, 255, 255)
CONTRAST = PipelineConfig().merge_delta_e


def _lab(bgr: np.ndarray) -> np.ndarray:
    rgb = np.ascontiguousarray(bgr[..., ::-1])
    return rgb_to_lab(rgb.reshape(-1, 3)).reshape(bgr.shape).astype(np.float32)


def _mask(bgr: np.ndarray, fg=FG, bg=BG) -> np.ndarray:
    d_fg = np.linalg.norm(bgr.astype(float) - np.array(fg, float), axis=-1)
    d_bg = np.linalg.norm(bgr.astype(float) - np.array(bg, float), axis=-1)
    return d_fg < d_bg


def _trace(mask: np.ndarray) -> np.ndarray:
    contours, _h = cv2.findContours(mask.astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    return max(contours, key=cv2.contourArea).reshape(-1, 2)


def _disc(w=300, h=300, c=150, r=100, s=S) -> tuple[np.ndarray, float, float]:
    """A disc drawn at `s`x and downscaled with INTER_AREA, the generator's
    recipe -> (image, true centre, true radius) in the downscaled frame's
    pixel-centre coordinates: the sub-pixel at index j sits at
    (j - (s - 1) / 2) / s, and cv2 fills the sub-pixels within r + 0.5."""
    canvas = np.full((h * s, w * s, 3), BG, np.uint8)
    cv2.circle(canvas, (c * s, c * s), r * s, FG, -1)
    img = cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)
    return img, c - (s - 1) / 2.0 / s, r + 0.5 / s


def _fit_circle(pts: np.ndarray) -> tuple[float, float, float]:
    x, y = pts[:, 0], pts[:, 1]
    a = np.column_stack([2 * x, 2 * y, np.ones(len(x))])
    cx, cy, c = np.linalg.lstsq(a, x ** 2 + y ** 2, rcond=None)[0]
    return float(cx), float(cy), float(np.sqrt(c + cx ** 2 + cy ** 2))


def _radial_rms(pts: np.ndarray, cx: float, cy: float, r: float) -> float:
    return float(np.sqrt(np.mean((np.hypot(pts[:, 0] - cx, pts[:, 1] - cy) - r) ** 2)))


@pytest.mark.parametrize("s", [S, 16])
def test_an_antialiased_disc_is_traced_to_a_fraction_of_a_pixel(s):
    """At the generator's 4x the coverage is quantised to quarters and the
    truth itself is only known to an eighth of a pixel; at 16x the
    estimator's own scatter and bias show: 0.04 and 0.01 px (2026-09-09).
    The pixel-centre trace carries the staircase (0.26 px) and sits half a
    pixel inside the edge; the moved vertices sit on it."""
    img, c, true_r = _disc(s=s)
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    assert accepted.mean() > 0.85, accepted.mean()
    res_raw = np.hypot(raw[:, 0] - c, raw[:, 1] - c) - true_r
    res_sub = (np.hypot(pts[:, 0] - c, pts[:, 1] - c) - true_r)[accepted]
    assert res_raw.std() > 0.2 and res_raw.mean() < -0.4, (res_raw.mean(), res_raw.std())
    assert res_sub.std() < 0.08, res_sub.std()
    assert abs(res_sub.mean()) < (0.15 if s == S else 0.05), res_sub.mean()


def _straight_edge(e: float, w=120, h=60) -> np.ndarray:
    """A rectangle whose right edge sits at x = `e` (a multiple of 1/4) in
    the downscaled frame's pixel-centre coordinates, drawn at 4x and
    downscaled: the sub-pixel at index j sits at (j - 1.5) / 4 and is
    filled when it lies left of the edge."""
    canvas = np.full((h * S, w * S, 3), BG, np.uint8)
    centres = (np.arange(w * S) - 1.5) / S
    canvas[:, centres < e - 1e-9] = FG
    canvas[:8 * S] = BG
    canvas[-8 * S:] = BG
    canvas[:, :8 * S] = BG
    return cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)


@pytest.mark.parametrize("e", [60.0, 60.25, 60.5, 60.75])
def test_a_straight_antialiased_edge_is_located_to_a_twentieth_of_a_pixel(e):
    img = _straight_edge(e)
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    side = (raw[:, 1] > 15) & (raw[:, 1] < 45) & (raw[:, 0] > 40)
    assert accepted[side].all()
    assert abs(pts[side, 0].mean() - e) < 0.06, (e, pts[side, 0].mean())
    assert pts[side, 0].std() < 0.02


def test_a_hard_edge_puts_the_vertex_on_the_pixel_boundary():
    img = np.full((120, 120, 3), BG, np.uint8)
    img[30:90, 40:100] = FG                              # columns 40..99 inclusive
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    left = (raw[:, 0] == 40) & (raw[:, 1] > 35) & (raw[:, 1] < 85)
    right = (raw[:, 0] == 99) & (raw[:, 1] > 35) & (raw[:, 1] < 85)
    assert accepted[left].all() and accepted[right].all()
    assert np.allclose(pts[left, 0], 39.5, atol=0.05), pts[left, 0]
    assert np.allclose(pts[right, 0], 99.5, atol=0.05), pts[right, 0]
    assert np.allclose(pts[left | right, 1], raw[left | right, 1], atol=0.05)


def test_isolated_rejects_are_dropped_and_runs_are_kept():
    pts = np.arange(20, dtype=float).reshape(10, 2)
    acc = np.ones(10, dtype=bool)
    acc[[2, 5, 6, 9]] = False                     # runs: 1 at 2; 2 at 5-6; 1 at 9 wrapping onto 0
    out, out_acc = drop_isolated_rejects(pts, acc, max_run=1)
    assert [int(p[0] // 2) for p in out] == [0, 1, 3, 4, 5, 6, 7, 8]
    assert out_acc.tolist() == [True, True, True, True, False, False, True, True]
    out, out_acc = drop_isolated_rejects(pts, acc, max_run=2)
    assert [int(p[0] // 2) for p in out] == [0, 1, 3, 4, 7, 8]
    acc[:] = False
    out, _o = drop_isolated_rejects(pts, acc)
    assert len(out) == 10, "a ring with nothing accepted is left alone"


def test_a_two_pixel_stroke_and_a_ringing_edge_keep_the_pixel_centres():
    # No plateau between the two ramps: the crossing is undefined.
    img = np.full((60, 200, 3), BG, np.uint8)
    img[30:32, 20:180] = FG
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    assert accepted.sum() == 0, accepted.sum()
    assert np.array_equal(pts, raw.astype(float))
    # JPEG-style ringing: a bright band and a dark band hugging the edge.
    grey = (128, 128, 128)
    dark = (40, 40, 40)
    ring = np.full((300, 300, 3), grey, np.uint8)
    cv2.circle(ring, (150, 150), 102, dark, 1)
    cv2.circle(ring, (150, 150), 101, (255, 255, 255), 1)
    cv2.circle(ring, (150, 150), 100, dark, -1)
    mask = _mask(ring, fg=dark, bg=grey) & (np.hypot(*np.meshgrid(np.arange(300) - 150,
                                                                 np.arange(300) - 150)) <= 100.5)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(ring), mask, (0, 0), min_contrast_de=CONTRAST)
    assert accepted.mean() < 0.2, accepted.mean()


def test_a_vertex_never_moves_further_than_the_window():
    img, _c, _r = _disc()
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _corner = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    moved = np.hypot(*(pts - raw).T)
    assert moved[accepted].max() <= ACCEPT_WINDOW_PX + 1e-9
    assert (moved[~accepted] == 0).all()


def test_off_never_runs_the_step_and_on_records_the_accepted_share():
    art = TESTDATA / "logo_whitebg.png"
    with patch("digitizer_core.stage4_vectorize.subpixel_contour",
               side_effect=AssertionError("the step ran with the flag off")):
        off, _plan = digitize(art, PipelineConfig(target_width_mm=80.0, subpixel_edges=False))
    assert not any("subpixel_accepted" in r.meta for r in off.regions)
    on, _plan = digitize(art, PipelineConfig(target_width_mm=80.0, subpixel_edges=True))
    shares = [r.meta["subpixel_accepted"] for r in on.regions if "subpixel_accepted" in r.meta]
    assert len(shares) >= 5, shares
    assert np.median(shares) > 0.8, shares


def _two_bars(path: Path) -> None:
    """A 0.5 mm bar (within 20% of the minimum cross: exempt per ring) and a
    2 mm bar, 10 mm long, on white at 10 px/mm for a 50 mm target."""
    img = np.full((160, 540, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 20), (519, 39), (30, 30, 30), -1)           # fixes the 50 mm width
    cv2.rectangle(img, (100, 80), (199, 84), (30, 30, 30), -1)          # 100 x 5 px: 0.5 mm wide
    cv2.rectangle(img, (300, 80), (399, 99), (30, 30, 30), -1)          # 100 x 20 px: 2 mm wide
    cv2.imwrite(str(path), img)


def test_near_floor_lettering_keeps_the_pixel_centre_polygon_per_ring(tmp_path):
    art = tmp_path / "bars.png"
    _two_bars(art)
    off, _p = digitize(art, PipelineConfig(target_width_mm=50.0, subpixel_edges=False))
    on, _p = digitize(art, PipelineConfig(target_width_mm=50.0, subpixel_edges=True))

    def height(r):
        _x0, y0, _x1, y1 = r.polygon.bounds
        return y1 - y0

    def pick(result, lo, hi):
        found = [r for r in result.regions
                 if lo <= height(r) <= hi and r.polygon.bounds[2] - r.polygon.bounds[0] < 20.0]
        assert len(found) == 1, [round(height(r), 2) for r in result.regions]
        return found[0]

    # The 5 px bar traces 0.4 mm tall either way: its pixel-centre polygon
    # is kept (the ring is within 20% of the minimum cross), untouched.
    thin_off, thin_on = pick(off, 0.3, 0.7), pick(on, 0.3, 0.7)
    assert "subpixel_accepted" not in thin_on.meta
    assert list(thin_on.polygon.exterior.coords) == list(thin_off.polygon.exterior.coords)
    # The 20 px bar moves to its true 2.0 mm edges (1.9 traced OFF).
    wide_off, wide_on = pick(off, 1.5, 2.2), pick(on, 1.5, 2.2)
    assert wide_on.meta.get("subpixel_accepted", 0.0) > 0.8
    assert abs(height(wide_on) - 2.0) < 0.05 < abs(height(wide_off) - 2.0), (height(wide_off), height(wide_on))


@pytest.fixture(scope="module")
def rung_400(tmp_path_factory):
    work = tmp_path_factory.mktemp("subpixel_ladder")
    return {"off": el.measure_rung("whitebg", 400, "flat", work, flag="subpixel_edges=false"),
            "on": el.measure_rung("whitebg", 400, "flat", work, flag="subpixel_edges")}


def _dp(points: np.ndarray, eps: float) -> np.ndarray:
    return cv2.approxPolyDP(points.astype(np.float32).reshape(-1, 1, 2), eps, True).reshape(-1, 2)


def _sag(poly: np.ndarray, c: float, r: float) -> float:
    """Worst inward deviation of the polygon's edges from the circle, px."""
    worst = 0.0
    for a, b in zip(poly, np.roll(poly, -1, axis=0)):
        for t in np.linspace(0.0, 1.0, 9):
            p = a + t * (b - a)
            worst = max(worst, r - float(np.hypot(p[0] - c, p[1] - c)))
    return worst


def test_the_refinement_floor_is_a_quarter_pixel_where_the_edge_was_read():
    """PR 3. A small disc (r = 30 px, the whitebg ring's hole at 400 px),
    rendered at 16x so its sub-pixel contour is known to ~0.04 px. At a
    one-pixel tolerance Douglas-Peucker leaves chords sagging over half a
    pixel, which today's refinement cannot touch — its floor IS a pixel, and
    on a radius this small the 15 deg turn rule asks for less than that on
    every chord under ~30 px — while keyed to acceptance the quarter-pixel
    floor lets it split down to the turn rule and the sag falls under 0.4
    px. `accepted=None`, or nothing accepted, is today's refinement
    exactly. (On a 100 px radius the turn rule binds first and the floor
    cannot show — the fixture's radius is the point.)"""
    img, c, r = _disc(w=100, h=100, c=50, r=30, s=16)
    mask = _mask(img)
    raw = _trace(mask)
    pts, accepted, _protect = subpixel_contour(raw, _lab(img), mask, (0, 0), min_contrast_de=CONTRAST)
    pts, accepted = drop_isolated_rejects(pts, accepted)
    pts = pts.astype(np.float32).astype(np.float64)     # the call site's round trip: DP keeps these exact values
    eps = 1.0
    simplified = _dp(pts, eps).astype(np.float64)
    today = s4._refine_curves(pts, simplified, eps, 15.0)
    keyed = s4._refine_curves(pts, simplified, eps, 15.0, accepted=accepted)
    unkeyed = s4._refine_curves(pts, simplified, eps, 15.0, accepted=np.zeros(len(pts), bool))
    assert np.array_equal(today, unkeyed), "nothing accepted must be today's refinement"
    assert _sag(simplified, c, r) > 0.5, _sag(simplified, c, r)
    assert np.array_equal(today, simplified), "the one-pixel floor leaves these chords alone"
    assert _sag(keyed, c, r) < 0.4, (_sag(today, c, r), _sag(keyed, c, r))
    assert len(keyed) > len(today)
    # the inserted vertices are the raw sub-pixel points themselves
    inserted = [v for v in keyed if not any(np.array_equal(v, q) for q in simplified)]
    assert inserted and all(any(np.array_equal(v, q) for q in pts) for v in inserted)


def test_the_resolution_gate_lifts_only_with_the_flag_on(tmp_path):
    """Today's refinement refuses everything under 20 px/mm, and its
    one-pixel floor refuses any chord shorter than ~30 px whatever the
    resolution — so a small disc (r = 40 px, 4 px/mm) keeps its coarse
    Douglas-Peucker polygon. Keyed to acceptance the floor is a quarter
    pixel and the polygon reaches the 15 deg turn rule."""
    img, _c, _r = _disc(w=100, h=100, c=50, r=40)            # the disc IS the art: 80 px at 20 mm = 4 px/mm
    art = tmp_path / "disc.png"
    cv2.imwrite(str(art), img)
    no_turn, _p = digitize(art, PipelineConfig(target_width_mm=20.0, curve_turn_deg=0.0, subpixel_edges=False))
    off, _p = digitize(art, PipelineConfig(target_width_mm=20.0, curve_turn_deg=15.0, subpixel_edges=False))
    on, _p = digitize(art, PipelineConfig(target_width_mm=20.0, curve_turn_deg=15.0, subpixel_edges=True))
    n = lambda res: len(max(res.regions, key=lambda r: r.polygon.area).polygon.exterior.coords) - 1  # noqa: E731
    assert n(off) == n(no_turn), "under 20 px/mm the gate keeps the refinement off, flag off"
    assert n(on) >= 22 and n(on) > n(off) + 4, (n(off), n(on))


def test_on_the_400_rung_the_vertices_move_onto_the_edges(rung_400):
    """PR 2 moves the VERTICES; the polygon's remaining deviation is the
    simplifier's chord sag, which the plan's §5 assigns to PR 3 — so the
    vertex-only columns are the ones this PR is judged on. Measured
    2026-09-09 at 400 px (4.2 px/mm): the circle's vertex spread 0.048 ->
    0.013 mm, the ring's 0.03 -> 0.006; the three rectangles land on their
    true edges (Hausdorff 0.12-0.18 -> 0.01-0.02 mm) once corners are read
    along each side. The dot (1 mm, near-floor) is exempt and unmoved."""
    off = {row["shape"]: row for row in rung_400["off"]["rows"]}
    on = {row["shape"]: row for row in rung_400["on"]["rows"]}
    for name in ("circle", "ring"):
        assert on[name]["produced"] and off[name]["produced"]
        assert on[name]["vertex_spread_mm"] < off[name]["vertex_spread_mm"] / 2, (
            name, off[name]["vertex_spread_mm"], on[name]["vertex_spread_mm"])
        assert abs(on[name]["vertex_offset_mm"]) < abs(off[name]["vertex_offset_mm"]), (
            name, off[name]["vertex_offset_mm"], on[name]["vertex_offset_mm"])
    # With the refinement keyed to acceptance (PR 3) the boundary follows the
    # vertices: the curves' spread and Hausdorff fall too.
    for name in ("circle", "ring"):
        assert on[name]["spread_mm"] < off[name]["spread_mm"], (name, off[name]["spread_mm"], on[name]["spread_mm"])
        assert on[name]["hausdorff_mm"] < off[name]["hausdorff_mm"], (name, off[name]["hausdorff_mm"], on[name]["hausdorff_mm"])
        assert on[name]["vertices"] > off[name]["vertices"]
    for name in ("bar", "purple", "orange"):
        assert on[name]["hausdorff_mm"] < off[name]["hausdorff_mm"] / 3, (
            name, off[name]["hausdorff_mm"], on[name]["hausdorff_mm"])
        assert abs(on[name]["offset_mm"]) < 0.02, (name, on[name]["offset_mm"])
        assert on[name]["vertices"] == 4, (name, on[name]["vertices"])
    assert on["dot"] == off["dot"]


def test_a_source_upscaled_to_the_resolution_floor_keeps_the_pixel_centre_polygon(tmp_path):
    """The Lanczos ramp is manufactured and the step declines it (the
    ladder's 200 px rung: the bar's polygon 4 -> 11 vertices, the orange
    rectangle's spread 0.063 -> 0.174 mm). A 120 px logo at 50 mm is 2.4
    px/mm in, upscaled to the 4.0 floor."""
    img, _c, _r = _disc(w=120, h=120, c=60, r=40)
    art = tmp_path / "small.png"
    cv2.imwrite(str(art), img)
    off, _p = digitize(art, PipelineConfig(target_width_mm=50.0, subpixel_edges=False))
    on, _p = digitize(art, PipelineConfig(target_width_mm=50.0, subpixel_edges=True))
    assert not any("subpixel_accepted" in r.meta for r in on.regions)
    assert [list(r.polygon.exterior.coords) for r in on.regions] == \
        [list(r.polygon.exterior.coords) for r in off.regions]

