"""No edge cap on lettering — `edge_cap_skip_lettering`, folded into the code
(lettering construction plan step 5, 2026-09-19).

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
trims / −319 stitches, uncovered area unchanged on all nine). The flag is
folded into the code since 2026-11-20; the OFF arm is gone from this file.
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
    # Same for `satin_rails_follow_edge`, "envelope" by default since #567
    # (2026-09-30, Kent's pick). The envelope lowers BOTH arms' uncovered
    # area but the capped arm more -- 16.8 -> 13.9 OFF, 17.6 -> 16.7 ON
    # (measured 2026-09-30) -- so this flag's marginal cost reads +20% there
    # against +4.8% here, while its absolute ON figure still improves. The
    # envelope's own price belongs to its own tests, not to this flag's.
    kw.setdefault("satin_rails_follow_edge", False)
    # And on the skeleton tier: the Column lane (`lettering_columns`, ON by
    # default since Kent's 2026-10-12 flip) takes the letters ahead of the
    # edge cap this file prices. Its own cap behaviour is pinned in
    # `tests/test_lettering_columns.py`.
    kw.setdefault("lettering_columns", False)
    kw.setdefault("bean_only_lines", False)   # this file prices the bean cap; the rule (ON 2026-10-27) sews none
    kw.setdefault("edge_cap", "bean")         # ...and the default is "none" since 2026-10-29
    cfg = PipelineConfig(target_width_mm=80.2, garment_id="left_chest",
                         max_colors=6, **kw)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return cfg, result, plan


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



# Deleted 2026-11-19 (satin construction flags folded into the engine): the
# OFF-arm finding this flag rests on -- "the cap is patching the letters' bare
# corners, 418 of 457 cap stitches on a satin letter" -- and the on-vs-off
# deltas (trims 23 -> 7, cap runs 18 -> 1). With tip caps, the crown cover and
# the junction stack always on, this fixture's letters have no bare corners for
# the cap to patch: both arms sew the same 2,388 stitches, 19 trims and one
# cap run of 35 stitches, none on a letter. `test_on_no_cap_sample...` still
# pins the rule's contract. Deleted 2026-11-20 (flag folded into the code, B5):
# `test_the_default_is_on`, `test_explicit_on_is_the_default_byte_for_byte`,
# `test_on_only_the_cap_moves` and `test_a_design_with_no_lettering_is_untouched`,
# which compared an `edge_cap_skip_lettering=False` arm that no longer exists.

def test_on_no_cap_sample_stands_on_a_satin_letter(on):
    """A typed glyph gets no cap: ON, not one cap sample lies within a
    thread's width of a satin-sewn letter's outline."""
    _cfg, result, plan = on
    letters = _satin_letters(result, plan)
    assert len(letters) >= 5
    on_letters, _total = _cap_stitches_on(letters, plan)
    assert on_letters == 0


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
    cfg_kw.setdefault("bean_only_lines", False)   # as above
    cfg_kw.setdefault("edge_cap", "bean")
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
