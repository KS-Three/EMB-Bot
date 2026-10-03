"""`stage2_photo_segment.snap_region_edges` — region edges follow pixels.

The gradient lane builds every region out of whole SEEDS superpixels, so a
region edge can only ever be a superpixel edge. Measured 2026-09-30 on Kent's
real Instagram file (2000 px, 80 mm): 148 superpixels straddle the white
ring/square edge, putting 7.6% of the white on the wrong side — the jagged
ring and bitten dot in the stitches. Forced flat, which labels per pixel,
sews the same shapes clean. `snap_region_edges` moves an edge pixel into a
neighbouring region only when its colour is closer to that region's mean by
`SNAP_MARGIN_LAB`, so a drawn edge snaps and a soft seam inside a sweep does
not move.

These fixtures are synthetic on purpose: they test a function's contract.
Gate 2 bars synthetic fixtures from CALIBRATING stage 0, which this is not.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from digitizer_core.config import PipelineConfig
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import SNAP_MARGIN_LAB, segment, snap_region_edges

PHOTO_DIR = Path(__file__).resolve().parent.parent / "testdata" / "photo"

H, W, BLOCK = 160, 200, 16


def _ramp_lab() -> np.ndarray:
    """A left-to-right magenta->orange-ish sweep in Lab: L 50..65, a 70..40,
    b -10..50 — about ΔE 70 end to end, under 0.4 per pixel."""
    t = np.linspace(0.0, 1.0, W)[None, :].repeat(H, 0)
    return np.stack([50 + 15 * t, 70 - 30 * t, -10 + 60 * t], axis=-1)


def _disc(cy=80, cx=100, r=37) -> np.ndarray:
    yy, xx = np.mgrid[:H, :W]
    return (yy - cy) ** 2 + (xx - cx) ** 2 <= r * r


def _blocky(mask: np.ndarray) -> np.ndarray:
    """What a superpixel union hands back: `mask` rounded to BLOCK-px tiles
    by majority, so its edge is a staircase that misses the real one."""
    out = np.zeros_like(mask)
    for y in range(0, H, BLOCK):
        for x in range(0, W, BLOCK):
            tile = mask[y:y + BLOCK, x:x + BLOCK]
            out[y:y + BLOCK, x:x + BLOCK] = tile.mean() > 0.5
    return out


def test_a_white_disc_on_a_sweep_snaps_to_its_real_edge():
    lab = _ramp_lab()
    disc = _disc()
    lab[disc] = (100.0, 0.0, 0.0)
    labels = np.where(_blocky(disc), 2, 1)
    valid = np.ones((H, W), bool)
    before = int(((labels == 2) ^ disc).sum())
    assert before > 300  # the staircase really misses the disc

    out = snap_region_edges(labels, valid, lab)

    after = int(((out == 2) ^ disc).sum())
    assert after == 0, (before, after)


def _staircase_seam() -> np.ndarray:
    yy, xx = np.mgrid[:H, :W]
    return np.where(xx + (yy // BLOCK) * 3 < W // 2, 1, 2)


def test_a_seam_inside_a_flattened_sweep_does_not_move():
    """The pipeline hands the snap the merge's Lab with the design ramp
    SUBTRACTED when it fits. There a sweep reads as one colour (residual
    well under the margin), so a staircase seam cut through it stays put."""
    rng = np.random.default_rng(0)
    lab = np.full((H, W, 3), (55.0, 55.0, 20.0)) + rng.normal(0, 1.5, (H, W, 3))
    labels = _staircase_seam()
    out = snap_region_edges(labels, np.ones((H, W), bool), lab)
    assert np.array_equal(out, labels)


def test_a_seam_inside_a_raw_sweep_only_settles_toward_the_colour_midpoint():
    """Without the ramp subtracted the two halves' means sit ΔE ~35 apart,
    so a pixel stranded deep on the wrong side of the colour midpoint does
    move. It is still a seam inside a sweep: it stays one clean left/right
    split and never leaves the band the staircase already spanned."""
    labels = _staircase_seam()
    out = snap_region_edges(labels, np.ones((H, W), bool), _ramp_lab())
    xx = np.mgrid[:H, :W][1]
    band = (xx >= W // 2 - 3 * (H // BLOCK)) & (xx <= W // 2)
    assert np.all(out[~band] == labels[~band])
    # Every row is still 1s then 2s: no island, no second seam.
    assert np.all(np.diff(out, axis=1) >= 0)


def test_excluded_pixels_are_never_read_or_written():
    lab = _ramp_lab()
    disc = _disc()
    lab[disc] = (100.0, 0.0, 0.0)
    labels = np.where(_blocky(disc), 2, 1)
    valid = np.ones((H, W), bool)
    valid[:, :40] = False
    labels[~valid] = 0
    lab[~valid] = (100.0, 0.0, 0.0)  # white, like the disc: must not attract it
    out = snap_region_edges(labels, valid, lab)
    assert np.all(out[~valid] == 0)
    assert int(((out == 2) & valid) .sum()) == int((disc & valid).sum())


def test_the_margin_is_the_documented_value():
    assert SNAP_MARGIN_LAB == 10.0


def test_the_flag_is_on_by_default():
    """Kent's flip, 2026-09-30, on renders (see `config.snap_region_edges`)."""
    assert PipelineConfig().snap_region_edges is True


def _wrong_side_px(snap: bool) -> tuple[int, int]:
    """Segment the committed gradient repro and count pixels on the wrong
    side of its white icon: white pixels in a mostly-colour label plus
    colour pixels in a mostly-white label. -> (wrong, white pixel count)."""
    cfg = PipelineConfig(target_width_mm=80.0, max_colors=6, edge_cap="none")
    p = prep(str(PHOTO_DIR / "repro_gradient_white_icon.png"), cfg)
    q = segment(p, cfg, snap_edges=snap)
    fg = q.labels >= 0
    white = (p.rgb.min(axis=2) > 235) & fg
    ids = q.labels[fg]
    n = int(ids.max()) + 1
    frac = np.bincount(ids, weights=white[fg], minlength=n) / np.maximum(np.bincount(ids, minlength=n), 1)
    pred = np.zeros_like(white)
    pred[fg] = frac[ids] > 0.5
    return int((pred ^ white).sum()), int(white.sum())


def test_on_the_repro_icon_white_lands_on_its_own_side():
    """End to end through `segment` on the committed gradient repro: the
    snap cuts the icon's wrong-side pixels by at least two thirds, and off
    is today's path (the default argument)."""
    off, n_white = _wrong_side_px(False)
    on, _ = _wrong_side_px(True)
    assert off > 0.01 * n_white  # the defect is really there on this fixture
    assert on < off / 3, (off, on, n_white)
