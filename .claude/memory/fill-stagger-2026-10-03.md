---
name: fill-stagger-2026-10-03
description: "2026-10-03 — `fillStagger` (row stagger) built OFF for the shape builder: the JS fill cut every row evenly, so 94% of needle holes stood under the row before's; now the Python fill's shifted grid, row for row, +7% stitches, a line of dashes left beside straight edges; how a bit-exact proof was wrong"
metadata:
  type: project
---

# Row stagger for the browser fill — 2026-10-03

**What was open.** Quality review 2026-09-08 §4, second bullet, the half
`fillColumns` did not close: `src/fill.js` cut every row into equal stitches
from the row's own end, so rows of one length were cut at the same places.
On ten manual-lane designs under every preset, 94.3% of the holes between a
row's ends had a hole of the next row within 0.3 mm and 86.5% headed three
in a line. 90% on a circle: not only squares.

**What is built (OFF).** `tatamiFill({ stagger, minStitch, splitTol })` in
`src/fill.js`, and `fillStagger` on `buildQualityDesign` for the COVER fill
(not the underlay, as in Python). One grid for the fill, a stitch apart,
shifted through a cycle of 4 rows in the order 0, 2, 1, 3; a point kept only
1 mm or more from both ends; a step left over a stitch by more than a micron
cut in equal parts, counted from the end the thread comes from.
`FILL_STAGGERS` and `MIN_STITCH_MM` are `machine.py`'s (wire test),
`SPLIT_TOLERANCE_MM` is `stitches.py`'s (its own test); the pitch is the
lane's own 4 mm stitch. Only the holes BETWEEN a row's ends move. After: 6
holes of 148,477 head three in a line. Cost: +6.9% stitches (4.70 a row to
5.12), stitches down to 1 mm at the edge, no cut added.
Doc and sheet: `docs/renders/fill-stagger-2026-10-03/`. Tool:
`tools/fill-stagger-census.mjs`.

**What it leaves.** 7.5% of holes still have one under them, and 95.6% of
those sit 1.5 to 2.6 mm from a row's end: along a straight edge, a pair of
holes every four rows, a line of dashes beside the edge. Only where the edge
is off the grid (a preset's pull compensation moves it). Python's fill does
the same. Kept, and stated for the flip.

**Why:** Kent's flip ("Waiting on Kent" 24). Not sewn from this lane. The
lettering builder's fill is not staggered and does not ship either
(`wideColumnFill`, off by Kent's ruling 2026-09-11, no Studio caller: 8,500
lettering builds, no fill row). A session sent to plumb the stagger there
measured that first and stopped (Kent's call 2026-10-03). It goes in with
whatever flips that flag.

**Its audit held nine claims of eleven.** Failed: "equal to the last bit"
(my proof sorted rows and sewed them all left to right, and never aimed a
row at the tolerance) and "no stitch under the shortest is added" (false for
a builder asked for a stitch under 2 mm). Both fixed; the second proof is in
thread order, 51,760 rows, and fails the audited commit on 997.

**How to apply:**

- A proof holds for what it was given. Compare in the order the thing is
  made, aim cases a hair either side of every threshold the rule has, and
  run the new proof on the known-wrong code to see it fail.
- A mechanism is not a place. I explained the 7.5% and stopped; the auditor
  asked where they are and found the line of dashes. Measure where a
  remainder lies before calling it scattered.
- Count a channel across THREE rows. Two in a line is the rule (a halved
  step lands by the next row's grid point); three is the defect.
- Print the count before writing "none". The table said 0.0%; it was 6.
- Read what the other engine already paid for before porting it, and port
  its SIZE too: I took the idea of a split tolerance and not the micron.
- A change that moves only part of a walk has a cheap, complete test: take
  that part out of both and compare the rest point for point.
- An option that is a count must refuse a flag: `stagger: true` was a cycle
  of one row, a grid with no shift.
- With other sessions live in the same file: tell them the exact lines, and
  put new tests in a new file.
- Before taking a rule to a second builder, run the PRODUCT's own call and
  count how often the path runs. `fillFromGeom` reads as live code and this
  note called it a gap; it was behind a flag ruled off three weeks earlier.
  Wrap `fill.tatamiFill`, build with `generate.js`'s options, count: 0.

Related: [[fill-columns-2026-10-03]], [[lock-stitches-2026-10-03]].
