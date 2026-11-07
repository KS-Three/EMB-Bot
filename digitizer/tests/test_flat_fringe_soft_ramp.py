"""The flat lane's soft-edge cure (built OFF 2026-11-06): `logo_bridge_bar.jpg`
routed flat, as `stage0_scale_relative_grad` routes it.

Two mechanisms, one cause: the 400 px JPEG is enlarged x3.25 to the 8 px/mm
working grid at 113.5 mm, and its edges are about 3 SOURCE pixels soft.

1. `flat_page_fringe_soft_ramp`: the spokes' black-to-page ramp is ~9 working
   px deep; `flat_page_fringe_exclude`'s band (OFF) stops at 5 (one source px). The
   neutral greys left outside it are nearer the blue lettering's centre than
   black or the page, drag it to Vintage Blue 4752, and the band copies it.
2. `flat_ramp_blend_dissolve`: the yellow-to-black and yellow-to-blue ramps
   inside the disc form olive 6156 and Tarnished Gold 0442 clusters, which the
   phantom dissolve keeps because only the one pixel at a label change counts
   as edge.

The cure is the two flags (both read an enlarged raster only); the existing
`flat_page_fringe_exclude` is not needed and is left out of it: at full
resolution it moves the screenshot fixture's lettering.

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

from .conftest import FLAT_GOLDEN_MD5, TESTDATA

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


def test_soft_ramp_alone_takes_the_page_fringe_out(pixels):
    # On an enlarged raster it runs the page-fringe exclusion by itself (no
    # outline-inner pass): the blue is Caribbean and none of it is at the page.
    p, q, cfg = _stage2(pixels, **SOFT)
    t = _threads(q, cfg)
    assert "4531" in t and "4752" not in t
    assert _near_page(p, q, t.index("4531")) == 0
    assert q.page_fringe is not None and q.page_fringe.any()


def test_the_ramp_dissolve_sends_olive_to_black_and_gold_to_yellow(pixels):
    p, off, cfg = _stage2(pixels)
    _p, on, _c = _stage2(pixels, **DISSOLVE)
    t_off, t_on = _threads(off, cfg), _threads(on, cfg)
    assert "6156" not in t_on and "0442" not in t_on
    # The olive pixels (the waves and anchor, thin BLACK strokes in the art)
    # join black, the nearer end of the chord, not the blue (nearer in Lab).
    olive = off.labels == t_off.index("6156")
    assert (on.labels[olive] == t_on.index("0020")).mean() > 0.95
    gold = off.labels == t_off.index("0442")
    assert (on.labels[gold] == t_on.index("0713")).mean() > 0.95
    # Independent of the page fringe: the blue still takes it.
    assert "4752" in t_on


@pytest.mark.parametrize("extra", [dict(SOFT, **DISSOLVE), dict(FRINGE, **SOFT, **DISSOLVE)],
                         ids=["cure", "cure+fringe_exclude"])
def test_the_cure_sews_the_arts_four_inks(pixels, extra):
    _p, q, cfg = _stage2(pixels, **extra)
    assert sorted(_threads(q, cfg)) == ["0020", "0713", "1521", "4531"]


def test_the_cure_reads_only_an_enlarged_raster():
    # A source above the grid has a one-pixel edge: both flags are inert there.
    big = np.full((400, 400, 3), (244, 241, 237), np.uint8)
    cv2.circle(big, (200, 200), 150, (20, 20, 20), -1)
    cv2.circle(big, (200, 200), 120, (40, 220, 250), -1)
    cv2.putText(big, "AB", (120, 240), cv2.FONT_HERSHEY_SIMPLEX, 3, (200, 120, 30), 6)
    base = dict(max_colors=6, forced_class="flat", target_width_mm=25.0)
    a = PipelineConfig(**base)
    b = PipelineConfig(**base, **SOFT, **DISSOLVE)
    pa = prep(big, a, design_class="flat")
    pb = prep(big, b, design_class="flat")
    assert pa.px_per_mm <= pa.input_px_per_mm + 1e-6
    qa, qb = quantize(pa, a), quantize(pb, b)
    assert np.array_equal(qa.labels, qb.labels) and qa.thread_indices == qb.thread_indices
    assert qb.page_fringe is None


def _golden_md5(fixture: str, **kw) -> str:
    import hashlib
    from digitizer_core import digitize
    _result, plan = digitize(TESTDATA / fixture, PipelineConfig(
        target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False, **kw))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(FLAT_GOLDEN_MD5))
def test_the_cure_moves_no_flat_golden(fixture):
    # The three flat-lane goldens are not enlarged at 80 mm (or are alpha
    # cut-outs): the cure ON is the golden, byte for byte.
    assert _golden_md5(fixture, **SOFT, **DISSOLVE) == FLAT_GOLDEN_MD5[fixture]
