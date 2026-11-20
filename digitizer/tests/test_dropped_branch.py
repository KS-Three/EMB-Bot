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


# --- `cfg.extra["lettering_columns_sew_dropped_hairline"]` (built OFF 2026-11-18)
# A dropped branch that is a HAIRLINE stroke. Sewn without a floor its crosses
# are dropped; sewn at the floor it adds more thread outside the ink than in,
# and the "net" judge refuses it. The DIA seal at 90 mm, the N of UNITED: both
# 0.3 mm stems took no stitch (cover 0.70; with the branches floored 1.00,
# spill 0.52 -> 1.11: refused). ON, the branches sew at the floor and the
# result is kept when the letter is not whole without it and whole with it.

def test_the_hairline_judge_is_the_whole_letter_rule():
    """The same rule `stroke_floor_keeps_lost_strokes` reads, on the same
    measure: not whole before, whole after."""
    from digitizer_core import stitches
    from digitizer_core.columns import SMALL_BOLD_COVER_MIN, satin_cover, stroke_floor_restores
    from digitizer_core.stitches import StitchRun
    letter = box(0.0, 0.0, 1.0, 4.0)

    def zig(y1):
        pts = [((0.0 if i % 2 == 0 else 1.0), round(0.2 * i, 4)) for i in range(int(y1 / 0.2) + 1)]
        return [StitchRun(points=pts, kind=stitches.SATIN, shape_id="L")]

    part, whole = zig(2.4), zig(4.0)
    assert satin_cover(part, letter) < SMALL_BOLD_COVER_MIN <= satin_cover(whole, letter)
    assert stroke_floor_restores(part, whole, letter)
    assert not stroke_floor_restores(whole, whole, letter)


def test_the_hairline_flag_is_on_since_kent_2026_11_19_and_pre_flip_pins_it_off():
    from digitizer_core import PipelineConfig
    from tests.conftest import DROPPED_HAIRLINE_2026_11_19_OFF, PRE_FLIP
    assert PipelineConfig().lettering_columns_sew_dropped_hairline is True
    assert PRE_FLIP["lettering_columns_sew_dropped_hairline"] is False
    off = PipelineConfig(**DROPPED_HAIRLINE_2026_11_19_OFF)
    assert off.lettering_columns_sew_dropped_hairline is False
