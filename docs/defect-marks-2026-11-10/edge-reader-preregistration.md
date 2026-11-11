# Edge-fault reader: what is fixed before any result (2026-11-10)

Written and committed BEFORE the reader was run on any item, so nothing below
was chosen by looking at how a reader scored against Kent's pins. The pins
themselves had been read (they are in `SITTING.md`); the reader's output had
not. The harness is `digitizer/tools/fault_reader_harness.py`, the reader
`digitizer/tools/edge_fault_reader.py`. Results go in
`docs/edge-fault-reader-2026-11-10.md`.

## The question

Does a reader that says WHERE a sewn edge wobbles land on the spots Kent
pinned as "this edge should be smooth" more often than the same flags land on
points placed at random? A flag "hits" a pin when it lies within the radius.

## Radius: 3.0 mm, fixed

- `edge_wobble.WINDOW_MM` is 3.0: the instrument cannot say where a wobble is
  any finer than its own high-pass window.
- Kent clicked a 12 px/mm render shown scaled to his screen, and many notes
  name a stretch, not a point ("the border around this logo", "all of the
  letters edges"). A sub-millimetre radius would score his aim, not the reader.
- Larger than ~3 mm and one flag covers a whole small letter on a 60 mm hat.

2.0 and 5.0 mm are reported beside it as sensitivity rows. The verdict is read
at 3.0 mm only.

## Which pins count ("relevant pins")

The NOTE decides; the kind is a hint (SITTING.md: the kind he picked and the
note he typed often disagree). Logo items only (`L_*`); the 4 photos are out of
scope (Terrible, almost no pins). A pin is relevant when, case-insensitive:

1. **Edge word in the note.** The note contains one of `jag`, `smooth`,
   `crisp`, `sawtooth`, `stair`, `wav`, `wobbl`, `lump`, `bump`, `straight`,
   `flat` (stems, so "jagged", "jaged", "wavey" all match).
2. **OR edge kind, note not naming another fault.** The kind is `jagged`,
   `wavy` or `lumpy_curve`, and the note names none of `gap`, `missing`,
   `colour`/`color`, `spacing`, `read`, `stitch`.
3. **EXCEPT stitching, not an edge.** A pin passing only through rule 1 whose
   note is about the stitches rather than an edge (it contains `stitch` and
   none of `edge`, `border`, `circle`, `outline`, `curve`, `line`, `letter`)
   is dropped. This is written for MFab pin 7, "The stitching isn't smooth,
   it has no flow here" (kind `mushed`): stitch flow, which an edge reader
   does not claim to see.
4. **Kent's own shorthand.** A pin with no note and no kind on an item where a
   noted pin says the bare marks are the same issue ("marks 1-4 are te same
   issue", Tires) inherits that pin's relevance. Golden Tee's "same for 1-20"
   pins inherit too; that note is about bean stitching, so they are not
   relevant.

Applied to `marks.json` by `fault_reader_harness.select_edge_pins`; the
resulting list is committed as `edge-reader-pins.json` beside this file so it
can be audited pin by pin.

## Chance

The SAME flags, scored against random points instead of Kent's pins: as many
points as the item has relevant pins, drawn uniformly over the item's stitched
area (pixels of our render at 12 px/mm that carry thread), 2,000 draws, seed
20261110. The item's chance figure is the mean hit rate over the draws.

A second, harder null is reported beside it: random points drawn only from the
stitched area's EDGE BAND (thread pixels within 1.0 mm of fabric). Kent's
edge pins sit on edges by construction, and a reader that merely flags edges
everywhere would beat the stitched-area null for free. Beating the edge-band
null says the reader knows WHICH edges.

## Pooled, clustered by item

Pooled hit rate = all hits / all relevant pins. Pooled chance = sum over items
of (pins x chance rate) / all pins. The confidence interval on (hit - chance)
is a 95% bootstrap over ITEMS (resample items with replacement, 5,000 draws,
seed 20261110), because pins on one design are not independent. Also
reported, threshold-free: the probability that a relevant pin's local flag
strength (strongest flag within the radius, 0 if none) beats a random
stitched-area point's, ties half (0.5 = chance).

## Flags: the reader's own cut, not tuned on pins

The reader flags an edge penetration whose high-passed deviation exceeds
`edge_wobble.OVER_MM` (0.15 mm, the instrument's pre-existing "visible" line)
and merges flags within 2.0 mm of a stronger one (the instrument's own `worst`
de-duplication distance). Strength = the cluster's largest |deviation| in mm.
Neither number is changed after seeing results.

## Verdict rule

"Finds what he pointed at better than chance" means: at 3.0 mm the pooled
(hit - chance) against the stitched-area null has a 95% item-bootstrap lower
bound above 0. The edge-band null is read the same way and reported as the
stronger claim. Anything else is "not shown", and that is recorded as a
result, not retried with a new radius.
