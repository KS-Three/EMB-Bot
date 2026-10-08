"""Two-tone art: snap a black-and-white logo's anti-alias grey to its two inks.

Defect 58 (MASTER_SCOPE): a black-and-white logo sews in four to six cones.
At ~5 source px/mm a thin stroke has almost no pixel of its own ink, so the
region former hands the palette a grey nobody drew and the palette rightly
buys it (DOCTRINE 2026-10-05, "A small shape on a low-resolution logo has no
pixel of its own ink"). Every per-REGION cure tried so far failed on the same
pair: a stroke wants its ink, a halo band wants dissolving, and nothing told
them apart — `logo_bridge_bar.jpg`'s teal ringing was repainted by the rule
that cured `logo_golke_roofing.png`.

This answers the question one level up, per IMAGE: when the art itself has
two inks, every grey in it is a mix of those two, whether it came from a
stroke or a halo, and the raster can be thresholded before any region exists.
Bridge Bar never reaches the snap, because it is colour art.

The test reads stage 1's raster and asks three things:

* **achromatic** — fewer than `MAX_CHROMA_FRAC` of pixels carry chroma
  (max - min channel) above `CHROMA`. JPEG noise on a black-and-white file
  stays under it; one coloured accent does not.
* **two separated modes** — the darkest-half and lightest-half histogram
  peaks at least `MIN_MODE_GAP` grey levels apart.
* **no grey plateau** — inside the middle 60% between the modes, no 8-level
  grey bin holds more than `MAX_MID_BIN` of all pixels. Anti-alias grey is
  spread thinly across the whole ramp; a drawn grey ink stacks in one bin.
  This is the gate that keeps a grey-and-black logo (`logo_hotel_fremont`,
  whose rope is a real grey) out.

Measured 2026-10-08 on every image under `testdata/art` and `testdata/photo`
(`tools/two_tone_probe.py --detect`): the seven black-and-white logos read
max-bin 0.0027-0.0064 and pass; the nearest refusal is
`logo_hotel_fremont_patch` at 0.0109, every colour or photographic file
fails the chroma test outright.

The snap replaces each pixel with the ink nearer it in grey (the midpoint
threshold), on `rgb` and on the other rasters stage 1 carries in its frame.
Because stage 1 has already Lanczos-upscaled a low-resolution source, the
threshold runs on a smooth interpolated ramp and the edge it draws is the
sub-pixel contour, not a staircase of source pixels.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CHROMA = 40
MAX_CHROMA_FRAC = 0.005
MIN_MODE_GAP = 150
MAX_MID_BIN = 0.008
# Pixels this close in grey to a mode are averaged to give that ink's RGB.
INK_BAND = 10


@dataclass(frozen=True)
class TwoTone:
    dark: tuple[int, int, int]
    light: tuple[int, int, int]
    dark_grey: int
    light_grey: int
    mid_frac: float      # share of pixels between the inks — the grey the snap removes
    max_mid_bin: float


def detect(rgb: np.ndarray) -> TwoTone | None:
    """The two inks of a two-tone raster, or None when it is not one."""
    px = rgb.reshape(-1, 3)
    if not len(px):
        return None
    chroma = px.max(1).astype(np.int16) - px.min(1).astype(np.int16)
    if float(np.mean(chroma > CHROMA)) >= MAX_CHROMA_FRAC:
        return None
    g = px.astype(np.float32).mean(1)
    hist = np.bincount(g.astype(np.int32), minlength=256)
    dark = int(np.argmax(hist[:128]))
    light = 128 + int(np.argmax(hist[128:]))
    if light - dark < MIN_MODE_GAP:
        return None
    lo, hi = dark + 0.2 * (light - dark), dark + 0.8 * (light - dark)
    mid = (g > lo) & (g < hi)
    mid_bins = np.bincount((g[mid] / 8).astype(np.int32), minlength=32)
    max_bin = float(mid_bins.max()) / len(g) if mid.any() else 0.0
    if max_bin > MAX_MID_BIN:
        return None

    def ink(at: int) -> tuple[int, int, int]:
        sel = np.abs(g - at) <= INK_BAND
        return tuple(int(round(v)) for v in px[sel].astype(np.float64).mean(0))

    return TwoTone(dark=ink(dark), light=ink(light), dark_grey=dark,
                   light_grey=light, mid_frac=round(float(mid.mean()), 4),
                   max_mid_bin=round(max_bin, 4))


def snap(rgb: np.ndarray, tt: TwoTone) -> np.ndarray:
    """`rgb` with every pixel replaced by the ink nearer it in grey."""
    cut = (tt.dark_grey + tt.light_grey) / 2.0
    light = rgb.astype(np.float32).mean(2) >= cut
    out = np.empty_like(rgb)
    out[...] = np.asarray(tt.dark, dtype=rgb.dtype)
    out[light] = np.asarray(tt.light, dtype=rgb.dtype)
    return out
