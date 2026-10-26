"""tools/script_census: square-to-stroke against flat-to-the-text-line, read off
the file's own coverage (L7, 2026-10-24).

A column slanted 30 deg off vertical (an italic stem) sewn two ways: crosses
square to the stroke, and crosses flat to the line of text. The stroke
direction comes from the coverage mask, so neither column can vouch for
itself through its own spine.
"""
import math

import pystitch

from tools import script_census as sc

SLANT = 30.0


def _stem(tmp_path, cross_deg: float, name: str):
    """A 4 mm column, 20 mm long, leaning SLANT deg right (y down), its crosses
    at `cross_deg` (0 = horizontal), pitch 0.4 mm along the stem."""
    t = math.radians(SLANT)
    up = (math.sin(t), -math.cos(t))          # along the stroke, upward
    c = math.radians(cross_deg)
    half = 2.0 / max(abs(math.cos(c - t)), 0.3)
    u = (math.cos(c) * half, math.sin(c) * half)
    pat = pystitch.EmbPattern()
    s, left = 0.0, True
    while s <= 20.0:
        m = (up[0] * s, up[1] * s)
        p = (m[0] - u[0], m[1] - u[1]) if left else (m[0] + u[0], m[1] + u[1])
        pat.add_stitch_absolute(pystitch.STITCH, p[0] * 10, p[1] * 10)
        s += 0.2
        left = not left
    pat.add_command(pystitch.END)
    path = tmp_path / f"{name}.dst"
    pystitch.write_dst(pat, str(path))
    return path


def test_square_crosses_read_square(tmp_path):
    g = sc.census(_stem(tmp_path, SLANT, "square"))["groups"][0]
    assert g["square_share"] > 0.9
    assert abs(g["slant_med"] - SLANT) < 6
    assert abs(g["slanted_dev_med"]) < 6


def test_flat_crosses_read_as_the_slant(tmp_path):
    g = sc.census(_stem(tmp_path, 0.0, "flat"))["groups"][0]
    assert g["square_share"] < 0.1
    assert abs(abs(g["slanted_dev_med"]) - SLANT) < 6
    assert abs(g["cross_vs_text_med"]) < 6
