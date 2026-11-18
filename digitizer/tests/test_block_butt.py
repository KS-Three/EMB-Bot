"""`cfg.lettering_columns_block_butt` (built OFF 2026-11-18 as a `cfg.extra` key, ON since Kent's flip):
a block letter's strokes sew as straight columns butted at the joins, not
fanned from a point (`outline_cut._BLOCK_BUTT`).

Prime-grader scorecard 2026-11-18, Becker hat large MARINE: the R, N and E
"fan their stitches out from one point instead of following the stroke".
The polygons are the letters of Becker's 102 mm hat as stage 7 hands them to
`letter_columns` (`testdata/marine102_R_letter.json`,
`testdata/marine102_EN_letters.json`). Three things, all gated:

* the E's pointed-slot fold (the apex-side fold that sweeps the whole spine in
  one fan) is left cut, so the arms butt the stem;
* the R's stem head: the `mitre` that slants from the counter's corner to the
  letter's corner is a `butt` up the stem's own edge instead;
* a piece that would fan past `SMALL_BOLD_FAN_DEG` is stationed straight, and
  a straight piece's slanted end is not fanned (the N's wedge and diagonal).
"""
from __future__ import annotations

import json
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


def _cut(name: str, on: bool):
    with oc.fold_apex_side_scope(True), oc.block_butt_scope(on):
        return oc.letter_columns(_poly(name), 0.4, corner_fold=True, **LANE)


def _sweep(lc) -> float:
    return max(oc.pivot_sweep(c.stations) for c in lc.columns)


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._BLOCK_BUTT.get() is False
    with oc.block_butt_scope(True):
        assert oc._BLOCK_BUTT.get() is True
    assert oc._BLOCK_BUTT.get() is False


def test_plan_stitches_sets_it_from_the_field_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._BLOCK_BUTT.get())
    on = PipelineConfig()
    assert pipeline.plan_stitches(None, on) is True
    assert pipeline.plan_stitches(None, replace(PipelineConfig(), lettering_columns_block_butt=False)) is False
    assert oc._BLOCK_BUTT.get() is False



@pytest.mark.parametrize("name", ["R", "E", "N"])
def test_off_the_letter_fans(name):
    assert _sweep(_cut(name, False)) > oc.SMALL_BOLD_FAN_DEG


@pytest.mark.parametrize("name", ["R", "E", "N"])
def test_on_no_column_pivots(name):
    assert _sweep(_cut(name, True)) <= oc.SMALL_BOLD_FAN_DEG


def test_on_the_e_keeps_its_slot_cuts_and_butts_arms_to_the_stem():
    lc = _cut("E", True)
    assert not [k for k in lc.cuts if k[2] == "fold"]
    assert len(lc.columns) == 4                       # stem and three arms
    assert all(c.kind == "straight" for c in lc.columns)


def test_on_the_r_stem_head_is_cut_on_the_stems_own_edge():
    off, on = _cut("R", False), _cut("R", True)
    butt = [k for k in on.cuts if k[2] == "butt"]
    assert len(butt) == 1 and not [k for k in off.cuts if k[2] == "butt"]
    (a, b, _r, _l) = butt[0]
    assert abs(a[0] - b[0]) < 0.25                    # upright: the edge of the stem, not a mitre
    assert abs(a[1] - b[1]) > 3.0


def test_on_a_plain_bar_is_the_cut_it_was():
    bar = Polygon([(0, 0), (4, 0), (4, 15), (0, 15)])
    with oc.block_butt_scope(False):
        off = oc.letter_columns(bar, 0.4, **LANE)
    with oc.block_butt_scope(True):
        on = oc.letter_columns(bar, 0.4, **LANE)
    assert off.cuts == on.cuts
    assert [c.stations for c in off.columns] == [c.stations for c in on.columns]
