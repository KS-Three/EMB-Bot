# Preflight on a photo that lost its subject (2026-11-14)

Source: build walkthrough 2026-11-13, section 4 and "What did not work" item 2.
`photo_dof_meadow.png` (two toadstools on a blurred meadow) went down the photo
lane, lost the small toadstool and the big one's stem to flat olive and
pale-green blobs, and preflight still said **B 76/100**, with a note to "remove
or simplify the smallest lettering" on a picture with no lettering. Two parts:
A is a fix, B is an instrument. Every number below is an instrument reading or
Kent's own grade, not a quality claim (ROADMAP gate 4).

## A. Lettering advice on a job with no lettering: fixed

**Reproduced** on `0b2f1b5f` at the walkthrough's 93.3 mm, left chest: 120 s,
27,609 stitches, `photo_scene`, B 76. Findings: `PHOTO_RESOLUTION_LOW`,
`LETTERING_TOO_SMALL` ("8 of 11 satin shapes sew below readable size …
Remove or simplify the smallest lettering. … about 8 across the smallest of
this lettering …"), `ARTWORK_UNCOVERED` (info), `STABILIZER_CUTAWAY` (info).
Text tags on the 59 regions: `text_candidate` 0, `text_cluster_id` 0, `word_id`
0, `lettering_group` 0; OCR legibility clusters 0.

**Cause.** `_lettering_findings` judges every SATIN shape (median column
under 1 mm, or a shape that fits in a 4 mm box) and always words its advice
as lettering. It never asks whether the job has text. A photo's small spots
and slivers are satin too. The same note shows up on other jobs with no text.
In the corpus scorecard baseline (`testdata/corpus_scorecard_baseline.json`),
13 of the 29 rows carrying `LETTERING_TOO_SMALL` have 0 text clusters. They
come from 7 fixtures: `bg_uncertain`, `logo_alpha` and `logo_whitebg`
(circles, a ring and bars), and `photo_chrome_specular`, `photo_dof_meadow`,
`photo_scene_stub` and `photo_sunset_backlit`. Re-run on this tree,
`logo_whitebg`, `logo_alpha` and `bg_uncertain` carry no lettering tag (so the
advice says "details"). `logo_hotel_fremont` (33 tagged) and `enthusiast_logo`
(24 tagged) do carry tags (so it stays "lettering").

**Fix** (`preflight._job_has_lettering`). A job has lettering when any region
carries `text_candidate`, `text_cluster_id`, `word_id` or a truthy
`lettering_group`. That covers stage 4's text tagger (the clusters OCR reads)
and typed outline-font text (`outline_fonts.py` sets `text_candidate`). When
the regions exist and none is tagged, the advice ends "Remove or simplify the
smallest **details**", the resolution note says "the smallest of **these
shapes**", and `extra.lettering` is `False` (`True` with text, `None` for a
bare plan, which keeps the old wording). The code, the severity and the grade
cost do not change, so **no grade moves on any job**. The shapes really are
too small to sew cleanly, and dropping the finding would have made the
toadstool's B even kinder. Golden md5s cannot move because no stitch changed.

**Live re-run after the fix** (same image, width and tree plus this change):
B 76, the same four findings, and the message now reads "… Remove or simplify
the smallest details. The artwork carries 8.4 pixels per millimetre at this
width, about 8 across the smallest of these shapes, …".

## B. "Did the result keep the subject's detail?": measured

### Readings

All of these use only what preflight already holds: stage 1's re-read of the
artwork (`prep`) and the sewn stitches with their thread colours. Plan
millimetres map onto the re-read the way `_uncovered_findings` maps them. The
sewn picture is a **thread map**: every needle-down run drawn 0.45 mm wide in
its thread's colour, in sew order, on the garment colour. Both pictures are in
CIE Lab, smoothed at sigma 0.3 mm and read on a grid of at most 8 px/mm.
Code: `digitizer_core/subject_detail.py` (edge half) and
`digitizer/tools/subject_detail.py` (blob half and the sweep).

| reading | what it is | lost reads |
|---|---|---|
| `edge_recall` | Share of the artwork's strong edges (a CIE76 step of 15 or more across 1 mm, inside `~bg_mask`, 1 mm in from the border) that have a strong thread-map edge within 1 mm | low |
| `blob_lost_frac` | Source quantised to 8 colours (k-means, Lab). A blob is a one-colour patch of at least 4 mm² that survives a 1 mm opening. A blob is lost when the thread map's median colour over it is more than 15 CIEDE2000 from its own mean. Share of blobs lost | high |
| `salient_lost_frac` | The same blobs, each weighted by its contrast with the 1 mm of artwork around it | high |
| `edge_density` (**control**) | Strong source edges per artwork pixel. No stitches involved: it measures how busy the picture is | high |
| `element_dropped_frac` | The existing `ARTWORK_ELEMENT_DROPPED` metric, read from each capture's own preflight | high |

**The order things were done in.** The edge and blob constants were written
before any row was read. The toadstool's whole-frame readings came back first
(edge recall 0.94, blob lost 0.09): they dilute a small subject. The salience
variant was added **after** that and **before** any reading was scored against
Kent's grades. The synthetic test then caught a bug in the blob reading: the
in-between colours along every clean edge formed thin "blobs" that always read
lost. The 1 mm opening fixes that, and it went in before the sweep that was
scored. The rows were never scored against the grades on the buggy version.

### Data

- **Corpus:** the 39-row Commons corpus's saved capture `main-950855b`
  (`digitizer/corpus_runs/`, local and gitignored), 80 mm, left chest, the
  Studio's request. Every reading was computed off-line from the saved stitches
  and the source photo. Nothing was re-digitized.
- **Toadstool:** captured the same way (the corpus worker's path and request)
  on `0b2f1b5f`, a later tree. Kent has not graded it. On that tree at 80 mm,
  the big cap sews red, its stem sews as a pale-green blob, and the small
  toadstool is gone.
- **Kent's grades of the SAME renders (tree `950855bf`):**
  `docs/defect-marks-2026-11-10` (the 4 corpus photos) and
  `docs/defect-marks-2026-11-11` (the 21 Commons logos). **LOST** means he
  ticked `detail_lost` or `unrecognizable` (13 rows). **GOOD** means Good or
  Great with neither tick (6 rows). The other 6 graded rows are MIDDLE. 15
  photo rows are ungraded. Kent graded **no photo** Good: all 4 photos he saw
  are Terrible.
- **Figure:** Somers' D = 2 × AUC − 1 for "the reading puts a LOST row on the
  lost side of a GOOD row". 0 is chance, 1 means every pair is ordered. The 95%
  interval comes from 5,000 bootstrap resamples within each group
  (`tools/subject_detail_score.py`).

Rows and scores: `docs/subject-loss-2026-11-14/rows.json`, `score.json`.

### Results

| reading | Somers' D | 95% CI | LOST / GOOD rows |
|---|---|---|---|
| `edge_recall` | **+0.88** | [+0.63, +1.00] | 13 / 5 (`neon_outline_sign`: no strong edge, None) |
| `blob_lost_frac` | +0.54 | [−0.10, +1.00] | 13 / 6 |
| `salient_lost_frac` | +0.56 | [−0.08, +1.00] | 13 / 6 |
| `element_dropped_frac` | +0.08 | [0.00, +0.23] | 13 / 6 |
| `edge_density` (control) | +0.28 | [−0.39, +0.90] | 13 / 6 |
| **class is not `flat`** (second control, computed afterwards) | +0.77 | [+0.54, +1.00] | 13 / 6 |
| `edge_recall`, flat art only | +1.00 | (15 pairs) | 3 / 5 |

The distribution covers all 40 rows, sorted by `edge_recall`, lowest (most
lost) first.

| row | class | Kent (label) | his ticks | edge_recall | blob_lost | salient_lost | edge_density (control) | element_dropped | preflight |
|---|---|---|---|---|---|---|---|---|---|
| `distressed_grunge` | flat | Terrible (LOST) | detail_lost, not_for_thread | 0.352 | 0.17 | 0.31 | 0.415 | 0.000 | A 100 |
| `qr_code` | flat | Terrible (MIDDLE) | not_for_thread | 0.496 | 0.25 | 0.28 | 0.526 | 0.098 | D 46 |
| `bw_street` | photo_scene | Terrible (LOST) | not_for_thread, unrecognizable | 0.543 | 0.68 | 0.48 | 0.364 | 0.000 | F 0 |
| `night_skyline` | photo_scene | - |  | 0.559 | 0.11 | 0.23 | 0.208 | 0.000 | C 64 |
| `flower_macro` | photo_scene | - |  | 0.576 | 0.72 | 0.69 | 0.338 | 0.000 | F 16 |
| `stained_glass` | photo_scene | - |  | 0.606 | 0.15 | 0.16 | 0.579 | 0.022 | D 40 |
| `duotone_poster` | photo_scene | Terrible (LOST) | not_for_thread, too_busy, unrecognizable | 0.657 | 0.70 | 0.75 | 0.259 | 0.000 | B 76 |
| `landscape_lake` | photo_scene | Terrible (LOST) | detail_lost, not_for_thread, unrecognizable | 0.676 | 0.29 | 0.28 | 0.399 | 0.000 | B 76 |
| `dark_dog` | photo_scene | - |  | 0.702 | 0.51 | 0.52 | 0.140 | 0.000 | F 16 |
| `halftone_dots` | photo_scene | Terrible (LOST) | detail_lost, not_for_thread, unrecognizable | 0.709 | 0.01 | 0.03 | 0.055 | 0.000 | B 88 |
| `isometric_icon` | gradient | Bad (LOST) | detail_lost, too_busy | 0.744 | 0.14 | 0.28 | 0.500 | 0.005 | B 76 |
| `food_plate` | photo_scene | - |  | 0.751 | 0.49 | 0.44 | 0.367 | 0.000 | F 16 |
| `fireworks` | photo_scene | - |  | 0.772 | 0.31 | 0.21 | 0.289 | 0.000 | F 34 |
| `snow_highkey` | photo_scene | - |  | 0.791 | 0.62 | 0.59 | 0.221 | 0.000 | D 46 |
| `underwater_reef` | photo_scene | - |  | 0.808 | 0.24 | 0.36 | 0.584 | 0.000 | B 76 |
| `comic_halftone` | flat | Terrible (LOST) | detail_lost, not_for_thread, too_busy, unrecognizable | 0.817 | 0.14 | 0.13 | 0.254 | 0.000 | F 0 |
| `architecture` | photo_scene | Terrible (LOST) | detail_lost, not_for_thread, too_busy, unrecognizable | 0.843 | 0.75 | 0.71 | 0.280 | 0.000 | D 52 |
| `night_neon` | photo_scene | Terrible (LOST) | detail_lost, not_for_thread, too_busy, unrecognizable | 0.857 | 0.26 | 0.37 | 0.578 | 0.000 | D 46 |
| `vintage_sepia` | flat | - |  | 0.860 | 0.00 | 0.00 | 0.089 | 0.000 | F 28 |
| `chalkboard_lettering` | photo_scene | Terrible (LOST) | detail_lost, too_busy, unrecognizable | 0.870 | 0.04 | 0.10 | 0.132 | 0.000 | B 88 |
| `pencil_sketch` | photo_scene | - |  | 0.879 | 0.00 | 0.00 | 0.026 | 0.000 | A 100 |
| `low_poly` | flat | Bad (MIDDLE) | not_for_thread | 0.894 | 0.02 | 0.00 | 0.333 | 0.000 | F 0 |
| `group_people` | flat | - |  | 0.915 | 0.08 | 0.08 | 0.441 | 0.005 | F 0 |
| `oil_painting` | photo_scene | - |  | 0.917 | 0.66 | 0.50 | 0.116 | 0.000 | F 28 |
| `watercolor` | photo_scene | - |  | 0.938 | 0.31 | 0.30 | 0.447 | 0.017 | D 46 |
| **toadstool_dof_meadow** | photo_scene | - |  | 0.940 | 0.09 | 0.26 | 0.022 | 0.000 | B 76 |
| `barcode` | flat | Terrible (LOST) | colours_off, detail_lost, not_for_thread, unrecognizable | 0.947 | 0.00 | 0.00 | 0.687 | 0.000 | F 34 |
| `arabic_calligraphy` | flat | Good (GOOD) |  | 0.949 | 0.00 | 0.00 | 0.768 | 0.000 | C 64 |
| `flat_emoji_icon` | flat | Good (GOOD) |  | 0.958 | 0.11 | 0.07 | 0.106 | 0.000 | B 76 |
| `heraldic_crest` | flat | Bad (MIDDLE) | too_busy | 0.968 | 0.03 | 0.05 | 0.480 | 0.000 | F 28 |
| `sports_action` | flat | - |  | 0.968 | 0.14 | 0.19 | 0.279 | 0.001 | F 0 |
| `vintage_engraved_badge` | photo_scene | Terrible (LOST) | detail_lost, unrecognizable | 0.981 | 0.35 | 0.37 | 0.673 | 0.000 | C 64 |
| `kanji_brush` | photo_scene | Terrible (LOST) | detail_lost, too_busy, unrecognizable | 0.990 | 0.40 | 0.32 | 0.353 | 0.000 | F 0 |
| `devanagari_logo` | flat | Okay (MIDDLE) |  | 0.992 | 0.20 | 0.31 | 0.642 | 0.000 | B 88 |
| `gradient_mascot` | flat | Great (GOOD) |  | 0.996 | 0.00 | 0.00 | 0.165 | 0.000 | C 70 |
| `pixel_art_sprite` | flat | Good (GOOD) |  | 0.999 | 0.83 | 0.93 | 0.223 | 0.000 | A 100 |
| `silhouette_logo` | flat | Bad (MIDDLE) |  | 1.000 | 0.00 | 0.00 | 0.221 | 0.000 | D 40 |
| `outline_lineart_logo` | flat | Great (GOOD) |  | 1.000 | 0.00 | 0.00 | 0.550 | 0.000 | B 76 |
| `kanji_seal` | flat | Bad (MIDDLE) | not_for_thread, too_busy | - | 0.31 | 0.92 | 0.000 | 0.000 | B 88 |
| `neon_outline_sign` | flat | Good (GOOD) |  | - | 0.00 | 0.00 | 0.000 | 0.000 | B 76 |

### Verdict

1. **`edge_recall` separates Kent's detail-lost rows from his Good rows:
   Somers' D +0.88 [+0.63, +1.00].** The source-only control does not
   (+0.28, CI crosses 0), so it is not just "busy pictures read lost".
2. **It is NOT shown to measure more than photo-ness.** Every GOOD row is
   flat art, and "the class is not flat" alone scores +0.77 [+0.54, +1.00].
   The 0.11 gap sits inside both intervals. The one hint beyond class: among
   the flat-art rows, it orders all 15 LOST/GOOD pairs (3 LOST, 5 GOOD), and it
   flags `distressed_grunge` (Terrible, detail lost, preflight **A 100**) at
   0.35. 3 against 5 is too few to read as more than a hint.
3. **It would not have caught the toadstool with any margin.** The toadstool
   reads 0.940: under all five GOOD rows, but by 0.009 (`arabic_calligraphy`
   0.949), and above three LOST rows (`barcode` 0.947, `vintage_engraved_badge`
   0.981, `kanji_brush` 0.990). The subject is small and most of the frame's
   strong edges are kept, so a whole-frame recall reads the loss as
   near-normal. No threshold drawn from this table both flags the toadstool
   and is safe for Good flat art.
4. **The blob readings and `element_dropped_frac` do not separate**: their
   CIs cross 0 or sit near 0. `ARTWORK_ELEMENT_DROPPED` reads 0 on the
   toadstool and on 12 of the 13 LOST rows. It counts what the pipeline
   reported losing; a photo's subject is lost by being recoloured into the
   background, which nothing reports.

**Shipped:** `subject_edge_recall` as a preflight **metric only** (no finding,
no grade, never shown to the customer). It costs about 0.2 s a job, measured
on 3 corpus rows. It is None without the artwork. The corpus scorecard's diff
skips a key its baseline lacks, so it is inert there until the next recapture.

**Not shipped, and why:** any threshold, finding or grade change. The figure
is above chance, but this data cannot tell it apart from the photo/flat
split, and it misses the motivating case. What would settle it is a sitting
where Kent grades **photos** Good as well as bad (today no photo is graded
Good), with the reading's cut-off written down before he sits.
