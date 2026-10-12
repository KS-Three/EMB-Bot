"""tools/counter_slots.py reads a known counter and known slots back.

Two synthetic letters with geometry fixed in mm: a ring (an O, one counter of
pi * 1.2^2 mm^2) and an E (two slots exactly 0.8 mm wide, 3 mm deep). Each
is read three ways: the artwork mask alone, the stitched ribbons alone, and
end to end through `measure` (an anti-aliased RGBA file on disk, a Design
dict of satin crosses and fill rows, registration and all). The task's bar:
within 5% on area and 0.05 mm on width.
"""
from __future__ import annotations

import math

import cv2
import numpy as np
import pytest
from PIL import Image

from tools import counter_slots as cs

PPM = cs.PX_PER_MM
RING_C, R_OUT, R_IN = (3.0, 2.5), 2.5, 1.2
COUNTER_MM2 = math.pi * R_IN ** 2
SLOT_W, SLOT_DEPTH = 0.8, 3.0
# E: stem x 7..8, three arms x 7..11, 1 mm tall, 0.8 mm apart; y DOWN, mm.
E_RECTS = [(7.0, 0.0, 8.0, 4.6), (7.0, 0.0, 11.0, 1.0),
           (7.0, 1.8, 11.0, 2.8), (7.0, 3.6, 11.0, 4.6)]
HALF = cs.THREAD_MM / 2


def _art(ppm: float) -> np.ndarray:
    """Both letters as a bool mask, mm (0, 0) at pixel (0, 0)."""
    m = np.zeros((int(6 * ppm), int(12 * ppm)), np.uint8)
    cv2.circle(m, (int(round(RING_C[0] * ppm)), int(round(RING_C[1] * ppm))),
               int(round(R_OUT * ppm)), 1, -1)
    cv2.circle(m, (int(round(RING_C[0] * ppm)), int(round(RING_C[1] * ppm))),
               int(round(R_IN * ppm)), 0, -1)
    for x0, y0, x1, y1 in E_RECTS:
        m[int(round(y0 * ppm)):int(round(y1 * ppm)), int(round(x0 * ppm)):int(round(x1 * ppm))] = 1
    return m.astype(bool)


def _split(mask: np.ndarray, ppm: float):
    cut = int(6.0 * ppm)
    return mask[:, :cut], mask[:, cut:]


def _stitches() -> tuple[list[dict], list[dict]]:
    """Satin crosses round the ring and fill rows in each E rectangle, every
    ribbon's EDGE (centre +- half a thread) on the drawn geometry."""
    pts: list[tuple] = []
    runs = []

    def emit(seq, shape):
        if pts:
            pts.append(("jump", seq[0]))
        i0 = len(pts)
        pts.extend(("stitch", p) for p in seq)
        runs.append({"i0": i0, "i1": len(pts) - 1, "kind": "satin", "shape": shape,
                     "role": "", "block": 0})

    ring = []
    r_a, r_b = R_IN + HALF, R_OUT - HALF
    n = int(2 * math.pi * (r_a + r_b) / 2 / 0.15)
    for k in range(n + 1):
        t = 2 * math.pi * k / n
        r = r_a if k % 2 == 0 else r_b
        ring.append((RING_C[0] + r * math.cos(t), RING_C[1] + r * math.sin(t)))
    emit(ring, "ring")
    for j, (x0, y0, x1, y1) in enumerate(E_RECTS):
        rows = []
        y = y0 + HALF
        flip = False
        while y <= y1 - HALF + 1e-9:
            a, b = (x0 + HALF, y), (x1 - HALF, y)
            rows += [b, a] if flip else [a, b]
            flip = not flip
            y += 0.15
        emit(rows, "E")
    st = [{"type": k, "x": p[0] * 10.0, "y": -p[1] * 10.0} for k, p in pts]
    return st, runs


def _design() -> dict:
    st, runs = _stitches()
    return {"stitches": st, "colors": [{"r": 0, "g": 0, "b": 0}], "runs": runs,
            "widthMM": 11.0 - 0.5}


def _check_ring(counters):
    assert len(counters) == 1
    assert counters[0]["area_mm2"] == pytest.approx(COUNTER_MM2, rel=0.05)


def _check_e(slots, key="width_mm"):
    assert len(slots) == 2
    for s in slots:
        assert abs(s[key] - SLOT_W) <= 0.05, s[key]


def test_artwork_ring_and_e_read_back():
    ring, e = _split(_art(PPM), PPM)
    r = cs.read_art(ring, PPM)
    _check_ring(r.counters)
    assert r.slots == []
    a = cs.read_art(e, PPM)
    assert a.counters == []
    _check_e(a.slots)
    for s in a.slots:
        assert s["depth_mm"] == pytest.approx(SLOT_DEPTH, abs=0.1)


def test_stitched_ring_and_e_read_back():
    design = _design()
    masks, tag = cs.thread_rasters(design, {"ring", "E"}, PPM)
    (h, w), to_px = cs._frame(design["stitches"], PPM, cs.PAD_MM)
    sewn = masks[(0, 0, 0)]
    # place the art on the stitched frame: `_frame` puts the stitches'
    # min x and max design-y (min y, mm down) at PAD_MM.
    x0 = min(s["x"] for s in design["stitches"]) / 10.0
    top = -max(s["y"] for s in design["stitches"]) / 10.0
    art = np.zeros_like(sewn)
    src = _art(PPM)
    ox = int(round((cs.PAD_MM - x0) * PPM))
    oy = int(round((cs.PAD_MM - top) * PPM))
    hh, ww = min(src.shape[0], h - oy), min(src.shape[1], w - ox)
    art[oy:oy + hh, ox:ox + ww] = src[:hh, :ww]
    cut = ox + int(6.0 * PPM)
    for part, check in ((slice(0, cut), "ring"), (slice(cut, w), "e")):
        a = cs.read_art(art[:, part], PPM)
        got = cs.read_sewn(a, sewn[:, part], PPM)
        if check == "ring":
            _check_ring(got["counters"])
            assert got["counters"][0]["status"] == "open"
        else:
            _check_e(got["slots"])
            assert all(s["status"] == "open" for s in got["slots"])


def test_end_to_end_through_measure(tmp_path):
    # An anti-aliased RGBA file: drawn at 10x, area-averaged to 20 px/mm.
    big = _art(200.0).astype(np.float32)
    alpha = cv2.resize(big, (big.shape[1] // 10, big.shape[0] // 10),
                       interpolation=cv2.INTER_AREA)
    rgba = np.zeros(alpha.shape + (4,), np.uint8)
    rgba[..., 3] = np.round(alpha * 255).astype(np.uint8)
    png = tmp_path / "ring_e.png"
    Image.fromarray(rgba, "RGBA").save(png)
    res = cs.measure(png, _design(), {"ring", "E"}, words=["OE"])
    by = {r["name"]: r for r in res["letters"]}
    assert set(by) == {"OE:O", "OE:E"}
    o, e = by["OE:O"], by["OE:E"]
    assert len(o["counters"]) == 1 and o["slots"] == []
    c = o["counters"][0]
    assert c["art_mm2"] == pytest.approx(COUNTER_MM2, rel=0.05)
    assert c["sewn_mm2"] == pytest.approx(COUNTER_MM2, rel=0.05)
    assert not c["closes"]
    assert e["counters"] == [] and len(e["slots"]) == 2
    for s in e["slots"]:
        assert abs(s["art_width_mm"] - SLOT_W) <= 0.05
        assert abs(s["sewn_width_mm"] - SLOT_W) <= 0.05
        assert not s["narrows"]


def test_flags_fire_on_a_closed_counter_and_a_pinched_slot():
    ring, e = _split(_art(PPM), PPM)
    a = cs.read_art(ring, PPM)
    shut = cs.read_sewn(a, ring | a.counters[0]["mask"], PPM)
    row = cs.compare(a, shut)
    assert row["counters"][0]["closes"] and row["counters"][0]["status"] == "closed"
    b = cs.read_art(e, PPM)
    # thread a quarter-millimetre into each slot from both sides: 0.3 mm left
    k = int(round(0.25 * PPM))
    grown = cv2.dilate(e.astype(np.uint8), np.ones((2 * k + 1, 1), np.uint8)).astype(bool)
    row = cs.compare(b, cs.read_sewn(b, grown, PPM))
    for s in row["slots"]:
        assert s["narrows"]
        assert abs(s["sewn_width_mm"] - (SLOT_W - 0.5)) <= 0.05


def test_a_stitch_across_the_mouth_bridges_but_does_not_narrow():
    _ring, e = _split(_art(PPM), PPM)
    b = cs.read_art(e, PPM)
    shut = e.copy()
    # one thread laid down the E's open side, across both mouths
    x = int(round((11.0 - 6.0 - HALF) * PPM))
    shut[:, x - int(HALF * PPM):x + int(HALF * PPM)] |= e.any(axis=1)[:, None]
    row = cs.compare(b, cs.read_sewn(b, shut, PPM))
    for s in row["slots"]:
        assert s["status"] == "bridged"
        assert abs(s["sewn_width_mm"] - SLOT_W) <= 0.05
        assert not s["narrows"]
