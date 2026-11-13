"""`cfg.photo_enclosed_rim` (2026-11-06, built OFF).

MFab's hat logo classes photo_scene at every width. Its white keyline is stage
1's ENCLOSED ground (bg-coloured, not border-connected), quantised as its own
population; the keyline's edge pixels miss that test and stay in the main
population, where the merge gathers them into one white label of 275 pieces.
The min-detail floor (`resolve_small_regions`, 1.5 mm) sees only the main
population, so every sub-floor piece is absorbed into its one neighbour, the
black, and the keyline thins by a pixel. SEEDS and the hierarchical merge are
byte-identical at 60 and 100.8 mm (the same 418 px raster); the floor is in mm,
so it is wider in pixels at 60 mm and the keyline breaks there (3 white fields
instead of 1, 0 small-line riders). ON, a piece of the enclosed ground's own
colour touching it joins its population before the floor.
`docs/photo-enclosed-rim-2026-11-06.md`.
"""
from __future__ import annotations

import hashlib
import json

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig, silhouette_underfill as su
from digitizer_core import stage2_photo_segment as s2
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.threads import rgb_to_lab

from .conftest import TESTDATA, frozen_cfg


def _lab(rgb):
    h, w = rgb.shape[:2]
    return rgb_to_lab(rgb.reshape(-1, 3).astype(np.float64)).reshape(h, w, 3)


def _keyline():
    """A black ring (label 1) round a white enclosed core; a white sliver
    (label 2) on the core's edge, outside the enclosed mask; a white speck
    (label 2) out in the black, touching no enclosed pixel."""
    rgb = np.zeros((40, 40, 3), np.uint8)
    rgb[10:30, 10:30] = 255
    rgb[5:7, 5:7] = 255
    enclosed = np.zeros((40, 40), bool)
    enclosed[11:30, 10:30] = True          # row 10 is the missed rim
    labels = np.ones((40, 40), np.int64)
    labels[10, 10:30] = 2
    labels[5:7, 5:7] = 2
    valid = ~enclosed
    return labels, valid, enclosed, _lab(rgb)


def test_rim_takes_the_ground_coloured_sliver_only():
    labels, valid, enclosed, lab = _keyline()
    rim = s2.enclosed_rim(labels, valid, enclosed, lab, 6.0)
    assert rim is not None
    assert rim[10, 10:30].all()            # the sliver on the core's edge
    assert not rim[5:7, 5:7].any()         # same colour, touches no ground
    assert not (rim & (labels == 1)).any()  # the black ring never


def test_rim_leaves_a_piece_big_enough_to_stand():
    # the 20 px sliver is over a 10 px floor: the floor would keep it, so it stays
    labels, valid, enclosed, lab = _keyline()
    assert s2.enclosed_rim(labels, valid, enclosed, lab, 6.0, max_px=10) is None
    assert s2.enclosed_rim(labels, valid, enclosed, lab, 6.0, max_px=21) is not None


def test_rim_is_none_without_a_ground_coloured_piece():
    labels, valid, enclosed, lab = _keyline()
    labels[10, 10:30] = 1
    lab[10, 10:30] = lab[0, 0]             # the edge row is black now
    assert s2.enclosed_rim(labels, valid, enclosed, lab, 6.0) is None


def test_the_flag_is_off_by_default():
    assert PipelineConfig().photo_enclosed_rim is False


# --- MFab hat, the Studio's route (photo_scene) ------------------------------------

#: photo_prep=False pins the lane these numbers were measured on: CI has no rembg
#: venv, so its cutout fails and prep is skipped with it. A machine WITH the venv
#: runs the cutout instead and gets different numbers (tests/test_mfab_cutout_lane.py).
def _cfg(width_mm, on):
    return frozen_cfg(target_width_mm=width_mm, max_colors=6, satin=True, detail_layer=False,
                      edge_cap="none", sew_enclosed_white=True, sew_enclosed_rgb=(255, 255, 255),
                      faces_route_flat=True, garment_id="hat_front",
                      garment_rgb=(235, 232, 223), photo_enclosed_rim=on, photo_prep=False)


def _mfab(width_mm, on):
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
    cfg = _cfg(width_mm, on)
    seen = {}
    real = su.apply_cfg

    def probe(regions, unsewn, cfg_, outlines, pinned=()):
        seen["riders"] = su.find_riders(regions, unsewn, outlines)
        seen["fields"] = len(su._fields(regions))
        return real(regions, unsewn, cfg_, outlines, pinned)

    su.apply_cfg = probe
    try:
        plan = plan_stitches(finish_generation(build_generation(pix, cfg), cfg), cfg)
    finally:
        su.apply_cfg = real
    design = plan_to_design(plan, name="t")
    return design, seen


#: md5 of the OFF design at 60 mm on the frozen 2026-10-27 engine: the flag OFF
#: runs none of the new code (`enclosed_rim` is called only with it ON).
MFAB_60_OFF_MD5 = "2fabb15a023f074f2eb1d46125f01ad7"


def test_off_never_reads_the_rim_and_pins_the_design(monkeypatch):
    def boom(*a, **kw):
        raise AssertionError("enclosed_rim read with the flag OFF")

    monkeypatch.setattr(s2, "enclosed_rim", boom)
    design, seen = _mfab(60.0, False)
    assert seen["riders"] == [] and seen["fields"] == 3
    digest = hashlib.md5(json.dumps(design, sort_keys=True).encode()).hexdigest()
    assert digest == MFAB_60_OFF_MD5


@pytest.mark.parametrize("width", [60.0, 100.8, 113.5])
def test_mfab_keyline_holds_and_the_small_line_rides_on(width):
    """ON: one white field (the keyline whole) and every small-line letter that
    rides OFF still rides, with more at 60 mm (OFF: 3 broken fields, 0 riders)."""
    _off_design, off = _mfab(width, False)
    design, on = _mfab(width, True)
    assert [c["name"] for c in design["colors"]] == ["0020 Black", "0015 White", "0020 Black"]
    assert on["fields"] == 1
    assert len(on["riders"]) >= 12
    assert len(on["riders"]) >= len(off["riders"])
    if width == 60.0:
        assert off["riders"] == [] and off["fields"] == 3


# --- a real photograph: no enclosed ground, nothing moves ----------------------------

class _Stop(Exception):
    pass


def _stage2(pix, cfg, monkeypatch):
    got = {}

    def capture(p, cfg_, kept, *a, **kw):
        got["enc"] = None if p.enclosed_mask is None else p.enclosed_mask.copy()
        got["kept"] = hashlib.md5(b"".join(
            np.ascontiguousarray(m.crop).tobytes() + repr(m.origin).encode() for m in kept)).hexdigest()
        raise _Stop

    monkeypatch.setattr(s2, "kept_masks_to_quant", capture)
    with pytest.raises(_Stop):
        build_generation(pix, cfg)
    return got


def test_owl_photograph_stage2_is_unchanged_on(monkeypatch):
    """owl_kent.jpg on the Studio's 80 mm request: the regions handed to the
    palette are the same OFF and ON."""
    pix = cv2.imread(str(TESTDATA / "photo" / "owl_kent.jpg"), cv2.IMREAD_UNCHANGED)
    off = _stage2(pix, frozen_cfg(target_width_mm=80.0, garment_id="left_chest"), monkeypatch)
    on = _stage2(pix, frozen_cfg(target_width_mm=80.0, garment_id="left_chest",
                                 photo_enclosed_rim=True), monkeypatch)
    assert on["kept"] == off["kept"]
    assert (on["enc"] is None) == (off["enc"] is None)
    if on["enc"] is not None:
        assert np.array_equal(on["enc"], off["enc"])
