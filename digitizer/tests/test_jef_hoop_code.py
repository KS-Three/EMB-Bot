"""The hoop a JEF file DECLARES, which is not the same as the one it fits.

JEF's header carries a hoop code, and a Janome reads it before it reads a
stitch: a file claiming a hoop the design overflows is refused, or loaded and
run into the frame. EMB-Bot started offering JEF on 2026-09-07, so the header
is now part of what this product ships and nothing was checking it.

`pystitch.JefWriter.get_jef_hoop_size` picks the code from the design's own
bbox, correctly, until the last line:

    if width < 500  and height < 500:  return HOOP_50X50
    if width < 1260 and height < 1100: return HOOP_126X110
    if width < 1400 and height < 2000: return HOOP_140X200
    if width < 2000 and height < 2000: return HOOP_200X200
    return HOOP_110X110

The fallthrough for anything at or over 200 mm is **110x110 — the second
SMALLEST hoop it knows**, handed to the largest designs. Measured 2026-09-07
through the real /export route: a 199.2 mm design declares 200x200 and fits;
a 201.2 mm design declares 110x110 and does not.

Pinned rather than worked around, the same way `test_service.py` pins U01's
missing colour changes. Two things follow from it:

  - Reachable in the product, and NOT only where the app already warns. Four
    garments (full_back 304.8, jacket_back 304.8, blanket 254.0, tote 203.2
    mm) have placement boxes over 200 mm and auto-fit targets the box, so
    every design on them lands in the band — and those already cost a
    deliberate confirm to export. But the band is wider than the warning: the
    Studio's largest hoop is 200x200 mm and its 6x10 is 160x250 mm, so a
    140 x 200 mm design FITS the largest hoop and a 150 x 240 mm design FITS
    the 6x10, `hoopFitNote` is silent for both, and both are stamped 110x110.
    That is why the Studio's caveat is a persistent note beside the JEF
    button rather than a line inside the hoop-exceeds dialog — the dialog
    does not open for the cases that fit a hoop the customer owns.
  - If this test starts failing, pystitch fixed it. That is good news: drop
    the xfail-shaped assertion and the note in MASTER_SCOPE area 4 with it.
"""
from __future__ import annotations

import struct

import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from fastapi.testclient import TestClient  # noqa: E402

from digitizer_service.app import app  # noqa: E402

# JefWriter's own constants, by value. Named here rather than imported so this
# file states what it believes and fails loudly if the writer renumbers them.
HOOPS_MM = {0: (110, 110), 1: (50, 50), 2: (140, 200), 3: (126, 110), 4: (200, 200)}
HOOP_CODE_OFFSET = 32   # bytes: after the 4+4 header, the date, and the counts


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _bar_design(width_mm: float, height_mm: float = 12.0) -> dict:
    """A plain two-colour sewn rectangle of an exact size, in 0.1 mm units.

    Hand-built rather than digitized: the point is to control the WIDTH to the
    tenth of a millimetre across the 200 mm boundary, which a real pipeline run
    cannot promise and which is the whole subject here.
    """
    w = int(round(width_mm * 10))
    h = int(round(height_mm * 10))
    stitches = [{"x": 0, "y": 0, "type": "jump"}]
    for x in range(0, w + 1, 25):
        stitches.append({"x": x, "y": 0, "type": "stitch"})
    for x in range(w, -1, -25):
        stitches.append({"x": x, "y": -h, "type": "stitch"})
    stitches.append({"x": 0, "y": 0, "type": "end"})
    return {
        "stitches": stitches,
        "colors": [{"r": 20, "g": 20, "b": 20, "name": "Black"}],
        "widthMM": width_mm,
        "heightMM": height_mm,
    }


def _hoop_code(client, design: dict) -> int:
    r = client.post("/export", json={"design": design, "format": "jef"})
    assert r.status_code == 200, r.text
    (code,) = struct.unpack_from("<i", r.content, HOOP_CODE_OFFSET)
    return code


def _declared_hoop_fits(code: int, w: float, h: float) -> bool:
    hw, hh = HOOPS_MM[code]
    return (w <= hw and h <= hh) or (h <= hw and w <= hh)


@pytest.mark.parametrize("width_mm", [40.0, 100.0, 150.0, 199.0])
def test_jef_declares_a_hoop_the_design_actually_fits_below_200mm(client, width_mm):
    code = _hoop_code(client, _bar_design(width_mm))
    assert code in HOOPS_MM, f"unknown hoop code {code} — JefWriter renumbered its constants"
    assert _declared_hoop_fits(code, width_mm, 12.0), (
        f"{width_mm} mm design declares hoop {code} = {HOOPS_MM[code]} mm, which it does not fit"
    )


def test_at_200mm_the_writer_falls_through_to_the_SMALLEST_hoop_but_one(client):
    """The upstream defect, pinned. Delete this when pystitch fixes it."""
    below = _hoop_code(client, _bar_design(199.0))
    above = _hoop_code(client, _bar_design(201.0))
    assert below == 4, f"199 mm should declare 200x200 (code 4), got {below}"
    assert above == 0, (
        f"201 mm now declares hoop {above} instead of the 110x110 fallthrough — if pystitch "
        "fixed get_jef_hoop_size, drop this test and the MASTER_SCOPE area 4 note with it"
    )
    # And say plainly what that means, so the number above is not just a code.
    assert not _declared_hoop_fits(above, 201.0, 12.0)


def test_every_garment_over_200mm_lands_in_that_band(client):
    """Not a hypothetical band — four shipped garments live in it.

    full_back 304.8, jacket_back 304.8, blanket 254.0, tote 203.2 mm, and
    auto-fit targets the placement box. Sizes are hard-coded rather than read
    from the engine so this states what it believes; `src/garments.js` is the
    source and `test/digitize.test.js` guards the engine side.
    """
    for name, width_mm in [("tote", 203.2), ("blanket", 254.0), ("jacket_back", 304.8), ("full_back", 304.8)]:
        code = _hoop_code(client, _bar_design(width_mm))
        assert code == 0, f"{name}: expected the 110x110 fallthrough, got {code}"
        assert not _declared_hoop_fits(code, width_mm, 12.0), name


# The Studio's own hoop presets, from src/garments.js. Named here rather than
# parsed out of the JS so this file states what it believes; test/garments.test.js
# guards the engine side of the same table.
STUDIO_HOOPS_MM = [("4x4 in", 100, 100), ("5x7 in", 130, 180),
                   ("6x10 in", 160, 250), ("8x8 in", 200, 200)]


def _studio_hoop_takes(w: float, h: float, hw: float, hh: float) -> bool:
    """src/garments.js `hoopFit` != "exceeds" — orientation-aware, inclusive."""
    return (w <= hw and h <= hh) or (h <= hw and w <= hh)


@pytest.mark.parametrize(
    "w,h,hoop",
    [
        (140.0, 200.0, "8x8 in"),    # fits the LARGEST hoop the app offers
        (150.0, 240.0, "6x10 in"),
        (120.0, 200.0, "8x8 in"),
        (160.0, 250.0, "6x10 in"),
    ],
)
def test_a_design_that_fits_a_studio_hoop_can_still_be_stamped_110x110(client, w, h, hoop):
    """The case the hoop-exceeds dialog does not cover, which is the point.

    Every pair here fits a hoop the app sells the customer on — so the Studio
    says nothing about size — and every one is written with the 110x110 code.
    If this ever goes green because the Studio's hoop table shrank rather than
    because pystitch was fixed, the first assertion is what says so.
    """
    hw, hh = next((a, b) for lbl, a, b in STUDIO_HOOPS_MM if lbl == hoop)
    assert _studio_hoop_takes(w, h, hw, hh), (
        f"{w}x{h} mm no longer fits the {hoop} hoop — the Studio's hoop table moved, "
        "so this case stopped being the silent one it was written for"
    )
    code = _hoop_code(client, _bar_design(w, h))
    assert code == 0, f"{w}x{h} mm: expected the 110x110 fallthrough, got {code}"
    assert not _declared_hoop_fits(code, w, h)
