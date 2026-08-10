"""The detail layer (stage6_detail.py) — technique row 11, first slice:
FDoG coherent line extraction emitted as bean runs on top of fills.

Every accuracy assertion is MEASURED FROM THE EMITTED GEOMETRY against an
analytically known truth — a drawn circle's extracted lines against the
circle's own radius, a step edge's against its known position, bean pitch
against the corpus constant — the discipline `test_stage6_streamline.py`
established. The honesty tests are as load-bearing as the accuracy ones:
flat color, iid noise and grain noise must extract exactly NOTHING (the
layer's contract is "emit no block", never "invent detail").
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
from shapely.geometry import LineString

from digitizer_core import machine, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_detail import (
    DETAIL_MIN_LINE_MM,
    detail_runs,
    extract_detail_lines,
)

HERE = Path(__file__).resolve().parent
PHOTO_DIR = HERE.parent / "testdata" / "photo"
LOGO = HERE.parent / "testdata" / "logo_whitebg.png"

_PX_PER_MM = 4.0
_TRIM_AT = 3.0


def _source(img: np.ndarray) -> SourcePixels:
    h, w = img.shape[:2]
    rgb = np.dstack([img] * 3) if img.ndim == 2 else img
    return SourcePixels(rgb=rgb.astype(np.uint8), px_per_mm=_PX_PER_MM,
                        origin_px=(w / 2.0, h / 2.0))


def _step_edge(contrast: float, size: int = 200) -> np.ndarray:
    hi = int(round(128 + contrast * 255 / 2))
    lo = int(round(128 - contrast * 255 / 2))
    img = np.full((size, size), hi, np.uint8)
    img[:, size // 2:] = lo
    return img


def _circle_img(radius_mm: float = 25.0, size: int = 300) -> np.ndarray:
    img = np.full((size, size), 245, np.uint8)
    cv2.circle(img, (size // 2, size // 2), int(radius_mm * _PX_PER_MM),
               30, 2, cv2.LINE_AA)
    return img


def _single_pass_len(run) -> float:
    """One bean pass's arc length: the run retraces itself BEAN_PASSES
    times, so a pass is total length over the pass count."""
    return run.length_mm / machine.BEAN_PASSES


# --- Honesty: nothing in, nothing out -----------------------------------------

def test_flat_color_extracts_nothing():
    assert extract_detail_lines(_source(np.full((200, 200), 128, np.uint8))) == []


def test_uniform_noise_extracts_nothing():
    """iid full-range noise carries plenty of DoG response but no coherent
    direction — the coherence gate (measured, see DETAIL_MIN_COHERENCE's
    comment) must reject all of it."""
    rng = np.random.default_rng(5)
    noise = rng.integers(0, 256, size=(200, 200)).astype(np.uint8)
    assert extract_detail_lines(_source(noise)) == []


def test_grain_noise_extracts_nothing():
    rng = np.random.default_rng(7)
    grain = (128 + rng.normal(0, 12, size=(200, 200))).clip(0, 255).astype(np.uint8)
    assert extract_detail_lines(_source(grain)) == []


def test_empty_extraction_emits_no_runs_and_an_honest_report():
    runs, report = detail_runs(_source(np.full((160, 160), 128, np.uint8)),
                               PipelineConfig(), entry=None, trim_at_mm=_TRIM_AT)
    assert runs == []
    assert report["empty"] is True
    assert report["lines"] == 0
    assert "thread_index" not in report


# --- Analytic truth: known geometry in, lines on that geometry out ------------

def test_circle_lines_follow_the_known_radius():
    """A drawn ring of known radius: every extracted point must sit ON the
    ring (distance from center = radius within tolerance), and the traced
    length must cover essentially the whole circumference — not a fragment.
    Tolerances are the measured calibration figures (median dev 0.08 mm,
    p90 0.19, max 0.31 at 4 px/mm) with margin."""
    r_mm = 25.0
    lines = extract_detail_lines(_source(_circle_img(r_mm)))
    assert lines, "a high-contrast ring must extract"

    devs = np.array([abs(math.hypot(x, y) - r_mm)
                     for pts in lines for x, y in pts])
    assert float(np.median(devs)) <= 0.15, f"median radial dev {np.median(devs):.3f}"
    assert float(np.percentile(devs, 90)) <= 0.30
    assert float(devs.max()) <= 0.50

    total = sum(LineString(pts).length for pts in lines)
    circumference = 2.0 * math.pi * r_mm
    assert 0.8 * circumference <= total <= 1.3 * circumference, (
        f"traced {total:.1f} mm of a {circumference:.1f} mm ring"
    )


def test_step_edge_line_lands_on_the_edge():
    """A 50%-contrast vertical step at x=0: the extracted line must run the
    height of the image AT the edge — |x| within half a millimetre."""
    lines = extract_detail_lines(_source(_step_edge(0.5)))
    assert lines
    xs = [x for pts in lines for x, _y in pts]
    ys = [y for pts in lines for _x, y in pts]
    assert max(abs(x) for x in xs) <= 0.5, f"line strayed to x={max(xs, key=abs):.3f}"
    # 200 px at 4 px/mm = 50 mm tall; the edge line must span most of it.
    assert max(ys) - min(ys) >= 0.8 * 50.0


def test_detection_knee_strong_edges_yes_weak_edges_no():
    """The calibrated operating point (FDOG_RESPONSE_GAIN's comment): the
    measured knee sits at 20% step contrast, so 25% must detect and 10%
    must not — margin on both sides of the pin."""
    assert extract_detail_lines(_source(_step_edge(0.25)))
    assert extract_detail_lines(_source(_step_edge(0.10))) == []


# --- Emission: bean structure, machine floors, jump/trim honesty --------------

def test_bean_runs_structure_pitch_and_floors():
    runs, report = detail_runs(_source(_circle_img()), PipelineConfig(),
                               entry=None, trim_at_mm=_TRIM_AT)
    assert report["empty"] is False
    assert report["lines"] == len(runs) > 0

    for r in runs:
        assert r.kind == stitches.BEAN
        assert r.shape_id == "detail"
        # A bean run is the line sewn BEAN_PASSES times: stations n, points
        # n + (passes-1)*(n-1).
        n_pts = len(r.points)
        n_stations = (n_pts + machine.BEAN_PASSES - 1) // machine.BEAN_PASSES
        assert n_pts == n_stations + (machine.BEAN_PASSES - 1) * (n_stations - 1)
        # ...and it ends where a 3-pass run must: at the far end of the line.
        assert r.points[-1] == r.points[n_stations - 1]

        seg = [math.dist(a, b) for a, b in zip(r.points, r.points[1:])]
        assert all(d > 1e-9 for d in seg), "coincident consecutive points"
        assert max(seg) <= machine.MAX_STITCH_MM + 1e-9
        # Station pitch at the corpus bean constant (equal division, so the
        # band is generous but centered on it).
        assert 0.5 * machine.BEAN_STITCH_MM <= float(np.median(seg)) \
            <= 1.5 * machine.BEAN_STITCH_MM
        # The sewable floor: no emitted line shorter than the run tier's own.
        assert _single_pass_len(r) >= 0.8 * DETAIL_MIN_LINE_MM


def test_jump_trim_accounting_is_honest_and_no_travel_is_emitted():
    """Two separate rings ~14 mm apart: the hop between them must be a
    LIFT (this layer sews on top of finished work — no needle-down travel,
    ever), a lift past trim_at must cut, and the report must count exactly
    the emitted flags."""
    img = np.full((240, 400), 245, np.uint8)
    cv2.circle(img, (100, 120), 32, 30, 2, cv2.LINE_AA)
    cv2.circle(img, (300, 120), 32, 30, 2, cv2.LINE_AA)
    runs, report = detail_runs(_source(img), PipelineConfig(),
                               entry=None, trim_at_mm=_TRIM_AT)
    assert len(runs) >= 2
    assert all(r.kind == stitches.BEAN for r in runs), "no travel runs, ever"
    jump_runs = [r for r in runs if r.jump]
    assert report["jumps"] == len(jump_runs) >= 1
    for r in runs:
        assert not (r.trim and not r.jump), "a trim without a lift is nonsense"
    for prev, r in zip(runs, runs[1:]):
        d = math.dist(prev.points[-1], r.points[0])
        if r.jump:
            assert r.trim == (d > _TRIM_AT)
        else:
            assert d < machine.TINY_STITCH_MM


def test_determinism():
    img = _circle_img()
    a_runs, a_rep = detail_runs(_source(img), PipelineConfig(),
                                entry=None, trim_at_mm=_TRIM_AT)
    b_runs, b_rep = detail_runs(_source(img), PipelineConfig(),
                                entry=None, trim_at_mm=_TRIM_AT)
    assert a_rep == b_rep
    assert [(r.kind, r.jump, r.trim, r.points) for r in a_runs] == \
           [(r.kind, r.jump, r.trim, r.points) for r in b_runs]


# --- The opt-in wiring (config -> pipeline -> stage 7) ------------------------

def test_pipeline_plumbs_source_pixels_only_on_explicit_opt_in():
    from digitizer_core.pipeline import run_stages

    on = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat", detail_layer=True))
    assert on.source_pixels is not None
    assert on.source_pixels.gradient_class is False, (
        "detail-layer pixels must NOT re-route fills through the blend tier"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when the flag is off"
    )


def test_gradient_class_still_carries_its_marker():
    """The routing marker this slice introduced: a gradient-classified
    design keeps blend routing (gradient_class True) whether or not the
    detail layer is also on."""
    from digitizer_core.pipeline import run_stages

    for extra in ({}, {"detail_layer": True}):
        result = run_stages(str(LOGO), PipelineConfig(
            target_width_mm=90.0, forced_class="gradient", **extra))
        assert result.source_pixels is not None
        assert result.source_pixels.gradient_class is True


def test_default_config_never_runs_the_layer(monkeypatch):
    """Off means off: with the default config the layer function must never
    even be CALLED — the strongest in-suite statement that the default
    lane's bytes cannot have moved (the golden byte-identity suites pin the
    bytes themselves)."""
    import digitizer_core.stage7_sequence as s7
    from digitizer_core.pipeline import digitize

    def boom(*a, **k):  # pragma: no cover - the point is it never fires
        raise AssertionError("detail_runs ran on a default config")

    monkeypatch.setattr(s7, "detail_runs", boom)
    _result, plan = digitize(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert plan.blocks


def test_detail_on_only_appends_a_final_bean_block():
    """Opt-in composes: every artwork block sews byte-for-byte what it sews
    with the flag off, and the ONLY change is one appended final block of
    bean runs in the lines' own snapped thread."""
    from digitizer_core.pipeline import digitize

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points)
                for b in plan.blocks for r in b.runs]

    _r0, plan_off = digitize(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    _r1, plan_on = digitize(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat", detail_layer=True))

    base, on = all_points(plan_off), all_points(plan_on)
    assert len(plan_on.blocks) == len(plan_off.blocks) + 1
    assert on[:len(base)] == base, "artwork blocks must be untouched"

    detail = plan_on.blocks[-1]
    assert detail.runs
    assert all(r.kind in (stitches.BEAN, stitches.TIE) for r in detail.runs)
    assert detail.runs[0].jump is True and detail.runs[0].trim is True, (
        "a new color block always lifts in and cuts the previous thread"
    )


def test_blind_source_appends_nothing_and_matches_off_exactly():
    """A raster the extractor honestly finds no lines in: the plan must be
    EXACTLY the flag-off plan — no empty block, no warning, nothing."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    def all_points(plan):
        return [(b.thread_index, r.kind, r.points)
                for b in plan.blocks for r in b.runs]

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            detail_layer=True)
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    result_blind = run_stages(str(LOGO), cfg_on)
    assert result_blind.source_pixels is not None
    result_blind.source_pixels.rgb = np.full_like(result_blind.source_pixels.rgb, 200)
    plan_blind = plan_stitches(result_blind, cfg_on)

    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)

    assert all_points(plan_blind) == all_points(plan_off)
    assert [w["code"] for w in plan_blind.warnings] == \
           [w["code"] for w in plan_off.warnings]


# --- Real art + the debugviz artifact -----------------------------------------

def test_drone_render_end_to_end(tmp_path, capsys):
    """Real art, end to end: measured line count, bean stitches, jumps and
    trims — reported concretely per house convention — plus the human-
    review render (dark lines over the dimmed source)."""
    from digitizer_core.stage1_prep import prep

    cfg = PipelineConfig(target_width_mm=90.0, debug_dir=str(tmp_path),
                         detail_layer=True)
    p = prep(str(PHOTO_DIR / "drone_render.png"), cfg)
    x0, y0, x1, y1 = p.art_bbox
    source = SourcePixels(rgb=p.rgb, px_per_mm=p.px_per_mm,
                          origin_px=((x0 + x1) / 2.0, (y0 + y1) / 2.0))
    runs, report = detail_runs(source, cfg, entry=None, trim_at_mm=_TRIM_AT)

    assert runs, "real art with hard panel lines must extract detail"
    assert report["empty"] is False
    assert report["lines"] == len(runs)
    total_stitches = sum(len(r.points) for r in runs)
    trims = sum(1 for r in runs if r.trim)
    print(
        f"\n[detail drone_render] lines={report['lines']} "
        f"bean_stitches={total_stitches} jumps={report['jumps']} "
        f"trims={trims} thread_index={report['thread_index']} "
        f"rgb={report['rgb']}"
    )

    # Every stitch inside the design's own bbox (with margin).
    w_mm = (x1 - x0) / p.px_per_mm
    h_mm = (y1 - y0) / p.px_per_mm
    for x, y in [pt for r in runs for pt in r.points]:
        assert abs(x) <= w_mm / 2 + 1.0 and abs(y) <= h_mm / 2 + 1.0

    out = tmp_path / "stage6_detail_lines.png"
    assert out.is_file()
    img = cv2.imread(str(out))
    assert img is not None
    assert img.min() < 100, "the render drew nothing"
