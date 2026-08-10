"""ShapeField — its own construction and correctness (DT-first migration M1,
docs/dt-first-architecture-2026-08-01.md §2).

Two things this file exists to prove independently of the byte-identical
regression test (`test_shapefield_byte_identical.py`, which only proves the
pipeline's OUTPUT does not move): that `ShapeField` itself computes sane
skeleton/EDT numbers on known geometry, and that its raster path really is a
faithful duplicate of `stage6_satin`'s own — not a reimplementation that
happens to agree on two fixture logos by coincidence.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Point, Polygon
from skimage.morphology import medial_axis

from digitizer_core.shapefield import ShapeField, build_shape_field, rasterize_polygon
from digitizer_core.stage6_satin import _WidthField, _rasterize, extract_strokes

BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])  # 24x2mm straight bar
O_RING = Polygon(
    [(math.cos(t) * 10, math.sin(t) * 10) for t in np.linspace(0, 2 * math.pi, 80)],
    [[(math.cos(t) * 7.5, math.sin(t) * 7.5) for t in np.linspace(2 * math.pi, 0, 80)]],
)
BLOB = Point(0, 0).buffer(8.0)


# --- rasterize_polygon mirrors stage6_satin._rasterize ----------------------

@pytest.mark.parametrize("poly", [BAR, O_RING, BLOB])
def test_rasterize_polygon_matches_stage6_satin_rasterize_exactly(poly):
    mask_a, scale_a, ox_a, oy_a = rasterize_polygon(poly)
    mask_b, scale_b, ox_b, oy_b = _rasterize(poly)
    assert scale_a == scale_b
    assert ox_a == ox_b
    assert oy_a == oy_b
    assert mask_a.shape == mask_b.shape
    assert np.array_equal(mask_a, mask_b)


# --- build_shape_field --------------------------------------------------

def test_build_shape_field_raises_the_same_way_stage6_satin_rasterize_does():
    """An empty (not merely tiny) polygon has NaN bounds and both
    rasterizers raise the same ValueError converting them to a pixel grid —
    `extract_strokes` never sees this because stage 4 never emits an empty
    polygon; this pins the two raster paths agreeing about the failure mode
    too, not just the success path."""
    empty = Polygon()
    with pytest.raises(ValueError):
        rasterize_polygon(empty)
    with pytest.raises(ValueError):
        _rasterize(empty)


def test_build_shape_field_matches_the_inline_medial_axis_call():
    """The core claim of the module: build_shape_field's skeleton and DT are
    the SAME arrays stage6_satin's own inline rasterize+medial_axis(rng=0)
    call would produce for the same polygon — a faithful hoist, not a
    reimplementation with different numerics."""
    mask, scale, ox, oy = _rasterize(BAR)
    expect_skel, expect_dist = medial_axis(mask > 0, return_distance=True, rng=0)

    field = build_shape_field(BAR)
    assert field is not None
    assert field.scale == scale
    assert field.ox == ox
    assert field.oy == oy
    assert np.array_equal(field.skel, expect_skel)
    assert np.array_equal(field.dist, expect_dist)
    assert np.array_equal(field.mask, mask.astype(bool))


def test_build_shape_field_reports_the_right_half_width_on_a_straight_bar():
    """BAR is 2mm wide. The medial axis's DT at skeletal pixels should read
    close to 1mm (half the width) in the bar's straight middle."""
    field = build_shape_field(BAR)
    assert field is not None
    max_half_mm = float(field.dist[field.skel].max()) / field.scale
    assert 0.8 <= max_half_mm <= 1.2


def test_build_shape_field_is_deterministic():
    """rng=0 must make repeated calls agree — same requirement
    extract_strokes's own docstring states for the inline call."""
    a = build_shape_field(O_RING)
    b = build_shape_field(O_RING)
    assert a is not None and b is not None
    assert np.array_equal(a.skel, b.skel)
    assert np.array_equal(a.dist, b.dist)


# --- ShapeField.half_at mirrors _WidthField.half_at -------------------------

def test_half_at_matches_widthfield_half_at_pointwise():
    field = build_shape_field(BAR)
    assert field is not None
    legacy = _WidthField(dist=field.dist, scale=field.scale, ox=field.ox, oy=field.oy)

    for pt in [(0.1, 1.0), (12.0, 1.0), (23.9, 1.0), (-5.0, -5.0), (12.0, 0.0)]:
        assert field.half_at(pt) == legacy.half_at(pt)


def test_half_at_is_zero_outside_the_field():
    field = build_shape_field(BAR)
    assert field is not None
    assert field.half_at((1000.0, 1000.0)) == 0.0


# --- ShapeField structure ----------------------------------------------

def test_shapefield_is_frozen():
    field = build_shape_field(BAR)
    assert field is not None
    with pytest.raises(Exception):
        field.scale = 99.0  # type: ignore[misc]


def test_shapefield_carries_mask_skel_dist_scale_origin():
    field = build_shape_field(BAR)
    assert field is not None
    assert isinstance(field, ShapeField)
    assert field.mask.dtype == np.bool_
    assert field.skel.dtype == np.bool_
    assert field.mask.shape == field.dist.shape == field.skel.shape
    assert field.scale > 0
    assert isinstance(field.ox, float)
    assert isinstance(field.oy, float)


# --- extract_strokes(use_shapefield=True) agrees with the default path -----

@pytest.mark.parametrize("poly", [BAR, O_RING, BLOB])
def test_extract_strokes_use_shapefield_matches_default_path(poly):
    strokes_a, half_a, field_a = extract_strokes(poly)
    strokes_b, half_b, field_b = extract_strokes(poly, use_shapefield=True)

    assert half_a == half_b
    assert len(strokes_a) == len(strokes_b)
    for sa, sb in zip(strokes_a, strokes_b):
        assert sa.spine == sb.spine
        assert sa.free_start == sb.free_start
        assert sa.free_end == sb.free_end
        assert sa.closed == sb.closed

    if field_a is None:
        assert field_b is None
    else:
        assert field_b is not None
        assert np.array_equal(field_a.dist, field_b.dist)
        assert field_a.scale == field_b.scale
        assert field_a.ox == field_b.ox
        assert field_a.oy == field_b.oy


def test_extract_strokes_use_shapefield_on_a_sliver_matches_default():
    """A sub-pixel sliver is the shape `test_satin.py`'s own
    `test_a_degenerate_sliver_reports_empty_never_raises` exercises — either
    an empty result or real strokes is honest, but whichever it is, both
    raster paths must agree."""
    sliver = Polygon([(0, 0), (10, 0), (10, 0.05), (0, 0.05)])
    a = extract_strokes(sliver)
    b = extract_strokes(sliver, use_shapefield=True)
    assert [s.spine for s in a[0]] == [s.spine for s in b[0]]
    assert a[1] == b[1]
