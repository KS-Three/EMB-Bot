"""The MARINE match flags (built OFF 2026-11-18, ON since Kent's 2026-11-19 flip; `docs/marine-pro-construction-2026-11-18.md`),
each pinned on the letter polygons Becker's 102 mm hat hands the lane
(`testdata/marine102_*_letter(s).json`):

* `lettering_columns_a_bar`: the A's crossbar a column of upright crosses between two legs
  that run uncut, in place of a slanted fan beside the left foot;
* `lettering_columns_block_butt_small`: block_butt's heavy-stroke gate 3.5 -> 3.0 mm (MARINE
  at 76.5-79.8 mm measures 3.46);
* `lettering_columns_block_lean`: a heavy block letter's steep strokes cross level (cap 50
  deg, not the satin convention's 30).
OFF is today's byte for byte. (`tests/test_r_bowl.py` has the R's.)"""
from __future__ import annotations

import json
import math
from dataclasses import replace
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc
from digitizer_core import column_lean as cl

TD = Path(__file__).resolve().parent.parent / "testdata"
LANE = {"fold_cuts": True, "mitre_ends": True, "rail_axis": True}


def _poly(name: str) -> Polygon:
    v = json.loads((TD / "marine102_MA_letters.json").read_text(encoding="utf-8"))["marine102_" + name]
    return Polygon(v["exterior"], v["holes"])


def _cut(name: str, **scopes):
    import contextlib
    with contextlib.ExitStack() as st:
        st.enter_context(oc.fold_apex_side_scope(True))
        st.enter_context(oc.block_butt_scope(True))
        for k, on in scopes.items():
            st.enter_context(getattr(oc, k + "_scope")(on))
        return oc.letter_columns(_poly(name), 0.4, corner_fold=True, **LANE)


def _cross_deg(st):
    """Median |cross angle| from level, degrees."""
    out = []
    for p, q in st:
        a = math.degrees(math.atan2(q[1] - p[1], q[0] - p[0])) % 180
        out.append(min(a, 180 - a))
    return sorted(out)[len(out) // 2]


@pytest.mark.parametrize("scope,flag", [("a_bar", "lettering_columns_a_bar"),
                                        ("block_small", "lettering_columns_block_butt_small")])
def test_scopes_off_by_default_and_plan_stitches_sets_them(scope, flag, monkeypatch):
    var = {"a_bar": oc._A_BAR, "block_small": oc._BLOCK_SMALL}[scope]
    assert var.get() is False
    with getattr(oc, scope + "_scope")(True):
        assert var.get() is True
    assert var.get() is False
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: var.get())
    assert pipeline.plan_stitches(None, PipelineConfig()) is True              # ON since Kent's 2026-11-19 flip
    assert pipeline.plan_stitches(None, replace(PipelineConfig(), **{flag: False})) is False


def test_block_lean_scope_is_off_by_default_and_set_from_the_field(monkeypatch):
    assert cl._BLOCK_LEAN.get() is False
    with cl.block_lean_scope(True):
        assert cl._BLOCK_LEAN.get() is True
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: cl._BLOCK_LEAN.get())
    assert pipeline.plan_stitches(None, PipelineConfig()) is True
    assert pipeline.plan_stitches(None, replace(PipelineConfig(), lettering_columns_block_lean=False)) is False


def test_all_four_fields_default_on_and_the_pre_flip_arm_turns_them_off():
    from tests.conftest import PRE_FLIP, MARINE_MATCH_2026_11_19_OFF
    for k in MARINE_MATCH_2026_11_19_OFF:
        assert getattr(PipelineConfig(), k) is True
        assert PRE_FLIP[k] is False
    import json
    pins = json.loads((Path(__file__).resolve().parent / "engine_2026_10_27.json").read_text(encoding="utf-8"))
    assert all(pins[k] is False for k in MARINE_MATCH_2026_11_19_OFF)


def test_a_bar_off_leaves_the_left_foot_and_bar_one_piece():
    lc = _cut("A", a_bar=False)
    assert not any(c.kind == "straight" and len(c.stations) < 14 and _cross_deg(c.stations) > 80 for c in lc.columns)
    assert any(c.kind == "curved" for c in lc.columns)           # the bar + left foot fan


def test_a_bar_on_the_bar_is_upright_between_two_straight_legs():
    lc = _cut("A", a_bar=True)
    assert len(lc.columns) == 3 and not lc.unsewn
    assert all(c.kind == "straight" for c in lc.columns)
    bar = [c for c in lc.columns if _cross_deg(c.stations) > 85]
    assert len(bar) == 1
    lens = [math.dist(a, b) for a, b in bar[0].stations]
    assert 3.0 < sorted(lens)[len(lens) // 2] < 6.0               # his: 4.5-4.7 mm, constant
    legs = [c for c in lc.columns if c is not bar[0]]
    assert all(oc.pivot_sweep(c.stations) <= 25 for c in legs)


def test_a_bar_changes_nothing_for_a_letter_with_no_counter():
    a = _cut("M", a_bar=False)
    b = _cut("M", a_bar=True)
    assert [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_block_small_lowers_the_gate_only_when_on():
    assert oc._butt_min_w() == oc.BUTT_MIN_W_MM
    with oc.block_small_scope(True):
        assert oc._butt_min_w() == oc.BUTT_MIN_W_SMALL_MM < oc.BUTT_MIN_W_MM


def test_block_small_gate_clears_every_other_committed_job():
    # measured widest letter per job (docs/block-butt-2026-11-18.md section 6): 0.8-1.7 mm
    assert oc.BUTT_MIN_W_SMALL_MM > 1.7 + 1.0


def test_block_lean_crosses_the_m_diagonals_level_and_off_does_not():
    from digitizer_core.columns import Column
    lc = _cut("M")
    diag = [c for c in lc.columns if c.kind == "straight" and c.axis is not None and abs(c.axis[0]) > 0.5]
    assert diag
    col = diag[0]
    off = cl.lean_column(col, 0.0, 0.4)
    with cl.block_lean_scope(True):
        on = cl.lean_column(col, 0.0, 0.4)
    assert _cross_deg(on.stations) < 3                              # level
    assert _cross_deg(off.stations) > 10                            # the 30 deg cap leaves it 15-25 off
    assert isinstance(on, Column)


def test_block_lean_leaves_an_upright_arm_alone():
    lc = _cut("A")
    for c in lc.columns:
        if c.kind != "straight" or c.axis is None:
            continue
        a = cl.lean_column(c, 0.0, 0.4)
        with cl.block_lean_scope(True):
            b = cl.lean_column(c, 0.0, 0.4)
        if abs(c.axis[0]) > 0.9:               # a near-horizontal stroke: its near-upright cross must not tilt further
            assert [s for s in b.stations] == [s for s in a.stations]


# ------------------------------------------------- e_top_arm and top_slab (built OFF 2026-11-19)
def _poly_en(name: str) -> Polygon:
    v = json.loads((TD / "marine102_EN_letters.json").read_text(encoding="utf-8"))["marine102_" + name]
    return Polygon(v["exterior"], v["holes"])


def _cut_en(name: str, **scopes):
    import contextlib
    with contextlib.ExitStack() as st:
        st.enter_context(oc.fold_apex_side_scope(True))
        st.enter_context(oc.block_butt_scope(True))
        for k, on in scopes.items():
            st.enter_context(getattr(oc, k + "_scope")(on))
        return oc.letter_columns(_poly_en(name), 0.4, corner_fold=True, **LANE)


def test_e_top_arm_and_top_slab_scopes_are_off_by_default_and_put_themselves_back():
    for var, scope in ((oc._E_TOP, "e_top"), (oc._TOP_SLAB, "top_slab")):
        assert var.get() is False
        with getattr(oc, scope + "_scope")(True):
            assert var.get() is True
        assert var.get() is False


def test_e_top_arm_on_the_top_arm_is_one_upright_band_over_the_stems_top():
    off = _cut_en("E", e_top=False)
    on = _cut_en("E", e_top=True)
    assert len(off.columns) == len(on.columns) == 4
    band = min(on.columns, key=lambda c: c.piece.bounds[1] * 1000 - c.piece.area)
    x0, y0, x1, y1 = on.poly.bounds
    assert band.piece.bounds[0] <= x0 + 1.5 and band.piece.bounds[2] >= x1 - 1.5      # the whole width of the letter
    assert _cross_deg(band.stations) > 85                                                # upright crosses
    stem = max(on.columns, key=lambda c: c.piece.bounds[3] - c.piece.bounds[1])
    assert _cross_deg(stem.stations) < 3                                                 # the stem below stays level


def test_e_top_arm_off_is_block_butts_cut():
    a, b = _cut_en("E"), _cut_en("E", e_top=False)
    assert [c.stations for c in a.columns] == [c.stations for c in b.columns]


@pytest.mark.parametrize("name", ["M", "A"])
def test_top_slab_on_one_upright_band_across_the_top_and_off_is_unchanged(name):
    a = _cut(name)
    off = _cut(name, top_slab=False)
    assert [c.stations for c in a.columns] == [c.stations for c in off.columns]
    on = _cut(name, top_slab=True)
    x0, y0, x1, y1 = on.poly.bounds
    bands = [c for c in on.columns if c.piece.bounds[1] <= y0 + 0.05 and c.piece.bounds[3] < y0 + 0.5 * (y1 - y0)]
    assert len(bands) == 1 and not on.unsewn
    assert 70 < _cross_deg(bands[0].stations) < 85                                       # sheared, near upright (his -74 to -90)
    # the band is the letter's own polygon: no cross leaves it
    from shapely.geometry import LineString
    assert all(on.poly.buffer(0.05).contains(LineString(st)) for st in bands[0].stations)
