"""`cfg.lettering_columns_cover_hops` (built OFF 2026-11-17): a needle-down
travel of a lettering word never crosses fabric that none of its satin
covers. The prime grader's Toat beanie scorecard: a bare run across the c of
Machine's mouth, a hop the link rule called "inside the letter" because the
outline grown by the pull closes the notch the satin leaves open."""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, columns, stitches
from digitizer_core.stitches import StitchRun


def _travel(points, jump=False, trim=False):
    return StitchRun(points=points, kind=stitches.TRAVEL, jump=jump, trim=trim)


def test_flag_is_off_by_default():
    assert PipelineConfig().lettering_columns_cover_hops is False


def test_covered_travel_is_untouched():
    ground = [Polygon([(0, 0), (10, 0), (10, 2), (0, 2)])]
    sat = StitchRun(points=[(0, 0), (1, 2)], kind=stitches.SATIN)
    r = _travel([(1, 1), (5, 1), (9, 1)])
    out = columns._cut_bare_travel([sat, r], ground, {})
    assert out == [sat, r] and out[1] is r and not r.jump and not r.trim


def test_bare_segment_breaks_the_run_with_a_trim():
    ground = [Polygon([(0, 0), (3, 0), (3, 2), (0, 2)]), Polygon([(6, 0), (9, 0), (9, 2), (6, 2)])]
    rep: dict = {}
    r = _travel([(1, 1), (2.5, 1), (3.5, 1.5), (5.5, 1.5), (6.5, 1), (8, 1)])
    nxt = StitchRun(points=[(8, 1), (8.5, 1.2)], kind=stitches.SATIN)
    out = columns._cut_bare_travel([r, nxt], ground, rep)
    assert rep["bare_hops_cut"] >= 1
    assert out[0].points[0] == (1, 1) and not out[0].jump
    assert any(o.jump and o.trim for o in out[1:])      # the far piece is reached by a trim
    assert out[-1] is nxt


def test_entry_walk_is_kept():
    ground = [Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])]
    r = _travel([(-5, 0.5), (0.5, 0.5)])
    assert columns._cut_bare_travel([r], ground, {}, skip_first=True) == [r]


def test_off_is_the_walk_as_it_was():
    """The kwarg defaults False in both emitters, so a call that does not name
    it is the walk it always was."""
    from digitizer_core import script_strokes
    assert columns.column_runs.__kwdefaults__["cover_hops"] is False
    assert script_strokes.script_strokes_shape.__kwdefaults__["cover_hops"] is False
