"""The satin PREDICTION and the satin VERDICT must ask one question.

`stage7_sequence._sews_satin` is the prediction. Three passes read it and
commit before a stitch exists: `borders_last_layers` moves satin-dominated
layers after fill-dominated ones, the within-group picking loop sews detail
satin last inside its own cone, and the seam-ownership pass decides which of
two abutting shapes yields its seam to the other. `stitch_one` is the
emitter — the ladder that actually routes a shape to `satin_shape`.

Until 2026-09-20 the two asked the classifier DIFFERENT questions. The
emitter called `classify_ribbon(..., polygon_axis=cfg.satin_polygon_axis,
area_weighted=cfg.classify_area_weighted)`; the prediction called
`is_satin_candidate(...)` and passed neither (`is_satin_candidate` has no
`polygon_axis` parameter at all). Both flags default OFF, so the gap was
latent rather than live — and both sit on the pending-flags list Kent has
not ruled on (`docs/kent-review-2026-09-18.md`), so either flip is the
moment it goes live: a layer moved late, a detail picked last, or a seam
yielded, on a shape that then sews fill.

The behavioural tests below turn each flag ON and compare the prediction
against the SEWN result (`run.kind == stitches.SATIN` out of `sequence`),
not against a re-derivation of the classifier call — a re-derivation would
only re-encode the same mistake. The `ast` test that follows them is the
part that closes the gap for a flag that does not exist yet: it reads the
keyword names off both call sites and requires the sets to match.

Scope, stated rather than implied. This pins the classifier CALL, not every
route into the satin tier: `_sews_satin` runs before stage 5 exists, so
widened lettering (classified on the column stage 5 grows) is outside it, as
are the two escapes `_sews_satin`'s own docstring already names — the
small-shape rescue and the photo-lane width floor. The fixture is flat and
well above `min_detail_mm`, so neither escape fires here.
"""
from __future__ import annotations

import ast
import inspect

import pytest
from shapely.geometry import Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, get_fabric, stitches
from digitizer_core.machine import satin_ceiling_mm
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import _sews_satin, sequence
from digitizer_core.threads import CHART

FAB = get_fabric("pique_knit")


# --- the fixture -------------------------------------------------------------
#
# Four shapes, placed apart so stage 5 has no overlap to resolve. Two are
# flag-independent controls; two were found by sweeping the classifier for a
# verdict the flag MOVES, because a fixture neither flag can move would let
# this whole file pass vacuously.

# A plain 30 x 2 mm band: satin under every combination.
RIBBON = box(0, 0, 30, 2)
# A 30 x 30 mm field: fill under every combination.
FIELD = box(0, 60, 30, 90)
# A wide body with a long thin tail. The tail outvotes the body by skeleton
# pixel COUNT, so the unweighted regularity gate reads `dt_irregular`;
# weighted by the area each pixel stands for, the body counts for what it is
# and the shape earns `satin` (p90 3.67 mm, inside the 5 mm cap).
TAIL = unary_union([box(0, 20, 8, 23.5), box(8, 21.25, 28, 22.25)])
# A 10 x 2.6 mm bar through a disc — a junction knot. Pooled over the whole
# region the radii are irregular; partitioned per stroke behind
# `satin_per_stroke`, the answer depends on WHICH skeleton the strokes are
# read off, which is what `satin_polygon_axis` changes (`stroke_ribbon`).
KNOT = unary_union([box(40, 3.7, 50, 6.3), Point(45, 5).buffer(3.64)])

SHAPES = {"RIBBON": RIBBON, "FIELD": FIELD, "TAIL": TAIL, "KNOT": KNOT}

# Each flag ON, and both together. `satin_polygon_axis` rides with
# `satin_per_stroke` on purpose and not as a convenience: the axis reaches
# the verdict only through `classify_ribbon`'s `dt_irregular` branch, which
# consults `_stroke_rung_takes` only behind the per-stroke flag. On its own
# the axis flag changes the SEWN column (`satin_shape`) but not the tier, so
# a lone-axis case could not fail this test in either direction.
FLAG_SETS = {
    "area_weighted": dict(classify_area_weighted=True),
    "polygon_axis": dict(satin_polygon_axis=True, satin_per_stroke=True),
    "both": dict(classify_area_weighted=True, satin_polygon_axis=True,
                 satin_per_stroke=True),
    "neither": dict(),
}


def _regions() -> list[Region]:
    out = []
    for i, (sid, poly) in enumerate(SHAPES.items()):
        out.append(Region(shape_id=sid, polygon=poly, thread_index=3 + i,
                          thread_number=CHART[3 + i].number,
                          area_mm2=poly.area, meta={"layer": i}))
    return out


def _cfg(**flags) -> PipelineConfig:
    # `edge_cap="none"`: the design-silhouette cap (ON by default since
    # 2026-09-11) adds a block with no region behind it, so it has no
    # prediction to compare against and is not what this file is about.
    return PipelineConfig(edge_cap="none", **flags)


def _predicted(cfg: PipelineConfig) -> dict[str, bool]:
    satin_max = satin_ceiling_mm(cfg)
    return {r.shape_id: bool(_sews_satin(r, cfg, satin_max, "flat"))
            for r in _regions()}


def _emitted(cfg: PipelineConfig) -> dict[str, bool]:
    """Which shapes actually put a satin cross down, from the sewn runs."""
    planned, _w = resolve_overlaps(_regions(), FAB, cfg)
    blocks, _warn = sequence(planned, FAB, cfg, design_class="flat")
    out = {sid: False for sid in SHAPES}
    for b in blocks:
        for run in b.runs:
            if run.shape_id in out and run.kind == stitches.SATIN:
                out[run.shape_id] = True
    return out


# --- the fixture is not vacuous ---------------------------------------------

def test_the_fixture_holds_both_tiers_under_every_flag_set():
    for name, flags in FLAG_SETS.items():
        emitted = _emitted(_cfg(**flags))
        assert any(emitted.values()), f"{name}: no shape sews satin"
        assert not all(emitted.values()), f"{name}: no shape sews fill"


def test_each_flag_moves_a_shape_it_is_supposed_to_move():
    """Without this, the agreement tests below could pass on a fixture
    neither flag can reach — which is how a latent gap stays latent."""
    base = _emitted(_cfg())
    aw = _emitted(_cfg(**FLAG_SETS["area_weighted"]))
    pa = _emitted(_cfg(**FLAG_SETS["polygon_axis"]))
    assert aw["TAIL"] and not base["TAIL"], \
        f"TAIL must flip on classify_area_weighted: {base['TAIL']} -> {aw['TAIL']}"
    assert pa["KNOT"] and not base["KNOT"], \
        f"KNOT must flip on satin_polygon_axis: {base['KNOT']} -> {pa['KNOT']}"


# --- the agreement itself ----------------------------------------------------

@pytest.mark.parametrize("flagset", sorted(FLAG_SETS))
def test_prediction_matches_the_emitted_tier(flagset):
    cfg = _cfg(**FLAG_SETS[flagset])
    predicted, emitted = _predicted(cfg), _emitted(cfg)
    disagree = {sid: (predicted[sid], emitted[sid])
                for sid in SHAPES if predicted[sid] != emitted[sid]}
    assert disagree == {}, (
        f"{flagset}: the borders-last/seam-ownership prediction and the sewn "
        f"tier disagree (predicted, emitted): {disagree}")


# --- the guard for a flag that does not exist yet ----------------------------

def _classifier_kwargs(fn_name: str) -> set[str]:
    """The keyword names the `classify_ribbon` call inside `fn_name` passes."""
    from digitizer_core import stage7_sequence as s7

    tree = ast.parse(inspect.getsource(s7))
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            calls = [c for c in ast.walk(node)
                     if isinstance(c, ast.Call)
                     and getattr(c.func, "id", None) == "classify_ribbon"]
            assert len(calls) == 1, \
                f"{fn_name} makes {len(calls)} classify_ribbon calls, expected 1"
            return {k.arg for k in calls[0].keywords}
    raise AssertionError(f"{fn_name} not found in stage7_sequence")


def test_the_prediction_and_the_emitter_pass_the_same_classifier_kwargs():
    """A behavioural test can only catch the flags that exist today. This one
    catches the next one: add a `cfg` flag to `stitch_one`'s classifier call
    and forget `_sews_satin`, and the sets stop matching."""
    prediction = _classifier_kwargs("_sews_satin")
    emitter = _classifier_kwargs("stitch_one")
    assert prediction == emitter, (
        f"the prediction and the emitter ask the classifier different "
        f"questions: prediction-only {sorted(prediction - emitter)}, "
        f"emitter-only {sorted(emitter - prediction)}")
