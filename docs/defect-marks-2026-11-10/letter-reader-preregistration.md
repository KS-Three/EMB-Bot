# Letter-fault reader: what is fixed before any result (2026-11-11)

The second reader scored against Kent's 2026-11-10 defect-marks pins, for
letters that **close up, merge or cannot be read**. Written and committed in
its own commit BEFORE the reader was run on any item that holds a relevant
pin, so nothing below was chosen by looking at how its flags fall against
those pins. The pins themselves had been read (they are in `SITTING.md`).
While it was built, the reader was run only on the five logos with NO
relevant pin (`L_becker_hat_large`, `L_tires_hat_3d`, `L_goldentee_hat`,
`L_precision_drone`, `L_toat_machine_hat`), to check its registration and
its flag counts; their flags are scored with the rest but carry no pin.
Those runs found three bugs, fixed before this page was committed: the art's
background colour equalled a thread colour (Becker's dark cutout, TOAT's
white field) and swallowed that thread's art; anti-aliased render edges
between black and white read as grey thread; and a white field sewn where the
art has no white (Becker's interiors) read its letters as closed bays.
After the fixes the five logos carry 0 (Becker), 0 (Tires), 5 (TOAT
machine), 7 (Golden Tee) and 157 (Precision Drone, whose shaded art breaks
into ~2,000 small colour pieces) flags. Drone's count was left alone: it is
what the rule reads on that art, and its chance figure would absorb it if it
had a pin.

The harness is `digitizer/tools/fault_reader_harness.py` (unchanged scoring,
`--fault letters`), the reader `digitizer/tools/letter_fault_reader.py`.
Results go in `docs/letter-fault-reader-2026-11-11.md`. The first reader's
page, `edge-reader-preregistration.md`, is the template; where this page
says nothing new, that page's rule holds.

## The question

Does a reader that says WHERE the thread closes a counter, joins two shapes
the art keeps apart, or closes a bay's mouth land on the spots Kent pinned as
"letters close up / merge / can't be read" more often than the same flags
land on points placed at random on the stitched area?

## Which pins count

The NOTE decides, the kind is a hint. Logo items only (`L_*`). Case-insensitive:

1. **Closure word in the note:** `spacing`, `space between`, `merg`, `hole`,
   `join`, `touch`, `intersect`, `closed up`, `filled in`.
2. **OR a read word on a letter:** the note matches `\bread`, `can't tell`,
   `cannot tell` or `can not tell` (so "thread" is not "read"), AND either the
   kind is `letter_shape` or the note names a letter (a quoted single letter
   or `&`, `letter`, `symbol`). "I cannot tell this is a drone" (kind
   `missing`) is a lost picture, not a letter, and is out.
3. **A pin the EDGE rule already claimed** is shared only when its own note
   names a closure too (rule 1). One pin passes: Gaulke 3, "The white spacing
   is not very apparent, and the edges are very jagged" names both faults.
   The two verdicts are separate tests, each on its own fault, so sharing a
   pin does not count it twice in either. Proseal 4 ("The M is jagged and n")
   names only an edge and stays the edge reader's.
4. **Kent's shorthand** (bare pins inheriting from a "same issue" note) as in
   the edge rule; no item's same-as note is a letter note, so it admits none.

Applied by `fault_reader_harness.select_letter_pins`; the list is
`letter-reader-pins.json` (14 pins on 6 logos: Bridge 2, 5, 6, 9, 10, 12;
Gaulke 2, 3, 6; Fremont 1, 2; MFab 10; Proseal 2; TOAT beanie 4), pinned by
`tests/test_letter_fault_reader.py`.

## What the reader flags

Per thread colour, the artwork the design was traced from (the prepped raster,
each pixel given its nearest spool, "unsewn" where stage 1's `bg_mask` says
background) against our own render of the stored design (every filament at
`render_design`'s width and endpoints, drawn in sew order as its colour with
no anti-alias), both on the render's 12 px/mm grid, registered through the
plan's own frame (no search; the dev runs' best integer shift was within
2 px, 0.17 mm). Numbers taken from `glyph_read`'s counter rule where it has one:

- **Counter lost:** an art hole that holds a circle of half a thread
  (0.2 mm) whose matching sewn hole (overlap >= 25% of the smaller, one to
  one) is missing, narrower than 0.2 mm, or narrower than HALF the art's
  width. Strength = art width - sewn width (mm).
- **Join:** two art shapes of one colour (each >= 0.12 mm2) whose thread is
  continuous across the line midway between them, where the art's gap is
  >= 0.2 mm, the thread there is wider than 1.5 filaments (0.6 mm; a single
  running stitch is travel, not a join), and one thread piece holds >= 0.05
  mm2 of each shape. Strength = the art gap covered (mm).
- **Bay closed:** a sewn hole >= 0.2 mm wide that overlaps no enclosed area
  of the art, lies at least half on the art's other-colour pixels (the
  mouth of an S or E shut), and is closed by a thread piece that sews a
  judged art shape of that colour (>= 0.05 mm2 of it). Strength = its width
  (mm).
- A shape is judged only when half its art pixels carry its thread in the
  render. No pull compensation (Kent marked the render). No merging of
  flags; each event is one flag.

Every constant is in the module's header and none is changed after a score.

## Radius, chance, pooling, verdict

All as the edge pre-registration, unchanged in the harness:

- **Radius 3.0 mm** (`RADIUS_MM`), 2.0 and 5.0 reported as sensitivity only.
  Kept: a letter on these hats is 3-10 mm tall, Kent's notes name a letter
  ("the B", "the e"), not a point on it, and a flag on the letter's counter or
  gap sits within 3 mm of a click anywhere on that letter.
- **Chance:** the same flags against as many random points as the item has
  relevant pins, uniform over the stitched area (thread pixels of our render
  at 12 px/mm, the edge reader's mask), 2,000 draws, seed 20261110. The
  edge-band null (thread within 1.0 mm of fabric) is reported beside it.
- **Pooled** pin-weighted over items, 95% bootstrap over ITEMS (5,000 draws).
  Strength AUC beside it (0.5 = chance).
- **Shown** means: at 3.0 mm the pooled (hit - chance) against the
  stitched-area null has its 95% item-bootstrap lower bound above 0. The
  edge-band null read the same way is the stronger claim. Anything else is
  **not shown**, recorded as a result, not retried with a new radius, rule or
  constant. With 14 pins on 6 items the interval will be wide; a "not shown"
  here is mostly a statement about power, and the write-up says so.
