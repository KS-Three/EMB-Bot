"""Fine ink bars sew satin, not a hollow bean ring (`cfg.fine_bars_satin`,
built OFF 2026-10-25; ON since Kent's flip 2026-10-26, "Fine bars as satin" --
`PRE_FLIP` names the OFF arm, and `_cfg` reads it unless a test sets the flag).

The pro sews every free-standing thin ink bar as ONE satin at its drawn
width plus his pull, in all 5 artworks that have them (the small-symbols
census); ours sends every bar under the area floor to `run_outline`'s ring.
ON, a bar `columns.is_fine_bar` reads skips the run rescue for the ordinary
satin tier. The fixture holds the targets (a 0.30 x 4.0 mm black bar, a
0.30 x 1.6 mm stub) beside every control the census named: a 1.2 mm hex dot,
a garment-white sliver, a light-grey bar on a dark-grey square (a
highlight), a row of tan rope lenses (aspect 3.7), and a teal bar at aspect
4.7. OFF byte-identical (md5 pinned on main's engine, d36ff80e).
"""
from __future__ import annotations

import hashlib
import math

from shapely import affinity
from shapely.geometry import LineString, Point, Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.columns import is_fine_bar
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_satin import is_small_solid
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import chart_for
from tests.conftest import PRE_FLIP

GARMENT = (235, 232, 223)        # the Studio's Natural


def _thread(rgb) -> int:
    chart = chart_for(PipelineConfig())
    return min(range(len(chart)), key=lambda i: sum((a - b) ** 2 for a, b in zip(chart[i].rgb, rgb)))


BLACK, WHITE, LIGHT, DARK, TAN, TEAL = (_thread(c) for c in (
    (20, 20, 20), GARMENT, (200, 200, 200), (70, 70, 70), (163, 150, 135), (0, 128, 128)))


def _hexagon(across: float, cx: float, cy: float) -> Polygon:
    r = across / 2.0
    return Polygon([(cx + r * math.cos(math.radians(60 * k)),
                     cy + r * math.sin(math.radians(60 * k))) for k in range(6)])


def _lens(cx: float) -> Polygon:
    return affinity.rotate(affinity.scale(Point(cx, 10).buffer(1.0), 0.3, 1.1), 30)


SHAPES = [
    ("Sbar", box(0, 0, 4.0, 0.3), BLACK),
    ("Sstub", box(0, 2, 1.6, 2.3), BLACK),
    ("Sdot", _hexagon(1.2, 8, 0), BLACK),
    ("Swhite", box(0, 0.6, 3.0, 0.9), WHITE),
    ("Ssquare", box(12, -3, 18, 3), DARK),
    ("Slight", box(13, 0, 17, 0.3), LIGHT),
    *[(f"Srope{i}", _lens(20 + i * 0.98), TAN) for i in range(10)],
    ("Steal", box(0, 14, 3.6, 14.76), TEAL),
]
TARGETS = {"Sbar", "Sstub"}
#: the OFF md5 of `_md5(_runs())`, captured on main (d36ff80e)
OFF_MD5 = "603bed4bde3d5ba9661d26d02edc4a5f"


def _region(sid, poly, thread, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=str(thread), area_mm2=poly.area, source="test",
                  meta={"layer": thread, **meta})


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("fine_bars_satin", PRE_FLIP["fine_bars_satin"])     # the OFF arm unless set
    return PipelineConfig(underlay=False, garment_rgb=GARMENT, **kw)


PULL = fabric_for_garment("hat_front").pull_comp_mm


def _runs(shapes=SHAPES, **kw):
    # stage 5's polygon: the artwork grown by the hat's pull, as the job's
    # long rules are sewn
    planned = [PlannedRegion(region=_region(sid, poly, t),
                             polygon=poly.buffer(PULL, join_style=2), sew_index=t)
               for sid, poly, t in shapes]
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


def test_default_on():
    # Kent's flip on the wave-3 flip sheet 2026-10-26: "Fine bars as satin"
    assert PipelineConfig().fine_bars_satin is True
    assert PRE_FLIP["fine_bars_satin"] is False


def test_off_is_byte_identical():
    off = _runs()
    assert _md5(off) == OFF_MD5
    assert _md5(_runs(fine_bars_satin=False)) == OFF_MD5
    assert {r.kind for r in _of(off, "Sbar")} == {stitches.RUN}      # today's ring


def test_on_the_bar_and_the_stub_sew_satin():
    on = _runs(fine_bars_satin=True)
    for sid in TARGETS:
        poly = dict((s, p) for s, p, _t in SHAPES)[sid]
        sat = [r for r in _of(on, sid) if r.kind == stitches.SATIN]
        assert sat, (sid, [r.kind for r in _of(on, sid)])
        for r in sat:
            crosses = [math.dist(a, b) for a, b in zip(r.points, r.points[1:])]
            assert min(crosses) >= machine.SATIN_MIN_CROSS_MM - 1e-6, (sid, min(crosses))
        # on the compensated polygon: the hat's pull past the drawn bar, no further
        reach = poly.buffer(PULL + 0.1, join_style=2)
        assert all(reach.covers(Point(p)) for r in _of(on, sid) for p in r.points), sid


def test_on_every_control_is_byte_identical_to_off():
    off, on = _runs(), _runs(fine_bars_satin=True)
    for sid, _p, _t in SHAPES:
        if sid in TARGETS:
            continue
        assert _md5(_of(on, sid)) == _md5(_of(off, sid)), sid


def test_on_with_the_hairline_tier_the_bar_still_sews_satin():
    on = _runs(fine_bars_satin=True, hairline=True)
    assert stitches.SATIN in {r.kind for r in _of(on, "Sbar")}


def test_small_solids_satin_keeps_every_shape_it_sews():
    # a 0.6 x 3.66 mm bar both rules read, wide enough to sew its own chord
    # on the artwork: small_solids_satin's column, byte for byte
    poly = box(0, 0, 3.66, 0.6)
    assert poly.area < PipelineConfig().min_detail_mm ** 2
    assert _edge(poly) and is_small_solid(poly, 0.4)
    bar = [("Sbar", poly, BLACK)]
    alone = _runs(bar, small_solids_satin=True)
    assert stitches.SATIN in {r.kind for r in alone}
    assert _md5(_runs(bar, fine_bars_satin=True, small_solids_satin=True)) == _md5(alone)


def test_a_bar_small_solids_cannot_sew_is_still_a_fine_bar():
    # 0.45 mm across: small_solids reads it but its artwork column is under
    # a cross, so it would ring; the fine bar sews it on stage 5's polygon
    poly = box(0, 0, 4.6, 0.45)
    assert _edge(poly) and is_small_solid(poly, 0.4)
    bar = [("Sbar", poly, BLACK)]
    assert {r.kind for r in _runs(bar, small_solids_satin=True)} == {stitches.RUN}
    both = _runs(bar, fine_bars_satin=True, small_solids_satin=True)
    assert stitches.SATIN in {r.kind for r in both}


def _edge(poly, **meta):
    return is_fine_bar(_region("Sx", poly, BLACK, **meta), poly, [], _cfg())


def test_is_fine_bar_edges():
    assert not _edge(box(0, 0, 3.54, 0.6))          # aspect 5.9, 0.6 across
    assert _edge(box(0, 0, 3.66, 0.6))              # aspect 6.1
    assert _edge(box(0, 0, 1.35, 0.45))             # 0.45 across at aspect 3
    assert not _edge(box(0, 0, 0.9, 0.1))           # 0.9 long: under two crosses
    assert not _edge(box(0, 0, 4.0, 0.3), text_candidate=True)
    holed = Polygon(box(0, 0, 4, 0.45).exterior, [box(1, 0.1, 3, 0.35).exterior])
    assert not _edge(holed)
    assert _edge(box(0, 0, 4.0, 0.3))               # touching nothing qualifies
    bar = box(0, 0, 4.0, 0.3)
    dark = _region("Sdark", box(-1, -1, 5, 1.3), DARK)
    assert not is_fine_bar(_region("Sx", bar, LIGHT), bar, [dark], _cfg())
    assert is_fine_bar(_region("Sx", bar, BLACK), bar, [dark], _cfg())
