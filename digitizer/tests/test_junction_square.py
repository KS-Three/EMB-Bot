"""`satin_junction_square` (built OFF, 2026-10-08): a stroke's end at a branch
node -- the E's and F's arms meeting the stem, a T's stem under its bar -- is
laid on the stroke's own straight line, the way `satin_join_square` lays a
corner member's end. Free ends and a corner stroke's inner members are not
read; a corner stroke's apex indices ride the shift."""
from __future__ import annotations

import inspect

from digitizer_core import PipelineConfig
from digitizer_core.stage6_satin import Stroke, _square_junction_ends, satin_shape

HALF = 0.5


def _bent_arm(n: int = 40, hook: float = 0.25) -> list[tuple[float, float]]:
    """A horizontal arm 0.1 mm a sample whose last 0.6 mm curve `hook` mm
    off its line into the node -- the medial axis's bend into a T."""
    pts = [(0.1 * i, 0.0) for i in range(n)]
    for k in range(1, 7):
        x, _ = pts[n - 1 - (6 - k)]
        pts[n - 1 - (6 - k)] = (x, hook * (k / 6.0) ** 2)
    return pts


def test_flag_is_off_by_default_everywhere():
    assert PipelineConfig().satin_junction_square is False
    assert inspect.signature(satin_shape).parameters["junction_square"].default is False


def test_a_junction_end_is_laid_on_the_arms_line():
    st = Stroke(spine=_bent_arm(), free_start=True, free_end=False, closed=False)
    out = _square_junction_ends(st, HALF)
    assert out is not st
    assert max(abs(y) for _x, y in out.spine) < 1e-9
    # the free start is untouched
    assert out.spine[:20] == st.spine[:20]


def test_a_free_end_is_never_read():
    st = Stroke(spine=_bent_arm(), free_start=True, free_end=True, closed=False)
    assert _square_junction_ends(st, HALF) is st


def test_a_bend_over_the_cap_keeps_its_line():
    # an apex 0.4 mm (0.8 half-widths) off the line is a bend, not a T --
    # `_STRAIGHT_MAX_MOVE_HALVES` (0.6) leaves it, exactly as at a corner
    st = Stroke(spine=_bent_arm(hook=0.4), free_start=True, free_end=False, closed=False)
    assert _square_junction_ends(st, HALF) is st


def test_corner_indices_follow_a_squared_start():
    arm = list(reversed(_bent_arm()))             # junction end at the START
    leg = [(arm[-1][0], 0.1 * j) for j in range(1, 30)]
    st = Stroke(spine=arm + leg, free_start=False, free_end=True, closed=False,
                corners=[(len(arm) - 1, True)])
    out = _square_junction_ends(st, HALF)
    apex = out.corners[0][0]
    assert out.spine[apex] == st.spine[len(arm) - 1]
    assert out.spine[apex:] == st.spine[len(arm) - 1:]
    assert max(abs(y) for _x, y in out.spine[:apex + 1]) < 1e-9
