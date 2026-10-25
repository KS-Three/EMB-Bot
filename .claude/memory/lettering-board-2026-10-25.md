---
name: lettering-board-2026-10-25
description: tools/lettering_board.py is the ONE board a lettering PR quotes -- ours beside the pro by job and drawn letter height (<4, 4-6, 6-10, 10+), five figures, n/a with a reason; baseline on main defaults is docs/scoreboards/lettering-board-2026-10-25.md; `--compare A.json B.json` is the delta
metadata:
  type: project
---

`digitizer/tools/lettering_board.py` (2026-10-25, no engine change). Run it, then
quote `--compare before.json after.json` in the PR instead of hand-picked numbers.
Baseline: `docs/scoreboards/lettering-board-2026-10-25.{md,json}`, engine `a7a7259f`
(main defaults; #1042 / #1048 landed after, both OFF), 16 pairs, 42 lines.

**What it reads.** Lines are PINNED in `testdata/lettering_board_lines.json` (text,
box in OUR frame, drawn height, the `word_legibility` words). Per line and file, the
same code on `ours.dst` and the pro's file: `small_text_floor_census` locates and
picks the thread, `column_harness.census` counts columns, `letter_band.crosses_xy`
gives the mean satin width, `trim_classes` the cuts INSIDE one letter (never a hop
between letters, never a colour change), `word_legibility` the chance-corrected cc.
Bands come from the DRAWN height, so a flag that grows small text cannot move a line
between cells and `--compare` stays aligned. A cell pools only lines BOTH files have a
figure for and says `(n/of)`; anything else is `n/a` with its reason, never 0.

**Baseline (ours / pro):** <4 mm: columns 23 / 163, stitches 3,080 / 4,504, cc +1.00 /
+0.92 (5 of 15 lines). 4-6: columns 208 / 181. 6-10: columns 334 / 291, trims 36 / 6.
10+: columns 336 / 206, trims 66 / 14, stitches 35,377 / 25,277, width 2.19 / 3.13,
cc +0.36 / +0.48. The <4 gap is the small-text floor ([[small-text-floor-2026-10-24]]);
the 10+ trims are Becker's and MFab's.

**Traps found building it (each cost a run):**
- The floor census's search box (1.5 x drawn height) is 27 mm for an 18 mm word: the
  badge outline then sits INSIDE the box, is not dropped as a frame touching the edge,
  and wins the "most thread in letter-like pieces" vote -- MFab's MFAB read 39 mm.
  Slack is capped at 4 mm; ours then reads 18.2. The pro's MFAB (a white keyline) reads
  8.65 and is n/a, so the cell is ours alone. `--compare` showed the change was local.
- Golden Tee is LEFT OFF (`left_off` in the JSON): GT and GOLF returned the same pro
  block. Bridge Bar's pro files are not on this machine, so it is listed, not scored.
- A pro's TRIM count must come from a DST: Becker's beanie has only a PES, so its trims
  are n/a (PES reports a trim at every jump).
- `design_from_pes(ours.dst)` gives the same cc as the plan's own design (Becker hat
  large: BECKER +0.21 / +1.00, MARINE +0.00 / +1.00, identical to `word_legibility`'s
  own run), so the board reads the cache, not a second pipeline.
- `resolve_pair` inside the patched `border_census.find_pair` recursed; pass the real finder.

**How to apply.** `--cache DIR` is for ONE flag set (it records it and refuses another);
a PR runs main's defaults once and its flags once, then `--compare`. Pin words in
`word_legibility_words.json` to light up cc for Gaulke, Drone and Tires (n/a today:
no words pinned). A new pair joins by a row in `border_census.PAIRS` and its lines in
the JSON (`--propose SLUG` prints the tagger's rows). cc is coarse (a whole step on one
letter); read `sewn mm` beside `drawn mm` before quoting a cell. Related:
[[word-legibility-instrument-2026-10-24]], [[lettering-5-10mm-band-2026-10-23]],
[[layout-judged-in-preview-2026-10-22]].
