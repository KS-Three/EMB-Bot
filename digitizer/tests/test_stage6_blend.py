"""Stage 6 — the gradient blend fill tier.

Geometry is measured from EMITTED stitch rows, never from the parameters
`blend_fill` was called with — a bug that only shows in what actually got
sewn (a wrong band boundary, a dropped layer) would sail through a test that
just re-checked the function's own arguments.

Fixture geometry (`gradient_ramp_linear.png` / `gradient_ramp_radial.png`,
`tools/make_gradient_fixture.py`, W=1000 H=650 MARGIN=70, no supersample
residue after the generator's own downscale): the linear ramp is the inset
rectangle `x0=70 y0=70 x1=930 y1=580`; the radial ramp is the disc centered
on the canvas center with radius `min(W, H)/2 - MARGIN = 255`. Both fixtures
share that canvas center, so one `SourcePixels` mapping (target width 90 mm,
origin at the canvas center) fits either.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import machine, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import (
    RAMP_REJECT_LOW_R2,
    RAMP_REJECT_SPECKLED,
    SourcePixels,
    blend_fill,
    detect_design_ramp_angle,
    detect_ramp,
    detect_ramp_detail,
)
from digitizer_core.stage6_fill import principal_angle_deg, stitch_shape
from digitizer_core.threads import CHART

HERE = Path(__file__).resolve().parent
PHOTO_DIR = HERE.parent / "testdata" / "photo"

# --- Fixture geometry (see module docstring) --------------------------------
_W, _H, _MARGIN = 1000, 650, 70
_TARGET_MM = 90.0
_PX_PER_MM = (_W - 2 * _MARGIN) / _TARGET_MM
_ORIGIN_PX = (_W / 2.0, _H / 2.0)
_RADIUS_PX = min(_W, _H) / 2.0 - _MARGIN


def _load_rgb(name: str) -> np.ndarray:
    bgr = cv2.imread(str(PHOTO_DIR / name), cv2.IMREAD_COLOR)
    assert bgr is not None, f"missing fixture {name}"
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)


def _to_mm(x_px: float, y_px: float) -> tuple[float, float]:
    return ((x_px - _ORIGIN_PX[0]) / _PX_PER_MM, (y_px - _ORIGIN_PX[1]) / _PX_PER_MM)


def _linear_region() -> Region:
    x0, y0 = _to_mm(_MARGIN, _MARGIN)
    x1, y1 = _to_mm(_W - _MARGIN, _H - _MARGIN)
    poly = Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])
    return Region(shape_id="Sramp", polygon=poly, thread_index=0,
                 thread_number=CHART[0].number, area_mm2=poly.area)


def _radial_region() -> Region:
    radius_mm = _RADIUS_PX / _PX_PER_MM
    poly = Point(0.0, 0.0).buffer(radius_mm, quad_segs=64)
    return Region(shape_id="Sramp", polygon=poly, thread_index=0,
                 thread_number=CHART[0].number, area_mm2=poly.area)


def _linear_source() -> SourcePixels:
    return SourcePixels(rgb=_load_rgb("gradient_ramp_linear.png"),
                        px_per_mm=_PX_PER_MM, origin_px=_ORIGIN_PX)


def _radial_source() -> SourcePixels:
    return SourcePixels(rgb=_load_rgb("gradient_ramp_radial.png"),
                        px_per_mm=_PX_PER_MM, origin_px=_ORIGIN_PX)


def _rotate(points, angle_deg: float) -> list[tuple[float, float]]:
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    return [(x * ca + y * sa, -x * sa + y * ca) for x, y in points]


def _layers_of(runs) -> dict[str, list]:
    """Group runs by their blend-layer shape_id suffix ("<id>-blend<i>")."""
    out: dict[str, list] = {}
    for r in runs:
        out.setdefault(r.shape_id, []).append(r)
    return out


def _row_ys(runs, angle_deg: float) -> list[float]:
    """Real row y-positions (rotated into the fill frame) for one layer's FILL
    runs — the row grid actually sewn.

    Two kinds of point never belong to that grid, and both are excluded:
    travel/underlay runs (a bridge follows the inset ring, not the row grid,
    landing at an arbitrary y), and `split_long_moves`'s own interpolated
    midpoints on a long row-to-row turn, which sit at exactly half a row
    spacing and would otherwise read as a spurious extra row. A real row
    carries many stitch points at its y (the row's own penetrations); a
    turn's interpolated midpoint carries exactly one, which is the filter.
    """
    from collections import Counter
    counts: Counter[float] = Counter()
    for r in runs:
        if r.kind != stitches.FILL:
            continue
        for p in _rotate(r.points, angle_deg):
            counts[round(p[1], 3)] += 1
    return sorted(y for y, c in counts.items() if c >= 3)


def _row_spacings_mm(runs, angle_deg: float) -> list[float]:
    """Consecutive gaps between real row y-positions — the row spacing
    actually sewn."""
    ordered = _row_ys(runs, angle_deg)
    return [round(b - a, 3) for a, b in zip(ordered, ordered[1:])]


def _row_length_coverage(runs, angle_deg: float, row_mm: float, region_area_mm2: float) -> float:
    """Physical coverage of one layer: for each row segment (two consecutive
    points sharing one rotated y — a stitch ALONG a row, not the turn to the
    next one), its swept footprint is (segment length) x row_mm — the strip
    of fabric that segment and the layer's own row spacing account for.
    Summed over every row segment and divided by the region's area, this is
    a coverage fraction computed entirely from what was actually sewn.

    Segments, not a naive min/max x per row: a ring-shaped layer's row can
    cross the shape twice (an arc on each side of the hole), and collapsing
    those two spans to their combined min/max would sew a nonexistent
    stitch straight across the hole. Summing the real along-row segments
    gets both arcs right without ever assuming a row has just one span.
    """
    total = 0.0
    for r in runs:
        if r.kind != stitches.FILL:
            continue
        pts = _rotate(r.points, angle_deg)
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if abs(yb - ya) > 1e-6:
                continue  # a row-to-row turn, not a stitch along a row
            total += abs(xb - xa) * row_mm
    return total / region_area_mm2


def _dominant_angle_deg(runs) -> float:
    """The direction most of a layer's stitch length runs along — the fill
    angle, recovered from the emitted geometry itself rather than trusted
    from a parameter. Rows are far longer in aggregate than the short turns
    between them, so a length-weighted circular mean of every segment's
    direction (folded into a half-turn, since a row's two ends point
    opposite ways) lands on the row direction.
    """
    sx = sy = 0.0
    for r in runs:
        if r.kind != stitches.FILL:
            continue
        for a, b in zip(r.points, r.points[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            theta2 = 2.0 * math.atan2(dy, dx)
            sx += math.cos(theta2) * length
            sy += math.sin(theta2) * length
    return math.degrees(math.atan2(sy, sx)) / 2.0


def _angle_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


@pytest.mark.parametrize("region_factory,source_factory", [
    (_linear_region, _linear_source),
    (_radial_region, _radial_source),
])
def test_blend_geometry_matches_the_plan_contract(region_factory, source_factory):
    region = region_factory()
    source = source_factory()
    cfg = PipelineConfig()

    runs, report = blend_fill(region, source, cfg)
    assert runs, "a ramp fixture must produce stitches"
    assert report["empty"] is False

    layers = _layers_of(runs)
    n = len(layers)
    assert 3 <= n <= 5, f"shade count out of [3, 5]: {n}"
    for sid in layers:
        assert sid.startswith(f"{region.shape_id}-blend"), sid

    angle = principal_angle_deg(region.polygon)

    # Every band is a fill and sews at the fill row (2026-09-03). Until then
    # this read `FILL_ROW_MM * n` — one sparse layer per band — and the
    # coverage sum below, which weights each row by the layer's OWN spacing,
    # summed the bands' areas to 1.0 while the cloth got a third to a fifth
    # of a fill. At the fill row the same sum is the physical coverage.
    expected_row_mm = machine.FILL_ROW_MM
    total_coverage = 0.0
    layer_angles = []
    for sid, layer_runs in layers.items():
        gaps = _row_spacings_mm(layer_runs, angle)
        assert gaps, f"{sid}: no distinct rows found"
        for g in gaps:
            assert g == pytest.approx(expected_row_mm, abs=0.02), (
                f"{sid}: row spacing {g} != {expected_row_mm} +/- 0.02mm"
            )
        total_coverage += _row_length_coverage(layer_runs, angle, expected_row_mm,
                                               region.polygon.area)
        layer_angles.append(_dominant_angle_deg(layer_runs))

    assert 1.0 <= total_coverage <= 1.2, f"sum coverage {total_coverage} outside [1.0, 1.2]"

    for a in layer_angles:
        assert _angle_diff_deg(a, angle) <= 2.0, (
            f"layer angle {a} deviates from the shared fill angle {angle}"
        )


def test_blend_report_distinguishes_decomposed_from_flattened():
    """The 2026-08-12 defect, at the unit level: nothing in `blend_fill`'s
    report told a caller whether decomposition ACTUALLY happened, so stage 0's
    routing announcement ("will decompose the ramp into a few thread shades")
    was the only signal a user ever got — and on Kent's owl it was wrong for
    all 25 regions. A real ramp and a noise field must now be
    distinguishable from the report alone, which is what stage 7 aggregates
    into BLEND_NO_REGIONS_DECOMPOSED.
    """
    cfg = PipelineConfig()

    ramp_region, ramp_source = _linear_region(), _linear_source()
    _, ramp_report = blend_fill(ramp_region, ramp_source, cfg)
    assert ramp_report["blend_shades"] >= 3, "a true ramp must report its shades"
    assert ramp_report["blend_reject"] == ""
    assert ramp_report["blend_best_r2"] >= 0.5

    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise_source = SourcePixels(
        rgb=rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8),
        px_per_mm=4.0, origin_px=(80.0, 60.0))
    noise_region = Region(shape_id="Snoise", polygon=poly, thread_index=0,
                          thread_number=CHART[0].number, area_mm2=poly.area)
    _, noise_report = blend_fill(noise_region, noise_source, cfg)
    assert noise_report["blend_shades"] == 0, (
        "a flattened region must not report shades it never sewed"
    )
    assert noise_report["blend_reject"] in (RAMP_REJECT_LOW_R2, RAMP_REJECT_SPECKLED)


def test_detect_ramp_detail_agrees_with_detect_ramp():
    """`detect_ramp` is now a wrapper over `detect_ramp_detail`. Pin that the
    split didn't change the accept/reject decision for either branch — every
    existing caller and test still goes through the wrapper."""
    ramp_region, ramp_source = _linear_region(), _linear_source()
    model, reason, r2 = detect_ramp_detail(ramp_region.polygon, ramp_source)
    assert model is not None and reason == "" and r2 >= 0.5
    assert detect_ramp(ramp_region.polygon, ramp_source) is not None

    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise_source = SourcePixels(
        rgb=rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8),
        px_per_mm=4.0, origin_px=(80.0, 60.0))
    model, reason, _ = detect_ramp_detail(poly, noise_source)
    assert model is None and reason != ""
    assert detect_ramp(poly, noise_source) is None


def test_blend_true_ramp_branch_honors_the_shared_design_angle():
    """`test_blend_geometry_matches_the_plan_contract` above never sets
    `design_row_angle_deg` on either fixture, so it never exercises
    `blend_fill`'s OTHER branch — this region's own ramp genuinely detected
    (`model.kind == "linear"`) AND a shared design angle set — leaving that
    combination unguarded by any regression test (a gap an independent
    review of the 2026-08-03 fix flagged). Forces a design angle that
    visibly differs from `_linear_region`'s own `principal_angle_deg` and
    checks every layer's rows actually land there instead."""
    region = _linear_region()
    source = _linear_source()
    forced_angle = 10.0
    natural_angle = principal_angle_deg(region.polygon)
    assert _angle_diff_deg(natural_angle, forced_angle) > 5.0, (
        "test fixture's natural angle must differ from the forced one to be a real check"
    )
    source.design_row_angle_deg = forced_angle
    cfg = PipelineConfig()

    assert detect_ramp(region.polygon, source) is not None, (
        "this test exists specifically to exercise the true-ramp branch"
    )
    runs, report = blend_fill(region, source, cfg)
    assert runs
    assert report["empty"] is False

    for sid, layer_runs in _layers_of(runs).items():
        gaps = _row_spacings_mm(layer_runs, forced_angle)
        assert gaps, f"{sid}: no distinct rows found at the forced angle"
        measured = _dominant_angle_deg(layer_runs)
        assert _angle_diff_deg(measured, forced_angle) <= 1.0, (
            f"{sid}: angle {measured} did not honor the forced design angle {forced_angle}"
        )


def test_blend_falls_back_to_ordinary_tatami_on_speckle():
    """Random noise has no structured residual at all — ramp detection must
    refuse it and this must sew exactly like `stage6_fill.stitch_shape`
    would, the real fallback path the contract calls for."""
    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise = rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8)
    source = SourcePixels(rgb=noise, px_per_mm=4.0, origin_px=(80.0, 60.0))
    region = Region(shape_id="Snoise", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)

    assert detect_ramp(poly, source) is None

    cfg = PipelineConfig()
    runs, report = blend_fill(region, source, cfg)

    expected, expected_report = stitch_shape(
        poly, region.shape_id, angle_deg=None, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
        trim_at_mm=machine.TRIM_AT_MM)
    assert [r.points for r in runs] == [r.points for r in expected]
    assert all(r.shape_id == region.shape_id for r in runs)
    # The stitch-planning half of the report must still be byte-identical to
    # what plain tatami produced — that IS the fallback contract. The blend_*
    # keys are diagnostics stage 7 aggregates into
    # BLEND_NO_REGIONS_DECOMPOSED and have no tatami counterpart, so they are
    # checked separately rather than weakening the equality above.
    assert {k: v for k, v in report.items()
            if not k.startswith("blend_")} == expected_report
    assert report["blend_shades"] == 0, "flat fallback must not claim shades"
    # Surfaced by the blend_reject diagnostic when it was added (2026-08-12):
    # despite this test's name, the noise field never reaches the speckle
    # gate. `detect_ramp` tests r2 FIRST, and random noise has no linear or
    # radial structure to fit, so it is rejected on RAMP_R2_MIN and the
    # speckle branch is never evaluated. The fallback behaviour this test
    # actually guards is unchanged and still correct; only the reason is not
    # the one the name implies. RAMP_SPECKLE_MAX's own coverage lives in the
    # radial-disc fixture cited in `_speckle_ratio`'s docstring.
    assert report["blend_reject"] == RAMP_REJECT_LOW_R2


def test_blend_fallback_uses_the_shared_design_angle_when_set():
    """The 2026-08-03 angle-fragmentation fix, at the unit level: a fragment
    whose own `detect_ramp` declines (the common case — see
    `blend_fill`'s own comment on this branch) must sew at
    `SourcePixels.design_row_angle_deg` when the caller set one, not at its
    own `principal_angle_deg`. Same noise fixture as the test above (still a
    real fallback, `detect_ramp` still declines it) — only the forced angle
    changes."""
    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise = rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8)
    source = SourcePixels(rgb=noise, px_per_mm=4.0, origin_px=(80.0, 60.0),
                          design_row_angle_deg=33.0)
    region = Region(shape_id="Snoise", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)
    assert detect_ramp(poly, source) is None

    cfg = PipelineConfig()
    runs, report = blend_fill(region, source, cfg)

    expected, expected_report = stitch_shape(
        poly, region.shape_id, angle_deg=33.0, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
        trim_at_mm=machine.TRIM_AT_MM)
    assert [r.points for r in runs] == [r.points for r in expected]
    assert {k: v for k, v in report.items()
            if not k.startswith("blend_")} == expected_report
    assert report["blend_shades"] == 0
    # And NOT what the untouched default (no shared angle) would have sewn —
    # otherwise this test could pass even if the angle were silently ignored.
    unforced, _ = stitch_shape(
        poly, region.shape_id, angle_deg=None, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
        trim_at_mm=machine.TRIM_AT_MM)
    assert [r.points for r in runs] != [r.points for r in unforced]


def test_detect_design_ramp_angle_finds_the_hue_carried_diagonal():
    """The confirmed 2026-08-03 repro (`repro_gradient_white_icon.png`): a
    real diagonal purple -> pink -> orange gradient whose lightness (L*)
    barely correlates with position at all (measured r2 0.003) because the
    ramp is a hue rotation, not a lightness slope — the exact case
    `detect_ramp`'s single-channel (L-only) fit would miss. The b* channel
    carries it (measured r2 0.45, direction ~45 degrees off-axis); this must
    find that and return the perpendicular row angle, not decline."""
    from digitizer_core.stage1_prep import prep

    # Background-existence guards off (2026-08-11): at defaults the guards now
    # correctly refuse to flood this full-bleed fixture, which changes prep's
    # design mask and dilutes the b* fit. The detector's math is what's pinned
    # here, on the exact prep state of the 2026-08-03 diagnosis — same pattern
    # as test_enclosed_background.py / test_thread_revalidate.py.
    p = prep(str(PHOTO_DIR / "repro_gradient_white_icon.png"),
             PipelineConfig(target_width_mm=90.0,
                            bg_border_agreement_min=0.0, bg_border_rival_min=0.0))
    angle = detect_design_ramp_angle(p)
    assert angle is not None
    # Expected row angle: perpendicular to the ~45 degree diagonal, i.e. also
    # ~45 degrees off-axis (a line's perpendicular here lands on the other
    # 45-degree diagonal, which is the same absolute angle mod 90 for a
    # perfect diagonal) — checked as a LINE (mod 180), with real margin.
    assert _angle_diff_deg(angle, 135.0) <= 5.0, angle


def test_detect_design_ramp_angle_declines_on_a_radial_design():
    """A radial ramp has no single line direction — the whole-design fit
    must recognize that (radial explains the color far better than any
    linear direction does) and decline, leaving every fragment's angle to
    fall back to its own per-region default, exactly as before this fix."""
    from digitizer_core.stage1_prep import prep

    p = prep(str(PHOTO_DIR / "gradient_ramp_radial.png"), PipelineConfig(target_width_mm=90.0))
    assert detect_design_ramp_angle(p) is None


def test_detect_design_ramp_angle_declines_on_pure_noise(tmp_path):
    """Random per-pixel color has no coherent spatial ramp in any channel —
    this must decline rather than manufacture a direction out of noise.

    Not tested here: an ordinary FLAT multi-color logo (a handful of solid
    blobs at fixed positions) can spuriously clear the R2 gate on one Lab
    channel by the same small-N-regression coincidence a per-region
    `detect_ramp` call is already exposed to (measured: `logo_whitebg.png`'s
    a* channel fits position at r2 0.61). This is not a new risk this fix
    introduces — both detectors share the one guard that actually matters in
    production: `pipeline.run_stages` only ever calls either of them when
    stage 0 has classified the whole design `gradient` in the first place.
    """
    from digitizer_core.stage1_prep import prep

    rng = np.random.default_rng(7)
    # A solid border frame so `prep`'s background flood has a clear color to
    # key off; noise fills the interior, the part this test actually probes.
    noise = rng.integers(0, 256, size=(200, 200, 3), dtype=np.uint8)
    noise[:10, :] = noise[-10:, :] = noise[:, :10] = noise[:, -10:] = 255
    path = tmp_path / "noise.png"
    cv2.imwrite(str(path), cv2.cvtColor(noise, cv2.COLOR_RGB2BGR))
    p = prep(str(path), PipelineConfig(target_width_mm=20.0))
    assert detect_design_ramp_angle(p) is None


def test_gradient_fragments_share_one_fill_angle_end_to_end():
    """The actual reported defect, reproduced and closed end to end: this
    gradient's stage-2 segmentation (`stage2_photo_segment`'s SLIC+RAG as of
    2026-08-04 — see that module's own docstring; plain k-means before that)
    still cuts it into several independent-color regions, but every one of
    those fragments must sew its fill rows at the SAME angle instead of each
    picking its own — the "patchwork of differently angled wedges" Kent's
    real-world test surfaced. Geometry is measured from emitted stitches
    (see module docstring), not from any parameter.

    **Below-floor fragments excluded, 2026-08-04:** SLIC+RAG can leave a
    couple of genuinely tiny (~4.5mm2, single fill row, ~22 stitch points)
    leftover slivers plain k-means's own fragment population on this
    fixture never happened to produce. Their `angle_deg` parameter IS the
    shared design angle (verified directly: `detect_ramp` declines on both,
    same fallback branch as every other fragment) — what differs is that
    `_dominant_angle_deg`'s length-weighted circular mean, recovering an
    angle from only ~1-2 short rows plus their boundary-following turns, is
    not a reliable instrument at this scale; the turns are proportionally
    significant enough to pull the measured angle a couple of degrees off
    the true one even though the correct angle was actually sewn. The real
    (large, visible) fragments below measure 590-1358mm2 / 745-1506 points
    each — an unambiguous population gap from the ~4.5mm2 / 22-point pair,
    so `_MIN_FRAGMENT_MM2` sits with wide margin on both sides, the same
    "measure the real population, don't just relax a number" reasoning this
    suite already uses elsewhere.
    """
    from digitizer_core.pipeline import plan_stitches, run_stages

    # Guards off for the same reason as the detector test above: the
    # fragmentation-plus-shared-angle scenario needs the diagnosis-time
    # flooded prep state, which the 2026-08-11 existence guards (correctly)
    # no longer produce at defaults on this full-bleed fixture.
    cfg = PipelineConfig(target_width_mm=90.0,
                         bg_border_agreement_min=0.0, bg_border_rival_min=0.0)
    result = run_stages(str(PHOTO_DIR / "repro_gradient_white_icon.png"), cfg)
    assert len(result.regions) > 1, "the fragmentation this fix works around must still repro"
    assert result.source_pixels is not None
    assert result.source_pixels.design_row_angle_deg is not None
    area_by_shape = {r.shape_id: r.area_mm2 for r in result.regions}

    plan = plan_stitches(result, cfg)
    by_shape: dict[str, list] = {}
    for block in plan.blocks:
        for run in block.runs:
            if run.kind != stitches.FILL:
                continue
            base = run.shape_id.split("-blend")[0]
            by_shape.setdefault(base, []).append(run)

    _MIN_FRAGMENT_MM2 = 25.0   # see the docstring's measured population gap
    measurable = {
        sid: runs for sid, runs in by_shape.items()
        if area_by_shape.get(sid, 0.0) >= _MIN_FRAGMENT_MM2
    }
    assert measurable, "no fragment large enough for the angle instrument to trust"
    assert len(measurable) >= 2, "need at least two measurable fragments to check angle agreement"
    angles = [_dominant_angle_deg(runs) for runs in measurable.values()]
    base_angle = angles[0]
    for a in angles[1:]:
        assert _angle_diff_deg(a, base_angle) <= 2.0, (
            f"fragment angle {a} deviates from {base_angle} — the patchwork defect is back"
        )


def test_blend_marks_jump_at_band_transitions():
    """2026-08-06 fix: adjacent shade bands are independent `stitch_shape`
    calls over different (overlapping) clips of the polygon, so a band's
    first run almost never starts where the previous band's last run
    ended — before this fix that boundary defaulted to `jump=False`, a bare
    straight stitch sewn across a real shade seam. Every band after the
    first must carry an explicit jump on its first run, with `trim` set
    correctly for the actual measured gap."""
    region = _linear_region()
    source = _linear_source()
    cfg = PipelineConfig()

    runs, report = blend_fill(region, source, cfg)
    layers = _layers_of(runs)
    assert len(layers) >= 3, "need at least two band transitions to be a real check"

    ordered = sorted(layers.items(), key=lambda kv: int(kv[0].rsplit("blend", 1)[1]))
    prev_end = None
    for sid, layer_runs in ordered:
        first = layer_runs[0]
        if prev_end is not None:
            d = math.dist(prev_end, first.points[0])
            assert first.jump is True, f"{sid}: first run must jump from the previous band"
            assert first.trim == (d > machine.TRIM_AT_MM), (
                f"{sid}: trim {first.trim} doesn't match measured gap {d}"
            )
        prev_end = layer_runs[-1].points[-1]


def test_blend_marks_jump_between_multiple_parts_of_one_band(monkeypatch):
    """2026-08-06 fix, the other half: `_band_clip` can hand back more than
    one disconnected polygon for a single band (a ring-shaped region
    straddling the ramp's hole, for instance) -- forced here via monkeypatch
    since neither committed fixture has that topology. Only the FIRST
    band's clip is overridden with two rectangles 10mm apart; every later
    band still gets the real (single-part) clip from the actual ramp model,
    so this only probes the specific branch under test."""
    import digitizer_core.stage6_blend as blend_mod

    region = _linear_region()
    source = _linear_source()
    cfg = PipelineConfig()

    real_band_clip = blend_mod._band_clip
    part_a = Polygon([(-40, -40), (-30, -40), (-30, -30), (-40, -30)])
    part_b = Polygon([(-20, -40), (-10, -40), (-10, -30), (-20, -30)])
    calls = {"n": 0}

    def fake_band_clip(poly, model, t_lo, t_hi):
        calls["n"] += 1
        if calls["n"] == 1:
            return [part_a, part_b]
        return real_band_clip(poly, model, t_lo, t_hi)

    monkeypatch.setattr(blend_mod, "_band_clip", fake_band_clip)

    runs, report = blend_fill(region, source, cfg)
    first_layer = _layers_of(runs)[f"{region.shape_id}-blend0"]
    assert len(first_layer) >= 2, "two disjoint parts must produce at least two runs"

    # The two rectangles' nearest edges are 10mm apart -- far past
    # TRIM_AT_MM and far past any ordinary row-to-row turn inside either
    # 10x10mm square -- so exactly one run-to-run gap in this layer should
    # be that large: the part seam.
    seams = [
        i for i in range(1, len(first_layer))
        if math.dist(first_layer[i - 1].points[-1], first_layer[i].points[0]) >= 8.0
    ]
    assert len(seams) == 1, f"expected exactly one part seam, found {seams}"
    seam_run = first_layer[seams[0]]
    assert seam_run.jump is True, "the part transition must be an explicit jump"
    assert seam_run.trim is True, "a >TRIM_AT_MM gap between parts must trim"


def test_blend_determinism():
    """No RNG surprises: the same region and pixels blend the same way twice."""
    region = _linear_region()
    source = _linear_source()
    cfg = PipelineConfig()
    a, a_report = blend_fill(region, source, cfg)
    b, b_report = blend_fill(region, source, cfg)
    assert [r.points for r in a] == [r.points for r in b]
    assert [r.shape_id for r in a] == [r.shape_id for r in b]
    assert a_report == b_report


def test_blend_debug_artifacts_are_written_when_requested(tmp_path):
    """`stage6_blend_shades.png` (the swatch strip) and `stage6_blend_rows.png`
    (the pre-merge interleaved layers) land in `cfg.debug_dir` on a fixture
    known to detect as a ramp — the direct test for deliverable #3, run where
    `detect_ramp` is guaranteed to fire so the artifact-writing path is
    actually exercised, not just reachable in principle."""
    region = _linear_region()
    source = _linear_source()
    cfg = PipelineConfig(debug_dir=str(tmp_path))
    assert detect_ramp(region.polygon, source) is not None

    runs, report = blend_fill(region, source, cfg)
    assert report["empty"] is False
    n_shades = len(_layers_of(runs))

    shades_path = tmp_path / "stage6_blend_shades.png"
    rows_path = tmp_path / "stage6_blend_rows.png"
    assert shades_path.is_file()
    assert rows_path.is_file()

    swatch = cv2.imread(str(shades_path))
    assert swatch is not None
    # One square swatch per shade, side by side.
    assert swatch.shape[1] == swatch.shape[0] * n_shades

    rows_img = cv2.imread(str(rows_path))
    assert rows_img is not None
    # Not a blank canvas: the row render actually drew something.
    assert rows_img.min() < 250


def test_drone_render_ab_debug_artifacts(tmp_path):
    """The plan's acceptance gate for the founding complaint (drone_render.png,
    the hat that came out as flat-quantized mush) is a human-reviewed debug
    render, not a pixel-diff. What's mechanically testable here is that a
    gradient pass over that real photographic art runs end to end without
    crashing and produces stitches — ramp or fallback, both are legitimate
    outcomes for a rectangle bounding a real photo (steps 3+ build the real
    photo region-former; this stage only owns what happens once a region is
    handed to it). `test_blend_debug_artifacts_are_written_when_requested`
    above is the direct test that the debug pair gets written; this test
    additionally confirms the artifact call is reached (or safely skipped)
    on real, not synthetic, pixels.
    """
    from digitizer_core.stage1_prep import prep

    cfg = PipelineConfig(target_width_mm=90.0, debug_dir=str(tmp_path))
    p = prep(str(PHOTO_DIR / "drone_render.png"), cfg)

    x0, y0, x1, y1 = p.art_bbox
    cx = (x0 + x1) / 2.0
    cy = (y0 + y1) / 2.0
    poly = Polygon([
        ((x0 - cx) / p.px_per_mm, (y0 - cy) / p.px_per_mm),
        ((x1 - cx) / p.px_per_mm, (y0 - cy) / p.px_per_mm),
        ((x1 - cx) / p.px_per_mm, (y1 - cy) / p.px_per_mm),
        ((x0 - cx) / p.px_per_mm, (y1 - cy) / p.px_per_mm),
    ])
    region = Region(shape_id="Sdrone", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)
    source = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm, origin_px=(cx, cy))

    runs, report = blend_fill(region, source, cfg)
    assert runs, "the drone render must produce stitches, gradient or fallback"
    assert report["empty"] is False

    shades_png = tmp_path / "stage6_blend_shades.png"
    if detect_ramp(poly, source) is not None:
        # Only a genuine ramp emits the blend debug pair; a fallback to
        # ordinary tatami on this art would be news worth its own look, not
        # a silent pass, so it is not asserted away here.
        assert shades_png.is_file()
        assert (tmp_path / "stage6_blend_rows.png").is_file()
        swatch = cv2.imread(str(shades_png))
        assert swatch is not None
        n_shades = len(_layers_of(runs))
        assert 3 <= n_shades <= 5
        assert swatch.shape[1] == swatch.shape[0] * n_shades


# --- start_near (2026-08-31, sew-out fragmentation follow-up) ---------------
# The gradient lane silently dropped the sew cursor: stage 7's picking loop
# hands every tier `entry` ("where the needle already is"), and blend_fill's
# two stitch_shape call sites passed nothing — so every gradient-class
# region entered at its own geometry-default corner however far the needle
# was. Measured on repro_gradient_white_icon.png at 80 mm: a 72.0 mm hop
# into one shape and 46 mm into another, inside single colour blocks.


def test_blend_fallback_honors_start_near():
    """The fallback tatami path (every k-means fragment of a real gradient
    takes it) must enter near the needle, exactly like the plain-tatami tier
    stage 7 calls directly."""
    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise = rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8)
    source = SourcePixels(rgb=noise, px_per_mm=4.0, origin_px=(80.0, 60.0))
    region = Region(shape_id="Snoise", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)
    assert detect_ramp(poly, source) is None

    cfg = PipelineConfig()
    near_a, _ = blend_fill(region, source, cfg, start_near=(0.0, 0.0))
    near_b, _ = blend_fill(region, source, cfg, start_near=(30.0, 20.0))
    a0, b0 = near_a[0].points[0], near_b[0].points[0]
    assert math.dist(a0, (0.0, 0.0)) < math.dist(b0, (0.0, 0.0))
    assert math.dist(b0, (30.0, 20.0)) < math.dist(a0, (30.0, 20.0))

    # And the geometry itself is the fallback's own: same rows, entered from
    # the requested side, byte-identical to what plain tatami does with the
    # same entry.
    expected, _ = stitch_shape(
        poly, region.shape_id, angle_deg=None, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style="none",
        trim_at_mm=machine.TRIM_AT_MM, start_near=(0.0, 0.0))
    assert [r.points for r in near_a] == [r.points for r in expected]


def test_blend_bands_chain_and_honor_start_near():
    """Decomposed bands: the FIRST band enters near the caller's cursor, and
    every later band enters near wherever the previous band's stitching
    ended, instead of each stitch_shape call starting at its own
    geometry-default corner."""
    region, source = _linear_region(), _linear_source()
    cfg = PipelineConfig()
    x0, y0, x1, y1 = region.polygon.bounds

    runs_a, report = blend_fill(region, source, cfg, start_near=(x0, y0))
    runs_b, _ = blend_fill(region, source, cfg, start_near=(x1, y1))
    assert report["blend_shades"] > 1, "fixture must decompose for this test"
    a0, b0 = runs_a[0].points[0], runs_b[0].points[0]
    assert math.dist(a0, (x0, y0)) < math.dist(b0, (x0, y0))

    # The discriminating half: band 0's two different entries leave the
    # needle at two different exits, and CHAINING means band 1 must respond
    # to that — enter differently in the two calls. The pre-fix code sewed
    # every band from its own fixed geometry default, byte-identical in
    # both calls no matter where the needle was.
    la, lb = _layers_of(runs_a), _layers_of(runs_b)
    band1 = f"{region.shape_id}-blend1"
    assert la[band1][0].points[0] != lb[band1][0].points[0]

    # Band boundaries chain: at every marked band seam, the entry chosen is
    # no farther from the previous stitch than the band's own far corner —
    # i.e. the seam gap stays under the band strip's own breadth instead of
    # flying to a fixed corner. Checked structurally: each band's first run
    # must start strictly nearer the previous band's exit than the WORST
    # entry the same band offers (its farthest stitch point).
    layers = _layers_of(runs_a)
    ids = sorted(layers, key=lambda s: int(s.rsplit("-blend", 1)[1]))
    prev_end = None
    for sid in ids:
        band_runs = layers[sid]
        first = band_runs[0].points[0]
        if prev_end is not None:
            pts = [p for r in band_runs for p in r.points]
            worst = max(math.dist(prev_end, p) for p in pts)
            assert math.dist(prev_end, first) < worst
        prev_end = band_runs[-1].points[-1]


# --- Seams between shade bands (2026-09-03, Kent's seam ruling) ------------

def _layer_extents_along_ramp(runs):
    """-> {layer_id: (lo, hi)} projections onto the ramp axis, the axis being
    the line from the darkest layer's centroid to the lightest's (by the L*
    of the layer's own snapped thread), so the test needs no ramp model."""
    from digitizer_core.threads import CHART
    layers = _layers_of(runs)
    lstar = {}
    pts = {}
    for sid, lr in layers.items():
        idx = next(r.shade_thread_index for r in lr if r.shade_thread_index is not None)
        lstar[sid] = float(CHART.lab[idx][0])
        pts[sid] = np.array([p for r in lr for p in r.points], float)
    dark = min(lstar, key=lstar.get)
    light = max(lstar, key=lstar.get)
    axis = pts[light].mean(axis=0) - pts[dark].mean(axis=0)
    axis /= np.linalg.norm(axis)
    return {sid: (float((pts[sid] @ axis).min()), float((pts[sid] @ axis).max())) for sid in layers}, lstar


def test_the_earlier_darker_band_reaches_under_the_lighter_one_by_overlap_mm():
    """Stage 5's seam rule applied inside a blend: at every band seam the
    band that sews first (darker by chart L*) extends `overlap_mm` toward
    the lighter band, and the lighter band stays on its own boundary.
    Measured as extents along the ramp axis, overlap 0.25 against 0.0."""
    region, source = _linear_region(), _linear_source()
    on, _ = blend_fill(region, source, PipelineConfig(overlap_mm=0.25))
    off, _ = blend_fill(region, source, PipelineConfig(overlap_mm=0.0))
    ext_on, lstar = _layer_extents_along_ramp(on)
    ext_off, _ = _layer_extents_along_ramp(off)
    assert set(ext_on) == set(ext_off)
    order = sorted(ext_on, key=lambda s: ext_off[s][0])          # dark end first along the axis
    darkest, lightest = order[0], order[-1]
    assert lstar[darkest] < lstar[lightest]
    # Every band but the lightest sews before its lighter neighbour: its
    # light-side edge moves toward the light end by the overlap...
    for sid in order[:-1]:
        moved = ext_on[sid][1] - ext_off[sid][1]
        assert moved == pytest.approx(0.25, abs=0.12), (sid, moved)
    # ...and no band grows back toward the dark end (its first row may
    # re-phase forward by a fraction of a layer row, never extend backward).
    for sid in order[1:]:
        assert ext_on[sid][0] >= ext_off[sid][0] - 0.1, sid
    # The lightest band is last to sew and reaches nowhere (its far row may
    # re-phase by a fraction of a layer row; a reach would be the full 0.25).
    assert ext_on[lightest][1] == pytest.approx(ext_off[lightest][1], abs=0.1)


def test_overlap_zero_puts_bands_edge_to_edge():
    region, source = _linear_region(), _linear_source()
    runs, _ = blend_fill(region, source, PipelineConfig(overlap_mm=0.0))
    ext, _ = _layer_extents_along_ramp(runs)
    order = sorted(ext, key=lambda s: ext[s][0])
    for a, b in zip(order, order[1:]):
        assert ext[a][1] <= ext[b][0] + machine.FILL_ROW_MM + 0.05, (a, b)


# --- The design ramp (2026-09-03, Kent's gradient ruling) ---------------------

def _thread_mm(runs) -> float:
    return sum(math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:]))


def test_band_clip_is_anchored_on_the_ramp_not_the_region_centre():
    """A linear ramp's band strip used to be anchored on the polygon's bbox
    centre, so a region whose centre projects off the origin along the ramp
    had its bands shifted by that projection: the fixture region moved 30 mm
    along its ramp clipped its first band to nothing and sewed a third less
    thread. Moving the region and the raster together must change nothing
    but position."""
    from shapely.affinity import translate

    region, source = _linear_region(), _linear_source()
    cfg = PipelineConfig()
    base_runs, base_report = blend_fill(region, source, cfg)
    base_mm = _thread_mm(base_runs)
    for dx, dy in [(30.0, 0.0), (0.0, 25.0), (30.0, 25.0)]:
        poly = translate(region.polygon, dx, dy)
        moved = Region(shape_id="Sramp", polygon=poly, thread_index=0,
                       thread_number=CHART[0].number, area_mm2=poly.area)
        ox, oy = source.origin_px
        moved_source = SourcePixels(
            rgb=source.rgb, px_per_mm=source.px_per_mm,
            origin_px=(ox - dx * source.px_per_mm, oy - dy * source.px_per_mm))
        runs, report = blend_fill(moved, moved_source, cfg)
        assert report["blend_shades"] == base_report["blend_shades"]
        assert len(_layers_of(runs)) == len(_layers_of(base_runs)), (dx, dy)
        assert _thread_mm(runs) == pytest.approx(base_mm, rel=0.02), (dx, dy)


def _fixture_design_ramp():
    """The linear fixture's own design ramp, in the tests' SourcePixels frame."""
    from digitizer_core.design_ramp import fit_design_ramp_pixels

    rgb = _load_rgb("gradient_ramp_linear.png")
    fg = np.zeros(rgb.shape[:2], bool)
    fg[_MARGIN:_H - _MARGIN, _MARGIN:_W - _MARGIN] = True
    ramp = fit_design_ramp_pixels(rgb, fg, _PX_PER_MM)
    assert ramp is not None
    return ramp.shifted(_ORIGIN_PX[0] / _PX_PER_MM, _ORIGIN_PX[1] / _PX_PER_MM)


def _design_source() -> SourcePixels:
    ramp = _fixture_design_ramp()
    return SourcePixels(rgb=_load_rgb("gradient_ramp_linear.png"),
                        px_per_mm=_PX_PER_MM, origin_px=_ORIGIN_PX,
                        design_row_angle_deg=ramp.row_angle_deg(),
                        design_ramp=ramp, gradient_class=True)


def _halves(poly: Polygon) -> tuple[Polygon, Polygon]:
    minx, miny, maxx, maxy = poly.bounds
    midy = (miny + maxy) / 2.0
    top = poly.intersection(Polygon([(minx, miny), (maxx, miny), (maxx, midy), (minx, midy)]))
    bottom = poly.intersection(Polygon([(minx, midy), (maxx, midy), (maxx, maxy), (minx, maxy)]))
    return top, bottom


def test_pieces_of_one_design_ramp_share_bands_and_threads():
    """Two pieces of one sweep (the fixture cut across the ramp) sewn with
    the design's bands: the same shade count, the same threads, and each
    thread's rows spanning the same interval along the ramp in both pieces —
    what makes a ramp an icon cuts into pieces read as one sweep."""
    source = _design_source()
    ramp = source.design_ramp
    cfg = PipelineConfig()
    top, bottom = _halves(_linear_region().polygon)
    reports = {}
    extents = {}
    for name, poly in (("top", top), ("bottom", bottom)):
        region = Region(shape_id=f"S{name}", polygon=poly, thread_index=0,
                        thread_number=CHART[0].number, area_mm2=poly.area)
        runs, report = blend_fill(region, source, cfg)
        assert report["blend_design_ramp"] is True
        assert report["blend_shades"] >= 3
        reports[name] = report
        by_thread: dict[int, list[float]] = {}
        for r in runs:
            if r.kind != stitches.FILL:
                continue
            proj = [ramp.raw(x, y) for x, y in r.points]
            by_thread.setdefault(r.shade_thread_index, []).extend(proj)
        extents[name] = {k: (min(v), max(v)) for k, v in by_thread.items()}
    assert reports["top"]["blend_shades"] == reports["bottom"]["blend_shades"]
    assert set(extents["top"]) == set(extents["bottom"])
    for thread, (lo, hi) in extents["top"].items():
        blo, bhi = extents["bottom"][thread]
        assert lo == pytest.approx(blo, abs=machine.FILL_ROW_MM + 0.05), thread
        assert hi == pytest.approx(bhi, abs=machine.FILL_ROW_MM + 0.05), thread


def test_a_region_off_the_design_ramp_takes_the_per_region_path():
    """The icon: a flat white region on a design whose ramp fits does not
    ride it — its pixels sit far off the ramp's planes — and sews exactly
    as it did before the design ramp existed (here: not a ramp, tatami)."""
    source = _design_source()
    white = SourcePixels(rgb=np.full_like(source.rgb, 255), px_per_mm=_PX_PER_MM,
                         origin_px=_ORIGIN_PX, design_row_angle_deg=source.design_row_angle_deg,
                         design_ramp=source.design_ramp, gradient_class=True)
    region = _linear_region()
    runs, report = blend_fill(region, white, PipelineConfig())
    assert runs
    assert report["blend_shades"] == 0
    assert report.get("blend_design_ramp", False) is False


def test_blend_bands_sew_at_the_fill_row():
    """Since 2026-09-03 every band is a fill at the fill row; until then the
    bands sewed at `FILL_ROW_MM * n`, a third to a fifth of a fill."""
    region, source = _linear_region(), _linear_source()
    runs, _ = blend_fill(region, source, PipelineConfig())
    angle = principal_angle_deg(region.polygon)
    for sid, layer_runs in _layers_of(runs).items():
        for g in _row_spacings_mm(layer_runs, angle):
            assert g == pytest.approx(machine.FILL_ROW_MM, abs=0.02), sid


def test_a_linear_ramp_design_is_sewn_everywhere_end_to_end():
    """The in-situ form of the band-clip defect: `gradient_ramp_linear.png`
    at 80 mm segments into regions centred off the origin, and on the
    2026-08-02 engine their bands were clipped against the region centre —
    46% of the ramp was more than 1 mm from any thread and the middle of
    the design was blank (audit, 2026-09-04). Every unit fixture is centred,
    so only a whole-design run can see it: no part of the stitched artwork
    may sit further than a fill row and a half from a fill stitch."""
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(str(PHOTO_DIR / "gradient_ramp_linear.png"), cfg)
    plan = plan_stitches(result, cfg)
    fills = [LineString(r.points) for _b, r in plan.iter_runs()
             if r.kind == stitches.FILL and len(r.points) >= 2]
    assert fills
    sewn = unary_union([f.buffer(1.5 * machine.FILL_ROW_MM) for f in fills])
    art = unary_union([r.polygon for r in result.regions if r.meta.get("stitched", True)])
    bare = art.difference(sewn)
    assert bare.area <= 0.01 * art.area, f"{bare.area:.1f} mm² of {art.area:.1f} never sewn"


def test_the_end_bands_absorb_a_region_that_reaches_past_the_design_range():
    """On the design path `model.lo/hi` are the design's, and a region can
    reach past them. The first and last bands take the overshoot; nothing
    of the polygon is left in no band (review, 2026-09-04: a clamp at 0 / 1
    left 3% of the repro's frame piece unsewn)."""
    from dataclasses import replace
    from shapely.ops import unary_union

    source = _design_source()
    ramp = source.design_ramp
    shrunk = replace(ramp, lo=ramp.lo + 3.0, hi=ramp.hi - 3.0)
    source = SourcePixels(rgb=source.rgb, px_per_mm=source.px_per_mm, origin_px=source.origin_px,
                          design_row_angle_deg=source.design_row_angle_deg,
                          design_ramp=shrunk, gradient_class=True)
    region = _linear_region()
    runs, report = blend_fill(region, source, PipelineConfig())
    assert report["blend_design_ramp"] is True
    from shapely.geometry import LineString
    fills = [LineString(r.points) for r in runs if r.kind == stitches.FILL and len(r.points) >= 2]
    sewn = unary_union([f.buffer(1.5 * machine.FILL_ROW_MM) for f in fills])
    bare = region.polygon.difference(sewn)
    assert bare.area <= 0.01 * region.polygon.area, bare.area


def test_a_region_that_rides_the_design_ramp_is_never_sewn_as_satin():
    """The repro's outer strip — a 3.5 mm ring of the sweep beyond the white
    frame — classifies as a satin ribbon. Sewn as satin it is one thread all
    the way round, fuchsia where the source turns orange (render,
    2026-09-04). A riding region falls through the satin rung to the sweep's
    bands; the white ring, which does not ride, keeps its satin."""
    from digitizer_core.pipeline import plan_stitches, run_stages
    from digitizer_core.stage6_blend import region_rides_design_ramp

    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(str(PHOTO_DIR / "repro_gradient_white_icon.png"), cfg)
    assert result.source_pixels is not None and result.source_pixels.design_ramp is not None
    plan = plan_stitches(result, cfg)
    kinds: dict[str, set] = {}
    shaded: dict[str, bool] = {}
    for _b, r in plan.iter_runs():
        base = r.shape_id.split("-blend")[0]
        kinds.setdefault(base, set()).add(r.kind)
        shaded[base] = shaded.get(base, False) or r.shade_thread_index is not None
    riders = [r for r in result.regions
              if r.meta.get("stitched", True) and r.area_mm2 >= 100.0
              and region_rides_design_ramp(r.polygon, result.source_pixels)]
    assert len(riders) >= 3, [r.shape_id for r in riders]
    for r in riders:
        assert stitches.SATIN not in kinds.get(r.shape_id, set()), r.shape_id
        assert shaded.get(r.shape_id), f"{r.shape_id} rides but sewed no shade band"
    non_riders = [r for r in result.regions if r.meta.get("stitched", True)
                  and r.area_mm2 >= 100.0 and r not in riders]
    assert any(stitches.SATIN in kinds.get(r.shape_id, set()) for r in non_riders), \
        "the white ring should still be satin"
