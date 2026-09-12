"""`cfg.layer_palette_from_regions` — the review screen's per-layer cone list,
elected from each layer's OWN regions. Defect 30. DEFAULT OFF.

`PipelineResult.palette[i]` is `thread_indices[i]`: what stage 2 CALLED layer
i. `compact_layers` only ever drops an empty slot, so a pass that moves a
region's thread without moving the region leaves the list naming a cone its
layer does not sew. `rehome_resnapped_regions` repairs exactly one such pass —
it keys on `meta["thread_resnapped_de00"]`, and `enforce_color_cap` both runs
AFTER it and stamps `color_cap_merged_from`.

Measured 2026-09-12 (`docs/palette-mismatch-2026-09-12.md`, re-measured after
the 2026-09-10 colour-bundle flip): **24 diverged regions on 3 of 26 fixtures**
at `max_colors=12` and **76 on two real-customer fixtures** at the Studio's
shipped 6, all 24 carrying `color_cap_merged_from` and not one a bare re-snap.
`PALETTE_THREAD_MISMATCH` also undercounts it — a layer naming a cone NO block
sews is invisible to that warning and sits on **9 of 26** fixtures, 6 of them
silent (`tools/palette_mismatch.py`'s phantom column reports that half).

**Harmless today, and only for one reason**: every customer-facing cone list
reads `stats.blocks` or `design.colors`, and `review.palette` has exactly two
readers, neither positional. `test_the_layer_palette_is_review_only` below
pins the other side of that — the flag cannot move a stitch, a block, or an
export.

**The invariant is `palette[i]["number"] in {r.thread_number for r in layer
i}` — never `palette ⊆ block cones`.** Two legitimate sources of a cone the
machine never loads: a layer whose every region is unstitched (the
enclosed-background default — `logo_whitebg`'s ring hole), and a blend/tonal
layer whose blocks are `shade_thread_index` shades of its base cone. Both are
real review rows and keep real colours; the fix makes the list TRUE about its
layers, it does not delete rows.
"""
from __future__ import annotations

from functools import lru_cache

import pytest
from shapely.geometry import Polygon

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize, run_stages
from digitizer_core.adapter import plan_to_design
from digitizer_core.regions import Region
from digitizer_core.stage3_segment import layer_palette_threads
from digitizer_core.stage4_vectorize import enforce_color_cap
from digitizer_core.threads import chart_for

from .conftest import TESTDATA, cfg

CHART = chart_for(PipelineConfig())

# The fixture the colour cap breaks: `COLOR_CAP_APPLIED` 13 -> 12 moves 7
# shapes out of layer 12, which goes on naming the cone they left (`0134`)
# while every one of them sews `4174`.
CAPPED = "photo/summit_badge.png"
# A flat control with no divergence at all — "review-only" has to be a claim
# about the shipped engine, not an artifact of testing one design.
FLAT = "logo_alpha.png"
# The blend tier's legitimate phantom: a tonal layer keeps its regions' base
# cone while the blocks it produces are `shade_thread_index` shades of it, so
# the cone it names is genuinely never loaded. `palette ⊆ block cones` is
# false here BY DESIGN, and must stay false after the fix.
BLEND = "photo/region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


@lru_cache(maxsize=None)
def _run(fixture: str, on: bool):
    """One pipeline run per (fixture, flag). Cached for the reason
    `test_resnap_mask_matches_grader` records: CI runners are 2-core and
    `summit_badge` costs ~54 s a digitize on this container."""
    result, plan = digitize(TESTDATA / fixture,
                            _cfg(layer_palette_from_regions=on))
    return result, plan


def _layer_cones(result) -> list[str]:
    return [str(c["number"]) for c in (result.palette or [])]


def _threads_by_layer(result) -> dict[int, set[str]]:
    by: dict[int, set[str]] = {}
    for r in result.regions:
        layer = r.meta.get("layer")
        if layer is not None:
            by.setdefault(int(layer), set()).add(str(r.thread_number))
    return by


def _violations(result) -> list[tuple[int, str, list[str]]]:
    """Layers whose palette entry names a cone no region in them carries."""
    cones, by = _layer_cones(result), _threads_by_layer(result)
    return [(i, c, sorted(by.get(i, ())))
            for i, c in enumerate(cones) if c not in by.get(i, ())]


# --- synthetic: the election itself -----------------------------------------

def _sq(size: float) -> Polygon:
    return Polygon([(0, 0), (size, 0), (size, size), (0, size)])


def _region(sid: str, thread: int, area: float, layer: int,
            stitched: bool = True) -> Region:
    return Region(shape_id=sid, polygon=_sq(max(area, 0.01) ** 0.5),
                  thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=area, meta={"layer": layer, "stitched": stitched})


def test_flag_defaults_on():
    """FLIPPED 2026-09-12 (Kent's ruling, on the corpus pass he asked for
    first). This asserted False until then.

    False is still the pre-flip engine byte for byte and stays reachable and
    tested rather than dead-by-default — `test_off_the_election_never_runs`
    proves the off path by call count, not by output comparison. What the
    pass bought: mislabelled layers 7 -> 0 at `max_colors=12` and 13 -> 0 at
    the Studio's shipped 6, with the plan digest identical off vs on across
    26/26 at both settings. What it cost, and Kent took it knowingly:
    duplicate review rows, because `merge_duplicate_cone_layers` folds on the
    DECLARED cone upstream of this election
    (`docs/palette-flip-corpus-2026-09-12.md`)."""
    assert PipelineConfig().layer_palette_from_regions is True


def test_a_capped_region_does_not_leave_its_layer_naming_a_dropped_cone():
    """The defect in one function, with no pipeline around it.

    Ten threads, one per layer, over a cap of six: `enforce_color_cap`
    remaps the four smallest onto kept cones and leaves `meta["layer"]`
    alone, which is precisely the mechanism. Stage 2's list is then wrong
    about four layers; the election is right about all ten.
    """
    regions = [_region(f"S{i}", i, 100.0 * (10 - i), layer=i)
               for i in range(10)]
    stage2 = list(range(10))

    assert enforce_color_cap(regions, CHART, 6)[0]["code"] == "COLOR_CAP_APPLIED"
    by_layer = {r.meta["layer"]: r.thread_index for r in regions}

    # The OFF answer, stated as a failure rather than assumed: if stage 2's
    # list still satisfied the invariant there would be nothing to fix here
    # and every assertion below would be vacuous.
    assert [i for i in range(10) if stage2[i] != by_layer[i]] == [6, 7, 8, 9]

    elected = layer_palette_threads(regions, stage2, {})
    assert elected == [by_layer[i] for i in range(10)]
    assert all(CHART[elected[i]].number == regions[i].thread_number
               for i in range(10))


def test_the_largest_stitched_region_wins_over_a_bigger_unstitched_one():
    """Tie-break `(stitched, area_mm2, -thread_index)`. Sewing beats area:
    a layer's cone should be the one a customer actually buys thread for."""
    regions = [
        _region("Sbig", 3, 500.0, layer=0, stitched=False),
        _region("Ssewn", 7, 10.0, layer=0, stitched=True),
    ]
    assert layer_palette_threads(regions, [99], {}) == [7]


def test_a_layer_that_sews_nothing_falls_back_to_its_largest_region():
    regions = [
        _region("Ssmall", 3, 10.0, layer=0, stitched=False),
        _region("Sbig", 7, 500.0, layer=0, stitched=False),
    ]
    assert layer_palette_threads(regions, [99], {}) == [7]


def test_equal_areas_break_on_the_lowest_chart_index():
    """Earliest-wins, the convention `rehome_resnapped_regions` and
    `merge_duplicate_cone_layers` both use — so the answer never depends on
    region order."""
    a = [_region("Sa", 12, 100.0, layer=0), _region("Sb", 4, 100.0, layer=0)]
    assert layer_palette_threads(a, [99], {}) == [4]
    assert layer_palette_threads(list(reversed(a)), [99], {}) == [4]


def test_a_layer_with_no_eligible_region_keeps_stage_2s_answer():
    """Today's answer, deliberately — an empty layer has nothing to elect
    from, so nothing regresses. (`compact_layers` normally removes these;
    the guard exists so the election cannot invent a cone.)"""
    regions = [_region("S0", 5, 100.0, layer=0)]
    assert layer_palette_threads(regions, [5, 11, 12], {}) == [5, 11, 12]


def test_a_user_layer_override_cannot_rename_the_layer_it_joins():
    """A shape the user moved is not evidence about its new layer's colour.

    The same exemption `PALETTE_THREAD_MISMATCH` already makes, for the same
    reason: `apply_layer_overrides` moves sew POSITION, never the cone, so
    reporting — or here, obeying — the move would read the user's own
    instruction back to them as a fact about the design.
    """
    regions = [
        _region("Snative", 4, 50.0, layer=0),
        _region("Smoved", 9, 5000.0, layer=0),     # huge, and ineligible
    ]
    overrides = {"Smoved": {"layer": 0}}
    assert layer_palette_threads(regions, [4], overrides) == [4]
    # Without the override it would win on area — so the exemption is what
    # this test is measuring, not an accident of the tie-break.
    assert layer_palette_threads(regions, [4], {}) == [9]


def test_a_shape_parked_past_the_end_of_the_list_elects_nothing():
    """`apply_layer_overrides` can set any int, including one past the last
    palette row; `PALETTE_THREAD_MISMATCH` guards the same way."""
    regions = [_region("S0", 5, 100.0, layer=0),
               _region("Sfar", 9, 900.0, layer=7)]
    assert layer_palette_threads(regions, [5], {}) == [5]


# --- the off path, proved by EXECUTION --------------------------------------

def test_off_the_election_never_runs(monkeypatch):
    """The off-path claim as an execution fact, not an output comparison.

    Two runs that happen to agree are weak evidence — a fixture can simply
    have no layer the election would move (`logo_whitebg` is exactly that,
    §3 of the doc). Zero calls is proof, on any fixture, that OFF runs the
    pre-flag instruction stream.

    Patched on `pipeline`'s own module attribute, so this scopes to the one
    call site and cannot be satisfied by some other importer.
    """
    import digitizer_core.pipeline as P

    real = P.layer_palette_threads
    seen = {}
    for on in (False, True):
        calls = []

        def shim(*a, _c=calls, **kw):
            _c.append(1)
            return real(*a, **kw)

        monkeypatch.setattr(P, "layer_palette_threads", shim)
        run_stages(TESTDATA / "logo_whitebg.png",
                   cfg(layer_palette_from_regions=on))
        monkeypatch.undo()
        seen[on] = len(calls)

    assert seen[False] == 0, (
        f"the election ran {seen[False]}x with the flag OFF — the guard "
        "leaks, so 'off is the pre-flag engine' is no longer true")
    assert seen[True] == 1, (
        f"the flag is ON and the election ran {seen[True]}x, so this test is "
        "not watching the guarded call site (or it moved)")


# --- real fixtures ----------------------------------------------------------

def test_the_election_closes_the_divergence_on_the_fixture_that_fires_it():
    """`summit_badge`: the cap moves 7 shapes out of layer 12 and the list
    goes on naming the cone they left. Read the CONE LIST, not a grade."""
    off, _ = _run(CAPPED, False)
    on, _ = _run(CAPPED, True)

    bad_off = _violations(off)
    assert bad_off, (
        "premise gone: `summit_badge` no longer diverges, so this file is "
        "measuring nothing — re-read docs/palette-mismatch-2026-09-12.md §1")
    assert [i for i, _c, _t in bad_off] == [12]
    assert bad_off[0][1] == "0134" and bad_off[0][2] == ["4174"]

    assert _violations(on) == []
    assert _layer_cones(on)[12] == "4174"
    # One entry per layer, still — the election renames rows, never drops one.
    assert len(on.palette) == len(off.palette)


def test_the_invariant_holds_on_every_layer_of_both_fixtures():
    """`palette[i]["number"] in {r.thread_number for r in layer i}`, which is
    the whole contract. Stated over all layers so a future pass that moves a
    thread without its region is caught here rather than on the corpus."""
    for fixture in (CAPPED, FLAT):
        result, _ = _run(fixture, True)
        assert _violations(result) == [], fixture


def test_a_layer_that_sews_nothing_names_its_own_shapes_cone():
    """`logo_whitebg`'s enclosed ring hole: layer 4 lists `0015 White`, 159.6
    mm², `stitched=False`, and the machine loads five spools not six.

    The fix does NOT delete it, and that is the point of this test. An
    unstitched layer is a real review row and must keep a real colour — the
    phantom here is the list telling the TRUTH about a layer that sews
    nothing. So `0015` is in the review list and in no block, both ways, and
    `palette ⊆ block cones` is NOT the invariant.
    """
    # `cfg()` is `PipelineConfig(target_width_mm=80.0)`, the config §3 of the
    # doc walked through, so these are the numbers it published.
    off, off_plan = digitize(TESTDATA / "logo_whitebg.png", cfg())
    on, on_plan = digitize(TESTDATA / "logo_whitebg.png",
                           cfg(layer_palette_from_regions=True))

    assert _layer_cones(off) == _layer_cones(on), (
        "an unstitched layer's cone was already its own regions' cone; the "
        "election must be a no-op here")
    assert _layer_cones(on)[4] == "0015"
    hole = [r for r in on.regions if r.meta["layer"] == 4]
    assert hole and all(r.meta["stitched"] is False for r in hole)
    assert _violations(on) == []

    # Six review rows, five spools — the gap is the ring hole, both ways.
    spools = {str(b.thread_number) for b in on_plan.blocks}
    assert spools == {str(b.thread_number) for b in off_plan.blocks}
    assert len(_layer_cones(on)) == 6 and len(spools) == 5
    assert set(_layer_cones(on)) - spools == {"0015"}


def test_a_blend_layers_unsewn_base_cone_survives_the_election():
    """The other legitimate phantom, and the reason the invariant is about
    the layer's own REGIONS and never about the block list.

    `region_blobs` sews 15 distinct block cones; its four review layers name
    `3770 2153 3630 5422`, of which `2153` and `3630` are on no block at all
    because the blocks under them are `shade_thread_index` shades. That is
    the contract `StitchPlan.palette` and `_stats_payload` both describe. A
    fix that chased `palette ⊆ block cones` would delete or rewrite those
    two rows; this one must leave them exactly as they are.
    """
    off, plan = _run(BLEND, False)
    on, _ = _run(BLEND, True)

    block_cones = {str(c["number"]) for c in plan.palette}
    unsewn = [c for c in _layer_cones(off) if c not in block_cones]
    assert unsewn, (
        "premise gone: `region_blobs` no longer names a cone its blocks do "
        "not sew, so this test is not covering the blend tier any more")

    assert _layer_cones(on) == _layer_cones(off)
    assert [c for c in _layer_cones(on) if c not in block_cones] == unsewn
    assert _violations(on) == []


@pytest.mark.parametrize("fixture", [CAPPED, FLAT])
def test_the_layer_palette_is_review_only(fixture):
    """Blast radius, checked rather than asserted.

    `result.palette` feeds exactly one consumer — `_review_payload["palette"]`
    (`digitizer_service/app.py:587`). Everything a customer is charged for or
    a machine sews comes off `plan.blocks`. So the operator list, every
    stitch coordinate and the download adapter's own thread list must be
    identical with the flag OFF and ON, on a fixture the flag DOES change
    (`summit_badge`) as well as one it does not.
    """
    off_r, off_p = _run(fixture, False)
    on_r, on_p = _run(fixture, True)

    def coords(plan):
        return tuple((round(x, 4), round(y, 4), run.kind, run.jump, run.trim)
                     for _b, run in plan.iter_runs() for x, y in run.points)

    def blocks(plan):
        return tuple((b.thread_index, b.thread_number, b.rgb, b.step,
                      b.stitch_count, round(b.length_mm, 4))
                     for b in plan.blocks)

    assert off_p.palette == on_p.palette            # the OPERATOR's list
    assert blocks(off_p) == blocks(on_p)
    assert coords(off_p) == coords(on_p)            # every stitch
    assert plan_to_design(off_p)["colors"] == plan_to_design(on_p)["colors"]
    assert off_p.stats.thread_mm_by_color == on_p.stats.thread_mm_by_color
    # ...and the per-shape review fields, which is what `.embproj` persists.
    assert ([(r.shape_id, r.thread_number, r.meta["layer"]) for r in off_r.regions]
            == [(r.shape_id, r.thread_number, r.meta["layer"]) for r in on_r.regions])
