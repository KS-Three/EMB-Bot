"""`cfg.small_glyph_keep` (built OFF 2026-10-13): a rescued small glyph keeps
its counters, and its ink when its ground has no hole for it.

Kent's Hotel Fremont at 81 mm on a hat sewed "1895" as "098"
(`tools/fremont_triage.py`, `tests/test_fremont_triage.py`). Both losses are
stage 4's hole floor (`min_detail_mm`² / 4, 0.5625 mm²), which knows nothing
of what is in the hole:

- the 8's and 9's counters (0.30-0.52 mm²) were filled, so each digit sewed
  as the outline of a blob;
- the white ground's hole for the "1" (0.47 mm²) was filled, so the 1's whole
  artwork lay under an earlier colour and stage 5's clip by what is already
  down left nothing (SHAPE_NOT_STITCHED).

These pin both halves on synthetic geometry, and that OFF is byte-identical
(the flat-lane goldens' md5, as `test_small_print.py` pins them).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, machine
from digitizer_core.fabrics import get_fabric
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stage4_vectorize import vectorize
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.warnings_codes import SHAPE_NOT_STITCHED

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
PPM = 30.0


def test_flag_is_off_by_default():
    assert PipelineConfig().small_glyph_keep is False


# --- stage 4: a rescued small glyph's counters --------------------------------

def _eight(counter_px: int = 16, shell=(36, 51)):
    """An "8" the size of Fremont's at 81 mm (1.2 x 1.7 mm at 30 px/mm) with
    two square counters of `counter_px` px a side (16 px: 0.28 mm²)."""
    w, h = shell
    m = np.zeros((100, 100), bool)
    y0, x0 = 20, 30
    m[y0:y0 + h, x0:x0 + w] = True
    cx = x0 + (w - counter_px) // 2
    for cy in (y0 + 6, y0 + h - 6 - counter_px):
        m[cy:cy + counter_px, cx:cx + counter_px] = False
    return m


def _vectorize(mask, **kw):
    p = Prep(rgb=np.zeros(mask.shape + (3,), np.uint8), bg_mask=np.zeros(mask.shape, bool),
             px_per_mm=PPM, art_bbox=(0, 0, mask.shape[1], mask.shape[0]))
    regions, dropped = vectorize([RegionMask.from_full(mask, layer=0)], [0], p,
                                 PipelineConfig(**kw))
    assert not dropped and len(regions) == 1
    return regions[0]


def test_off_fills_a_small_glyphs_counters_on_keeps_them():
    off = _vectorize(_eight(), small_glyph_keep=False)
    on = _vectorize(_eight(), small_glyph_keep=True)
    assert off.meta["rescued_small_shape"] and on.meta["rescued_small_shape"]
    floor = 0.25 * PipelineConfig().min_detail_mm ** 2
    holes = [Polygon(r).area for r in on.polygon.interiors]
    assert len(off.polygon.interiors) == 0
    assert len(holes) == 2
    assert all(machine.RUN_MIN_AREA_MM2 <= a < floor for a in holes), holes
    assert on.polygon.exterior.equals(off.polygon.exterior)


def test_a_counter_under_the_run_floor_stays_filled():
    on = _vectorize(_eight(counter_px=10), small_glyph_keep=True)   # 0.11 mm²
    assert len(on.polygon.interiors) == 0


def test_a_shape_over_the_detail_floor_keeps_the_sliver_floor():
    """Only a rescued small shape's holes move: a big shape's 0.28 mm² hole
    is still filled ON, as it always was."""
    m = np.zeros((200, 200), bool)
    m[20:180, 20:180] = True
    m[90:106, 90:106] = False
    on = _vectorize(m, small_glyph_keep=True)
    assert "rescued_small_shape" not in on.meta
    assert len(on.polygon.interiors) == 0


# --- stage 5: a rescued small glyph its ground has no hole for -----------------

FABRIC = get_fabric("structured_cap")


def _region(sid, poly, layer, **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=layer,
                  thread_number=f"{1000 + layer}", area_mm2=float(poly.area),
                  meta={"layer": layer, **meta})


def _ground_and_one(rescued: bool = True, glyph=None):
    """The Fremont "1": a 0.2 x 2 mm stroke on a white ground whose hole for
    it fell under stage 4's floor, so the ground covers it whole."""
    ground = _region("ground", box(0, 0, 20, 10), 0, tier="fill")
    one = _region("one", glyph or box(10, 4, 10.25, 6), 1,
                  **({"rescued_small_shape": True} if rescued else {}))
    return [ground, one]


def _plan(regions, **kw):
    return resolve_overlaps(regions, FABRIC, PipelineConfig(**kw))


def _lost(warnings):
    return [i for w in warnings if w["code"] == SHAPE_NOT_STITCHED for i in w.get("ids", [])]


def test_off_loses_the_glyph_under_its_ground_on_sews_its_ink():
    regs = _ground_and_one()
    off, off_w = _plan(regs, small_glyph_keep=False)
    assert "one" not in [p.shape_id for p in off]
    assert _lost(off_w) == ["one"]

    on, on_w = _plan(regs, small_glyph_keep=True)
    one = next(p for p in on if p.shape_id == "one")
    assert one.polygon.equals(regs[1].polygon), "the artwork, ungrown"
    assert not _lost(on_w)
    # The ground plans exactly as it did.
    g_off = next(p for p in off if p.shape_id == "ground")
    g_on = next(p for p in on if p.shape_id == "ground")
    assert g_on.polygon.equals_exact(g_off.polygon, 0.0)


def test_a_shape_that_is_not_a_rescued_glyph_is_still_clipped():
    regs = _ground_and_one(rescued=False)
    on, on_w = _plan(regs, small_glyph_keep=True)
    assert "one" not in [p.shape_id for p in on]
    assert _lost(on_w) == ["one"]


def test_a_glyph_with_ink_left_after_the_clip_plans_as_before():
    """Half the stroke runs off the ground: the clip leaves ink, so ON is the
    clip exactly."""
    regs = _ground_and_one(glyph=box(10, 8, 10.25, 12))
    off, _ = _plan(regs, small_glyph_keep=False)
    on, _ = _plan(regs, small_glyph_keep=True)
    a = next(p for p in off if p.shape_id == "one")
    b = next(p for p in on if p.shape_id == "one")
    assert b.polygon.equals_exact(a.polygon, 0.0)


# --- OFF is byte-identical -----------------------------------------------------

# The flat-lane goldens' stitch streams, as `test_small_print.py` pins them.
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
    """OFF is the engine as it was. ON too, on these three: none has a
    rescued small shape with a hole or one sitting wholly on a ground."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            small_glyph_keep=flag))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
