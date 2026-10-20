"""`cfg.small_dot_rung` (built OFF 2026-10-14, ON with its lettering scope
since 2026-10-20, Kent's flip): a closed part under the run
tier's loop floor -- the dot of a small i or j -- is admitted and sewn as a
tack ring instead of being dropped. `machine.RUN_MIN_LOOP_MM` is untouched
(ROADMAP gate 1); the rung's numbers are candidates. `tools/small_dot_rung.py`
carries the measurements.

Pinned here: the run tier sews an OUTER ring in the rung's band and still
skips a HOLE ring there (sewing Fremont's 8 counter ring shut it); stage 3
admits a dot standing on its ground but not a small glyph's counter; the
80 mm synthetic word's dots sew ON and drop OFF; and OFF is byte-identical
(the flat-lane goldens' md5, as `test_small_glyph_keep.py` pins them).
"""
from __future__ import annotations

import hashlib
import json
import math

import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, digitize, machine
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.stage6_border import run_outline
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA


def test_flag_defaults_on_and_the_floor_is_untouched():
    """ON since 2026-10-20 (Kent, MASTER_SCOPE item 52; PR #991's renders),
    scoped to lettering, so `PRE_FLIP` pins both False; the loop floor is a
    gate-1 cloth value and did not move with the flip."""
    from .conftest import PRE_FLIP
    cfg = PipelineConfig()
    assert cfg.small_dot_rung is True and cfg.small_dot_rung_lettering is True
    assert PRE_FLIP["small_dot_rung"] is False and PRE_FLIP["small_dot_rung_lettering"] is False
    assert machine.RUN_MIN_LOOP_MM == 2.2
    assert machine.DOT_RUNG_MIN_LOOP_MM == pytest.approx(3 * machine.DOT_RUNG_STITCH_MM)
    assert machine.DOT_RUNG_MIN_LOOP_MM < machine.RUN_MIN_LOOP_MM


# --- the run tier ------------------------------------------------------------------

def _disc(ring_mm: float, centre=(0.0, 0.0)) -> Polygon:
    return Point(centre).buffer(ring_mm / (2 * math.pi), 64)


def test_a_sub_floor_outline_is_skipped_off_and_tacked_on():
    dot = _disc(1.8)
    assert machine.DOT_RUNG_MIN_LOOP_MM <= dot.exterior.length < machine.RUN_MIN_LOOP_MM
    off_runs, off = run_outline(dot, "d", entry=None, trim_at_mm=3.0)
    assert off["empty"] and not off_runs
    runs, rep = run_outline(dot, "d", entry=None, trim_at_mm=3.0, dot_rung=True)
    assert not rep["empty"] and rep["dot_rings"] == 1 and len(runs) == 1
    pts = runs[0].points
    n = max(3, round(dot.exterior.length / machine.DOT_RUNG_STITCH_MM))
    assert len(pts) == n * machine.DOT_RUNG_PASSES + 1
    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(steps) <= machine.DOT_RUNG_STITCH_MM * 1.25


def test_under_the_rung_floor_still_drops():
    runs, rep = run_outline(_disc(1.2), "d", entry=None, trim_at_mm=3.0, dot_rung=True)
    assert rep["empty"] and rep["dot_rings"] == 0


def test_a_ring_over_the_floor_sews_the_same_either_way():
    poly = _disc(3.0)
    a, _ = run_outline(poly, "d", entry=(5.0, 0.0), trim_at_mm=3.0)
    b, rep = run_outline(poly, "d", entry=(5.0, 0.0), trim_at_mm=3.0, dot_rung=True)
    assert [r.points for r in a] == [r.points for r in b] and rep["dot_rings"] == 0


def test_a_sub_floor_hole_ring_is_never_tacked():
    """Fremont 81 mm Hat's 8: tacking its 2.05 mm counter ring shut that
    counter (1895 legibility 0.551 -> 0.426). The rung sews parts, not holes."""
    hole = list(_disc(2.0).exterior.coords)
    eight = Polygon(list(_disc(6.0).exterior.coords), [hole])
    off, off_rep = run_outline(eight, "e", entry=None, trim_at_mm=3.0)
    on, on_rep = run_outline(eight, "e", entry=None, trim_at_mm=3.0, dot_rung=True)
    assert [r.points for r in off] == [r.points for r in on]
    assert on_rep["loops"] == 1 and on_rep["dot_rings"] == 0


# --- stage 3: a dot on its ground, not a small glyph's counter ---------------------

PX = 30.0
FRAME = (200, 200)
RGB = np.array([(255, 255, 255), (0, 0, 0), (0, 0, 0), (255, 255, 255)], float)


def _mask(m: np.ndarray, layer: int) -> RegionMask:
    return RegionMask.from_full(m, layer)


def _scene():
    """A white panel holding a black 18 x 18 px dot (0.36 mm², 0.6 mm
    across: 2 x max(w, h) 1.2 mm, under both floors; isoperimetric bound
    2.13 mm, over the rung's 1.35) and a black 30 x 30 px "o" (0.78 mm²) whose
    14 x 14 px white counter (0.22 mm²) is a region of its own."""
    dot = np.zeros(FRAME, bool)
    dot[40:58, 40:58] = True
    o = np.zeros(FRAME, bool)
    o[100:130, 100:130] = True
    counter = np.zeros(FRAME, bool)
    counter[108:122, 108:122] = True
    o &= ~counter
    panel = np.zeros(FRAME, bool)
    panel[10:190, 10:190] = True
    panel &= ~dot & ~o & ~counter
    return [_mask(panel, 0), _mask(dot, 1), _mask(o, 2), _mask(counter, 3)]


def _kept(on: bool):
    regions = _scene()
    # The unscoped rung: this scene's dot has no stem, which the lettering
    # scope (ON by default since 2026-10-20) would refuse; the scope's own
    # stage-3 tests are in `tests/test_dot_rung_lettering.py`.
    cfg = PipelineConfig(small_dot_rung=on, small_dot_rung_lettering=False)
    kept, _w = resolve_small_regions(regions, cfg, PX,
                                     layer_lab=rgb_to_lab(RGB))
    return regions, kept


def test_the_scene_is_what_its_docstring_says():
    cfg = PipelineConfig()
    assert (cfg.min_detail_mm * PX) ** 2 > 30 * 30
    assert machine.RUN_MIN_AREA_MM2 * PX ** 2 < 14 * 14
    assert 2 * 18 < machine.DOT_RUNG_MIN_LOOP_MM * PX
    assert 2 * math.sqrt(math.pi * 14 * 14) >= machine.DOT_RUNG_MIN_LOOP_MM * PX
    assert 2 * math.sqrt(math.pi * 18 * 18) < machine.RUN_MIN_LOOP_MM * PX


def test_stage3_keeps_the_dot_on_and_not_off():
    regions, off = _kept(False)
    assert not any(k is regions[1] for k in off)
    regions, on = _kept(True)
    assert any(k is regions[1] for k in on)


def test_stage3_never_keeps_a_small_glyphs_counter():
    """The first cut kept Fremont's 8 and 9 counters as white runs."""
    for on in (False, True):
        regions, kept = _kept(on)
        assert not any(k is regions[3] for k in kept)


# --- the whole pipeline: the 80 mm synthetic dots ------------------------------------

def test_the_80mm_synthetic_dots_sew_on_and_drop_off(tmp_path):
    from tools.small_dot_rung import WORD, dot_cases, dots
    import tools.small_dot_rung as sdr
    word = [c for c in dot_cases(tmp_path) if c[0] == f"word {WORD}"]
    real = sdr.dot_cases
    sdr.dot_cases = lambda _tmp: word
    try:
        off, on = dots(False, tmp_path)[0], dots(True, tmp_path)[0]
    finally:
        sdr.dot_cases = real
    assert off["dots_in_art"] == on["dots_in_art"] == 4
    assert off["dots_sewn"] == 0 and off["dropped_small_shapes"] > 0
    assert on["dots_sewn"] == 4 and on["dropped_small_shapes"] == 0
    assert on["shape_not_stitched"] == 0
    assert on["stitches"] > off["stitches"]


# --- OFF is byte-identical ----------------------------------------------------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("flag", [False, True])
def test_goldens_are_byte_identical_either_way(fixture, flag):
    """OFF is the engine as it was. ON too, on these three: none has a part
    in the rung's band (the census, `tools/small_dot_rung.py census`)."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            small_dot_rung=flag,
                                            small_dot_rung_lettering=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
