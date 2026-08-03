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
from digitizer_core.stage6_blend import SourcePixels, blend_fill, detect_ramp
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

    expected_row_mm = machine.FILL_ROW_MM * n
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
    assert report == expected_report


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
