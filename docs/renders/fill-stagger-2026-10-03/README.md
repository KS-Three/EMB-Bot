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
- **A step that this leaves longer than a stitch is cut in equal parts.**
- **A row's two ends do not move.** They are on the outline, and they are
  the edge.
- **Nothing else moves either**: no turn, no run along a rim, no float, no
  cut, and not the order of anything. Take the holes between the rows' ends
  out of a staggered fill and it is the fill as shipped, point for point.
  That is a test, over both walks.
- **The cover fill only.** The underlay's rows are 2 mm and more apart and
  lie under the cover. The Python engine does not stagger its underlay
  either.

The two numbers are `machine.py`'s, `FILL_STAGGERS` 4 and `MIN_STITCH_MM`
1.0, and the wire test holds them equal. The grid's pitch is this lane's own
stitch length, 4 mm.

**The JS row is the Python row.** On 32,000 random rows (a stitch of 2.5 to
6 mm, cycles of 1 to 8 rows) the holes `tatamiFill` returns are the ones the
Python fill makes (`_row_points`, then `split_long_moves`): 205,047
penetrations, equal to the last bit.

*(measured 2026-10-03 — a throwaway script against both engines; the claim was handed to the audit below)*

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
- **Read "three in a line", not "one under it".** A step cut in half lands
  near the next row's grid point by the rule itself, once, with nothing above
  or below it. Those are the 7.5%.

## What it costs

- **Stitches: +6.9% over the set.** +2% on a plain 40 mm square, +10% to +12%
  on a shape in small pieces (36 holes, 6 mm dots, a 10 mm triangle). A row
  cut evenly needs the fewest stitches there are. A row on a grid opens and
  closes on a part stitch: 4.70 stitches a row become 5.12, and short rows
  feel it most.
- **Shorter stitches at the edge.** Along a row the shortest stitch goes from
  2.00 mm to 1.00 mm, and stitches under 2 mm from none to 9.5%. That is the
  1 mm floor at work, the Python lane's number.
- **No cut is added, no float, no jump.** 176 cuts before and after, 144 with
  `fillColumns`. The design's size does not move.

## Seen, not changed

- **The lettering builder's fill fallback is not staggered.** A letter too
  wide for satin is filled by `src/satinplay.js`, which calls the same
  `tatamiFill` with no stagger. It is a cover fill with the same lines in it.
  A different builder with its own snapshots; not in this change.
- **The shape lane's stitch is 4 mm and the Python fill's is 3 mm.** The grid
  uses the lane's own. Changing it would be a third more stitches in every
  fill and a different decision.
- **A row shorter than 0.5 mm.** The Python fill sews it as one penetration
  at its middle. That moves a row's ends, which both walks are built on, so
  it is not ported: such a row keeps its two ends, as it does today.

## Safety

- **Off is byte-identical.** 1,500 recorded designs hash the same before and
  after the change. In the suite every engine test that existed passes
  unchanged, and guards hold `stagger` off, zero and absent to one fill and
  `fillStagger: false` to no flag.
- **Take the holes between the rows' ends out and it is the shipped walk**,
  point for point: 60 random shapes, both walks, center-out and not.
- **Engine suite 674 of 674.** 14 new tests; 8 were watched failing before
  the change, the other 6 are guards that hold with it and without.

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

Against: about 7% more stitches, and stitches as short as 1 mm where a row
meets the edge. Not sewn from this lane.

MASTER_SCOPE "Waiting on Kent" 24.
