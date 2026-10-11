"""`cfg.bg_structural` (DEFAULT OFF): the background as one paint colour under
smooth shading — existence read at a fixed visible-difference line against a
field fitted to the border ring, extent flooded against that field.

The two stage-1 defects it answers (`docs/kent-review-2026-08-27.md`,
re-verified on main 2026-10-11):

1. `summit_badge`'s background was half removed: a constant modal colour
   cannot follow a vignette, so only the dark corners came off.
2. `BACKGROUND_ABSENT` was decided by `bg_tolerance_lab`, the FLOOD
   tolerance: summit_badge read ABSENT below 4.8, logo_toat_beanie at 3.0.
"""
import dataclasses
from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.threads import rgb_to_lab
from digitizer_core.warnings_codes import BACKGROUND_ABSENT

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
SUMMIT = TESTDATA / "photo" / "summit_badge.png"
BEANIE = TESTDATA / "art" / "logo_toat_beanie.png"

# The range the 2026-08-27 `bg_tolerance_lab` search swept, with the two
# values its verdict crossing sat between.
TOLERANCES = (3.0, 4.0, 4.5, 4.8, 5.0, 6.0, 7.0, 8.0)


def cfg(**kw) -> PipelineConfig:
    return dataclasses.replace(PipelineConfig(), **kw)


def verdict(p) -> str:
    codes = {w["code"] for w in p.warnings}
    if BACKGROUND_ABSENT in codes:
        return "absent"
    if any(w.get("reason") == "subject_dominated_border" for w in p.warnings):
        return "subject_dominated"
    return "background"


def test_off_is_the_default_and_the_shipped_engine():
    assert PipelineConfig().bg_structural is False
    a = prep(SUMMIT, PipelineConfig())
    b = prep(SUMMIT, cfg(bg_structural=False))
    assert np.array_equal(a.bg_mask, b.bg_mask)
    assert np.array_equal(a.rgb, b.rgb)
    assert a.warnings == b.warnings


def _summit_regions(p):
    """Masks in `p.rgb`'s frame: the true background (outside the badge disc
    and the two text lines), the badge disc, and the light text strokes.
    Geometry read off the 900 x 900 source: disc centre (450, 410), outer
    black ring radius ~262 px; text rows 700-830."""
    h, w = p.rgb.shape[:2]
    sy, sx = h / 900.0, w / 900.0
    yy, xx = np.mgrid[0:h, 0:w]
    r = np.hypot((xx / sx) - 450, (yy / sy) - 410)
    text_box = ((yy / sy) >= 700) & ((yy / sy) <= 830) & ((xx / sx) >= 130) & ((xx / sx) <= 770)
    background = (r > 275) & ~text_box
    disc = r < 250
    lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(h, w, 3)
    text_ink = text_box & (lab[..., 0] > 70)
    return background, disc, text_ink


def test_summit_background_is_removed_whole():
    # The two runs come back on different grids: removing the whole vignette
    # narrows the art bbox, so px_per_mm and the working-grid enlargement
    # move. Each mask is read against regions in its own frame.
    off = prep(SUMMIT, PipelineConfig())
    off_cover = off.bg_mask[_summit_regions(off)[0]].mean()
    on = prep(SUMMIT, cfg(bg_structural=True))
    background, disc, text_ink = _summit_regions(on)
    on_cover = on.bg_mask[background].mean()
    # Measured 2026-10-11: OFF 0.383 of the true background, ON 0.9995.
    assert off_cover < 0.5, f"premise gone: OFF already removes {off_cover:.3f}"
    assert on_cover >= 0.98, f"ON removes only {on_cover:.3f} of the background"
    # ...and nothing that is art: the badge and the lettering stay whole.
    assert not on.bg_mask[disc].any(), f"{int(on.bg_mask[disc].sum())} badge px removed"
    # The lettering: no stroke interior removed. Its rim may lose a pixel —
    # ON enlarges summit onto a 949 px grid, where the mask is resized
    # NEAREST and the colour Lanczos (19 of 10,269 rim pixels, measured).
    assert text_ink.sum() > 1000
    core = cv2.erode(text_ink.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
    assert not on.bg_mask[core].any(), "lettering removed with the background"
    assert on.bg_mask[text_ink].mean() < 0.005
    assert verdict(on) == "background"


# Stage-1 verdict at the shipped tolerance, OFF and ON, for every committed
# fixture without a usable alpha channel (alpha sources never reach the
# flood). Measured 2026-10-11. One row changes: photo_chrome_specular is a
# sphere on a dark, noisy backdrop — a background the constant-colour test
# could not see through the noise and the shading field does.
VERDICTS = [
    # fixture, OFF, ON
    ("art/logo_golke_roofing.png", "background", "background"),
    ("art/logo_hotel_fremont_patch.png", "absent", "absent"),
    ("art/logo_mfab_hat.png", "background", "background"),
    ("art/logo_mfab_lc.png", "background", "background"),
    ("art/logo_toat_beanie.png", "background", "background"),
    ("art/logo_toat_machine.png", "background", "background"),
    ("photo/fur_ramp.png", "background", "background"),
    ("photo/gradient_ramp_linear.png", "background", "background"),
    ("photo/gradient_ramp_radial.png", "background", "background"),
    ("photo/logo_bridge_bar.jpg", "background", "background"),
    ("photo/logo_gaulke_roofing.png", "background", "background"),
    ("photo/logo_golden_tee.jpg", "background", "background"),
    ("photo/owl_kent.jpg", "absent", "absent"),
    ("photo/photo_chrome_specular.png", "absent", "background"),
    ("photo/photo_dof_meadow.png", "absent", "absent"),
    ("photo/photo_grass_macro.png", "absent", "absent"),
    ("photo/photo_owl_pale.png", "absent", "absent"),
    ("photo/photo_scene_stub.png", "absent", "absent"),
    ("photo/photo_subject_stub.png", "absent", "absent"),
    ("photo/photo_sunset_backlit.png", "absent", "absent"),
    ("photo/region_blobs.png", "background", "background"),
    ("photo/repro_gradient_white_icon.png", "absent", "absent"),
    ("photo/screenshot_phone_ui_golke.jpg", "background", "background"),
    ("photo/summit_badge.png", "background", "background"),
    ("photo/tight_crop_pale_subject.png", "subject_dominated", "subject_dominated"),
    ("bg_uncertain.png", "background", "background"),
    ("black_ground_holes.png", "background", "background"),
    ("logo_script_tires.png", "background", "background"),
    ("logo_whitebg.png", "background", "background"),
    ("ribbon_curve.png", "background", "background"),
]


@pytest.mark.parametrize("fixture,off_want,on_want", VERDICTS)
def test_verdicts_at_the_shipped_tolerance(fixture, off_want, on_want):
    path = TESTDATA / fixture
    assert verdict(prep(path, PipelineConfig())) == off_want
    on = prep(path, cfg(bg_structural=True))
    assert verdict(on) == on_want
    if on_want == "background":
        assert on.bg_mask.any()


@pytest.mark.parametrize("fixture", [SUMMIT, BEANIE])
def test_the_verdict_does_not_move_with_the_flood_tolerance(fixture):
    off = {t: verdict(prep(fixture, cfg(bg_tolerance_lab=t))) for t in TOLERANCES}
    on = {t: verdict(prep(fixture, cfg(bg_tolerance_lab=t, bg_structural=True)))
          for t in TOLERANCES}
    # The defect, still on main: OFF reads ABSENT at the strict end.
    assert len(set(off.values())) > 1, f"premise gone: OFF is steady {off}"
    assert set(on.values()) == {"background"}, on
