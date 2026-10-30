"""`cfg.color_cap_sewn` (built OFF 2026-10-29): "Colors (max N)" holds on the
SEWN design, not only on stage 4's regions.

The photo-style census (2026-10-27, item 3) found sewn designs loading 13 / 8
/ 8 / 7 cones against the 6 the cap's own warning promised. Two mechanisms,
both AFTER `enforce_color_cap` has run (`docs/superpowers/specs/2026-10-29-
colour-cap-sewn-design.md`):

1. "Sew white areas" (`apply_enclosed_white`, `finish_generation`) recolours
   the fields it sews to a thread the cap never ranked — both leaks on main
   (`isometric_icon`, `watercolor`: six artwork cones + White 0015).
2. The gradient lane's blend tier snaps every shade band to the whole chart
   (`stage6_blend.blend_fill`, `design_shade_scheme`); the photo lane's shade
   bind is gated on `is_photographic` and never reaches a gradient design
   (`flower_macro` forced gradient: 13 cones, 7 of them bands of 9–57 mm).

What this file pins, load-bearing first:

1. **Flag off is byte-identical.** The config default; `enforce_color_cap`
   with the new keywords at their defaults is the old function; stage 7 hands
   the fold never runs; the whole
   pipeline on a fixture that leaks (`logo_whitebg` at a cap of 2 with the
   Studio's white tick) still leaks exactly as before, on the frozen engine.
2. **The second pass**: protected threads keep their slot and count against
   the budget; `stitched_only` ranks by the resolved verdict; protected alone
   at the budget keep only themselves.
3. **The plan-level fold** (`stage7_sequence.fold_stray_cones`): at or under
   the budget nothing moves (a one-region ramp keeps its five shades); over
   it, the regions' cones keep their slots, the longest strays fill the free
   ones and the rest are recoloured in place to their nearest kept cone.
4. **End to end**: the leaking fixture sews exactly its cap with the flag on,
   White (the customer's stated colour) among the cones kept, and the
   `COLOR_CAP_APPLIED` sentence appears once.

Spool choices come from the live chart by criteria, never hardcoded.
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import stage7_sequence as S7
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import enforce_color_cap
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage7_sequence import fold_stray_cones
from digitizer_core.stitches import FILL, StitchBlock, StitchRun
from digitizer_core.threads import chart_for
from digitizer_core.warnings_codes import COLOR_CAP_APPLIED
from tests.conftest import TESTDATA, frozen_cfg, own_thread_only

CHART = chart_for(PipelineConfig())
FAB = get_fabric("pique_knit")
WHITE_T = CHART.nearest_index(np.array([100.0, 0.0, 0.0]))
NATURAL = (235, 232, 223)


def _sq(size: float) -> Polygon:
    return Polygon([(0, 0), (size, 0), (size, size), (0, size)])


def _region(sid: str, thread: int, area: float, **meta) -> Region:
    return Region(shape_id=sid, polygon=_sq(max(area, 0.01) ** 0.5),
                  thread_index=thread, thread_number=CHART[thread].number,
                  area_mm2=area, meta=meta)


# --- 1. Flag off is byte-identical ------------------------------------------------

def test_flag_defaults_off():
    assert PipelineConfig().color_cap_sewn is False
    assert frozen_cfg().color_cap_sewn is False


def test_keywords_at_their_defaults_are_the_stage4_cap():
    """`protected=()` and `stitched_only=False` reproduce the old ranking and
    remap exactly: an enclosed region buys no slot, the biggest areas keep
    their cones, the dropped one lands on its nearest kept."""
    def design():
        return [_region("a", 10, 100.0), _region("b", 20, 50.0),
                _region("c", 30, 1.0), _region("d", 40, 500.0, enclosed_background=True)]
    old = design()
    enforce_color_cap(old, CHART, 2)
    new = design()
    enforce_color_cap(new, CHART, 2, protected=(), stitched_only=False)
    assert [r.thread_index for r in old] == [r.thread_index for r in new]
    assert {r.thread_index for r in old if not r.meta.get("enclosed_background")} == {10, 20}


def test_sequence_hands_the_blend_tier_no_palette_with_the_flag_off(monkeypatch):
    seen: list[object] = []
    real = S7.blend_fill

    def spy(region, source_pixels, cfg, *a, **kw):
        seen.append(kw.get("palette_indices", "MISSING"))
        return real(region, source_pixels, cfg, *a, **kw)

    monkeypatch.setattr(S7, "blend_fill", own_thread_only(spy, real))
    _sequence_gradient(PipelineConfig(color_cap_sewn=False))
    assert seen == ["MISSING"], seen


# --- 2. The second pass -------------------------------------------------------------

def test_protected_threads_keep_their_slot_and_count_against_the_budget():
    """White on a 10 mm2 field is the smallest cone by area; protected, it
    stays, and the artwork gets the ONE slot left: the 100 mm2 cone. The 50
    and 1 mm2 cones fold onto their nearest kept thread."""
    regions = [_region("a", 10, 100.0, stitched=True), _region("b", 20, 50.0, stitched=True),
               _region("c", 30, 1.0, stitched=True), _region("w", WHITE_T, 10.0, stitched=True)]
    warnings = enforce_color_cap(regions, CHART, 2, protected={WHITE_T}, stitched_only=True)
    kept = {r.thread_index for r in regions}
    assert kept == {10, WHITE_T}
    assert warnings and warnings[0]["code"] == COLOR_CAP_APPLIED
    assert warnings[0]["after"] == 2 and warnings[0]["dropped"] == 2


def test_stitched_only_ranks_by_the_resolved_verdict_not_the_enclosed_tag():
    """An enclosed field the garment rule or the white tick made `stitched`
    buys its slot; an unstitched artwork region buys none (and is remapped
    so nothing names a dropped cone)."""
    regions = [_region("a", 10, 100.0, stitched=True),
               _region("hole", 20, 60.0, stitched=True, enclosed_background=True),
               _region("off", 30, 500.0, stitched=False)]
    enforce_color_cap(regions, CHART, 2, stitched_only=True)
    assert {r.thread_index for r in regions if r.meta["stitched"]} == {10, 20}
    assert regions[2].thread_index in {10, 20}


def test_protected_alone_at_the_budget_keep_only_themselves():
    regions = [_region("a", 10, 100.0, stitched=True), _region("b", 20, 50.0, stitched=True),
               _region("p", 30, 1.0, stitched=True), _region("q", 40, 1.0, stitched=True)]
    enforce_color_cap(regions, CHART, 2, protected={30, 40}, stitched_only=True)
    assert {r.thread_index for r in regions} == {30, 40}


def test_a_protected_thread_nothing_wears_is_ignored():
    regions = [_region("a", 10, 100.0, stitched=True), _region("b", 20, 50.0, stitched=True),
               _region("c", 30, 1.0, stitched=True)]
    enforce_color_cap(regions, CHART, 2, protected={999}, stitched_only=True)
    assert {r.thread_index for r in regions} == {10, 20}


# --- 3. The plan-level fold ---------------------------------------------------------

def _block(thread: int, length_mm: float, n_runs: int = 1) -> StitchBlock:
    runs = [StitchRun(points=[(0.0, float(i)), (length_mm / n_runs, float(i))], kind=FILL)
            for i in range(n_runs)]
    return StitchBlock(thread_index=thread, thread_number=CHART[thread].number,
                       rgb=tuple(CHART[thread].rgb), runs=runs)


def test_fold_is_a_no_op_at_or_under_the_budget():
    blocks = [_block(5, 100.0), _block(280, 10.0), _block(283, 5.0)]
    out, w = fold_stray_cones(blocks, {5}, 3, CHART)
    assert out is blocks and w is None
    out, w = fold_stray_cones(blocks, {5}, 6, CHART)
    assert out is blocks and w is None


def test_fold_spends_the_free_slots_on_the_longest_strays_then_folds_the_rest():
    """One admitted cone, four strays, a cap of 3: the two strays with the
    most thread keep their slots, the two slivers land on their nearest kept
    cone -- in place, same runs, same order."""
    blocks = [_block(5, 100.0), _block(280, 40.0), _block(283, 2.0),
              _block(290, 60.0), _block(311, 1.0)]
    out, w = fold_stray_cones(blocks, {5}, 3, CHART)
    assert [b.thread_index for b in out][:2] == [5, 280]
    assert out[3].thread_index == 290
    kept = {5, 280, 290}
    assert {b.thread_index for b in out} == kept
    for before, after in zip(blocks, out):
        assert after.runs is before.runs
    from skimage.color import deltaE_ciede2000
    for i in (2, 4):
        t = blocks[i].thread_index
        d = deltaE_ciede2000(np.repeat(CHART.lab[t].reshape(1, 3), 3, axis=0),
                             CHART.lab[sorted(kept)])
        assert out[i].thread_index == sorted(kept)[int(np.argmin(d))]
        assert out[i].thread_number == CHART[out[i].thread_index].number
    assert w["code"] == COLOR_CAP_APPLIED and w["stage"] == "plan"
    assert (w["before"], w["after"], w["dropped"], w["blocks"]) == (5, 3, 2, 2)


def test_admitted_cones_keep_their_slots_whatever_their_length():
    blocks = [_block(5, 1.0), _block(7, 1.0), _block(280, 500.0), _block(283, 400.0)]
    out, _ = fold_stray_cones(blocks, {5, 7}, 3, CHART)
    assert {b.thread_index for b in out} == {5, 7, 280}


def test_sequence_leaves_the_blocks_alone_with_the_flag_off(monkeypatch):
    seen: list[int] = []
    real = S7.fold_stray_cones

    def spy(*a, **kw):
        seen.append(1)
        return real(*a, **kw)

    monkeypatch.setattr(S7, "fold_stray_cones", own_thread_only(spy, real))
    _sequence_gradient(PipelineConfig(color_cap_sewn=False, edge_cap="none", max_colors=2))
    assert seen == []


def _ramp_source() -> SourcePixels:
    w, h = 320, 240
    t = np.linspace(0.0, 1.0, w)
    rgb = np.zeros((h, w, 3), np.uint8)
    rgb[..., 0] = np.tile(20 + 220 * t, (h, 1))      # black -> warm orange
    rgb[..., 1] = np.tile(10 + 120 * t, (h, 1))
    rgb[..., 2] = np.tile(5 + 20 * t, (h, 1))
    return SourcePixels(rgb=rgb, px_per_mm=4.0, origin_px=(w / 2.0, h / 2.0),
                        gradient_class=True)


def _sequence_gradient(cfg: PipelineConfig):
    poly = Polygon([(-35, -25), (35, -25), (35, 25), (-35, 25)])
    region = Region(shape_id="Sramp", polygon=poly, thread_index=5,
                    thread_number=CHART[5].number, area_mm2=poly.area,
                    meta={"layer": 0, "tier": "fill"})
    planned, _ = resolve_overlaps([region], FAB, cfg, design_class="gradient")
    return S7.sequence(planned, FAB, cfg, source_pixels=_ramp_source(),
                       design_class="gradient")


def test_a_one_region_ramp_keeps_its_shades_while_the_budget_has_room():
    off, _ = _sequence_gradient(PipelineConfig(color_cap_sewn=False, edge_cap="none"))
    on, _ = _sequence_gradient(PipelineConfig(color_cap_sewn=True, edge_cap="none"))
    assert len({b.thread_index for b in off}) >= 3, "fixture must exercise the chart-wide bands"
    assert [(b.thread_index, len(b.runs)) for b in on] == [(b.thread_index, len(b.runs)) for b in off]


def test_a_one_region_ramp_over_budget_sews_exactly_the_cap_and_keeps_the_region_cone():
    off, _ = _sequence_gradient(PipelineConfig(color_cap_sewn=False, edge_cap="none", max_colors=2))
    on, w = _sequence_gradient(PipelineConfig(color_cap_sewn=True, edge_cap="none", max_colors=2))
    off_cones = {b.thread_index for b in off}
    assert len(off_cones) > 2
    on_cones = {b.thread_index for b in on}
    assert len(on_cones) == 2 and on_cones <= off_cones
    assert sum(len(b.runs) for b in on) == sum(len(b.runs) for b in off)
    assert sum(1 for x in w if x.get("code") == COLOR_CAP_APPLIED) == 1


# --- 4. End to end ------------------------------------------------------------------

def _studio_like(**kw) -> PipelineConfig:
    """The Studio's request on the frozen engine: a cap of 2 on `logo_whitebg`
    with "Sew white areas" ticked white — three artwork cones at stage 4
    capped to two, then White recoloured onto the hole."""
    return frozen_cfg(target_width_mm=80.0, max_colors=2, garment_id="left_chest",
                      garment_rgb=NATURAL, sew_enclosed_white=True,
                      sew_enclosed_rgb=(255, 255, 255), **kw)


@pytest.fixture(scope="module")
def whitebg_arms():
    off = digitize(TESTDATA / "logo_whitebg.png", _studio_like(color_cap_sewn=False))
    on = digitize(TESTDATA / "logo_whitebg.png", _studio_like(color_cap_sewn=True))
    return off, on


def _cones(plan) -> set[int]:
    return {b.thread_index for b in plan.blocks}


def test_off_arm_leaks_the_white_cone_past_the_cap(whitebg_arms):
    (res, plan), _ = whitebg_arms
    assert WHITE_T in _cones(plan)
    assert len(_cones(plan)) == 3, sorted(_cones(plan))
    assert sum(1 for w in plan.warnings if w.get("code") == COLOR_CAP_APPLIED) == 1


def test_on_arm_sews_exactly_the_cap_with_white_kept(whitebg_arms):
    _, (res, plan) = whitebg_arms
    cones = _cones(plan)
    assert len(cones) == 2, sorted(cones)
    assert WHITE_T in cones
    assert {r.thread_index for r in res.regions if r.meta.get("stitched")} == cones
    caps = [w for w in plan.warnings if w.get("code") == COLOR_CAP_APPLIED]
    assert len(caps) == 1 and caps[0]["after"] == 2
