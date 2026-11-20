"""`cfg.outline_loop_split_shared` (2026-11-18, built OFF): where two holes of
one outline stand under two loop widths apart, the loops' crosses stop at the
line the holes share, so the stem between them is sewn once, not by both.

Prime grader, Becker large (pin x 21 y 8.5): the black stem between the B and
the E was covered by two columns side by side and knotted at the dip."""
from __future__ import annotations

import numpy as np
from shapely.geometry import Polygon, box

from digitizer_core import config as cfgmod
from digitizer_core import machine
from digitizer_core.stage6_border import SPLIT_LAP_MM, keyline_runs

WIDTH = 2.4
GAP = 3.0        # stem between the holes: 1.25 x one loop width, under two


def _band(gap: float = GAP):
    left = box(2.0, 3.0, 10.0, 9.0)
    right = box(10.0 + gap, 3.0, 18.0 + gap, 9.0)
    outer = box(0.0, 0.0, 20.0 + gap, 12.0)
    band = Polygon(outer.exterior, [left.exterior, right.exterior])
    return band, [(Polygon(left.exterior), WIDTH), (Polygon(right.exterior), WIDTH)]


def _satin(runs):
    return [r for r in runs if r.kind == "satin"]


def _loops(split: bool | None, gap: float = GAP):
    band, holes = _band(gap)
    kw = {} if split is None else {"split_shared": split}
    runs, rep = keyline_runs(band, "x", reach=band, entry=None, trim_at_mm=5.0,
                             holes=holes, **kw)
    return _satin(runs), rep


def _stem_reach(runs, x_lo: float, x_hi: float):
    """Per loop: the x range of its satin points that stand in the stem."""
    out = []
    for r in runs:
        p = np.asarray(r.points, float)
        m = (p[:, 0] > x_lo - 1e-6) & (p[:, 0] < x_hi + 1e-6) & (p[:, 1] > 3.5) & (p[:, 1] < 8.5)
        out.append((p[m, 0].min(), p[m, 0].max()) if m.any() else None)
    return out


def test_field_default_is_on_and_pre_flip_is_off():
    # ON since 2026-11-19 (Kent 2026-11-19, shown the OFF | ON review pack: "satin_overlap_run (Recommended), outline_loop_split_shared, through_last, e_top_arm + top_slab")
    from tests.conftest import PRE_FLIP
    assert cfgmod.PipelineConfig().outline_loop_split_shared is True
    assert PRE_FLIP["outline_loop_split_shared"] is False


def test_off_is_byte_identical_to_the_kwarg_left_out():
    a, _ = _loops(None)
    b, _ = _loops(False)
    assert [r.points for r in a] == [r.points for r in b]


def test_off_both_loops_cover_the_whole_stem():
    runs, _ = _loops(False)
    reach = _stem_reach(runs, 10.0, 10.0 + GAP)
    # the first loop sewn reaches past the middle of the stem (13 - 1.5 = 11.5)
    assert max(hi for lo, hi in filter(None, reach)) > 10.0 + GAP / 2 + SPLIT_LAP_MM + 0.1


def test_on_each_loop_stops_at_the_shared_line_and_the_stem_stays_covered():
    runs, rep = _loops(True)
    assert rep["loops"] == 2
    mid = 10.0 + GAP / 2
    # the left hole's loop: its crosses end at the middle of the stem + the lap
    left = [r for r in runs if np.asarray(r.points)[:, 0].mean() < 10.0 + GAP / 2]
    assert left
    reach = _stem_reach(runs, 10.0, 10.0 + GAP)
    los = [lo for lo, hi in filter(None, reach)]
    his = [hi for lo, hi in filter(None, reach)]
    assert min(los) == 10.0 or min(los) < 10.0 + 0.05
    assert max(his) > 10.0 + GAP - 0.05                     # the stem is still covered to the far hole
    # no loop's crosses run more than the lap past the middle line
    for r in runs:
        p = np.asarray(r.points, float)
        stem = p[(p[:, 0] > 10.0 + 0.2) & (p[:, 0] < 10.0 + GAP - 0.2) & (p[:, 1] > 3.5) & (p[:, 1] < 8.5)]
        if not len(stem):
            continue
        centre = stem[:, 0].mean()
        side = -1.0 if centre < mid else 1.0
        assert (side * (stem[:, 0] - mid)).max() <= SPLIT_LAP_MM + 0.05


def test_a_stem_under_two_satin_floors_keeps_both_loops_whole():
    """Along the stem itself (the corner fans, which stand past the holes'
    ends, may still be cut): half the stem plus the lap is under the floor."""
    gap = machine.SATIN_MIN_CROSS_MM
    off, _ = _loops(False, gap)
    on, _ = _loops(True, gap)

    def along(runs):
        return [[p for p in r.points if 3.5 < p[1] < 8.5] for r in runs]
    assert along(off) == along(on)


def test_far_apart_holes_do_not_change():
    off, _ = _loops(False, 6.0)       # 2.5 widths apart: no cross reaches the middle
    on, _ = _loops(True, 6.0)
    assert [r.points for r in off] == [r.points for r in on]
