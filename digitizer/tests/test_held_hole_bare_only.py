"""`cfg.held_hole_bare_only` — stage 5 holds open only the BARE part of a hole.

A hole the shell's pull growth would shrink under `min_detail_mm²` is held at
its original size. For a counter that is right; for a hole a LATER stitched
colour sews in, it strips the ground's pull and underlap tongue from the whole
seam round that piece (MASTER_SCOPE defect 6, "Seams"). The flag keeps the
hold for whatever no later stitched shape covers, at or over the same floor.
Real-art before/after: `tools/held_hole_tongue.py`.
"""
from __future__ import annotations

from dataclasses import replace

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import _bare_part, resolve_overlaps

FABRIC = fabric_for_garment("left_chest")
PULL = FABRIC.pull_comp_mm


def _region(shape_id, poly, layer, stitched=True):
    return Region(shape_id=shape_id, polygon=poly, thread_index=5 + layer,
                  thread_number=str(5 + layer), area_mm2=poly.area, source="test",
                  meta={"layer": layer, "stitched": stitched})


def _ground(hole: Polygon) -> Polygon:
    return Polygon(box(0, 0, 20, 20).exterior.coords, [hole.exterior.coords])


def _run(regions, flag, **kw):
    cfg = replace(PipelineConfig(), held_hole_bare_only=flag, **kw)
    planned, warns = resolve_overlaps(regions, FABRIC, cfg)
    by_id = {p.shape_id: p for p in planned}
    held = sum(w.get("count", 0) for w in warns if w.get("code") == "HOLE_NEARLY_CLOSED")
    return by_id, held


# A 1.8 mm square hole: 3.24 mm², over the 2.25 floor, and 1.44 once the shell
# grows by 0.3 -- so the OFF engine holds it.
HOLE = box(9.1, 9.1, 10.9, 10.9)
# A later piece in it, a hair (0.05 mm) inside the hole's edge: the anti-alias
# sliver every vectorized piece-in-a-hole carries.
PIECE = box(9.15, 9.15, 10.85, 10.85)


def test_the_premise_pull_and_floor():
    assert PULL == pytest.approx(0.3)
    assert PipelineConfig().min_detail_mm ** 2 == pytest.approx(2.25)
    assert PipelineConfig().held_hole_bare_only is False


def test_off_holds_the_filled_hole_and_the_piece_gets_no_tongue():
    g, p = _region("G", _ground(HOLE), 0), _region("P", PIECE, 1)
    by_id, held = _run([g, p], False)
    assert held == 1
    assert by_id["G"].polygon.intersection(PIECE).area == pytest.approx(0.0, abs=1e-9)


def test_on_releases_it_and_the_ground_reaches_under_the_piece():
    g, p = _region("G", _ground(HOLE), 0), _region("P", PIECE, 1)
    by_id, held = _run([g, p], True)
    assert held == 0
    tongue = by_id["G"].polygon.intersection(PIECE)
    # pull + overlap from each side of a 1.7 mm piece: a band 0.5 mm deep
    # round the whole edge (the 0.05 sliver eats the rest of the 0.55).
    band = PIECE.difference(PIECE.buffer(-0.5))
    assert tongue.area == pytest.approx(band.area, rel=0.05)
    # and the sliver between them is sewn by the ground, not left as fabric
    sliver = HOLE.difference(PIECE)
    assert sliver.difference(by_id["G"].polygon).area == pytest.approx(0.0, abs=1e-6)


def test_a_true_counter_is_held_exactly_as_before():
    g = _region("G", _ground(HOLE), 0)
    other = _region("O", box(30, 30, 35, 35), 1)      # a later colour, elsewhere
    off, held_off = _run([g, other], False)
    on, held_on = _run([g, other], True)
    assert held_off == held_on == 1
    assert on["G"].polygon.wkb == off["G"].polygon.wkb
    assert on["O"].polygon.wkb == off["O"].polygon.wkb


def test_a_bare_part_over_the_floor_stays_open_and_the_rest_gets_its_tongue():
    # 3.4 x 1.4 hole (4.76 mm², 2.24 after the shell's growth: held OFF); a
    # piece fills its left 1.0 mm, leaving 2.4 x 1.4 = 3.36 mm² of fabric.
    hole = box(8.0, 9.3, 11.4, 10.7)
    piece = box(8.0, 9.3, 9.0, 10.7)
    bare = box(9.0, 9.3, 11.4, 10.7)
    g, p = _region("G", _ground(hole), 0), _region("P", piece, 1)
    by_id, held = _run([g, p], True)
    assert held == 1
    assert by_id["G"].polygon.intersection(bare).area == pytest.approx(0.0, abs=1e-6)
    assert by_id["G"].polygon.intersection(piece).area > 0.3


def test_a_later_shape_that_only_touches_the_hole_leaves_it_byte_identical():
    # On the ground, outside the hole, sharing its right edge: no interior
    # overlap, so the counter is held exactly as without the flag.
    g = _region("G", _ground(HOLE), 0)
    t = _region("T", box(10.9, 9.5, 14.0, 10.5), 1)
    off, held_off = _run([g, t], False)
    on, held_on = _run([g, t], True)
    assert held_off == held_on == 1
    assert on["G"].polygon.wkb == off["G"].polygon.wkb


def test_two_bare_parts_over_the_floor_are_both_held_as_one_hole():
    # A 6.0 x 1.0 hole (6.0 mm²) shrinks to 5.4 x 0.4 = 2.16 under the
    # shell's growth: held OFF. A piece across its middle leaves two bare
    # ends of 2.6 mm² each, both over the floor.
    hole = box(7.0, 9.5, 13.0, 10.5)
    piece = box(9.6, 9.5, 10.4, 10.5)                 # the middle 0.8 mm
    left, right = box(7.0, 9.5, 9.6, 10.5), box(10.4, 9.5, 13.0, 10.5)  # 2.6 mm² each
    g, p = _region("G", _ground(hole), 0), _region("P", piece, 1)
    by_id, held = _run([g, p], True)
    assert held == 1
    for bare in (left, right):
        assert by_id["G"].polygon.intersection(bare).area == pytest.approx(0.0, abs=1e-6)
    assert by_id["G"].polygon.intersection(piece).area > 0.2


def test_directional_comp_releases_the_filled_hole_too():
    g, p = _region("G", _ground(HOLE), 0), _region("P", PIECE, 1)
    off, held_off = _run([g, p], False, directional_comp=True)
    on, held_on = _run([g, p], True, directional_comp=True)
    assert (held_off, held_on) == (1, 0)
    assert off["G"].polygon.intersection(PIECE).area == pytest.approx(0.0, abs=1e-9)
    assert on["G"].polygon.intersection(PIECE).area > 0.0


def test_an_unstitched_later_shape_is_bare_fabric_and_covers_nothing():
    # `plan_stitches` drops unstitched regions before stage 5, so the pipeline
    # never reaches this; tools that pass `result.regions` whole do.
    g = _region("G", _ground(HOLE), 0)
    p = _region("P", PIECE, 1, stitched=False)
    off, held_off = _run([g, p], False)
    on, held_on = _run([g, p], True)
    assert held_off == held_on == 1
    assert on["G"].polygon.wkb == off["G"].polygon.wkb


def test_bare_part_helper():
    assert _bare_part(HOLE, None, 2.25) == [HOLE]
    assert _bare_part(HOLE, box(30, 30, 31, 31), 2.25) == [HOLE]
    assert _bare_part(HOLE, HOLE.buffer(0.1), 2.25) == []
    assert _bare_part(HOLE, PIECE, 2.25) == []     # the sliver is under the floor
