"""The decode seam's working-resolution ceiling (`_decode` + DECODE_MAX_SIDE_PX).

Why this seam is guarded: MAX_PIXELS rejects absurdities but admits images the
pipeline cannot afford — a 7.4 MP phone photo OOM-killed the service at
13.9 GB RSS in a 16 GB container (2026-08-23). `_decode` now downscales
anything whose long side exceeds DECODE_MAX_SIDE_PX (INTER_AREA, aspect
preserved) before the pixels reach the generation cache or the pipeline. The
full evidence and the silent-normalize decision live on the constant's comment
in `digitizer_service/app.py`.

Two contracts pinned here, both load-bearing for the golden suite:

1. Anything at or under the ceiling passes through BYTE-IDENTICAL — the
   normalize must be invisible to every committed fixture, or goldens shift.
2. Anything over it lands EXACTLY on the ceiling, long side first, short side
   rounded (floor 1 px), dtype and channel count untouched.

Plus the inventory that made 2800 the number: no committed raster under
testdata/ may exceed the ceiling. A future fixture that does fails loud here
instead of as a baffling golden mismatch four stages downstream.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

import cv2
import numpy as np
import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from fastapi import HTTPException  # noqa: E402

from digitizer_service.app import (  # noqa: E402
    DECODE_MAX_SIDE_PX,
    MAX_PIXELS,
    _decode,
)

from .conftest import TESTDATA  # noqa: E402


def _png(arr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", arr)
    assert ok
    return buf.tobytes()


# --- contract 1: at-or-under the ceiling is byte-identical -----------------

def test_under_ceiling_is_byte_identical():
    """PNG is lossless, and _decode must add nothing to that: same shape,
    same dtype, same bytes. This is the whole committed corpus's proxy."""
    rng = np.random.default_rng(7)
    arr = rng.integers(0, 256, size=(200, 300, 3), dtype=np.uint8)
    out = _decode(_png(arr))
    assert out.shape == arr.shape
    assert out.dtype == arr.dtype
    assert out.tobytes() == arr.tobytes()


def test_exactly_at_ceiling_is_untouched():
    """The trigger is strictly 'exceeds' — a fixture sitting exactly on the
    ceiling must not be resampled (off-by-one here WOULD move goldens)."""
    rng = np.random.default_rng(11)
    arr = rng.integers(0, 256, size=(DECODE_MAX_SIDE_PX, 40, 3), dtype=np.uint8)
    out = _decode(_png(arr))
    assert out.shape == arr.shape
    assert out.tobytes() == arr.tobytes()


# --- contract 2: over the ceiling lands exactly on it ----------------------

def test_oversized_lands_exactly_on_the_ceiling():
    """Landscape, with dims chosen so the short side actually exercises
    rounding (not an integer multiple of the scale)."""
    long_px, short_px = 5000, 333
    out = _decode(_png(np.zeros((short_px, long_px, 3), np.uint8)))
    expect_short = max(1, round(short_px * DECODE_MAX_SIDE_PX / long_px))
    assert out.shape == (expect_short, DECODE_MAX_SIDE_PX, 3)
    assert out.dtype == np.uint8


def test_oversized_portrait_preserves_orientation_and_alpha():
    """The same contract with h/w swapped — cv2.resize takes (width, height),
    the classic transposition bug — and with an alpha channel riding along:
    IMREAD_UNCHANGED keeps 4 channels, so the resize must too."""
    long_px, short_px = 5000, 333
    out = _decode(_png(np.zeros((long_px, short_px, 4), np.uint8)))
    expect_short = max(1, round(short_px * DECODE_MAX_SIDE_PX / long_px))
    assert out.shape == (DECODE_MAX_SIDE_PX, expect_short, 4)


# --- the 413 path is unchanged ---------------------------------------------

def test_max_pixels_413_still_fires_before_any_resize():
    """Over MAX_PIXELS still 413s at submit. The fixture's long side is also
    far over the decode ceiling, so this doubles as an ordering check: the
    reject runs first — the normalize never quietly swallows an image the
    contract says to refuse."""
    w, h = 8000, 5001                      # 40,008,000 px, just over the limit
    assert w * h > MAX_PIXELS
    assert max(w, h) > DECODE_MAX_SIDE_PX
    with pytest.raises(HTTPException) as exc:
        _decode(_png(np.zeros((h, w), np.uint8)))   # gray keeps the array cheap
    assert exc.value.status_code == 413
    assert "megapixels" in exc.value.detail


# --- the inventory the ceiling was chosen against --------------------------

_RASTER_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp", ".gif"}


def test_ceiling_clears_every_committed_fixture():
    """DECODE_MAX_SIDE_PX exists to normalize real uploads, never the repo's
    own corpus: a committed fixture above the ceiling would be resized at this
    seam and every golden downstream would shift. 2800 was chosen just above
    the largest committed raster (photo/logo_gaulke_roofing.png, 1284x2778,
    measured 2026-08-23) — this keeps that clearance from rotting.

    COMMITTED means `git ls-files`, deliberately: the gitignored drop zones
    (testdata/photo/acceptance/, testdata/inbox/) hold real uncommitted phone
    photos that legitimately exceed the ceiling — normalizing those is the
    feature. Header-only PIL reads (Pillow arrives via pytesseract's own
    deps — see pyproject.toml) keep this at milliseconds, not full decodes.
    """
    pil_image = pytest.importorskip(
        "PIL.Image", reason="Pillow (pytesseract's dependency) not installed")
    digitizer_root = TESTDATA.parent
    proc = subprocess.run(
        ["git", "ls-files", "--", "testdata/"],
        cwd=digitizer_root, capture_output=True, text=True,
    )
    if proc.returncode != 0:
        pytest.skip("not a git checkout — committed-fixture inventory unavailable")
    committed = [
        digitizer_root / line
        for line in proc.stdout.splitlines()
        if Path(line).suffix.lower() in _RASTER_EXTS
    ]
    assert committed, "no committed rasters under testdata/ — inventory broke"

    over = {}
    for p in committed:
        with pil_image.open(p) as im:
            side = max(im.size)
        if side > DECODE_MAX_SIDE_PX:
            over[p.name] = side
    assert not over, (
        f"committed fixture(s) exceed DECODE_MAX_SIDE_PX={DECODE_MAX_SIDE_PX}: "
        f"{over} — _decode would resize them and shift every downstream golden. "
        "Either shrink the fixture or raise the ceiling (with fresh memory "
        "evidence) in digitizer_service/app.py."
    )
