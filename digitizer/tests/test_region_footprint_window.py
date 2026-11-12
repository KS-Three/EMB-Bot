"""`stage4_vectorize._region_footprint_window` is `_region_footprint` cut to
the polygon's own pixel box (2026-11-11, speed only): the same pixels, so
`revalidate_threads` and `tag_enclosed_background` read the same counts and
the same Lab samples in the same order as they did off the frame-sized mask.

The window is what took those two passes from (regions x frame pixels) to
(regions x box pixels): 82 s and 44 s of the low-poly dolphin's 300 mm run.
"""
from __future__ import annotations

import math
from types import SimpleNamespace

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core.stage4_vectorize import _region_footprint, _region_footprint_window

SHAPE = (90, 140)              # (h, w) px
PX_PER_MM = 8.0
CX, CY = 70.0, 45.0


def _star(rng, cx_mm, cy_mm, r_mm, n) -> list[tuple[float, float]]:
    """A star-shaped ring round (cx, cy): random radii at sorted angles."""
    angles = np.sort(rng.uniform(0.0, 2.0 * math.pi, n))
    radii = rng.uniform(0.35, 1.0, n) * r_mm
    return [(cx_mm + r * math.cos(a), cy_mm + r * math.sin(a)) for a, r in zip(angles, radii)]


def _regions(seed: int, count: int):
    """Polygons in mm about the frame centre: most inside the frame, some
    across an edge, some wholly off it, a third with a hole."""
    rng = np.random.default_rng(seed)
    half_w, half_h = SHAPE[1] / 2 / PX_PER_MM, SHAPE[0] / 2 / PX_PER_MM
    for k in range(count):
        reach = 1.6 if k % 4 == 0 else 0.8          # every fourth may leave the frame
        cx_mm = rng.uniform(-half_w, half_w) * reach
        cy_mm = rng.uniform(-half_h, half_h) * reach
        r_mm = rng.uniform(0.2, 4.0)
        shell = _star(rng, cx_mm, cy_mm, r_mm, int(rng.integers(3, 14)))
        holes = [_star(rng, cx_mm, cy_mm, r_mm * 0.3, 5)] if k % 3 == 0 else []
        yield SimpleNamespace(polygon=Polygon(shell, holes))


def _window_as_frame(win) -> np.ndarray:
    full = np.zeros(SHAPE, bool)
    if win is not None:
        y0, x0, crop = win
        full[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]] = crop
    return full


@pytest.mark.parametrize("pad", [0, 1, 3])
def test_window_is_the_frame_mask_cut_to_its_box(pad):
    seen_edge = seen_off = seen_hole = 0
    for r in _regions(seed=20261111, count=400):
        want = _region_footprint(r, SHAPE, CX, CY, PX_PER_MM)
        win = _region_footprint_window(r, SHAPE, CX, CY, PX_PER_MM, pad=pad)
        assert np.array_equal(_window_as_frame(win), want)
        if win is None:
            seen_off += 1
            continue
        y0, x0, crop = win
        assert crop.dtype == bool and crop.size > 0
        assert 0 <= y0 and y0 + crop.shape[0] <= SHAPE[0]
        assert 0 <= x0 and x0 + crop.shape[1] <= SHAPE[1]
        seen_hole += bool(r.polygon.interiors)
        x0mm, y0mm, x1mm, y1mm = r.polygon.bounds
        seen_edge += (x0mm * PX_PER_MM + CX < 0 or y0mm * PX_PER_MM + CY < 0
                      or x1mm * PX_PER_MM + CX > SHAPE[1] or y1mm * PX_PER_MM + CY > SHAPE[0])
    # the cases the docstring names were all exercised
    assert seen_edge >= 10 and seen_off >= 3 and seen_hole >= 50


def test_no_pad_window_is_tight_on_an_inside_polygon():
    r = SimpleNamespace(polygon=Polygon([(-2, -1), (2, -1), (2, 1), (-2, 1)]))
    y0, x0, crop = _region_footprint_window(r, SHAPE, CX, CY, PX_PER_MM)
    assert (y0, x0) == (37, 54) and crop.shape == (17, 33)
    assert crop.all()


def test_one_pixel_pad_erodes_like_the_frame():
    """`revalidate_threads` erodes the footprint 3x3 under
    `resnap_mask_matches_grader`. With one clear pixel of margin the window's
    erosion is the frame's, at the frame's edge too (`cv2.erode` leaves the
    border alone, and the window ends where the frame does)."""
    kernel = np.ones((3, 3), np.uint8)
    checked = 0
    for r in _regions(seed=7, count=400):
        win = _region_footprint_window(r, SHAPE, CX, CY, PX_PER_MM, pad=1)
        frame = cv2.erode(_region_footprint(r, SHAPE, CX, CY, PX_PER_MM).astype(np.uint8), kernel) > 0
        if win is None:
            assert not frame.any()
            continue
        y0, x0, crop = win
        eroded = cv2.erode(crop.astype(np.uint8), kernel) > 0
        assert np.array_equal(_window_as_frame((y0, x0, eroded)), frame)
        checked += bool(frame.any())
    assert checked >= 100


def test_window_reads_the_same_pixels_in_the_same_order():
    """Boolean indexing walks a mask in raster order, so the Lab samples
    `revalidate_threads` draws through the window are the frame's, in order."""
    rng = np.random.default_rng(3)
    lab = rng.normal(size=(*SHAPE, 3))
    for r in _regions(seed=11, count=120):
        win = _region_footprint_window(r, SHAPE, CX, CY, PX_PER_MM)
        want = lab[_region_footprint(r, SHAPE, CX, CY, PX_PER_MM)]
        if win is None:
            assert len(want) == 0
            continue
        y0, x0, crop = win
        got = lab[y0:y0 + crop.shape[0], x0:x0 + crop.shape[1]][crop]
        assert np.array_equal(got, want)
