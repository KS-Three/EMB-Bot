# defect-marks-1112: the third sitting, 2026-11-13

Kent marked all 9 items of the kit `defect-marks-1112` (last save
2026-11-13 19:33 UTC; he said "done" the same day). It is the same page as the
first two sittings (`tools/defect_marks.py serve`, PR #1385): a grade for each
render, a pin on each fault (where it is, what kind, how bad, a note), and
ticks for problems that have no single spot.

The kit is the nine public-domain lettering logos in
`digitizer/testdata/art/commons_lettering/`. None of them had been pinned
before. The kit was built for one purpose: to replicate the letter-fault
reader (PR #1389) under the pre-registration committed first, in `ea13a362`
([`letter-reader-replication-preregistration.md`](letter-reader-replication-preregistration.md)).
Kent ruled "Sit as built" (2026-11-12). The page never shows the yardstick's
reading or any reader's flags, so his marks are blind to both. They are not
blind to the art itself: he saw these designs as eye pairs on 2026-11-02.

Every figure below is either his own answer or an instrument reading on tree
`ea13a362`. None of it is a quality claim (ROADMAP gate 4).

## What is in this folder

- `marks.json`: his answers exactly as the server stored them. It is a
  byte-for-byte copy of the primary checkout's
  `digitizer/eye_pairs_out/defect-marks-1112/marks.json`, made before anything
  read it; both have sha256 `12e74bff709304a6fed27f324a481ac26179e08e5b7ea0db587d09938bdf9c9c`.
  Its `kit_sha256` is `f824c55c…`, the same as `kit.json`.
- `kit.json`: the item list and the yardstick's reading of each item.
- `letter-reader-replication-score.json`: the score from the registered
  scorer `score_replication.py`.
- `C_lt_bukit_asam.flags.json` and `C_lt_n_sync.flags.json`: the frozen
  reader's flags on the two items that carry a selected pin.
- `build_kit.py`, `score_replication.py`: the kit driver and the scorer, both
  unchanged since #1415.
- No pictures. The kit's `img/` stays in the gitignored
  `digitizer/eye_pairs_out/defect-marks-1112/` on Kent's machine.

To rerun the table below, from `digitizer/`:

    python -m tools.defect_marks report --kit ../docs/defect-marks-2026-11-12

## Grades beside the yardstick

All 9 items are answered: 8 with pins, and `C_lt_but_seriously` marked
"Nothing wrong". There are 60 pins in all. `step` is Kent's grade minus the
preflight letter, with A..F mapped to Great..Terrible; a step above 0 means
the yardstick was kinder than Kent.

| item | Kent | yardstick (score) | step | pins (ruins) | his pins by kind | yardstick findings |
|---|---|---|---|---|---|---|
| C_lt_bukit_asam | Bad | D (52) | +0 | 5 (3) | direction 1, mushed 1, other 1, unnamed 2; not_for_thread | LETTERING_TOO_SMALL 1, STITCHES_TOO_SHORT 1, THREAD_MATCH_POOR 1, TRIM_HEAVY 1 |
| C_lt_but_seriously | Great | B (76) | -1 | 0 (0) | - | LETTERING_TOO_SMALL 1, SATIN_GAPS_TIGHT 1, TRIM_HEAVY 1 |
| C_lt_hed_p_e | Okay | B (88) | +1 | 3 (0) | mushed 2, stitch_type 1 | LETTERING_TOO_SMALL 1, SATIN_GAPS_TIGHT 1 |
| C_lt_jakarta | Bad | C (64) | +1 | 9 (0) | other 1, unnamed 7, wavy 1; not_for_thread | ARTWORK_UNCOVERED 1, LETTERING_TOO_SMALL 1, STITCHES_TOO_SHORT 1, TRIM_HEAVY 1 |
| C_lt_k_line | Okay | B (88) | +1 | 7 (0) | missing 2, mushed 1, other 2, pen_flow 1, unnamed 1 | ARTWORK_UNCOVERED 1, LETTERING_TOO_SMALL 1 |
| C_lt_ahora | Good | D (46) | -2 | 3 (0) | missing 1, stitch_type 2 | DENSITY_STACKED 1, GROUND_SEWN 1, LETTERING_TOO_SMALL 1, SATIN_GAPS_TIGHT 1 |
| C_lt_dot_music | Okay | A (100) | +2 | 3 (0) | jagged 1, mushed 2 | - |
| C_lt_n_sync | Good | B (88) | +0 | 7 (0) | blob 1, pen_flow 2, unnamed 4 | THREAD_MATCH_POOR 1 |
| C_lt_and_pizza | Okay | A (100) | +2 | 23 (0) | gap 1, jagged 1, missing 3, unnamed 18 | ARTWORK_UNCOVERED 1 |

Pins by kind across all items: unnamed 32, mushed 6, missing 6, other 4,
stitch_type 3, pen_flow 3, jagged 2, direction 1, wavy 1, blob 1, gap 1.

## What his notes are about

Read from the notes, not counted by any rule:

- **Straight and flat edges on letters:** the I, the Z and the E
  ("should be perfectly flat", "not a crisp rectangular edge").
- **Smooth curves:** `and_pizza`'s 14 bare pins ("#6-#19 not a smooth
  radiused edge"), and "all of the letters are jagged" on `dot_music`.
- **Letters out of line:** on `jakarta` and `bukit_asam`, "the letters jumped
  in elevation", across 8 and 3 pins.
- **Stitch type or angle changing inside one shape:** `hed_p_e`, `ahora`,
  `k_line` and `n_sync`.
- **Shapes that came out as the wrong shape:** the gear on `ahora`, the red
  box on `k_line`, the notch on `dot_music`.

Only two notes are about closure (letters merging, joining, or a counter
filled in), and the frozen rule selects exactly those two.
