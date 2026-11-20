"""`satin_lettering_split` (folded into the code 2026-11-19) — split, never fill, for lettering
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
renders. Contracts pinned: the helper lifts the ceiling for a text member
only; every letter sews satin and no letter carries a fill run. (The OFF
arm's own contrasts -- stitches fall, the other regions keep their tiers,
the xfail on the crown holes -- went with the flag; the crown holes are
`satin_crown_cover`'s, `tests/test_crown_cover.py`.) The cost the flag exposes -- a bold letter's
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


def test_the_helper_lifts_the_ceiling_for_lettering_only():
    cap = machine.SATIN_MAX_WIDTH_MM
    on = PipelineConfig()
    assert _satin_ceiling_for(_region(True), on, cap) == (math.inf, True, True)
    assert _satin_ceiling_for(_region(False), on, cap) == (cap, on.satin_per_stroke, bool(on.wide_columns))


# --- through the pipeline ---------------------------------------------------

def _plan(art: Path, **kw):
    # On the skeleton tier, explicitly: the Column lane (`lettering_columns`,
    # ON by default since Kent's 2026-10-12 flip) takes a text-tagged word
    # ahead of the split this file prices, and sews it as columns, never as
    # tatami. The lane's own sewing is pinned in `tests/test_lettering_columns.py`.
    kw.setdefault("lettering_columns", False)
    kw.setdefault("bean_only_lines", False)   # the split's numbers predate the bean rule (ON 2026-10-27)
    kw.setdefault("edge_cap", "bean")         # ...and the "none" default (2026-10-29)
    # ...and the flag ends/seam trio (ON 2026-11-17, Kent). With it ON the strict
    # xfail below (`..._goes_bare_where_the_fill_lane_did_not`) XPASSes: the
    # bare-crown defect it tracks is measured on the engine before the trio.
    from tests.conftest import FLAG_ENDS_SEAM_2026_11_17_OFF
    for name, value in FLAG_ENDS_SEAM_2026_11_17_OFF.items():
        kw.setdefault(name, value)
    cfg =PipelineConfig(target_width_mm=127.4, garment_id="left_chest", max_colors=6, **kw)
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
def on():
    """The shipped engine."""
    return _plan(FIXTURE)


def test_every_letter_sews_satin_and_none_carries_a_fill(on):
    _cfg, result, plan = on
    letters = [r.shape_id for r in result.regions if r.meta.get("text_candidate")]
    tiers = _tiers(plan)
    assert letters
    assert all(tiers.get(s) == {stitches.SATIN} for s in letters), {s: tiers.get(s) for s in letters}
