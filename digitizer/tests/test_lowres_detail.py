"""`tools/lowres_detail.py` — the scoring half, on rasters whose answer is
known. The digitizing half is the pipeline; it is not re-tested here."""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

from lowres_detail import RASTER_PX_PER_MM, score  # noqa: E402

RED, TEAL, YELLOW = (216, 44, 48), (51, 153, 153), (255, 237, 56)


def _canvas():
    """A 30 x 30 mm design at the instrument's raster: a 10 x 10 mm block and,
    beside it, a 1 mm stroke 10 mm long — fine ink by the 1.5 mm rule."""
    n = int(30 * RASTER_PX_PER_MM)
    rgb = np.zeros((n, n, 3), np.uint8)
    mask = np.zeros((n, n), bool)
    s = int(RASTER_PX_PER_MM)
    rgb[5 * s:15 * s, 5 * s:15 * s] = RED
    mask[5 * s:15 * s, 5 * s:15 * s] = True
    rgb[5 * s:15 * s, 20 * s:21 * s] = TEAL
    mask[5 * s:15 * s, 20 * s:21 * s] = True
    return rgb, mask, s


def test_a_design_scored_against_itself_is_whole():
    rgb, mask, _ = _canvas()
    out = score(rgb, mask, rgb, mask)
    assert out["agree"] == 1.0 and out["fine"] == 1.0
    assert out["fine_mm2"] == pytest.approx(10.0, abs=1.5)      # the stroke, and only the stroke


def test_a_lost_stroke_is_the_fine_score_not_the_area_score():
    """The block is ten times the stroke's area, so area agreement barely
    notices the stroke going; the fine score is nothing else."""
    rgb, mask, s = _canvas()
    arm_rgb, arm_mask = rgb.copy(), mask.copy()
    arm_mask[5 * s:15 * s, 20 * s:21 * s] = False
    out = score(rgb, mask, arm_rgb, arm_mask)
    assert out["fine"] == 0.0
    assert 0.88 <= out["agree"] <= 0.93


def test_a_stroke_sewn_in_the_grounds_colour_is_lost():
    rgb, mask, s = _canvas()
    arm_rgb = rgb.copy()
    arm_rgb[5 * s:15 * s, 20 * s:21 * s] = YELLOW
    assert score(rgb, mask, arm_rgb, mask)["fine"] == 0.0


def test_a_neighbouring_spool_and_a_third_of_a_millimetre_are_forgiven():
    """Two runs of one logo pick neighbouring cones for one ink and place an
    edge a few tenths apart; neither is a lost stroke."""
    rgb, mask, s = _canvas()
    arm_rgb, arm_mask = np.zeros_like(rgb), np.zeros_like(mask)
    shift = int(0.3 * RASTER_PX_PER_MM)
    arm_rgb[:, shift:] = rgb[:, :-shift]
    arm_mask[:, shift:] = mask[:, :-shift]
    arm_rgb[(arm_rgb == TEAL).all(axis=2)] = (0, 155, 170)       # Marine Aqua for Caribbean
    out = score(rgb, mask, arm_rgb, arm_mask)
    assert out["fine"] >= 0.95


def test_a_different_frame_is_centred_not_refused():
    """Design frames are centred on the design; an arm whose bbox came out a
    millimetre wider is compared about the centre."""
    rgb, mask, _ = _canvas()
    pad = int(RASTER_PX_PER_MM)
    arm_rgb = np.pad(rgb, ((pad, pad), (pad, pad), (0, 0)))
    arm_mask = np.pad(mask, pad)
    out = score(rgb, mask, arm_rgb, arm_mask)
    assert out["agree"] == 1.0 and out["fine"] == 1.0
