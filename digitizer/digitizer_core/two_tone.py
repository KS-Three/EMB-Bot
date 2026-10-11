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

The test reads stage 1's FOREGROUND (`~bg_mask`) and asks four things:

* **achromatic** — fewer than `MAX_CHROMA_FRAC` of pixels carry chroma
  (max - min channel) above `CHROMA`;
* **both inks present** — each half of the grey histogram holds at least
  `MIN_INK_FRAC` (a white logo on transparency has no dark half);
* **two separated modes** — the darkest-half and lightest-half peaks at least
  `MIN_MODE_GAP` grey levels apart;
* **no grey plateau** — over the 8-level bins lying wholly inside the middle
  60% between the modes, the tallest is at most `MAX_PLATEAU` times their
  mean. Anti-alias grey spreads evenly across the ramp; a drawn grey ink
  stacks in one bin. This keeps `logo_hotel_fremont` (rope in a real grey,
  14.3) and `logo_hotel_fremont_patch` (2.34) out.

Measured 2026-10-08 over every image under `testdata/`, `testdata/art` and
`testdata/photo` (`tools/two_tone_probe.py --detect`): it fires on the six
black-and-white logos, the tires script and one synthetic black-and-white
fixture (plateau 1.08-1.92) and on nothing else. `logo_gaulke_roofing` at
1.92 is the closest pass; the patch at 2.34 the closest refusal.

The snap replaces each pixel of `rgb` with the ink nearer it in grey (the
midpoint threshold). Because stage 1 has already Lanczos-upscaled a
low-resolution source, the threshold runs on a smooth interpolated ramp and
draws the sub-pixel contour, not a staircase of source pixels. The rasters
stage 1 keeps BESIDE `rgb` are not snapped: `native_rgb` feeds stage 4's
sub-pixel edge read, and `raw_rgb` / `bg_rgb` / `bg_edge_rgb` describe the
file's background. `fold_fringe` then hands the snapped outer halo back to
the background.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

CHROMA = 40
MAX_CHROMA_FRAC = 0.005
MIN_MODE_GAP = 150
MAX_PLATEAU = 2.1
# Each half of the histogram must hold at least this share of the pixels.
MIN_INK_FRAC = 0.01
# Pixels this close in grey to a mode are averaged to give that ink's RGB.
INK_BAND = 10
# An ink within this (max channel) of stage 1's background colour IS it.
BG_INK_TOL = 40


@dataclass(frozen=True)
class TwoTone:
    dark: tuple[int, int, int]
    light: tuple[int, int, int]
    dark_grey: int
    light_grey: int
    mid_frac: float      # share of pixels between the inks — the grey the snap removes
    plateau: float


def stats(rgb: np.ndarray, fg: np.ndarray | None = None) -> dict | None:
    """What `detect` reads, over the foreground pixels (all of them when
    `fg` is None): chroma share, the two grey modes, the mid-grey share and
    its plateau (tallest 8-level bin over their mean), and the population of each half of the
    histogram. None when there are no pixels."""
    px = rgb.reshape(-1, 3) if fg is None else rgb[fg]
    if not len(px):
        return None
    chroma = px.max(1).astype(np.int16) - px.min(1).astype(np.int16)
    g = px.astype(np.float32).mean(1)
    hist = np.bincount(g.astype(np.int32), minlength=256)
    dark = int(np.argmax(hist[:128]))
    light = 128 + int(np.argmax(hist[128:]))
    lo, hi = dark + 0.2 * (light - dark), dark + 0.8 * (light - dark)
    mid = (g > lo) & (g < hi)
    # The 8-level bins lying wholly inside the band: its tallest over its
    # mean. Scale-free, so neither the margin nor how much linework the
    # logo has moves it.
    bins = np.bincount((g[mid] / 8).astype(np.int32), minlength=32)[int(lo // 8) + 1:int(hi // 8)]
    return {
        "px": px, "g": g,
        "chroma_frac": float(np.mean(chroma > CHROMA)),
        "dark": dark, "light": light,
        "dark_frac": float(hist[:128].sum()) / len(g),
        "light_frac": float(hist[128:].sum()) / len(g),
        "mid_frac": float(mid.mean()),
        "plateau": float(bins.max() / bins.mean()) if len(bins) and bins.sum() else 0.0,
    }


def detect(rgb: np.ndarray, fg: np.ndarray | None = None) -> TwoTone | None:
    """The two inks of a two-tone raster, or None when it is not one.

    Reads the FOREGROUND (`fg`, stage 1's `~bg_mask`) so the verdict does not
    move with how much margin the customer left round the art: every
    threshold here is a share of the pixels read, and a white margin would
    dilute a small colour accent or a drawn grey under them."""
    st = stats(rgb, fg)
    if st is None:
        return None
    if st["chroma_frac"] >= MAX_CHROMA_FRAC:
        return None
    # Both inks must actually be present: a white logo on transparency has
    # no dark half at all, and argmax of an empty half is a mode at 0.
    if st["dark_frac"] < MIN_INK_FRAC or st["light_frac"] < MIN_INK_FRAC:
        return None
    if st["light"] - st["dark"] < MIN_MODE_GAP:
        return None
    if st["plateau"] > MAX_PLATEAU:
        return None
    px, g = st["px"], st["g"]

    def ink(at: int) -> tuple[int, int, int]:
        sel = np.abs(g - at) <= INK_BAND
        return tuple(int(round(v)) for v in px[sel].astype(np.float64).mean(0))

    return TwoTone(dark=ink(st["dark"]), light=ink(st["light"]),
                   dark_grey=st["dark"], light_grey=st["light"],
                   mid_frac=round(st["mid_frac"], 4),
                   plateau=round(st["plateau"], 2))


def apply(p) -> bool:
    """Stage 1.3 on a stage-1 `Prep`, in place: detect on the foreground,
    snap `p.rgb`, fold the snapped halo into `p.bg_mask`, hand the thin
    drawn lines back as light ink (`keep_lines`), and trim `enclosed_mask`
    to what is still foreground. True when the snap fired.

    One function because two callers must agree on every pixel: the
    pipeline, and preflight's thread grader, which re-reads stage 1 and
    would otherwise judge each thread against the anti-alias grey the snap
    removed (2026-10-08: White blocked on golke at dE 14.6 and gaulke 33.9
    under the lines `keep_lines` widens). `native_rgb`, `raw_rgb`, `bg_rgb`
    and `bg_edge_rgb` are left alone (pipeline.py, stage 1.3)."""
    tt = detect(p.rgb, ~p.bg_mask)
    if tt is None:
        return False
    p.rgb = snap(p.rgb, tt)
    p.bg_mask = fold_fringe(p.rgb, tt, p.bg_mask, p.bg_rgb)
    # A thin white line drawn between the inks is background-coloured and
    # open to the background, so the flood and the fold take it; as bare
    # fabric it is too narrow to stay open. Sew it light.
    lines = keep_lines(p.bg_mask, p.px_per_mm)
    if lines.any():
        p.rgb[lines] = np.asarray(tt.light, dtype=p.rgb.dtype)
        p.bg_mask = p.bg_mask & ~lines
    if p.enclosed_mask is not None:
        p.enclosed_mask = p.enclosed_mask & ~p.bg_mask
        if not p.enclosed_mask.any():
            p.enclosed_mask = None
    return True


def snap(rgb: np.ndarray, tt: TwoTone) -> np.ndarray:
    """`rgb` with every pixel replaced by the ink nearer it in grey."""
    cut = (tt.dark_grey + tt.light_grey) / 2.0
    light = rgb.astype(np.float32).mean(2) >= cut
    out = np.empty_like(rgb)
    out[...] = np.asarray(tt.dark, dtype=rgb.dtype)
    out[light] = np.asarray(tt.light, dtype=rgb.dtype)
    return out


def fold_fringe(snapped: np.ndarray, tt: TwoTone, bg_mask: np.ndarray,
                bg_rgb: tuple[int, int, int] | None) -> np.ndarray:
    """`bg_mask` grown by the snapped foreground that IS the background.

    Stage 1's border flood stops at its colour tolerance, so the outer
    anti-alias halo — grey that stage 2 dissolved as a blend toward the
    background — sits inside the foreground. The snap turns the lighter half
    of it into pure ink of the background's own colour, which no longer reads
    as a blend: left alone it becomes slivers of its own regions round the
    outer edge (reviewer, 2026-10-08: golke 1 → 12 such regions). Every
    connected run of the background-coloured ink that touches the
    background joins it. Nothing moves when the background colour is
    unknown (an alpha cutout, `bg_rgb` None) or matches neither ink."""
    if bg_rgb is None:
        return bg_mask
    import cv2

    bg = np.asarray(bg_rgb, dtype=np.int16)
    inks = (tt.dark, tt.light)
    d = [int(np.abs(np.asarray(c, dtype=np.int16) - bg).max()) for c in inks]
    k = int(np.argmin(d))
    if d[k] > BG_INK_TOL:
        return bg_mask
    same = np.all(snapped == np.asarray(inks[k], dtype=snapped.dtype), axis=2) & ~bg_mask
    if not same.any():
        return bg_mask
    n, lab = cv2.connectedComponents(same.astype(np.uint8), connectivity=8)
    touch = cv2.dilate(bg_mask.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
    hit = np.unique(lab[same & touch])
    hit = hit[hit > 0]
    if not len(hit):
        return bg_mask
    return bg_mask | np.isin(lab, hit)


# A background channel at most this wide (mm) cannot stay open as bare
# fabric: the fills either side of it, with their pull compensation, close
# it, so the art's white line sews as one black mass (golke's roof lines,
# 2026-10-08). `keep_lines` hands such a channel back to the art as light ink.
LINE_MAX_W_MM = 1.0
# ... but only when it is a drawn LINE, not the gap between two letters.
# Measured on the snap's fixtures at 80 mm (2026-10-08, `keep_lines` docstring):
# the lines run 8.0-43.5 mm at an elongation (length over mean width) of
# 9.8-124; the longest letter gap 5.6 mm, the most elongated 8.6.
LINE_MIN_LEN_MM = 7.0
LINE_MIN_ELONGATION = 9.0


def keep_lines(bg_mask: np.ndarray, px_per_mm: float) -> np.ndarray:
    """The pixels of `bg_mask` that are a thin drawn line between inks.

    A white line drawn between two black shapes is background-coloured and
    open to the background at its ends, so stage 1's flood takes its core and
    `fold_fringe` its snapped edges. Snapped, it is a channel of bare fabric
    narrower than stitching keeps open; unsnapped it sewed as grey edges and
    still read as a line. A channel is what an opening by a disk
    `LINE_MAX_W_MM` across removes from the background; it is a line when
    its skeleton runs at least `LINE_MIN_LEN_MM` and `LINE_MIN_ELONGATION`
    times its mean width. That keeps the gaps between letters, the crumbs
    the opening cuts from the background's corners, and the strip between
    the art and the canvas edge (the border counts as background) where
    they are.

    Measured 2026-10-08 at 80 mm: golke's roof chevron (42.4 mm), window
    cross (10.8) and the two halves of the sun's zigzag (8.2, 8.0) are lines;
    gaulke's chevron (43.5) and window cross (11.0) too. Its letter gaps
    (up to 5.6 mm, elongation up to 8.6) and every channel on mfab_lc,
    mfab_hat, toat_machine, toat_beanie and the tires script (none over
    1.8 mm) are not."""
    import cv2
    from skimage.morphology import skeletonize

    r = max(1, int(round(LINE_MAX_W_MM * px_per_mm / 2.0)))
    disk = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    opened = cv2.morphologyEx(bg_mask.astype(np.uint8), cv2.MORPH_OPEN, disk,
                              borderType=cv2.BORDER_CONSTANT, borderValue=1).astype(bool)
    thin = bg_mask & ~opened
    out = np.zeros_like(bg_mask)
    if not thin.any():
        return out
    n, lab, st, _ = cv2.connectedComponentsWithStats(thin.astype(np.uint8), connectivity=8)
    skel = skeletonize(thin)
    skel_len = np.bincount(lab[skel], minlength=n)
    for i in range(1, n):
        length = int(skel_len[i])
        if length < LINE_MIN_LEN_MM * px_per_mm:
            continue
        width = st[i, cv2.CC_STAT_AREA] / length
        if length >= LINE_MIN_ELONGATION * width:
            out |= lab == i
    if not out.any():
        return out
    # Widened to the satin floor along its own centre line, into the ink
    # either side: golke's chevron is 0.2-0.3 mm at stage 1, and a column
    # under `SATIN_MIN_CROSS_MM` is dropped downstream, so the line sewed
    # broken (2026-10-08). The floor is the existing constant, not a new one.
    from .machine import SATIN_MIN_CROSS_MM

    rr = max(1, int(np.ceil(SATIN_MIN_CROSS_MM * px_per_mm / 2.0)))
    core = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * rr + 1, 2 * rr + 1))
    return out | cv2.dilate((skel & out).astype(np.uint8), core).astype(bool)
