"""The pro's silhouette under-fill (`cfg.silhouette_underfill`, built OFF 2026-10-24).

Read per colour block (`tools/tier_census.py`, L9): on MFab hat the pro's
black covers our band 1.00 and its holes 0.82 -- one fill of the band's
outline, white keyline on top; on the Becker beanie his letter colour covers
0.91 of the BECKER silhouette, 0.74 of our ring, and the ring is satin on top.
ON, a ring whose holes hold other shapes gets its outline (holes closed)
filled once, underneath, in the colour that dominates the holes; the ring and
its contents sew on top, and inner shapes of the under-fill's colour merge
into it. Off, byte-identical (md5 pinned against origin/main d184fd68).
"""
from __future__ import annotations

import hashlib
import json

from shapely.geometry import Polygon, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, silhouette_underfill as su, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from tests.conftest import FLIP_2026_10_23, FLIP_2026_10_27

FABRIC = fabric_for_garment("hat_front")


def _reg(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(4000 + thread),
                  area_mm2=poly.area, source="test", meta={"layer": layer, **meta})


def _holed(outer, *holes):
    return Polygon(outer.exterior.coords, [list(h.exterior.coords)[::-1] for h in holes])


def mfab():
    """MFab's shape: a black band round a thin white keyline round black
    letters; white sews first today."""
    l1, l2 = box(5.2, 5.2, 29.4, 18.8), box(30.6, 5.2, 54.8, 18.8)
    return [_reg("Skey", _holed(box(4, 4, 56, 20), l1, l2), 1, 0),
            _reg("Sring", _holed(box(0, 0, 60, 24), box(4, 4, 56, 20)), 0, 1),
            _reg("Sl1", l1, 0, 1), _reg("Sl2", l2, 0, 1)]


def becker():
    """Becker's shape with `sew_enclosed_white`: white letters in the holes
    of a black ring, the white in its front layer."""
    b1, b2 = box(4, 4, 29, 20), box(32, 4, 56, 20)
    return [_reg("Sb1", b1, 1, 0), _reg("Sb2", b2, 1, 0),
            _reg("Sring", _holed(box(0, 0, 60, 24), b1, b2), 0, 1)]


def _sew(regions, **kw):
    """`plan_stitches`' order: the pass (ON), stage 5, stage 7."""
    # OFF_MD5 was captured on main before the 2026-10-23 and 2026-10-27 flips: pin them off (conftest)
    cfg = PipelineConfig(underlay=False, **{**FLIP_2026_10_23, **FLIP_2026_10_27, **kw})
    if cfg.silhouette_underfill:
        regions, _ = su.apply(regions)
    planned, _ = resolve_overlaps(regions, FABRIC, cfg)
    blocks, _ = sequence(planned, FABRIC, cfg)
    return planned, blocks


def _md5(blocks) -> str:
    rows = [[b.thread_index, r.shape_id, r.kind, bool(r.jump), bool(r.trim),
             [[round(x, 4), round(y, 4)] for x, y in r.points]] for b in blocks for r in b.runs]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


# Captured on origin/main d184fd68 (before this flag) with tools' pin2 script.
OFF_MD5 = {"mfab": "65da8df6f52b38595bf511d4a3cf5f5c", "becker": "73e9fc7eb9d781b86f2f503f647d366f"}


def test_flag_default_is_on():
    # ON since the recipe went to every job (Kent 2026-10-27, "Every job (Recommended)")
    assert PipelineConfig().silhouette_underfill is True


def test_off_is_byte_identical_to_main():
    assert _md5(_sew(mfab())[1]) == OFF_MD5["mfab"]
    assert _md5(_sew(becker())[1]) == OFF_MD5["becker"]


def test_mfab_the_ring_becomes_the_underfill_and_its_letters_merge():
    rings = su.plan(mfab())
    assert len(rings) == 1
    ring, host, outline, merged, _inner = rings[0]
    assert ring.shape_id == host.shape_id == "Sring"
    assert merged == ["Sl1", "Sl2"]
    assert abs(outline.area - 60 * 24) < 1e-6
    out, report = su.apply(mfab())
    ids = {r.shape_id: r for r in out}
    assert "Sl1" not in ids and "Sl2" not in ids
    assert ids["Sring"].meta["tier"] == "fill"
    # black now sews before the white keyline -- the reverse of today's order
    assert ids["Sring"].meta["layer"] < ids["Skey"].meta["layer"]
    assert report[0]["host"] == "Sring"


def test_mfab_on_the_band_sews_its_outline_and_the_keyline_keeps_its_artwork():
    planned, blocks = _sew(mfab(), silhouette_underfill=True)
    by = {p.region.shape_id: p for p in planned}
    assert by["Sring"].polygon.area >= 0.98 * 60 * 24
    key_art = mfab()[0].polygon
    assert by["Skey"].polygon.intersection(key_art).area >= 0.9 * key_art.area
    order = [b.thread_index for b in blocks]
    assert order.index(0) < order.index(1)
    kinds = {r.kind for b in blocks for r in b.runs if r.shape_id == "Sring"}
    assert stitches.FILL in kinds and stitches.SATIN not in kinds


def test_becker_the_letter_colour_fills_and_the_ring_sews_on_top_unchanged():
    rings = su.plan(becker())
    assert len(rings) == 1
    ring, host, _outline, merged, _inner = rings[0]
    assert (ring.shape_id, host.shape_id, merged) == ("Sring", "Sb1", ["Sb2"])
    planned, blocks = _sew(becker(), silhouette_underfill=True)
    by = {p.region.shape_id: p for p in planned}
    assert "Sb2" not in by
    assert by["Sb1"].polygon.area >= 0.98 * 60 * 24
    # the ring sews as it did -- same planned shape, same kinds; only where
    # stage 7 enters it moves, because the fill before it ends elsewhere
    off_planned, off_blocks = _sew(becker())
    off_ring = next(p for p in off_planned if p.region.shape_id == "Sring")
    assert by["Sring"].polygon.symmetric_difference(off_ring.polygon).area < 1e-6
    kinds = lambda bs: sorted({r.kind for b in bs for r in b.runs if r.shape_id == "Sring"})  # noqa: E731
    assert kinds(blocks) == kinds(off_blocks)
    order = [b.thread_index for b in blocks]
    assert order.index(1) < order.index(0)


def test_fremont_a_ground_round_its_lettering_fills_under_it():
    """The ground's colour covers most of the outline (the ring counts for
    its own colour): the ground hosts, the letters sew on top, after it."""
    t1, t2 = box(10, 8, 20, 16), box(30, 8, 40, 16)
    regs = [_reg("St1", t1, 1, 0), _reg("St2", t2, 1, 0),
            _reg("Sground", _holed(box(0, 0, 60, 24), t1, t2), 0, 1)]
    (ring, host, _o, merged, _i), = su.plan(regs)
    assert ring.shape_id == host.shape_id == "Sground" and merged == []
    out, _ = su.apply(regs)
    ids = {r.shape_id: r for r in out}
    assert ids["Sground"].meta["layer"] < ids["St1"].meta["layer"] == ids["St2"].meta["layer"]


def test_a_shape_left_unsewn_stays_garment():
    """MFab without `sew_enclosed_white`: the white keyline is left as fabric
    on purpose, so the black under-fill is cut back off it -- it must not
    sew black over the keyline the design shows."""
    regs = mfab()
    key = regs.pop(0)
    (_r, host, outline, merged, _i), = su.plan(regs, unsewn=[key])
    assert host.shape_id == "Sring" and merged == ["Sl1", "Sl2"]
    assert outline.intersection(key.polygon).area < 1e-6
    assert abs(outline.area - (60 * 24 - key.polygon.area)) < 1e-6
    # held only by sewn shapes: a ring whose holes hold nothing sewn reads nothing
    assert su.plan([mfab()[1]], unsewn=[key]) == []


def _sewn_cover(planned, blocks, poly):
    """Share of `poly` the host and its stage-5 pieces sew, and the stitch
    kinds those shapes sew with."""
    ids = {p.region.shape_id for p in planned
           if p.region.shape_id == "Sring" or p.region.meta.get("clip_piece_of") == "Sring"}
    cover = unary_union([p.polygon for p in planned if p.region.shape_id in ids])
    kinds = {r.kind for b in blocks for r in b.runs if r.shape_id in ids}
    return cover.intersection(poly).area / poly.area, kinds


def test_an_unsewn_keyline_round_two_bodies_leaves_both_sewn():
    """MFab with the white unsewn (arm b): the keyline cut splits the outline
    into the band and the two bodies it held. Every body still sews as the
    host's fill -- stage 5 judged the pieces on the band's artwork alone and
    dropped both bodies uncounted (MFab LC: 26 merged shapes, sewn by nobody)."""
    regs = mfab()
    key = regs.pop(0)
    out, report = su.apply(regs, unsewn=[key])
    assert report[0]["merged"] == ["Sl1", "Sl2"]
    assert len(getattr(out[0].meta[su.UNDERFILL_KEY], "geoms", [None])) == 3   # band + 2 bodies
    cfg = PipelineConfig(underlay=False, **{**FLIP_2026_10_27, "silhouette_underfill": True})
    planned, _ = resolve_overlaps(out, FABRIC, cfg)
    blocks, _ = sequence(planned, FABRIC, cfg)
    l1, l2 = regs[1].polygon, regs[2].polygon
    for body in (l1, l2):
        cover, kinds = _sewn_cover(planned, blocks, body)
        assert cover >= 0.95
        assert stitches.FILL in kinds and stitches.SATIN not in kinds
    # one angle: every piece sews on the host's axis
    axes = {round(p.stitch_angle_deg, 6) for p in planned
            if p.region.shape_id == "Sring" or p.region.meta.get("clip_piece_of") == "Sring"}
    assert len(axes) == 1
    # and the keyline stays garment
    sewn = unary_union([p.polygon for p in planned])
    assert sewn.intersection(key.polygon.buffer(-0.5)).area < 1e-6


def test_no_ring_reads_without_a_reason():
    # a ring too small to be a silhouette (a letter with a counter)
    small = [_reg("Sr", _holed(box(0, 0, 10, 10), box(2, 2, 8, 8)), 0, 1), _reg("Sd", box(2, 2, 8, 8), 1, 0)]
    assert su.plan(small) == []
    # empty holes: nothing inside holds them
    assert su.plan([mfab()[1]]) == []
    # a lettering ring is the lettering lane's
    regs = mfab()
    regs[1] = _reg("Sring", regs[1].polygon, 0, 1, text_candidate=True)
    assert su.plan(regs) == []
    # a review override on the ring wins
    regs = mfab()
    regs[1] = _reg("Sring", regs[1].polygon, 0, 1, tier="satin")
    assert su.plan(regs) == []


def test_a_review_tier_inside_is_never_merged():
    regs = mfab()
    regs[2] = _reg("Sl1", regs[2].polygon, 0, 1, tier="satin")
    (_r, _h, _o, merged, _i), = su.plan(regs)
    assert merged == ["Sl2"]


def test_apply_without_a_ring_returns_the_regions_untouched():
    regs = [_reg("Sa", box(0, 0, 10, 10), 0, 0)]
    out, report = su.apply(regs)
    assert out is regs and report == []
