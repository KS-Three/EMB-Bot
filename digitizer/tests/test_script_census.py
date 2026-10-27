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


def _word(tmp_path, gaps_mm=(0.0, 6.0), name: str = "word"):
    """Upright 2 mm columns 10 mm tall at the given x offsets, joined into one
    needle-down run by a short walk along the baseline: one word, one group."""
    pat = pystitch.EmbPattern()
    for k, x0 in enumerate(gaps_mm):
        if k:       # the join: a walk along the baseline to the next column
            for s in range(1, 13):
                pat.add_stitch_absolute(pystitch.STITCH, (gaps_mm[k - 1] + 1.0 + s * 0.4) * 10, 0)
        y, left = 0.0, True
        while y >= -10.0:
            pat.add_stitch_absolute(pystitch.STITCH, (x0 + (0.0 if left else 2.0)) * 10, y * 10)
            y -= 0.2
            left = not left
        pat.add_stitch_absolute(pystitch.STITCH, (x0 + 1.0) * 10, y * 10)
    pat.add_command(pystitch.END)
    path = tmp_path / f"{name}.dst"
    pystitch.write_dst(pat, str(path))
    return path


def test_a_word_cut_into_letters_counts_each_letters_columns(tmp_path):
    word = max(sc.census(_word(tmp_path), letters=[0.5])["groups"], key=lambda g: g["area_mm2"])
    rows = word["letters"]
    assert [r["letter"] for r in rows] == [0, 1]
    assert [r["columns"] for r in rows] == [1, 1]
    assert all(r["breaks"] == 0 for r in rows)          # each letter one unbroken stretch
    assert all(1.8 <= r["width_mm"] <= 2.2 for r in rows)
