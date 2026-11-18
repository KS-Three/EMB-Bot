"""A round dot sews round (`cfg.round_dot_ring`, built OFF 2026-11-18).

Prime grader pin on `tires_hat_3d` (the i's dot, 5.7 mm across): "flat spots
at top and bottom and a jutting last stitch ... faceted rather than a round
dot". A dot over the hat's satin ceiling sews as tatami rows whose ends make
the edge. ON, the size rule (`border_by_size`) reads a ROUND compact solid
from 4 mm instead of 6, so the dot is a fill under the pro's 1.5 mm satin
ring and the ring draws the outline. Off, byte-identical.

Synthetic shapes only: the dot's artwork is the committed Tires PNG, which
the job-level evidence run covers (docs/renders/round-dot-ring-2026-11-18/).
"""
from __future__ import annotations

import hashlib

from shapely.geometry import Point, box

from digitizer_core import PipelineConfig, machine
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage7_sequence import _border_by_size_width, _is_round_solid, sequence

ON = dict(round_dot_ring=True)


def _region(poly, sid="Sdot", **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="4101",
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _runs(poly, **cfg_kw):
    planned = [PlannedRegion(region=_region(poly), polygon=poly, sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _md5(runs):
    h = hashlib.md5()
    for r in runs:
        h.update(str(r.kind).encode())
        for x, y in r.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _disc(d_mm):
    return Point(0, 0).buffer(d_mm / 2.0, quad_segs=32)


def test_flag_default_is_on():
    # Kent 2026-11-18, from the Tires dot ORIGINAL | BEFORE | AFTER: "Flip ON (Recommended)"
    assert PipelineConfig().round_dot_ring is True


def test_the_pre_flip_dict_pins_it_off():
    from .conftest import ROUND_DOT_RING_2026_11_18_OFF
    assert PipelineConfig(**ROUND_DOT_RING_2026_11_18_OFF).round_dot_ring is False


def test_constants_sit_on_the_census_band():
    assert machine.ROUND_DOT_MIN_DIM_MM == 4.0
    assert machine.ROUND_DOT_MIN_DIM_MM < machine.BORDER_BY_SIZE_MIN_DIM_MM
    # a disc is 1.0; a square is pi/4 = 0.785, which must stay under the bar
    assert 0.785 < machine.ROUND_DOT_MIN_CIRCULARITY < 1.0


def test_round_solid_reads_discs_not_squares_or_rings():
    assert _is_round_solid(_disc(5.7))
    assert not _is_round_solid(box(0, 0, 5.7, 5.7))
    assert not _is_round_solid(box(0, 0, 11.0, 3.0))
    assert not _is_round_solid(_disc(5.7).difference(_disc(2.0)))


def test_off_reads_the_dot_as_no_ring():
    reg = _region(_disc(5.7))
    assert _border_by_size_width(reg, PipelineConfig(round_dot_ring=False)) is None


def test_on_rings_a_round_dot_at_the_4_to_6_band_width():
    reg = _region(_disc(5.7))
    assert _border_by_size_width(reg, PipelineConfig(**ON)) == machine.border_by_size_width_mm(5.7) == 1.5


def test_on_leaves_the_rest_of_the_rule_alone():
    cfg = PipelineConfig(**ON)
    assert _border_by_size_width(_region(_disc(3.5)), cfg) is None          # under 4 mm
    assert _border_by_size_width(_region(box(0, 0, 5.7, 5.7)), cfg) is None   # not round
    assert _border_by_size_width(_region(_disc(5.7), tier="fill"), cfg) is None   # per-shape intent
    # over 6 mm the rule reads it with or without the flag, at the same width
    big = _region(_disc(8.0))
    assert _border_by_size_width(big, cfg) == _border_by_size_width(big, PipelineConfig(round_dot_ring=False)) == 2.1


def test_off_plan_is_byte_identical_to_the_default():
    poly = _disc(5.7)
    # OFF, a 5.7 mm dot is read by no ring at all: the plan is the one with the size rule off
    assert _md5(_runs(poly, round_dot_ring=False)) == _md5(_runs(poly, round_dot_ring=False, border_by_size=False))


def test_on_sews_the_dot_as_fill_plus_a_border_ring():
    kinds_off = {str(r.kind) for r in _runs(_disc(5.7), round_dot_ring=False)}
    kinds_on = {str(r.kind) for r in _runs(_disc(5.7), **ON)}
    assert "border" not in kinds_off
    assert "border" in kinds_on and "fill" in kinds_on
