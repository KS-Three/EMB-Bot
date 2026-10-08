"""Robustness fuzz: `digitize()` on synthetic EDGE images.

The contract asserted here is deliberately narrow and makes NO quality claim:
for each odd input the pipeline must either raise a CLEAN error (a
`ValueError` -- the type the service maps to a 4xx) or return a structurally
valid plan (finite coordinates, a computable `stats`). A `cv2.error`,
`IndexError`, hang or non-finite point is a crash.

Crashes found are `xfail(strict=True)` with the cause named, so a fix flips the
test to XPASS-fail and someone deletes the marker. Listed in the PR body.

Inputs are built in memory and handed over as encoded bytes (the shape the
service passes), so no fixture files are added to the public repo.
"""
import io
import math
import os

import cv2
import numpy as np
import pytest
from PIL import Image

from digitizer_core import digitize


def _enc(im: Image.Image, fmt: str) -> bytes:
    buf = io.BytesIO()
    im.save(buf, fmt)
    return buf.getvalue()


def _one_by_one():
    return _enc(Image.new("RGB", (1, 1), (10, 20, 30)), "PNG")


def _all_transparent():
    return _enc(Image.new("RGBA", (120, 90), (0, 0, 0, 0)), "PNG")


def _all_one_colour():
    return _enc(Image.new("RGB", (160, 120), (200, 30, 30)), "PNG")


def _huge_thin_line():
    a = np.full((200, 6000, 3), 255, np.uint8)
    a[100:102, :] = 0
    return _enc(Image.fromarray(a), "PNG")


def _palette_png():
    arr = np.zeros((120, 160), np.uint8)
    arr[30:90, 40:120] = 1
    arr[50:70, 60:100] = 2
    im = Image.fromarray(arr, "P")
    im.putpalette([255, 255, 255, 0, 0, 0, 200, 0, 0] + [0] * 759)
    return _enc(im, "PNG")


def _cmyk_jpeg():
    a = np.full((120, 160, 3), 255, np.uint8)
    cv2.rectangle(a, (30, 30), (130, 90), (0, 0, 0), -1)
    return _enc(Image.fromarray(a).convert("CMYK"), "JPEG")


def _png16_gray():
    a = np.full((120, 160), 65535, np.uint16)
    a[30:90, 40:120] = 0
    return cv2.imencode(".png", a)[1].tobytes()


def _png16_rgb():
    a = np.full((120, 160, 3), 65535, np.uint16)
    a[30:90, 40:120] = (0, 0, 40000)
    return cv2.imencode(".png", a)[1].tobytes()


def _8000px():
    a = np.full((8000, 8000, 3), 255, np.uint8)
    cv2.circle(a, (4000, 4000), 2500, (0, 0, 200), -1)
    return _enc(Image.fromarray(a), "PNG")


def _8000_wide_strip():
    a = np.full((400, 8000, 3), 255, np.uint8)
    cv2.rectangle(a, (500, 100), (7500, 300), (0, 0, 200), -1)
    return _enc(Image.fromarray(a), "PNG")


# 16-bit PNG decodes (IMREAD_UNCHANGED) to uint16, which `_load` passes on
# without a depth conversion; the bilateral filter then rejects it. Found
# 2026-10-08; gray and RGB both hit it.
_16BIT = ("cv2.error from a 16-bit PNG: `_load` keeps uint16 and "
          "cv2.bilateralFilter rejects it (-210 Unsupported format)")

CASES = [
    pytest.param(_one_by_one, id="1x1"),
    pytest.param(_all_transparent, id="all-transparent"),
    pytest.param(_all_one_colour, id="all-one-colour"),
    pytest.param(_huge_thin_line, id="huge-thin-line"),
    pytest.param(_palette_png, id="palette-png"),
    pytest.param(_cmyk_jpeg, id="cmyk-jpeg"),
    pytest.param(_png16_gray, id="png16-gray",
                 marks=pytest.mark.xfail(reason=_16BIT, raises=cv2.error, strict=True)),
    pytest.param(_png16_rgb, id="png16-rgb",
                 marks=pytest.mark.xfail(reason=_16BIT, raises=cv2.error, strict=True)),
    pytest.param(_8000_wide_strip, id="8000px-wide-strip"),
    # Completes, but measured 485 s / ~2 GB RSS on 2026-10-08 (4-core cloud
    # container): far too slow for the CI shards, so opt-in.
    pytest.param(_8000px, id="8000px-square", marks=pytest.mark.skipif(
        not os.environ.get("EMB_FUZZ_HUGE"),
        reason="~8 min, ~2 GB; set EMB_FUZZ_HUGE=1 to run")),
]


def _assert_valid_plan(result, plan):
    assert result is not None and plan is not None
    for _block, run in plan.iter_runs():
        for x, y in run.points:
            assert math.isfinite(x) and math.isfinite(y)
    stats = plan.stats
    assert stats.stitch_count >= 0
    assert all(math.isfinite(v) for v in stats.bbox_mm)
    assert all(math.isfinite(v) for v in stats.size_mm)


@pytest.mark.parametrize("make", CASES)
def test_edge_image_clean_error_or_valid_plan(make):
    data = make()
    try:
        result, plan = digitize(data)
    except ValueError:
        return  # a clean, caller-facing refusal
    _assert_valid_plan(result, plan)
