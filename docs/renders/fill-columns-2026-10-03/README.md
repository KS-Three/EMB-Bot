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

## The numbers

| shape | floats off | floats on | cuts off | cuts on | stitches off | stitches on |
|---|---|---|---|---|---|---|
| Badge, two cut-outs (12 mm and 3 mm) | 79 (915 mm) | 2 (49 mm) | 1 | 3 | 3,149 | 3,226 (+2.4%) |
| Ring (an O) | 89 (1380 mm) | 2 (17 mm) | 1 | 2 | 1,579 | 1,667 (+5.6%) |
| Two counters (a B) | 148 (1248 mm) | 1 (10 mm) | 1 | 5 | 1,779 | 1,933 (+8.7%) |
| Wide U (no hole at all: a notch) | 121 (1894 mm) | 1 (1 mm) | 1 | 1 | 2,092 | 2,213 (+5.8%) |

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
  the underlay round a hole, then the fill). They stay over the shape's own
  ground, and the fill covers them.
- **The price is cuts and a few stitches.** One to four more cuts per shape.
  Stitches rise 2% to 9%, because every span of a split row now gets its own
  first penetration; today's engine starts those spans one stitch late.

## Not built

- **Travel under cover.** The Python engine avoids most of these cuts by
  running under rows it has not sewn yet. Here a join that cannot be made
  with one stitch inside the shape is cut.
- **Row stagger**, the other half of quality review 2026-09-08 §4.

The flip is Kent's: MASTER_SCOPE defect 52, "Waiting on Kent" 22.
