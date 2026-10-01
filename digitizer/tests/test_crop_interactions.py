"""Crop against the two stage-1 mechanisms it can disturb."""
from pathlib import Path

import cv2
import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core import stage1_prep
from digitizer_core.crop import validate_crop
from digitizer_core.warnings_codes import INPUT_LOW_RESOLUTION

ROOT = Path(__file__).resolve().parents[1]
BECKER = ROOT / "testdata" / "becker_marine_logo.png"


def test_a_crop_that_drops_a_design_under_the_floor_upscales_and_says_so():
    """Cropping removes pixels, so it can push artwork under
    `min_px_per_mm` that cleared it before. That must upscale AND warn --
    silently enlarging is the case `INPUT_LOW_RESOLUTION` exists to report."""
    # px/mm is measured on the ARTWORK's bounding box, not the frame, so the
    # artwork must span the frame for the arithmetic below to hold: an opaque
    # band touching both side edges (a crop of empty margin would move
    # nothing). Alpha marks the background, since a band that touches the
    # side edges defeats border-colour detection on an opaque array.
    art = np.zeros((400, 400, 4), np.uint8)      # BGRA, fully transparent
    art[150:250, :, :3] = 20
    art[150:250, :, 3] = 255
    # 400 px of artwork over 80 mm = 5.0 px/mm, above the 4.0 floor.
    clear = stage1_prep.prep(art, PipelineConfig(target_width_mm=80.0))
    assert clear.input_px_per_mm >= 4.0
    assert not any(w["code"] == INPUT_LOW_RESOLUTION for w in clear.warnings)

    # Crop to the middle 30%, cutting into the band: 120 px over 80 mm = 1.5 px/mm, under the floor.
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
    # The asserts above only relate native_rgb to rgb, which come from the
    # SAME frame, so they hold with the crop removed too. This one does not:
    # the native frame is the cropped box of the source, absolutely.
    src_h, src_w = cv2.imread(str(BECKER), cv2.IMREAD_UNCHANGED).shape[:2]
    x0, y0, x1, y1 = validate_crop(cfg.crop, (src_h, src_w))
    assert p.native_rgb.shape[:2] == (y1 - y0, x1 - x0)
    assert p.native_rgb.shape[:2] != (src_h, src_w)
