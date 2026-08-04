"""Stage 1.5 — photo prep (CLAHE tone rescue + texture kill).

Photo plan §2 rows 3-4, build step 3's zero-new-dependency first slice
(stage1_photo_prep.py). What this file pins:

1. The flag ON changes NOTHING for flat-classified designs — the golden
   fixtures re-run through `test_flat_lane_byte_identical`'s own snapshot
   helper with `photo_prep=True` still match the pre-change golden (the
   double gate's classification half).
2. The flag OFF changes nothing for photo-classified designs (the opt-in
   half): a forced-photo run under default config emits no
   PHOTO_PREP_APPLIED and its regions match a pre-slice construction.
3. Measured behavior on real pixels, not vibes: tone prep expands
   foreground L contrast on a deliberately low-contrast raster; texture
   kill collapses sub-detail grain while keeping a real step edge.
4. The rolling_guidance CONTRIB SEAM degrades honestly: without
   cv2.ximgproc it falls back to bilateral byte-for-byte and says so; with
   contrib installed it takes the real path (this branch runs only in a
   contrib venv — the swap-gate probe environment).
5. Determinism — same input, same bytes, twice.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage1_photo_prep import (
    PhotoPrepResult,
    _tone_prep,
    photo_prep,
)
from digitizer_core.stage1_prep import prep
from digitizer_core.warnings_codes import PHOTO_PREP_APPLIED

from .test_flat_lane_byte_identical import GOLDEN
from .test_flat_lane_byte_identical import _snapshot as _golden_snapshot

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FIXTURE = TESTDATA / "photo" / "region_blobs.png"

HAS_CONTRIB = hasattr(cv2, "ximgproc") and hasattr(cv2.ximgproc, "rollingGuidanceFilter")


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- Deterministic synthetic rasters -----------------------------------------


def _low_contrast_image() -> np.ndarray:
    """A luminance ramp deliberately compressed into [90, 160] — plenty of
    real structure, none of it using the full range: exactly what the tone
    prep exists to rescue."""
    h, w = 200, 300
    ramp = np.linspace(90, 160, w, dtype=np.float32)
    rgb = np.repeat(ramp[None, :], h, axis=0)
    rng = np.random.default_rng(3)
    rgb = rgb + rng.normal(0, 2.0, (h, w)).astype(np.float32)
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    return np.stack([rgb, rgb, rgb], axis=-1)


def _grainy_step_image() -> np.ndarray:
    """Two flat halves (a real edge worth keeping) covered in seeded
    per-pixel grain (texture worth killing). Grain sigma 8 — the amplitude
    the module's filter constants were sweep-tuned at (see the measured
    figures on BILATERAL_* / MEANSHIFT_SR in stage1_photo_prep.py); the
    tone stretch amplifies it to ~27 std, already well beyond realistic
    JPEG/weave grain. iid-Gaussian at this heat is bilateral's WORST case
    (every pixel disagrees with every neighbor), so passing here is a
    conservative bar, not a friendly one."""
    h, w = 200, 300
    rgb = np.full((h, w, 3), 80, np.float32)
    rgb[:, w // 2:] = 170
    rng = np.random.default_rng(7)
    rgb += rng.normal(0, 8.0, (h, w, 1)).astype(np.float32)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def _no_bg(shape: tuple[int, int]) -> np.ndarray:
    return np.zeros(shape, bool)


# --- 1. Flag ON, flat class: byte-identical -----------------------------------


def _snapshot_with_prep_on(name: str) -> dict:
    """`test_flat_lane_byte_identical._snapshot`'s exact construction, with
    the one config delta under test."""
    from digitizer_core.pipeline import digitize

    result, plan = digitize(
        TESTDATA / name, PipelineConfig(target_width_mm=80.0, photo_prep=True)
    )
    return {
        "shape_ids": sorted(r.shape_id for r in result.regions),
        "areas_mm2": sorted(round(r.area_mm2, 4) for r in result.regions),
        "warnings": sorted(
            f"{w['code']}:{w.get('count', '')}" for w in result.warnings
        ),
        "stitch_count": sum(len(r.points) for _, r in plan.iter_runs()),
        "stitch_coords": [
            [round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
            for _, r in plan.iter_runs()
            for x, y in r.points
        ],
    }


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flag_on_is_byte_identical_for_flat_classified_designs(fixture):
    """The classification half of the double gate: photo_prep=True on a
    flat-classified design must not move one byte vs the pre-change golden.
    (Compared against the same-environment baseline snapshot, not the
    committed golden directly, so this test measures THIS slice's delta and
    stays green in environments where the golden itself has a known,
    pre-existing mismatch — see COOKBOOK.md's container-environment note.)"""
    assert _snapshot_with_prep_on(fixture) == _golden_snapshot(fixture)


# --- 2. Flag OFF, photo class: nothing happens --------------------------------


def test_flag_off_emits_no_prep_and_flag_on_emits_one():
    """The opt-in half of the double gate, plus the warning contract."""
    off = run_stages(FIXTURE, _cfg(forced_class="photo_scene"))
    assert not any(w["code"] == PHOTO_PREP_APPLIED for w in off.warnings)

    on = run_stages(FIXTURE, _cfg(forced_class="photo_scene", photo_prep=True))
    applied = [w for w in on.warnings if w["code"] == PHOTO_PREP_APPLIED]
    assert len(applied) == 1
    w = applied[0]
    assert w["technique"] == "bilateral"
    assert w["fallback"] is False
    assert w["kill_px"] >= 2
    assert w["tone_ms"] >= 0 and w["texture_ms"] >= 0


def test_prep_actually_changes_the_raster_the_photo_lane_sees():
    cfg = _cfg()
    p = prep(FIXTURE, cfg)
    pp = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, _cfg(photo_prep=True))
    assert pp.rgb.shape == p.rgb.shape and pp.rgb.dtype == np.uint8
    assert not np.array_equal(pp.rgb, p.rgb), "prep was a silent no-op on a real photo fixture"


# --- 3. Measured effects -------------------------------------------------------


def test_tone_prep_expands_foreground_l_contrast():
    rgb = _low_contrast_image()
    fg = ~_no_bg(rgb.shape[:2])
    out = _tone_prep(rgb, fg, _cfg())

    def l_std(img: np.ndarray) -> float:
        return float(cv2.cvtColor(img, cv2.COLOR_RGB2LAB)[:, :, 0][fg].std())

    def l_range(img: np.ndarray) -> float:
        L = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)[:, :, 0][fg]
        return float(np.percentile(L, 98) - np.percentile(L, 2))

    assert l_std(out) > 1.5 * l_std(rgb), "tone prep failed to expand L spread"
    assert l_range(out) > 1.5 * l_range(rgb), "tone prep failed to expand L range"


def test_texture_kill_flattens_grain_but_keeps_the_step_edge():
    rgb = _grainy_step_image()
    h, w = rgb.shape[:2]
    cfg = _cfg(photo_prep=True, photo_prep_texture_kill="bilateral")
    pp = photo_prep(rgb, _no_bg((h, w)), px_per_mm=4.0, cfg=cfg)

    # Grain: within-half std, measured well away from the edge, against the
    # TONE-PREPPED raster (pp.rgb_tone) so the comparison isolates the
    # texture-kill step rather than crediting/blaming the CLAHE pass.
    def half_std(img: np.ndarray) -> float:
        left = img[:, : w // 2 - 20, 0].astype(np.float32)
        right = img[:, w // 2 + 20 :, 0].astype(np.float32)
        return float((left.std() + right.std()) / 2.0)

    before, after = half_std(pp.rgb_tone), half_std(pp.rgb)
    assert after < 0.5 * before, (
        f"texture kill left {after:.2f} of {before:.2f} grain std standing"
    )

    # Edge: the step's amplitude across the boundary survives.
    def edge_amp(img: np.ndarray) -> float:
        left = float(img[:, w // 2 - 25 : w // 2 - 15, 0].astype(np.float32).mean())
        right = float(img[:, w // 2 + 15 : w // 2 + 25, 0].astype(np.float32).mean())
        return abs(right - left)

    assert edge_amp(pp.rgb) > 0.8 * edge_amp(pp.rgb_tone), "the real edge got smoothed away"


# --- 4. The contrib seam -------------------------------------------------------


@pytest.mark.skipif(HAS_CONTRIB, reason="contrib installed: the fallback branch cannot fire")
def test_rolling_guidance_without_contrib_falls_back_to_bilateral_and_says_so():
    rgb = _grainy_step_image()
    bg = _no_bg(rgb.shape[:2])
    want_rg = _cfg(photo_prep=True, photo_prep_texture_kill="rolling_guidance")
    want_bl = _cfg(photo_prep=True, photo_prep_texture_kill="bilateral")

    pp_rg = photo_prep(rgb, bg, 4.0, want_rg)
    pp_bl = photo_prep(rgb, bg, 4.0, want_bl)

    assert pp_rg.fallback is True and pp_rg.technique == "bilateral"
    assert np.array_equal(pp_rg.rgb, pp_bl.rgb), "fallback must be bilateral, byte-for-byte"
    assert "fell back" in pp_rg.warnings[0]["message"]


@pytest.mark.skipif(not HAS_CONTRIB, reason="needs the opencv-contrib wheel (swap-gate probe env)")
def test_rolling_guidance_with_contrib_takes_the_real_path():
    rgb = _grainy_step_image()
    bg = _no_bg(rgb.shape[:2])
    pp = photo_prep(rgb, bg, 4.0, _cfg(photo_prep=True, photo_prep_texture_kill="rolling_guidance"))
    assert pp.fallback is False and pp.technique == "rolling_guidance"
    # It must still do the job: grain collapses (same bar as bilateral's).
    w = rgb.shape[1]
    def half_std(img):
        return float((img[:, : w // 2 - 20, 0].astype(np.float32).std()
                      + img[:, w // 2 + 20 :, 0].astype(np.float32).std()) / 2.0)
    assert half_std(pp.rgb) < 0.5 * half_std(pp.rgb_tone)


# --- 5. The other techniques + determinism + validation ------------------------


def test_meanshift_runs_and_flattens():
    rgb = _grainy_step_image()
    pp = photo_prep(rgb, _no_bg(rgb.shape[:2]), 4.0,
                    _cfg(photo_prep=True, photo_prep_texture_kill="meanshift"))
    assert pp.technique == "meanshift" and pp.fallback is False
    assert pp.rgb.shape == rgb.shape and pp.rgb.dtype == np.uint8
    w = rgb.shape[1]
    def half_std(img):
        return float((img[:, : w // 2 - 20, 0].astype(np.float32).std()
                      + img[:, w // 2 + 20 :, 0].astype(np.float32).std()) / 2.0)
    assert half_std(pp.rgb) < 0.5 * half_std(pp.rgb_tone)


def test_technique_none_is_tone_prep_only():
    rgb = _grainy_step_image()
    pp = photo_prep(rgb, _no_bg(rgb.shape[:2]), 4.0,
                    _cfg(photo_prep=True, photo_prep_texture_kill="none"))
    assert pp.technique == "none"
    assert np.array_equal(pp.rgb, pp.rgb_tone)


def test_determinism():
    cfg = _cfg(photo_prep=True)
    p = prep(FIXTURE, _cfg())
    a: PhotoPrepResult = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, cfg)
    b: PhotoPrepResult = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, cfg)
    assert np.array_equal(a.rgb, b.rgb)
    assert np.array_equal(a.rgb_tone, b.rgb_tone)


def test_unknown_technique_raises():
    rgb = _grainy_step_image()
    with pytest.raises(ValueError, match="photo_prep_texture_kill"):
        photo_prep(rgb, _no_bg(rgb.shape[:2]), 4.0,
                   _cfg(photo_prep=True, photo_prep_texture_kill="l0smooth"))
