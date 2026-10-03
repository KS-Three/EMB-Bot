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

The Studio's preview cannot show this. `src/render.js` draws no jumps, so the
screen shows a clean hole whether the option is on or off. This sheet is the
first place the floats are visible.

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

Measured over 255 designs: 17 shapes (T, L, U, H, E, a plus, stairs, an
arrow, badges and rings with one to 36 holes), five row angles including the
one the engine picks, with no fabric, pique and cap.

| | off | on |
|---|---|---|
| floats longer than a stitch (4 mm) that leave the ground the fill covers | 16,550, on 239 designs | **0** |
| designs with thread deeper than one fill row off that ground | 242 | **0** |
| deepest such thread | 11.0 mm | none |

*(measured 2026-10-03 against the rings the fill is sewn to, with 0.08 mm
allowed for a stitch's rounding; a throwaway sweep, of which the guards kept
are `test/fill.test.js` and `test/digitize.test.js`, "fillColumns:" and
"columns:")*

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
| 36 square holes of 4 mm, 60 mm badge | no fabric | the engine's own angle | 1 | 0 | +1.4% | 7 ms | 21 ms |
| 36 square holes of 4 mm, 60 mm badge | no fabric | 30° | 1 | 0 | +14.0% | 8 ms | 114 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | the engine's own angle | 1 | 0 | +2.7% | 2 ms | 42 ms |
| 36 square holes of 4 mm, 60 mm badge | pique_knit | 30° | 1 | 0 | +5.4% | 4 ms | 61 ms |
| 36 square holes of 4 mm, 60 mm badge | structured_cap | 30° | 1 | 0 | +8.1% | 12 ms | 67 ms |
| 36 square holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +10.6% | 4 ms | 74 ms |
| 36 round holes of 4 mm, 60 mm badge | pique_knit | 30° | 1 | 0 | +4.2% | 6 ms | 51 ms |
| 36 round holes of 4 mm, 60 mm badge | terry_towel | 30° | 1 | 0 | +12.1% | 5 ms | 31 ms |
| 196 square holes of 3 mm, 100 mm | no fabric | 30° | 1 | 0 | +9.1% | 10 ms | 305 ms |
| 196 square holes of 3 mm, 100 mm | pique_knit | 30° | 1 | 0 | +8.1% | 12 ms | 178 ms |
| 196 square holes of 3 mm, 100 mm | terry_towel | 30° | 1 | 0 | +12.5% | 8 ms | 269 ms |

*(measured 2026-10-03 — the same tool prints all 24 rows, of which these are
eleven; every one of the 24 has 0 in "cuts on". Times are one run on a
laptop.)*

- **Cuts: none on a holed shape in one piece.** The one cut in the "off"
  column is center-out's own, which a forked fill no longer makes. Two places
  a cut can remain: between two edge runs, where every straight way to the
  next hole lies across one already sewn round (0 to 4 on a 2,025-hole stress
  shape under pique); and on a notched shape whose rows never fork, which
  keeps center-out's cut and may add one on the way into a pass (a T with no
  fabric: 1 → 2).
- **Stitches: 1% to 14% more.** Most where the rows run at an angle to a grid
  of holes, because the thread travels more.
- **Time: 3 to 30 times the "off" time, and still under a third of a second**
  on these. A 2,025-hole stress shape takes 0.4 to 1.3 seconds (off: 0.1 to
  0.2).
- **A large fill with a hole no longer sews center-out.** A plain one still
  does, and so does a T or an L whose rows never fork.
- **Edge runs move.** On a shape with a hole or an inside corner the edge-run
  underlay lies 0.2 mm inside the fill and keeps its corners. A shape with
  neither keeps the edge run it has today.
- **More thread on rims.** A way round a hole is a line of running stitch on
  the hole's edge. In an underlay it is covered. In the fill it lies on the
  row ends, or under them where the strip was entered by its far end.

## Not built

- **Row stagger**, the other half of quality review 2026-09-08 §4.
- **Tie stitches at a cut.** No cut in the browser lanes is locked (the same
  review). With the option on there are fewer cuts to lock.

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
  the underlay under it then reads as uncovered (26 of 787 such designs).
- **The finishing outline (`outline: true`) is sewn after the fill**, so a
  float to it lies on top of the fill. No caller in the Studio passes it.

## How it got here

Three builds. The first passed its own tests and failed an independent audit
three ways. The second cleared those and failed a second audit four more
ways, and cost 35 to 122 cuts on a 36-hole badge. This is the third:
`docs/scope-history.md`, 2026-10-03.

The flip is Kent's: MASTER_SCOPE defect 52, "Waiting on Kent" 22.
