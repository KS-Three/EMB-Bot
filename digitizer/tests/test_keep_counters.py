"""`cfg.keep_counters` — a letter's counter on a coloured ground stays a hole.

Measured 2026-10-02 on clean 4 mm "BAR & RESTAURANT" (bridge's words, Kent's
pick): on white the counters are background and the letters sew as letters;
on a yellow panel each counter is a region of the ground's colour under
`min_detail_mm`², `resolve_small_regions` absorbs it into the letter round
it, and every letter sews as one bar. Built OFF.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.stage3_segment import RegionMask, resolve_small_regions

PX_PER_MM = 8.0          # floor: (1.5 mm x 8)^2 = 144 px
# CIELAB per layer: 0 the yellow ground, 1 the teal letter, 2 a lime blend
# nearer the ground, 3 a blue-green nearer the letter.
LAYER_LAB = np.array([[90.0, -5.0, 80.0], [55.0, -35.0, -10.0],
                      [82.0, -15.0, 60.0], [60.0, -32.0, 0.0]])


def _scene(counter_layer: int = 0, on_page: bool = False, notch: bool = False, gap: int = 6):
    """A 20 x 20 px letter block with a `gap` x `gap` px gap, on a 60 x 60 ground.

    -> [ground, letter, small]. `on_page` leaves the ground out (the letter
    sits on the page). `notch` puts the small region on the letter's EDGE
    instead, touching letter and ground alike — a sliver, not a counter."""
    frame = np.zeros((80, 80), bool)
    letter = frame.copy()
    letter[30:50, 30:50] = True
    small = frame.copy()
    if notch:
        small[37:43, 30:36] = True          # on the left edge: ring is half ground
    else:
        small[40 - gap // 2:40 - gap // 2 + gap, 40 - gap // 2:40 - gap // 2 + gap] = True
    letter &= ~small
    ground = frame.copy()
    ground[10:70, 10:70] = True
    ground &= ~(letter | small)
    out = [] if on_page else [RegionMask.from_full(ground, 0)]
    return out + [RegionMask.from_full(letter, 1), RegionMask.from_full(small, counter_layer)]


def _resolve(regions, **kw):
    return resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, layer_lab=LAYER_LAB, **kw)[0]


def test_the_flag_ships_off():
    assert PipelineConfig().keep_counters is False


def test_without_the_gate_a_counter_is_absorbed_into_its_letter():
    kept = _resolve(_scene())
    assert len(kept) == 2
    assert sorted(r.area for r in kept)[0] == 400       # the letter, its gap filled


def test_a_counter_of_the_grounds_colour_is_kept_as_a_gap():
    kept = _resolve(_scene(), keep_counters=True)
    assert len(kept) == 3
    counter = [r for r in kept if r.source == "counter"]
    assert len(counter) == 1 and counter[0].area == 36
    assert sorted(r.area for r in kept)[1] == 364       # the letter kept its hole


def test_a_blend_nearer_the_ground_than_the_letter_is_still_a_counter():
    """A 1 mm counter in a 3.5 px/mm file is a blend and can take a third
    thread; nearer the ground is what makes it the gap."""
    kept = _resolve(_scene(counter_layer=2), keep_counters=True)
    assert [r.area for r in kept if r.source == "counter"] == [36]


def test_a_region_nearer_the_letters_colour_is_a_sliver_of_it():
    kept = _resolve(_scene(counter_layer=3), keep_counters=True)
    assert not [r for r in kept if r.source == "counter"]
    assert len(kept) == 2


def test_a_sliver_on_the_letters_edge_is_not_a_counter():
    """Half its ring is the ground: it is absorbed exactly as before."""
    on = _resolve(_scene(notch=True), keep_counters=True)
    off = _resolve(_scene(notch=True))
    assert not [r for r in on if r.source == "counter"]
    assert sorted(r.area for r in on) == sorted(r.area for r in off)


def test_a_gap_the_run_tier_can_sew_is_sewn_exactly_as_before():
    """Asked LAST: a contrasting region that clears the run tier's floors is
    rescued and sewn today (a 10 px gap: 2 x 10 px clears the 2.2 mm loop
    floor at 8 px/mm), and the gate does not take thread away. The first cut
    asked it first and unstitched the yellow in the bowl of bridge's "B"."""
    on = _resolve(_scene(gap=10), keep_counters=True)
    off = _resolve(_scene(gap=10))
    assert not [r for r in on if r.source == "counter"]
    assert [r.area for r in on] == [r.area for r in off] and len(on) == 3


def test_a_letter_on_the_page_has_no_ground_to_match():
    """The encloser sits on background, which is `Prep.enclosed_mask`'s
    case, not this one."""
    on = _resolve(_scene(on_page=True), keep_counters=True)
    assert not [r for r in on if r.source == "counter"]


def test_the_gradient_lanes_call_reads_the_raster():
    """Every region is layer 0 there and no layer colours exist; the regions'
    own means in `lab_img` answer instead."""
    regions = _scene()
    for r in regions:
        r.layer = 0
    lab_img = np.zeros((80, 80, 3))
    lab_img[:] = LAYER_LAB[0]
    lab_img[30:50, 30:50] = LAYER_LAB[1]
    lab_img[37:43, 37:43] = LAYER_LAB[2]
    kept, _ = resolve_small_regions(regions, PipelineConfig(), PX_PER_MM, chain_rescue=False,
                                    lab_img=lab_img, keep_counters=True)
    assert [r.area for r in kept if r.source == "counter"] == [36]
    # ... and with nothing to read colour from, the gate is inert.
    bare, _ = resolve_small_regions(_scene(), PipelineConfig(), PX_PER_MM, keep_counters=True)
    assert len(bare) == 2


# --- through the pipeline ----------------------------------------------------

def _panel(path: Path) -> tuple[Path, float]:
    """Four teal 3.4 x 4.0 mm blocks, each with a 0.9 x 0.9 mm gap, on a
    yellow panel with a white margin — drawn at 40 px/mm and delivered at
    3.5, the density bridge arrives at. 0.9 because the engine already keeps
    a crisp 1.2 mm gap on its own (measured: four holes, flag off, both
    lanes); under about 1.1 mm the floor takes it.
    -> (file, the panel's width in mm)."""
    big = 40
    mm = lambda v: int(round(v * big))                         # noqa: E731
    w_mm, h_mm, margin = 26.0, 10.0, 3.0
    img = np.full((mm(h_mm + 2 * margin), mm(w_mm + 2 * margin), 3), 255, np.uint8)
    img[mm(margin):mm(margin + h_mm), mm(margin):mm(margin + w_mm)] = (40, 230, 250)   # BGR yellow
    for k in range(4):
        x0, y0 = margin + 3.0 + k * 5.4, margin + 3.0
        img[mm(y0):mm(y0 + 4.0), mm(x0):mm(x0 + 3.4)] = (150, 140, 0)                  # BGR teal
        img[mm(y0 + 1.55):mm(y0 + 2.45), mm(x0 + 1.25):mm(x0 + 2.15)] = (40, 230, 250)
    s = 3.5 / big
    small = cv2.resize(img, (int(round(img.shape[1] * s)), int(round(img.shape[0] * s))),
                       interpolation=cv2.INTER_AREA)
    cv2.imwrite(str(path), small)
    return path, w_mm


def _teal(result, cfg):
    from digitizer_core.threads import chart_for
    chart = chart_for(cfg)

    def is_teal(rgb) -> bool:
        r, g, b = rgb
        return b > r + 40 and g > r + 40

    return [r for r in result.regions if is_teal(chart[r.thread_index].rgb)]


@pytest.mark.parametrize("lane", [{}, {"forced_class": "flat"}], ids=["as_classified", "flat"])
def test_the_blocks_get_their_gaps_back_and_no_counter_is_sewn(tmp_path, lane):
    """Measured on Windows 2026-10-02, holes in the four teal polygons, flag
    off -> on: 0 -> 3 as classified (the gradient lane; the kept gaps clear
    the run floors downstream and are sewn as today's rescue sews them),
    0 -> 2 forced flat (all four gaps tagged `counter` and left unsewn; two
    fall under stage 4's own hole floor)."""
    from digitizer_core.pipeline import digitize

    art, width_mm = _panel(tmp_path / "panel.png")

    def run(flag: bool):
        cfg = PipelineConfig(target_width_mm=width_mm, garment_id="left_chest", max_colors=6,
                             keep_counters=flag, **lane)
        result, plan = digitize(art, cfg)
        return result, plan, cfg

    off, _plan, cfg = run(False)
    off_holes = sum(len(r.polygon.interiors) for r in _teal(off, cfg))
    assert not [r for r in off.regions if r.meta.get("counter")]

    on, plan, cfg = run(True)
    on_holes = sum(len(r.polygon.interiors) for r in _teal(on, cfg))
    assert on_holes >= 2 and on_holes > off_holes
    counters = [r for r in on.regions if r.meta.get("counter")]
    if lane:
        assert counters
    assert all(r.meta.get("enclosed_background") and r.meta.get("stitched") is False for r in counters)
    sewn = {run_.shape_id for block in plan.blocks for run_ in block.runs}
    assert not sewn & {r.shape_id for r in counters}
