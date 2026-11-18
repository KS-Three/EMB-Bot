"""`cfg.extra["lettering_columns_sew_dropped_branch"]` (built OFF 2026-11-18).

Kent's ruling 2026-11-14 on the cover hand-back ("Keep OFF, record") named
the fix nobody had built: the Column lane drops a branch of a letter, so sew
that branch in the lane. The Peace Corps logo at 90 mm: the R of CORPS is cut
once, at its leg; its stem and bowl stay one folded column whose stations run
round the bowl and the top serif, and the whole stem takes no stitch.
`columns.dropped_branches` names the parts of a column's piece its stations
do not reach; the lane cuts each as a letter of its own and sews it, and
keeps the result only on `columns.absorb_gains`.
"""
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core.columns import Column, dropped_branches

W = 2.0
STEM = box(0.0, 0.0, 2.0, 10.0)              # the branch the cut left in the column
ARM = box(2.0, 8.0, 8.0, 10.0)               # the part the stations cover
PIECE = unary_union([STEM, ARM])


def _column(stations, piece=PIECE):
    return Column(stations=stations, piece=piece, kind="curved", axis=None, width_mm=W)


def _arm_stations(x0=2.0, x1=8.0, step=0.4):
    n = int(round((x1 - x0) / step))
    return [((x0 + i * step, 8.0), (x0 + i * step, 10.0)) for i in range(n + 1)]


def test_a_stem_the_stations_never_reach_is_a_dropped_branch():
    found = dropped_branches([_column(_arm_stations())], W)
    assert len(found) == 1
    assert found[0].area > 0.9 * STEM.area
    assert found[0].within(STEM.buffer(0.2))


def test_a_column_whose_stations_cover_its_piece_drops_nothing():
    assert dropped_branches([_column(_arm_stations(), piece=ARM)], W) == []


def test_a_sliver_along_a_rail_is_not_a_branch():
    """Stations 0.3 mm short of one rail leave a strip: thinner than W / 2."""
    short = [((x, 8.3), (x, 10.0)) for (x, _), _b in _arm_stations()]
    assert dropped_branches([_column(short, piece=ARM)], W) == []


def test_a_part_under_one_stroke_square_is_not_a_branch():
    nub = unary_union([ARM, box(0.5, 8.0, 2.0, 10.0)])       # 3 mm2 against W x W = 4
    assert dropped_branches([_column(_arm_stations(), piece=nub)], W) == []


def test_a_column_with_no_stations_names_nothing():
    assert dropped_branches([_column([])], W) == []


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("lettering_columns_sew_dropped_branch")
