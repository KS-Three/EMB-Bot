"""Crop against the two stage-1 mechanisms it can disturb."""
from pathlib import Path

import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core import stage1_prep
from digitizer_core.warnings_codes import INPUT_LOW_RESOLUTION

ROOT = Path(__file__).resolve().parents[1]
BECKER = ROOT / "testdata" / "becker_marine_logo.png"


def test_a_crop_that_drops_a_design_under_the_floor_upscales_and_says_so():
    """Cropping removes pixels, so it can push artwork under
    `min_px_per_mm` that cleared it before. That must upscale AND warn --
    silently enlarging is the case `INPUT_LOW_RESOLUTION` exists to report."""
    # `px_per_mm` is measured off the FOREGROUND bbox, not the canvas (see
    # stage1_prep.py's own header comment) -- so the fixture needs a feature
    # that sets a wide bbox pre-crop and falls entirely outside the crop
    # window, leaving only the narrow square to set the bbox post-crop.
    art = np.full((400, 400, 3), 255, np.uint8)
    art[5:9, 10:390] = 20          # wide anchor, outside the crop window
    art[150:250, 150:250] = 20     # narrow square, inside the crop window
    # Pre-crop bbox spans the anchor: 380 px over 80 mm = 4.75 px/mm, above
    # the 4.0 floor.
    clear = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0))
    assert clear.input_px_per_mm >= 4.0
    assert not any(w["code"] == INPUT_LOW_RESOLUTION for w in clear.warnings)

    # Crop to the middle 30% (pixels 140:260): the anchor falls outside it,
    # so only the 100 px square sets the bbox. 100 px over 80 mm = 1.25
    # px/mm, under the floor.
    cropped = stage1_prep.prep(
        art, PipelineConfig(target_width_mm=80.0, crop=(0.35, 0.35, 0.65, 0.65)))
    assert cropped.input_px_per_mm < 4.0
    assert cropped.px_per_mm > cropped.input_px_per_mm     # it upscaled
    assert any(w["code"] == INPUT_LOW_RESOLUTION for w in cropped.warnings)


def test_cropping_an_alpha_cutout_keeps_the_native_frame_bookkeeping_consistent():
    """`native_rgb`/`native_alpha` are the SOURCE's own pixels and `upscale`
    the per-axis factor to `rgb`; stage 4 reads edges from them. After a crop
    they must describe the CROPPED source, not the original frame, or every
    subpixel edge read lands in the wrong place."""
    cfg = PipelineConfig(target_width_mm=100.0, crop=(0.1, 0.1, 0.9, 0.9))
    p = stage1_prep.prep(str(BECKER), cfg)
    assert p.native_rgb is not None and p.native_alpha is not None
    # Same frame as each other, and the recorded factor takes them to `rgb`.
    assert p.native_rgb.shape[:2] == p.native_alpha.shape[:2]
    sx, sy = p.upscale
    assert round(p.native_rgb.shape[1] * sx) == p.rgb.shape[1]
    assert round(p.native_rgb.shape[0] * sy) == p.rgb.shape[0]
