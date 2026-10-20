# Small shapes in the browser's medial satin: `satinSmallShapes` off beside on (2026-10-20)

> **Flipped ON by default later the same day** (Kent's ruling, with this sheet in
> front of him: flip it whole, tips capped like round ends). The "OFF" column
> below is now the off arm, `satinSmallShapes: false`; the text that follows
> was written while OFF was the default and is kept as the measurement.

MASTER_SCOPE defect 57's remainder ("Waiting on Kent" 26, after PR #817): a
star's centre, a round end's last cross, small squares and dots. The cure is
built in `src/satin.js` behind one engine option, **`satinSmallShapes`, OFF by
default**; the flip is Kent's (gate 3). Nothing here was sewn: every number is
of the stitch plan, and the plan's thread width is the preview's 0.4 mm.

[`sheet.png`](sheet.png): one row per shape, **OFF on the left, ON on the
right**, at one scale (the blue rule is 1 mm). Grey is the shape as drawn,
black is thread, red is a needle-up move. [`svg/`](svg/) has each design
twice through `src/svgexport.js`; [`measures.json`](measures.json) every
number below. To draw it again:

```bash
node tools/satin-small-shapes.mjs --sheet sheet.png --svg svg --json measures.json
```

Each design is built as the Studio builds a `shape` element on left chest
(the pique preset: 0.3 mm of pull compensation, 0.15 mm a side; underlay
on; 0.4 mm satin pitch), a word as it builds a `text` element. The first
four shapes and the two words are the pinned set of
`test/satin-small-shapes.test.js`; the rest widen the evidence.

## The table

"Out" is how far the farthest needle of the shape's satin lands outside its
drawn outline; 0.15 mm of it is the preset's pull compensation, which is put
on outside the outline on purpose, and the file rounds to 0.1 mm. "Up" is the
needle-up distance between the design's runs. "Cover" is the share of the
drawn shape under thread. The md5 is of the stitch stream (x, y, type of
every record).

| design | tier | stitches | longest stitch mm | out mm | up mm | cover | sewn mm | md5 moved ON |
|---|---|---|---|---|---|---|---|---|
| 5-point star, 10 mm, inner ratio 0.45 | satin | 131 → 104 | 8.02 → 4.60 | 0.64 → 0.18 | 16.0 → 17.0 | 99.7% → 96.9% | 10.0 × 9.5 → 9.6 × 9.4 | yes |
| 10 × 2 mm stroke, round ends | satin | 55 → 55 | 2.40 → 2.40 | 0.35 → 0.20 | 1.0 → 0.8 | 96.7% → 98.1% | 10.0 × 2.4 → 9.4 × 2.4 | yes |
| 1.5 mm square | satin | 8 → 8 | 1.80 → 1.80 | 0.15 → 0.15 | 0 → 0 | 100% → 100% | 1.4 × 1.8 → 1.4 × 1.8 | **no** |
| 1 mm dot | satin | 6 → 6 | 1.41 → 1.40 | 0.31 → 0.20 | 0 → 0 | 67.5% → 100% | 1.6 × 1.6 → 0.8 × 1.4 | yes |
| 6-point star, 10 mm, inner ratio 0.45 | satin | 170 → 127 | 9.85 → 5.30 | 0.58 → 0.18 | 42.6 → 22.3 | 99.7% → 95.9% | 10.2 × 11.2 → 10.0 × 11.2 | yes |
| T, arms 10 × 2 mm, drawn and set to satin | satin | 101 → 98 | 10.40 → 2.53 | 0.70 → 0.20 | 20.0 → 20.5 | 99.1% → 96.1% | 10.2 × 10.4 → 10.0 × 10.2 | yes |
| 6 mm square | satin | 47 → 33 | 7.78 → 6.40 | 0.40 → 0.20 | 3.6 → 3.6 | 88.2% → 93.7% | 6.8 × 6.8 → 6.0 × 6.4 | yes |
| 6 mm dot | satin | 27 → 33 | 6.20 → 6.20 | 0.14 → 0.10 | 2.0 → 3.0 | 89.6% → 95.5% | 6.2 × 5.0 → 5.4 × 6.2 | yes |
| "Fritsch" in barstitch_regular, 12 mm | satin | 1,635 → 1,635 | 4.22 → 4.22 | – | 151.0 → 151.0 | – | 101.8 × 25.3 | **no** |
| "Stitches" in venezia, 10 mm | satin | 1,859 → 1,859 | 4.63 → 4.63 | – | 105.2 → 105.2 | – | 102.7 × 21.8 | **no** |

OFF md5s, byte-identical to `main` at `0eb5e02` (taken there before the
option existed, re-read with it built in):

| design | OFF md5 |
|---|---|
| 5-point star | `52ec3113edbb326b446cb6fa7f393108` |
| round-ended stroke | `92d9d1fec2dc684d2430dd75d655d796` |
| 1.5 mm square | `795d20f7a8ebba5d7e7d5c660492803d` |
| 1 mm dot | `4aeeb8a9eb16656b49c9e60712ea9d1f` |
| "Fritsch", barstitch_regular | `5cb7310b4644edb28c192dfcd60d46c8` |
| "Stitches", venezia | `f4f5e3f98be5396c7814d9b777c7622b` |

Lettering never reaches `medialSatin` (its columns are the font's own
rails, played by `satinplay`), so the two words do not move with the option
on either; they are in the pin so that stays measured rather than assumed.

## What changed per shape, and why

**The five-point star.** OFF, the branch guard passes a 10 mm five-point star
as satin (its two halves are of equal length and every rung's midpoint lies
inside), the skeleton is five arms meeting at a cluster of three node pixels,
and each arm's stations run in to the centre. From a station inside the
centre pentagon the ray cast across the arm leaves the arm through its base
and lands on another arm's far wall: crosses of 5.6 to 7.7 mm on an arm
2.6 mm wide at its base, one set per arm, so the centre is sewn five times
over (26 crosses through the inscribed disc) and the longest stitch of the
design is 8.0 mm. ON, each arm is cut where it enters the disc inscribed at
the junction, whose radius is the distance from the junction to the nearest
wall. On a regular star that is the inradius of the centre pentagon, which is
exactly where a cross stops meeting its own arm: an arm's base cross is the
pentagon's edge. The five arms are sewn as five tapering columns, tip to base
and base to tip in turn, and the centre is sewn ONCE, as the smallest column
over the polygon their base crosses bound (7 crosses through the disc, the
zone's own). The longest stitch is 4.6 mm, the zone's width. The needle-up
distance stays about what it was (16.0 → 17.0 mm): the moves between arms are
base to base where a column's parity allows (0.2 and 0.5 mm, across the zone
and under its thread, since it is sewn last) and tip to tip in turn (6.0 and
6.1 mm; one in two is the fewest a path through five arms can have). The
six-point star reads the same way, with less needle-up (42.6 → 22.3 mm). The
cost: the tips. OFF's last cross at a tip carried the width of the station
before it and stood 0.5 mm beyond the tip's edges; ON that cross is pulled
onto the edges just behind the tip, so the plan's extent reads 9.6 mm for a
10 mm star and cover falls 99.7% → 96.9% (the tips and the slivers between
the disc and the pentagon's corners, within a thread's width). Say if a sharp
tip should keep the overshoot.

**The T** is the same junction in a letter's clothes: OFF the stem's stations
inside the bar cast along it (a 10.4 mm stitch, the bar's length); ON the
junction block is one zone (longest 2.5 mm). Drawn by hand and set to satin
because the classifier sends a T to fill.

**The round-ended stroke.** OFF, a free end is run out to the outline and
the station that lands on the apex takes the width of the station before it,
so the last cross stands on the apex 1.5 mm wide where the shape has no
width: its ends 0.27 mm outside the curve before pull compensation (0.35
measured, with it). ON, a cross's end outside the shape is pulled onto the
nearest point of the outline, `satinColumn`'s own fallback for a ray that
misses: the last cross is a chord of the cap, its ends on the curve, and
nothing lands outside but the pull compensation (0.20 = 0.15 + rounding).
The stitch count and the longest stitch do not move. The cost: the chord sits
0.3 mm behind the apex, so the plan's extent reads 9.4 mm for a 10 mm stroke;
the thread's own width reaches to within 0.1 mm of the apex and cover goes
up (96.7% → 98.1%), since nothing is laid on bare cloth beyond the ends.

**The 1.5 mm square does not move.** Its skeleton is two pixels that happen to
lie level, so OFF already sews it as the column ON builds on purpose: four
level crosses the square's height, from one side to the other. The same
bytes. **The 6 mm square** shows why that was luck: its two pixels lie on the
diagonal, and OFF sews a diagonal column (7.8 mm stitches, 88% covered, the
plan 6.8 mm square). ON, a shape none of whose strokes reaches
`ringToSpines`' own floor for a stroke is sewn as the smallest column along
the ring's principal axis, from the polygon's second moments; a square's two
moments are equal and the axis is then level. 16 level crosses the square's
height, end to end (longest 6.4 = 6 + pull compensation, 94% covered, 33
stitches against 47).

**The 1 mm dot.** OFF, two skeleton pixels on the diagonal: three crosses as
wide as the dot whose ends stand 0.16 mm outside it, a square of thread on a
round shape (the plan 1.6 mm square, 68% of the dot under thread). ON, the
smallest column across the dot: three crosses, the middle one the dot's
width, the two at the ends chords pulled onto the circle by the cap, nothing
outside, 100% under thread. The plan's needle extent reads 0.8 × 1.4 mm: the
end chords sit 0.15 mm inside the apex each side, which the thread's width
covers. **The 6 mm dot** had no skeleton at all and fell to the outline-split
column, whose end-cap trim starts 12% in from each end (sewn 5.0 mm tall of
6); ON it is the smallest column too, 6.2 mm tall, 95% covered against 90%.

## What this is not

No new number. The thresholds the cure reads are the ring's own half-width
(the cluster radius for a junction), `ringToSpines`' stroke floor
(`max(3, 1.2 × half-width)`, which decides a blob), the distance from a
junction to the nearest wall (the zone's disc), the file's `EPS` (whether a
ring has an axis), and the satin pitch. A sharp tip is capped like a round
one; whether it should keep its overshoot is a question for Kent's eye, not
a number. Not drawn: the image lane's logos (every junction of every satin
letter there is a zone when the option is on), other garments, a star the
classifier sends to fill.
