"""The speckle-gate r² override (`cfg.blend_speckle_r2_override`).

Funded by Kent 2026-08-23 for the acceptance A/B, after the tonal-eng
measurement (docs/tonal-eng-measurements-2026-08-22.md §1) showed the
speckle gate — not the r² floor — is the blend tier's real off-switch on
real art: 41 of the 42 real regions clearing the floor die at `speckled`,
because real-photo texture carries local variance a synthetic ramp does
not, even when the ramp model explains 92% of the region.

The fixture here reproduces that failure mode synthetically ON PURPOSE —
it exercises a gate's mechanics, not stage-0 routing, so hard gate 2 (real
fixtures for routing decisions) is not in play: a clean linear ramp plus
per-pixel noise is rejected `speckled` at r² 0.93 by the stock gate,
exactly like the measured drone patches. The three-point contract:

  rescued   — speckled-but-well-fit passes under the override;
  guarded   — genuine noise (r² under the floor) is NEVER rescued: the
              override vouches past the speckle gate only, the floor holds;
  identical — None (the default) is the shipped gate byte-for-byte, and a
              clean ramp behaves the same under both.
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import (
    RAMP_R2_MIN,
    SourcePixels,
    blend_fill,
    detect_ramp_detail,
)
from digitizer_core.threads import chart_for

POLY = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])


def _noisy_ramp_source(sigma: float) -> SourcePixels:
    rng = np.random.default_rng(7)
    ramp = np.linspace(30, 225, 160, dtype=np.float64)[None, :, None]
    rgb = np.broadcast_to(ramp, (120, 160, 3)).copy()
    rgb += rng.normal(0, sigma, size=rgb.shape)
    return SourcePixels(rgb=np.clip(rgb, 0, 255).astype(np.uint8),
                        px_per_mm=4.0, origin_px=(80.0, 60.0))


def test_override_rescues_a_well_fit_region_the_speckle_gate_vetoes():
    sp = _noisy_ramp_source(sigma=10.0)
    model, reason, r2 = detect_ramp_detail(POLY, sp)
    # Premise, asserted so a drifting fixture fails loud: the stock gate
    # rejects THIS region as speckle while its fit is excellent.
    assert model is None and reason == "speckled" and r2 > 0.9, (reason, r2)

    model, reason, r2 = detect_ramp_detail(POLY, sp,
                                           speckle_r2_override=RAMP_R2_MIN)
    assert model is not None, (reason, r2)


def test_override_never_rescues_genuine_noise():
    sp = _noisy_ramp_source(sigma=60.0)
    model, reason, r2 = detect_ramp_detail(POLY, sp)
    assert model is None and reason == "low_r2" and r2 < RAMP_R2_MIN, (reason, r2)

    model, reason, _ = detect_ramp_detail(POLY, sp,
                                          speckle_r2_override=RAMP_R2_MIN)
    assert model is None and reason == "low_r2", (
        "the override vouches past the SPECKLE gate only — the r² floor holds")


def test_default_none_is_the_shipped_gate():
    sp = _noisy_ramp_source(sigma=10.0)
    explicit_none = detect_ramp_detail(POLY, sp, speckle_r2_override=None)
    implicit = detect_ramp_detail(POLY, sp)
    assert explicit_none[1] == implicit[1] == "speckled"
    assert PipelineConfig().blend_speckle_r2_override is None


def test_blend_fill_threads_the_config_field():
    """End to end through the tier every real region takes: the same
    speckled ramp decomposes into shades under the override and flattens
    to plain tatami without it."""
    chart = chart_for(PipelineConfig())
    region = Region(shape_id="Sspeckle", polygon=POLY, thread_index=0,
                    thread_number=chart[0].number, area_mm2=POLY.area)
    sp = _noisy_ramp_source(sigma=10.0)

    _, stock = blend_fill(region, sp, PipelineConfig())
    assert stock["blend_shades"] == 0 and stock["blend_reject"] == "speckled"

    _, relaxed = blend_fill(
        region, sp, PipelineConfig(blend_speckle_r2_override=RAMP_R2_MIN))
    assert relaxed["blend_shades"] >= 3, relaxed


# --- cfg.blend_speckle_residual: speckle measured on the fit's residual ------
# Same synthetic-mechanics licence as above (a gate's arithmetic, not stage-0
# routing). Contract: pixel grain around a ramp passes; a second structure the
# ramp cannot explain still rejects; False is the shipped gate.


def _ramp_with_step_source() -> SourcePixels:
    """A clean ramp with a 66-level dark band across part of it: stitch-scale
    structure the linear fit leaves in its residual. The crop the polygon
    reads is columns 80-160, so the band (100-130) sits inside it.

    Note what this pins: the residual ratio is bounded by roughly 1 - r², so
    under the shared RAMP_SPECKLE_MAX (0.35) it can only reject a fit below
    ~0.65 whose miss is COARSE. This fixture sits at r² 0.52 on purpose."""
    ramp = np.linspace(30, 225, 160, dtype=np.float64)[None, :, None]
    rgb = np.broadcast_to(ramp, (120, 160, 3)).copy()
    rgb[:, 100:130] -= 66.0
    return SourcePixels(rgb=np.clip(rgb, 0, 255).astype(np.uint8),
                        px_per_mm=4.0, origin_px=(80.0, 60.0))


def test_residual_measure_passes_pixel_grain_around_a_ramp():
    sp = _noisy_ramp_source(sigma=10.0)
    assert detect_ramp_detail(POLY, sp)[1] == "speckled"
    model, reason, r2 = detect_ramp_detail(POLY, sp, speckle_residual=True)
    assert model is not None, (reason, r2)


def test_residual_measure_still_rejects_structure_the_ramp_misses():
    sp = _ramp_with_step_source()
    _m, reason, r2 = detect_ramp_detail(POLY, sp, speckle_r2_override=RAMP_R2_MIN)
    # Premise: the fit clears the floor, so the override would wave it through.
    assert reason == "" and r2 >= RAMP_R2_MIN, (reason, r2)
    model, reason, _ = detect_ramp_detail(POLY, sp, speckle_residual=True)
    assert model is None and reason == "speckled"


def test_residual_default_false_is_the_shipped_gate():
    assert PipelineConfig().blend_speckle_residual is False
    sp = _noisy_ramp_source(sigma=10.0)
    assert (detect_ramp_detail(POLY, sp, speckle_residual=False)[1]
            == detect_ramp_detail(POLY, sp)[1] == "speckled")
    clean = _noisy_ramp_source(sigma=0.0)
    assert (detect_ramp_detail(POLY, clean, speckle_residual=True)[0]
            is not None)
