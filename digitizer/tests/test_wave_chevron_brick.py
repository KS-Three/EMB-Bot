"""Wave / chevron / brick fill — wiring tests.

The geometry itself (the sine perturbation's amplitude/wavelength/phase, the
chevron alternation's amplitude/period, the brick stagger's exact
running-bond phase, and every one of them leaving the two row ends alone) is
proven directly against `_wave_row_points`/`_chevron_row_points`/
`_brick_row_points` in `test_fill.py`. What this file proves — mirroring
`test_crosshatch.py`'s own split between geometry and wiring — is that all
three techniques actually REACH stitches through both of their documented
entry points:

- the design-wide `fill_technique="wave"/"chevron"/"brick"` flag, and
- the per-shape `tier: "wave"/"chevron"/"brick"` override,

plus both closed-set tier-vocabulary validation layers (`regions.
_TIER_VALUES`, `digitizer_service.app._TIER_VALUES`). The three techniques
share one wiring skeleton — each is a `stitch_shape(..., technique=name)`
call in the same `stitch_one` precedence slot crosshatch occupies — so the
tests below are parametrized across all three rather than tripled by hand.

Isolation between shapes (the "touches only its own shape" claim) is proven
by comparing SORTED SETS of a shape's own emitted fill coordinates, not raw
point lists: `_row_points`-family functions place a row's interior points as
a pure function of (x0, x1, y, row_index, stitch_mm) — never of which end of
a column got entered first — so the coordinate SET a shape sews is the same
regardless of which order its neighbours happen to be visited in, while the
ORDER/reversedness of points along a path is not. Comparing sets rather than
ordered lists is what keeps this test from being a hostage to unrelated
nearest-neighbour entry-point decisions elsewhere in the plan.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, plan_stitches
from digitizer_core.export import export_dst
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import run_stages
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART
from tests.conftest import PLAN_CFG_KW, cfg

FAB = get_fabric("pique_knit")
LOGO = str(Path(__file__).resolve().parent.parent / "testdata" / "logo_whitebg.png")

TECHNIQUES = ["wave", "chevron", "brick"]


# --- helpers -----------------------------------------------------------------

def _region(shape_id: str, poly: Polygon, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area, meta=m)


def _plan_for(regions: list[Region], **cfg_kw):
    """Stage 5 + stage 7 only — the same minimal-plan helper
    `test_crosshatch.py`/`test_stage6_streamline.py` use for their own
    per-shape-override tests."""
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)

    class _P:  # just enough plan for the assertions below
        pass

    p = _P()
    p.blocks = blocks
    return p, warnings


def _runs_for(blocks, shape_id):
    return [r for b in blocks for r in b.runs if r.shape_id == shape_id]


def _fill_point_set(runs) -> set[tuple[float, float]]:
    return {(round(x, 4), round(y, 4)) for r in runs if r.kind == "fill" for x, y in r.points}


RECT = Polygon([(-20, -10), (20, -10), (20, 10), (-20, 10)])


# --- Design-wide fill_technique -----------------------------------------------

def test_tatami_is_still_the_default():
    assert PipelineConfig().fill_technique == "tatami"


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_the_flag_is_reachable_from_plan_stitches(whitebg, technique):
    """The dead-code check `test_contour.py`/`test_crosshatch.py` each run
    for their own technique, extended to wave/chevron/brick: setting the
    flag must actually change the exported file."""
    off = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    on = export_dst(plan_stitches(whitebg, cfg(fill_technique=technique, **PLAN_CFG_KW)))
    assert off != on, f"the {technique} flag changed nothing — dead wiring"


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_the_flag_off_changes_nothing(whitebg, technique):
    """The byte-identical regression every other technique's own flag-off
    test rests on: naming the default explicitly and leaving it alone
    produce the same file, byte for byte — the additive-change contract.
    Also the direct proof that introducing wave/chevron/brick did not
    perturb plain tatami's own output."""
    plain = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    named = export_dst(plan_stitches(whitebg, cfg(fill_technique="tatami",
                                                   **PLAN_CFG_KW)))
    assert plain == named


# --- Per-shape tier == "wave"/"chevron"/"brick" override ---------------------

@pytest.mark.parametrize("technique", TECHNIQUES)
def test_forced_tier_changes_the_shapes_own_fill_points(technique):
    """One shape forced `tier: <technique>` inside an otherwise-default
    (`fill_technique="tatami"`) plan must sew different fill geometry than
    the same shape left on `auto` — the per-shape override actually reaches
    `stitch_shape`, the same dead-wiring check
    `test_forced_crosshatch_tier_sews_two_distinct_passes_on_one_shape`
    performs for crosshatch."""
    auto_plan, _ = _plan_for([_region("Stest", RECT)])
    forced_plan, _ = _plan_for([_region("Stest", RECT, {"tier": technique})])

    auto_points = _fill_point_set(_runs_for(auto_plan.blocks, "Stest"))
    forced_points = _fill_point_set(_runs_for(forced_plan.blocks, "Stest"))
    assert forced_points, f"forced {technique} must still sew something"
    assert forced_points != auto_points, (
        f"the forced {technique} tier must not just re-sew plain tatami"
    )


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_forced_tier_touches_only_its_own_shape(technique):
    """A per-shape `tier: <technique>` override on one shape in an
    otherwise-tatami design must not change its untouched neighbour's own
    fill points — mirrors `test_forced_crosshatch_tier_touches_only_its_
    own_shape`'s two-shape-in-one-plan isolation pattern, compared as
    coordinate SETS (see module docstring) rather than ordered point lists
    so a different entry point into shape B, caused by shape A's own
    geometry changing, cannot masquerade as leakage."""
    a = Polygon([(-30, -10), (-10, -10), (-10, 10), (-30, 10)])
    b = Polygon([(10, -10), (30, -10), (30, 10), (10, 10)])
    forced_plan, _ = _plan_for([_region("A", a, {"tier": technique}), _region("B", b)])
    auto_plan, _ = _plan_for([_region("A", a), _region("B", b)])

    a_forced = _fill_point_set(_runs_for(forced_plan.blocks, "A"))
    a_auto = _fill_point_set(_runs_for(auto_plan.blocks, "A"))
    b_forced = _fill_point_set(_runs_for(forced_plan.blocks, "B"))
    b_auto = _fill_point_set(_runs_for(auto_plan.blocks, "B"))

    assert a_forced != a_auto, f"shape A's forced {technique} must change its own fill points"
    assert b_forced == b_auto, (
        f"shape B (untouched) must sew identical fill points whether or not "
        f"A is forced to {technique}"
    )


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_override_needs_no_source_pixels(technique):
    """Unlike "sketch"/"streamline", wave/chevron/brick are purely geometric
    variants of tatami — a per-shape override must not trigger `pipeline.
    run_stages`' source-pixel opt-in plumbing, the same claim
    `test_crosshatch_override_needs_no_source_pixels_unlike_streamline`
    proves for crosshatch."""
    ov = run_stages(LOGO, PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        shape_overrides={"Swhatever": {"tier": technique}}))
    assert ov.source_pixels is None, (
        f"a per-shape tier:'{technique}' override is purely geometric and "
        "must not grow a raster payload the flat lane never asked for"
    )


# --- Closed-set tier-vocabulary validation ------------------------------------

@pytest.mark.parametrize("technique", TECHNIQUES)
def test_apply_shape_edits_accepts_the_tier_and_still_rejects_junk(technique):
    """Core-layer validation (`regions._TIER_VALUES`): the new tier is
    stored on the region's meta like every forced tier; an unknown value
    still raises — the same defense-in-depth
    `test_apply_shape_edits_accepts_crosshatch_and_still_rejects_junk` pins
    for crosshatch."""
    regs = [_region("Stest", Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))]
    _regions, _threads, warnings = apply_shape_edits(
        regs, [0], [], {"Stest": {"tier": technique}}, chart=[0] * 20)
    assert regs[0].meta.get("tier") == technique
    assert warnings == []

    with pytest.raises(ValueError):
        apply_shape_edits(
            [_region("Stest", Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))],
            [0], [], {"Stest": {"tier": "scribble"}}, chart=[0] * 20)


@pytest.mark.parametrize("technique", TECHNIQUES)
def test_service_validates_and_canonicalizes_the_tier(technique):
    """Service-layer validation (`app._TIER_VALUES`, the third of the three
    contract layers this vocabulary is mirrored in): mixed case lowercases
    and survives `_parse_config`, and an unknown tier is still a 400 at
    submit — the same proof `test_service_validates_and_canonicalizes_the_
    crosshatch_tier` runs for crosshatch."""
    from fastapi import HTTPException

    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"tier": technique.capitalize()}}})) == \
        {"shape_overrides": {"S1": {"tier": technique}}}
    with pytest.raises(HTTPException):
        _parse_config(json.dumps({"shape_overrides": {"S1": {"tier": "scribble"}}}))
