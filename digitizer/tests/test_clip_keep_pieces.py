"""Stage 5's clip cutting a shape in two (defect 61): two settings.

Stage 5 clips each grown shape by the colours already sewn. Where a later
colour's artwork overlaps an earlier one's right across, the clip cuts the
later shape in pieces, and the engine before this fix kept only the largest
(`_largest_polygon`): the rest of the artwork was never sewn and nothing said
so. Two settings, one per half of the cure:

* `cfg.clip_parent_keeps_ink` (default ON, Kent 2026-10-12): the shape keeps
  the piece carrying the most ARTWORK, not the most sewn area. It adds no
  region and no warning.
* `cfg.clip_keep_pieces` (default OFF): every other piece whose ARTWORK
  clears the stage-4 region floor sews as its own region of the same thread
  and tier, planned right after its parent; smaller ones are dropped as
  before and counted in `CLIP_DROPPED_SLIVER`.

Both off is the engine before it, byte for byte.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize, run_stages
from digitizer_core import stage5_overlap as s5
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import (CLIP_PIECE_OF_KEY, clip_piece_floor_mm2,
                                           resolve_overlaps)
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER
from tests.conftest import own_thread_only

FABRIC = get_fabric("pique_knit")
ROOT = Path(__file__).resolve().parents[1]

# The engine before defect 61.
LEGACY = dict(clip_parent_keeps_ink=False, clip_keep_pieces=False)


def _region(sid, poly, layer, thread):
    return Region(shape_id=sid, polygon=poly, thread_index=layer,
                  thread_number=thread, area_mm2=float(poly.area),
                  meta={"layer": layer, "tier": "fill", "fill_angle_deg": 0.0})


def _cross(left_x0: float):
    """A, sewn first, is a vertical bar from x 4 to 6 running past both ends
    of B; B, sewn after, overlaps A's artwork right across, so the clip by
    A cuts B in two: a left piece from `left_x0` to 4 and the right one."""
    a = _region("A", box(4, -5, 6, 15), 0, "1000")
    b = _region("B", box(left_x0, 0, 20, 10), 1, "2000")
    return [a, b]


def _plan(regions, **kw):
    return resolve_overlaps(regions, FABRIC, PipelineConfig(**kw))


def _strip():
    """The drone `S53adc87e` pattern: a thin strip B (3 mm² of ink) whose
    underlap tongue under the later C is cut off its artwork by the earlier
    A sitting between them, and the tongue is the BIGGER piece."""
    b = _region("B", box(0, 0, 10, 0.3), 1, "2000")
    a = _region("A", box(-5, 0.3, 15, 0.4), 0, "1000")
    c = _region("C", box(-5, 0.4, 15, 10), 2, "3000")
    return [a, b, c], dict(overlap_mm=1.0)


def test_defaults():
    cfg = PipelineConfig()
    assert cfg.clip_parent_keeps_ink is True
    assert cfg.clip_keep_pieces is False


def test_off_drops_the_smaller_piece_on_keeps_it():
    regs = _cross(0.0)
    off, off_w = _plan(regs, **LEGACY)
    b_off = [p for p in off if p.region.thread_number == "2000"]
    assert len(b_off) == 1
    # OFF: only the right piece sews -- the 40 mm² left of A is gone.
    assert b_off[0].polygon.bounds[0] > 5.9
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in off_w)

    on, on_w = _plan(regs, clip_keep_pieces=True)
    b_on = [p for p in on if p.region.thread_number == "2000"]
    assert [p.shape_id for p in b_on] == ["B", "B-clip2"]
    piece = b_on[1]
    assert piece.region.meta[CLIP_PIECE_OF_KEY] == "B"
    assert piece.region.meta["tier"] == "fill"
    assert piece.region.thread_index == regs[1].thread_index
    assert piece.sew_index == b_on[0].sew_index
    # The piece's artwork is B's left of A, all of it, and it sews it.
    assert piece.region.polygon.area == pytest.approx(40.0, abs=1e-6)
    assert piece.polygon.covers(box(0, 0, 4, 10).buffer(-1e-6))
    # The parent sews exactly what it sewed OFF, and gives the piece's
    # artwork up so no tier that sews the artwork sews it twice.
    assert b_on[0].polygon.equals_exact(b_off[0].polygon, 0.0)
    assert b_on[0].region.polygon.intersection(piece.region.polygon).area < 1e-9
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in on_w)
    # Planned right after its parent, and A is untouched.
    ids = [p.shape_id for p in on]
    assert ids.index("B-clip2") == ids.index("B") + 1
    assert [p.polygon.wkb for p in on if p.shape_id == "A"] == \
        [p.polygon.wkb for p in off if p.shape_id == "A"]


def test_parent_ink_alone_adds_no_region():
    """The shipped default: `clip_parent_keeps_ink` on, `clip_keep_pieces`
    off. Where the largest piece is also the inkiest -- B's right piece --
    the plan is the legacy plan byte for byte, and the 40 mm² left of A
    still drops: this setting never adds a region."""
    regs = _cross(0.0)
    legacy, _ = _plan(regs, **LEGACY)
    default, default_w = _plan(regs)
    assert [p.shape_id for p in default] == [p.shape_id for p in legacy]
    assert [p.polygon.wkb for p in default] == [p.polygon.wkb for p in legacy]
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in default_w)


def test_a_sliver_under_the_floor_is_dropped_and_counted():
    floor = clip_piece_floor_mm2(PipelineConfig())
    # 0.04 mm x 10 mm = 0.4 mm² of artwork left of A: under the floor.
    regs = _cross(3.96)
    assert 0.4 < floor
    off, _ = _plan(regs, **LEGACY)
    on, on_w = _plan(regs, clip_keep_pieces=True)
    assert [p.polygon.wkb for p in on] == [p.polygon.wkb for p in off]
    slivers = [w for w in on_w if w["code"] == CLIP_DROPPED_SLIVER]
    assert len(slivers) == 1
    w = slivers[0]
    assert w["count"] == 1 and w["ids"] == ["B"]
    assert w["total_mm2"] == pytest.approx(0.4, abs=1e-3)
    assert w["floor_mm2"] == pytest.approx(floor, abs=1e-4)
    # The default (parent keeps ink alone) drops it exactly as before, and
    # says nothing: it keeps no pieces, so it counts none.
    default, default_w = _plan(regs)
    assert [p.polygon.wkb for p in default] == [p.polygon.wkb for p in off]
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in default_w)


def test_the_shape_keeps_its_ink_not_its_largest_piece():
    """The drone case (`S53adc87e`, 2026-10-12): the strip's underlap tongue
    is cut off its artwork and is the BIGGER piece. The legacy engine sews
    the tongue -- no artwork in it -- and drops every square millimetre of
    the strip's ink. The default keeps the ink, and adds no region."""
    regs, kw = _strip()
    off, _ = _plan(regs, **LEGACY, **kw)
    b_off = [p for p in off if p.region.thread_number == "2000"]
    assert len(b_off) == 1 and b_off[0].polygon.intersection(regs[1].polygon).area < 1e-6
    for extra in ({}, {"clip_keep_pieces": True}):
        on, on_w = _plan(regs, **kw, **extra)
        b_on = [p for p in on if p.region.thread_number == "2000"]
        assert [p.shape_id for p in b_on] == ["B"]
        assert b_on[0].polygon.intersection(regs[1].polygon).area == pytest.approx(3.0, abs=1e-6)
        assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in on_w)


def test_keeping_pieces_does_not_need_the_ink_rule():
    """The two settings are independent: pieces on, parent-by-ink off keeps
    the largest piece as the shape (the legacy parent) and the others as
    regions."""
    regs = _cross(0.0)
    legacy, _ = _plan(regs, **LEGACY)
    plan, _ = _plan(regs, clip_parent_keeps_ink=False, clip_keep_pieces=True)
    assert [p.shape_id for p in plan if p.region.thread_number == "2000"] == ["B", "B-clip2"]
    assert plan[1].polygon.equals_exact(
        [p for p in legacy if p.shape_id == "B"][0].polygon, 0.0)
    # And on the strip it keeps the tongue, as legacy: the setting that
    # decides the parent is the one left off.
    sregs, kw = _strip()
    p2, _ = _plan(sregs, clip_parent_keeps_ink=False, clip_keep_pieces=True, **kw)
    b = [p for p in p2 if p.shape_id == "B"][0]
    assert b.polygon.intersection(sregs[1].polygon).area < 1e-6


def test_a_piece_of_pure_growth_is_not_ink_and_is_not_counted():
    # B's artwork stops exactly at A's left edge: the only thing the clip
    # cuts off on that side is B's pull band, which carries no artwork.
    regs = _cross(6.0)
    regs[1] = _region("B", box(6.0, 0, 20, 10), 1, "2000")
    on, on_w = _plan(regs, clip_keep_pieces=True)
    assert [p.shape_id for p in on if p.region.thread_number == "2000"] == ["B"]
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in on_w)


def test_the_floor_is_stage_fours():
    cfg = PipelineConfig()
    assert clip_piece_floor_mm2(cfg) == pytest.approx(0.25 * cfg.min_detail_mm ** 2)


def test_both_off_never_leaves_largest_polygon(monkeypatch):
    """Both settings off is `_largest_polygon` at every split, byte for byte:
    `_split_clip` is not even called, and a run with `_split_clip` replaced
    by its definition (the largest piece, nothing else) plans the same."""
    def boom(*a, **k):
        raise AssertionError("_split_clip reached with both settings off")

    reference = {}
    for name, (regs, kw) in {"cross": (_cross(0.0), {}), "strip": _strip()}.items():
        plan, w = _plan(regs, **LEGACY, **kw)
        reference[name] = ([p.shape_id for p in plan], [p.polygon.wkb for p in plan])
    with monkeypatch.context() as m:
        m.setattr(s5, "_split_clip", own_thread_only(boom, s5._split_clip))
        for name, (regs, kw) in {"cross": (_cross(0.0), {}), "strip": _strip()}.items():
            plan, _ = _plan(regs, **LEGACY, **kw)
            assert ([p.shape_id for p in plan], [p.polygon.wkb for p in plan]) == reference[name]
    # The default setting equals that reference wherever the largest piece
    # is the inkiest -- the cross -- and only differs on the strip.
    regs = _cross(0.0)
    plan, _ = _plan(regs)
    assert ([p.shape_id for p in plan], [p.polygon.wkb for p in plan]) == reference["cross"]


def _inkless_parents(planned, regions) -> list[str]:
    """Shapes stage 5 plans to sew with NO artwork in their sewing polygon,
    though some of their artwork lies clear of every earlier colour's."""
    art = {r.shape_id: r for r in regions}
    out = []
    for p in planned:
        r = art.get(p.shape_id)
        if r is None:
            continue
        earlier = [o.polygon for o in regions if o.meta["layer"] < r.meta["layer"]]
        own = r.polygon.difference(unary_union(earlier)) if earlier else r.polygon
        if own.area >= 1.0 and p.polygon.intersection(r.polygon).area < 1e-3:
            out.append(p.shape_id)
    return out


def test_gaulke_roof_line_is_sewn_by_default_and_lost_legacy():
    """The real case (2026-10-12): on `logo_gaulke_roofing.png` the black
    roof-line stroke's largest clip piece is its underlap tongue -- no ink --
    so the legacy engine sews the tongue under the white and the whole roof
    line is missing. Read without shape ids, which move per platform. The
    default (the parent keeps its ink) sews it, and so does the full path."""
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(ROOT / "testdata" / "photo" / "logo_gaulke_roofing.png", cfg)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    fabric = fabric_for(cfg)
    kw = dict(target_width_mm=80.0, garment_id="left_chest")
    off, _ = resolve_overlaps(regions, fabric, PipelineConfig(**kw, **LEGACY),
                              result.design_class)
    assert _inkless_parents(off, regions), "the fixture no longer exercises the drop"
    for extra in ({}, {"clip_keep_pieces": True}):
        on, _ = resolve_overlaps(regions, fabric, PipelineConfig(**kw, **extra),
                                 result.design_class)
        assert _inkless_parents(on, regions) == []


def _plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


# Three fixtures the census (2026-10-12, `tools/clip_keep_pieces.py`) reads no
# split on that carries artwork, so every setting must be byte-identical
# there: the new path with nothing to switch or keep is the legacy path.
@pytest.mark.parametrize("rel", ["logo_whitebg.png", "logo_alpha.png", "ribbon_curve.png"])
def test_legacy_default_and_nothing_to_keep_are_byte_identical(rel):
    path = ROOT / "testdata" / rel
    md5 = {}
    for tag, extra in (("default", {}),
                       ("legacy", LEGACY),
                       ("pieces", {"clip_keep_pieces": True})):
        md5[tag] = _plan_md5(digitize(path, PipelineConfig(target_width_mm=80.0, **extra))[1])
    assert md5["default"] == md5["legacy"] == md5["pieces"]
