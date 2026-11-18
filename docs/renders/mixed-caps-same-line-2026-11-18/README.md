# `text_cluster_mixed_caps` with the same-line rule, 2026-11-18

Rule added to the pair bound of `docs/renders/mixed-caps-bound-2026-11-18/`: letters of a word sit on ONE line.
`textcluster._on_one_line` cuts a re-clustered group to the members whose vertical centres spread within
`SAME_LINE_SPREAD` (0.5) of the tallest member, dropping the member farthest from the median centre until the
group fits; a group that cannot keep 3 members is dropped. A ratio of the row's own geometry, no millimetre
number; it rests on **three rows** (TOAT hat 0.19, the same group on the beanie with the i-dot 1.26, the gradient
icon's group 1.83), and the config-side comment in `textcluster.py` says so. Still built OFF; OFF is byte-identical.

## The census READS THE TAGS, not only the pictures

Every one of the 44 designs (9 committed pro jobs, 9 other pro rows, 26 fixtures at the Studio request, 80 mm left
chest), flag ON, regions listed with the pass's tag. **40 of 44 designs: no shape tagged by the mixed-height pass.**
The 4 that tag, every tagged shape named and read against the art (the red outlines are in each `__tagged.jpg`):

| Design | Shape id | Height x width mm | Area mm2 | Row (n, centre spread) | Letter? |
|---|---|---|---|---|---|
| `toat_machine_hat` | S4f6ab0e2 | 11.8 x 7.5 | 31.7 | TC82ff8e (4, 0.19) | letter: the first **T** |
| | S90355d5d | 7.2 x 6.3 | 28.0 | same row | letter: the **o** |
| | S1e51cea2 | 7.6 x 5.2 | 24.0 | same row | letter: the small **A** |
| | S031be116 | 11.9 x 7.5 | 33.1 | same row | letter: the second **T** |
| `toat_beanie` | Sa80ef53d / S20a653ec | 10.2 x 6.8 / 10.3 x 7.1 | 26.9 / 28.0 | TC669b1a (4, 0.21) | letters: the two **T**s |
| | S24bc6c56 / Sad8aa242 | 6.2 x 5.6 / 6.7 x 4.8 | 21.9 / 18.6 | same row | letters: the **o** and the **A** |
| `otherrow_toat_machine_beanie` | S35e741a6 / Sdfa266d4 | 10.7 x 6.9 / 10.6 x 6.9 | 27.6 / 26.4 | TC9ecd08 (4, 0.21) | letters: the two **T**s |
| | S7fe065f2 / Sdeb36c9b | 6.7 x 5.7 / 6.9 x 4.6 | 23.2 / 19.3 | same row | letters: the **o** and the **A** |
| `screenshot_phone_ui_golke` (fixture) | Sf663a4ed, S6537cb07, Se48b6ddb, S152a196e | 2.5 x 1.8, 1.9 x 1.8, 1.9 x 1.7, 2.4 x 1.5 | 2.4, 2.0, 2.0, 1.5 | TC3ed9cd (4, 0.15) | letters: four of the five letters of the word **"Photo"** (phone UI label), at drawn size |

**Every tagged shape is a letter** (or, for the golke, a letter of its word). **Not a letter: none.** What the
two earlier builds tagged and this one does not: the gradient icon's twin frame bars, rotated bar and triangle
(`repro_gradient_white_icon`: no shape tagged now, its stitches equal OFF's), and the beanie's i-dot (cluster
spread 1.26: dropped from the row). `drone_render` and `mfab_lc`, which moved before, no longer move.

## Movers (4 of 44), worse first

**Worse: none.** One spot looked at twice: the first T's foot on `toat_beanie` (`toat_beanie__zoom4.jpg`) now ends
on a slant with a small left tip; the art's foot is flat with a left flare, so it follows the art: neutral.

| Design | Pictures | By eye |
|---|---|---|
| `toat_machine_hat` (89.5 mm) | `toat_machine_hat__whole/zoom1..3/tagged` | **better**: the A has two legs, a flat top, an open counter and a crossbar; the T bars lose the fanned patch. 17,314 -> 17,209 stitches, trims 21 -> 19 |
| `toat_beanie` | `toat_beanie__whole/zoom1..4/tagged` | **better**: the A and both T bars (zoom2, zoom3); 17,389 -> 17,349, trims 26 -> 28 |
| `otherrow_toat_machine_beanie` | `otherrow_toat_machine_beanie__whole/zoom1..3/tagged` | **better**: the A and the T bars; 17,030 -> 16,973, trims 20 -> 18 |
| `screenshot_phone_ui_golke` (fixture) | `fixture_screenshot_phone_ui_golke__whole/tagged` | no visible change: the "Photo" stays at its drawn size and no changed region shows by eye; 10,744 -> 10,726 stitches |

## Every test file that mentions text, tag, letter, border, cluster or repro_gradient, flag ON

156 files (names matching those words, plus every file mentioning `text_cluster`, `textcluster`, `repro_gradient`,
`letter_candidates`, `is_lettering` or `text_candidate`), the default temporarily True:
**2,685 passed, 18 skipped, 2 xfailed, 3 failed. No guard breach.** The three failures:
1. `test_text_cluster_mixed_caps.py::test_the_config_field_defaults_off...`: my own "defaults OFF" assertion,
   expected under the temporary True.
2. `test_stage2_photo_segment.py::...match_golden...[photo/enthusiast_logo.png]`: the known platform-numerics golden
   (CI deselects it); it fails the same way with the flag OFF.
3. `test_small_text_reset_record.py::test_the_pipeline_keeps_the_rows_and_hands_them_on`: **my own artefact**. The
   test reads `inspect.getsource(pipeline.finish_generation)`, and I merged `origin/main` into the working tree
   while the 19-minute run was in progress, so the source on disk no longer matched the imported module. Re-run on
   its own it passes with the flag OFF **and** ON (4 passed, 4 passed).
`test_borders_last.py::test_repro_fixture_border_satin_sews_after_its_cone_s_fills` (the guard the first flip
broke) passes with the flag ON.
