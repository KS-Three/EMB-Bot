# `fillColumns`: the browser fill, off beside on (2026-10-03)

One sheet: [`sheet.svg`](sheet.svg). Four shapes a person draws in the manual
lane, sewn by `buildQualityDesign` the way `app/src/lib/generate.js` calls it
(left chest, the pique knit preset, underlay on). Left column is the engine
as it ships. Right column is the same call with `fillColumns: true`.

Nothing here has been sewn. These are measurements of the stitch file.

## How to read it

- **Blue** is sewn thread.
- **Red is a float:** a frame move made with the thread still attached, so it
  lies loose on the cloth.
- An **orange dot** is a cut.
- **Pale yellow** is a hole. It should stay empty.

**In the Studio, turn on Jumps.** The field draws no jumps unless that toggle
is on, and it is off by default, so the screen shows a clean hole with the
option off or on. With Jumps on, the badge below draws 77 dashed lines across
its 12 mm cut-out with the option off and none with it on *(measured
2026-10-03 — `jumpTrimMarks` in `app/src/lib/strands.js`, the function behind
the toggle)*. The toggle draws every needle-up move the same, a float and a
move after a cut alike. This sheet tells them apart.

## The four shapes

| shape | floats off | floats on | cuts off | cuts on | stitches off | stitches on |
|---|---|---|---|---|---|---|
| Badge, two cut-outs (12 mm and 3 mm) | 79 (915 mm) | 3 (48 mm) | 1 | 0 | 3,149 | 3,253 (+3.3%) |
| Ring (an O) | 89 (1380 mm) | 2 (16 mm) | 1 | 0 | 1,579 | 1,700 (+7.7%) |
| Two counters (a B) | 148 (1248 mm) | 3 (40 mm) | 1 | 0 | 1,779 | 1,957 (+10.0%) |
| Wide U (no hole at all: a notch) | 121 (1894 mm) | 1 (1 mm) | 1 | 0 | 2,092 | 2,230 (+6.6%) |

*(measured 2026-10-03 with `node tools/fill-columns-sheet.mjs`, which prints
this table and the next one and writes the sheet)*

## What to judge

- **Off, every hole is solid red.** Each fill row crosses the hole: as a
  float when the hole is wider than a stitch (4 mm), as a sewn stitch when it
  is not. The 3 mm cut-out in the badge is stitched shut.
- **The wide U is the same defect with no hole in it.** Its rows run across
  the notch, so 121 floats lie over bare cloth outside the shape.
- **On, the holes and the notch are clear, and nothing is cut.** The two or
  three red lines left are moves between the runs of one shape (the underlay
  round the outside, the underlay round a hole, then the fill). They lie on
  ground the fill covers.
- **Stitches rise 3% to 10%.** Every span of a split row now gets its own
  first penetration (today's engine starts those spans one stitch late), and
  the thread travels along rims instead of floating.

## What the option promises

Every move a fill shape makes, in every pass of it, is asked what ground it
runs over. The ground is **what the fill covers**: the drawn outline, or
under a fabric preset the pull-compensated one the fill is sewn to. There are
three answers:

- **On that ground.** Nothing changes. A float there ends up under the fill.
- **On the rim:** off that ground, but never deeper than one fill row
  (0.15 mm). It is **sewn**, never floated.
- **Open ground:** deeper than one fill row into a hole, a notch or the
  outside. The thread does not go there. It **goes round** instead, and is
  cut only when there is no way round.

Measured by an independent audit with its own clipper, on 9,869 sound
drawings: shapes with and without holes and notches, at 2, 10 and 40 px per
mm, under all seven presets and none, underlay on and off.

| | off | on |
|---|---|---|
| floats longer than a stitch (4 mm) that leave the ground the fill covers | 1,154,992, on 8,308 designs | **0** |
| designs with thread deeper than one fill row off that ground | 8,581 | **36** |
| deepest such thread | 80.5 mm | 0.85 mm |

*(measured 2026-10-03 — the third audit's re-check, against the rings the
fill is sewn to, with 0.08 mm allowed for a stitch's rounding. The guards
kept are `test/fill.test.js` and `test/digitize.test.js`, "fillColumns:" and
"columns:")*

On 24,048 direct calls of the fill itself, no thread lay deeper than 1.1
times the tolerance in open ground, no float left the ground, and every span
of every row was sewn.

**The 36 are not thread across a hole.** 29 are islands, where the fill
itself is sewn small (below, "Seen, not changed"); the option leaves 29 such
designs where there are 78 without it. 7 are an edge run 0.27 mm beside a
hole too thin to compensate, 0.04 mm over the measure. None of the 36 has
thread outside both the cover and the drawing.

## How it gets round a hole without a cut

- **Round the ring.** From one side of a hole to the other along the hole's
  own edge, corner to corner.
- **In by the far end.** A strip beside a hole is entered by running along
  its own side to its far end first and sewing back, where that leaves the
  thread beside what comes next. The run lies under the strip's own row ends.
- **Along rims and rows**, when it is stranded: the shortest way made of
  those two moves and of runs along a row.
- **Each pass starts where the thread already is**, sewing from the bottom up
  if that is where the last pass ended.
- **The edge runs round holes** are taken nearest-first and entered at the
  corner the thread can reach.

A way round has a budget, the Python engine's: 20 mm, or four times the
straight distance if that is more. Past it the thread is cut.

## What it costs

| shape | preset | rows | cuts off | cuts on | stitches | time off | time on |
|---|---|---|---|---|---|---|---|
| 36 square holes of 4 mm, 60 mm badge | no fabric | the engine's own angle | 1 | 0 | +1.4% | 5 ms | 15 ms |
| 36 square holes of 4 mm, 60 mm badge | no fabric | 30° | 1 | 0 | +14.0% | 10 ms | 86 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | the engine's own angle | 1 | 0 | +2.7% | 1 ms | 35 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | 30° | 1 | 0 | +5.4% | 2 ms | 50 ms |
| 36 square holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +10.6% | 3 ms | 58 ms |
| 36 round holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +12.1% | 4 ms | 25 ms |
| 196 square holes of 3 mm, 100 mm | no fabric | 30° | 1 | 0 | +9.1% | 8 ms | 217 ms |
| 196 square holes of 3 mm, 100 mm | pique_knit | 30° | 1 | 0 | +8.1% | 7 ms | 135 ms |
| 196 square holes of 3 mm, 100 mm | terry_towel | 30° | 1 | 0 | +12.5% | 9 ms | 158 ms |
| 2,025 square holes of 1.2 mm, 100 mm | no fabric | 30° | 1 | 0 | +19.8% | 212 ms | 2075 ms |
| 2,025 square holes of 1.2 mm, 100 mm | pique_knit | the engine's own angle | 1 | 4 | +20.0% | 40 ms | 1221 ms |
| 2,025 square holes of 1.2 mm, 100 mm | structured_cap | 30° | 1 | 2 | +40.6% | 49 ms | 1580 ms |
| 2,025 square holes of 1.2 mm, 100 mm | terry_towel | the engine's own angle | 1 | 34 | +21.0% | 51 ms | 920 ms |
| 2,025 square holes of 1.2 mm, 100 mm | terry_towel | 30° | 1 | 8 | +30.0% | 71 ms | 2728 ms |

*(measured 2026-10-03 — the same tool prints all 32 rows, of which these are
fourteen. On the 36-hole and 196-hole shapes every one of the 24 rows has 0
in "cuts on". Times are one run on a laptop. The last shape is a stress
test, not a design.)*

What follows is the third audit's count on its own sweep *(measured
2026-10-03 — 9,869 sound designs, re-checked on this build)*.

- **Cuts fall from 0.89 a design to 0.25.** Fewer on 6,866 designs, more on
  433. The one cut in the "off" column is center-out's own, which a forked
  fill no longer makes.
- **A holed shape in one piece nearly always sews without one: 3,222 of
  3,317.** The other 95 keep one or two (100 cuts in all; without the option
  the same designs carry 2,885). 51 are on the way into a pass, on a thin
  ring or a tiny design where the thread ends beside nothing the next pass
  can start from. 38 are between two edge runs. 9 are inside a tatami
  underlay and 2 inside the fill, where the walk found no way round within
  its budget.
- **A notched shape can cost more cuts than today: 354 of 6,372.** The worst
  is a comb of eight teeth under fleece, 1 → 5: a tooth is too long to go
  round within the budget, so the underlay is cut where it used to be
  carried across the gap.
- **An island is a separate piece.** A ring inside a hole is cut to, and cut
  from, on every pass: a bullseye under terry, 1 → 4 (1 → 6 until the
  island's fill was sewn to its right size: below). An island 0.3 to 0.6 mm
  from the wall of its hole costs most, 1 → 7 on terry and fleece: until
  that fix its fill sat shrunk against the wall and the thread was carried
  over. (Neither lane the Studio builds through hands one over inside a
  shape: below.)
- **Stitches: 3.3% more in all.** By design the median is +4.3%, nine in ten
  are under +13.5%, and the worst is +36.9% (a 16-tooth gear with a hole).
  A dense grid of small holes costs most: up to +41% on the stress shape.
- **Time: under a quarter of a second up to 196 holes.** The stress shape
  takes 0.6 to 2.7 seconds (off: 0.04 to 0.2). The audit found 3.5 to 18
  seconds on a grid like it with the rows at 30°, in one loop that is now a
  heap.
- **The thread that replaces the floats is on show in places.** In a holed
  fill, 54 mm of sewn thread is neither a row nor a row turn (median 42).
  16 mm of it lies over rows already sewn: 14 mm on the rim, and 2.3 mm
  across the face of the fill. The face figure is 0 on the median design,
  over 5 mm on 365 of 2,221 and over 20 mm on 19 (most: 44 mm). Another
  12.5 mm runs along a row over a row already sewn, which reads as that row.
- **Thread piles up on rims.** Edge runs and the travel of every pass go
  round the same edges. On the worst millimetre of rim a design carries 3.0
  lines of it on average, 9.2 at most (off: 1.3 and 2.2). Four or more on 690
  of 2,815 designs, six or more on 45.
- **A few more very short stitches.** Under 0.3 mm in underlay: 10,086 →
  11,467 over 9,100 designs, and more than five extra on 20 of them. Holes
  traced with 400 points each are the worst: 4 → 48 on a 36-hole badge.
- **A large fill with a hole no longer sews center-out.** A plain one still
  does, and so does a T or an L whose rows never fork.
- **Edge runs move.** On a shape with a hole or an inside corner the edge-run
  underlay lies 0.2 mm inside the fill and keeps its corners. A shape with
  neither keeps the edge run it has today.

## Not built

- **Row stagger**, the other half of quality review 2026-09-08 §4.
- (**Tie stitches at a cut** were built the same day, also OFF: `ties`, in
  [`docs/lock-stitches-2026-10-03.md`](../../lock-stitches-2026-10-03.md).
  With this option on there are fewer cuts to lock.)

## Seen, not changed

Each of these is the same with the option on or off.

- **A row turn longer than a stitch INSIDE the shape is still a float.** In
  the fill it happens where an edge runs within two degrees of the rows, and
  it lies between two fill rows. In an underlay, with rows 2 mm apart, it is
  common, and it lies under the fill.
- **In a plain fill a span can start one stitch late** after a float (199 of
  2,022 plain fills in the second audit; 1,843 with the option off).
- **Pull compensation can fold a thin shape.** A sliver or a pinch narrower
  than twice the compensation is left partly unsewn by the fill itself, and
  the underlay under it then reads as uncovered (26 of 787 such designs). A
  hole 0.2 mm across is turned inside out by it, to 1 mm.
- **Pull compensation shrank an island: FIXED since, 2026-10-03, the option
  off or on.** A ring inside a hole is filled ground, and it was compensated
  as if it were a hole: under terry its fill was sewn 0.6 mm small on every
  side and its underlay showed that far outside it. And rings nested so that
  their areas summed to the outline's or more built nothing at all (three
  of them 4 mm apart in a 40 mm box), because the island's area was taken
  off like a hole's. An island now grows as the outline does, or is sewn as
  drawn where growing would bring it against the ring beside it or across
  itself (`islandsAmong` in `digitize.js`; `docs/scope-history.md`, the
  island entry of 2026-10-03). The 29 island designs among the 36 above
  were measured before that and not again. Neither lane the Studio builds
  through hands a shape over that way (the image lane and hand-drawn shapes
  each make an island its own shape; SVG import, which the app does not
  call today, does too for rings that nest without crossing);
  `groupRingsIntoShapes`, which three tool scripts use, does.
- **A float shorter than the preset's trim length between two SHAPES is
  left**, whatever lies between them. Where a fill ends decides whether that
  rule bites: 2 of 450 two-shape designs gained such a float with the option
  on.
- **The finishing outline (`outline: true`) is sewn after the fill**, so a
  float to it lies on top of the fill. No caller in the Studio passes it.

## How it got here

Three builds and three audits, each by an independent agent with its own
clipper, handed the claims as claims.

- **The first build** passed its own tests and failed three ways.
- **The second** cleared those, failed four more ways, and cost 35 to 122
  cuts on a 36-hole badge.
- **The third** held on thread across holes and failed on the question
  itself. A move running exactly along a line the shape's own corners lie on
  was read differently in its two directions, and the wide U on this sheet,
  under terry, had 14.8 mm of fill sewn across its notch. Every sweep of mine
  had used three presets; the audit used all seven. It also found an island's
  edge run on the wrong side of its ring, 3.5 to 18 seconds of build time on
  the stress shape with its rows at 30°, and three sentences of this page
  that said more than had been measured.

All of that is changed in this build. `docs/scope-history.md`, 2026-10-03.

The flip is Kent's: MASTER_SCOPE defect 52, "Waiting on Kent" 22.
