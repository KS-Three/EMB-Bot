# Does `coverage_edges` close counters and slots? Becker, 2026-10-11

Waiting-on-Kent item 38 asks whether `coverage_edges` should ship with the
Column lane. `docs/coverage-edges-under-columns-2026-10-11.md` saw in the
pictures that the A's counter and leg notch closed and the E's lower slot
narrowed, but did not measure them. This doc measures them with a new
instrument, `digitizer/tools/counter_slots.py`. **All three flags stay OFF.
Nothing was sewn.**

## Verdict (one minute)

**Yes. `coverage_edges` closes slots that the path without it keeps open. It
is clearest at 80 mm, and the Column lane does not protect against it.**

- **80 mm, with the Column lane:** `coverage_edges` takes three slots from
  open to under one thread (0.4 mm). The E's lower slot goes 0.49 → 0.04 mm,
  the E's upper slot 0.49 → 0.19 mm, and the R's leg slot 0.41 → 0.04 mm.
  The lane alone has **0** flags; with `coverage_edges` it has **3**.
  Without the lane it does the same thing: E lower 0.86 → 0.06 mm, R leg
  0.69 → 0.19 mm, and flags go from 1 to 3.
- **Counters never close in any cell.** The smallest sewn counter is 0.71
  mm², against the 0.16 mm² closing line. They do shrink, though. At 80 mm
  under the lane, `coverage_edges` takes the A's counter 3.03 → 2.46 mm²
  (−19%) and the R's 3.01 → 1.76 mm² (−42%).
- **50 mm is already lost without the flag.** Every arm narrows 5 to 7
  slots, because MARINE's slots there are 0.7 to 1.4 mm wide in the
  artwork. The flag adds 1 to 2 flags on top. The one the earlier doc saw
  is real: the **A's leg notch is 0.48 mm under the lane and 0.10 mm with
  `coverage_edges`**. The M's top V goes 0.45 → 0.24 mm.

So shipping `coverage_edges` with the Column lane would cost Becker's E both
its slots and the R its leg slot at a left-chest 80 mm. The lane alone keeps
all three open. That is a measured cost against the lane's gains in #824
(fewer long crosses, less bare satin, lower `lost_frac`). Whether to take
the trade is Kent's call.

## The numbers

Each cell is one digitize, at the Studio's six colours, left chest. Counter
values are artwork / sewn area in mm². Slot values are artwork / sewn
minimum width in mm. A **bold** value is a flag: a slot under 0.4 mm, or a
counter under 0.16 mm², where the artwork was at least that. The full
per-letter tables are in `docs/renders/coverage-counters-2026-10-11/becker.md`
(and `.json`).

### 80 mm

| feature (artwork) | shipped | coverage_edges | columns_words | coverage + columns |
|---|---|---|---|---|
| A counter (5.53 mm²) | 3.99 | 2.65 | 3.03 | 2.46 |
| R counter (6.07 mm²) | 3.66 | 2.25 | 3.01 | 1.76 |
| A leg notch (1.74 mm) | 1.33 | 0.83 | 1.30 | 0.88 |
| M top V (2.04 mm) | 1.58 | 0.66 | 1.16 | 0.88 |
| R leg slot (1.24 mm) | 0.69 | **0.19** | 0.41 | **0.04** |
| E upper slot (1.09 mm) | **0.39** | **0.37** | 0.49 | **0.19** (bridged) |
| E lower slot (1.29 mm) | 0.86 | **0.06** | 0.49 (bridged) | **0.04** |
| flags | 1 | 3 | 0 | 3 |

### 50 mm

| feature (artwork) | shipped | coverage_edges | columns_words | coverage + columns |
|---|---|---|---|---|
| A counter (2.17 mm²) | 1.20 | 0.88 | 1.11 | 0.75 |
| R counter (2.38 mm²) | 2.09 | 0.71 | 1.26 | 0.92 |
| A leg notch (1.09 mm) | **0.06** | **0.15** | 0.48 | **0.10** |
| M top V (1.26 mm) | 0.42 | **0.37** | 0.45 | **0.24** |
| R bowl notch (1.11 mm) | 0.43 | **0.35** | **0.32** | 0.41 |
| N top notch (1.12 mm) | 0.55 | **0.28** | **0.24** | **0.29** |
| N lower notch (1.39 mm) | **0.10** | 0.44 | **0.14** | **0.17** |
| R leg slot (0.79 mm) | **0.04** | **0.00** | **0.00** | **0.00** |
| E upper slot (0.69 mm) | **0.00** | **0.00** | **0.00** | **0.00** |
| E lower slot (0.79 mm) | **0.14** | **0.00** | **0.04** | **0.00** |
| flags | 5 | 7 | 6 | 7 |

The controls: **`coverage_edges` is inert on the opaque files, as it should
be.** It reads alpha only. On `hotel_fremont` and `golden_tee` at 80 mm,
`--assert-inert shipped,coverage_edges` passes. The stitches are identical
and so is the table, in `hotel_fremont.md` and `golden_tee.md`.

Pictures: `becker-{50,80}mm-MARINE-{A,E}.png`. Each shows the four arms side
by side as the thread render of the letter. The artwork's edge is drawn in
green, and its counters and slots in magenta.

## How it reads

- **Letters.** A letter is one connected component of one thread colour in
  the artwork. It is read at its native resolution and scaled to the
  design's width. Alpha is cut at its own 0.5 contour. A component counts
  as a letter when more than half of it lies under thread from a shape that
  either text tagger marked (`text_candidate`, `lettering_group` or
  `word_id`). That way the set does not change when `lettering_words`
  flips. BECKER is knocked out of a dark panel, so its letters are cloth,
  not ink, and only MARINE's six letters are read.
- **The stitched side** is the needle-down segments of the colour that
  covers the letter. Each segment is drawn as a ribbon 0.4 mm wide
  (`machine.COVERAGE_THREAD_W_MM`) on `stitchviz._frame`'s pixels. That is
  the footprint `render_design(lit=False)` paints, not the polygon. Both
  sides are read at 40 px/mm. The two are aligned with the registration the
  ink instruments share, then refined to ±0.1 mm for each letter.
- **Counter**: an enclosed hole in the letter. Its sewn area is the area of
  the thread holes it overlaps.
- **Slot**: a concavity of the letter's hull that is at least 0.2 times as
  deep as its mouth is wide. Its width is the diameter of the largest disc
  that can travel from the slot's inner half out to its mouth band. One
  stitch laid across the mouth does not count as narrowing. It is reported
  as `bridged`.
- **Tests** (`digitizer/tests/test_counter_slots.py`): a synthetic ring and
  a synthetic E are read three ways, from artwork, from stitches, and end to
  end from a file on disk. The ring has a 4.52 mm² counter and the E has two
  slots 0.8 mm wide. Every reading lands within 5% and 0.05 mm (0.787 mm for
  the slots). The tests also cover a closed counter, a pinched slot, and a
  bridged mouth.

## What could be wrong

- **One fixture, one run per cell, and no sew-out.** The thread is modelled
  as a ribbon exactly 0.4 mm wide. A real sew-out spreads and pulls, so the
  sewn widths are a model and not a measurement of cloth. What this
  measures reliably is the **difference** between arms, since every arm
  goes through the same model.
- Becker's file is 146 px wide, so at 50 mm its artwork carries about 2.9
  px/mm. The artwork side of every 50 mm feature is the bilinear 0.5
  contour of a few pixels.
- Thread lying within one thread width of the hull line is ignored for
  width. So a narrowing caused only by an arm's tip thickening at the mouth
  is missed.
- The opaque fixtures' tables include low-IoU letters (fine text at 80 mm).
  They serve only as the inert control here, and are not readings of those
  logos. Letters under IoU 0.25 are marked `unread`.

Re-run, from `digitizer/` with the digitizer venv:

```
python -m tools.counter_slots --fixture becker --widths 50,80 \
  --arms shipped,coverage_edges,columns_words,coverage_columns \
  --out ../docs/renders/coverage-counters-2026-10-11 --crops MARINE:A,MARINE:E
python -m tools.counter_slots --fixture hotel_fremont --widths 80 \
  --out ../docs/renders/coverage-counters-2026-10-11 --assert-inert shipped,coverage_edges
python -m tools.counter_slots --fixture golden_tee --widths 80 \
  --out ../docs/renders/coverage-counters-2026-10-11 --assert-inert shipped,coverage_edges
```
