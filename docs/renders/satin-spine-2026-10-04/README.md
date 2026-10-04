# The spine of a satin shape: before and after (2026-10-04)

Every row of every sheet is one design twice: **left** as `origin/main`
sews it, **right** with this change, at one scale. Each is drawn from its
own DST bytes (the engine's encoder writes the file, `src/dstimport.js`
reads it back). **Grey** is the shape as drawn, **black** is thread, **red**
is a needle-up move, and the **blue rule** at the bottom left is the scale
(its length is in the tables). A preset shape is built the way
`app/src/lib/generate.js` builds a `shape` element and a picture the way it
builds an `image` element (left chest, the pique knit preset, underlay on,
4 colours).

Nothing here has been sewn. These are measurements of the stitch file.

To draw a sheet yourself, with `<dir>` an export of the tree before
(`git archive 59b30b02 src app/package.json app/src/lib | tar -x -C <dir>`):

```bash
node tools/satin-walk-census.mjs --against <dir> --sheet bars.png --shape rect:3:0:30 --shape rect:3:1.5:30
```

The other shapes are in the tables: `rect:<height>:<corner radius>:<width>`,
`star:<points>:<inner ratio>:<size>`, `circle:<size>`, `heart:<size>`,
`image:<file>:<size or auto>[:<shape id>]`.

## What was wrong

The skeleton of every shape was wrong along its top and its left. `thin`
never deletes a pixel on the edge of its grid, and the shape was laid
against the grid's top and left with no spare cell, so its top row and left
column were never thinned and everything else thinned onto them. A bar's
"skeleton" was its top edge and its left edge, an L. The crosses were cast
from that to the outline: right along the top, turning at the corner, the
last of them the length of the bar.

Two rules, no new number: one spare cell on those two sides, so the skeleton
is the centre line; and, because a centre line stops half the stroke's width
short of its end, a free end is run on to the outline.

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
  ended and the move was 1.9 mm on row 1 (and 145 mm on row 2). Sewing the
  underlay toward the column's start takes the census's bars from a median
  49.4 mm of it to 1.4 mm; that is priced and not built.
- **The last cross of a round end** (rows 2, 4, 5, 7, 8). It stands on the
  very end of the bar, where the shape has no height, and is as tall as the
  crosses beside it make it: its two ends are up to 0.46 mm outside the
  curve. Not changed; say if it should be.

## [`small.png`](small.png)

| row | shape (rule 1 mm) | before | after |
|---|---|---|---|
| 1 | circle, 6 mm | 48 stitches, 77% covered | 27, 90% |
| 2 | heart, 8 mm | 88, sewn 7.0 x 6.6 mm, 86% | 76, sewn 8.7 x 7.0, 96% |
| 3 | square, 6 x 6 mm | 55, 92%, longest stitch 7.1 mm | 37, 85%, longest 8.8 |
| 4 | 5 x 2 mm, round ends | 38, sewn 4.1 x 2.6, 80% | 28, sewn 5.0 x 2.4, 96% |
| 5 | 12-point star, ratio 0.9, 6 mm | 25, 70% | 33, 95% |

**Row 3 is the one that gets worse**, and rows 1 and 3 show why. A disc or a
square up to 6 mm is satin by the classifier's rule, and its true skeleton
is a point: there is no stroke to sew. Before, the L gave it two (one down,
one across, sewn over each other). Now it takes the fallback the engine has
always had for a ring with no stroke, a column between the two farthest
points of the outline, which starts and ends 12% of its length in from
them: the caps of the circle and two corners of the square are bare, and the
square's column runs corner to corner, so its middle crosses are its
diagonal. The heart is sewn 0.7 mm wider than drawn (0.4 mm of that is pull
compensation).

## [`stars.png`](stars.png)

| row | star (rule 5 mm, row 4: 10 mm) | before | after |
|---|---|---|---|
| 1 | 12 points, ratio 0.15, 20 mm | 729 stitches, sewn 17.1 mm across | 763, 17.6 |
| 2 | 8 points, ratio 0.15, 20 mm | 592, 17.6 | 602, 18.4 |
| 3 | 6 points, ratio 0.40, 15 mm | 439, sewn 14.8 x 16.0 mm | 514, 15.2 x 17.4 |
| 4 | 10 points, ratio 0.15, 78 mm | 3,215, sewn 74.0 x 78.6, longest stitch 72.5 mm | 3,345, 77.7 x 80.4, longest 72.5 |

The arms now run to their tips, or nearer (row 3's lower left arm was a
loose triangle of thread before). **The centre is not touched**: the long
stitches from arm to arm and the red needle-up moves between strokes
(190 mm of them in row 1, 763 mm in row 4) are defect 57's other half and
are in both columns. At a tip a cross is wider than the tip, as it was.

## [`logos.png`](logos.png) and [`logo-shapes.png`](logo-shapes.png)

Whole designs first (rule 5 mm; row 3: 10 mm). Fills are the same stitch
for stitch; look at the thin shapes.

| row | picture | before | after |
|---|---|---|---|
| 1 | `becker_marine_logo`, 40 mm | 2,919 stitches | 3,002 |
| 2 | `logo_whitebg`, 40 mm | 2,707 | 2,689 |
| 3 | `logo_script_tires`, its own size | 18,223 | 14,013 |

Row 3's black slab on the stroke of the T is one shape sewn 4,378 stitches
deep; it is 145 stitches now.

Then one shape at a time, its own thread black and every other colour faint
(rule 1 mm). "Covered" is the share of the shape under **its own** thread:
in a picture a ground fill often runs under a small shape, and counting that
thread hides what the satin does.

| row | shape | before | after |
|---|---|---|---|
| 1 | `logo_gaulke_roofing` 40 mm, `s19`, 6.3 x 1.4 mm | 16 stitches, 17% covered | 34, 98% |
| 2 | `black_ground_holes` own size, `s19`, 3.4 x 3.2 mm | 13, 52% | 26, 97% |
| 3 | `logo_whitebg` 40 mm, `s6`, a 6 mm dot | 26, 64% | 33, 94% |
| 4 | `becker_marine_logo` 40 mm, `s2`, 6.4 x 6.6 mm | 84, 83% | 184, 99% |
| 5 | `enthusiast_logo` own size, `s4`, 8.0 x 8.5 mm | 114, 80% | 145, 91% |
| 6 | `black_ground_holes` own size, `s20`, 3.4 x 3.2 mm | 65, 99% | 20, 89% |
| 7 | `black_ground_holes` 40 mm, `s20`, 1.3 x 1.3 mm | 25, 99% | 6, 81% |
| 8 | `logo_drone_thermal_badge` 40 mm, `s20`, 1.8 x 1.5 mm | 33, 98% | 14, 89% |
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
  (`--cover`) the share covered goes from a median 98.3% to 99.5%, and the
  bars under 90% from 99 of 1,480 to 6.
- **Stars**, 10 to 100 mm, ten garments (`--garments all`): 15,312 of
  145,600 are satin and every one moves; no fill does. The sewn width is a
  median 0.2 mm short of the drawn one (it was 1.2 mm). The longest stitch
  is as it was: a median 21.1 mm. Out of line with their neighbours in size:
  30 designs before, 10 now.
- **Circles and hearts**, 5 to 100 mm (`--kind circle --sizes 5:100:0.5
  --garments all`): the 30 satin circles go from a median 79.8% covered to
  89.6%, with 19 to 27 fewer stitches; the 80 satin hearts from 87.4% to
  98.0%, and the 6 mm heart loses 3 to 4 points on seven garments.
- **Pictures** (`--images`): eight corpus logos at their own size and at
  40 mm, 408 shapes. All 196 satin shapes move. Not one of the 212 fills'
  own stitch records does. Under their own thread 99 satin shapes gain over
  2 points (48 over 10) and 41 lose over 2 (16 over 10, every one a dot or a
  square under 3.5 mm that was sewn about three times over before). Satin
  shapes under 90%: 69 before, 39 now; the least covered 17% before, 70%
  now.

Live status: MASTER_SCOPE defect 57 and "Waiting on Kent" 26. The cause, what
moves and the independent re-measure: `docs/scope-history.md`, the entry of
this date.
