---
name: garment-size-like-pro-2026-10-26
description: The pro's per-garment placement boxes read from his stitch files - hat 113.5x64, left chest 96x76.5 (height raised 10-27 for Bridge LC, Kent), beanie 94.5x56 - against our round-inch 127x57.2 / 101.6 sq / 114.3x63.5; built OFF as `proSized` in src/garments.js; median width error 11-16% -> 1-3%. Hat height 64 vs our 57.2 is a cap-frame (gate 1) question for Kent.
metadata:
  type: project
---

2026-10-26, task 8, lane `diagonal-junction-letters-62899f`, branch
`claude/garment-size-like-pro`. `digitizer/tools/garment_size_census.py` (new),
`src/garments.js` `PRO_PLACEMENT_MM` / `placementBoxMm` / `opts.proSized` on
`fitScale`, `autoFitBoxMm`, `suggestHoop`; tests in `test/garments.test.js`.

**Census** (zip + Bridge folder, one row per design: byte-identical files and
DST/PES twins counted once; garment from the intake registry, else
`pro_intake.garment_of`; artwork aspect = its ink box, committed pairs' art
ahead of the registry's, which gives Becker's beanie the To a T art). His box
= the box that, auto-fitting OUR artwork's aspect, best reproduces his widths
(median relative error on a 0.5 mm grid). Searched on HIS file's aspect the
LC box reads 96 x 61.5 -- 4.8% median on our art; the art aspect is the one
that matters.

**Result** (auto-fit OFF -> ON, median |width error| vs his):
hat 11.2% -> 1.1% (0 -> 8 of 12 within 5%), LC 13.5% -> 0.8% (0 -> 4/7),
beanie 15.5% -> 3.3% (1 -> 4/6). Today 6 of 12 hats sew SHORTER than his (57.2
cap vs his 62-64) and the wide ones WIDER (127 vs 114.3).

**Rows the boxes miss:** size variants (Becker hat/chest small), Fremont hat
(he sews it 22% smaller), MFab hat +8%, Bridge LC (he sews a square 76.6 where
the box gives 64.5), the two Gaulke beanies disagree (93.8 / 110.5 wide).

**LC height 64.5 -> 76.5, Kent 2026-10-27** ("Raise LC box to 76.5 tall (Recommended)"), after the Bridge census
named Bridge LC the box's one real miss (he sews 76.6 x 76.5; the box fitted 64.5 wide, -15.8%). Of the 8 paired LC
jobs two move: Bridge -15.8% -> -0.1%, and Machine's 1.385:1 art goes 89.3 -> 96.0 wide against his 89.5 (-0.2% ->
+7.3%), because a design squarer than 1.255:1 stops being height-limited. Median |width error| stays 0.84%; rows over
5% stay three (Becker chest small +25.5%, Gaulke Plowing LC +7.4%, now Machine). Wider LCs are width-limited: no move.

**Traps:** a lane has no `scratch_kent` -- find the registry up the tree;
the registry spells job folders differently from the zip ("To a T-Becker
Beanies" vs "To a T:Becker Beanies", a leading space on " C Gaulke Plowing").
Main's MEMORY.md was 4 chars OVER its ceiling on 2026-10-26: reclaimed here.
