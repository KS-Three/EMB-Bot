"""The bold-letter junction sewn as the pro sews it — `cfg.satin_junction_stack`
(`docs/superpowers/plans/2026-09-19-junction-construction.md`, Kent's ruling
2026-09-19: A + B + C as one flag, OFF).

The defect it is for: the R of the lettering plan's 127 mm fixture under
`satin_lettering_split` folds one column over itself through one welded
corner — 311 self-crossing pairs, all in one run, 294 seated in one junction
blob — and across the nine logos 88% of the seam pairs the blob census reads
sit in the same 30–60° welds.

A: a weld is refused past `_STACK_WELD_TURN_DEG` of turn by the merge's own
baseline and the arms end at the node. B: an arm ending at a meeting of
several runs INTO the node by its own half-width, so the arms stack. C: the
satin junction cover under the arms for whatever is still bare.

Measured 2026-09-19 (first build): the R fixture 311 → 0 pairs at trims
34 → 44, uncovered 0.0 both ways; MARINE at 80 mm 103 → 0 at trims 7 → 9,
uncovered 0.0 both ways; Becker at 100 mm under the split flag uncovered
35.5 → 0.0. Off is byte-identical.

**Built OFF and FLIPPED ON the same day** (Kent's call 2026-09-19, over
those numbers, the nine-logo sheet and the goldens). `False` is the
pre-flip merge, tuck and cover byte for byte, and this file pins both sides.
"""
from __future__ import annotations

import math

import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from digitizer_core.preflight import run_preflight
from digitizer_core.stitches import strip_ties

from .test_lettering_split import FIXTURE as FIXTURE_127
from .test_stroke_order_euler import FIXTURE as FIXTURE_80

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _crossing_pairs(points) -> int:
    """`tools/wide_columns.crossing_pairs` on a run's zigzag with ties and
    splits stripped — within ONE run, the fold this flag is about."""
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
    from wide_columns import crossing_pairs
    return crossing_pairs(s6.strip_splits(strip_ties(points)))


def _run(fixture, width_mm: float, **kw):
    cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest",
                         max_colors=6, **kw)
    gen = build_generation(str(fixture), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return cfg, result, plan


def _letter_folds(result, plan) -> int:
    text = {r.shape_id for r in result.regions if r.meta.get("text_candidate")}
    return sum(_crossing_pairs(run.points) for _b, run in plan.iter_runs()
               if run.kind == "satin" and run.shape_id in text)


def _uncovered(fixture, cfg, result, plan) -> float:
    pf = run_preflight(result, plan, cfg, image=str(fixture))
    return float(pf["metrics"].get("uncovered_total_mm2") or 0.0)


def _points(plan):
    return [r.points for _b, r in plan.iter_runs()]


@pytest.fixture(scope="module")
def m80_off():
    """The pre-flip engine, explicitly."""
    return _run(FIXTURE_80, 80.2, satin_junction_stack=False)


@pytest.fixture(scope="module")
def m80_on():
    """The default since the flip."""
    return _run(FIXTURE_80, 80.2)


@pytest.fixture(scope="module")
def r127_off():
    return _run(FIXTURE_127, 127.4, satin_lettering_split=True,
                satin_junction_stack=False)


@pytest.fixture(scope="module")
def r127_on():
    return _run(FIXTURE_127, 127.4, satin_lettering_split=True)


# --- the flag ---------------------------------------------------------------

def test_the_default_is_on():
    """Built OFF and flipped ON the same day — Kent's call. False stays
    reachable: it is the pre-flip engine, pinned by every OFF fixture here."""
    assert PipelineConfig().satin_junction_stack is True
    assert PipelineConfig(satin_junction_stack=False).satin_junction_stack is False


def test_explicit_on_is_the_default_byte_for_byte(m80_on):
    _c, _r, default = m80_on
    _c2, _r2, explicit = _run(FIXTURE_80, 80.2, satin_junction_stack=True)
    assert _points(explicit) == _points(default)


# --- part A: the weld gate ----------------------------------------------------

def _three_arm_node(turn_deg: float):
    """A node with a straight arm in, an arm out turned by `turn_deg`, and a
    third arm off to the side — the geometry the merge welds through."""
    node = (50, 50)
    length = 30
    a_in = [(node[0] - i, node[1]) for i in range(length, 0, -1)] + [node]
    t = math.radians(turn_deg)
    a_out = [node] + [(int(round(node[0] + i * math.cos(t))),
                       int(round(node[1] + i * math.sin(t)))) for i in range(1, length + 1)]
    a_side = [node] + [(node[0], node[1] - i) for i in range(1, length + 1)]
    return [
        {"pts": a_in, "free_start": True, "free_end": False, "closed": False},
        {"pts": a_out, "free_start": False, "free_end": True, "closed": False},
        {"pts": a_side, "free_start": False, "free_end": True, "closed": False},
    ]


def test_the_gate_refuses_a_bendy_weld_the_default_admits():
    """A 45° turn welds at the shipped threshold (60°) and is refused under
    the stack (30°): the arms stay two strokes."""
    edges = _three_arm_node(45.0)
    shipped = s6._merge_through_junctions(edges)
    assert len(shipped) == 2, "the shipped merge should weld the pair"
    gated = s6._merge_through_junctions(edges, weld_max_dot=s6._STACK_WELD_MAX_DOT)
    assert len(gated) == 3, "the gate should leave all three arms standing"


def test_the_gate_keeps_a_straight_through_weld():
    """A T's bar (0° turn) welds under both thresholds: the gate is about
    the bend, not the junction."""
    edges = _three_arm_node(0.0)
    assert len(s6._merge_through_junctions(edges)) == 2
    assert len(s6._merge_through_junctions(edges, weld_max_dot=s6._STACK_WELD_MAX_DOT)) == 2


def test_the_threshold_is_the_corpus_number():
    """30°, read off `tools/weld_turns.py`'s histogram (the seam pairs sit in
    the 30–60° welds); `None` is the shipped threshold."""
    assert s6._STACK_WELD_TURN_DEG == 30.0
    assert math.isclose(s6._STACK_WELD_MAX_DOT, -math.cos(math.radians(30.0)))
    assert s6._STACK_WELD_MAX_DOT < s6._WELD_MAX_DOT


# --- the fixtures ------------------------------------------------------------

def test_the_R_stops_folding(r127_off, r127_on):
    """The defect the flag is for: 311 → 0 measured. Pinned as a floor —
    under a tenth of what OFF folds — so a later change to the fixture's
    decomposition does not fail this on a handful of pairs."""
    _c1, r_off, p_off = r127_off
    _c2, r_on, p_on = r127_on
    folds_off = _letter_folds(r_off, p_off)
    assert folds_off >= 100, "the fixture should fold OFF"
    assert _letter_folds(r_on, p_on) <= folds_off // 10


def test_the_R_keeps_its_cover_and_its_thread(r127_off, r127_on):
    """Uncovered artwork does not grow (0.0 → 0.0 measured); stitches within
    2% (7,253 → 7,283); trims within +12 (34 → 44)."""
    c_off, r_off, p_off = r127_off
    c_on, r_on, p_on = r127_on
    assert _uncovered(FIXTURE_127, c_on, r_on, p_on) <= _uncovered(FIXTURE_127, c_off, r_off, p_off) + 0.5
    assert abs(p_on.stats.stitch_count - p_off.stats.stitch_count) <= 0.02 * p_off.stats.stitch_count
    assert p_on.stats.trims <= p_off.stats.trims + 12


def test_marine_80_stops_folding_at_two_trims(m80_off, m80_on):
    """103 → 0 at trims 7 → 9 measured: part B is what keeps the trims — the
    proxy without it (the doc's A + C) paid +12."""
    _c1, r_off, p_off = m80_off
    _c2, r_on, p_on = m80_on
    assert _letter_folds(r_off, p_off) >= 50
    assert _letter_folds(r_on, p_on) == 0
    assert p_on.stats.trims <= p_off.stats.trims + 4


def test_marine_80_keeps_its_cover_without_the_junction_cover(monkeypatch):
    """Prediction 2 of the plan (§6): A + B alone leave no bare artwork on
    the fixture — the cover (C) is the backstop, not the construction.
    Falsified if uncovered rises over 0.5 mm² with the cover neutralised."""
    monkeypatch.setattr(s6, "_junction_cover_runs", lambda *a, **k: [])
    cfg, result, plan = _run(FIXTURE_80, 80.2)
    assert _letter_folds(result, plan) == 0
    assert _uncovered(FIXTURE_80, cfg, result, plan) <= 0.5


def test_an_explicit_cover_setting_wins_over_part_c():
    """`satin_patch_junctions=True` (the tatami patch) is kept as asked; part
    C only fills in when nothing was asked for."""
    seen = []
    real = s6.satin_shape

    def spy(poly, shape_id, **kw):
        seen.append(kw.get("patch_junctions"))
        return real(poly, shape_id, **kw)

    import digitizer_core.stage7_sequence as s7
    s7.satin_shape = spy
    try:
        _run(FIXTURE_80, 80.2, satin_patch_junctions=True)
    finally:
        s7.satin_shape = real
    assert seen and all(v is True for v in seen)
