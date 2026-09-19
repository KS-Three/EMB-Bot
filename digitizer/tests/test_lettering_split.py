"""`cfg.satin_lettering_split` — split, never fill, for lettering
(`stage7_sequence._satin_ceiling_for`, lettering construction plan step 4,
2026-09-19; Kent's 2026-09-11 rule for the browser lettering engine, applied
on the traced path).

A text-cluster member is classified and sewn with NO width ceiling: the
classifier's width gates never send a letter to tatami, the per-stroke rung
reads its arms, and the emitter's per-station cap is lifted with the
wide-column fold guard holding every bend, so a wide letter stroke is a
split-satin column (crosses over `SPLIT_SATIN_ABOVE_MM` split as they always
did) rather than a fill. The ribbon gates about SHAPE still apply, and every
shape that is not lettering keeps `machine.satin_ceiling_mm`.

Fixtures: the plan's MARINE (`manga_impact`) traced at 127.4 mm, the size
where 14 of the trace's 15 regions and all but one of its six letters fell
to tatami (the route review's "127 mm collapse"), committed with its
renders. Contracts pinned: OFF (the default) is the shipped engine; the
helper lifts the ceiling for a text member only and only under the flag;
ON, every letter sews satin, no letter carries a fill run, the stitches
fall, the uncovered artwork does not grow, and the regions that are not
lettering keep their tiers. The cost the flag exposes -- a bold letter's
junction ball sewn as one fanning column (the R: 311 self-crossing pairs)
-- is DOCTRINE 2026-09-09's "a junction blob is not a column" and is
recorded in scope-history, not pinned here.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig, machine
from digitizer_core import stitches
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import run_preflight
from digitizer_core.regions import Region
from digitizer_core.stage7_sequence import _satin_ceiling_for
from shapely.geometry import Polygon

FIXTURE = (Path(__file__).resolve().parents[2] / "docs" / "renders"
           / "lettering-split-2026-09-19" / "marine_127mm_traced_input.png")


def _region(text: bool) -> Region:
    poly = Polygon([(0, 0), (10, 0), (10, 2), (0, 2)])
    meta = {"text_candidate": True} if text else {}
    return Region(shape_id="r", polygon=poly, thread_index=0, thread_number="1000",
                  area_mm2=poly.area, meta=meta)


def test_the_flag_is_off_by_default():
    """Built OFF; the flip is Kent's."""
    assert PipelineConfig().satin_lettering_split is False


def test_the_helper_lifts_the_ceiling_for_lettering_only_under_the_flag():
    cap = machine.SATIN_MAX_WIDTH_MM
    off = PipelineConfig()
    assert _satin_ceiling_for(_region(True), off, cap) == (cap, off.satin_per_stroke, bool(off.wide_columns))
    assert _satin_ceiling_for(_region(False), off, cap) == (cap, off.satin_per_stroke, bool(off.wide_columns))
    on = PipelineConfig(satin_lettering_split=True)
    assert _satin_ceiling_for(_region(True), on, cap) == (math.inf, True, True)
    assert _satin_ceiling_for(_region(False), on, cap) == (cap, on.satin_per_stroke, bool(on.wide_columns))


# --- through the pipeline ---------------------------------------------------

def _plan(art: Path, **kw):
    cfg = PipelineConfig(target_width_mm=127.4, garment_id="left_chest", max_colors=6, **kw)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    return cfg, result, plan_stitches(result, cfg)


def _tiers(plan) -> dict[str, set]:
    out: dict[str, set] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id and run.kind in (stitches.SATIN, stitches.FILL):
            out.setdefault(run.shape_id, set()).add(run.kind)
    return out


@pytest.fixture(scope="module")
def off():
    assert FIXTURE.exists(), FIXTURE
    return _plan(FIXTURE)


@pytest.fixture(scope="module")
def on():
    return _plan(FIXTURE, satin_lettering_split=True)


def test_off_explicitly_is_the_default(off):
    _cfg, _r, explicit = _plan(FIXTURE, satin_lettering_split=False)
    a = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in off[2].iter_runs()]
    b = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in explicit.iter_runs()]
    assert a == b


def test_off_the_wide_word_falls_to_tatami(off):
    _cfg, result, plan = off
    letters = [r.shape_id for r in result.regions if r.meta.get("text_candidate")]
    tiers = _tiers(plan)
    assert len(letters) >= 5
    assert sum(1 for s in letters if stitches.FILL in tiers.get(s, set())) >= len(letters) - 1   # 5 of 6 measured


def test_on_every_letter_sews_satin_and_none_carries_a_fill(on):
    _cfg, result, plan = on
    letters = [r.shape_id for r in result.regions if r.meta.get("text_candidate")]
    tiers = _tiers(plan)
    assert letters
    assert all(tiers.get(s) == {stitches.SATIN} for s in letters), {s: tiers.get(s) for s in letters}


def test_on_the_shapes_that_are_not_lettering_keep_their_tiers(off, on):
    letters = {r.shape_id for r in on[1].regions if r.meta.get("text_candidate")}
    t_off, t_on = _tiers(off[2]), _tiers(on[2])
    others = (set(t_off) | set(t_on)) - letters
    assert others
    assert {s: t_off.get(s) for s in others} == {s: t_on.get(s) for s in others}


def test_on_the_word_sews_fewer_stitches_and_nothing_goes_bare(off, on):
    assert on[2].stats.stitch_count < off[2].stats.stitch_count                # 9,642 -> 7,753 measured
    pf_off = run_preflight(off[1], off[2], off[0], image=str(FIXTURE))
    pf_on = run_preflight(on[1], on[2], on[0], image=str(FIXTURE))
    assert pf_on["metrics"].get("uncovered_total_mm2", 0.0) <= pf_off["metrics"].get("uncovered_total_mm2", 0.0)
