"""The streamline tier's dark-end row spacing follows the thread weight.

#843 §4 ("streamline dark spacing 0.8 / ~0.64 / ~0.52 mm at 40 / 60 / 75 wt,
two widths [calc]"). `machine.thread_profile(wt).streamline_dark_sep_mm` is
2 laid thread widths; `stage6_streamline` reads it per colour block. 60 and 75
are CANDIDATES (ROADMAP gate 1, no sew-out), so these tests pin the 40 wt value
unchanged and that a finer thread lays lines closer -- not that 0.64 is right.
"""
from __future__ import annotations

import hashlib
import json
import statistics

import numpy as np
import pytest
from shapely.geometry import Point

from digitizer_core import machine
from digitizer_core.config import PipelineConfig
from digitizer_core.fabrics import get_fabric
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_streamline import (
    STREAMLINE_D_SEP_DARK_MM,
    STREAMLINE_D_SEP_LIGHT_MM,
    _d_sep,
    streamline_fill,
)
from digitizer_core.stage7_sequence import sequence
from digitizer_core.threads import CHART

GRAY = 100                      # uniform mid-dark: the analytic d_sep applies
DARKNESS = 1.0 - GRAY / 255.0


def _disc_region(meta: dict | None = None) -> Region:
    disc = Point(0, 0).buffer(15.0, quad_segs=64)
    m = {"layer": 0, **(meta or {})}
    return Region(shape_id="Stest", polygon=disc, thread_index=0,
                  thread_number=CHART[0].number, area_mm2=disc.area, meta=m)


def _source(gray: int = GRAY) -> SourcePixels:
    img = np.full((200, 200), gray, np.uint8)
    return SourcePixels(rgb=np.dstack([img] * 3), px_per_mm=4.0, origin_px=(100.0, 100.0))


def _md5(runs) -> str:
    pts = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
           for r in runs for x, y in r.points]
    return hashlib.md5(json.dumps(pts).encode()).hexdigest()


def _spacing(runs) -> float:
    fill = [r for r in runs if r.kind == "fill"]
    ys = sorted(float(np.mean([p[1] for p in r.points])) for r in fill)
    return statistics.median(np.diff(ys))


def test_profile_dark_separation_is_two_laid_widths_and_forty_is_unchanged():
    p40, p60, p75 = (machine.thread_profile(w) for w in (40, 60, 75))
    assert p40.streamline_dark_sep_mm == STREAMLINE_D_SEP_DARK_MM == 0.8
    assert p60.streamline_dark_sep_mm == pytest.approx(0.64)
    assert p75.streamline_dark_sep_mm == pytest.approx(0.52)
    for p in (p40, p60, p75):
        assert p.streamline_dark_sep_mm == machine.STREAMLINE_DARK_SEP_WIDTHS * p.width_mm
    assert p75.streamline_dark_sep_mm < p60.streamline_dark_sep_mm < p40.streamline_dark_sep_mm


def test_d_sep_default_is_the_forty_weight_curve_and_only_the_dark_end_moves():
    for d in (0.0, 0.08, 0.3, 0.61, 1.0):
        assert _d_sep(d) == _d_sep(d, STREAMLINE_D_SEP_DARK_MM)
    assert _d_sep(1.0, 0.64) == pytest.approx(0.64)
    assert _d_sep(0.0, 0.64) == STREAMLINE_D_SEP_LIGHT_MM   # light end is fixed


# --- 40 wt is byte-identical: md5 of the run stream, captured on origin/main ---

@pytest.mark.parametrize("gray,pin", [
    (100, "e911a84d6ec5e179309c9a84f0e6e3f3"),
    (30, "efc78680940a896e1f4d7b7315fe804e"),
])
def test_forty_weight_run_stream_md5_is_pinned(gray, pin):
    src = _source(gray)
    default, _ = streamline_fill(_disc_region(), src, PipelineConfig())
    explicit, _ = streamline_fill(_disc_region(), src, PipelineConfig(thread_wt=40))
    kw, _ = streamline_fill(_disc_region(), src, PipelineConfig(), thread_wt=40)
    assert _md5(default) == _md5(explicit) == _md5(kw) == pin


# --- a finer thread lays lines closer ---------------------------------------

def test_sixty_weight_lays_denser_lines_at_the_analytic_separation():
    src = _source()
    r40, rep40 = streamline_fill(_disc_region(), src, PipelineConfig())
    r60, rep60 = streamline_fill(_disc_region(), src, PipelineConfig(thread_wt=60))
    dark60 = machine.thread_profile(60).streamline_dark_sep_mm
    assert rep60["streamlines"] > rep40["streamlines"]
    assert _spacing(r60) < _spacing(r40)
    expected = _d_sep(DARKNESS, dark60)
    assert abs(_spacing(r60) - expected) <= 0.10 * expected
    assert _md5(r60) != _md5(r40)


def test_seventy_five_is_denser_than_sixty():
    src = _source()
    _, rep60 = streamline_fill(_disc_region(), src, PipelineConfig(thread_wt=60))
    _, rep75 = streamline_fill(_disc_region(), src, PipelineConfig(thread_wt=75))
    assert rep75["streamlines"] > rep60["streamlines"]


def test_the_shapes_own_weight_is_read_when_no_block_weight_is_passed():
    src = _source()
    via_meta, _ = streamline_fill(_disc_region({"thread_wt": 60}), src, PipelineConfig())
    via_cfg, _ = streamline_fill(_disc_region(), src, PipelineConfig(thread_wt=60))
    assert _md5(via_meta) == _md5(via_cfg)


# --- the colour block's weight reaches the tier through stage 7 ------------------

def _stage7_fill_count(region: Region, **cfg_kw) -> int:
    cfg = PipelineConfig(**cfg_kw)
    fab = get_fabric("pique_knit")
    planned, _ = resolve_overlaps([region], fab, cfg)
    blocks, _ = sequence(planned, fab, cfg, source_pixels=_source())
    return sum(1 for b in blocks for r in b.runs if r.kind == "fill")


def test_a_block_weight_override_reaches_the_forced_streamline_tier():
    base = _stage7_fill_count(_disc_region({"tier": "streamline"}))
    fine_shape = _stage7_fill_count(_disc_region({"tier": "streamline", "thread_wt": 60}))
    fine_design = _stage7_fill_count(_disc_region({"tier": "streamline"}), thread_wt=60)
    assert fine_shape > base
    assert fine_shape == fine_design
