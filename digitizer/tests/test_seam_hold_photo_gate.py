"""`satin_seam_hold` is held off for photo-class designs (Kent, 2026-11-20).

His ruling, asked what to do about the flip guard's finding that the hold cost
`photo/photo_scene_stub.png` at 80 mm left_chest 11 extra trims (62 -> 73) and 1.0 mm
extra bare thread (1.0 -> 2.0) while its measured gains (Golden Tee -11% stitches,
Gaulke -3%) are logos: "Keep it off photos (Recommended)". `plan_stitches` clears the
flag for `PHOTO_CLASSES`, as it does `outline_inlets_kept`; logos keep the hold.
"""
from tests.conftest import TESTDATA

PHOTO = TESTDATA / "photo" / "photo_scene_stub.png"
LOGO = TESTDATA / "photo" / "logo_golden_tee.jpg"


def _sew(path, **kw):
    from tools.eye_pairs.features import base_cfg, digitize_once

    _gen, result, _plan, design = digitize_once(path, base_cfg(80.0, "left_chest", **kw))
    return result.design_class, design


def test_photo_plans_the_same_as_with_the_hold_off():
    cls_on, on = _sew(PHOTO)
    cls_off, off = _sew(PHOTO, satin_seam_hold=False)
    assert cls_on in ("photo_scene", "photo_subject")
    assert on == off


def test_flat_logo_still_differs():
    cls_on, on = _sew(LOGO)
    _cls_off, off = _sew(LOGO, satin_seam_hold=False)
    assert cls_on not in ("photo_scene", "photo_subject")
    assert on != off
