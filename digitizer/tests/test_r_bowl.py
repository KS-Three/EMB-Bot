"""`cfg.extra["lettering_columns_r_bowl"]` (2026-11-18, built OFF): a block letter with one
counter and a stem-head butt (Becker MARINE's R) sews as the pro sews it -- a slab across
the top (upright crosses), the stem (level), the bowl as one band whose crosses turn round
the counter, the leg (level). Read off the pro's R in
`docs/marine-pro-construction-2026-11-18.md`. Layout only: no stitch, floor or compensation
number changes (gate 1). The polygon is the R of Becker's 102 mm hat as stage 7 hands it
to `letter_columns` (`testdata/marine102_R_letter.json`)."""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc

TD = Path(__file__).resolve().parent.parent / "testdata"
LANE = {"fold_cuts": True, "mitre_ends": True, "rail_axis": True}


def _poly(name: str) -> Polygon:
    if name == "R":
        v = json.loads((TD / "marine102_R_letter.json").read_text(encoding="utf-8"))
    else:
        v = json.loads((TD / "marine102_EN_letters.json").read_text(encoding="utf-8"))["marine102_" + name]
    return Polygon(v["exterior"], v["holes"])


def _cut(name: str, bowl: bool, butt: bool = True):
    with oc.fold_apex_side_scope(True), oc.block_butt_scope(butt), oc.r_bowl_scope(bowl):
        return oc.letter_columns(_poly(name), 0.4, corner_fold=True, **LANE)


def _cross_angle(st) -> float:
    """Median |angle| of a column's crosses from level, degrees."""
    a = sorted(abs(math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 180 - (180 if
               math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 180 > 90 else 0)) for p, q in st)
    return a[len(a) // 2]


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._R_BOWL.get() is False
    with oc.r_bowl_scope(True):
        assert oc._R_BOWL.get() is True
    assert oc._R_BOWL.get() is False


def test_plan_stitches_sets_it_from_the_extra_key_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._R_BOWL.get())
    on = replace(PipelineConfig(), extra={"lettering_columns_r_bowl": True})
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, PipelineConfig()) is False
    assert oc._R_BOWL.get() is False


def test_off_is_the_block_butt_cut_byte_for_byte():
    a, b = _cut("R", False), _cut("R", False)
    assert [(k[2], k[0], k[1]) for k in a.cuts] == [(k[2], k[0], k[1]) for k in b.cuts]
    assert [c.kind for c in a.columns] == ["straight", "straight"]        # stem, bowl + leg (block_butt alone)


def test_on_the_r_is_slab_stem_bowl_leg():
    lc = _cut("R", True)
    kinds = sorted(c.kind for c in lc.columns)
    assert kinds == ["curved", "straight", "straight", "straight"]
    assert not lc.unsewn
    bowl = next(c for c in lc.columns if c.kind == "curved")
    assert 40 < oc.pivot_sweep(bowl.stations) < 100   # the crosses turn from the right wall's to the floor's round one corner
    assert len(bowl.stations) > 25
    from shapely.geometry import LineString
    hole = Polygon(_poly("R").interiors[0])
    assert not any(LineString(st).intersection(hole).length > 0.05 for st in bowl.stations)   # none across the counter
    levels = [c for c in lc.columns if c.kind == "straight" and _cross_angle(c.stations) < 3]
    uprights = [c for c in lc.columns if c.kind == "straight" and _cross_angle(c.stations) > 87]
    assert len(levels) == 2 and len(uprights) == 1    # stem and leg level, the slab upright


def test_on_the_bowl_crosses_stay_in_the_letter_and_cover_its_band():
    lc = _cut("R", True)
    bowl = next(c for c in lc.columns if c.kind == "curved")
    from shapely.geometry import LineString
    from shapely.ops import unary_union
    reach = unary_union([LineString([a, b]).buffer(0.2) for a, b in bowl.stations])
    assert bowl.piece.difference(reach).area < 0.12 * bowl.piece.area


@pytest.mark.parametrize("name", ["E", "N"])
def test_a_letter_with_no_counter_is_unchanged(name):
    a, b = _cut(name, False), _cut(name, True)
    assert [(k[2], k[0], k[1]) for k in a.cuts] == [(k[2], k[0], k[1]) for k in b.cuts]
    assert [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_without_block_butt_nothing_happens():
    a, b = _cut("R", False, butt=False), _cut("R", True, butt=False)
    assert [(k[2], k[0], k[1]) for k in a.cuts] == [(k[2], k[0], k[1]) for k in b.cuts]
