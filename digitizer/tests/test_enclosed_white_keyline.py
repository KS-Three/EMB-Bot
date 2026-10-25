"""The keyline band (`cfg.enclosed_white_keyline`, built OFF 2026-10-23).

With `sew_enclosed_white` ON our selection already matches the pro's (32 of
34 bodies, PR #1053); what did not was the CONSTRUCTION of one white keyline
band. MFab's band (868 mm², 17 letter holes, medial width p25 0.72 / p50
1.20 mm) sewed on the satin tier as 253 skeleton columns: 2,181 of its satin
crosses and 522 underlay stitches under 1 mm. The pro sews the band as a
satin loop round each letter, rail on the letter's edge, crosses ~2.1 mm
(`machine.KEYLINE_WIDTH_MM`; his MFab keyline 2.33 median, Becker's 2.09 and
2.06) out across the band and on under the colour sewn after it.

ON (and only with `sew_enclosed_white`'s "field" mark), a field that is a
keyline -- holes, and at least `KEYLINE_REACH_FRAC` of it within that width
of a hole -- sews as those loops, crosses clamped to the band plus what sews
later (`PlannedRegion.covered_by`), never to the bare garment; what the loops
cannot reach is filled first, under them. Anything else is untouched. OFF,
byte-identical (md5 pinned on main's engine, 2d62a373).
"""
from __future__ import annotations

import hashlib
import math

from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_border import keyline_band, keyline_rest
from digitizer_core.stage7_sequence import sequence

OUTER = Polygon([(-17, -9), (17, -9), (17, 9), (-17, 9)])
LEFT = Polygon([(-15, -7), (-1, -7), (-1, 7), (-15, 7)])
RIGHT = Polygon([(1, -7), (15, -7), (15, 7), (1, 7)])
#: two 14 mm letters in a 2 mm white keyline
BAND = Polygon(OUTER.exterior, [LEFT.exterior, RIGHT.exterior])
#: the same band with a 4 x 4 mm tab past the loops' reach
TABBED = Polygon(OUTER.union(Polygon([(17, -2), (21, -2), (21, 2), (17, 2)])).exterior,
                 [LEFT.exterior, RIGHT.exterior])
#: MFab's outer black outline, sewn after the white
RING = Polygon(OUTER.buffer(2.0, join_style=2).exterior, [OUTER.exterior])
#: the OFF md5 of `_plan(BAND)`'s points, captured on main (2d62a373)
OFF_MD5 = "6a116e979bdaff6967d340b70e55d6e2"


def _plan(band: Polygon, field: str | None = "field", later=(LEFT, RIGHT), **cfg_kw):
    meta = {"layer": 0}
    if field:
        meta["sew_enclosed_white"] = field
    reg = Region(shape_id="Sband", polygon=band, thread_index=0, thread_number="0015",
                 area_mm2=band.area, source="test", meta=meta)
    planned = [PlannedRegion(region=reg, polygon=band, sew_index=0,
                             covered_by=unary_union(list(later)) if later else None)]
    for i, poly in enumerate(later):
        lr = Region(shape_id=f"Sletter{i}", polygon=poly, thread_index=1,
                    thread_number="0020", area_mm2=poly.area, source="test",
                    meta={"layer": 1})
        planned.append(PlannedRegion(region=lr, polygon=poly, sew_index=1))
    cfg = PipelineConfig(underlay=False, sew_enclosed_white=True, **cfg_kw)
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"), cfg)
    return [r for b in blocks for r in b.runs if r.shape_id == "Sband"]


def _md5(runs) -> str:
    h = hashlib.md5()
    for r in runs:
        h.update(repr((r.kind, r.jump, r.trim, [(round(x, 6), round(y, 6)) for x, y in r.points])).encode())
    return h.hexdigest()


def _segments(runs, kind=None):
    for r in runs:
        if kind is not None and r.kind != kind:
            continue
        for a, b in zip(r.points, r.points[1:]):
            yield a, b


def test_flag_default_is_on_and_the_width_is_the_pros():
    # Kent 2026-10-24, the flip sheet
    assert PipelineConfig().enclosed_white_keyline is True
    assert machine.KEYLINE_WIDTH_MM == 2.1
    assert machine.KEYLINE_REACH_FRAC == 0.9


def test_off_is_byte_identical_to_main():
    # ON by default since 2026-10-24: False is the engine as it was
    assert _md5(_plan(BAND, enclosed_white_keyline=False)) == OFF_MD5
    assert _md5(_plan(BAND)) != OFF_MD5


def test_a_band_round_letters_is_a_keyline_and_a_letter_body_is_not():
    assert keyline_band(BAND, machine.KEYLINE_WIDTH_MM, machine.KEYLINE_REACH_FRAC)
    # Becker's B: a 5 mm-thick body with two counters reaches nowhere near
    body = Polygon([(0, 0), (20, 0), (20, 30), (0, 30)],
                   [[(5, 5), (15, 5), (15, 12), (5, 12)], [(5, 17), (15, 17), (15, 25), (5, 25)]])
    assert not keyline_band(body, machine.KEYLINE_WIDTH_MM, machine.KEYLINE_REACH_FRAC)
    assert not keyline_band(OUTER, machine.KEYLINE_WIDTH_MM, machine.KEYLINE_REACH_FRAC)


def test_on_one_satin_loop_per_letter_and_no_skeleton_columns():
    off = _plan(BAND, enclosed_white_keyline=False)
    on = _plan(BAND, enclosed_white_keyline=True)
    loops = [r for r in on if r.kind == stitches.SATIN]
    assert len(loops) == 2
    assert not [r for r in on if r.kind == stitches.UNDERLAY]
    # every loop's rail rides its letter's edge
    for r in loops:
        rail = r.points[0::2]
        assert min(min(LEFT.exterior.distance(Point(p)), RIGHT.exterior.distance(Point(p)))
                   for p in rail) < 1e-6
    # not the skeleton: OFF sews this jag-free band as satin columns too, so
    # the sub-1 mm count is read on MFab (PR body), not on a synthetic ring
    assert [r for r in off if r.kind == stitches.SATIN]


def test_on_crosses_are_the_pro_width_under_the_letters_never_on_bare_garment():
    on = _plan(BAND, later=(LEFT, RIGHT, RING), enclosed_white_keyline=True)
    reach = BAND.union(LEFT).union(RIGHT).union(RING).buffer(1e-3)
    crosses = []
    for a, b in _segments(on, stitches.SATIN):
        assert reach.covers(LineString([a, b]))
        crosses.append(math.dist(a, b))
    crosses.sort()
    med = crosses[len(crosses) // 2]
    assert abs(med - machine.KEYLINE_WIDTH_MM) < 0.15
    # the 2 mm band alone would have clamped every cross to <= 2 mm
    assert med > 2.0


def test_on_a_cross_stops_at_bare_garment():
    # no outline sewn after the white: the outer crosses clamp to the band
    on = _plan(BAND, enclosed_white_keyline=True)
    reach = BAND.union(LEFT).union(RIGHT).buffer(1e-3)
    for a, b in _segments(on, stitches.SATIN):
        assert reach.covers(LineString([a, b]))


def test_on_with_nothing_sewn_later_the_crosses_stay_in_the_band():
    on = _plan(BAND, later=(), enclosed_white_keyline=True)
    slack = BAND.buffer(1e-3)
    for a, b in _segments(on, stitches.SATIN):
        assert slack.covers(LineString([a, b]))


def test_on_the_part_no_loop_reaches_is_filled_first_under_them():
    rest = keyline_rest(TABBED, machine.KEYLINE_WIDTH_MM, 0.25, machine.MIN_FILL_WIDTH_MM)
    assert len(rest) == 1 and rest[0].area > 12.0
    assert keyline_rest(BAND, machine.KEYLINE_WIDTH_MM, 0.25, machine.MIN_FILL_WIDTH_MM) == []
    on = _plan(TABBED, enclosed_white_keyline=True)
    kinds = [r.kind for r in on if r.kind != stitches.TRAVEL]
    first_loop = kinds.index(stitches.SATIN)
    assert stitches.FILL in kinds[:first_loop]
    assert stitches.FILL not in kinds[first_loop:]


def test_on_reads_only_sew_enclosed_whites_fields():
    for field in (None, "counter", "counter_in_field"):
        a = _plan(BAND, field=field, enclosed_white_keyline=False)
        b = _plan(BAND, field=field, enclosed_white_keyline=True)
        assert _md5(a) == _md5(b)


def test_on_a_per_shape_tier_still_wins():
    reg_tier = {"tier": "fill"}
    meta = {"layer": 0, "sew_enclosed_white": "field", **reg_tier}
    reg = Region(shape_id="Sband", polygon=BAND, thread_index=0, thread_number="0015",
                 area_mm2=BAND.area, source="test", meta=meta)
    def run(**kw):
        planned = [PlannedRegion(region=reg, polygon=BAND, sew_index=0)]
        blocks, _ = sequence(planned, fabric_for_garment("hat_front"),
                             PipelineConfig(underlay=False, sew_enclosed_white=True, **kw))
        return [r for b in blocks for r in b.runs]
    assert _md5(run()) == _md5(run(enclosed_white_keyline=True))


def test_on_with_satin_underlay_each_loop_walks_its_centre_first():
    from digitizer_core.stage6_border import keyline_runs
    runs, rep = keyline_runs(BAND, "Sband", reach=BAND.union(LEFT).union(RIGHT).union(RING),
                             entry=None, trim_at_mm=3.0, underlay=True)
    kinds = [r.kind for r in runs if r.kind != stitches.TRAVEL]
    assert kinds == [stitches.UNDERLAY, stitches.SATIN] * 2 and rep["loops"] == 2
    for u, s in zip(runs, runs[1:]):
        if u.kind == stitches.UNDERLAY:
            assert s.kind == stitches.SATIN
            assert math.dist(u.points[-1], s.points[0]) < 1e-9
            # the centre run sits about half a column off the letter's edge
            mid = u.points[len(u.points) // 2]
            d = min(LEFT.exterior.distance(Point(mid)), RIGHT.exterior.distance(Point(mid)))
            assert abs(d - machine.KEYLINE_WIDTH_MM / 2) < 0.3


def test_on_two_unreached_parts_each_fill_under_the_loops():
    two = Polygon(OUTER.union(Polygon([(17, -1.5), (20, -1.5), (20, 1.5), (17, 1.5)]))
                  .union(Polygon([(-20, -1.5), (-17, -1.5), (-17, 1.5), (-20, 1.5)])).exterior,
                  [LEFT.exterior, RIGHT.exterior])
    assert len(keyline_rest(two, machine.KEYLINE_WIDTH_MM, 0.25, machine.MIN_FILL_WIDTH_MM)) == 2
    assert keyline_band(two, machine.KEYLINE_WIDTH_MM, machine.KEYLINE_REACH_FRAC)
    on = _plan(two, enclosed_white_keyline=True)
    kinds = [r.kind for r in on if r.kind != stitches.TRAVEL]
    first_loop = kinds.index(stitches.SATIN)
    assert stitches.FILL in kinds[:first_loop] and kinds.count(stitches.SATIN) == 2


def test_on_the_loops_ride_the_artwork_not_stage5s_grown_polygon():
    # stage 5 grows the first-sewn band under every letter (on MFab its sewing
    # polygon held 224 holes, slivers of the letters); the loops read the art
    grown = Polygon(OUTER.exterior, [LEFT.buffer(-1.0).exterior, RIGHT.buffer(-1.0).exterior])
    meta = {"layer": 0, "sew_enclosed_white": "field"}
    reg = Region(shape_id="Sband", polygon=BAND, thread_index=0, thread_number="0015",
                 area_mm2=BAND.area, source="test", meta=meta)
    planned = [PlannedRegion(region=reg, polygon=grown, sew_index=0,
                             covered_by=unary_union([LEFT, RIGHT, RING]))]
    blocks, _ = sequence(planned, fabric_for_garment("hat_front"),
                         PipelineConfig(underlay=False, sew_enclosed_white=True,
                                        enclosed_white_keyline=True))
    loops = [r for b in blocks for r in b.runs if r.kind == stitches.SATIN]
    assert len(loops) == 2
    for r in loops:
        assert min(min(LEFT.exterior.distance(Point(q)), RIGHT.exterior.distance(Point(q)))
                   for q in r.points[0::2]) < 1e-6
