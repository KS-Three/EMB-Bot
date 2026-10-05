# The spine of a satin shape: before and after (2026-10-04)

Every row of every sheet is one design twice: **left** as `origin/main`
sews it, **right** with this change, at one scale. Each is drawn from its
own DST bytes (the engine's encoder writes the file, `src/dstimport.js`
reads it back). **Grey** is the shape as drawn, **black** is thread, **red**
is a needle-up move, and the **blue rule** at the bottom left is the scale
(its length is in the tables). A preset shape is built the way
`app/src/lib/generate.js` builds a `shape` element, a hand-drawn stroke the
way it builds a `manual` one, and a picture the way it builds an `image`
(left chest, the pique knit preset, underlay on, 4 colours).

Nothing here has been sewn. These are measurements of the stitch file.

To draw a sheet yourself, with `<dir>` an export of the tree before
(`git archive 59b30b02 src app/package.json app/src/lib | tar -x -C <dir>`):

```bash
node tools/satin-walk-census.mjs --against <dir> --sheet bars.png --shape rect:3:0:30 --shape rect:3:1.5:30
node tools/satin-walk-census.mjs --against <dir> --satin --sheet arcs.png --shape arc:12:3:330:270
```

The other shapes are in the tables: `rect:<height>:<corner radius>:<width>`,
`star:<points>:<inner ratio>:<size>`, `circle:<size>`, `heart:<size>`,
`arc:<radius>:<width>:<sweep>:<turn>`,
`image:<file>:<size or auto>[:<shape id>]`.

## What was wrong

Three things, each hiding the next.

1. **The skeleton.** `thin` never deletes a pixel on the edge of its grid,
   and a shape was laid against the grid's top and left with no spare cell,
   so its top row and left column were never thinned and everything else
   thinned onto them. A bar's "skeleton" was its top edge and its left edge,
   an L. The crosses are cast from the skeleton to the outline: right along
   the top, turning at the corner, the last of them the length of the bar.
2. **The walk.** The tracer that turns a skeleton into strokes would step
   into the corner filler of a staircase, end its edge there, and sew the
   stroke again from the other end; and what its walks left over it closed
   into "rings" with a chord. The wrong skeleton had hidden this: its border
   row and column gave every curve real nodes to stop at.
3. **The ends.** A true centre line stops half the stroke's width short of
   the stroke's end, so a free end is run on to the outline; and a cross cast
   from the point that lands on the outline can leave through the end.

No new number. The walk is the Python engine's own, ported.

## [`bars.png`](bars.png)

| row | bar (rule 5 mm, row 8: 1 mm) | before | after |
|---|---|---|---|
| 1 | 30 x 3 mm, sharp | 173 stitches, sewn 30.3 x 4.2 mm, longest stitch 30.2 mm | 165, 30.0 x 3.4, longest 3.4 |
| 2 | 30 x 3 mm, round ends | 174, 30.2 x 3.6, longest 30.2 | 165, 30.0 x 3.4, longest 3.4 |
| 3 | 16 x 3 mm, sharp | 96, 16.3 x 3.9, longest 16.2 | 88, 16.0 x 3.4, longest 3.4 |
| 4 | 16 x 3 mm, round ends | 102, 15.1 x 3.5, longest 6.7, 90% covered | 88, 16.0 x 3.4, longest 3.4, 98% |
| 5 | 30 x 2 mm, round ends | 165, 29.1 x 2.5, longest 3.6 | 165, 30.0 x 2.4, longest 2.4 |
| 6 | 20 x 1 mm, sharp | 112, 20.2 x 5.4, longest 20.2 | 110, 20.0 x 1.4, longest 2.0 |
| 7 | 12 x 3 mm, corner radius 0.75 | 78, 10.4 x 3.5, longest 6.6, 86% covered | 66, 12.0 x 3.4, longest 3.4, 97% |
| 8 | 6 x 3 mm, round ends | 26, 6.0 x 3.9, longest 5.2, 80% covered | 33, 6.0 x 3.4, longest 3.4, 94% |

The 0.4 mm over the drawn height is the pique preset's 0.3 mm of pull
compensation, 0.15 mm a side, each rounded to the file's 0.1 mm.

**Two things to look at on the right, both costs:**

- **The red line the length of the bar.** The underlay is one straight run
  along the bar and the column then starts at the end the underlay started
  from, so the frame carries the thread back the whole way with the needle
  up (28.5 mm on the 30 mm bars). Before, the L started where the underlay
  ended and the move was 1.9 mm on row 1 (and 145 mm on row 2). It is so on
  the seven garments whose preset underlays a satin with a centre run; on
  the three with a zigzag (towel, full back, blanket) it is the other way
  about. Not changed here.
- **The last cross of a round end** (rows 2, 4, 5, 7, 8). It stands on the
  very end of the bar, where the shape has no height, and is as long as the
  cross before it: its two ends are up to 0.46 mm outside the curve. Not
  changed; say if it should be.

## [`arcs.png`](arcs.png)

A stroke drawn by hand as a C and set to satin by the user. This is the
lane the first build of this change broke (row 1 came out 6,047 stitches,
the mouth of the C sewn solid), and what an independent re-measure caught.

| row | arc, 3 mm wide (rule 5 mm) | before | after |
|---|---|---|---|
| 1 | 330 degrees of radius 12 | 447 stitches, longest stitch 8.8 mm, needle up for 47.9 mm | 304, longest 3.4, needle up 0 |
| 2 | 270 degrees of radius 12 | 425, longest 8.8, 86% covered, needle up 50.0 | 248, longest 3.4, 95%, needle up 0 |
| 3 | 300 degrees of radius 8 | 351, longest 7.1, needle up 41.6 | 176, longest 3.4, needle up 8.0 |
| 4 | 180 degrees of radius 12, 2 mm wide | 320, 91% covered, needle up 15.5 | 174, 96%, needle up 0 |

Before, the upper left of each C is sewn two and three times over and the
far end of rows 2 and 3 is bare. After, each is one column from end to end.

## [`small.png`](small.png)

| row | shape (rule 1 mm) | before | after |
|---|---|---|---|
| 1 | circle, 6 mm | 48 stitches, 77% covered | 27, 90% |
| 2 | heart, 8 mm | 88, sewn 7.0 x 6.6 mm, 86% | 65, sewn 8.5 x 7.1, 97% |
| 3 | square, 6 x 6 mm | 55, 92%, longest stitch 7.1 mm | 37, 85%, longest 8.8 |
| 4 | 5 x 2 mm, round ends | 38, sewn 4.1 x 2.6, 80% | 28, sewn 5.0 x 2.4, 96% |
| 5 | 12-point star, ratio 0.9, 6 mm | 25, 70% | 27, 92% |

**Row 3 is the one that gets worse**, and rows 1 and 3 show why. A disc or a
square up to 6 mm is satin by the classifier's rule, and its true skeleton
is a point: there is no stroke to sew. Before, the L gave it two (one down,
one across, sewn over each other). Now it takes the fallback the engine has
always had for a ring with no stroke, a column between the two farthest
points of the outline, which starts and ends 12% of its length in from
them: the caps of the circle and two corners of the square are bare, and the
square's column runs corner to corner, so its middle crosses are its
diagonal. The heart is sewn 0.5 mm wider than drawn (0.4 mm of that is pull
compensation).

## [`stars.png`](stars.png)

| row | star (rule 5 mm, row 4: 10 mm) | before | after |
|---|---|---|---|
| 1 | 12 points, ratio 0.15, 20 mm | 729 stitches, sewn 17.1 mm across, needle up for 190 mm | 524, 17.6, needle up 120 |
| 2 | 8 points, ratio 0.15, 20 mm | 592, 17.6, needle up 120 | 390, 18.4, needle up 68 |
| 3 | 6 points, ratio 0.40, 15 mm | 439, sewn 14.8 x 16.0 mm | 261, 15.2 x 17.4 |
| 4 | 10 points, ratio 0.15, 78 mm | 3,215, sewn 74.0 x 78.6, longest stitch 72.5 mm | 2,036, 77.7 x 80.8, longest 80.8 |

Each arm is sewn once now, where it was sewn two and three times, and runs
to its tip or nearer. **The centre is not cured**: a cross cast from a
station by the centre still runs out along another arm, and row 4's longest
stitch is the height of the star. That is the star's half of defect 57 (the
classifier sends twelve arms to satin as one column) and this change does
not touch it. At a tip a cross is wider than the tip, as it was.

## [`logos.png`](logos.png) and [`logo-shapes.png`](logo-shapes.png)

Whole designs first (rule 5 mm; row 3: 10 mm). Fills are the same stitch
for stitch; look at the thin shapes.

| row | picture | before | after |
|---|---|---|---|
| 1 | `becker_marine_logo`, 40 mm | 2,919 stitches | 2,885 |
| 2 | `logo_whitebg`, 40 mm | 2,707 | 2,686 |
| 3 | `logo_script_tires`, its own size | 18,223 | 13,996 |

Row 3's black slab on the stroke of the T is one shape sewn 4,378 stitches
deep; it is 145 stitches now.

Then one shape at a time, its own colour's thread black and every other
colour faint (rule 1 mm). "Covered" is the share of the shape under **its
own** thread: in a picture a ground fill often runs under a small shape, and
counting that thread hides what the satin does.

| row | shape | before | after |
|---|---|---|---|
| 1 | `logo_gaulke_roofing` 40 mm, `s19`, 6.3 x 1.4 mm | 16 stitches, 17% covered | 34, 98% |
| 2 | `black_ground_holes` own size, `s19`, 3.4 x 3.2 mm | 13, 52% | 26, 97% |
| 3 | `logo_whitebg` 40 mm, `s6`, a 6 mm dot | 26, 64% | 33, 94% |
| 4 | `becker_marine_logo` 40 mm, `s2`, 6.4 x 6.6 mm | 84, 83% | 78, 93% |
| 5 | `enthusiast_logo` own size, `s4`, 8.0 x 8.5 mm | 114, 80% | 111, 90% |
| 6 | `black_ground_holes` own size, `s20`, 3.4 x 3.2 mm | 65, 99% | 20, 89% |
| 7 | `black_ground_holes` 40 mm, `s20`, 1.3 x 1.3 mm | 25, 99% | 6, 81% |
| 8 | `logo_drone_thermal_badge` 40 mm, `s20`, 1.8 x 1.5 mm | 33, 98% | 14, 90% |
| 9 | `logo_script_tires` 40 mm, `s2`, 7.4 x 7.6 mm | 1,728, 100% | 57, 95% |

Rows 6 to 8 are the shapes that lose the most. Rows 2 and 6 are the same
square in two places in one picture: before, one was sewn 13 stitches and
the other 65, by how each fell on the raster; now 26 and 20.

## The numbers behind the pictures

All from `tools/satin-walk-census.mjs`, each against the tree before.

- **Bars**, 5 to 100 mm long, ten garments (`--kind rect --sizes 5:100:1
  --garments all`): 14,812 of 43,200 are satin and every one moves; no fill
  does. Bars with a stitch over 12.1 mm: 3,731 before, none now (the only
  ones over 7 mm are the 6 x 6 mm square's, 8.6 to 9.1 mm by garment). Sewn
  length against drawn, on the 14,260 their hoop does not scale down: within
  0.6 mm on every one; 4,866 were over 0.5 mm short. On left chest
  (`--cover`) the bars under 90% covered go from 99 of 1,480 to 6, and those
  with thread over open ground from 495 to none.
- **Curved strokes**, 320 arcs (`--kind arc --satin --cover`, and without
  `--satin` for the classifier's own call): on the user's satin, thread over
  open ground in 167 before (4,052 stitches, 29.7 m of it) and in none now;
  under 90% covered, 150 before and none now; the largest 3,500 stitches
  before, 318 now. On the classifier's call 192 are satin: 102 under 90%
  before, none now; the 128 it fills do not move.
- **Stars**, 10 to 100 mm (`--garments all`; `--cover` on left chest):
  STAR_BULLET
- **Circles and hearts**, 5 to 100 mm (`--kind circle --sizes 5:100:0.5
  --garments all --cover`): the 30 satin circles go from a median 79.8%
  covered to 89.6%, with 19 to 27 fewer stitches; the 80 satin hearts from
  87.4% to 96.8%, and the 6 mm heart loses 3 to 4 points on seven garments.
- **Pictures** (`--images`): eight corpus logos at their own size and at
  40 mm, 408 shapes. All 196 satin shapes move. Not one of the 212 fills'
  own stitch records does. Under their own thread 96 satin shapes gain over
  2 points (46 over 10) and 49 lose over 2. The 18 that lose over 10 are
  all under 3.5 mm: thirteen small squares of `black_ground_holes` that had
  been sewn three and four times over (25 stitches to 6, 65 to 20), four
  2 mm shapes of `logo_gaulke_roofing` and a 0.9 mm speck of
  `enthusiast_logo`. Satin shapes under 90%: 69 before, 42 now; the least
  covered 17% before, 70% now. The satin shapes of every design sew fewer
  stitches than they did.

Live status: MASTER_SCOPE defect 57 and "Waiting on Kent" 26. The cause, what
moves and the two independent re-measures: `docs/scope-history.md`, the entry
of this date.
