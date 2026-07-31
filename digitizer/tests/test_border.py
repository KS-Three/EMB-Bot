"""Stage 6 border — an outline sewn as one closed circuit.

The module's whole thesis is that a border is the region between two offsets
of a ring, expressed with `buffer` so containment is a boolean rather than a
sign convention. These tests hold it to the four numbers the corpus measured
(width, density, one circuit per ring, corners sewn through) and to the one
promise the default makes: with `border="off"` nothing changes at all.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.stage6_border import border_runs
from tests.conftest import TESTDATA, cfg

SQUARE = Polygon([(0, 0), (20, 0), (20, 20), (0, 20)])
DONUT = Polygon(
    [(math.cos(t) * 12, math.sin(t) * 12) for t in np.linspace(0, 2 * math.pi, 96)],
    [[(math.cos(t) * 6, math.sin(t) * 6) for t in np.linspace(2 * math.pi, 0, 96)]],
)
THIN_BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])
HAIRLINE = Polygon([(0, 0), (24, 0), (24, 0.5), (0, 0.5)])


def _runs(poly, style="auto", **kw):
    runs, report = border_runs(poly, "S1", entry=None, trim_at_mm=3.0,
                               style=style, **kw)
    return runs, report


# --- The default promises nothing changes ----------------------------------

def test_off_is_the_default_and_changes_nothing():
    """The measured case for `off`: our fill already ends both row ends on the
    shape's edge, so there is no ragged edge for a border to cover, and an
    unearned outline is a few hundred stitches of machine time for nothing."""
    assert PipelineConfig().border == "off"

    plain = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front"))[1]
    off = digitize(TESTDATA / "logo_whitebg.png",
                   cfg(garment_id="hat_front", border="off"))[1]
    assert plain.stats.stitch_count == off.stats.stitch_count
    assert not [r for _b, r in off.iter_runs() if r.kind in ("border", "bean")]


def test_style_none_and_missing_geometry_are_no_ops():
    assert _runs(SQUARE, style="none")[0] == []
    assert border_runs(None, "S1", entry=None, trim_at_mm=3.0)[0] == []


# --- One closed circuit per ring (law 13, 18/18) ---------------------------

def test_a_square_sews_as_one_circuit():
    runs, report = _runs(SQUARE)
    border = [r for r in runs if r.kind == "border"]
    assert len(border) == 1, "an outline is one circuit, not an assembly of arcs"
    assert report["loops"] == 1

    pts = border[0].points
    # A closed circuit ends where it began, within the deliberate overlap that
    # closes the seam.
    assert math.dist(pts[0], pts[-1]) <= machine.BORDER_CLOSURE_OVERLAP_MM + 0.5


def test_a_counter_gets_its_own_circuit():
    """A shape with a hole has two visible edges, so it has two borders. This
    is why the geometry is built with buffer: one call returns every ring."""
    _runs_, report = _runs(DONUT)
    assert report["loops"] == 2, f"expected exterior + counter, got {report['loops']}"


# --- The corpus numbers ----------------------------------------------------

def test_the_column_is_border_width_not_lettering_width():
    """Corpus law 1: border columns run 1.40 mm median against 2.21 mm for
    satin generally. Sewing borders at lettering width is most of why a
    machine outline reads heavy."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    crosses = sorted(math.dist(a, b) for a, b in zip(pts, pts[1:]))
    med = crosses[len(crosses) // 2]
    assert med == pytest.approx(machine.BORDER_WIDTH_MM, abs=0.15), \
        f"border column median {med:.2f} mm"


def test_density_is_the_looser_border_figure():
    """Corpus law 2: 0.45 mm, against 0.40-0.42 for lettering. Rails alternate
    A, B, A, B ... so two apart is the same rail."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    adv = sorted(math.dist(pts[i], pts[i + 2]) for i in range(len(pts) - 2))
    n = len(adv)
    assert adv[n // 2] == pytest.approx(machine.BORDER_DENSITY_MM, abs=0.08), \
        f"median same-rail advance {adv[n // 2]:.2f} mm"
    assert adv[int(n * 0.95)] <= 2 * machine.BORDER_DENSITY_MM


def test_no_stitch_exceeds_the_dst_ceiling():
    for poly in (SQUARE, DONUT, THIN_BAR):
        runs, _ = _runs(poly)
        for r in runs:
            for a, b in zip(r.points, r.points[1:]):
                assert math.dist(a, b) <= machine.MAX_STITCH_MM + 1e-6


# --- Containment is the point ----------------------------------------------

def test_the_whole_column_lies_inside_the_shape():
    """With BORDER_SEAM_OFFSET_MM at 0.0 the outer rail sits ON the visible
    edge and nothing crosses it. This is the assertion that would catch the
    winding-sign bug the module was built with `buffer` to make unexpressable:
    if offsets ever flipped outward, every border would fail here at once.
    """
    for poly in (SQUARE, DONUT):
        runs, _ = _runs(poly)
        room = poly.buffer(0.15)
        outside = [p for r in runs if r.kind == "border"
                   for p in r.points if not room.covers(Point(p))]
        assert outside == [], f"{len(outside)} border points outside the shape"


# --- The light tier and the refusal ----------------------------------------

def test_a_shape_too_thin_for_a_column_lightens_to_a_bean_run():
    runs, report = _runs(THIN_BAR)
    assert report["bean_loops"] >= 1
    assert report["loops"] == 0, "a 2 mm bar cannot host a 1.4 mm column"
    assert all(r.kind != "border" for r in runs)


def test_bean_style_lightens_even_where_a_column_would_fit():
    runs, report = _runs(SQUARE, style="bean")
    assert report["bean_loops"] >= 1 and report["loops"] == 0
    assert any(r.kind == "bean" for r in runs)


def test_a_shape_with_no_room_at_all_is_refused_not_faked():
    _runs_, report = _runs(HAIRLINE)
    assert report["too_narrow"] >= 1
    assert report["empty"], "nothing may be drawn where a centreline cannot live"


# --- Wiring ----------------------------------------------------------------

def test_auto_borders_the_fills_and_warns_when_it_lightens():
    auto = digitize(TESTDATA / "logo_whitebg.png",
                    cfg(garment_id="hat_front", border="auto"))[1]
    kinds = {r.kind for _b, r in auto.iter_runs()}
    assert "border" in kinds

    bean = digitize(TESTDATA / "logo_whitebg.png",
                    cfg(garment_id="hat_front", border="bean"))[1]
    assert "bean" in {r.kind for _b, r in bean.iter_runs()}
    assert "BORDER_LIGHTENED" in {w["code"] for w in bean.warnings}
