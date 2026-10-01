"""`cfg.work_px_per_mm` — the grid stage 1 brings a low-resolution source up to.

Bridge's teal "BAR & RESTAURANT" (2026-09-30): 3.25-4.5 mm letters in a
400 px JPEG, 3.5 px/mm at 80 mm. Stage 1 enlarged the file to
`min_px_per_mm` = 4 and the gradient lane's merge then lost half the words:
a 0.7-1.4 mm stroke is 3-5 pixels there, every superpixel around the
lettering holds ink AND ground, and regions are merged on their MEAN colour.
The same file at 5 px/mm and above keeps the letters (measured 5, 6, 7, 8,
10 — `docs/fine-detail-work-grid-2026-09-30.md`), because the pixels the
artwork already has are spread over enough of the grid for the oversegmenter
to cut a stroke out whole.

So the line under which a source is REPORTED as too small
(`min_px_per_mm`, `INPUT_LOW_RESOLUTION`) and the grid it is TRACED on are
two numbers, and these tests pin that they are.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.alpha_edge import extension_applies
from digitizer_core.config import work_grid_px_per_mm
from digitizer_core.stage1_prep import prep
from digitizer_core.warnings_codes import INPUT_LOW_RESOLUTION

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
BRIDGE = TESTDATA / "photo" / "logo_bridge_bar.jpg"


def _band(px: int) -> np.ndarray:
    """A BGRA cutout whose artwork spans the frame: `px` pixels of artwork
    width, so at 80 mm it delivers px / 80 pixels per millimetre."""
    art = np.zeros((px, px, 4), np.uint8)
    art[px * 3 // 8: px * 5 // 8, :, :3] = 20
    art[px * 3 // 8: px * 5 // 8, :, 3] = 255
    return art


def _cfg(**kw) -> PipelineConfig:
    return PipelineConfig(target_width_mm=80.0, garment_id="left_chest", **kw)


def _low_res(p) -> dict | None:
    found = [w for w in p.warnings if w["code"] == INPUT_LOW_RESOLUTION]
    return found[0] if found else None


def test_a_source_between_the_source_line_and_the_grid_is_enlarged_and_stays_quiet():
    """6 px/mm is not a low-resolution file — nothing for the customer to do —
    and it is still traced on the working grid."""
    p = prep(_band(480), _cfg(work_px_per_mm=8.0))
    assert p.input_px_per_mm == pytest.approx(6.0)
    assert p.px_per_mm == pytest.approx(8.0)
    assert p.rgb.shape[1] == 640
    assert p.native_rgb is not None and p.native_rgb.shape[1] == 480
    assert _low_res(p) is None


def test_a_source_under_the_source_line_reaches_the_grid_and_still_says_so():
    p = prep(_band(280), _cfg(work_px_per_mm=8.0))
    assert p.input_px_per_mm == pytest.approx(3.5)
    assert p.px_per_mm == pytest.approx(8.0)
    w = _low_res(p)
    assert w is not None
    assert w["px_per_mm"] == pytest.approx(3.5)
    assert w["upscaled_to"] == pytest.approx(8.0)
    assert w["min_px_per_mm"] == pytest.approx(4.0)          # the line it is judged against, not the grid


def test_a_source_on_or_over_the_grid_is_left_alone():
    p = prep(_band(720), _cfg(work_px_per_mm=8.0))
    assert p.px_per_mm == pytest.approx(9.0)
    assert p.native_rgb is None and p.upscale == (1.0, 1.0)


def test_the_enlargement_cap_still_bounds_it():
    """A 100 px file is enlarged `upscale_cap` times and no further, whatever
    the grid asks for."""
    cfg = _cfg(work_px_per_mm=8.0)
    p = prep(_band(100), cfg)
    assert p.px_per_mm == pytest.approx(1.25 * cfg.upscale_cap)


def test_no_working_grid_means_the_source_line_is_the_grid():
    """`None` is the engine before the knob existed: only a source under
    `min_px_per_mm` is enlarged, and only to it."""
    cfg = _cfg(work_px_per_mm=None)
    assert work_grid_px_per_mm(cfg) == cfg.min_px_per_mm
    assert prep(_band(480), cfg).px_per_mm == pytest.approx(6.0)
    assert prep(_band(280), cfg).px_per_mm == pytest.approx(4.0)


def test_a_grid_under_the_source_line_cannot_lower_it():
    cfg = _cfg(work_px_per_mm=2.0)
    assert work_grid_px_per_mm(cfg) == cfg.min_px_per_mm
    assert prep(_band(280), cfg).px_per_mm == pytest.approx(4.0)


@pytest.mark.parametrize("class_", ["photo_subject", "photo_scene"])
def test_a_photograph_keeps_the_source_line(class_):
    """The defect is line art: a stroke a few pixels wide averaged into its
    ground. A photograph has no strokes to lose and its lane was never
    measured on an enlarged raster, so the photo classes — and a design the
    caller DECLARED photographic — are traced as they were."""
    cfg = _cfg(work_px_per_mm=8.0)
    assert work_grid_px_per_mm(cfg, class_) == cfg.min_px_per_mm
    assert work_grid_px_per_mm(cfg, "gradient") == 8.0
    assert work_grid_px_per_mm(cfg, "flat") == 8.0
    assert work_grid_px_per_mm(_cfg(work_px_per_mm=8.0, is_photographic=True), "gradient") == cfg.min_px_per_mm
    p = prep(_band(480), cfg, design_class=class_)
    assert p.px_per_mm == pytest.approx(6.0) and p.native_rgb is None
    assert extension_applies(cfg, _band(480)[..., 3], design_class=class_) is False


def test_the_enlargement_stops_at_the_pixel_budget():
    """8 px/mm of a 400 mm jacket back is 3,200 pixels a side, past the
    2,800 the service caps a decoded upload at (the size that ran a job out
    of memory). The working grid enlarges up to that side and no further —
    but never gives back what `min_px_per_mm` alone would have enlarged."""
    from digitizer_core.stage1_prep import WORK_GRID_MAX_SIDE_PX
    big = PipelineConfig(target_width_mm=400.0, garment_id="left_chest", work_px_per_mm=8.0)
    p = prep(_band(2000), big)                                 # 5 px/mm; 8 would be 3,200 px
    assert max(p.rgb.shape[:2]) == WORK_GRID_MAX_SIDE_PX
    assert p.px_per_mm == pytest.approx(7.0)
    low = prep(_band(1000), big)                               # 2.5 px/mm: the source line needs 1,600
    assert max(low.rgb.shape[:2]) == WORK_GRID_MAX_SIDE_PX and low.px_per_mm == pytest.approx(7.0)
    tiny_budget = prep(_band(280), _cfg(work_px_per_mm=8.0))   # nowhere near the budget
    assert tiny_budget.px_per_mm == pytest.approx(8.0)


def _disc_on_white(px: int) -> np.ndarray:
    """An opaque BGR raster: a dark disc `px` pixels across on white, drawn
    4x supersampled and reduced by area so its edge is a real anti-alias
    ramp, with a white margin for the border flood to find."""
    import cv2
    n = (px + 80) * 4
    big = np.full((n, n, 3), 255, np.uint8)
    cv2.circle(big, (n // 2, n // 2), px * 2, (30, 30, 180), -1)
    return cv2.resize(big, (px + 80, px + 80), interpolation=cv2.INTER_AREA)


def test_the_knob_ships_off_and_off_is_the_engine_before_it():
    """Built OFF (the flip is Kent's, on renders): the default traces a
    low-resolution source on `min_px_per_mm` exactly as before, including the
    one odd path the old code had — an `upscale_cap` of 1 still records the
    native raster and still warns."""
    assert PipelineConfig().work_px_per_mm is None
    p = prep(_band(280), _cfg(upscale_cap=1.0))
    assert p.px_per_mm == pytest.approx(3.5) and p.native_rgb is not None
    assert _low_res(p) is not None


def test_without_the_working_grid_the_mask_is_enlarged_as_it_always_was():
    """`None` is byte-identical to the engine before the knob, staircase
    included: a sub-floor source's mask is the source's mask, NEAREST."""
    import cv2
    art = _disc_on_white(240)                                  # 3 px/mm at 80 mm: under the source line
    off = prep(art, _cfg(work_px_per_mm=None))
    assert off.px_per_mm == pytest.approx(4.0)
    native = prep(art, _cfg(work_px_per_mm=None, min_px_per_mm=1.0)).bg_mask
    h, w = off.bg_mask.shape
    blocky = cv2.resize(native.astype(np.uint8), (w, h), interpolation=cv2.INTER_NEAREST) > 0
    assert np.array_equal(off.bg_mask, blocky)


def test_the_alpha_extension_follows_the_enlargement_not_the_source_line():
    """`alpha_edge_extend_upscaled_only` exists because the Lanczos
    enlargement is the reader that smears the colour under a cutout's
    transparency into the sewn edge. It must run wherever the enlargement
    will, so it reads the working grid."""
    alpha = _band(480)[..., 3]                                  # 6 px/mm at 80 mm
    assert extension_applies(_cfg(work_px_per_mm=8.0), alpha) is True
    assert extension_applies(_cfg(work_px_per_mm=None), alpha) is False


class _Plan:
    """The one field `_resolution_note` reads off a plan: an 80 mm design."""
    class stats:
        bbox_mm = (-40.0, -10.0, 40.0, 10.0)


class _Prep:
    def __init__(self, source: float, traced: float):
        self.input_px_per_mm = source
        self.px_per_mm = traced


def _too_small(extent_mm: float) -> dict:
    return {"code": "LETTERING_TOO_SMALL", "severity": "warn", "message": "small.",
            "extra": {"count": 1, "satin_total": 1,
                      "shapes": [{"shape_id": "S1", "column_mm": 0.8, "extent_mm": extent_mm}]}}


def test_lettering_the_working_grid_traces_is_not_called_lost_in_tracing():
    """The note's constant was calibrated in GRID pixels (bridge: lost at
    13-18, back at 28). 3.4 mm letters from a 3.5 px/mm file are 12 source
    pixels and 27 on an 8 px/mm grid: traced, so the finding keeps its own
    words and its ordinary size step."""
    from digitizer_core.preflight import _resolution_note
    f = _too_small(3.4)
    _resolution_note([f], _Prep(3.49, 8.0), _Plan, _cfg(work_px_per_mm=8.0))
    assert f["message"] == "small." and "input_px_per_mm" not in f["extra"]


def test_lettering_still_under_the_grids_reach_names_the_width_on_that_grid():
    """2 mm letters are 16 pixels even at 8 px/mm. The width that would give
    them 20 is read on the grid the tracer will actually use."""
    from digitizer_core.preflight import LETTERING_MIN_SOURCE_PX, _resolution_note
    f = _too_small(2.0)
    _resolution_note([f], _Prep(3.49, 8.0), _Plan, _cfg(work_px_per_mm=8.0))
    assert "lost in tracing" in f["message"]
    assert f["extra"]["source_px_per_letter"] == 7.0
    assert f["extra"]["traced_at_mm"] == round(80.0 * LETTERING_MIN_SOURCE_PX / (2.0 * 8.0))


def test_a_source_enlarged_to_the_grid_is_offered_the_bigger_design_too():
    """6 px/mm is over the source line and under the grid: stage 1 enlarges
    it, so a bigger design does give the tracer more pixels per letter."""
    from digitizer_core.preflight import _resolution_note
    f = _too_small(2.0)
    _resolution_note([f], _Prep(6.0, 8.0), _Plan, _cfg(work_px_per_mm=8.0))
    assert f["extra"]["traced_at_mm"] == 100 and "adds no pixels" not in f["message"]


def _teal(result, cfg) -> list:
    from digitizer_core.threads import chart_for
    chart = chart_for(cfg)

    def is_teal(rgb) -> bool:
        r, g, b = rgb
        return b > r + 40 and g > r + 40

    return [r for r in result.regions if is_teal(chart[r.thread_index].rgb)]


def test_bridges_teal_words_survive_tracing_on_the_working_grid():
    """The defect itself. On the 4 px/mm grid six teal blobs are left of
    "BAR & RESTAURANT" — 46.6 of the artwork's ~96 mm² of teal — and the word
    RESTAURANT is three of them. On 8 px/mm the letters reach stage 4 as
    letter groups: 11 regions, 118.8 mm² (measured 2026-09-30)."""
    from digitizer_core.pipeline import build_generation, finish_generation

    def teal(**kw):
        cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest", max_colors=6, **kw)
        return _teal(finish_generation(build_generation(str(BRIDGE), cfg).fork(), cfg), cfg)

    before = teal(work_px_per_mm=None)
    after = teal(work_px_per_mm=8.0)
    assert sum(r.area_mm2 for r in before) < 60.0            # the blobs: the defect is still measurable OFF
    assert len(after) >= 9
    assert sum(r.area_mm2 for r in after) >= 100.0
