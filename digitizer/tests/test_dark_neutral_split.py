"""`cfg.dark_neutral_split` (2026-11-19): stage 2 cuts a large dark NEUTRAL region
into near-black and mid-dark panels, only inside the census bounds."""
import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core import stage2_photo_segment as s2
from digitizer_core.stage3_segment import RegionMask


class _P:
    px_per_mm = 4.0


def _prep(rgb):
    p = _P()
    p.rgb = rgb
    return p


def _region(h, w):
    crop = np.ones((h, w), bool)
    return RegionMask(crop=crop, origin=(0, 0), frame_shape=(h, w), layer=0, source="t")


def _art(mid_rgb, base=(2, 2, 2)):
    # 40 x 40 mm at 4 px/mm: near-black base, two 9 x 9 mm panels (81 mm2 each)
    img = np.zeros((160, 160, 3), np.uint8)
    img[:] = base
    img[20:56, 20:56] = mid_rgb
    img[90:126, 90:126] = mid_rgb
    return img


def test_default_off():
    assert PipelineConfig().dark_neutral_split is False


def test_off_returns_input_unchanged():
    p = _prep(_art((60, 60, 60)))
    kept = [_region(160, 160)]
    out, n = s2.split_dark_neutral_regions(p, kept, enabled=False)
    assert out is kept and n == 0


def test_neutral_panels_are_cut_and_union_is_parent():
    p = _prep(_art((60, 60, 60)))
    out, n = s2.split_dark_neutral_regions(p, [_region(160, 160)], enabled=True)
    assert n == 1 and len(out) == 3          # two panels + the remainder
    union = np.zeros((160, 160), bool)
    for r in out:
        assert not (union & r.crop).any()    # disjoint
        union |= r.crop
    assert union.all()                       # nothing lost


def test_chromatic_panels_stay_whole():
    p = _prep(_art((10, 20, 120)))           # a dark blue, not a neutral
    out, n = s2.split_dark_neutral_regions(p, [_region(160, 160)], enabled=True)
    assert n == 0 and len(out) == 1


def test_small_gap_stays_whole():
    p = _prep(_art((30, 30, 30), base=(24, 24, 24)))   # L* gap well under 12
    out, n = s2.split_dark_neutral_regions(p, [_region(160, 160)], enabled=True)
    assert n == 0
