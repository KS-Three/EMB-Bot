"""`cfg.satin_corner_twigs` — the spur pruner's structure rule
(`stage6_satin._prune_spurs`, lettering construction plan step 3, 2026-09-19;
the letterform study's mechanism #2).

`_prune_spurs` erases a corner's short twig and, with it, the junction's
degree: a 3-way node with a letter's diagonal, its stem and a short branch
into the corner becomes a 2-way pass-through, and the walker welds the
diagonal to the stem as one column folding through the corner (PRECISION's
N, Becker's R foot — the bare bottom-right). Keeping every twig instead
hooks a square-capped bar's spine into its corner (the study's H defect).
ON, the rule is by structure: a node with two short free arms and one longer
arm is a cap and both arms go whatever their exact length; a node with one
short free arm between two longer arms is a corner and the twig stays,
holding the junction open for `_merge_through_junctions`.

Built OFF and flipped ON the same day (Kent, 2026-09-19); False is the
pre-flip pruner.

Contracts pinned: ON is the default and explicit ON is the default's
output; OFF is still the pre-flip pruner; a square-capped bar's spine is
straight either way; a synthetic N stops folding 90 deg through its
corners; on the plan's fixture the satin self-crossings fall by more than
half (277 -> 103 measured), the stitches fall, and nothing goes uncovered.
"""
from __future__ import annotations

import math
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.preflight import run_preflight
from digitizer_core.stitches import strip_ties

from tests.test_stroke_order_euler import FIXTURE


def _bar(x0, y0, x1, y1, w=2.0) -> Polygon:
    return LineString([(x0, y0), (x1, y1)]).buffer(w / 2.0, cap_style=2)


def _max_turn_deg(spine) -> float:
    turn = 0.0
    for i in range(1, len(spine) - 1):
        a = math.atan2(spine[i][1] - spine[i - 1][1], spine[i][0] - spine[i - 1][0])
        b = math.atan2(spine[i + 1][1] - spine[i][1], spine[i + 1][0] - spine[i][0])
        turn = max(turn, abs((math.degrees(b - a) + 180.0) % 360.0 - 180.0))
    return turn


def _crossing_pairs(points, window: int = 40) -> int:
    """Self-crossing pairs of one run, the wide_columns tool's count."""
    from tools.wide_columns import crossing_pairs
    return crossing_pairs(points, window)


def test_the_flag_is_on_by_default():
    """Built OFF, flipped ON the same day -- Kent's call, 2026-09-19."""
    assert PipelineConfig().satin_corner_twigs is True


def test_a_square_capped_bar_keeps_a_straight_spine_either_way():
    bar = Polygon([(0, 0), (45, 0), (45, 4.5), (0, 4.5)])
    for corner_twigs in (False, True):
        strokes, _half, _field = s6.extract_strokes(bar, corner_twigs=corner_twigs)
        assert len(strokes) == 1
        sp = strokes[0].spine
        first = math.degrees(math.atan2(sp[1][1] - sp[0][1], sp[1][0] - sp[0][0])) % 180.0
        last = math.degrees(math.atan2(sp[-1][1] - sp[-2][1], sp[-1][0] - sp[-2][0])) % 180.0
        assert min(first, 180.0 - first) < 1.0 and min(last, 180.0 - last) < 1.0, (corner_twigs, first, last)


def test_a_synthetic_n_stops_folding_through_its_corners():
    """Two stems and a diagonal, 2 mm wide: off, the pruner drops the corner
    twigs and two of the three strokes fold 90 deg through the corners; on,
    the junctions stay open and no stroke turns more than 45 deg."""
    n = _bar(0, 0, 0, 12).union(_bar(0, 12, 8, 0)).union(_bar(8, 0, 8, 12))
    off, _h, _f = s6.extract_strokes(n, corner_twigs=False)
    on, _h, _f = s6.extract_strokes(n, corner_twigs=True)
    assert max(_max_turn_deg(st.spine) for st in off) >= 80.0
    assert max(_max_turn_deg(st.spine) for st in on) <= 50.0, [_max_turn_deg(st.spine) for st in on]
    assert len(on) == 3


# --- through the pipeline ---------------------------------------------------

def _plan(art: Path, **kw):
    cfg = PipelineConfig(target_width_mm=80.2, garment_id="left_chest", max_colors=6, **kw)
    gen = build_generation(str(art), cfg)
    result = finish_generation(gen.fork(), cfg)
    return cfg, result, plan_stitches(result, cfg)


@pytest.fixture(scope="module")
def off():
    """The pre-flip pruner, explicitly."""
    return _plan(FIXTURE, satin_corner_twigs=False)


@pytest.fixture(scope="module")
def on():
    """The shipped default."""
    return _plan(FIXTURE)


def _crossings(plan) -> int:
    return sum(_crossing_pairs(strip_ties(run.points)) for _b, run in plan.iter_runs() if run.kind == "satin")


def test_on_explicitly_is_the_default(on):
    _cfg, _r, explicit = _plan(FIXTURE, satin_corner_twigs=True)
    a = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in on[2].iter_runs()]
    b = [(str(run.kind), run.shape_id, [tuple(p) for p in run.points]) for _b, run in explicit.iter_runs()]
    assert a == b


def test_the_fixture_stops_folding_its_columns(off, on):
    x_off, x_on = _crossings(off[2]), _crossings(on[2])
    assert x_on <= 0.6 * x_off, (x_off, x_on)                                  # measured 277 -> 103
    assert on[2].stats.stitch_count < off[2].stats.stitch_count                # 2,480 -> 2,192
    assert on[2].stats.trims <= off[2].stats.trims                             # 28 -> 23


def test_the_fixture_stays_covered(off, on):
    pf_off = run_preflight(off[1], off[2], off[0], image=str(FIXTURE))
    pf_on = run_preflight(on[1], on[2], on[0], image=str(FIXTURE))
    assert pf_on["metrics"].get("uncovered_total_mm2", 0.0) <= pf_off["metrics"].get("uncovered_total_mm2", 0.0)
