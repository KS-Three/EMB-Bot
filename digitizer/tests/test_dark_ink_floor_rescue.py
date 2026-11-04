"""`cfg.dark_ink_floor_rescue` (built OFF 2026-11-03): a dark-ink carve under
stage 3's detail floor is kept for the lettering path instead of absorbed,
the dark read's kernel/width test reads `dark_ink_read_floor_mm` instead of a
coarser `min_detail_mm`, and a rescued stroke no text cluster claims is
dropped, counted with the dropped shapes.

Measured on Kent's Pooh pot (PR body): the fifth letter at 54.6 mm was never
a stage-3 absorb -- `min_detail_mm` feeds the dark read's kernel, so the 25 px
kernel closed it into the ground. Lowering `min_detail_mm` tests both
mechanisms at once; these tests hold them apart.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.regions import Region
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions
from digitizer_core.thin_ink import drop_unclaimed_floor_rescues
from digitizer_core.warnings_codes import ABSORBED_SMALL_SHAPES

from .test_keep_dark_thin_strokes import _dark_regions_in_blob, _lettered_blob

PX_PER_MM = 10.0
FRAME = (200, 200)


def _mask(rows: slice, cols: slice, layer: int, carve=()) -> RegionMask:
    m = np.zeros(FRAME, bool)
    m[rows, cols] = True
    for r, c in carve:
        m[r, c] = False
    return RegionMask.from_full(m, layer)


def _scene() -> list[RegionMask]:
    """A pot-sized panel (layer 0) with a 0.3 x 6 mm dark stroke (layer 1, 180
    px, under the 225 px floor) cut into it, beside a full-size dark stroke
    (layer 1) that clears the floor, and a 3 x 3 px speck (layer 2)."""
    small = (slice(100, 103), slice(40, 100))
    big = (slice(60, 66), slice(40, 100))
    speck = (slice(150, 153), slice(150, 153))
    panel = _mask(slice(20, 180), slice(20, 180), 0, carve=[small, big, speck])
    return [panel, _mask(*small, 1), _mask(*big, 1), _mask(*speck, 2)]


def _cfg() -> PipelineConfig:
    return PipelineConfig(keep_thin_strokes=False, small_dot_rung=False)


def test_off_the_sub_floor_stroke_is_absorbed():
    kept, warnings = resolve_small_regions(_scene(), _cfg(), PX_PER_MM)
    assert len(kept) == 2                       # panel + the full-size stroke
    assert not any(m.floor_rescued for m in kept)
    assert any(w["code"] == ABSORBED_SMALL_SHAPES for w in warnings)


def test_on_the_sub_floor_dark_stroke_survives_flagged_and_the_speck_does_not():
    kept, _ = resolve_small_regions(_scene(), _cfg(), PX_PER_MM, protect_layers=frozenset({1}))
    rescued = [m for m in kept if m.floor_rescued]
    assert len(rescued) == 1 and rescued[0].layer == 1
    assert int(rescued[0].crop.sum()) == 180    # kept as-is, not merged
    assert len(kept) == 3                       # panel, big stroke, rescued; the layer-2 speck went
    assert not any(m.layer == 2 for m in kept)


def test_protect_none_is_the_old_call():
    a, wa = resolve_small_regions(_scene(), _cfg(), PX_PER_MM)
    b, wb = resolve_small_regions(_scene(), _cfg(), PX_PER_MM, protect_layers=None)
    assert [int(m.crop.sum()) for m in a] == [int(m.crop.sum()) for m in b]
    assert wa == wb


def _region(area: float, **meta) -> Region:
    from shapely.geometry import box
    return Region(shape_id="", polygon=box(0, 0, area, 1.0), thread_index=0, thread_number="0",
                  area_mm2=area, source="classical", meta=dict(meta))


def test_an_unclaimed_rescue_is_dropped_and_counted_a_claimed_one_stays():
    crumb = _region(0.9, dark_ink_floor_rescued=True)
    letter = _region(2.0, dark_ink_floor_rescued=True, text_cluster_id="TC1")
    plain = _region(5.0)
    regions = [crumb, letter, plain]
    dropped = drop_unclaimed_floor_rescues(regions)
    assert dropped == [0.9]
    assert regions == [letter, plain]


def test_defaults_are_off_and_the_read_floor_sits_under_the_detail_floor():
    cfg = PipelineConfig()
    assert cfg.dark_ink_floor_rescue is False
    assert cfg.dark_ink_read_floor_mm < cfg.min_detail_mm


def test_on_the_lettered_blob_the_rescued_letters_reach_the_lettering_path(tmp_path):
    art = tmp_path / "blob.png"
    _lettered_blob(art)

    def run(flag: bool):
        cfg = PipelineConfig(target_width_mm=40.0, max_colors=6, forced_class="gradient",
                             edge_cap="none", min_detail_mm=2.5, keep_thin_strokes=False,
                             dark_ink_floor_rescue=flag)
        return run_stages(str(art), cfg)

    off, on = run(False), run(True)
    assert not any(r.meta.get("dark_ink_floor_rescued") for r in off.regions)
    resc = [r for r in on.regions if r.meta.get("dark_ink_floor_rescued")]
    assert resc, "the letters are sub-floor at 2.5 mm, so stage 3 protects them"
    assert all(r.meta.get("text_cluster_id") and r.meta.get("dark_ink") for r in resc)
    assert len(_dark_regions_in_blob(on.regions)) >= 5
