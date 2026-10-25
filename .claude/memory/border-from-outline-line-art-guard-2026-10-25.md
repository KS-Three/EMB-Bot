---
name: border-from-outline-line-art-guard-2026-10-25
description: border_from_outline's live false positive is Bridge's hairline bowl drawing; guard `border_from_outline_line_art_guard` (Kent flipped ON 10-25) = hairline AND leaves strokes. Thinness alone kills Machine's frame (pro widens it); dropped alone kills MFab. Pro's Bridge art had NO drawing.
metadata:
  type: project
---

Task 9, 2026-10-25. Guard in `digitizer_core/art_outline.py`
(`line_art_reading`, flag `cfg.border_from_outline_line_art_guard`, built
OFF in #1078, ON since the flip below),
tests `tests/test_outline_line_art_guard.py`, tool `tools/outline_census.py`
(`measure --line-art-guard`, `defects`, `--guard` arms).

- **The pro has no bowl to compare.** His BMP shows the art he digitized:
  redrawn (script "Bridge", orange text, an anchor with no waves). Both his
  files (63.3 / 76.6 mm) carry no drawing. So the guard is OUR construction's
  limit, not his rule. His wheel rim reads BORDER (a closed satin loop on the
  disc edge, 1.89 / 2.14 mm); ours SATIN 2.7 / 1.3. The flag never reads the
  wheel (reach 0.67-0.71), so OFF = ON = guard there.
- **The rule:** line art = fill share (opening by MIN_FILL_WIDTH_MM / 2) under
  0.5 AND dropped (beyond the loop width of every looped hole, too thin to
  fill) at least 0.02. Bridge 0.09-0.34 / 0.045-0.066; keylines 0.74-0.98;
  Machine's frame 0.00 / 0.000.
- **Measured negatives (don't rebuild them):** thinness alone (fill share,
  2A/P, band < floor) kills To-a-T Machine's 0.8 mm hexagon frame, which the
  pro widens to a 2.0-2.3 mm BORDER on all four Machine/To-a-T files (census
  kappa 0.76 -> 0.75 on 14 jobs). Dropped alone fires on MFab hat from the
  committed crop art (0.038, slivers on the keyline's outer edge). Skeleton
  free ends: Becker's keylines carry 6-10 spurs, no gap. The brief's example
  class (band fraction 0.67-0.71) is the WHEEL: the bowl reads 0.99-1.00.
- **Numbers:** census kappa 0.76 -> 0.85 (10 jobs; >= 4 mm 0.73 -> 0.84),
  0.76 -> 0.84 with the four Machine jobs (their borders kept). Bowl window,
  rays/fans/pinholes: hat OFF 1/1/1, ON 22/10/3, guard 1/1/1; LC ON 21/9/1.
  Guard ON: Bridge hat + LC DST = flag-OFF bytes; Becker hat small, MFab hat,
  Fremont hat = today's ON bytes. At 90 and 110 mm the rule reads no outline
  on Bridge at all: the false positive lives at the pro's two widths.
- The bowl's bodies include the anchor (black, the outline's own colour) in
  the LC: ON loops it into a bloated blob.

- **Kent flipped it ON 2026-10-25** ("Flip it ON", from #1078's bowl renders),
  in the flip PR off `claude/flip-line-art-guard`. `PRE_FLIP` pins it False.
  No pin moved back: every test #1070 re-pinned holds `border_from_outline`
  OFF, where the guard is inert, and no Bridge test pinned the #1070 bytes.

**Why:** the defect was live on main from #1070 until the flip.
**How to apply:** read a "thin outline" claim against Machine's frame before
building on line weight. Related: [[border-from-outline-2026-10-24]],
[[flip-sheet-wave2-2026-10-24]], [[layout-judged-in-preview-2026-10-22]].
