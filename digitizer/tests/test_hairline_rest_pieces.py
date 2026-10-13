"""`stage6_hairline.rest_planned` keeps every part of a split rest piece.

A rest piece (the thick part of a hairline shape) has one sewing polygon:
`p.polygon` clipped to the piece grown. When stage 5's clip of the shape by an
earlier colour cuts the piece in two while the shape stays one Polygon
(joined round the outside by a hairline branch), that sewing polygon has two
real parts. `rest_planned` used to sew the largest and drop the other's ink
with no warning (PR #855's audit flagged it: the hairline twin of defect 61).
It now keeps every part whose artwork clears `clip_piece_floor_mm2`, each as
a copy of its own, and counts the sub-floor ones in `CLIP_DROPPED_SLIVER`,
exactly as stage 5's `clip_keep_pieces` does.

`tools/hairline_rest_pieces.py` measures it over the corpus. `cfg.hairline` is
default OFF and nothing here runs without it, so the OFF path is untouched by
construction (`test_off_path_never_reaches_rest_planned`); the fix rides that
flag and has none of its own.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core import stage7_sequence
from digitizer_core.pipeline import (BackgroundInfo, PipelineResult, build_generation,
                                     fabric_for, plan_stitches)
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import clip_piece_floor_mm2, resolve_overlaps
from digitizer_core.stage6_hairline import (REST_KEY, hairline_candidates,
                                            rest_planned, rest_sew_parts)
from digitizer_core.threads import chart_for
from digitizer_core.warnings_codes import CLIP_DROPPED_SLIVER
from tools import hairline_rest_pieces as census

CHART = chart_for(PipelineConfig())
DARK = int(np.argmin(CHART.lab[:, 0]))
TESTDATA = Path(__file__).resolve().parent.parent / "testdata"

SPLIT = box(7.0, -1.5, 9.0, 1.5)        # across the bar, clear of the loop: two real parts
SLIVER = box(0.3, -1.5, 0.6, 1.5)       # leaves a 0.56 mm2 stub at the bar's end, under the floor
BIG_STUB = box(0.6, -1.5, 0.9, 1.5)     # leaves a 1.04 mm2 stub, over it


def _region(sid, poly, thread=DARK, layer=0):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, "stitched": True})


def _u_shape():
    """A 20 mm thick bar joined at both ends by a thin loop beneath it: one
    connected shape, thick bar + thin strand."""
    bar = LineString([(0, 0), (20, 0)]).buffer(0.8, cap_style=2)
    loop = LineString([(0, 0), (0, -6), (20, -6), (20, 0)]).buffer(0.15, cap_style=2)
    return unary_union([bar, loop])


def _planned(cut):
    """The U shape through stage 5, its sewing polygon then cut by `cut`
    (what an earlier colour's clip does), still ONE Polygon via the loop."""
    reg = _region("Su", _u_shape())
    cfg = PipelineConfig(hairline=True)
    cands = hairline_candidates([reg], cfg)
    planned, _w = resolve_overlaps([reg], fabric_for(cfg), cfg, hairline=cands)
    p = planned[0]
    if cut is not None:
        p = dataclasses.replace(p, polygon=p.polygon.difference(cut))
        assert p.polygon.geom_type == "Polygon"
    return p, cands["Su"], cfg


def _old_rest_planned(p, m):
    """`rest_planned` as it was before this change: the largest sewing part."""
    out = []
    for piece, parts in rest_sew_parts(p, m):
        sew = parts[0]
        region = dataclasses.replace(p.region, polygon=piece, area_mm2=float(piece.area),
                                     meta={**p.region.meta, REST_KEY: True})
        vis = None if p.visible is None else p.visible.intersection(sew)
        out.append(dataclasses.replace(p, region=region, polygon=sew, visible=vis))
    return out


def test_the_fixture_is_a_bar_for_the_ladder_and_a_loop_for_the_tier():
    p, m, _cfg = _planned(None)
    assert m["hair_edges"] and m["thick_edges"]
    pieces = rest_sew_parts(p, m)
    assert len(pieces) == 1 and len(pieces[0][1]) == 1


def test_an_unsplit_piece_is_what_it_always_was():
    """One sewing part: the copy is the old one, field for field."""
    p, m, cfg = _planned(None)
    new = rest_planned(p, m, floor=clip_piece_floor_mm2(cfg))
    old = _old_rest_planned(p, m)
    assert len(new) == len(old) == 1
    assert new[0].polygon.equals_exact(old[0].polygon, 0)
    assert new[0].region.polygon.equals_exact(old[0].region.polygon, 0)
    assert new[0].region.meta == old[0].region.meta
    assert new[0].visible == old[0].visible


def test_a_carve_that_splits_the_rest_keeps_both_pieces():
    p, m, cfg = _planned(SPLIT)
    floor = clip_piece_floor_mm2(cfg)
    (piece, parts), = rest_sew_parts(p, m)
    assert len(parts) == 2 and all(g.intersection(piece).area > floor for g in parts)
    dropped: list = []
    out = rest_planned(p, m, floor=floor, dropped=dropped)
    assert len(out) == 2 and dropped == []
    # Both parts are sewn, each as a copy the ladder will not hand back to the tier.
    assert sorted(o.polygon.area for o in out) == pytest.approx(sorted(g.area for g in parts))
    assert all(o.region.meta.get(REST_KEY) is True for o in out)
    assert all(o.shape_id == "Su" for o in out)
    # Each part's artwork is its own share of the piece: nothing sewn twice, none lost.
    arts = [o.region.polygon for o in out]
    assert arts[0].intersection(arts[1]).area < 1e-6
    assert unary_union(arts).area == pytest.approx(piece.area, abs=1e-3)
    # The old rule sewed the one and lost the other's ink.
    old = _old_rest_planned(p, m)
    assert len(old) == 1
    lost = sum(g.intersection(piece).area for g in parts[1:])
    assert lost > floor


def test_a_sliver_under_the_floor_is_dropped_and_counted():
    p, m, cfg = _planned(SLIVER)
    floor = clip_piece_floor_mm2(cfg)
    (piece, parts), = rest_sew_parts(p, m)
    assert len(parts) == 2
    stub = parts[1].intersection(piece).area
    assert 1e-6 < stub < floor
    dropped: list = []
    out = rest_planned(p, m, floor=floor, dropped=dropped)
    assert len(out) == 1 and out[0].polygon.equals(parts[0])
    assert dropped == [("Su", pytest.approx(stub))]
    # The main copy keeps the whole piece for its artwork: nothing shared out.
    assert out[0].region.polygon.equals(piece)


def test_a_stub_over_the_floor_is_sewn_not_dropped():
    p, m, cfg = _planned(BIG_STUB)
    dropped: list = []
    out = rest_planned(p, m, floor=clip_piece_floor_mm2(cfg), dropped=dropped)
    assert len(out) == 2 and dropped == []


def test_the_census_reads_before_and_after_off_the_real_output():
    p, m, cfg = _planned(SPLIT)
    (piece, parts), = rest_sew_parts(p, m)
    floor = clip_piece_floor_mm2(cfg)
    row = census.census_piece(piece, parts, [c.polygon for c in rest_planned(p, m, floor=floor)], floor)
    assert row["parts"] == 2 and row["above_floor"] == 2
    assert row["before_mm2"] > floor            # the old rule dropped this much ink
    assert row["unsewn_above_floor"] == 0 and row["unsewn_mm2"] == 0.0
    # What the old rule handed over leaves it unsewn.
    row = census.census_piece(piece, parts, [parts[0]], floor)
    assert row["unsewn_above_floor"] == 1 and row["unsewn_mm2"] == row["before_mm2"]


def test_the_census_counts_slivers_apart_from_loss():
    p, m, cfg = _planned(SLIVER)
    (piece, parts), = rest_sew_parts(p, m)
    floor = clip_piece_floor_mm2(cfg)
    row = census.census_piece(piece, parts, [c.polygon for c in rest_planned(p, m, floor=floor)], floor)
    assert row["parts"] == 2 and row["above_floor"] == 1
    assert row["slivers"] == 1 and 0 < row["sliver_mm2"] < floor
    assert row["unsewn_above_floor"] == 0 and row["unsewn_mm2"] == 0.0


def _warnings(cut):
    p, m, cfg = _planned(cut)
    _blocks, warnings = stage7_sequence.sequence([p], fabric_for(cfg), cfg, hairline={"Su": m})
    return [w for w in warnings if w["code"] == CLIP_DROPPED_SLIVER]


def test_stage7_counts_the_sliver_in_clip_dropped_sliver():
    (w,) = _warnings(SLIVER)
    assert w["count"] == 1 and w["ids"] == ["Su"] and w["source"] == "hairline_rest"
    assert 0 < w["total_mm2"] < w["floor_mm2"]
    assert w["pieces"] == [{"id": "Su", "art_mm2": w["total_mm2"]}]


def test_stage7_says_nothing_when_nothing_was_dropped():
    assert _warnings(None) == []
    assert _warnings(SPLIT) == []


def test_stage7_sews_both_parts():
    p, m, cfg = _planned(SPLIT)
    blocks, _w = stage7_sequence.sequence([p], fabric_for(cfg), cfg, hairline={"Su": m})
    kept = [r for b in blocks for r in b.runs if r.kind == "satin"]
    p1, m1, cfg1 = _planned(None)
    one, _w = stage7_sequence.sequence([p1], fabric_for(cfg1), cfg1, hairline={"Su": m1})
    assert len(kept) == 2 and len([r for b in one for r in b.runs if r.kind == "satin"]) == 1


def test_corpus_rest_pieces_lose_no_ink():
    """End to end on `logo_golden_tee.jpg` at 80 mm left_chest, `hairline` on:
    every rest piece's at-or-over-floor parts are handed to the ladder. If a
    change makes a part go unsewn this goes red:
    `python -m tools.hairline_rest_pieces --scorecard`."""
    kw = {"target_width_mm": 80.0, "garment_id": "left_chest"}
    gen = build_generation(str(TESTDATA / "photo" / "logo_golden_tee.jpg"),
                           PipelineConfig(**kw))
    for extra in ({"hairline": True}, {"hairline": True, "hairline_over_ground": True}):
        got = census.run_mode(gen, kw, extra)
        assert got["rest_pieces"] > 0, "reach: no rest piece was planned at all"
        assert got["unsewn_pieces"] == 0 and got["unsewn_mm2"] == 0.0


def test_off_path_never_reaches_rest_planned(monkeypatch):
    """`cfg.hairline` False: stage 7 does not call `rest_planned` at all."""
    called = []
    monkeypatch.setattr(stage7_sequence, "rest_planned",
                        lambda *a, **k: called.append(1) or [])
    reg = _region("Su", _u_shape())
    palette = [{"brand": CHART.label, "brand_id": CHART.id, "number": CHART[DARK].number,
                "name": "x", "rgb": list(CHART[DARK].rgb)}]
    plan_stitches(PipelineResult(regions=[reg], palette=palette,
                                 background=BackgroundInfo(detected=False),
                                 px_per_mm=10.0, design_size_mm=(24.0, 24.0)),
                  PipelineConfig())
    assert not called
