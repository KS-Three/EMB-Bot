# Small-cap census of the lettering font library, 2026-10-12

Measurement only. No engine file changed. Every threshold below is a CANDIDATE:
ROADMAP gate 1 says no physical constant is settled without a sew-out, and nothing
here was sewn.

Tool: `tools/small-cap-census.mjs` (pins: `test/small-cap-census.test.js`).
Data: `docs/small-cap-census-2026-10-12.csv` (510 cells, one row per font and cap).
Picture: `docs/small-cap-census-2026-10-12-sheet.png` (7 fonts at 3 / 4 / 6 mm; a
render of the stitch stream, not a sew-out).

## Method

All 85 shipped fonts (`src/fonts/bin/*.embf`) are laid out through
`buildLetteringDesign`, the Studio's text path (pxPerMm 8, normal weight, no
fabric, engine defaults), on the string `Hamburgefonstiv 0123` at cap heights 2.5,
3, 4, 5 and 6 mm, plus a 12 mm control per font. The cap is calibrated from the
engine's own `lettering.capMm` and every cell landed within 2% of its target (0
`capMiss`). The garment is `full_back`: on `left_chest` (101 mm) the engine would
scale the wider fonts down and they would not be at the cap asked for. A full run
takes about 31 s.

The floors are read from `satinfont.LETTERING_GUARDS`, not restated:

| Floor | Value | Used for |
|---|---|---|
| `SHORT_STITCH_AT_MM` | 0.3 mm | the short-stitch floor: share of sewn segments under it (`sub03`, includes same-hole repeats) |
| `SATIN_MIN_CROSS_MM` | 0.5 mm | a satin cross under it is sewn as a bean run; the engine counts these as `hairlineSpans` |
| `COLUMN_FLOOR_MM` | 1.0 mm | the minimum column width; columns under it are `thinSpans` (reported, never clamped by the engine) |

Narrowest column: the engine reports stroke length under each floor but no width, so
the tool reads it off the stream. A satin span is cross, rail step, cross, so the even
segments are the crosses; a stroke's width is the median of its crosses, and
`narrowestMm` is the smallest over strokes of 5 or more crosses. The single shortest
cross anywhere (`minCrossMm`) reads 0.40 to 0.45 mm in nearly every font because every
column tapers to the 0.5 mm floor at its tips, so it is not used to rank anything.

Clean, two readings, and a font's verdict is the smallest cap from which it STAYS clean
at every larger grid cap:

- **engine**: no hairline span, nothing over one DST record, no error.
- **relative**: engine, and the share of sewn segments under 0.3 mm is within 2
  points of the font's OWN 12 mm control. The 2-point margin is a candidate, chosen
  to show the spread.

Columns under 1.0 mm are not a clean criterion: they are 94% of all strokes at 2.5 mm,
87% at 4 mm and 59% at 6 mm, so using them would fail the whole library and rank
nothing. They are reported instead.

## Result

Errors: 0 across 510 cells. Two fonts sew nothing of the string (`hebrew_font_large`,
`hebrew_font_medium`: no Latin glyphs), so 83 are scored. One font drops characters
(`apesplit`). 21 of the 83 have no satin column at all (run, fill, bean or pixel
construction), so for them `narrowestMm` and `thin spans` do not apply.

Fonts clean at each cap (of 83):

| Cap (mm) | engine | relative |
|---|---|---|
| 2.5 | 35 | 1 |
| 3 | 36 | 3 |
| 4 | 43 | 19 |
| 5 | 47 | 26 |
| 6 | 56 | 40 |

Smallest cap from which a font stays clean:

| From (mm) | engine | relative |
|---|---|---|
| 2.5 | 30 | 0 |
| 3 | 4 | 3 |
| 4 | 8 | 16 |
| 5 | 4 | 6 |
| 6 | 10 | 15 |
| none up to 6 | 27 | 43 |

Library totals per cap, over every cell (sewn segments under 0.3 mm / hairline spans
/ strokes under 1.0 mm):

| Cap (mm) | stitches | under 0.3 mm | same-hole repeats | hairline spans | thin strokes |
|---|---|---|---|---|---|
| 2.5 | 76,798 | 49.0% | 6,310 | 1,350 | 94.2% |
| 3 | 87,085 | 37.7% | 5,409 | 1,333 | 91.7% |
| 4 | 107,844 | 24.3% | 4,109 | 1,325 | 86.6% |
| 5 | 153,523 | 12.7% | 3,679 | 1,308 | 71.8% |
| 6 | 178,852 | 8.4% | 3,461 | 1,410 | 58.5% |
| 12 | 315,794 | 2.9% | 2,452 | 1,445 | 30.2% |

## Verdict (candidate thresholds, unsewn)

- **No font is clean from 2.5 mm** on the relative reading, and only 3 are clean from
  3 mm (`mimosa_medium`, `mimosa_large`, `jaquarda_bastarda_9`). Under 3 mm, treat
  every font as unsafe.
- **Unsafe below 4 mm**: all but those 3. 16 fonts are clean from 4 mm (for example
  `western_light`, `alchemy`, `eloquent`, `egyptian`, `noble`, `heavenly`,
  `cyrillic`, `small_font`, `medium_font`).
- **Unsafe below 5 mm**: 6 more (`glacial_tiny`, `barstitch_bold`, `caffeine_KOR`,
  `caffeine_tiny`, `jacquard_12`, `barstitch_regular`).
- **Unsafe below 6 mm**: 15 more (`bathaus_FI`, `venezia`, `excalibur`,
  `pacificlo`, `magnolia_*`, `ags_garamond_latin_grec` and others, see the table).
- **Not clean at any size up to 6 mm: 43 fonts.** 27 of those carry hairline spans even
  at 6 mm (the engine sews strokes under 0.5 mm as a bean run): script and ornamental
  faces such as `montecarlo`, `sunset`, `initials_XL`, `kum_tsoan_*`,
  `apesplit`, `marifenda`, `mam_script`. 8 more are engine-clean but sew far more
  sub-0.3 mm segments than their own 12 mm control (`jersey_15` 94.8% at 4 mm against 0.0% at 12 mm; `pixel10`
  37.5%; `fold_inkstitch` 30.3%; `califragilistic`, `barstitch_mandala`,
  `ondulamarif_*`). 8 more clear the engine reading only from 5 or 6 mm.
- Several fonts are not clean even at 12 mm on the engine reading (12 of 83 cells show
  a hairline span at the control size), so for those a larger cap does not fix it:
  the stroke is under the 0.5 mm floor at least up to 12 mm.

Where this agrees with the research doc: the 6 mm floor for thin thread is about where
the relative reading starts to clear (40 of 83), and 4 mm is where the Studio's own
CAP_FLOOR_MM warning sits and where the first large group (16) clears. It does not
support 3 mm as a safe size for any font but three.

## Caveats

- One test string. Fonts with a different glyph mix (all-caps, no digits) are measured
  on what they sew; `apesplit` drops characters and its stitch count is understated.
- The width read is off the sewn stream, which carries pull compensation and rounds to
  0.1 mm. The stroke widths are good to roughly 0.05 to 0.1 mm.
- `sub03` counts consecutive stitch-to-stitch segments, including satin crosses that
  the engine already pulled. It is the engine's own floor applied to the output, not a
  claim that 0.3 mm is the right number (gate 1).
- Nothing here predicts how a stroke SEWS (thread weight, fabric, stabilizer). That is a
  sew-out question.

## Ranked table, all 83 fonts

Best first: smallest relative-clean cap, then smallest engine-clean cap, then fewest hairline
spans at 4 mm, then least short-stitch share at 4 mm.

| # | font | clean from, relative (mm) | clean from, engine (mm) | stitches @4 mm | short < floor @4 mm (12 mm control) | hairline spans @3 / 4 / 5 / 6 mm | thin spans @4 mm | narrowest column @4 mm (mm) | note |
|---|---|---|---|---|---|---|---|---|---|
| 1 | mimosa_medium | 3 | 2.5 | 1066 | 0.0% (0.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 2 | mimosa_large | 3 | 2.5 | 1072 | 0.9% (0.1%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 3 | jaquarda_bastarda_9 | 3 | 2.5 | 1168 | 5.1% (5.1%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 4 | western_light | 4 | 2.5 | 402 | 0.8% (0.8%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 5 | inkstitch_masego | 4 | 2.5 | 784 | 1.1% (0.0%) | 0 / 0 / 0 / 0 | 0 of 38 | 1.1 |  |
| 6 | cyrillic | 4 | 2.5 | 864 | 1.7% (0.7%) | 0 / 0 / 0 / 0 | 34 of 38 | 0.6 |  |
| 7 | roaring_twenties_KOR | 4 | 2.5 | 586 | 1.8% (0.5%) | 0 / 0 / 0 / 0 | 0 of 29 | 1.2 |  |
| 8 | roaring_twenties_KOR_small | 4 | 2.5 | 586 | 1.8% (0.5%) | 0 / 0 / 0 / 0 | 0 of 29 | 1.2 |  |
| 9 | neon_blinking | 4 | 2.5 | 234 | 2.3% (0.6%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 10 | eloquent | 4 | 2.5 | 1100 | 3.9% (3.9%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 11 | eloquent_small | 4 | 2.5 | 1100 | 3.9% (3.9%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 12 | egyptian | 4 | 2.5 | 1104 | 4.0% (4.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 13 | egyptian_small | 4 | 2.5 | 1104 | 4.0% (4.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 14 | noble | 4 | 2.5 | 1244 | 4.3% (4.3%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 15 | heavenly | 4 | 2.5 | 932 | 5.0% (5.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 16 | heavenly_small | 4 | 2.5 | 932 | 5.0% (5.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 17 | small_font | 4 | 3 | 960 | 1.6% (0.9%) | 0 / 0 / 0 / 0 | 39 of 39 | 0.57 |  |
| 18 | medium_font | 4 | 3 | 966 | 2.1% (0.9%) | 0 / 0 / 0 / 0 | 39 of 39 | 0.59 |  |
| 19 | alchemy | 4 | 4 | 881 | 1.6% (0.7%) | 1 / 0 / 0 / 0 | 15 of 35 | 0.72 |  |
| 20 | glacial_tiny | 5 | 2.5 | 912 | 3.4% (0.4%) | 0 / 0 / 0 / 0 | 18 of 39 | 0.71 |  |
| 21 | barstitch_bold | 5 | 2.5 | 906 | 3.7% (0.5%) | 0 / 0 / 0 / 0 | 20 of 40 | 0.71 |  |
| 22 | caffeine_KOR | 5 | 2.5 | 868 | 5.1% (1.1%) | 0 / 0 / 0 / 0 | 43 of 43 | 0.64 |  |
| 23 | caffeine_tiny | 5 | 2.5 | 868 | 5.2% (1.0%) | 0 / 0 / 0 / 0 | 43 of 43 | 0.64 |  |
| 24 | jacquard_12 | 5 | 2.5 | 2612 | 24.5% (2.8%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 25 | barstitch_regular | 5 | 4 | 880 | 3.5% (1.3%) | 16 / 0 / 0 / 0 | 36 of 36 | 0.5 |  |
| 26 | allegria20 | 6 | 2.5 | 936 | 13.0% (6.3%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 27 | bathaus_FI | 6 | 3 | 862 | 6.2% (0.9%) | 0 / 0 / 0 / 0 | 40 of 40 | 0.57 |  |
| 28 | bathaus_FI_Small | 6 | 3 | 862 | 6.2% (0.9%) | 0 / 0 / 0 / 0 | 40 of 40 | 0.57 |  |
| 29 | venezia | 6 | 4 | 1162 | 5.0% (1.2%) | 7 / 0 / 0 / 0 | 41 of 41 | 0.58 |  |
| 30 | venezia_small | 6 | 4 | 1162 | 5.1% (1.1%) | 7 / 0 / 0 / 0 | 41 of 41 | 0.58 |  |
| 31 | excalibur_KOR | 6 | 4 | 802 | 6.1% (1.1%) | 1 / 0 / 0 / 0 | 39 of 40 | 0.51 |  |
| 32 | excalibur_small | 6 | 4 | 802 | 6.1% (1.1%) | 1 / 0 / 0 / 0 | 39 of 40 | 0.51 |  |
| 33 | pacificlo | 6 | 4 | 784 | 7.3% (1.1%) | 2 / 0 / 0 / 0 | 30 of 30 | 0.57 |  |
| 34 | pacificlo_tiny | 6 | 4 | 784 | 7.3% (1.1%) | 2 / 0 / 0 / 0 | 30 of 30 | 0.57 |  |
| 35 | magnolia_KOR | 6 | 6 | 812 | 4.3% (1.5%) | 5 / 5 / 2 / 0 | 32 of 35 | 0.56 |  |
| 36 | magnolia_small | 6 | 6 | 812 | 4.3% (1.5%) | 5 / 5 / 2 / 0 | 32 of 35 | 0.56 |  |
| 37 | ags_garamond_latin_grec | 6 | 6 | 939 | 7.5% (2.1%) | 8 / 5 / 3 / 0 | 30 of 34 | 0.54 |  |
| 38 | digory_doodles_bean | 6 | 6 | 399 | 4.8% (1.3%) | 20 / 6 / 1 / 0 | 15 of 15 | 0.51 |  |
| 39 | magnolia_bicolor | 6 | 6 | 1572 | 7.4% (1.2%) | 10 / 10 / 4 / 0 | 72 of 76 | 0.51 |  |
| 40 | magnolia_tamed | 6 | 6 | 1572 | 7.4% (1.2%) | 10 / 10 / 4 / 0 | 72 of 76 | 0.51 |  |
| 41 | ondulamarif_S | none | 2.5 | 480 | 15.2% (4.4%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 42 | ondulamarif_Medium | none | 2.5 | 482 | 15.6% (4.6%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 43 | ondulamarif_XL | none | 2.5 | 480 | 16.3% (5.5%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 44 | barstitch_mandala | none | 2.5 | 1280 | 20.2% (6.7%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 45 | califragilistic | none | 2.5 | 1458 | 24.9% (9.3%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 46 | fold_inkstitch | none | 2.5 | 2956 | 30.3% (13.9%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 47 | pixel10 | none | 2.5 | 8328 | 37.5% (0.8%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 48 | jersey_15 | none | 2.5 | 11920 | 94.8% (0.0%) | 0 / 0 / 0 / 0 | 0 of 0 | no satin |  |
| 49 | auberge_marif | none | 5 | 772 | 9.7% (1.4%) | 37 / 2 / 0 / 0 | 29 of 29 | 0.5 |  |
| 50 | auberge_small | none | 5 | 772 | 9.7% (1.4%) | 37 / 2 / 0 / 0 | 29 of 29 | 0.5 |  |
| 51 | art_nouveau | none | 5 | 732 | 11.6% (1.5%) | 7 / 2 / 0 / 0 | 22 of 22 | 0.5 |  |
| 52 | roman_ags | none | 5 | 860 | 5.4% (1.2%) | 8 / 7 / 0 / 0 | 32 of 35 | 0.5 |  |
| 53 | pisankris | none | 6 | 700 | 10.8% (2.0%) | 4 / 2 / 1 / 0 | 27 of 27 | 0.51 |  |
| 54 | cogs_KOR | none | 6 | 1024 | 16.6% (0.9%) | 37 / 3 / 1 / 0 | 38 of 38 | 0.5 |  |
| 55 | stebor_AGS | none | 6 | 867 | 5.1% (0.9%) | 7 / 4 / 2 / 0 | 25 of 39 | 0.5 |  |
| 56 | chicken_scratch | none | 6 | 580 | 9.1% (1.9%) | 36 / 15 / 1 / 0 | 21 of 21 | 0.5 |  |
| 57 | manga_impact | none | none | 1152 | 4.6% (1.2%) | 0 / 0 / 0 / 1 | 23 of 53 | 0.71 |  |
| 58 | amitaclo | none | none | 866 | 7.0% (2.3%) | 4 / 4 / 1 / 1 | 39 of 39 | 0.52 |  |
| 59 | amitaclo_small | none | none | 866 | 7.0% (2.3%) | 4 / 4 / 1 / 1 | 39 of 39 | 0.52 |  |
| 60 | ambigue | none | none | 817 | 2.3% (1.3%) | 9 / 8 / 6 / 5 | 37 of 39 | 0.58 |  |
| 61 | marifenda | none | none | 770 | 3.9% (0.9%) | 8 / 8 / 9 / 9 | 36 of 36 | 0.54 |  |
| 62 | mam_script | none | none | 749 | 7.0% (1.9%) | 12 / 9 / 5 / 4 | 30 of 30 | 0.5 |  |
| 63 | mai_en_fleur | none | none | 2336 | 53.8% (9.0%) | 0 / 10 / 46 / 132 | 0 of 0 | no satin |  |
| 64 | neon | none | none | 1249 | 0.1% (1.1%) | 19 / 19 / 20 / 41 | 0 of 0 | no satin |  |
| 65 | cats | none | none | 979 | 13.1% (1.8%) | 53 / 20 / 2 / 1 | 28 of 28 | 0.45 |  |
| 66 | violin_serif | none | none | 872 | 13.5% (2.9%) | 35 / 20 / 22 / 30 | 25 of 25 | 0.5 |  |
| 67 | caesarus_SC_FI | none | none | 881 | 6.4% (1.2%) | 25 / 21 / 6 / 1 | 35 of 35 | 0.54 |  |
| 68 | apex_simple_AGS | none | none | 883 | 13.0% (2.2%) | 19 / 21 / 17 / 8 | 31 of 31 | 0.54 |  |
| 69 | apex_simple_small_AGS | none | none | 883 | 13.0% (2.2%) | 19 / 21 / 17 / 8 | 31 of 31 | 0.54 |  |
| 70 | chicken_little | none | none | 782 | 12.4% (2.1%) | 17 / 22 / 12 / 3 | 28 of 28 | 0.5 |  |
| 71 | chicken_little_small | none | none | 782 | 12.4% (2.1%) | 17 / 22 / 12 / 3 | 28 of 28 | 0.5 |  |
| 72 | cooper_marif | none | none | 1177 | 0.3% (3.7%) | 28 / 29 / 30 / 30 | 0 of 0 | no satin |  |
| 73 | colorful | none | none | 1160 | 1.1% (0.9%) | 26 / 33 / 8 / 3 | 3 of 3 | 0.5 |  |
| 74 | barstitch_textured | none | none | 1248 | 2.0% (1.2%) | 41 / 45 / 58 / 1 | 0 of 0 | no satin |  |
| 75 | allegria55 | none | none | 757 | 9.8% (2.4%) | 42 / 51 / 37 / 35 | 0 of 0 | no satin |  |
| 76 | montecarlo | none | none | 782 | 10.9% (2.9%) | 44 / 55 / 57 / 51 | 1 of 1 | 0.5 |  |
| 77 | perspective_tricolore_KOR | none | none | 864 | 7.4% (1.3%) | 55 / 63 / 27 / 16 | 5 of 5 | 0.5 |  |
| 78 | sunset | none | none | 1907 | 2.6% (1.8%) | 86 / 93 / 102 / 109 | 0 of 0 | no satin |  |
| 79 | initials_XL | none | none | 4507 | 60.8% (17.4%) | 41 / 96 / 161 / 247 | 0 of 0 | no satin |  |
| 80 | kum_tsoan_tartan | none | none | 1489 | 10.1% (3.1%) | 91 / 109 / 116 / 119 | 0 of 0 | no satin |  |
| 81 | initials_medium | none | none | 1770 | 14.4% (5.1%) | 102 / 142 / 157 / 174 | 0 of 0 | no satin |  |
| 82 | apesplit | none | none | 2679 | 29.2% (6.5%) | 129 / 160 / 187 / 202 | 0 of 0 | no satin | drops characters |
| 83 | kum_tsoan_AGS | none | none | 2553 | 8.3% (3.1%) | 139 / 162 / 171 / 175 | 0 of 0 | no satin |  |
