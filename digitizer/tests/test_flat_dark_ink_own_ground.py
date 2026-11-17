"""`flat_dark_ink_own_ground` (built OFF 2026-11-16): `absorbed_dark_ink` counts
a dark component ringed by another label survives unless its label is an ink
label (at least half its pixels in the dark thin population). Synthetic arrays
only."""
import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core.thin_ink import ThinInk, absorbed_dark_ink


def _dark(mask):
    labels = np.full(mask.shape, -1, np.int32)
    labels[mask] = 0
    return ThinInk(mask=mask, labels=labels, spools=[7], components=1,
                   length_mm=1.0, dark=1)


def _frame(piece_label, ring_label=1):
    """60x60 foreground. Label 0 is big (left third); the rest is `ring_label`;
    a 4x4 dark piece at rows 28-31, cols 40-43 carries `piece_label`."""
    merged = np.full((60, 60), ring_label, np.int32)
    merged[:, :20] = 0
    mask = np.zeros((60, 60), bool)
    mask[28:32, 40:44] = True
    merged[mask] = piece_label
    valid = np.ones((60, 60), bool)
    return _dark(mask), merged, valid


def test_flag_default_is_false():
    assert PipelineConfig().flat_dark_ink_own_ground is False


def test_stroke_on_its_own_ground_is_absorbed_either_way():
    dark, merged, valid = _frame(piece_label=1, ring_label=1)
    for flag in (False, True):
        got = absorbed_dark_ink(dark, merged, valid, own_ground=flag)
        assert got is not None
        assert int(got.mask.sum()) == 16


def test_piece_ringed_by_another_label_survives_only_with_flag():
    dark, merged, valid = _frame(piece_label=0, ring_label=1)
    off = absorbed_dark_ink(dark, merged, valid)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert off is not None and int(off.mask.sum()) == 16
    assert on is None


def test_no_foreground_ring_answers_as_today():
    dark, merged, valid = _frame(piece_label=0, ring_label=1)
    valid = valid.copy()
    # label 0's big block stays foreground; round the piece only it is
    # foreground, so its ring has no foreground pixels
    valid[:, 20:] = False
    valid[dark.mask] = True
    off = absorbed_dark_ink(dark, merged, valid)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert off is not None
    assert on is not None
    assert np.array_equal(off.mask, on.mask)


def test_keyword_off_equals_no_keyword():
    for piece in (0, 1):
        dark, merged, valid = _frame(piece_label=piece)
        a = absorbed_dark_ink(dark, merged, valid)
        b = absorbed_dark_ink(dark, merged, valid, own_ground=False)
        assert (a is None) == (b is None)
        if a is not None:
            assert np.array_equal(a.mask, b.mask)
            assert np.array_equal(a.labels, b.labels)
            assert a.spools == b.spools


def _ink_label_frame(extra_body=0):
    """Label 0 is made of dark strokes: five 4x4 pieces (rows 28-31) ringed
    by label 1, plus `extra_body` non-dark label-0 pixels (a strip at the left
    edge). Returns the frame and the first piece's mask."""
    merged = np.full((60, 60), 1, np.int32)
    mask = np.zeros((60, 60), bool)
    for k in range(5):
        mask[28:32, 6 + 10 * k:10 + 10 * k] = True
    merged[mask] = 0
    if extra_body:
        merged[:extra_body, :1] = 0
    valid = np.ones((60, 60), bool)
    first = np.zeros_like(mask)
    first[28:32, 6:10] = True
    return _dark(mask), merged, valid, first


def test_piece_whose_label_is_the_strokes_is_absorbed_with_flag():
    dark, merged, valid, first = _ink_label_frame()
    for flag in (False, True):
        got = absorbed_dark_ink(dark, merged, valid, own_ground=flag)
        assert got is not None
        assert int(got.mask.sum()) == 80
        assert got.mask[first].all()


def test_piece_whose_label_is_a_solid_body_survives_only_with_flag():
    # the same five pieces on label 0, but label 0 is mostly a solid body
    dark, merged, valid, first = _ink_label_frame(extra_body=60)
    merged[:, :1] = 0                      # 60 body px
    merged[:, 1:6] = 0                     # +300 more: ink share 80/440
    off = absorbed_dark_ink(dark, merged, valid)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert off is not None and off.mask[first].all()
    assert on is None


def test_ink_share_is_read_over_the_whole_dark_population():
    # label 0: a 10x20 dark component that survives (own share 0.85), a 4x4
    # dark piece ringed by label 1, and 20 non-dark px. The label's ink share
    # is 216/236 = 0.92 only when the survivor counts; over the absorbed
    # piece alone it would be 16/236 = 0.07 and the piece would survive.
    merged = np.full((60, 60), 1, np.int32)
    mask = np.zeros((60, 60), bool)
    mask[5:15, 40:60] = True
    mask[28:32, 40:44] = True
    merged[mask] = 0
    merged[:10, :2] = 0
    valid = np.ones((60, 60), bool)
    dark = _dark(mask)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert on is not None
    assert int(on.mask.sum()) == 16
    assert on.mask[28:32, 40:44].all()
