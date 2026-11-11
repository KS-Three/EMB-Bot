# defect-marks-1110: the sitting, 2026-11-10

Kent marked all 15 items of the kit `defect-marks-1110` on 2026-11-10: the
Becker hat at 14:55 local time, the other 14 between 20:08 and 20:37. The page
is `tools/defect_marks.py serve` (PR #1385). On each render he gave an absolute
grade, pinned each fault (where, what kind, how bad, a note) and ticked the
problems that have no single spot. The page never receives the yardstick's
reading, so his marks are blind to it. They are NOT blind to the pro: on the 11
pro-paired logos the pro's file is drawn beside ours, and 3 of his notes compare
against it (Bridge 8, Fremont 2, MFab 3).

Every figure below is his own answer or an instrument reading on one tree
(`950855bf`), not a quality claim (ROADMAP gate 4).

## What is in this folder

- `marks.json`: his answers as the server stored them (sha256 `6524ac1c...`).
  Pin positions are `x`, `y` as fractions of the render and `x_mm`, `y_mm` in
  the design frame, measured from the render's top-left corner including its
  2 mm pad, so a pin in the pad can read slightly negative.
- `kit.json`: the kit's item list and the yardstick's reading of each item
  (preflight grade, score, findings, metrics), kit sha256 `65087d65...`.
  `marks.json` carries the same `kit_sha256`, so the marks were made against
  this item set.
- No pictures. The kit's `img/` holds client artwork and renders of the pro's
  files, and stays in the gitignored `digitizer/eye_pairs_out/defect-marks-1110/`
  on Kent's machine.

Rerun the side-by-side table from `digitizer/`:

    python -m tools.defect_marks report --kit ../docs/defect-marks-2026-11-10

## The kit

11 pro-paired logos (one job per artwork, each at its job's garment and width)
and 4 corpus photos. The kit was built while the 39-row photo capture was still
running, so 35 corpus rows are listed under `skipped` in `kit.json` and were
never shown. The photo half of this sitting is 4 rows.

## Grades beside the yardstick

`step` is Kent's grade minus the preflight letter mapped A..F to
Great..Terrible; above 0 means the yardstick was kinder than Kent.

| item | size | Kent | yardstick | step | pins | no kind | whole-design ticks |
|---|---|---|---|---|---|---|---|
| `L_becker_hat_large` | 102.0 x 64.7 mm on hat_front | Okay | A 100 | +2 | 20 | 0 | - |
| `L_bridge_hat` | 62.9 x 63.2 mm on hat_front | Okay | F 0 | -2 | 12 | 1 | detail_lost |
| `L_gaulke_roofing_hat` | 114.2 x 47.6 mm on hat_front | none | B 88 |  | 6 | 1 | - |
| `L_hotel_fremont_hat` | 93.3 x 50.6 mm on hat_front | Good | B 76 | +0 | 4 | 0 | detail_lost |
| `L_mfab_hat` | 105.3 x 40.2 mm on hat_front | Okay | B 76 | +1 | 10 | 1 | detail_lost |
| `L_precision_drone` | 63.2 x 65.0 mm on hat_front | Terrible | F 28 | +0 | 5 | 0 | unrecognizable, too_busy, colours_off, detail_lost, not_for_thread |
| `L_proseal_hat` | 85.7 x 64.2 mm on hat_front | Good | C 64 | -1 | 4 | 0 | - |
| `L_tires_hat_3d` | 114.5 x 42.4 mm on hat_front | Good | A 100 | +1 | 4 | 3 | - |
| `L_goldentee_hat` | 75.4 x 62.9 mm on hat_front | none | F 0 |  | 20 | 19 | too_busy |
| `L_toat_machine_hat` | 90.6 x 64.7 mm on hat_front | Good | D 46 | -2 | 4 | 0 | detail_lost |
| `L_toat_beanie` | 83.4 x 56.1 mm on beanie | none | F 34 |  | 4 | 0 | - |
| `P_bw_street` | 73.2 x 43.2 mm on left_chest | Terrible | F 0 | +0 | 0 | 0 | unrecognizable, not_for_thread |
| `P_night_neon` | 80.6 x 53.9 mm on left_chest | Terrible | D 46 | +1 | 0 | 0 | unrecognizable, too_busy, detail_lost, not_for_thread |
| `P_architecture` | 80.5 x 53.8 mm on left_chest | Terrible | D 52 | +1 | 1 | 0 | unrecognizable, too_busy, detail_lost, not_for_thread |
| `P_landscape_lake` | 80.6 x 53.7 mm on left_chest | Terrible | B 76 | +3 | 1 | 0 | unrecognizable, detail_lost, not_for_thread |

- **Grades:** Good 4, Okay 3, Terrible 5, none 3. No Great and no Bad.
- **Step, 12 graded items:** 0 on 3, yardstick kinder on 6, yardstick harsher
  on 3. The widest: `P_landscape_lake` Terrible against B 76 (+3),
  `L_becker_hat_large` Okay against A 100 (+2), `L_bridge_hat` Okay against
  F 0 (-2), `L_toat_machine_hat` Good against D 46 (-2).
- **Rank agreement, his grade against the preflight score:** Spearman +0.41 on
  the 12 graded items, +0.32 on the 8 graded logos alone. Both n are too small
  to read as more than "not zero, not close". The 4 photos sit at the bottom of
  both scales and lift the 12-item figure.
- **All 4 photos are Terrible**, each ticked "can't tell what it is" and "not
  for thread". He placed 2 pins on them in total, both "everything is wrong".
  A photo this far off gives pins nothing to point at.

## What he pinned

95 pins, 93 of them on the 11 logos.

| kind | pins |
|---|---|
| letter_shape | 14 |
| missing | 10 |
| mushed | 7 |
| other | 7 |
| jagged | 5 |
| wavy | 5 |
| stray | 4 |
| gap | 4 |
| lumpy_curve | 3 |
| pen_flow | 3 |
| direction | 3 |
| colour | 2 |
| stitch_type | 2 |
| blob | 1 |
| no kind chosen | 25 |

How bad: noticeable 50, nitpick 17, ruins 4, not chosen 24.
Whole-design ticks: detail_lost 8, unrecognizable 5, not_for_thread 5,
too_busy 4, colours_off 1.

### Reading the notes (this section is the session's reading, not Kent's)

The kind he picked and the note he typed often disagree, so a fault reader
should be checked against the NOTE, with the kind as a hint. Keyword counts
over the 95 notes, rough on purpose:

- **Edges that should be smooth** ("jagged", "smooth", "crisp", "clean"):
  17 pins on 7 items, filed under jagged 5, lumpy_curve 3, wavy 2, mushed 2,
  direction 1, letter_shape 1, other 1 and no kind 2. Two of his whole-item
  reasons say it too
  (Becker, Gaulke). By notes this is the largest single theme, larger than the
  kind table shows.
- **Letters that close up, merge or cannot be read** ("spacing", "merge",
  "read", "holes"): 15 pins on 6 items, 12 of them filed as letter_shape. A
  counter that fills (the B, the S, the E, the G) and two letters that join
  (B+R, N+T) are the repeated cases.
- **Stray crossover stitches:** 4 pins, all on Becker, all filed as stray.
- **Pieces missing:** 10 pins, 8 of them on Precision Drone (trees, drone,
  propellers) and the two TOAT jobs (gaps in a line, a missing top bar).

## Gaps in the record

- **No grade on 3 items:** `L_gaulke_roofing_hat`, `L_goldentee_hat`,
  `L_toat_beanie`. `report` therefore counts 12 of 15 as answered.
- **25 pins have no kind.** 22 are deliberate shorthand: Golden Tee's pin 1
  note says "same for 1-20" (19 bare pins) and Tires' says "marks 1-4 are te
  same issue" (3 bare pins). The file keeps them bare; reading them as copies
  of pin 1 is an interpretation. The other 3 (Bridge 4, Gaulke 4, MFab 1) have
  a note and no kind. One further pin on each of Bridge and Gaulke has a kind
  and no severity.
- **`P_bw_street` has "nothing wrong" ticked beside a Terrible grade** and two
  whole-design ticks. Read the grade; the tick looks like a mis-click.
- **The page server stopped once mid-sitting** (20:24:38 local, after item 7
  was saved; restarted about three minutes later). Items 1-7 were compared
  against a copy of the file as it stood at the stop and were unchanged. Item 8
  (Tires) was open when the server stopped: its first save after the restart
  carried the reason "No image.", which his later "This is a 9/10" replaced.
- **One sitting, one tree, no repeats.** Nothing here measures how stable his
  marks are.

## Kent's words, per item (verbatim)

### `L_becker_hat_large` - Okay

Reason: "The logo needs to flow, to many jagged endges around the BECKER. Satin lettering in MARINE needs to be clean, the outline is good, but the stitch fill is only OKAy."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 56.98, 12.6 | stray | noticeable | Random Cross over stitch shouldn't be here |
| 2 | 37.28, 16.79 | stray | noticeable | Random Cross over stitch shouldn't be here |
| 3 | 87.6, 4.04 | jagged | noticeable | The border around this logo should be smooth |
| 4 | 24.17, 51.49 | gap | nitpick | The "A" should be solid and i can see stitchin begind it. |
| 5 | 22.64, 29.38 | mushed | noticeable | The shape doesn't flow, it becomes very abrupy and just get's cut-off |
| 6 | 30.26, 55.53 | other | noticeable | This should be a triangle shape, but it's not. it doesn't look very clean |
| 7 | 28.37, 4.28 | wavy | noticeable | These jagged adges are not clean/smooth. |
| 8 | 78.01, 4.42 | lumpy_curve | noticeable | Its jagged and should be smooth |
| 9 | 97.43, 21.22 | lumpy_curve | noticeable | Its jagged and should be smooth |
| 10 | 1.35, 37.13 | gap | noticeable | A border should not have a gap |
| 11 | 71.44, 47.5 | wavy | noticeable | The letters should be flat |
| 12 | 81.22, 65.02 | wavy | noticeable | The letters should be flat |
| 13 | 56.14, 53.61 | lumpy_curve | nitpick | The R should be smooth and it has a bump here. |
| 14 | 27.78, 61.48 | pen_flow | noticeable | The cross member of the "A" should not go into the left side of the leg |
| 15 | 89.02, 62.82 | stray | noticeable | random cross over stitch |
| 16 | 95.43, 50.74 | stray | noticeable | Random cross over stitch |
| 17 | 75.12, 11.72 | blob | noticeable | The stitching directions and angles are very inconsistent here. |
| 18 | 92.08, 35.24 | direction | noticeable | It looks like it created 2 stitch paths to create one single shape, instead of overlapping 2 stitches, it should have just made 1 extra wide stitch |
| 19 | 95.99, 24.76 | other | noticeable | The stitches don't flow together, the stitches meet while the angles are completely different |
| 20 | 50.48, 5.01 | gap | noticeable | under layer can be seen. |

### `L_bridge_hat` - Okay

Reason: "The lettering needs to be cleaned up & the fine details need to be improved."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 2.23, 31.28 | letter_shape | noticeable | All of the wheel handles look different from eachother, this would be better if they all looked the same. |
| 2 | 16.89, 34.66 | letter_shape | noticeable | The B is missing the two center holes. |
| 3 | 34.07, 32.72 | other | nitpick | The stitching is thicker than what the image shows |
| 4 | 38.85, 43.04 | - | noticeable | This is the only letter that is thinly stitched |
| 5 | 22.19, 43.15 | letter_shape | noticeable | I can't tell this is an & symbol |
| 6 | 23.51, 24.88 | letter_shape | - | The B and R merge together and you cannot tell what it is. |
| 7 | 32.96, 54.17 | missing | noticeable | The steering wheel handle is missing the little jut outs |
| 8 | 23.45, 30.61 | direction | nitpick | The satin stitching is running vertical, while the pros runs horizontal |
| 9 | 43.73, 24.17 | letter_shape | noticeable | I cannot read the e |
| 10 | 28.74, 22.56 | letter_shape | noticeable | There is no space between the body of the eye, and the dot |
| 11 | 37.05, 11.5 | jagged | noticeable | The circle should be smooth, not jagged |
| 12 | 44.75, 35.1 | letter_shape | noticeable | The N and the T are mergerd together |

### `L_gaulke_roofing_hat` - no grade

Reason: "Jagged edges around the lettering and logo"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 57.61, 24.7 | mushed | noticeable | Cannot see the window divididers/ |
| 2 | 98.22, 36.14 | letter_shape | noticeable | Note enough spacing between the "E" |
| 3 | 53.93, 13.07 | mushed | noticeable | The white spacing is not very apparent, and the edges are very jagged. |
| 4 | 61.38, 0.48 | - | noticeable | The circle edges should be smooth |
| 5 | 62.12, 38.76 | missing | noticeable | A chuck of the "D" is missing |
| 6 | 77.44, 35.19 | letter_shape | - | The "S" doesn't have spacing between the curves |

### `L_hotel_fremont_hat` - Good

Reason: "This is one of the better digitized images."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 36.08, 36.54 | letter_shape | noticeable | The A is hard to read |
| 2 | 40.99, 12.01 | letter_shape | noticeable | The Pro makes the lettering slighlty larger so it's is easier to read, these letters are to fine print to read. |
| 3 | 19.45, 15.74 | direction | nitpick | The end of this rope doesn't finish cleanly |
| 4 | 7.02, 24.09 | jagged | nitpick | All of the letters edges are jagged, they should be smooth. |

### `L_mfab_hat` - Okay

Reason: "Some of the fine details got missed (denoted)"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 21.87, -0.31 | - | nitpick | The border is jagged, but it matches the photo quality... |
| 2 | 40.69, 8.44 | wavy | nitpick | It isn't straight like the photo |
| 3 | 69.99, 16.77 | mushed | nitpick | This random stitch in the middle doesnt match the pros |
| 4 | 85.81, 24.9 | mushed | noticeable | Hard to tell what the stitches are doing here. |
| 5 | 35.94, 16.73 | other | noticeable | The cross stitches should not interfere with lettering, the M is correct, but the F is wrong |
| 6 | 89.73, 28.02 | gap | nitpick | Black showing through |
| 7 | 65.11, 23.5 | mushed | noticeable | The stitching isn't smooth, it has no flow here |
| 8 | 34.68, 28.43 | wavy | nitpick | This doesn;t look clean here |
| 9 | 18.93, 7.38 | colour | nitpick | This preview makes it look like a different color than the white |
| 10 | 78.24, 26.43 | letter_shape | noticeable | I can't read the "G" there is no spacing between the full lettering |

### `L_precision_drone` - Terrible

Reason: "This one needs alot of work, too hard to identify all of the issues with comments."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 19.77, 23.29 | missing | ruins | The trees are missing |
| 2 | 32.22, 21.59 | missing | ruins | I cannot tell this is a drone |
| 3 | 15.78, 35.8 | stitch_type | noticeable | The border bean stitch is changing colors too much here. |
| 4 | 36.7, 5.5 | colour | noticeable | This is black instead of blue |
| 5 | 13.18, 10.47 | missing | noticeable | The Drone propellers are missing or don't look like propellers |

### `L_proseal_hat` - Good

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 44.01, 57.8 | mushed | noticeable | The satin border is changing colors too much |
| 2 | 6.23, 63.08 | letter_shape | nitpick | The "S" doesn't have spacing between the curves |
| 3 | 33.36, 31.76 | jagged | nitpick | This doesn't have a crisp edge cut-off |
| 4 | 41.1, 61.98 | letter_shape | noticeable | The "M" is jagged and n |

### `L_tires_hat_3d` - Good

Reason: "This is a 9/10"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 53.78, 17.41 | jagged | nitpick | Jagged edges don't look clean (marks 1-4 are te same issue) |

Pins with no note (3): (no kind) 3.

### `L_goldentee_hat` - no grade

Reason: "Hard one to judge (almost like it's trying too hard)"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 26.14, 35.95 | stitch_type | noticeable | The bean stitching makes "golf" look to bust (same for 1-20) |

Pins with no note (19): (no kind) 19.

### `L_toat_machine_hat` - Good

Reason: "Close, just a few improvements needed"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 22.35, 13.7 | missing | noticeable | Missing top bar |
| 2 | 43.38, 47.32 | missing | noticeable | Gap/Jump in the line |

Pins with no note (2): missing 1, pen_flow 1.

### `L_toat_beanie` - no grade

Reason: "This one is good, just a few small improvements required"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 61.53, 12.56 | missing | noticeable | Gap in the line |
| 2 | 27.17, 43.96 | missing | noticeable | gap in the line |
| 3 | 30.63, 33.98 | pen_flow | noticeable | No flow here in the stitching |
| 4 | 56.73, 7.42 | other | nitpick | The "T" intersects the border |

### `P_bw_street` - Terrible

Reason: "Not even close, I cannot tell what it is."

### `P_night_neon` - Terrible

Reason: "All of the details just dissapaered"

### `P_architecture` - Terrible

Reason: "Details are gone"

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 42.58, 24.78 | other | ruins | Everything is wrong |

### `P_landscape_lake` - Terrible

Reason: "Too much detail lost, I cant even tell what this is."

| pin | at (mm) | kind | how bad | note |
|---|---|---|---|---|
| 1 | 40.18, 30.01 | other | ruins | Everything looks wrong |

