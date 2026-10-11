"""`cfg.coverage_edges` — the outline of an alpha cutout read straight from
the source's own alpha, as the half-coverage contour, instead of from the
nearest-upscaled mask's staircase.

Measured before it was built (docs/tracer-head-to-head-2026-10-10.md,
addendum): on two real logos' single-colour layers at 1.8 px/mm the mask
and everything traced from it sit about 0.10 mm from the true edge, the
coverage contour about 0.04, with a third of the turning. Default OFF.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import build_generation

from .conftest import TESTDATA

S = 16          # supersampling the truth is drawn at
FRAME = 120     # source pixels
WIDTH_MM = 50.0


def _cutout(tmp_path: Path, name: str, cov: np.ndarray, rgb=(0, 0, 0)) -> Path:
    """One colour everywhere, the shape in alpha — Becker's layout."""
    img = np.zeros((*cov.shape, 4), np.uint8)
    img[:, :, :3] = rgb[::-1]
    img[:, :, 3] = cov
    path = tmp_path / name
    cv2.imwrite(str(path), img)
    return path


def _coverage(draw) -> np.ndarray:
    canvas = np.zeros((FRAME * S, FRAME * S), np.uint8)
    draw(canvas)
    return cv2.resize(canvas, (FRAME, FRAME), interpolation=cv2.INTER_AREA)


def _disc_cov() -> np.ndarray:
    return _coverage(lambda c: cv2.circle(c, (60 * S, 60 * S), 40 * S, 255, -1))


def _bar_truth() -> np.ndarray:
    """A 70 x 24 px bar turned 27 degrees, corners in SUPERSAMPLED pixels."""
    a = np.radians(27.0)
    rot = np.array([[np.cos(a), -np.sin(a)], [np.sin(a), np.cos(a)]])
    half = np.array([[-35, -12], [35, -12], [35, 12], [-35, 12]], float)
    return (half @ rot.T + 60.0) * S


def _bar_cov() -> np.ndarray:
    pts = np.round(_bar_truth()).astype(np.int32)
    return _coverage(lambda c: cv2.fillPoly(c, [pts], 255))


def _ink(art: Path, **cfg_kw):
    """-> (Prep, the sewn regions) from stages 0-4."""
    gen = build_generation(str(art), PipelineConfig(target_width_mm=WIDTH_MM, **cfg_kw))
    return gen.p, [r for r in gen.regions if not r.meta.get("enclosed_background")]


def _to_source_px(p, pts_mm: np.ndarray) -> np.ndarray:
    """Stage 4's millimetres back to the SOURCE's pixel-centre coordinates,
    so an error is read against the truth and not against the sizing."""
    x0, y0, x1, y1 = p.art_bbox
    xw = pts_mm[:, 0] * p.px_per_mm + (x0 + x1) / 2.0
    yw = pts_mm[:, 1] * p.px_per_mm + (y0 + y1) / 2.0
    return np.column_stack([(xw + 0.5) / p.upscale[0] - 0.5, (yw + 0.5) / p.upscale[1] - 0.5])


def _densify(pts: np.ndarray, step: float = 0.05) -> np.ndarray:
    out = []
    for a, b in zip(pts, np.roll(pts, -1, axis=0)):
        n = max(1, int(np.ceil(np.hypot(*(b - a)) / step)))
        out.append(a + (b - a) * (np.arange(n)[:, None] / n))
    return np.vstack(out)


def _spikes(poly: Polygon) -> int:
    """Vertices where the outline turns back on itself by more than 120 degrees."""
    n = 0
    for ring in [poly.exterior, *poly.interiors]:
        pts = np.asarray(ring.coords)[:-1]
        seg = np.roll(pts, -1, axis=0) - pts
        ang = np.arctan2(seg[:, 1], seg[:, 0])
        turn = np.abs((np.diff(np.concatenate([ang, ang[:1]])) + np.pi) % (2 * np.pi) - np.pi)
        n += int((turn > np.radians(120)).sum())
    return n


def _vertices(regions) -> int:
    return sum(len(r.polygon.exterior.coords) - 1 + sum(len(h.coords) - 1 for h in r.polygon.interiors)
               for r in regions)


def test_it_ships_off():
    assert PipelineConfig().coverage_edges is False


def test_a_low_res_cutout_disc_lands_on_the_circle(tmp_path):
    art = _cutout(tmp_path, "disc.png", _disc_cov())
    p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert p.upscale[0] > 1.0                               # the regime under test
    assert len(on) == len(off) == 1
    assert on[0].meta.get("coverage_edges") is True
    assert "coverage_edges" not in off[0].meta
    # Read against the true circle, in source pixels: centre 60 - 0.5 + 0.5/16,
    # radius 40 + 0.5/16 (cv2 fills sub-pixels within r + 0.5).
    c, r = 60.0 + 0.5 / S - 0.5, 40.0 + 0.5 / S
    px_mm = p.px_per_mm / p.upscale[0]

    def err(region):
        """Each VERTEX's distance from the circle, mm. The chords between
        them sag inside it by the simplify tolerance on either setting, and
        that is `simplify_tol_mm`'s business, not this flag's."""
        pts = _to_source_px(p, np.asarray(region.polygon.exterior.coords)[:-1])
        return np.abs(np.hypot(pts[:, 0] - c, pts[:, 1] - c) - r) / px_mm

    e_off, e_on = err(off[0]), err(on[0])
    assert np.median(e_on) < 0.02, np.median(e_on)
    assert e_on.max() < 0.06, e_on.max()
    # A clean disc is where the shipped native read is already at its best;
    # the contour has to match it there, not beat it.
    assert np.median(e_on) < np.median(e_off) + 0.01, (np.median(e_off), np.median(e_on))
    assert _spikes(on[0].polygon) == 0


def test_a_low_res_cutout_bar_keeps_straight_sides_and_rounds_its_corners(tmp_path):
    """The stated cost, pinned. Half coverage cannot hold a sharp corner: it
    cuts across it by a fraction of a source pixel (0.625 mm here), where
    the shipped native read fits the two sides and squares it (0.03 mm at
    worst on this bar, in 4 vertices). On a clean synthetic the shipped
    polygon is the better one; the flag earns its keep on real artwork,
    where that fit is refused more often than not."""
    art = _cutout(tmp_path, "bar.png", _bar_cov())
    p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert len(on) == len(off) == 1
    truth = Polygon((_bar_truth() + 0.5) / S - 0.5).exterior
    px_mm = p.px_per_mm / p.upscale[0]

    def err(region):
        pts = _to_source_px(p, _densify(np.asarray(region.polygon.exterior.coords)[:-1]))
        return np.array([truth.distance(Point(q)) for q in pts]) / px_mm

    e_off, e_on = err(off[0]), err(on[0])
    assert np.median(e_on) < 0.05, np.median(e_on)          # the sides
    assert 0.10 < e_on.max() < 0.25, e_on.max()              # the corners, bounded
    assert e_off.max() < 0.06, e_off.max()                   # what it gives up here
    assert _spikes(on[0].polygon) == 0


def test_it_is_inert_without_alpha(tmp_path):
    cov = _disc_cov()
    opaque = np.full((FRAME, FRAME, 3), 255, np.uint8)
    opaque[cov > 0] = (255 - cov[cov > 0, None] * np.array([1.0, 0.8, 0.6])).astype(np.uint8)
    art = tmp_path / "opaque.png"
    cv2.imwrite(str(art), opaque)
    _p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert [r.polygon.wkt for r in on] == [r.polygon.wkt for r in off]
    assert all("coverage_edges" not in r.meta for r in on)


def test_it_is_inert_on_a_source_at_its_own_resolution(tmp_path):
    canvas = np.zeros((900, 900), np.uint8)
    cv2.circle(canvas, (450, 450), 400, 255, -1, cv2.LINE_AA)
    art = _cutout(tmp_path, "big.png", canvas)
    p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert p.upscale == (1.0, 1.0)
    assert [r.polygon.wkt for r in on] == [r.polygon.wkt for r in off]


def test_a_second_ink_leaves_the_whole_cutout_alone(tmp_path):
    """The alpha contour is the whole outline only when there is one ink.
    Two colours meeting inside a cutout share an edge alpha says nothing
    about, so nothing in it is rewritten."""
    cov = _disc_cov()
    img = np.zeros((FRAME, FRAME, 4), np.uint8)
    img[:, :60, :3] = (200, 30, 30)
    img[:, 60:, :3] = (30, 30, 200)
    img[:, :, 3] = cov
    art = tmp_path / "halves.png"
    cv2.imwrite(str(art), img)
    _p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert len(off) >= 2
    assert [r.polygon.wkt for r in on] == [r.polygon.wkt for r in off]
    assert all("coverage_edges" not in r.meta for r in on)


def test_becker_loses_its_reversals_and_keeps_its_ink():
    """The real file the flag was built for. Shipped, the outline turns back
    on itself 37 times (a vertex turning more than 120 degrees) over ten
    regions; from the alpha contour, 7 — the letters' own tips. Same
    regions, the same ink to within the half-pixel the mask sat inside."""
    art = TESTDATA / "becker_marine_logo.png"
    p, off = _ink(art)
    _p, on = _ink(art, coverage_edges=True)
    assert p.native_alpha is not None and p.upscale[0] > 1.0
    assert len(on) == len(off)
    assert all(r.meta.get("coverage_edges") for r in on)
    # The enclosed letter bodies are the same contour from the other side.
    holes = [r for r in build_generation(str(art), PipelineConfig(
        target_width_mm=WIDTH_MM, coverage_edges=True)).regions if r.meta.get("enclosed_background")]
    assert holes and all(r.meta.get("coverage_edges") for r in holes)
    spikes_off, spikes_on = (sum(_spikes(r.polygon) for r in rs) for rs in (off, on))
    assert spikes_off > 25, spikes_off                       # what it is for
    assert spikes_on < spikes_off / 3, (spikes_off, spikes_on)
    area_off, area_on = (sum(r.polygon.area for r in rs) for rs in (off, on))
    assert abs(area_on - area_off) / area_off < 0.03, (area_off, area_on)
    assert _vertices(on) < _vertices(off), (_vertices(off), _vertices(on))
