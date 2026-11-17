"""`cfg.extra["group_consistent_fill_angle_split_ground"]` (built OFF 2026-11-17).

Energy Star at 85 mm: three blue panels of one thread inside one white
keyline frame filled at 0, 175 and 100 deg, and the odd panel read as a
darker blue. `group_consistency.split_grounds` groups fills that one line
bounds; `split_ground_angles` gives every panel the biggest panel's angle.
"""
from types import SimpleNamespace

from shapely.geometry import Polygon, box

from digitizer_core.group_consistency import split_ground_angles, split_grounds

BLUE, WHITE, RED = 1, 2, 3


def _r(sid, poly, thread):
    return SimpleNamespace(shape_id=sid, polygon=poly, thread_index=thread, meta={})


def _framed_panels():
    """Two blue panels inside one white frame with a white bar between them."""
    top = box(1, 1, 41, 15)
    bottom = box(1, 16, 41, 40)
    frame = box(0, 0, 42, 41).difference(top).difference(bottom)
    return _r("top", top, BLUE), _r("bottom", bottom, BLUE), _r("frame", frame, WHITE)


def test_panels_of_one_frame_are_one_group():
    top, bottom, frame = _framed_panels()
    groups = split_grounds([top, bottom], [frame], 0.25)
    assert [[r.shape_id for r in g] for g in groups] == [["top", "bottom"]]


def test_a_panel_with_lettering_holes_still_counts():
    """The share is read on the outer ring: holes are the lettering it carries."""
    top, bottom, frame = _framed_panels()
    holes = [box(3 + 4 * i, 20, 5 + 4 * i, 36).exterior.coords for i in range(9)]
    bottom.polygon = Polygon(bottom.polygon.exterior.coords, holes)
    assert len(split_grounds([top, bottom], [frame], 0.25)) == 1


def test_fills_of_two_threads_are_two_grounds():
    top, bottom, frame = _framed_panels()
    bottom.thread_index = RED
    assert split_grounds([top, bottom], [frame], 0.25) == []


def test_a_fill_that_only_touches_the_line_is_not_its_panel():
    top, bottom, frame = _framed_panels()
    outside = _r("outside", box(42, 0, 82, 41), BLUE)      # one side of four on the frame
    groups = split_grounds([top, bottom, outside], [frame], 0.25)
    assert [[r.shape_id for r in g] for g in groups] == [["top", "bottom"]]


def test_no_line_no_group():
    top, bottom, _frame = _framed_panels()
    assert split_grounds([top, bottom], [], 0.25) == []


def test_every_panel_takes_the_biggest_panels_angle():
    top, bottom, frame = _framed_panels()
    own = {"top": 100.0, "bottom": 0.0}
    out = split_ground_angles(split_grounds([top, bottom], [frame], 0.25), lambda r: own[r.shape_id])
    assert out == {"top": 0.0, "bottom": 0.0}


def test_a_group_that_agrees_is_left_alone():
    top, bottom, frame = _framed_panels()
    own = {"top": 176.0, "bottom": 0.0}                     # 4 deg apart, mod 180
    assert split_ground_angles(split_grounds([top, bottom], [frame], 0.25),
                               lambda r: own[r.shape_id]) == {}


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("group_consistent_fill_angle_split_ground")
