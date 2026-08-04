"""Stage 6 — the scan-line mono tonal tier (photo plan, technique row 8).

House rule, same as `test_stage6_blend.py`: every geometric claim is measured
from EMITTED stitches, never from the parameters `scanline_fill` was called
with. A darkness→density mapping that silently stopped modulating anything
would sail through a test that re-checked its own constants.

The ramp fixture is synthetic and built in-test (goldens must not depend on
found photographs): a vertical luminance ramp, near-white at the top to
near-black at the bottom, so horizontal scan rows each see ~constant darkness
and per-strip measurements are clean.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import machine, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_scanline import (
    SCANLINE_LEVEL_DARKNESS,
    SCANLINE_ROW_MM,
    scanline_fill,
)
from digitizer_core.threads import CHART

HERE = Path(__file__).resolve().parent
PHOTO_DIR = HERE.parent / "testdata" / "photo"

_PX_PER_MM = 4.0
_RECT_W_MM = 90.0
_RECT_H_MM = 60.0


def _flat_source(gray: int, w_px: int = 400, h_px: int = 280) -> SourcePixels:
    rgb = np.full((h_px, w_px, 3), gray, np.uint8)
    return SourcePixels(rgb=rgb, px_per_mm=_PX_PER_MM,
                        origin_px=(w_px / 2.0, h_px / 2.0))


def _ramp_source(lo: int = 250, hi: int = 8, w_px: int = 400, h_px: int = 280) -> SourcePixels:
    """Vertical luminance ramp: gray `lo` on the top row of pixels down to
    `hi` on the bottom row — light at top, dark at bottom, y-down."""
    col = np.linspace(lo, hi, h_px).round().astype(np.uint8)
    gray = np.tile(col[:, None], (1, w_px))
    rgb = np.stack([gray] * 3, axis=-1)
    return SourcePixels(rgb=rgb, px_per_mm=_PX_PER_MM,
                        origin_px=(w_px / 2.0, h_px / 2.0))


def _rect_region() -> Region:
    hw, hh = _RECT_W_MM / 2.0, _RECT_H_MM / 2.0
    poly = Polygon([(-hw, -hh), (hw, -hh), (hw, hh), (-hw, hh)])
    return Region(shape_id="Sscan", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area)


def _fill_runs(runs):
    return [r for r in runs if r.kind == stitches.FILL]


def _strip_thread_density(runs, y0: float, y1: float, strip_area_mm2: float) -> float:
    """Sewn thread length per mm² inside the horizontal strip [y0, y1),
    measured from emitted FILL stitch segments (segment counted by its
    midpoint)."""
    total = 0.0
    for r in _fill_runs(runs):
        for a, b in zip(r.points, r.points[1:]):
            my = (a[1] + b[1]) / 2.0
            if y0 <= my < y1:
                total += math.dist(a, b)
    return total / strip_area_mm2


def _strip_penetration_density(runs, y0: float, y1: float, strip_area_mm2: float) -> float:
    count = 0
    for r in _fill_runs(runs):
        for x, y in r.points:
            if y0 <= y < y1:
                count += 1
    return count / strip_area_mm2


def _strip_mean_zigzag_dy(runs, y0: float, y1: float) -> float:
    """Mean |dy| between consecutive penetrations of one run inside the strip
    — the emitted zigzag amplitude signature (a zigzag's |dy| is 2×amp; a
    flat run's is ~0)."""
    dys = []
    for r in _fill_runs(runs):
        for a, b in zip(r.points, r.points[1:]):
            my = (a[1] + b[1]) / 2.0
            if y0 <= my < y1:
                dys.append(abs(b[1] - a[1]))
    return float(np.mean(dys)) if dys else 0.0


def _run_row_ys(runs) -> list[float]:
    """One y per emitted FILL run — each run is a single row segment, so its
    points' mean y sits on the row centerline (zigzag offsets cancel)."""
    ys = []
    for r in _fill_runs(runs):
        ys.append(float(np.mean([p[1] for p in r.points])))
    return sorted(ys)


def test_ramp_darkness_drives_density_and_amplitude_monotonically():
    """The tier's whole contract: darker fabric gets more thread. Thread
    length per area, penetration density AND zigzag amplitude must all rise
    from the light end of the ramp to the dark end, measured from emitted
    stitch geometry."""
    region = _rect_region()
    source = _ramp_source()
    runs, report = scanline_fill(region, source, PipelineConfig())
    assert runs, "the ramp must produce stitches"
    assert report["empty"] is False

    hh = _RECT_H_MM / 2.0
    n_strips = 6
    strip_h = _RECT_H_MM / n_strips
    strip_area = _RECT_W_MM * strip_h
    densities = []
    for k in range(n_strips):
        y0 = -hh + k * strip_h
        densities.append(_strip_thread_density(runs, y0, y0 + strip_h, strip_area))

    # Adjacent strips are allowed row-count quantization noise (a 10 mm
    # strip holds ~5.5 rows at the sparsest 1.8 mm spacing, so one row more
    # or less swings a strip ~18%); two strips apart the tone difference
    # dominates and the ordering must be strict.
    for a, b in zip(densities, densities[1:]):
        assert b >= a * 0.8, f"density fell along the ramp: {densities}"
    for a, b in zip(densities, densities[2:]):
        assert b > a, f"density not rising two strips apart: {densities}"
    # ... and strongly separated end to end.
    assert densities[-1] > 3.0 * max(densities[0], 1e-9), (
        f"dark end not measurably denser than light end: {densities}"
    )

    pen_light = _strip_penetration_density(runs, -hh, -hh + strip_h, strip_area)
    pen_dark = _strip_penetration_density(runs, hh - strip_h, hh, strip_area)
    assert pen_dark > 2.0 * max(pen_light, 1e-9), (
        f"penetration density did not rise: light {pen_light}, dark {pen_dark}"
    )

    amp_light = _strip_mean_zigzag_dy(runs, -hh, -hh + 2 * strip_h)
    amp_dark = _strip_mean_zigzag_dy(runs, hh - 2 * strip_h, hh)
    assert amp_dark > amp_light + 0.3, (
        f"zigzag amplitude did not rise: light {amp_light}, dark {amp_dark}"
    )


def test_ramp_stitch_budget_lands_in_the_mono_band():
    """Plan §1d: mono sketch/scan class ≈ 0.5–1.0 st/mm². Measured as emitted
    penetrations over the region's own area on the full ramp (which includes
    the near-white stretch that deliberately sews nothing — fabric is a
    value in this genre)."""
    region = _rect_region()
    source = _ramp_source()
    runs, _ = scanline_fill(region, source, PipelineConfig())
    count = sum(len(r.points) for r in _fill_runs(runs))
    density = count / region.polygon.area
    assert 0.4 <= density <= 1.1, f"st/mm² {density:.3f} outside the mono band"


def test_flat_midgray_is_uniform_and_respects_machine_floors():
    region = _rect_region()
    source = _flat_source(120)  # darkness ~0.53 -> the middle decimation level
    runs, report = scanline_fill(region, source, PipelineConfig())
    assert runs
    assert report["empty"] is False

    # Uniform tone -> uniform density across strips.
    hh = _RECT_H_MM / 2.0
    n_strips = 4
    strip_h = _RECT_H_MM / n_strips
    strip_area = _RECT_W_MM * strip_h
    densities = [
        _strip_thread_density(runs, -hh + k * strip_h, -hh + (k + 1) * strip_h, strip_area)
        for k in range(n_strips)
    ]
    mean = float(np.mean(densities))
    for d in densities:
        assert abs(d - mean) <= 0.15 * mean, f"flat tone sewed uneven strips: {densities}"

    # Rows sit on one uniform grid: consecutive distinct row centerlines one
    # decimation-level spacing apart (a multiple of the base row pitch).
    ys = _run_row_ys(runs)
    uniq = []
    for y in ys:
        if not uniq or y - uniq[-1] > SCANLINE_ROW_MM / 2.0:
            uniq.append(y)
    gaps = [b - a for a, b in zip(uniq, uniq[1:])]
    assert len(gaps) > 4
    expected = round(np.median(gaps) / SCANLINE_ROW_MM) * SCANLINE_ROW_MM
    # The first and last rows sit close enough to the shape's edge that
    # their outward zigzag offsets clamp to the centerline (see the
    # containment rule in _span_segments), which biases those two runs'
    # mean y — the INTERIOR grid is the thing that must be uniform.
    for g in gaps[1:-1]:
        assert g == pytest.approx(expected, abs=0.05), (
            f"uneven row grid on flat tone: {gaps}"
        )
    for g in (gaps[0], gaps[-1]):
        assert g == pytest.approx(expected, abs=0.3)

    # Machine floors, measured on every emitted stitch.
    for r in _fill_runs(runs):
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            assert d <= machine.MAX_STITCH_MM + 1e-6
            assert d >= machine.MIN_STITCH_MM - 1e-6, (
                f"stitch under the needle floor: {d}"
            )


def test_near_white_is_empty_and_the_report_is_honest():
    """Fabric-as-highlight: tone below the cutoff sews nothing at all, and
    the report says so instead of pretending."""
    region = _rect_region()
    runs, report = scanline_fill(region, _flat_source(250), PipelineConfig())
    assert runs == []
    assert report["empty"] is True
    assert report["jumps"] == 0


def test_just_above_cutoff_is_sparse_not_dense():
    region = _rect_region()
    cutoff = SCANLINE_LEVEL_DARKNESS[0]
    gray = int(round(255 * (1.0 - cutoff))) - 6  # a hair darker than the cutoff
    runs, report = scanline_fill(region, _flat_source(gray), PipelineConfig())
    assert runs, "tone just past the cutoff must sew a sparse pass, not nothing"
    assert report["empty"] is False
    count = sum(len(r.points) for r in _fill_runs(runs))
    density = count / region.polygon.area
    assert 0.0 < density < 0.3, f"near-white should be sparse, measured {density:.3f}"


def test_determinism():
    region = _rect_region()
    source = _ramp_source()
    cfg = PipelineConfig()
    a, a_report = scanline_fill(region, source, cfg)
    b, b_report = scanline_fill(region, source, cfg)
    assert [r.points for r in a] == [r.points for r in b]
    assert [r.kind for r in a] == [r.kind for r in b]
    assert a_report == b_report


def test_every_stitch_stays_inside_the_shape():
    """Rows, zigzag offsets and travel bridges all live inside the polygon
    (hair of slack for float noise, same tolerance the fill's travel test
    uses)."""
    region = _rect_region()
    source = _ramp_source()
    runs, _ = scanline_fill(region, source, PipelineConfig())
    room = region.polygon.buffer(0.05)
    from shapely.geometry import Point
    for r in runs:
        for x, y in r.points:
            assert room.covers(Point(x, y)), f"stitch escaped the shape: {(x, y)}"


def test_angle_config_turns_the_grain():
    """cfg.fill_angle_deg turns the scan grain; the emitted rows' dominant
    direction must follow it (measured length-weighted from the stitches)."""
    region = _rect_region()
    source = _ramp_source()
    runs, _ = scanline_fill(region, source, PipelineConfig(fill_angle_deg=30.0))
    sx = sy = 0.0
    for r in _fill_runs(runs):
        for a, b in zip(r.points, r.points[1:]):
            dx, dy = b[0] - a[0], b[1] - a[1]
            length = math.hypot(dx, dy)
            if length < 1e-9:
                continue
            theta2 = 2.0 * math.atan2(dy, dx)
            sx += math.cos(theta2) * length
            sy += math.sin(theta2) * length
    dominant = math.degrees(math.atan2(sy, sx)) / 2.0
    diff = abs(dominant - 30.0) % 180.0
    assert min(diff, 180.0 - diff) <= 3.0, f"grain angle {dominant} != 30"


def test_debug_artifact_is_written_when_requested(tmp_path):
    region = _rect_region()
    source = _ramp_source()
    cfg = PipelineConfig(debug_dir=str(tmp_path))
    runs, _ = scanline_fill(region, source, cfg)
    assert runs
    out = tmp_path / "stage6_scanline_rows.png"
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    assert img.min() < 250, "the render drew nothing"


def test_drone_render_debugviz_smoke(tmp_path):
    """The human-judgeable render on real art: the tier runs end to end over
    `drone_render.png`'s bbox and writes its debug render. What the picture
    LOOKS like is Kent's call, not an assertion's."""
    from digitizer_core.stage1_prep import prep

    cfg = PipelineConfig(target_width_mm=90.0, debug_dir=str(tmp_path))
    p = prep(str(PHOTO_DIR / "drone_render.png"), cfg)
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    poly = Polygon([
        ((x0 - cx) / p.px_per_mm, (y0 - cy) / p.px_per_mm),
        ((x1 - cx) / p.px_per_mm, (y0 - cy) / p.px_per_mm),
        ((x1 - cx) / p.px_per_mm, (y1 - cy) / p.px_per_mm),
        ((x0 - cx) / p.px_per_mm, (y1 - cy) / p.px_per_mm),
    ])
    region = Region(shape_id="Sdrone", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)
    source = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm, origin_px=(cx, cy))
    runs, report = scanline_fill(region, source, cfg)
    assert runs, "real art must produce stitches"
    assert report["empty"] is False
    assert (tmp_path / "stage6_scanline_rows.png").is_file()


# --- The opt-in wiring (config -> pipeline -> stage 7) -----------------------

LOGO = HERE.parent / "testdata" / "logo_whitebg.png"


def test_pipeline_plumbs_source_pixels_only_on_explicit_opt_in():
    from digitizer_core.pipeline import run_stages

    on = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        fill_technique="scanline_tonal"))
    assert on.source_pixels is not None, (
        "explicit scanline_tonal opt-in must carry source pixels through"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when the flag is off"
    )


def test_scanline_plan_differs_from_tatami_and_off_is_identical():
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="scanline_tonal")
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    result_on = run_stages(str(LOGO), cfg_on)
    plan_on = plan_stitches(result_on, cfg_on)
    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points) for b in plan.blocks for r in b.runs]

    assert all_points(plan_on) != all_points(plan_off), (
        "opt-in produced the same stitches as tatami — the tier never ran"
    )
    # Never-drop-artwork: every stitched region still put thread down.
    assert plan_on.blocks
    assert sum(len(b.runs) for b in plan_on.blocks) > 0


def test_scanline_falls_back_to_tatami_when_it_produces_nothing():
    """The contour-tier contract, verbatim: a shape the technique cannot sew
    (here: source pixels all near-white, so the tonal tier honestly emits
    nothing) falls back to ordinary tatami rather than dropping artwork —
    and the fallback is byte-identical to what plain tatami would have sewn."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="scanline_tonal")
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    result_on = run_stages(str(LOGO), cfg_on)
    assert result_on.source_pixels is not None
    # Blind the tier: uniformly near-white pixels sew nothing, honestly.
    result_on.source_pixels.rgb = np.full_like(result_on.source_pixels.rgb, 252)
    plan_fallback = plan_stitches(result_on, cfg_on)

    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points) for b in plan.blocks for r in b.runs]

    assert all_points(plan_fallback) == all_points(plan_off), (
        "the tatami fallback must sew exactly what tatami would have"
    )
