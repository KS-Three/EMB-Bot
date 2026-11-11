"""`cfg.sliver_prune` (built OFF 2026-11-10): masks narrower than the source's
own pixels that are not a shape (`digitizer_core/sliver_prune.py`).

Kent's Pooh at 54 mm is the measurement (not committed: Disney art, kept in
gitignored `scratch_kent/`). Automatic lane, 266 px source enlarged x1.81:
three near-white masks along the right silhouette, 0.91 / 0.96 / 0.99 source
pixels wide, on threads 2.6 / 11.9 / 11.9 dE00 from the page, sewed as seven
white runs; the shirt carried a 57 px (7.1 mm) spike wedged between two gold
shapes, 18.7 dE00 off the shirt's own colour. ON: 30 -> 23 shapes, 11,036 ->
10,580 stitch records, 9 -> 6 colour blocks. Kept beside them, and the reason
for each guard below: a real ear outline 1.32 source pixels wide on the
silhouette (41.7 dE00 from the page), a body spur out on the page (55% page
rim), a body spur in its own colour (3.0 dE00).

The synthetic frame is 8 px/mm from a 4 px/mm source, so one source pixel is
two working pixels and the tendril opening is 5 px across.
"""
from types import SimpleNamespace

import numpy as np

from digitizer_core import sliver_prune
from digitizer_core.config import PipelineConfig
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.threads import load_chart, rgb_to_lab

H, W = 170, 180
PAGE = (255, 255, 255)
GOLD = (216, 140, 2)
RED = (200, 20, 30)
CREASE = (105, 45, 30)      # the dark line drawn between two gold shapes
HALO = (236, 236, 236)      # the page's half of a JPEG edge ramp
OUTLINE = (70, 40, 25)
CHART = load_chart()


def _thread(rgb) -> int:
    return CHART.nearest_index(rgb_to_lab(np.asarray(rgb, np.float64).reshape(1, 3))[0])


class Scene:
    """Masks painted into one frame; the page is whatever no mask covers."""

    def __init__(self):
        self.rgb = np.full((H, W, 3), PAGE, np.uint8)
        self.masks: list[np.ndarray] = []
        self.threads: list[int] = []

    def add(self, thread_rgb, *rects, paint=None) -> int:
        m = np.zeros((H, W), bool)
        for y0, x0, y1, x1 in rects:
            m[y0:y1, x0:x1] = True
        for other in self.masks:
            other &= ~m
        self.masks.append(m)
        self.threads.append(_thread(thread_rgb))
        self.rgb[m] = paint or thread_rgb
        return len(self.masks) - 1

    def paint(self, rgb, y0, x0, y1, x1):
        self.rgb[y0:y1, x0:x1] = rgb

    def build(self, alpha=False):
        covered = np.zeros((H, W), bool)
        for m in self.masks:
            covered |= m
        p = SimpleNamespace(rgb=self.rgb, bg_mask=~covered, bg_rgb=PAGE, bg_from_alpha=alpha,
                            px_per_mm=8.0, input_px_per_mm=4.0)
        masks = [RegionMask.from_full(m, layer) for layer, m in enumerate(self.masks)]
        return masks, self.threads, p


def _figure():
    """A gold body (20..100 x 20..140) over a red shirt (100..130)."""
    s = Scene()
    gold = s.add(GOLD, (20, 20, 100, 140))
    shirt = s.add(RED, (100, 20, 130, 140))
    return s, gold, shirt


def _areas(masks):
    return [m.area for m in masks]


def test_default_is_off():
    assert PipelineConfig().sliver_prune is False


def test_an_off_colour_tendril_wedged_in_the_figure_goes_to_its_neighbour():
    s, gold, shirt = _figure()
    s.masks[shirt][40:100, 78:82] = True        # the spike: 4 px = 2 source px wide, 60 long
    s.masks[gold][40:100, 78:82] = False
    s.paint(CREASE, 40, 78, 100, 82)
    masks, threads, p = s.build()
    before = _areas(masks)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats == {"tendrils": 1, "page_slivers": 0}
    after = _areas(out)
    moved = before[shirt] - after[shirt]
    # all 240 px of it bar the fillet an opening leaves where a spike meets its body
    assert 230 <= moved <= 240 and after[gold] == before[gold] + moved
    assert out[shirt].bbox[0] >= 98 and out[shirt].bbox[1:] == (20, 130, 140)   # re-cropped
    assert out[gold].full_mask()[40:98, 78:82].all()
    assert _areas(masks) == before                       # the caller's masks are untouched


def test_a_tendril_in_its_bodys_own_colour_stays():
    """A whisker in the nose's ink is the nose's."""
    s, gold, shirt = _figure()
    s.masks[shirt][40:100, 78:82] = True
    s.masks[gold][40:100, 78:82] = False
    s.paint(RED, 40, 78, 100, 82)
    masks, threads, p = s.build()
    before = _areas(masks)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["tendrils"] == 0 and _areas(out) == before


def test_a_tendril_out_on_the_page_stays():
    """A balloon's string: page on both sides, nothing to hand it to."""
    s, gold, shirt = _figure()
    s.masks[shirt][130:168, 78:82] = True
    s.paint(CREASE, 130, 78, 168, 82)
    masks, threads, p = s.build()
    before = _areas(masks)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["tendrils"] == 0 and _areas(out) == before


def test_a_bridge_between_two_bodies_of_one_mask_is_not_cut():
    s = Scene()
    gold = s.add(GOLD, (20, 20, 150, 140))
    red = s.add(RED, (30, 30, 60, 130), (110, 30, 140, 130), (60, 78, 110, 82))
    s.paint(CREASE, 60, 78, 110, 82)
    masks, threads, p = s.build()
    before = _areas(masks)
    recs = [r for r in sliver_prune.tendrils(masks, p) if r["index"] == red]
    assert recs and all(r["bridge"] and not r["tendril"] for r in recs)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["tendrils"] == 0 and out is masks and _areas(out) == before
    assert not out[gold].full_mask()[60:110, 78:82].any()        # gold took none of it


def test_two_tendrils_holding_a_lobe_on_lose_only_one():
    """Neither is a bridge alone; the second is once the first has gone."""
    s = Scene()
    gold = s.add(GOLD, (10, 10, 160, 170))
    red = s.add(RED, (30, 30, 70, 150), (110, 30, 150, 150), (70, 60, 110, 64), (70, 100, 110, 104))
    s.paint(CREASE, 70, 60, 110, 64)
    s.paint(CREASE, 70, 100, 110, 104)
    masks, threads, p = s.build()
    recs = [r for r in sliver_prune.tendrils(masks, p) if r["index"] == red]
    assert len(recs) == 2 and all(r["tendril"] and not r["bridge"] for r in recs)
    before = _areas(masks)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["tendrils"] == 1
    assert sliver_prune._pieces(out[red].crop) == 1               # the lobe is still attached
    assert sum(_areas(out)) == sum(before) and _areas(out)[gold] > before[gold]


def test_two_spikes_and_a_halo_on_one_figure():
    """Records made on the masks as they came in, applied one after another."""
    s, gold, shirt = _figure()
    for x in (60, 100):
        s.masks[shirt][40:100, x:x + 4] = True
        s.masks[gold][40:100, x:x + 4] = False
        s.paint(CREASE, 40, x, 100, x + 4)
    halo = s.add(HALO, (30, 140, 90, 142))
    masks, threads, p = s.build()
    before = _areas(masks)
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats == {"tendrils": 2, "page_slivers": 1} and len(out) == 2 and halo == 2
    moved = before[shirt] - out[shirt].area
    assert 460 <= moved <= 480 and out[gold].area == before[gold] + moved
    assert sliver_prune._pieces(out[shirt].crop) == 1 and sliver_prune._pieces(out[gold].crop) == 1
    assert out[gold].full_mask()[40:98, 60:64].all() and out[gold].full_mask()[40:98, 100:104].all()


def test_a_mask_another_rule_kept_is_left_alone():
    """A floor-rescued stroke or a dot rung is someone's decision, not a halo."""
    s, gold, shirt = _figure()
    s.masks[shirt][40:100, 78:82] = True
    s.masks[gold][40:100, 78:82] = False
    s.paint(CREASE, 40, 78, 100, 82)
    halo = s.add(HALO, (30, 140, 90, 142))
    masks, threads, p = s.build()
    masks[halo].floor_rescued = True
    masks[shirt].dot_rung = True
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert out is masks and stats == {"tendrils": 0, "page_slivers": 0}


def test_the_pipeline_calls_it_only_when_on(monkeypatch):
    """The wiring in `build_generation`: reached ON, on an enlarged flat
    raster (100 px at 40 mm), with stage 3's masks; never OFF."""
    import cv2

    from digitizer_core import pipeline

    big = np.full((400, 400, 3), PAGE, np.uint8)
    cv2.ellipse(big, (200, 200), (150, 120), 0, 0, 360, GOLD[::-1], -1)
    cv2.rectangle(big, (110, 220), (290, 290), RED[::-1], -1)
    bgr = cv2.resize(big, (100, 100), interpolation=cv2.INTER_AREA)
    seen = []
    real = sliver_prune.prune

    def spy(masks, thread_indices, p, chart):
        seen.append((len(masks), sliver_prune._src_px(p)))
        return real(masks, thread_indices, p, chart)

    monkeypatch.setattr(sliver_prune, "prune", spy)
    kw = dict(max_colors=4, forced_class="flat", target_width_mm=40.0)
    off = pipeline.build_generation(bgr, PipelineConfig(**kw))
    assert seen == []
    on = pipeline.build_generation(bgr, PipelineConfig(sliver_prune=True, **kw))
    assert len(seen) == 1 and seen[0][0] >= 2 and seen[0][1] >= sliver_prune.MIN_ENLARGEMENT
    assert len(on.regions) >= 2 and len(off.regions) >= 2


def test_a_page_coloured_sliver_on_the_silhouette_is_dropped():
    s, gold, shirt = _figure()
    halo = s.add(HALO, (30, 140, 90, 142))      # 2 px = 1 source px, on the body's right edge
    masks, threads, p = s.build()
    rec = next(r for r in sliver_prune.page_slivers(masks, threads, p, CHART) if r["index"] == halo)
    assert rec["sliver"] and rec["mean_width_src_px"] <= 1.0
    assert 0.4 <= rec["page"] <= 0.6 and rec["figure"] >= 0.4
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats == {"tendrils": 0, "page_slivers": 1}
    assert len(out) == len(masks) - 1 and _areas(out) == _areas(masks)[:2]


def test_a_thin_dark_outline_on_the_silhouette_stays():
    """Pooh's ear outline: as thin, as much on the page, but not the page's colour."""
    s, gold, shirt = _figure()
    line = s.add(OUTLINE, (30, 140, 90, 142))
    masks, threads, p = s.build()
    rec = next(r for r in sliver_prune.page_slivers(masks, threads, p, CHART) if r["index"] == line)
    assert not rec["sliver"] and rec["de_page"] > sliver_prune.SLIVER_PAGE_DE00_MAX
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["page_slivers"] == 0 and len(out) == len(masks)


def test_a_pale_stroke_alone_on_the_page_stays():
    """A pale letter's stem touches no figure: not a silhouette's halo."""
    s, gold, shirt = _figure()
    stem = s.add(HALO, (30, 160, 90, 162))
    masks, threads, p = s.build()
    rec = next(r for r in sliver_prune.page_slivers(masks, threads, p, CHART) if r["index"] == stem)
    assert not rec["sliver"] and rec["figure"] == 0.0
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["page_slivers"] == 0 and len(out) == len(masks)


def test_a_pale_band_wider_than_the_source_resolves_stays():
    """A real pale keyline, three source pixels wide, is never asked."""
    s, gold, shirt = _figure()
    band = s.add(HALO, (30, 140, 90, 146))
    masks, threads, p = s.build()
    assert all(r["index"] != band for r in sliver_prune.page_slivers(masks, threads, p, CHART))


def test_an_alpha_cutout_has_no_page_half():
    s, gold, shirt = _figure()
    s.add(HALO, (30, 140, 90, 142))
    masks, threads, p = s.build(alpha=True)
    assert sliver_prune.page_slivers(masks, threads, p, CHART) == []
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert stats["page_slivers"] == 0 and len(out) == len(masks)


def test_a_source_at_or_near_the_grid_is_untouched():
    """The same tendril and the same halo, on a raster stage 1 did not enlarge
    (or enlarged under `MIN_ENLARGEMENT`: 8 / 6.5 = x1.23)."""
    s, gold, shirt = _figure()
    s.masks[shirt][40:100, 78:82] = True
    s.masks[gold][40:100, 78:82] = False
    s.paint(CREASE, 40, 78, 100, 82)
    s.add(HALO, (30, 140, 90, 142))
    masks, threads, p = s.build()
    assert sliver_prune.prune(masks, threads, p, CHART)[1] == {"tendrils": 1, "page_slivers": 1}
    for native in (8.0, 12.0, 0.0, 6.5):
        p.input_px_per_mm = native
        out, stats = sliver_prune.prune(masks, threads, p, CHART)
        assert out is masks and stats == {"tendrils": 0, "page_slivers": 0}
    assert sliver_prune.MIN_ENLARGEMENT == 1.25


def test_nothing_found_returns_the_list_as_given():
    s, gold, shirt = _figure()
    masks, threads, p = s.build()
    out, stats = sliver_prune.prune(masks, threads, p, CHART)
    assert out is masks and stats == {"tendrils": 0, "page_slivers": 0}


def test_a_source_at_the_grid_reads_one_pixel_as_one_pixel():
    p = SimpleNamespace(px_per_mm=8.0, input_px_per_mm=8.0)
    assert sliver_prune._src_px(p) == 1.0
    assert sliver_prune._src_px(SimpleNamespace(px_per_mm=8.0, input_px_per_mm=0.0)) == 1.0
    assert sliver_prune._src_px(SimpleNamespace(px_per_mm=8.0, input_px_per_mm=12.0)) == 1.0
