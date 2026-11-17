"""`flat_dark_ink_own_ground` (built OFF 2026-11-16): `absorbed_dark_ink` counts
a dark component absorbed only when the label it carries is also the label of
the ground round it. Synthetic arrays only."""
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
