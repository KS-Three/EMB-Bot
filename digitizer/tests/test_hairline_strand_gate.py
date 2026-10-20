"""Hairline step 3 (2026-10-12): the width gate decides per skeleton BRANCH.

docs/hairline-strand-gate-2026-10-12.md. Everything is DEFAULT OFF
(`cfg.hairline`); this REPLACES the prototype's all-or-nothing shape gate
rather than sitting beside it behind a second flag, because with `hairline`
off nothing here runs (the OFF md5 pins in `test_thread_profile.py` and
`test_hairline_ground.py` are the proof) and a shape that is thin throughout
takes the same path as before (`test_a_shape_thin_throughout_is_untouched`).
Every number is a property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import (BackgroundInfo, PipelineResult, fabric_for,
                                     plan_stitches, run_stages)
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import _hairline_ground, resolve_overlaps
from digitizer_core.stage6_hairline import hairline_candidates, measure, rest_planned
from digitizer_core.threads import chart_for
from tools import draw_hair_fixtures as fx
from tools.hairline_renders import SYN, drawn_width_mm

CHART = chart_for(PipelineConfig())
_L = CHART.lab[:, 0]
LIGHT = int(np.argmax(_L))
DARK = int(np.argmin(_L))
P40 = machine.thread_profile(40)
P60 = machine.thread_profile(60)


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, "stitched": True, **meta})


def _network(thin_w=0.3, thick_w=0.8):
    """A 20 mm bar `thick_w` wide with a 20 mm strand `thin_w` wide crossing
    it at the middle: one connected shape, two widths."""
    thin = LineString([(0, -10), (0, 10)]).buffer(thin_w / 2, cap_style=2)
    thick = LineString([(-10, 0), (10, 0)]).buffer(thick_w / 2, cap_style=2)
    return unary_union([thin, thick]), thin, thick


def _plan(regions, palette_threads, **kw):
    palette = [{"brand": CHART.label, "brand_id": CHART.id, "number": CHART[t].number,
                "name": "x", "rgb": list(CHART[t].rgb)} for t in palette_threads]
    return plan_stitches(PipelineResult(regions=regions, palette=palette,
                                        background=BackgroundInfo(detected=False),
                                        px_per_mm=10.0, design_size_mm=(24.0, 24.0)),
                         PipelineConfig(**kw))


def _runs(plan):
    return [r for _b, r in plan.iter_runs()]


def _bbox(r):
    xs = [p[0] for p in r.points]
    ys = [p[1] for p in r.points]
    return min(xs), min(ys), max(xs), max(ys)


# --- 1. the gate is per branch ------------------------------------------------

def test_the_gate_reads_each_branch_on_its_own_width():
    poly, _thin, _thick = _network()
    m = measure(poly, P40.hairline_max_width_mm)
    assert m["admit"]
    assert m["hair_edges"] and m["thick_edges"]
    assert all(e["w"] <= P40.hairline_max_width_mm for e in m["hair_edges"])
    assert all(e["w"] > P40.hairline_max_width_mm for e in m["thick_edges"])
    # The thin strand's edges are the vertical ones, the thick bar's the horizontal.
    for e in m["hair_edges"]:
        xs = [p[0] for p in e["pts"]]
        assert max(xs) - min(xs) < 0.6
    for e in m["thick_edges"]:
        ys = [p[1] for p in e["pts"]]
        assert max(ys) - min(ys) < 0.6


def test_the_prototypes_one_number_for_the_network_is_neither_branchs_width():
    """The old gate read ONE number for the whole network (`width_mm`, kept
    as the shape's summary). It is neither branch's width, which is why a
    per-shape gate cannot be right for a network of mixed strands."""
    poly, _thin, _thick = _network()
    m = measure(poly, P40.hairline_max_width_mm)
    thin_w = max(e["w"] for e in m["hair_edges"])
    thick_w = min(e["w"] for e in m["thick_edges"])
    assert thin_w < 0.4 and thick_w > 0.7


def test_a_thin_branch_is_one_run_and_the_thick_one_keeps_todays_tier():
    poly, thin, thick = _network()
    reg = _region("Snet", poly, DARK, 0)
    on = _plan([reg], [DARK], hairline=True)
    off = _plan([reg], [DARK])
    runs = [r for r in _runs(on) if r.kind == "run"]
    # The thin strand: ONE pass, its own length, down its middle.
    assert len(runs) == 1
    r = runs[0]
    # Its own length in real stitches; the 0.8 mm lock legs the tie rule adds
    # at the ends are not part of the strand.
    steps = [math.dist(a, b) for a, b in zip(r.points, r.points[1:])]
    length = sum(s for s in steps if s >= machine.MIN_STITCH_MM - 1e-9)
    assert length == pytest.approx(20.0, rel=0.08)
    assert all(s >= machine.MIN_STITCH_MM - 1e-9 or s == pytest.approx(machine.TIE_STITCH_MM)
               for s in steps)
    x0, y0, x1, y1 = _bbox(r)
    assert max(abs(x0), abs(x1)) < 0.4 and y0 < -9.5 and y1 > 9.5
    # The thick bar: what it sews as with the tier OFF (a satin column), on
    # the bar and not on the strand. Nothing of it is a run.
    others = [q for q in _runs(on) if q.kind not in ("run", "tie")]
    assert {q.kind for q in others} == {q.kind for q in _runs(off) if q.kind != "tie"} - {"run"}
    assert any(q.kind == "satin" for q in others)
    for q in others:
        a, b, c, d = _bbox(q)
        assert d - b < 2.0          # no column along the 20 mm strand
    warn = next(w for w in on.warnings if w["code"] == "HAIRLINE_TIER_SEWN")
    assert warn["shapes"] == 1 and warn["strands"] == 1


def test_the_remainder_is_the_thick_bar_and_not_the_strand():
    poly, thin, thick = _network()
    m = measure(poly, P40.hairline_max_width_mm)
    rest = m["rest"]
    assert rest is not None
    assert rest.symmetric_difference(thick).area < 0.12 * thick.area
    assert rest.intersection(thin.difference(thick).buffer(-0.02)).area < 0.05
    # The hairline territory is the strand: everything of the shape off the rest.
    assert m["hair_geom"].symmetric_difference(poly.difference(rest)).area < 1e-9


def test_a_shape_thin_throughout_is_untouched():
    """No thick branch: no remainder, the whole polygon is the strand, as in
    the prototype and step 2 (the crossing test in `test_hairline_tier.py`
    pins its stitches)."""
    a = LineString([(0, 0), (20, 20)]).buffer(0.15)
    b = LineString([(0, 20), (20, 0)]).buffer(0.15)
    m = measure(unary_union([a, b]), P40.hairline_max_width_mm)
    assert m["admit"] and not m["thick_edges"]
    assert m["rest"] is None and m["hair_geom"] is None


def test_a_shape_thick_throughout_is_not_a_hairline():
    poly = LineString([(0, 0), (20, 0)]).buffer(0.5)
    m = measure(poly, P40.hairline_max_width_mm)
    assert m is None or (not m["admit"] and not m["hair_edges"])


def test_the_gate_follows_the_weight_branch_by_branch():
    """A 0.55 mm strand passes the 40 wt line (0.60) and fails the 60 wt one
    (0.48): the same network moves from thin to thick as the thread thins."""
    poly, _thin, _thick = _network(thin_w=0.55, thick_w=0.9)
    m40 = measure(poly, P40.hairline_max_width_mm)
    m60 = measure(poly, P60.hairline_max_width_mm)
    assert m40["admit"] and not m60["admit"]


def test_the_rest_planned_shape_is_offered_to_the_ladder_once():
    poly, _thin, _thick = _network()
    reg = _region("Snet", poly, DARK, 0)
    cfg = PipelineConfig(hairline=True)
    cands = hairline_candidates([reg], cfg)
    planned, _w = resolve_overlaps([reg], fabric_for(cfg), cfg, hairline=cands)
    p = planned[0]
    pieces = rest_planned(p, cands["Snet"])
    assert len(pieces) == 1 and pieces[0].shape_id == "Snet"
    rp = pieces[0]
    assert rp.region.polygon.equals(cands["Snet"]["rest"])
    assert p.polygon.buffer(0.01).contains(rp.polygon)
    assert rp.region.meta.get("_hairline_rest") is True
    assert "_hairline_rest" not in p.region.meta        # the original is untouched
    # Thin throughout: nothing is left to the ladder.
    thin = _region("Sthin", LineString([(0, 0), (10, 0)]).buffer(0.15), DARK, 0)
    tc = hairline_candidates([thin], cfg)
    tp, _w = resolve_overlaps([thin], fabric_for(cfg), cfg, hairline=tc)
    assert rest_planned(tp[0], tc["Sthin"]) == []


# --- 2. the ground goes under the hairline parts only ---------------------------

def test_the_ground_runs_under_the_thin_strand_and_not_the_thick_bar():
    """Four skin cells with the network cut out between them: the ground that
    goes under the strands (`_hairline_ground`) covers the thin strand's slot
    and leaves the thick bar's to the ladder, which sews it as its own shape.
    (The finished skin polygons cannot show this alone: their underlap
    tongue, a 0.4 mm slot's worth either side, reaches under a 0.8 mm bar
    whatever this does.)"""
    poly, thin, thick = _network()
    cells = [_region(f"Sskin{i}", box(x, y, x + 10, y + 10).difference(poly), LIGHT, 0)
             for i, (x, y) in enumerate([(-10, -10), (0, -10), (-10, 0), (0, 0)])]
    regions = cells + [_region("Snet", poly, DARK, 1)]
    cfg = PipelineConfig(hairline=True, hairline_over_ground=True)
    cands = hairline_candidates(regions, cfg)
    assert "Snet" in cands and cands["Snet"]["rest"] is not None
    under = unary_union(list(_hairline_ground(regions, cands, cfg, "flat").values()))
    thin_only = thin.difference(thick.buffer(0.45))
    bar_only = thick.difference(thin.buffer(0.45))
    assert under.intersection(thin_only).area >= 0.95 * thin_only.area
    assert under.intersection(bar_only).area <= 0.05 * bar_only.area
    # A shape thin throughout keeps step 2's reach: its whole polygon.
    tc = hairline_candidates(cells[:2] + [_region("Sthin", thin, DARK, 1)], cfg)
    assert tc["Sthin"]["hair_geom"] is None


# --- 3. the fixtures ------------------------------------------------------------

def test_hair_fine_is_the_same_hair_drawn_finer():
    coarse = fx.hair_strands()
    fine = fx.hair_strands(fine=True)
    assert len(fine) == len(coarse) == 40
    for (p0, _w0), (p1, _w1) in zip(coarse, fine):
        assert np.array_equal(p0, p1)                  # same crossings, same curls
    widths = [w for _p, w in fine]
    assert min(widths) >= 0.25 - 1e-9 and max(widths) <= 0.35 + 1e-9
    assert float(np.median(widths)) == pytest.approx(0.30, abs=1e-9)


def test_the_committed_hair_fine_png_is_what_the_script_draws(tmp_path):
    out = tmp_path / "hair_fine.png"
    fx.draw_hair(out, fine=True)
    a = cv2.imread(str(out), cv2.IMREAD_UNCHANGED)
    b = cv2.imread(str(SYN / "hair_fine.png"), cv2.IMREAD_UNCHANGED)
    assert a.shape == b.shape and np.array_equal(a, b)


def _fixture(name, wt):
    width = drawn_width_mm(SYN / name)
    base = dict(target_width_mm=width, forced_class="flat")
    result = run_stages(SYN / name, PipelineConfig(**base))
    stitched = [r for r in result.regions if r.meta.get("stitched", True)]
    cfg = PipelineConfig(**base, hairline=True, thread_wt=wt)
    cands = hairline_candidates(stitched, cfg, ink=result.ink_source)
    return result, cfg, cands


@pytest.fixture(scope="module")
def fine60():
    return _fixture("hair_fine.png", 60)


@pytest.fixture(scope="module")
def coarse60():
    return _fixture("hair_strands.png", 60)


def test_hair_fine_admits_at_60_weight_with_margin(fine60):
    _result, _cfg, cands = fine60
    lim = P60.hairline_max_width_mm
    assert cands
    net = max(cands.values(), key=lambda m: len(m["hair_edges"]))
    assert lim - net["width_mm"] >= 0.10, net["width_mm"]
    # And the network is run nearly whole: the few branches left to the
    # ladder are where the tracer fused neighbouring strands (measured 19 of
    # 338 branches, 2026-10-12).
    assert max(e["w"] for e in net["hair_edges"]) < lim
    assert len(net["thick_edges"]) <= 0.10 * (len(net["hair_edges"]) + len(net["thick_edges"]))


def test_hair_strands_thick_branches_go_to_the_ladder_and_thin_ones_to_runs(coarse60):
    result, cfg, cands = coarse60
    net = max(cands.values(), key=lambda m: len(m["hair_edges"]))
    lim = P60.hairline_max_width_mm
    assert net["hair_edges"] and net["thick_edges"]
    assert all(e["w"] <= lim for e in net["hair_edges"])
    # A thick branch is over the line, or a piece too short to read that sits
    # between branches that are (it follows its neighbours).
    over = [e for e in net["thick_edges"] if e["decided"]]
    assert over and all(e["w"] > lim or e["p95"] > 2 * lim for e in over)
    assert net["rest"] is not None and net["rest"].area > 1.0
    plan = plan_stitches(result, cfg)
    kinds = {}
    for b, r in plan.iter_runs():
        if b.thread_number == min(plan.blocks, key=lambda x: sum(x.rgb)).thread_number:
            kinds[r.kind] = kinds.get(r.kind, 0) + 1
    assert kinds.get("run", 0) > 0                       # the thin strands
    assert sum(v for k, v in kinds.items() if k not in ("run", "tie")) > 0   # the rest
    warn = next(w for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN")
    assert warn["strands"] > 0
