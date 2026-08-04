"""Streamline thread-paint tier (stage6_streamline.py) — technique row 10,
first (mono) slice.

Every accuracy assertion is MEASURED FROM THE EMITTED GEOMETRY against an
analytically known truth — spacing against the darkness->d_sep mapping,
direction against generated stripe fixtures with a known angle (the same
fixture convention `test_directionfield.py` established), density against the
raw luminance ramp. Nothing re-reads the parameters the tier was configured
with and calls that a measurement.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import machine
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_streamline import (
    STREAMLINE_CUTOFF_DARKNESS,
    STREAMLINE_D_SEP_DARK_MM,
    STREAMLINE_TRAVEL_MAX_MM,
    _d_sep,
    streamline_fill,
)
from digitizer_core.threads import CHART

HERE = Path(__file__).resolve().parent
PHOTO_DIR = HERE.parent / "testdata" / "photo"
LOGO = HERE.parent / "testdata" / "logo_whitebg.png"

_PX_PER_MM = 4.0


def _source(gray_img: np.ndarray) -> SourcePixels:
    """A grayscale raster -> SourcePixels centered on the raster center."""
    h, w = gray_img.shape[:2]
    rgb = np.dstack([gray_img] * 3) if gray_img.ndim == 2 else gray_img
    return SourcePixels(rgb=rgb.astype(np.uint8), px_per_mm=_PX_PER_MM,
                        origin_px=(w / 2.0, h / 2.0))


def _region(poly: Polygon) -> Region:
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area)


def _stripes(angle_deg: float, size: int = 240, period: float = 12.0) -> np.ndarray:
    """Sinusoidal stripes whose LINES run along `angle_deg` (y-down) — the
    `test_directionfield.py` fixture convention, truth = the angle itself."""
    a = math.radians(angle_deg)
    nx, ny = -math.sin(a), math.cos(a)
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float64)
    phase = 2.0 * math.pi * (xx * nx + yy * ny) / period
    return (127.5 + 127.5 * np.sin(phase)).astype(np.uint8)


def _fill_runs(runs):
    return [r for r in runs if r.kind == "fill"]


def _angle_diff_deg(a: float, b: float) -> float:
    d = abs(a - b) % 180.0
    return min(d, 180.0 - d)


def _segment_angle_devs(runs, truth_deg: float, min_seg_mm: float = 0.3
                        ) -> tuple[np.ndarray, np.ndarray]:
    """(deviation from truth, segment length) for every emitted fill segment
    long enough to carry a direction."""
    devs, wts = [], []
    for r in _fill_runs(runs):
        for a, b in zip(r.points, r.points[1:]):
            length = math.dist(a, b)
            if length < min_seg_mm:
                continue
            theta = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
            devs.append(_angle_diff_deg(theta, truth_deg))
            wts.append(length)
    return np.array(devs), np.array(wts)


def _weighted_percentile(values: np.ndarray, weights: np.ndarray, q: float) -> float:
    order = np.argsort(values)
    cum = np.cumsum(weights[order]) / weights.sum()
    return float(values[order][np.searchsorted(cum, q)])


# --- Even spacing (the Jobard–Lefer core) ------------------------------------

def test_uniform_disc_spacing_is_tight_around_d_sep():
    """A uniform-darkness disc through a uniform field (flat color reads
    incoherent, so the house-angle constant field carries the trace — the
    fallback IS the synthetic uniform field): neighbouring parallel lines
    must sit at the analytic d_sep for that darkness, tightly."""
    gray = 100
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    runs, report = streamline_fill(
        _region(disc), _source(np.full((200, 200), gray, np.uint8)),
        PipelineConfig())

    assert report["empty"] is False
    assert report["house_fallback"] is True  # flat color has no field direction
    fill = _fill_runs(runs)
    assert len(fill) >= 10

    # House angle defaults to 0 deg -> horizontal lines; each line's
    # transverse position is its mean y, and consecutive positions are the
    # measured spacing.
    ys = sorted(float(np.mean([p[1] for p in r.points])) for r in fill)
    spacing = np.diff(ys)
    expected = _d_sep(1.0 - gray / 255.0)
    assert len(spacing) >= 9
    assert abs(float(np.median(spacing)) - expected) <= 0.10 * expected, (
        f"median spacing {np.median(spacing):.3f} vs d_sep {expected:.3f}"
    )
    # Tightness, not just central tendency: 90% of gaps within 15% of d_sep.
    assert float(np.percentile(np.abs(spacing - expected), 90)) <= 0.15 * expected, (
        f"spacing distribution too loose: {sorted(np.round(spacing, 3))}"
    )


# --- Direction-following ------------------------------------------------------

@pytest.mark.parametrize("angle", [30.0, 117.5])
def test_emitted_runs_follow_the_field_on_stripes(angle):
    """On the stripe fixture the field's truth is the stripe angle itself
    (pinned by test_directionfield); the EMITTED STITCHES must carry that
    direction — the tier's whole reason to exist, measured from geometry."""
    poly = Polygon([(-25, -25), (25, -25), (25, 25), (-25, 25)])
    runs, report = streamline_fill(
        _region(poly), _source(_stripes(angle)), PipelineConfig())

    assert report["house_fallback"] is False
    assert report["field_coherence"] > 0.9
    devs, wts = _segment_angle_devs(runs, angle)
    assert len(devs) > 50
    assert _weighted_percentile(devs, wts, 0.5) <= 2.0
    assert _weighted_percentile(devs, wts, 0.9) <= 6.0


# --- Darkness modulation ------------------------------------------------------

def test_darkness_modulates_spacing_on_a_ramp():
    """A horizontal luminance ramp (light left, dark right): the field's
    tangents run vertical (along the iso-lines), so streamlines are vertical
    and their spacing is measured along x — denser on the dark side, and
    both sides near the analytic d_sep for their own local darkness."""
    w_px, h_px = 320, 240
    ramp = np.tile(np.linspace(240, 20, w_px), (h_px, 1)).astype(np.uint8)
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    runs, report = streamline_fill(_region(poly), _source(ramp), PipelineConfig())

    assert report["house_fallback"] is False
    xs = sorted(float(np.mean([p[0] for p in r.points])) for r in _fill_runs(runs))
    pairs = list(zip(xs, np.diff(xs)))
    light = [d for x, d in pairs if x < -15]
    dark = [d for x, d in pairs if x > 15]
    assert len(light) >= 3 and len(dark) >= 8
    mean_light, mean_dark = float(np.mean(light)), float(np.mean(dark))
    assert mean_dark < 0.6 * mean_light, (
        f"dark side must be denser: light {mean_light:.2f}, dark {mean_dark:.2f}"
    )

    def analytic(x_mm: float) -> float:
        col = int(w_px / 2 + x_mm * _PX_PER_MM)
        return _d_sep(1.0 - float(ramp[0, col]) / 255.0)

    assert abs(mean_light - analytic(-25.0)) <= 0.2 * analytic(-25.0)
    assert abs(mean_dark - analytic(25.0)) <= 0.2 * analytic(25.0)


def test_near_white_is_empty_and_the_report_is_honest():
    """Above the highlight cutoff nothing sews — fabric is the highlight
    value, and the report says `empty` so stage 7's ladder can decide."""
    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    runs, report = streamline_fill(
        _region(disc), _source(np.full((160, 160), 250, np.uint8)),
        PipelineConfig())
    assert runs == []
    assert report["empty"] is True
    assert report["streamlines"] == 0
    # Sanity on the mapping itself: 250/255 luminance is above the cutoff.
    assert 1.0 - 250 / 255.0 < STREAMLINE_CUTOFF_DARKNESS


# --- Coherence fallback -------------------------------------------------------

def test_noise_falls_back_to_parallel_house_angle_lines():
    """Uniform noise reads incoherent (the direction-field tests pin that);
    the tier must then emit PARALLEL lines at the house angle — measurably
    uniform, not garbage spaghetti."""
    rng = np.random.default_rng(5)
    noise = rng.integers(0, 256, size=(240, 240), dtype=np.uint8)
    poly = Polygon([(-25, -25), (25, -25), (25, 25), (-25, 25)])
    house = 25.0
    runs, report = streamline_fill(
        _region(poly), _source(noise), PipelineConfig(fill_angle_deg=house))

    assert report["house_fallback"] is True
    assert report["field_coherence"] < 0.25
    devs, wts = _segment_angle_devs(runs, house)
    assert len(devs) > 50
    # Parallel means parallel: essentially every segment on the house angle.
    assert _weighted_percentile(devs, wts, 0.9) <= 1.0


def test_house_fallback_angle_precedence_review_override_wins():
    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    region = _region(disc)
    region.meta["fill_angle_deg"] = 70.0
    runs, report = streamline_fill(
        region, _source(np.full((160, 160), 90, np.uint8)),
        PipelineConfig(fill_angle_deg=10.0))
    assert report["house_fallback"] is True
    devs, wts = _segment_angle_devs(runs, 70.0)
    assert _weighted_percentile(devs, wts, 0.9) <= 1.0


# --- Determinism --------------------------------------------------------------

def test_determinism():
    img = _stripes(30.0)
    poly = Polygon([(-20, -20), (20, -20), (20, 20), (-20, 20)])
    a_runs, a_report = streamline_fill(_region(poly), _source(img), PipelineConfig())
    b_runs, b_report = streamline_fill(_region(poly), _source(img), PipelineConfig())
    assert a_report == b_report
    assert [(r.kind, r.jump, r.trim, r.points) for r in a_runs] == \
           [(r.kind, r.jump, r.trim, r.points) for r in b_runs]


# --- Machine floors, stitch band, jump/trim honesty ---------------------------

def test_machine_floors_stitch_band_and_containment():
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    runs, _report = streamline_fill(
        _region(disc), _source(np.full((200, 200), 100, np.uint8)),
        PipelineConfig())

    room = disc.buffer(0.05)
    seg_lengths = []
    for r in runs:
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            assert d <= machine.MAX_STITCH_MM + 1e-9
            assert d > 1e-9, "coincident consecutive points inflate counts"
            if r.kind == "fill":
                seg_lengths.append(d)
        for x, y in r.points:
            assert room.covers(Point(x, y)), f"stitch outside the shape: {(x, y)}"
    # The resample pitch lands in the plan's 2.5-4 mm run band.
    assert 2.5 <= float(np.median(seg_lengths)) <= 4.0


def test_jump_and_trim_accounting_is_honest():
    """Two dark patches separated by more highlight than the travel cap: the
    needle must LIFT between them (never sew a float across bare fabric),
    the report's jump count must equal the emitted jump flags, and a jump
    past trim_at must be a trim."""
    img = np.full((200, 320), 250, np.uint8)   # highlight everywhere...
    img[:, :100] = 80                          # ...except a dark left band
    img[:, 220:] = 80                          # ...and a dark right band
    poly = Polygon([(-38, -22), (38, -22), (38, 22), (-38, 22)])
    runs, report = streamline_fill(_region(poly), _source(img), PipelineConfig())

    jump_runs = [r for r in runs if r.jump]
    assert report["jumps"] == len(jump_runs) >= 1
    for r in runs:
        assert not (r.trim and not r.jump), "a trim without a lift is nonsense"
    # The two bands are ~30 mm apart: crossing them is a trim, not a float.
    assert any(r.trim for r in jump_runs)
    # And no needle-down bridge may span more than the travel cap.
    prev_end = None
    for r in runs:
        if prev_end is not None and r.kind == "travel":
            assert math.dist(prev_end, r.points[0]) <= STREAMLINE_TRAVEL_MAX_MM + 1e-6
        prev_end = r.points[-1]


def test_dark_end_spacing_respects_the_floor_constant():
    """Full black may not pack lines tighter than the dark-end constant —
    the density floor that keeps a mono layer from becoming a board."""
    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    runs, _ = streamline_fill(
        _region(disc), _source(np.zeros((160, 160), np.uint8)), PipelineConfig())
    ys = sorted(float(np.mean([p[1] for p in r.points])) for r in _fill_runs(runs))
    spacing = np.diff(ys)
    assert float(np.min(spacing)) >= 0.8 * STREAMLINE_D_SEP_DARK_MM


# --- Debug artifact + real art ------------------------------------------------

def test_drone_render_debugviz_smoke(tmp_path):
    """The human-judgeable render on real art: the tier runs end to end over
    `drone_render.png`'s bbox and writes its debug render. Whether the
    strokes follow the drone's structure is Kent's call, not an assertion's."""
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
    source = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm, origin_px=(cx, cy))
    runs, report = streamline_fill(_region(poly), source, cfg)
    assert runs, "real art must produce stitches"
    assert report["empty"] is False
    assert report["house_fallback"] is False, (
        "the drone render carries real structure; sewing it at one house "
        "angle would defeat the tier"
    )
    out = tmp_path / "stage6_streamline_paths.png"
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    assert img.min() < 100, "the render drew nothing"


# --- The opt-in wiring (config -> pipeline -> stage 7) ------------------------

def test_pipeline_plumbs_source_pixels_only_on_explicit_opt_in():
    from digitizer_core.pipeline import run_stages

    on = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat", fill_technique="streamline"))
    assert on.source_pixels is not None, (
        "explicit streamline opt-in must carry source pixels through"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when the flag is off"
    )


def test_default_config_never_runs_the_tier(monkeypatch):
    """Off means off: with the default fill_technique the tier function must
    never even be CALLED — the strongest in-suite statement that the default
    lane's bytes cannot have moved (the golden byte-identity suites pin the
    bytes themselves)."""
    import digitizer_core.stage7_sequence as s7
    from digitizer_core.pipeline import digitize

    def boom(*a, **k):  # pragma: no cover - the point is it never fires
        raise AssertionError("streamline_fill ran on a default config")

    monkeypatch.setattr(s7, "streamline_fill", boom)
    _result, plan = digitize(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert plan.blocks


def test_streamline_plan_differs_from_tatami_and_falls_back_when_blind():
    """Opt-in changes the stitches; a source raster the tier honestly sews
    nothing from (near-white) falls back to EXACTLY the tatami plan — the
    contour-tier never-drop-artwork contract, verbatim."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="streamline")
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points) for b in plan.blocks for r in b.runs]

    result_on = run_stages(str(LOGO), cfg_on)
    plan_on = plan_stitches(result_on, cfg_on)
    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)
    assert all_points(plan_on) != all_points(plan_off), (
        "opt-in produced the same stitches as tatami — the tier never ran"
    )
    assert plan_on.blocks and sum(len(b.runs) for b in plan_on.blocks) > 0

    result_blind = run_stages(str(LOGO), cfg_on)
    assert result_blind.source_pixels is not None
    result_blind.source_pixels.rgb = np.full_like(result_blind.source_pixels.rgb, 252)
    plan_blind = plan_stitches(result_blind, cfg_on)
    assert all_points(plan_blind) == all_points(plan_off), (
        "the tatami fallback must sew exactly what tatami would have"
    )
