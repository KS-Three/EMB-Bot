"""`blend_fallback_underlay` (2026-10-05, built OFF): a gradient-class design's
fills that sew as ordinary full-density tatami — `blend_fill`'s fallback, the
path nearly every real region takes — get the underlay style stage 7 resolved
for every other fill tier, instead of the hardcoded "none". True ramp bands
stay bare. Evidence and sources: `docs/underlay-research-2026-10-05.md`.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core import machine, stitches
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stage6_blend import SourcePixels, blend_fill, detect_ramp
from digitizer_core.stage6_fill import stitch_shape
from digitizer_core.threads import CHART

from .test_stage6_blend import _linear_region, _linear_source

PHOTO_DIR = Path(__file__).resolve().parent.parent / "testdata" / "photo"


def _noise_fallback() -> tuple[Region, SourcePixels]:
    """A region `detect_ramp` declines, so `blend_fill` sews it as tatami —
    the same fixture `test_blend_falls_back_to_ordinary_tatami_on_speckle`
    uses."""
    rng = np.random.default_rng(3)
    poly = Polygon([(0, 0), (30, 0), (30, 20), (0, 20)])
    noise = rng.integers(0, 256, size=(120, 160, 3), dtype=np.uint8)
    source = SourcePixels(rgb=noise, px_per_mm=4.0, origin_px=(80.0, 60.0))
    region = Region(shape_id="Snoise", polygon=poly, thread_index=0,
                    thread_number=CHART[0].number, area_mm2=poly.area)
    assert detect_ramp(poly, source) is None
    return region, source


def _plain(poly, shape_id, style):
    return stitch_shape(
        poly, shape_id, angle_deg=None, row_mm=machine.FILL_ROW_MM,
        stitch_mm=machine.FILL_STITCH_MM, underlay_style=style,
        trim_at_mm=machine.TRIM_AT_MM)[0]


def _kinds(runs) -> list[str]:
    return [r.kind for r in runs]


def test_the_flag_is_off_by_default():
    assert PipelineConfig().blend_fallback_underlay is False


def test_off_the_fallback_sews_bare_whatever_style_it_is_handed():
    region, source = _noise_fallback()
    runs, _ = blend_fill(region, source, PipelineConfig(),
                         underlay_style="edge_run")
    assert stitches.UNDERLAY not in _kinds(runs)
    assert ([r.points for r in runs]
            == [r.points for r in _plain(region.polygon, region.shape_id, "none")])


@pytest.mark.parametrize("style", ["edge_run", "edge_lattice", "double_lattice"])
def test_on_the_fallback_sews_the_style_it_is_handed(style):
    region, source = _noise_fallback()
    cfg = PipelineConfig(blend_fallback_underlay=True)
    runs, report = blend_fill(region, source, cfg, underlay_style=style)

    expected = _plain(region.polygon, region.shape_id, style)
    assert [(r.kind, r.points) for r in runs] == [(r.kind, r.points) for r in expected]
    kinds = _kinds(runs)
    assert stitches.UNDERLAY in kinds
    # Underlay goes down before the fill that covers it.
    assert kinds.index(stitches.UNDERLAY) < kinds.index(stitches.FILL)
    assert report["blend_shades"] == 0


def test_on_with_no_style_handed_the_fallback_is_still_bare():
    """Every caller that does not pass a style — and stage 7 with
    `cfg.underlay` off, which resolves to "none" — keeps a bare fill."""
    region, source = _noise_fallback()
    cfg = PipelineConfig(blend_fallback_underlay=True)
    runs, _ = blend_fill(region, source, cfg)
    assert stitches.UNDERLAY not in _kinds(runs)
    runs, _ = blend_fill(region, source, cfg, underlay_style="none")
    assert stitches.UNDERLAY not in _kinds(runs)


def test_on_true_ramp_bands_stay_bare():
    """Wilcom and mySewnet both say no underlay under a variable-density
    blend; the band path is not touched."""
    region, source = _linear_region(), _linear_source()
    off, off_report = blend_fill(region, source, PipelineConfig(),
                                 underlay_style="edge_lattice")
    on, on_report = blend_fill(region, source,
                               PipelineConfig(blend_fallback_underlay=True),
                               underlay_style="edge_lattice")
    assert on_report["blend_shades"] >= 2, "fixture must take the band path"
    assert stitches.UNDERLAY not in _kinds(on)
    assert [(r.kind, r.points) for r in on] == [(r.kind, r.points) for r in off]


def _blend_calls(monkeypatch, cfg):
    """Run the repro end to end; return (plan, what stage 7 handed each
    blend call as `underlay_style`, the shape ids that took the fallback)."""
    import digitizer_core.stage7_sequence as s7
    from digitizer_core.pipeline import plan_stitches, run_stages

    real = s7.blend_fill
    handed: list = []
    fallback_ids: set[str] = set()

    def spy(region, sp, c, start_near=None, **kw):
        handed.append(kw.get("underlay_style"))
        runs, report = real(region, sp, c, start_near, **kw)
        if report.get("blend_shades") == 0:
            fallback_ids.add(region.shape_id)
        return runs, report

    monkeypatch.setattr(s7, "blend_fill", spy)
    result = run_stages(str(PHOTO_DIR / "repro_gradient_white_icon.png"), cfg)
    plan = plan_stitches(result, cfg)
    assert handed, "the repro routes through the blend tier"
    return plan, handed, fallback_ids


def _underlay_stitches(plan, shape_ids) -> int:
    return sum(len(r.points) for b in plan.blocks for r in b.runs
               if r.kind == stitches.UNDERLAY and r.shape_id in shape_ids)


def test_stage7_hands_the_blend_tier_the_fabrics_fill_underlay(monkeypatch):
    from digitizer_core.pipeline import fabric_for

    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         blend_fallback_underlay=True)
    plan, handed, fallback_ids = _blend_calls(monkeypatch, cfg)
    assert set(handed) == {fabric_for(cfg).fill_underlay}
    assert fallback_ids
    assert _underlay_stitches(plan, fallback_ids) > 0


def test_off_end_to_end_the_gradient_lane_has_no_fill_underlay(monkeypatch):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    plan, _handed, fallback_ids = _blend_calls(monkeypatch, cfg)
    assert fallback_ids
    assert _underlay_stitches(plan, fallback_ids) == 0


def test_the_underlay_switch_still_wins_end_to_end(monkeypatch):
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         blend_fallback_underlay=True, underlay=False)
    plan, handed, fallback_ids = _blend_calls(monkeypatch, cfg)
    assert set(handed) == {"none"}
    assert _underlay_stitches(plan, fallback_ids) == 0
