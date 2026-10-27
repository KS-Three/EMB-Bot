"""`cfg.extra["absorb_fragments"]` (built OFF 2026-10-25): a fragment
narrower than the pro's narrowest sewn satin column, lying within one thread
of a sewn body of its own thread, is sewn as part of that body.

Measured on MFab hat with `sew_enclosed_white` ON
(`docs/isolated-pieces-2026-10-25.md`): 30 white keyline fragments, 16 of
the job's 77 trims cut fragment to fragment. Here, on hand-built shapes: who
is a fragment, who is a body, what the union adds, and that OFF is the plan
as it was.
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import replace

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig
from digitizer_core import fragment_absorb as fa
from digitizer_core.pipeline import BackgroundInfo, PipelineResult, plan_stitches
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.threads import chart_for
from tests.conftest import frozen_cfg

ON = frozen_cfg(extra={fa.KEY: True})
OFF = frozen_cfg()

# a white keyline band (thread 1) round a black body (thread 0); white
# slivers 0.4 mm wide lie 0.15 mm inside the band's inner edge, on the black
BAND = box(-20, -10, 20, 10).difference(box(-16, -6, 16, 6))
BODY = box(-16, -6, 16, 6)


def _r(name, poly, thread, layer, **meta):
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=f"{1000 + thread}", area_mm2=poly.area,
                  meta={"layer": layer, "stitched": True, **meta})


def _sliver(x0, gap=0.15, w=0.4, length=3.0):
    return box(x0, -6 + gap, x0 + length, -6 + gap + w)


def _design(**sliver_meta):
    return [_r("Sbody", BODY, 0, 0), _r("Sband", BAND, 1, 1),
            *[_r(f"Sfrag{i}", _sliver(x), 1, 1, **sliver_meta) for i, x in enumerate((-10.0, 0.0, 8.0))]]


def _planned(regions, grow=0.0):
    """Stage 5's shape of things: each region planned, its sewing polygon
    `grow` mm past the artwork (pull compensation's place)."""
    return [PlannedRegion(region=r, polygon=r.polygon.buffer(grow, join_style=2) if grow else r.polygon,
                          sew_index=r.thread_index, visible=r.polygon) for r in regions]


def _absorb(regions, cfg):
    """`fa.absorb` on `_planned(regions)`, read back as regions."""
    return [p.region for p in fa.absorb(_planned(regions), cfg)]


def _ids(regions):
    return [r.shape_id for r in regions]


# --- who is absorbed ---------------------------------------------------------

def test_off_returns_the_list_itself():
    planned = _planned(_design())
    assert fa.absorb(planned, OFF) is planned


def test_on_only_the_body_and_its_fragments_change():
    """Every other planned entry is stage 5's own object, untouched; the
    body's artwork AND sewing polygons both take the fragments in."""
    planned = _planned(_design(rescued_small_shape=True), grow=0.1)
    out = fa.absorb(planned, ON)
    assert out[0] is planned[0]                       # the black body, as stage 5 left it
    band = out[1]
    for f in planned[2:]:
        assert band.region.polygon.buffer(1e-6).covers(f.region.polygon)
        assert band.polygon.buffer(1e-6).covers(f.polygon)
        assert band.visible.buffer(1e-6).covers(f.visible)
    assert band.sew_index == planned[1].sew_index
    assert planned[1].region.polygon.equals(BAND)   # the input is untouched


def test_slivers_beside_their_band_join_it():
    regions = _design(rescued_small_shape=True)
    out = _absorb(regions, ON)
    assert _ids(out) == ["Sbody", "Sband"]
    band = out[1]
    assert band.meta["absorbed_fragments"] == ["Sfrag0", "Sfrag1", "Sfrag2"]
    assert band.polygon.geom_type == "Polygon"
    for r in regions[2:]:
        assert band.polygon.buffer(1e-6).covers(r.polygon)
    # the union adds the slivers and the 0.15 mm gaps beside them, little else
    added = band.area_mm2 - BAND.area - sum(r.area_mm2 for r in regions[2:])
    assert 0 < added < 3 * (3.0 + 2 * 0.4) * 0.4
    # the input is untouched: the band in `regions` is the band as drawn
    assert regions[1].polygon.equals(BAND) and "absorbed_fragments" not in regions[1].meta


def test_another_thread_is_not_absorbed():
    regions = [_r("Sbody", BODY, 0, 0), _r("Sband", BAND, 1, 1), _r("Sfrag", _sliver(0.0), 2, 1)]
    assert _ids(_absorb(regions, ON)) == _ids(regions)


def test_a_gap_wider_than_a_thread_is_not_closed():
    regions = [_r("Sband", BAND, 1, 1), _r("Sfrag", _sliver(0.0, gap=fa.FRAGMENT_REACH_MM + 0.1), 1, 1)]
    assert _ids(_absorb(regions, ON)) == _ids(regions)


def test_a_shape_the_pro_could_sew_as_a_column_is_not_a_fragment():
    wide = _sliver(0.0, w=fa.PRO_MIN_SWING_MM + 0.1)
    regions = [_r("Sband", BAND, 1, 1), _r("Sfrag", wide, 1, 1)]
    assert _ids(_absorb(regions, ON)) == _ids(regions)
    narrow = _sliver(0.0, w=fa.PRO_MIN_SWING_MM - 0.1)
    assert _ids(_absorb([_r("Sband", BAND, 1, 1), _r("Sfrag", narrow, 1, 1)], ON)) == ["Sband"]


@pytest.mark.parametrize("key", ["text_cluster_id", "lettering_group", "word_id", "bean_letter"])
def test_lettering_is_never_a_fragment_nor_a_body(key):
    regions = [_r("Sband", BAND, 1, 1), _r("Sfrag", _sliver(0.0), 1, 1, **{key: "T1"})]
    assert _ids(_absorb(regions, ON)) == _ids(regions)
    regions = [_r("Sband", BAND, 1, 1, **{key: "T1"}), _r("Sfrag", _sliver(0.0), 1, 1)]
    assert _ids(_absorb(regions, ON)) == _ids(regions)


def test_a_hair_walled_in_by_the_join_is_filled_a_real_hole_is_not():
    """A C-shaped fragment opening onto the band walls in a pocket of the
    colour beneath. Narrower than the pro's narrowest column, it is not a
    hole (left open, stage 5 cuts the same ring out of the colour beneath and
    re-sections its fill); the band's own holes survive untouched."""
    from shapely.geometry import Polygon as P
    # a 0.4 mm wide U whose arms end 0.15 mm off the band's inner edge (y=-6):
    # the pocket it walls in is 0.4 mm tall
    u = box(0.0, -5.6, 3.0, -5.2).union(box(0.0, -5.85, 0.4, -5.2)).union(box(2.6, -5.85, 3.0, -5.2))
    out = _absorb([_r("Sband", BAND, 1, 1), _r("Sfrag", u, 1, 1)], ON)
    (band,) = out
    # the band's one own hole (the black body's square) is still there, as it was
    assert len(band.polygon.interiors) == 1
    assert P(band.polygon.interiors[0]).buffer(1e-6).covers(P(BAND.interiors[0]).difference(u.convex_hull.buffer(0.3)))
    # a wide pocket (a 2 mm U) stays a hole
    wide = box(0.0, -3.0, 3.0, -2.6).union(box(0.0, -5.85, 0.4, -2.6)).union(box(2.6, -5.85, 3.0, -2.6))
    (band,) = _absorb([_r("Sband", BAND, 1, 1), _r("Sfrag", wide, 1, 1)], ON)
    assert len(band.polygon.interiors) == 2


# --- the panel under the riders (MFab, 2026-10-26) ---------------------------

def _rings(poly):
    return [Polygon(r).exterior.wkb for r in poly.interiors]


def test_the_bodys_own_holes_keep_their_rings():
    """Later passes match a body's holes by WKB (stage 7's rider holes,
    `outline_holes`' widths): a hole the join leaves alone keeps its ring,
    vertex for vertex."""
    band = box(-30, -10, 30, 10).difference(box(-16, -6, -2, 6)).difference(box(2, -6, 16, 6))
    outside = box(-5.0, 10.15, 5.0, 10.55)       # a sliver on the band's outer edge
    (got,) = _absorb([_r("Sband", band, 1, 1), _r("Sfrag", outside, 1, 1)], ON)
    assert got.meta["absorbed_fragments"] == ["Sfrag"]
    assert sorted(_rings(got.polygon)) == sorted(_rings(band))


def test_a_fragment_inside_a_rider_hole_leaves_every_piece_the_panels():
    """MFab LC: white fragments lie inside the panel the riders sit in (a
    `RIDER_HOLES_KEY` hole stage 7 closes and fills). Joined to the field, one
    split the panel, and the pieces were looped instead of filled -- bare
    garment in the riders' counters. Every hole of the joined field inside a
    rider hole is still a rider hole, by the ring stage 7 compares."""
    from digitizer_core.silhouette_underfill import RIDER_HOLES_KEY
    panel = Polygon(BAND.interiors[0])
    across = box(-15.85, -0.2, 15.85, 0.2)          # a sliver right across the panel, 0.15 mm off both sides
    (got,) = _absorb([_r("Sband", BAND, 1, 1, **{RIDER_HOLES_KEY: [panel]}),
                      _r("Sfrag", across, 1, 1)], ON)
    assert got.meta["absorbed_fragments"] == ["Sfrag"]
    assert len(got.polygon.interiors) == 2                      # the panel, split in two
    assert sorted(h.exterior.wkb for h in got.meta[RIDER_HOLES_KEY]) == sorted(_rings(got.polygon))
    # stage 7's own test closes both: none of the joined field's holes is left to loop
    ridden = {h.exterior.wkb for h in got.meta[RIDER_HOLES_KEY]}
    assert not [r for r in got.polygon.interiors if Polygon(r).exterior.wkb not in ridden]


def test_a_hole_that_is_no_riders_stays_out_of_the_panel():
    from digitizer_core.silhouette_underfill import RIDER_HOLES_KEY
    band = box(-30, -10, 30, 10).difference(box(-16, -6, -2, 6)).difference(box(2, -6, 16, 6))
    rider, letter = (Polygon(r) for r in band.interiors)
    if not rider.intersects(box(-16, -6, -2, 6)):
        rider, letter = letter, rider
    edge = box(-15.85, -0.2, -2.15, 0.2)            # inside the rider hole, 0.15 mm off both sides
    (got,) = _absorb([_r("Sband", band, 1, 1, **{RIDER_HOLES_KEY: [rider]}),
                      _r("Sfrag", edge, 1, 1)], ON)
    ridden = {h.exterior.wkb for h in got.meta[RIDER_HOLES_KEY]}
    assert len(ridden) == 2                                    # the rider hole's two pieces
    assert Polygon(letter.exterior).exterior.wkb not in ridden   # the letter's hole, as it was, loops
    assert letter.exterior.wkb in {Polygon(r).exterior.wkb for r in got.polygon.interiors}


def test_two_rescued_specks_do_not_grow_a_body():
    """Fremont has clusters of 26 rescued specks a hair apart: a speck wide
    enough to be a body must not swallow its neighbours one by one."""
    speck = _r("Sspeck", box(0, 0, 1.2, 1.2), 1, 1, rescued_small_shape=True)
    frag = _r("Sfrag", box(1.3, 0, 1.6, 1.2), 1, 1, rescued_small_shape=True)
    assert _ids(_absorb([speck, frag], ON)) == ["Sspeck", "Sfrag"]


def test_the_constants_are_the_census_and_the_thread():
    from tools import sequence_pro as sp
    assert fa.FRAGMENT_REACH_MM == sp.THREAD_MM
    assert fa.PRO_MIN_SWING_MM == 0.70


# --- through the plan --------------------------------------------------------

def _plan(cfg):
    chart = chart_for(cfg)
    regions = [replace(r, thread_number=chart[r.thread_index].number) for r in _design(rescued_small_shape=True)]
    palette = [{"brand": chart.label, "brand_id": chart.id, "number": chart[i].number,
                "name": f"t{i}", "rgb": rgb} for i, rgb in ((0, [0, 0, 0]), (1, [255, 255, 255]))]
    return plan_stitches(PipelineResult(regions=regions, palette=palette,
                                        background=BackgroundInfo(detected=False), px_per_mm=10.0,
                                        design_size_mm=(40.0, 20.0)), cfg)


def _md5(plan) -> str:
    rows = [[b.thread_index, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                              for r in b.runs for x, y in r.points]] for b in plan.blocks]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _shapes(plan):
    return {r.shape_id for b in plan.blocks for r in b.runs}


def test_on_the_slivers_are_sewn_as_the_band():
    off, on = _plan(OFF), _plan(ON)
    assert {"Sfrag0", "Sfrag1", "Sfrag2"} <= _shapes(off)
    assert not ({"Sfrag0", "Sfrag1", "Sfrag2"} & _shapes(on))
    assert on.stats.trims < off.stats.trims


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("absorb_fragments code reached with the flag off")
    monkeypatch.setattr(fa, "_narrow", boom)
    monkeypatch.setattr(fa, "_merge", boom)
    _plan(OFF)


# Captured on origin/main b19dee77, which has no `fragment_absorb` (the same
# fixture planned by that tree's `plan_stitches`). First captured on
# 7995d515 (93082348...); #1057's flips moved the base plan, not this flag.
# Re-captured 2026-10-26 on main 5cf8da43: #1112 / #1121's flips moved it
# (e16ecce0...); with `fine_bars_satin`, `small_text_bay_mouth`,
# `sew_enclosed_white` and `outline_loop_mitre` off it still reads e16ecce0.
OFF_MD5 = "3717378ff2c67ebdb8de5364d26e9a92"


def test_off_is_the_plan_without_the_pass(monkeypatch):
    """Platform-safe: OFF equals the flag ON with its pass stubbed to the
    identity, so the flag's only effect is the pass. The cross-commit pin is
    asserted where it was captured (`test_cut_every_jump`'s pattern)."""
    off = _md5(_plan(OFF))
    if sys.platform == "win32":
        assert off == OFF_MD5
    monkeypatch.setattr(fa, "absorb", lambda planned, cfg, *_a: planned)
    assert _md5(_plan(ON)) == off


def test_a_hairline_strand_is_the_hairline_tiers():
    """A strand (`cfg.hairline`'s set) is narrow by design: neither it nor a
    shape that tier handed back to the ground is a fragment here."""
    from digitizer_core.stage6_hairline import HairlineSet
    planned = _planned([_r("Sband", BAND, 1, 1), _r("Sfrag", _sliver(0.0), 1, 1)])
    strands = HairlineSet({"Sfrag": 1.0})
    assert [p.region.shape_id for p in fa.absorb(planned, ON, strands)] == ["Sband", "Sfrag"]
    handed_back = HairlineSet()
    handed_back.fragments = {"Sfrag"}
    assert [p.region.shape_id for p in fa.absorb(planned, ON, handed_back)] == ["Sband", "Sfrag"]
    assert [p.region.shape_id for p in fa.absorb(planned, ON, None)] == ["Sband"]
