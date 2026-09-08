"""`tools/thin_strokes.py` — thin-stroke recall, pinned on synthetic art.

The contract: a stroke narrower than the detail floor is found in the
artwork whatever lane the design took; a bar wider than the floor is not a
stroke; a stroke counts as sewn only where thread of its own colour lies on
it, and a jump paints nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

from thin_strokes import (_MIN_STROKE_PX, _link_length_mm, _plan_frame,  # noqa: E402
                          find_thin_strokes, measure, score_strokes,
                          thread_masks)

from digitizer_core import PipelineConfig, machine  # noqa: E402
from digitizer_core.pipeline import build_generation  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun  # noqa: E402

# 400 px of artwork drawn crisp (no anti-alias) at a 20 mm target. The art
# bbox is the bar's 360 px, so the prepped raster is 18 px/mm.
W, H = 400, 200
TARGET_MM = 20.0
BAR = ((20, 40), (380, 100))       # 61 px tall = 3.4 mm: NOT a thin stroke
STROKE_Y = 150                     # 9 px tall (cv2 includes both corners) = 0.5 mm, 341 px = 19 mm
STROKE = ((30, STROKE_Y - 4), (370, STROKE_Y + 4))


@pytest.fixture(scope="module")
def art(tmp_path_factory) -> Path:
    img = np.full((H, W, 3), 255, np.uint8)
    cv2.rectangle(img, BAR[0], BAR[1], (30, 30, 30), -1)          # black bar
    cv2.rectangle(img, STROKE[0], STROKE[1], (40, 40, 230), -1)   # red hairline (BGR)
    p = tmp_path_factory.mktemp("thin") / "bar_and_hairline.png"
    cv2.imwrite(str(p), img)
    return p


@pytest.fixture(scope="module")
def gen(art):
    return build_generation(str(art), PipelineConfig(target_width_mm=TARGET_MM))


def _cfg() -> PipelineConfig:
    return PipelineConfig(target_width_mm=TARGET_MM)


def test_link_length_reads_a_diagonal_as_root_two_and_a_row_as_one():
    row = np.zeros((3, 11), bool)
    row[1, :] = True
    assert _link_length_mm(row, 1.0) == pytest.approx(10.0)
    diag = np.eye(11, dtype=bool)
    assert _link_length_mm(diag, 1.0) == pytest.approx(10 * 2 ** 0.5)
    assert _link_length_mm(diag, 2.0) == pytest.approx(5 * 2 ** 0.5)


def test_the_hairline_is_found_and_the_bar_is_not(gen):
    strokes = find_thin_strokes(gen.p, _cfg())
    assert len(strokes) == 1, [(s.width_mm, s.length_mm) for s in strokes]
    s = strokes[0]
    # 9 px at 18 px/mm is 0.5 mm; the distance transform reads the centre row
    # at 5 px, so allow the raster's own quantum either side.
    assert 0.4 <= s.width_mm <= 0.65, s.width_mm
    assert 16.0 <= s.length_mm <= 20.5, s.length_mm
    # Red, not black: the stroke's own colour is what recall is scored against.
    assert s.rgb[0] > 150 and s.rgb[1] < 100, s.rgb


def test_a_two_pixel_sliver_is_halo_not_ink(gen):
    """The pixel floor: a component narrower than `_MIN_STROKE_PX` is the
    raster's anti-alias or compression ringing, whatever its millimetres.
    Asking for strokes under 3 px wide on this crisp fixture finds none."""
    assert _MIN_STROKE_PX >= 3.0
    cx, cy, ppm = _plan_frame(gen.p)
    # The floor in mm at this resolution is 3 / 18 = 0.167 mm; a width floor
    # below that can admit nothing.
    assert find_thin_strokes(gen.p, _cfg(), width_floor_mm=_MIN_STROKE_PX / ppm - 1e-9) == []


def _stroke_line_mm(gen) -> tuple[tuple[float, float], tuple[float, float]]:
    cx, cy, ppm = _plan_frame(gen.p)
    y = (STROKE_Y - cy) / ppm
    return ((STROKE[0][0] + 2 - cx) / ppm, y), ((STROKE[1][0] - 2 - cx) / ppm, y)


def _plan(runs: list[StitchRun], rgb: tuple[int, int, int]) -> StitchPlan:
    block = StitchBlock(thread_index=0, thread_number="0000", rgb=rgb, runs=runs)
    return StitchPlan(blocks=[block], palette=[{"number": "0000", "name": "test"}])


def test_thread_along_the_stroke_in_its_colour_is_full_recall(gen):
    strokes = find_thin_strokes(gen.p, _cfg())
    a, b = _stroke_line_mm(gen)
    plan = _plan([StitchRun(points=[a, b])], strokes[0].rgb)
    score_strokes(strokes, gen.p, _cfg(), plan)
    assert strokes[0].recall >= 0.9, strokes[0].recall


def test_thread_of_another_colour_on_the_stroke_is_lost(gen):
    strokes = find_thin_strokes(gen.p, _cfg())
    a, b = _stroke_line_mm(gen)
    plan = _plan([StitchRun(points=[a, b])], (30, 30, 230))   # blue over a red stroke
    score_strokes(strokes, gen.p, _cfg(), plan)
    assert strokes[0].recall == 0.0


def test_thread_three_millimetres_away_is_lost(gen):
    strokes = find_thin_strokes(gen.p, _cfg())
    a, b = _stroke_line_mm(gen)
    off = ((a[0], a[1] - 3.0), (b[0], b[1] - 3.0))
    plan = _plan([StitchRun(points=list(off))], strokes[0].rgb)
    score_strokes(strokes, gen.p, _cfg(), plan)
    assert strokes[0].recall == 0.0


def test_a_jump_between_the_two_ends_paints_no_thread(gen):
    strokes = find_thin_strokes(gen.p, _cfg())
    a, b = _stroke_line_mm(gen)
    far = (a[0], a[1] - 5.0)
    # Sewn: one run from a to b.  Jumped: the needle lifts between them, so
    # the same two points lay no thread on the stroke.
    sewn = _plan([StitchRun(points=[far, far]), StitchRun(points=[a, b], jump=True)], strokes[0].rgb)
    jumped = _plan([StitchRun(points=[far, far]), StitchRun(points=[a], jump=True),
                    StitchRun(points=[b], jump=True)], strokes[0].rgb)
    cx, cy, ppm = _plan_frame(gen.p)
    shape = gen.p.rgb.shape[:2]
    m_sewn = thread_masks(sewn, shape, cx, cy, ppm)
    m_jumped = thread_masks(jumped, shape, cx, cy, ppm)
    assert m_sewn and m_sewn[0][1].sum() > 0
    assert (not m_jumped) or m_jumped[0][1].sum() == 0


def test_measure_reports_the_lost_stroke_first(gen):
    r = measure(gen.p, _cfg(), _plan([], (0, 0, 0)))
    assert r["thin_strokes"] == 1
    assert r["lost_strokes"] == 1
    assert r["recall"] == 0.0
    assert r["worst_lost"][0]["lost_mm"] == pytest.approx(r["thin_length_mm"], abs=0.01)


def test_the_floors_are_the_run_tiers_own_constants():
    """No new millimetre: the width floor is `min_detail_mm`, the length floor
    is `RUN_MIN_LOOP_MM / 2`. If either constant moves, this instrument moves
    with it — that is the point of pinning the wiring, not the values."""
    import inspect

    import thin_strokes as ts

    src = inspect.getsource(ts.find_thin_strokes)
    assert "cfg.min_detail_mm" in src
    assert "machine.RUN_MIN_LOOP_MM / 2.0" in src
    assert machine.RUN_MIN_LOOP_MM > 0
