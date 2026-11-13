"""MFab hat on the CUTOUT lane: the one a deployed service runs.

`photo_prep_background_removal` is a shipped default and its rembg venv is a
required deploy step (`rembg_isolated/README.md`), but CI never builds that venv.
So on CI the cutout fails, prep is skipped with it, and every MFab test pins the
numbers of that fallback lane (`photo_prep=False` in those files makes that
explicit, so they agree on any machine). This file holds the same claims on the
lane production takes, and skips where the venv is missing.

Measured 2026-11-13 on 336e2eb3 (no cutout vs cutout; fields = white fields,
riders = small-line letters riding on the black):

    width  rim  no cutout          cutout
    60     OFF  3 fields, 0 riders  2 fields, 6 riders
    60     ON   1 field, 12 riders  2 fields, 10 riders
    100.8  OFF  1, 10               1, 12
    100.8  ON   1, 13               1, 15
    113.5  OFF  1, 12               1, 12
    113.5  ON   1, 12               1, 11

So with the cutout the shipped default is already better at 60 mm (the small
line sews black over white, which the no-cutout lane's KNOWN_WRONG_ORDER says
it does not), but `photo_enclosed_rim` does NOT deliver its claim there: the
keyline stays in two fields at 60 mm and loses a rider at 113.5 mm. The rim was
measured on the no-cutout lane only (docs/photo-enclosed-rim-2026-11-06.md).
The two strict xfails below are that gap; when one passes, its mark must go.
"""
from __future__ import annotations

import cv2
import pytest

from digitizer_core import silhouette_underfill as su
from digitizer_core.adapter import plan_to_design
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
from digitizer_core.stage1_photo_prep import background_removal_unavailable_reason

from .conftest import TESTDATA, frozen_cfg

pytestmark = pytest.mark.skipif(
    background_removal_unavailable_reason() is not None,
    reason="isolated rembg venv not built in this environment — see digitizer/rembg_isolated/README.md")

BLACK_WHITE_BLACK = ["0020 Black", "0015 White", "0020 Black"]


def _mfab(width_mm, rim):
    cfg = frozen_cfg(target_width_mm=width_mm, max_colors=6, satin=True, detail_layer=False,
                     edge_cap="none", sew_enclosed_white=True, sew_enclosed_rgb=(255, 255, 255),
                     faces_route_flat=True, garment_id="hat_front",
                     garment_rgb=(235, 232, 223), photo_enclosed_rim=rim)
    pix = cv2.imread(str(TESTDATA / "art" / "logo_mfab_hat.png"), cv2.IMREAD_UNCHANGED)
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
    return [c["name"] for c in plan_to_design(plan, name="t")["colors"]], seen


@pytest.mark.parametrize("width", [60.0, 100.8, 113.5])
def test_default_sews_the_keyline_on_the_black_with_the_cutout(width):
    # rim OFF (the shipped default): black, white, black at every width, 60 mm included
    blocks, _seen = _mfab(width, False)
    assert blocks == BLACK_WHITE_BLACK


_RIM_GAP = pytest.mark.xfail(strict=True, reason="photo_enclosed_rim not yet measured or tuned on the cutout lane")


@pytest.mark.parametrize("width", [pytest.param(60.0, marks=_RIM_GAP), 100.8,
                                   pytest.param(113.5, marks=_RIM_GAP)])
def test_rim_holds_the_keyline_and_keeps_every_rider_with_the_cutout(width):
    _blocks_off, off = _mfab(width, False)
    blocks, on = _mfab(width, True)
    assert blocks == BLACK_WHITE_BLACK
    assert on["fields"] == 1
    assert len(on["riders"]) >= len(off["riders"])
