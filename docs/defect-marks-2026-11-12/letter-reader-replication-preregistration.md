# Letter-fault reader replication: what is fixed before any result (2026-11-12)

Written and committed in its own commit BEFORE any item below is rendered,
pinned or scored. It freezes the letter-fault reader of PR #1389, its pin
rule and its pass line, and names the items a replication is scored on.
Nothing below may change after a pin or a flag on these items exists; a
change before then is an amendment appended to this file, dated, with its
reason.

The first result: 9 of 14 pins on 6 pro logos hit at 3 mm against 0.24 for
random points on the stitched area, item-bootstrap 95% CI [+0.08, +0.57],
"shown" by `docs/defect-marks-2026-11-10/letter-reader-preregistration.md`,
but leave-one-item-out loses the lower bound on 3 of the 6 logos
(`docs/letter-fault-reader-2026-11-11.md`). The same 14 pins chose the pin
rule, and the reader's three dev fixes were made on the other five logos of
that kit, so that result is not independent of its data.

## Held-out data that already exists

Every defect-marks sitting record was checked (`docs/defect-marks-2026-11-10/`,
`docs/defect-marks-2026-11-11/`; no other `marks.json` exists in the repo or in
the primary checkout's `digitizer/eye_pairs_out/`).

- **2026-11-10:** the six logos the first result came from, and five pro logos
  and four photos with no letter pin under the rule. Not held out.
- **2026-11-11:** 21 Commons logo rows, none in the first kit. The frozen rule
  selects 30 pins, all on ONE item (`C_silhouette_logo`: one note, "The
  lettering is extremely hard to read", and the 29 bare pins it covers). That
  hold-out was already scored on 2026-11-11 and recorded as **no verdict**
  (`docs/defect-marks-2026-11-11/SITTING.md`): one item makes the
  item-bootstrap interval a point, and 30 pins are one judgement.
- Two more 11-11 notes are about a letter but are NOT admitted by the frozen
  rule, and are not added: `C_comic_halftone` 1, "The N isn't an "N"" (no
  closure or read word), and `C_outline_lineart_logo` 1, "Hard to decipher
  the dot on the "I"" ("decipher" is not a read word in the rule). Adding them
  would be choosing pins after the rule, which is what this page forbids.

So the held-out data is one item. That gives no verdict under the pass line
below (it needs at least 5 items), so the replication needs a new sitting.

## The frozen reader

`digitizer/tools/letter_fault_reader.py` as merged in `79fa7646` (PR #1389).
Since then only its plumbing moved (`c65fcb14`, PR #1392: corpus rows `C_<slug>`
read through `tools.fault_reader_jobs`, the art path taken from the job's
spec). Its detection code is unchanged: the AST of `colour_classes`, `to_mm`,
`_holes`, `_deepest`, `counter_events`, `join_events`, `bay_events`,
`read_class`, `read_faults` and the constants below hashes to
`b5211fb9477b76af731d235562d5761e4b8dd4c2ff78d92b26a8e4268ca92870` at both
`79fa7646` and `bdae1860`. `tests/test_letter_reader_replication.py` pins
that digest, so an edit to any of them fails the suite.

| constant | value |
|---|---|
| `PXMM` | 12.0 px/mm (the review render's scale, the pins' frame) |
| `PAD_MM` | 2.0 |
| `THREAD_MM` | 0.4 (asserted equal to `stitchviz.THREAD_MM` by the worker) |
| `MIN_CLEAR_MM` | 0.2 (half a thread) |
| `KEEP_FRAC` | 0.5 |
| `MIN_SHAPE_MM2` | 0.12 |
| `OVERLAP` | 0.25 |
| `SEWN_FRAC` | 0.5 |
| `BRIDGE_MIN_MM` | 0.6 (1.5 threads) |
| `TOUCH_MM2` | 0.05 |
| `COLOUR_MERGE` | 12.0 (RGB distance) |

The worker refuses an item unless its re-run's stitches equal the stored
design's; a refused item is reported and carries no score, never re-run on
another tree.

## The frozen pin rule

`fault_reader_harness.select_letter_pins` (rules 1-4 of the 2026-11-10 letter
pre-registration), as merged in `79fa7646`, unchanged at `bdae1860`. The
NOTE decides: (1) a closure word (`spacing`, `space between`, `merg`, `hole`,
`join`, `touch`, `intersect`, `closed up`, `filled in`); or (2) a read word
(`\bread`, `can't tell`, `cannot tell`, `can not tell`) on a letter (kind
`letter_shape`, or the note names a quoted single letter, `&`, `letter` or
`symbol`); (3) a pin the edge rule claims counts only with a closure word too;
(4) bare pins (no note, no kind) inherit from the item's "same issue" note.
Item prefix `C_lt_` (the items below), so no earlier sitting's item can enter.

## The items

The nine public-domain lettering logos in
`digitizer/testdata/art/commons_lettering/` (Wikimedia Commons, provenance per
file in its `manifest.json` and `docs/asset-provenance.json`, committed
2026-11-01 in `b1c0b7c3` "for the next blinded sitting"). None has been in a
defect-marks sitting, so neither the pin rule nor the reader's dev fixes saw
a pin or a flag on them. Kent HAS seen them: they were population B of the
2026-11-02 pro-size-lettering pair sitting (left/right picks at hat_front
100 mm, no pins). The reader has never been run on them.

| item | file |
|---|---|
| `C_lt_bukit_asam` | `bukit_asam_logo_cmyk_01.png` |
| `C_lt_but_seriously` | `but_seriously_logo.png` |
| `C_lt_hed_p_e` | `hed_p_e_logo.png` |
| `C_lt_jakarta` | `jakarta_logo.png` |
| `C_lt_k_line` | `k_line_logo.png` |
| `C_lt_ahora` | `logo_ahora.png` |
| `C_lt_dot_music` | `music_logo.png` |
| `C_lt_n_sync` | `n_sync_logo.png` |
| `C_lt_and_pizza` | `pizza_logo.png` |

Each is digitized once, with the Studio's own request at 80 mm on left_chest
(`photo_corpus`'s `WIDTH_MM` / `GARMENT`, the request the 2026-11-11 kit used),
on the tree this lane holds when the kit is built (its sha goes in the kit),
one process at a time, and shown in `tools/defect_marks.py`'s page unchanged.
No size or item is chosen by looking at a render or a reader's flags. An item
whose digitize fails or has no stitches is listed as skipped, not replaced.

## Scoring

Unchanged in the harness (`digitizer/tools/fault_reader_harness.py`,
`--fault letters`), the same as the first result:

- **Radius 3.0 mm** (`RADIUS_MM`); 2.0 and 5.0 reported, never the verdict.
- **Chance null:** the same flags against as many random points as the item
  has selected pins, uniform over the stitched area (thread pixels of the
  render at 12 px/mm), 2,000 draws, seed 20261110 (`chance_area`). The
  edge-band null is reported beside it but not used: it read exactly 0.00 on
  Bridge and on `C_silhouette_logo`, which looks like an instrument fault on
  lettering sewn inside a field.
- **Candidate-pick null:** not available. This reader writes no candidate set
  (`"candidates"` in the flags file), and defining one now would be a new
  instrument. Not computed, not part of the verdict.
- **Pooled** pin-weighted over items, 95% bootstrap over ITEMS (5,000 draws,
  seed 20261110). Strength AUC beside it.

## Pass line

On the new sitting's pins ALONE (the 11-10 and 11-11 pins are never pooled
into it):

1. **No verdict** when fewer than **5 items** carry selected pins. With 5
   items, simulated from the first result's six items at its own effect, the
   lower bound clears 0 about half the time (below); fewer cannot test it.
2. Otherwise **shown** when BOTH, at 3.0 mm against `chance_area`:
   a. the pooled (hit - chance) has its item-bootstrap 95% lower bound above
      0 (the first result's line, unchanged); and
   b. the same holds with every rule-4 pin removed (each written note counted
      once, so a "same issue" note over 29 bare pins weighs as one pin).
3. **Not shown** otherwise, recorded as a result, not retried with a new
   radius, rule, size, null or constant.
4. A "shown" is called **fragile** when dropping any one item puts the lower
   bound of 2a at or below 0, as the first result was; **robust** otherwise.

Reported beside the verdict: per-item pins, flags, hits and chance; the misses
and the strongest unpinned flags; leave-one-out lower bounds; 2.0 and 5.0 mm.
None is a quality claim (ROADMAP gate 4); the verdict is about whether the
reader's flags land on Kent's pins more than chance, not about the designs.

## Power (why this is worth a sitting, and what it cannot do)

Simulated from the first result's six items (pins, chance, hit rate at 3 mm):
k items drawn with replacement, hits drawn binomially at each donor's rate
shrunk toward its chance by a factor s, 400 simulations, 1,000-draw item
bootstrap. P(lower bound of 2a above 0):

| items with pins | s = 1 (first effect) | s = 0.5 | s = 0 (no effect) | median CI width, s = 1 |
|---|---|---|---|---|
| 3 | 0.23 | 0.17 | 0.03 | 0.80 |
| 5 | 0.51 | 0.28 | 0.04 | 0.58 |
| 6 | 0.60 | 0.32 | 0.06 | 0.52 |
| 9 | 0.76 | 0.43 | 0.04 | 0.44 |
| 12 | 0.88 | 0.55 | 0.04 | 0.39 |

Nine items is the most this pool can give. On the first sitting, 6 of 11 pro
logos carried a letter pin under the rule; on the second, 1 of 21 Commons
rows. If 5 of the 9 carry pins, the sitting detects the first effect about
half the time and a half-size effect about a quarter of the time, so a "not
shown" from it is mostly a statement about power, and the write-up will say
so. A false "shown" with no effect at all runs about 4-6%.
