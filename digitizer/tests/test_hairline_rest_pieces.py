"""`stage6_hairline.rest_planned` sews the largest part of a rest piece: what that can lose.

A rest piece (the thick part of a hairline shape) has one sewing polygon:
`p.polygon` clipped to the piece grown. When stage 5's clip of the shape by an
earlier colour cuts the piece in two while the shape stays one Polygon
(joined round the outside by a hairline branch), that sewing polygon has two
real parts. `rest_planned` keeps the largest and drops the other's ink with no
warning (PR #855's audit flagged it, the hairline twin of defect 61).

`tools/hairline_rest_pieces.py` measured it on the corpus: no rest piece has a
second part carrying ink, so nothing is built (see the docstring of
`rest_planned`). These tests pin the latent drop on a synthetic cut, so a
future fix is a deliberate change, and `test_corpus_rest_pieces_carry_ink_in_
one_part` is the tripwire: it goes red the day a stage-5 change starts
cutting a rest piece in two.

`cfg.hairline` is default OFF and nothing here runs without it, so the OFF
path is untouched by construction (`test_off_path_never_reaches_rest_planned`).
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig
from digitizer_core import stage7_sequence
from digitizer_core.pipeline import (BackgroundInfo, PipelineResult, build_generation,
                                     fabric_for, plan_stitches)
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import clip_piece_floor_mm2, resolve_overlaps
from digitizer_core.stage6_hairline import (hairline_candidates, rest_planned,
                                            rest_sew_parts)
from digitizer_core.threads import chart_for
from tools import hairline_rest_pieces as census

CHART = chart_for(PipelineConfig())
DARK = int(np.argmin(CHART.lab[:, 0]))
TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


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


def test_the_fixture_is_a_bar_for_the_ladder_and_a_loop_for_the_tier():
    p, m, _cfg = _planned(None)
    assert m["hair_edges"] and m["thick_edges"]
    pieces = rest_sew_parts(p, m)
    assert len(pieces) == 1 and len(pieces[0][1]) == 1


def test_a_clip_that_splits_a_rest_piece_sews_only_the_largest_part():
    """The latent drop, pinned: two real parts, one copy for the ladder, and
    the other part's ink (above the stage-4 region floor) goes unsewn."""
    p, m, cfg = _planned(box(7.0, -1.5, 9.0, 1.5))      # across the bar, clear of the loop
    (piece, parts), = rest_sew_parts(p, m)
    floor = clip_piece_floor_mm2(cfg)
    assert len(parts) == 2 and all(g.intersection(piece).area > floor for g in parts)
    out = rest_planned(p, m)
    assert len(out) == 1 and out[0].polygon.equals(parts[0])
    assert out[0].region.polygon.equals(piece)
    assert out[0].region.meta.get("_hairline_rest") is True


def test_the_census_reads_the_loss_off_the_real_output():
    p, m, cfg = _planned(box(7.0, -1.5, 9.0, 1.5))
    (piece, parts), = rest_sew_parts(p, m)
    floor = clip_piece_floor_mm2(cfg)
    row = census.census_piece(piece, parts, [c.polygon for c in rest_planned(p, m)], floor)
    assert row["parts"] == 2 and row["above_floor"] == 2
    assert row["unsewn_above_floor"] == 1 and row["unsewn_mm2"] > floor
    # Had both parts been handed to the ladder, nothing is unsewn.
    row = census.census_piece(piece, parts, list(parts), floor)
    assert row["unsewn_above_floor"] == 0 and row["unsewn_mm2"] == 0.0


def test_a_part_under_the_floor_is_not_counted_as_lost():
    """Underlap beside the piece, outside its artwork, carries no ink."""
    p, m, cfg = _planned(box(7.0, -1.5, 9.0, 1.5))
    (piece, parts), = rest_sew_parts(p, m)
    fleck = box(100, 100, 100.2, 100.2)
    row = census.census_piece(piece, [parts[0], fleck], [parts[0]], clip_piece_floor_mm2(cfg))
    assert row["parts"] == 2 and row["above_floor"] == 1
    assert row["unsewn_above_floor"] == 0 and row["unsewn_mm2"] == 0.0


def test_corpus_rest_pieces_carry_ink_in_one_part():
    """End to end on `logo_golden_tee.jpg` at 80 mm left_chest, `hairline` on:
    8 shapes hand 12 rest pieces to the ladder and 4 have a second sewing
    part (measured 2026-10-12), every one of them underlap outside the piece
    with no ink. If a change makes a second part carry ink this goes red:
    run `python -m tools.hairline_rest_pieces --scorecard`."""
    kw = {"target_width_mm": 80.0, "garment_id": "left_chest"}
    gen = build_generation(str(TESTDATA / "photo" / "logo_golden_tee.jpg"),
                           PipelineConfig(**kw))
    for extra in ({"hairline": True}, {"hairline": True, "hairline_over_ground": True}):
        got = census.run_mode(gen, kw, extra)
        assert got["rest_pieces"] > 0, "reach: no rest piece was planned at all"
        assert got["multi_above_floor"] == 0
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
