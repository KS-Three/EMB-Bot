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
from digitizer_core.fabrics import get_fabric
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SHADE_COUNT_MAX, SHADE_COUNT_MIN, SourcePixels
from digitizer_core.stage6_streamline import (
    STREAMLINE_CUTOFF_DARKNESS,
    STREAMLINE_D_SEP_DARK_MM,
    STREAMLINE_D_SEP_LIGHT_MM,
    STREAMLINE_TRAVEL_MAX_MM,
    _d_sep,
    _darkness_sampler,
    _shade_layers,
    streamline_fill,
)
from digitizer_core.stage7_sequence import sequence
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


def _region(poly: Polygon, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area, meta=m)


FAB = get_fabric("pique_knit")


def _plan_for(regions: list[Region], source_pixels=None, **cfg_kw):
    """Stage 5 + stage 7 only — the same minimal-plan helper
    `test_stage6_sketch.py` uses for its per-shape-override tests, reused
    here for the streamline tier's own per-shape form."""
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c, source_pixels=source_pixels)

    class _P:  # just enough plan for the assertions below
        pass

    p = _P()
    p.blocks = blocks
    return p, warnings


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


# --- The multi-color seam (layered mode, technique row 10's full spec) -------
#
# `cfg.streamline_mode == "layered"` (module docstring, config.py). Every
# assertion below is measured from EMITTED geometry — line spacing, run
# sequence, shape_id tags on real StitchRuns — the same discipline the mono
# suite above holds itself to, not a re-read of the tier's own parameters.

def _full_ramp(w_px: int = 320, h_px: int = 240) -> np.ndarray:
    """Light-to-dark horizontal ramp spanning close to the full luminance
    range, so even the extreme chart shades' canonical darkness (0 and 1)
    fall inside the sampled range and every shade gets a real peak to test
    against, not just the interior ones."""
    return np.tile(np.linspace(250, 5, w_px), (h_px, 1)).astype(np.uint8)


def _shade_fill_runs(runs, shape_id: str, i: int):
    tag = f"{shape_id}-shade{i}"
    return [r for r in runs if r.shape_id == tag and r.kind == "fill"]


def _luma(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b


def test_layered_shade_count_and_report_contract():
    """A saturated ramp splits into the plan's 3-5 chart shades; the report
    carries them dark-to-light, and the existing `streamlines`/`too_thin`/
    `jumps`/`empty` keys keep their old meaning (now design-wide totals)."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    runs, report = streamline_fill(
        _region(poly), _source(_full_ramp()), PipelineConfig(streamline_mode="layered"))

    assert report["empty"] is False
    n = report["layers"]
    assert SHADE_COUNT_MIN <= n <= SHADE_COUNT_MAX
    assert len(report["shade_thread_idx"]) == n
    assert len(report["shade_rgb"]) == n
    assert len(report["streamlines_by_layer"]) == n
    assert sum(report["streamlines_by_layer"]) == report["streamlines"] > 0
    assert report["streamlines"] == len([r for r in runs if r.kind == "fill"])

    lumas = [_luma(rgb) for rgb in report["shade_rgb"]]
    assert lumas[0] < lumas[-1], "report must name shades dark to light"
    assert all(a <= b + 1e-6 for a, b in zip(lumas, lumas[1:])), lumas


def test_layered_sew_order_is_dark_shade_first_in_the_actual_runs():
    """The EMITTED run sequence, not just the report's bookkeeping: every
    shade's own runs form one contiguous dark-to-light block (no
    interleaving), and every shade boundary is an unconditional colour
    change — forced jump+trim, the same forcing stage 7 applies to a brand
    new colour stop, never a travel bridge."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    region = _region(poly)
    runs, report = streamline_fill(
        region, _source(_full_ramp()), PipelineConfig(streamline_mode="layered"))

    seen_order = []
    for r in runs:
        if r.shape_id.startswith(f"{region.shape_id}-shade"):
            idx = int(r.shape_id.rsplit("shade", 1)[1])
            if not seen_order or seen_order[-1] != idx:
                seen_order.append(idx)
    assert seen_order == sorted(seen_order), (
        f"shade layers must appear as one dark->light block each: {seen_order}"
    )
    assert len(seen_order) == len(set(seen_order)), (
        f"a shade must not reappear after a later shade started: {seen_order}"
    )
    assert len(seen_order) >= 2, "fixture must exercise more than one shade"

    boundaries = [r for i, r in enumerate(runs)
                 if i > 0 and r.shape_id != runs[i - 1].shape_id]
    assert boundaries
    for b in boundaries:
        assert b.jump is True and b.trim is True, (
            "every shade boundary must be a forced colour change"
        )


def test_layered_each_shades_d_sep_tracks_its_own_coverage_share():
    """The seam's own claim: 'each layer's d_sep [is] driven by that shade's
    own coverage share rather than raw darkness'. A shade sitting well
    inside the ramp's range must sew NEAR the dark-end floor at its OWN
    coverage peak (a triangular tent's own kink means the seed lattice never
    settles to the exact analytic value the way it does on the mono slice's
    smooth ramp — this checks it lands close, not exactly), and it must open
    up on EITHER side as that same coverage share falls toward this shade's
    cutoff — even on the side where the RAW ramp is getting LIGHTER, which
    is the one direction raw darkness alone would have predicted TIGHTER
    spacing, not sparser. That two-sided agreement is what pins the "not raw
    darkness" half of the claim: raw darkness moves opposite directions on
    the two sides of the peak, but this shade's own spacing does not."""
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    source = _source(_full_ramp())
    region = _region(poly)
    cfg = PipelineConfig(streamline_mode="layered")

    runs, report = streamline_fill(region, source, cfg)
    n = report["layers"]
    assert n >= 3

    base_darkness = _darkness_sampler(source)
    shades = _shade_layers(poly, source, base_darkness, region, cfg)
    mid = n // 2
    thread_idx, _rgb, membership = shades[mid]
    assert thread_idx == report["shade_thread_idx"][mid]

    xs = np.linspace(-34.0, 34.0, 400)
    shares = np.array([membership(x, 0.0) for x in xs])
    peak_i = int(np.argmax(shares))
    peak_x, peak_share = float(xs[peak_i]), float(shares[peak_i])
    assert peak_share > 0.9, f"fixture must reach this shade's own peak: {peak_share}"
    # Raw darkness at the peak, for the "not raw darkness" contrast below.
    peak_raw_darkness = base_darkness(peak_x, 0.0)

    fill = _shade_fill_runs(runs, region.shape_id, mid)
    assert len(fill) >= 6, "fixture must give this shade room for several lines"
    line_xs = sorted(float(np.mean([p[0] for p in r.points])) for r in fill)

    # Classify each CONSECUTIVE-line gap by this shade's own coverage share
    # at the gap's midpoint (not by a fixed mm window, which would mix
    # different shares together over any window wide enough to hold several
    # gaps) — a direct, per-gap correlation between measured spacing and the
    # membership value that (per the seam's contract) is supposed to have
    # produced it. Split the low-coverage ("edge") gaps by which side of the
    # peak they fall on: the light side (raw darkness LOWER than the peak's
    # own) and the dark side (raw darkness HIGHER).
    gaps = [((a + b) / 2.0, b - a, membership((a + b) / 2.0, 0.0))
            for a, b in zip(line_xs, line_xs[1:])]
    peak_gaps = [g for _mid, g, m in gaps if m >= 0.9]
    light_edge_gaps = [g for mid_x, g, m in gaps
                       if 0.15 <= m <= 0.45 and mid_x < peak_x]
    dark_edge_gaps = [g for mid_x, g, m in gaps
                      if 0.15 <= m <= 0.45 and mid_x > peak_x]
    assert len(peak_gaps) >= 2, gaps
    assert len(light_edge_gaps) >= 2, gaps
    assert len(dark_edge_gaps) >= 2, gaps

    median_peak = float(np.median(peak_gaps))
    median_light_edge = float(np.median(light_edge_gaps))
    median_dark_edge = float(np.median(dark_edge_gaps))

    # Near the peak: closer to the dark-end floor than to the light-end
    # ceiling, and comfortably under the ceiling itself.
    assert abs(median_peak - STREAMLINE_D_SEP_DARK_MM) < \
        abs(median_peak - STREAMLINE_D_SEP_LIGHT_MM), (
        f"peak spacing {median_peak:.3f} must read closer to the dark-end "
        f"floor {STREAMLINE_D_SEP_DARK_MM} than the light-end ceiling "
        f"{STREAMLINE_D_SEP_LIGHT_MM}"
    )
    assert median_peak < 0.6 * STREAMLINE_D_SEP_LIGHT_MM, median_peak

    # Both edges open up relative to the peak...
    assert median_light_edge > 1.3 * median_peak, (median_light_edge, median_peak)
    assert median_dark_edge > 1.3 * median_peak, (median_dark_edge, median_peak)
    # ...and open up COMPARABLY on both sides, despite the light-side raw
    # darkness moving AWAY from black (toward the fixture's light end) while
    # the dark-side raw darkness moves TOWARD it — raw darkness predicts
    # these two edges should differ sharply; coverage share predicts they
    # should not, because both sit the same distance from this shade's own
    # canonical center on the darkness axis.
    ratio = median_light_edge / median_dark_edge
    assert 0.5 <= ratio <= 2.0, (
        f"the two edges must open up comparably on coverage share alone: "
        f"light {median_light_edge:.3f} vs dark {median_dark_edge:.3f} "
        f"(peak raw darkness {peak_raw_darkness:.3f})"
    )


def test_layered_near_white_is_empty_like_mono():
    """Above the highlight cutoff every shade's coverage share is also
    (correctly) below cutoff — an all-highlight shape still reports empty
    honestly in layered mode."""
    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    runs, report = streamline_fill(
        _region(disc), _source(np.full((160, 160), 250, np.uint8)),
        PipelineConfig(streamline_mode="layered"))
    assert runs == []
    assert report["empty"] is True
    assert report["streamlines"] == 0


def test_layered_off_is_byte_identical_to_mono_default():
    """`streamline_mode` defaults to "mono", and setting it to "mono"
    explicitly must be indistinguishable from leaving it unset — the flag
    itself, not just the tier, is opt-in."""
    poly = Polygon([(-20, -20), (20, -20), (20, 20), (-20, 20)])
    img = _stripes(30.0)

    default_runs, default_report = streamline_fill(
        _region(poly), _source(img), PipelineConfig())
    mono_runs, mono_report = streamline_fill(
        _region(poly), _source(img), PipelineConfig(streamline_mode="mono"))

    assert default_report == mono_report
    assert "layers" not in default_report
    assert [(r.kind, r.jump, r.trim, r.points) for r in default_runs] == \
           [(r.kind, r.jump, r.trim, r.points) for r in mono_runs]


def test_layered_pipeline_falls_back_to_tatami_when_blind():
    """The multi-color mode inherits the same never-drop-artwork fallback as
    mono: a source the tier honestly sews nothing from sews exactly the
    tatami plan, layered or not."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_layered = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                                 fill_technique="streamline", streamline_mode="layered")
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points) for b in plan.blocks for r in b.runs]

    result_blind = run_stages(str(LOGO), cfg_layered)
    assert result_blind.source_pixels is not None
    result_blind.source_pixels.rgb = np.full_like(result_blind.source_pixels.rgb, 252)
    plan_blind = plan_stitches(result_blind, cfg_layered)

    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)

    assert all_points(plan_blind) == all_points(plan_off)


def test_layered_drone_render_end_to_end(tmp_path, capsys):
    """Real art, layered mode, end to end: measured layer count, streamlines
    per layer, total run stitches and forced colour-change trims — reported
    concretely, the same standard the mono slice's own drone-render test and
    commit message held."""
    from digitizer_core.stage1_prep import prep

    cfg = PipelineConfig(target_width_mm=90.0, debug_dir=str(tmp_path),
                         streamline_mode="layered")
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

    assert runs, "real art must produce stitches in layered mode too"
    assert report["empty"] is False
    n = report["layers"]
    assert SHADE_COUNT_MIN <= n <= SHADE_COUNT_MAX

    total_stitches = sum(len(r.points) for r in runs)
    trims = sum(1 for r in runs if r.trim)
    fill_runs = [r for r in runs if r.kind == "fill"]
    travel_runs = [r for r in runs if r.kind == "travel"]
    print(
        f"\n[layered drone_render] layers={n} "
        f"streamlines_by_layer={report['streamlines_by_layer']} "
        f"total_streamlines={report['streamlines']} "
        f"fill_runs={len(fill_runs)} travel_runs={len(travel_runs)} "
        f"total_run_stitches={total_stitches} jumps={report['jumps']} "
        f"trims={trims}"
    )

    for x, y in [p for r in runs for p in r.points]:
        assert -100.0 <= x <= 100.0 and -100.0 <= y <= 100.0

    out = tmp_path / "stage6_streamline_paths.png"
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    assert img.min() < 100, "the render drew nothing"


# --- The per-shape override (shape-layers contract v1.6): streamline fill  --
# outside the photo auto-pipeline, on one manually-classified (flat-lane)
# shape at a time — the same `tier: "sketch"` mechanism `test_stage6_sketch.py`
# already exercises, extended by one value. Every accuracy claim below is
# measured from EMITTED geometry with the exact same analytic-truth
# discipline the design-wide tests above hold themselves to: this is not a
# "does it crash" smoke test, it is proof the forced tier sews REAL
# Jobard-Lefer evenly-spaced streamline output.

def test_forced_streamline_tier_follows_the_field_on_a_manually_classified_shape():
    """One shape forced `tier: "streamline"` inside an otherwise-default
    (`fill_technique="tatami"`) plan — nothing about this design is
    photo-classified or opted into the design-wide streamline preset — must
    sew stitches that follow the direction field, measured exactly like
    `test_emitted_runs_follow_the_field_on_stripes` above: the stripe
    fixture's truth angle recovered from the EMITTED segments themselves."""
    angle = 40.0
    poly = Polygon([(-25, -25), (25, -25), (25, 25), (-25, 25)])
    source = _source(_stripes(angle))

    auto_plan, _ = _plan_for([_region(poly)], source_pixels=source)
    forced_plan, _ = _plan_for([_region(poly, {"tier": "streamline"})],
                               source_pixels=source)

    auto_runs = [r for b in auto_plan.blocks for r in b.runs]
    forced_runs = [r for b in forced_plan.blocks for r in b.runs]
    assert [(r.kind, r.points) for r in forced_runs] != \
           [(r.kind, r.points) for r in auto_runs], (
        "the forced tier must not just re-sew plain tatami"
    )

    devs, wts = _segment_angle_devs(forced_runs, angle)
    assert len(devs) > 30
    assert _weighted_percentile(devs, wts, 0.5) <= 2.0, (
        "the forced-tier stitches must actually follow the direction field, "
        "not merely differ from tatami by coincidence"
    )
    assert _weighted_percentile(devs, wts, 0.9) <= 6.0


def test_forced_streamline_tier_spacing_matches_the_analytic_d_sep():
    """Same forced `tier: "streamline"` override, uniform-darkness fixture
    this time (the flat-color / house-angle path a genuinely vector-drawn,
    textureless shape would take): line-to-line spacing must land on the
    analytic d_sep for this darkness, the same measurement
    `test_uniform_disc_spacing_is_tight_around_d_sep` makes of the
    design-wide tier — proof this is real evenly-spaced J-L placement, not
    an arbitrary sparse fill that merely looks different from tatami."""
    gray = 100
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    source = _source(np.full((200, 200), gray, np.uint8))

    forced_plan, _ = _plan_for([_region(disc, {"tier": "streamline"})],
                               source_pixels=source)
    fill = [r for b in forced_plan.blocks for r in b.runs if r.kind == "fill"]
    assert len(fill) >= 10, "must produce genuine multi-line streamline output"

    ys = sorted(float(np.mean([p[1] for p in r.points])) for r in fill)
    spacing = np.diff(ys)
    expected = _d_sep(1.0 - gray / 255.0)
    assert len(spacing) >= 9
    assert abs(float(np.median(spacing)) - expected) <= 0.10 * expected, (
        f"median spacing {np.median(spacing):.3f} vs analytic d_sep {expected:.3f} — "
        "this must be real J-L placement, not tatami rows or a random scatter"
    )


def test_pipeline_plumbs_source_pixels_for_per_shape_streamline_override():
    """The opt-in wiring, per-shape form: a review-screen edit forcing ONE
    shape onto streamline fill must carry source pixels through even though
    the design stays `fill_technique="tatami"` throughout and classifies
    "flat" — a manually-classified shape, not a photo — mirroring
    `test_stage6_sketch.py`'s identical proof for `tier: "sketch"`."""
    from digitizer_core.pipeline import run_stages

    ov = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        shape_overrides={"Swhatever": {"tier": "streamline"}}))
    assert ov.source_pixels is not None, (
        "a per-shape tier:'streamline' override is an explicit opt-in too"
    )
    assert ov.source_pixels.gradient_class is False, (
        "the per-shape override must not re-route fills through the blend tier"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when nothing asked"
    )


def test_streamline_override_without_source_pixels_sews_tatami_exactly():
    """The standing tonal-tier contract, per-shape form: a forced streamline
    tier with no raster to read (a hand-built PipelineResult that never
    plumbed source pixels) sews EXACTLY what the unforced shape would have —
    never a dropped shape, never a crash."""
    poly = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])
    plain, _ = _plan_for([_region(poly)])
    forced, _ = _plan_for([_region(poly, {"tier": "streamline"})])

    def all_points(plan):
        return [(r.kind, r.points) for b in plan.blocks for r in b.runs]

    assert all_points(forced) == all_points(plain)


def test_apply_shape_edits_accepts_streamline_and_still_rejects_junk():
    """Core-layer validation (`regions._TIER_VALUES`): "streamline" is
    stored on the region's meta like every forced tier; an unknown value
    still raises — the same defense-in-depth the sketch tier's own test
    pins for its value."""
    regs = [_region(Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))]
    _regions, _threads, warnings = apply_shape_edits(
        regs, [0], [], {"Stest": {"tier": "streamline"}}, chart=[0] * 20)
    assert regs[0].meta.get("tier") == "streamline"
    assert warnings == []

    with pytest.raises(ValueError):
        apply_shape_edits(
            [_region(Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))],
            [0], [], {"Stest": {"tier": "scribble"}}, chart=[0] * 20)


def test_service_validates_and_canonicalizes_the_streamline_tier():
    """Service-layer validation (`app._TIER_VALUES`, the first of the three
    contract layers): "Streamline" lowercases and survives `_parse_config`,
    and an unknown tier is still a 400 at submit — the closed set grew by
    exactly one value, the same proof `test_stage6_sketch.py` runs for
    "sketch"."""
    import json

    from fastapi import HTTPException

    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"tier": "Streamline"}}})) == \
        {"shape_overrides": {"S1": {"tier": "streamline"}}}
    with pytest.raises(HTTPException):
        _parse_config(json.dumps({"shape_overrides": {"S1": {"tier": "scribble"}}}))
