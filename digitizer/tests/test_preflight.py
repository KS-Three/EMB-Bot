"""Preflight — the report an operator reads before the machine sews.

Two kinds of test, deliberately. The synthetic-plan tests hand the scorer a
StitchPlan built to embody exactly one defect, because each threshold is a
measured number and the test should show the measurement tripping it. The
fixture tests run the real pipeline output through the real scorer, holding
the one promise every metric here was validated against first: a clean plan
earns a clean report. A metric that flags clean work trains the operator to
ignore the report — that failure mode has already cost this project once.
"""
from __future__ import annotations

import json
import math

import cv2
import numpy as np
import pytest

from digitizer_core import machine

from digitizer_core import (PipelineConfig, StitchBlock, StitchPlan,
                            StitchRun, machine, run_stages)
from digitizer_core import stitches as st
# The module object, not its names: the uncovered-artwork test monkeypatches
# `_prune_spurs` to re-create the defect the check was built against.
from digitizer_core import stage6_satin
from digitizer_core.pipeline import digitize, plan_stitches
from digitizer_core.preflight import (
    ARTWORK_UNCOVERED,
    CLASS_OVERRIDE_TECHNIQUE_MISMATCH,
    COLOR_STOPS_HEAVY,
    COLOR_STOPS_MAX,
    CONTOUR_STARVED,
    DELTA_E_CLEARLY_DIFFERENT,
    DELTA_E_VISIBLE,
    DENSITY_EXTREME,
    DENSITY_STACKED,
    LETTERING_TOO_SMALL,
    LINK_UNCOVERED,
    PHOTO_MIN_PX_PER_MM,
    PHOTO_RESOLUTION_LOW,
    SAME_HOLE_HEAVY,
    STABILIZER_CUTAWAY,
    STITCHES_CUTAWAY_MIN,
    STITCHES_TOO_LONG,
    STITCHES_TOO_SHORT,
    SUBJECT_CONTRAST_LOW,
    SUBJECT_DELTA_L_MIN,
    THREAD_MATCH_POOR,
    TRIM_HEAVY,
    _CONTOUR_RING_UNREACHABLE,
    _PHOTO_TONAL_TECHNIQUES,
    _TONAL_FILL_BAND_MM,
    _coverage_map,
    run_preflight,
)
from tests.conftest import PLAN_CFG_KW, TESTDATA, cfg

ART = TESTDATA / "logo_whitebg.png"
PHOTO = TESTDATA / "photo"

PHOTO_GUARD_CODES = {PHOTO_RESOLUTION_LOW, SUBJECT_CONTRAST_LOW,
                     STABILIZER_CUTAWAY, COLOR_STOPS_HEAVY}


def _plan(*runs: StitchRun) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="1704",
                        rgb=(230, 60, 60), runs=list(runs))
    return StitchPlan(blocks=[block], palette=[])


def _satin_column(crosses: int, width_mm: float, spacing_mm: float,
                  shape_id: str = "S1") -> StitchRun:
    """A straight zigzag column: rails alternate A, B, A, B."""
    pts = []
    for i in range(crosses):
        pts.append((i * spacing_mm, 0.0))
        pts.append((i * spacing_mm, width_mm))
    return StitchRun(points=pts, kind=st.SATIN, shape_id=shape_id)


def _codes(report: dict) -> set[str]:
    return {f["code"] for f in report["findings"]}


# --- A clean plan earns a clean report --------------------------------------

def test_a_clean_real_plan_earns_a_clean_report(whitebg, plan):
    """The fixture logo, planned by the real pipeline, scores 100 — every
    threshold in the module was validated against this promise first."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW), image=ART)

    assert report["findings"] == []
    assert report["score"] == 100
    assert report["grade"] == "A"
    # And the instruments actually measured, rather than silently skipping.
    m = report["metrics"]
    assert m["thread_match_checked"] is True
    assert m["fill_advance_mm"] == pytest.approx(machine.FILL_ROW_MM, abs=0.05)
    assert m["satin_advance_mm"] == pytest.approx(0.40, abs=0.05)
    assert m["satin_short_fraction"] < 0.25
    # Law 27's region sum measured, and comfortably inside its budget.
    # Re-measured 2026-08-05 after corpus laws 23/26 landed: pique_knit's
    # fill_underlay dropped its crosshatch-lattice pass (edge_lattice ->
    # edge_run), so a clean single-layer fill now reads the geometric ideal
    # of 1.00 rather than the old lattice-inflated 1.20.
    # One engine-density fill is one FILL LAYER (2.67 physical units since
    # 2026-09-03 -- see COVERAGE_FILL_LAYER_UNITS).
    assert m["coverage_p50"] == pytest.approx(machine.COVERAGE_FILL_LAYER_UNITS, abs=0.15)
    assert m["coverage_over_warn_mm2"] == 0.0
    assert m["same_hole_fraction"] is not None
    # Chaining law 60 and the contour tier, both measured rather than skipped.
    # Re-measured 2026-08-02 after the fill-axis geometry fix (stage6_fill.py,
    # commit c9556ae): rows now run the shape's true long axis instead of a
    # spurious diagonal, which changes both the fill geometry chaining routes
    # around and the travel distance between shapes -- 99.4->109.0 mm needle-
    # down, and, apparently for the better on this fixture, the previously
    # 0.40 mm of bare link exposure is now fully covered (0.0). Same fix
    # already re-pinned GOLDEN_FLAG_OFF and the flat-lane golden elsewhere in
    # this suite; this is that same blast radius, not a new defect.
    # Re-measured again 2026-08-05 after corpus laws 23/26: removing
    # pique_knit's crosshatch-lattice underlay pass (law 26) and widening
    # satin's own zigzag underlay legs (law 23) both move geometry the
    # travel graph routes around, dropping needle-down link distance
    # 109.0 -> 87.8 mm. Link coverage itself is unaffected (still 0.0 mm
    # bare).
    # Re-pinned 2026-08-11: the link instrument now scores BETWEEN-shape
    # transport only (hardening closeout 2026-08-02 finding 4 -- a fill's own
    # row-skip travel is not a chain link). The 87.8 mm this plan used to
    # report was all stage 6 internal routing; with chaining off nothing here
    # sews shape-to-shape needle-down, so the honest reading is zero. The
    # chain-on measurement lives in
    # test_the_real_fixture_leaves_no_link_on_bare_fabric.
    assert m["link_segments"] == 0
    assert m["link_thread_mm"] == 0.0
    assert m["link_uncovered_max_mm"] == pytest.approx(0.0, abs=0.05)
    assert m["fill_axis_concentration"] == pytest.approx(0.974, abs=0.02)
    assert m["contour_starved_shapes"] == 0
    # The photo-guardrail instruments measured too (photo plan §2 row 15):
    # the fixture sits UNDER the 10 px/mm photo floor and nothing fires,
    # because it is flat art and the floor is a photo-class fact — the
    # measured table at PHOTO_MIN_PX_PER_MM is exactly this number.
    assert m["input_px_per_mm"] == pytest.approx(8.39, abs=0.05)
    assert m["input_px_per_mm"] < PHOTO_MIN_PX_PER_MM
    assert m["subject_bg_delta_l"] == pytest.approx(59.2, abs=0.5)
    assert m["color_changes"] == 4


# --- Thread color fidelity ---------------------------------------------------

def test_madeira_fires_on_the_purple_and_isacord_does_not(whitebg):
    """The motivating case: Madeira Rayon's nearest thread to the fixture's
    purple is deltaE00 ~10.7 (12.2 by the step-8 probe) — visibly a different
    color, and silent before this module existed. Isacord matches everything
    on the same art within 4.4 and must stay silent, or the warning is noise.

    The empty plan is deliberate: only the thread check needs the artwork,
    and skipping stages 5-7 keeps the test at run_stages cost.
    """
    empty = StitchPlan(blocks=[], palette=[])

    mad_cfg = cfg(thread_brand="madeira-rayon")
    mad = run_preflight(run_stages(ART, mad_cfg), empty, mad_cfg, image=ART)
    purple = [f for f in mad["findings"]
              if f["code"] == THREAD_MATCH_POOR
              and f["extra"]["thread_number"] == "1033"]
    assert purple, "the deltaE ~12 purple substitution must be surfaced"
    assert purple[0]["severity"] == "block"
    assert purple[0]["extra"]["delta_e"] > DELTA_E_CLEARLY_DIFFERENT

    iso = run_preflight(whitebg, empty, cfg(), image=ART)
    assert THREAD_MATCH_POOR not in _codes(iso)


def test_without_the_artwork_the_thread_check_is_skipped_and_says_so(whitebg):
    """A stored plan may outlive its artwork; the report must distinguish
    'checked and clean' from 'never checked'."""
    report = run_preflight(whitebg, StitchPlan(blocks=[], palette=[]), cfg())

    assert THREAD_MATCH_POOR not in _codes(report)
    assert report["metrics"]["thread_match_checked"] is False
    assert report["metrics"]["thread_worst_delta_e"] is None


def test_a_bimodal_thread_is_judged_by_its_worst_region_not_the_pool():
    """THE trap this instrument used to fall into, twice in one day (docs/
    photo-quality-root-cause-2026-08-11.md): two regions share one spool,
    the bigger sits exactly on the spool's colour and the smaller is a
    different colour entirely. Pooled, the bigger region's pixels own the
    per-channel median, the pool scores CLEAN, and the old instrument was
    silent — worse, a verified per-region fix moved its number the wrong way
    (drone_render's pooled worst read 9.2 -> 33.6 across stage 4's thread
    revalidation, which HALVED the honest per-region worst, 20.99 -> 10.64).
    Per-region, the bad region is a block finding that names itself."""
    from types import SimpleNamespace

    from shapely.geometry import Polygon
    from skimage.color import deltaE_ciede2000

    from digitizer_core.regions import Region
    from digitizer_core.stage1_prep import prep
    from digitizer_core.threads import chart_for, rgb_to_lab

    c = cfg()
    chart = chart_for(c)
    spool_i = chart.nearest_index(rgb_to_lab(np.array([[230, 60, 60]]))[0])
    spool_rgb = chart[spool_i].rgb
    off_rgb = (60, 60, 230)   # a blue no red spool is anywhere near

    # White background; the big rect painted EXACTLY the spool's colour, at
    # 4x the pixels of the small rect painted far off it — so the pooled
    # per-channel median IS the spool colour and the pool hides the defect
    # by construction. BGR, the ndarray-input convention (stage1_prep._load
    # treats an ndarray as cv2-decoded).
    img = np.full((400, 500, 3), 255, np.uint8)
    img[40:240, 60:260] = spool_rgb[::-1]
    img[80:180, 320:420] = off_rgb[::-1]
    p = prep(img, c)

    x0, y0, x1, y1 = p.art_bbox
    px_cx, px_cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    def rect_mm(px0, py0, px1, py1) -> Polygon:
        """A pixel rect as the mm polygon preflight rasterizes back over it
        (origin art-bbox center, y-down), inset 2 px so the eroded mask
        stays inside the painted colour."""
        corners = [(px0 + 2, py0 + 2), (px1 - 2, py0 + 2),
                   (px1 - 2, py1 - 2), (px0 + 2, py1 - 2)]
        return Polygon([((x - px_cx) / p.px_per_mm, (y - px_cy) / p.px_per_mm)
                        for x, y in corners])

    def region(shape_id: str, poly: Polygon) -> Region:
        return Region(shape_id=shape_id, polygon=poly, thread_index=spool_i,
                      thread_number=chart[spool_i].number,
                      area_mm2=float(poly.area))

    result = SimpleNamespace(regions=[region("Sgood", rect_mm(60, 40, 260, 240)),
                                      region("Sbad", rect_mm(320, 80, 420, 180))])
    report = run_preflight(result, StitchPlan(blocks=[], palette=[]), c, image=img)

    # The pool really is blind here — asserted, not narrated: the per-channel
    # median over both regions' pixels is the spool's own colour, delta-E ~0.
    pooled = np.median(np.concatenate([
        np.tile(spool_rgb, (200 * 200, 1)), np.tile(off_rgb, (100 * 100, 1))
    ]), axis=0)
    pooled_de = float(deltaE_ciede2000(
        rgb_to_lab(pooled.reshape(1, 3)),
        rgb_to_lab(np.asarray(spool_rgb, np.float64).reshape(1, 3)))[0])
    assert pooled_de < DELTA_E_VISIBLE

    hit = [f for f in report["findings"] if f["code"] == THREAD_MATCH_POOR]
    assert len(hit) == 1
    assert hit[0]["severity"] == "block"
    assert hit[0]["extra"]["delta_e"] > DELTA_E_CLEARLY_DIFFERENT
    assert hit[0]["extra"]["worst_shape_id"] == "Sbad"
    assert "Sbad" in hit[0]["message"]
    assert hit[0]["extra"]["region_count"] == 1
    assert hit[0]["extra"]["regions_scored"] == 2
    assert hit[0]["extra"]["regions"] == [
        {"shape_id": "Sbad", "delta_e": hit[0]["extra"]["delta_e"]}]
    # The worst-region number rides out as the metric to watch.
    assert report["metrics"]["thread_worst_delta_e"] == hit[0]["extra"]["delta_e"]
    json.dumps(report)


# --- Lettering size ----------------------------------------------------------

def test_satin_below_sewable_lettering_size_is_flagged():
    """House sew-out fact: stacked text below ~4 mm cap height dies at hat
    scale, and Hatch's own font ranges bottom out at 5 mm. A 3 mm shape of
    0.8 mm columns is both too small overall and too thin per stroke."""
    tiny = _plan(_satin_column(8, width_mm=0.8, spacing_mm=0.4))
    report = run_preflight(None, tiny, cfg())

    flagged = [f for f in report["findings"] if f["code"] == LETTERING_TOO_SMALL]
    assert len(flagged) == 1
    assert flagged[0]["extra"]["count"] == 1
    assert flagged[0]["extra"]["shapes"][0]["shape_id"] == "S1"


def test_lettering_too_small_reports_the_denominator_not_a_target_size():
    """The count needs its denominator, and must NOT quote a suggested width.

    "38 satin shapes are too small" reads like specks to trim; "38 of 46" says
    the wordmark does not fit. The denominator is also the only summary that
    survives rescaling — measured on `logo_hotel_fremont` at 92.5/120/165/220
    mm, the flagged count falls 38 -> 13 while the median flagged column stays
    flat near 0.8 mm, because segmentation regenerates sub-millimetre shapes
    as the design grows. A worst-shape-derived "enlarge to N mm" swings
    258 -> 697 -> 397 mm over that same sweep, so this check must not offer
    one; asserting its absence is what keeps a future edit from adding it back
    without a stable measurement behind it.
    """
    tiny = _plan(_satin_column(8, width_mm=0.8, spacing_mm=0.4),
                 _satin_column(30, width_mm=2.5, spacing_mm=0.4, shape_id="S2"))
    report = run_preflight(None, tiny, cfg())

    flagged = [f for f in report["findings"] if f["code"] == LETTERING_TOO_SMALL]
    assert len(flagged) == 1
    extra = flagged[0]["extra"]
    assert extra["count"] == 1            # only the 0.8 mm column fails
    assert extra["satin_total"] == 2      # ...out of two satin shapes
    assert "1 of 2 satin shape" in flagged[0]["message"]
    # No fabricated target size, in the message or the payload.
    assert "needed_width_mm" not in extra
    assert "mm of design width" not in flagged[0]["message"]


def test_a_healthy_column_is_not_lettering_too_small():
    healthy = _plan(_satin_column(30, width_mm=2.5, spacing_mm=0.4))
    assert LETTERING_TOO_SMALL not in _codes(run_preflight(None, healthy, cfg()))


# --- Stitch length -----------------------------------------------------------

def test_the_dst_ceiling_backstop_reports_a_stitch_the_planner_missed():
    """The planner splits long moves at the source, so any step past 12.1 mm
    is a regression the operator should hear about before the export quietly
    papers over it."""
    plan = _plan(StitchRun(points=[(0.0, 0.0), (15.0, 0.0)], kind=st.FILL))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == STITCHES_TOO_LONG]
    assert len(hit) == 1
    assert hit[0]["extra"]["count"] == 1
    assert hit[0]["extra"]["max_mm"] == pytest.approx(15.0, abs=0.01)


def test_a_regressed_satin_short_fraction_warns():
    """The benchmark measured 54.6% of satin stitches under the needle
    minimum before the zigzag-order fix and ~10% after; 25% is the tripwire
    halfway back to the broken world. Every cross of a 0.7 mm column is
    under the minimum, which is exactly the geometry that regression made."""
    regressed = _plan(_satin_column(40, width_mm=0.7, spacing_mm=0.4))
    report = run_preflight(None, regressed, cfg())

    hit = [f for f in report["findings"] if f["code"] == STITCHES_TOO_SHORT]
    assert len(hit) == 1
    assert hit[0]["extra"]["fraction"] > 0.25

    healthy = _plan(_satin_column(40, width_mm=2.5, spacing_mm=0.4))
    assert STITCHES_TOO_SHORT not in _codes(run_preflight(None, healthy, cfg()))


# --- Trims -------------------------------------------------------------------

def _rows(n_runs: int, pts_per_run: int, trim_from: int | None) -> list[StitchRun]:
    """n straight fill rows, 2 mm steps; runs from `trim_from` on are cut."""
    runs = []
    for r in range(n_runs):
        pts = [(2.0 * i, 3.0 * r) for i in range(pts_per_run)]
        runs.append(StitchRun(points=pts, kind=st.FILL,
                              trim=(r == 0 or (trim_from is not None and r >= trim_from)),
                              jump=True))
    return runs


def test_trim_heavy_measures_the_file_not_the_plan():
    """The plan marks the first run trimmed but the machine has no thread to
    cut yet — the corrected rate must read zero for a design that never cuts,
    and fire once real cuts pass the corpus's 4.1 per 1,000."""
    never_cuts = _plan(*_rows(4, 10, trim_from=None))
    report = run_preflight(None, never_cuts, cfg())
    assert TRIM_HEAVY not in _codes(report)
    assert report["metrics"]["trims_per_1000"] == 0.0

    scissors = _plan(*_rows(10, 10, trim_from=1))
    report = run_preflight(None, scissors, cfg())
    hit = [f for f in report["findings"] if f["code"] == TRIM_HEAVY]
    assert len(hit) == 1
    assert hit[0]["extra"]["trims"] == 9
    assert hit[0]["extra"]["per_1000"] > 4.1


# --- Density -----------------------------------------------------------------

def test_sparse_fill_rows_are_density_extreme():
    """Rows advancing 1.0 mm against the FILL_ROW_MM target (0.15 since
    2026-09-03, so 6.7x sparse) — bare fabric grinning through the coverage."""
    pts: list[tuple[float, float]] = []
    for row in range(34):
        xs = [0.0, 2.0, 4.0, 6.0, 8.0]
        if row % 2:
            xs.reverse()
        pts.extend((x, row * 1.0) for x in xs)
    plan = _plan(StitchRun(points=pts, kind=st.FILL))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert hit[0]["extra"]["kind"] == "fill"
    assert hit[0]["extra"]["ratio"] == pytest.approx(1.0 / machine.FILL_ROW_MM, abs=0.2)


def test_overdense_satin_is_density_extreme():
    """Same-rail advance 0.15 mm against the 0.40 spacing packs 2.7x the
    thread into the column — puckered fabric and needle heat."""
    plan = _plan(_satin_column(45, width_mm=2.0, spacing_mm=0.15))
    report = run_preflight(None, plan, cfg())

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert hit[0]["extra"]["kind"] == "satin"
    assert hit[0]["extra"]["ratio"] < 1.0


def test_a_deliberate_density_override_is_not_extreme():
    """The comparison target mirrors stage 7's own formula, so an operator
    who ASKED for 1.0 mm rows must not be warned about getting them."""
    pts: list[tuple[float, float]] = []
    for row in range(34):
        xs = [0.0, 2.0, 4.0, 6.0, 8.0]
        if row % 2:
            xs.reverse()
        pts.extend((x, row * 1.0) for x in xs)
    plan = _plan(StitchRun(points=pts, kind=st.FILL))
    report = run_preflight(None, plan, cfg(fill_row_mm=1.0))

    assert DENSITY_EXTREME not in _codes(report)


# --- Density: the tonal fill band --------------------------------------------

def _tonal_rows(advance_mm: float, tier: str | None = None) -> StitchPlan:
    """Boustrophedon fill rows `advance_mm` apart — the sparse-fill test's
    own geometry, with rows long enough (32 mm) that even 6.0 mm advances
    clear the axis gate (|R| = (32-6)/(32+6) = 0.68 vs the 0.6 floor).
    `tier` appends the run_stages PHOTO_AUTO_TIER warning the auto route
    publishes, extras flattened at top level exactly as warnings_codes.warn
    emits them."""
    pts: list[tuple[float, float]] = []
    for row in range(34):
        xs = [2.0 * i for i in range(17)]
        if row % 2:
            xs.reverse()
        pts.extend((x, row * advance_mm) for x in xs)
    plan = _plan(StitchRun(points=pts, kind=st.FILL))
    if tier is not None:
        plan.warnings.append({"code": "photo_auto_tier", "tier": tier,
                              "streamline_mode": "layered"})
    return plan


def test_the_photo_auto_routes_own_spacing_is_not_density_extreme():
    """The 2026-08-23 defect (debug_out/acceptance_2026-08-23): the photo
    auto-route sews streamline lines ~1.7 mm apart — inside the tier's own
    0.8-3.2 mm tone band — and the fill check, scoring against the 0.40 mm
    tatami target, told every toggle-route user to re-digitize ("4.3x its
    0.40 mm density target", warn, on a real portrait). The pipeline's own
    deliberate tier choice must not trip its own density check."""
    report = run_preflight(None, _tonal_rows(1.7, tier="streamline"), cfg())

    assert DENSITY_EXTREME not in _codes(report)
    # The instrument still measured — the metric rides out either way.
    assert report["metrics"]["fill_advance_mm"] == pytest.approx(1.7, abs=0.01)


def test_an_explicit_tonal_technique_gets_the_same_band():
    """`fill_technique="streamline"` set by hand is the same intent stated
    the other way — no auto-route warning exists to re-read, so the band
    must come off cfg alone."""
    report = run_preflight(None, _tonal_rows(1.7),
                           cfg(fill_technique="streamline"))

    assert DENSITY_EXTREME not in _codes(report)


def test_a_collapsed_tonal_fill_still_warns():
    """Rescored, not silenced: 6.0 mm between lines is past even the
    lightest spacing streamline intends (3.2 mm) by more than the 1.5x
    slack — a genuinely broken tonal fill keeps its warning, scored
    against the edge it violated."""
    report = run_preflight(None, _tonal_rows(6.0, tier="streamline"), cfg())

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert hit[0]["extra"]["kind"] == "fill"
    assert hit[0]["extra"]["technique"] == "streamline"
    assert hit[0]["extra"]["target_mm"] == pytest.approx(3.2)
    assert hit[0]["extra"]["ratio"] == pytest.approx(6.0 / 3.2, abs=0.01)


def test_a_tonal_designs_tatami_fallback_rows_are_not_extreme():
    """Stage 7's never-drop ladder sews plain tatami rows inside a tonal
    design wherever a shape came back empty — at the tatami target, denser
    than streamline's own 0.8 mm dark edge. The band is widened by that
    target so the fallback's correct density never reads as matting."""
    report = run_preflight(None, _tonal_rows(0.4, tier="streamline"), cfg())

    assert DENSITY_EXTREME not in _codes(report)


def test_an_explicit_technique_outranks_a_stale_auto_tier_warning():
    """Stage 7 re-resolves `auto_tier or cfg.fill_technique` on every
    re-plan, so an explicit non-tonal technique sews tatami-target rows
    even when the plan still carries the original run's auto-route warning
    — and the check must score it against the tatami target too."""
    report = run_preflight(None, _tonal_rows(1.7, tier="streamline"),
                           cfg(fill_technique="crosshatch"))

    hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
    assert len(hit) == 1
    assert "technique" not in hit[0]["extra"]
    assert hit[0]["extra"]["ratio"] == pytest.approx(1.7 / machine.FILL_ROW_MM, abs=0.05)


def _interleaved_shade_layers(n: int = 4, side_mm: float = 14.0, stamped: bool = True):
    """`n` blend-style layers of one square, each at FILL_ROW_MM * n and offset
    by one row from the last, so the union sits exactly at FILL_ROW_MM."""
    runs = []
    for i in range(n):
        pts = []
        y = -side_mm / 2 + i * machine.FILL_ROW_MM
        row = 0
        while y <= side_mm / 2:
            xs = [-side_mm / 2 + 2.0 * k for k in range(int(side_mm / 2.0) + 1)]
            if row % 2:
                xs.reverse()
            pts.extend((x, y) for x in xs)
            y += machine.FILL_ROW_MM * n
            row += 1
        runs.append(StitchRun(points=pts, kind=st.FILL, shape_id=f"S1-blend{i}",
                              shade_thread_index=(i if stamped else None)))
    return _plan(*runs)


def _shade_bands(n: int = 4, side_mm: float = 14.0):
    """`n` blend-style bands of one square, each a horizontal slice sewn at
    the fill row — what `stage6_blend._emit_bands` puts down since 2026-09-03."""
    runs = []
    band_h = side_mm / n
    for i in range(n):
        pts = []
        y = -side_mm / 2 + i * band_h
        row = 0
        while y <= -side_mm / 2 + (i + 1) * band_h:
            xs = [-side_mm / 2 + 2.0 * k for k in range(int(side_mm / 2.0) + 1)]
            if row % 2:
                xs.reverse()
            pts.extend((x, y) for x in xs)
            y += machine.FILL_ROW_MM
            row += 1
        runs.append(StitchRun(points=pts, kind=st.FILL, shape_id=f"S1-blend{i}",
                              shade_thread_index=i))
    return _plan(*runs)


def test_blend_shade_bands_at_the_fill_row_read_clean():
    report = run_preflight(None, _shade_bands(4), cfg())

    assert DENSITY_EXTREME not in _codes(report)
    assert report["metrics"]["fill_advance_mm"] == pytest.approx(machine.FILL_ROW_MM, abs=0.01)


def test_blend_shade_layers_are_judged_like_any_fill():
    """PR #339 (2026-09-03) exempted runs stamped `shade_thread_index` from
    this reader on the premise that n interleaved layers at n times the row
    union to the row. The premise was false — the bands were disjoint, each
    a sparse layer on its own — and the exemption hid exactly the cloth
    between rows the sew-out showed. Gone the same day the bands moved to
    the fill row: the old layout, stamped or not, is 4x sparse and says so."""
    for stamped in (True, False):
        report = run_preflight(None, _interleaved_shade_layers(4, stamped=stamped), cfg())
        hit = [f for f in report["findings"] if f["code"] == DENSITY_EXTREME]
        assert len(hit) == 1, stamped
        assert hit[0]["extra"]["ratio"] == pytest.approx(4.0, abs=0.1)


def test_the_band_table_stays_in_lockstep_with_the_technique_gate():
    """_TONAL_FILL_BAND_MM and _PHOTO_TONAL_TECHNIQUES answer for the same
    tier set — one is the class-override gate, the other the density
    yardstick. A tier added to one and not the other fails here instead of
    quietly keeping the tatami yardstick."""
    assert set(_TONAL_FILL_BAND_MM) == set(_PHOTO_TONAL_TECHNIQUES)


# --- Per-region coverage (law 27) --------------------------------------------

def _square_fill(side_mm: float = 14.0,
                 spacing_mm: float = machine.FILL_ROW_MM,
                 shape_id: str = "F1") -> StitchRun:
    """A boustrophedon fill of one square, rows `spacing_mm` apart.

    Rows run 2 mm per stitch, which is what stage 6 emits; the square is big
    enough (14 mm) that a stacked patch clears law 27's 5x5 mm floor.
    """
    pts: list[tuple[float, float]] = []
    row, y = 0, -side_mm / 2
    while y <= side_mm / 2:
        xs = [-side_mm / 2 + 2.0 * i for i in range(int(side_mm / 2.0) + 1)]
        if row % 2:
            xs.reverse()
        pts.extend((x, y) for x in xs)
        y += spacing_mm
        row += 1
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _stacked(layers: int) -> StitchPlan:
    """The same square filled `layers` times — one patch, N full layers."""
    return _plan(*(_square_fill(shape_id=f"F{i}") for i in range(layers)))


def test_one_full_density_fill_measures_exactly_one_covering_layer():
    """The instrument's zero point. Law 16: 40wt thread is 0.4 mm wide, so
    rows at the 0.40 mm default sit edge to edge and ARE one full covering
    layer. If this reads anything but 1.0, every threshold above is nonsense.
    """
    one_layer = _plan(_square_fill(spacing_mm=machine.COVERAGE_THREAD_W_MM))
    m = run_preflight(None, one_layer, cfg())["metrics"]

    assert m["coverage_p50"] == pytest.approx(1.0, abs=0.02)
    assert m["coverage_max"] == pytest.approx(1.0, abs=0.05)

    # And one fill at the engine's own pitch (0.15 since 2026-09-03) reads
    # exactly the fill-layer factor the thresholds are stated in.
    m = run_preflight(None, _stacked(1), cfg())["metrics"]
    assert m["coverage_p50"] == pytest.approx(machine.COVERAGE_FILL_LAYER_UNITS, abs=0.05)


def test_a_satin_column_counts_one_layer_per_same_rail_advance():
    """Law 27's unit for satin is 0.4 / SAME-RAIL advance, so a column at the
    0.40 mm default is ONE layer. A zigzag lays two legs between consecutive
    same-rail penetrations, so counting raw thread would read 2.0 here and
    would score the playbook's own 'safe classic stack' at 3.2 instead of
    2.5 — flagging the arrangement law 27 calls safe.
    """
    column = _plan(_satin_column(60, width_mm=4.0, spacing_mm=0.4))
    m = run_preflight(None, column, cfg())["metrics"]

    assert m["coverage_p50"] == pytest.approx(1.0, abs=0.1)
    assert DENSITY_STACKED not in _codes(run_preflight(None, column, cfg()))


def test_underlay_is_charged_to_the_budget_not_ignored():
    """Law 28: underlay costs ~0.1-0.2 coverage units — cheap, but not zero,
    and law 27's region sum includes it. A zigzag underlay at the 2.0 mm
    house spacing must price at 0.4 / 2.0 = 0.20, the top of law 28's band,
    derived from the stitch geometry alone rather than assumed.

    Asserted areally, over the band the underlay sweeps, because that is the
    figure law 28 quotes. A percentile would answer a different question: at
    2.0 mm the zigzag is coarser than a 1.0 mm cell, so the map resolves its
    individual legs (0.4 on a leg, less between) instead of averaging them —
    correct, and not what "0.1-0.2 units" means.
    """
    crosses = 40
    zig = _satin_column(crosses, width_mm=6.0,
                        spacing_mm=machine.UNDERLAY_ZIGZAG_MM, shape_id="U1")
    zig.kind = st.UNDERLAY
    grid, _origin = _coverage_map(_plan(zig))

    swept_mm2 = 6.0 * (crosses - 1) * machine.UNDERLAY_ZIGZAG_MM
    laid = float(grid.sum()) * machine.COVERAGE_CELL_MM ** 2
    assert laid / swept_mm2 == pytest.approx(0.20, abs=0.02)


def test_two_full_density_fills_stay_inside_the_budget():
    """Law 27 permits it in as many words — 'never more than TWO full-density
    fills stacked' — so 2.0 units must not be a finding, or the check
    condemns a legal construction."""
    report = run_preflight(None, _stacked(2), cfg())

    assert report["metrics"]["coverage_p50"] == pytest.approx(2 * machine.COVERAGE_FILL_LAYER_UNITS, abs=0.1)
    assert DENSITY_STACKED not in _codes(report)


def test_a_third_stacked_layer_warns_though_every_object_passes_alone():
    """THE defect this check exists for. Three fills at the correct 0.40 mm
    spacing on one patch of fabric: every per-OBJECT density check passes,
    because each layer is exactly on target — DENSITY_EXTREME compares
    emitted spacing against the planner's own, and 0.40 is the planner's own.
    Only the per-REGION sum sees it. Law 27: 'a third layer means cutting a
    hole in the base'. Measured 3.00 units over 175 mm2.
    """
    report = run_preflight(None, _stacked(3), cfg())

    assert DENSITY_EXTREME not in _codes(report), \
        "the per-object check must be blind to this — that is the defect"
    hit = [f for f in report["findings"] if f["code"] == DENSITY_STACKED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["peak_units"] == pytest.approx(3 * machine.COVERAGE_FILL_LAYER_UNITS, abs=0.15)
    assert hit[0]["extra"]["over_warn_mm2"] > 100.0
    assert hit[0]["extra"]["over_block_mm2"] == 0.0


def test_a_fourth_stacked_layer_blocks():
    """Past 3.5 units the file is not a judgement call. Embrilliance's red
    line is 6 thread layers ~ 3 lockstitch passes and we are over it."""
    hit = [f for f in run_preflight(None, _stacked(4), cfg())["findings"]
           if f["code"] == DENSITY_STACKED]

    assert len(hit) == 1
    assert hit[0]["severity"] == "block"
    assert hit[0]["extra"]["peak_units"] == pytest.approx(4 * machine.COVERAGE_FILL_LAYER_UNITS, abs=0.2)


def test_a_stacked_speckle_too_small_to_act_on_is_not_a_finding():
    """Law 27's remedy stops at 5x5 mm ('no holes under objects < 5x5 mm'),
    and clean work does speckle over 2.5 where satin columns join or a shape
    too small for anything else is rescued with a triple run. Measured on the
    house fixtures, the biggest such speckle is 11 mm2 on the benchmark and
    6 mm2 on the fixture logo. Four stacked layers on a 3 mm square is 9 mm2
    of fabric — over the threshold, under the floor, and silent."""
    report = run_preflight(None, _plan(*(_square_fill(side_mm=3.0, shape_id=f"F{i}")
                                         for i in range(4))), cfg())

    assert report["metrics"]["coverage_max"] > machine.COVERAGE_BLOCK_UNITS
    assert DENSITY_STACKED not in _codes(report)


def test_organic_compact_regions_no_longer_stack_into_a_density_block():
    """Regression pin for the satin/fill classifier fix (`digitizer_core.
    stage6_satin.is_satin_candidate`'s `design_class`-scoped DT check).

    Both committed photo fixtures carry real, near-square, segmentation-noisy
    regions (`region_blobs.png`'s `Sd12bfc9e`/`S94f29987`, `summit_badge.png`'s
    `Sed818ef7`/`S00d736bf`/`S6096e7a9`) that `ribbon_width_mm`'s perimeter-only
    read used to satin — zigzag underlay on a compact blob stacks enough
    thread on the same patch to trip this exact finding. Measured directly
    against this repo's own `PipelineConfig(target_width_mm=60.0,
    garment_id="left_chest")` repro before the fix: `region_blobs.png` blocked
    (`over_block_mm2` 76.0, `peak_units` 10.02) and `summit_badge.png` warned
    (`over_warn_mm2` 247.0); after the fix, neither fixture raises
    `DENSITY_STACKED` at all -- not just a severity step down."""
    for name in ("region_blobs.png", "summit_badge.png"):
        report = _digitize_report(str(PHOTO / name), target_width_mm=60.0,
                                  garment_id="left_chest")
        hit = [f for f in report["findings"] if f["code"] == DENSITY_STACKED]
        assert not hit, f"{name}: still stacks -- {hit}"


def test_a_wide_oversize_satin_stroke_does_not_block_on_underlay_glue(alpha):
    """Regression pin, added 2026-08-05 after an independent stitch-geometry
    audit of the initial corpus law 23 landing (commit `edbd4d4`) caught a
    real defect on `logo_alpha.png`: `DENSITY_STACKED` flipped `warn` ->
    `block` (`coverage_max` 13.11 -> 16.69, `coverage_over_block_mm2` 0.0 ->
    43.0) at `target_width_mm=80`, `garment_id="left_chest"` (also
    reproduced at width 60 and on `hat_front`/`structured_cap` -- a fabric
    law 26 never touches, confirming law 23's zigzag underlay as the cause,
    not law 26's fill change).

    Root cause: `logo_alpha.png` carries shape `Sf5200f3f`, a multi-stroke
    glyph classified satin on its per-shape MEAN width (~5.0mm, right at
    `SATIN_MAX_WIDTH_MM`) while one skeleton stroke's own LOCAL corridor
    runs 0.33-10.33mm -- well past where the corpus ever validated a satin
    zigzag underlay's pitch or width (docs/corpus-laws-round3-2026-08-01.md
    flags its own >7.0mm bucket as 82% non-ribbon junk). The satin crosses
    THEMSELVES already self-overlap there in the unmodified engine
    (`coverage_max` 13.11 pre-law-23 too, confirmed by isolating satin-only
    coverage) -- at the time this test was written, a pre-existing, separate
    defect the underlay fix below did not touch -- sitting just under
    `_COVERAGE_MIN_PATCH_MM2`'s 25mm2 connected-patch gate. Law 23's denser,
    wider zigzag underlay supplied just enough extra "glue" thread to bridge
    that pre-existing near-miss into a real 30-43mm2 connected block patch.

    Fix (`stage6_satin.py::_stroke_underlay`): skip the zigzag pass
    entirely for a stroke whose local width anywhere exceeds
    `SATIN_MAX_WIDTH_MM`, falling back to the center-run walk only --
    the corpus gives no guidance for that regime under EITHER the old or
    the new numbers, so omitting the guess is more honest than extrapolating
    either one. The fixed-up severity is no finding at all (better than the
    pre-law-23 `warn`, not merely restored to it) because the pre-existing
    satin self-overlap alone doesn't reach the connected-patch gate either
    -- asserted directly here rather than assumed.

    UPDATE, same day, separate pass: the satin self-overlap itself is now
    ALSO fixed (`_rail_points`' `SATIN_MAX_WIDTH_MM / 2` per-station cap --
    see its comment and `test_satin.py::
    test_satin_crosses_do_not_self_overlap_across_a_wide_junction` for the
    geometry-level pin). `coverage_max` on this exact fixture/config dropped
    13.11 -> 3.24; the `> 10.0` floor this test used to assert is gone on
    purpose, not a regression -- re-asserted below as a ceiling instead so a
    future junction-cap regression still trips this test."""
    c = cfg(target_width_mm=80.0, garment_id="left_chest")
    report = run_preflight(alpha, plan_stitches(alpha, c), c,
                           image=str(TESTDATA / "logo_alpha.png"))

    hit = [f for f in report["findings"] if f["code"] == DENSITY_STACKED]
    assert not hit, f"must not regress to a DENSITY_STACKED finding: {hit}"
    assert report["metrics"]["coverage_over_block_mm2"] == 0.0
    assert report["metrics"]["coverage_over_warn_mm2"] == 0.0
    # The satin self-overlap that used to hold this peak above 10.0 is fixed
    # (see the docstring UPDATE above) -- pin it low now, not just "not a
    # finding", so a regression in the junction cap shows up here too.
    assert report["metrics"]["coverage_max"] < 5.0


def test_coverage_reads_stitch_geometry_through_ties_and_splits(plan):
    """The playbook's two parity traps, which would double every satin
    number. Stage 7 splices tie bounces INTO the runs they protect and a
    bounce is a 180 deg reversal; split satin inserts mid-cross penetrations
    that make consecutive segments collinear. Either one, unstripped, moves a
    real satin column across the reversal gate and gets it charged at twice
    its density. The fixture's real plan carries both, and its satin still
    prices at one layer."""
    stitch_plan, _planned, _warnings = plan
    m = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))["metrics"]

    # Fill at 0.40 is the classic stack's floor. Re-measured 2026-08-05 after
    # corpus laws 23/26: pique_knit's edge_run underlay (was edge_lattice)
    # contributes almost nothing outside the boundary walk, so the region
    # reads the geometric ideal 1.00 rather than the old lattice-inflated
    # 1.20 (see COVERAGE_WARN_UNITS's derivation comment in machine.py).
    # One fill layer (2.67 physical units at FILL_ROW_MM 0.15, 2026-09-03).
    assert m["coverage_p50"] == pytest.approx(machine.COVERAGE_FILL_LAYER_UNITS, abs=0.15)
    assert m["coverage_p95"] < machine.COVERAGE_WARN_UNITS


# --- Uncovered links (chaining law 60) ---------------------------------------

def _fill_rect(x0: float, y0: float, x1: float, y1: float,
               spacing: float = machine.FILL_ROW_MM,
               shape_id: str = "F") -> StitchRun:
    """A boustrophedon fill of an axis-aligned rectangle, rows `spacing` apart."""
    pts: list[tuple[float, float]] = []
    y, row = y0, 0
    cols = [x0 + 2.0 * i for i in range(int((x1 - x0) / 2.0) + 1)]
    while y <= y1 + 1e-9:
        xs = cols[::-1] if row % 2 else cols
        pts.extend((x, y) for x in xs)
        y += spacing
        row += 1
    return StitchRun(points=pts, kind=st.FILL, shape_id=shape_id)


def _outline_rect(x0: float, y0: float, x1: float, y1: float,
                  shape_id: str = "R") -> StitchRun:
    """The run tier's answer to a small shape: its OUTLINE, nothing inside."""
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    pts: list[tuple[float, float]] = [corners[0]]
    for a, b in zip(corners, corners[1:]):
        n = max(1, int(math.ceil(math.dist(a, b) / machine.BEAN_STITCH_MM)))
        pts.extend((a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                   for i in range(1, n + 1))
    return StitchRun(points=pts, kind=st.RUN, shape_id=shape_id)


def _link_run(a: tuple[float, float], b: tuple[float, float],
              shape_id: str = "L") -> StitchRun:
    """A needle-DOWN link between two shapes, at the chaining law's 2.0 mm."""
    n = max(1, int(math.ceil(math.dist(a, b) / 2.0)))
    return StitchRun(
        points=[(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n)
                for i in range(n + 1)],
        kind=st.TRAVEL, shape_id=shape_id)


def _two_shapes_linked(*later_runs: StitchRun) -> StitchPlan:
    """Two filled squares 12 mm apart, joined by a needle-down link, and
    whatever sews after them in a second colour."""
    first = StitchBlock(thread_index=0, thread_number="1704", rgb=(230, 60, 60),
                        runs=[_fill_rect(-14.0, -4.0, -6.0, 4.0, shape_id="F1"),
                              _link_run((-6.0, 0.0), (6.0, 0.0)),
                              _fill_rect(6.0, -4.0, 14.0, 4.0, shape_id="F2")])
    blocks = [first]
    if later_runs:
        blocks.append(StitchBlock(thread_index=1, thread_number="3902",
                                  rgb=(60, 120, 200), runs=list(later_runs)))
    return StitchPlan(blocks=blocks, palette=[])


def test_a_link_across_bare_fabric_blocks():
    """Chaining declines a trim on the promise the thread will be buried. Here
    nothing buries it: 12 mm of needle-down thread crosses open fabric between
    two squares, which is the float the trim rule exists to cut out, now sewn
    in instead. The limit is the fabric's own trim distance — 3.0 mm on pique
    knit — because that is the number this engine already uses to decide when
    exposed thread may not be left on a garment."""
    report = run_preflight(None, _two_shapes_linked(), cfg())

    hit = [f for f in report["findings"] if f["code"] == LINK_UNCOVERED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "block"
    assert hit[0]["extra"]["limit_mm"] == 3.0
    assert hit[0]["extra"]["max_mm"] == pytest.approx(11.6, abs=0.3)
    # And it names where to look on the garment.
    assert hit[0]["extra"]["at_mm"][1] == pytest.approx(0.0, abs=0.3)


def test_a_link_buried_under_the_next_colour_is_silent():
    """Law 60's main mechanism, and the anti-noise half of the pair: the same
    link under a colour that sews after it is invisible on the finished
    garment, so it must not cost the design a thing."""
    buried = _two_shapes_linked(_fill_rect(-7.0, -3.0, 7.0, 3.0, shape_id="F3"))
    report = run_preflight(None, buried, cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["metrics"]["link_uncovered_max_mm"] == 0.0
    assert report["score"] == 100


def test_the_link_check_reads_laid_thread_not_the_shape_that_claims_to_cover_it():
    """THE defect this instrument exists for, and the known gap in stage 7's
    own test. A link is legal there when its route lies inside the covering
    geometry — POLYGONS — and the run tier sews a small shape's outline and
    nothing else, so its polygon claims cover that no thread provides. Same
    link, same covering shape, same polygon: filled it is buried, outlined it
    is a stray line across bare fabric. Only an instrument that reads the
    stitches can tell those apart, and the difference is the whole finding.
    """
    box = (-7.0, -3.0, 7.0, 3.0)
    filled = run_preflight(None, _two_shapes_linked(
        _fill_rect(*box, shape_id="F3")), cfg())
    outlined = run_preflight(None, _two_shapes_linked(
        _outline_rect(*box, shape_id="R3")), cfg())

    # The link runs straight through the middle of that shape either way.
    assert box[0] < -6.0 and box[2] > 6.0 and box[1] < 0.0 < box[3]

    assert LINK_UNCOVERED not in _codes(filled)
    assert LINK_UNCOVERED in _codes(outlined)
    assert outlined["metrics"]["link_uncovered_max_mm"] > 3.0


def test_content_thread_on_bare_fabric_is_not_a_link():
    """A fill row lying on open fabric IS the design; only thread whose job is
    to get somewhere can be a stray line. Three stacked fills therefore raise
    nothing — while the two needle-down moves BETWEEN them are still counted,
    because the machine really does sew from the end of one run to the start of
    the next. That connection belongs to no run's point list, so every
    instrument that walks a run's consecutive pairs is blind to it,
    `_coverage_map` included; here it is transport, and it is covered."""
    report = run_preflight(None, _stacked(3), cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["metrics"]["link_segments"] == 2
    assert report["metrics"]["link_uncovered_max_mm"] == 0.0


def test_a_fills_own_row_skip_travel_is_not_a_link():
    """THE false block of the hardening closeout (2026-08-02, finding 4).

    One shape, two fill columns, and the fill's OWN row-skip travel between
    them — exactly what `stage6_fill.emit` bridges across a sub-row-spacing
    neck of one polygon, needle down, inside the shape's own artwork. Most of
    that bridge lies on fabric the fill leaves bare, and the old transport
    classification scored it as a chain link: a clean ONE-shape design
    blocked with "thread crosses bare fabric between shapes" (score 100 ->
    70, measured on this exact plan). There are no other shapes. Thread from
    a shape to itself is routing, not a link — and it is not counted in the
    link metrics either, or the operator reads phantom "link thread" on
    designs that contain no links at all."""
    one_shape = _plan(
        _fill_rect(-13.0, -4.0, -5.0, 4.0, shape_id="F1"),
        _link_run((-5.0, 4.0), (5.0, -4.0), shape_id="F1"),
        _fill_rect(5.0, -4.0, 13.0, 4.0, shape_id="F1"))
    report = run_preflight(None, one_shape, cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["score"] == 100
    assert report["metrics"]["link_segments"] == 0
    assert report["metrics"]["link_thread_mm"] == 0.0


def test_a_shape_the_needle_JUMPED_to_opens_with_routing_not_a_link():
    """The SECOND false positive of this instrument (found 2026-09-02).

    Real plans routinely open a shape with that shape's own travel run, and
    stage 7 marks it `jump` because the machine lifts to reach it (the gap
    beats `machine.TINY_STITCH_MM`). The needle is UP across that boundary,
    so no thread goes from F1 to F2 at all — but the classifier compared
    against the last CONTENT it had seen (F1) rather than against where the
    needle was standing, and scored F2's own opening travel, plus the step
    out of it into F2's fill, as between-shape transport.

    Measured on `enthusiast_logo @ 80 mm/hat_front` with chaining shipping
    default-OFF: 4 link segments and 4.2 mm of "link thread" on a plan that
    chains nothing — the exact reading `_link_findings` promises is
    impossible. It is what moved that fixture's `link_segments` 0 -> 4 in the
    corpus scorecard, and it is why the connect branch's `not run.jump` rule
    now applies to travel runs too.

    The travel here is deliberately laid across bare fabric BETWEEN the two
    squares, so nothing about coverage rescues the answer: only reading the
    lift does.
    """
    jumped = _plan(
        _fill_rect(-14.0, -4.0, -6.0, 4.0, shape_id="F1"),
        # F2's own opening routing, reached with the needle up.
        StitchRun(points=_link_run((-6.0, 0.0), (6.0, 0.0)).points,
                  kind=st.TRAVEL, shape_id="F2", jump=True),
        _fill_rect(6.0, -4.0, 14.0, 4.0, shape_id="F2"))
    report = run_preflight(None, jumped, cfg())

    assert LINK_UNCOVERED not in _codes(report)
    assert report["metrics"]["link_segments"] == 0
    assert report["metrics"]["link_thread_mm"] == 0.0


def test_reading_the_lift_does_not_blind_the_instrument_to_a_real_link():
    """The other half of the pin, and the one that matters more.

    Same plan, same jump — but the travel now belongs to F1 and ends inside
    F2's fill, so it is thread that genuinely leaves one shape's routing and
    lands in another's content. `link_segments` skipping a lift must not
    become "a link that starts after a jump is free": chaining sews exactly
    such links, and law 60 is about the thread, not about how the needle got
    to its start.
    """
    real = _plan(
        _fill_rect(-14.0, -4.0, -6.0, 4.0, shape_id="F1"),
        StitchRun(points=_link_run((-6.0, 0.0), (6.0, 0.0)).points,
                  kind=st.TRAVEL, shape_id="F1", jump=True),
        _fill_rect(6.0, -4.0, 14.0, 4.0, shape_id="F2"))
    report = run_preflight(None, real, cfg())

    assert LINK_UNCOVERED in _codes(report)
    assert report["metrics"]["link_thread_mm"] > 10.0


def test_with_chaining_off_no_link_can_reach_the_float_ceiling():
    """The property that makes `_link_findings`' promise checkable.

    That docstring used to say a chain-off plan reports zero link thread. Very
    nearly true, and the exception is structural rather than a bug: stage 7
    lifts only once a gap beats `machine.TINY_STITCH_MM` (0.5 mm), so two
    shapes whose ends land closer than that stay joined needle-down without
    any chaining at all. On `enthusiast_logo @ 80 mm/hat_front` that is one
    0.4 mm connection — real thread, correctly counted, and six times under
    the 3 mm float this fabric cuts at.

    So the honest invariant is the one asserted here: with chaining off the
    instrument may report thread, but never enough to block. Anything past
    half a millimetre means either chaining ran or the classifier is reading
    thread the needle was not down for — the failure this test exists for.
    """
    art = TESTDATA / "photo" / "enthusiast_logo.png"
    for garment in ("left_chest", "hat_front"):
        c = cfg(target_width_mm=80.0, garment_id=garment)
        assert c.chain_links is False, "the premise"
        result = run_stages(art, c)
        stitch_plan = plan_stitches(result, c)
        report = run_preflight(None, stitch_plan, c)
        m = report["metrics"]
        assert LINK_UNCOVERED not in _codes(report), garment
        assert m["link_thread_mm"] < machine.TINY_STITCH_MM, (garment, m)


def test_a_clean_one_shape_design_is_silent_across_the_2026_08_02_firing_band():
    """The pipeline half of the same pin, at the sizes the closeout measured
    the false block: bg_uncertain.png is ONE shape, and at 104-107 mm
    (left_chest and hat_front) its fill's own row-skip routing used to read
    as 3.26-3.32 mm of "link" on bare fabric — a block on clean artwork that
    a 4-value size sweep couldn't find (the band is 4 mm wide). The design
    must pass inside the band, on its edges, and well outside it, on both
    garments that fired. The travel-length assertion keeps the pin honest:
    the design still routes internally (hundreds of mm on hat_front), the
    instrument just no longer calls that a link between shapes."""
    art = TESTDATA / "bg_uncertain.png"
    travel_mm = 0.0
    for width in (90.0, 104.0, 105.0, 106.0, 107.0, 120.0):
        result = run_stages(art, cfg(target_width_mm=width))
        assert len(result.regions) == 1, "the premise: one shape, no links possible"
        for garment in ("left_chest", "hat_front"):
            c = cfg(target_width_mm=width, garment_id=garment)
            stitch_plan = plan_stitches(result, c)
            travel_mm += sum(r.length_mm for _b, r in stitch_plan.iter_runs()
                             if r.kind == st.TRAVEL)
            report = run_preflight(None, stitch_plan, c)
            assert LINK_UNCOVERED not in _codes(report), (width, garment)
            assert report["metrics"]["link_thread_mm"] == 0.0, (width, garment)
    assert travel_mm > 50.0, "the design does travel; the instrument declines to score it"


def test_the_real_fixture_leaves_no_link_on_bare_fabric(enthusiast_logo_93mm):
    """The promise every threshold here was validated against. Measured
    2026-08-02 over 60 configurations (5 artworks x 4 sizes x 3 garments, with
    chaining on) the longest bare stretch is 2.29 mm and the p90 is 1.07,
    against a 3.0 mm ceiling on pique knit — so real work is silent, and the
    margin comes from measurement rather than from a threshold rounded up to
    fit.

    Re-pointed 2026-08-11 at the chain-ON benchmark plan: the instrument now
    scores between-shape transport only, and with chaining off no plan sews
    from one shape to another needle-down — the chain-off fixture's honest
    reading is zero link thread (pinned in the clean-report test above).
    The links this measures are the benchmark's own ~18 chained trims
    (test_chaining.py's acceptance numbers), the exact thread law 60 is
    about."""
    stitch_plan = plan_stitches(
        enthusiast_logo_93mm,
        cfg(target_width_mm=93.0, garment_id="left_chest", chain_links=True))
    m = run_preflight(
        None, stitch_plan,
        cfg(target_width_mm=93.0, garment_id="left_chest", chain_links=True),
    )["metrics"]

    assert m["link_segments"] > 0, "the benchmark chains links; measure them"
    assert m["link_uncovered_max_mm"] < 3.0
    assert m["link_uncovered_mm"] < m["link_thread_mm"] * 0.05


# --- Contour fill starvation (laws 39-44) ------------------------------------

def _starved_plan(**extra) -> StitchPlan:
    """A clean plan carrying stage 6's contour-starvation warning."""
    p = _plan(_square_fill())
    p.warnings = [dict(code=_CONTOUR_RING_UNREACHABLE,
                       message="rings too short to sew", **extra)]
    return p


def test_contour_starvation_reaches_the_operator():
    """Stage 6 knows a shape's dropped rings left more than 1% of it bare and
    says so in `plan.warnings`, which the preflight report never read — the one
    number that says a fill has a hole in it reached nobody scoring the file."""
    report = run_preflight(None, _starved_plan(count=2, rings=4), cfg())

    hit = [f for f in report["findings"] if f["code"] == CONTOUR_STARVED]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["count"] == 2
    assert hit[0]["extra"]["rings"] == 4


def test_contour_starvation_names_the_shapes_when_stage_6_carries_them():
    """'Which shape' is the operator's actual question. The contour lane's
    warning carries only a count today, so the finding degrades to that; the
    moment it carries `shapes`, this says which ones with no further change."""
    report = run_preflight(None, _starved_plan(count=1, rings=2,
                                               shapes=["Sb253ebba"]), cfg())

    hit = [f for f in report["findings"] if f["code"] == CONTOUR_STARVED][0]
    assert hit["extra"]["shapes"] == ["Sb253ebba"]
    assert "Sb253ebba" in hit["message"]


def test_a_plan_with_no_starved_shape_says_nothing_about_contours(plan):
    """The silent half. A tatami fixture carries no such warning and must not
    grow one — and the metric must read 0 rather than going missing, so a
    caller can tell 'none' from 'not checked'."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert CONTOUR_STARVED not in _codes(report)
    assert report["metrics"]["contour_starved_shapes"] == 0


# --- The fill-density instrument declines what it cannot measure -------------

def _rings(outer_mm: float = 8.0, inner_mm: float = 2.0,
           spacing: float = machine.FILL_ROW_MM) -> StitchRun:
    """Concentric rings at `spacing`, sewn outer to inner — a contour fill's
    geometry, which has no dominant stitch axis by construction."""
    pts: list[tuple[float, float]] = []
    r = outer_mm
    while r >= inner_mm:
        n = max(8, int(math.ceil(2 * math.pi * r / 1.5)))
        pts.extend((r * math.cos(2 * math.pi * i / n),
                    r * math.sin(2 * math.pi * i / n)) for i in range(n + 1))
        r -= spacing
    return StitchRun(points=pts, kind=st.FILL, shape_id="C1")


def test_the_row_density_instrument_declines_on_contour_rings():
    """Warning noise, caught before it shipped. `_fill_row_advance_mm` models a
    fill as rows along one axis with short turns between them; a contour fill
    has no such axis, so the model does not degrade on it, it inverts — nearly
    every step reads as a turn and the median 'row advance' returned is really
    the ring chord. Measured on the real tier: 2.19 / 2.35 / 2.98 mm against
    the 0.40 mm target, a DENSITY_EXTREME warn on three house fixtures out of
    four whose coverage map read a healthy 1.36-1.39 units. The instrument now
    checks its own assumption and stays quiet when it does not hold."""
    report = run_preflight(None, _plan(_rings()), cfg())

    assert report["metrics"]["fill_axis_concentration"] < 0.6
    assert report["metrics"]["fill_advance_mm"] is None
    assert DENSITY_EXTREME not in _codes(report)


def test_the_gate_does_not_blind_the_instrument_to_real_rows():
    """The other half: tatami rows concentrate hard on one axis (measured
    0.913-0.991 on the house fixtures against 0.003-0.270 for contour), so the
    gate must be invisible to them and the 0.40 mm reading must survive it."""
    m = run_preflight(None, _stacked(1), cfg())["metrics"]

    assert m["fill_axis_concentration"] > 0.6
    assert m["fill_advance_mm"] == pytest.approx(machine.FILL_ROW_MM, abs=0.02)


# --- Same-hole strikes (law 17) ----------------------------------------------

def test_same_hole_stays_silent_on_the_practice_professionals_share(plan):
    """The field note of 2026-08-01 measured 9.455% of penetrations landing
    on points struck 2+ times across the 36-file corpus, ALL 36 files
    containing 3+ stacked points, against our benchmark's 9.8% — the same
    practice, and both charges against the engine were dismissed. A check
    that fires there is wrong, and 'the naive fix would have been damaging':
    reading law 17 strictly 'would condemn every satin column ever sewn'.
    """
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert SAME_HOLE_HEAVY not in _codes(report)
    assert report["metrics"]["same_hole_fraction"] < 0.09455


def test_same_hole_fires_only_on_a_rate_far_above_the_corpus():
    """A regression that revisits every penetration once more: 50% of
    landings are on an already-struck point, five times the corpus's 9.455%.
    INFO severity — law 17's mechanism is real but its trade phrasing is
    stricter than professional files, so this must never cost score."""
    pts: list[tuple[float, float]] = []
    for i in range(40):
        a, b = (2.0 * i, 0.0), (2.0 * i, 4.0)
        pts.extend([a, b, a, b])
    report = run_preflight(None, _plan(StitchRun(points=pts, kind=st.RUN)), cfg())

    hit = [f for f in report["findings"] if f["code"] == SAME_HOLE_HEAVY]
    assert len(hit) == 1
    assert hit[0]["severity"] == "info"
    assert hit[0]["extra"]["fraction"] > 0.25
    assert report["score"] == 100, "an info finding must not cost score"


# --- Photo guardrails (photo plan §2 row 15) ---------------------------------
#
# The plan's own step-9 acceptance, held on both sides for every guard:
# fires on a constructed negative, stays quiet on the committed happy-path
# fixtures — measured from real preflight output on real pipeline runs, not
# mocked findings. The constructed negatives are deterministic ndarrays built
# in-test (the same rule F6 states for gradient goldens: constructed inputs,
# never found photographs).

def _digitize_report(image, **kw):
    c = cfg(**kw)
    result, stitch_plan = digitize(image, c)
    return run_preflight(result, stitch_plan, c, image=image)


@pytest.fixture(scope="module")
def scene_stub_report():
    """The committed photo-class happy path (photo_scene_stub classifies
    photo_scene NATURALLY, so this also exercises the plan.warnings half of
    the class gate — the forced-class half is exercised by the negatives).
    Measured: 12.5 px/mm input, subject/bg delta-L p90 27.6, 4 color
    changes, ~8k stitches — above every floor and under every ceiling.

    Background-existence guards off (2026-08-11): at defaults the guards now
    read this full-bleed stub as having no background (border agreement below
    0.75), which makes subject_bg_delta_l unmeasurable — the guards are the
    subject of their own tests; THIS test needs the with-background happy
    path so every floor is genuinely measured, not skipped."""
    return _digitize_report(str(PHOTO / "photo_scene_stub.png"),
                            bg_border_agreement_min=0.0,
                            bg_border_rival_min=0.0)


def test_every_photo_guard_stays_quiet_on_the_committed_photo_happy_path(scene_stub_report):
    m = scene_stub_report["metrics"]
    assert not (_codes(scene_stub_report) & PHOTO_GUARD_CODES)
    # And quiet because measured clear of the floors, not because skipped.
    assert m["input_px_per_mm"] == pytest.approx(12.5, abs=0.05)
    assert m["subject_bg_delta_l"] == pytest.approx(27.6, abs=0.5)
    assert m["color_changes"] <= COLOR_STOPS_MAX
    assert m["stitch_count"] <= STITCHES_CUTAWAY_MIN


def test_every_photo_guard_stays_quiet_on_the_committed_flat_fixtures():
    """The flat lane's committed fixtures, planned by the real pipeline. All
    of them sit UNDER the 10 px/mm photo floor (8.4-8.8 at 80 mm, measured
    table at PHOTO_MIN_PX_PER_MM) — the class gate is what keeps the photo
    floor from condemning clean flat work, and this is where that promise is
    pinned. logo_whitebg is pinned by the clean-report test above."""
    for art in ("logo_alpha.png", "ribbon_curve.png"):
        report = _digitize_report(str(TESTDATA / art))
        assert not (_codes(report) & PHOTO_GUARD_CODES), art
        assert report["metrics"]["input_px_per_mm"] < PHOTO_MIN_PX_PER_MM, art


# --- guard 1: the photo resolution floor -------------------------------------

def test_underresolved_photo_input_warns():
    """The constructed low-res negative: the photo lane's own integration
    fixture forced photo-class at 80 mm delivers 7.15 px per output mm —
    under Embird's 10 px/mm floor. (Forced class: this half of the gate reads
    cfg.forced_class, since a forced classification writes no warning.)"""
    report = _digitize_report(str(PHOTO / "region_blobs.png"),
                              forced_class="photo_scene")

    hit = [f for f in report["findings"] if f["code"] == PHOTO_RESOLUTION_LOW]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["px_per_mm"] == pytest.approx(7.15, abs=0.1)
    assert hit[0]["extra"]["min_px_per_mm"] == PHOTO_MIN_PX_PER_MM
    json.dumps(report)


def test_the_resolution_instrument_reads_input_pixels_not_the_upscaled_raster():
    """Stage 1's Lanczos rescue inflates px_per_mm below cfg.min_px_per_mm
    (4.0), and upscaling manufactures pixels, not detail — the guard must
    judge the resolution the INPUT delivered. region_blobs at 160 mm is
    3.57 px/mm raw; prep upscales the raster but `input_px_per_mm` holds."""
    from digitizer_core.stage1_prep import prep

    p = prep(str(PHOTO / "region_blobs.png"), cfg(target_width_mm=160.0))

    assert p.input_px_per_mm == pytest.approx(3.57, abs=0.05)
    assert p.px_per_mm > p.input_px_per_mm   # the rescue really ran


# --- guard 2: subject/background contrast ------------------------------------

def _isoluminant_photo() -> np.ndarray:
    """The plan's 'iso-luminant pair' negative: a saturated red subject on
    the green whose L* matches it to 0.16 (searched over sRGB greens —
    derivation at SUBJECT_DELTA_L_MIN). BGR, the convention an ndarray input
    is read in (stage1_prep._load treats it as cv2-decoded). The circle is
    840 px across so the input stays ABOVE the 10 px/mm photo floor at
    80 mm — one defect per negative."""
    img = np.zeros((900, 1000, 3), np.uint8)
    img[:, :] = (0, 130, 0)                       # BGR green, L* 46.93
    cv2.circle(img, (500, 450), 420, (60, 60, 200), -1)   # BGR red, L* 46.77
    return img


def test_an_isoluminant_subject_warns_it_will_vanish():
    report = _digitize_report(_isoluminant_photo(), forced_class="photo_subject")

    hit = [f for f in report["findings"] if f["code"] == SUBJECT_CONTRAST_LOW]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["delta_l"] == pytest.approx(0.16, abs=0.1)
    assert hit[0]["extra"]["min_delta_l"] == SUBJECT_DELTA_L_MIN
    # One defect per negative: the input is above the resolution floor.
    assert PHOTO_RESOLUTION_LOW not in _codes(report)
    assert report["metrics"]["input_px_per_mm"] >= PHOTO_MIN_PX_PER_MM
    json.dumps(report)


def test_flat_art_is_never_told_it_will_vanish():
    """The class gate's other half, on the SAME iso-luminant art: unforced,
    stage 0 classifies this flat (two hard-edged colors), and a flat logo
    sews its actual hue — red thread on the garment vanishes nowhere. The
    metric still rides out; only the finding is photo-gated."""
    report = _digitize_report(_isoluminant_photo())

    assert SUBJECT_CONTRAST_LOW not in _codes(report)
    assert report["metrics"]["subject_bg_delta_l"] == pytest.approx(0.16, abs=0.1)


def test_an_alpha_cutout_background_declines_the_contrast_instrument(alpha):
    """An alpha cutout's background is the garment, whose color the pipeline
    cannot know (the RGB under transparency is whatever the exporter left) —
    the instrument declines with the metric None rather than judging a
    lightness gap it never measured."""
    c = cfg()
    report = run_preflight(alpha, plan_stitches(alpha, c), c,
                           image=str(TESTDATA / "logo_alpha.png"))

    assert SUBJECT_CONTRAST_LOW not in _codes(report)
    assert report["metrics"]["subject_bg_delta_l"] is None


# --- guard 3: the cutaway-stabilizer prescription ----------------------------

def test_a_heavy_design_prescribes_cutaway_stabilizer():
    """The constructed 25k+ negative: a solid 180 mm square fills to 28.4k
    stitches through the real pipeline. INFO severity — nothing is wrong
    with the file, the operator just hoops cutaway under it [P — OESD, via
    the photo plan §2 row 15] — so it must not cost score, same contract as
    SAME_HOLE_HEAVY.

    Grown from 160 mm (26.7k) to 180 mm 2026-08-05: corpus laws 23/26
    landing (fabrics.py fill_underlay edge_lattice -> edge_run for
    pique_knit/jersey_tee) removes the fill's crosshatch-lattice underlay
    pass, dropping this fill-only fixture's count to 22.5k at the old
    size — legitimately UNDER STITCHES_CUTAWAY_MIN, since law 26 only
    removes stitches and law 23 only adds them to satin, which this
    all-fill fixture has none of. STITCHES_CUTAWAY_MIN itself is untouched
    (externally sourced, independent of engine output); the fixture grew so
    it still tests the real 25k boundary rather than a boundary the corrected
    engine no longer reaches."""
    square = np.full((820, 820, 3), 255, np.uint8)
    square[10:810, 10:810] = (40, 40, 120)
    report = _digitize_report(square, target_width_mm=180.0)

    hit = [f for f in report["findings"] if f["code"] == STABILIZER_CUTAWAY]
    assert len(hit) == 1
    assert hit[0]["severity"] == "info"
    assert hit[0]["extra"]["stitch_count"] > STITCHES_CUTAWAY_MIN
    assert "cutaway" in hit[0]["message"]
    # The single-defect construction: the prescription is the WHOLE report.
    assert _codes(report) == {STABILIZER_CUTAWAY}
    assert report["score"] == 100, "a prescription must not cost score"
    json.dumps(report)


def test_a_modest_design_gets_no_prescription(plan):
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert STABILIZER_CUTAWAY not in _codes(report)
    assert report["metrics"]["stitch_count"] < STITCHES_CUTAWAY_MIN


# --- guard 4: the single-needle color-stop wall ------------------------------

def test_color_stops_past_the_single_needle_wall_warn():
    """The constructed 11-stop negative: twelve distinct color patches
    through the real pipeline plan eleven thread changes — one past the
    ~10-stop single-needle default the plan cites (COLOR_STOPS_MAX has the
    derivation). Every change is a machine stop and a manual re-thread."""
    colors = [(230, 40, 40), (40, 180, 40), (40, 40, 230), (230, 230, 40),
              (230, 40, 230), (40, 230, 230), (140, 70, 20), (250, 140, 20),
              (120, 20, 160), (20, 120, 90), (90, 90, 90), (10, 10, 10)]
    patches = np.full((340, 460, 3), 255, np.uint8)
    for i, c in enumerate(colors):
        row, col = divmod(i, 4)
        y, x = 20 + row * 105, 20 + col * 110
        patches[y:y + 85, x:x + 90] = c
    report = _digitize_report(patches, target_width_mm=100.0)

    hit = [f for f in report["findings"] if f["code"] == COLOR_STOPS_HEAVY]
    assert len(hit) == 1
    assert hit[0]["severity"] == "warn"
    assert hit[0]["extra"]["color_changes"] == 11
    assert hit[0]["extra"]["max_stops"] == COLOR_STOPS_MAX
    assert report["metrics"]["color_changes"] == 11
    json.dumps(report)


def test_a_design_at_the_stop_cap_is_not_warned(plan):
    """<= 10 stops is inside every vendor's single-needle default; the wall
    is at 11. The fixture's own 4 changes are pinned in the clean-report
    test; here the metric must read rather than go missing."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(None, stitch_plan, cfg(**PLAN_CFG_KW))

    assert COLOR_STOPS_HEAVY not in _codes(report)
    assert report["metrics"]["color_changes"] == 4


# --- Scoring -----------------------------------------------------------------

def test_the_score_prices_severity_not_finding_count():
    """One block outweighs one warn: a wrong thread color is most of a letter
    grade, a heavy trim count is a nuisance."""
    clean = run_preflight(None, StitchPlan(blocks=[], palette=[]), cfg())
    assert (clean["score"], clean["grade"]) == (100, "A")

    warn_only = run_preflight(None, _plan(*_rows(10, 10, trim_from=1)), cfg())
    assert warn_only["score"] == 88
    assert warn_only["grade"] == "B"

    # Both thread findings ride on the madeira path (block + warn = 58, D);
    # asserted there rather than mocked here — the scorer has no seam for
    # injecting findings, deliberately.
    blocked = run_preflight(
        None, _plan(_satin_column(8, width_mm=0.8, spacing_mm=0.4)), cfg())
    assert blocked["score"] == 88   # one warn: lettering


# --- CLASS_OVERRIDE_TECHNIQUE_MISMATCH (photo plan §2 row 15) ---------------
#
# `enthusiast_logo.png` classifies "flat" on its own (confirmed directly via
# stage0_classify.classify, and pinned again below) — a real commissioned
# flat two-color logo, not a constructed negative, giving this guard a real
# fixture where forcing a photo-tonal class is a genuine mismatch rather
# than a coin flip near a threshold.

_FLAT_FIXTURE = str(PHOTO / "enthusiast_logo.png")


def test_enthusiast_logo_still_classifies_flat_on_its_own():
    """Precondition the mismatch tests below depend on — if this fixture's
    own classification ever drifts, those tests would stop meaning what they
    claim to."""
    from digitizer_core.stage0_classify import classify

    result = classify(_FLAT_FIXTURE, cfg())
    assert result.class_ == "flat"


def test_forcing_a_photo_class_with_a_tonal_technique_warns():
    """The actual defect this guard exists for: a flat-classifying design
    forced to "photo_subject" with the streamline tonal tier selected —
    exactly the combination that reads SourcePixels darkness on content that
    was never a photographic tonal range."""
    report = _digitize_report(
        _FLAT_FIXTURE, forced_class="photo_subject", fill_technique="streamline")

    hits = [f for f in report["findings"] if f["code"] == CLASS_OVERRIDE_TECHNIQUE_MISMATCH]
    assert len(hits) == 1
    hit = hits[0]
    assert hit["severity"] == "warn"
    assert hit["extra"] == {
        "forced_class": "photo_subject",
        "detected_class": "flat",
        "fill_technique": "streamline",
    }
    assert report["metrics"]["class_override_detected_class"] == "flat"
    json.dumps(report)


@pytest.mark.parametrize("technique", ["scanline_tonal", "meander_tonal", "sketch"])
def test_every_photo_tonal_technique_trips_the_guard(technique):
    """Not just streamline — every technique this guard's own docstring
    names reads the same raster-darkness signal and must trip the same way."""
    report = _digitize_report(
        _FLAT_FIXTURE, forced_class="photo_scene", fill_technique=technique)
    hits = {f["code"] for f in report["findings"]}
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH in hits


def test_forcing_the_class_it_would_pick_anyway_stays_silent():
    """Forcing "flat" on a design that already classifies flat is not an
    override doing any real work — nothing to warn about even with a tonal
    technique selected."""
    report = _digitize_report(
        _FLAT_FIXTURE, forced_class="flat", fill_technique="streamline")
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH not in _codes(report)


def test_a_forced_class_with_an_ordinary_technique_stays_silent():
    """The override alone, without a photo-tonal technique, is a legitimate
    power-user move this guard has nothing to say about (tatami is the
    default fill_technique)."""
    report = _digitize_report(_FLAT_FIXTURE, forced_class="photo_subject")
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH not in _codes(report)


def test_no_override_stays_silent_even_with_a_tonal_technique():
    """No forced_class at all: whatever stage 0 decides on its own, there is
    no override to disagree with the router about."""
    report = _digitize_report(_FLAT_FIXTURE, fill_technique="streamline")
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH not in _codes(report)


def test_the_guard_declines_without_the_artwork():
    """`image=None` mirrors the thread-match / photo-resolution checks:
    without the artwork this guard cannot re-run the unforced classifier, so
    it says nothing rather than guessing."""
    c = cfg(forced_class="photo_subject", fill_technique="streamline")
    result, plan = digitize(_FLAT_FIXTURE, c)
    report = run_preflight(result, plan, c, image=None)
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH not in _codes(report)
    assert report["metrics"]["class_override_detected_class"] is None


def test_the_real_fixture_clean_report_never_trips_the_new_guard(whitebg, plan):
    """The default-config clean-report fixture (no forced_class at all) —
    already asserted empty findings above, re-asserted narrowly here so a
    future change to this guard's gating cannot silently regress it."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW), image=ART)
    assert CLASS_OVERRIDE_TECHNIQUE_MISMATCH not in _codes(report)


def test_the_report_is_json_safe():
    """The service hands this straight to a JSON boundary; a stray numpy
    scalar would 500 the job endpoint."""
    import json

    plan = _plan(_satin_column(40, width_mm=0.7, spacing_mm=0.4),
                 StitchRun(points=[(0.0, 0.0), (15.0, 0.0)], kind=st.FILL))
    json.dumps(run_preflight(None, plan, cfg()))
    # The link check builds its answer out of numpy arrays; a stray numpy
    # scalar in the coordinate or the length would 500 the job endpoint.
    json.dumps(run_preflight(None, _two_shapes_linked(), cfg()))
    json.dumps(run_preflight(None, _starved_plan(count=1, rings=1,
                                                 shapes=["S1"]), cfg()))


# --- Artwork left uncovered -------------------------------------------------
#
# The defect these guard is the one every other check in this module is blind
# to by construction: a shape whose outline is right, whose tier is right, and
# which reports `stitched: true`, that still puts no thread on part of itself.
# Found on `enthusiast_logo` 2026-08-20 by eye, after preflight graded it A.


def _uncovered(report: dict) -> dict | None:
    for f in report["findings"]:
        if f["code"] == ARTWORK_UNCOVERED:
            return f
    return None


def test_a_dropped_limb_is_reported_and_names_its_shape(monkeypatch):
    """`enthusiast_logo` at 150 mm used to drop the emblem bracket's inward tab.

    The drop itself was fixed 2026-08-21 (`stage6_satin._prune_spurs` no longer
    re-measures a stem its own earlier pass un-branched), and with it went the
    only fixture in the corpus that put this check on real ground. Rather than
    lose the positive case, the fault is injected: `_prune_spurs` is restored to
    its pre-fix behaviour and the check must still fire, still name the shape.

    The shape id is the point of the finding: "7.8 mm2 is missing" sends nobody
    anywhere, `S041897f7` sends them to the bracket. Asserted on the id rather
    than only the area so a change that keeps the area but loses the
    attribution still fails.
    """
    def unguarded(mask, spur_len_px):
        """`_prune_spurs` exactly as it shipped before the 2026-08-21 fix."""
        for _ in range(4):
            removed = 0
            for e in stage6_satin._skeleton_edges(mask):
                if e["closed"] or (e["free_start"] == e["free_end"]):
                    continue
                length = sum(math.dist(a, b)
                             for a, b in zip(e["pts"], e["pts"][1:]))
                if length >= spur_len_px:
                    continue
                keep = e["pts"][-1] if e["free_start"] else e["pts"][0]
                for px in e["pts"]:
                    if px != keep:
                        mask[px[1], px[0]] = 0
                        removed += 1
            if not removed:
                return

    monkeypatch.setattr(stage6_satin, "_prune_spurs", unguarded)

    art = TESTDATA / "photo/enthusiast_logo.png"
    c = cfg(target_width_mm=150.0, max_colors=6)
    result, plan_ = digitize(art, c)
    report = run_preflight(result, plan_, c, image=art)

    found = _uncovered(report)
    assert found is not None, "the dropped tab must be reported"
    assert found["severity"] == "warn"
    ids = {s["shape_id"] for s in found["extra"]["shapes"]}
    assert "S041897f7" in ids, f"expected the left bracket, got {ids}"
    assert report["metrics"]["uncovered_worst_mm2"] >= 5.0


def test_the_bracket_tab_the_check_found_is_now_sewn():
    """The other half: with the fix in place the same job comes back clean.

    Paired with the fault-injection test above on purpose — together they say
    the check fires when there IS a hole and stays silent when there is not,
    which neither test proves alone. `enthusiast_logo` was the corpus's only
    real uncovered-artwork case, so this is also the regression guard for the
    prune fix at the product level rather than the graph level.
    """
    art = TESTDATA / "photo/enthusiast_logo.png"
    c = cfg(target_width_mm=150.0, max_colors=6)
    result, plan_ = digitize(art, c)
    report = run_preflight(result, plan_, c, image=art)

    assert _uncovered(report) is None, (
        "the emblem bracket's tab is sewn again — a finding here means the "
        "prune guard regressed"
    )
    assert report["metrics"]["uncovered_checked"] is True
    assert report["metrics"]["uncovered_worst_mm2"] < 5.0


def test_a_clean_fixture_leaves_no_artwork_uncovered(whitebg, plan):
    """The promise every threshold here is validated against, for this check:
    clean work reports zero, not 'a little'."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW), image=ART)

    assert _uncovered(report) is None
    m = report["metrics"]
    assert m["uncovered_checked"] is True
    assert m["uncovered_worst_mm2"] == 0.0
    assert m["uncovered_wanted_mm2"] > 0.0     # it really did measure something


def test_a_full_bleed_design_does_not_report_its_own_border():
    """Regression guard for the erosion border, measured 2026-08-20.

    `cv2.erode`'s default border does not erode artwork that touches the
    image edge, so a full-bleed design read a permanent uncovered strip down
    its rim — 37.5 mm2 on this fixture, at every erosion width, before
    `borderValue=0`. A check that fires on every full-bleed logo is a check
    operators learn to ignore.
    """
    art = TESTDATA / "photo/logo_gaulke_roofing.png"
    c = cfg(target_width_mm=90.0, max_colors=6)
    result, plan_ = digitize(art, c)
    report = run_preflight(result, plan_, c, image=art)

    assert _uncovered(report) is None
    assert report["metrics"]["uncovered_worst_mm2"] == 0.0


def test_without_the_artwork_the_uncovered_check_is_skipped_and_says_so(whitebg, plan):
    """No image means no ground truth. It reports None rather than zero —
    'not measured' and 'measured clean' must not look alike."""
    stitch_plan, _planned, _warnings = plan
    report = run_preflight(whitebg, stitch_plan, cfg(**PLAN_CFG_KW), image=None)

    m = report["metrics"]
    assert m["uncovered_checked"] is False
    assert m["uncovered_worst_mm2"] is None
    assert m["uncovered_wanted_mm2"] is None


# --- Thread fidelity on the photo route (2026-08-24) -------------------------
#
# Reducing a photograph to a capped cone list guarantees per-thread colour
# distance. On the 32-job acceptance sheet THREAD_MATCH_POOR fired 256 times at
# `block`, so every photo job graded F / "do not sew" — the DENSITY_EXTREME
# misfire of PR #216 in a different check. The fix rescores the photo route on
# EXCESS over the best already-loaded spool. These four tests pin both halves:
# an optimal assignment goes quiet, a genuinely wrong one still blocks.

def _two_spool_photo_scene(assign_swapped: bool):
    """Two rectangles painted two colours far apart, sewn in two spools.

    Returns (result, cfg_kwargs, image). When `assign_swapped` is False each
    region gets the loaded spool nearest its own paint — the best any capped
    cone list could do, so the excess yardstick must read ~0. When True the
    two assignments are exchanged, so for each region the OTHER already-loaded
    spool is closer: a free improvement left on the table, which must still
    block on any route.
    """
    from types import SimpleNamespace

    from shapely.geometry import Polygon

    from digitizer_core.regions import Region
    from digitizer_core.stage1_prep import prep
    from digitizer_core.threads import chart_for, rgb_to_lab

    c = cfg()
    chart = chart_for(c)
    red_rgb = (215, 45, 45)
    blue_rgb = (45, 45, 215)
    red_i = chart.nearest_index(rgb_to_lab(np.array([list(red_rgb)], np.uint8))[0])
    blue_i = chart.nearest_index(rgb_to_lab(np.array([list(blue_rgb)], np.uint8))[0])
    assert red_i != blue_i, "fixture needs two distinct spools to swap between"

    img = np.full((400, 500, 3), 255, np.uint8)
    img[40:240, 60:260] = red_rgb[::-1]      # BGR, the ndarray convention
    img[40:240, 300:460] = blue_rgb[::-1]
    p = prep(img, c)
    x0, y0, x1, y1 = p.art_bbox
    px_cx, px_cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0

    def rect_mm(px0, py0, px1, py1) -> Polygon:
        corners = [(px0 + 2, py0 + 2), (px1 - 2, py0 + 2),
                   (px1 - 2, py1 - 2), (px0 + 2, py1 - 2)]
        return Polygon([((x - px_cx) / p.px_per_mm, (y - px_cy) / p.px_per_mm)
                        for x, y in corners])

    r_spool, b_spool = (blue_i, red_i) if assign_swapped else (red_i, blue_i)

    def region(shape_id, poly, spool):
        return Region(shape_id=shape_id, polygon=poly, thread_index=spool,
                      thread_number=chart[spool].number,
                      area_mm2=float(poly.area))

    result = SimpleNamespace(regions=[
        region("Sred", rect_mm(60, 40, 260, 240), r_spool),
        region("Sblue", rect_mm(300, 40, 460, 240), b_spool),
    ])
    return result, img, chart, red_i, blue_i


def test_photo_route_stays_quiet_when_every_cone_is_the_best_one_loaded():
    """The misfire this rescoring exists to stop.

    Each region wears the closest spool the design loads, so no reassignment
    could help and preflight must say nothing.

    The second half is what makes that silence meaningful rather than an
    artifact of well-matched paint: the SAME fixture on a non-photo class
    does fire — one warn, measured 5.1 dE00, just over DELTA_E_VISIBLE. So
    the raw yardstick has something to say here, and the photo yardstick
    correctly answers "no cone this design loads could have done better".
    """
    result, img, _chart, _r, _b = _two_spool_photo_scene(assign_swapped=False)
    empty = StitchPlan(blocks=[], palette=[])

    photo = run_preflight(result, empty, cfg(forced_class="photo_subject"),
                          image=img)
    assert THREAD_MATCH_POOR not in _codes(photo)

    raw = run_preflight(result, empty, cfg(), image=img)
    raw_hits = [f for f in raw["findings"] if f["code"] == THREAD_MATCH_POOR]
    assert raw_hits, "fixture must be non-trivial: the raw yardstick fires here"
    assert raw_hits[0]["extra"]["delta_e"] > DELTA_E_VISIBLE


def test_photo_route_still_blocks_a_cone_swap_that_was_free():
    """The half a blanket photo exemption would have thrown away.

    Measured in-pipeline on the real portraits, this class survives the
    rescoring: baby_deck_laugh carries a region with 13.18 dE00 of excess —
    a spool sitting loaded and that much closer to the artwork than the one
    that sewed it — and it still blocks. Swapping two assignments reproduces
    the class deterministically.
    """
    result, img, chart, red_i, blue_i = _two_spool_photo_scene(assign_swapped=True)
    empty = StitchPlan(blocks=[], palette=[])

    report = run_preflight(result, empty, cfg(forced_class="photo_subject"),
                           image=img)
    hit = [f for f in report["findings"] if f["code"] == THREAD_MATCH_POOR]
    assert hit, "a free, strictly better already-loaded spool must still fire"
    assert all(f["severity"] == "block" for f in hit)

    # The finding names the swap: excess is populated (so a reader can tell
    # which yardstick set the severity) and better_spool points at the cone
    # already on the machine.
    numbers = {chart[red_i].number, chart[blue_i].number}
    for f in hit:
        assert f["extra"]["excess_delta_e"] > DELTA_E_CLEARLY_DIFFERENT
        assert f["extra"]["better_spool"] in numbers
        assert f["extra"]["better_spool"] != f["extra"]["thread_number"]
        assert "already loaded" in f["message"]
    json.dumps(report)


def test_non_photo_routes_keep_the_raw_yardstick_untouched():
    """Byte-identity guard, the #216 discipline: only the photo route is
    rescored. On a flat design the same swapped fixture scores on raw
    distance, and the excess fields stay None so nothing downstream can
    mistake a raw finding for a rescored one."""
    result, img, _chart, _r, _b = _two_spool_photo_scene(assign_swapped=True)
    empty = StitchPlan(blocks=[], palette=[])

    report = run_preflight(result, empty, cfg(), image=img)
    hit = [f for f in report["findings"] if f["code"] == THREAD_MATCH_POOR]
    assert hit
    for f in hit:
        assert f["extra"]["excess_delta_e"] is None
        assert f["extra"]["better_spool"] is None
        assert "Pick a closer thread" in f["message"]


def test_a_one_cone_photo_design_is_not_silenced_by_the_rescoring():
    """The degenerate guard. With a single loaded spool every excess is 0 by
    construction, so an unguarded rescoring would go permanently quiet and
    hide an honestly unreachable colour. `len(loaded) > 1` keeps raw scoring
    there — the one-cone case still reports."""
    from types import SimpleNamespace

    result, img, chart, red_i, _b = _two_spool_photo_scene(assign_swapped=True)
    # Collapse to one cone: both regions sew the red spool, so the blue
    # rectangle is far off it and nothing else is loaded to rescue it.
    for r in result.regions:
        r.thread_index = red_i
        r.thread_number = chart[red_i].number
    one_cone = SimpleNamespace(regions=result.regions)
    empty = StitchPlan(blocks=[], palette=[])

    report = run_preflight(one_cone, empty, cfg(forced_class="photo_subject"),
                           image=img)
    hit = [f for f in report["findings"] if f["code"] == THREAD_MATCH_POOR]
    assert hit, "a single-cone photo design must still report an unreachable colour"
    assert hit[0]["extra"]["excess_delta_e"] is None
    assert hit[0]["extra"]["delta_e"] > DELTA_E_CLEARLY_DIFFERENT
