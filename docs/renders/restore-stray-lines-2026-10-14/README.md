# Restore keeps stray LINES (`cfg.small_text_keep_stray_lines`), 2026-10-14

Built OFF. Renders of EMB-Bot's own stitch output from `digitizer/testdata/photo/logo_hotel_fremont.webp`
(already in the repo), not cloth. Nothing sewn.

At 65 mm the text tagger puts Fremont's black THE in the tan date's cluster. `restore_small_text`
keeps the date line (`_core`: one thread, one height, one baseline) and strips the rest as strays,
which #933 added for the tagline's two black bars and a twist of rope. THE lost its cluster tags and
lettering treatment, was traced 1.8x fatter (T 1.18 -> 2.10 mm2) and its E closed. With the flag,
strays that are themselves a line of three or more keep their tags as their own cluster and are
considered like any other line; anything fewer is stripped as before.

## Fremont Hat, switch vs switch + keep (`hat_cells/`; OCR glyphs, legibility)

| width | arm | st / tr | EST | 1895 | THE | tagline |
|---|---|---|---|---|---|---|
| 65 mm | switch | 11,314 / 39 | 1/3 | 1/4 | 1/3 (outline, fat) | 5/11 |
| 65 mm | keep | 11,269 / 39 | 1/3 | 1/4 | **3/3** (bean) | 5/11 |
| 72 mm | both | 13,195 / 46 | identical design (`ad05327b`) |
| 81 mm | both | 15,330 / 41 | identical design (`ec047164`) |
| 92.5 mm | both | 18,675 / 54 | identical design (`a7444c5b`) |

Picture: `fremont65_the_switch_vs_keep.jpg`.

## Corpus (`corpus/`): switch vs switch + keep, 17 designs, all byte-identical (stitch-stream md5)
