"""Column-lane ribbon hand-back (`cfg.lettering_columns_ribbon_handback`, built
OFF 2026-11-16).

A text-cluster member whose ORDINARY ribbon verdict (`classify_ribbon` at the
design's satin ceiling, not the lettering split's open one) is fill is a
solid, not a stroke: Texaco's red-disc wedges and Adidas' smallest bar were
tagged into a text cluster and sewed as fanned satin columns. ON, such a
member takes the ladder's route as if untagged (its tags stay); a member
whose verdict is satin, and a design with no text cluster, are untouched.

Synthetic shapes only: no logo art lives in the repo.
"""
from __future__ import annotations

import hashlib

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_satin import classify_ribbon
from digitizer_core.stage7_sequence import _ribbon_handback, satin_ceiling_mm, sequence
from digitizer_core.stitches import FILL, SATIN

# a slab T, 81 mm2 and solid (Texaco class: dt_p90_cap); TRI a wedge (dt_irregular)
SLAB = Polygon([(0, 0), (9, 0), (9, 5), (6.5, 5), (6.5, 14), (2.5, 14), (2.5, 5), (0, 5)])
# a stroke letter: a 2 x 12 mm stem
TRI = Polygon([(0, 0), (12, 0), (4, 15)])
STEM = box(0, 0, 2.0, 12.0)


def _region(poly, tagged=True, sid="Sx"):
    meta = {"layer": 0}
    if tagged:
        meta.update(text_candidate=True, text_cluster_id="TC1")
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="0020",
                  area_mm2=poly.area, source="test", meta=meta)


def _sew(poly, tagged=True, **cfg_kw):
    cfg = PipelineConfig(**cfg_kw)
    r = _region(poly, tagged)
    blocks, _ = sequence([PlannedRegion(region=r, polygon=poly, sew_index=0)], fabric_for(cfg), cfg)
    return [x for b in blocks for x in b.runs if x.shape_id == r.shape_id]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _kinds(runs) -> set[str]:
    return {r.kind for r in runs}


SOLIDS = pytest.mark.parametrize("poly", [SLAB, TRI], ids=["slab", "tri"])


def test_flag_is_built_off():
    assert PipelineConfig().lettering_columns_ribbon_handback is False


def test_the_fixtures_read_as_intended():
    cfg = PipelineConfig()
    cap = satin_ceiling_mm(cfg)
    assert not classify_ribbon(SLAB, cap).satin and not classify_ribbon(TRI, cap).satin   # solids: fill at the ordinary ceiling
    assert classify_ribbon(STEM, cap).satin               # a stroke: satin
    assert not _ribbon_handback(_region(SLAB), cfg, cap, "flat")      # flag off: never


@SOLIDS
def test_off_a_tagged_solid_sews_in_the_column_lane(poly):
    runs = _sew(poly)
    assert SATIN in _kinds(runs) and FILL not in _kinds(runs)


@SOLIDS
def test_on_a_tagged_solid_sews_its_ladder_verdict_fill(poly):
    off = _sew(poly)
    on = _sew(poly, lettering_columns_ribbon_handback=True)
    assert FILL in _kinds(on) and SATIN not in _kinds(on)
    assert _md5(on) != _md5(off)


@SOLIDS
def test_on_the_ladder_route_is_the_untagged_route(poly):
    # handed back, the member sews as the same shape with no cluster tags at all
    tagged_on = _sew(poly, lettering_columns_ribbon_handback=True)
    untagged = _sew(poly, tagged=False)
    assert _md5(tagged_on) == _md5(untagged)


@SOLIDS
def test_off_spelled_false_is_the_default_byte_for_byte(poly):
    assert _md5(_sew(poly)) == _md5(_sew(poly, lettering_columns_ribbon_handback=False))


def test_a_stroke_letter_is_untouched_on():
    off = _sew(STEM)
    on = _sew(STEM, lettering_columns_ribbon_handback=True)
    assert SATIN in _kinds(on)
    assert _md5(on) == _md5(off)


@pytest.mark.parametrize("poly", [SLAB, TRI, STEM], ids=["slab", "tri", "stem"])
def test_a_design_with_no_text_cluster_is_untouched(poly):
    off = _sew(poly, tagged=False)
    on = _sew(poly, tagged=False, lettering_columns_ribbon_handback=True)
    assert _md5(on) == _md5(off)


@SOLIDS
def test_the_cluster_tags_stay_on(poly):
    cfg = PipelineConfig(lettering_columns_ribbon_handback=True)
    r = _region(poly)
    assert _ribbon_handback(r, cfg, satin_ceiling_mm(cfg), "flat")     # handed back
    assert r.meta["text_candidate"] and r.meta["text_cluster_id"] == "TC1"   # and still tagged


def test_a_forced_tier_is_not_handed_back():
    cfg = PipelineConfig(lettering_columns_ribbon_handback=True)
    r = _region(SLAB)
    r.meta["tier"] = "satin"
    assert not _ribbon_handback(r, cfg, satin_ceiling_mm(cfg), "flat")
