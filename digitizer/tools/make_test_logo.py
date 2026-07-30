#!/usr/bin/env python
"""Generate the committed synthetic test fixtures (testdata/*.png).

Deterministic by construction (no RNG). Drawn at 4x supersample and
downscaled with INTER_AREA so every edge carries a realistic 1-2px
anti-alias halo — the exact artifact stage 2's AA handling must survive.

Fixtures:
  logo_whitebg.png   5-color flat logo on opaque white — the primary golden.
  logo_alpha.png     the same art with a transparent background.
  bg_uncertain.png   a navy block with a white notch cut in from the border —
                     the border flood legitimately intrudes deep past the
                     artwork margin, which must raise BACKGROUND_UNCERTAIN.
  ribbon_curve.png   one ~2 mm stroke curved through an S — the satin case the
                     flat logo cannot pose, where the medial axis runs into a
                     cap corner and the column has to survive it.

Art inventory (what each element exercises):
  red filled circle          blob -> fill; absorb target for the teal patch
  blue ring                  polygon WITH HOLE preservation
  green thin bar (~2 mm)     satin-width candidate; must not be eaten by AA pass
  purple|orange touching     adjacent different-color regions stay separate
  orange small dot (~1 mm)   below min-detail -> dropped with warning
  teal 1 mm patch on circle  sub-sewable -> absorbed into circle; its thread
                             layer then holds zero regions and must vanish
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "testdata"

S = 4  # supersample factor
W, H = 800, 500

WHITE = (255, 255, 255)
RED = (60, 60, 235)      # BGR — reads as red
BLUE = (200, 90, 30)     # readable blue
GREEN = (70, 170, 60)
PURPLE = (180, 60, 130)
ORANGE = (40, 140, 245)
TEAL = (160, 160, 40)
NAVY = (90, 40, 20)


def draw_art(canvas: np.ndarray) -> None:
    """Draw the 5-color logo (plus teal absorb patch) at supersampled scale."""
    def pt(x: int, y: int) -> tuple[int, int]:
        return (x * S, y * S)

    # red circle (blob)
    cv2.circle(canvas, pt(200, 250), 120 * S, RED, -1)
    # teal absorb patch straddling the circle's right edge (~1 mm square)
    cv2.rectangle(canvas, pt(315, 245), pt(325, 255), TEAL, -1)
    # blue ring (hole preserved). Hole is punched AFTER, per-variant.
    cv2.circle(canvas, pt(450, 250), 110 * S, BLUE, -1)
    # green thin bar (~2 mm at the 80 mm target width)
    cv2.rectangle(canvas, pt(560, 120), pt(750, 139), GREEN, -1)
    # touching purple|orange rectangles (shared edge at x=650)
    cv2.rectangle(canvas, pt(560, 300), pt(650, 380), PURPLE, -1)
    cv2.rectangle(canvas, pt(650, 300), pt(740, 380), ORANGE, -1)
    # orange sub-detail dot (~1 mm diameter)
    cv2.circle(canvas, pt(700, 180), 5 * S, ORANGE, -1)


def punch_hole(canvas: np.ndarray, color) -> None:
    cv2.circle(canvas, (450 * S, 250 * S), 60 * S, color, -1)


def down(canvas: np.ndarray) -> np.ndarray:
    return cv2.resize(canvas, (W, H), interpolation=cv2.INTER_AREA)


def main() -> None:
    OUT.mkdir(exist_ok=True)

    # --- logo_whitebg.png (opaque, white background, white ring hole) -------
    bgr = np.full((H * S, W * S, 3), 255, np.uint8)
    draw_art(bgr)
    punch_hole(bgr, WHITE)
    cv2.imwrite(str(OUT / "logo_whitebg.png"), down(bgr))

    # --- logo_alpha.png (transparent background and ring hole) --------------
    bgra = np.zeros((H * S, W * S, 4), np.uint8)
    art = np.zeros((H * S, W * S, 3), np.uint8)
    draw_art(art)
    mask = np.zeros((H * S, W * S), np.uint8)
    draw_art_mask = np.any(art != 0, axis=2).astype(np.uint8) * 255
    mask[:] = draw_art_mask
    bgra[:, :, :3] = art
    bgra[:, :, 3] = mask
    # punch the ring hole out of color AND alpha
    punch_hole(bgra, (0, 0, 0, 0))
    cv2.imwrite(str(OUT / "logo_alpha.png"), down(bgra))

    # --- ribbon_curve.png (one long thin curved stroke, nothing else) -------
    # The satin stress case the flat logo cannot pose: a stroke that is thin
    # enough for a column AND curved enough that its medial axis runs into a
    # cap corner at each free end. Drawn as a stroked polyline so its caps are
    # square, which is where the corner forks.
    rib = np.full((H * S, W * S, 3), 255, np.uint8)
    curve = np.array(
        [[int((60 + t / 199 * 680) * S),
          int((250 + 120 * math.sin(t / 199 * math.pi * 1.6)) * S)]
         for t in range(200)], np.int32)
    cv2.polylines(rib, [curve], False, RED, int(2.2 * S * W / 80))
    cv2.imwrite(str(OUT / "ribbon_curve.png"), down(rib))

    # --- bg_uncertain.png (white notch from border deep into the art) -------
    unc = np.full((H * S, W * S, 3), 255, np.uint8)
    cv2.rectangle(unc, (100 * S, 80 * S), (700 * S, 420 * S), NAVY, -1)
    cv2.rectangle(unc, (380 * S, 0), (420 * S, 300 * S), WHITE, -1)
    cv2.imwrite(str(OUT / "bg_uncertain.png"), down(unc))

    for f in sorted(OUT.glob("*.png")):
        print(f.name, f.stat().st_size, "bytes")


if __name__ == "__main__":
    main()
