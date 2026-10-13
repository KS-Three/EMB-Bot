"""The hairline tier on a real photograph (docs/hairline-photo-trial-2026-10-12.md).

Two halves:

1. The LINE test the trial added to the per-strand gate
   (`stage6_hairline._line_contrasts`, `_LINE_MIN_CONTRAST`), on drawn
   rasters: a dark line on white is a strand; the grey blur band between a
   black field and a white one, and a sliver of a flat field, are not —
   whatever their width.
2. The trial's key counts on `owl_kent.jpg` (Kent's own photograph, the one
   real photo in the corpus), on the route that reproduces anywhere: the photo
   lane with `photo_prep=False`, which is byte-identical to what a machine
   without the rembg venv runs. Bounds, not exact values, where a count rests
   on medial-axis pixels that can move by one across platforms; the exact
   figures measured are in the doc's table.

`cfg.hairline` is default OFF and none of this runs with it off; the OFF md5
pins live in `test_thread_profile.py` and `test_hairline_ground.py`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, box

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from digitizer_core.stage6_hairline import (InkSource, _LINE_MIN_CONTRAST,  # noqa: E402
                                            measure)

PPM = 20.0          # source px per mm
SIZE = 200          # px: a 10 x 10 mm canvas, mm 0 at its centre
LIMIT = 0.48        # the 60 wt hairline line


def _ink(rgb: np.ndarray) -> InkSource:
    return InkSource(rgb=rgb, alpha=None, bg=np.zeros(rgb.shape[:2], bool),
                     upscale=(1.0, 1.0), px_per_mm=PPM, origin_px=(SIZE / 2.0, SIZE / 2.0))


def _paint(rgb, poly, colour):
    pts = np.asarray(poly.exterior.coords) * PPM + SIZE / 2.0 - 0.5
    cv2.fillPoly(rgb, [np.round(pts * 16).astype(np.int32)], colour,
                 lineType=cv2.LINE_AA, shift=4)


def _strand():
    return LineString([(-3.5, -0.4), (0.0, 0.3), (3.5, -0.2)]).buffer(0.15, cap_style=2)


def test_a_dark_line_on_white_is_a_strand():
    rgb = np.full((SIZE, SIZE, 3), 255, np.uint8)
    poly = _strand()
    _paint(rgb, poly, (20, 20, 20))
    m = measure(poly, LIMIT, ink=_ink(rgb))
    assert m["admit"], "a 0.3 mm dark line on white must sew as a hairline"
    lines = [e["line"] for e in m["hair_edges"] if "line" in e]   # read branches
    assert lines and min(lines) >= _LINE_MIN_CONTRAST, lines
    assert not any(e.get("refused") for e in m["thick_edges"])


def test_the_blur_band_between_black_and_white_is_not_a_strand():
    """The trial's commonest false strand: the grey rim a photo carries
    between a dark feather bar and white down. Its colour lies ON the path
    from one side to the other, so it is no line, however thin."""
    rgb = np.full((SIZE, SIZE, 3), 255, np.uint8)
    rgb[:, : SIZE // 2] = 0
    band = box(-0.15, -3.5, 0.15, 3.5)
    _paint(rgb, band, (128, 128, 128))
    m = measure(band, LIMIT, ink=_ink(rgb))
    assert m is not None
    assert not m["admit"], "a ramp band between two colours sewed as a hairline"
    assert any(e.get("refused") == "no_line" for e in m["thick_edges"])


def test_a_sliver_of_a_flat_field_is_not_a_strand():
    """A thin region the segmenter cut out of a smooth area: no edge at all.
    Before the line test this fell back to the traced width and passed."""
    rgb = np.full((SIZE, SIZE, 3), 200, np.uint8)
    poly = _strand()
    m = measure(poly, LIMIT, ink=_ink(rgb))
    assert m is not None
    assert not m["admit"]


def test_without_a_source_the_gate_is_unchanged():
    """No `ink`, no line test: the traced width alone decides, as before."""
    m = measure(_strand(), LIMIT, ink=None)
    assert m["admit"]
    assert all("line" not in e for e in m["hair_edges"] + m["thick_edges"])


# --- the owl ---------------------------------------------------------------

@pytest.fixture(scope="module")
def owl():
    from tools.hairline_photo_trial import PHOTO, stage_result
    if not PHOTO.exists():
        pytest.fail(f"{PHOTO} missing: the corpus photograph this trial pins")
    return stage_result("classical")


@pytest.mark.parametrize("wt", [40, 60])
def test_owl_census(owl, wt):
    from tools.hairline_photo_trial import census
    c = census(owl, "classical", wt)
    exp = PINS[wt]
    assert owl.design_class == "photo_subject"
    for key, (lo, hi) in exp.items():
        assert lo <= c[key] <= hi, f"{wt} wt {key} = {c[key]}, pinned {lo}..{hi}"
    # The diagnosis, as an invariant: on a real photo the line test refuses
    # a large share of the branches the width gate alone would have sewn.
    refused, run = c["branches_refused_no_line"], c["branches_run"]
    assert refused >= 0.5 * run, (refused, run)


# Measured 2026-10-12 (docs/hairline-photo-trial-2026-10-12.md, route
# `classical`, 127 mm), as (low, high) around the value measured — exact at
# the time: 40 wt 9 candidates / 19 run / 33 ladder / 16 refused; 60 wt 6 /
# 14 / 24 / 11. Before the line test the same census read 19 and 16
# candidates, 71 and 63 run branches, 0 refused.
PINS = {
    40: {"candidates": (7, 11), "branches_run": (15, 23),
         "branches_refused_no_line": (12, 20), "fragments": (5, 9)},
    60: {"candidates": (4, 8), "branches_run": (10, 18),
         "branches_refused_no_line": (8, 14), "fragments": (5, 9)},
}
