"""`cfg.small_print_floor`: a column nowhere near a counter keeps its floors
(2026-11-17).

The flag's branch in `columns.column_runs` took EVERY column of a floored
letter, and that branch has none of the lane's floors (`thin_floor`,
`_STROKE_FLOOR`, `_RING_FLOOR`): a piece under the cross floor was dropped
instead of sewn at the floor. The SBA logo's subtitle at 90 mm (2.6 mm
letters) lost each t's crossbar, an m's first arch and an r's arm -- letters
with no counter at all. Now only a column whose zigzag comes within the
clearance of a counter takes the branch (`_zigzag_near_counter`).
"""
from shapely.geometry import Polygon

from digitizer_core import outline_cut as oc
from digitizer_core.columns import (_zigzag_near_counter, lettering_columns_shape,
                                    satin_cover)

#: SBA's "t" as the Column lane received it (plan mm, y down): no counter.
SMALL_T = Polygon([
    (27.844, 15.844), (27.844, 16.5), (27.562, 16.594), (27.844, 19.125), (28.688, 19.125),
    (28.688, 17.344), (29.156, 17.25), (29.156, 16.594), (28.688, 16.5), (28.688, 15.844),
])
#: SBA's "a": one counter, about 1.2 mm across.
SMALL_A = Polygon(
    [(-24.938, 16.969), (-25.219, 18.188), (-24.656, 19.031), (-22.312, 19.125),
     (-22.312, 16.594), (-23.25, 16.781), (-24.188, 16.5)],
    [[(-24.0, 17.25), (-23.156, 17.625), (-23.438, 18.469), (-24.0, 18.469), (-24.375, 18.094)]])

LANE_KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5,
               underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
               small_bold=True, short_columns=True, corner_fold=True,
               corner_fold_apex_side=True, inside_stagger=True, inside_connectors=True,
               edge_walk=True)
CLEAR = 0.2          # half a 40 wt laid width, what the flag passes


def _sew(poly, **extra):
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True):
        return lettering_columns_shape(poly, "x", **LANE_KW, **extra)


def test_a_letter_with_no_counter_sews_the_same_with_and_without_the_clearance():
    off, rep_off = _sew(SMALL_T)
    on, rep_on = _sew(SMALL_T, counter_clear_mm=CLEAR)
    assert [r.points for r in on] == [r.points for r in off]
    assert rep_on["columns"] == rep_off["columns"]
    assert rep_on["columns_unsewn"] == 0


def test_the_ts_crossbar_is_sewn_under_the_clearance():
    on, _ = _sew(SMALL_T, counter_clear_mm=CLEAR)
    assert satin_cover(on, SMALL_T) > 0.97


def test_a_letter_with_a_counter_still_holds_its_thread_off_it():
    """The flag's own job is untouched: the a's ring column is near its
    counter, takes the clearance, and covers less of the letter than without
    it (the thread's edge, not its centre, meets the counter)."""
    off, _ = _sew(SMALL_A)
    on, rep_on = _sew(SMALL_A, counter_clear_mm=CLEAR)
    assert [r.points for r in on] != [r.points for r in off]
    assert not rep_on["empty"] and rep_on["columns_unsewn"] == 0
    assert satin_cover(on, SMALL_A) < satin_cover(off, SMALL_A)


def test_zigzag_near_counter():
    hole = list(SMALL_A.interiors[0].coords)
    hx = sum(p[0] for p in hole[:-1]) / (len(hole) - 1)
    hy = sum(p[1] for p in hole[:-1]) / (len(hole) - 1)
    over = [((hx - 1.0, hy), (hx + 1.0, hy))]                 # a cross through the counter
    far = [((-22.5, 16.7), (-22.4, 16.7)), ((-22.5, 16.9), (-22.4, 16.9))]
    assert _zigzag_near_counter(over, SMALL_A, CLEAR)
    assert not _zigzag_near_counter(far, SMALL_A, CLEAR)
    assert not _zigzag_near_counter(over, SMALL_T, CLEAR)     # no counter, never near one
