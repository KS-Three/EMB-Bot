"""The sketch tier (stage6_sketch.py) — technique row 12: the config preset
over rows 10+11, sparse mono streamline line work plus the FDoG detail block.

The module under test owns NO algorithm — it is `streamline_fill` mono with
the darkness field attenuated, plus stage 7 appending `detail_runs` for the
technique — so what this file pins is the COMPOSITION: the preset routes,
the attenuation measurably sparsifies against the row-10 tier's own analytic
mapping, the detail block rides on top, the per-shape `tier: "sketch"`
override threads through all three contract layers, and off means off (the
flat lane's bytes cannot move — the golden byte-identity suites pin the
bytes themselves, the monkeypatch test here pins that the tier is never even
called). Every accuracy assertion is measured from emitted geometry, per the
discipline `test_stage6_streamline.py` established.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon

from digitizer_core import stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_sketch import SKETCH_DARKNESS_SCALE, sketch_fill
from digitizer_core.stage6_streamline import (
    STREAMLINE_CUTOFF_DARKNESS,
    _d_sep,
    streamline_fill,
)
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

HERE = Path(__file__).resolve().parent
TESTDATA = HERE.parent / "testdata"
PHOTO_DIR = TESTDATA / "photo"
LOGO = TESTDATA / "logo_whitebg.png"
FUR = PHOTO_DIR / "fur_ramp.png"

_PX_PER_MM = 4.0
FAB = get_fabric("pique_knit")


def _source(gray_img: np.ndarray) -> SourcePixels:
    h, w = gray_img.shape[:2]
    rgb = np.dstack([gray_img] * 3) if gray_img.ndim == 2 else gray_img
    return SourcePixels(rgb=rgb.astype(np.uint8), px_per_mm=_PX_PER_MM,
                        origin_px=(w / 2.0, h / 2.0))


def _region(poly: Polygon, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id="Stest", polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area, meta=m)


def _fill_runs(runs):
    return [r for r in runs if r.kind == stitches.FILL]


def _line_spacing(runs) -> np.ndarray:
    """Consecutive transverse gaps between horizontal (house-angle) lines."""
    ys = sorted(float(np.mean([p[1] for p in r.points])) for r in _fill_runs(runs))
    return np.diff(ys)


def _bar(w: float, h: float) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, -w / 2, -h / 2)


def _plan_for(regions: list[Region], source_pixels=None, **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c, source_pixels=source_pixels)

    class _P:  # just enough plan for the helpers here
        pass

    p = _P()
    p.blocks = blocks
    return p, warnings


def _all_points(plan):
    return [(b.thread_index, r.kind, r.points) for b in plan.blocks for r in b.runs]


# --- The attenuation: measurably sparser, against the row-10 analytic truth ---

def test_sketch_is_sparser_than_streamline_and_matches_the_analytic_mapping():
    """Uniform mid-gray disc (flat color -> house-angle parallels, the same
    fixture the row-10 spacing test uses): the sketch preset's median line
    gap must land on `_d_sep(SKETCH_DARKNESS_SCALE * darkness)` — the
    row-10 mapping read through the attenuation, no new constant — and must
    be measurably wider than the thread-paint tier's own gap on the very
    same raster."""
    gray = 100
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    img = np.full((200, 200), gray, np.uint8)

    sk_runs, sk_report = sketch_fill(_region(disc), _source(img), PipelineConfig())
    sl_runs, _ = streamline_fill(_region(disc), _source(img), PipelineConfig())

    assert sk_report["empty"] is False
    assert sk_report["house_fallback"] is True  # flat color has no direction
    sk_gaps, sl_gaps = _line_spacing(sk_runs), _line_spacing(sl_runs)
    assert len(sk_gaps) >= 5 and len(sl_gaps) >= 9

    darkness = 1.0 - gray / 255.0
    expected = _d_sep(SKETCH_DARKNESS_SCALE * darkness)
    measured = float(np.median(sk_gaps))
    assert abs(measured - expected) <= 0.10 * expected, (
        f"sketch median gap {measured:.3f} vs analytic {expected:.3f}"
    )
    assert measured > 1.3 * float(np.median(sl_gaps)), (
        "the sketch preset must be measurably sparser than thread-paint: "
        f"sketch {measured:.3f} vs streamline {np.median(sl_gaps):.3f}"
    )


def test_sketch_raised_highlight_cutoff_leaves_more_fabric_bare():
    """A tone BETWEEN the two effective cutoffs (raw darkness above the
    row-10 cutoff but below cutoff/scale): thread-paint still sews it, the
    sketch reads it as fabric — the 'more bare fabric' half of the preset,
    measured as emitted-vs-empty on the same raster."""
    gray = 230
    darkness = 1.0 - gray / 255.0
    assert STREAMLINE_CUTOFF_DARKNESS < darkness < \
        STREAMLINE_CUTOFF_DARKNESS / SKETCH_DARKNESS_SCALE, "fixture must sit between"

    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    img = np.full((160, 160), gray, np.uint8)
    sl_runs, sl_report = streamline_fill(_region(disc), _source(img), PipelineConfig())
    sk_runs, sk_report = sketch_fill(_region(disc), _source(img), PipelineConfig())

    assert sl_report["empty"] is False and sl_runs
    assert sk_report["empty"] is True and sk_runs == []
    assert sk_report["streamlines"] == 0


def test_sketch_forces_mono_even_when_streamline_mode_is_layered():
    """A sketch is one thread of line work by definition (law 10): the
    layered multi-color mode belongs to the streamline technique and must
    not leak in — same runs, no layered report keys, no shade shape_ids."""
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    img = np.full((200, 200), 90, np.uint8)

    mono_runs, mono_report = sketch_fill(
        _region(disc), _source(img), PipelineConfig())
    layered_runs, layered_report = sketch_fill(
        _region(disc), _source(img), PipelineConfig(streamline_mode="layered"))

    assert layered_report == mono_report
    assert "layers" not in layered_report
    assert [(r.kind, r.jump, r.trim, r.points) for r in layered_runs] == \
           [(r.kind, r.jump, r.trim, r.points) for r in mono_runs]
    assert all(not r.shape_id.endswith("shade0") for r in layered_runs)


def test_determinism():
    disc = Point(0, 0).buffer(12.0, quad_segs=32)
    img = np.full((160, 160), 80, np.uint8)
    a_runs, a_rep = sketch_fill(_region(disc), _source(img), PipelineConfig())
    b_runs, b_rep = sketch_fill(_region(disc), _source(img), PipelineConfig())
    assert a_rep == b_rep
    assert [(r.kind, r.jump, r.trim, r.points) for r in a_runs] == \
           [(r.kind, r.jump, r.trim, r.points) for r in b_runs]


# --- The opt-in wiring (config -> pipeline -> stage 7) ------------------------

def test_pipeline_plumbs_source_pixels_only_on_explicit_opt_in():
    from digitizer_core.pipeline import run_stages

    on = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat", fill_technique="sketch"))
    assert on.source_pixels is not None, (
        "explicit sketch opt-in must carry source pixels through"
    )
    assert on.source_pixels.gradient_class is False, (
        "sketch pixels must NOT re-route fills through the blend tier"
    )

    ov = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        shape_overrides={"Swhatever": {"tier": "sketch"}}))
    assert ov.source_pixels is not None, (
        "a per-shape tier:'sketch' override is an explicit opt-in too"
    )

    off = run_stages(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert off.source_pixels is None, (
        "the flat lane must not grow a raster payload when nothing asked"
    )


def test_default_config_never_runs_the_tier(monkeypatch):
    """Off means off: with the default fill_technique (and no override) the
    tier function must never even be CALLED — the strongest in-suite
    statement that the default lane's bytes cannot have moved (the golden
    byte-identity suites pin the bytes themselves)."""
    import digitizer_core.stage7_sequence as s7
    from digitizer_core.pipeline import digitize

    def boom(*a, **k):  # pragma: no cover - the point is it never fires
        raise AssertionError("sketch_fill ran on a default config")

    monkeypatch.setattr(s7, "sketch_fill", boom)
    _result, plan = digitize(str(LOGO), PipelineConfig(
        target_width_mm=90.0, forced_class="flat"))
    assert plan.blocks


def test_sketch_plan_differs_from_tatami_and_falls_back_when_blind():
    """Opt-in changes the stitches; a source raster the tier honestly sews
    nothing from (near-white — which also extracts no detail lines) falls
    back to EXACTLY the tatami plan, detail block included in the nothing —
    the never-drop-artwork contract, verbatim."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_on = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="sketch")
    cfg_off = PipelineConfig(target_width_mm=90.0, forced_class="flat")

    result_on = run_stages(str(LOGO), cfg_on)
    plan_on = plan_stitches(result_on, cfg_on)
    result_off = run_stages(str(LOGO), cfg_off)
    plan_off = plan_stitches(result_off, cfg_off)
    assert _all_points(plan_on) != _all_points(plan_off), (
        "opt-in produced the same stitches as tatami — the preset never ran"
    )

    result_blind = run_stages(str(LOGO), cfg_on)
    assert result_blind.source_pixels is not None
    result_blind.source_pixels.rgb = np.full_like(result_blind.source_pixels.rgb, 252)
    plan_blind = plan_stitches(result_blind, cfg_on)
    assert _all_points(plan_blind) == _all_points(plan_off), (
        "the tatami fallback must sew exactly what tatami would have"
    )


def test_sketch_technique_implies_the_detail_block():
    """Row 12's recipe is 'layered run passes + FDoG detail lines' — ONE
    preset: with `detail_layer` left at its default False, the sketch plan
    must still end in the row-11 bean block, and the streamline technique
    (which shares every other piece of plumbing) must not — the detail
    implication belongs to the sketch preset alone."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    cfg_sk = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="sketch")
    assert cfg_sk.detail_layer is False
    res_sk = run_stages(str(LOGO), cfg_sk)
    plan_sk = plan_stitches(res_sk, cfg_sk)

    last = plan_sk.blocks[-1]
    assert last.runs
    assert all(r.kind in (stitches.BEAN, stitches.TIE) for r in last.runs)
    assert last.runs[0].jump is True and last.runs[0].trim is True, (
        "a new color block always lifts in and cuts the previous thread"
    )

    cfg_sl = PipelineConfig(target_width_mm=90.0, forced_class="flat",
                            fill_technique="streamline")
    res_sl = run_stages(str(LOGO), cfg_sl)
    plan_sl = plan_stitches(res_sl, cfg_sl)
    assert not any(r.kind == stitches.BEAN for b in plan_sl.blocks for r in b.runs)


# --- The per-shape override, three layers deep --------------------------------

def test_forced_sketch_tier_changes_what_the_machine_sews():
    """Stage-7 consumption: one shape forced `tier: "sketch"` under the
    default tatami technique sews sparse fill lines instead of dense tatami
    rows — measured as an emitted-stitch collapse on the same geometry, with
    the line spacing landing on the sketch preset's own analytic value."""
    bar = _bar(20, 12)
    img = np.full((200, 200), 60, np.uint8)
    sp = _source(img)

    auto_plan, _ = _plan_for([_region(bar)], source_pixels=sp)
    sketch_plan, _ = _plan_for([_region(bar, {"tier": "sketch"})], source_pixels=sp)

    def fill_points(plan):
        return sum(len(r.points) for b in plan.blocks for r in b.runs
                   if r.kind == stitches.FILL)

    assert fill_points(auto_plan) > 0 and fill_points(sketch_plan) > 0
    assert fill_points(sketch_plan) < 0.5 * fill_points(auto_plan), (
        f"forced sketch must sew far sparser than tatami: "
        f"{fill_points(sketch_plan)} vs {fill_points(auto_plan)}"
    )
    gaps = _line_spacing([r for b in sketch_plan.blocks for r in b.runs])
    expected = _d_sep(SKETCH_DARKNESS_SCALE * (1.0 - 60 / 255.0))
    assert abs(float(np.median(gaps)) - expected) <= 0.15 * expected
    assert not any(r.kind == stitches.SATIN for b in sketch_plan.blocks
                   for r in b.runs)


def test_sketch_override_without_source_pixels_sews_tatami_exactly():
    """The standing tonal-tier contract: a forced sketch with no raster to
    read sews EXACTLY what the unforced shape would have — never a dropped
    shape, never a crash on a hand-built PipelineResult."""
    bar = _bar(20, 12)
    plain, _ = _plan_for([_region(bar)])
    forced, _ = _plan_for([_region(bar, {"tier": "sketch"})])
    assert _all_points(forced) == _all_points(plain)


def test_apply_shape_edits_accepts_sketch_and_still_rejects_junk():
    """Core-layer validation (`regions._TIER_VALUES`): "sketch" is stored on
    the region's meta like every forced tier; an unknown value still raises
    — the same defense-in-depth `underlay_style` pins for its own set."""
    regs = [_region(_bar(12, 12))]
    _regions, _threads, warnings = apply_shape_edits(
        regs, [0], [], {"Stest": {"tier": "sketch"}}, chart=[0] * 20)
    assert regs[0].meta.get("tier") == "sketch"
    assert warnings == []

    with pytest.raises(ValueError):
        apply_shape_edits([_region(_bar(12, 12))], [0], [],
                          {"Stest": {"tier": "scribble"}}, chart=[0] * 20)


def test_service_validates_and_canonicalizes_the_sketch_tier():
    """Service-layer validation (`app._TIER_VALUES`, the first of the three
    contract layers): "Sketch" lowercases and survives `_parse_config`, and
    an unknown tier is still a 400 at submit — the closed set grew by
    exactly one value."""
    pytest.importorskip("fastapi", reason="service extra not installed")
    from fastapi import HTTPException

    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"tier": "Sketch"}}})) == \
        {"shape_overrides": {"S1": {"tier": "sketch"}}}
    with pytest.raises(HTTPException):
        _parse_config(json.dumps({"shape_overrides": {"S1": {"tier": "scribble"}}}))


# --- Real photo fixture, end to end -------------------------------------------

def test_photo_fixture_end_to_end_sketch_preset(capsys):
    """The committed photo fixture (`fur_ramp.png`, fixture rule F6) through
    the full pipeline on the sketch preset: it digitizes, it sews sparse —
    measurably fewer fill stitches than the thread-paint tier on the very
    same fixture and class routing — and every stitch stays inside the
    design. Fingerprint stats reported concretely, per house convention."""
    from digitizer_core.pipeline import plan_stitches, run_stages

    def fill_points(plan):
        return sum(len(r.points) for b in plan.blocks for r in b.runs
                   if r.kind == stitches.FILL)

    cfg_sk = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                            fill_technique="sketch")
    res_sk = run_stages(str(FUR), cfg_sk)
    assert res_sk.source_pixels is not None
    plan_sk = plan_stitches(res_sk, cfg_sk)
    assert plan_sk.blocks and fill_points(plan_sk) > 0

    cfg_sl = PipelineConfig(target_width_mm=80.0, forced_class="photo_subject",
                            fill_technique="streamline")
    res_sl = run_stages(str(FUR), cfg_sl)
    plan_sl = plan_stitches(res_sl, cfg_sl)
    assert fill_points(plan_sk) < fill_points(plan_sl), (
        "the sketch preset must sew sparser than thread-paint on the same "
        f"fixture: {fill_points(plan_sk)} vs {fill_points(plan_sl)}"
    )

    w_mm, h_mm = res_sk.design_size_mm
    for b in plan_sk.blocks:
        for r in b.runs:
            for x, y in r.points:
                assert abs(x) <= w_mm / 2 + 1.0 and abs(y) <= h_mm / 2 + 1.0

    total = sum(len(r.points) for b in plan_sk.blocks for r in b.runs)
    trims = sum(1 for b in plan_sk.blocks for r in b.runs if r.trim)
    runs_n = sum(len(b.runs) for b in plan_sk.blocks)
    print(
        f"\n[sketch fur_ramp] blocks={len(plan_sk.blocks)} runs={runs_n} "
        f"total_stitches={total} fill_stitches={fill_points(plan_sk)} "
        f"trims={trims} (streamline fill_stitches={fill_points(plan_sl)})"
    )
