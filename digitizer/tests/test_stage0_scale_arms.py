"""`tools/stage0_scale_arms.py` — the committed instrument behind the
2026-09-20 reading of how much of stage 0's resolution-dependence is the RGB
under an alpha cutout's transparency (which `alpha_edge_extend` removes) and
how much is the pixel-absolute signal windows (which it cannot touch).

Pinned: the three arms are the three forms of the flag, the shipped one
among them; on a synthetic cutout the tool reports the gate open under the
floor and shut above it, the extension changing pixels only where the file
has alpha with a different colour underneath, and the opaque control reading
identically under every arm — the property the real fixtures' tables rest on.
"""
from __future__ import annotations

import cv2
import numpy as np
import pytest
from PIL import Image

from digitizer_core import PipelineConfig
from tools import stage0_scale_arms as t


def test_the_arms_are_the_flag_s_forms_and_the_shipped_one_is_among_them():
    shipped = PipelineConfig()
    assert set(t.ARMS) == {"off", "gated", "whole", "gated_s0whole"}
    assert PipelineConfig(**t.ARMS["off"]).alpha_edge_extend is False
    g = PipelineConfig(**t.ARMS["gated"])
    assert (g.alpha_edge_extend, g.alpha_edge_extend_upscaled_only, g.alpha_edge_extend_stage0_whole) == (True, True, False)
    w = PipelineConfig(**t.ARMS["whole"])
    assert (w.alpha_edge_extend, w.alpha_edge_extend_upscaled_only, w.alpha_edge_extend_stage0_whole) == (True, False, False)
    # Kent's pick on the 2026-09-20 tables is the shipped engine.
    k = PipelineConfig(**t.ARMS["gated_s0whole"])
    assert (k.alpha_edge_extend, k.alpha_edge_extend_upscaled_only, k.alpha_edge_extend_stage0_whole) == (
        shipped.alpha_edge_extend, shipped.alpha_edge_extend_upscaled_only, shipped.alpha_edge_extend_stage0_whole) == (True, True, True)
    assert set(t.SWEEP) <= set(t.WIDTHS)


def _cutout(path, under_rgb, size=600):
    """A wide RGBA square with black (or the ink colour) under its alpha."""
    a = np.zeros((size // 2, size), np.uint8)
    a[size // 8: size // 2 - size // 8, size // 8: size - size // 8] = 255
    a = cv2.GaussianBlur(a, (9, 9), 0)
    rgb = np.empty((size // 2, size, 3), np.uint8)
    rgb[...] = under_rgb
    rgb[a == 255] = (180, 30, 30)
    Image.fromarray(np.dstack([rgb, a]), "RGBA").save(path)
    return path


def test_on_a_cutout_the_gate_and_the_extension_are_reported_per_width(tmp_path):
    src = _cutout(tmp_path / "cut.png", (0, 0, 0))
    rows = t.measure_fixture(src, widths=(200, 500), tmp=tmp_path)
    assert [r["width"] for r in rows] == [200, 500, "native"]
    for r in rows:
        assert r["has_alpha"] and r["extension_changes_pixels"]
        assert set(r) >= {"off", "gated", "whole"} and set(r["off"]) >= {"class", "confidence", "unique_color_mass", "gradient_smoothness"}
    # 200 px of image at the default 80 mm is under the 4 px/mm floor; 500 is not.
    assert rows[0]["gate_open"] is True and rows[1]["gate_open"] is False
    # Where the gate is shut, the gated arm IS the off arm — and the shipped
    # engine (stage 0 on the whole-image extension) reads what `whole` reads.
    assert rows[1]["gated"] == rows[1]["off"]
    assert rows[1]["gated_s0whole"] == rows[1]["whole"]
    assert rows[0]["gated_s0whole"] == rows[0]["gated"] == rows[0]["whole"]
    # On the FILE, the two exporters' choice of under-alpha colour stops
    # mattering under the whole-image extension: this file with black under
    # its alpha ramp reads what the same file with the ink colour there reads
    # (the census's invariance, scope-history 2026-09-20), while the pre-flip
    # engine reads them apart.
    friendly = t.measure_fixture(_cutout(tmp_path / "friendly.png", (180, 30, 30)), widths=(200,), tmp=tmp_path)
    hostile_native, friendly_native = rows[2], friendly[1]
    assert hostile_native["width"] == friendly_native["width"] == "native"
    assert hostile_native["whole"] == friendly_native["whole"]
    assert hostile_native["off"] != friendly_native["off"]
    # At native the friendly file has nothing for the extension to change...
    assert friendly_native["extension_changes_pixels"] is False
    # ...but its 200-px resample DOES: PIL resamples RGBA premultiplied, so
    # every downscaled fixture arrives with black under alpha == 0 and
    # rounding noise under the ramp — the rewrite the Studio's canvas made
    # (DOCTRINE 2026-09-19/20), built into the scale test's own harness.
    assert friendly[0]["extension_changes_pixels"] is True
    small = np.array(Image.open(tmp_path / "friendly_200.png").convert("RGBA"))
    assert (small[small[..., 3] == 0][:, :3] == 0).all()
    # And that resample bakes the exporter's RAMP colour into pixels that come
    # out opaque (Lanczos overshoot clips alpha to 255), which no extension
    # can undo: at 200 px the two files read apart even under whole-image.
    # The tables rest on this fact — a downscaled alpha fixture is a hostile
    # file twice over — so it is pinned here.
    assert rows[0]["whole"] != friendly[0]["whole"]


def test_an_opaque_file_reads_the_same_under_every_arm(tmp_path):
    rgb = np.full((300, 600, 3), 255, np.uint8)
    rgb[60:240, 80:520] = (20, 40, 200)
    p = tmp_path / "opaque.png"
    Image.fromarray(rgb, "RGB").save(p)
    rows = t.measure_fixture(p, widths=(200,), tmp=tmp_path)
    for r in rows:
        assert r["has_alpha"] is False and r["gate_open"] is False and r["extension_changes_pixels"] is False
        assert r["off"] == r["gated"] == r["whole"] == r["gated_s0whole"]
    text = t.tables(rows)
    assert "opaque" in text and "| off |" in text and "| whole |" in text


def test_the_fixture_list_is_the_scale_test_s():
    from tests import test_classifier_scale_invariance as scale
    assert t.FIXTURES == scale.FIXTURES
    assert tuple(scale.WIDTHS) == t.SWEEP
