# Row stagger for the browser fill (2026-10-03)

`fillStagger: true` on `buildQualityDesign` puts the needle holes of a
shape's cover fill on one shared grid, shifted row by row. It is **default
OFF**: nothing a customer exports changes until Kent flips it. Nothing here
has been sewn.

One sheet: [`sheet.svg`](sheet.svg). Three patches of fill, as shipped on the
left and staggered on the right. One dot is a needle penetration, one faint
line a row. The rows are drawn 0.4 mm apart so that they can be told apart;
the engine's own are 0.15 mm.

## What was wrong

`src/fill.js` cuts every row into equal stitches from the row's own end. Two
rows of the same length are cut at the same places, so on any shape with
straight sides the holes of one row stand straight under the holes of the
row before. On the sheet a rectangle's holes are seven straight lines and a
circle's are arcs. Light runs down those lines. `stage6_fill.py`'s docstring
calls it the single most recognisable mark of a naive scanline fill, and
quality review 2026-09-08 §4 named it for this lane: manual draw, basic
shapes, SVG import and the flatten lane.

The Python engine does not do it. Its rows share one grid, and each row is
shifted along it.

## The rule

A port of `_stagger_slots` and `_row_points_at_phase`, and of the
`split_long_moves` the Python fill then runs over its rows.

- **One grid for the whole fill**, a stitch apart along the rows.
- **Each row is shifted along it** by its slot in a cycle of four rows, a
  quarter of a stitch a slot. The slots run 0, 2, 1, 3 and not 0, 1, 2, 3: a
  shift that walks one notch a row lines the holes up along a diagonal, and
  the channel is still there, tilted.
- **A grid point is sewn only when it is 1 mm or more from both ends of the
  row.** The grid is the fill's and not the row's, so its first point inside
  a row is any fraction of a stitch past the edge, and sewn it would put the
  needle down beside the hole it has just made.
- **A step that this leaves longer than a stitch is cut in equal parts**,
  counted from the end the thread comes from. "Longer" means by more than a
  micron: a step a hair over a stitch is a stitch.
- **A row's two ends do not move.** They are on the outline, and they are
  the edge.
- **Nothing else moves either**: no turn, no run along a rim, no float, no
  cut, and not the order of anything. Take the holes between the rows' ends
  out of a staggered fill and it is the fill as shipped, point for point.
  That is a test, over both walks.
- **The cover fill only.** The underlay's rows are 2 mm and more apart and
  lie under the cover. The Python engine does not stagger its underlay
  either.

The numbers are the Python engine's: `FILL_STAGGERS` 4 and `MIN_STITCH_MM`
1.0 (`machine.py`, held equal by the wire test) and the micron,
`SPLIT_TOLERANCE_MM` (`stitches.py`, held by a test of its own). The grid's
pitch is this lane's own stitch length, 4 mm.

**The JS row is the Python row.** On 51,760 rows, half of them sewn right to
left (a stitch of 2.5 to 6 mm, cycles of 1 to 8 rows, and rows built to sit
a hair either side of the tolerance), the holes `tatamiFill` returns are the
ones the Python fill makes (`_row_points`, then `split_long_moves`), in the
order the thread runs: 345,858 penetrations, equal to the last bit. That is
the second proof. The first compared 32,000 rows sorted and all sewn left to
right, said the same thing, and was wrong twice: see the audit below.

*(measured 2026-10-03 — a throwaway script against both engines)*

Two limits of the rule, found by the audit and now written down:

- **The 1 mm floor holds where a stitch is at least 2 mm.** A step between
  one stitch and one stitch plus 1 mm is halved, so with a builder asked for
  a stitch under 2 mm the halves come out under 1 mm. Never under half a
  stitch, which is as far down as an even cut goes too, but far more of
  them: in the audit's 54 builds at a 1.5 mm stitch, 34,458 steps of 0.75 to
  1.0 mm where the shipped fill has 306. The default is 4 mm and no Studio
  caller asks for less.
- **A grid point exactly 1 mm from a row's end falls either way on the last
  bit**, in both engines. It falls the same way all along a straight edge,
  so nothing shows. It is common on a drawing in round numbers with no
  preset (1,988 of 66,768 rows of the audit's 40 mm squares), and it can
  fall differently at 0 and at 90 degrees for the same drawing.

## What it does

A **hole** here is a penetration between a row's two ends. The ends are the
shape's edge, and stand in line wherever the edge is straight. **In line** is
within 0.3 mm along the row.

Left chest, the pique preset, underlay on, `fillColumns` off:

| design | holes | with one under it: off | on | three in a line: off | on | stitches off | on | more |
|---|---|---|---|---|---|---|---|---|
| Square, 40 mm | 2,710 | 99.6% | 4.9% | 99.3% | 0.0% | 3,331 | 3,399 | +2.04% |
| Bar, 40 x 8 mm | 580 | 98.3% | 5.0% | 96.6% | 0.0% | 744 | 759 | +2.02% |
| Circle, 30 mm | 1,120 | 95.6% | 5.3% | 90.3% | 0.0% | 1,574 | 1,677 | +6.54% |
| Star, 40 mm | 801 | 81.1% | 7.9% | 56.3% | 0.0% | 1,445 | 1,567 | +8.44% |
| Triangle, 10 mm | 66 | 93.9% | 21.7% | 54.5% | 0.0% | 230 | 256 | +11.30% |
| Badge, two cut-outs, 40 mm | 2,390 | 99.0% | 6.8% | 97.9% | 0.0% | 3,149 | 3,316 | +5.30% |
| Ring (an O), 40 mm | 1,345 | 90.6% | 8.2% | 75.3% | 0.0% | 2,129 | 2,342 | +10.00% |
| Badge, 36 holes, 60 mm | 4,563 | 88.0% | 9.4% | 71.2% | 0.0% | 8,222 | 9,077 | +10.40% |
| Three squares apart, one colour | 2,070 | 99.3% | 9.7% | 98.6% | 0.0% | 3,015 | 3,120 | +3.48% |
| Twelve 6 mm dots, one colour | 416 | 97.1% | 19.5% | 94.2% | 0.0% | 1,590 | 1,775 | +11.64% |

The same ten designs under every preset and under none, 80 builds a row:

| `fillColumns` | holes off | on | with one under it: off | on | three in a line: off | on | stitches | stitches a row: off | on | cuts off | on |
|---|---|---|---|---|---|---|---|---|---|---|---|
| off | 133,306 | 148,477 | 94.3% | 7.5% | 86.5% | 0.0% (6 holes) | +6.93% | 4.70 | 5.12 | 176 | 176 |
| on | 133,850 | 149,021 | 94.2% | 7.5% | 86.3% | 0.0% (11 holes) | +6.69% | 4.71 | 5.14 | 144 | 144 |

*(measured 2026-10-03 with `node tools/fill-stagger-census.mjs`, which also draws the sheet with `--sheet`)*

- **As shipped, nineteen holes in twenty have a hole straight under them,
  and nearly nine in ten are the head of three in a line.** Not only on
  squares: 90% on a circle, 56% on a five-pointed star.
- **Staggered, 6 holes of 148,477 are the head of three in a line.** All six
  are on rows about one stitch long (3.8 to 4.9 mm), at a star's tip or the
  cap of a 6 mm dot: the grid has no point there with room on both sides, so
  the row is cut in half, and three such rows running put their middles in
  line. With `fillColumns` on the count is 11, and includes the column walk's
  own runs along a row.
- **The 7.5% that still have one under them are not scattered.** See the next
  section.

## What is left: a line of dashes beside a straight edge

A row's first or last step can be longer than a stitch, because the grid
point that would have shortened it was within 1 mm of the edge and was not
sewn. That step is cut in half, and the half lands within 0.3 mm of the next
row's first grid hole. Of the 11,083 holes that still have one under them,
95.6% are 1.5 to 2.6 mm from an end of their own row.

Each is one pair, with nothing above or below it. But along a straight edge
the same thing happens at the same place every cycle. One 40 mm square:

| preset | rows | pairs | rows to a pair | from the nearer edge, median |
|---|---|---|---|---|
| none | 267 | 0 | - | - |
| structured_cap | 272 | 136 | 2.0 | 2.20 mm |
| pique_knit | 271 | 136 | 2.0 | 2.15 mm |
| jersey_tee | 272 | 136 | 2.0 | 2.18 mm |
| fleece_sweatshirt | 304 | 152 | 2.0 | 2.25 mm |
| canvas_tote | 270 | 136 | 2.0 | 2.10 mm |
| terry_towel | 324 | 81 | 4.0 | 2.30 mm |
| woven_dress | 270 | 136 | 2.0 | 2.10 mm |

*(measured 2026-10-03 with `node tools/fill-stagger-census.mjs`)*

- **Under a preset, both edges the rows end on carry one**: a pair of holes
  every four rows, about 2.2 mm inside the edge, the whole length of the
  edge. Terry has it on one edge. That is a line of dashes parallel to the
  edge.
- **With no preset there is none.** The square's edges then sit on the grid
  and no first step is long. A preset's pull compensation moves the edge off
  it. So it turns on where an edge falls, not on the shape.
- **As shipped that line is solid, and there is one every 4 mm across the
  whole fill.** This is what is left of it: half the rows, at one distance
  from each straight edge.
- **The Python fill does the same.** The audit ran its rows: a 40 mm span,
  267 rows, 66 pairs at 1.6 mm from the edge at Python's own 3 mm stitch, 67
  at 2.1 or 2.3 mm at 4 mm, none with the edge on a grid multiple.
- **Whether it reads on cloth needs a sew-out.** Nothing on a screen settles
  it.

## What it costs

- **Stitches: +6.9% over the set.** Under pique, +2% on a plain 40 mm square
  and +10% to +12% on a shape in small pieces (36 holes, 6 mm dots, a 10 mm
  triangle). A row
  cut evenly needs the fewest stitches there are. A row on a grid opens and
  closes on a part stitch: 4.70 stitches a row become 5.12, and short rows
  feel it most. The audit's wider sweep (12,880 designs): the median design
  +7.5%, nine in ten under +11.8%, the worst +29%.
- **Shorter stitches at the edge.** With `fillColumns` off, the shortest
  stitch along a row goes from 2.00 mm to 1.00 mm, and stitches under 2 mm
  from none to 9.5%. That is the 1 mm floor at work, the Python lane's
  number. With `fillColumns` on the same figure reads 0.00 mm before and
  after: the column walk's own runs along a row already put holes between a
  row's own, and the stagger does not add to them.
- **No cut is added, no float, no jump.** 176 cuts before and after, 144 with
  `fillColumns`. The design's size does not move.

## What an independent audit found

An agent with its own reader, written from the rule as stated and handed the
claims as claims.

- **What held:** flag off identical to the commit before and to `main` on
  12,880 shape designs with `fillColumns` off and on, and on 7,074 direct
  fills; with the holes between row ends taken out, the same walk in all of
  them and in 25,760 builds' record streams (cuts, jumps, colours, size,
  spans); every row on the reader's own grid, 6.1 million rows with
  `fillColumns` off and as many with it on; the in-line counts above,
  re-derived; no row given a neighbour's shift, to
  offsets of a hundred million pixels; the underlay untouched; after
  rounding to 0.1 mm no stitch of no length and no stitch under 0.5 mm that
  the shipped stream does not have.
- **What did not: "equal to the last bit".** Six rows of 39,979 were one ulp
  off, all sewn right to left: Python cuts a long step from the end the
  thread comes from. And Python cuts only when a step is over a stitch by
  more than a micron, where this cut at a billionth of a stitch: one row of
  the 12.2 million was halved here and would not have been there. My proof
  had sorted every row and never aimed a row at the tolerance.
- **And "no stitch under the shortest is added".** True at the default. With
  a builder asked for a 1.5 mm stitch, stitches under 1 mm went from 29,852
  to 64,004. That one is a limit of the rule and not a slip in the port. My
  first answer was to take the shortest as half a stitch there, and it
  failed the second look: the floor did not move (a halved step was never
  under half a stitch) and it made a third more short stitches, 45,552
  against 34,458. It is taken out, and the claim now carries its limit.
- **Where the 7.5% are.** I had written them off as "once, with nothing above
  or below". The audit asked where, and found the line of dashes.
- **Three smaller things**, two caught while writing tests for the audit's
  list and one from its report, all corrected: a table that printed "0.0%"
  for six holes; `stagger: 1e9` building a table of a thousand million
  slots; and `stagger: true` meaning a cycle of one row, which is a grid
  with no shift at all.

The first failure is fixed and the fix is a test. The second is a limit,
stated above and tested as one. The row proof above is the one made after.

**The second look, at the fixes.** Its own 39,979 rows and a band of 12,005
more, aimed a hair either side of every threshold the rule has: all
bit-identical with Python (the first head: 39,973 and 11,014). No row halved
that Python would not halve, at design size or at offsets of a hundred
million pixels. Flag off still identical on all 12,880 designs. Of 25,760
builds with the flag on, 18 differ from the first head: 16 by one record
moved 0.1 mm (a one-ulp half that sat on a rounding edge) and 2 by the one
row in the tolerance band. The half-a-stitch change came out after that
look, on its advice; the line that decides the clearance is again, to the
character, the one the first round read.

*(measured 2026-10-03 — the auditor's sweeps, two rounds)*

## Seen, not changed

- **The line of dashes.** It is the Python rule's, row for row, and the two
  engines keep the same rule until a sew-out says otherwise. A cure would be
  a new rule in both.
- **The lettering builder's fill is not staggered, and does not ship.** A
  letter too wide for satin is filled by `src/satinplay.js` only under
  `wideColumnFill`, which is off by Kent's ruling of 2026-09-11 and which no
  Studio caller passes. If that flag is ever turned on, its fill has the
  same lines in it.
- **The shape lane's stitch is 4 mm and the Python fill's is 3 mm.** The grid
  uses the lane's own. Changing it would be a third more stitches in every
  fill and a different decision.
- **A row shorter than 0.5 mm.** The Python fill sews it as one penetration
  at its middle. That moves a row's ends, which both walks are built on, so
  it is not ported: such a row keeps its two ends, as it does today.
- **The column walk's runs along a row are not staggered.** They are travel,
  laid under or over a row that is itself staggered: 3,007 of them in the
  audit's sweep, each on one row.

## Safety

- **Off is byte-identical.** 1,500 recorded designs hash the same before and
  after the change, and the audit's 12,880 the same. In the suite every
  engine test that existed passes unchanged, and guards hold `stagger` off,
  zero and absent to one fill and `fillStagger: false` to no flag.
- **Take the holes between the rows' ends out and it is the shipped walk**,
  point for point: 60 random shapes, both walks, center-out and not.
- **Engine suite 681 of 681.** 21 new tests; 14 were watched failing before
  the code that passes them, the other 7 are guards that hold with it and
  without.

## What a flip needs

- `app/src/lib/generate.js` passes `fillStagger: true` at its three
  `buildQualityDesign` call sites.
- Every shape snapshot re-pins: every fill row with room for a hole changes.
- It stacks with the other two flags waiting on the same lane. `fillColumns`
  decides where the thread travels and `ties` locks its ends; neither moves a
  hole between a row's ends, and this moves nothing else.

## The open question: Kent's

Flip `fillStagger` on for the browser shape lanes?

For: every fill this lane exports has the lines in it, and the Python lane's
fills do not. It is the Python rule, row for row.

Against: about 7% more stitches, stitches as short as 1 mm where a row meets
the edge, and a line of dashes about 2 mm inside a straight edge where there
were solid lines across the whole fill. Not sewn from this lane. The honest
choices: flip now, or sew one square first and look for the dashes.

MASTER_SCOPE "Waiting on Kent" 24.
