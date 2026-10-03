# `fillColumns`: the browser fill, off beside on (2026-10-03)

One sheet: [`sheet.svg`](sheet.svg). Four shapes a person draws in the manual
lane, sewn by `buildQualityDesign` the way `app/src/lib/generate.js` calls it
(left chest, the pique knit preset, underlay on). Left column is the engine
as it ships. Right column is the same call with `fillColumns: true`.

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
| Badge, two cut-outs (12 mm and 3 mm) | 79 (915 mm) | 2 (49 mm) | 1 | 4 | 3,149 | 3,229 (+2.5%) |
| Ring (an O) | 89 (1380 mm) | 2 (17 mm) | 1 | 1 | 1,579 | 1,667 (+5.6%) |
| Two counters (a B) | 148 (1248 mm) | 2 (23 mm) | 1 | 3 | 1,779 | 1,936 (+8.8%) |
| Wide U (no hole at all: a notch) | 121 (1894 mm) | 1 (1 mm) | 1 | 1 | 2,092 | 2,220 (+6.1%) |

*(measured 2026-10-03 with `node tools/fill-columns-sheet.mjs`, which prints
this table and writes the sheet)*

## What to judge

- **Off, every hole is solid red.** Each fill row crosses the hole: as a
  float when the hole is wider than a stitch (4 mm), as a sewn stitch when it
  is not. The 3 mm cut-out in the badge is stitched shut.
- **The wide U is the same defect with no hole in it.** Its rows run across
  the notch, so 121 floats lie over bare cloth outside the shape.
- **On, the holes and the notch are clear.** The one or two red lines left
  are moves between the runs of one shape (the underlay round the outside,
  the underlay round a hole, then the fill). They stay over ground the fill
  covers.
- **Stitches rise 2% to 9%**, because every span of a split row now gets its
  own first penetration; today's engine starts those spans one stitch late.

## What the option promises

Every move a fill makes, in every tatami pass of it, is asked what ground it
runs over, and there are three answers:

- **Inside the fill.** Nothing changes. A float there ends up under the fill.
- **On the rim:** outside the shape, but never deeper than one fill row
  (0.15 mm). It is **sewn**, never floated. This is the turn at the step of a
  T, an L or a tall U, which runs along the step's own edge: today's engine
  floats it, 6 to 28 mm of loose thread that no later row covers.
- **Open ground:** deeper than one fill row into a hole, a notch or the
  outside. The thread is **cut**.

Measured over 255 designs: 17 shapes (T, L, U, H, E, a plus, stairs, an
arrow, badges and rings with one to 36 holes), five row angles including the
one the engine picks, with no fabric, pique and cap.

| | off | on |
|---|---|---|
| floats longer than a stitch (4 mm) that leave the ground the fill covers | 16,550, on 239 designs | **0** |
| designs with thread deeper than one fill row off that ground | 242 | 115, the edge run only (see "Seen, not changed") |
| deepest such thread | 11.0 mm | 0.64 mm |

*(measured 2026-10-03 against the pull-compensated outline the fill is sewn
to, with 0.08 mm allowed for a stitch's rounding; a throwaway sweep, of which
the guards kept are `test/fill.test.js` and `test/digitize.test.js`,
"fillColumns:")*

## The price is cuts, and it grows with holes

On these four shapes the cost is zero to three more cuts. A shape with many
holes pays much more, and almost all of it is in the underlay, not the fill.
One 60 mm badge with 36 holes of 4 mm, cuts off → on:

| preset (underlay style) | cuts | of which the fill | where the rest are |
|---|---|---|---|
| pique, tote (edge run) | 1 → 42 | 6 | 36 between the edge runs round each hole |
| no fabric (lattice) | 1 → 76 | 6 | 69 inside the lattice underlay |
| cap (edge zigzag) | 1 → 94 | 6 | 52 inside the zigzag underlay, 36 between runs |
| fleece, towel (double lattice) | 1 → 92 to 94 | 6 | the two lattice passes |

*(measured 2026-10-03 — `buildQualityDesign`, same call as the sheet, garment
and preset varied)*

- **The fill costs one cut per ROW of holes.** It finishes each level before
  it descends and steps from strip to strip along a hole's own top or bottom
  edge. Six rows of holes, six cuts.
- **An edge-run underlay costs one per hole.** Each run ends on its own hole's
  rim, and the straight move to the next hole crosses that hole.
- **A tatami underlay costs one per strip.** Its rows are 2 to 2.5 mm apart,
  so the step along the row would sit up to 2 mm inside the hole, and it is
  cut instead.
- **No cut in the browser lanes is locked.** Every trim here already leaves
  two unlocked ends (quality review 2026-09-08 §4); more cuts means more of
  them until the tie stitches are built.
- **A large fill with a hole no longer sews center-out.** A plain one still
  does, and so does a T or an L whose rows never fork.
- **A shape with no hole pays too, where its edge folds in.** A 60 mm blob
  with a wavy edge, traced with 720 points and with 3,000: 1 → 1 or 2 on
  pique, 1 → 2 or 3 on cap, 1 → 6 to 10 with no fabric.

## Not built

- **Travel that follows a hole's edge.** The Python engine runs along the
  shape's own edge, or under rows it has not sewn yet, before it cuts. That
  would remove most of the underlay cuts above.
- **Row stagger**, the other half of quality review 2026-09-08 §4.

## Seen, not changed

Each of these is the same with the option on or off.

- **The underlay's edge run chords across inside corners.** It is a running
  stitch round the inset outline and round each hole, it does not stop at a
  corner, and it is not a tatami pass. Measured: 0.9 mm of stitch 0.6 mm
  outside an L's inside corner with no fabric; 0.3 mm past the fill at the
  corners of a 3 mm hole on pique.
- **A row turn longer than a stitch INSIDE the shape is still a float.** In
  the fill it happens where an edge runs within two degrees of the rows, and
  it lies between two fill rows. In an underlay, with rows 2 mm apart, it is
  common, and it lies under the fill.
- **A float between two runs is cut only when it goes deep.** One that only
  grazed the rim would stay. None did, in the 255 designs above.
- **The finishing outline (`outline: true`) is sewn after the fill**, so a
  float to it lies on top of the fill. No caller in the Studio passes it.

The flip is Kent's: MASTER_SCOPE defect 52, "Waiting on Kent" 22.
