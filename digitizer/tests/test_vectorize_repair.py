"""Stage 4 keeps what a geometry repair returns — all of it, at any depth.

`approxPolyDP` can make a traced boundary cross itself, and `make_valid` then
repairs it. The repair's SHAPE is not one thing: sometimes a bare Polygon,
sometimes a MultiPolygon, sometimes a GeometryCollection mixing a MultiPolygon
with the dangling edges the repair shed. Stage 4 used to scan only the top
level for `Polygon` and keep the single largest match, which failed twice over:

  * a GeometryCollection scanned as "no polygons at all" and the whole region
    was dropped — 944 mm² and 718 mm² on `owl_kent.jpg` (20% and 15% of the
    design, taking their thread colours with them), and 2,787 mm² on
    `summit_badge.png`, the entire badge body;
  * a repair that splits a mask into several parts lost every part but the
    largest — that is where the bare patch in the owl's lower body came from,
    a 30 mm² piece of the body region that simply lost the size contest.

Both were reported to the user as details "too small or thin to hold a
stitch", which is why they went unnoticed. These tests pin the geometry AND
that wording, because the wording is what made the geometry bug invisible.
"""
import numpy as np
import pytest
from shapely.geometry import GeometryCollection, LineString, MultiPolygon, Polygon
from shapely.validation import make_valid

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stage4_vectorize import _polygon_parts, vectorize
from digitizer_core.warnings_codes import DROPPED_SMALL_SHAPES

from .conftest import TESTDATA, cfg


# --- the flattener, against the shapes make_valid actually returns ----------


def test_polygon_parts_finds_a_bare_polygon():
    p = Polygon([(0, 0), (10, 0), (10, 10)])
    assert _polygon_parts(p) == [p]


def test_polygon_parts_finds_multipolygon_members():
    a = Polygon([(0, 0), (4, 0), (4, 4)])
    b = Polygon([(9, 9), (13, 9), (13, 13)])
    assert len(_polygon_parts(MultiPolygon([a, b]))) == 2


def test_polygon_parts_finds_polygons_NESTED_in_a_collection():
    # The exact shape that dropped two fifths of the owl: the polygons are
    # inside a MultiPolygon inside the collection, so a flat scan sees none.
    a = Polygon([(0, 0), (4, 0), (4, 4)])
    b = Polygon([(9, 9), (13, 9), (13, 13)])
    gc = GeometryCollection([MultiPolygon([a, b]), LineString([(0, 0), (1, 1)])])
    assert [g.geom_type for g in gc.geoms] == ["MultiPolygon", "LineString"]
    assert len(_polygon_parts(gc)) == 2


def test_polygon_parts_ignores_lines_and_empties():
    assert _polygon_parts(LineString([(0, 0), (1, 1)])) == []
    assert _polygon_parts(Polygon()) == []
    assert _polygon_parts(None) == []


def test_a_self_intersecting_bowtie_really_does_repair_to_several_parts():
    # Not a mock: this is the geometry class stage 4 meets, and the reason
    # "keep the largest part" loses real area.
    bowtie = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])
    assert not bowtie.is_valid
    parts = _polygon_parts(make_valid(bowtie))
    assert len(parts) == 2


# --- the stage itself ------------------------------------------------------


def _prep(h=120, w=120, px_per_mm=4.0):
    return Prep(
        rgb=np.zeros((h, w, 3), np.uint8),
        bg_mask=np.zeros((h, w), bool),
        px_per_mm=px_per_mm,
        art_bbox=(0, 0, w, h),
    )


def _bowtie_mask(h=120, w=120):
    """A mask whose traced outline self-intersects: two blocks meeting at one
    pixel corner, which is exactly what a pinched region looks like after
    simplification."""
    m = np.zeros((h, w), bool)
    m[10:50, 10:50] = True
    m[50:90, 50:90] = True
    return m


def test_a_pinched_mask_keeps_BOTH_of_its_parts():
    p = _prep()
    cfg = PipelineConfig()
    regions, dropped = vectorize([RegionMask.from_full(_bowtie_mask(), layer=0)], [0], p, cfg)
    assert not dropped, "a sewable mask must never be reported as dropped"
    assert len(regions) == 2, (
        "keeping only the largest part is what left bare fabric in the owl")
    # Both lobes are ~100 mm² at 4 px/mm; neither is a rounding artefact.
    assert min(r.area_mm2 for r in regions) > 50


def test_both_parts_carry_the_masks_own_thread_and_layer():
    # They are the same artwork in the same colour — a repair must not invent
    # a thread or strand one part into another layer.
    p = _prep()
    regions, _ = vectorize([RegionMask.from_full(_bowtie_mask(), layer=0)], [0], p, PipelineConfig())
    assert {r.thread_index for r in regions} == {0}
    assert {r.meta["layer"] for r in regions} == {0}
    assert len({r.shape_id for r in regions}) == len(regions), "ids must stay unique"


def test_an_ordinary_solid_mask_still_makes_exactly_one_region():
    # The valid-polygon path is the common one and must be untouched by any of
    # this: every flat-lane golden depends on it.
    p = _prep()
    m = np.zeros((120, 120), bool)
    m[20:100, 20:100] = True
    regions, dropped = vectorize([RegionMask.from_full(m, layer=0)], [0], p, PipelineConfig())
    assert len(regions) == 1
    assert not dropped


def test_a_mask_with_nothing_sewable_is_still_reported_as_dropped():
    # The drop path has to keep working — a shape vanishing with no trace is
    # the failure mode stage 4's own docstring calls untrustworthy.
    p = _prep(px_per_mm=1.0)
    m = np.zeros((120, 120), bool)
    m[10, 10] = True
    cfg = PipelineConfig()
    regions, dropped = vectorize([RegionMask.from_full(m, layer=0)], [0], p, cfg)
    assert regions == []
    assert len(dropped) == 1


# --- the warning that hid all of the above ---------------------------------


def _drop_warning(monkeypatch, areas):
    """Run the real pipeline with stage 4 forced to report `areas` as dropped,
    and return the DROPPED_SMALL_SHAPES warning it produces."""
    import digitizer_core.pipeline as pipeline

    real = pipeline.vectorize

    def fake(masks, thread_indices, p, cfg):
        regions, _ = real(masks, thread_indices, p, cfg)
        return regions, list(areas)

    monkeypatch.setattr(pipeline, "vectorize", fake)
    res = pipeline.run_stages(TESTDATA / "logo_whitebg.png", cfg())
    hits = [w for w in res.warnings if w["code"] == DROPPED_SMALL_SHAPES]
    assert hits, "the drop has to be reported at all"
    return hits[0]


def test_a_genuinely_tiny_drop_is_still_called_a_detail(monkeypatch):
    w = _drop_warning(monkeypatch, [1.0])
    assert w["all_small"] is True
    assert "too small or thin" in w["message"]


def test_a_LARGE_drop_is_not_called_a_detail_and_says_how_big(monkeypatch):
    # The whole point. 2,787 mm² of summit_badge.png went missing under the
    # words "too small or thin to hold a stitch"; a user who reads that does
    # not go looking for a missing region, and nobody did.
    w = _drop_warning(monkeypatch, [2787.3, 0.4])
    assert w["all_small"] is False
    assert "too small" not in w["message"]
    assert "2787" in w["message"].replace(",", "")
    assert w["largest_mm2"] == pytest.approx(2787.3)
