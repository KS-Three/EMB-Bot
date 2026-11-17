"""`cfg.extra["small_bold_pull_reaches_floor"]` (built OFF 2026-11-17).

The small-bold recipe caps a letter's pull at `SMALL_BOLD_PULL_FRAC` of its
stroke. On a light face that starves the column under one satin cross: HHS's
ring text at 90 mm (0.29-0.34 mm strokes) got 0.045 mm of pull, sewed 0.39 mm
wide and lost its crosses to the floor ("SFRVICFS"). ON, a stroke under the
floor takes its whole shortfall on each rail (`columns.small_bold_pull_cap`).
"""
import pytest
from shapely.geometry import Polygon

from digitizer_core import machine, outline_cut as oc
from digitizer_core.columns import (SMALL_BOLD_PULL_FRAC, lettering_columns_shape,
                                    satin_cover, small_bold_pull_cap)

FLOOR = machine.SATIN_MIN_CROSS_MM


def test_off_the_cap_is_the_share_of_the_stroke():
    for w in (0.2, 0.3, 0.5, 0.9):
        assert small_bold_pull_cap(w) == pytest.approx(SMALL_BOLD_PULL_FRAC * w)


def test_on_a_stroke_under_the_floor_takes_its_shortfall_on_each_rail():
    assert small_bold_pull_cap(0.30, True) == pytest.approx(FLOOR - 0.30)
    # ... so even a hairline half the stroke's width still sews a cross
    assert 0.15 + 2 * small_bold_pull_cap(0.30, True) >= FLOOR


def test_on_a_bold_stroke_is_untouched():
    """From FLOOR / (1 + SMALL_BOLD_PULL_FRAC) up the share is the larger."""
    edge = FLOOR / (1.0 + SMALL_BOLD_PULL_FRAC)
    for w in (edge + 0.001, 0.5, 0.7, 1.2):
        assert small_bold_pull_cap(w, True) == pytest.approx(small_bold_pull_cap(w))


#: The first S of HHS's "SERVICES" as the Column lane received it (plan mm,
#: y down): a light serif letter, stroke width 0.34 mm.
LIGHT_S = Polygon([
    (-7.484, -44.526), (-7.674, -44.242), (-9.0, -44.242), (-9.758, -43.579), (-9.474, -42.442),
    (-7.863, -41.874), (-7.011, -41.211), (-7.011, -40.737), (-7.579, -40.263), (-8.716, -40.358),
    (-9.379, -41.116), (-9.095, -39.884), (-8.905, -40.168), (-7.389, -40.168), (-6.632, -40.737),
    (-6.537, -41.495), (-6.916, -42.063), (-9.379, -43.2), (-9.379, -43.674), (-8.716, -44.147),
    (-7.768, -43.958), (-7.2, -43.2),
])
LANE_KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5,
               underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
               small_bold=True, short_columns=True, corner_fold=True,
               corner_fold_apex_side=True, inside_stagger=True, inside_connectors=True,
               edge_walk=True)


def _sew(**extra):
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True):
        return lettering_columns_shape(LIGHT_S, "S", **LANE_KW, **extra)


def test_a_light_letter_covers_more_of_itself_with_the_floor():
    off, _ = _sew()
    on, _ = _sew(small_bold_pull_floor=True)
    assert satin_cover(on, LIGHT_S) > satin_cover(off, LIGHT_S)


def test_the_flag_changes_nothing_without_small_bold():
    kw = {k: v for k, v in LANE_KW.items() if k != "small_bold"}
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True):
        plain, _ = lettering_columns_shape(LIGHT_S, "S", **kw)
        flagged, _ = lettering_columns_shape(LIGHT_S, "S", **kw, small_bold_pull_floor=True)
    assert [r.points for r in flagged] == [r.points for r in plain]


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("small_bold_pull_reaches_floor")
