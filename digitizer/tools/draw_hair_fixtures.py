"""Draw the hairline tier's two synthetic fixtures (2026-10-12).

    python -m tools.draw_hair_fixtures            # from digitizer/

Writes, deterministically (seeded):

- `testdata/synthetic/hair_strands.png` — RGBA, 80 mm wide at 20 px/mm: a
  skin-toned oval with ~40 dark brown strands drawn over it, 0.25-0.6 mm
  wide, some crossing, a few curls under 2 mm radius. Hard-edged (no
  anti-aliasing) so stage 0 reads it as flat art and every strand is one
  colour.
- `testdata/synthetic/hair_fine.png` — the same canvas, oval, curves,
  crossings and curls as `hair_strands.png`, with the 40 strands drawn
  0.25-0.35 mm wide (median 0.30): the fixture a 60 wt gate (0.48 mm) can
  admit with margin. Hair and ground colours are `hair_strands.png`'s.
- `testdata/synthetic/thin_script.png` — RGBA, 60 mm wide: a signature-style
  looping script line, 0.3-0.5 mm strokes, one ink, transparent ground.

Both are this repo's own drawings (public repo: no photographs of people, no
client art). `STRANDS` is returned by `hair_strands()` so a test can count
drawn strands against sewn ones.
"""
from __future__ import annotations

import math
from pathlib import Path

import cv2
import numpy as np

PX_PER_MM = 20.0
OUT = Path(__file__).resolve().parents[1] / "testdata" / "synthetic"

SKIN = (224, 182, 150)      # RGB
HAIR = (58, 36, 24)         # RGB, dark brown
INK = (24, 32, 60)          # RGB, navy script


def _bezier(p0, p1, p2, p3, n=200):
    t = np.linspace(0.0, 1.0, n)[:, None]
    return ((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1
            + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)


def _curl(cx, cy, r, turns, a0, n=200):
    a = a0 + np.linspace(0.0, 2 * math.pi * turns, n)
    rr = r * (1.0 - 0.25 * np.linspace(0.0, 1.0, n))     # a gently tightening spiral
    return np.column_stack([cx + rr * np.cos(a), cy + rr * np.sin(a)])


FINE_RANGE_MM = (0.25, 0.35)    # hair_fine: median 0.30


def hair_strands(seed: int = 12, fine: bool = False):
    """-> list of (polyline mm Nx2, width mm). ~40 strands.

    `fine` keeps every curve (same crossings, same curls) and replaces the
    widths with `FINE_RANGE_MM` evenly spread over the 40 strands, in a
    seeded shuffle, so the median is exactly 0.30 mm (step 3, 2026-10-12:
    the fixture a 60 wt gate can admit with margin)."""
    rng = np.random.default_rng(seed)
    strands = []
    # Long flowing strands, falling from the crown (top) across the oval.
    for i in range(30):
        x0 = 12 + 56 * (i / 29) + rng.uniform(-1.5, 1.5)
        y0 = 8 + rng.uniform(0, 4)
        sweep = rng.uniform(-10, 10)
        wave = rng.uniform(4, 9) * (1 if i % 2 else -1)
        p0 = np.array([x0, y0])
        p1 = np.array([x0 + sweep * 0.3 + wave, y0 + 12])
        p2 = np.array([x0 + sweep * 0.8 - wave, y0 + 24])
        p3 = np.array([x0 + sweep, y0 + rng.uniform(30, 40)])
        strands.append((_bezier(p0, p1, p2, p3), float(rng.uniform(0.25, 0.6))))
    # Cross strands: shallow arcs laid across the falls, so strands cross.
    for i in range(6):
        y = 16 + 5 * i + rng.uniform(-1, 1)
        p0 = np.array([14 + rng.uniform(0, 6), y])
        p3 = np.array([66 - rng.uniform(0, 6), y + rng.uniform(-3, 3)])
        p1 = p0 + np.array([15, rng.uniform(-6, 6)])
        p2 = p3 + np.array([-15, rng.uniform(-6, 6)])
        strands.append((_bezier(p0, p1, p2, p3), float(rng.uniform(0.25, 0.45))))
    # Curls under 2 mm radius, at the ends of the falls.
    for cx, cy in ((20, 48), (36, 50), (52, 49), (63, 45)):
        r = float(rng.uniform(1.1, 1.9))
        strands.append((_curl(cx, cy, r, 1.4, rng.uniform(0, 2 * math.pi)),
                        float(rng.uniform(0.3, 0.45))))
    if fine:
        w = np.linspace(FINE_RANGE_MM[0], FINE_RANGE_MM[1], len(strands))
        np.random.default_rng(seed + 1).shuffle(w)
        strands = [(pts, float(wi)) for (pts, _w), wi in zip(strands, w)]
    return strands


def _canvas(w_mm, h_mm):
    return np.zeros((int(round(h_mm * PX_PER_MM)), int(round(w_mm * PX_PER_MM)), 4), np.uint8)


def _stroke(img, pts_mm, width_mm, rgb):
    pts = np.round(np.asarray(pts_mm) * PX_PER_MM).astype(np.int32)
    # cv2's thick line paints about one pixel wider than `thickness` (measured
    # on this fixture: 610 mm2 of hair pixels against 528 mm2 of exact
    # buffers), so ask for one less to land on the stated width.
    t = max(1, int(round(width_mm * PX_PER_MM)) - 1)
    cv2.polylines(img, [pts.reshape(-1, 1, 2)], False, (*rgb, 255), t, cv2.LINE_8)


def _stroke_exact(img, pts_mm, width_mm, rgb):
    """A stroke of the stated width, to the pixel: the exact buffer of the
    centreline, filled aliased. `_stroke`'s `cv2.polylines` can only draw an
    ODD pixel count of widths (an odd `thickness` paints as the next even
    one: 0.30 mm comes out 0.35), which is fine for the 0.25-0.6 fixture but
    would turn `hair_fine`'s 0.30 median into 0.35. `cv2.fillPoly` paints the
    boundary pixels on both sides, so the buffer is one pixel narrower."""
    from shapely.geometry import LineString
    half = max(width_mm - 1.0 / PX_PER_MM, 1.0 / PX_PER_MM) / 2.0
    poly = LineString(np.asarray(pts_mm)).buffer(half, quad_segs=8)
    for part in (poly.geoms if hasattr(poly, "geoms") else [poly]):
        ring = np.round(np.asarray(part.exterior.coords) * PX_PER_MM).astype(np.int32)
        cv2.fillPoly(img, [ring.reshape(-1, 1, 2)], (*rgb, 255), cv2.LINE_8)


def draw_hair(path: Path, fine: bool = False) -> int:
    img = _canvas(80, 62)
    cv2.ellipse(img, (int(40 * PX_PER_MM), int(32 * PX_PER_MM)),
                (int(34 * PX_PER_MM), int(27 * PX_PER_MM)), 0, 0, 360,
                (*SKIN, 255), -1, cv2.LINE_8)
    strands = hair_strands(fine=fine)
    for pts, w in strands:
        (_stroke_exact if fine else _stroke)(img, pts, w, HAIR)
    rgba = cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA)
    cv2.imwrite(str(path), rgba)
    return len(strands)


def script_strokes():
    """A looping signature line: a run of cursive loops, a capital swash,
    and an underline flourish. -> list of (polyline mm, width mm)."""
    out = []
    # Capital: a tall loop.
    t = np.linspace(0, 2 * math.pi, 240)
    cap = np.column_stack([8 + 3.5 * np.sin(t) * 0.8, 14 - 8 * np.cos(t) * 0.9 + 4])
    out.append((cap, 0.45))
    # Lowercase loops: a prolate cycloid, the classic "lll" handwriting curve.
    s = np.linspace(0, 7 * 2 * math.pi, 1400)
    x = 13 + 1.05 * s - 2.2 * np.sin(s)
    y = 18 - 3.0 * (1 - np.cos(s)) * 0.9
    out.append((np.column_stack([x, y + 3]), 0.35))
    # Underline flourish.
    out.append((_bezier(np.array([6.0, 26.0]), np.array([20.0, 31.0]),
                        np.array([40.0, 22.0]), np.array([58.0, 27.0])), 0.4))
    # A dot and a crossbar (short strokes; the bar is long enough to sew).
    out.append((np.array([[30.0, 9.5], [36.0, 9.0]]), 0.3))
    return out


def draw_script(path: Path) -> int:
    img = _canvas(62, 32)
    strokes = script_strokes()
    for pts, w in strokes:
        _stroke(img, pts, w, INK)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGBA2BGRA))
    return len(strokes)


def main(argv=None) -> None:
    import argparse

    argparse.ArgumentParser(description=__doc__.split("\n\n")[0]).parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    n = draw_hair(OUT / "hair_strands.png")
    f = draw_hair(OUT / "hair_fine.png", fine=True)
    m = draw_script(OUT / "thin_script.png")
    print(f"hair_strands.png: {n} strands; hair_fine.png: {f} strands; "
          f"thin_script.png: {m} strokes -> {OUT}")


if __name__ == "__main__":
    main()
