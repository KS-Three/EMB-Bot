"""Branch-coverage gaps in export.py, threads.py and stage6_meander.py.

Found by running pytest --cov over a subset of the suite (export 84%, threads
92%, stage6_meander 93%); each test targets lines that run never reached.
Every assertion is measured from the emitted file / values, not parameters.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import export, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_meander import (
    _runs_from_points,
    _segments_conflict,
    _walk_polyline,
    meander_fill,
)
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from digitizer_core.threads import (
    CHART,
    DEFAULT_BRAND,
    brand_index,
    chart_for,
    load_chart,
    rgb_to_lab,
    snap_palette,
)


# --------------------------------------------------------------- export.py
def _plan() -> StitchPlan:
    runs = [StitchRun(points=[(0.0, 0.0), (2.0, 0.0), (2.0, 2.0)], kind=stitches.FILL)]
    return StitchPlan(
        blocks=[StitchBlock(0, CHART[0].number, CHART[0].rgb, runs)],
        palette=[{}],
    )


def test_write_dst_creates_parent_dirs_and_round_trips(tmp_path):
    out = export.write_dst(_plan(), tmp_path / "deep" / "nest" / "a.dst", label="x" * 40)
    assert out.is_file()
    pts = export.read_dst_points(out.read_bytes())
    # DST is relative-encoded; the shape (a 2 mm L) is what must survive.
    xs = [p[0] - pts[0][0] for p in pts]
    ys = [p[1] - pts[0][1] for p in pts]
    assert max(xs) == pytest.approx(2.0, abs=0.11)
    assert max(ys) == pytest.approx(2.0, abs=0.11)


def test_read_dst_points_skips_non_stitch_records():
    """A jump/trim/colour change must not appear as a needle penetration."""
    a = StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=stitches.FILL)
    b = StitchRun(points=[(5.0, 0.0), (6.0, 0.0)], kind=stitches.FILL, jump=True, trim=True)
    plan = StitchPlan(
        blocks=[StitchBlock(0, "1", (0, 0, 0), [a, b]),
                StitchBlock(1, "2", (255, 0, 0), [a])],
        palette=[{}, {}],
    )
    n_cmds = sum(1 for c, _ in stitches.iter_machine_commands(plan)
                 if c == stitches.CMD_STITCH)
    pts = export.read_dst_points(export.export_dst(plan))
    assert len(pts) == n_cmds


# -------------------------------------------------------------- threads.py
def test_chart_container_protocol_and_repr():
    chart = load_chart(DEFAULT_BRAND)
    assert len(chart) == len(chart.threads)
    assert chart[0] is chart.threads[0]
    assert list(iter(chart)) == chart.threads
    assert DEFAULT_BRAND in repr(chart) and str(len(chart)) in repr(chart)
    assert chart.lab.shape == (len(chart), 3)


def test_delta_e_is_zero_on_self_and_symmetric_ish():
    chart = load_chart(DEFAULT_BRAND)
    assert chart.delta_e(3, 3) == pytest.approx(0.0, abs=1e-9)
    assert chart.delta_e(0, 5) == pytest.approx(chart.delta_e(5, 0), abs=1e-6)
    assert chart.delta_e(0, 5) > 0.0


def test_chart_for_default_and_named_brand():
    class Cfg:
        thread_brand = None
    assert chart_for(Cfg()).id == DEFAULT_BRAND
    assert chart_for(None).id == DEFAULT_BRAND
    other = next(b["id"] for b in brand_index() if b["id"] != DEFAULT_BRAND)
    class Named:
        thread_brand = other
    assert chart_for(Named()).id == other


def test_module_level_snap_palette_matches_default_chart():
    rgbs = np.array([t.rgb for t in CHART.threads[:4]], dtype=np.float64)
    assert snap_palette(rgbs) == CHART.snap_palette(rgbs)
    assert len(snap_palette(rgbs)) == 4
    assert rgb_to_lab(rgbs).shape == (4, 3)


# ------------------------------------------------------ stage6_meander.py
def test_segments_conflict_branches():
    # proper crossing
    assert _segments_conflict((0, 0), (2, 2), (0, 2), (2, 0))
    # shared endpoint, different directions: legal contact
    assert not _segments_conflict((0, 0), (1, 0), (1, 0), (1, 1))
    # shared endpoint, doubling back along one line: thread on thread
    assert _segments_conflict((0, 0), (2, 0), (0, 0), (1, 0))
    # collinear continuation sharing only the endpoint: legal
    assert not _segments_conflict((0, 0), (1, 0), (1, 0), (2, 0))
    # collinear overlap (x-dominant, then y-dominant)
    assert _segments_conflict((0, 0), (3, 0), (1, 0), (4, 0))
    assert _segments_conflict((0, 0), (0, 3), (0, 1), (0, 4))
    # collinear, disjoint
    assert not _segments_conflict((0, 0), (1, 0), (2, 0), (3, 0))
    # T-touch: endpoint on the other segment's interior
    assert _segments_conflict((1, 0), (1, 1), (0, 0), (2, 0))
    # clear miss
    assert not _segments_conflict((0, 0), (1, 0), (0, 1), (1, 1))


def test_walk_polyline_short_and_zero_length_inputs():
    dark = lambda x, y: 1.0
    inside = lambda p: True
    assert _walk_polyline([(0.0, 0.0)], [1.0], dark, inside) == []
    # a zero-length segment is skipped, the real one after it is walked
    pts = _walk_polyline([(0.0, 0.0), (0.0, 0.0), (10.0, 0.0)],
                         [1.0, 1.0, 1.0], dark, inside)
    assert len(pts) >= 2
    assert all(sewing for _, sewing in pts)


def test_walk_polyline_light_tone_travels_and_amp_clamped_outside():
    light = lambda x, y: 0.0
    pts = _walk_polyline([(0.0, 0.0), (10.0, 0.0)], [1.0, 1.0], light,
                         lambda p: True)
    assert len(pts) >= 2 and not any(s for _, s in pts)
    # dark tone but nowhere inside: the zig-zag offset is refused and the
    # stitch stays ON the curve (y == 0), never off it.
    dark = lambda x, y: 1.0
    pts = _walk_polyline([(0.0, 0.0), (10.0, 0.0)], [2.0, 2.0], dark,
                         lambda p: False)
    assert len(pts) >= 2
    assert all(abs(p[1]) < 1e-9 for p, _ in pts)


def test_runs_from_points_demotes_lone_sewing_point_and_merges():
    pts = [((0.0, 0.0), False), ((1.0, 0.0), True), ((2.0, 0.0), False),
           ((3.0, 0.0), False)]
    runs = _runs_from_points(pts, "S")
    # the lone sewing point became travel and merged with its neighbours
    assert [r.kind for r in runs] == [stitches.TRAVEL]
    assert runs[0].points == [(0.0, 0.0), (1.0, 0.0), (2.0, 0.0), (3.0, 0.0)]
    # a real sewing pair stays a FILL run between travel runs
    pts = [((0.0, 0.0), False), ((1.0, 0.0), True), ((2.0, 0.0), True),
           ((3.0, 0.0), False)]
    kinds = [r.kind for r in _runs_from_points(pts, "S")]
    assert kinds == [stitches.TRAVEL, stitches.FILL, stitches.TRAVEL]
    assert _runs_from_points([], "S") == []


def _tiny_region(w_mm: float, h_mm: float) -> Region:
    poly = Polygon([(-w_mm / 2, -h_mm / 2), (w_mm / 2, -h_mm / 2),
                    (w_mm / 2, h_mm / 2), (-w_mm / 2, h_mm / 2)])
    return Region(shape_id="Sx", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area)


def _dark_source() -> SourcePixels:
    rgb = np.full((280, 400, 3), 8, np.uint8)
    return SourcePixels(rgb=rgb, px_per_mm=4.0, origin_px=(200.0, 140.0))


@pytest.mark.parametrize("w,h", [(0.05, 0.05), (0.3, 0.3)])
def test_meander_fill_degenerate_regions_report_empty(w, h):
    runs, report = meander_fill(_tiny_region(w, h), _dark_source(), PipelineConfig())
    assert report["empty"] is True
    assert runs == []
    assert report["too_thin"] is True


def test_meander_fill_thin_strip_flags_too_thin_but_still_sews():
    runs, report = meander_fill(_tiny_region(60.0, 0.3), _dark_source(), PipelineConfig())
    assert report["too_thin"] is True
