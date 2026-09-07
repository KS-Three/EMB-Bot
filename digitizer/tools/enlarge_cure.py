#!/usr/bin/env python
"""Does the Studio's "Make it bigger" button actually clear what it is offered for?

`app/src/ui/DigitizePanel.svelte`'s `FIX_FOR` offers exactly one cure for both
`LETTERING_TOO_SMALL` and `STITCHES_TOO_SHORT` — `target_width_mm` x 1.25,
capped at 400, deduped so the two findings never show the button twice. Nobody
had measured what a press does to the number the second finding is scored on.

Measured 2026-09-06, the ten corpus fixtures that fire `STITCHES_TOO_SHORT` at
80 mm / left_chest, swept 80 -> 100 -> 125 mm (the button once, then twice):

  * **one press cleared the finding on 1 of 10** (`drone_render`); two presses
    on 4 of 10 (`drone_render`, `summit_badge`, `gaulke_roofing`,
    `golden_tee`);
  * **it moved the fraction the WRONG WAY on 3 of 10** —
    `photo_dof_meadow` 0.36 -> 0.58 -> **0.71**, worse at every press;
    `logo_bridge_bar` 0.30 -> 0.36; `photo_sunset_backlit` 0.65 -> 0.66;
  * the satin SHAPE count rose on **every fixture** (2 -> 9, 42 -> 71), which
    is `_lettering_findings`' own "the smallest shapes regenerate at any size"
    seen from the short-step side: enlarging buys more shapes as fast as it
    widens the ones already there.

**Do not read the score column as this finding's doing.** Grades move because
several checks move at once (hoop fit, density, thread match), and 5 of the 10
sit on the clamped floor at 0 where nothing registers at all
(`tools/floor_depth.py`). The attributable columns are `frac`, `steps`,
`shapes` and whether the finding fires.

The documented root cause of the short columns is per-stroke satin routing
(`docs/superpowers/plans/2026-09-04-per-stroke-satin-routing.md`), which is
scale-invariant -- so a scale knob was never going to be the cure. Re-run this
after that lands.

    .venv/bin/python -m tools.enlarge_cure
"""
from __future__ import annotations

import sys

from digitizer_core import preflight as pf
from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import digitize

# The fixtures that fire the finding at the corpus's own 80 mm baseline.
# Not every fixture: a sweep over all 26 is ~2x this one's runtime and the
# other 16 have nothing to clear.
FIRED = (
    "photo/drone_render.png", "photo/photo_chrome_specular.png",
    "photo/photo_dof_meadow.png", "photo/photo_sunset_backlit.png",
    "photo/summit_badge.png", "photo/logo_bridge_bar.jpg",
    "photo/logo_gaulke_roofing.png", "photo/logo_golden_tee.jpg",
    "photo/logo_hotel_fremont.webp", "photo/screenshot_phone_ui_golke.jpg",
)

# The button is `Math.min(400, round(w * 1.25))`, so these are one press and
# two from the corpus baseline. Kept in step with the Svelte by hand -- if the
# multiplier moves, move these.
WIDTHS = (80.0, 100.0, 125.0)


def _one(art, width: float):
    cfg = PipelineConfig(target_width_mm=width, garment_id="left_chest")
    result, plan = digitize(art, cfg)
    rep = pf.run_preflight(result, plan, cfg, image=art)
    m = rep["metrics"]
    return (m["satin_short_fraction"], m["satin_steps"], m["satin_shapes"],
            any(f["code"] == pf.STITCHES_TOO_SHORT for f in rep["findings"]),
            rep["score"], rep["grade"])


def main(argv: list[str]) -> int:
    from tests.conftest import TESTDATA

    hdr = (f"{'fixture':40} {'mm':>5} {'frac':>5} {'steps':>6} {'shapes':>6} "
           f"{'fires':>5} {'score':>6}")
    print(hdr)
    print("-" * len(hdr))
    cleared_one = cleared_two = worse = 0
    for fx in FIRED:
        art = TESTDATA / fx
        row = {}
        for w in WIDTHS:
            try:
                row[w] = _one(art, w)
            except Exception as exc:                      # pragma: no cover
                print(f"SKIP {fx} @{w:g}: {exc}")
                continue
            r = row[w]
            print(f"{fx:40} {w:5.0f} {r[0]:5.2f} {r[1]:6} {r[2]:6} "
                  f"{'yes' if r[3] else '  -':>5} {r[4]:4} {r[5]:>1}")
            sys.stdout.flush()
        print()
        if len(row) == len(WIDTHS) and row[WIDTHS[0]][3]:
            if not row[WIDTHS[1]][3]:
                cleared_one += 1
            if not row[WIDTHS[-1]][3]:
                cleared_two += 1
            if row[WIDTHS[1]][0] > row[WIDTHS[0]][0]:
                worse += 1

    n = len(FIRED)
    print(f"one press cleared the finding on {cleared_one}/{n}; "
          f"two presses on {cleared_two}/{n}; "
          f"the fraction got WORSE on one press on {worse}/{n}")
    print("score/grade moves are NOT this finding's doing — several checks "
          "move with size, and the floored designs cannot register any of it")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
