# defect-marks-1111: the second sitting, 2026-11-11

Kent marked all 21 items of the kit `defect-marks-1111` on 2026-11-11 (last
save 16:39 UTC). The page is `tools/defect_marks.py serve` (PR #1385), the same
page as the first sitting (`docs/defect-marks-2026-11-10/SITTING.md`): an
absolute grade per render, a pin on each fault (where, what kind, how bad, a
note) and ticks for problems with no single spot.

The kit is the 21 Commons logo rows of the photo corpus, none of them in the
first kit. It was built for one purpose: fresh pins to test the letter-fault
reader (PR #1389) on designs its pin rule and constants had never seen. The
page never receives the yardstick's reading or any reader's flags, so his marks
are blind to both. They are NOT blind to the designs: he graded the same 21
artworks on 2026-10-28 (an older tree, a different render, no pins).

Every figure below is his own answer or an instrument reading on one tree
(`950855bf`), not a quality claim (ROADMAP gate 4).

## What is in this folder

- `marks.json`: his answers as the server stored them (sha256 `1487a735...`).
  Pin positions as in the first sitting: `x_mm`, `y_mm` in the design frame from
  the render's top-left corner, 2 mm pad included.
- `kit.json`: the item list and the yardstick's reading of each item, kit
  sha256 `d6f844cd...`; `marks.json` carries the same `kit_sha256`.
- `letter-reader-holdout-pins.json`: the pins the frozen letter rule selects
  from these marks.
- `letter-reader-holdout-score.json`: the harness's score of the frozen reader
  against them.
- `C_silhouette_logo.flags.json`: the reader's 65 flags on the one item scored.
- `run_reader_corpus.py`: the driver that ran the merged reader on a corpus
  row. The reader's `run` is wired to the pro jobs; the driver changes where
  the artwork is read from and the item prefix, nothing else.
- No pictures. The kit's `img/` stays in the gitignored
  `digitizer/eye_pairs_out/defect-marks-1111/` on Kent's machine.

Rerun the side-by-side table from `digitizer/`:

    python -m tools.defect_marks report --kit ../docs/defect-marks-2026-11-11

## The kit

21 Commons logo styles, each at the corpus request (left chest, 80 mm), from
the finished capture `corpus_runs/main-950855b` (all 39 corpus rows; the 18
photo rows were left out on purpose and are listed under `skipped`). The first
sitting showed that a photo this far off gives pins nothing to point at.

## Grades beside the yardstick

`step` is Kent's grade minus the preflight letter mapped A..F to
Great..Terrible; above 0 means the yardstick was kinder than Kent.

| item | size | Kent | yardstick | step | pins | no kind | whole-design ticks |
|---|---|---|---|---|---|---|---|
| `C_pixel_art_sprite` | 80.6 x 57.0 mm on left_chest | Good | A 100 | +1 | 1 | 0 | - |
| `C_low_poly` | 80.0 x 49.4 mm on left_chest | Bad | F 0 | -1 | 11 | 0 | not_for_thread |
| `C_arabic_calligraphy` | 80.2 x 63.2 mm on left_chest | Good | C 64 | -1 | 3 | 0 | - |
| `C_qr_code` | 80.5 x 80.5 mm on left_chest | Terrible | D 46 | +1 | 3 | 0 | not_for_thread |
| `C_barcode` | 39.0 x 18.4 mm on left_chest | Terrible | F 34 | +0 | 0 | 0 | unrecognizable, colours_off, detail_lost, not_for_thread |
| `C_heraldic_crest` | 80.6 x 100.9 mm on left_chest | Bad | F 28 | -1 | 4 | 0 | too_busy |
| `C_flat_emoji_icon` | 80.3 x 91.3 mm on left_chest | Good | B 76 | +0 | 3 | 0 | - |
| `C_silhouette_logo` | 80.4 x 80.4 mm on left_chest | Bad | D 40 | +0 | 32 | 29 | - |
| `C_distressed_grunge` | 80.6 x 80.5 mm on left_chest | Terrible | A 100 | +4 | 0 | 0 | detail_lost, not_for_thread |
| `C_halftone_dots` | 80.6 x 111.9 mm on left_chest | Terrible | B 88 | +3 | 0 | 0 | unrecognizable, detail_lost, not_for_thread |
| `C_neon_outline_sign` | 79.9 x 40.0 mm on left_chest | Good | B 76 | +0 | 5 | 0 | - |
| `C_duotone_poster` | 75.1 x 96.8 mm on left_chest | Terrible | B 76 | +3 | 0 | 0 | unrecognizable, too_busy, not_for_thread |
| `C_isometric_icon` | 80.6 x 51.2 mm on left_chest | Bad | B 76 | +2 | 10 | 2 | too_busy, detail_lost |
| `C_comic_halftone` | 77.7 x 99.8 mm on left_chest | Terrible | F 0 | +0 | 1 | 0 | unrecognizable, too_busy, detail_lost, not_for_thread |
| `C_devanagari_logo` | 80.2 x 44.3 mm on left_chest | Okay | B 88 | +1 | 8 | 2 | - |
| `C_kanji_seal` | 80.4 x 80.3 mm on left_chest | Bad | B 88 | +2 | 28 | 27 | too_busy, not_for_thread |
| `C_vintage_engraved_badge` | 78.0 x 58.4 mm on left_chest | Terrible | C 64 | +2 | 0 | 0 | unrecognizable, detail_lost |
| `C_gradient_mascot` | 80.3 x 97.3 mm on left_chest | Great | C 70 | -2 | 3 | 1 | - |
| `C_outline_lineart_logo` | 79.3 x 46.0 mm on left_chest | Great | B 76 | -1 | 2 | 0 | - |
| `C_kanji_brush` | 65.4 x 65.3 mm on left_chest | Terrible | F 0 | +0 | 0 | 0 | unrecognizable, too_busy, detail_lost |
| `C_chalkboard_lettering` | 80.6 x 60.6 mm on left_chest | Terrible | B 88 | +3 | 1 | 0 | unrecognizable, too_busy, detail_lost |

- **Grades:** Great 2, Good 4, Okay 1, Bad 5, Terrible 9. All 21 graded.
- **Step, 21 items:** 0 on 6, yardstick kinder on 10, yardstick harsher on 5.
  The widest: `C_distressed_grunge` Terrible against A 100 (+4);
  `C_halftone_dots`, `C_duotone_poster` and `C_chalkboard_lettering` Terrible
  against B (+3); `C_gradient_mascot` Great against C 70 (-2).
- **Rank agreement, his grade against the preflight score:** Spearman +0.18
  (n 21). On his 2026-10-28 grades of the same artworks it was 0.00
  (`.claude/memory/defect-marks-sitting-2026-11-10.md`). Neither is distinguishable
  from no relation at this n.
- **Against his own 2026-10-28 grades of the same 21 artworks:** Spearman
  +0.77; same grade 9, worse now 11, better now 1. This is NOT a test-retest:
  the tree moved (`5ff48c56` to `950855bf`), the render is drawn differently,
  and this page shows the artwork beside it and asks for faults. The widest
  drops: `C_duotone_poster` and `C_comic_halftone` Good to Terrible,
  `C_heraldic_crest` and `C_silhouette_logo` Good to Bad. Whether the designs
  got worse or the page makes him stricter is not separable from this record.

## What he pinned

115 pins on 15 of the 21 items; 6 items carry none (all 6 Terrible).

| kind | pins |
|---|---|
| extra | 13 |
| pen_flow | 9 |
| mushed | 7 |
| missing | 7 |
| blob | 7 |
| colour | 4 |
| gap | 3 |
| stitch_type | 1 |
| direction | 1 |
| other | 1 |
| letter_shape | 1 |
| no kind chosen | 61 |

How bad: noticeable 30, nitpick 20, ruins 1, not chosen 64.
Whole-design ticks: not_for_thread 8, detail_lost 8, unrecognizable 7,
too_busy 7, colours_off 1.

### Reading the notes (this section is the session's reading, not Kent's)

The words differ from the first sitting. "Jagged", "smooth", "spacing" and
"merge" barely appear; the repeated complaints here are:

- **Extra stitches in lettering:** 30 pins on `C_silhouette_logo` (pin 3 and
  the 29 bare pins it covers: "all of the extra green stitches (#3 - #32) are
  the same issue").
- **The same feature treated differently in different places:** 28 pins on
  `C_kanji_seal` ("extra in-fill, some empty spaces have it while others
  don't"), 3 on `C_devanagari_logo` ("the only lettering in-fill, it doesn't
  match the rest"), and one note each on `C_pixel_art_sprite` (bean stitch
  round some openings and not others), `C_gradient_mascot` (one nostril, feet
  of two colours) and `C_flat_emoji_icon` (one leg's fill direction).
- **Random spots:** 7 "Random Black Spot" pins on `C_low_poly`.
- **Pieces missing:** `C_qr_code` 3, `C_arabic_calligraphy` 2,
  `C_heraldic_crest` (the eye, the crown), and the whole-item reasons of
  `C_distressed_grunge` and `C_duotone_poster`.
- **Flow:** 9 pen_flow pins (`C_neon_outline_sign` 4, `C_devanagari_logo` 4,
  `C_arabic_calligraphy` 1) and the reasons of `C_kanji_seal` and
  `C_kanji_brush` ("no flow").

One note is a request, not a fault: `C_low_poly` pin 2 asks for an
investigation of border stitches that carry a colour change.

## The letter-fault reader on these pins (hold-out)

The reader (`digitizer/tools/letter_fault_reader.py`) and its pin rule
(`fault_reader_harness.select_letter_pins`) were used as merged in `79fa7646`,
no constant changed, from a detached checkout of that commit. Kent's marks were
complete and backed up before the rule or the reader was run on them.

- **Pins the rule selects:** 30, all on `C_silhouette_logo`: pin 3 by rule 2
  ("hard to read" on lettering) and pins 4-32 by rule 4 (bare pins that inherit
  a "same issue" note). No other item's pins match the rule's words. The edge
  rule selects 0.
- **Reader on that item:** the re-run's stitches equal the stored design's;
  65 flags (counter_lost 52, join 11, bay_closed 2).
- **Score at the pre-registered 3 mm:** 26 of 30 pins have a flag within reach
  (0.87) against 0.13 for random points on the stitched area. At 2 mm 21 of 30
  (0.70 against 0.08); at 5 mm 30 of 30 (1.00 against 0.20). Strength AUC 0.90.

**Verdict: no verdict. The hold-out is consistent with the first result and
does not confirm it.** Reasons, all structural:

1. One item. The harness resamples by item, so with one item its interval is a
   point; the pre-registered rule for "shown" cannot be applied.
2. The 30 pins are one judgement written once, not 30 independent ones.
3. All 30 pins lie in the lettering band (about 43 x 14 mm of an 84 x 84 mm
   render) and 64 of the 65 flags lie in the same band. The area null spreads
   random points over the whole design, bear included, so 0.13 measures "the
   reader found the lettering", which it did. Inside the band the flags are
   dense enough that nearly any point is within 3 mm of one, so this record
   says nothing about whether the reader finds WHICH letter is wrong.
4. The harness's edge-band null reads 0.00 here, as it did on Bridge in the
   first score. A null of exactly zero beside 65 flags on thread looks like an
   instrument fault and is not used above.

What the hold-out does show: on a design outside the rule's and the reader's
development set, Kent called the lettering the only thing wrong and the reader
put 64 of its 65 flags on the lettering.

## Gaps in the record

- **61 pins have no kind.** At least 56 are deliberate shorthand:
  `C_silhouette_logo` 29 (covered by pin 3's note) and `C_kanji_seal` 27
  (covered by pin 1's "#1-#28"). The file keeps them bare.
- **64 pins have no severity**, mostly the same bare pins.
- **`C_heraldic_crest` and `C_silhouette_logo` were graded in a second pass.**
  The page read 19 of 21; the session told him which two had pins and a reason
  but no grade, and he graded them. He was not shown the yardstick or the
  reader in between.
- **`C_comic_halftone`'s reason was typed last** (16:39:52 UTC, 35 seconds
  after his "done"). No pin or grade changed in that save; the pin rule and the
  reader were run after it.
- **The reader was run on 1 of the 21 items**, the only one with selected
  pins. Its flags on the other 20 are unknown.
- **One sitting, one tree, no repeats**, and he had seen these 21 artworks
  before.

## Kent's words, per item (verbatim)

### `C_pixel_art_sprite` - Good

Reason: "The only reason it didn't reeceive a greatem is becuase some of the interior opening have bean stitches, while others dont."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 20.13, 36.82 | stitch_type | noticeable | The interior gaps are inconsistant, some have bean stitching around the openings, while the other doesn't |

### `C_low_poly` - Bad

Reason: "The digitized image almost looks like abstract art, like a pacaso."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 72.45, 35.75 | mushed | ruins | These details get lost, all of the shapes are triangles but the digitizer some how rounded to tips off. |
| 2 | 37.61, 5.94 | colour | nitpick | The change in bean stitch bordering looks off, though it matches the photo... You should have an agent investigate how to do border stitches that contain color changes |
| 3 | 11.45, 26.72 | mushed | noticeable | All detail in these fine shapes is lost. |
| 4 | 54.09, 20.08 | extra | noticeable | Random Black Spot |
| 5 | 34.33, 12.72 | extra | noticeable | Random Black Spot |
| 6 | 21.29, 28.39 | extra | noticeable | Random Black Spot |
| 7 | 19.83, 18.48 | extra | noticeable | Random Black Spot |
| 8 | 20.56, 21.76 | extra | noticeable | Random Black Spot |
| 9 | 67.93, 27.95 | extra | noticeable | Random Black Spot |
| 10 | 44.03, 9.15 | extra | noticeable | Random Black Spot |

Pins with no note (1): mushed 1.

### `C_arabic_calligraphy` - Good

Reason: "90% of the way there"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 2 | 70.41, 9.76 | missing | nitpick | missing line |
| 3 | 6.73, 15.89 | missing | nitpick | missing line |

Pins with no note (1): pen_flow 1.

### `C_qr_code` - Terrible

Reason: "This is real bad, pieces missing entirely, stitching that is rounded (when the image is made of squares)"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 8.98, 69.99 | missing | noticeable | Entire black square and black border is missing |
| 2 | 8.48, 27.41 | missing | noticeable | Entire black square and black border is missing |
| 3 | 71.24, 28.32 | missing | noticeable | Entire black square and black border is missing |

### `C_barcode` - Terrible

Reason: "I can't even tell what is happenign here."

### `C_heraldic_crest` - Bad

Reason: "The fine detail got drowned out on this one."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 41.37, 9.98 | missing | nitpick | Missing the eye |
| 2 | 40.87, 32.71 | mushed | noticeable | The crown is missing |
| 3 | 36.5, 13.12 | blob | noticeable | Can't tell what this is |
| 4 | 40.77, 69.15 | mushed | nitpick | Missing the eye |

### `C_flat_emoji_icon` - Good

Reason: "Overall, this is one of the better digitized images"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 58.19, 0.43 | gap | nitpick | The bean stitch didn't cover to tip of the horn |
| 2 | 37.56, 55.53 | gap | nitpick | The bean stitch didn't cover to tip of the horn |
| 3 | 74.97, 82.22 | direction | noticeable | right leg infill doesn't match left leg |

### `C_silhouette_logo` - Bad

Reason: "Everything looks good besides the lettering"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 50.84, 35.09 | other | nitpick | The border isn't tight to the bear |
| 3 | 19.02, 57.86 | mushed | noticeable | The lettering is extremely hard to read, all of the extra green stitches (#3 - #32) are the same issue |

Pins with no note (30): (no kind) 29, colour 1.

### `C_distressed_grunge` - Terrible

Reason: "It's missing the entire center logo, along with the "MACHINE" on the bottom is missing"

### `C_halftone_dots` - Terrible

Reason: "Too many detail points lost"

### `C_neon_outline_sign` - Good

Reason: "This one is pretty good, just a few areas that require flow improvement."

Pins with no note (5): pen_flow 4, extra 1.

### `C_duotone_poster` - Terrible

Reason: "The entire top portion got lost, and the bottom is distorted"

### `C_isometric_icon` - Bad

Reason: "The border stitches do not help define some of the gradient transitions"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 6 | 50.78, 29.51 | missing | noticeable | No defination break between shapes |
| 7 | 44.4, 22.43 | extra | noticeable | 7-8 does not portray the image definition |
| 9 | 33.43, 16.35 | blob | noticeable | for 9-10 |

Pins with no note (7): blob 5, (no kind) 2.

### `C_comic_halftone` - Terrible

Reason: "All of the people detail (in the face) is lost"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 6.66, 76.7 | letter_shape | noticeable | The N isn't an "N" |

### `C_devanagari_logo` - Okay

Reason: "Close, just needs to improve lettering flow"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 68.67, 14.61 | extra | noticeable | This is the only lettering in-fill, it doesn't match the rest |
| 5 | 16.95, 37.09 | extra | nitpick | in-fill only in select spots (#5-#6) |
| 7 | 10.74, 8.81 | pen_flow | nitpick | for 7-8 |

Pins with no note (5): pen_flow 3, (no kind) 2.

### `C_kanji_seal` - Bad

Reason: "No flow with the patterns, it's just a bunch of stitches to fill the color voids"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 6.84, 7.41 | extra | noticeable | #1-#28 extra in-fill, some empty spaces have it while others don't |

Pins with no note (27): (no kind) 27.

### `C_vintage_engraved_badge` - Terrible

Reason: "All of the fine detail is lost"

### `C_gradient_mascot` - Great

Reason: "This one is 95% of the way complete"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 35.07, 24.24 | extra | nitpick | This extra bean stitch is inconsistant from the right nostrel. |
| 2 | 14.92, 79.49 | colour | - | #2-#3 feet are differnt colors, they should be the same |

Pins with no note (1): (no kind) 1.

### `C_outline_lineart_logo` - Great

Reason: "This one is also 95% of the way there."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 22.54, 29.57 | mushed | nitpick | Hard to decipher the dot on the "I" |
| 2 | 46.42, 35.16 | gap | nitpick | Stitch border isn't tight tot he lettering |

### `C_kanji_brush` - Terrible

Reason: "The stitching is so random, it matches the color fine but it doesn't have smoothness or any or flow to it."

### `C_chalkboard_lettering` - Terrible

Reason: "I can't tell what this is."

Pins with no note (1): colour 1.
