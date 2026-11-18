"""`cfg.extra["cap_merged_layer_home"]` and `cfg.extra["shadow_to_page"]` (2026-11-18, built OFF).

Golden Tee's GOLF (prime grader): the teal bevel the colour cap folded onto black
kept its quantize layer (6, last) and sewed over the gold; the soft drop shadow
was quantised to a Fieldstone band and sewn as a grey fringe.
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage4_vectorize import rehome_cap_merged_regions
from digitizer_core.threads import chart_for

CHART = chart_for(PipelineConfig())


def _r(sid, thread, layer, merged_from=None, **meta):
    m = {"layer": layer, **meta}
    if merged_from:
        m["color_cap_merged_from"] = merged_from
    return Region(shape_id=sid, polygon=box(0, 0, 1, 1), thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=1.0, meta=m)


def test_cap_merged_region_takes_the_earliest_layer_declaring_its_new_spool():
    layer_threads = [3, 7, 9, 12, 14, 20, 22]      # layer 1 declares spool 7
    merged = _r("teal", 7, 6, merged_from="3344")   # folded onto spool 7, still layer 6
    plain = _r("black", 7, 1)
    gold = _r("gold", 12, 3)
    assert rehome_cap_merged_regions([merged, plain, gold], layer_threads) == 1
    assert merged.meta["layer"] == 1
    assert plain.meta["layer"] == 1 and gold.meta["layer"] == 3


def test_nothing_moves_onto_a_cone_no_layer_declares_or_for_a_step_region():
    a = _r("a", 99, 4, merged_from="x")
    b = _r("b", 7, 4, merged_from="x", step_key="s")
    assert rehome_cap_merged_regions([a, b], [3, 7, 9]) == 0
    assert a.meta["layer"] == 4 and b.meta["layer"] == 4


def test_both_flags_are_cfg_extra_keys_default_off():
    assert not (PipelineConfig().extra or {}).get("cap_merged_layer_home")
    assert not (PipelineConfig().extra or {}).get("shadow_to_page")


def test_golden_tee_with_the_flags_on():
    """Through the Studio request at the pro's size: OFF is the engine, A puts the
    black under the gold (one black block, not two), B drops the grey fringe."""
    from tools import pro_pair as pp
    from tools.pro_baseline import JOBS, resolve
    garment, width, spec, *_ = JOBS["goldentee_hat"]
    art = resolve(spec)

    def grey(d):
        return sum(r.area_mm2 for r in d.result.regions if r.thread_number == "0124")

    off = pp.digitize(art, width, garment)
    a = pp.digitize(art, width, garment, {"extra.cap_merged_layer_home": True})
    b = pp.digitize(art, width, garment, {"extra.shadow_to_page": True})
    blacks = lambda d: sum(1 for x in d.plan.blocks if x.thread_number == "0020")
    assert blacks(off) == 2 and blacks(a) == 1
    assert grey(b) < 0.5 * grey(off)
    assert grey(a) == grey(off)
