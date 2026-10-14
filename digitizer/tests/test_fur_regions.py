"""Fur regions on the streamline tier (`cfg.hair_regions_directional`, OFF).

`digitizer_core/fur_regions.py`: a region the hair gate (the line route's
ridge test) reads as a strand FIELD sews on the per-shape `streamline` tier.
These pin: OFF is byte-identical (the flat-lane goldens' md5s), the flat lane
is never read, the gate on drawn rasters (a strand field is fur, a flat patch
and a single strand are not), the route is a copy that an override beats,
and the end-to-end switch: a fur region sews streamline runs ON and tatami
OFF, and a result built without the gate routes nothing.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, fur_regions, stitches
from digitizer_core.pipeline import (BackgroundInfo, PipelineResult, digitize,
                                     plan_stitches)
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.threads import chart_for
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

CHART = chart_for(PipelineConfig())
PX_MM = 10.0
W_MM, H_MM = 70.0, 40.0
GROUND = (200, 180, 150)
STRAND = (70, 50, 30)


def _canvas():
    w, h = int(W_MM * PX_MM), int(H_MM * PX_MM)
    img = np.full((h, w, 3), 245, np.uint8)
    return img, (w / 2.0, h / 2.0)


def _px(x_mm, y_mm, origin):
    return int(round(x_mm * PX_MM + origin[0])), int(round(y_mm * PX_MM + origin[1]))


def _drawn():
    """Three 20 x 20 mm patches of one tan ground, left to right: a FIELD of
    short dark strands (fur), a flat patch, and one long strand alone."""
    img, o = _canvas()
    patches = {"fur": (-30.0, -10.0), "flat": (-10.0, -10.0), "single": (10.0, -10.0)}
    for x0, y0 in patches.values():
        cv2.rectangle(img, _px(x0, y0, o), _px(x0 + 20, y0 + 20, o), GROUND, -1)
    fx, fy = patches["fur"]
    rng = np.random.default_rng(7)
    # Short strands, 5 mm long, one row per mm, staggered: a fur texture
    # about 0.8 mm of strand per mm2.
    for row in range(19):
        y = fy + 1.0 + row * 1.0
        x = fx + 0.5 + (row % 3) * 2.0 - 2.0
        while x < fx + 19.5:
            a = math.radians(8 + rng.uniform(-4, 4))
            p = (max(x, fx + 0.5), y)
            q = (min(x + 5.0 * math.cos(a), fx + 19.5), y + 5.0 * math.sin(a) * 0.2)
            if q[0] - p[0] > 1.0:
                cv2.line(img, _px(*p, o), _px(*q, o), STRAND, 2, cv2.LINE_AA)
            x += 6.0
    sx, sy = patches["single"]
    cv2.line(img, _px(sx + 10, sy + 2, o), _px(sx + 10, sy + 18, o), STRAND, 2, cv2.LINE_AA)
    sp = SourcePixels(rgb=cv2.cvtColor(img, cv2.COLOR_BGR2RGB), px_per_mm=PX_MM, origin_px=o)
    regions = [Region(shape_id=f"S_{k}", polygon=box(x0, y0, x0 + 20, y0 + 20), thread_index=3,
                      thread_number=CHART[3].number, area_mm2=400.0,
                      meta={"layer": 0, "stitched": True})
               for k, (x0, y0) in patches.items()]
    return sp, regions


# --- OFF ----------------------------------------------------------------------

def test_the_flag_is_off_by_default():
    assert PipelineConfig().hair_regions_directional is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical_to_the_golden(fixture):
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            hair_regions_directional=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]


def test_the_flat_lane_is_never_read():
    on = PipelineConfig(hair_regions_directional=True)
    assert not fur_regions.applies(on, "flat")
    assert not fur_regions.applies(PipelineConfig(), "gradient")
    for cls in ("gradient", "photo_scene", "photo_subject"):
        assert fur_regions.applies(on, cls)


def test_a_flat_logo_is_unchanged_with_the_flag_on():
    """The flat lane never reads, so ON is the golden too."""
    fixture = "logo_alpha.png"
    result, plan = digitize(TESTDATA / fixture,
                            PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                           hair_regions_directional=True))
    assert result.hair_fur_read is None and result.hair_fur_ids is None
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _coords_md5(coords) == GOLDEN_MD5[fixture]


# --- the gate -----------------------------------------------------------------

def test_a_strand_field_is_fur_and_a_flat_patch_or_one_strand_is_not():
    sp, regions = _drawn()
    read = fur_regions.read_regions(regions, sp, PipelineConfig())
    fur, flat, single = read["S_fur"], read["S_flat"], read["S_single"]
    assert fur["fur"], fur
    assert fur["strands"] >= fur_regions.FUR_MIN_STRANDS
    assert fur["density"] >= fur_regions.FUR_MIN_STRAND_DENSITY
    assert not flat["fur"] and flat["strands"] == 0, flat
    assert not single["fur"] and single["strands"] < fur_regions.FUR_MIN_STRANDS, single


def test_the_gate_skips_small_and_overridden_regions():
    sp, regions = _drawn()
    regions[0].meta["tier"] = "satin"
    tiny = Region(shape_id="S_tiny", polygon=box(-29, -9, -26, -6), thread_index=3,
                  thread_number=CHART[3].number, area_mm2=9.0,
                  meta={"layer": 0, "stitched": True})
    read = fur_regions.read_regions([*regions, tiny], sp, PipelineConfig())
    assert "S_fur" not in read            # a per-shape tier is the user's
    assert not read["S_tiny"]["fur"]      # under the area floor: a strand, not a field


# --- the route ----------------------------------------------------------------

def test_route_is_a_copy_and_an_override_wins():
    _sp, regions = _drawn()
    regions[1].meta["tier"] = "fill"
    out = fur_regions.route(regions, ["S_fur", "S_flat"])
    by = {r.shape_id: r for r in out}
    assert by["S_fur"].meta["tier"] == "streamline"
    assert by["S_flat"].meta["tier"] == "fill"            # override kept
    assert "tier" not in by["S_single"].meta
    assert "tier" not in regions[0].meta                   # caller untouched


def _result(sp, regions, fur_ids, design_class="photo_scene"):
    palette = [{"brand": CHART.label, "brand_id": CHART.id, "number": CHART[3].number,
                "name": "x", "rgb": list(CHART[3].rgb)}]
    return PipelineResult(regions=regions, palette=palette,
                          background=BackgroundInfo(detected=False), px_per_mm=PX_MM,
                          design_size_mm=(W_MM, H_MM), source_pixels=sp,
                          design_class=design_class, hair_fur_ids=fur_ids)


def _md5(plan):
    return _coords_md5([[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
                        for _, r in plan.iter_runs() for x, y in r.points])


def test_a_fur_region_sews_streamline_on_and_tatami_off():
    sp, regions = _drawn()
    fur_only = [regions[0]]
    res = _result(sp, fur_only, ("S_fur",))
    off = plan_stitches(res, PipelineConfig(hair_regions_directional=False))
    on = plan_stitches(res, PipelineConfig(hair_regions_directional=True))
    assert _md5(off) != _md5(on)
    # Exactly the review screen's own route: the region's `tier` set to
    # streamline (what `apply_shape_overrides` writes), the flag off.
    forced = fur_regions.route(fur_only, ("S_fur",))
    streamline = plan_stitches(_result(sp, forced, None), PipelineConfig())
    assert _md5(on) == _md5(streamline)
    assert all(r.kind != stitches.UNDERLAY for _, r in on.iter_runs())


def test_where_every_fill_is_already_streamline_nothing_moves():
    """photo_subject's auto-route sews every fill streamline already; a
    per-shape tier there only took the shape off the `auto` paths (the owl's
    `classical` route moved at 0.25 in the census for exactly that)."""
    sp, regions = _drawn()
    res = _result(sp, [regions[0]], ("S_fur",), design_class="photo_subject")
    off = plan_stitches(res, PipelineConfig(hair_regions_directional=False))
    on = plan_stitches(res, PipelineConfig(hair_regions_directional=True))
    assert _md5(off) == _md5(on)
    res = _result(sp, [regions[0]], ("S_fur",))
    off = plan_stitches(res, PipelineConfig(fill_technique="streamline"))
    on = plan_stitches(res, PipelineConfig(fill_technique="streamline",
                                           hair_regions_directional=True))
    assert _md5(off) == _md5(on)


def test_a_result_built_without_the_gate_routes_nothing():
    sp, regions = _drawn()
    res = _result(sp, [regions[0]], None)
    off = plan_stitches(res, PipelineConfig(hair_regions_directional=False))
    on = plan_stitches(res, PipelineConfig(hair_regions_directional=True))
    assert _md5(off) == _md5(on)
