"""A stripe field sews its lighter thread once underneath (`cfg.stripe_underfill`).

Kent on his Flag.webp (96 mm hat, 2026-11-12): fill the whole field white and
sew the red stripes on top as satin, the pro's way with a flag. Sewn side by
side, the colour sewn last lay over its neighbours (white 4.67 mm against red's
visible 3.14 from 3.96 mm art stripes).
"""
from __future__ import annotations

import numpy as np
import pytest
from shapely.geometry import Polygon, box

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region
from digitizer_core.silhouette_underfill import (STRIPE_HOST_KEY, STRIPE_ON_KEY, UNDERFILL_KEY,
                                                 apply_stripes, plan_stripes)
from digitizer_core.threads import CHART, rgb_to_lab

WHITE = CHART.nearest_index(rgb_to_lab((255, 255, 255))[0])
RED = CHART.nearest_index(rgb_to_lab((179, 25, 66))[0])
NAVY = CHART.nearest_index(rgb_to_lab((10, 40, 88))[0])


def _r(sid, poly, thread, layer):
    return Region(sid, poly, thread, CHART[thread].number, poly.area,
                  meta={"layer": layer, "tier": "auto"})


def _field(n=7, w=100.0, h=4.0):
    """n alternating bands, red first (layer 0), white (layer 1)."""
    return [_r(f"B{i}", box(0, i * h, w, (i + 1) * h), RED if i % 2 == 0 else WHITE,
               0 if i % 2 == 0 else 1) for i in range(n)]


def test_default_is_off():
    assert PipelineConfig().stripe_underfill is False


def test_a_field_fills_its_lighter_thread_under_the_darker():
    [(host, ring, outline, merged, inner)] = plan_stripes(_field())
    assert host is ring and host.thread_index == WHITE
    assert outline.equals(box(0, 0, 100, 28)) or abs(outline.area - 2800) < 1e-6
    assert len(merged) == 2                       # three whites: one host, two merged
    assert sorted(r.shape_id for r in inner if r.thread_index == RED) == \
        ["B0", "B2", "B4", "B6"]


def test_the_fill_sews_first_and_the_bands_on_it_are_tagged():
    out, report = apply_stripes(_field())
    assert report and report[0]["stripes"]
    host = next(r for r in out if r.meta.get(STRIPE_HOST_KEY))
    assert host.meta[UNDERFILL_KEY].area == pytest.approx(2800)
    reds = [r for r in out if r.thread_index == RED]
    assert all(r.meta[STRIPE_ON_KEY] == host.shape_id for r in reds)
    assert all(r.meta["layer"] > host.meta["layer"] for r in reds)
    # the merged whites are gone: the fill sews them
    assert sum(1 for r in out if r.thread_index == WHITE) == 1


@pytest.mark.parametrize("regions", [
    _field(n=3),                                                    # too few bands
    [_r("A", box(0, 0, 100, 4), RED, 0), _r("B", box(0, 4, 100, 8), RED, 0),
     _r("C", box(0, 8, 100, 12), WHITE, 1), _r("D", box(0, 12, 100, 16), WHITE, 1)],
    [_r(f"Q{i}", box(i * 10, 0, (i + 1) * 10, 10), RED if i % 2 else WHITE, i % 2)
     for i in range(6)],                                            # squares, not bands
], ids=["three", "same-colour-neighbours", "squares"])
def test_no_field(regions):
    assert plan_stripes(regions) == []
    assert apply_stripes(regions) == (regions, [])


def test_a_hole_in_the_field_is_no_field():
    regions = _field()
    regions[3] = _r("B3", Polygon(box(0, 12, 100, 16).exterior, [box(40, 12.5, 60, 15.5).exterior]),
                    WHITE, 1)
    assert plan_stripes(regions) == []


def test_lettering_is_never_a_band():
    regions = _field()
    regions[0].meta["text_candidate"] = True
    regions[2].meta["text_candidate"] = True
    regions[4].meta["text_candidate"] = True
    regions[6].meta["text_candidate"] = True
    assert plan_stripes(regions) == []


def test_a_carrier_of_the_light_thread_sews_ahead_of_the_fill():
    """The canton carries the stars: it stays ahead of the white fill."""
    regions = _field()
    canton = Polygon(box(-30, 0, 0, 28).exterior, [box(-20, 10, -16, 14).exterior])
    star = box(-20, 10, -16, 14)
    regions = [_r("C", canton, NAVY, 1)] + [
        _r(r.shape_id, r.polygon, r.thread_index, 0 if r.thread_index == RED else 2)
        for r in regions] + [_r("S", star, WHITE, 2)]
    out, _ = apply_stripes(regions)
    layer = {r.shape_id: r.meta["layer"] for r in out}
    host = next(r.shape_id for r in out if r.meta.get(STRIPE_HOST_KEY))
    assert layer["C"] < layer[host] == layer["S"] < layer["B0"]


# --- the whole pipeline -------------------------------------------------------

RED_BGR = (66, 25, 179)
WHITE_BGR = (250, 250, 250)
NAVY_BGR = (88, 40, 10)
STRIPES = 7
ROW_PX = 48  # 4 mm at 100 mm wide: satin when side by side


@pytest.fixture(scope="module")
def flag():
    art = np.full((ROW_PX * STRIPES, 1200, 4), 255, np.uint8)
    for i in range(STRIPES):
        art[i * ROW_PX:(i + 1) * ROW_PX, :, :3] = RED_BGR if i % 2 == 0 else WHITE_BGR
    art[:ROW_PX * 4, :480, :3] = NAVY_BGR
    return art


def _sew(art, **flags):
    cfg = PipelineConfig(target_width_mm=100, forced_class="flat", edge_cap="none",
                         garment_id="hat_front", garment_rgb=(120, 120, 120), **flags)
    return digitize(art.copy(), cfg)[1]


def _block_rgbs(plan):
    return [tuple(b.rgb) if hasattr(b, "rgb") else None for b in plan.blocks]


def _inner_red_widths(plan):
    """Sewn width of every red band that does not lie on the field's edge,
    5th to 95th percentile of its needles in y."""
    ys = []
    for b in plan.blocks:
        if b.thread_index != RED:
            continue
        for run in b.runs:
            if run.kind == "satin":
                v = np.array([p[1] for p in run.points])
                ys.append((v.min(), np.percentile(v, 95) - np.percentile(v, 5)))
    ys.sort()
    return [w for _lo, w in ys[1:-1]]


def test_on_the_flag_the_red_bands_sew_their_art(flag):
    art_mm = 100.0 * ROW_PX / 1200
    plan = _sew(flag, stripe_underfill=True)
    widths = _inner_red_widths(plan)
    assert widths, "no inner red band"
    assert np.median(widths) == pytest.approx(art_mm, abs=0.15)
    white = [b for b in plan.blocks if b.thread_index == WHITE]
    assert [r.kind for b in white for r in b.runs if r.kind in ("fill", "satin")] == ["fill"]
    # navy, white, red: the canton keeps its place ahead of the fill
    order = [b.thread_index for b in plan.blocks]
    assert order.index(NAVY) < order.index(WHITE) < order.index(RED)


def test_off_the_last_colour_lies_over_its_neighbours(flag):
    """The fault the flag fixes, pinned so a change to the side-by-side path shows."""
    art_mm = 100.0 * ROW_PX / 1200
    plan = _sew(flag)
    assert not any(r.kind == "fill" for b in plan.blocks if b.thread_index == WHITE
                   for r in b.runs)
    # red sews last here and takes its pull on both rails, over the white
    assert [b.thread_index for b in plan.blocks][-1] == RED
    assert np.median(_inner_red_widths(plan)) > art_mm + 0.35
