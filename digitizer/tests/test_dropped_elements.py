"""Metric-core tests for tools/dropped_elements.py.

Pure-array tests only: no corpus, no engine run, no service — the rule
`test_enginefidelity.py` states for its sibling instrument. The full-set run is
a tool invocation, not a suite concern.

This instrument exists because Kent looked at fourteen stitch-outs on
2026-08-27 and named whole elements going missing on seven of them, while
`preflight.ARTWORK_UNCOVERED` reported `0.0 mm2` on six of those seven and
`artfidelity_self` ranked two of them mid-table. The tests below pin the part
that took three attempts to get right: WHAT gets segmented.
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import dropped_elements as de  # noqa: E402


def write_rgba(path, rgba):
    Image.fromarray(rgba.astype(np.uint8), "RGBA").save(path)


def solid(h, w, rgb):
    return np.tile(np.array(rgb, np.uint8), (h, w, 1))


# ---------------------------------------------------------------- constants

def test_lost_threshold_is_well_above_merely_visible():
    # The question is not "is the colour slightly off" (preflight owns that at
    # 10.0 "clearly different") but "is the element GONE".
    from digitizer_core.preflight import DELTA_E_CLEARLY_DIFFERENT
    assert de.LOST_DELTA_E > DELTA_E_CLEARLY_DIFFERENT * 1.5


def test_halo_kernel_is_about_one_stitch_wide():
    # Documented as the smallest odd kernel at or above one thread width, so it
    # clears a boundary mismatch of up to roughly a stitch and keeps anything
    # wider. Read machine.py's own number rather than restating 0.40.
    from digitizer_core.machine import COVERAGE_THREAD_W_MM
    mm = de.HALO_OPEN_PX / de.RES
    assert de.HALO_OPEN_PX % 2 == 1, "an even kernel has no centre pixel"
    assert COVERAGE_THREAD_W_MM <= mm <= COVERAGE_THREAD_W_MM + 0.2


# --------------------------------------------------------------- components

def test_components_filters_by_minimum_area():
    m = np.zeros((40, 40), bool)
    m[2:4, 2:4] = True            # 4 px
    m[10:20, 10:20] = True        # 100 px
    _, comps = de._components(m, min_px=50)
    assert len(comps) == 1
    assert comps[0]["area_px"] == 100


def test_components_are_eight_connected():
    # A diagonal hairline is one element to the eye; 4-connectivity would report
    # it as a dotted line of separate specks.
    m = np.zeros((20, 20), bool)
    for i in range(10):
        m[i + 2, i + 2] = True
    _, comps = de._components(m, min_px=1)
    assert len(comps) == 1


# ------------------------------------------------------------- artwork side

def test_art_colour_field_crops_to_ink_and_scales_to_width(tmp_path):
    a = np.zeros((200, 200, 4), np.uint8)
    a[80:120, 60:140] = (200, 30, 40, 255)      # 80x40 px of ink, lots of pad
    p = tmp_path / "pad.png"
    write_rgba(p, a)

    rgb, ink = de.art_colour_field(p, width_mm=20.0)
    assert rgb.shape[1] == int(round(20.0 * de.RES))
    assert rgb.shape[:2] == ink.shape
    # padding must not change the raster: the ink bbox is 2:1, so the height
    # follows the INK, not the file.
    assert rgb.shape[0] == pytest.approx(rgb.shape[1] / 2, abs=1)
    assert ink.mean() > 0.95


def test_art_colour_field_keeps_the_artwork_colours(tmp_path):
    a = np.zeros((100, 100, 4), np.uint8)
    a[20:80, 20:80] = (200, 30, 40, 255)
    p = tmp_path / "red.png"
    write_rgba(p, a)

    rgb, ink = de.art_colour_field(p, width_mm=10.0)
    mid = rgb[rgb.shape[0] // 2, rgb.shape[1] // 2]
    assert abs(int(mid[0]) - 200) < 12 and abs(int(mid[1]) - 30) < 12


# ------------------------------------------------------- the disagreement

def test_identical_images_disagree_nowhere():
    a = solid(60, 60, (200, 30, 40))
    d, wrong = de.disagreement(a, a.copy())
    assert d.max() == pytest.approx(0.0, abs=1e-6)
    assert not wrong.any()


def test_unsewn_ink_is_flagged():
    """The plainest failure: a colour belongs here and the cloth is bare."""
    a = solid(60, 60, (255, 255, 255))
    a[20:40, 20:40] = (200, 30, 40)          # a red element in the artwork
    s = solid(60, 60, (255, 255, 255))       # nothing sewn at all
    _, wrong = de.disagreement(a, s)
    assert wrong[25:35, 25:35].all()
    assert not wrong[0:5, 0:5].any(), "bare cloth where none was asked for"


def test_a_filled_in_knockout_is_flagged():
    """The failure the two earlier designs could not see: bare cloth belongs
    here (a knocked-out letter) and thread was laid over it anyway."""
    a = solid(60, 60, (200, 30, 40))
    a[20:40, 20:40] = (255, 255, 255)        # knockout in the artwork
    s = solid(60, 60, (200, 30, 40))         # sewn solid, knockout gone
    _, wrong = de.disagreement(a, s)
    assert wrong[25:35, 25:35].all()


def test_the_wrong_thread_is_flagged():
    a = solid(60, 60, (255, 255, 255))
    a[20:40, 20:40] = (200, 30, 40)          # should be red
    s = solid(60, 60, (255, 255, 255))
    s[20:40, 20:40] = (30, 60, 200)          # sewn blue
    _, wrong = de.disagreement(a, s)
    assert wrong[25:35, 25:35].all()


def test_a_boundary_hairline_is_opened_away():
    """Every shape edge disagrees by a fraction of a millimetre, because thread
    lands slightly off the ink boundary. That is the SMOOTHNESS complaint, not a
    lost element, and a report full of one-pixel outlines would bury the thing
    this instrument is for."""
    a = solid(60, 60, (255, 255, 255))
    s = solid(60, 60, (255, 255, 255))
    s[30, :] = (200, 30, 40)                 # a 1 px line of disagreement
    _, wrong = de.disagreement(a, s)
    assert not wrong.any()


def test_a_block_wider_than_the_kernel_survives_the_opening():
    a = solid(60, 60, (255, 255, 255))
    s = solid(60, 60, (255, 255, 255))
    w = de.HALO_OPEN_PX + 4
    s[20:20 + w, 20:20 + w] = (200, 30, 40)
    _, wrong = de.disagreement(a, s)
    assert wrong.any(), "a real blob must survive the hairline opening"


def test_a_small_wrong_patch_is_not_hidden_by_a_large_right_one():
    """The bug that killed the third design of this instrument.

    Segmenting the ARTWORK made the background one component spanning the frame;
    a median over it drowned a small filled-in patch and the instrument reported
    nothing. Segmenting the DISAGREEMENT cannot do that, because the patch is
    its own region no matter how much agreeing area surrounds it.
    """
    a = solid(200, 200, (255, 255, 255))     # a big, correct, empty ground
    s = solid(200, 200, (255, 255, 255))
    s[100:112, 100:112] = (200, 30, 40)      # one small wrong patch
    _, wrong = de.disagreement(a, s)
    _, comps = de._components(wrong, min_px=1)
    assert len(comps) == 1
    assert wrong.mean() < 0.01, "the patch is a tiny fraction of the frame"
    assert comps[0]["area_px"] > 0
