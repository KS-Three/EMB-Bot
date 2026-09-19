"""No edge cap on lettering — `cfg.edge_cap_skip_lettering` (lettering
construction plan step 5, 2026-09-19).

The design-silhouette cap (`cfg.edge_cap`) sews only the stretches of the
outline nothing linear already covers, and on a satin-sewn letter that is
exactly the bare corners and junction seams the satin decomposition leaves:
on the plan's traced MARINE at 80 mm, 17 of the cap's 18 runs and 418 of its
457 stitches stood on the letters' outlines — the cap patching a defect
upstream, at 16 of the word's 41 trims before steps 1–3. A typed glyph gets
no cap. ON, a text-cluster member that sewed SATIN hands its sewn polygon to
the cap's `omit`; a member that sewed FILL keeps its cap, because a tatami
letter's rows end in open air at its edge and that is the defect the cap
exists for.

Measured 2026-09-19 on the fixture (`docs/renders/lettering-route-2026-09-19/
marine_80mm_traced_input.png`, 80.2 mm): stitches 2,192 → 1,774, trims
23 → 7, cap runs 18 → 1, cap stitches on satin letters 418 → 0, uncovered
artwork 0.0 both ways. The 127 mm fixture, whose letters fill, is
byte-identical either way — the negative half of the rule.

**Built OFF and FLIPPED ON the same day** (Kent's call 2026-09-19, over
those numbers, the render and the nine-logo sheet: five logos move for −12
trims / −319 stitches, uncovered area unchanged on all nine). `False` is the
pre-flip cap byte for byte, and this file pins both sides.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from shapely import affinity
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

from digitizer_core import PipelineConfig, get_fabric, stitches
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from digitizer_core.preflight import run_preflight
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import _satin_lettering_cover, sequence
from digitizer_core.threads import CHART

from .test_stroke_order_euler import FIXTURE

FAB = get_fabric("pique_knit")
# How close a cap sample has to be to a letter's outline to be "standing on
# it" — the thread's own width, generously: a bean station on the outline
# sits at 0.0 and one on the fabric a column's width away sits at 0.7+.
TOL_MM = 0.35


# --- the fixture ------------------------------------------------------------

def _run(**kw):
    cfg = PipelineConfig(target_width_mm=80.2, garment_id="left_chest",
                         max_colors=6, **kw)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return cfg, result, plan


@pytest.fixture(scope="module")
def off():
    """The pre-flip cap, explicitly."""
    return _run(edge_cap_skip_lettering=False)


@pytest.fixture(scope="module")
def on():
    """The default since the flip."""
    return _run()


def _tiers(plan):
    tiers: dict[str, set[str]] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id and run.kind in (stitches.SATIN, stitches.FILL):
            tiers.setdefault(run.shape_id, set()).add(str(run.kind))
    return tiers


def _satin_letters(result, plan):
    tiers = _tiers(plan)
    return [r for r in result.regions if r.meta.get("text_candidate")
            and tiers.get(r.shape_id) == {str(stitches.SATIN)}]


def _cap_runs(plan):
    return [run for _b, run in plan.iter_runs()
            if run.shape_id == "__edge_cap__"]


def _cap_stitches_on(letters, plan) -> tuple[int, int]:
    """-> (cap samples within TOL_MM of a letter's outline, all cap samples)."""
    ring = prep(unary_union([r.polygon.boundary.buffer(TOL_MM)
                             for r in letters]))
    total = on_letters = 0
    for run in _cap_runs(plan):
        for p in run.points:
            total += 1
            if ring.intersects(Point(p)):
                on_letters += 1
    return on_letters, total


def _uncovered(cfg, result, plan) -> float:
    pf = run_preflight(result, plan, cfg, image=str(FIXTURE))
    return float(pf["metrics"].get("uncovered_total_mm2") or 0.0)


def test_the_default_is_on():
    """Built OFF and flipped ON the same day — Kent's call (plan step 5).
    False stays reachable: it is the pre-flip cap, pinned below."""
    assert PipelineConfig().edge_cap_skip_lettering is True
    assert PipelineConfig(edge_cap_skip_lettering=False).edge_cap_skip_lettering is False


def test_explicit_on_is_the_default_byte_for_byte(on):
    _cfg, _result, default = on
    _c, _r, explicit = _run(edge_cap_skip_lettering=True)
    assert ([r.points for _b, r in explicit.iter_runs()]
            == [r.points for _b, r in default.iter_runs()])


def test_off_the_cap_stands_on_the_satin_letters(off):
    """The finding the step rests on: the cap is patching the letters'
    bare corners. Most of its stitches sit on a satin letter's outline."""
    _cfg, result, plan = off
    letters = _satin_letters(result, plan)
    assert len(letters) >= 5, "the fixture's word should sew as satin"
    on_letters, total = _cap_stitches_on(letters, plan)
    assert total > 0, "the fixture should be capped OFF"
    assert on_letters > total / 2, (on_letters, total)   # 418 of 457 measured


def test_on_no_cap_sample_stands_on_a_satin_letter(on):
    """A typed glyph gets no cap: ON, not one cap sample lies within a
    thread's width of a satin-sewn letter's outline."""
    _cfg, result, plan = on
    letters = _satin_letters(result, plan)
    assert len(letters) >= 5
    on_letters, _total = _cap_stitches_on(letters, plan)
    assert on_letters == 0


def test_on_the_fixture_loses_its_cap_trims_and_keeps_its_cover(off, on):
    """Measured: trims 23 → 7, cap runs 18 → 1, stitches 2,192 → 1,774,
    uncovered 0.0 → 0.0. Pinned as directions and floors, not as the
    numbers, so a later step that moves the fixture does not fail this."""
    cfg_off, res_off, p_off = off
    cfg_on, res_on, p_on = on
    assert p_on.stats.trims <= p_off.stats.trims - 10
    assert len(_cap_runs(p_on)) <= 2 < len(_cap_runs(p_off))
    assert p_on.stats.stitch_count < p_off.stats.stitch_count
    # The bare corners a letter still has are now its own to show — and on
    # this fixture, with step 3's corner rule ON, they stay under the
    # coverage floor: no uncovered artwork appears.
    assert _uncovered(cfg_on, res_on, p_on) <= _uncovered(cfg_off, res_off, p_off) + 0.5


def test_on_only_the_cap_moves(off, on):
    """Every run that is not the cap is what it was: the flag reaches the
    cap's `omit` and nothing else."""
    _c1, _r1, p_off = off
    _c2, _r2, p_on = on
    art_off = [r.points for _b, r in p_off.iter_runs() if r.shape_id != "__edge_cap__"]
    art_on = [r.points for _b, r in p_on.iter_runs() if r.shape_id != "__edge_cap__"]
    assert art_on == art_off


# --- the negative half, on synthetic geometry --------------------------------

def _bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def _region(poly: Polygon, sid: str, thread: int, layer: int,
            meta: dict | None = None) -> Region:
    m = {"layer": layer}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta=m)


def _plan_for(regions: list[Region], **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)
    return SimpleNamespace(blocks=blocks, warnings=warnings, cfg=c)


def _points(plan):
    return [r.points for b in plan.blocks for r in b.runs]


def _cap_block(plan):
    for b in plan.blocks:
        if any(r.shape_id == "__edge_cap__" for r in b.runs):
            return b
    return None


def test_a_fill_sewn_text_candidate_keeps_its_cap():
    """A 20 mm-wide "letter" fills (over the satin ceiling), and its rows
    end in open air at its edge — the defect the cap exists for. ON is
    byte-identical to OFF, cap included."""
    slab = [_region(_bar(20, 30), "T", 3, 0, {"text_candidate": True})]
    off = _plan_for(slab, edge_cap_skip_lettering=False)
    on = _plan_for(slab)
    kinds = {str(r.kind) for b in off.blocks for r in b.runs if r.shape_id == "T"}
    assert str(stitches.FILL) in kinds, kinds
    assert _cap_block(off) is not None, "a lone fill should be capped"
    assert _points(on) == _points(off)


def test_a_design_with_no_lettering_is_untouched():
    """Two abutting fields, no text candidate anywhere: the flag has no
    input and the plan is what it was."""
    both = [_region(_bar(15, 30, cx=-7.5), "L", 3, 0),
            _region(_bar(15, 30, cx=7.5), "R", 5, 1)]
    assert _points(_plan_for(both, edge_cap_skip_lettering=False)) == _points(_plan_for(both))


# --- the helper reads the runs, not a verdict --------------------------------

def _planned(sid: str, poly: Polygon, text: bool):
    region = SimpleNamespace(meta={"text_candidate": text} if text else {})
    return SimpleNamespace(shape_id=sid, region=region, polygon=poly)


def _blocks(*kinds_by_shape: tuple[str, str]):
    runs = [stitches.StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=kind,
                               shape_id=sid) for sid, kind in kinds_by_shape]
    return [stitches.StitchBlock(thread_index=0, thread_number="1234",
                                 rgb=(0, 0, 0), runs=runs)]


def test_the_cover_is_the_satin_letters_and_nothing_else():
    a, b, c = _bar(3, 30, cx=-10), _bar(3, 30), _bar(3, 30, cx=10)
    sewn = [_planned("A", a, text=True),      # satin letter -> covered
            _planned("B", b, text=True),      # letter that FILLED -> kept
            _planned("C", c, text=False)]     # satin, not a letter -> kept
    blocks = _blocks(("A", stitches.SATIN), ("B", stitches.SATIN),
                     ("B", stitches.FILL), ("C", stitches.SATIN))
    cover = _satin_lettering_cover(sewn, blocks)
    assert cover is not None
    assert cover.equals(a)


def test_no_satin_letter_means_no_cover_at_all():
    sewn = [_planned("B", _bar(3, 30), text=True),
            _planned("C", _bar(3, 30, cx=10), text=False)]
    blocks = _blocks(("B", stitches.FILL), ("C", stitches.SATIN))
    assert _satin_lettering_cover(sewn, blocks) is None
