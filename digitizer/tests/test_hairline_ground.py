"""Hairline step 2 (2026-10-12): the ground under the strands, the width read
off the source, and the ground-fragment rule. docs/hairline-ground-2026-10-12.md.

Everything here is DEFAULT OFF (`cfg.hairline`, `cfg.hairline_over_ground`)
and every number is a candidate until the card is sewn (ROADMAP gate 1).
"""
from __future__ import annotations

import json
import math

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, box

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import (BackgroundInfo, PipelineResult, digitize, fabric_for,
                                     plan_stitches, run_stages)
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_hairline import InkSource, hairline_candidates, measure
from digitizer_core.threads import chart_for
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5
from tools import draw_hair_fixtures as fx

CHART = chart_for(PipelineConfig())
_L = CHART.lab[:, 0]
LIGHT = int(np.argmax(_L))     # the chart's lightest thread: a "skin" ground
DARK = int(np.argmin(_L))      # the darkest: a "hair" strand


def _region(sid, poly, thread, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer, "stitched": True, **meta})


# --- 0. OFF is byte-identical -----------------------------------------------

@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_ground_flag_alone_is_byte_identical_to_the_golden(fixture):
    """#848's pins (`test_thread_profile.GOLDEN_MD5`, the golden FILE's md5
    written into the test): `hairline_over_ground` without `hairline` is
    inert, and both new defaults stay today's stream."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            thread_wt=40, hairline=False,
                                            hairline_over_ground=True))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]


# --- 1. the width read off the source (finding 1) ----------------------------

def _s_curve(n=400):
    t = np.linspace(0.0, 1.0, n)
    return np.column_stack([4.0 + 22.0 * t, 8.0 + 3.0 * np.sin(2 * math.pi * t)])


@pytest.fixture(scope="module")
def drawn_stroke(tmp_path_factory):
    """A 0.35 mm dark stroke drawn the way the hair fixture draws its strands
    (`draw_hair_fixtures._stroke`, 20 px/mm, aliased) over a skin oval on
    transparency, traced by the real pipeline. -> (result, the strand region,
    the DRAWN width: ink pixels' area over the centreline's length)."""
    img = fx._canvas(30, 16)
    s = fx.PX_PER_MM
    cv2.ellipse(img, (int(15 * s), int(8 * s)), (int(14 * s), int(7.5 * s)), 0, 0, 360,
                (*fx.SKIN, 255), -1, cv2.LINE_8)
    pts = _s_curve()
    fx._stroke(img, pts, 0.35, fx.HAIR)
    ink = np.all(img[..., :3] == np.array(fx.HAIR, np.uint8), axis=-1) & (img[..., 3] > 0)
    drawn = float(ink.sum()) / (s * s) / LineString(pts).length
    path = tmp_path_factory.mktemp("hair") / "stroke.png"
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    # Sized so the design's mm ARE the drawing's mm (the art box at 20 px/mm).
    xs = np.nonzero(img[..., 3].any(axis=0))[0]
    width_mm = (xs.max() - xs.min() + 1) / s
    result = run_stages(path, PipelineConfig(target_width_mm=width_mm, forced_class="flat"))
    assert result.px_per_mm == pytest.approx(s, rel=1e-3)
    hair_lab = CHART.lab  # nearest-by-L* is enough: two colours, far apart
    strand = min((r for r in result.regions if r.meta.get("stitched", True)),
                 key=lambda r: hair_lab[r.thread_index][0])
    return result, strand, drawn


def test_the_drawn_stroke_is_what_the_fixture_says(drawn_stroke):
    _result, _strand, drawn = drawn_stroke
    assert abs(drawn - 0.35) <= 0.03, drawn


def test_the_traced_width_misreads_and_the_source_read_does_not(drawn_stroke):
    """Measured 2026-10-12: a LONE 0.33 mm stroke traces THIN (0.24 mm
    median; the polygon's own area over length is 0.28), where the hair
    network traced 0.11 mm FAT (finding 1, cells absorbed at crossings). The
    tracer's error has no fixed sign, which is the case for reading the
    source rather than correcting the trace by a constant. The fat case is
    `test_the_source_read_reads_an_upscaled_source_in_its_own_frame`."""
    result, strand, drawn = drawn_stroke
    traced = measure(strand.polygon, 0.6)
    assert traced["width_source_mm"] is None          # no ink given: the prototype's read
    assert abs(traced["width_mm"] - drawn) >= 0.05, (traced["width_mm"], drawn)
    m = measure(strand.polygon, 0.6, ink=result.ink_source)
    assert m["width_source_mm"] is not None
    assert abs(m["width_source_mm"] - drawn) <= 0.03, (m["width_source_mm"], drawn)
    assert m["width_mm"] == m["width_source_mm"]       # the gate reads the source
    assert m["width_traced_mm"] == pytest.approx(traced["width_mm"])


def test_sixty_weight_admits_the_drawn_stroke_with_margin_from_the_source(drawn_stroke):
    result, strand, drawn = drawn_stroke
    lim = machine.thread_profile(60).hairline_max_width_mm          # 0.48
    m = measure(strand.polygon, lim, ink=result.ink_source)
    assert m["admit"] and lim - m["width_mm"] >= 0.1


def test_no_contrast_edge_falls_back_to_the_traced_width():
    """An opaque source of ONE colour has no edge to read: the gate keeps the
    traced width rather than read zero."""
    poly = LineString([(-5, 0), (5, 0)]).buffer(0.2, cap_style=2)
    flat = np.full((200, 400, 3), 128, np.uint8)
    ink = InkSource(rgb=flat, alpha=None, bg=None, upscale=(1.0, 1.0),
                    px_per_mm=20.0, origin_px=(200.0, 100.0))
    m = measure(poly, 0.6, ink=ink)
    assert m["width_source_mm"] is None
    assert m["width_mm"] == m["width_traced_mm"]


def test_the_source_read_reads_an_upscaled_source_in_its_own_frame():
    """Stage 1's upscale: the traced grid is 3x the source's. A 0.4 mm bar
    drawn on the SOURCE (8 px/mm, so 3.2 px, anti-aliased) reads 0.4 through
    `to_src`'s half-pixel-centre mapping."""
    src_ppm, up = 8.0, 3.0
    h, w = 80, 160
    yy = (np.arange(h) + 0.5) / src_ppm - h / 2 / src_ppm      # mm from centre
    cov = np.clip(0.2 - np.abs(yy) + 0.5 / src_ppm, 0, 1.0 / src_ppm) * src_ppm
    a = np.repeat(cov[:, None], w, axis=1)
    rgb = np.full((h, w, 3), 30, np.uint8)
    alpha = (a * 255).round().astype(np.uint8)
    ink = InkSource(rgb=rgb, alpha=alpha, bg=None, upscale=(up, up),
                    px_per_mm=src_ppm * up, origin_px=(w * up / 2.0, h * up / 2.0))
    poly = box(-8, -0.26, 8, 0.26)                      # the tracer's fatter 0.52
    m = measure(poly, 0.6, ink=ink)
    assert m["width_traced_mm"] == pytest.approx(0.52, abs=0.04)
    assert m["width_source_mm"] == pytest.approx(0.4, abs=0.03)


# --- 2. the ground-fragment rule (finding 4) ---------------------------------

def test_a_sliver_of_the_ground_colour_is_not_a_hairline():
    """Skin cells with two dark strands between them, and a thin skin sliver
    pinched between the strands: the strands qualify, the sliver does not —
    it is lighter than what surrounds it, and its colour fills an area."""
    cfg = PipelineConfig(hairline=True)
    skin_a = _region("Sskina", box(-10, -10, 10, -0.5), LIGHT, 0)
    skin_b = _region("Sskinb", box(-10, 0.5, 10, 10), LIGHT, 0)
    sliver = _region("Ssliver", box(-10, -0.2, 10, 0.2), LIGHT, 0)
    s1 = _region("Sstrand1", box(-10, -0.5, 10, -0.2), DARK, 1)
    s2 = _region("Sstrand2", box(-10, 0.2, 10, 0.5), DARK, 1)
    regions = [skin_a, skin_b, sliver, s1, s2]
    got = hairline_candidates(regions, cfg)
    assert set(got) == {"Sstrand1", "Sstrand2"}
    assert got.fragments == {"Ssliver"}      # handed back to the ground


def test_the_sliver_rule_leaves_the_ground_colour_alone_in_the_plan():
    """Through stage 7: the sliver sews on the ladder as it did with the tier
    off (not as a one-thread run), and only the strands are counted."""
    regions = [_region("Sskina", box(-10, -10, 10, -0.5), LIGHT, 0),
               _region("Sskinb", box(-10, 0.5, 10, 10), LIGHT, 0),
               _region("Ssliver", box(-10, -0.2, 10, 0.2), LIGHT, 0),
               _region("Sstrand1", box(-10, -0.5, 10, -0.2), DARK, 1),
               _region("Sstrand2", box(-10, 0.2, 10, 0.5), DARK, 1)]
    palette = [{"brand": CHART.label, "brand_id": CHART.id, "number": CHART[t].number,
                "name": "x", "rgb": list(CHART[t].rgb)} for t in (LIGHT, DARK)]

    def plan(**kw):
        return plan_stitches(PipelineResult(regions=regions, palette=palette,
                                            background=BackgroundInfo(detected=False),
                                            px_per_mm=10.0, design_size_mm=(20.0, 20.0)),
                             PipelineConfig(**kw))

    def sliver(p):
        return [(r.kind, [tuple(map(lambda v: round(v, 4), q)) for q in r.points])
                for _b, r in p.iter_runs() if r.shape_id == "Ssliver"]

    on = plan(hairline=True)
    assert sliver(on) and sliver(on) == sliver(plan())
    warn = next(w for w in on.warnings if w["code"] == "HAIRLINE_TIER_SEWN")
    assert warn["shapes"] == 2


def test_a_thin_dark_line_of_a_filled_colour_still_qualifies():
    """The same dark thread filling a block AND drawing a hairline on the
    garment: the line touches no other colour, so it is not a ground fragment."""
    cfg = PipelineConfig(hairline=True)
    block = _region("Sblock", box(-10, -10, 10, -2), DARK, 0)
    line = _region("Sline", box(-10, 2, 10, 2.35), DARK, 0)
    got = hairline_candidates([block, line], cfg)
    assert set(got) == {"Sline"}


def test_a_thin_shape_of_a_colour_with_no_area_always_qualifies():
    cfg = PipelineConfig(hairline=True)
    ground = _region("Sground", box(-10, -10, 10, 10).difference(box(-8, -0.2, 8, 0.2)), DARK, 0)
    light = _region("Slight", box(-8, -0.2, 8, 0.2), LIGHT, 1)
    assert set(hairline_candidates([ground, light], cfg)) == {"Slight"}


# --- 3. the ground under the strands (finding 3) -----------------------------

def _skin_with_strand():
    """A 20 x 20 mm skin field with one 0.45 mm strand cut out of it as a
    HOLE (how stage 4 traces a strand inside a field), and a second strand
    that splits the field at a crossing into two cells."""
    strand = LineString([(-8, -4), (8, 4)]).buffer(0.225, cap_style=2)
    cut = LineString([(0, -10), (0, 10)]).buffer(0.2, cap_style=2)
    field = box(-10, -10, 10, 10)
    left = field.intersection(box(-10, -10, -0.2, 10)).difference(strand)
    right = field.intersection(box(0.2, -10, 10, 10)).difference(strand)
    hair = strand.union(cut)
    regions = [_region("Sleft", left, LIGHT, 0), _region("Sright", right, LIGHT, 0),
               _region("Shair", hair, DARK, 1)]
    return regions, hair


def _planned(regions, **kw):
    cfg = PipelineConfig(hairline=True, **kw)
    cands = hairline_candidates(regions, cfg)
    planned, _w = resolve_overlaps(regions, fabric_for(cfg), cfg, hairline=cands)
    return {p.region.shape_id: p for p in planned}, cands


def test_the_ground_keeps_its_full_polygon_under_every_strand():
    regions, hair = _skin_with_strand()
    on, cands = _planned(regions, hairline_over_ground=True)
    assert "Shair" in cands
    ground = on["Sleft"].polygon.union(on["Sright"].polygon)
    inside = hair.intersection(box(-10, -10, 10, 10)).buffer(-0.02)
    assert ground.contains(inside)
    # The skin's own artwork is all still there: nothing was cut away.
    for sid in ("Sleft", "Sright"):
        art = next(r for r in regions if r.shape_id == sid).polygon
        assert on[sid].polygon.contains(art.buffer(-0.02))


def _strand_in_a_hole():
    """One strand traced as a HOLE in the skin: today stage 5 shrinks the
    hole by the pull, finds it would close, and holds it open at its traced
    size — the ground is knocked out from under the strand."""
    strand = LineString([(-6, -2), (6, 2)]).buffer(0.225, cap_style=1)
    skin = box(-10, -10, 10, 10).difference(strand)
    return [_region("Sskin", skin, LIGHT, 0), _region("Sstrand", strand, DARK, 1)], strand


def test_without_the_ground_flag_a_strand_hole_is_held_open():
    regions, strand = _strand_in_a_hole()
    off, cands = _planned(regions)
    assert "Sstrand" in cands
    assert len(off["Sskin"].polygon.interiors) == 1
    assert off["Sskin"].polygon.intersection(strand).area < 0.05 * strand.area


def test_with_the_ground_flag_a_strand_hole_is_filled_under_the_strand():
    regions, strand = _strand_in_a_hole()
    on, _ = _planned(regions, hairline_over_ground=True)
    assert len(on["Sskin"].polygon.interiors) == 0
    assert on["Sskin"].polygon.contains(strand.buffer(-0.02))


def test_a_ground_sewn_after_the_strand_does_not_reach_under_it():
    regions, hair = _skin_with_strand()
    regions = [_region(r.shape_id, r.polygon, r.thread_index, 2 if r.thread_index == LIGHT else 1)
               for r in regions]
    on, _ = _planned(regions, hairline_over_ground=True)
    off, _ = _planned(regions)
    for sid in ("Sleft", "Sright"):
        assert on[sid].polygon.equals(off[sid].polygon)


def test_the_ground_sews_first_and_the_strands_sew_on_top_as_runs():
    regions, hair = _skin_with_strand()
    cfg = PipelineConfig(hairline=True, hairline_over_ground=True)
    chart = chart_for(cfg)
    palette = [{"brand": chart.label, "brand_id": chart.id, "number": CHART[t].number,
                "name": "x", "rgb": list(CHART[t].rgb)} for t in (LIGHT, DARK)]
    plan = plan_stitches(PipelineResult(regions=regions, palette=palette,
                                        background=BackgroundInfo(detected=False),
                                        px_per_mm=10.0, design_size_mm=(20.0, 20.0)), cfg)
    order = [(b.thread_index, r.kind, r.shape_id) for b, r in plan.iter_runs()]
    first_hair = next(i for i, (t, _k, _s) in enumerate(order) if t == DARK)
    assert all(t == LIGHT for t, _k, _s in order[:first_hair])
    assert any(k == "fill" for _t, k, _s in order[:first_hair])
    assert {k for t, k, _s in order[first_hair:] if t == DARK} <= {"run", "tie"}
    warn = next(w for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN")
    assert warn["shapes"] == 1
