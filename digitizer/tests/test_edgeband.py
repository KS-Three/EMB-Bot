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


def test_bare_arc_measures_a_strip_of_known_length():
    """THE calibration test. A 100 px square covered everywhere except a 30 px
    run of its bottom edge reports 2.1 mm, within one pixel. An instrument never
    shown a known answer is how this repo acquired a 0.00 mm figure with nothing
    behind it.

    2.1 and not 3.0, counted rather than assumed. A boundary pixel is bare when
    the nearest thread is FURTHER than w_px, so the four columns at each end of
    the strip — within 4 px of the thread that survives beside it — are not bare:
    30 - 4 - 4 = 22 bare pixels, EDT 5.0 at col 44 and 4.0 at col 43. An arc is
    then the distance walked BETWEEN its pixels, 21 steps of 0.1 mm. Both
    subtractions are the module's stated definitions, so this pins them; a
    version that measured the deleted strip instead would read 3.0 here.
    """
    sh = square(140, 140, 20, 20, 100, 100)
    thread = sh.copy()
    thread[110:120, 40:70] = False      # 30 px of the bottom edge, 10 px deep
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert arcs, "a 30 px bare strip must produce an arc"
    assert max(arcs) == pytest.approx(2.1, abs=0.1), f"got {sorted(arcs)}"


def test_fully_covered_shape_reports_no_arcs():
    sh = square(140, 140, 20, 20, 100, 100)
    assert eb.bare_arcs(sh, sh, 4.0) == []


def test_shape_with_no_thread_at_all_reports_its_whole_perimeter():
    """Perimeter of a 100 px square is 400 px = 40 mm. The contour walks pixel
    centres, so it traces a 99 px square: 396 px = 39.6 mm."""
    sh = square(140, 140, 20, 20, 100, 100)
    arcs = eb.bare_arcs(sh, np.zeros((140, 140), bool), 4.0)
    assert max(arcs) == pytest.approx(39.6, abs=0.2), f"got {sorted(arcs)}"


def test_an_arc_wraps_the_start_of_a_ring():
    """A bare run straddling the contour's own index 0 is ONE arc, not two.
    Rings close; an implementation that forgets it halves its worst finding."""
    sh = square(140, 140, 20, 20, 100, 100)
    thread = sh.copy()
    thread[20:30, 20:60] = False        # top edge, spanning the top-left corner
    thread[20:60, 20:30] = False        # left edge, same corner
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert max(arcs) > 6.0, f"corner-spanning run must not be split: {sorted(arcs)}"


def test_holes_are_walked_as_well_as_the_outline():
    """A ring's inner boundary is an edge like any other."""
    sh = square(140, 140, 20, 20, 100, 100)
    sh[55:85, 55:85] = False           # a 30 px square hole
    thread = sh.copy()
    thread[50:90, 50:90] = False       # strip thread from all around the hole
    arcs = eb.bare_arcs(sh, thread, 4.0)
    assert arcs, "the hole's own boundary must be measured"


def write_stitches(path, pts, breaks=None):
    """A minimal `*_stitches.csv` in the harness's own column vocabulary."""
    breaks = breaks or [False] * len(pts)
    with open(path, "w", newline="") as f:
        f.write("x_mm,y_mm,trim,jump\n")
        for (x, y), b in zip(pts, breaks):
            f.write(f"{x},{y},{1 if b else 0},0\n")


def test_both_sides_read_through_one_rasteriser():
    """Mutation guard. `prep_both.py` hand-rolled a second copy of a shared
    block and silently dropped three keys from it for weeks (fixed 5328257).
    Re-hand-rolling a reader here — any different thread width, any different
    padding — fails this."""
    import artfidelity
    tmp = Path(__import__("tempfile").mkdtemp())
    pts = [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]
    write_stitches(tmp / "s.csv", pts)
    assert np.array_equal(eb.side_mask(tmp / "s.csv"),
                          artfidelity.pro_mask(tmp / "s.csv"))


def test_side_mask_returns_bool():
    """`boundary_distance_mm` documents what a uint8 mask costs: 6553.6 mm
    returned as a plausible number, past every guard, with no exception
    (enginefidelity.py:96-105). Same trap, same guard."""
    tmp = Path(__import__("tempfile").mkdtemp())
    write_stitches(tmp / "s.csv", [(0.0, 0.0), (10.0, 0.0), (10.0, 6.0)])
    assert eb.side_mask(tmp / "s.csv").dtype == bool
