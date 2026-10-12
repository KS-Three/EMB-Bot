"""`cfg.clip_keep_pieces` — stage 5's clip cutting a shape in two (defect 61).

Stage 5 clips each grown shape by the colours already sewn. Where a later
colour's artwork overlaps an earlier one's right across, the clip cuts the
later shape in pieces, and the shipped engine keeps only the largest
(`_largest_polygon`): the rest of the artwork is never sewn and nothing says
so. With the flag, every cut-off piece whose ARTWORK clears the stage-4
region floor sews as its own region of the same thread and tier, planned
right after its parent; smaller ones are dropped as before and counted in
`CLIP_DROPPED_SLIVER`. OFF is the engine before it, byte for byte.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize, run_stages
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import fabric_for
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import (CLIP_PIECE_OF_KEY, clip_piece_floor_mm2,
                                           resolve_overlaps)
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER

FABRIC = get_fabric("pique_knit")
ROOT = Path(__file__).resolve().parents[1]


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


def _plan(regions, on):
    return resolve_overlaps(regions, FABRIC, PipelineConfig(clip_keep_pieces=on))


def test_default_is_off():
    assert PipelineConfig().clip_keep_pieces is False


def test_off_drops_the_smaller_piece_on_keeps_it():
    regs = _cross(0.0)
    off, off_w = _plan(regs, False)
    b_off = [p for p in off if p.region.thread_number == "2000"]
    assert len(b_off) == 1
    # OFF: only the right piece sews -- the 40 mm² left of A is gone.
    assert b_off[0].polygon.bounds[0] > 5.9
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in off_w)

    on, on_w = _plan(regs, True)
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


def test_a_sliver_under_the_floor_is_dropped_and_counted():
    floor = clip_piece_floor_mm2(PipelineConfig())
    # 0.04 mm x 10 mm = 0.4 mm² of artwork left of A: under the floor.
    regs = _cross(3.96)
    assert 0.4 < floor
    off, _ = _plan(regs, False)
    on, on_w = _plan(regs, True)
    assert [p.polygon.wkb for p in on] == [p.polygon.wkb for p in off]
    slivers = [w for w in on_w if w["code"] == CLIP_DROPPED_SLIVER]
    assert len(slivers) == 1
    w = slivers[0]
    assert w["count"] == 1 and w["ids"] == ["B"]
    assert w["total_mm2"] == pytest.approx(0.4, abs=1e-3)
    assert w["floor_mm2"] == pytest.approx(floor, abs=1e-4)


def test_the_shape_keeps_its_ink_not_its_largest_piece():
    """The drone case (`S53adc87e`, 2026-10-12): a thin strip whose underlap
    tongue under a later colour is cut off its artwork by an earlier colour,
    and the tongue is the BIGGER piece. OFF sews the tongue — no artwork in
    it — and drops every square millimetre of the strip's ink."""
    b = _region("B", box(0, 0, 10, 0.3), 1, "2000")            # the strip, 3 mm²
    a = _region("A", box(-5, 0.3, 15, 0.4), 0, "1000")         # sewn first, between
    c = _region("C", box(-5, 0.4, 15, 10), 2, "3000")          # sewn last, above
    regs = [a, b, c]
    kw = dict(overlap_mm=1.0)
    off, _ = resolve_overlaps(regs, FABRIC, PipelineConfig(**kw))
    on, on_w = resolve_overlaps(regs, FABRIC, PipelineConfig(clip_keep_pieces=True, **kw))
    b_off = [p for p in off if p.region.thread_number == "2000"]
    assert len(b_off) == 1 and b_off[0].polygon.intersection(b.polygon).area < 1e-6
    b_on = [p for p in on if p.region.thread_number == "2000"]
    assert [p.shape_id for p in b_on] == ["B"]
    assert b_on[0].polygon.intersection(b.polygon).area == pytest.approx(3.0, abs=1e-6)
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in on_w)


def test_a_piece_of_pure_growth_is_not_ink_and_is_not_counted():
    # B's artwork stops exactly at A's left edge: the only thing the clip
    # cuts off on that side is B's pull band, which carries no artwork.
    regs = _cross(6.0)
    regs[1] = _region("B", box(6.0, 0, 20, 10), 1, "2000")
    on, on_w = _plan(regs, True)
    assert [p.shape_id for p in on if p.region.thread_number == "2000"] == ["B"]
    assert not any(w["code"] == CLIP_DROPPED_SLIVER for w in on_w)


def test_the_floor_is_stage_fours():
    cfg = PipelineConfig()
    assert clip_piece_floor_mm2(cfg) == pytest.approx(0.25 * cfg.min_detail_mm ** 2)


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


def test_gaulke_roof_line_is_sewn_on_and_lost_off():
    """The real case (2026-10-12): on `logo_gaulke_roofing.png` the black
    roof-line stroke's largest clip piece is its underlap tongue — no ink —
    so the shipped engine sews the tongue under the white and the whole
    roof line is missing. Read without shape ids, which move per platform."""
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    result = run_stages(ROOT / "testdata" / "photo" / "logo_gaulke_roofing.png", cfg)
    regions = [r for r in result.regions if r.meta.get("stitched", True)]
    fabric = fabric_for(cfg)
    off, _ = resolve_overlaps(regions, fabric, cfg, result.design_class)
    on_cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", clip_keep_pieces=True)
    on, _ = resolve_overlaps(regions, fabric, on_cfg, result.design_class)
    assert _inkless_parents(off, regions), "the fixture no longer exercises the drop"
    assert _inkless_parents(on, regions) == []


def _plan_md5(plan) -> str:
    h = hashlib.md5()
    for _b, run in plan.iter_runs():
        h.update(run.kind.encode())
        for x, y in run.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


# OFF is the engine before it. Three fixtures the census (2026-10-12,
# `tools/clip_keep_pieces.py`) reads no kept piece on, so ON must also be
# byte-identical there: the ON path with nothing to keep is the OFF path.
@pytest.mark.parametrize("rel", ["logo_whitebg.png", "logo_alpha.png", "ribbon_curve.png"])
def test_off_and_nothing_to_keep_are_byte_identical(rel):
    path = ROOT / "testdata" / rel
    default = _plan_md5(digitize(path, PipelineConfig(target_width_mm=80.0))[1])
    off = _plan_md5(digitize(path, PipelineConfig(target_width_mm=80.0,
                                                   clip_keep_pieces=False))[1])
    on = _plan_md5(digitize(path, PipelineConfig(target_width_mm=80.0,
                                                  clip_keep_pieces=True))[1])
    assert default == off == on
