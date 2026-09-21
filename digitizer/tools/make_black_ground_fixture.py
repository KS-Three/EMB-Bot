#!/usr/bin/env python
"""Generate `testdata/black_ground_holes.png` — a BLACK-ground design whose
enclosed counters are background-coloured, and which `strip_letterbox` can
never touch.

## Why this fixture exists

`cfg.enclosed_by_garment` needs a design where the background colour is (a)
known and (b) NOT white, so the tests can show `prep` carrying the flood
colour rather than assuming one. That job was done by
`photo/logo_gaulke_roofing.png`, whose pure-black letterbox bars were read as
the background — and it did the job only BY ACCIDENT of those bars. When
`strip_letterbox` went default-ON (2026-09-14) the bars were cropped, the
design became BACKGROUND_ABSENT, its 46 enclosed holes went to zero, and the
tests lost the property they were testing rather than the assertion changing.

DOCTRINE's rule for that situation is explicit: re-point at a fixture that
still carries the property, never at whatever the engine now happens to emit.
This is that fixture.

## Why it is letterbox-PROOF by construction

The ground is black on ALL FOUR sides. `letterbox.detect_letterbox`'s
governing rule is semantic rather than tuned — **letterboxing is
ONE-DIMENSIONAL**, because bars are added on a single axis to fit a different
aspect ratio — so a uniform border on both axes is a MARGIN and is never
stripped. That is the same rule that saves `bg_uncertain.png`. So this
fixture cannot lose its background to the same change twice, which is exactly
what made the gaulke arrangement fragile.

Run from digitizer/:  .venv/Scripts/python tools/make_black_ground_fixture.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "testdata" / "black_ground_holes.png"

BLACK = (0, 0, 0)
CREAM = (232, 236, 240)   # BGR — a light mark, far from the ground in dE00


# The gaulke arrangement this replaces carried 46 enclosed letter bodies, and
# `test_gaulke_letter_bodies_sew_on_natural_and_stay_holes_on_black` asserts
# `>= 40` of them — a SCALE property, not just the rule. A two-hole fixture
# would have forced that assertion down to `>= 2`, which is re-pointing at
# what the engine emits by another name. So the grid carries 40.
COLS, ROWS = 8, 5
ENCLOSED_BODIES = COLS * ROWS


def build() -> np.ndarray:
    # 900 px wide against the tests' 80 mm target is 11.25 px/mm, so the
    # 30 px counters below land at 2.7 mm — clear of the 1.5 mm
    # `min_detail_mm` floor that would otherwise absorb them before they
    # could be tagged.
    h, w = 560, 900
    img = np.full((h, w, 3), BLACK, np.uint8)

    # 40 letter-body counters: a light mark with a black hole in it, the
    # shape `enclosed_background` is written about. The 40 px black margin on
    # ALL FOUR sides is what makes the ground unambiguous AND makes the
    # border a margin rather than letterboxing.
    cell_w, cell_h = (w - 80) // COLS, (h - 80) // ROWS
    for r in range(ROWS):
        for c in range(COLS):
            x0 = 40 + c * cell_w + 8
            y0 = 40 + r * cell_h + 8
            x1, y1 = x0 + cell_w - 22, y0 + cell_h - 22
            cv2.rectangle(img, (x0, y0), (x1, y1), CREAM, -1)
            cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
            cv2.rectangle(img, (cx - 15, cy - 14), (cx + 15, cy + 14), BLACK, -1)
    return img


def main() -> int:
    img = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(OUT), img)
    print("wrote", OUT, img.shape)

    sys.path.insert(0, str(ROOT))
    from digitizer_core.config import PipelineConfig          # noqa: E402
    from digitizer_core.letterbox import detect_letterbox     # noqa: E402
    from digitizer_core.stage1_prep import prep               # noqa: E402

    rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    bars = detect_letterbox(rgb)
    print("detect_letterbox -> (top, bottom, left, right) =", bars,
          "(all zero means nothing is stripped)")

    for flag in (False, True):
        p = prep(OUT, PipelineConfig(target_width_mm=80.0, strip_letterbox=flag))
        enclosed = None if p.enclosed_mask is None else int(p.enclosed_mask.sum())
        print(f"  strip_letterbox={flag!s:5s} bg_rgb={p.bg_rgb} "
              f"enclosed_px={enclosed} warnings={[w['code'] for w in p.warnings]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
