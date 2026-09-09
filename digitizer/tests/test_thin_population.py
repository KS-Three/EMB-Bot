"""The photo lane's thin population (`digitizer_core/thin_ink.py`, PR 3 of
the thin-stroke plan) — `cfg.keep_thin_strokes` on the gradient/photo lanes.

Four contracts. `find_thin_ink` reads strokes and refuses bands: on a panel
carrying six 0.6 x 3 mm bars it finds the six, with or without the one-ground
test; on a steep ramp posterised into thin, long bands it finds bands only
with the test OFF and NOTHING with it on, which is the discriminator that
keeps photographs empty. End to end, the bars a superpixel swallows today are
sewn in their own colour with the flag on, read by `tools/thin_strokes.py` on
the stitches. And where the population comes back empty, ON is byte-identical
to OFF on stage 2's own output — the invariant the photo goldens pin; the
photo CLASSES are byte-identical ON by construction, because the pipeline
asks for the population on the gradient class only.
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import segment
from digitizer_core.thin_ink import THIN_INK_MIN_PX, find_thin_ink, ground_share

from .conftest import TESTDATA
from .test_keep_thin_strokes import _strokes_on_a_panel

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "tools"))


def _foreground(p):
    valid = ~p.bg_mask
    if p.enclosed_mask is not None and p.enclosed_mask.any():
        valid = valid & ~p.enclosed_mask
    return valid


def test_six_bars_on_a_panel_are_the_thin_population_either_arm(tmp_path):
    art = tmp_path / "bars.png"
    _strokes_on_a_panel(art)
    cfg = PipelineConfig(target_width_mm=50.0, max_colors=6)
    p = prep(str(art), cfg)
    for ground_test in (False, True):
        thin = find_thin_ink(p, cfg, _foreground(p), ground_test=ground_test)
        assert thin is not None, ground_test
        assert thin.components == 6, (ground_test, thin.components)
        # 6 x 30 px bars at 10 px/mm: a 2.4-3 mm skeleton each
        assert 12.0 < thin.length_mm < 20.0, thin.length_mm
        assert len(thin.spools) == 1, "one dark colour"
        assert thin.mask.sum() == pytest.approx(6 * 6 * 30, rel=0.15)
        assert set(np.unique(thin.labels[thin.mask]).tolist()) == {0}
        assert (thin.labels[~thin.mask] == -1).all()


def _steep_ramp(path: Path) -> None:
    """Two flat colours joined by a 20 px ramp of five 4 px steps: the
    quantiser keeps the steps as their own labels (a 4 px band is half edge
    pixels, under the phantom dissolve's 0.9), so they arrive as thin, long
    components — the shape a posterised gradient leaves between two of its
    levels — with a different level on each side."""
    img = np.zeros((300, 600, 3), np.uint8)
    a, b = np.array((40, 60, 200), float), np.array((220, 200, 60), float)   # BGR
    img[:, :290] = a
    img[:, 310:] = b
    for i in range(5):
        t = (i + 1) / 6.0
        img[:, 290 + 4 * i:294 + 4 * i] = (a + t * (b - a)).astype(np.uint8)
    cv2.imwrite(str(path), img)


def test_a_posterised_ramps_bands_are_refused_by_the_one_ground_test(tmp_path):
    art = tmp_path / "ramp.png"
    _steep_ramp(art)
    cfg = PipelineConfig(target_width_mm=60.0, max_colors=6, bg_border_agreement_min=0.0,
                         bg_border_rival_min=0.0)
    p = prep(str(art), cfg)
    valid = _foreground(p)
    loose = find_thin_ink(p, cfg, valid, ground_test=False)
    assert loose is not None and loose.components >= 1, "the fixture makes no thin band; rebuild it"
    assert find_thin_ink(p, cfg, valid) is None, "a band between two levels read as a stroke"


def test_ground_share_reads_one_ground_as_one_and_a_band_as_a_half():
    labels = np.zeros((40, 40), np.int32)
    comp = np.zeros((4, 20), bool)
    comp[:] = True
    # a stroke (label 1) laid on label 0 everywhere: the ring is all 0
    labels[18:22, 10:30] = 1
    assert ground_share(labels, comp, 18, 10) == 1.0
    # the same stroke as a band between label 0 above and label 2 below
    labels[22:, :] = 2
    share = ground_share(labels, comp, 18, 10)
    assert 0.4 < share < 0.65, share


def test_the_pixel_floor_is_three_pixels_the_same_class_as_the_curve_gate():
    assert THIN_INK_MIN_PX == 3.0


def test_on_the_photo_lane_the_bars_a_superpixel_swallows_are_sewn_with_the_flag_on(tmp_path):
    import thin_strokes as ts

    art = tmp_path / "bars.png"
    _strokes_on_a_panel(art)
    off = ts.run(art, 50.0, "left_chest", forced_class="gradient")
    on = ts.run(art, 50.0, "left_chest", forced_class="gradient", flag="keep_thin_strokes")
    assert off["thin_strokes"] == 6 and on["thin_strokes"] == 6, (off["thin_strokes"], on["thin_strokes"])
    assert off["recall"] < 0.2, off["recall"]
    assert on["recall"] >= 0.8, on["recall"]
    assert on["regions"] >= off["regions"] + 5, (off["regions"], on["regions"])


def _quant_digest(q) -> tuple:
    return (hashlib.sha256(np.ascontiguousarray(q.labels).tobytes()).hexdigest(),
            list(q.thread_indices), [tuple(map(float, c)) for c in q.cluster_rgb], q.warnings)


@pytest.mark.parametrize("fixture", ["photo/fur_ramp.png", "photo/photo_subject_stub.png",
                                     "photo/gradient_ramp_linear.png"])
def test_where_nothing_is_thin_the_flag_on_is_byte_identical_to_off(fixture):
    """Photographs and smooth ramps carry no strokes; the population must
    come back EMPTY there (measured 2026-09-08 on every committed photo
    fixture, scope-history 09-08) and stage 2's output must then not move by
    a label — the same invariant the photo golden pins for OFF."""
    path = TESTDATA / fixture
    off_cfg = PipelineConfig(target_width_mm=80.0)
    on_cfg = PipelineConfig(target_width_mm=80.0, keep_thin_strokes=True)
    p = prep(str(path), off_cfg)
    assert find_thin_ink(p, on_cfg, _foreground(p)) is None, "the population is not empty here"
    assert _quant_digest(segment(p, off_cfg)) == _quant_digest(
        segment(prep(str(path), on_cfg), on_cfg, thin_population=True))


def test_the_population_is_gated_to_the_gradient_class_at_the_call_site():
    """Measured 2026-09-08: on a photograph the population is NOT empty at
    any ring share that keeps Fremont's lettering whole (the owl keeps 199 mm
    of "strokes" at 0.75), so the pipeline asks for it only on the gradient
    class and the photo classes are byte-identical ON by construction."""
    import inspect

    from digitizer_core import pipeline

    src = inspect.getsource(pipeline.build_generation)
    assert 'thin_population=bool(cfg.keep_thin_strokes and classification.class_ == "gradient")' in src
    sig = inspect.signature(segment)
    assert sig.parameters["thin_population"].default is False
