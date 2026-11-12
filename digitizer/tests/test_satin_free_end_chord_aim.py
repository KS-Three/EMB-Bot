"""A free satin end aimed by its chord, not by a raster hook (`cfg.satin_free_end_chord_aim`).

Kent's Flag.webp (96 mm hat, 2026-11-12): every stripe's spine ended in a
0.17 mm last segment leaning 16.5 deg, the tip still mid-stroke (no cap fork
for `_cut_cap_fork`). `_extend_to_cap` aimed the 1.9 mm extension along that
segment, so each left end sewed slanted with its last crosses fanned. And an
end landing exactly ON a square cap kept 2.6 of its 3.9 mm final cross.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.stage6_satin import _extend_to_cap, _CAP_INSET_MM, chord_aim_scope

BAR = box(-50.0, 0.0, 50.0, 4.0)       # a 4 mm stripe, cap at x = -50
HALF = 1.9
# the flag's left end, read from its spine: straight down the middle, then the hook
HOOKED = [(-46.34, 1.86), (-46.18, 1.91), (-46.01, 1.94), (-45.84, 1.94), (-45.68, 1.94),
          (-45.51, 1.94), (-45.0, 1.94), (-44.0, 1.94), (-42.0, 1.94), (-40.0, 1.94)]
STRAIGHT = [(-46.34 + 0.17 * i, 2.0) for i in range(12)]


def _cap(spine, **kw):
    return _extend_to_cap(spine, BAR, HALF, at_start=True, **kw)[0]


def test_default_is_off():
    assert PipelineConfig().satin_free_end_chord_aim is False


def test_the_hook_aims_the_extension_off_true():
    cap = _cap(HOOKED)
    # 1.66 mm along 16.5 deg: the end lands 0.5 mm off the stroke's middle
    assert abs(cap[1] - 1.94) > 0.3


def test_the_chord_aims_it_down_the_stroke():
    cap = _cap(HOOKED, chord_aim=True)
    assert cap[0] == pytest.approx(-50.0 + _CAP_INSET_MM, abs=0.01)
    # the hook's tip itself sits 0.08 mm low, so the chord from it leans a hair
    assert abs(cap[1] - 1.94) < 0.2
    assert abs(cap[1] - 1.94) < 0.4 * abs(_cap(HOOKED)[1] - 1.94)


def test_the_scope_sets_it_for_a_plan():
    with chord_aim_scope(True):
        inside = _cap(HOOKED)
    assert inside == _cap(HOOKED, chord_aim=True)
    assert _cap(HOOKED) != inside             # reset on leaving


def test_an_end_that_agrees_with_its_chord_keeps_its_aim():
    plain, aimed = _cap(STRAIGHT), _cap(STRAIGHT, chord_aim=True)
    assert aimed[1] == plain[1]
    # only the hair inside the cap
    assert aimed[0] - plain[0] == pytest.approx(_CAP_INSET_MM, abs=1e-9)


def test_a_short_spine_is_left_alone():
    short = [(-46.34, 1.86), (-46.18, 1.91), (-46.01, 1.94)]   # under one stroke width
    plain, aimed = _cap(short), _cap(short, chord_aim=True)
    # same aim: the two caps differ only by the inset, along that aim
    assert math.dist(plain, aimed) == pytest.approx(_CAP_INSET_MM, abs=1e-9)
