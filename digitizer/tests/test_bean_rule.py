"""The reference digitizer's bean rule (`cfg.bean_only_lines`, built OFF and
flipped ON by Kent the same day, 2026-10-27, PR #1161; `digitizer_core/bean_rule.py`).

Measured over 17 paired jobs (`tools/bean_census.py`): he beans only LINES
the art draws as a thin stroke of their own colour; never a filled body's
edge, never small lettering, never a small solid. The fixture holds one of
each beside the sources that bean them today: a 0.3 mm thin ring (a LINE
under the area floor: the run tier's bean ring, kept), a 1.4 mm dot (a SOLID:
the run tier's ring, refused), a lettering-tagged 0.3 mm ring (a LETTER,
refused), and a 9 x 6 mm fill whose silhouette the bean edge cap rings
(refused). The satin rungs that would take the dot and the ring on today's
defaults (`compact_solids_satin`, `small_solids_satin`, `border_by_size`) are
off in the fixture so the sources under test are the ones that sew; OFF is
byte-identical to the frozen engine (`frozen_cfg`, md5 pinned).
"""
from __future__ import annotations

import hashlib

from shapely.geometry import Point, Polygon, box

from digitizer_core import PipelineConfig, bean_rule, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import chart_for
from tests.conftest import PRE_FLIP, frozen_cfg

GARMENT = (235, 232, 223)


def _thread(rgb) -> int:
    chart = chart_for(PipelineConfig())
    return min(range(len(chart)), key=lambda i: sum((a - b) ** 2 for a, b in zip(chart[i].rgb, rgb)))


BLACK = _thread((20, 20, 20))
RED = _thread((200, 30, 30))

def _ring(cx, cy, r_out=1.3, w=0.3) -> Polygon:
    return Point(cx, cy).buffer(r_out).difference(Point(cx, cy).buffer(r_out - w))


SHAPES = [
    ("Sline", _ring(0, 0), BLACK, {}),                               # a thin ring, a LINE: bean stays
    ("Sdot", Point(8, 0).buffer(0.7), BLACK, {}),                    # a 1.4 mm SOLID: no bean
    ("Sletter", _ring(0, 4), BLACK, {"text_candidate": True,         # a LETTER: no bean
                                     "text_cluster_id": "T1"}),
    ("Sfill", box(0, 8, 9.0, 14.0), RED, {}),                        # a fill: its EDGE is never a bean
]
PULL = 0.2


def _region(sid, poly, thread, meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=str(thread), area_mm2=poly.area, source="test",
                  meta={"layer": thread, **meta})


def _cfg(**kw) -> PipelineConfig:
    base = {"underlay": False, "garment_rgb": GARMENT, "edge_cap": "bean", "small_shape_rescue": True,
            "compact_solids_satin": False, "small_solids_satin": False, "border_by_size": False,
            "lettering_columns_small_stem": False}
    return frozen_cfg(**{**base, **kw})


def _runs(**kw):
    planned = [PlannedRegion(region=_region(sid, poly, t, meta),
                             polygon=poly.buffer(PULL, join_style=2), sew_index=i)
               for i, (sid, poly, t, meta) in enumerate(SHAPES)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"), _cfg(**kw))
    return [r for b in blocks for r in b.runs]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.shape_id, r.kind, r.jump, r.trim,
                       [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _of(runs, sid):
    return [r for r in runs if r.shape_id == sid]


def _bean_kinds(runs):
    return {r.shape_id for r in runs if r.kind in (stitches.RUN, stitches.BEAN)}


# --- the decision ---------------------------------------------------------------

def test_default_on():
    # Kent's flip on PR #1161, 2026-10-27: "Flip ON (Recommended)"
    assert PipelineConfig().bean_only_lines is True
    assert PRE_FLIP["bean_only_lines"] is False


def test_a_line_wants_a_bean_and_nothing_else_does():
    assert bean_rule.element_of(box(0, 0, 4.0, 0.3)) == bean_rule.LINE
    assert bean_rule.element_of(Point(0, 0).buffer(0.7)) == bean_rule.SOLID
    assert bean_rule.element_of(box(0, 0, 4.0, 0.3), letter=True) == bean_rule.LETTER
    assert bean_rule.allows_bean(box(0, 0, 4.0, 0.3))
    assert bean_rule.allows_bean(box(0, 0, 20.0, 1.1))
    assert not bean_rule.allows_bean(box(0, 0, 20.0, 1.4))
    assert not bean_rule.allows_bean(Point(0, 0).buffer(0.7))
    assert not bean_rule.allows_bean(box(0, 0, 4.0, 0.3), letter=True)
    assert not bean_rule.wants_bean(bean_rule.EDGE)


def test_the_line_threshold_is_the_measured_one():
    # the reference's retraced runs lie on strokes of 0.47-1.7 mm (median 1.4);
    # his satin floor for a free bar is 0.86. A ring that is not a polygon is no line.
    assert bean_rule.LINE_MAX_MM == 1.2
    assert bean_rule.min_dim_mm(None) == 0.0
    assert bean_rule.min_dim_mm(Polygon()) == 0.0
    assert abs(bean_rule.min_dim_mm(box(0, 0, 10, 1.0)) - 1.0) < 0.06


# --- the sources, through stage 7 ----------------------------------------------

#: `_md5(_runs())` on the frozen engine (tests/engine_2026_10_27.json), OFF
OFF_MD5 = "24c068ad1eda533deae5635598222986"


def test_off_is_byte_identical():
    off = _runs()
    assert _md5(off) == OFF_MD5
    assert _md5(_runs(bean_only_lines=False)) == OFF_MD5
    # today: the dot and the letter ring as beans, the fill's silhouette is capped
    assert {"Sdot", "Sletter", "Sline"} <= _bean_kinds(off)
    assert any(r.role == stitches.ROLE_EDGE_CAP for r in off)


def test_on_only_the_line_keeps_its_bean():
    on = _runs(bean_only_lines=True)
    assert "Sline" in _bean_kinds(on)
    assert not any(r.kind in (stitches.RUN, stitches.BEAN) for r in _of(on, "Sdot"))
    assert not any(r.kind in (stitches.RUN, stitches.BEAN) for r in _of(on, "Sletter"))
    # the bean edge cap sews nothing
    assert not any(r.role == stitches.ROLE_EDGE_CAP for r in on)
    # the line and the fill are laid exactly as OFF laid them
    off = _runs()
    for sid in ("Sline", "Sfill"):
        assert _md5(_of(on, sid)) == _md5(_of(off, sid)), sid


def test_on_the_satin_edge_cap_is_untouched():
    off = _runs(edge_cap="satin")
    on = _runs(edge_cap="satin", bean_only_lines=True)
    cap_off = [r for r in off if r.role == stitches.ROLE_EDGE_CAP]
    cap_on = [r for r in on if r.role == stitches.ROLE_EDGE_CAP]
    assert cap_off and _md5(cap_off) == _md5(cap_on)


def test_an_explicit_run_tier_is_still_an_instruction():
    planned = [PlannedRegion(region=_region("Sdot", Point(8, 0).buffer(0.7), BLACK, {"tier": "run"}),
                             polygon=Point(8, 0).buffer(0.7 + PULL), sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"), _cfg(bean_only_lines=True))
    runs = [r for b in blocks for r in b.runs]
    assert any(r.kind == stitches.RUN for r in runs)
