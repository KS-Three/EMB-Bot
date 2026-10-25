"""`cfg.pro_measured_values` (2026-10-23, built OFF): the pro's own fill stitch
length, satin spacing and bean pitch on the hat / left-chest / beanie presets.

Sources (docs/settings-vs-pro-2026-10-21.md, 28 of the pro's DSTs): fill stitch
3.49 mm (row 11), satin 0.37 mm hat and left chest, 0.35 beanie (rows 1-2), bean
0.95 mm (row 19). Physical constants (ROADMAP gate 1): a flag for the sew-out,
nothing here is a default.

Asserted on OUTPUT geometry: the stitch runs a plan sews, not the config.
"""
from __future__ import annotations

import math
import statistics

import pytest
from shapely.geometry import Polygon, Point

from digitizer_core import PipelineConfig, fabrics, get_fabric, stitches
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

FIELD = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])      # fill
STRIPE = Polygon([(-15, -1.2), (15, -1.2), (15, 1.2), (-15, 1.2)])  # satin column


def _plan(fabric_id, poly, meta=None, **cfg_kw):
    cfg_kw.setdefault("edge_cap", "none")
    m = {"layer": 0}
    m.update(meta or {})
    reg = Region(shape_id="S1", polygon=poly, thread_index=5,
                 thread_number=CHART[5].number, area_mm2=poly.area, meta=m)
    fab = get_fabric(fabric_id)
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps([reg], fab, c)
    blocks, _w = sequence(planned, fab, c)
    return [r for b in blocks for r in b.runs]


def _steps(runs, kind):
    return [math.dist(p, q) for r in runs if r.kind == kind
            for p, q in zip(r.points, r.points[1:]) if math.dist(p, q) > 1e-9]


def test_default_is_off_and_the_table_is_untouched():
    assert PipelineConfig().pro_measured_values is False
    from digitizer_core import machine
    assert (machine.FILL_STITCH_MM, machine.SATIN_SPACING_MM, machine.BEAN_STITCH_MM) == (3.0, 0.4, 0.73)


@pytest.mark.parametrize("fabric_id", sorted(
    {f.id for f in fabrics.FABRICS} - set(fabrics.PRO_VALUE_FABRICS)))
def test_other_presets_do_not_move(fabric_id):
    for poly in (FIELD, STRIPE):
        a = _plan(fabric_id, poly)
        b = _plan(fabric_id, poly, pro_measured_values=True)
        assert [(r.kind, r.points) for r in a] == [(r.kind, r.points) for r in b]


@pytest.mark.parametrize("fabric_id", fabrics.PRO_VALUE_FABRICS)
def test_fill_stitch_length_on_the_output(fabric_id):
    off = _steps(_plan(fabric_id, FIELD), stitches.FILL)
    on = _steps(_plan(fabric_id, FIELD, pro_measured_values=True), stitches.FILL)
    # interior stitches only: the row ends are the stagger remainders
    mo, mn = statistics.median(off), statistics.median(on)
    assert 2.9 <= mo <= 3.05
    assert 3.4 <= mn <= 3.55
    assert mn / mo == pytest.approx(3.49 / 3.0, rel=0.03)


@pytest.mark.parametrize("fabric_id,want", [("structured_cap", 0.37), ("pique_knit", 0.37),
                                            ("jersey_tee", 0.35)])
def test_satin_spacing_on_the_output(fabric_id, want):
    def pitch(runs):
        s = [r for r in runs if r.kind == stitches.SATIN]
        assert s, "the stripe sewed no satin"
        pts = [p for r in s for p in r.points]
        xs = sorted({round(p[0], 4) for p in pts})
        return (xs[-1] - xs[0]) / (len(xs) - 1)
    off = pitch(_plan(fabric_id, STRIPE))
    on = pitch(_plan(fabric_id, STRIPE, pro_measured_values=True))
    assert off == pytest.approx(0.40, rel=0.05)
    assert on == pytest.approx(want, rel=0.05)


@pytest.mark.parametrize("fabric_id", fabrics.PRO_VALUE_FABRICS)
def test_bean_pitch_on_the_output(fabric_id):
    # A small closed shape sews as a bean run outline (the run tier is untouched
    # by this flag); the edge cap is the bean station this flag moves.
    poly = Polygon([(-15, -10), (15, -10), (15, 10), (-15, 10)])
    off = _steps(_plan(fabric_id, poly, edge_cap="bean"), stitches.RUN)
    on = _steps(_plan(fabric_id, poly, edge_cap="bean", pro_measured_values=True), stitches.RUN)
    assert off and on
    cap_off = [s for s in off if s < 1.5]
    cap_on = [s for s in on if s < 1.5]
    assert statistics.median(cap_off) == pytest.approx(0.73, rel=0.1)
    assert statistics.median(cap_on) == pytest.approx(0.95, rel=0.1)


def test_explicit_knobs_still_win():
    a = _plan("structured_cap", FIELD, pro_measured_values=True, fill_stitch_mm=2.5)
    b = _plan("structured_cap", FIELD, fill_stitch_mm=2.5)
    assert [(r.kind, r.points) for r in a] == [(r.kind, r.points) for r in b]
