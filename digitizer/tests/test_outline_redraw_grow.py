"""`cfg.outline_redraw_grow_mm` (built OFF 2026-11-14): the redraw's inward seat
given back.

The redraw seats edges inside the source: about 0.065-0.088 mm on a 50 mm
upscaled disc. That shift is Becker's bare-fabric rise and, measured at the
pro's config, most of the redraw's extra trims. Growing the rewritten shapes
by 0.07 mm took Becker hat large back from 17 to 13 trims, its count without
the redraw (`docs/redraw-trims-2026-11-14.md`). Off (0.0), nothing runs.
"""
from __future__ import annotations

from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core.outline_redraw import apply_outline_redraw
from digitizer_core.regions import Region

SRC_PX, GRID_PX = 0.625, 0.125          # an upscaled source, as Becker's


def _staircase_disc(r_mm=8.0, hole=None):
    """A disc traced at source-pixel centres: the staircase the redraw rewrites."""
    cells = []
    n = int(r_mm / SRC_PX) + 2
    for i in range(-n, n):
        for j in range(-n, n):
            cx, cy = (i + 0.5) * SRC_PX, (j + 0.5) * SRC_PX
            if cx * cx + cy * cy <= r_mm * r_mm and (hole is None or cx * cx + cy * cy > hole * hole):
                cells.append(box(i * SRC_PX, j * SRC_PX, (i + 1) * SRC_PX, (j + 1) * SRC_PX))
    return unary_union(cells)


def _region(poly, sid="S1"):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area, source="test", meta={})


def test_off_by_default():
    assert PipelineConfig().outline_redraw_grow_mm == 0.0


def test_zero_is_the_redraw_as_it_was():
    a, b = [_region(_staircase_disc())], [_region(_staircase_disc())]
    apply_outline_redraw(a, SRC_PX, GRID_PX, k=0.75)
    apply_outline_redraw(b, SRC_PX, GRID_PX, k=0.75, grow_mm=0.0)
    assert a[0].meta["outline_redraw"] == "redrawn"
    assert a[0].polygon.wkb == b[0].polygon.wkb


def test_on_grows_only_what_was_redrawn_and_keeps_its_holes():
    plain = [_region(_staircase_disc(hole=3.0))]
    grown = [_region(_staircase_disc(hole=3.0))]
    apply_outline_redraw(plain, SRC_PX, GRID_PX, k=0.75)
    apply_outline_redraw(grown, SRC_PX, GRID_PX, k=0.75, grow_mm=0.07)
    p, g = plain[0].polygon, grown[0].polygon
    assert plain[0].meta["outline_redraw"] == grown[0].meta["outline_redraw"] == "redrawn"
    assert len(g.interiors) == len(p.interiors) == 1
    # the outer edge moves out by the offset and the hole's edge in by it
    centre = Point(0.0, 0.0)
    assert abs(g.exterior.distance(centre) - p.exterior.distance(centre) - 0.07) < 0.01
    assert abs(p.interiors[0].distance(centre) - g.interiors[0].distance(centre) - 0.07) < 0.01
    assert abs(grown[0].area_mm2 - g.area) < 1e-9


def test_a_shape_the_letterform_pass_refit_is_not_grown():
    r = _region(_staircase_disc())
    r.meta["letterform_prior"] = "refit"
    before = r.polygon.wkb
    apply_outline_redraw([r], SRC_PX, GRID_PX, k=0.75, grow_mm=0.07)
    assert r.meta["outline_redraw"] == "letterform" and r.polygon.wkb == before
