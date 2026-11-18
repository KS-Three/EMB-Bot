"""`cfg.color_cap_fuse_split_tones`: a letter the palette cut in two tones, fused after the cap.

Precision Drone's THERMAL (2026-11-18): the E and R were each a light band
(thread 0700) over a deep band (0824), both folded onto spool 1305 by the cap
and left as two overlapping shapes. The flag unions such a pair into one shape.
"""
from __future__ import annotations

from shapely.geometry import Polygon, box

from digitizer_core import cap_fuse
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())


def _r(sid, poly, merged_from=None, thread=5):
    m = {"color_cap_merged_from": merged_from} if merged_from else {}
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=float(poly.area), meta=m)


def test_default_is_off():
    assert PipelineConfig().color_cap_fuse_split_tones is False


def test_two_tone_halves_fuse_into_one_shape():
    top = _r("Stop", box(0, 0, 5, 2.4), "0700")
    body = _r("Sbody", box(0, 2.0, 5, 5), "0824")          # overlaps the top by 0.4 mm
    regions = [top, body]
    rep = cap_fuse.apply(regions)
    assert rep["removed"] == 1 and len(regions) == 1
    g = regions[0].polygon
    assert g.geom_type == "Polygon" and abs(g.area - 25.0) < 0.2
    assert regions[0].shape_id == "Sbody"                   # the larger keeps its identity
    assert regions[0].meta["cap_fused"] == ["Stop"]


def test_halves_that_only_touch_along_a_seam_fuse():
    regions = [_r("A", box(0, 0, 4, 2), "0700"), _r("B", box(0, 2, 4, 5), "0824")]
    assert cap_fuse.apply(regions)["removed"] == 1


def test_same_original_thread_twice_is_not_a_split_tone():
    regions = [_r("A", box(0, 0, 4, 2), "0824"), _r("B", box(0, 2, 4, 5), "0824")]
    assert cap_fuse.apply(regions)["removed"] == 0 and len(regions) == 2


def test_a_shape_the_cap_never_moved_is_left_alone():
    regions = [_r("A", box(0, 0, 4, 2), "0700"), _r("B", box(0, 2, 4, 5))]
    assert cap_fuse.apply(regions)["removed"] == 0


def test_a_corner_touch_is_not_a_seam():
    regions = [_r("A", box(0, 0, 3, 3), "0700"), _r("B", box(3, 3, 6, 6), "0824")]
    assert cap_fuse.apply(regions)["removed"] == 0


def test_different_threads_are_never_fused():
    regions = [_r("A", box(0, 0, 4, 2), "0700", thread=5), _r("B", box(0, 2, 4, 5), "0824", thread=6)]
    assert cap_fuse.apply(regions)["removed"] == 0


def test_a_union_that_is_not_one_polygon_is_refused():
    # two bars linked only by a hairline overlap far from either: union stays one piece,
    # but a pair that would leave a MultiPolygon must not be fused
    a = _r("A", Polygon([(0, 0), (4, 0), (4, 2), (0, 2)]), "0700")
    b = _r("B", Polygon([(0, 2), (4, 2), (4, 5), (0, 5)]), "0824")
    c = _r("C", box(10, 0, 12, 2), "0700")                   # far away, same thread: untouched
    regions = [a, b, c]
    cap_fuse.apply(regions)
    assert any(r.shape_id == "C" for r in regions)
    assert all(r.polygon.geom_type == "Polygon" for r in regions)
