"""`cfg.inshape_piece_lift` (built OFF 2026-11-14): the step between two
`stitch_shape` pieces of one shape (`border_from_outline`, `enclosed_white_
keyline`) is lifted when it leaves the shape and sewn as split travel when it
stays on it -- never one needle-down stitch longer than a DST record, laid
across whatever lies between (Becker's 15.0 and 37.5 mm, pinned by Kent)."""
from __future__ import annotations

import math
import sys
from pathlib import Path

from shapely.geometry import Polygon

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from digitizer_core import machine, stitches  # noqa: E402
from digitizer_core.config import PipelineConfig  # noqa: E402
from digitizer_core.stage7_sequence import lift_piece  # noqa: E402
from digitizer_core.stitches import StitchRun  # noqa: E402

# a 40 x 10 mm band with a 20 x 6 mm hole in the middle: pieces left and right
BAND = Polygon([(0, 0), (40, 0), (40, 10), (0, 10)], [[(10, 2), (30, 2), (30, 8), (10, 8)]])


def _runs(start, end):
    return [StitchRun(points=[start, end], kind=stitches.FILL, shape_id="S")]


def test_off_by_default():
    assert PipelineConfig().inshape_piece_lift is False


def test_a_step_across_a_hole_is_lifted_and_cut_without_touching_the_callee_run():
    prev = _runs((2.0, 5.0), (8.0, 5.0))
    nxt = _runs((32.0, 5.0), (38.0, 5.0))
    out = lift_piece(prev, nxt, "S", BAND, trim_at=2.0)
    assert out[0].jump and out[0].trim
    assert out[0].points == nxt[0].points
    assert nxt[0].jump is False and nxt[0].trim is False      # replaced, not mutated
    assert len(out) == len(nxt)


def test_a_short_lift_under_the_cut_threshold_is_a_jump_only():
    # 4.1 mm off a 9.8 mm-wide shape: a jump, not a cut, under a 5 mm trim_at
    prev = _runs((2.0, 5.0), (9.5, 5.0))
    nxt = _runs((10.5, 1.0), (20.0, 1.0))
    out = lift_piece(prev, nxt, "S", Polygon([(0, 0), (9.8, 0), (9.8, 10), (0, 10)]), trim_at=5.0)
    assert out[0].jump and not out[0].trim


def test_a_step_that_stays_on_the_shape_is_sewn_as_split_travel():
    prev = _runs((2.0, 1.0), (5.0, 1.0))
    nxt = _runs((35.0, 1.0), (38.0, 1.0))       # 30 mm along the band's lower bar
    out = lift_piece(prev, nxt, "S", BAND, trim_at=2.0)
    assert out[0].kind == stitches.TRAVEL and not out[1].jump
    pts = [prev[0].points[-1]] + out[0].points + [nxt[0].points[0]]
    assert max(math.dist(a, b) for a, b in zip(pts, pts[1:])) <= machine.MAX_STITCH_MM + 1e-9


def test_a_step_that_already_fits_or_a_callee_jump_is_left_alone():
    prev = _runs((2.0, 1.0), (5.0, 1.0))
    near = _runs((5.2, 1.0), (8.0, 1.0))       # one short stitch on the shape: nothing to split
    assert lift_piece(prev, near, "S", BAND, trim_at=2.0) is near
    jumped = [StitchRun(points=[(32.0, 5.0), (38.0, 5.0)], kind=stitches.FILL, jump=True, shape_id="S")]
    assert lift_piece(prev, jumped, "S", BAND, trim_at=2.0) is jumped
    assert lift_piece([], jumped, "S", BAND, trim_at=2.0) is jumped
