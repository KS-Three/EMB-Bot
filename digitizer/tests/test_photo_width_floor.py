"""Law 31's satin width floor, photo classes only (live defect 2's fix).

The measured defect: sub-millimetre satin — a zigzag column narrower than
the thread itself (snag/break/perforation risk, Law 31: "under 1 mm:
convert to multi-ply run"). 19 of 162 corpus regions sew it, all on the
photo fixture family (`docs/dt-first-verdict-2026-08-11.md` §3.2-4). The
same reroute is DISPROVED for flat art — on 15 real customer logos, 61 of
64 sub-1.0mm satin shapes are ground the pro also satined
(`docs/satin-gate-attribution-2026-08-16.md` §7) — and the disproof
population classifies "gradient" like most real logo art, so the gate is
the photo lane itself, the one lane a user reaches via the "This is a
photo" toggle.

The floor CONSTANT is Law 31's printed 1.0 mm, adopted verbatim, not swept
— ROADMAP hard gate 1 names the satin width floor a fabric question, so
tuning it waits on cloth; citing it does not.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import BackgroundInfo, PipelineResult, plan_stitches
from digitizer_core.regions import Region
from digitizer_core.stage6_satin import (
    PHOTO_MIN_SATIN_WIDTH_MM,
    _PHOTO_CLASSES,
    classify_ribbon,
    is_satin_candidate,
)
from digitizer_core.stage7_sequence import PHOTO_CLASSES
from digitizer_core.threads import chart_for

# A hairline stroke: long enough to clear the aspect gate by miles, wide
# enough to skeletonize, but sewing a 0.7 mm column — under the floor.
HAIRLINE = Polygon([(0, 0), (24, 0), (24, 0.7), (0, 0.7)])
# The known-good satin bar every satin test uses (24x2 mm — 2.0 mm column).
BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])

SATIN_MAX = 5.0


def test_hairline_reroutes_in_the_photo_classes_only():
    for cls in ("photo_subject", "photo_scene"):
        v = classify_ribbon(HAIRLINE, SATIN_MAX, design_class=cls)
        assert v.reason == "photo_width_floor" and not v.satin, (cls, v.reason)
        assert v.metrics["dt_p90_mm"] < PHOTO_MIN_SATIN_WIDTH_MM
    for cls in ("flat", "gradient"):
        v = classify_ribbon(HAIRLINE, SATIN_MAX, design_class=cls)
        assert v.satin, (cls, v.reason)


def test_a_normal_bar_keeps_its_satin_in_the_photo_classes():
    v = classify_ribbon(BAR, SATIN_MAX, design_class="photo_subject")
    assert v.satin and v.reason == "satin", v.reason


def test_photo_class_mirror_is_in_lockstep():
    """stage6_satin mirrors stage7's PHOTO_CLASSES (importing would cycle);
    drift here fails SILENT in production — a new photo class would get
    photo sequencing but not the width floor — so the lockstep is pinned."""
    assert _PHOTO_CLASSES == PHOTO_CLASSES


def _end_flared_stroke() -> Polygon:
    """A script-stroke shape that takes classify_ribbon's PROMOTED exit:
    a 0.16 mm hairline body flaring to 0.9 mm at one end spreads the medial
    radii past the regularity term (2σ >= μ) while `explained`/`elongation`
    still read ribbon — measured cv 0.60, explained 0.84, elongation 118,
    p90 0.476 mm. Exists because the floor gates BOTH satin-earning exits
    and the plain HAIRLINE bar only ever exercises the regular one."""
    xs = np.linspace(0.0, 30.0, 200)
    def w(x):
        return 0.16 if x < 25.0 else 0.16 + 0.74 * (x - 25.0) / 5.0
    top = [(float(x), w(x) / 2.0) for x in xs]
    bot = [(float(x), -w(x) / 2.0) for x in reversed(xs)]
    return Polygon(top + bot)


def test_the_promoted_ribbon_exit_is_floored_too():
    flared = _end_flared_stroke()
    flat = classify_ribbon(flared, SATIN_MAX, design_class="flat")
    assert flat.satin and flat.reason == "promoted_ribbon", flat.reason
    photo = classify_ribbon(flared, SATIN_MAX, design_class="photo_subject")
    assert not photo.satin and photo.reason == "photo_width_floor", photo.reason


def test_is_satin_candidate_carries_the_floor_to_stage5():
    """Stage 5's `_comp_axis` uses the bool wrapper to decide satin-axis
    compensation; a floor-rerouted shape must read as not-satin there too,
    the same treatment an explicit tier:"run" override already gets."""
    assert is_satin_candidate(HAIRLINE, SATIN_MAX, design_class="photo_subject") is False
    assert is_satin_candidate(HAIRLINE, SATIN_MAX, design_class="flat") is True


def _one_shape_result(poly: Polygon, design_class: str) -> PipelineResult:
    """Hand-built PipelineResult, the same pattern test_photo_auto_route's
    `_photo_subject_result` uses — stage 5-7 run for real on deterministic
    topology. No source_pixels: the streamline auto-route needs them, but a
    satin-vs-run tier call does not, and their absence falls back to tatami
    for fill tiers without touching this test's shape."""
    chart = chart_for(PipelineConfig())
    region = Region(
        shape_id="Stest0001",
        polygon=poly,
        thread_index=0,
        thread_number=chart[0].number,
        area_mm2=poly.area,
        meta={"layer": 0, "stitched": True},
    )
    return PipelineResult(
        regions=[region],
        palette=[{"brand": chart.label, "brand_id": chart.id,
                  "number": region.thread_number, "name": "x", "rgb": [0, 0, 0]}],
        background=BackgroundInfo(detected=False),
        px_per_mm=10.0,
        design_size_mm=(30.0, 5.0),
        design_class=design_class,
    )


def _kinds(plan) -> set:
    return {r.kind for b in plan.blocks for r in b.runs}


def test_stage7_sews_the_hairline_as_a_run_on_the_photo_route():
    # An explicit fill_technique would suppress the photo auto-route and is
    # irrelevant here — the satin/run ladder runs before any fill tier.
    cfg = PipelineConfig(preflight=False)
    photo = plan_stitches(_one_shape_result(HAIRLINE, "photo_subject"), cfg)
    photo_kinds = _kinds(photo)
    assert "satin" not in photo_kinds, photo_kinds
    assert photo_kinds & {"run", "bean"}, photo_kinds

    flat = plan_stitches(_one_shape_result(HAIRLINE, "flat"), cfg)
    assert "satin" in _kinds(flat), _kinds(flat)


def test_stage7_still_satins_the_bar_on_the_photo_route():
    cfg = PipelineConfig(preflight=False)
    photo = plan_stitches(_one_shape_result(BAR, "photo_subject"), cfg)
    assert "satin" in _kinds(photo), _kinds(photo)


def test_an_explicit_satin_override_beats_the_floor():
    """tier:"satin" skips the classifier entirely ("the user has already
    answered the question it asks") — the one user path back to satin on a
    sub-mm photo shape, and the escape hatch the review asked to see pinned."""
    result = _one_shape_result(HAIRLINE, "photo_subject")
    result.regions[0].meta["tier"] = "satin"
    plan = plan_stitches(result, PipelineConfig(preflight=False))
    assert "satin" in _kinds(plan), _kinds(plan)
