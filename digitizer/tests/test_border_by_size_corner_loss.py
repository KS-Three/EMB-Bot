"""No size ring on a shape its own corner rounding would redraw (`cfg.border_by_size_corner_loss`, ON since 2026-11-17).

The size ring (`border_by_size`) is built on the shape with every corner
relaxed inward by `BORDER_CORNER_RADIUS_MM` (2.1 mm). On Intel's blue square
(Commons PNG, 100 mm left chest, 7.3 x 7.2 mm) that leaves 3 mm of straight
edge between four 2.1 mm arcs and costs 12% of the area: the square reads as
a cushion. ON, a shape whose rounding loss is over
`machine.BORDER_BY_SIZE_CORNER_LOSS_MAX` is no ring's and sews as a plain
fill. Off (conftest.CORNER_LOSS_2026_11_17_OFF), byte-identical to the
pre-flip engine. Flipped ON by Kent 2026-11-17 from the Intel sheets.

Synthetic shapes only: the logo is not in the repo.
"""
from __future__ import annotations

import hashlib

from shapely.geometry import Point, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import (BORDER_GROUP_KEY, _border_by_size_width, _corner_loss,
                                            _sews_satin, sequence, tag_border_by_size_groups)

ON = dict(border_by_size_corner_loss=True)
OFF = dict(border_by_size_corner_loss=False)      # the pre-flip engine (conftest.CORNER_LOSS_2026_11_17_OFF)


def _region(poly, sid="Sbig", **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="4101",
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _plan(poly, **cfg_kw):
    reg = _region(poly)
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _kinds(runs):
    return [r.kind for r in runs]


def _md5(runs):
    h = hashlib.md5()
    for r in runs:
        h.update(r.kind.encode())
        for x, y in r.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def test_flag_default_is_on():
    # Kent 2026-11-17, from the Intel ORIGINAL ART | BEFORE | AFTER sheets: "Flip ON"
    assert PipelineConfig().border_by_size_corner_loss is True


def test_the_pre_flip_dict_pins_it_off():
    from .conftest import CORNER_LOSS_2026_11_17_OFF
    assert PipelineConfig(**CORNER_LOSS_2026_11_17_OFF).border_by_size_corner_loss is False


def test_the_constant_sits_between_the_census_numbers():
    # 19 census rings: Intel's square 0.1205, the next highest 0.0575
    assert 0.0575 < machine.BORDER_BY_SIZE_CORNER_LOSS_MAX < 0.1205


def test_loss_reads_the_square_high_and_the_big_and_round_shapes_low():
    assert _corner_loss(box(0, 0, 7.2, 7.2)) > machine.BORDER_BY_SIZE_CORNER_LOSS_MAX
    assert _corner_loss(box(0, 0, 30, 30)) < machine.BORDER_BY_SIZE_CORNER_LOSS_MAX
    assert _corner_loss(Point(0, 0).buffer(6.0, 64)) < 0.01


def test_off_the_7mm_square_is_ringed():
    kinds = _kinds(_plan(box(0, 0, 7.2, 7.2), **OFF))
    assert stitches.BORDER in kinds and stitches.FILL in kinds


def test_on_the_7mm_square_is_a_plain_fill():
    kinds = _kinds(_plan(box(0, 0, 7.2, 7.2), **ON))
    assert stitches.FILL in kinds and stitches.BORDER not in kinds


def test_on_a_30mm_square_keeps_its_ring_byte_identical():
    sq = box(0, 0, 30, 30)
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER in _kinds(on)
    assert _md5(off) == _md5(on)


def test_on_a_12mm_disc_is_byte_identical():
    disc = Point(0, 0).buffer(6.0, 64)
    off, on = _plan(disc, **OFF), _plan(disc, **ON)
    assert stitches.BORDER in _kinds(off)
    assert _md5(off) == _md5(on)


def test_on_an_8mm_sharp_square_is_a_plain_fill():
    # loss 0.096 > 0.083: a 2.1 mm corner radius leaves 3.8 mm of straight side
    assert _corner_loss(box(0, 0, 8, 8)) > machine.BORDER_BY_SIZE_CORNER_LOSS_MAX
    kinds = _kinds(_plan(box(0, 0, 8, 8), **ON))
    assert stitches.FILL in kinds and stitches.BORDER not in kinds


def test_on_a_10mm_sharp_square_keeps_its_ring_byte_identical():
    sq = box(0, 0, 10, 10)
    assert _corner_loss(sq) < machine.BORDER_BY_SIZE_CORNER_LOSS_MAX      # 0.061
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER in _kinds(on)
    assert _md5(off) == _md5(on)


def test_a_shape_under_the_floor_is_untouched():
    sq = box(0, 0, 5.0, 5.0)            # smallest dimension 5.0 < 6.0, loss over the max
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER not in _kinds(off)
    assert _md5(off) == _md5(on)


def test_the_default_is_the_on_arm_byte_for_byte():
    sq = box(0, 0, 7.2, 7.2)
    assert _md5(_plan(sq)) == _md5(_plan(sq, **ON))


def test_the_prediction_and_the_emitter_agree_for_the_square_both_ways():
    sq = box(0, 0, 7.2, 7.2)
    for flags, ringed in ((OFF, True), (ON, False)):
        cfg = PipelineConfig(underlay=False, **flags)
        reg = _region(sq)
        # the by-size reader (prediction, seam ownership, emitter's two blocks) ...
        assert (_border_by_size_width(reg, cfg) is not None) is ringed
        # ... the satin prediction never calls a 7.2 mm square satin ...
        assert not _sews_satin(reg, cfg, machine.satin_ceiling_mm(cfg), "flat")
        # ... and the sewn result has the ring exactly when the reader said
        assert (stitches.BORDER in _kinds(_plan(sq, **flags))) is ringed


def test_the_corner_rule_wins_over_a_group_stamp():
    sq = _region(box(0, 0, 7.2, 7.2))
    sq.meta[BORDER_GROUP_KEY] = True
    assert _border_by_size_width(sq, PipelineConfig(**ON)) is None
    assert _border_by_size_width(sq, PipelineConfig(**OFF)) is not None


def test_a_refused_shape_is_not_evidence_for_its_line():
    # three like bars (one line) plus the square among them: with the square
    # refused the bars' verdicts are the same as without it
    bars = [_region(box(x, 0, x + 6.3, 20), sid=f"B{i}") for i, x in enumerate((20, 30, 40))]
    sq = _region(box(0, 5, 7.2, 12.2), sid="Sq")
    on = PipelineConfig(**ON)
    tag_border_by_size_groups(bars + [sq], on)
    with_sq = [b.meta.get(BORDER_GROUP_KEY) for b in bars]
    tag_border_by_size_groups(bars, on)
    assert with_sq == [b.meta.get(BORDER_GROUP_KEY) for b in bars]
    assert BORDER_GROUP_KEY not in sq.meta
