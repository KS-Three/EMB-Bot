"""A blend rim between two inks is never a thread of its own
(`cfg.flat_blend_band_any_scale`, built OFF 2026-11-14, ON since that day by
Kent's flip, "Flip ON"; `_quant` below is the OFF arm unless a test sets it).

`flat_ramp_blend_dissolve` (ON) already folds a cluster that is edge only at
a ramp's depth and lies on the chord between two kept colours -- on an
ENLARGED raster only. A JPEG at or above the working grid has the same rim
from compression and anti-aliasing: silhouette_logo's white letters sewed in
mint satin outlines, ProSeal's teal bar under a Spearmint band. ON, the round
runs there too: `BLEND_BAND_PX` deep, the Lab or the RGB chord, each band
pixel to the label of its nearest non-band pixel (the page included; a speck
or hairline never a target). A thin colour that is not
between its neighbours (a keyline) stays. Stage 2 only (`prep` + `quantize`).
"""
import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core import stage2_quantize as q
from digitizer_core.stage1_prep import prep
from digitizer_core.threads import chart_for
from digitizer_core.threads import rgb_to_lab

# The letters' ink. Yellow, not white: white bars on a near-white page are
# the page's colour, and stage 2 sorts them into the enclosed-background
# population, where the rim never sees them (silhouette_logo's letters read
# greenish-white, L* 91, and stay in the base population).
GREEN, WHITE, PAGE = (40, 150, 60), (250, 215, 60), (244, 241, 237)


def _is_letter(rgb):
    return rgb[0] > 200 and rgb[1] > 170 and rgb[2] < 140


def _blend(a, b, t):
    return tuple(int(round(x + (y - x) * t)) for x, y in zip(a, b))


def _letters_on_green(rim=True):
    """White bars on a green disc, each bar wrapped in a 3 px rim half way
    between them (a JPEG's mint), at a size the grid does not enlarge."""
    img = np.full((800, 800, 3), PAGE, np.uint8)
    cv2.circle(img, (400, 400), 380, GREEN, -1)
    mint = _blend(WHITE, GREEN, 0.45)
    for k in range(6):
        x0 = 150 + k * 90
        if rim:
            cv2.rectangle(img, (x0 - 3, 250 - 3), (x0 + 30 + 3, 550 + 3), mint, -1)
        cv2.rectangle(img, (x0, 250), (x0 + 30, 550), WHITE, -1)
    return img[:, :, ::-1].copy()      # BGR -> the RGB `prep` reads


def _quant(img, **kw):
    kw.setdefault("flat_blend_band_any_scale", False)     # OFF arm unless set (pre-flip engine)
    cfg = PipelineConfig(max_colors=6, forced_class="flat", target_width_mm=60.0, **kw)
    p = prep(img, cfg, design_class="flat")
    return p, q.quantize(p, cfg), cfg


def _threads(qq, cfg):
    chart = chart_for(cfg)
    return [chart[s].rgb for s in qq.thread_indices]


def _has_between(rgbs, a, b, tol=12.0):
    la, lb = rgb_to_lab(np.array([a], float))[0], rgb_to_lab(np.array([b], float))[0]
    for c in rgbs:
        lc = rgb_to_lab(np.array([c], float))[0]
        ab = lb - la
        t = float((lc - la) @ ab) / float(ab @ ab)
        if 0.15 < t < 0.85 and float(np.linalg.norm(lc - (la + t * ab))) < tol:
            return True
    return False


def test_the_raster_is_not_enlarged():
    p, _qq, _cfg = _quant(_letters_on_green())
    assert p.px_per_mm <= p.input_px_per_mm + 1e-6


def test_off_the_rim_is_a_thread_on_it_joins_the_letters():
    _p, off, cfg = _quant(_letters_on_green())
    assert _has_between(_threads(off, cfg), WHITE, GREEN), _threads(off, cfg)
    _p, on, cfg = _quant(_letters_on_green(), flat_blend_band_any_scale=True)
    assert not _has_between(_threads(on, cfg), WHITE, GREEN), _threads(on, cfg)
    # the rim split between what it touches: the letters gained part of it
    # (the 3 px rim, nearest-pixel, gives each side about half)
    white = [i for i, s in enumerate(on.thread_indices) if _is_letter(chart_for(cfg)[s].rgb)]
    assert white
    _p, norim, _c = _quant(_letters_on_green(rim=False))
    nw = [i for i, s in enumerate(norim.thread_indices) if _is_letter(chart_for(cfg)[s].rgb)]
    gained = int(np.isin(on.labels, white).sum()) - int(np.isin(norim.labels, nw).sum())
    rim_px = 6 * ((36 + 1) * (306 + 1) - 31 * 301)
    assert 0.2 * rim_px < gained < 0.8 * rim_px, (gained, rim_px)


def test_a_speck_of_the_band_colour_elsewhere_joins_what_it_touches():
    # ProSeal: the pale band over the teal bar also rings black strokes as
    # JPEG noise. Folded as a cluster into the teal it painted those specks
    # teal (a teal N). Nearest-pixel, a speck in the green field goes green.
    img = _letters_on_green()[:, :, ::-1].copy()
    mint = _blend(WHITE, GREEN, 0.45)
    cv2.rectangle(img, (150, 650), (153, 700), mint, -1)       # a lone mint sliver in the field
    img = img[:, :, ::-1].copy()
    _p, on, cfg = _quant(img, flat_blend_band_any_scale=True)
    chart = chart_for(cfg)
    lab_at = on.labels[675, 151]
    assert lab_at >= 0 and not _is_letter(chart[on.thread_indices[lab_at]].rgb)


def test_a_rim_against_the_page_splits_with_the_page():
    # ProSeal's hexagon cells: teal on white, each ringed by a pale JPEG rim,
    # 0.3-0.5 mm apart. Joined all to the ink, every cell grew a pixel a side
    # into the white gaps and stage 6 closed them. Half to each side keeps
    # the gap: each square takes about half its rim, the page the rest.
    teal = (0, 150, 170)
    img = np.full((800, 800, 3), PAGE, np.uint8)
    pale = _blend(PAGE, teal, 0.3)
    for x0 in (150, 406):
        cv2.rectangle(img, (x0 - 3, 250 - 3), (x0 + 240 + 2, 550 + 2), pale, -1)
    for x0 in (150, 406):
        cv2.rectangle(img, (x0, 250), (x0 + 239, 549), teal, -1)
    img = img[:, :, ::-1].copy()
    p, off, cfg = _quant(img)
    assert p.px_per_mm == p.input_px_per_mm
    assert len(off.thread_indices) == 2, _threads(off, cfg)      # teal + the rim's own
    _p, on, cfg = _quant(img, flat_blend_band_any_scale=True)
    assert len(on.thread_indices) == 1, _threads(on, cfg)
    m = (on.labels == 0).astype(np.uint8)
    n, _cc, stats, _c = cv2.connectedComponentsWithStats(m, 8)
    rim = 246 * 306 - 240 * 300
    assert n - 1 == 2
    for a in stats[1:, cv2.CC_STAT_AREA]:
        assert 240 * 300 + 0.3 * rim < a < 240 * 300 + 0.7 * rim, (a, rim)
    assert (on.labels[400, 392:404] == -1).all()                 # the gap is page


def test_a_keyline_that_is_not_a_blend_stays():
    # A 4 px black ring between a white field and a blue disc: thin, all edge
    # at 2 px, and not between white and blue. It keeps its thread.
    img = np.full((800, 800, 3), PAGE, np.uint8)
    cv2.circle(img, (400, 400), 360, WHITE, -1)
    cv2.circle(img, (400, 400), 200, (10, 10, 10), -1)
    cv2.circle(img, (400, 400), 196, (30, 60, 200), -1)
    img = img[:, :, ::-1].copy()
    _p, off, cfg = _quant(img)
    _p, on, _c = _quant(img, flat_blend_band_any_scale=True)
    dark = lambda qq: any(sum(chart_for(cfg)[s].rgb) < 120 for s in qq.thread_indices)  # noqa: E731
    assert dark(off) and dark(on)
    assert off.thread_indices == on.thread_indices


def test_an_enlarged_raster_is_untouched_on():
    big = np.full((120, 120, 3), PAGE, np.uint8)
    cv2.circle(big, (60, 60), 50, GREEN, -1)
    cv2.rectangle(big, (40, 30), (50, 90), WHITE, -1)
    big = big[:, :, ::-1].copy()
    cfg_a = PipelineConfig(max_colors=6, forced_class="flat", target_width_mm=60.0,
                           flat_blend_band_any_scale=False)
    cfg_b = PipelineConfig(max_colors=6, forced_class="flat", target_width_mm=60.0,
                           flat_blend_band_any_scale=True)
    pa, pb = prep(big, cfg_a, design_class="flat"), prep(big, cfg_b, design_class="flat")
    assert pa.px_per_mm > pa.input_px_per_mm
    qa, qb = q.quantize(pa, cfg_a), q.quantize(pb, cfg_b)
    assert np.array_equal(qa.labels, qb.labels) and qa.thread_indices == qb.thread_indices


def test_rgb_chord_reads_a_blend_the_lab_chord_misses():
    page, teal = np.array([255.0, 255.0, 255.0]), np.array([0.0, 165.0, 180.0])
    band = page + 0.25 * (teal - page)
    mean = {7: band, 3: teal}
    t = q._rgb_chord_t(7, None, 3, mean, page, 6.0)
    assert t is not None and abs(t - 0.25) < 0.01
    assert q._rgb_chord_t(7, None, 3, {7: np.array([255.0, 0.0, 0.0]), 3: teal}, page, 6.0) is None


def test_on_by_default():
    # Kent's flip 2026-11-14 ("Flip ON"); PRE_FLIP keeps the OFF arm
    assert PipelineConfig().flat_blend_band_any_scale is True
    assert q.BLEND_BAND_PX == 2
