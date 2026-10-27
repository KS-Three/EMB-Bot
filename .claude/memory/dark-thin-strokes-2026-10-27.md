---
name: dark-thin-strokes-2026-10-27
description: "2026-10-27 — HUNNY on the Pooh pot: hand lettering 21.5 dE00 from a shaded ground is absorbed by the gradient lane's merge; `keep_dark_thin_strokes` (OFF) reads it by lightness, carves only the absorbed strokes out after the merge, and the colour cap keeps the ink off its ground's thread"
metadata:
  type: project
---

# Dark thin strokes on a shaded ground — 2026-10-27

Kent's Winnie-the-Pooh cartoon (266 x 373 JPEG, Disney: never committed, no
render of it either) digitized at 80 mm hat_front sewed one letter of HUNNY and
half of another. Stage 0 says `gradient`; the pen ink reads Lab (43.7, -1.0,
20.5) on a pot at (66.1, -4.1, 18.6), 21.5 dE00 — under `MERGE_DELTAE00_THRESH`
26.0 — and 0.5-0.75 mm wide at the 8 px/mm working grid. `find_thin_ink` reads
the artwork with the flat quantiser, so a stroke only exists for it when k-means
gives it a colour; this ink's lightness tracks the shading under it and gets none
(`tools.thin_strokes`: 0 lost, same reader). Forced flat: same loss.

**Built (`thin_ink.find_dark_thin_ink`, PR from lane `claude/pooh-thin-dark-strokes`):**
a black-hat on L* with an ellipse `2 * floor_px + 1` wide (floor = `min_detail_mm`),
pixels deeper than `DARK_INK_DEPTH_L` 8.0, then the thin population's own floors
through `iter_thin_components`, a one-ground ring (2 px out, 2 px wide; share
`THIN_INK_GROUND_SHARE` within `DARK_INK_GROUND_DE00` 13.0 = the boundary-contrast
rule's local threshold, background counted against) and contrast
`DARK_INK_MIN_CONTRAST_DE00` 10.0 against the ring median. Measured on the cartoon:
letters 12.1-25.9 dE00, ripples 2.7-3.7; rings 0.97-1.00 vs outlines 0.01-0.46.
Strokes are grouped into inks (single linkage at 13.0) and snapped once.

**Two lessons that cost a run each.**
1. Taking the dark pixels out of the SEEDS foreground (the quantiser read's path)
   also took the nose and toe lines — their own regions on main — out of the
   main population: the palette medoids moved, the pot split into two threads,
   34 → 68 regions, +3,000 stitches, +31 trims. Now the read happens before
   SEEDS but the carve happens AFTER the merge, and only for strokes whose
   majority merged label is not their own (`absorbed_dark_ink`): 34 → 37
   regions, +215 stitches, +9 trims, six colours as before.
2. The colour cap (`enforce_color_cap`, max 6) drops the ink's spool as the
   smallest sewn area and remaps to the NEAREST kept colour — the pot's own
   thread. Five rescued letters sewed invisible. `meta["dark_ink"]` regions now
   remap to the nearest kept thread not lighter than the dropped spool
   (Pony 1233 here, 20 dE00 off the pot; Very Dark Brown would need "darkest",
   not built).

**Not built, Kent's call:** the letters sew as 0.5-0.75 mm columns at their
drawn size (~6-7 mm tall); the pro re-sets small text to ~4 mm satin.

**Traps.** This lane's working tree is CRLF (`core.autocrlf true`): a Python
patch must read with universal newlines and write each file's own ending, and
`grep -q $''` in the Bash tool says LF for a CRLF file. A synthetic fixture
with ONE ink colour cannot show the loss — the quantiser gives it a cluster;
the tracking pen (ink = ground − the cartoon's offset) plus five colour panels
does (`tests/test_keep_dark_thin_strokes.py`). Related: [[flip-proof-pins-2026-10-27]],
[[the-80mm-ink-link-2026-10-15]], [[small-text-floor-2026-10-24]].
