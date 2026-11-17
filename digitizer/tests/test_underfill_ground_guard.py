"""A ring that lies ON a ground is no silhouette (`cfg.silhouette_underfill_ground_guard`, ON since 2026-11-16).

The under-fill moves its host's whole thread layer ahead of every colour the
ring holds, on the evidence of the ring alone. On the NASA insignia at 100 mm
the white S, second A and orbit trace as one 330 mm2 shape whose only hole is
the A's 9 mm2 blue counter: it read as a ring, hosted itself, and the white
layer moved ahead of the blue ground it sits on. Every white shape sewed first
and the ground sewed over them (the orbit's left arc buried, six stars gone).

ON, a ring whose host would move ahead of layers that border most of its OUTER
edge reads no ring. A silhouette's outside is garment (MFab, Becker, Fremont
read as before), and a host that does not move is never asked.

The shapes here are synthetic: the insignia itself is not in the repo.
"""
from __future__ import annotations

import hashlib
import json

from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, silhouette_underfill as su
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from tests.conftest import frozen_cfg

FABRIC = fabric_for_garment("hat_front")
BLUE, WHITE = 0, 1


def _reg(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _holed(outer, *holes):
    return Polygon(outer.exterior.coords, [list(h.exterior.coords)[::-1] for h in holes])


def insignia():
    """The insignia's shape: a blue ground in two pieces (the red vector cuts
    the real one), a white weld of letters lying on it, and the weld's one
    small blue counter. The ground sews first today, as it should."""
    weld, counter = box(20, 20, 60, 40), box(38, 28, 42, 32)
    left = box(0, 0, 40, 60).difference(weld)
    right = box(40, 0, 80, 60).difference(weld)
    return [_reg("Sleft", left, BLUE, 0), _reg("Sright", right, BLUE, 0),
            _reg("Scounter", counter, BLUE, 0),
            _reg("Sweld", _holed(weld, counter), WHITE, 1)]


def letters_on_garment(tab=None):
    """The same weld with nothing round it: a silhouette on the garment.
    `tab`: a blue shape touching part of its outer edge."""
    weld, counter = box(20, 20, 60, 40), box(38, 28, 42, 32)
    regs = [_reg("Scounter", counter, BLUE, 0), _reg("Sweld", _holed(weld, counter), WHITE, 1)]
    if tab is not None:
        regs.insert(0, _reg("Stab", tab, BLUE, 0))
    return regs


def mfab():
    """`tests/test_silhouette_underfill.py`'s MFab: the black band moves
    ahead of the white keyline it holds; its outside is garment."""
    l1, l2 = box(5.2, 5.2, 29.4, 18.8), box(30.6, 5.2, 54.8, 18.8)
    return [_reg("Skey", _holed(box(4, 4, 56, 20), l1, l2), 1, 0),
            _reg("Sring", _holed(box(0, 0, 60, 24), box(4, 4, 56, 20)), 0, 1),
            _reg("Sl1", l1, 0, 1), _reg("Sl2", l2, 0, 1)]


def _ids(rings):
    return [(ring.shape_id, host.shape_id, sorted(merged)) for ring, host, _o, merged, _i in rings]


def _sew(regions, cfg):
    if cfg.silhouette_underfill:
        regions, _report, _outlines = su.apply_cfg(regions, [], cfg, None)
    planned, _ = resolve_overlaps(regions, FABRIC, cfg)
    blocks, _ = sequence(planned, FABRIC, cfg)
    return blocks


def _md5(blocks) -> str:
    rows = [[b.thread_index, r.shape_id, r.kind, bool(r.jump), bool(r.trim),
             [[round(x, 4), round(y, 4)] for x, y in r.points]] for b in blocks for r in b.runs]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def test_flag_default_is_on():
    # ON since 2026-11-16 (Kent, from the art | before | after sheets: "Flip ON")
    assert PipelineConfig().silhouette_underfill_ground_guard is True


def test_the_defect_a_weld_on_its_ground_reads_as_a_ring_and_jumps_the_ground():
    """Guard off: the weld hosts itself and the white layer moves ahead of
    the blue -- the ground it lies on."""
    assert _ids(su.plan(insignia())) == [("Sweld", "Sweld", [])]
    out, _ = su.apply(insignia())
    layer = {r.shape_id: r.meta["layer"] for r in out}
    assert layer["Sweld"] < layer["Sleft"] == layer["Sright"] == layer["Scounter"]


def test_on_a_weld_on_its_ground_reads_no_ring():
    regs = insignia()
    assert su.plan(regs, ground_guard=True) == []
    out, report = su.apply(regs, ground_guard=True)
    assert out is regs and report == []


def _share(regs):
    ring, host, _o, _m, inner = su.plan(regs)[0]
    return su._jumped_ground_share(ring, host, inner, regs)


def test_the_measure_is_the_share_of_the_outer_edge_the_jumped_layers_border():
    """The weld's outer edge is 120 mm. The counter is inside it and never
    counts; the touch tolerance adds at most `STRIPE_TOUCH_MM` per end."""
    tol = 4 * su.STRIPE_TOUCH_MM / 120.0
    assert _share(insignia()) == 1.0                                   # wrapped all round
    assert _share(letters_on_garment()) == 0.0                         # garment
    assert abs(_share(letters_on_garment(tab=box(20, 40, 40, 46))) - 20 / 120) <= tol
    cup = box(14, 14, 66, 46).difference(box(20, 20, 60, 46))          # left, bottom, right
    assert abs(_share(letters_on_garment(tab=cup)) - 80 / 120) <= tol
    assert 20 / 120 + tol < su.GROUND_EDGE_MIN < 80 / 120 - tol


def test_a_host_that_would_not_move_reads_zero_whatever_borders_it():
    flipped = [_reg(r.shape_id, r.polygon, r.thread_index, 1 - r.meta["layer"]) for r in insignia()]
    assert _share(flipped) == 0.0


def test_a_silhouette_on_garment_reads_as_before():
    for regs in (mfab(), letters_on_garment()):
        assert _ids(su.plan(regs, ground_guard=True)) == _ids(su.plan(regs))
        on, rep_on = su.apply(regs, ground_guard=True)
        off, rep_off = su.apply(regs)
        assert on == off and rep_on == rep_off and rep_on


def test_a_neighbour_on_a_short_stretch_of_the_edge_is_not_a_ground():
    """A blue tab along 20 of the weld's 120 mm outer edge: under
    `GROUND_EDGE_MIN`, still a silhouette. Along 80 mm of it: a ground."""
    short = letters_on_garment(tab=box(20, 40, 40, 46))
    assert _ids(su.plan(short, ground_guard=True)) == [("Sweld", "Sweld", [])]
    cup = box(14, 14, 66, 46).difference(box(20, 20, 60, 46))    # left, bottom and right edges
    wrapped = letters_on_garment(tab=cup)
    assert su.plan(wrapped, ground_guard=True) == []
    assert _ids(su.plan(wrapped)) == [("Sweld", "Sweld", [])]


def test_a_lettered_ground_inside_a_frame_keeps_its_underfill():
    """The Fremont patch art's shape: a white panel holding a row of black
    letters, a black frame round it, black first in the layer order. The
    frame borders all of the panel's outer edge, and the panel is still the
    silhouette its letters make it (holes over `GROUND_HELD_MAX` of its
    outline): the guard does not ask, and white moves under the black."""
    panel = box(10, 10, 70, 40)
    letters = [box(14 + 9 * i, 16, 20 + 9 * i, 34) for i in range(6)]       # 648 of 1,800 mm2
    # the frame in two pieces, so it is no ring of its own (the art's is cut too)
    halves = [box(4, 4, 40, 46).difference(panel), box(40, 4, 76, 46).difference(panel)]
    regs = ([_reg(f"Sframe{i}", h, BLUE, 0) for i, h in enumerate(halves)]
            + [_reg("Spanel", _holed(panel, *letters), WHITE, 1)]
            + [_reg(f"Sl{i}", p, BLUE, 0) for i, p in enumerate(letters)])
    held = sum(p.area for p in letters) / panel.area
    assert held > su.GROUND_HELD_MAX
    rings = [r for r in su.plan(regs, ground_guard=True) if r[0].shape_id == "Spanel"]
    assert rings and rings == [r for r in su.plan(regs) if r[0].shape_id == "Spanel"]
    ring, host, _o, _m, inner = rings[0]
    assert su._on_jumped_ground(ring, host, inner, regs)          # bordered all round, and kept


def test_a_host_that_does_not_move_is_never_asked():
    """The weld already sews first (layer 0, the blue after it): accepting
    the ring moves nothing, so what borders it is not read."""
    regs = insignia()
    flipped = [_reg(r.shape_id, r.polygon, r.thread_index, 1 - r.meta["layer"]) for r in regs]
    assert _ids(su.plan(flipped, ground_guard=True)) == [("Sweld", "Sweld", [])]


def test_a_refused_ring_leaves_its_shapes_to_another_ring():
    """The guard drops the ring before `used` takes its shapes: a real
    silhouette elsewhere in the design still reads."""
    far = [_reg(r.shape_id + "b", Polygon([(x + 200, y) for x, y in r.polygon.exterior.coords],
                                          [[(x + 200, y) for x, y in h.coords]
                                           for h in r.polygon.interiors]),
                r.thread_index + 2, r.meta["layer"] + 2) for r in mfab()]
    regs = insignia() + far
    assert _ids(su.plan(regs, ground_guard=True)) == [("Sringb", "Sringb", ["Sl1b", "Sl2b"])]


def test_sewn_the_ground_goes_down_first_and_the_weld_on_top():
    """End to end through stage 5 and 7: guard off, white opens the design
    and the blue sews after it; on, blue then white -- the same stitches as
    with the under-fill off, since no ring reads."""
    def order(blocks):
        return [b.thread_index for b in blocks]
    off = _sew(insignia(), frozen_cfg(underlay=False, silhouette_underfill=True))
    on = _sew(insignia(), frozen_cfg(underlay=False, silhouette_underfill=True,
                                     silhouette_underfill_ground_guard=True))
    none = _sew(insignia(), frozen_cfg(underlay=False, silhouette_underfill=False))
    assert order(off).index(WHITE) < order(off).index(BLUE)
    assert order(on).index(BLUE) < order(on).index(WHITE)
    assert _md5(on) == _md5(none) != _md5(off)


def test_on_a_panel_with_riders_reads_as_before():
    """The rider path (`find_riders`, then `apply` with them): a silhouette
    on garment keeps its riders, its panel and its outlines with the guard ON."""
    from tests.test_silhouette_underfill_panels import OUTLINES, panel
    kw = dict(silhouette_underfill=True, sew_enclosed_white=True, silhouette_underfill_panels=True)
    off = su.apply_cfg(panel(), (), PipelineConfig(silhouette_underfill_ground_guard=False, **kw),
                       OUTLINES)
    on = su.apply_cfg(panel(), (), PipelineConfig(silhouette_underfill_ground_guard=True, **kw),
                      OUTLINES)
    assert on == off
    assert any(rep.get("riders") for rep in on[1])


def test_the_flag_alone_changes_nothing_where_no_ring_is_refused():
    base = _sew(mfab(), frozen_cfg(underlay=False, silhouette_underfill=True))
    on = _sew(mfab(), frozen_cfg(underlay=False, silhouette_underfill=True,
                                 silhouette_underfill_ground_guard=True))
    assert _md5(on) == _md5(base)
