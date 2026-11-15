"""Kent's 2026-11-15 flips of the counters worker's gap flags ("Flip both,
value 0.5"): defaults, and the OFF arm pinned in `tests/conftest.py` PRE_FLIP."""
from digitizer_core.config import PipelineConfig
from tests.conftest import PRE_FLIP


def test_satin_push_keeps_gaps_flip_is_held():
    """Kent ruled 0.5; the Director held the flip (2026-11-15) until the push
    never costs a stroke (enthusiast's tagline lost E arms and an N stem)."""
    assert PipelineConfig().satin_push_keeps_gaps is None
    assert PRE_FLIP["satin_push_keeps_gaps"] is None


def test_compact_satin_keeps_gaps_is_on_and_pinned_off():
    assert PipelineConfig().compact_satin_keeps_gaps is True
    assert PRE_FLIP["compact_satin_keeps_gaps"] is False


def test_a_kept_polygon_with_stray_lines_sews_its_polygon():
    """hed p.e. at 80 mm (2026-11-15): `_kept_gaps` gave one polygon and six
    zero-area LineStrings, and `small_solid_satin` raised on the collection,
    failing the whole digitize. The polygon is what sews."""
    from shapely.geometry import GeometryCollection, LineString, box

    from digitizer_core.stage7_sequence import _one_polygon
    body, fallback = box(0, 0, 3, 4), box(-1, -1, 4, 5)
    kept = GeometryCollection([body, LineString([(3, 0), (3.1, 0)]), LineString([(0, 4), (0, 4.2)])])
    out = _one_polygon(kept, fallback)
    assert out.geom_type == "Polygon" and out.equals(body)


def test_a_shape_cut_in_two_sews_as_stage_5_left_it():
    from shapely.geometry import GeometryCollection, LineString, MultiPolygon, box

    from digitizer_core.stage7_sequence import _one_polygon
    fallback = box(0, 0, 5, 2)
    two = MultiPolygon([box(0, 0, 2, 2), box(3, 0, 5, 2)])
    assert _one_polygon(two, fallback) is fallback
    assert _one_polygon(GeometryCollection([two, LineString([(0, 0), (1, 1)])]), fallback) is fallback
    assert _one_polygon(GeometryCollection(), fallback) is fallback
    assert _one_polygon(None, fallback) is fallback


def test_a_clip_geos_refuses_falls_back_to_the_intersection(monkeypatch):
    """`satin_push_keeps_gaps` 0.5 on CI (2026-11-15): `_push_rails`' fast
    `clip_by_rect` built a three-point ring on `test_preflight`'s full-bleed
    design and GEOS raised, failing the digitize. The clip now falls back."""
    import shapely
    from shapely.geometry import box

    from digitizer_core import stage6_satin

    poly = box(0, 0, 10, 10)
    assert stage6_satin._clip_rect(poly, 2, 2, 5, 5).equals(box(2, 2, 5, 5))

    def refuse(*_a, **_k):
        raise shapely.errors.GEOSException(
            "IllegalArgumentException: Invalid number of points in LinearRing found 3")
    monkeypatch.setattr(shapely, "clip_by_rect", refuse)
    assert stage6_satin._clip_rect(poly, 2, 2, 5, 5).equals(box(2, 2, 5, 5))


def test_a_plain_polygon_passes_through_untouched():
    from shapely.geometry import box

    from digitizer_core.stage7_sequence import _one_polygon
    poly = box(0, 0, 1, 1)
    assert _one_polygon(poly, box(0, 0, 2, 2)) is poly
