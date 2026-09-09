"""The tier rule for widened lettering (`stage7_sequence` and
`stage5_overlap`, plan §4d's second half, 2026-09-09).

`cfg.lettering_min_column_mm` widens a door-1 cluster member's artwork to
half the sewn floor less the pull; measured on its own that changed nothing
about how the glyph SEWED, because stage 7 routed every sub-floor shape to
the run tier before satin was asked and classified on the artwork polygon.
The rule: a member the regularizer widened (`text_cluster_widened_mm`) is
exempt from that routing and is classified and sewn on its compensated
polygon. Pinned end to end on a row of thin bars: without the floor they
sew as bean runs; with it they sew as satin columns a millimetre wide, read
by `tools/satin_columns.py` on the stitches.

The second half is stage 5's. A glyph on a ground is a hole in that ground
at its ORIGINAL width, and "never grow back over a colour already down"
clipped the widened glyph back to its hole — on Fremont every widened glyph
was classified on a 0.28 mm hole and sewn as the hairline it was. Widened
lettering keeps its growth over the ground beneath it, so the same bars cut
into a panel, kept by `keep_thin_strokes` (the population this floor was
built for), sew the same millimetre column. The OCR gate is held open for
the widened arm: it is a legibility judgement about letters, has nothing to
say about six identical bars (it reads each as "|" and refuses the wider
one), and has its own tests. A widened glyph the satin tier declines sews
the bean run it sewed before the floor, never a millimetre-wide tatami. With
the floor unset nothing carries the tag, and the run-tier suite pins that
ladder as it was.
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import cv2
import numpy as np

from digitizer_core import PipelineConfig, stitches
from digitizer_core.pipeline import digitize
from digitizer_core.stage6_satin import RibbonVerdict

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))

import satin_columns as sc  # noqa: E402

from .test_keep_thin_strokes import PX_PER_MM  # noqa: E402
from .test_textcluster import _OCR_GATE_PATH  # noqa: E402

FLOOR_MM = 1.0


def _thin_bars(path: Path) -> None:
    """Six 0.3 x 3 mm dark bars on a white ground, 4.8 mm apart, drawn crisp
    at 10 px/mm for a 50 mm target: each is an isolated sub-floor shape
    (0.9 mm², under the 2.25 mm² floor, over the run tier's own floors), so
    stage 3 rescues it and together they are a door-1 text cluster at a
    0.15 mm median half-width. Two 2 x 4 mm blocks, inset from the edge so
    the white border still reads as background, fix the 50 mm art width;
    they are ordinary shapes, over the floor, and far from the row."""
    img = np.full((220, 540, 3), 255, np.uint8)
    for k in range(6):
        x = 130 + 48 * k
        cv2.rectangle(img, (x, 85), (x + 2, 114), (30, 30, 30), -1)     # 3 x 30 px
    for x in (20, 500):
        cv2.rectangle(img, (x, 160), (x + 19, 199), (30, 30, 30), -1)   # 20 x 40 px; bbox 20..519 = 500 px
    cv2.imwrite(str(path), img)


def _thin_bars_on_a_panel(path: Path) -> None:
    """The same six bars cut into a red panel that fills the 50 mm art
    width. Each bar is a contrasting sub-floor region on the panel, which
    `keep_thin_strokes` keeps for the run tier (`stage3_segment`), and the
    panel is vectorized with a hole the bar's original width."""
    img = np.full((220, 540, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 30), (519, 189), (30, 30, 200), -1)          # 500 x 160 px red (BGR)
    for k in range(6):
        x = 130 + 48 * k
        cv2.rectangle(img, (x, 85), (x + 2, 114), (30, 30, 30), -1)     # 3 x 30 px
    cv2.imwrite(str(path), img)


def _satin_columns_of(plan, regions) -> dict:
    ids = {r.shape_id for r in regions}
    return sc.measure(sc.passes_from_plan(plan, kinds=frozenset({stitches.SATIN}), shape_ids=ids))


def _cluster_kinds(result, plan) -> dict[str, int]:
    ids = {r.shape_id for r in result.regions if r.meta.get("text_cluster_id")}
    kinds: dict[str, int] = {}
    for _b, run in plan.iter_runs():
        if run.shape_id in ids:
            kinds[run.kind] = kinds.get(run.kind, 0) + len(run.points)
    return kinds


def test_widened_lettering_sews_as_a_column_where_it_sewed_as_a_bean(tmp_path):
    art = tmp_path / "bars.png"
    _thin_bars(art)
    off_cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest")
    on_cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest",
                            lettering_min_column_mm=FLOOR_MM)
    off, off_plan = digitize(art, off_cfg)
    with patch(_OCR_GATE_PATH, return_value=False):
        on, on_plan = digitize(art, on_cfg)

    clustered_off = [r for r in off.regions if r.meta.get("text_cluster_id")]
    assert len(clustered_off) >= 5, "the bars must form a door-1 cluster for this test to mean anything"
    assert all(r.meta.get("rescued_small_shape") for r in clustered_off)
    widened = [r for r in on.regions if r.meta.get("text_cluster_widened_mm")]
    assert len(widened) >= 5, [r.meta.get("text_cluster_regularize_skip_reason") for r in on.regions
                               if r.meta.get("text_cluster_id")]

    # OFF: the run tier, on the artwork outline. ON: satin, on the column.
    kinds_off = _cluster_kinds(off, off_plan)
    kinds_on = _cluster_kinds(on, on_plan)
    assert kinds_off.get("run", 0) > 0 and kinds_off.get("satin", 0) == 0, kinds_off
    assert kinds_on.get("satin", 0) > 0, kinds_on

    # The column is the floor: the pull (0.3 mm on the knit) added back to a
    # 0.4 mm artwork gives 1.0 mm of sewn width, read off the crosses of the
    # widened shapes alone (the width markers sew satin too).
    m = _satin_columns_of(on_plan, widened)
    assert m["columns"] >= 5 * 6, m           # six bars, a handful of crosses each
    assert 0.8 <= m["median_mm"] <= 1.25, m
    assert m["p90_mm"] <= 1.25, m


def test_bars_cut_into_a_panel_sew_the_same_column_over_the_ground(tmp_path):
    """Fremont's configuration: lettering on a filled ground, kept by
    `keep_thin_strokes`. Without stage 5's exemption the widened glyph is
    clipped back to the hole its ground was vectorized with and sews as the
    0.3 mm hairline it was."""
    art = tmp_path / "panel.png"
    _thin_bars_on_a_panel(art)
    assert PX_PER_MM == 10.0
    off_cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest", keep_thin_strokes=True)
    on_cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest", keep_thin_strokes=True,
                            lettering_min_column_mm=FLOOR_MM)
    off, off_plan = digitize(art, off_cfg)
    with patch(_OCR_GATE_PATH, return_value=False):
        on, on_plan = digitize(art, on_cfg)

    clustered_off = [r for r in off.regions if r.meta.get("text_cluster_id")]
    assert len(clustered_off) >= 5 and all(r.meta.get("rescued_small_shape") for r in clustered_off)
    kinds_off = _cluster_kinds(off, off_plan)
    assert kinds_off.get("run", 0) > 0 and kinds_off.get("satin", 0) == 0, kinds_off

    widened = [r for r in on.regions if r.meta.get("text_cluster_widened_mm")]
    assert len(widened) >= 5, [r.meta.get("text_cluster_regularize_skip_reason") for r in on.regions
                               if r.meta.get("text_cluster_id")]
    kinds_on = _cluster_kinds(on, on_plan)
    assert kinds_on.get("satin", 0) > 0 and kinds_on.get("fill", 0) == 0, kinds_on
    m = _satin_columns_of(on_plan, widened)
    assert m["columns"] >= 5 * 6, m
    assert 0.8 <= m["median_mm"] <= 1.25, m
    assert m["p90_mm"] <= 1.25, m
    # The panel still sews, and its hole is still the bar's own width: the
    # column lies OVER the ground, it does not cut a wider hole in it.
    panel_on = [r for r in on.regions if not r.meta.get("text_cluster_id")]
    assert len(panel_on) == 1 and 700.0 < panel_on[0].polygon.area < 800.0    # 50 x 16 mm less six bars


def test_with_the_floor_unset_nothing_carries_the_tag_and_the_ladder_is_unchanged(tmp_path):
    art = tmp_path / "bars.png"
    _thin_bars(art)
    result, plan = digitize(art, PipelineConfig(target_width_mm=50.0, garment_id="left_chest"))
    assert not any(r.meta.get("text_cluster_widened_mm") for r in result.regions)
    kinds = _cluster_kinds(result, plan)
    assert kinds.get("satin", 0) == 0 and kinds.get("run", 0) > 0, kinds


def test_a_widened_glyph_the_satin_tier_declines_sews_the_bean_run_it_sewed_before(tmp_path):
    art = tmp_path / "bars.png"
    _thin_bars(art)
    cfg = PipelineConfig(target_width_mm=50.0, garment_id="left_chest", lettering_min_column_mm=FLOOR_MM)
    declined = RibbonVerdict(satin=False, reason="dt_irregular", metrics={})
    with patch(_OCR_GATE_PATH, return_value=False), \
            patch("digitizer_core.stage7_sequence.classify_ribbon", return_value=declined):
        result, plan = digitize(art, cfg)
    widened = [r for r in result.regions if r.meta.get("text_cluster_widened_mm")]
    assert len(widened) >= 5
    kinds = _cluster_kinds(result, plan)
    assert kinds.get("run", 0) > 0, kinds
    assert kinds.get("satin", 0) == 0 and kinds.get("fill", 0) == 0, kinds
