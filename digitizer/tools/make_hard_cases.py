#!/usr/bin/env python
"""Generate the harder synthetic review cases (debug_out/cases/*.png).

Not committed fixtures — these exist so the quality review can see defects the
committed testdata does not exercise: serif lettering, a long thin curved
ribbon, and tightly nested colors. Deterministic, drawn 4x and downscaled with
INTER_AREA so every edge carries a realistic anti-alias halo.

Run: .venv/Scripts/python tools/make_hard_cases.py
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "debug_out" / "cases"
S = 4

WHITE = (255, 255, 255)
BLACK = (30, 30, 30)
RED = (60, 60, 235)
BLUE = (200, 90, 30)
GREEN = (70, 170, 60)
GOLD = (40, 175, 235)
NAVY = (90, 40, 20)


def down(canvas: np.ndarray, w: int, h: int) -> np.ndarray:
    return cv2.resize(canvas, (w, h), interpolation=cv2.INTER_AREA)


def serif_text() -> np.ndarray:
    """Fine serif lettering — the classic satin-lettering stress case."""
    w, h = 900, 260
    c = np.full((h * S, w * S, 3), 255, np.uint8)
    cv2.putText(c, "Fritsch", (30 * S, 170 * S), cv2.FONT_HERSHEY_TRIPLEX,
                5.0 * S, BLACK, 4 * S, cv2.LINE_AA)
    return down(c, w, h)


def curved_ribbon() -> np.ndarray:
    """A long thin curved ribbon — pull on curves, spine quality, caps."""
    w, h = 800, 400
    c = np.full((h * S, w * S, 3), 255, np.uint8)
    pts = []
    for i in range(200):
        t = i / 199.0
        x = 60 + t * 680
        y = 200 + 120 * math.sin(t * math.pi * 1.6)
        pts.append((int(x * S), int(y * S)))
    cv2.polylines(c, [np.array(pts, np.int32)], False, RED, int(2.2 * S * 800 / 80))
    return down(c, w, h)


def nested_colors() -> np.ndarray:
    """Tightly nested rings — color breaks, slivers, underlap direction."""
    w, h = 600, 600
    c = np.full((h * S, w * S, 3), 255, np.uint8)
    cx, cy = 300 * S, 300 * S
    for r, col in ((260, NAVY), (200, GOLD), (140, BLUE), (80, GREEN), (30, RED)):
        cv2.circle(c, (cx, cy), r * S, col, -1)
    return down(c, w, h)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, img in (("serif_text", serif_text()),
                      ("curved_ribbon", curved_ribbon()),
                      ("nested_colors", nested_colors())):
        cv2.imwrite(str(OUT / f"{name}.png"), img)
        print("wrote", OUT / f"{name}.png")


if __name__ == "__main__":
    main()
