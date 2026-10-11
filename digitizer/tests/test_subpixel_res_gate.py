"""`cfg.subpixel_edges_min_px_per_mm`: a resolution floor under the native
edge read (`subpixel_edges_upscaled`), built 2026-10-11, default None.

The contracts. None is today's pipeline byte for byte — the default, and an
explicit None, trace exactly what they traced before the field existed (the
committed goldens hold the whole-pipeline half of that). Set, a source that
stage 1 upscaled and that delivers LESS than the floor skips the read and
keeps the pre-flip polygon, exactly as `subpixel_edges_upscaled=False`
would; a source at or above it takes the read as today. The evidence for
where the floor belongs is `docs/subpixel-res-gate-2026-10-11.md`.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import build_generation

ART_PX = 80          # the disc's own extent in source pixels = the art bbox


def _cutout(tmp_path: Path) -> Path:
    """A becker-shaped source: one ink, the shape a coverage-ramped disc in
    alpha. Its art bbox is the disc's ART_PX, so px/mm in = ART_PX / width."""
    s, w = 16, 120
    canvas = np.zeros((w * s, w * s), np.uint8)
    cv2.circle(canvas, (60 * s, 60 * s), (ART_PX // 2) * s, 255, -1)
    img = np.zeros((w, w, 4), np.uint8)
    img[..., 3] = cv2.resize(canvas, (w, w), interpolation=cv2.INTER_AREA)
    path = tmp_path / "cutout.png"
    cv2.imwrite(str(path), img)
    return path


def _run(art: Path, px_per_mm: float, **kw):
    """-> (Prep, regions) at the target width that gives `px_per_mm` in. The
    width is rounded DOWN to 0.1 mm so the resolution lands at or above the
    nominal one, never a float's breadth under it."""
    width = np.floor(ART_PX / px_per_mm * 10.0) / 10.0
    gen = build_generation(str(art), PipelineConfig(target_width_mm=float(width), **kw))
    return gen.p, [r for r in gen.regions if not r.meta.get("enclosed_background")]


def _wkts(regions):
    return [r.polygon.wkt for r in regions]


def test_the_default_is_none():
    assert PipelineConfig().subpixel_edges_min_px_per_mm is None


@pytest.mark.parametrize("ppm", [1.8, 5.0])
def test_none_is_todays_polygon_byte_for_byte(tmp_path, ppm):
    art = _cutout(tmp_path)
    _p, default = _run(art, ppm)
    _p, explicit = _run(art, ppm, subpixel_edges_min_px_per_mm=None)
    assert _wkts(default) == _wkts(explicit)
    assert all("subpixel_accepted" in r.meta for r in default)      # the read ran


@pytest.mark.parametrize("ppm,taken", [(1.8, False), (3.0, True), (5.0, True)])
def test_a_floor_of_3_skips_the_read_at_1_8_and_takes_it_at_3_and_5(tmp_path, ppm, taken):
    art = _cutout(tmp_path)
    p, gated = _run(art, ppm, subpixel_edges_min_px_per_mm=3.0)
    assert p.upscale[0] > 1.0                                        # the regime under test
    assert p.input_px_per_mm == pytest.approx(ppm, rel=0.02)
    _p, on = _run(art, ppm)
    _p, off = _run(art, ppm, subpixel_edges_upscaled=False)
    assert _wkts(on) != _wkts(off)                                   # the read moves this disc
    if taken:
        assert _wkts(gated) == _wkts(on)
        assert all("subpixel_accepted" in r.meta for r in gated)
    else:
        assert _wkts(gated) == _wkts(off)
        assert not any("subpixel_accepted" in r.meta for r in gated)


def test_the_floor_never_touches_a_source_at_its_own_resolution(tmp_path):
    """Not upscaled, the native read never ran; a floor above the source's
    resolution must not switch off the ordinary native-resolution read."""
    art = _cutout(tmp_path)
    p, base = _run(art, 10.0)
    assert p.upscale == (1.0, 1.0)
    _p, gated = _run(art, 10.0, subpixel_edges_min_px_per_mm=50.0)
    assert _wkts(gated) == _wkts(base)
