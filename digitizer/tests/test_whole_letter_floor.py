"""`cfg.extra["lettering_columns_whole_letter_floor"]` (built OFF 2026-11-18).

A small serif E: a bold stem with hairline arms. The small-bold cut sews the
stem and drops the arms; the lane's plain cut runs a column along the arms,
but sewn without a floor their 0.3 mm crosses are dropped, so the plain sew
gains nothing and the E reads as an F (Marine Corps emblem at 90 mm, the E
of UNITED, STATES and MARINE, cover 0.84). ON, once the small-bold ladder is
spent and the letter is still under `SMALL_BOLD_COVER_MIN`, the plain cut is
sewn with every thin cross at the floor and kept only if the letter is whole.
"""
from shapely.geometry import Polygon

from digitizer_core.columns import SMALL_BOLD_COVER_MIN, lettering_columns_shape, satin_cover

# The E of UNITED as stage 4 traced it (4.4 x 4.9 mm on the slant): a bold
# stem, hairline top and bottom arms, a wedge of a middle arm.
SERIF_E = Polygon([(2.812, 0.0), (0.0, 0.844), (0.562, 1.219), (1.5, 4.594), (1.219, 4.875),
                   (4.406, 3.844), (4.219, 3.094), (3.938, 3.75), (2.531, 4.312), (1.969, 3.656),
                   (1.688, 2.625), (2.438, 2.438), (2.906, 2.812), (2.625, 1.5), (1.688, 2.344),
                   (1.125, 0.75), (2.062, 0.375), (3.094, 0.75)])
KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5,
          underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
          small_bold=True, short_columns=True, corner_fold=True, inside_stagger=True,
          inside_connectors=True, edge_walk=True, cover_hops=True)


def _sew(**extra):
    return lettering_columns_shape(SERIF_E, "E", **KW, **extra)


def test_off_the_hairline_arms_are_lost():
    runs, report = _sew()
    assert satin_cover(runs, SERIF_E) < SMALL_BOLD_COVER_MIN
    assert "whole_letter_floor" not in report


def test_on_the_letter_sews_whole():
    runs, report = _sew(whole_letter_floor=True)
    assert report.get("whole_letter_floor") == 1
    assert satin_cover(runs, SERIF_E) >= SMALL_BOLD_COVER_MIN


def test_on_a_letter_already_whole_is_untouched():
    bold = Polygon([(0, 0), (3.2, 0), (3.2, 0.9), (0.9, 0.9), (0.9, 3.5), (3.2, 3.5),
                    (3.2, 4.4), (0, 4.4)])
    off, _ = lettering_columns_shape(bold, "C", **KW)
    on, report = lettering_columns_shape(bold, "C", **KW, whole_letter_floor=True)
    assert "whole_letter_floor" not in report
    assert [r.points for r in on] == [r.points for r in off]


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("lettering_columns_whole_letter_floor")
