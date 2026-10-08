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
| Ring (an O) | 89 (1380 mm) | 2 (16 mm) | 1 | 0 | 1,579 | 1,698 (+7.5%) |
| Two counters (a B) | 148 (1248 mm) | 3 (40 mm) | 1 | 0 | 1,779 | 1,955 (+9.9%) |
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
| 36 square holes of 4 mm, 60 mm badge | no fabric | 30° | 1 | 0 | +12.7% | 10 ms | 86 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | the engine's own angle | 1 | 0 | +2.7% | 1 ms | 35 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | 30° | 1 | 0 | +4.6% | 2 ms | 50 ms |
| 36 square holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +10.3% | 3 ms | 58 ms |
| 36 round holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +11.6% | 4 ms | 25 ms |
| 196 square holes of 3 mm, 100 mm | no fabric | 30° | 1 | 0 | +8.8% | 8 ms | 217 ms |
| 196 square holes of 3 mm, 100 mm | pique_knit | 30° | 1 | 0 | +8.1% | 7 ms | 135 ms |
| 196 square holes of 3 mm, 100 mm | terry_towel | 30° | 1 | 0 | +12.5% | 9 ms | 158 ms |
| 2,025 square holes of 1.2 mm, 100 mm | no fabric | 30° | 1 | 0 | +19.1% | 212 ms | 2075 ms |
| 2,025 square holes of 1.2 mm, 100 mm | pique_knit | the engine's own angle | 1 | 4 | +20.0% | 40 ms | 1221 ms |
| 2,025 square holes of 1.2 mm, 100 mm | structured_cap | 30° | 1 | 2 | +38.8% | 49 ms | 1580 ms |
| 2,025 square holes of 1.2 mm, 100 mm | terry_towel | the engine's own angle | 1 | 19 | +22.7% | 51 ms | 920 ms |
| 2,025 square holes of 1.2 mm, 100 mm | terry_towel | 30° | 1 | 8 | +29.8% | 71 ms | 2728 ms |

*(measured 2026-10-03 — the same tool prints all 32 rows, of which these are
fourteen. On the 36-hole and 196-hole shapes every one of the 24 rows has 0
in "cuts on". Times are one run on a laptop. The last shape is a stress
test, not a design. Cuts and stitches are as re-measured after "A corner on
a scanline", below: 19 of the 32 rows moved in stitches and one in cuts. One
row moved again with "Where a pass ends", at the foot of this page: the
stress shape under terry at the engine's own angle, 28 cuts → 19; the other
31 rows are what they were. The two time columns are the run before both, on
a quieter laptop; what the change does to them is given there.)*

What follows is the third audit's count on its own sweep *(measured
2026-10-03 — 9,869 sound designs, re-checked on this build)*. It is the
build before "A corner on a scanline", at the foot of this page; what that
moved is given there.

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
  A dense grid of small holes costs most: up to +39% on the stress shape.
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
- **A plain fill whose top is a single corner starts with two penetrations
  in that corner.** The first scanline passes through it and finds a span of
  no length, and the plain walk sews what it finds: 1,094 times in 8,255
  designs built with the option on. The walk never cuts for one. The builder
  can, either side of a pass that is nothing else: 14 combs 1.8 mm across,
  under fleece and terry, in the re-measure. (The column walk leaves that
  span out: "A corner on a scanline", below.)

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

## A corner on a scanline

Found the same day by the independent audit of the lock stitches (PR #609),
which built 12,880 designs with this option on: **18 threads were a stub.** A
cut, two penetrations in one hole, and the end of the design.

A scanline that passes exactly through a corner pointing up the rows finds
both of that corner's edges and pairs them: a span of no length. The first
scanline sits on the shape's topmost point, so a shape whose top is a single
corner has one. A drawing on whole numbers has one wherever a corner lands
on a row: a comb's teeth 28 px wide, under rows 1.5 px apart. The walk made
a column of it, travelled to it like any other, and sewed it: two
penetrations in one hole. Left for last with no way round, it was cut to.
The Python engine has always left such a span out; the port had not. The
columns are now cut from the rows without it.

Before and after, on 8,255 designs (4,095 drawn on whole numbers, 4,160
random; all seven presets and none), option on:

| | before | after |
|---|---|---|
| threads that never leave one hole | 106, on 66 designs | 0 on this sweep; not none (the re-measure, below) |
| two penetrations on one point, in a pass the column walk sews | 11,797, on 6,597 designs | 159, on 121 |
| cuts | 2,354 | 2,196 |
| stitches | 19,301,027 | 19,242,860 |
| sewn thread | 57,773 m | 57,630 m |
| float length | 292 m | 318 m |
| designs with thread deeper than a fill row off the cover | 12 | 12, none with more of it |

Option off or absent, all 8,255 are byte for byte what they were. 6,550 of
the 7,269 designs with a pass the column walk sews changed in some stitch.
On the fill itself, 9,000 seeded shapes: a doubled point in 7,348 of 8,226
column walks before and in none after, with the cuts the same shape for
shape. With `ties` on as well, the same 8,255 carry 20,902 locks where they
carried 21,006, and 2,442 of them on a stitch under 0.3 mm where 2,790 were.

*(measured 2026-10-03 — both engines side by side on one sweep;
`test/fill.test.js`, `test/digitize.test.js`, "found by the audit of the
lock stitches")*

**What it costs:**

- **On this sweep, a cut more on 27 designs, one each; fewer on 125.**
  (Elsewhere a design can gain several: the re-measure, below.) On 8, combs under
  fleece and terry, it is inside an underlay: the walk had travelled 109 mm
  through that corner to the next tooth, which the budget allows when the
  corner is far enough off (four times the straight line). The move that
  trip stood in for is over the budget, so it is a cut: 3 → 4 on a comb of
  six teeth. On the other 19 it is between two passes: the first used to end
  on that corner (in 9, after 20 to 81 mm of travel to it) and the next
  could be floated to from there. From where the pass ends now, it cannot.
  Each of the 27 sews 18 to 125 mm less thread.
- **The floats into a pass are longer: 9% in all, 30 → 33 mm on the median
  design.** A pass may begin at any corner the thread can float to uncut,
  and takes the one that leaves the walk best placed for the move after its
  first column. Beside a tip that move was one stitch to the corner of no
  length, which counted as well placed and led nowhere: the walk then
  travelled back. Now it looks further for a corner that is, and floats
  further to reach it (551 of 1,989 passes read, and most of the rise).
  Those floats lie on ground the fill covers, and the travel they replace is
  part of the 142 m of sewn thread the table loses.
- **The stress shape under terry builds slower:** about twice as long at the
  engine's own angle (with 28 cuts where there were 34) and a fifth longer
  at 30°. Its other six rows are within a fifth either way *(timed side by
  side, best of three, on a busy laptop)*.

**What it leaves**, with the option on:

- **Two columns that touch at a point: the 159 above.** The move from one to
  the other has no length and was sewn all the same: two penetrations in
  one hole. Gone since, with what else made them: "A move of no length",
  below.
- **A thread of one stitch.** A short row of a lattice underlay at the tip
  of a comb's tooth can still be cut to and cut from: 52 on 24 designs, all
  under fleece or terry, 0.7 to 2.5 mm long (94 on 42 before). Eight designs
  gained one, with the cut above. (On this sweep. Other presets and shorter
  ones: the re-measure, below.)

**The independent re-measure came back after this had merged**, and it held
the rule and failed two things this section says. (The change reached `main`
inside #617, which was cut from its branch.) An agent with its own generator
and its own reader built 45,416 designs and a second 10,000 on other seeds:
combs of sixteen sizes in four orientations, T, L, U, E, H, staircases,
badges, tip-topped shapes, random stars and blobs, under all seven presets
and none, at 10, 2 and 40 px per mm. And 23,980 direct fills.

What held:

- **Option absent, and option false: identical on all 55,416**, and on
  10,994 direct fills without `columns`.
- **The plain walk is untouched:** a design whose every pass is a plain walk
  is the same with the option on too, 9,703 of 9,703. The stitches changed on
  exactly the 30,498 designs with a span of no length in a column walk.
- **No column walk sews a row of no length:** 68,412 before, none after.
- **No span with a length is left unsewn:** none in 60,753 column-walk passes,
  28,897 of whose spans are under half a pixel long.
- **No new thread off the cover:** no float over 4 mm leaves it, and no design
  gains more than 0.07 mm of thread deeper than a fill row off it.
- **Cuts fall, 15,125 → 14,249**, stitches by 0.43%, and the option builds 9%
  faster over the sweep.

What did not:

- **The stub is narrowed, not closed.** Threads that never leave one hole:
  731 on 304 designs → 17 on 16, and 31 → 22 on the second sweep. Eight
  designs have one now and had none before. Each is a row WITH a length, but
  under the file's rounding step: 0.44 px on the audit's own comb drawn 3%
  narrower. Alone in its column, in a tatami underlay, it is cut to, sewn as
  two penetrations the file rounds into one hole, and cut from. The rule
  here leaves out a span of NO length; "a row with a length, however short,
  is still a row" keeps this one. None is in a fill pass, and none under the
  four presets whose underlay is an edge run. It is the next section's "a
  stitch shorter than the file's unit".
- **A design can gain several cuts, not one.** Fewer on 814 designs, more on
  388; 13 gain two to four, and 15 on the second sweep gain two to seven.
  Three teeth 4 mm wide under terry: no cut → two, with a stub. Four teeth
  under terry with rows at 61.3°: none → three. Only with a tatami underlay:
  no design of 19,097 under pique, jersey, canvas or woven gains one, and
  none of 6,483 with underlay off. Of the 404 cuts gained, 330 are on the
  float into a plain walk, 34 on the float into a column walk, 34 inside one
  and 6 on the float into an edge run. 26 of the 388 sew more thread, not
  less (33 mm at most).
- **Why, traced on two of its drawings.** The walk takes the nearest column it
  can reach and looks one move ahead. A corner of no length was somewhere it
  could always go next, so with it gone the order of a pass changes from its
  first column on: for the better on twice as many designs as for the worse,
  and nothing in the rule says which. On the three teeth the old engine's
  "no cut" was 292 mm more thread, 99 mm of it travel round the outline in
  the fill itself, to seven corners of no length.
- **A thread of one stitch is not only fleece and terry:** 27 under no preset
  and 8 under the cap preset, 0.1 to 3.3 mm long, 32 of them under 0.5 mm.
  249 on 99 designs → 234 on 92; on the second sweep 807 → 837.
- **The floats: 7.6% longer, and 16.2% on the second sweep**, every one over
  4 mm on the cover. It tested the reason I first gave (the corner filling
  the list of nearest starts) and found it wrong: widening that list in the
  old engine moves float length 1.3%. The reason above, the look-ahead, is
  the one its numbers fit.
- **Closer to the edge of the promise.** Thread 0.15 to 0.22 mm off the
  cover, as the file rounds it: 9,850 → 10,404 mm, more on 398 designs. The
  walk now sews along a row exactly one pitch outside an edge in places it
  did not: within "never deeper than one fill row", and nearer to it.
- **On the fill itself** its 7,954 column walks went 3,395 → 3,386 cuts, four
  calls differing, where this page's 9,000 seeded shapes were the same shape
  for shape.
- **"A pass whose every span is a point sews nothing"** is true of a pass the
  column walk sews. A pass that is ONE point is a plain walk and still
  returns its two penetrations.

*(measured 2026-10-03 — an agent handed the claims as claims; five of its
drawings rebuilt here on `main` as it stands, where they give the same
threads)*

**Those five drawings**, for whoever takes up what is left. Points in px;
each built as `test/digitize.test.js`'s `drawn()` builds one (left chest, 10
px per mm, the target width the drawing's own, underlay on, the option on).
"Threads" is the penetrations between one cut and the next.

```
1. terry_towel, the engine's own angle. The audit's comb, 3% narrower.
   A stub: a row 0.44 px long, alone in its column. Threads [360, 2 in one hole, 464, 1441, 1435].
[[0,0],[27.15,0],[27.15,253.45],[44.12,253.45],[44.12,0],[71.26,0],[71.26,253.45],[88.23,253.45],[88.23,0],[115.38,0],[115.38,253.45],[132.35,253.45],[132.35,0],[159.5,0],[159.5,253.45],[176.46,253.45],[176.46,0],[203.61,0],[203.61,253.45],[220.58,253.45],[220.58,0],[247.73,0],[247.73,253.45],[264.7,253.45],[264.7,0],[291.84,0],[291.84,253.45],[308.81,253.45],[308.81,0],[335.96,0],[335.96,362.07],[0,362.07]]

2. terry_towel, the engine's own angle. Three teeth pointing down.
   No cut before, two now, with a stub. Threads [102, 2 in one hole, 1384].
   (The digits matter: with 91.55 and 99.7 the engine's angle changes sign and there is no stub.)
[[0,333],[41.7,333],[41.7,89.78],[49.85,89.78],[49.85,333],[91.55000000000001,333],[91.55000000000001,89.78],[99.70000000000002,89.78],[99.7,333],[141.4,333],[141.4,0],[0,0]]

3. terry_towel, angleOverride 61.3. Four teeth to the right.
   No cut before, three now. Threads [315, 3, 3, 1756].
[[321.56,0],[321.56,11.42],[70.94,11.42],[70.94,30.17],[321.56,30.17],[321.56,41.59],[70.94,41.59],[70.94,60.34],[321.56,60.34],[321.56,71.76],[70.94,71.76],[70.94,90.51],[321.56,90.51],[321.56,101.93],[0,101.93],[0,0]]

4. structured_cap, the engine's own angle. An arrow.
   One cut before, two now, and 27.5 mm more thread: the underlay ends at the barb, and the float into the fill is cut.
[[300,120],[180,240],[180,168],[0,168],[0,72],[180,72],[180,0]]

5. structured_cap, angleOverride 61.3. The audit's comb ("no cut is made to reach a corner", test/digitize.test.js) with each point [x, y] turned to [350 - y, x].
   Six threads of two penetrations one after the other, each cut to and cut from, from rows 1.28 to 0.21 px long; the last two in one hole.
   The same six before the fix and after it. Threads now [269, 2, 2, 2, 2, 2 in one hole, 2 in one hole, 4674].
```

## A move of no length

What the section above left: on 121 of the same 8,255 designs a pass the
column walk sews put two penetrations on one point, 159 times. Traced in a
copy of the engine, every one was a stitch to the point the needle was
already on.

**152 were the move between two spans of one scanline that meet at a
point**, with a gap of no width between them. Each span has a length and is
rightly a column. The move from the end of one to the start of the other
has none. Three things make such a pair:

- **A wall on a scanline: 136.** The scanline runs along a wall of a hole or
  a notch that a quarter turn has left a hair off level (3e-14 px on a 10 mm
  wall), and finds the wall's corner twice.
- **A corner on a scanline: 15.** The top of a round hole, the inside corner
  of a star.
- **A notch of no width: 1 here, and far the most where it happens.** A
  notch exactly twice the pull compensation wide (1.2 mm under terry) is
  closed to a slit by the outline the fill is sewn to. Every row that
  crosses the slit is two spans that meet on it, so the hole was doubled
  once a ROW: 81 of the 649 stitches of an H under terry, 680 on one comb
  under fleece. I had read this one as a corner. The independent re-measure
  told them apart.

**7 were a pass landing on its own first column.** When the thread can
float to no corner a pass could start from, it lands on the nearest corner
it can reach and travels from there. Its first move was then to the corner
it stood on.

128 of the 159 were in the fill and 31 in an underlay. None had a cut beside
it, and none made a stub.

**In 73 of the 159 the two points were not the same numbers.** They differ
in their last digits, by 2e-12 px at most: a scanline misses a corner by a
rounding error, or two edges do not meet to the last bit. A rule that asked
for equal numbers would have left them. "The same point" is the measure the
walk already uses round a ring: a millionth of a pixel.

Now a move of no length lays no stitch (`sewTo`, `src/fill.js`): the needle
is already there. Before and after, on those 8,255 designs, option on:

| | before | after |
|---|---|---|
| two penetrations on one point, in a pass the column walk sews | 159, on 121 designs | **0** |
| stitches | 19,242,860 | 19,242,701 |
| cuts | 2,196 | 2,196 |
| sewn thread | 57,630 m | 57,630 m |
| float length | 318 m | 318 m |

**Nothing else moves.** Read record by record, each new stitch file is the
old one with those penetrations taken out, 159 in all, and no other
difference. Option off or absent, all 8,255 are byte for byte what they
were. No cut or stitch count in either table above changes, nor the sheet,
nor the lock-stitch census (both tools re-run on both engines). With `ties`
on, the 121 designs carry the same 276 locks on the same legs.

**A drawing on whole numbers does it far more often than that sweep says.**
A second one, 240 shapes drawn on whole numbers only (combs, T, L, U, E, H,
staircases, badges with square holes, houses) as 8,400 designs: 1,727 on
278 designs before and none after. 1,420 of them lay along slits, on ten
combs whose gaps are twice fleece's pull compensation, and 6 were one leg
of a longer way through the columns' corners, not a move of their own: the
rule sits where a stitch is laid, so it has them too. Cuts 3,869 and 3,869.

*(measured 2026-10-03 — both engines side by side; `test/fill.test.js` "a
move of no length", `test/digitize.test.js`)*

**The independent re-measure** built 49,920 designs of its own: 780
drawings, 22 families on whole numbers and 120 random, spread over the four
quarter turns, under all seven presets and none, with its own generator and
its own reader. Option absent and option false: identical on every one.
Option on: 1,474 such penetrations in 56,760 column-walk passes before and
none after, cuts 7,140 and 7,140, each new file the old one with those
records taken out. It corrected three things I had claimed:

- **The notch of no width**, above: 581 of its 1,474.
- **"On the spot of the one before it" is true before rounding, not always
  in the file.** Two points 1e-14 px apart can fall either side of a 0.1 mm
  boundary. In 18 of its 1,474 the old file had a stitch one unit long
  there. It is gone all the same.
- **One of the 1,474 was at the very end of its design**, not in
  mid-thread. No cut beside it either.

*(measured 2026-10-03 — an agent handed the claims as claims; its three
counter-examples rebuilt here)*

**What is still two stitches on one point**, with the option on. None of it
is new, and none of it is a move:

- **A stitch shorter than the file's unit: the larger part of what is
  left.** Two penetrations a real distance apart, up to 0.14 mm, that the
  0.1 mm file rounds onto one point: 2,689 on the 8,255 designs, 2,621 of
  them in a column walk. The re-measure counts 15,566 on its own designs,
  nearly all a row shorter than 0.1 mm at a tip or a sliver, and a machine
  cannot tell one from the 159. "A row with a length, however short, is
  still a row" is the rule that keeps them.
- **The plain walk's doubled point**: 1,094 on the 8,255 ("Seen, not
  changed").
- **A thread of one stitch**, as above: 52 on 24 designs.

With the option OFF the same 8,255 designs carry 16,575 such records where
the option on now leaves 3,783: the plain walk sews every span and every
move of no length it meets (12,344), and has its own short stitches (4,231).

*(measured 2026-10-03 — the fixed engine, each record traced to the run it
came from)*

## Where a pass ends, and which column it begins with

What the corner fix's re-measure left open: "a walk whose cut count turns on
its first column", and 330 of the 404 cuts it gained, on the float into a
plain walk.

**Checked before anything was changed.** Its drawings give on `main` what it
said they give: the arrow 1 cut → 2, the four teeth 0 → 3, the three teeth
0 → 2. Its 45,416 designs, rebuilt here with its generator and read with its
reader and with one of mine: 15,125 cuts before the corner fix and 14,190 on
`main` (its 14,249, less 59 on its bullseye, which the island fix has moved
since); 388 designs with more cuts, 404 cuts, 13 of them two to four; none
under the four edge-run presets, none with underlay off. My reader puts the
404 where its did, but for six: 330 on the float into a plain walk, 34 inside
a column walk, 40 on the float into one (it had 34, and 6 into an edge run).

**Where `main`'s cuts are**, option on, on those 45,416: by the run before
the cut and the run after it.

| the cut is | on `main` | now |
|---|---|---|
| inside a plain walk (center-out's own) | 7,298 | 7,298 |
| on the float from an edge run into a plain walk | 2,342 | 2,342 |
| on the float from a column walk into a plain walk | 2,261 | **13** |
| inside a column walk | 902 | **378** |
| between two shapes, or at a colour change | 834 | 834 |
| between two edge runs | 182 | 182 |
| on the float from an edge run into a column walk | 152 | **48** |
| on the float from a plain walk into a plain walk | 129 | 129 |
| on the float from a column walk into a column walk | 90 | **22** |
| all | 14,190 | **11,246** |

The third row is the one nothing asked about. A pass was told where the
thread was and never where it had to go next, so an underlay the column walk
sewed ended wherever its last column did, and the float from there to a fill
that begins at a point of its own was cut.

Two things are built, both behind the option.

**1. A pass is told where the thread goes next.** A pass the plain walk sews
begins where it begins, wherever the thread is, and is the same pass built
first or last. So the builder builds it FIRST and tells the pass before it
where it begins: the fill before its underlay, the second lattice pass before
the first. The column walk then makes the float out its last move:

- **It leaves its last column by a corner the thread can float on from.**
  The other three corners cost a run laid under that column's own rows, as
  they do for any column.
- **Where no corner of that column will do, the thread travels on**: sewn,
  through the columns' corners, to the nearest corner that will, inside the
  budget every way round has. That travel lies over the underlay and under
  the fill. Only an underlay is told where the thread goes; a fill is not.

**2. A walk that comes out cut is walked again.** The walk takes the nearest
column it can reach and looks one move ahead; what it costs turns on its
first column, and nothing in the rule says which is the better one. So a
walk with a cut (inside it, on the float in, or on the float out) is walked
again from each of the other first columns the thread can float to, nearest
first, eight at most, and the better walk is kept. It looks past the eight
nearest starts, which the first walk does not. A walk with no cut is the
walk it was.

**Better is by two counts:** a walk's cuts, and its threads of fewer than
four penetrations between two of them. Such a thread is a row or two with a
cut at each end. It holds nothing, so the row is as good as not sewn and the
two cuts that fence it bought nothing. A later walk takes the place of the
best so far if it has fewer cuts and no more such threads, or as many cuts
and fewer of them; on a tie the first stands. (The second count came from
this section's own re-measure, below: by cuts alone a walk could save a cut
by stranding one more row.)

| option on, 45,416 designs | `main` | 1 alone | 1 and 2 |
|---|---|---|---|
| cuts | 14,190 | 11,942 | **11,246** |
| designs with fewer cuts than on `main` | | 2,230 | **2,520** |
| designs with more | | 0 | **0** |
| threads of fewer than four penetrations | 306, on 121 designs | 298 | **21, on 21** |
| threads that never leave one hole | 17 | 17 | 14 |
| stitches | 54,927,142 | 54,938,773 | 54,940,111 |
| sewn thread | 136,667 m | 136,699 m | 136,702 m |
| floats | 89,763 | 92,011 | 92,183 |
| float length | 740.8 m | 776.0 m | 782.2 m |

**On these designs a design's stitches moved only where it lost a cut:** the
2,520 that differ from `main` are the 2,520 with fewer, and none gained a
thread of fewer than four penetrations (102 lost one or more). That is what
these drawings show and not a rule: see the re-measure, below. Option off or
absent, all 45,416 are byte for byte what they were. By preset, underlay on:
no preset 1,690 → 1,185, cap 1,883 → 1,403, fleece 2,291 → 1,329, terry
2,292 → 1,351; and under the four edge-run presets, where only the second
rule has anything to do, 4,639 → 4,583 on 15,845 designs. With underlay off
nothing moves (6,483 designs).

**Nothing was traded for the cuts**, by the earlier re-measure's own reader
on the same 45,416: floats over 4 mm that leave the cover 25 → 25; sewn
thread deeper than 0.23 mm off it 17,053 mm → 17,053 mm, on the same 105
designs, more on none of them; no span with a length left unsewn in a column
walk, and no two penetrations on one point in one, before or after. Its
count of threads of one stitch: 234 → 7.

**A second sweep, drawn for this:** 223 drawings on whole numbers and halves
(combs of sixteen sizes and four with teeth of unequal height in all four
orientations, T, L, U, E, F, H, plus, arrows of one head and two, chevrons,
staircases, zigzags, badges with square, round and diamond holes, rings,
letters with counters), each under all seven presets and none, at the
engine's own angle, 0°, 90° and two more, and once with underlay off: 10,704
designs. Cuts 3,340 → 2,787; on the float from a column walk into a plain
walk 511 → 0; inside a column walk 81 → 43. Fewer on 534, more on none, and
those 534 are the only designs that changed. Threads of fewer than four
penetrations 25 → 5. Off or absent, identical on all.

**The re-measure's five drawings**, above, as threads:

| | `main` | now |
|---|---|---|
| 1. the audit's comb, 3% narrower | [360, 2 in one hole, 464, 1441, 1435] | [360, 2 in one hole, 1912, 1435] |
| 2. three teeth pointing down | [102, 2 in one hole, 1384] | [1484] |
| 3. four teeth to the right | [315, 3, 3, 1756] | [2092] |
| 4. the arrow | [121, 429, 430] | [552, 430] |
| 5. the audit's comb turned, rows at 61.3° | [269, 2, 2, 2, 2, 2 in one hole, 2 in one hole, 4674] | [4940] |

The second sews 15 mm less thread than `main` does and the third 61 mm more;
against the engine before the corner fix, which cut neither, 307 and 64 mm
less. The arrow's cut that is left is center-out's own. The stub in the
first is still there.

**On the fill itself**, the suite's seeded shapes by hand: 15,000 of five
seeds, each sewn four ways (told nothing; told where the thread is; told
that and where it goes next; told only where it goes), `main`'s fill beside
this one. Told nothing, every pass is `main`'s point for point. Every
assertion of the suite's test holds on every pass. No pass costs more cuts
than `main`'s on the same call, the caller's two counted. Told where the
thread is and where it goes next, the float out was one the caller cuts on
6,687 of 13,732 column walks, and is on 4; the float in on 20, and is on 5.
Every pass that changed has fewer cuts. Those shapes have no cut inside a
walk at all, with either engine: the second rule is tested on drawings, not
on these.

*(measured 2026-10-04 — both engines side by side; `test/fill.test.js`
"told where the thread goes next", "walked again", "the travel on has the
budget", "one of the cuts a walk is judged by"; `test/digitize.test.js`
"where a pass ends")*

**The independent re-measure** (2026-10-04: a separate agent, its own
generator, reader and clipper, the claims handed over as claims). Besides
the two corpora above it drew 9,084 designs of its own (406 drawings of 20
kinds: snakes, spirals, mazes, blobs, gears, flowers, crescents, arcs, wave
bands, rakes, islands, slit holes, small holes, several shapes to a design),
3,520 rows of small shapes, 3,572 mazes, spirals and islands made to find a
design with more cuts, 96 combs, 24 large drawings, and 6,500 direct calls
each sewn five ways.

*What held, to the digit:* option off or absent, identical on every design
of every one of those, with lock stitches and the row stagger on as well;
the plain walk untouched (14,943 plain fills, record for record); 14,190 →
11,246 and each row of the table above; no design with more cuts anywhere
it looked; pass by pass never more cuts (6,249 column walks, five ways);
nothing deeper than 0.23 mm off the cover that `main` does not have, no
float over 4 mm off it, not one span unsewn in 11.1 million of 60,753 column
walks, no doubled point, no stitch over 4 mm; the travel on never over its
budget and never in a fill; the floats; the five drawings.

*What did not, and what was done:*

- **A walk walked again could save a cut by stranding a row.** A maze under
  fleece went from threads of [261, 35, 4, 1724] to [302, 2, 1701]; two
  islands in a hole from [84, 4, 10, 57, 55, 791] to [96, 2, 59, 55, 791].
  One stitch, cut to and cut from. That is the second count above, built
  after this finding: both drawings are `main`'s walk again. On the
  re-measure's 9,860 mazes, spirals and islands, by my reader: 3 designs
  gained such a thread by cuts alone, and 1 does now (below).
- **"A design changes only by losing cuts" is these corpora, not a rule.**
  The count a walk is judged by is its own pass's. A pass that ends
  elsewhere starts the next one elsewhere: of those 9,860, 30 change and
  keep their count (in 20 a pass loses a cut and the pass after it gains
  one; in 10 the walk kept has as many cuts and fewer short threads), and
  one loses a cut and gains a thread of two penetrations in the pass after,
  which from where it now begins has one walk and no other. None has more
  cuts: 7,124 → 6,135, fewer on 821. Threads of fewer than four penetrations
  147 → 110.
- **Time was understated**, and so was the worst case of the option against
  no option: both under "what it costs" and "what it leaves", with its
  numbers.
- **Two phrases were wrong:** the 2,342 cuts on the float from an edge run
  are into a plain walk, 662 of them an underlay pass and not a fill; and
  they are not the only kind left under the four edge-run presets (72 more:
  12 from an edge run into a column walk's fill, 60 inside one). Both are
  put right below.

*Re-checked by the same agent once the second count was built:* every claim
about it held on its own reader. Option off or absent, identical on 68,724
designs. The 45,416 differ from the engine it first read in three designs
(two combs under terry), each with the cuts it had. On 29,400 direct calls
told where the thread is and not where it goes, no pass has more cuts than
`main`'s and none has more short threads between its own cuts (two had).
No design of 78,584 has more cuts than on `main`, and one gains a short
thread (the one above). **What the second count costs**, by its reading:
where it keeps a walk for its threads and saves no cut (11 of the 9,860), a
fill's travel rises 1.4 to 1.8 mm and one float under the fill goes from
2.3 mm to 17.7 mm; and on the two combs it moved in the 45,416 the floats
under the fill are longer (5.0 mm in all on `main`, 29.4 mm before the
count, 46.1 mm now; and 2.2, 6.4 and 21.9 mm). All on the cover.

*(the re-measure's report, relayed to Kent 2026-10-04; its drawings rebuilt
here with my reader; `test/fill.test.js` "a walk with a cut fewer is not
kept", "its first thread and its last are not counted", "of two walks with as
many cuts"; `test/digitize.test.js` "not left with a one-stitch thread")*

**What it costs:**

- **Thread, a little.** 35 m more in 136,667 m. On the 2,230 designs the
  first rule changes, the run under the last column and the travel on come
  to 0 to 67.5 mm, 13 mm on the median design. With the second rule a design
  can sew less: −189 to +241 mm on the 2,520, +12 mm on the median, more on
  2,362 of them.
- **A float where each cut was, and not a short one.** 2,420 more floats,
  2,367 of them longer than a stitch: 41 m more float, 5.6%. On the 2,520
  designs that changed, the longest float is now 18 mm on the median design,
  under 30 mm on nine in ten, 49 mm at most (the longest on any design is
  60 mm, as it was), and longer than `main`'s longest on 1,784 of them. Each
  lies on ground the fill covers and ends up under it; none has been sewn.
- **Travel over an underlay.** The travel on is laid over the rows of the
  pass it ends, as the walk's other ways round are. It is never added to a
  fill. The re-measure read it: 23.75 m in 1,501 passes, 1.7 to 67 mm a
  pass, 60% of it over thread that pass had already laid, none of it deeper
  than 0.18 mm off the cover.
- **Travel on show, in a FILL.** A walk walked again is kept for its cuts,
  whatever it sews to save them, and what a fill sews is on top. The
  re-measure, on the 198 fills of the 45,416 that walking again moved:
  travel across rows 20.07 m → 21.30 m; of that, along the rim over rows
  already sewn, 4.62 m → 5.60 m; across the face 403 mm → 386 mm; more
  travel on 102 fills, less on 55. On 107 fills of its own designs: 26.2 m →
  30.0 m, over the rim 9.77 m → 11.54 m, across the face 559 mm → 646 mm
  (the worst fill 4.8 mm → 24.4 mm). Its worst trade: a maze under terry,
  one cut saved for 404 mm more thread in the fill (travel 410 mm → 829 mm,
  125 stitches). Nothing in the rule says what a cut is worth in travel:
  the budget of a way round is asked of each move, not of a walk. (Read
  again after the second count: the same, but for 16 mm more along the rim
  on the three designs that count moved.)
- **More thread along the rim.** The runs under a last column, the travel on
  and a fill's travel all lie along it: by the re-measure, the rim with six
  or more lines of thread on it 34.3 m → 36.4 m (+5.9%), the worst
  millimetre up on 138 designs and down on 50, at most 14 lines, as before.
- **Time, where a walk has a cut.** A pass that comes out cut is walked up
  to nine times, and every walk is paid for whether it is kept or not. Both
  engines in one process, alternately, best of three, on a busy laptop. The
  2,781 designs with a cut the walk could do something about: 1.15 times
  `main`'s time in all, 1.19 on the median design, under 3.7 on 99 in 100,
  and 21 times on the worst (21 ms → 155 ms). A sample of the rest, 4,260
  designs: 1.05, which is a second pass over the fill's rows where the
  underlay asks and the fill turns out to be the column walk's. The
  re-measure's own timing agrees (1.20 on 927 designs, 1.05 on 1,066), and
  on its own designs 806 of 2,110 column passes were walked again and 689 of
  them were no better for it. **Where a big pass stays cut it is seconds.**
  The 2,025-hole stress shape on a 4 in garment under terry (41 cuts → 35;
  one pass of 791 columns walked nine times): 2.1 times `main`'s build here
  (3.8 s → 7.8 s), 3 times by the re-measure. A comb of 100 teeth on a 12 in
  back under the cap preset, 615 cuts either way: 5.0 s → 18.5 s. The sheet
  tool's own 32 rows are on an 8 in garment, where that stress shape under
  terry is 28 cuts → 19 and no slower; as a whole they came to 1.01, 1.05
  and 0.88 times `main`'s on three runs.
- **The builder asks where a plain pass begins with a function of its own,
  `fill.plainStart`** (2026-10-05; see the code review, below). It was
  first an option of `tatamiFill` (`plainOnly`) that answered null for a
  column walk and had the pass built before its turn, and three tools wrap
  `tatamiFill` to watch the passes. A stagger test and the stagger census
  took the null for a pass and were patched; the third was found broken by
  the review. `tatamiFill` answers every call with a pass again, once for
  each pass and in the order they are sewn, and the two patched files are
  `main`'s again.

**What it leaves**, option on:

- **378 cuts inside a column walk and 70 on the float into one.** On these
  designs the first column is not what they turn on: walked from every first
  column the thread can float to and not from eight, not one design of 9,084
  differs, and the re-measure found the same on both sweeps. (From four, 18
  more cuts, on three combs.) Under the four edge-run presets, 60 of them
  are inside the bullseye's fill and 12 on the float into the fill of a thin
  eight-pointed star.
- **Long combs: tens to hundreds of cuts that no option does not have.**
  Found by the re-measure, outside every sweep here. Teeth 1.5 to 2 mm wide
  and 80 mm long, rows on a slant. 24 teeth under fleece: 1 cut with the
  option off, 52 on `main`, 52 now. 30 teeth: 1, 59, 41. On a 12 in back, 60
  teeth: 1, 230, 178; and 100 teeth under the cap preset: 1, 615, 615, with
  600 threads of fewer than four penetrations. Eight tries are not enough
  for them, and the walks that would do it are not on the list at all where
  the thread cannot float to their start. Those walks begin at an END of the
  pass: its first column sewn downward, as a pass told nothing is walked, or
  its last sewn upward. Tried first in a copy of the engine, with the cut on
  the float in counted where there is one: 52 → 0, 41 → 0, 178 → 0, 615 → 1,
  and the stress shape above 35 → 27 in 0.6 of the time. **Not built here.**
  It is a third rule: it moves 72 of the 5,642 designs a walk is walked
  again on (5,085 cuts → 5,075, one design from none to two), and wants its
  own tests and its own re-measure.
- **The pass after.** A walk is judged by its own pass. Where it ends is
  where the next pass begins, and that is not weighed: see the re-measure,
  above (of 9,860 designs, in 20 the pass after gained the cut this one
  lost, and in one it gained a thread of two penetrations).
- **13 on the float from a column walk into a plain walk.** Twelve are one
  zigzag band 0.1 and 0.3 mm thick under fleece and terry. One is a comb
  whose fill begins on the end wall of a gap, where no corner of the
  underlay can float to it.
- **The float from an EDGE RUN into a plain walk: 2,342 cuts, and this
  change does not touch it.** 1,680 are into a plain fill and 662 into an
  underlay pass the plain walk sews. It is now the most of any kind a walk
  could do something about, and it is the kind the preset a left chest uses
  has: 398 of pique's 1,110. An edge run is a closed ring, sewn from
  wherever the drawing began; it could begin where the pass after it can be
  floated to. Not built here.
- **129 between two plain walks.** Both ends are where they are.
- **The stub.** A row shorter than the file's unit, alone in its column, is
  still cut to and cut from (the first drawing above).
- **A design can still have more cuts with the option than without:** 4,717
  designs on `main`, 2,442 now; the worst no cut → 15 on `main`, no cut → 8
  now. Those are the worst of these 45,416. The long combs above are far
  worse, on `main` and now.

**Mutated 34 ways: 32 die.** The other two build a plain fill twice over and
are the same engine, stitch for stitch on 15,139 designs. Four of the first
25 passed every test until a test was written for each: the travel on with
no budget, the cut on the float out left out of a walk's count, the last
walk kept on a tie and not the first, and one other first column tried and
not eight. The first two change nothing on the 45,416 designs either. A
spiral shows both. Nine are of the second count (cuts alone; as many cuts
and fewer short threads not the better; a short thread one of fewer than
three, or of five; the first thread of the pass counted as well, or the
last): each dies. The two that count an end thread die by a test written
for them, on drawings where that changes the walk.

The sheet is byte for byte the same, and so are its four rows; one row of
the cost table moved (above). The lock-stitch census and the stagger census
print the same numbers on `main`'s engine and on this one.

**`main` moved while this was measured** (c11d2c1c → 4fb4fcd4: the island
cures, the star's satin walk and `dedupeHoles` among 53 commits). Merged,
and all three sweeps built again on both: of 65,980 designs not one is a
stitch different from what it was, on `main` or here, and option off or
absent the merged engine is `main`'s on all 56,120 of the first two.

*(measured 2026-10-04 — `node tools/fill-columns-sheet.mjs`,
`tools/lock-stitch-census.mjs`, `tools/fill-stagger-census.mjs`, each on both
engines)*

**A code review after the re-measure (2026-10-05) found three things no
sweep above had.** One is fixed here. Two are not, and "more on none" above
is a count of those 45,416 designs and not a rule.

1. **A tool on `main` was broken by it. Fixed.**
   `tools/sub-unit-stitch-census.mjs` wraps `tatamiFill` too, runs in no
   test, threw on the `plainOnly` null and paired passes to spans by the
   order of the calls: on the Studio's 8,270 designs, 2,261 builds failed
   and 2,454 passes were not found in the stream. With `fill.plainStart`,
   none and none. Not a stitch moves by it: the three sweeps built again,
   65,980 designs with the option on, each the stream it was, and with the
   option off or absent on all 56,120 of the first two.
2. **A design with MORE cuts than `main`, option on. Not cured.** A maze of
   64 points under fleece, rows at 165: 1 trim → 3, and a thread of three
   penetrations; rows at 15: 3 → 4. The first lattice pass is walked again
   and ends elsewhere, and the second, a column walk begun from there, is
   cut where `main`'s is not. A walk is judged by its own pass ("the pass
   after", above).
3. **A trim record saved is not always a cut saved in the file. Not
   cured.** The DST writer lays a float over 24.2 mm on an axis as three
   jump records or more, and a reader of the file counts that as a cut. On
   the 45,416: trim records 14,190 → 11,246, cuts in the file 19,782 →
   17,182. Of the 2,520 designs with fewer trim records the file has fewer
   cuts on 2,248, as many on 263 and MORE on 9 (each 1 → 2, combs under
   fleece and terry). Three teeth pointing down under terry: 2 trim records
   → 0, and 2 cuts in the file either way.

*(measured 2026-10-05 — the tool itself on this branch's engine before the
fix and after; the maze and the teeth built on `main` at 546ae759 and
here; the file's cuts read back from the DST of every design at 35b2a8b6
against `main` at 4fb4fcd4, and this engine is 35b2a8b6's stitch for
stitch)*

The flip is Kent's: MASTER_SCOPE defect 52, "Waiting on Kent" 22.
