---
name: fill-stagger-2026-10-03
description: "2026-10-03 — `fillStagger` (row stagger) built OFF for the shape builder: the JS fill cut every row evenly, so 94% of needle holes stood under the row before's; now the Python fill's shifted grid, row for row, +7% stitches; how to count a channel and prove a port"
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

**What is built (OFF).** `tatamiFill({ stagger, minStitch })` in
`src/fill.js`, and `fillStagger` on `buildQualityDesign` for the COVER fill
(not the underlay, as in Python). One grid for the fill, a stitch apart,
shifted through a cycle of 4 rows in the order 0, 2, 1, 3; a point kept only
1 mm or more from both ends; a step left over a stitch cut in equal parts.
`FILL_STAGGERS` and `MIN_STITCH_MM` are `machine.py`'s (wire test); the
pitch is the lane's own 4 mm stitch. Only the holes BETWEEN a row's ends
move. After: 6 holes of 148,477 head three in a line. Cost: +6.9% stitches
(4.70 a row to 5.12), stitches down to 1 mm at the edge, no cut added.
Doc and sheet: `docs/renders/fill-stagger-2026-10-03/`. Tool:
`tools/fill-stagger-census.mjs`.

**Why:** Kent's flip ("Waiting on Kent" 24). Not sewn from this lane. Not
covered: the fill under a letter too wide for satin (`satinplay.js`).

**How to apply:**

- Count a channel across THREE rows. My first test asked that no hole have
  one under it, and the exact port failed it at 4 to 6%: a halved step lands
  within half a millimetre of the next row's grid point by the rule itself.
  Two in a line is the rule. Three is the defect.
- Print the count before writing "none". The table said 0.0%; it was 6.
- A row-level port can be PROVEN, not sampled: make random rows in Python,
  sew them in JS, compare to the bit (32,000 rows, 205,047 holes, equal).
  Do that before any metric; then the metric is about the rule, not the port.
- Read what the other engine already paid for before porting it: the slot
  order (0, 2, 1, 3, not 0, 1, 2, 3) and the tolerance on "longer than a
  stitch" (`split_long_moves`, defect 25) are both written down in Python.
- A change that moves only part of a walk has a cheap, complete test: take
  that part out of both and compare the rest point for point.
- With other sessions live in the same file: tell them the exact lines, and
  put new tests in a new file.

Related: [[fill-columns-2026-10-03]], [[lock-stitches-2026-10-03]].
