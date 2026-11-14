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
   contrib installed it takes the real path. Since the 2026-08-04
   opencv-contrib-headless swap in requirements.txt, the real-path branch
   is the one that runs in CI and any freshly-installed venv; the fallback
   branch skips there and only fires in a pre-swap env.
5. Determinism — same input, same bytes, twice.
6. The tone switch (`photo_prep_tone`, OFF by default since 2026-11-13):
   off never calls `_tone_prep` and still runs the texture kill; on is
   byte-identical to the engine before the switch; the warning says which
   passes ran. Tests that measure the texture-kill constants set
   `photo_prep_tone=True`, because those constants were swept on the toned
   raster.
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

from .conftest import frozen_cfg
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
        TESTDATA / name,
        # `edge_cap="none"` matches `_golden_snapshot`'s own config
        # (2026-09-11): both sides of a byte-identity comparison must stand on
        # the same engine, and the cap is not what photo_prep is measured
        # against. `sew_enclosed_white=False` likewise: the golden's pin since
        # Kent's 2026-10-26 flip.
        PipelineConfig(target_width_mm=80.0, photo_prep=True, edge_cap="none",
                       sew_enclosed_white=False),
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


# `photo_prep_background_removal=False` is PINNED in the prep-gate tests
# below as of 2026-08-24. Kent flipped that default ON that day, and a
# requested-but-unavailable cutout now skips the entire prep block
# (see pipeline.build_generation) — so without the pin these would stop
# exercising the gate they are named for and quietly start exercising
# the fallback. Exactly why every forced-class acceptance arm pins
# `shade_palette_bind` after its own default moved.
def test_flag_off_emits_no_prep_and_flag_on_emits_one():
    """The opt-in half of the double gate, plus the warning contract."""
    # `photo_prep=False` pinned 2026-09-22, for exactly the reason the block
    # above pins `photo_prep_background_removal`: this arm is named for the
    # flag being OFF and stopped setting it when the DEFAULT flipped ON
    # (`fe007e7c`, Kent's 2026-08-24 ruling -- the `on` arm below already
    # passes `photo_prep=True` explicitly because the default was False when
    # this was written). From that day it ran the flag ON and passed only
    # because a requested-but-unavailable rembg cutout makes
    # `pipeline.build_generation` skip the whole prep block -- the fallback,
    # not the gate. Nobody saw it: `rembg_isolated/venv` is gitignored, so a
    # worktree and a fresh clone have no cutout, and on a checkout that DOES
    # have one this same call crashed in native SEEDS before reaching the
    # assertion (see stage2_photo_segment's SEEDS_MIN_PX_PER_SUPERPIXEL).
    # Measured 2026-09-22 with the cutout forced available: crash fixed, this
    # line then failed honestly on `assert not True`.
    off = run_stages(FIXTURE, _cfg(forced_class="photo_scene", photo_prep=False))
    assert not any(w["code"] == PHOTO_PREP_APPLIED for w in off.warnings)

    on = run_stages(FIXTURE, _cfg(forced_class="photo_scene", photo_prep=True,
                                  photo_prep_background_removal=False))
    applied = [w for w in on.warnings if w["code"] == PHOTO_PREP_APPLIED]
    assert len(applied) == 1
    w = applied[0]
    assert w["technique"] == "bilateral"
    assert w["fallback"] is False
    assert w["kill_px"] >= 2
    assert w["tone_ms"] >= 0 and w["texture_ms"] >= 0
    # Production default since 2026-11-13: the tone pass does not run.
    assert w["tone"] is False and w["tone_ms"] == 0.0


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
    # `photo_prep_tone=True` (OFF by default since 2026-11-13): the filter
    # constants were swept on the TONE-AMPLIFIED grain (~27 std), so this
    # bar is measured on that raster, as it was written.
    cfg = _cfg(photo_prep=True, photo_prep_texture_kill="bilateral", photo_prep_tone=True)
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
    want_rg = _cfg(photo_prep=True, photo_prep_texture_kill="rolling_guidance",
                   photo_prep_tone=True)
    want_bl = _cfg(photo_prep=True, photo_prep_texture_kill="bilateral", photo_prep_tone=True)

    pp_rg = photo_prep(rgb, bg, 4.0, want_rg)
    pp_bl = photo_prep(rgb, bg, 4.0, want_bl)

    assert pp_rg.fallback is True and pp_rg.technique == "bilateral"
    assert np.array_equal(pp_rg.rgb, pp_bl.rgb), "fallback must be bilateral, byte-for-byte"
    assert "fell back" in pp_rg.warnings[0]["message"]


@pytest.mark.skipif(not HAS_CONTRIB, reason="needs the opencv-contrib wheel (swap-gate probe env)")
def test_rolling_guidance_with_contrib_takes_the_real_path():
    rgb = _grainy_step_image()
    bg = _no_bg(rgb.shape[:2])
    pp = photo_prep(rgb, bg, 4.0, _cfg(photo_prep=True, photo_prep_texture_kill="rolling_guidance",
                                       photo_prep_tone=True))  # RGF_SIGMA_COLOR's sweep raster
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
                    _cfg(photo_prep=True, photo_prep_texture_kill="meanshift",
                         photo_prep_tone=True))  # MEANSHIFT_SR's sweep raster
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
                    _cfg(photo_prep=True, photo_prep_texture_kill="none", photo_prep_tone=True))
    assert pp.technique == "none"
    assert np.array_equal(pp.rgb, pp.rgb_tone)
    assert not np.array_equal(pp.rgb, rgb), "the tone pass was asked for and did nothing"


def test_determinism():
    cfg = _cfg(photo_prep=True)
    p = prep(FIXTURE, _cfg())
    a: PhotoPrepResult = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, cfg)
    b: PhotoPrepResult = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, cfg)
    assert np.array_equal(a.rgb, b.rgb)
    assert np.array_equal(a.rgb_tone, b.rgb_tone)


# --- 6. The tone switch (`photo_prep_tone`, OFF since 2026-11-13) -------------
# docs/photo-prep-tone-off-2026-11-13.md. Main's prep output on FIXTURE at
# d9737a7b (the commit before the switch), frozen 2026-10-27 engine at 80 mm:
# md5 of the raw bytes of `pp.rgb` and `pp.rgb_tone`.
MAIN_PREP_RGB_MD5 = "0578755a44d4c1cb42de770370a6e515"
MAIN_PREP_TONE_MD5 = "7d08b35bb6c0a6280f8724888bb0ba8f"


def _md5(a: np.ndarray) -> str:
    import hashlib
    return hashlib.md5(np.ascontiguousarray(a).tobytes()).hexdigest()


def _boom(*_a, **_k):
    raise AssertionError("_tone_prep ran with photo_prep_tone off")


def test_tone_switch_defaults_off_and_the_frozen_engine_keeps_it_on():
    assert PipelineConfig().photo_prep_tone is False
    assert frozen_cfg().photo_prep_tone is True


def test_tone_off_never_calls_tone_prep_and_the_texture_kill_still_runs(monkeypatch):
    import digitizer_core.stage1_photo_prep as spp
    monkeypatch.setattr(spp, "_tone_prep", _boom)
    rgb = _grainy_step_image()
    cfg = _cfg(photo_prep=True)
    pp = photo_prep(rgb, _no_bg(rgb.shape[:2]), 4.0, cfg)
    assert pp.tone is False and pp.technique == "bilateral" and pp.tone_ms == 0.0
    # The raster entering the texture kill is the un-toned input (the
    # 2026-11-13 study's arm B), and the kill is exactly bilateral on it.
    assert np.array_equal(pp.rgb_tone, rgb) and pp.rgb_tone is not rgb
    assert np.array_equal(pp.rgb, spp._bilateral(rgb, spp._kill_scale_px(4.0, cfg)))
    assert not np.array_equal(pp.rgb, rgb)


def test_tone_off_through_the_pipeline_never_calls_tone_prep(monkeypatch):
    import digitizer_core.stage1_photo_prep as spp
    monkeypatch.setattr(spp, "_tone_prep", _boom)
    out = run_stages(FIXTURE, _cfg(forced_class="photo_scene", photo_prep=True,
                                   photo_prep_background_removal=False))
    applied = [w for w in out.warnings if w["code"] == PHOTO_PREP_APPLIED]
    assert len(applied) == 1 and applied[0]["tone"] is False


def test_tone_on_is_byte_identical_to_main():
    for c in (frozen_cfg(target_width_mm=80.0),
              frozen_cfg(target_width_mm=80.0, photo_prep_tone=True)):
        p = prep(FIXTURE, c)
        pp = photo_prep(p.rgb, p.bg_mask, p.px_per_mm, c)
        assert pp.tone is True
        assert _md5(pp.rgb_tone) == MAIN_PREP_TONE_MD5
        assert _md5(pp.rgb) == MAIN_PREP_RGB_MD5


def test_warning_says_which_passes_ran():
    rgb = _grainy_step_image()
    bg = _no_bg(rgb.shape[:2])

    def warning(**kw):
        (w,) = photo_prep(rgb, bg, 4.0, _cfg(photo_prep=True, **kw)).warnings
        assert w["code"] == PHOTO_PREP_APPLIED
        return w

    on = warning(photo_prep_tone=True)
    assert on["tone"] is True
    assert on["message"] == ("Photo prep applied: tone (CLAHE clip 2.5, 8x8 tiles) + "
                             f"texture kill 'bilateral' at {on['kill_px']} px.")
    off = warning()
    assert off["tone"] is False and "CLAHE" not in off["message"]
    assert off["message"] == (f"Photo prep applied: texture kill 'bilateral' at "
                              f"{off['kill_px']} px (tone pass off).")
    neither = warning(photo_prep_texture_kill="none")
    assert neither["tone"] is False and neither["technique"] == "none"
    assert neither["message"] == ("Photo prep applied: no pass ran "
                                  "(tone pass off, texture kill 'none').")


def test_unknown_technique_raises():
    rgb = _grainy_step_image()
    with pytest.raises(ValueError, match="photo_prep_texture_kill"):
        photo_prep(rgb, _no_bg(rgb.shape[:2]), 4.0,
                   _cfg(photo_prep=True, photo_prep_texture_kill="l0smooth"))
