"""`cfg.fine_bar_survive` (built OFF 2026-11-14): thin ink bars kept whole.

To a T's speed lines (Kent's five pins) are split into pieces by stages 2-4
and lost at stage 5 when the field sewn first grows over them. The pass reads
each bar off the art and redraws it as one straight bar; stage 5 keeps its art.

Synthetic: a white page with one straight black line 0.375 mm thick (3 px at
8 px/mm), whose stage-4 trace is two pieces with a 5 mm gap."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from shapely.geometry import box

from digitizer_core import fine_bar as fb
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.threads import chart_for

PPM = 8.0
W, H = 400, 160                 # px: 50 x 20 mm, centre (200, 80)


def _nearest(cfg, rgb):
    ch = chart_for(cfg)
    return min(range(len(ch)), key=lambda i: sum((a - b) ** 2 for a, b in zip(ch[i].rgb, rgb)))


def _prep(draw):
    rgb = np.full((H, W, 3), 255, np.uint8)
    draw(rgb)
    return SimpleNamespace(rgb=rgb, px_per_mm=PPM, art_bbox=(0, 0, W, H), bg_rgb=(255, 255, 255))


def _line(rgb):
    rgb[79:82, 80:320] = 0      # x -15..15 mm, 3 px thick


def _regions(cfg, pieces, *, ink=(0, 0, 0)):
    k, w = _nearest(cfg, ink), _nearest(cfg, (255, 255, 255))
    field = Region("SF", box(-24, -9, 24, 9), w, "W", 48 * 18, meta={"layer": 0})
    out = [field]
    for i, poly in enumerate(pieces):
        out.append(Region(f"S{i}", poly, k, "K", poly.area, meta={"layer": 1}))
    return out


def test_flag_is_off_by_default():
    assert PipelineConfig().fine_bar_survive is False


def test_a_split_bar_becomes_one_straight_bar():
    cfg = PipelineConfig(fine_bar_survive=True)
    p = _prep(_line)
    regions = _regions(cfg, [box(-15, -0.125, -5, 0.125), box(0, -0.125, 15, 0.125)])
    recs = fb.apply_fine_bar_survive(regions, p, cfg)
    bars = [r for r in regions if r.shape_id != "SF"]
    assert len(recs) == 1 and recs[0]["pieces"] == 2
    assert len(bars) == 1, [r.shape_id for r in regions]
    bar = bars[0]
    minx, miny, maxx, maxy = bar.polygon.bounds
    assert minx == pytest.approx(-15.0, abs=0.2) and maxx == pytest.approx(15.0, abs=0.2)
    assert maxy - miny == pytest.approx(0.25, abs=0.06)          # one pixel under the ink, as stage 4 traces
    assert bar.meta[fb.FINE_BAR_KEY]["pieces"] == 2
    assert bar.area_mm2 == pytest.approx(bar.polygon.area)


def test_a_whole_bar_keeps_its_outline_and_is_only_tagged():
    """Fremont's "|" divider: traced whole, sews straight already. Redrawing
    it from the anti-aliased ink only widened it, so it is left alone and
    tagged for stage 5."""
    cfg = PipelineConfig(fine_bar_survive=True)
    p = _prep(_line)
    whole = box(-15, -0.125, 15, 0.125)
    regions = _regions(cfg, [whole])
    assert fb.apply_fine_bar_survive(regions, p, cfg) == []
    assert regions[1].polygon.equals(whole)
    assert regions[1].meta[fb.FINE_BAR_KEY] == {"pieces": 1, "redrawn": False}


def test_a_curved_stroke_is_left_as_traced():
    cfg = PipelineConfig(fine_bar_survive=True)

    def arc(rgb):
        xs = np.arange(80, 320)
        ys = (80 + 0.02 * (xs - 200) ** 2).astype(int)       # 0.4 mm sag over 3 mm
        for x, y in zip(xs, ys):
            rgb[y - 1:y + 2, x] = 0
    p = _prep(arc)
    piece = box(-3, -0.125, 3, 0.125)
    regions = _regions(cfg, [piece])
    assert fb.apply_fine_bar_survive(regions, p, cfg) == []
    assert regions[1].polygon.equals(piece) and fb.FINE_BAR_KEY not in regions[1].meta


def test_a_page_coloured_sliver_is_not_ink():
    cfg = PipelineConfig(fine_bar_survive=True)

    def dark_page_white_line(rgb):
        rgb[:] = 0
        rgb[79:82, 80:320] = 255
    p = _prep(dark_page_white_line)
    p.bg_rgb = (255, 255, 255)          # the page is white: a white line is the page showing
    k = _nearest(cfg, (0, 0, 0))
    w = _nearest(cfg, (255, 255, 255))
    field = Region("SF", box(-24, -9, 24, 9), k, "K", 48 * 18, meta={"layer": 0})
    sliver = Region("S0", box(-15, -0.125, 15, 0.125), w, "W", 7.5, meta={"layer": 1})
    regions = [field, sliver]
    assert fb.apply_fine_bar_survive(regions, p, cfg) == []
    assert fb.FINE_BAR_KEY not in sliver.meta


def test_fit_bar_trims_a_letter_stroke_off_the_end():
    # a bar running into a 2 mm stroke at its right end: the stroke is not the bar
    m = np.zeros((H, W), bool)
    m[79:82, 80:300] = True
    m[76:85, 300:316] = True        # the stroke as the band clips it (1.1 mm)
    ys, xs = np.nonzero(m)
    bar = fb.fit_bar(xs.astype(float), ys.astype(float), PPM, 200.0, 80.0)
    assert bar is not None
    assert bar.bounds[2] < 300 / PPM - 25 + 0.3        # stops at the stroke (x 12.5 mm)


def _resolve(regions, cfg):
    from digitizer_core.fabrics import fabric_for_garment
    from digitizer_core.stage5_overlap import resolve_overlaps
    return resolve_overlaps(regions, fabric_for_garment("left_chest"), cfg)


def _field_over_bar(cfg, tagged: bool):
    bar = box(-10, -0.125, 10, 0.125)
    k, w = _nearest(cfg, (0, 0, 0)), _nearest(cfg, (255, 255, 255))
    # as on To a T's hat at stage 5 (traced 2026-11-14): the sewn white field
    # has become an under-fill (`silhouette_underfill`, `keyline_folded`) whose
    # polygon covers the bar's hole, so the bar sewn after it clips to nothing
    field = Region("SF", box(-24, -9, 24, 9), w, "W", 48 * 18,
                   meta={"layer": 0, "enclosed_background": True,
                         "sew_enclosed_white": "field", "stitched": True})
    meta = {"layer": 1, **({fb.FINE_BAR_KEY: {"pieces": 1}} if tagged else {})}
    return [field, Region("SB", bar, k, "K", bar.area, meta=meta)]


def test_stage5_keeps_a_redrawn_bar_the_field_grew_over():
    off = PipelineConfig()
    planned, warns = _resolve(_field_over_bar(off, tagged=True), off)
    lost = [i for w in warns if w.get("code") == "SHAPE_NOT_STITCHED" for i in w.get("ids") or ()]
    assert "SB" in lost, "the fixture must lose the bar today, or the test proves nothing"
    on = PipelineConfig(fine_bar_survive=True)
    planned, warns = _resolve(_field_over_bar(on, tagged=True), on)
    kept = [pr for pr in planned if pr.region.shape_id == "SB"]
    assert kept and kept[0].polygon.area >= 0.9 * 20 * 0.25
    assert not any(w.get("code") == "SHAPE_NOT_STITCHED" for w in warns)


def test_stage5_leaves_an_untagged_bar_to_the_clip():
    on = PipelineConfig(fine_bar_survive=True)
    _planned, warns = _resolve(_field_over_bar(on, tagged=False), on)
    lost = [i for w in warns if w.get("code") == "SHAPE_NOT_STITCHED" for i in w.get("ids") or ()]
    assert "SB" in lost


def test_off_never_loads_the_module(monkeypatch):
    """With the flag off, `build_generation` never calls the pass."""
    import digitizer_core.fine_bar as mod
    called = []
    monkeypatch.setattr(mod, "apply_fine_bar_survive", lambda *a, **k: called.append(1) or [])
    from pathlib import Path
    from digitizer_core.pipeline import build_generation
    art = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"
    build_generation(str(art), PipelineConfig(target_width_mm=30.0))
    assert called == []
    build_generation(str(art), PipelineConfig(target_width_mm=30.0, fine_bar_survive=True))
    assert called == [1]

