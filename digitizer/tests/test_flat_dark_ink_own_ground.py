"""`flat_dark_ink_own_ground` (built OFF 2026-11-16): `absorbed_dark_ink` counts
rule v3: a dark component ringed by another label survives (is not carved) only
when its label is a body label (under half its pixels in the dark thin
population) AND a pixel of its own label touches it; letter counters are
refused through `find_dark_thin_ink`'s `glyphs`. Synthetic arrays only."""
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


def test_attached_limb_of_a_body_survives_island_of_it_stays_ink():
    # the same five pieces on label 0, but label 0 is mostly a solid body
    # (cols 0-5, ink share 80/440). Only the first piece touches the body (an
    # attached limb: not carved); the other four are islands of the body's
    # colour ringed by label 1 (strokes: still carved), as NPS's snow streaks.
    dark, merged, valid, first = _ink_label_frame(extra_body=60)
    merged[:, :6] = 0
    off = absorbed_dark_ink(dark, merged, valid)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert off is not None and off.mask[first].all() and int(off.mask.sum()) == 80
    assert on is not None
    assert not on.mask[first].any()
    assert int(on.mask.sum()) == 64


def test_island_of_a_body_label_is_absorbed_with_flag():
    dark, merged, valid = _frame(piece_label=0, ring_label=1)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert on is not None and int(on.mask.sum()) == 16


def test_attached_piece_of_a_body_label_survives_with_flag():
    # the 4x4 piece touches label 0's body (cols 0-19) at col 19/20
    dark, merged, valid = _frame(piece_label=0, ring_label=1)
    merged[28:32, 40:44] = 1
    mask = np.zeros_like(dark.mask)
    mask[28:32, 20:24] = True
    merged[mask] = 0
    dark = _dark(mask)
    off = absorbed_dark_ink(dark, merged, valid)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert off is not None and int(off.mask.sum()) == 16
    assert on is None


def test_a_dark_piece_ringed_by_a_thin_glyph_is_refused_as_a_counter():
    from digitizer_core.thin_ink import find_dark_thin_ink

    class _P:
        px_per_mm = 10.0
        bg_edge_rgb = None
        art_bbox = (0, 0, 120, 120)
        bg_mask = np.zeros((120, 120), bool)
        enclosed_mask = None
    rgb = np.full((120, 120, 3), 255, np.uint8)
    rgb[30:90, 30:90] = (196, 168, 120)
    rgb[56:62, 40:80] = (90, 60, 40)
    p = _P()
    p.rgb = rgb
    valid = np.ones((120, 120), bool)
    glyphs = np.zeros((120, 120), bool)
    glyphs[30:90, 30:90] = True
    assert find_dark_thin_ink(p, PipelineConfig(), valid) is not None
    assert find_dark_thin_ink(p, PipelineConfig(), valid, glyphs=glyphs) is None


def test_ink_share_is_read_over_the_whole_dark_population():
    # label 0: a 10x20 dark component that survives (own share 0.81), a 4x4
    # dark piece ATTACHED to 32 non-dark label-0 px (rows 20-27 above it) and
    # ringed by label 1. The label's ink share is 216/248 = 0.87 only when the
    # survivor counts; over the absorbed piece alone it would be 16/248 and
    # the attached piece would survive.
    merged = np.full((60, 60), 1, np.int32)
    mask = np.zeros((60, 60), bool)
    mask[5:15, 40:60] = True
    mask[28:32, 40:44] = True
    merged[mask] = 0
    merged[20:28, 40:44] = 0
    valid = np.ones((60, 60), bool)
    dark = _dark(mask)
    on = absorbed_dark_ink(dark, merged, valid, own_ground=True)
    assert on is not None
    assert int(on.mask.sum()) == 16
    assert on.mask[28:32, 40:44].all()
