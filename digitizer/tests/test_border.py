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

from digitizer_core import PipelineConfig, Region, digitize, fabric_for_garment, machine
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_border import border_runs
from digitizer_core.stage7_sequence import sequence
from digitizer_core.warnings_codes import BORDER_SEAM_SHARED
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
    # closes the seam — plus the whole-station phase the closure carries so its
    # penetrations land between the opening ones, and up to a column width
    # because start and end may sit on opposite rails.
    slack = machine.BORDER_CLOSURE_OVERLAP_MM + machine.BORDER_DENSITY_MM / 2 \
        + machine.BORDER_WIDTH_MM / 2
    assert math.dist(pts[0], pts[-1]) <= slack + 0.1


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


# --- The review wave: closure phase, meta carry, corner bite ----------------

def test_closing_penetrations_avoid_their_own_rails_holes():
    """Regression, from adversarial review: the closing overlap was phased by
    HALF a station, but stations alternate rails, so same-rail holes sit two
    stations apart and the half shift put every closing penetration a
    quarter-pitch (0.11 mm — inside the same-hole radius) from an existing
    hole on its own rail. The whole-station phase lands each closing cross at
    an opposite-rail opening's position instead: 0.225 mm, dead midway, from
    the nearest own-rail hole."""
    runs, _ = _runs(SQUARE)
    pts = [r.points for r in runs if r.kind == "border"][0]
    extra = int(machine.BORDER_CLOSURE_OVERLAP_MM / (machine.BORDER_DENSITY_MM / 2))
    assert extra >= 4, "fixture too small to exercise the closure"
    opening, closing = pts[:len(pts) - extra], pts[len(pts) - extra:]
    for gi in range(len(pts) - extra, len(pts)):
        c = pts[gi]
        same_rail = [p for j, p in enumerate(opening) if j % 2 == gi % 2]
        dmin = min(math.dist(c, p) for p in same_rail)
        assert dmin >= 0.2, \
            f"closing penetration {gi} lands {dmin:.3f} mm from an own-rail hole"


def test_border_intent_survives_a_redigitize():
    """Regression, from adversarial review: config.py promises the per-shape
    override 'rides the existing match_shape_ids carry-forward', but the match
    copied only the id and stage 4 rebuilds meta each generation — so a
    review-screen border decision silently reverted on every re-digitize."""
    from digitizer_core.regions import Region, match_shape_ids

    def region(sid, dx=0.0, **meta):
        poly = Polygon([(dx, 0), (10 + dx, 0), (10 + dx, 4), (dx, 4)])
        return Region(shape_id=sid, polygon=poly, thread_index=0,
                      thread_number="1", area_mm2=poly.area,
                      meta={"layer": 0, **meta})

    prev = [region("S_kept", border=False)]
    cur = [region("S_new", dx=0.3)]          # same art, nudged a hair
    match_shape_ids(prev, cur)
    assert cur[0].shape_id == "S_kept"
    assert cur[0].meta.get("border") is False, \
        "the operator's border decision must ride the id carry-forward"
    assert cur[0].meta["layer"] == 0, "pipeline facts stay the new generation's"


def test_corner_rounding_never_bites_deeper_than_half_a_column():
    """Regression, from adversarial review: the uncapped relaxation's fixed
    point on a spike-sharp star tip sat 1.85 mm inside it (its docstring
    claimed 0.66) — the outline visibly cut every corner off while the fill
    reached the true apex. Capped, a tip retreats at most about half a border
    width plus one sampling step, which stays inside the column's own thread."""
    from digitizer_core.stage6_border import round_inward

    for size in (24.0, 12.0):
        half = size / 2
        tips = []
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5
            rad = half if i % 2 == 0 else size / 5
            pts.append((rad * math.cos(ang), rad * math.sin(ang)))
            if i % 2 == 0:
                tips.append(pts[-1])
        star = Polygon(pts)
        rounded = round_inward(star, machine.BORDER_CORNER_RADIUS_MM,
                               machine.BORDER_DENSITY_MM / 2)
        for t in tips:
            bite = Point(t).distance(rounded)
            assert bite <= machine.BORDER_WIDTH_MM / 2 + 0.15, \
                f"{size} mm star tip bitten {bite:.2f} mm"


# --- The seam-sharing mitigation (KNOWN LIMITATION, detect-and-warn only) --

_SEAM_FABRIC = fabric_for_garment("left_chest")  # pique knit, 0.3 mm pull comp


def _seam_bar(x0: float, x1: float, layer: int, thread: int, name: str,
             border) -> Region:
    # Forced to "fill", same reasoning as test_chaining's fixtures: "auto"
    # would let the classifier decide satin vs fill per rectangle aspect
    # ratio, which has nothing to do with what this test measures.
    poly = Polygon([(x0, 0), (x1, 0), (x1, 10), (x0, 10)])
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=f"{1000 + thread}", area_mm2=poly.area,
                  meta={"layer": layer, "tier": "fill", "border": border})


def _seam_plan(regions):
    conf = PipelineConfig()
    planned, _ = resolve_overlaps(regions, _SEAM_FABRIC, conf)
    return sequence(planned, _SEAM_FABRIC, conf)


def test_border_seam_shared_names_both_shapes_when_two_bordered_shapes_abut():
    """Two different-colour rectangles sharing the edge x=10, both bordered.

    Stage 5 gives the earlier colour's underlap tongue back to the later one
    (`grown.difference(earlier)` / `visible.difference(later)`), so both
    shapes' VISIBLE edges land on the identical x=10 line — the exact
    coincidence `stage6_border`'s KNOWN LIMITATION describes. The 10 mm shared
    run is well past the 2 x BORDER_WIDTH_MM (2.8 mm) threshold.
    """
    regions = [_seam_bar(0, 10, 0, 0, "Sleft", True),
              _seam_bar(10, 20, 1, 1, "Sright", True)]
    _blocks, warnings = _seam_plan(regions)

    hits = [w for w in warnings if w["code"] == BORDER_SEAM_SHARED]
    assert len(hits) == 1, f"expected one BORDER_SEAM_SHARED finding, got {warnings}"
    assert hits[0]["count"] == 1
    pair = {tuple(sorted(p)) for p in hits[0]["pairs"]}
    assert pair == {("Sleft", "Sright")}, \
        "the finding must name both shapes on the shared seam"


def test_border_seam_shared_does_not_fire_without_abutment_or_border():
    """Negative case, two ways: a real gap between the shapes, and the seam
    intact but border turned off. Neither is the defect the warning exists
    for, so neither may fire it."""
    gap = [_seam_bar(0, 10, 0, 0, "Sleft", True),
          _seam_bar(16, 26, 1, 1, "Sright", True)]   # 6 mm gap, not abutting
    _blocks, gap_warnings = _seam_plan(gap)
    assert not [w for w in gap_warnings if w["code"] == BORDER_SEAM_SHARED]

    off = [_seam_bar(0, 10, 0, 0, "Sleft", False),
          _seam_bar(10, 20, 1, 1, "Sright", False)]  # abutting, border off
    _blocks, off_warnings = _seam_plan(off)
    assert not [w for w in off_warnings if w["code"] == BORDER_SEAM_SHARED]
