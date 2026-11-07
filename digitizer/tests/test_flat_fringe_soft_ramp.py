"""The flat lane's soft-edge cure (built OFF 2026-11-06): `logo_bridge_bar.jpg`
routed flat, as `stage0_scale_relative_grad` routes it.

Two mechanisms, one cause: the 400 px JPEG is enlarged x3.25 to the 8 px/mm
working grid at 113.5 mm, and its edges are about 3 SOURCE pixels soft.

1. `flat_page_fringe_soft_ramp`: the spokes' black-to-page ramp is ~9 working
   px deep; `flat_page_fringe_exclude`'s band stops at 5 (one source px). The
   neutral greys left outside it are nearer the blue lettering's centre than
   black or the page, drag it to Vintage Blue 4752, and the band copies it.
2. `flat_ramp_blend_dissolve`: the yellow-to-black and yellow-to-blue ramps
   inside the disc form olive 6156 and Tarnished Gold 0442 clusters, which the
   phantom dissolve keeps because only the one pixel at a label change counts
   as edge.

Stage 2 only (`prep` + two-tone snap + `quantize`), the pipeline's own order.
"""
import json

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig, two_tone
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_quantize import quantize
from digitizer_core.threads import chart_for

from .conftest import TESTDATA

ART = TESTDATA / "photo" / "logo_bridge_bar.jpg"
FRINGE = {"flat_page_fringe_exclude": True}
SOFT = {"flat_page_fringe_soft_ramp": True}
DISSOLVE = {"flat_ramp_blend_dissolve": True}


def _cfg(**extra):
    from digitizer_service.app import _parse_config
    from tools import pro_pair as pp
    return PipelineConfig(**_parse_config(json.dumps(pp.request(113.5, "hat_front", extra))))


@pytest.fixture(scope="module")
def pixels():
    from digitizer_service.app import _decode
    return _decode(ART.read_bytes())


def _stage2(pixels, **extra):
    cfg = _cfg(**extra)
    p = prep(pixels, cfg, design_class="flat")
    if cfg.two_tone_snap:
        two_tone.apply(p)
    return p, quantize(p, cfg), cfg


def _threads(q, cfg):
    chart = chart_for(cfg)
    return [chart[s].number for s in q.thread_indices]


def _near_page(p, q, label, reach=12):
    dist = cv2.distanceTransform((~p.bg_mask).astype(np.uint8), cv2.DIST_L2, 5)
    return int(((q.labels == label) & (dist <= reach)).sum())


def test_the_raster_is_enlarged_past_its_source(pixels):
    p, _q, _cfg = _stage2(pixels)
    assert p.px_per_mm / p.input_px_per_mm == pytest.approx(3.25, abs=0.01)


def test_off_the_blue_takes_the_spokes_page_fringe(pixels):
    # The defect, as the flat lane ships it: no 4531, a Vintage Blue slot whose
    # pixels sit along the page; the yellow ramps sew olive and gold.
    p, q, cfg = _stage2(pixels)
    t = _threads(q, cfg)
    assert "4752" in t and "4531" not in t
    assert {"6156", "0442"} <= set(t)
    assert _near_page(p, q, t.index("4752")) > 15_000


@pytest.mark.parametrize("band_src_px, left", [(None, 14_000), (3.0, 0)])
def test_the_soft_band_reaches_the_whole_page_ramp(pixels, band_src_px, left):
    # The existing fringe flag alone brings the blue back to Caribbean 4531
    # but leaves its one-source-pixel band short of the ramp: the greys past
    # it still vote blue and every band pixel copies them (16,696 px within
    # 12 px of the page). Three source px reaches it: none.
    extra = dict(FRINGE, **(SOFT if band_src_px else {}))
    p, q, cfg = _stage2(pixels, **extra)
    t = _threads(q, cfg)
    assert "4531" in t and "4752" not in t
    n = _near_page(p, q, t.index("4531"))
    assert (n == 0) if left == 0 else (n > left)


def test_soft_ramp_needs_the_fringe_flag(pixels):
    # It sizes `flat_page_fringe_exclude`'s band; alone it changes nothing.
    _p, off, _c = _stage2(pixels)
    _p, on, _c = _stage2(pixels, **SOFT)
    assert np.array_equal(off.labels, on.labels) and off.thread_indices == on.thread_indices


def test_the_ramp_dissolve_sends_olive_to_black_and_gold_to_yellow(pixels):
    p, off, cfg = _stage2(pixels)
    _p, on, _c = _stage2(pixels, **DISSOLVE)
    t_off, t_on = _threads(off, cfg), _threads(on, cfg)
    assert "6156" not in t_on and "0442" not in t_on
    # The olive pixels (the waves and anchor, thin BLACK strokes in the art)
    # join black, the nearer end of the chord, not the blue (as near in Lab).
    olive = off.labels == t_off.index("6156")
    assert (on.labels[olive] == t_on.index("0020")).mean() > 0.95
    gold = off.labels == t_off.index("0442")
    assert (on.labels[gold] == t_on.index("0713")).mean() > 0.95
    # Independent of the page fringe: the blue still takes it.
    assert "4752" in t_on


def test_all_three_sew_the_arts_four_inks(pixels):
    _p, q, cfg = _stage2(pixels, **FRINGE, **SOFT, **DISSOLVE)
    assert sorted(_threads(q, cfg)) == ["0020", "0713", "1521", "4531"]


def test_the_dissolve_reads_only_an_enlarged_raster():
    # A source at the grid has a one-pixel edge: the flag is inert there.
    big = np.full((400, 400, 3), (244, 241, 237), np.uint8)
    cv2.circle(big, (200, 200), 150, (20, 20, 20), -1)
    cv2.circle(big, (200, 200), 120, (40, 220, 250), -1)
    cv2.putText(big, "AB", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 3, (200, 120, 30), 6)
    base = dict(max_colors=6, forced_class="flat", target_width_mm=25.0)
    a = PipelineConfig(**base)
    b = PipelineConfig(**base, **DISSOLVE)
    pa = prep(big, a, design_class="flat")
    pb = prep(big, b, design_class="flat")
    assert pa.px_per_mm <= pa.input_px_per_mm + 1e-6
    qa, qb = quantize(pa, a), quantize(pb, b)
    assert np.array_equal(qa.labels, qb.labels) and qa.thread_indices == qb.thread_indices
