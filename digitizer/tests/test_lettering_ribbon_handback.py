"""Column-lane ribbon hand-back (`cfg.lettering_columns_ribbon_handback`, built
OFF 2026-11-16), narrowed to cluster outliers the same day.

A text-cluster member is handed back to the ladder only when BOTH hold: its
ordinary ribbon verdict (`classify_ribbon` at the design's satin ceiling, not
the lettering split's open one) is fill, and its dt_p90 is at least
`RIBBON_HANDBACK_OUTLIER` (1.6) times the median dt_p90 of its cluster's lane
members, in a cluster of 3 or more. Adidas' smallest bar reads 2.01; real bold
letters (Becker, Visa, Canon, USGS) reach 1.30 and stay in the lane.

Synthetic shapes only: no logo art lives in the repo.
"""
from __future__ import annotations

import hashlib

from shapely.affinity import translate
from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_satin import _dt_stats, classify_ribbon
from digitizer_core.stage7_sequence import (RIBBON_HANDBACK_MIN_CLUSTER, RIBBON_HANDBACK_OUTLIER,
                                            RIBBON_OUTLIER_KEY, satin_ceiling_mm, sequence,
                                            stamp_ribbon_outliers)
from digitizer_core.stitches import FILL, SATIN

H = 14.0


def bar(w):
    return box(0, 0, w, H)


def p90(poly):
    return _dt_stats(poly).p90_mm


def _regions(polys, tagged=True):
    out = []
    for i, poly in enumerate(polys):
        poly = translate(poly, xoff=i * 22.0)
        meta = {"layer": 0}
        if tagged:
            meta.update(text_candidate=True, text_cluster_id="TC1")
        out.append(Region(shape_id=f"S{i}", polygon=poly, thread_index=0, thread_number="0020",
                          area_mm2=poly.area, source="test", meta=meta))
    return out


def _sew(polys, tagged=True, **cfg_kw):
    cfg = PipelineConfig(**cfg_kw)
    regs = _regions(polys, tagged)
    blocks, _ = sequence([PlannedRegion(region=r, polygon=r.polygon, sew_index=i) for i, r in enumerate(regs)],
                         fabric_for(cfg), cfg)
    runs = [x for b in blocks for x in b.runs]
    return {r.shape_id: [x for x in runs if x.shape_id == r.shape_id] for r in regs}


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, r.shape_id,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _md5_all(by) -> str:
    return hashlib.md5("".join(_md5(by[k]) for k in sorted(by)).encode()).hexdigest()


def _kinds(runs) -> set[str]:
    return {r.kind for r in runs}


ON = {"lettering_columns_ribbon_handback": True}
MATES_THIN = [bar(3.0)] * 3                 # p90 ~3.0, satin
MATES_BOLD = [bar(4.4)] * 3                 # p90 ~4.4, still satin


def test_flag_is_built_off():
    assert PipelineConfig().lettering_columns_ribbon_handback is False
    assert RIBBON_HANDBACK_OUTLIER == 1.6 and RIBBON_HANDBACK_MIN_CLUSTER == 3


def test_the_fixtures_read_as_intended():
    cap = satin_ceiling_mm(PipelineConfig())
    assert classify_ribbon(bar(3.0), cap).satin and classify_ribbon(bar(4.4), cap).satin
    for w in (6.4, 5.8):
        assert not classify_ribbon(bar(w), cap).satin                 # fill verdicts
    assert p90(bar(6.4)) / p90(bar(3.0)) >= 2.0
    assert 1.25 <= p90(bar(5.8)) / p90(bar(4.4)) < 1.45               # a real bold letter's ratio, under 1.6


def test_off_every_member_sews_in_the_column_lane():
    by = _sew(MATES_THIN + [bar(6.4)])
    assert SATIN in _kinds(by["S3"]) and FILL not in _kinds(by["S3"])


def test_on_a_blob_at_2x_its_mates_is_handed_back():
    off = _sew(MATES_THIN + [bar(6.4)])
    on = _sew(MATES_THIN + [bar(6.4)], **ON)
    assert FILL in _kinds(on["S3"]) and SATIN not in _kinds(on["S3"])
    assert _md5(on["S3"]) != _md5(off["S3"])
    for k in ("S0", "S1", "S2"):                                       # its mates stay in the lane
        assert SATIN in _kinds(on[k])


def test_on_the_handed_back_blob_sews_as_the_untagged_one():
    on = _sew(MATES_THIN + [bar(6.4)], **ON)
    alone = _sew([bar(6.4)], tagged=False)
    assert [r.kind for r in on["S3"]] == [r.kind for r in alone["S0"]]


def test_on_a_blob_at_1_3x_its_mates_stays_in_the_lane():
    polys = MATES_BOLD + [bar(5.8)]
    assert _md5_all(_sew(polys, **ON)) == _md5_all(_sew(polys))
    assert SATIN in _kinds(_sew(polys, **ON)["S3"])


def test_a_word_of_uniform_bold_letters_is_untouched():
    polys = [bar(6.0)] * 4                  # every member a fill verdict, none an outlier of its word
    assert _md5_all(_sew(polys, **ON)) == _md5_all(_sew(polys))


def test_a_two_member_cluster_never_hands_back():
    polys = [bar(3.0), bar(6.4)]
    assert _md5_all(_sew(polys, **ON)) == _md5_all(_sew(polys))


def test_off_spelled_false_is_the_default_byte_for_byte():
    polys = MATES_THIN + [bar(6.4)]
    assert _md5_all(_sew(polys)) == _md5_all(_sew(polys, lettering_columns_ribbon_handback=False))


def test_a_design_with_no_text_cluster_is_untouched():
    polys = MATES_THIN + [bar(6.4)]
    assert _md5_all(_sew(polys, tagged=False, **ON)) == _md5_all(_sew(polys, tagged=False))


def test_the_stamp_and_the_cluster_tags():
    regs = _regions(MATES_THIN + [bar(6.4)])
    stamp_ribbon_outliers(regs, PipelineConfig(**ON))
    assert [bool(r.meta.get(RIBBON_OUTLIER_KEY)) for r in regs] == [False, False, False, True]
    assert all(r.meta["text_candidate"] and r.meta["text_cluster_id"] == "TC1" for r in regs)   # tags stay
    regs_off = _regions(MATES_THIN + [bar(6.4)])
    stamp_ribbon_outliers(regs_off, PipelineConfig())
    assert not any(RIBBON_OUTLIER_KEY in r.meta for r in regs_off)                              # off: nothing written


def test_a_forced_tier_is_not_stamped():
    regs = _regions(MATES_THIN + [bar(6.4)])
    regs[3].meta["tier"] = "satin"
    stamp_ribbon_outliers(regs, PipelineConfig(**ON))
    assert not regs[3].meta.get(RIBBON_OUTLIER_KEY)
