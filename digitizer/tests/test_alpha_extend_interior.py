"""`cfg.extra["alpha_extend_keeps_interior"]` (built OFF 2026-11-18).

`alpha_edge.extend_opaque_colour` gives every pixel under alpha 255 the
colour of its nearest fully opaque pixel, so what an exporter left under an
edge's transparency cannot leak into the filters. The HUD seal's white disc
is alpha 253: nearly opaque, 77% of the foreground. Read as non-opaque, the
whole disc took its neighbours' blue and green, and stage 0 classed a flat
logo `gradient` on that smear (`tonal_frac` 0.647; 0.003 with the flag).
ON, a foreground pixel well inside the foreground keeps its own colour.
"""
import numpy as np

from digitizer_core.alpha_edge import (INTERIOR_EDGE_PX, INTERIOR_KEY, extend_opaque_colour,
                                       interior_opaque)

WHITE, BLUE, JUNK = (255, 255, 255), (20, 90, 200), (0, 0, 0)


def _disc():
    """A 60 px white plate at alpha 253 holding a 12 px opaque blue square,
    on a transparent ground whose RGB is junk."""
    rgb = np.zeros((80, 80, 3), np.uint8)
    rgb[:] = JUNK
    alpha = np.zeros((80, 80), np.uint8)
    rgb[10:70, 10:70] = WHITE
    alpha[10:70, 10:70] = 253
    rgb[34:46, 34:46] = BLUE
    alpha[34:46, 34:46] = 255
    return rgb, alpha


def test_off_the_nearly_opaque_plate_takes_the_squares_colour():
    rgb, alpha = _disc()
    out = extend_opaque_colour(rgb, alpha)
    assert tuple(out[20, 20]) == BLUE                    # the fault


def test_on_the_plate_keeps_its_own_colour():
    rgb, alpha = _disc()
    out = extend_opaque_colour(rgb, alpha, keep_interior=True)
    assert tuple(out[20, 20]) == WHITE
    assert tuple(out[40, 40]) == BLUE


def test_on_the_junk_under_the_transparent_ground_is_still_replaced():
    rgb, alpha = _disc()
    out = extend_opaque_colour(rgb, alpha, keep_interior=True)
    assert tuple(out[5, 40]) == WHITE                    # nearest artwork colour, not JUNK
    assert tuple(out[11, 40]) == WHITE                   # the edge ring too


def test_the_edge_ring_is_not_interior():
    _rgb, alpha = _disc()
    inside = interior_opaque(alpha)
    assert not inside[10, 40] and not inside[10 + INTERIOR_EDGE_PX - 1, 40]
    assert inside[10 + INTERIOR_EDGE_PX, 40]


def test_on_a_file_with_no_semi_opaque_plateau_is_unchanged():
    rgb = np.zeros((40, 40, 3), np.uint8)
    rgb[:] = JUNK
    alpha = np.zeros((40, 40), np.uint8)
    rgb[8:32, 8:32] = BLUE
    alpha[8:32, 8:32] = 255
    a = extend_opaque_colour(rgb, alpha)
    b = extend_opaque_colour(rgb, alpha, keep_interior=True)
    assert np.array_equal(a, b)


def test_the_halo_bound_still_applies():
    rgb, alpha = _disc()
    out = extend_opaque_colour(rgb, alpha, 3, keep_interior=True)
    assert tuple(out[2, 40]) == JUNK                     # further than 3 px from the artwork
    assert tuple(out[8, 40]) == WHITE


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get(INTERIOR_KEY)
