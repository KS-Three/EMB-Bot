---
name: underfill-outer-rim-2026-10-25
description: Where a ring hosts its own silhouette under-fill (MFab's black band, Fremont's white ground) the pro rims the fill's WHOLE outer edge with satin in the fill's colour (MFab one closed column 1.86-1.94 mm; Fremont the same edge in two passes 1.39-1.73); ours sewed none of it (rim share 0.0). Built OFF as `silhouette_underfill_rim`, 1.75 mm, keyline_runs' loop with #1093's pivot.
metadata:
  type: project
---

2026-10-25, lane `diagonal-junction-letters-62899f`, branch
`claude/underfill-outer-rim`. Flag `cfg.silhouette_underfill_rim` (OFF),
`stage6_border.underfill_rim_runs` / `underfill_rim_after`, one call in
`stage7_sequence` after `stitch_one`, tests `tests/test_underfill_rim.py`, a
flip-sheet row. Numbers and crops: the PR body.

**Reader** (scratch `outer_rim.py`, quoted in the PR): the silhouette from the
file's OWN stitches (segments drawn, closed 1.5 mm, holes filled); a rim cross
has one end within 0.5 mm of the outer contour, the other 0.6-5 mm in, within
35 deg of square; a column is rim crosses in one needle-down run. No carry,
no snap: one rule on both files.

**His rule.** 16 pairs read. Full rim only where a ring hosts its own
under-fill: MFab hat/LC rim share 1.00, one closed column, 1.94 / 1.86 mm, CV
0.03, 6 deg off square, block 0 (the fill's own block, sewn after it);
Fremont hat/patch 1.00 in the WHITE ground's colour (blocks 3/5, 4/6 are
#f0f0f0 like block 0), two passes, 1.39-1.73. Becker's beanie (a LETTER
hosts) has its ring as the satin (0.51 of the outer edge, knockdown block
excluded); Drone (he does not under-fill) 0.25; Gaulke, Tires, Proseal
0.12-0.26. Bridge's pro files are on G: (unread).

**Trap:** a beanie's knockdown block widens the silhouette past the design,
so its rim reads 0.0 -- exclude block 0 (`RIM_EXCL=0`) before reading.

**Open.** The Drone: `silhouette_underfill` fires there and he neither
under-fills nor rims, so the rim inherits that over-reach (the under-fill's
row against). The width is one constant (median 1.76); MFab alone would be
1.9.
