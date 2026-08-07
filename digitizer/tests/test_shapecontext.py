"""`shapecontext.shape_context_distance` — Belongie/Malik/Puzicha 2002's Shape
Context descriptor, a pure geometry comparison between two point sets (see
the module's own docstring for what it does and does not answer). These
tests establish the invariances the module docstring claims (translation,
scale; rotation is deliberately NOT invariant) and that the distance
actually discriminates a small perturbation from a structural change (a
corner appearing, a hole opening) — the property `textcluster.py`'s
before/after regularization gate depends on.
"""
from __future__ import annotations

import pytest
from shapely.affinity import rotate, scale, translate
from shapely.geometry import Polygon

from digitizer_core.shapecontext import shape_context_distance


def _rect(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    return Polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                     (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])


def _ring(outer: float, inner: float) -> Polygon:
    o = _rect(outer, outer)
    i = _rect(inner, inner)
    return Polygon(o.exterior.coords, [i.exterior.coords])


def _l_shape(long_arm: float = 1.8, short_arm: float = 0.5, thick: float = 0.35) -> Polygon:
    return Polygon([
        (0, 0), (thick, 0), (thick, long_arm - thick),
        (short_arm, long_arm - thick), (short_arm, long_arm),
        (0, long_arm),
    ])


def _chamfered_square(w: float, h: float, cut: float) -> Polygon:
    """A square with one corner sliced off by a right triangle of leg
    length `cut` -- a small `cut` is a minor edit (the kind of thing
    de-staircasing/smoothing legitimately does); a large `cut` removes a
    real structural chunk of the shape."""
    return Polygon([(-w / 2, -h / 2), (w / 2 - cut, -h / 2), (w / 2, -h / 2 + cut),
                     (w / 2, h / 2), (-w / 2, h / 2)])


def test_identical_shape_has_zero_distance():
    sq = _rect(1.8, 1.8)
    assert shape_context_distance(sq, sq) == pytest.approx(0.0, abs=1e-9)


def test_translation_invariant():
    """A shared shift changes every pairwise DIFFERENCE by nothing — the
    descriptor is built entirely from point-to-point differences within
    each shape (see the module docstring's "automatic, not implemented
    separately" note)."""
    sq = _rect(1.8, 1.8)
    moved = translate(sq, 37.0, -12.5)
    assert shape_context_distance(sq, moved) == pytest.approx(0.0, abs=1e-2)


def test_scale_invariant():
    """Every pairwise distance is normalized by the point set's own mean
    pairwise distance before binning (module docstring) — a shape and a
    uniformly-scaled copy of itself must match near-exactly."""
    sq = _rect(1.8, 1.8)
    bigger = scale(sq, 2.0, 2.0)
    smaller = scale(sq, 0.4, 0.4)
    # Small nonzero slack for bin-edge quantization at a different absolute
    # scale (a handful of the 64 sampled points can land one bin over when
    # the raster/geometry is rescaled) -- both must still be an order of
    # magnitude below any of this file's real perturbation/structural-change
    # distances (>= 0.01), not just "close to 0" by accident.
    assert shape_context_distance(sq, bigger) < 1e-3
    assert shape_context_distance(sq, smaller) < 1e-3


def test_rotation_is_not_invariant_by_design():
    """Deliberate scope decision (module docstring): the one real caller
    compares a shape to itself before/after an edit that never rotates it,
    so a 45-degree rotation should read as a real, nonzero difference, not
    silently normalized away."""
    sq = _rect(1.8, 1.8)
    rotated = rotate(sq, 45.0)
    assert shape_context_distance(sq, rotated) > 0.2


def test_small_perturbation_scores_lower_than_a_structural_change():
    """The core discriminative claim this module exists for: a minor edit
    (a small corner chamfer, the kind of thing de-staircasing/smoothing
    legitimately does) must score clearly lower than a major one (slicing
    off most of the shape) against the same base square — not just
    "nonzero", genuinely separated and monotonic in how much material
    changed."""
    sq = _rect(1.8, 1.8)
    minor = _chamfered_square(1.8, 1.8, cut=0.05)
    major = _chamfered_square(1.8, 1.8, cut=0.9)

    d_minor = shape_context_distance(sq, minor)
    d_major = shape_context_distance(sq, major)
    assert d_minor is not None and d_major is not None
    assert d_minor < 0.05, d_minor
    assert d_major > 5 * d_minor, (d_minor, d_major)


def test_a_hole_appearing_reads_as_a_real_structural_change():
    """Regularization filling in a letter's counter (the hole in an "O",
    "e", "a"...) must not look like a minor tweak — holes are sampled
    alongside the exterior ring specifically so this case is visible (module
    docstring's "Holes are sampled too" note)."""
    solid = _rect(1.8, 1.8)
    ring = _ring(1.8, 0.8)
    d = shape_context_distance(solid, ring)
    assert d is not None and d > 0.15, d


def test_matched_regularization_scores_far_below_a_mismatched_one():
    """Direct analog of `textcluster.SHAPE_CONTEXT_MAX_DIST`'s own real
    measurement: an L-shape buffered from its skeleton at its OWN true
    stroke half-width (a healthy regularization) must score far lower than
    the identical shape buffered at a radius wildly mismatched from its own
    stroke (a damaging one) -- confirms the distance actually separates
    "fine" from "damaged" rather than just reacting to any buffer at all.

    Uses `textcluster`'s own buffering primitive directly
    (`_skeleton_buffer_polygon`), bypassing `regularize_text_clusters`'s
    public entry point on purpose: that function now GATES on this exact
    distance (see `test_regularize_gates_on_shape_context_distance` in
    `test_textcluster.py`), so the mismatched case would already be
    rejected (polygon left untouched, distance measured against itself ==
    0) before this test could observe the raw discriminative signal it's
    checking.
    """
    from digitizer_core.shapefield import build_shape_field
    from digitizer_core.textcluster import _skeleton_buffer_polygon

    def buffered_distance(radius_mm: float) -> float:
        poly = _l_shape()
        field = build_shape_field(poly)
        assert field is not None
        new_poly = _skeleton_buffer_polygon(field, radius_mm)
        assert new_poly is not None, \
            "fixture radius must produce a valid buffer for this comparison to mean anything"
        d = shape_context_distance(poly, new_poly)
        assert d is not None
        return d

    matched = buffered_distance(0.175)     # ~= the L's own half stroke width
    mismatched = buffered_distance(0.9)    # ~5x too big
    assert matched < mismatched
    assert mismatched > 0.25, mismatched


def test_degenerate_polygon_returns_none_not_a_crash():
    sq = _rect(1.8, 1.8)
    assert shape_context_distance(sq, Polygon()) is None
    assert shape_context_distance(Polygon(), sq) is None
    assert shape_context_distance(Polygon(), Polygon()) is None
