# Does `coverage_edges` close counters and slots? Becker, 2026-10-11

Waiting-on-Kent item 38 asks whether `coverage_edges` should ship with the
Column lane. `docs/coverage-edges-under-columns-2026-10-11.md` saw in the
pictures that the A's counter and leg notch closed and the E's lower slot
narrowed, but did not measure them. This doc measures them with a new
instrument, `digitizer/tools/counter_slots.py`, on `main` as of #839 (the
Column lane includes #837's rail inset). **All three flags stay OFF. Nothing
was sewn.**

## Verdict (one minute)

**Yes. At 80 mm `coverage_edges` narrows three slots below one thread
(0.4 mm), slots that the Column lane alone keeps open. It closes no
counter, but it shrinks two of them.**

- **80 mm, with the Column lane:** `coverage_edges` takes the E's lower
  slot from 0.79 to 0.24 mm, the E's upper slot from 0.70 to 0.39 mm, and
  the R's slot between stem and leg from 0.59 to 0.26 mm. The lane alone
  has **0** flags; with `coverage_edges` it has **3**. Without the lane
  the story is the same and slightly worse: the E's lower slot goes 0.86 to
  0.06 mm and the R's slot 0.69 to 0.19 mm, so flags go from 1 to 3.
- **Counters never close in any cell.** The smallest sewn counter is 0.71
  mm², against a closing line of 0.16 mm² (one thread squared). They do
  shrink. At 80 mm under the lane, `coverage_edges` takes the A's counter
  from 3.86 to 3.27 mm² (−15%) and the R's from 3.87 to 2.13 mm² (−45%).
- **At 50 mm the slots are already lost, flag or no flag.** MARINE's slots
  are only 0.7 to 1.4 mm wide in the artwork at that size, and every arm
  narrows 5 to 7 of them. Under the lane the flag count does not move (5
  and 5), but the flag still closes the M's top V (0.40 to 0.06 mm) and
  both of the E's slots (0.04 and 0.19 to 0.00).
  **The earlier doc's A notch did not reproduce on the lane:** the lane
  keeps the A's leg notch open at 50 mm whether the flag is off (0.80 mm)
  or on (0.88 mm). Only the satin tier closes it (0.06 mm off, 0.15 mm
  on). The A's counter does shrink: 1.56 to 1.23 mm² under the lane, and
  1.20 to 0.88 mm² without it.

**So shipping `coverage_edges` with the Column lane would cost Becker the
E's two slots and the R's stem-to-leg slot at a left-chest 80 mm. The lane
alone keeps all three open.** Weigh that against what the flag buys inside
the lane in #824: less bare satin, less uncovered ink, and a lower
`lost_frac` at 50 mm. Whether to make that trade is Kent's call.

## The numbers

Each cell is one digitize, at the Studio's six colours, left chest.

- Counter rows give sewn area in mm².
- Slot rows give the sewn minimum width in mm.
- The artwork value is in the first column.
- **Bold** marks a flag: a slot under 0.4 mm, or a counter under 0.16 mm²,
  where the artwork was at least that size.
- `bridged` means a stitch crosses the slot's mouth. The width is measured
  behind that stitch.

The full per-letter tables are in
`docs/renders/coverage-counters-2026-10-11/becker.md` (and `.json`).

### 80 mm

| feature (artwork) | shipped | coverage_edges | columns_words | coverage + columns |
|---|---|---|---|---|
| A counter (5.53 mm²) | 3.99 | 2.65 | 3.86 | 3.27 |
| R counter (6.07 mm²) | 3.66 | 2.25 | 3.87 | 2.13 |
| A leg notch (1.74 mm) | 1.33 | 0.83 | 1.40 | 1.35 |
| M top V (2.04 mm) | 1.58 | 0.66 | 1.38 | 0.77 |
| R bowl notch (1.79 mm) | 1.06 | 0.96 | 0.56 | 1.08 |
| R stem-to-leg slot (1.24 mm) | 0.69 | **0.19** | 0.59 | **0.26** |
| E upper slot (1.09 mm) | **0.39** | **0.37** | 0.70 | **0.39** bridged |
| E lower slot (1.29 mm) | 0.86 | **0.06** | 0.79 bridged | **0.24** |
| flags | 1 | 3 | 0 | 3 |

### 50 mm

| feature (artwork) | shipped | coverage_edges | columns_words | coverage + columns |
|---|---|---|---|---|
| A counter (2.17 mm²) | 1.20 | 0.88 | 1.56 | 1.23 |
| R counter (2.38 mm²) | 2.09 | 0.71 | 1.85 | 1.15 |
| A leg notch (1.09 mm) | **0.06** | **0.15** | 0.80 | 0.88 |
| M top V (1.26 mm) | 0.42 | **0.37** | **0.40** | **0.06** |
| R bowl notch (1.11 mm) | 0.43 | **0.35** | 0.52 | 0.56 |
| R stem-to-leg slot (0.79 mm) | **0.04** | **0.00** | **0.13** | **0.00** |
| N top notch (1.12 mm) | 0.55 | **0.28** | 0.49 | **0.29** |
| N lower notch (1.39 mm) | **0.10** | 0.44 | **0.34** | 0.56 |
| E upper slot (0.69 mm) | **0.00** | **0.00** | **0.04** bridged | **0.00** |
| E lower slot (0.79 mm) | **0.14** | **0.00** | **0.19** | **0.00** |
| flags | 5 | 7 | 5 | 5 |

### The control

**`coverage_edges` changes nothing on the opaque files, as it should.** It
reads alpha only. On `hotel_fremont` and `golden_tee` at 80 mm,
`--assert-inert shipped,coverage_edges` passes: the stitches are identical
and so is the table (`hotel_fremont.md`, `golden_tee.md`).

### Pictures

`becker-{50,80}mm-MARINE-{A,E}.jpg` show the four arms side by side, each as
a thread render of the letter. The artwork's edge is drawn in green and its
counters and slots in magenta.

## How it reads

- **Letters.** A letter is one connected component of one thread colour in
  the artwork. The artwork is read at its native resolution and scaled to
  the design's width, with alpha cut at its own 0.5 contour. A component
  counts as a letter when more than half of it lies under thread from a
  shape that either text tagger marked (`text_candidate`,
  `lettering_group` or `word_id`), so the set of letters does not change
  when `lettering_words` flips. BECKER is knocked out of a dark panel: its
  letters are bare cloth, not ink. So only MARINE's six letters are read.
- **The stitched side** is every needle-down segment of the thread colour
  that matches the letter, drawn as a ribbon 0.4 mm wide
  (`machine.COVERAGE_THREAD_W_MM`) on `stitchviz._frame`'s pixels. That is
  the footprint `render_design(lit=False)` paints, not the polygon. Both
  sides are read at 40 px/mm. They are aligned by the registration the ink
  instruments share, then refined to within 0.1 mm for each letter.
- **Counter**: an enclosed hole in the letter. Its sewn area is the area of
  the thread holes it overlaps.
- **Slot**: a concavity of the letter's hull whose depth is at least 0.2
  times the length of its mouth. Its width is the diameter of the largest
  disc that can travel from the slot's inner half out to its mouth band.
- **Tests** (`digitizer/tests/test_counter_slots.py`) use a synthetic ring
  with a 4.52 mm² counter and a synthetic E with two 0.8 mm slots. Each is
  read three ways: from the artwork, from the stitches, and end to end from
  a file on disk. Every reading lands within 5% on area and 0.05 mm on width
  (the slots read 0.787 mm). The tests also check that a closed counter, a
  pinched slot and a bridged mouth are flagged.

## What could be wrong

- **One fixture, one run per cell, and no sew-out.** The thread is modelled
  as a ribbon exactly 0.4 mm wide, and real thread spreads and pulls. So the
  absolute sewn widths are a model. What can be trusted is the
  **difference between arms**, because every arm goes through the same
  model.
- **It moves with the lane.** The first run of this instrument used `main`
  before #837 (the rail inset). There the lane's E slots read 0.49 mm, and
  `coverage_edges` took the A's leg notch at 50 mm from 0.48 to 0.10 mm.
  #837 widened the lane's slots, and the notch result went away. The
  80 mm verdict held in both runs.
- Becker's file is 146 px wide, so at 50 mm the artwork has about 2.9
  pixels per millimetre. Every 50 mm feature on the artwork side is a
  bilinear 0.5 contour of a few pixels.
- Thread within one thread width of the hull line is ignored when reading a
  slot's width. A narrowing made only by an arm's tip fattening at the
  mouth is therefore missed.
- The opaque fixtures' tables include many low-IoU letters (fine text at
  80 mm). There they serve only as the inert control and are not readings
  of those logos. Letters under IoU 0.25 are marked `unread`.

Re-run from `digitizer/` with the digitizer venv:

```
python -m tools.counter_slots --fixture becker --widths 50,80 \
  --arms shipped,coverage_edges,columns_words,coverage_columns \
  --out ../docs/renders/coverage-counters-2026-10-11 --crops MARINE:A,MARINE:E
python -m tools.counter_slots --fixture hotel_fremont --widths 80 \
  --out ../docs/renders/coverage-counters-2026-10-11 --assert-inert shipped,coverage_edges
python -m tools.counter_slots --fixture golden_tee --widths 80 \
  --out ../docs/renders/coverage-counters-2026-10-11 --assert-inert shipped,coverage_edges
```
