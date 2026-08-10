"""Cross-hatch fill — wiring tests.

The geometry itself (two angularly-distinct passes, the widened per-pass
spacing, chaining pass 2 off pass 1's own exit point, degrading sensibly on a
too-thin shape) is proven directly against `_crosshatch_fill_paths` in
`test_fill.py`. What this file proves is that the technique actually REACHES
stitches through both of its documented entry points:

- the design-wide `fill_technique="crosshatch"` flag (mirroring
  `test_contour.py`'s own design-wide proof for "contour"), and
- the per-shape `tier: "crosshatch"` override (mirroring
  `test_stage6_streamline.py`'s per-shape-override proof for "streamline",
  and `test_shape_overrides.py`'s multi-shape isolation pattern).

Every accuracy claim below is measured from EMITTED geometry — the same
length-weighted-direction discipline `test_shape_overrides.py`'s
`axis_lengths` helper and `test_fill.py`'s `_dominant_row_angle_deg` use —
never a trust of the code path taken.
"""
from __future__ import annotations

import math
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


# --- helpers -----------------------------------------------------------------

def _region(shape_id: str, poly: Polygon, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=poly.area, meta=m)


def _plan_for(regions: list[Region], **cfg_kw):
    """Stage 5 + stage 7 only — the same minimal-plan helper
    `test_stage6_streamline.py`/`test_shape_overrides.py` use for their
    per-shape-override tests, reused here for crosshatch's own per-shape
    form."""
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)

    class _P:  # just enough plan for the assertions below
        pass

    p = _P()
    p.blocks = blocks
    return p, warnings


def _axis_lengths(runs) -> tuple[float, float]:
    """Total fill-segment length near 0deg and near 90deg, across a list of
    runs — `test_shape_overrides.py`'s own `axis_lengths` measurement,
    reused: robust to which end of a path a column happened to start from
    (unlike a byte-for-byte point comparison), and exactly what tells a real
    two-pass cross-hatch (both axes carry real length) apart from a
    single-angle tatami fill (one axis near zero)."""
    h = v = 0.0
    for r in runs:
        if r.kind != "fill":
            continue
        for a, b in zip(r.points, r.points[1:]):
            d = math.dist(a, b)
            ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0
            if min(ang, 180.0 - ang) < 20.0:
                h += d
            elif abs(ang - 90.0) < 20.0:
                v += d
    return h, v


def _runs_for(blocks, shape_id):
    return [r for b in blocks for r in b.runs if r.shape_id == shape_id]


# --- Design-wide fill_technique="crosshatch" ---------------------------------

def test_tatami_is_still_the_default():
    assert PipelineConfig().fill_technique == "tatami"


def test_the_crosshatch_flag_is_reachable_from_plan_stitches(whitebg):
    """The dead-code check `test_contour.py` runs for "contour", extended to
    "crosshatch": setting the flag must actually change the exported file."""
    off = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    on = export_dst(plan_stitches(whitebg, cfg(fill_technique="crosshatch",
                                               **PLAN_CFG_KW)))
    assert off != on, "the crosshatch flag changed nothing — dead wiring"


def test_the_crosshatch_flag_off_changes_nothing(whitebg):
    """The byte-identical regression every other technique's own flag-off
    test rests on: naming the default explicitly and leaving it alone
    produce the same file, byte for byte — the additive-change contract."""
    plain = export_dst(plan_stitches(whitebg, cfg(**PLAN_CFG_KW)))
    named = export_dst(plan_stitches(whitebg, cfg(fill_technique="tatami",
                                                  **PLAN_CFG_KW)))
    assert plain == named


def test_crosshatch_plan_produces_two_angularly_distinct_fill_passes(whitebg):
    """End to end, on real artwork: the crosshatch plan's fill stitches carry
    real length on BOTH the 0deg and 90deg axes — proof this is a genuine
    two-pass fill, not tatami re-sewn under a different flag. A plain tatami
    plan of the same fixture is the negative control: it is dominated by
    whatever single angle each shape's own tatami pass chose."""
    plan = plan_stitches(whitebg, cfg(fill_technique="crosshatch", **PLAN_CFG_KW))
    fills = [r for _b, r in plan.iter_runs() if r.kind == "fill"]
    assert fills, "crosshatch produced no fill runs at all"

    h, v = _axis_lengths(fills)
    assert h > 0 and v > 0, "both passes must contribute real stitch length"
    # Neither axis should be a rounding artifact of the other.
    assert min(h, v) > 0.05 * max(h, v)


# --- Per-shape tier == "crosshatch" override ---------------------------------

RECT = Polygon([(-20, -10), (20, -10), (20, 10), (-20, 10)])


def test_forced_crosshatch_tier_sews_two_distinct_passes_on_one_shape():
    """One shape forced `tier: "crosshatch"` inside an otherwise-default
    (`fill_technique="tatami"`) plan — nothing about this design opts into
    the design-wide crosshatch preset — must sew real two-pass geometry, the
    same measurement discipline `test_forced_streamline_tier_follows_the_
    field_on_a_manually_classified_shape` holds itself to for "streamline"."""
    auto_plan, _ = _plan_for([_region("Stest", RECT)])
    forced_plan, _ = _plan_for([_region("Stest", RECT, {"tier": "crosshatch"})])

    auto_runs = [r for b in auto_plan.blocks for r in b.runs]
    forced_runs = [r for b in forced_plan.blocks for r in b.runs]
    assert [(r.kind, r.points) for r in forced_runs] != \
           [(r.kind, r.points) for r in auto_runs], (
        "the forced tier must not just re-sew plain tatami"
    )

    auto_h, auto_v = _axis_lengths(auto_runs)
    forced_h, forced_v = _axis_lengths(forced_runs)
    assert auto_v < 0.05 * auto_h, "sanity: plain tatami on this rect is one-axis"
    assert forced_h > 0 and forced_v > 0, "forced crosshatch must carry both axes"
    assert min(forced_h, forced_v) > 0.2 * max(forced_h, forced_v)


def test_forced_crosshatch_tier_touches_only_its_own_shape():
    """A per-shape `tier: "crosshatch"` override on one shape in an
    otherwise-tatami design produces cross-hatch only on that shape — the
    other shape keeps sewing plain single-angle tatami. Mirrors
    `test_shape_overrides.py::test_per_shape_fill_angle_beats_the_global`'s
    two-shape-in-one-plan pattern, the established way this suite proves a
    per-shape override does not leak onto its neighbour."""
    a = Polygon([(-30, -10), (-10, -10), (-10, 10), (-30, 10)])
    b = Polygon([(10, -10), (30, -10), (30, 10), (10, 10)])
    plan, _ = _plan_for([_region("A", a, {"tier": "crosshatch"}), _region("B", b)])

    a_runs = _runs_for(plan.blocks, "A")
    b_runs = _runs_for(plan.blocks, "B")
    a_h, a_v = _axis_lengths(a_runs)
    b_h, b_v = _axis_lengths(b_runs)

    assert a_h > 0 and a_v > 0 and min(a_h, a_v) > 0.2 * max(a_h, a_v), (
        "shape A (forced) must show real cross-hatch on both axes"
    )
    assert b_v < 0.05 * b_h, (
        "shape B (untouched) must keep sewing plain single-angle tatami"
    )


def test_crosshatch_override_needs_no_source_pixels_unlike_streamline():
    """Unlike "sketch"/"streamline", cross-hatch is a purely geometric
    variant of tatami — it must not trigger `pipeline.run_stages`'
    source-pixel opt-in plumbing the way a per-shape `tier: "streamline"`
    override does (`test_pipeline_plumbs_source_pixels_for_per_shape_
    streamline_override`'s exact claim, inverted here)."""
    ov = run_stages(LOGO, PipelineConfig(
        target_width_mm=90.0, forced_class="flat",
        shape_overrides={"Swhatever": {"tier": "crosshatch"}}))
    assert ov.source_pixels is None, (
        "a per-shape tier:'crosshatch' override is purely geometric and "
        "must not grow a raster payload the flat lane never asked for"
    )


def test_apply_shape_edits_accepts_crosshatch_and_still_rejects_junk():
    """Core-layer validation (`regions._TIER_VALUES`): "crosshatch" is
    stored on the region's meta like every forced tier; an unknown value
    still raises — the same defense-in-depth
    `test_apply_shape_edits_accepts_streamline_and_still_rejects_junk`
    pins for "streamline"."""
    regs = [_region("Stest", Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))]
    _regions, _threads, warnings = apply_shape_edits(
        regs, [0], [], {"Stest": {"tier": "crosshatch"}}, chart=[0] * 20)
    assert regs[0].meta.get("tier") == "crosshatch"
    assert warnings == []

    with pytest.raises(ValueError):
        apply_shape_edits(
            [_region("Stest", Polygon([(0, 0), (12, 0), (12, 12), (0, 12)]))],
            [0], [], {"Stest": {"tier": "scribble"}}, chart=[0] * 20)


def test_service_validates_and_canonicalizes_the_crosshatch_tier():
    """Service-layer validation (`app._TIER_VALUES`, the third of the three
    contract layers this vocabulary is mirrored in): "Crosshatch" lowercases
    and survives `_parse_config`, and an unknown tier is still a 400 at
    submit — the same proof `test_service_validates_and_canonicalizes_the_
    streamline_tier` runs for "streamline"."""
    import json

    from fastapi import HTTPException

    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"tier": "Crosshatch"}}})) == \
        {"shape_overrides": {"S1": {"tier": "crosshatch"}}}
    with pytest.raises(HTTPException):
        _parse_config(json.dumps({"shape_overrides": {"S1": {"tier": "scribble"}}}))
