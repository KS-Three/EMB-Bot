"""Metric-core tests for tools/pro_parity/enginefidelity.py.

Pure-array tests only: no corpus, no engine run, no service. The instrument's
job is to see what the scorecard cannot — outline deviation between the
artwork's ink and the engine's coverage, in mm — so these tests pin the
geometry math on masks with hand-computable answers before the CLI ever
touches a real design.
"""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "pro_parity"))

import enginefidelity as ef  # noqa: E402


RES = 10.0  # px per mm, mirrors artfidelity.RES — asserted below so drift is loud


def disc(r_px, size=None, center=None):
    size = size or (2 * r_px + 21)
    cy, cx = center or (size // 2, size // 2)
    yy, xx = np.mgrid[:size, :size]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r_px ** 2


def ngon_disc(r_px, n, size=None):
    """Filled regular n-gon inscribed in a circle of r_px, same frame as disc()."""
    import cv2

    size = size or (2 * r_px + 21)
    c = size // 2
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    pts = np.stack([c + r_px * np.cos(ang), c + r_px * np.sin(ang)], axis=1)
    m = np.zeros((size, size), np.uint8)
    cv2.fillPoly(m, [np.round(pts).astype(np.int32)], 1)
    return m.astype(bool)


def test_constants_track_artfidelity():
    # The two instruments must rasterise identically or their numbers are not
    # comparable design-by-design.
    import artfidelity

    assert ef.RES == artfidelity.RES
    assert ef.THREAD_W_MM == artfidelity.THREAD_W_MM
    # Paint wider than physical thread on purpose: 0.40 mm at RES 10 aliases
    # against the ~3.98 px fill-row advance and manufactures pinholes
    # (measured 2026-08-17; see artfidelity.PAINT_W_MM's comment).
    assert ef.PAINT_W_MM == artfidelity.PAINT_W_MM
    assert ef.PAINT_W_MM > ef.THREAD_W_MM


def test_identical_masks_are_perfect():
    m = disc(50)
    haus, mean = ef.boundary_distance_mm(m, m)
    assert haus == 0.0
    assert mean == 0.0


def test_centered_squares_have_known_distance():
    # 200x200 px square vs 100x100 px square, same center. Edge midpoints are
    # 50 px apart, but the outer CORNERS' nearest inner point is the inner
    # corner at 50·√2 ≈ 70.7 px — Hausdorff takes the corner: 7.071 mm.
    # The symmetric mean: inner→outer is 50 px everywhere (perpendicular hit);
    # outer→inner averages ≈53.7 px (edges perpendicular, corner zones slant);
    # perimeter-weighted (800:400) ≈ 52.5 px = 5.25 mm.
    a = np.zeros((300, 300), bool)
    b = np.zeros((300, 300), bool)
    a[50:250, 50:250] = True
    b[100:200, 100:200] = True
    haus, mean = ef.boundary_distance_mm(a, b)
    assert haus == pytest.approx(7.071, abs=0.2)
    assert mean == pytest.approx(5.25, abs=0.3)


def test_disc_vs_20gon_sees_rdp_faceting():
    # The defect this instrument exists to measure: a 20 mm circle RDP'd into a
    # 20-gon. Max deviation is the sagitta of an 18° chord on r = 10 mm:
    # r·(1−cos 9°) ≈ 0.123 mm. The metric must resolve it (nonzero, right
    # order of magnitude), not drown it in raster noise.
    r = 100  # px = 10 mm at RES 10
    a = disc(r)
    b = ngon_disc(r, 20)
    haus, mean = ef.boundary_distance_mm(a, b)
    assert 0.05 <= haus <= 0.30, haus
    assert 0.0 < mean <= haus


def test_mean_is_below_hausdorff_for_local_defect():
    # A single bite out of one edge: worst-point distance is deep, the average
    # stays shallow. Distinguishes "one bad notch" from "everything is off".
    a = np.zeros((300, 300), bool)
    a[50:250, 50:250] = True
    b = a.copy()
    b[140:160, 50:80] = False  # 3 mm deep notch in the left edge
    haus, mean = ef.boundary_distance_mm(a, b)
    assert haus == pytest.approx(3.0, abs=0.3)
    assert mean < haus / 3


def test_empty_mask_raises():
    m = disc(30)
    empty = np.zeros_like(m)
    with pytest.raises(ValueError):
        ef.boundary_distance_mm(m, empty)
    with pytest.raises(ValueError):
        ef.boundary_distance_mm(empty, m)


def test_engine_mask_reads_ours_stitches_csv(tmp_path):
    # Same columns prep_all writes (block,run,trim,jump,x_mm,y_mm). Two runs:
    # a sewn horizontal segment, then a trim-move whose arriving segment must
    # NOT be painted — identical semantics to artfidelity.pro_mask.
    p = tmp_path / "ours_stitches.csv"
    p.write_text(
        "block,run,trim,jump,x_mm,y_mm\n"
        "0,0,0,0,0.0,0.0\n"
        "0,0,0,0,10.0,0.0\n"
        "0,1,1,0,10.0,5.0\n"
        "0,1,0,0,20.0,5.0\n"
    )
    m = ef.engine_mask(p)
    assert m.dtype == bool
    # cv2.line's thickness is approximate (a requested 5 paints 7 rows on this
    # build), so don't pin its internals — self-calibrate: paint one reference
    # 100 px line at the same requested width and bound the CSV mask against
    # twice that. The two sewn 10 mm segments must land near 2x the reference;
    # the trim hop (10,0)→(10,5) must contribute nothing.
    import cv2

    ref = np.zeros((60, 300), np.uint8)
    tw = max(1, int(round(ef.PAINT_W_MM * ef.RES)))
    cv2.line(ref, (4, 30), (104, 30), 1, tw)
    ref_on = np.count_nonzero(ref)
    on = np.count_nonzero(m)
    assert 1.7 * ref_on <= on <= 2.3 * ref_on, (on, ref_on)
    # Trim semantics: the hop's midpoint (10 mm, 2.5 mm) is bare.
    assert not m[int(2.5 * ef.RES) + 4, int(10.0 * ef.RES) + 4]
