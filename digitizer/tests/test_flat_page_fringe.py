"""`cfg.flat_page_fringe_exclude` (built OFF 2026-11-03): the figure's page-edge
anti-alias fringe neither votes in the palette fit nor survives as slivers.

Fixture: a dark-outlined gold ellipse with a pale sheen patch on an off-white
page, drawn at 4x and downsampled so the edge ramp is real, then enlarged by
stage 1 the way a low-resolution source always is (4x here: the ramp is the
upscale factor wide, which is why the band scales with it).
"""
import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_quantize import quantize
from digitizer_core.threads import chart_for

PAGE = (244, 241, 237)
OUTLINE = (70, 40, 25)
GOLD = (216, 140, 2)
SHEEN = (190, 182, 150)
KEYLINE = (190, 215, 235)   # a pale blue ring: not a tint of the page


def _art(keyline=None, s=4, n=100):
    big = np.full((n * s, n * s, 3), PAGE, np.uint8)
    c = (n * s // 2, n * s // 2)
    if keyline:
        cv2.ellipse(big, c, (41 * s, 35 * s), 0, 0, 360, keyline, -1)
    cv2.ellipse(big, c, (38 * s, 32 * s), 0, 0, 360, OUTLINE, -1)
    cv2.ellipse(big, c, (37 * s, 31 * s), 0, 0, 360, GOLD, -1)
    cv2.ellipse(big, (c[0] - 10 * s, c[1] - 6 * s), (12 * s, 8 * s), 0, 0, 360, SHEEN, -1)
    return cv2.resize(big, (n, n), interpolation=cv2.INTER_AREA)


def _run(rgb, on, **kw):
    cfg = PipelineConfig(max_colors=4, forced_class="flat", target_width_mm=40.0,
                         flat_page_fringe_exclude=on, **kw)
    p = prep(np.ascontiguousarray(rgb[..., ::-1]), cfg, design_class="flat")
    return p, quantize(p, cfg), cfg


def _small_pale_components(p, q, cfg, floor_mm2=1.5):
    """Sub-floor components of the label nearest the sheen colour."""
    chart = chart_for(cfg)
    sheen = np.array(SHEEN, float)
    lbl = min(range(len(q.thread_indices)),
              key=lambda i: np.linalg.norm(np.array(chart[q.thread_indices[i]].rgb, float) - sheen))
    n, _cc, st, _ = cv2.connectedComponentsWithStats((q.labels == lbl).astype(np.uint8), connectivity=8)
    area_mm2 = st[1:, cv2.CC_STAT_AREA] / p.px_per_mm ** 2
    return int((area_mm2 < floor_mm2).sum()), int((area_mm2 >= floor_mm2).sum())


def test_off_records_no_fringe_and_is_the_unflagged_path():
    p, q, _ = _run(_art(), False)
    assert q.page_fringe is None


def test_on_finds_a_fringe_of_figure_pixels_beside_the_page():
    # `flat_outline_max_mm=0`: no label is thin, so this reads the page band alone
    p, q, _ = _run(_art(), True, flat_outline_max_mm=0.0)
    f = q.page_fringe
    assert f is not None and f.sum() > 300
    assert not (f & p.bg_mask).any()            # figure pixels only
    dist = cv2.distanceTransform((~p.bg_mask).astype(np.uint8), cv2.DIST_L2, 5)
    assert dist[f].max() <= 6                   # within the band (4x upscale + 1 + slack)


def test_on_leaves_fewer_pale_slivers_and_keeps_the_sheen():
    off = _small_pale_components(*_run(_art(), False))
    on = _small_pale_components(*_run(_art(), True))
    assert on[0] < off[0]                       # fewer sub-floor pale slivers
    assert on[1] >= 1                           # the real sheen is still there


def test_the_sheen_keeps_its_own_thread_on():
    p, q, cfg = _run(_art(), True)
    chart = chart_for(cfg)
    sheen = np.array(SHEEN, float)
    # a centre within 12 dE-ish RGB distance of the sheen's own colour
    near = [np.linalg.norm(np.array(chart[t].rgb, float) - sheen) for t in q.thread_indices]
    assert min(near) < 60


def test_a_keyline_off_the_chord_survives_on():
    """A pale ring round the figure is real content: one component, same thread, ON as OFF."""
    img = _art(keyline=KEYLINE)
    res = {}
    for on in (False, True):
        p, q, cfg = _run(img, on)
        chart = chart_for(cfg)
        key = np.array(KEYLINE, float)
        lbl = min(range(len(q.thread_indices)),
                  key=lambda i: np.linalg.norm(np.array(chart[q.thread_indices[i]].rgb, float) - key))
        n, _cc, st, _ = cv2.connectedComponentsWithStats((q.labels == lbl).astype(np.uint8), connectivity=8)
        res[on] = (n - 1, int((q.labels == lbl).sum()), chart[q.thread_indices[lbl]].name)
    assert res[True][0] == 1                    # still one ring
    assert res[True][2] == res[False][2]        # on the same thread
    assert abs(res[True][1] - res[False][1]) < 0.03 * res[False][1]


def test_an_alpha_cutout_is_a_noop():
    """No page, no fringe: the flag changes nothing for an image with real alpha."""
    rgb = _art()
    alpha = np.where(cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY) < 240, 255, 0).astype(np.uint8)
    rgba = np.dstack([rgb[..., ::-1], alpha])   # BGRA
    outs = []
    for on in (False, True):
        cfg = PipelineConfig(max_colors=4, forced_class="flat", target_width_mm=40.0,
                             flat_page_fringe_exclude=on)
        p = prep(np.ascontiguousarray(rgba), cfg, design_class="flat")
        assert p.bg_from_alpha
        q = quantize(p, cfg)
        assert q.page_fringe is None
        outs.append(q.labels)
    assert np.array_equal(outs[0], outs[1])


def test_off_labels_ignore_the_band_constant():
    """OFF reads neither flag nor band width: labels identical for any `flat_page_fringe_px`."""
    a = _run(_art(), False, flat_page_fringe_px=2)[1].labels
    b = _run(_art(), False, flat_page_fringe_px=7)[1].labels
    assert np.array_equal(a, b)


def test_the_outline_inner_blend_adds_fringe_and_a_zero_width_outline_removes_it():
    """B (`outline_inner_blend`): the blend between the thin dark outline and the fill is
    fringe too; `flat_outline_max_mm=0` means no label is thin, so only the page band remains."""
    with_b = _run(_art(), True)[1].page_fringe
    page_only = _run(_art(), True, flat_outline_max_mm=0.0)[1].page_fringe
    assert with_b.sum() > page_only.sum() + 200
    # the union never touches the outline's own pixels' page side: still figure pixels only
    p = _run(_art(), True)[0]
    assert not (with_b & p.bg_mask).any()
