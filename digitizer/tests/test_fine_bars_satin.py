"""Fine ink bars sew satin, not a hollow bean ring (`fine_bars_satin`,
built OFF 2026-10-25; ON since Kent's flip 2026-10-26, "Fine bars as satin";
folded into the code 2026-11-19).

The pro sews every free-standing thin ink bar as ONE satin at its drawn
width plus his pull, in all 5 artworks that have them (the small-symbols
census); ours sends every bar under the area floor to `run_outline`'s ring.
A bar `columns.is_fine_bar` reads skips the run rescue for the ordinary
satin tier. The fixture holds the targets (a 0.30 x 4.0 mm black bar, a
0.30 x 1.6 mm stub) beside every control the census named: a 1.2 mm hex dot,
a garment-white sliver, a light-grey bar on a dark-grey square (a
highlight), a row of tan rope lenses (aspect 3.7), and a teal bar at aspect
4.7.
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


def _region(sid, poly, thread, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=str(thread), area_mm2=poly.area, source="test",
                  meta={"layer": thread, **meta})


def _cfg(**kw) -> PipelineConfig:
    # `bean_only_lines` (ON since Kent's 2026-10-27 flip) refuses the dot's and
    # the lenses' rings; this file prices the bars alone, on the engine the md5 was pinned on
    kw.setdefault("bean_only_lines", PRE_FLIP["bean_only_lines"])
    # `border_by_size_corner_loss` (ON since 2026-11-17): the fixture's 6 mm sharp
    # square (Ssquare, rounding loss 0.171) lost its size ring; the md5 was pinned with it
    kw.setdefault("border_by_size_corner_loss", PRE_FLIP["border_by_size_corner_loss"])
    # the flag ends/seam trio (ON since 2026-11-17) insets every free satin end; pinned before it
    for name in ("satin_cap_skew_inset", "satin_seam_hold", "satin_free_end_chord_aim"):
        kw.setdefault(name, PRE_FLIP[name])
    # `satin_rectangles` (ON since 2026-11-19) sews the bars as rectangles; pinned before it
    kw.setdefault("satin_rectangles", PRE_FLIP["satin_rectangles"])
    kw.setdefault("edge_cap", "bean")   # ...with the bean cap that engine sewed (default "none" since 2026-10-29)
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


def test_the_bar_and_the_stub_sew_satin():
    on = _runs()
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


def test_with_the_hairline_tier_the_bar_still_sews_satin():
    on = _runs(hairline=True)
    assert stitches.SATIN in {r.kind for r in _of(on, "Sbar")}


def test_small_solids_satin_keeps_every_shape_it_sews():
    # a 0.6 x 3.66 mm bar both rules read, wide enough to sew its own chord
    # on the artwork: small_solids_satin's column, byte for byte
    poly = box(0, 0, 3.66, 0.6)
    assert poly.area < PipelineConfig().min_detail_mm ** 2
    assert _edge(poly) and is_small_solid(poly, 0.4)
    bar = [("Sbar", poly, BLACK)]
    alone = _runs(bar)
    assert stitches.SATIN in {r.kind for r in alone}


def test_a_bar_small_solids_cannot_sew_is_still_a_fine_bar():
    # 0.45 mm across: small_solids reads it but its artwork column is under
    # a cross, so it would ring; the fine bar sews it on stage 5's polygon
    poly = box(0, 0, 4.6, 0.45)
    assert _edge(poly) and is_small_solid(poly, 0.4)
    bar = [("Sbar", poly, BLACK)]
    both = _runs(bar)
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
