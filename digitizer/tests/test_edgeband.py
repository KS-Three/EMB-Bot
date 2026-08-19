"""Calibration and wiring for the edge-coverage probe (tools/pro_parity/edgeband.py).

Every number this instrument reports is a millimetre nobody can check by eye, so
each primitive is measured against a synthetic shape whose answer is known by
construction before it is ever pointed at real work. The repo already carries one
edge-coverage figure with no instrument behind it — "starvation 0.00 mm with zero
variance on 13 real letterforms", config.py:685, which appears exactly once in the
repository and nowhere else. That is what this file exists to prevent.
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np
import pytest

TOOL = Path(__file__).resolve().parent.parent / "tools" / "pro_parity" / "edgeband.py"
spec = importlib.util.spec_from_file_location("pro_parity_edgeband", TOOL)
eb = importlib.util.module_from_spec(spec)
sys.modules["pro_parity_edgeband"] = eb
spec.loader.exec_module(eb)


def square(h, w, y0, x0, sh, sw):
    """A solid rectangle `sh` x `sw` at (y0, x0) on an h x w bool canvas."""
    m = np.zeros((h, w), bool)
    m[y0:y0 + sh, x0:x0 + sw] = True
    return m


def test_band_is_the_ring_within_w_px_of_the_boundary():
    """A 100x100 px square banded at 4 px keeps a 92x92 core.

    Counted, not eyeballed: the band is every pixel whose exact Euclidean
    distance to outside the shape is <= 4 px, which for a rectangle is the
    4-pixel frame — 100*100 - 92*92 = 1536 pixels.
    """
    sh = square(140, 140, 20, 20, 100, 100)
    band = eb.band_mask(sh, 4.0)
    assert band.dtype == bool
    assert np.count_nonzero(band) == 100 * 100 - 92 * 92
    assert not (band & ~sh).any(), "band must never leave the shape"


def test_band_of_an_empty_shape_is_empty_not_an_error():
    assert not eb.band_mask(np.zeros((10, 10), bool), 4.0).any()


def test_bare_frac_counts_only_band_pixels_with_no_thread():
    """Thread covering the left half of a square leaves exactly half its band bare."""
    sh = square(140, 140, 20, 20, 100, 100)
    thread = np.zeros((140, 140), bool)
    thread[:, :70] = True          # covers x in [20, 70) of the shape
    band = eb.band_mask(sh, 4.0)
    got = eb.bare_frac(band, thread)
    expect = np.count_nonzero(band & ~thread) / np.count_nonzero(band)
    assert got == pytest.approx(expect)
    assert 0.4 < got < 0.6, f"half-covered square should be near half bare, got {got}"


def test_bare_frac_of_an_empty_band_is_none_not_zero():
    """None means 'not measured'. Zero would read as 'perfectly covered'."""
    assert eb.bare_frac(np.zeros((10, 10), bool), np.zeros((10, 10), bool)) is None
