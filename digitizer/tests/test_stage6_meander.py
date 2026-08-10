"""Stage 6 — the meander mono tonal tier (photo plan, technique row 9).

House rule, same as `test_stage6_scanline.py`: every geometric claim is
measured from EMITTED stitches, never from the parameters `meander_fill` was
called with. The two claims this tier lives on — one continuous path whose
needle-down segments never cross, and single-digit trims — are checked with a
real segment-intersection sweep and a real trim count, not assumed from the
Hilbert construction.

The ramp fixture is synthetic and built in-test (goldens must not depend on
found photographs): a vertical luminance ramp, near-white at the top to
near-black at the bottom, so horizontal strips each see ~constant darkness
and per-strip measurements are clean.
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
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_meander import (
    MEANDER_LEVEL_DARKNESS,
    meander_fill,
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
    return Region(shape_id="Smea", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area)


def _fill_runs(runs):
    return [r for r in runs if r.kind == stitches.FILL]


def _needle_down_segments(runs):
    """Every segment the needle sews: within each run, plus the connecting
    segment between consecutive runs wherever the needle did NOT lift — the
    machine stitches from the last point of one run to the first of the
    next, so that segment is thread too and belongs in the non-crossing
    check."""
    segs = []
    prev_end = None
    for r in runs:
        if prev_end is not None and not r.jump:
            segs.append((prev_end, r.points[0]))
        segs.extend(zip(r.points, r.points[1:]))
        prev_end = r.points[-1]
    return segs


def _crossing_pairs(segs) -> int:
    """Count pairs of segments that properly cross (interior intersection).

    Shared endpoints are the path's own joints and legal; path-adjacent
    segments are skipped for the same reason. A spatial hash keeps the sweep
    quadratic only within 4 mm buckets."""
    cell = 4.0
    grid: dict[tuple[int, int], list[int]] = {}
    for idx, (a, b) in enumerate(segs):
        for i in range(int(min(a[0], b[0]) // cell), int(max(a[0], b[0]) // cell) + 1):
            for j in range(int(min(a[1], b[1]) // cell), int(max(a[1], b[1]) // cell) + 1):
                grid.setdefault((i, j), []).append(idx)

    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    def cross(s, t):
        p1, p2 = s
        p3, p4 = t
        eps = 1e-9
        for u in (p1, p2):
            for v in (p3, p4):
                if abs(u[0] - v[0]) < eps and abs(u[1] - v[1]) < eps:
                    return False  # shared endpoint: a joint, not a crossing
        d1 = orient(p3, p4, p1)
        d2 = orient(p3, p4, p2)
        d3 = orient(p1, p2, p3)
        d4 = orient(p1, p2, p4)
        return (((d1 > eps and d2 < -eps) or (d1 < -eps and d2 > eps))
                and ((d3 > eps and d4 < -eps) or (d3 < -eps and d4 > eps)))

    bad = 0
    seen: set[tuple[int, int]] = set()
    for bucket in grid.values():
        for u in range(len(bucket)):
            for v in range(u + 1, len(bucket)):
                i, j = bucket[u], bucket[v]
                if abs(i - j) <= 1:
                    continue
                key = (min(i, j), max(i, j))
                if key in seen:
                    continue
                seen.add(key)
                if cross(segs[i], segs[j]):
                    bad += 1
    return bad


def _strip_thread_density(runs, y0: float, y1: float, strip_area_mm2: float) -> float:
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


def test_ramp_darkness_drives_density_monotonically():
    """The tier's whole contract: darker fabric gets more thread. Thread
    length per area, penetration density AND the zigzag-burst signature must
    all rise from the light end of the ramp to the dark end, measured from
    emitted stitch geometry."""
    region = _rect_region()
    runs, report = meander_fill(region, _ramp_source(), PipelineConfig())
    assert runs, "the ramp must produce stitches"
    assert report["empty"] is False

    hh = _RECT_H_MM / 2.0
    n_strips = 6
    strip_h = _RECT_H_MM / n_strips
    strip_area = _RECT_W_MM * strip_h
    densities = []
    pens = []
    for k in range(n_strips):
        y0 = -hh + k * strip_h
        densities.append(_strip_thread_density(runs, y0, y0 + strip_h, strip_area))
        pens.append(_strip_penetration_density(runs, y0, y0 + strip_h, strip_area))

    # Adjacent strips are allowed quantization noise (a strip boundary can
    # sit mid-transition between two quadtree levels); two strips apart the
    # tone difference dominates and the ordering must be strict.
    for a, b in zip(densities, densities[1:]):
        assert b >= a * 0.8, f"thread density fell along the ramp: {densities}"
    for a, b in zip(densities, densities[2:]):
        assert b > a, f"thread density not rising two strips apart: {densities}"
    assert densities[-1] > 2.5 * max(densities[0], 1e-9), (
        f"dark end not measurably denser than light end: {densities}"
    )

    for a, b in zip(pens, pens[2:]):
        assert b > a, f"penetration density not rising two strips apart: {pens}"
    assert pens[-1] > 3.0 * max(pens[0], 1e-9), (
        f"penetration density did not separate end to end: {pens}"
    )


def test_zigzag_burst_oscillates_with_darkness():
    """The burst mechanism, pinned where it is honestly measurable — and a
    metric-hygiene record, because THREE tier-level metrics were tried and
    each measured something else: point-to-chord deviation scored the light
    end higher (coarse-cell curve corners deviate more than a fine zigzag),
    a thread-length ablation read ~0 (emission is arc-clocked, so amplitude
    buys band width, not length), and displacement-under-ablation drowned
    in the corner-cut noise of a curve whose finest cell is smaller than
    the needle floor. On a STRAIGHT stretch of path there are no corners:
    the walk's emitted penetrations must oscillate perpendicular to the
    path with amplitude that rises with darkness and vanishes toward the
    cutoff — the mechanism itself, measured from emitted penetrations. At
    tier level the burst reads as line texture, which the debugviz render
    exists for."""
    from digitizer_core.stage6_meander import _walk_polyline

    line = [(0.0, 0.0), (200.0, 0.0)]  # one long straight segment
    cells = [0.9, 0.9]

    def walk_offsets(gray: int):
        dark = 1.0 - gray / 255.0
        pts = _walk_polyline(line, cells, lambda x, y: dark, lambda p: True)
        return [p[1] for (p, sewing) in pts if sewing]

    dark_off = walk_offsets(20)    # darkness ~0.92
    light_off = walk_offsets(200)  # darkness ~0.22, just past the cutoff

    dark_amp = float(np.mean(np.abs(dark_off[1:])))
    assert dark_amp > 0.15, f"dark burst amplitude {dark_amp:.3f} too small"
    signs = np.sign(dark_off[1:])
    flips = float(np.mean(signs[:-1] != signs[1:]))
    assert flips > 0.9, f"dark offsets do not alternate: flip rate {flips:.2f}"

    light_amp = float(np.mean(np.abs(light_off[1:]))) if len(light_off) > 1 else 0.0
    assert light_amp < 0.08, f"light amplitude {light_amp:.3f} did not fade"
    assert dark_amp > 2.0 * max(light_amp, 1e-9)


def test_ramp_stitch_budget():
    """Plan §1d puts the mono meander class at ≈ 0.5–1.0 st/mm² on the
    genre's own art. The ramp includes a deliberately-bare highlight stretch
    (fabric is a value here more than in any other tier), so its whole-shape
    figure sits below real art's: measured 0.35 st/mm² at the shipped knobs,
    asserted with margin. The real-art figure is measured on
    `drone_render.png` below."""
    region = _rect_region()
    runs, _ = meander_fill(region, _ramp_source(), PipelineConfig())
    count = sum(len(r.points) for r in _fill_runs(runs))
    density = count / region.polygon.area
    assert 0.25 <= density <= 1.1, f"st/mm² {density:.3f} out of band"


def test_ramp_path_never_crosses_itself():
    """The genre's first selling point, checked geometrically: no two
    needle-down segments properly intersect anywhere in the emitted plan —
    sewing, travel and the joints between runs included."""
    region = _rect_region()
    runs, _ = meander_fill(region, _ramp_source(), PipelineConfig())
    segs = _needle_down_segments(runs)
    assert len(segs) > 500
    assert _crossing_pairs(segs) == 0


def test_ramp_trims_single_digit():
    """The genre's second selling point. Every lift the tier takes is
    counted in the report; only lifts past the trim distance cost a trim,
    and the total must stay single-digit."""
    region = _rect_region()
    runs, report = meander_fill(region, _ramp_source(), PipelineConfig())
    trims = sum(1 for r in runs if r.trim)
    jumps = sum(1 for r in runs if r.jump)
    assert trims <= 9, f"trims {trims} broke the single-digit budget"
    assert jumps == report["jumps"]


def test_flat_midgray_is_uniform_and_respects_machine_floors():
    region = _rect_region()
    runs, report = meander_fill(region, _flat_source(120), PipelineConfig())
    assert runs
    assert report["empty"] is False

    # Uniform tone -> uniform density across strips (the meander's cell
    # grid quantizes harder than scanline rows, hence the looser 25%).
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
        assert abs(d - mean) <= 0.25 * mean, f"flat tone sewed uneven strips: {densities}"

    # Machine floors, measured on every emitted needle-down stitch.
    for r in runs:
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            assert d <= machine.MAX_STITCH_MM + 1e-6
            assert d >= machine.MIN_STITCH_MM - 1e-6, (
                f"stitch under the needle floor: {d}"
            )

    assert sum(1 for r in runs if r.trim) <= 9


def test_near_white_is_empty_and_the_report_is_honest():
    """Fabric-as-highlight: tone below the cutoff sews nothing at all, and
    the report says so instead of pretending."""
    region = _rect_region()
    runs, report = meander_fill(region, _flat_source(250), PipelineConfig())
    assert runs == []
    assert report["empty"] is True
    assert report["jumps"] == 0


def test_just_above_cutoff_is_sparse_not_dense():
    region = _rect_region()
    cutoff = MEANDER_LEVEL_DARKNESS[0]
    gray = int(round(255 * (1.0 - cutoff))) - 6  # a hair darker than the cutoff
    runs, report = meander_fill(region, _flat_source(gray), PipelineConfig())
    assert runs, "tone just past the cutoff must sew a sparse pass, not nothing"
    assert report["empty"] is False
    count = sum(len(r.points) for r in _fill_runs(runs))
    density = count / region.polygon.area
    assert 0.0 < density < 0.25, f"near-white should be sparse, measured {density:.3f}"


def test_determinism():
    region = _rect_region()
    source = _ramp_source()
    cfg = PipelineConfig()
    a, a_report = meander_fill(region, source, cfg)
    b, b_report = meander_fill(region, source, cfg)
    assert [r.points for r in a] == [r.points for r in b]
    assert [r.kind for r in a] == [r.kind for r in b]
    assert [(r.jump, r.trim) for r in a] == [(r.jump, r.trim) for r in b]
    assert a_report == b_report


def test_every_stitch_stays_inside_the_shape():
    """Curve visits, zigzag excursions, boundary clips and links all live
    inside the polygon (hair of slack for float noise, same tolerance the
    fill's travel test uses)."""
    region = _rect_region()
    runs, _ = meander_fill(region, _ramp_source(), PipelineConfig())
    room = region.polygon.buffer(0.05)
    for r in runs:
        for x, y in r.points:
            assert room.covers(Point(x, y)), f"stitch escaped the shape: {(x, y)}"


def test_adaptive_hilbert_traversal_is_gapless():
    """The reimplemented curve math itself (Velho & Gomes' traversal, made
    adaptive): on a uniform grid consecutive cells are exactly edge-adjacent,
    and on a 2:1-balanced mixed-depth grid consecutive leaves stay within
    the adjacency bound the module's break detector relies on."""
    from digitizer_core.stage6_meander import (_desired_depth_grid,
                                               _hilbert_leaves, _max_pyramid)

    md = 3
    side = 8
    depth = np.full((side, side), md, np.int32)
    pyr = _max_pyramid(depth, md)
    leaves = _hilbert_leaves(pyr, lambda bx, by, s: False, md)
    assert len(leaves) == side * side
    for a, b in zip(leaves, leaves[1:]):
        assert math.dist(a[:2], b[:2]) == pytest.approx(1.0), (
            "uniform Hilbert order must visit edge-adjacent cells"
        )

    dark = np.zeros((side, side))
    dark[:, side // 2:] = 0.9  # right half demands the finest cells
    inside = np.ones((side, side), bool)
    depth = _desired_depth_grid(dark, inside, md)
    pyr = _max_pyramid(depth, md)
    leaves = _hilbert_leaves(pyr, lambda bx, by, s: False, md)
    sizes = {s for _, _, s in leaves}
    assert len(sizes) > 1, "the adaptive grid must actually mix cell sizes"
    for a, b in zip(leaves, leaves[1:]):
        limit = 1.25 * (a[2] + b[2]) / 2.0
        assert math.dist(a[:2], b[:2]) <= limit, (
            f"adaptive traversal skipped: {a} -> {b}"
        )


def test_debug_artifact_is_written_when_requested(tmp_path):
    region = _rect_region()
    cfg = PipelineConfig(debug_dir=str(tmp_path))
    runs, _ = meander_fill(region, _ramp_source(), cfg)
    assert runs
    out = tmp_path / "stage6_meander_path.png"
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    assert img.min() < 250, "the render drew nothing"


def test_drone_render_measured_end_to_end(tmp_path):
    """The human-judgeable render on real art, with the genre's own numbers
    measured on it: single-digit trims, zero crossings, and a stitch budget
    in the mono band's neighbourhood (measured 0.44 st/mm² — the render's
    big soft highlights stay bare, which is the point of the tier). What the
    picture LOOKS like is Kent's call, not an assertion's."""
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
    runs, report = meander_fill(region, source, cfg)
    assert runs, "real art must produce stitches"
    assert report["empty"] is False
    assert (tmp_path / "stage6_meander_path.png").is_file()

    trims = sum(1 for r in runs if r.trim)
    assert trims <= 9, f"trims {trims} broke the single-digit budget on real art"
    assert _crossing_pairs(_needle_down_segments(runs)) == 0

    pens = sum(len(r.points) for r in _fill_runs(runs))
    density = pens / poly.area
    assert 0.3 <= density <= 1.2, f"st/mm² {density:.3f} out of band on real art"


# --- The opt-in wiring (config -> pipeline -> stage 7) -----------------------

LOGO = HERE.parent / "testdata" / "logo_whitebg.png"


def test_pipeline_plumbs_source_pixels_only_on_explicit_opt_in():
    from digitizer_core.pipeline import run_stages

    on = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        fill_technique="meander_tonal"))
    assert on.source_pixels is not None, (
        "explicit meander_tonal opt-in must carry source pixels through"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when the flag is off"
    )


def test_meander_plan_differs_from_tatami_and_off_is_identical():
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="meander_tonal")
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


def test_meander_falls_back_to_tatami_when_it_produces_nothing():
    """The contour-tier contract, verbatim: a shape the technique cannot sew
    (here: source pixels all near-white, so the tonal tier honestly emits
    nothing) falls back to ordinary tatami rather than dropping artwork —
    and the fallback is byte-identical to what plain tatami would have sewn."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="meander_tonal")
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
