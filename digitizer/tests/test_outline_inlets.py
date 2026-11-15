"""`cfg.outline_inlets_kept` (built OFF 2026-11-14 in `cfg.extra`; ON since 2026-11-15,
Kent's tick "K-Line box + gear flags"): a shape's own
outline inlets -- a gear's tooth gaps, an open beak, a notch -- are kept open
at stitch time (`digitizer_core.outline_inlets`). Kent's "shape detail lost"
pins, traced in `docs/shape-detail-traced-2026-11-14.md`.

Every test reads WHERE thread goes; the pull itself (gate 1) is untouched.
False is the engine as it was; `_plan` below runs OFF unless a test asks for ON.
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import Point, Polygon, box

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core import outline_inlets as oi
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stitches import FILL, SATIN, StitchBlock, StitchPlan, StitchRun

PIQUE = get_fabric("pique_knit")          # 0.30 mm pull


def _r(poly, sid, thread=0, layer=0, **meta) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(1000 + thread),
                  area_mm2=float(poly.area), meta={"layer": layer, **meta})


def _notched_disc():
    """A 6 mm disc with a 0.8 mm slot cut 2 mm in from its edge (music's notch)."""
    disc = Point(0, 0).buffer(3.0, quad_segs=32)
    slot = box(1.0, -0.4, 3.5, 0.4)
    return disc.difference(slot)


def _gear(teeth=12, r_root=3.0, r_tip=3.8, r_hole=2.0):
    """A ring with square-ish teeth, half the pitch each (Ahora's gear)."""
    pts = []
    for k in range(teeth):
        a0 = 2 * math.pi * k / teeth
        a1 = a0 + math.pi / teeth
        for a, r in ((a0, r_root), (a0, r_tip), (a1, r_tip), (a1, r_root)):
            pts.append((r * math.cos(a), r * math.sin(a)))
    shell = Polygon(pts)
    return Polygon(shell.exterior, [Point(0, 0).buffer(r_hole, quad_segs=32).exterior.coords])


def _plan(regions, outline_inlets_kept=False):
    c = PipelineConfig(overlap_mm=0.25, outline_inlets_kept=outline_inlets_kept)
    planned, _w = resolve_overlaps(regions, PIQUE, c)
    return {p.region.shape_id: p.polygon for p in planned}


def _md5(planned) -> str:
    h = hashlib.md5()
    for sid in sorted(planned):
        h.update(sid.encode())
        h.update(planned[sid].wkb)
    return h.hexdigest()


def test_inlets_are_the_outline_notches_not_corners_or_counters():
    assert oi.inlets(box(0, 0, 5, 3)) == []                       # square corners: fillets only
    assert oi.inlets(Point(0, 0).buffer(3.0)) == []
    ring = Point(0, 0).buffer(3.0).difference(Point(0, 0).buffer(1.5))
    assert oi.inlets(ring) == []                                  # a counter is not an inlet
    notch = oi.inlets(_notched_disc())
    assert len(notch) == 1 and 0.5 <= oi.inscribed_width(notch[0]) <= 0.85
    gaps = oi.inlets(_gear())
    assert len(gaps) == 12                                        # one per tooth gap


def test_on_by_default_and_a_shape_with_no_inlet_does_not_move():
    assert PipelineConfig().outline_inlets_kept is True
    def scene():
        return [_r(box(0, -3, 3, 3), "D", tier="fill", fill_angle_deg=0.0),
                _r(box(4, -3, 9, 3), "B", thread=1, layer=1, tier="fill", fill_angle_deg=90.0)]
    assert _md5(_plan(scene(), outline_inlets_kept=True)) == _md5(_plan(scene()))


def test_a_fills_growth_keeps_out_of_its_own_notch():
    art = _notched_disc()
    slot = oi.inlets(art)[0]
    off = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0)])["D"]
    on = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0)], outline_inlets_kept=True)["D"]
    # OFF the pull grows in from both walls and closes the 0.8 mm slot
    assert off.intersection(slot).area > 0.6 * slot.area
    # ON the slot is bare; the rest of the shape still grows
    assert on.intersection(slot).area < 0.02 * slot.area
    # and its mouth: the growth band round the disc does not weld it shut
    mouth = Point(3.1, 0.25)
    assert off.covers(mouth) and not on.covers(mouth)
    assert on.covers(art.buffer(-1e-6))
    assert on.area > art.area + 1.0


def test_an_inlet_another_colour_fills_is_not_bare():
    art = _notched_disc()
    plug = box(1.0, -0.4, 3.5, 0.4)
    planned = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0),
                     _r(plug, "P", thread=1, layer=1, tier="fill", fill_angle_deg=0.0)],
                    outline_inlets_kept=True)
    off = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0),
                 _r(plug, "P", thread=1, layer=1, tier="fill", fill_angle_deg=0.0)])
    assert _md5(planned) == _md5(off)


def _satin_plan(sid, pts):
    run = StitchRun(points=pts, kind=SATIN, shape_id=sid)
    return StitchPlan(blocks=[StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0), runs=[run])],
                      palette=[])


def _zigzag_over(poly, n=200):
    """A satin-like zigzag from the centre to the outer TIP radius all round:
    the scalloped column that sews over every tooth gap."""
    pts = []
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 2.0 if k % 2 else 3.8
        pts.append((r * math.cos(a), r * math.sin(a)))
    return pts


def test_a_satin_over_its_tooth_gaps_is_named_and_a_letter_never_is():
    gear = _gear()
    plan = _satin_plan("G", _zigzag_over(gear))
    over = oi.satin_over_inlets([_r(gear, "G")], plan)
    assert set(over) == {"G"} and over["G"] >= oi.SATIN_OVER_INLET_SHARE
    assert oi.satin_over_inlets([_r(gear, "G", text_candidate=True)], plan) == {}
    assert oi.satin_over_inlets([_r(gear, "G", tier="satin")], plan) == {}


def test_a_satin_that_keeps_to_its_root_is_left_alone():
    gear = _gear()
    pts = []
    for k in range(200):
        a = 2 * math.pi * k / 200
        r = 2.0 if k % 2 else 2.95                               # stops at the root circle
        pts.append((r * math.cos(a), r * math.sin(a)))
    assert oi.satin_over_inlets([_r(gear, "G")], _satin_plan("G", pts)) == {}
    # a fill run is not a satin column
    fill = StitchPlan(blocks=[StitchBlock(0, "1000", (0, 0, 0),
                                          [StitchRun(points=_zigzag_over(gear), kind=FILL, shape_id="G")])],
                      palette=[])
    assert oi.satin_over_inlets([_r(gear, "G")], fill) == {}


def test_a_wide_band_whose_satin_crosses_one_small_dip_is_left_alone():
    # Becker's black border: inlets 0.2% of its area; the pro sews it as a
    # satin band too. One 0.8 x 1 mm dip in a 40 x 6 mm band, sewn over.
    band = box(0, 0, 40, 6).difference(box(20, 5, 20.8, 6))
    assert len(oi.inlets(band)) == 1
    pts = [(x * 0.2, 0.0 if k % 2 else 6.0) for k, x in enumerate(range(200))]
    assert oi.satin_over_inlets([_r(band, "B")], _satin_plan("B", pts)) == {}


def test_a_letters_notch_is_the_lettering_lanes():
    art = _notched_disc()
    off = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0, text_candidate=True)])
    on = _plan([_r(art, "D", tier="fill", fill_angle_deg=90.0, text_candidate=True)], outline_inlets_kept=True)
    assert _md5(on) == _md5(off)


def test_a_toothed_ring_splits_into_its_body_and_one_piece_per_tooth():
    gear = _gear()                                   # 12 teeth, root 3.0, tips 3.8, hole 2.0
    body, teeth = oi.tooth_split(_r(gear, "G"))
    assert len(teeth) == 12
    assert body.shape_id == "G" and len(body.polygon.interiors) == 1
    assert body.polygon.buffer(1e-6).contains(Point(0, 0).buffer(2.95).difference(Point(0, 0).buffer(2.05)))
    for t in teeth:
        assert t.shape_id.startswith("G-t") and t.meta["tier"] == "fill"
        assert t.meta[oi.TOOTH_OF_KEY] == "G"
        # rows square to the tooth's own (radial) axis: tangential
        c = t.polygon.centroid
        radial = math.degrees(math.atan2(c.y, c.x)) % 180.0
        d = abs((t.meta["fill_angle_deg"] - radial) % 180.0 - 90.0)
        assert d < 12.0
        # the tooth reaches under the body, down its own axis
        assert t.polygon.intersection(body.polygon).area > 0.0
    # the teeth come first, then the body, in turn round the shape
    assert [t.meta["sew_order"] for t in teeth] == list(range(12)) and body.meta["sew_order"] == 12


def test_a_notch_or_a_mouth_is_not_a_row_of_teeth():
    assert oi.tooth_split(_r(_notched_disc(), "D")) is None
    assert oi.tooth_split(_r(box(0, 0, 10, 4), "B")) is None


def test_rebuild_splits_toothed_shapes_and_fills_the_rest():
    regs = [_r(_gear(), "G"), _r(_notched_disc(), "D"), _r(box(20, 0, 22, 2), "X")]
    out, bodies = oi.rebuild(regs, {"G", "D"}, teeth=True)
    ids = [r.shape_id for r in out]
    assert set(bodies) == {"G"}
    assert ids.count("G") == 1 and sum(i.startswith("G-t") for i in ids) == 12
    assert next(r for r in out if r.shape_id == "D").meta["tier"] == "fill"
    assert next(r for r in out if r.shape_id == "X") is regs[2]
    out2, bodies2 = oi.rebuild(regs, {"G", "D"}, teeth=False)
    assert bodies2 == {} and all(r.meta.get("tier") == "fill" for r in out2 if r.shape_id in ("G", "D"))


def test_a_jump_between_teeth_is_sewn_along_the_root_and_a_trim_is_left():
    gear = _gear()
    body, teeth = oi.tooth_split(_r(gear, "G"))
    a = teeth[0].polygon.centroid
    b = teeth[1].polygon.centroid
    r0 = StitchRun(points=[(a.x, a.y)], kind=FILL, shape_id="G-t0")
    r1 = StitchRun(points=[(b.x, b.y), (b.x + 0.1, b.y)], kind=FILL, shape_id="G-t1", jump=True)
    r2 = StitchRun(points=[(0.0, 2.5)], kind=FILL, shape_id="G-t2", jump=True, trim=True)
    other = StitchRun(points=[(9.0, 9.0)], kind=FILL, shape_id="Z", jump=True)
    plan = StitchPlan(blocks=[StitchBlock(0, "1000", (0, 0, 0), [r0, r1, r2, other])], palette=[])
    assert oi.bury_tooth_moves(plan, {"G": body.polygon}, 0.5) == 1
    assert not r1.jump and len(r1.points) > 2
    # the buried path runs inside the body, just in from its outer edge
    for p in r1.points[:-2]:
        assert body.polygon.buffer(0.05).covers(Point(p))
    assert r2.jump and r2.trim and other.jump        # a trim and another shape's jump stay


def test_as_fill_moves_only_the_named_shapes_on_copies():
    a, b = _r(box(0, 0, 1, 1), "A"), _r(box(2, 0, 3, 1), "B")
    out = oi.as_fill([a, b], {"A"})
    assert out[0].meta["tier"] == "fill" and out[0] is not a
    assert out[1] is b and "tier" not in a.meta
